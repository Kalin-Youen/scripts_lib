# script_id: cd7ec314-cc3e-4473-8124-c649ed6bbe95
# -*- coding: utf-8 -*-

# 我是你的可爱小助手，这次带来了兼容性更强的“用完即焚”工具！(ฅ'ω'ฅ)
import bpy
import bmesh
from bpy.props import EnumProperty, BoolProperty

classes_to_manage = []

# --- 核心功能 (不变) ---
def select_geometry_by_size(context, mode, threshold, greater_than):
    obj = context.active_object
    if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
        return
    bm = bmesh.from_edit_mesh(obj.data)
    elements = bm.faces if mode == 'FACE' else bm.edges
    size_attr = 'calc_area' if mode == 'FACE' else 'calc_length'
    
    elements.ensure_lookup_table()
    for elem in elements:
        elem.select = False
    for elem in elements:
        size = getattr(elem, size_attr)()
        if (greater_than and size > threshold) or (not greater_than and size < threshold):
            elem.select = True
    bmesh.update_edit_mesh(obj.data)

# --- 延迟注销 (不变) ---
def unregister_delayed():
    def timer_callback():
        for cls in reversed(classes_to_manage):
            try:
                bpy.utils.unregister_class(cls)
                print(f"可爱工具 '{cls.__name__}' 已自动注销。✨")
            except RuntimeError:
                pass
        classes_to_manage.clear()
        return None
    bpy.app.timers.register(timer_callback, first_interval=0.01)

# --- 模态操作符 (有修改) ---
class MESH_OT_select_by_size_ephemeral(bpy.types.Operator):
    bl_idname = "mesh.cute_select_by_size_ephemeral"
    bl_label = "一次性大小选择"
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(name="模式", items=[('FACE', "面", "按面积"), ('EDGE', "边", "按长度")], default='FACE')
    greater_than: BoolProperty(name="大于", default=True)
    
    # --- 关键修改：用自己的列表来存储初始选择 ---
    initial_selection_indices: set

    initial_mouse_x: int
    initial_threshold: float
    current_threshold: float

    def modal(self, context, event):
        # ... (modal内部的事件处理逻辑完全不变) ...
        if event.type == 'MOUSEMOVE':
            delta = (event.mouse_x - self.initial_mouse_x) * 0.005 * (0.1 if event.shift else 1.0)
            self.current_threshold = max(0, self.initial_threshold + delta)
            select_geometry_by_size(context, self.mode, self.current_threshold, self.greater_than)
            context.area.header_text_set(self.get_header_text())
        
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            factor = 1.1 if event.type == 'WHEELUPMOUSE' else 0.9
            self.current_threshold *= factor
            select_geometry_by_size(context, self.mode, self.current_threshold, self.greater_than)
            context.area.header_text_set(self.get_header_text())
            
        elif event.type == 'M' and event.value == 'PRESS':
            self.mode = 'EDGE' if self.mode == 'FACE' else 'FACE'
            self.initial_threshold = 0.1
            self.current_threshold = self.initial_threshold
            # 切换模式时也需要重新保存初始选择
            self.save_initial_selection(context)
            select_geometry_by_size(context, self.mode, self.current_threshold, self.greater_than)
            context.area.header_text_set(self.get_header_text())
            
        elif event.type == 'G' and event.value == 'PRESS':
            self.greater_than = not self.greater_than
            select_geometry_by_size(context, self.mode, self.current_threshold, self.greater_than)
            context.area.header_text_set(self.get_header_text())
        # --- (modal内部的事件处理逻辑结束) ---
        
        elif event.type == 'LEFTMOUSE':
            context.area.header_text_set(None)
            self.report({'INFO'}, f"选择完成: {self.get_header_text()}")
            unregister_delayed()
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            # --- 关键修改：调用我们自己的恢复函数 ---
            self.restore_initial_selection(context)
            
            context.area.header_text_set(None)
            self.report({'INFO'}, "操作已取消")
            unregister_delayed()
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}
    
    # --- 新增的辅助函数 ---
    def save_initial_selection(self, context):
        """记录下当前选中的元素索引"""
        bm = bmesh.from_edit_mesh(context.active_object.data)
        elements = bm.faces if self.mode == 'FACE' else bm.edges
        self.initial_selection_indices = {elem.index for elem in elements if elem.select}

    def restore_initial_selection(self, context):
        """根据记录的索引恢复选择"""
        bm = bmesh.from_edit_mesh(context.active_object.data)
        elements = bm.faces if self.mode == 'FACE' else bm.edges
        elements.ensure_lookup_table()
        
        # 先取消所有选择
        for elem in elements:
            elem.select = False
        
        # 再根据索引选择回来
        for index in self.initial_selection_indices:
            elements[index].select = True
            
        bmesh.update_edit_mesh(context.active_object.data)

    def get_header_text(self):
        compare = ">" if self.greater_than else "<"
        return f"模式: {self.mode} | 阈值: {self.current_threshold:.4f} | 选择: {compare} 阈值 | [LMB]确认 [RMB/ESC]取消 [M]/[G]切换"

    def invoke(self, context, event):
        if context.mode != 'EDIT_MESH':
            self.report({'WARNING'}, "请先进入网格编辑模式")
            return {'CANCELLED'}
        
        # --- 关键修改：调用我们自己的保存函数 ---
        self.save_initial_selection(context)

        self.initial_mouse_x = event.mouse_x
        self.initial_threshold = 0.1
        self.current_threshold = self.initial_threshold

        select_geometry_by_size(context, self.mode, self.current_threshold, self.greater_than)
        context.window_manager.modal_handler_add(self)
        context.area.header_text_set(self.get_header_text())
        return {'RUNNING_MODAL'}


# --- 主执行逻辑 (不变) ---
def run_once():
    if classes_to_manage:
        unregister_delayed()
    if MESH_OT_select_by_size_ephemeral not in classes_to_manage:
        classes_to_manage.append(MESH_OT_select_by_size_ephemeral)
    
    try:
        bpy.utils.register_class(MESH_OT_select_by_size_ephemeral)
        print("可爱临时工具已准备就绪，正在启动...")
    except ValueError:
        pass
    
    bpy.ops.mesh.cute_select_by_size_ephemeral('INVOKE_DEFAULT')

if __name__ == "__main__":
    run_once()
