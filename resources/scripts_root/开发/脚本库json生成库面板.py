# script_id: bedb398e-234a-4b0a-94a6-79242efcc14f
# -*- coding: utf-8 -*-

bl_info = {
    "name": "智能脚本管理器 (Smart Script Manager)",
    "author": "代码高手 AI & YourName", 
    "version": (2, 2, 2), # 修复版 - 重构高级元数据管理逻辑，修复子操作符无法访问父操作符实例的问题
    "blender": (3, 0, 0),
    "location": "3D视图 > N面板 > 脚本",
    "description": "一个基于元数据的智能脚本管理和启动器 - 增强版 (折叠过滤器, 搜索, 多行描述, 路径修改, 上下文过滤, 分离高级元数据管理) - 修复版 2",
    "category": "Development",
}

import bpy
import os
import json
import uuid
from datetime import datetime
from bpy.props import StringProperty, EnumProperty, BoolProperty, PointerProperty, IntProperty, CollectionProperty
from bpy.app.handlers import persistent
from urllib import request, error, parse # 用于在线库功能

# =============================================================================
# 0. 路径配置 (Path Configuration)
# =============================================================================
ADDON_DIR = os.path.dirname(__file__) 
RESOURCES_DIR = "E:\\files\\code\\BlenderAddonPackageTool-master\\addons\\quick_run_scripts\\resources" # <-- 请确保此路径正确
METADATA_PATH = os.path.join(RESOURCES_DIR, "metadata.json")
SCRIPTS_ROOT_DIR = os.path.join(RESOURCES_DIR, "scripts_root")

# =============================================================================
# 1. 数据管理核心 (Data Management Core) - 增强版 + 修复
# =============================================================================

class ScriptDataManager:
    """一个单例类，用于加载、管理和保存所有脚本的元数据"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ScriptDataManager, cls).__new__(cls)
            cls._instance.metadata = {}
            cls._instance.all_tags = []
            cls._instance.is_dirty = False
            # --- 为高级元数据管理器存储临时状态 ---
            cls._instance.advanced_metadata_temp_state = {
                'new_scripts_found': [],
                'missing_scripts_found': [],
                'path_changed_scripts_found': [],
                'github_repo_owner': "Kalin-Youen",
                'github_repo_name': "scripts_lib",
                'github_branch_name': "main",
                'external_metadata_path': ""
            }
            # -------------------------------------
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
        self._normalize_script_data()

    def save_data(self):
        """将内存中的元数据保存到JSON文件"""
        if not self.metadata:
            print("智能脚本管理器：没有元数据可保存。")
            return
            
        print(f"智能脚本管理器：正在保存元数据到 '{METADATA_PATH}'...")
        try:
            os.makedirs(os.path.dirname(METADATA_PATH), exist_ok=True)
            self.metadata['metadata_last_updated'] = datetime.now().isoformat()
            with open(METADATA_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=4, ensure_ascii=False)
            print("  > 元数据保存成功。")
            self.is_dirty = False
        except IOError as e:
            print(f"  > 错误：保存元数据失败！ ({e})")

    def _initialize_empty_metadata(self):
        """初始化一个空的元数据结构"""
        self.metadata = {
            "version": "2.2.2",
            "metadata_last_updated": datetime.now().isoformat(),
            "ui_config": {
                "display_columns": 2,
                "show_descriptions_as_tooltip": True,
                "compact_mode": False,
                "show_details": False,
                "tag_filter_expanded": True,
                "tag_filter_mode": 'TOGGLE',
                "search_text": "",
                "tag_settings_expanded": True,
                "search_mode": 'INTERSECT' 
            },
            "scripts": {}
        }
        
    def _collect_all_tags(self):
        """收集所有标签"""
        tags = set()
        for script_data in self.metadata.get('scripts', {}).values():
            for tag in script_data.get('tags', []):
                tags.add(tag.strip())
        return sorted(list(tags))

    def _normalize_script_data(self):
        """确保所有脚本数据都包含必需的字段，特别是新增的 context 和 mode"""
        for script_id, data in self.metadata.get('scripts', {}).items():
            if 'local_config' not in data:
                data['local_config'] = {}
            config = data['local_config']
            if 'execution_context' not in config:
                config['execution_context'] = 'ALL'
            if 'execution_mode' not in config:
                config['execution_mode'] = 'ALL'

    def get_ui_config(self):
        """获取UI配置"""
        return self.metadata.get('ui_config', {
            "display_columns": 2,
            "show_descriptions_as_tooltip": True,
            "compact_mode": False,
            "show_details": False,
            "tag_filter_expanded": True,
            "tag_filter_mode": 'TOGGLE',
            "search_text": "",
            "tag_settings_expanded": True,
            "search_mode": 'INTERSECT'
        })

    def update_ui_config(self, **kwargs):
        """更新UI配置"""
        ui_config = self.get_ui_config()
        ui_config.update(kwargs)
        self.metadata['ui_config'] = ui_config
        self.is_dirty = True

    def get_filtered_and_sorted_scripts(self, context):
        """核心函数：根据UI设置（标签、搜索）过滤和排序脚本"""
        addon_props = context.scene.smart_script_manager_props
        
        scripts_data = self.metadata.get('scripts', {})
        filtered_scripts = scripts_data.copy()

        # --- 1. Apply Tag Filter ---
        active_tags_props = addon_props.active_tags
        active_tags = {tag.name for tag in active_tags_props if tag.is_active}
        tag_filter_mode = DATA_MANAGER.get_ui_config().get('tag_filter_mode', 'TOGGLE')
        
        if active_tags:
            if tag_filter_mode == 'TOGGLE':
                matching_script_ids = set()
                for script_id, data in scripts_data.items():
                     script_tags = set(data.get('tags', []))
                     if active_tags & script_tags:
                         matching_script_ids.add(script_id)
                filtered_scripts = {k: v for k, v in filtered_scripts.items() if k in matching_script_ids}
                
            elif tag_filter_mode == 'INTERSECT':
                matching_script_ids = set()
                for script_id, data in scripts_data.items():
                    script_tags = set(data.get('tags', []))
                    if active_tags.issubset(script_tags):
                        matching_script_ids.add(script_id)
                filtered_scripts = {k: v for k, v in filtered_scripts.items() if k in matching_script_ids}
                
            elif tag_filter_mode == 'UNION':
                matching_script_ids = set()
                for script_id, data in scripts_data.items():
                    script_tags = set(data.get('tags', []))
                    if active_tags & script_tags:
                        matching_script_ids.add(script_id)
                filtered_scripts = {k: v for k, v in filtered_scripts.items() if k in matching_script_ids}

        # --- 2. Apply Search Filter ---
        search_text = DATA_MANAGER.get_ui_config().get('search_text', '').strip().lower()
        search_mode = DATA_MANAGER.get_ui_config().get('search_mode', 'INTERSECT')
        
        if search_text:
            search_matching_script_ids = set()
            for script_id, data in filtered_scripts.items():
                name_match = search_text in data.get('display_name', '').lower()
                desc_match = search_text in data.get('description', '').lower()
                tags_match = any(search_text in tag.lower() for tag in data.get('tags', []))
                
                if name_match or desc_match or tags_match:
                    search_matching_script_ids.add(script_id)
            
            if search_mode == 'INTERSECT':
                filtered_scripts = {k: v for k, v in filtered_scripts.items() if k in search_matching_script_ids}
            elif search_mode == 'UNION':
                all_matching_ids = set(filtered_scripts.keys()) | search_matching_script_ids
                filtered_scripts = {k: v for k, v in scripts_data.items() if k in all_matching_ids}

        # --- 3. Sort ---
        sort_by = addon_props.sort_mode
        
        def sort_key(item):
            _, data = item
            config = data.get('local_config', {})
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

    # --- 新增：将高级元数据管理的核心逻辑移至此处 ---
    def scan_directory(self, directory):
        """扫描目录下的所有 .py 文件"""
        found_scripts = {}
        if not os.path.isdir(directory):
            print(f"警告：目录不存在: {directory}")
            return found_scripts
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, directory).replace('\\', '/') # 标准化路径分隔符
                    unique_key = relative_path
                    display_name = os.path.splitext(file)[0] # 去掉 .py 后缀
                    found_scripts[unique_key] = {
                        'display_name': display_name,
                        'relative_path': relative_path,
                        'full_path': full_path
                    }
        return found_scripts

    def generate_new_metadata(self, found_scripts_dict):
        """根据扫描结果生成新的元数据结构"""
        new_metadata = {
            "version": "2.2.2",
            "metadata_last_updated": datetime.now().isoformat(),
            "ui_config": self.get_ui_config(), # 保留当前UI配置
            "scripts": {}
        }
        for key, info in found_scripts_dict.items():
            script_id = str(uuid.uuid4())
            new_metadata['scripts'][script_id] = {
                "display_name": info['display_name'],
                "description": "",
                "tags": [],
                "remote_info": {
                    "file_path": info['relative_path']
                },
                "local_config": {
                    "usage_count": 0,
                    "last_used": "1970-01-01T00:00:00Z",
                    "is_favorite": False,
                    "custom_priority": 50,
                    "execution_context": "ALL",
                    "execution_mode": "ALL"
                }
            }
        return new_metadata

    def compare_metadata(self, current_metadata, found_scripts_dict):
        """比较当前元数据和扫描结果，找出新增、丢失、路径变更的脚本"""
        current_scripts = current_metadata.get('scripts', {})

        # 清空旧的对比结果
        self.advanced_metadata_temp_state['new_scripts_found'].clear()
        self.advanced_metadata_temp_state['missing_scripts_found'].clear()
        self.advanced_metadata_temp_state['path_changed_scripts_found'].clear()

        found_relative_paths = {info['relative_path'] for info in found_scripts_dict.values()}
        current_relative_paths = {data.get('remote_info', {}).get('file_path'): script_id for script_id, data in current_scripts.items()}

        # 1. 找出新增的脚本 (在目录中但不在元数据中)
        for key, info in found_scripts_dict.items():
            if info['relative_path'] not in current_relative_paths:
                self.advanced_metadata_temp_state['new_scripts_found'].append({
                    'name': f"{info['display_name']} ({info['relative_path']})",
                    'key': key,
                    'info': info
                })

        # 2. 找出丢失的脚本 (在元数据中但不在目录中)
        for rel_path, script_id in current_relative_paths.items():
            if rel_path not in found_relative_paths:
                self.advanced_metadata_temp_state['missing_scripts_found'].append({
                    'name': f"{current_scripts[script_id]['display_name']} ({rel_path})",
                    'rel_path': rel_path,
                    'script_id': script_id
                })

        # 3. 找出路径变更的脚本 (文件名相同但路径不同)
        current_filenames = {os.path.basename(rel_path): (rel_path, script_id) for rel_path, script_id in current_relative_paths.items()}
        for key, info in found_scripts_dict.items():
            filename = os.path.basename(info['relative_path'])
            if filename in current_filenames:
                old_rel_path, old_script_id = current_filenames[filename]
                if old_rel_path != info['relative_path']:
                   self.advanced_metadata_temp_state['path_changed_scripts_found'].append({
                        'name': f"{info['display_name']}: '{old_rel_path}' -> '{info['relative_path']}'",
                        'old_rel_path': old_rel_path,
                        'new_info': info,
                        'script_id': old_script_id # 假设是同一个脚本，ID不变
                    })

    def load_external_metadata(self, filepath):
        """加载外部元数据文件"""
        if not os.path.exists(filepath):
            print(f"错误：外部元数据文件不存在: {filepath}")
            return None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"错误：加载外部元数据失败: {e}")
            return None

    def merge_metadata(self, target_metadata, source_metadata, mode='ADD'):
        """合并两个元数据字典"""
        merged_scripts = target_metadata.get('scripts', {}).copy()
        source_scripts = source_metadata.get('scripts', {})
        
        if mode == 'ADD':
            # 将源元数据中的脚本添加到目标元数据中（如果ID冲突则跳过）
            for script_id, script_data in source_scripts.items():
                if script_id not in merged_scripts:
                    merged_scripts[script_id] = script_data
                else:
                    print(f"警告：合并时跳过重复ID: {script_id}")
                    
        elif mode == 'UPDATE':
            # 用源元数据中的条目更新目标元数据中已存在的条目
            for script_id, script_data in source_scripts.items():
                if script_id in merged_scripts:
                    merged_scripts[script_id] = script_data
                    
        elif mode == 'OVERWRITE':
            # 完全覆盖 scripts 部分
            merged_scripts = source_scripts.copy()
            
        target_metadata['scripts'] = merged_scripts
        # 更新时间戳
        target_metadata['metadata_last_updated'] = datetime.now().isoformat()
        return target_metadata

    def fetch_github_api(self, api_url):
        """获取 GitHub API 数据"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = request.Request(api_url, headers=headers)
            with request.urlopen(req, timeout=15) as response:
                if response.status == 200:
                    data = response.read().decode('utf-8')
                    return json.loads(data)
                else:
                    print(f"错误：GitHub API 请求失败，状态码: {response.status}")
                    return None
        except error.HTTPError as e:
            print(f"错误：GitHub HTTP 错误: {e.code} - {e.reason}")
            return None
        except Exception as e:
            print(f"错误：获取 GitHub 数据时发生错误: {e}")
            return None

    def fetch_raw_content(self, owner, repo, branch, file_path):
        """获取 GitHub 文件内容"""
        try:
            encoded_path = parse.quote(file_path)
            #raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{encoded_path}"
            raw_url = f"https://ghproxy.net/https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{encoded_path}"
        
            #raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{encoded_path}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = request.Request(raw_url, headers=headers)
            with request.urlopen(req, timeout=15) as response:
                if response.status == 200:
                    return response.read().decode('utf-8')
                else:
                    print(f"错误：获取文件内容失败，状态码: {response.status}")
                    return None
        except Exception as e:
            print(f"错误：获取文件内容时发生错误: {e}")
            return None
    # --- 结束新增逻辑 ---

DATA_MANAGER = ScriptDataManager()

# =============================================================================
# 2. 属性组 (Properties) - 增强版 + 修复
# =============================================================================
# --- 新增：定义独立的 update 函数 ---
def update_display_columns(self, context):
    """更新显示列数的回调函数"""
    DATA_MANAGER.update_ui_config(display_columns=self.display_columns)
    return None

def update_show_details(self, context):
    """更新是否显示详细信息的回调函数"""
    DATA_MANAGER.update_ui_config(show_details=self.show_details)
    return None

def update_search_text_prop(self, context):
    """更新搜索文本的回调函数"""
    bpy.ops.ssm.update_search_text(search_text=self.ssm_search_text_prop)
    return None

def update_search_mode_prop(self, context):
    """更新搜索模式的回调函数"""
    bpy.ops.ssm.set_search_mode(mode=self.ssm_search_mode_prop)
    return None

def update_tag_filter_expanded_prop(self, context):
    """更新标签过滤器展开状态的回调函数"""
    bpy.ops.ssm.toggle_tag_filter_expanded()
    return None
# --- 结束新增 ---

class SSM_TagProperty(bpy.types.PropertyGroup):
    """单个标签的属性"""
    is_active: BoolProperty(name="Active", default=False)

class SSM_AvailableTagProperty(bpy.types.PropertyGroup):
    """可用标签列表（用于编辑时选择）"""
    name: StringProperty()
    is_selected: BoolProperty(name="选择", default=False)

class SSM_DescriptionLineProperty(bpy.types.PropertyGroup):
    """脚本描述的一行"""
    text: StringProperty(name="描述行", default="")

class SSM_Properties(bpy.types.PropertyGroup):
    """主属性组"""
    active_tags: bpy.props.CollectionProperty(type=SSM_TagProperty)
    available_tags: bpy.props.CollectionProperty(type=SSM_AvailableTagProperty)
    description_lines: CollectionProperty(type=SSM_DescriptionLineProperty) 
    
    sort_mode: EnumProperty(
        name="排序方式",
        description="选择脚本的排序方式",
        items=[
            ('FAVORITE', "收藏/优先级", "按收藏状态和优先级排序"),
            ('RECENT', "最近使用", "按最后使用时间排序"), 
            ('USAGE', "使用频率", "按使用次数排序"),
            ('NAME', "名称", "按名称字母顺序排序")
        ],
        default='FAVORITE'
    )
    
    is_settings_mode: BoolProperty(name="设置模式", default=False)
    
    display_columns: IntProperty(
        name="显示列数",
        description="设置脚本显示的列数（水平方向）",
        default=2,
        min=1,
        max=6,
        update=update_display_columns
    )
    
    show_details: BoolProperty(
        name="详细信息",
        description="显示使用次数、标签等详细信息",
        default=False,
        update=update_show_details
    )

    filter_context: EnumProperty(
        name="过滤上下文",
        description="根据区域类型过滤脚本",
        items=[
            ('ALL', "所有上下文", "显示所有脚本"),
            ('VIEW_3D', "3D 视图", "仅在 3D 视图中显示"),
            ('IMAGE_EDITOR', "UV/图像编辑器", "仅在 UV/图像编辑器中显示"),
            ('NODE_EDITOR', "节点编辑器", "仅在节点编辑器中显示"),
        ],
        default='ALL',
    )
    
    filter_mode: EnumProperty(
        name="过滤模式",
        description="根据对象模式过滤脚本",
        items=[
            ('ALL', "所有模式", "显示所有脚本"),
            ('OBJECT', "物体模式", "仅在物体模式下显示"),
            ('EDIT_MESH', "编辑模式 (网格)", "仅在网格编辑模式下显示"),
            ('EDIT_CURVE', "编辑模式 (曲线)", "仅在曲线编辑模式下显示"),
            ('SCULPT', "雕刻模式", "仅在雕刻模式下显示"),
            ('POSE', "姿态模式", "仅在姿态模式下显示"),
        ],
        default='ALL',
    )

    @classmethod
    def register(cls):
        bpy.types.Scene.smart_script_manager_props = PointerProperty(type=cls)

    @classmethod
    def unregister(cls):
        del bpy.types.Scene.smart_script_manager_props

# =============================================================================
# 3. 操作符 (Operators) - 超级增强版 + 修复
# =============================================================================

class SSM_OT_ExecuteScript(bpy.types.Operator):
    """执行脚本操作符"""
    bl_idname = "ssm.execute_script"
    bl_label = "运行脚本"
    bl_description = "运行选择的脚本"
    bl_options = {'REGISTER', 'UNDO'}
    
    script_id: StringProperty()
    
    @classmethod
    def description(cls, context, properties):
        script_data = DATA_MANAGER.metadata.get('scripts', {}).get(properties.script_id)
        if script_data:
            description = script_data.get('description', '无描述')
            if len(description) > 100:
                description = description[:97] + "..."
            return description
        return "运行脚本"
    
    def execute(self, context):
        script_data = DATA_MANAGER.metadata.get('scripts', {}).get(self.script_id)
        if not script_data:
            self.report({'ERROR'}, f"未找到ID为 {self.script_id} 的元数据！")
            return {'CANCELLED'}
            
        relative_path = script_data.get('remote_info', {}).get('file_path')
        if not relative_path:
            self.report({'ERROR'}, "脚本路径信息缺失！")
            return {'CANCELLED'}
            
        absolute_path = os.path.join(SCRIPTS_ROOT_DIR, relative_path)
        
        if not os.path.exists(absolute_path):
            self.report({'ERROR'}, f"脚本文件不存在: {absolute_path}")
            return {'CANCELLED'}

        try:
            with open(absolute_path, 'r', encoding='utf-8') as file:
                script_code = file.read()
            compiled_code = compile(script_code, absolute_path, 'exec')
            exec(compiled_code, globals())

            self.report({'INFO'}, f"成功运行: {script_data.get('display_name', '未知脚本')}")
            
            if 'local_config' not in script_data:
                script_data['local_config'] = {}
            config = script_data['local_config']
            config['usage_count'] = config.get('usage_count', 0) + 1
            config['last_used'] = datetime.now().isoformat()
            
            DATA_MANAGER.is_dirty = True 

        except Exception as e:
            self.report({'ERROR'}, f"执行脚本时出错: {e}")
            return {'CANCELLED'}
        
        return {'FINISHED'}

class SSM_OT_ToggleTagFilterExpanded(bpy.types.Operator):
    bl_idname = "ssm.toggle_tag_filter_expanded"
    bl_label = "切换标签过滤器展开"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        current_state = DATA_MANAGER.get_ui_config().get('tag_filter_expanded', True)
        DATA_MANAGER.update_ui_config(tag_filter_expanded=not current_state)
        return {'FINISHED'}

class SSM_OT_SetTagFilterMode(bpy.types.Operator):
    bl_idname = "ssm.set_tag_filter_mode"
    bl_label = "设置标签过滤模式"
    bl_options = {'REGISTER', 'UNDO'}
    
    mode: EnumProperty(
        items=[
            ('TOGGLE', "切换", ""),
            ('INTERSECT', "交集", ""),
            ('UNION', "并集", "")
        ]
    )
    
    def execute(self, context):
        if self.mode == 'TOGGLE':
             props = context.scene.smart_script_manager_props
             for tag_prop in props.active_tags:
                 if tag_prop.is_active:
                     tag_prop.is_active = False
        DATA_MANAGER.update_ui_config(tag_filter_mode=self.mode)
        return {'FINISHED'}

class SSM_OT_ClearActiveTags(bpy.types.Operator):
    bl_idname = "ssm.clear_active_tags"
    bl_label = "清除标签"
    bl_description = "清除所有激活的标签过滤器"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.smart_script_manager_props
        for tag_prop in props.active_tags:
            tag_prop.is_active = False
        return {'FINISHED'}

class SSM_OT_ActivateTag(bpy.types.Operator):
    bl_idname = "ssm.activate_tag"
    bl_label = "激活标签"
    bl_options = {'REGISTER', 'UNDO'}
    
    tag_name: StringProperty()
    mode: EnumProperty(
        items=[
            ('TOGGLE', "切换", ""),
            ('ACTIVATE', "激活", ""),
            ('DEACTIVATE', "停用", "")
        ]
    )
    
    def execute(self, context):
        props = context.scene.smart_script_manager_props
        tag_filter_mode = DATA_MANAGER.get_ui_config().get('tag_filter_mode', 'TOGGLE')

        if tag_filter_mode == 'TOGGLE':
            tag_prop_clicked = next((t for t in props.active_tags if t.name == self.tag_name), None)
            if tag_prop_clicked:
                is_only_active = tag_prop_clicked.is_active
                for t in props.active_tags:
                    if t.is_active and t.name != self.tag_name:
                        is_only_active = False
                        break

                if is_only_active:
                    for t in props.active_tags:
                        t.is_active = False
                else:
                    for t in props.active_tags:
                        t.is_active = (t.name == self.tag_name)
        else:
            tag_prop = next((t for t in props.active_tags if t.name == self.tag_name), None)
            if tag_prop:
                if self.mode == 'TOGGLE':
                    tag_prop.is_active = not tag_prop.is_active
                elif self.mode == 'ACTIVATE':
                    tag_prop.is_active = True
                elif self.mode == 'DEACTIVATE':
                    tag_prop.is_active = False
        return {'FINISHED'}

class SSM_OT_UpdateSearchText(bpy.types.Operator):
    bl_idname = "ssm.update_search_text"
    bl_label = "更新搜索文本"
    bl_options = {'REGISTER', 'UNDO'}
    
    search_text: StringProperty()

    def execute(self, context):
        DATA_MANAGER.update_ui_config(search_text=self.search_text)
        return {'FINISHED'}

class SSM_OT_SetSearchMode(bpy.types.Operator):
    bl_idname = "ssm.set_search_mode"
    bl_label = "设置搜索模式"
    bl_options = {'REGISTER', 'UNDO'}
    
    mode: EnumProperty(
        items=[
            ('INTERSECT', "交集", "搜索结果与标签结果取交集"),
            ('UNION', "并集", "搜索结果与标签结果取并集")
        ]
    )
    
    def execute(self, context):
        DATA_MANAGER.update_ui_config(search_mode=self.mode)
        return {'FINISHED'}

class SSM_OT_OpenSettings(bpy.types.Operator):
    """打开脚本设置对话框"""
    bl_idname = "ssm.open_settings"
    bl_label = "脚本设置"
    bl_options = {'REGISTER', 'UNDO'}

    script_id: StringProperty()
    
    display_name: StringProperty(name="显示名称")
    script_file_path: StringProperty(
        name="脚本文件路径",
        description="关联的 Python 脚本文件的相对路径",
        subtype='FILE_PATH'
    )
    execution_context: EnumProperty(
        name="执行上下文",
        description="脚本应在哪个区域类型下执行",
        items=[
            ('ALL', "所有上下文", "在任何区域都可以执行"),
            ('VIEW_3D', "3D 视图", ""),
            ('IMAGE_EDITOR', "UV/图像编辑器", ""),
            ('NODE_EDITOR', "节点编辑器", ""),
        ]
    )
    execution_mode: EnumProperty(
        name="执行模式",
        description="脚本应在哪个对象模式下执行",
        items=[
            ('ALL', "所有模式", "在任何模式下都可以执行"),
            ('OBJECT', "物体模式", ""),
            ('EDIT_MESH', "编辑模式 (网格)", ""),
            ('EDIT_CURVE', "编辑模式 (曲线)", ""),
            ('SCULPT', "雕刻模式", ""),
            ('POSE', "姿态模式", ""),
        ]
    )

    custom_priority: IntProperty(name="优先级", min=0, max=100)
    is_favorite: BoolProperty(name="收藏")
    new_tag_name: StringProperty(name="新标签")

    def invoke(self, context, event):
        script_data = DATA_MANAGER.metadata.get('scripts', {}).get(self.script_id)
        if not script_data: 
            return {'CANCELLED'}
            
        self.display_name = script_data.get('display_name', '')
        
        remote_info = script_data.get('remote_info', {})
        self.script_file_path = remote_info.get('file_path', '')
        
        config = script_data.get('local_config', {})
        self.execution_context = config.get('execution_context', 'ALL')
        self.execution_mode = config.get('execution_mode', 'ALL')

        context.scene.smart_script_manager_props.description_lines.clear()
        desc_text = script_data.get('description', '')
        if desc_text:
             lines = desc_text.split('\n')
             for line_text in lines:
                 line_item = context.scene.smart_script_manager_props.description_lines.add()
                 line_item.text = line_text
        if len(context.scene.smart_script_manager_props.description_lines) == 0:
            context.scene.smart_script_manager_props.description_lines.add()

        self.is_favorite = config.get('is_favorite', False)
        self.custom_priority = config.get('custom_priority', 50)
        
        self._update_available_tags(context, script_data.get('tags', []))
        
        return context.window_manager.invoke_props_dialog(self, width=600)

    def _update_available_tags(self, context, current_tags):
        """更新可用标签列表"""
        props = context.scene.smart_script_manager_props
        props.available_tags.clear()
        current_tags_set = set(current_tags)
        for tag in DATA_MANAGER.all_tags:
            item = props.available_tags.add()
            item.name = tag
            item.is_selected = tag in current_tags_set

    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="基本信息", icon='INFO')
        box.prop(self, "display_name")
        
        box = layout.box()
        box.label(text="文件路径", icon='FILE')
        box.prop(self, "script_file_path")

        box = layout.box()
        box.label(text="执行条件", icon='PLAY')
        box.prop(self, "execution_context")
        box.prop(self, "execution_mode")

        box = layout.box()
        box.label(text="描述:", icon='TEXT')
        desc_props = context.scene.smart_script_manager_props.description_lines
        for i, line_prop in enumerate(desc_props):
             row = box.row()
             row.prop(line_prop, "text", text=f"行 {i+1}")
             if len(desc_props) > 1:
                 op = row.operator("ssm.remove_description_line", text="", icon='X')
                 op.line_index = i
        box.operator("ssm.add_description_line", text="添加描述行", icon='ADD')

        box.prop(self, "custom_priority")
        box.prop(self, "is_favorite")
        
        ui_config = DATA_MANAGER.get_ui_config()
        expanded = ui_config.get('tag_settings_expanded', True)
        
        box = layout.box()
        row = box.row()
        icon = 'TRIA_DOWN' if expanded else 'TRIA_RIGHT'
        row.prop(context.scene, "dummy_prop_for_tag_settings_expand", 
                 text="标签管理", icon=icon, emboss=False)
        row.operator("ssm.toggle_tag_settings_expanded", text="", icon='PREFERENCES', emboss=False)
        
        if expanded:
            props = context.scene.smart_script_manager_props
            if props.available_tags:
                flow = box.grid_flow(row_major=True, columns=3, even_columns=True, even_rows=False, align=True)
                for tag_prop in props.available_tags:
                    flow.prop(tag_prop, "is_selected", text=tag_prop.name, toggle=True)
        
            row = box.row(align=True)
            row.prop(self, "new_tag_name", text="新标签")
            add_op = row.operator("ssm.add_new_tag", text="", icon='ADD')
            add_op.tag_name = self.new_tag_name
            add_op.script_id = self.script_id

    def execute(self, context):
        script_data = DATA_MANAGER.metadata.get('scripts', {}).get(self.script_id)
        if not script_data: 
            return {'CANCELLED'}

        script_data['display_name'] = self.display_name
        
        if 'remote_info' not in script_data:
            script_data['remote_info'] = {}
        script_data['remote_info']['file_path'] = self.script_file_path
        
        if 'local_config' not in script_data:
            script_data['local_config'] = {}
        config = script_data['local_config']
        config['execution_context'] = self.execution_context
        config['execution_mode'] = self.execution_mode

        desc_lines = [line_prop.text for line_prop in context.scene.smart_script_manager_props.description_lines]
        script_data['description'] = '\n'.join(desc_lines)

        props = context.scene.smart_script_manager_props
        selected_tags = [tag.name for tag in props.available_tags if tag.is_selected]
        script_data['tags'] = selected_tags
        
        config['is_favorite'] = self.is_favorite
        config['custom_priority'] = self.custom_priority
        
        DATA_MANAGER.is_dirty = True
        DATA_MANAGER.all_tags = DATA_MANAGER._collect_all_tags()
        initialize_dynamic_properties()

        self.report({'INFO'}, f"设置已保存: {self.display_name}")
        return {'FINISHED'}

class SSM_OT_AddDescriptionLine(bpy.types.Operator):
    bl_idname = "ssm.add_description_line"
    bl_label = "添加描述行"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        line_item = context.scene.smart_script_manager_props.description_lines.add()
        line_item.text = ""
        return {'FINISHED'}

class SSM_OT_RemoveDescriptionLine(bpy.types.Operator):
    bl_idname = "ssm.remove_description_line"
    bl_label = "删除描述行"
    bl_options = {'REGISTER', 'UNDO'}
    
    line_index: IntProperty()

    def execute(self, context):
        desc_lines = context.scene.smart_script_manager_props.description_lines
        if 0 <= self.line_index < len(desc_lines):
            if len(desc_lines) > 1:
                desc_lines.remove(self.line_index)
            else:
                desc_lines[0].text = ""
        return {'FINISHED'}

bpy.types.Scene.dummy_prop_for_tag_settings_expand = BoolProperty(default=True)

class SSM_OT_ToggleTagSettingsExpanded(bpy.types.Operator):
    bl_idname = "ssm.toggle_tag_settings_expanded"
    bl_label = "切换标签设置展开"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        current_state = DATA_MANAGER.get_ui_config().get('tag_settings_expanded', True)
        DATA_MANAGER.update_ui_config(tag_settings_expanded=not current_state)
        context.scene.dummy_prop_for_tag_settings_expand = not context.scene.dummy_prop_for_tag_settings_expand
        return {'FINISHED'}

class SSM_OT_AddNewTag(bpy.types.Operator):
    """添加新标签"""
    bl_idname = "ssm.add_new_tag"
    bl_label = "添加标签"
    
    tag_name: StringProperty()
    script_id: StringProperty()
    
    def execute(self, context):
        if not self.tag_name.strip():
            return {'CANCELLED'}
            
        tag_name = self.tag_name.strip()
        if tag_name not in DATA_MANAGER.all_tags:
            DATA_MANAGER.all_tags.append(tag_name)
            DATA_MANAGER.all_tags.sort()
        
        props = context.scene.smart_script_manager_props
        
        existing = False
        for tag_prop in props.available_tags:
            if tag_prop.name == tag_name:
                tag_prop.is_selected = True
                existing = True
                break
        
        if not existing:
            item = props.available_tags.add()
            item.name = tag_name
            item.is_selected = True
        
        return {'FINISHED'}

class SSM_OT_UpdateUIConfig(bpy.types.Operator):
    """更新UI配置"""
    bl_idname = "ssm.update_ui_config"
    bl_label = "应用UI设置"
    
    def execute(self, context):
        props = context.scene.smart_script_manager_props
        DATA_MANAGER.update_ui_config(
            display_columns=props.display_columns,
            show_details=props.show_details
        )
        self.report({'INFO'}, "UI设置已保存")
        return {'FINISHED'}

# =============================================================================
# 4. 新增/修改：高级元数据管理操作符 (Advanced Metadata Manager Operator) - 优化版
# =============================================================================

class SSM_OT_AdvancedMetadataManager(bpy.types.Operator):
    """高级元数据管理器 - 独立窗口"""
    bl_idname = "ssm.advanced_metadata_manager"
    bl_label = "高级元数据管理器"
    bl_description = "管理元数据文件：扫描、对比、批量操作、导入/导出/同步"
    bl_options = {'REGISTER'}

    # --- 在线库相关属性 ---
    github_repo_owner: StringProperty(
        name="仓库所有者",
        default="Kalin-Youen",
        update=lambda self, context: setattr(DATA_MANAGER.advanced_metadata_temp_state, 'github_repo_owner', self.github_repo_owner)
    )
    github_repo_name: StringProperty(
        name="仓库名称",
        default="scripts_lib",
        update=lambda self, context: setattr(DATA_MANAGER.advanced_metadata_temp_state, 'github_repo_name', self.github_repo_name)
    )
    github_branch_name: StringProperty(
        name="分支名称",
        default="main",
        update=lambda self, context: setattr(DATA_MANAGER.advanced_metadata_temp_state, 'github_branch_name', self.github_branch_name)
    )
    external_metadata: StringProperty(
        name="外部元数据文件路径",
        subtype='FILE_PATH',
        update=lambda self, context: setattr(DATA_MANAGER.advanced_metadata_temp_state, 'external_metadata_path', self.external_metadata)
    )
    # --- 结束在线库属性 ---

    def invoke(self, context, event):
        wm = context.window_manager
        # 从 DATA_MANAGER 加载临时状态到属性
        state = DATA_MANAGER.advanced_metadata_temp_state
        self.github_repo_owner = state.get('github_repo_owner', "Kalin-Youen")
        self.github_repo_name = state.get('github_repo_name', "scripts_lib")
        self.github_branch_name = state.get('github_branch_name', "main")
        self.external_metadata = state.get('external_metadata_path', "")
        return wm.invoke_props_dialog(self, width=900) # 增加宽度以适应更多信息

    def draw(self, context):
        layout = self.layout
        state = DATA_MANAGER.advanced_metadata_temp_state # 获取临时状态
        current_scripts = DATA_MANAGER.metadata.get('scripts', {})

        # --- 元数据状态 ---
        box = layout.box()
        box.label(text="元数据状态", icon='INFO')
        col = box.column(align=True)
        col.label(text=f"脚本总数: {len(current_scripts)}")
        col.label(text=f"最后更新: {DATA_MANAGER.metadata.get('metadata_last_updated', 'N/A')}")
        col.operator("ssm.save_metadata", text="保存元数据到文件", icon='FILE_TICK')

        # --- 扫描与对比 ---
        box = layout.box()
        box.label(text="扫描与对比", icon='ZOOM_ALL')
        col = box.column(align=True)
        col.operator("ssm.scan_and_compare_metadata", text="重新扫描并对比", icon='FILE_REFRESH')
        
        # 显示对比结果 (从 DATA_MANAGER 读取)
        if state.get('new_scripts_found') or state.get('missing_scripts_found') or state.get('path_changed_scripts_found'):
            col.separator()
            col.label(text="扫描结果:", icon='ALIGN_JUSTIFY')
            
            # --- 新增脚本 ---
            if state.get('new_scripts_found'):
                box_new = box.box()
                row = box_new.row()
                row.label(text=f"新增脚本 ({len(state['new_scripts_found'])}):", icon='ADD')
                row.operator("ssm.apply_scan_changes_new", text="全部添加", icon='PLUS').action='ADD'
                for item in state['new_scripts_found']:
                    row = box_new.row()
                    row.label(text=f"ID: {item.get('script_id', 'N/A')[:8]}...")
                    row.label(text=f"名称: {item['name']}")
                    row.label(text=f"路径: {item['info']['relative_path']}")
                    op = row.operator("ssm.apply_scan_changes_new", text="", icon='ADD')
                    op.action = 'ADD_ONE'
                    op.script_key = item['key'] # 传递 key 用于添加单个

            # --- 丢失脚本 ---
            if state.get('missing_scripts_found'):
                box_missing = box.box()
                row = box_missing.row()
                row.label(text=f"丢失脚本 ({len(state['missing_scripts_found'])}):", icon='REMOVE')
                row.operator("ssm.apply_scan_changes_missing", text="全部移除", icon='X').action='REMOVE_ALL'
                for item in state['missing_scripts_found']:
                    row = box_missing.row()
                    row.label(text=f"ID: {item['script_id'][:8]}...")
                    row.label(text=f"名称: {item['name']}")
                    row.label(text=f"旧路径: {item['rel_path']}")
                    op = row.operator("ssm.apply_scan_changes_missing", text="", icon='X')
                    op.action = 'REMOVE_ONE'
                    op.script_id = item['script_id'] # 传递 ID 用于移除单个

            # --- 路径变更脚本 ---
            if state.get('path_changed_scripts_found'):
                box_changed = box.box()
                row = box_changed.row()
                row.label(text=f"路径变更 ({len(state['path_changed_scripts_found'])}):", icon='FILE_PARENT')
                row.operator("ssm.apply_scan_changes_path", text="全部更新", icon='FILE_REFRESH').action='UPDATE_ALL'
                for item in state['path_changed_scripts_found']:
                    row = box_changed.row()
                    row.label(text=f"ID: {item['script_id'][:8]}...")
                    row.label(text=f"名称: {item['name'].split(':')[0]}") # 只显示名称部分
                    row.label(text=f"新路径: {item['new_info']['relative_path']}")
                    op = row.operator("ssm.apply_scan_changes_path", text="", icon='FILE_REFRESH')
                    op.action = 'UPDATE_ONE'
                    op.script_id = item['script_id'] # 传递 ID 用于更新单个
                    op.new_rel_path = item['new_info']['relative_path'] # 传递新路径

            # --- 应用所有变更按钮 ---
            col.separator()
            col.operator("ssm.apply_scan_changes", text="应用所有扫描变更", icon='FILE_TICK')
        else:
            box.label(text="请先点击 '重新扫描并对比'", icon='INFO')

        # --- 批量操作 ---
        box = layout.box()
        box.label(text="批量操作", icon='MODIFIER')
        col = box.column(align=True)
        col.operator("ssm.batch_add_tags_from_path", text="根据路径批量添加标签", icon='BOOKMARKS')
        col.operator("ssm.batch_rename_to_filename", text="批量重置显示名为文件名", icon='SORTALPHA')

        # --- 导入/导出/同步 ---
        box = layout.box()
        box.label(text="导入/合并外部元数据", icon='IMPORT')
        box.prop(self, "external_metadata") # 使用 self 的属性
        col = box.column(align=True)
        col.operator("ssm.import_and_merge_metadata", text="导入并合并", icon='IMPORT').mode = 'ADD'
        col.operator("ssm.import_and_merge_metadata", text="导入并覆盖", icon='FILE_REFRESH').mode = 'OVERWRITE'

        box = layout.box()
        box.label(text="在线库同步", icon='WORLD')
        box.prop(self, "github_repo_owner") # 使用 self 的属性
        box.prop(self, "github_repo_name") # 使用 self 的属性
        box.prop(self, "github_branch_name") # 使用 self 的属性
        col = box.column(align=True)
        col.operator("ssm.fetch_and_merge_github_metadata", text="获取并合并在线库", icon='URL').mode = 'ADD'
        col.operator("ssm.fetch_and_merge_github_metadata", text="获取并覆盖在线库", icon='URL').mode = 'OVERWRITE'

    def execute(self, context):
        # 保存当前属性到 DATA_MANAGER 的临时状态
        state = DATA_MANAGER.advanced_metadata_temp_state
        state['github_repo_owner'] = self.github_repo_owner
        state['github_repo_name'] = self.github_repo_name
        state['github_branch_name'] = self.github_branch_name
        state['external_metadata_path'] = self.external_metadata
        return {'FINISHED'}

# --- 子操作符：扫描并对比当前元数据 - 修复版 ---
class SSM_OT_ScanAndCompareMetadata(bpy.types.Operator):
    bl_idname = "ssm.scan_and_compare_metadata"
    bl_label = "扫描并对比"
    bl_description = "重新扫描脚本目录并与当前元数据进行对比"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        print("开始扫描目录以对比当前元数据...")
        found_scripts = DATA_MANAGER.scan_directory(SCRIPTS_ROOT_DIR)
        DATA_MANAGER.compare_metadata(DATA_MANAGER.metadata, found_scripts)
        self.report({'INFO'}, "扫描和对比完成，请查看结果。")
        return {'FINISHED'}
# --- 结束子操作符 ---

# --- 子操作符：应用扫描变更 (拆分逻辑) ---
# 新增：处理新增脚本
class SSM_OT_ApplyScanChangesNew(bpy.types.Operator):
    bl_idname = "ssm.apply_scan_changes_new"
    bl_label = "应用新增变更"
    bl_options = {'REGISTER', 'UNDO'}
    
    action: EnumProperty(items=[('ADD', "添加", ""), ('ADD_ONE', "添加单个", "")])
    script_key: StringProperty() # 用于添加单个

    def execute(self, context):
        state = DATA_MANAGER.advanced_metadata_temp_state
        current_scripts = DATA_MANAGER.metadata.get('scripts', {})
        found_scripts = DATA_MANAGER.scan_directory(SCRIPTS_ROOT_DIR)

        if self.action == 'ADD':
            items_to_process = state.get('new_scripts_found', [])
        elif self.action == 'ADD_ONE':
            items_to_process = [item for item in state.get('new_scripts_found', []) if item.get('key') == self.script_key]
        else:
            items_to_process = []

        added_count = 0
        for item in items_to_process:
            info = item['info']
            script_id = str(uuid.uuid4())
            # 为新增脚本生成ID并存储
            item['script_id'] = script_id
            current_scripts[script_id] = {
                "display_name": info['display_name'],
                "description": "",
                "tags": [],
                "remote_info": {
                    "file_path": info['relative_path']
                },
                "local_config": {
                    "usage_count": 0,
                    "last_used": "1970-01-01T00:00:00Z",
                    "is_favorite": False,
                    "custom_priority": 50,
                    "execution_context": "ALL",
                    "execution_mode": "ALL"
                }
            }
            added_count += 1

        if self.action == 'ADD':
            state['new_scripts_found'].clear() # 全部添加后清空列表
        elif self.action == 'ADD_ONE':
             state['new_scripts_found'] = [item for item in state['new_scripts_found'] if item.get('key') != self.script_key]

        if added_count > 0:
            DATA_MANAGER.all_tags = DATA_MANAGER._collect_all_tags()
            DATA_MANAGER.is_dirty = True
            self.report({'INFO'}, f"已添加 {added_count} 个新增脚本。")
        else:
            self.report({'WARNING'}, "没有新增脚本被添加。")
        return {'FINISHED'}

# 新增：处理丢失脚本
class SSM_OT_ApplyScanChangesMissing(bpy.types.Operator):
    bl_idname = "ssm.apply_scan_changes_missing"
    bl_label = "应用丢失变更"
    bl_options = {'REGISTER', 'UNDO'}
    
    action: EnumProperty(items=[('REMOVE_ALL', "移除全部", ""), ('REMOVE_ONE', "移除单个", "")])
    script_id: StringProperty() # 用于移除单个

    def execute(self, context):
        state = DATA_MANAGER.advanced_metadata_temp_state
        current_scripts = DATA_MANAGER.metadata.get('scripts', {})

        if self.action == 'REMOVE_ALL':
            items_to_process = state.get('missing_scripts_found', [])
        elif self.action == 'REMOVE_ONE':
            items_to_process = [item for item in state.get('missing_scripts_found', []) if item.get('script_id') == self.script_id]
        else:
            items_to_process = []

        removed_count = 0
        for item in items_to_process:
            script_id_to_remove = item['script_id']
            current_scripts.pop(script_id_to_remove, None)
            removed_count += 1

        if self.action == 'REMOVE_ALL':
            state['missing_scripts_found'].clear()
        elif self.action == 'REMOVE_ONE':
             state['missing_scripts_found'] = [item for item in state['missing_scripts_found'] if item.get('script_id') != self.script_id]

        if removed_count > 0:
            DATA_MANAGER.all_tags = DATA_MANAGER._collect_all_tags()
            DATA_MANAGER.is_dirty = True
            self.report({'INFO'}, f"已移除 {removed_count} 个丢失脚本。")
        else:
            self.report({'WARNING'}, "没有丢失脚本被移除。")
        return {'FINISHED'}

# 新增：处理路径变更脚本
class SSM_OT_ApplyScanChangesPath(bpy.types.Operator):
    bl_idname = "ssm.apply_scan_changes_path"
    bl_label = "应用路径变更"
    bl_options = {'REGISTER', 'UNDO'}
    
    action: EnumProperty(items=[('UPDATE_ALL', "更新全部", ""), ('UPDATE_ONE', "更新单个", "")])
    script_id: StringProperty() # 用于更新单个
    new_rel_path: StringProperty() # 用于更新单个

    def execute(self, context):
        state = DATA_MANAGER.advanced_metadata_temp_state
        current_scripts = DATA_MANAGER.metadata.get('scripts', {})

        if self.action == 'UPDATE_ALL':
            items_to_process = state.get('path_changed_scripts_found', [])
        elif self.action == 'UPDATE_ONE':
            items_to_process = [item for item in state.get('path_changed_scripts_found', []) if item.get('script_id') == self.script_id]
        else:
            items_to_process = []

        updated_count = 0
        for item in items_to_process:
            script_id_to_update = item['script_id']
            new_path = item['new_info']['relative_path'] if self.action == 'UPDATE_ALL' else self.new_rel_path
            if script_id_to_update in current_scripts:
                current_scripts[script_id_to_update]['remote_info']['file_path'] = new_path
                updated_count += 1

        if self.action == 'UPDATE_ALL':
            state['path_changed_scripts_found'].clear()
        elif self.action == 'UPDATE_ONE':
             state['path_changed_scripts_found'] = [item for item in state['path_changed_scripts_found'] if item.get('script_id') != self.script_id]

        if updated_count > 0:
            DATA_MANAGER.is_dirty = True
            self.report({'INFO'}, f"已更新 {updated_count} 个脚本路径。")
        else:
            self.report({'WARNING'}, "没有脚本路径被更新。")
        return {'FINISHED'}

# 原始的 ApplyScanChanges 保留，用于应用所有变更
class SSM_OT_ApplyScanChanges(bpy.types.Operator):
    bl_idname = "ssm.apply_scan_changes"
    bl_label = "应用扫描变更"
    bl_description = "将扫描发现的所有变更（新增、丢失、路径变更）应用到当前会话"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 调用新的子操作符逻辑来处理所有变更
        # 注意：这里我们直接操作 DATA_MANAGER 的状态，因为子操作符已经处理了UI列表的更新
        state = DATA_MANAGER.advanced_metadata_temp_state
        current_scripts = DATA_MANAGER.metadata.get('scripts', {})
        found_scripts = DATA_MANAGER.scan_directory(SCRIPTS_ROOT_DIR)

        # --- 应用新增 ---
        for item in state.get('new_scripts_found', []):
             info = item['info']
             script_id = str(uuid.uuid4())
             current_scripts[script_id] = {
                 "display_name": info['display_name'],
                 "description": "",
                 "tags": [],
                 "remote_info": {
                     "file_path": info['relative_path']
                 },
                 "local_config": {
                     "usage_count": 0,
                     "last_used": "1970-01-01T00:00:00Z",
                     "is_favorite": False,
                     "custom_priority": 50,
                     "execution_context": "ALL",
                     "execution_mode": "ALL"
                 }
             }

        # --- 应用丢失（移除）---
        for item in state.get('missing_scripts_found', []):
            script_id_to_remove = item['script_id']
            current_scripts.pop(script_id_to_remove, None)

        # --- 应用路径变更 ---
        for item in state.get('path_changed_scripts_found', []):
            script_id_to_update = item['script_id']
            new_info = item['new_info']
            if script_id_to_update in current_scripts:
                current_scripts[script_id_to_update]['remote_info']['file_path'] = new_info['relative_path']

        DATA_MANAGER.all_tags = DATA_MANAGER._collect_all_tags()
        DATA_MANAGER.is_dirty = True
        # 清空临时状态
        state['new_scripts_found'].clear()
        state['missing_scripts_found'].clear()
        state['path_changed_scripts_found'].clear()
        self.report({'INFO'}, "所有扫描变更已应用。")
        return {'FINISHED'}
# --- 结束子操作符 ---

# --- 子操作符：批量操作 ---
class SSM_OT_BatchAddTagsFromPath(bpy.types.Operator):
    bl_idname = "ssm.batch_add_tags_from_path"
    bl_label = "根据路径批量添加标签"
    bl_description = "为所有脚本根据其文件夹路径添加标签"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        current_scripts = DATA_MANAGER.metadata.get('scripts', {})
        added_tags_count = 0
        updated_scripts_count = 0

        for script_id, script_data in current_scripts.items():
            rel_path = script_data.get('remote_info', {}).get('file_path', '')
            if rel_path:
                # 获取路径中的所有父文件夹作为标签
                # 例如: 'folder1/folder2/script.py' -> ['folder1', 'folder2']
                tags_from_path = [p for p in os.path.dirname(rel_path).split(os.sep) if p]
                current_tags = set(script_data.get('tags', []))
                new_tags = set(tags_from_path) - current_tags
                if new_tags:
                    script_data['tags'].extend(list(new_tags))
                    added_tags_count += len(new_tags)
                    updated_scripts_count += 1

        if updated_scripts_count > 0:
            DATA_MANAGER.all_tags = DATA_MANAGER._collect_all_tags()
            DATA_MANAGER.is_dirty = True
            initialize_dynamic_properties() # 更新UI标签列表
            self.report({'INFO'}, f"已为 {updated_scripts_count} 个脚本添加了 {added_tags_count} 个新标签。")
        else:
            self.report({'INFO'}, "没有添加新标签。")
        return {'FINISHED'}

class SSM_OT_BatchRenameToFilename(bpy.types.Operator):
    bl_idname = "ssm.batch_rename_to_filename"
    bl_label = "批量重置显示名为文件名"
    bl_description = "将所有脚本的显示名设置为与其文件名一致"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        current_scripts = DATA_MANAGER.metadata.get('scripts', {})
        updated_count = 0

        for script_id, script_data in current_scripts.items():
            rel_path = script_data.get('remote_info', {}).get('file_path', '')
            if rel_path:
                filename = os.path.splitext(os.path.basename(rel_path))[0]
                if script_data.get('display_name') != filename:
                    script_data['display_name'] = filename
                    updated_count += 1

        if updated_count > 0:
            DATA_MANAGER.is_dirty = True
            self.report({'INFO'}, f"已更新 {updated_count} 个脚本的显示名。")
        else:
            self.report({'INFO'}, "没有脚本显示名需要更新。")
        return {'FINISHED'}
# --- 结束批量操作子操作符 ---

# --- 其他子操作符 (如 SaveMetadata, ImportAndMerge, FetchAndMergeGithub) 保持不变 ---
class SSM_OT_SaveMetadata(bpy.types.Operator):
    bl_idname = "ssm.save_metadata"
    bl_label = "保存元数据"
    bl_description = "将当前内存中的元数据保存到文件"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        DATA_MANAGER.save_data()
        self.report({'INFO'}, "元数据已保存到文件。")
        return {'FINISHED'}

class SSM_OT_ImportAndMergeMetadata(bpy.types.Operator):
    bl_idname = "ssm.import_and_merge_metadata"
    bl_label = "导入并合并元数据"
    bl_description = "导入外部元数据文件并与当前元数据合并"
    bl_options = {'REGISTER', 'UNDO'}
    
    mode: EnumProperty(items=[('ADD', "添加", ""), ('OVERWRITE', "覆盖", "")])

    def execute(self, context):
        external_metadata_path = DATA_MANAGER.advanced_metadata_temp_state.get('external_metadata_path', "")
        if not external_metadata_path:
            self.report({'ERROR'}, "请先指定外部元数据文件路径。")
            return {'CANCELLED'}

        external_data = DATA_MANAGER.load_external_metadata(external_metadata_path)
        if not external_data:
            return {'CANCELLED'}

        DATA_MANAGER.metadata = DATA_MANAGER.merge_metadata(DATA_MANAGER.metadata, external_data, self.mode)
        DATA_MANAGER.all_tags = DATA_MANAGER._collect_all_tags()
        DATA_MANAGER.is_dirty = True
        initialize_dynamic_properties()
        self.report({'INFO'}, f"外部元数据已{('添加' if self.mode == 'ADD' else '覆盖')}合并。")
        return {'FINISHED'}

class SSM_OT_FetchAndMergeGithubMetadata(bpy.types.Operator):
    bl_idname = "ssm.fetch_and_merge_github_metadata"
    bl_label = "获取并合并 GitHub 元数据"
    bl_description = "从 GitHub 仓库获取元数据并与当前元数据合并"
    bl_options = {'REGISTER', 'UNDO'}
    
    mode: EnumProperty(items=[('ADD', "添加", ""), ('OVERWRITE', "覆盖", "")])

    def execute(self, context):
        state = DATA_MANAGER.advanced_metadata_temp_state
        owner = state.get('github_repo_owner', "Kalin-Youen")
        repo = state.get('github_repo_name', "scripts_lib")
        branch = state.get('github_branch_name', "main")
        file_path = "resources/metadata.json"

        print(f"正在从 GitHub 获取元数据: {owner}/{repo}/{branch}/{file_path}")
        content = DATA_MANAGER.fetch_raw_content(owner, repo, branch, file_path)
        
        if not content:
            self.report({'ERROR'}, "无法从 GitHub 获取元数据内容。")
            return {'CANCELLED'}

        try:
            github_metadata = json.loads(content)
        except json.JSONDecodeError as e:
            self.report({'ERROR'}, f"解析 GitHub 元数据失败: {e}")
            return {'CANCELLED'}

        DATA_MANAGER.metadata = DATA_MANAGER.merge_metadata(DATA_MANAGER.metadata, github_metadata, self.mode)
        DATA_MANAGER.all_tags = DATA_MANAGER._collect_all_tags()
        DATA_MANAGER.is_dirty = True
        initialize_dynamic_properties()
        self.report({'INFO'}, f"GitHub 元数据已{('添加' if self.mode == 'ADD' else '覆盖')}合并。")
        return {'FINISHED'}
# --- 结束其他子操作符 ---

# =============================================================================
# 5. UI 面板 (UI Panel) - 修复并增强版
# =============================================================================

class SSM_PT_MainPanel(bpy.types.Panel):
    """主面板"""
    bl_label = "智能脚本管理器 v2.2.2"
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
        
        if props.is_settings_mode:
            row.operator("ssm.advanced_metadata_manager", text="", icon='PREFERENCES')
            
        row.prop(props, "sort_mode", text="")
        
        config_row = header.row(align=True)
        config_row.prop(props, "display_columns", text="列数")
        config_row.prop(props, "show_details", text="详细信息", toggle=True, icon='INFO')
        config_row.operator("ssm.update_ui_config", text="", icon='FILE_TICK')

        filter_box = layout.box()
        filter_row = filter_box.row(align=True)
        filter_row.label(text="过滤:")
        filter_row.prop(props, "filter_context", text="")
        filter_row.prop(props, "filter_mode", text="")

        search_box = layout.box()
        search_row = search_box.row(align=True)
        search_text = DATA_MANAGER.get_ui_config().get('search_text', '')
        op = search_row.operator("ssm.update_search_text", text="", icon='VIEWZOOM')
        op.search_text = search_text
        search_row.prop(context.scene, "ssm_search_text_prop", text="")
        search_mode = DATA_MANAGER.get_ui_config().get('search_mode', 'INTERSECT')
        search_row.prop_menu_enum(context.scene, "ssm_search_mode_prop", text=search_mode, icon='DOWNARROW_HLT')

        tag_filter_expanded = DATA_MANAGER.get_ui_config().get('tag_filter_expanded', True)
        tag_box = layout.box()
        tag_header_row = tag_box.row()
        icon = 'TRIA_DOWN' if tag_filter_expanded else 'TRIA_RIGHT'
        tag_header_row.prop(context.scene, "ssm_tag_filter_expanded_prop", 
                           text="标签过滤器", icon=icon, emboss=False)
        sub_row = tag_header_row.row(align=True)
        sub_row.scale_x = 0.8
        tag_filter_mode = DATA_MANAGER.get_ui_config().get('tag_filter_mode', 'TOGGLE')
        sub_row.operator_menu_enum("ssm.set_tag_filter_mode", "mode", text=tag_filter_mode, icon='DOWNARROW_HLT')
        sub_row.operator("ssm.clear_active_tags", text="", icon='X')
        
        if tag_filter_expanded and DATA_MANAGER.all_tags:
            columns = props.display_columns if props.display_columns > 1 else 4
            all_tags_props = props.active_tags
            flow = tag_box.grid_flow(row_major=True, columns=columns, even_columns=True, even_rows=False, align=True)
            for tag_prop in all_tags_props:
                op_params = f"ssm.activate_tag"
                op = flow.operator(op_params, text=tag_prop.name, depress=tag_prop.is_active)
                op.tag_name = tag_prop.name
                tag_mode = DATA_MANAGER.get_ui_config().get('tag_filter_mode', 'TOGGLE')
                op.mode = 'TOGGLE'

        layout.separator()
        
        scripts_to_show = DATA_MANAGER.get_filtered_and_sorted_scripts(context)
        
        current_context = context.space_data.type if context.space_data else 'UNKNOWN'
        current_mode = context.mode if context.mode else 'UNKNOWN'
        
        filtered_scripts_final = []
        for script_id, data in scripts_to_show:
            config = data.get('local_config', {})
            req_context = config.get('execution_context', 'ALL')
            req_mode = config.get('execution_mode', 'ALL')
            
            context_match = (req_context == 'ALL' or req_context == current_context)
            mode_match = (req_mode == 'ALL' or req_mode == current_mode)
            
            if context_match and mode_match:
                filtered_scripts_final.append((script_id, data))
                
        scripts_to_show = filtered_scripts_final

        if not scripts_to_show:
            layout.label(text="没有匹配的脚本", icon='INFO')
            return

        columns = max(1, props.display_columns)
        current_row = None
        
        for i, (script_id, data) in enumerate(scripts_to_show):
            if i % columns == 0:
                current_row = layout.row(align=True)
            box = current_row.box()
            col = box.column()
            
            op_idname = SSM_OT_OpenSettings.bl_idname if props.is_settings_mode else SSM_OT_ExecuteScript.bl_idname
            op = col.operator(op_idname, text=data.get('display_name', '未知脚本'))
            op.script_id = script_id
            
            if props.show_details:
                info_row = col.row(align=True)
                if data.get('local_config', {}).get('is_favorite', False):
                    info_row.label(text="", icon='FUND')
                usage_count = data.get('local_config', {}).get('usage_count', 0)
                if usage_count > 0:
                    info_row.label(text=f"{usage_count}次", icon='LOOP_FORWARDS')
                tags = data.get('tags', [])
                if tags:
                    max_tags_to_show = 2 if columns > 2 else 3
                    for tag in tags[:max_tags_to_show]:
                        info_row.label(text=tag, icon='BOOKMARKS')
                    if len(tags) > max_tags_to_show:
                        info_row.label(text=f"+{len(tags) - max_tags_to_show}", icon='BOOKMARKS')

# --- 添加场景属性用于驱动UI状态 ---
def register_scene_props():
    bpy.types.Scene.ssm_search_text_prop = StringProperty(
        name="搜索",
        description="输入关键词搜索脚本",
        default="",
        update=update_search_text_prop
    )
    bpy.types.Scene.ssm_search_mode_prop = EnumProperty(
        name="搜索模式",
        description="搜索结果与标签过滤的组合方式",
        items=[
            ('INTERSECT', "交集", "搜索结果与标签结果取交集"),
            ('UNION', "并集", "搜索结果与标签结果取并集")
        ],
        default='INTERSECT',
        update=update_search_mode_prop
    )
    bpy.types.Scene.ssm_tag_filter_expanded_prop = BoolProperty(
        name="标签过滤器展开",
        default=True,
        update=update_tag_filter_expanded_prop
    )

def unregister_scene_props():
    del bpy.types.Scene.ssm_search_text_prop
    del bpy.types.Scene.ssm_search_mode_prop
    del bpy.types.Scene.ssm_tag_filter_expanded_prop
# -----------------------------------

# =============================================================================
# 6. 注册与注销 (Registration & Handlers) - 增强版 + 修复
# =============================================================================

classes = (
    SSM_TagProperty, 
    SSM_AvailableTagProperty,
    SSM_DescriptionLineProperty,
    SSM_Properties,
    SSM_OT_ExecuteScript, 
    SSM_OT_ToggleTagFilterExpanded,
    SSM_OT_SetTagFilterMode,
    SSM_OT_ClearActiveTags,
    SSM_OT_ActivateTag,
    SSM_OT_UpdateSearchText,
    SSM_OT_SetSearchMode,
    SSM_OT_OpenSettings,
    SSM_OT_AddDescriptionLine,
    SSM_OT_RemoveDescriptionLine,
    SSM_OT_ToggleTagSettingsExpanded,
    SSM_OT_AddNewTag,
    SSM_OT_UpdateUIConfig,
    SSM_OT_AdvancedMetadataManager,
    SSM_OT_ScanAndCompareMetadata,
    SSM_OT_ApplyScanChangesNew,
    SSM_OT_ApplyScanChangesMissing,
    SSM_OT_ApplyScanChangesPath,
    SSM_OT_ApplyScanChanges,
    SSM_OT_BatchAddTagsFromPath,
    SSM_OT_BatchRenameToFilename,
    SSM_OT_SaveMetadata,
    SSM_OT_ImportAndMergeMetadata,
    SSM_OT_FetchAndMergeGithubMetadata,
    SSM_PT_MainPanel,
)

@persistent
def save_on_exit_handler(dummy):
    """Blender关闭时自动保存"""
    if hasattr(DATA_MANAGER, 'is_dirty') and DATA_MANAGER.is_dirty:
        print("智能脚本管理器：检测到数据变化，正在自动保存...")
        DATA_MANAGER.save_data()

def initialize_dynamic_properties():
    """初始化动态属性"""
    if not hasattr(bpy.context.scene, 'smart_script_manager_props'):
        return
        
    props = bpy.context.scene.smart_script_manager_props
    current_tags = {tag.name for tag in props.active_tags}
    new_tags = set(DATA_MANAGER.all_tags)

    for tag_name in current_tags - new_tags:
        idx = next((i for i, tag in enumerate(props.active_tags) if tag.name == tag_name), -1)
        if idx != -1:
            props.active_tags.remove(idx)
    
    for tag_name in new_tags - current_tags:
        item = props.active_tags.add()
        item.name = tag_name

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    register_scene_props()
    
    DATA_MANAGER.load_data()
    DATA_MANAGER.is_dirty = False
    
    initialize_dynamic_properties()
    
    scene = bpy.context.scene
    ui_config = DATA_MANAGER.get_ui_config()
    scene.ssm_search_text_prop = ui_config.get('search_text', '')
    scene.ssm_search_mode_prop = ui_config.get('search_mode', 'INTERSECT')
    scene.ssm_tag_filter_expanded_prop = ui_config.get('tag_filter_expanded', True)
    scene.dummy_prop_for_tag_settings_expand = ui_config.get('tag_settings_expanded', True)

    if save_on_exit_handler not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(save_on_exit_handler)
    
    print("智能脚本管理器 v2.2.2 修复版 已加载完成！")

def unregister():
    if hasattr(DATA_MANAGER, 'is_dirty') and DATA_MANAGER.is_dirty:
        save_on_exit_handler(None)
    
    if save_on_exit_handler in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(save_on_exit_handler)

    unregister_scene_props()

    for cls in reversed(classes):
        if hasattr(bpy.types, cls.__name__):
            bpy.utils.unregister_class(cls)
            
    print("智能脚本管理器已卸载。")

if __name__ == "__main__":
    register()



