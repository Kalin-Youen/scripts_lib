# -*- coding: utf-8 -*-

bl_info = {
    "name": "智能脚本管理器 (Smart Script Manager)",
    "author": "代码高手 AI & YourName",
    "version": (1, 1), # 版本升级
    "blender": (3, 0, 0),
    "location": "3D视图 > N面板 > 脚本",
    "description": "一个基于元数据的智能脚本管理和启动器",
    "category": "Development",
}

import bpy
import os
import json
from datetime import datetime
from bpy.props import StringProperty, EnumProperty, BoolProperty, PointerProperty
from bpy.app.handlers import persistent

# =============================================================================
# 0. 路径配置 (Path Configuration)
# =============================================================================
# 使用 os.path.dirname(__file__) 获取插件文件所在目录，这是更健壮的方式
ADDON_DIR = os.path.dirname(__file__) 
RESOURCES_DIR = "E:\\files\\code\\BlenderAddonPackageTool-master\\addons\\quick_run_scripts\\resources"
METADATA_PATH = os.path.join(RESOURCES_DIR, "metadata.json")
SCRIPTS_ROOT_DIR = os.path.join(RESOURCES_DIR, "scripts_root")


# =============================================================================
# 1. 数据管理核心 (Data Management Core)
# =============================================================================

class ScriptDataManager:
    """一个单例类，用于加载、管理和保存所有脚本的元数据"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ScriptDataManager, cls).__new__(cls)
            # 将初始化移到单独的方法中，以便可以重新加载
            cls._instance.metadata = {}
            cls._instance.all_tags = []
        return cls._instance

    def load_data(self):
        """从JSON文件加载元数据"""
        print(f"智能脚本管理器：正在从 '{METADATA_PATH}' 加载元数据...")
        if os.path.exists(METADATA_PATH):
            try:
                with open(METADATA_PATH, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                print("  > 元数据加载成功。")
            except (json.JSONDecodeError, IOError) as e:
                print(f"  > 警告：加载元数据失败 ({e})，将使用空数据。")
                self._initialize_empty_metadata()
        else:
            print("  > 警告：元数据文件不存在，将使用空数据。")
            self._initialize_empty_metadata()
            
        self.all_tags = self._collect_all_tags()

    def save_data(self):
        """将内存中的元数据保存到JSON文件"""
        if not self.metadata:
            print("智能脚本管理器：没有元数据可保存。")
            return
            
        print(f"智能脚本管理器：正在保存元数据到 '{METADATA_PATH}'...")
        try:
            # 更新最后保存时间
            self.metadata['metadata_last_updated'] = datetime.now().isoformat()
            with open(METADATA_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=4, ensure_ascii=False)
            print("  > 元数据保存成功。")
        except IOError as e:
            print(f"  > 错误：保存元数据失败！ ({e})")

    def _initialize_empty_metadata(self):
        """初始化一个空的元数据结构"""
        self.metadata = {
            "version": "2.0",
            "metadata_last_updated": datetime.now().isoformat(),
            "scripts": {}
        }
        
    def _collect_all_tags(self):
        tags = set()
        # 确保 'scripts' 键存在
        for script_data in self.metadata.get('scripts', {}).values():
            for tag in script_data.get('tags', []):
                tags.add(tag)
        return sorted(list(tags))

    def get_filtered_and_sorted_scripts(self, context):
        """核心函数：根据UI设置过滤和排序脚本"""
        addon_props = context.scene.smart_script_manager_props
        
        filtered_scripts = {}
        active_tags_props = addon_props.active_tags
        # 使用列表推导式提高效率
        active_tags = {tag.name for tag in active_tags_props if tag.is_active}
        
        scripts_data = self.metadata.get('scripts', {})
        
        for script_id, data in scripts_data.items():
            if not active_tags:
                filtered_scripts[script_id] = data
            else:
                script_tags = set(data.get('tags', []))
                if active_tags.issubset(script_tags):
                    filtered_scripts[script_id] = data
        
        sort_by = addon_props.sort_mode
        
        def sort_key(item):
            _, data = item
            config = data['local_config']
            if sort_by == 'FAVORITE':
                return (not config.get('is_favorite', False), -config.get('custom_priority', 0))
            elif sort_by == 'RECENT':
                return config.get('last_used', "1970-01-01T00:00:00Z")
            elif sort_by == 'USAGE':
                return config.get('usage_count', 0)
            elif sort_by == 'NAME':
                return data.get('display_name', '').lower()
            return 0

        reverse_order = sort_by in ['RECENT', 'USAGE']
        
        return sorted(filtered_scripts.items(), key=sort_key, reverse=reverse_order)

# 初始化数据管理器
DATA_MANAGER = ScriptDataManager()

# =============================================================================
# 2. 属性组 (Properties) - 存储UI状态 (无变化)
# =============================================================================
class SSM_TagProperty(bpy.types.PropertyGroup):
    is_active: BoolProperty(name="Active", default=False, update=lambda s,c: bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1))

class SSM_Properties(bpy.types.PropertyGroup):
    active_tags: bpy.props.CollectionProperty(type=SSM_TagProperty)
    sort_mode: EnumProperty(
        name="排序方式",
        description="选择脚本的排序方式",
        items=[('FAVORITE', "收藏/优先级", ""), ('RECENT', "最近使用", ""), ('USAGE', "使用频率", ""), ('NAME', "名称", "")],
        default='FAVORITE'
    )
    is_settings_mode: BoolProperty(name="设置模式", default=False)
    
    @classmethod
    def register(cls):
        bpy.types.Scene.smart_script_manager_props = PointerProperty(type=cls)

    @classmethod
    def unregister(cls):
        del bpy.types.Scene.smart_script_manager_props

# =============================================================================
# 3. 操作符 (Operators) - 定义按钮行为 (已修改)
# =============================================================================
class SSM_OT_ExecuteScript(bpy.types.Operator):
    bl_idname = "ssm.execute_script"
    bl_label = "运行脚本"
    bl_options = {'REGISTER', 'UNDO'}
    
    script_id: StringProperty()
    
    def execute(self, context):
        script_data = DATA_MANAGER.metadata['scripts'].get(self.script_id)
        if not script_data:
            self.report({'ERROR'}, f"未找到ID为 {self.script_id} 的元数据！")
            return {'CANCELLED'}
            
        relative_path = script_data['remote_info']['file_path']
        # --- 真实执行逻辑 ---
        absolute_path = os.path.join(SCRIPTS_ROOT_DIR, relative_path)
        
        if not os.path.exists(absolute_path):
            self.report({'ERROR'}, f"脚本文件不存在: {absolute_path}")
            return {'CANCELLED'}

        try:
            # 使用 compile 和 exec 是执行外部脚本的推荐方式
            with open(absolute_path, 'r', encoding='utf-8') as file:
                script_code = file.read()
            compiled_code = compile(script_code, absolute_path, 'exec')
            exec(compiled_code, globals())

            self.report({'INFO'}, f"成功运行: {script_data['display_name']}")
            
            # --- 更新使用统计 ---
            config = script_data['local_config']
            config['usage_count'] = config.get('usage_count', 0) + 1
            config['last_used'] = datetime.now().isoformat()
            
            # 标记为已修改，以便在退出时保存
            DATA_MANAGER.is_dirty = True 

        except Exception as e:
            self.report({'ERROR'}, f"执行脚本时出错: {e}")
            return {'CANCELLED'}
        
        return {'FINISHED'}

class SSM_OT_OpenSettings(bpy.types.Operator):
    bl_idname = "ssm.open_settings"
    bl_label = "脚本设置"
    bl_options = {'REGISTER', 'UNDO'}

    script_id: StringProperty()

    display_name: StringProperty(name="显示名称")
    tags_str: StringProperty(name="标签 (用,分隔)")
    description: StringProperty(name="描述")
    custom_priority: bpy.props.IntProperty(name="优先级")
    is_favorite: BoolProperty(name="收藏")

    def invoke(self, context, event):
        script_data = DATA_MANAGER.metadata['scripts'].get(self.script_id)
        if not script_data: return {'CANCELLED'}
            
        self.display_name = script_data['display_name']
        self.tags_str = ", ".join(script_data.get('tags', []))
        self.description = script_data.get('description', '')
        config = script_data['local_config']
        self.is_favorite = config.get('is_favorite', False)
        self.custom_priority = config.get('custom_priority', 50)
        
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "display_name")
        layout.prop(self, "tags_str")
        layout.prop(self, "description")
        layout.prop(self, "custom_priority")
        layout.prop(self, "is_favorite")
        
    def execute(self, context):
        # --- 真实保存逻辑 ---
        script_data = DATA_MANAGER.metadata['scripts'].get(self.script_id)
        if not script_data: return {'CANCELLED'}

        script_data['display_name'] = self.display_name
        # 清理用户输入的tags
        script_data['tags'] = [tag.strip() for tag in self.tags_str.split(',') if tag.strip()]
        script_data['description'] = self.description
        
        config = script_data['local_config']
        config['is_favorite'] = self.is_favorite
        config['custom_priority'] = self.custom_priority
        
        # 标记为已修改
        DATA_MANAGER.is_dirty = True
        
        # 刷新Tag列表和UI
        DATA_MANAGER.all_tags = DATA_MANAGER._collect_all_tags()
        initialize_dynamic_properties()

        self.report({'INFO'}, f"设置已保存: {self.display_name}")
        return {'FINISHED'}

# =============================================================================
# 4. UI 面板 (UI Panel) (无变化)
# =============================================================================
class SSM_PT_MainPanel(bpy.types.Panel):
    bl_label = "智能脚本管理器"
    bl_idname = "SSM_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '脚本'

    def draw(self, context):
        layout = self.layout
        props = context.scene.smart_script_manager_props

        header = layout.box()
        row = header.row(align=True)
        icon_settings = 'SETTINGS' if props.is_settings_mode else 'MODIFIER'
        row.prop(props, "is_settings_mode", text="设置", toggle=True, icon=icon_settings)
        row.prop(props, "sort_mode", text="")

        tag_box = layout.box()
        row = tag_box.row(align=True)
        all_tags_props = props.active_tags
        for i, tag_prop in enumerate(all_tags_props):
            if i > 0 and i % 4 == 0: row = tag_box.row(align=True)
            row.prop(tag_prop, "is_active", text=tag_prop.name, toggle=True)
            
        layout.separator()
        
        scripts_to_show = DATA_MANAGER.get_filtered_and_sorted_scripts(context)
        
        if not scripts_to_show:
            layout.label(text="没有匹配的脚本", icon='INFO')
            return

        for script_id, data in scripts_to_show:
            box = layout.box()
            row = box.row()
            op_idname = SSM_OT_OpenSettings.bl_idname if props.is_settings_mode else SSM_OT_ExecuteScript.bl_idname
            op = row.operator(op_idname, text=data['display_name'])
            op.script_id = script_id

            if data['local_config'].get('is_favorite', False):
                row.label(text="", icon='FUND')

# =============================================================================
# 5. 注册与注销 (Registration & Handlers)
# =============================================================================
classes = (
    SSM_TagProperty, SSM_Properties,
    SSM_OT_ExecuteScript, SSM_OT_OpenSettings,
    SSM_PT_MainPanel,
)

@persistent
def save_on_exit_handler(dummy):
    """Blender关闭时自动保存"""
    if hasattr(DATA_MANAGER, 'is_dirty') and DATA_MANAGER.is_dirty:
        DATA_MANAGER.save_data()

def initialize_dynamic_properties():
    props = bpy.context.scene.smart_script_manager_props
    current_tags = {tag.name for tag in props.active_tags}
    new_tags = set(DATA_MANAGER.all_tags)

    # 移除不再存在的tags
    for tag_name in current_tags - new_tags:
        idx = props.active_tags.find(tag_name)
        if idx != -1:
            props.active_tags.remove(idx)
    
    # 添加新tags
    for tag_name in new_tags - current_tags:
        item = props.active_tags.add()
        item.name = tag_name

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    DATA_MANAGER.load_data()
    DATA_MANAGER.is_dirty = False # 初始化脏标记
    initialize_dynamic_properties()
    
    # 添加退出时保存的处理器
    bpy.app.handlers.save_post.append(save_on_exit_handler)

def unregister():
    # 退出前最后保存一次
    save_on_exit_handler(None)
    
    # 移除处理器
    if save_on_exit_handler in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(save_on_exit_handler)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
