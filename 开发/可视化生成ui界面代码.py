# -*- coding: utf-8 -*-
# ──────────────────────────────────────────────────────────
#   UI Code Generator Pro v2.5.0 (Architect Edition)
#   作者: 代码高手 (由 AI 高手以架构师视角重构)
#   功能: 通过可视化和拖拽式层级管理构建UI界面，并一键生成其Python代码。
#   更新日志 (v2.5.0):
#   - [架构] 重构UI面板，明确职责：层级面板只管根元素，属性面板管子元素。
#   - [修复] 彻底解决 'UILayout' object has no attribute 'context' 崩溃。
#   - [修复] 修正添加子元素的逻辑，现在总能添加到正确的位置。
#   - [优化] 移除冗余UI组件，界面更整洁、直观。
#   - [稳定] 改进数据刷新机制，移除不稳定的 call_soon，操作更流畅。
# ──────────────────────────────────────────────────────────
import bpy
from bpy.props import (
    StringProperty,
    EnumProperty,
    BoolProperty,
    CollectionProperty,
    PointerProperty,
    IntProperty,
)
from bpy.types import (
    PropertyGroup,
    Operator,
    Panel,
    Scene,
    UIList,
    WindowManager
)

bl_info = {
    "name": "UI Code Generator Pro (Architect Edition)",
    "author": "代码高手 (AI 高手重构版)",
    "version": (2, 5, 0),
    "blender": (3, 0, 0),
    "location": "3D Viewport > Sidebar > UI Gen Pro",
    "description": "通过拖拽式的层级管理来构建UI界面，并一键生成其Python代码。",
    "category": "Development",
    "doc_url": "https://github.com/your-repo-link-here",
}

# -------------------------------------------------------------------
# 1. 数据结构 (核心部分)
# -------------------------------------------------------------------
class UCG_ElementProperties(PropertyGroup):
    """存储单个UI元素的信息，并支持嵌套"""
    name: StringProperty(name="Name", default="Element")

    element_type: EnumProperty(
        items=[
            ('LABEL', "Label", "一个简单的文本标签"),
            ('BUTTON', "Button", "一个可点击的按钮"),
            ('SLIDER_FLOAT', "Slider (Float)", "一个浮点数滑块"),
            ('SEPARATOR', "Separator", "一条分割线"),
            ('ROW', "Row", "水平布局容器"),
            ('COLUMN', "Column", "垂直布局容器"),
            ('BOX', "Box", "带背景的容器"),
        ],
        name="Element Type"
    )

    text: StringProperty(name="Text/Label")
    icon: StringProperty(name="Icon", default="NONE")
    operator_id: StringProperty(name="Operator ID", description="按钮点击时执行的操作符ID, 如 'object.delete'")
    prop_pointer: StringProperty(name="Property Pointer", description="属性指针, 如 'context.scene.frame_end'")
    is_expanded: BoolProperty(
        name="Expanded", 
        default=True, 
        description="在UI结构视图中是否展开子项",
        # update函数是修改数据的安全上下文，可以直接调用重建列表的函数
        update=lambda s, c: rebuild_flat_list(c)
    )

class UCG_ListItem(PropertyGroup):
    """UIList中显示的扁平化列表项"""
    element_path: StringProperty()
    depth: IntProperty()

class UCG_Settings(PropertyGroup):
    """存储代码生成器的用户设置"""
    panel_label: StringProperty(name="Panel Label", default="My Generated Panel")
    panel_idname: StringProperty(name="Panel ID Name", default="OBJECT_PT_my_generated_panel")
    panel_category: StringProperty(name="Panel Category", default="My Panel")

# -------------------------------------------------------------------
# 2. 辅助函数与数据流管理
# -------------------------------------------------------------------
def get_element_from_path(context, path_str):
    if not path_str: return None
    try:
        indices = [int(i) for i in path_str.split('.')]
        collection = context.scene.ucg_ui_elements
        element = None
        for index in indices:
            if 0 <= index < len(collection):
                element = collection[index]
                collection = element.children
            else: return None
        return element
    except (ValueError, IndexError): return None

def get_parent_collection_from_path(context, path_str):
    if '.' not in path_str:
        return context.scene.ucg_ui_elements, int(path_str)
    parent_path, child_index_str = path_str.rsplit('.', 1)
    parent_element = get_element_from_path(context, parent_path)
    if parent_element:
        return parent_element.children, int(child_index_str)
    return None, -1

def rebuild_flat_list(context):
    """
    核心数据流函数：遍历树状结构，生成供 UIList 使用的扁平化“视图模型”。
    这个函数应该在任何数据结构发生变化后被调用（增、删、改、移动、展开/折叠）。
    """
    flat_list = context.scene.ucg_flat_list
    active_path = context.scene.ucg_active_element_path
    
    flat_list.clear()

    def traverse(elements, depth, path_prefix):
        for i, element in enumerate(elements):
            current_path = f"{path_prefix}{i}" if path_prefix else str(i)
            item = flat_list.add()
            item.element_path = current_path
            item.depth = depth
            
            is_container = element.element_type in ['ROW', 'COLUMN', 'BOX']
            if is_container and element.is_expanded and element.children:
                traverse(element.children, depth + 1, f"{current_path}.")

    traverse(context.scene.ucg_ui_elements, 0, "")

    # 数据变化后，根据活动路径反向更新UIList中的选中项索引
    new_active_index = -1
    for i, item in enumerate(flat_list):
        if item.element_path == active_path:
            new_active_index = i
            break
    
    # 只有在索引确实变化时才更新，防止触发不必要的update循环
    if context.scene.ucg_active_list_index != new_active_index:
        context.scene.ucg_active_list_index = new_active_index

def on_active_list_index_update(self, context):
    """当UIList中的选中项变化时，更新全局的'active_element_path'"""
    if 0 <= self.ucg_active_list_index < len(self.ucg_flat_list):
        new_path = self.ucg_flat_list[self.ucg_active_list_index].element_path
        if self.ucg_active_element_path != new_path:
            self.ucg_active_element_path = new_path
    else: # 当选择被清除时
        if self.ucg_active_element_path != "":
            self.ucg_active_element_path = ""
    
    # 强制重绘所有3D视图区域，以确保属性面板及时更新
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

# -------------------------------------------------------------------
# 3. UIList 和 操作符 (控制器)
# -------------------------------------------------------------------
class UCG_UL_ElementList(UIList):
    """UIList的实现，负责层级结构的可视化"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if index >= len(context.scene.ucg_flat_list): return

        flat_item = context.scene.ucg_flat_list[index]
        element = get_element_from_path(context, flat_item.element_path)

        if not element:
            layout.label(text=f"Invalid Path: {flat_item.element_path}", icon='ERROR')
            return

        is_container = element.element_type in ['ROW', 'COLUMN', 'BOX']
        row = layout.row(align=True)
        
        # 使用spacer实现动态缩进，更稳定
        row.label(text="", icon='BLANK1')
        for _ in range(flat_item.depth):
            row.label(text="", icon='BLANK1')

        if is_container:
            icon = 'TRIA_DOWN' if element.is_expanded else 'TRIA_RIGHT'
            row.prop(element, "is_expanded", text="", icon=icon, emboss=False)
        else:
            row.label(text="", icon='DOT')
        
        row.label(text=element.text or element.name)
        row.label(text=f"({element.element_type.replace('_', ' ').title()})")
        
        op = row.operator(UCG_OT_RemoveElement.bl_idname, text="", icon='X', emboss=False)
        op.element_path = flat_item.element_path
        
    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        if self.use_filter_sort_alpha:
            flt_flags = [self.bitflag_filter_item] * len(items)
            sorted_items = sorted(
                [(i, item) for i, item in enumerate(items)],
                key=lambda x: get_element_from_path(context, x[1].element_path).name.lower()
            )
            flt_neworder = [item[0] for item in sorted_items]
            return flt_flags, flt_neworder
        # 默认返回空列表，表示不进行任何过滤或排序，这是最稳妥的方式
        return [], []
        
    def get_drag_drop_operator(self):
        return UCG_OT_MoveElement.bl_idname

class UCG_OT_AddElement(Operator):
    bl_idname = "ucg.add_element"
    bl_label = "Add UI Element"
    bl_options = {'REGISTER', 'UNDO'}

    element_type: StringProperty()
    parent_path: StringProperty(default="")

    def execute(self, context):
        target_collection = context.scene.ucg_ui_elements
        parent_element = None
        if self.parent_path:
            parent_element = get_element_from_path(context, self.parent_path)
            if not parent_element:
                self.report({'WARNING'}, "Parent not found")
                return {'CANCELLED'}
            target_collection = parent_element.children
        
        if parent_element:
            parent_element.is_expanded = True

        new_element = target_collection.add()
        new_element.element_type = self.element_type
        new_element.name = f"New {self.element_type.replace('_', ' ').title()}"
        new_element.text = new_element.name

        # 操作结束后，统一调用数据刷新
        rebuild_flat_list(context)
        return {'FINISHED'}

class UCG_OT_RemoveElement(Operator):
    bl_idname = "ucg.remove_element"
    bl_label = "Remove UI Element"
    bl_options = {'REGISTER', 'UNDO'}

    element_path: StringProperty()

    def execute(self, context):
        if context.scene.ucg_active_element_path.startswith(self.element_path):
            context.scene.ucg_active_element_path = ""

        parent_collection, index = get_parent_collection_from_path(context, self.element_path)
        if parent_collection is not None and 0 <= index < len(parent_collection):
            parent_collection.remove(index)
        
        rebuild_flat_list(context)
        return {'FINISHED'}

class UCG_OT_MoveElement(Operator):
    bl_idname = "ucg.move_element"
    bl_label = "Move UI Element in List"
    bl_options = {'REGISTER', 'UNDO'}

    from_index: IntProperty()
    to_index: IntProperty()
    drop_mode: EnumProperty(items=[('ABOVE', 'Above', ''), ('BELOW', 'Below', ''), ('INTO', 'Into', '')])

    def copy_element_recursively(self, source_element, target_element):
        """递归复制一个元素及其所有子孙"""
        for prop in source_element.rna_type.properties:
            if not prop.is_readonly and prop.identifier != 'children':
                setattr(target_element, prop.identifier, getattr(source_element, prop.identifier))
        for child in source_element.children:
            new_child = target_element.children.add()
            self.copy_element_recursively(child, new_child)

    def execute(self, context):
        flat_list = context.scene.ucg_flat_list
        if not (0 <= self.from_index < len(flat_list) and 0 <= self.to_index < len(flat_list)):
            return {'CANCELLED'}
            
        from_path = flat_list[self.from_index].element_path
        to_path = flat_list[self.to_index].element_path
        
        if from_path == to_path or to_path.startswith(from_path + '.'):
            if to_path.startswith(from_path + '.'):
                self.report({'ERROR'}, "Cannot move a parent into its own child.")
            return {'CANCELLED'}

        from_parent_coll, from_idx = get_parent_collection_from_path(context, from_path)
        if from_parent_coll is None: return {'CANCELLED'}
        
        temp_storage = context.window_manager.ucg_temp_element
        temp_storage.clear()
        temp_element = temp_storage.add()
        self.copy_element_recursively(from_parent_coll[from_idx], temp_element)
        
        from_parent_coll.remove(from_idx)
        
        to_parent_coll, to_idx = get_parent_collection_from_path(context, to_path)
        if to_parent_coll is None: return {'CANCELLED'}

        if from_parent_coll == to_parent_coll and from_idx < to_idx:
            to_idx -= 1
        
        to_element = get_element_from_path(context, to_path)
        is_to_container = to_element and to_element.element_type in ['ROW', 'COLUMN', 'BOX']

        target_coll, insert_idx = to_parent_coll, to_idx
        parent_path_for_new = to_path.rsplit('.', 1)[0] if '.' in to_path else ""

        if self.drop_mode == 'INTO' and is_to_container:
            target_coll, insert_idx = to_element.children, len(to_element.children)
            to_element.is_expanded = True
            parent_path_for_new = to_path
        elif self.drop_mode == 'BELOW':
            insert_idx += 1
        
        new_element = target_coll.add()
        self.copy_element_recursively(temp_element, new_element)
        target_coll.move(len(target_coll) - 1, insert_idx)
        
        new_path = f"{parent_path_for_new}.{insert_idx}" if parent_path_for_new else str(insert_idx)
        context.scene.ucg_active_element_path = new_path
        rebuild_flat_list(context)
        return {'FINISHED'}

# ... 其他操作符 (Generate, Copy, Clear) 保持不变，它们逻辑清晰 ...
class UCG_OT_GenerateCode(Operator):
    bl_idname = "ucg.generate_code"
    bl_label = "Generate UI Code"
    def execute(self, context):
        settings = context.scene.ucg_settings
        def generate_recursive(elements, current_layout_var, indent_level):
            lines = []
            indent = "    " * indent_level
            for element in elements:
                text_prop = f'text="{element.text}"' if element.text else ""
                icon_prop = f"icon='{element.icon}'" if element.icon and element.icon != 'NONE' else ""
                props = ", ".join(filter(None, [text_prop, icon_prop]))
                if element.element_type == 'LABEL': 
                    lines.append(f'{indent}{current_layout_var}.label({props})')
                elif element.element_type == 'BUTTON':
                    op_id = element.operator_id or "wm.url_open_preset"
                    lines.append(f'{indent}{current_layout_var}.operator("{op_id}", {props})')
                elif element.element_type == 'SLIDER_FLOAT':
                    prop_ptr = element.prop_pointer or "context.scene.frame_start"
                    try:
                        obj_path, prop_name = prop_ptr.rsplit('.', 1)
                        lines.append(f'{indent}{current_layout_var}.prop({obj_path}, "{prop_name}", text="{element.text}")')
                    except ValueError:
                        lines.append(f'{indent}# Invalid property pointer: "{prop_ptr}"')
                        lines.append(f'{indent}{current_layout_var}.prop(context.scene, "frame_start", text="{element.text}")')
                elif element.element_type == 'SEPARATOR': 
                    lines.append(f'{indent}{current_layout_var}.separator()')
                elif element.element_type in ['ROW', 'COLUMN', 'BOX']:
                    child_layout_var = element.element_type.lower()
                    if element.element_type == 'ROW': 
                        lines.append(f'{indent}{child_layout_var} = {current_layout_var}.row(align=True)')
                    elif element.element_type == 'COLUMN': 
                        lines.append(f'{indent}{child_layout_var} = {current_layout_var}.column(align=True)')
                    elif element.element_type == 'BOX': 
                        lines.append(f'{indent}{child_layout_var} = {current_layout_var}.box()')
                    if element.children:
                        lines.extend(generate_recursive(element.children, child_layout_var, indent_level + 1))
                    else:
                        lines.append(f'{indent}{child_layout_var}.label(text="Empty {element.element_type.title()}")')
            return lines
        code_lines = ["import bpy", "", "class MyUIPanel(bpy.types.Panel):", f'    bl_label = "{settings.panel_label}"', f'    bl_idname = "{settings.panel_idname}"', "    bl_space_type = 'VIEW_3D'", "    bl_region_type = 'UI'", f'    bl_category = "{settings.panel_category}"', "", "    def draw(self, context):", "        layout = self.layout", ""]
        code_lines.extend(generate_recursive(context.scene.ucg_ui_elements, 'layout', 2))
        code_lines.extend(["", "def register():", "    bpy.utils.register_class(MyUIPanel)", "", "def unregister():", "    bpy.utils.unregister_class(MyUIPanel)", "", "if __name__ == \"__main__\":", "    register()"])
        context.scene.ucg_generated_code = "\n".join(code_lines)
        self.report({'INFO'}, "UI Code Generated!")
        return {'FINISHED'}

class UCG_OT_CopyCode(Operator):
    bl_idname = "ucg.copy_code"
    bl_label = "Copy Code to Clipboard"
    def execute(self, context):
        context.window_manager.clipboard = context.scene.ucg_generated_code
        self.report({'INFO'}, "Code copied to clipboard!")
        return {'FINISHED'}

class UCG_OT_ClearAllElements(Operator):
    bl_idname = "ucg.clear_all_elements"
    bl_label = "Clear All UI Elements"
    bl_options = {'REGISTER', 'UNDO'}
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)
    def execute(self, context):
        context.scene.ucg_ui_elements.clear()
        context.scene.ucg_active_element_path = ""
        rebuild_flat_list(context)
        self.report({'INFO'}, "All UI elements cleared.")
        return {'FINISHED'}
# -------------------------------------------------------------------
# 4. 界面面板 (视图)
# -------------------------------------------------------------------
def draw_add_element_buttons(layout, parent_path=""):
    """一个可复用的函数，用于绘制添加元素的按钮组"""
    label = "Add Child Element:" if parent_path else "Add Root Element:"
    layout.label(text=label)
    
    row = layout.row(align=True)
    op = row.operator(UCG_OT_AddElement.bl_idname, text="Label"); op.element_type, op.parent_path = 'LABEL', parent_path
    op = row.operator(UCG_OT_AddElement.bl_idname, text="Button"); op.element_type, op.parent_path = 'BUTTON', parent_path
    op = row.operator(UCG_OT_AddElement.bl_idname, text="Slider"); op.element_type, op.parent_path = 'SLIDER_FLOAT', parent_path
    
    row = layout.row(align=True)
    op = row.operator(UCG_OT_AddElement.bl_idname, text="Row"); op.element_type, op.parent_path = 'ROW', parent_path
    op = row.operator(UCG_OT_AddElement.bl_idname, text="Column"); op.element_type, op.parent_path = 'COLUMN', parent_path
    op = row.operator(UCG_OT_AddElement.bl_idname, text="Box"); op.element_type, op.parent_path = 'BOX', parent_path

class UCG_PT_HierarchyPanel(Panel):
    """
    [视图] UI结构主面板。
    职责：显示层级列表，提供添加“根”元素和清空的功能。
    """
    bl_label = "UI Structure"
    bl_idname = "UCG_PT_hierarchy_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'UI Gen Pro'
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # UIList本身会处理绘制，draw函数中不应再包含复杂逻辑
        layout.template_list(
            "UCG_UL_ElementList", "", 
            scene, "ucg_flat_list", 
            scene, "ucg_active_list_index", 
            rows=8
        )
        
        box = layout.box()
        # 在此面板，parent_path永远是""，表示添加根元素
        draw_add_element_buttons(box, parent_path="")
        box.separator()
        box.operator(UCG_OT_ClearAllElements.bl_idname, text="Clear All", icon="TRASH")
        
class UCG_PT_ElementPropertiesPanel(Panel):
    """
    [视图] 元素属性面板。
    职责：显示和编辑当前选中元素的属性，如果元素是容器，则提供添加“子”元素的功能。
    """
    bl_label = "Element Properties"
    bl_idname = "UCG_PT_element_properties_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'UI Gen Pro'
    bl_order = 2
    bl_parent_id = UCG_PT_HierarchyPanel.bl_idname # 将此面板嵌套在主面板下

    @classmethod
    def poll(cls, context):
        # 仅当有元素被选中时才显示此面板
        return context.scene.ucg_active_element_path != ""

    def draw(self, context):
        layout = self.layout
        active_element = get_element_from_path(context, context.scene.ucg_active_element_path)
        if not active_element: # 安全检查
            return

        box = layout.box()
        box.prop(active_element, "text")
        box.prop(active_element, "icon")

        if active_element.element_type == 'BUTTON':
            box.prop(active_element, "operator_id")
        elif active_element.element_type == 'SLIDER_FLOAT':
            box.prop(active_element, "prop_pointer")

        # [核心逻辑] 仅当选中项是容器时，才显示添加子元素的按钮
        if active_element.element_type in ['ROW', 'COLUMN', 'BOX']:
            box.separator()
            # 在此面板，parent_path是当前活动元素的路径
            draw_add_element_buttons(box, parent_path=context.scene.ucg_active_element_path)

class UCG_PT_PreviewAndCodePanel(Panel):
    """[视图] 预览和代码生成面板。职责单一。"""
    bl_label = "Preview & Code"
    bl_idname = "UCG_PT_preview_and_code_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'UI Gen Pro'
    bl_order = 3
    
    def draw_live_preview(self, layout, elements, context):
        for element in elements:
            # ... (代码与之前版本相同，省略以保持简洁)
            if element.element_type == 'LABEL': 
                layout.label(text=element.text, icon=element.icon)
            elif element.element_type == 'BUTTON': 
                op_id = element.operator_id or "wm.url_open_preset"
                layout.operator(op_id, text=element.text, icon=element.icon)
            elif element.element_type == 'SLIDER_FLOAT':
                try:
                    obj_path, prop_name = (element.prop_pointer or "context.scene.frame_start").rsplit('.', 1)
                    target_obj = eval(obj_path, {"bpy": bpy, "context": context})
                    layout.prop(target_obj, f'"{prop_name}"', text=element.text)
                except Exception:
                    row = layout.row(align=True); row.alert = True
                    row.label(text=f"Invalid Pointer", icon='ERROR')
            elif element.element_type == 'SEPARATOR': 
                layout.separator()
            elif element.element_type in ['ROW', 'COLUMN', 'BOX']:
                sub_layout = layout.row(align=True) if element.element_type == 'ROW' else \
                             layout.column(align=True) if element.element_type == 'COLUMN' else \
                             layout.box()
                if element.children: 
                    self.draw_live_preview(sub_layout, element.children, context)
                else: 
                    sub_layout.label(text=f"Empty {element.element_type.title()}", icon='INFO')

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        box = layout.box()
        box.label(text="Live Preview")
        preview_box = box.box()

        if scene.ucg_ui_elements:
            self.draw_live_preview(preview_box, scene.ucg_ui_elements, context)
        else:
            preview_box.label(text="Add elements in 'UI Structure' to see a preview.", icon='INFO')
        
        layout.separator()
        
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Generated Code", icon="TEXT")
        row.operator(UCG_OT_GenerateCode.bl_idname, icon="CON_ACTION")
        row.operator(UCG_OT_CopyCode.bl_idname, text="", icon="COPYDOWN")
        
        if scene.ucg_generated_code:
            code_box = box.box()
            for line in scene.ucg_generated_code.splitlines():
                code_box.label(text=line)

class UCG_PT_SettingsPanel(Panel):
    """[视图] 设置面板。职责单一。"""
    bl_label = "Generator Settings"
    bl_idname = "UCG_PT_settings_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'UI Gen Pro'
    bl_order = 0
    def draw(self, context):
        layout = self.layout
        settings = context.scene.ucg_settings
        box = layout.box()
        box.label(text="Generated Panel Properties:")
        box.prop(settings, "panel_label")
        box.prop(settings, "panel_idname")
        box.prop(settings, "panel_category")

# -------------------------------------------------------------------
# 5. 注册与注销
# -------------------------------------------------------------------
classes = (
    UCG_ElementProperties, UCG_ListItem, UCG_Settings,
    UCG_UL_ElementList,
    UCG_OT_AddElement, UCG_OT_RemoveElement, UCG_OT_MoveElement, UCG_OT_GenerateCode,
    UCG_OT_CopyCode, UCG_OT_ClearAllElements,
    UCG_PT_SettingsPanel, UCG_PT_HierarchyPanel, UCG_PT_ElementPropertiesPanel, UCG_PT_PreviewAndCodePanel
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    setattr(UCG_ElementProperties, 'children', CollectionProperty(type=UCG_ElementProperties))

    Scene.ucg_ui_elements = CollectionProperty(type=UCG_ElementProperties)
    Scene.ucg_flat_list = CollectionProperty(type=UCG_ListItem)
    Scene.ucg_active_list_index = IntProperty(name="Active List Index", default=-1, update=on_active_list_index_update)
    Scene.ucg_active_element_path = StringProperty(name="Active Element Path")
    Scene.ucg_generated_code = StringProperty(name="Generated Code", default="Click 'Generate UI Code'...")
    Scene.ucg_settings = PointerProperty(type=UCG_Settings)

    WindowManager.ucg_temp_element = CollectionProperty(type=UCG_ElementProperties)

def unregister():
    del WindowManager.ucg_temp_element
    del Scene.ucg_settings
    del Scene.ucg_generated_code
    del Scene.ucg_active_element_path
    del Scene.ucg_active_list_index
    del Scene.ucg_flat_list
    del Scene.ucg_ui_elements
    
    if hasattr(UCG_ElementProperties, 'children'):
        delattr(UCG_ElementProperties, 'children')
        
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    try: unregister()
    except (RuntimeError, AttributeError): pass
    register()
