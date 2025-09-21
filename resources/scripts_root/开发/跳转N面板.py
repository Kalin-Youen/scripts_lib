# -*- coding: utf-8 -*-
# ──────────────────────────────────────────────────────────
#   N-Panel Quick Access (Multi-Context) - v3.3 ROBUST with Popup Window
#   作者: Claude Code AI & Your Name
#   功能: 多上下文智能N面板快捷访问，全面支持各种编辑器
#         - [修复] 解决了在紧凑UI下无法切换面板的上下文错误
#         - [增强] 切换面板的操作符现在更加健壮，能适应各种UI布局
#         - [新增] 在面板顶部标签右方增加一个按钮，用于弹出独立窗口
#   适配: Blender 4.3, 4.4+
# ──────────────────────────────────────────────────────────

bl_info = {
    "name": "N-Panel Quick Access (Multi-Context) with Popup",
    "author": "Claude Code AI",
    "version": (3, 3, 0),
    "blender": (4, 0, 0),
    "location": "Press F3 -> Search 'N-Panel Quick Access'",
    "description": "Provides a powerful, compact dialog to quickly access N-panel tabs, with settings saved per context. Includes a button to pop out the N-panel.",
    "warning": "",
    "doc_url": "",
    "category": "Interface",
}


import bpy
import json
import os
import platform
import ctypes
from ctypes import c_int, c_void_p, POINTER, windll, wintypes
from bpy.props import StringProperty, CollectionProperty, IntProperty, BoolProperty, PointerProperty
from bpy.types import Operator, PropertyGroup, AddonPreferences

# 全局变量，用于标记设置是否已从文件加载
_settings_loaded = False

# =============================================================================
# === Windows API 定义 (已增强，增加坐标转换)
# =============================================================================
try:
    if platform.system() == "Windows":
        user32 = windll.user32
        kernel32 = windll.kernel32

        # --- 结构体定义 ---
        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        # --- API 函数原型 ---
        SetWindowPos = user32.SetWindowPos
        SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, c_int, c_int, c_int, c_int, wintypes.UINT]
        SetWindowPos.restype = wintypes.BOOL

        EnumWindows = user32.EnumWindows
        EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
        EnumWindows.restype = wintypes.BOOL

        GetWindowThreadProcessId = user32.GetWindowThreadProcessId
        GetWindowThreadProcessId.argtypes = [wintypes.HWND, POINTER(wintypes.DWORD)]
        GetWindowThreadProcessId.restype = wintypes.DWORD

        GetCurrentProcessId = kernel32.GetCurrentProcessId
        GetCurrentProcessId.restype = wintypes.DWORD

        IsWindow = user32.IsWindow
        IsWindow.argtypes = [wintypes.HWND]
        IsWindow.restype = wintypes.BOOL

        # 【新增】用于坐标转换
        ClientToScreen = user32.ClientToScreen
        ClientToScreen.argtypes = [wintypes.HWND, POINTER(POINT)]
        ClientToScreen.restype = wintypes.BOOL

        # --- 常量 ---
        HWND_TOP = 0
        SWP_NOMOVE = 0x0002
        SWP_NOZORDER = 0x0004
        SWP_SHOWWINDOW = 0x0040
    else:
        user32 = kernel32 = None
        print("提示：当前非 Windows 系统，窗口定位与缩放功能将不可用。")

except (AttributeError, OSError):
    print("警告：未能加载 user32.dll 或 kernel32.dll。")
    user32 = kernel32 = None


# =============================================================================
# === 定义 wmWindow 结构体
# =============================================================================
class wmWindow(ctypes.Structure):
    _fields_ = [
        ("next", c_void_p), ("prev", c_void_p), ("main", c_void_p),
        ("screen", c_void_p), ("ghostwin", c_void_p), ("parent", c_void_p),
        ("scene", c_void_p), ("winid", c_int), ("posx", c_int),
        ("posy", c_int), ("sizex", c_int), ("sizey", c_int),
    ]

# =============================================================================
# === 辅助函数
# =============================================================================
def _find_hwnd_from_bpy_window(target_win: bpy.types.Window) -> int:
    """【新增】通过 bpy.types.Window 对象反向查找其窗口句柄 (HWND)。"""
    for hwnd in get_process_hwnds(GetCurrentProcessId()):
        found_win = _find_bpy_window_by_hwnd(hwnd)
        if found_win and found_win.as_pointer() == target_win.as_pointer():
            return hwnd
    return 0

def get_process_hwnds(pid: int) -> set:
    """获取属于指定进程ID (PID) 的所有顶层窗口句柄。"""
    hwnds = set()

    def enum_callback(hwnd, _):
        process_id = wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        if process_id.value == pid:
            hwnds.add(hwnd)
        return True

    callback_ptr = WNDENUMPROC(enum_callback)
    EnumWindows(callback_ptr, 0)
    return hwnds

def _find_bpy_window_by_hwnd(hwnd) -> bpy.types.Window:
    """通过 HWND 反向查找对应的 bpy.types.Window 对象。"""
    for win in bpy.context.window_manager.windows:
        try:
            c_win = ctypes.cast(win.as_pointer(), POINTER(wmWindow)).contents
            if not c_win.ghostwin:
                continue
            for offset in range(0, 128, 8):
                try:
                    hwnd_ptr = ctypes.cast(c_win.ghostwin + offset, POINTER(wintypes.HWND))
                    if hwnd_ptr.contents.value == hwnd:
                        return win
                except:
                    continue
        except:
            continue
    return None

# =============================================================================
# === 核心窗口控制器 (已增强，支持定位)
# =============================================================================
class PopupWindowResizer:
    """弹出新窗口并调整其大小和位置。"""
    active_instances = []

    def __init__(self, width: int, height: int, x: int = None, y: int = None, on_success=None, on_failure=None, max_retries: int = 20, interval: float = 0.05):
        self.target_width = width
        self.target_height = height
        self.target_x = x
        self.target_y = y
        self.on_success = on_success
        self.on_failure = on_failure
        self.max_retries = max_retries
        self.interval = interval

        self.retries_left = self.max_retries
        self.before_hwnds = set()
        self.pid = 0

    def execute(self):
        if not user32 or not kernel32:
            self._fail("Windows API 未加载")
            return

        self.pid = GetCurrentProcessId()
        self.before_hwnds = get_process_hwnds(self.pid)

        PopupWindowResizer.active_instances.append(self)
        bpy.ops.screen.area_dupli('INVOKE_DEFAULT')
        bpy.app.timers.register(self._poll_and_resize, first_interval=self.interval)
        pos_str = f" at ({self.target_x}, {self.target_y})" if self.target_x is not None else ""
        print(f"📌 已发送弹出请求，目标尺寸: {self.target_width}x{self.target_height}{pos_str}")

    def _poll_and_resize(self):
        if self.retries_left <= 0:
            self._fail("超时：未检测到新窗口")
            return None

        after_hwnds = get_process_hwnds(self.pid)
        new_hwnds = after_hwnds - self.before_hwnds

        if len(new_hwnds) == 1:
            new_hwnd = new_hwnds.pop()
            if not IsWindow(new_hwnd):
                self._fail("窗口句柄已失效")
                return None

            flags = SWP_NOZORDER | SWP_SHOWWINDOW
            x, y = 0, 0
            if self.target_x is None or self.target_y is None:
                flags |= SWP_NOMOVE
            else:
                x, y = self.target_x, self.target_y

            success = SetWindowPos(
                new_hwnd, HWND_TOP, x, y,
                self.target_width, self.target_height,
                flags
            )

            if not success:
                self._fail("SetWindowPos 失败")
                return None

            new_bpy_window = self._find_bpy_window_by_hwnd(new_hwnd)
            if new_bpy_window:
                print(f"🎉 成功获取 bpy.types.Window 对象 (ID: {new_bpy_window.as_pointer()})")
                self._success(new_bpy_window)
            else:
                self._fail("无法关联到 bpy.types.Window")

            return None
        else:
            self.retries_left -= 1
            return self.interval

    def _success(self, window: bpy.types.Window):
        if self.on_success:
            try:
                self.on_success(window)
            except Exception as e:
                print(f"⚠️ on_success 回调中发生错误: {e}")
        self._cleanup()

    def _fail(self, reason: str):
        print(f"❌ {reason}")
        if self.on_failure:
            try:
                self.on_failure(reason)
            except Exception as e:
                print(f"⚠️ on_failure 回调中发生错误: {e}")
        self._cleanup()

    def _cleanup(self):
        if self in PopupWindowResizer.active_instances:
            PopupWindowResizer.active_instances.remove(self)

# =============================================================================
# === 核心功能函数
# =============================================================================
def _get_n_panel_width_from_context() -> int:
    """辅助函数：从当前上下文中安全地获取N面板的宽度。"""
    area = bpy.context.area
    if not area:
        return 0
    space = area.spaces.active
    if not hasattr(space, 'show_region_ui'):
        return 0
    was_closed = not space.show_region_ui
    if was_closed:
        space.show_region_ui = True
        bpy.context.view_layer.update()
    ui_region = next((r for r in area.regions if r.type == 'UI' and r.alignment == 'RIGHT'), None)
    n_panel_width = ui_region.width if ui_region else 0
    if was_closed:
        space.show_region_ui = False
        bpy.context.view_layer.update()
    if n_panel_width > 0:
        print(f"  - 检测到N面板宽度: {n_panel_width}px。")
    return n_panel_width

def popup_editor_window(width=500, height=800, on_success=None, on_failure=None, add_n_panel_width=False, center_on_area=True):
    """【最终版】弹出编辑器窗口，可居中定位、合并N面板宽度，并返回窗口对象。"""
    source_area = bpy.context.area
    if not source_area:
        if on_failure:
            on_failure("无有效编辑器区域")
        return {'CANCELLED'}

    target_width = width
    if add_n_panel_width:
        print("🔎 正在计算N面板宽度...")
        n_panel_w = _get_n_panel_width_from_context()
        target_width += n_panel_w
        print(f"  - 最终目标宽度: {width}(基础) + {n_panel_w}(N面板) = {target_width}px")

    pos_x, pos_y = None, None
    if center_on_area and user32:
        print("🌍 正在计算窗口居中位置...")
        main_window = bpy.context.window
        main_hwnd = _find_hwnd_from_bpy_window(main_window)

        if main_hwnd:
            area_top_left_y_client = main_window.height - source_area.y - source_area.height
            point = POINT(source_area.x, area_top_left_y_client)
            ClientToScreen(main_hwnd, ctypes.byref(point))

            area_center_x_screen = point.x + source_area.width // 2
            area_center_y_screen = point.y + source_area.height // 2

            pos_x = area_center_x_screen - target_width // 2
            pos_y = area_center_y_screen - height // 2
            print(f"  - 目标位置计算完成: ({pos_x}, {pos_y})")
        else:
            print("  - 警告: 未能找到主窗口句柄，无法居中。")

    resizer = PopupWindowResizer(
        width=target_width, height=height, x=pos_x, y=pos_y,
        on_success=on_success, on_failure=on_failure
    )
    resizer.execute()
    return {'RUNNING_MODAL'}


def open_n_panel_in_window(target_window: bpy.types.Window):
    """在指定的 bpy.types.Window 中激活 N 面板。"""
    try:
        for area in target_window.screen.areas:
            if area.type == 'VIEW_3D':
                with bpy.context.temp_override(window=target_window, area=area):
                    bpy.ops.view3d.sidebar('INVOKE_DEFAULT', action='OPEN')
                print(f"✅ 在窗口 {target_window} 中打开了 N 面板")
                return True
        return False
    except Exception as e:
        print(f"❌ 打开 N 面板失败: {e}")
        return False
def cleanup_3d_view_ui(target_window: bpy.types.Window):
    """【终极强化版】在新窗口的3D视图中，关闭所有多余UI，只保留内容区和N面板。"""
    print("🧹 正在终极清理新窗口的3D视图UI...")
    try:
        for area in target_window.screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                with bpy.context.temp_override(window=target_window, area=area, space=space):
                    
                    # --- 1. 关闭顶部工具头 (Tool Header) ---
                    if hasattr(space, 'show_region_tool_header'):
                        space.show_region_tool_header = False
                        print("  - ✅ 已关闭顶部工具头 (Tool Header)")

                    # --- 2. 关闭左侧工具栏 (T Panel) ---
                    if hasattr(space, 'show_region_toolbar') and space.show_region_toolbar:
                        space.show_region_toolbar = False
                        print("  - ✅ 已关闭左侧工具栏 (T Panel)")

                    # --- 3. 关闭底部工具设置栏 (Tool Settings) ---
                    if hasattr(space, 'show_tool_settings') and space.show_tool_settings:
                        space.show_tool_settings = False
                        print("  - ✅ 已关闭底部工具设置栏")

                    # --- 4. 关闭所有 Gizmo 和导航控件 ---
                    if hasattr(space, 'show_gizmo') and space.show_gizmo:
                        space.show_gizmo = False
                        print("  - ✅ 已关闭所有 Gizmo")

                    # --- 5. 关闭视图叠加层（网格、原点、线框等）---
                    if hasattr(space, 'overlay') and space.overlay:
                        space.overlay.show_overlays = False
                        print("  - ✅ 已关闭所有视图叠加层 (网格/原点/线框等)")

                    # --- 6. （可选）隐藏标题栏（窗口顶部的 Screen 标签栏）---
                    # 注意：这会隐藏 Screen 名字，慎用
                    # area.show_region_header = False
                    # print("  - ⚠️ 已隐藏区域标题栏（Screen 标签）")

                # 刷新区域
                area.tag_redraw()
                print(f"🎉 3D视图UI清理完成！窗口: {target_window}")
                return

        print("⚠️ 未找到 3D View 区域进行清理")
    except Exception as e:
        print(f"❌ 清理3D视图UI时发生错误: {e}")
# =============================================================================
# === 使用示例 (最终版)
# =============================================================================
def on_window_ready(window: bpy.types.Window):
    """当新窗口准备就绪时，执行一系列配置操作。"""
    print(f"🌟 新窗口已就绪: {window}，尺寸与位置已精确设置。")
    cleanup_3d_view_ui(window)
    open_n_panel_in_window(window)

def on_window_failed(reason: str):
    print(f"💥 窗口创建失败: {reason}")

# ===================================================================
# 1. 数据结构 (无变化)
# ===================================================================
class QAP_QuickItem(PropertyGroup):
    """快捷访问项"""
    name: StringProperty(name="面板名")
    category: StringProperty(name="类别ID")
    area_type: StringProperty(name="区域类型")

class QAP_ContextData(PropertyGroup):
    """上下文数据"""
    context_mode: StringProperty(name="模式")
    area_type: StringProperty(name="区域类型")
    items: CollectionProperty(type=QAP_QuickItem)

class QAP_GlobalData(PropertyGroup):
    """全局数据存储 (运行时)"""
    contexts: CollectionProperty(type=QAP_ContextData)


# ===================================================================
# 2. 核心工具函数 (无变化)
# ===================================================================
def get_config_path():
    """获取配置文件的标准路径"""
    addon_name = __name__.split('.')[0]
    config_dir = os.path.join(bpy.utils.user_resource('CONFIG'), 'scripts', 'addons', addon_name)
    
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
        
    return os.path.join(config_dir, "qap_settings.json")

def save_settings(context):
    """将当前设置保存到JSON文件"""
    settings = context.window_manager.qap_data
    filepath = get_config_path()
    
    data_to_save = {
        'contexts': [
            {
                'context_mode': ctx.context_mode,
                'area_type': ctx.area_type,
                'items': [
                    {
                        'name': item.name,
                        'category': item.category,
                        'area_type': item.area_type
                    } for item in ctx.items
                ]
            } for ctx in settings.contexts
        ]
    }
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        print(f"N-Panel Quick Access: 设置已保存到 {filepath}")
    except Exception as e:
        print(f"N-Panel Quick Access: 保存设置失败! 错误: {e}")

def load_settings(context):
    """从JSON文件加载设置"""
    global _settings_loaded
    if _settings_loaded:
        return

    filepath = get_config_path()
    settings = context.window_manager.qap_data
    settings.contexts.clear() 

    if not os.path.exists(filepath):
        print("N-Panel Quick Access: 未找到配置文件，将使用默认空设置。")
        _settings_loaded = True
        return

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        
        for ctx_dict in loaded_data.get('contexts', []):
            new_ctx = settings.contexts.add()
            new_ctx.context_mode = ctx_dict.get('context_mode', '')
            new_ctx.area_type = ctx_dict.get('area_type', '')
            
            for item_dict in ctx_dict.get('items', []):
                new_item = new_ctx.items.add()
                new_item.name = item_dict.get('name', '')
                new_item.category = item_dict.get('category', '')
                new_item.area_type = item_dict.get('area_type', '')
        
        print(f"N-Panel Quick Access: 设置已从 {filepath} 加载。")
    except Exception as e:
        print(f"N-Panel Quick Access: 加载设置失败! 文件可能已损坏。错误: {e}")
    
    _settings_loaded = True

def get_current_context():
    """获取当前精确上下文（区域类型 + 模式）"""
    context = bpy.context
    area = context.area
    area_type = area.type if area else 'VIEW_3D'
    
    if area_type == 'VIEW_3D':
        if not hasattr(context, 'mode'): return f"{area_type}_OBJECT"
        mode = context.mode
        obj = context.active_object
        if obj and obj.type == 'MESH' and mode == 'EDIT': return f"{area_type}_EDIT_MESH"
        elif obj and obj.type == 'CURVE' and mode == 'EDIT': return f"{area_type}_EDIT_CURVE"
        elif obj and obj.type == 'ARMATURE' and mode == 'EDIT': return f"{area_type}_EDIT_ARMATURE"
        elif mode == 'SCULPT': return f"{area_type}_SCULPT"
        elif mode == 'WEIGHT_PAINT': return f"{area_type}_WEIGHT_PAINT"
        elif mode == 'TEXTURE_PAINT': return f"{area_type}_TEXTURE_PAINT"
        else: return f"{area_type}_{mode}"
    elif area_type == 'TEXT_EDITOR': return f"{area_type}_TEXT"
    elif area_type == 'NODE_EDITOR':
        space = area.spaces.active if area else None
        if space and hasattr(space, 'tree_type'): return f"{area_type}_{space.tree_type}"
        return f"{area_type}_GENERIC"
    elif area_type == 'IMAGE_EDITOR':
        space = area.spaces.active if area else None
        if space and hasattr(space, 'mode'): return f"{area_type}_{space.mode}"
        return f"{area_type}_VIEW"
    elif area_type == 'SEQUENCE_EDITOR':
        space = area.spaces.active if area else None
        if space and hasattr(space, 'view_type'): return f"{area_type}_{space.view_type}"
        return f"{area_type}_SEQUENCER"
    else:
        return f"{area_type}_GENERIC"

def get_real_available_categories():
    """获取当前真实可用的N面板类别（支持多区域）"""
    context = bpy.context
    area = context.area
    if not area: return []
    
    area_type = area.type
    categories = set()
    
    for region in area.regions:
        if region.type == 'UI':
            for panel_cls in bpy.types.Panel.__subclasses__():
                if getattr(panel_cls, 'bl_space_type', None) == area_type and \
                   getattr(panel_cls, 'bl_region_type', None) == 'UI':
                    category = getattr(panel_cls, 'bl_category', None)
                    if category:
                        try:
                            if hasattr(panel_cls, 'poll') and not panel_cls.poll(context):
                                continue
                            categories.add(category)
                        except Exception:
                            continue
            break
    return sorted(list(categories))

def get_current_data(context):
    """获取当前上下文的数据"""
    load_settings(context)
    settings = context.window_manager.qap_data
    current_context = get_current_context()
    area_type = context.area.type if context.area else 'VIEW_3D'
    
    for ctx_data in settings.contexts:
        if ctx_data.context_mode == current_context and ctx_data.area_type == area_type:
            return ctx_data
    
    new_ctx = settings.contexts.add()
    new_ctx.context_mode = current_context
    new_ctx.area_type = area_type
    return new_ctx

def get_context_display_name(context_mode):
    """获取上下文的友好显示名称"""
    name_map = {
        'VIEW_3D_OBJECT': '3D视图 - 物体模式', 'VIEW_3D_EDIT_MESH': '3D视图 - 网格编辑',
        'VIEW_3D_EDIT_CURVE': '3D视图 - 曲线编辑', 'VIEW_3D_EDIT_ARMATURE': '3D视图 - 骨骼编辑',
        'VIEW_3D_SCULPT': '3D视图 - 雕刻模式', 'VIEW_3D_WEIGHT_PAINT': '3D视图 - 权重绘制',
        'VIEW_3D_TEXTURE_PAINT': '3D视图 - 纹理绘制', 'TEXT_EDITOR_TEXT': '文本编辑器',
        'NODE_EDITOR_ShaderNodeTree': '着色器节点', 'NODE_EDITOR_GeometryNodeTree': '几何节点',
        'NODE_EDITOR_CompositorNodeTree': '合成节点', 'IMAGE_EDITOR_VIEW': '图像编辑器 - 查看',
        'IMAGE_EDITOR_PAINT': '图像编辑器 - 绘制', 'SEQUENCE_EDITOR_SEQUENCER': '视频序列编辑器',
    }
    if context_mode.startswith("NODE_EDITOR_"):
        node_name = context_mode.replace("NODE_EDITOR_", "").replace("NodeTree", " 节点")
        return name_map.get(context_mode, node_name)
    return name_map.get(context_mode, context_mode)


# ===================================================================
# 3. 操作符 (关键修复)
# ===================================================================
class QAP_OT_JumpPanel(Operator):
    """跳转到N面板, 执行后会关闭对话框"""
    bl_idname = "qap.jump_panel"
    bl_label = "跳转面板"
    bl_options = {'INTERNAL'}
    
    category: StringProperty()
    target_area_type: StringProperty()
    
    def execute(self, context):
        if self.target_area_type and self.target_area_type != context.area.type:
            self.report({'INFO'}, f"请先点击切换到 '{self.target_area_type}' 区域")
            return {'FINISHED'}
        
        available = get_real_available_categories()
        if self.category not in available:
            self.report({'ERROR'}, f"面板 '{self.category}' 在当前上下文不可用")
            return {'CANCELLED'}
        
        area = context.area
        ui_region = None
        if area:
            for region in area.regions:
                if region.type == 'UI':
                    ui_region = region
                    break
        
        if not ui_region:
            self.report({'WARNING'}, f"未找到 {area.type if area else '当前'} 区域的UI面板")
            return {'CANCELLED'}

        # 【核心修复】创建精确的上下文覆盖，强制命令在正确的区域执行
        override = {'area': area, 'region': ui_region}
        
        try:
            # 主要方法：使用上下文覆盖来调用操作符
            bpy.ops.wm.context_set_string(override, data_path="area.ui_type", value=self.category)
            area.tag_redraw()
            return {'FINISHED'}
        except Exception as e:
            # 备用方法：直接修改区域属性，兼容性更强
            try:
                # 在某些情况下，这个旧方法可能仍然有效
                ui_region.active_panel_category = self.category
                area.tag_redraw()
                return {'FINISHED'}
            except Exception as e_fallback:
                self.report({'ERROR'}, f"无法切换到 '{self.category}': {str(e_fallback)}")
                return {'CANCELLED'}


class QAP_OT_AddItem(Operator):
    """添加快捷项"""
    bl_idname = "qap.add_item"
    bl_label = "添加"
    bl_options = {'INTERNAL'}
    
    category: StringProperty()
    
    def execute(self, context):
        ctx_data = get_current_data(context)
        area_type = context.area.type if context.area else 'VIEW_3D'
        
        if any(item.category == self.category for item in ctx_data.items):
            return {'CANCELLED'}
        
        new_item = ctx_data.items.add()
        new_item.category = self.category
        new_item.name = self.category
        new_item.area_type = area_type
        
        save_settings(context)
        return {'FINISHED'}

class QAP_OT_RemoveItem(Operator):
    """移除快捷项"""
    bl_idname = "qap.remove_item"
    bl_label = "移除"
    bl_options = {'INTERNAL'}
    
    index: IntProperty()
    
    def execute(self, context):
        ctx_data = get_current_data(context)
        if 0 <= self.index < len(ctx_data.items):
            ctx_data.items.remove(self.index)
            save_settings(context)
        return {'FINISHED'}

# 新增操作符：弹出N面板窗口
class QAP_OT_PopupNPanel(Operator):
    """弹出一个包含N面板的独立窗口"""
    bl_idname = "qap.popup_n_panel"
    bl_label = "弹出N面板窗口"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        print("\n--- 启动带UI清理、居中定位和N面板宽度计算的终极窗口弹出程序 ---")

        popup_editor_window(
            width=0,
            height=500,
            add_n_panel_width=True,
            center_on_area=True,
            on_success=on_window_ready,
            on_failure=on_window_failed
        )
        return {'FINISHED'}

# ===================================================================
# 4. 主界面 (精简设计无变化，但添加了弹出按钮)
# ===================================================================
class QAP_OT_MainDialog(Operator):
    """主对话框（多上下文支持）"""
    bl_idname = "qap.main_dialog"
    bl_label = "N-Panel Quick Access"
    
    edit_mode: BoolProperty(name="编辑模式", default=False)
    columns: IntProperty(name="列数", default=3, min=1, max=6)
    show_all: BoolProperty(name="添加新面板", default=False)
    show_other_contexts: BoolProperty(name="显示其它上下文", default=False)
    
    def invoke(self, context, event):
        load_settings(context)
        return context.window_manager.invoke_props_dialog(self, width=450)
    
    def execute(self, context):
        return {'FINISHED'}
    
    def draw(self, context):
        layout = self.layout
        ctx_data = get_current_data(context)

        # ────────────────  编辑模式  ────────────────
        if self.edit_mode:
            header_row = layout.row(align=True)
            current_mode = get_current_context()
            context_name = get_context_display_name(current_mode)
            header_row.label(text=f"当前: {context_name}", icon='WORKSPACE')
            
            # 在编辑模式下，在标题行右侧添加弹出按钮
            header_row.operator(QAP_OT_PopupNPanel.bl_idname, text="", icon='WINDOW')
            
            header_row.prop(self, "edit_mode", text="", icon='SETTINGS', toggle=True)
            layout.separator()

            box = layout.box()
            sub_header = box.row(align=True)
            sub_header.label(text="当前快捷方式", icon='PINNED')
            sub_header.prop(self, "columns", text="")
            
            if not ctx_data.items:
                box.label(text="无快捷方式，请从下方添加", icon='INFO')
            else:
                flow = box.grid_flow(columns=self.columns, even_columns=True, align=True)
                for i, item in enumerate(ctx_data.items):
                    row = flow.row(align=True)
                    row.label(text=item.name) 
                    op_del = row.operator(QAP_OT_RemoveItem.bl_idname, text="", icon='X', emboss=False)
                    op_del.index = i
            
            layout.separator(factor=0.5)
            
            add_box = layout.box()
            add_row = add_box.row(align=True)
            add_row.prop(self, "show_all", icon="TRIA_DOWN" if self.show_all else "TRIA_RIGHT", 
                         icon_only=True, emboss=False)
            add_row.label(text="添加新面板")
            
            if self.show_all:
                available = get_real_available_categories()
                added = {item.category for item in ctx_data.items}
                to_add = [cat for cat in available if cat not in added]
                
                if to_add:
                    flow = add_box.grid_flow(columns=self.columns, even_columns=True, align=True)
                    for cat in to_add:
                        op = flow.operator(QAP_OT_AddItem.bl_idname, text=cat, icon='ADD')
                        op.category = cat
                else:
                    add_box.label(text="所有可用面板均已添加", icon='CHECKMARK')

            settings = context.window_manager.qap_data
            other_contexts = [c for c in settings.contexts if c != ctx_data and c.items]
            if other_contexts:
                other_box = layout.box()
                other_row = other_box.row(align=True)
                other_row.prop(self, "show_other_contexts", icon="TRIA_DOWN" if self.show_other_contexts else "TRIA_RIGHT", 
                               icon_only=True, emboss=False)
                other_row.label(text=f"其它上下文快捷方式 ({len(other_contexts)})")

                if self.show_other_contexts:
                    for other_ctx in other_contexts:
                        other_box.separator(factor=0.5)
                        other_name = get_context_display_name(other_ctx.context_mode)
                        other_box.label(text=other_name, icon='OUTLINER_OB_LIGHT')
                        
                        flow = other_box.grid_flow(columns=self.columns, even_columns=True, align=True)
                        for item in other_ctx.items:
                            flow.label(text=item.name)

        # ────────────────  默认紧凑视图  ────────────────
        else:
            if not ctx_data.items:
                col = layout.column(align=True)
                col.label(text="没有快捷方式", icon='INFO')
                col.label(text="点击右侧齿轮图标进行设置")
            else:
                flow = layout.grid_flow(columns=self.columns, even_columns=True, align=True)
                for item in ctx_data.items:
                    op = flow.operator(QAP_OT_JumpPanel.bl_idname, text=item.name)
                    op.category = item.category
                    op.target_area_type = item.area_type
            
            layout.separator()
            footer_row = layout.row(align=True)
            footer_row.alignment = 'RIGHT'
            # 在非编辑模式下，也在底部右侧添加弹出按钮
            footer_row.operator(QAP_OT_PopupNPanel.bl_idname, text="", icon='WINDOW')
            footer_row.prop(self, "edit_mode", text="", icon='SETTINGS', toggle=True)


# ===================================================================
# 5. 注册管理 (无变化)
# ===================================================================
classes = (
    QAP_QuickItem,
    QAP_ContextData,
    QAP_GlobalData,
    QAP_OT_JumpPanel,
    QAP_OT_AddItem,
    QAP_OT_RemoveItem,
    QAP_OT_PopupNPanel, # 新增
    QAP_OT_MainDialog,
)

def register():
    print("注册 N-Panel Quick Access Multi-Context v3.3 with Popup...")
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.WindowManager.qap_data = PointerProperty(type=QAP_GlobalData)

def unregister():
    print("注销 N-Panel Quick Access...")
    if hasattr(bpy.context, 'window_manager') and hasattr(bpy.context.window_manager, 'qap_data'):
        save_settings(bpy.context)

    del bpy.types.WindowManager.qap_data
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    global _settings_loaded
    _settings_loaded = False


# ===================================================================
# 6. 执行入口 (仅用于测试)
# ===================================================================
if __name__ == "__main__":
    try: unregister()
    except Exception: pass
    register()
    bpy.ops.qap.main_dialog('INVOKE_DEFAULT')




