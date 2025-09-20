# -*- coding: utf-8 -*-
# ──────────────────────────────────────────────────────────
#   智能材质贴图重命名工具 (运行即用版) - v2.5 (唯一材质列表版)
#   作者: Your Pro Coder
#   功能: 弹窗UI重构，只显示唯一的材质列表，并标注每个材质的使用者。
#         彻底解决UI中重复材质的问题，界面更清晰。
# ──────────────────────────────────────────────────────────

import bpy
import re
import os
from collections import defaultdict
from bpy.props import CollectionProperty, BoolProperty, PointerProperty, StringProperty, IntProperty
from bpy.types import Operator, PropertyGroup

# 全局变量，用于存储需要注册的类
_classes_to_register = []

# ===================================================================
# 1. 核心转换逻辑 (无改动)
# ===================================================================

# 贴图类型映射
texture_type_map = {
    'Specular IOR Level': 'Specular', 'Specular Tint': 'SpecularTint',
    'Base Color': 'BaseColor', 'Metallic': 'Metallic', 'Specular': 'Specular',
    'Roughness': 'Roughness', 'Normal': 'Normal', 'Alpha': 'Opacity',
    'Emission': 'Emission', 'Height': 'Height', 'Subsurface': 'Subsurface',
    'Subsurface Color': 'SubsurfaceColor', 'Subsurface Radius': 'SubsurfaceRadius',
    'Sheen': 'Sheen', 'Sheen Tint': 'SheenTint', 'Clearcoat': 'Clearcoat',
    'Clearcoat Roughness': 'ClearcoatRoughness', 'IOR': 'IOR',
    'Transmission': 'Transmission', 'Anisotropic': 'Anisotropic',
    'Anisotropic Rotation': 'AnisotropicRotation'
}

def sanitize_name(name):
    return re.sub(r'[^\w-]', '_', name.split('.')[0]).rstrip('_')

def traverse_node_tree(node, visited=None):
    visited = visited or set()
    if node in visited: return []
    visited.add(node)
    textures = []
    if node.type == 'TEX_IMAGE': textures.append(node)
    for input_socket in node.inputs:
        if input_socket.is_linked:
            for link in input_socket.links:
                textures.extend(traverse_node_tree(link.from_node, visited))
    return list(set(textures))

def rename_and_relink_texture(tex_node, new_name, unpack_path):
    image = tex_node.image
    if not image:
        print(f"节点 '{tex_node.name}' 没有图像，已跳过。")
        return False
    ext = ".jpg"
    new_filename = f"{new_name}{ext}"
    new_path = os.path.join(unpack_path, new_filename)
    if image.packed_file:
        image.unpack(method='WRITE_LOCAL')
    old_path = bpy.path.abspath(image.filepath)
    try:
        if not os.path.exists(old_path):
            original_settings = image.file_format
            image.file_format = 'JPEG'
            image.save(filepath=new_path, quality=80)
            image.file_format = original_settings
        elif old_path != new_path:
            if os.path.exists(new_path):
                os.remove(new_path)
            os.rename(old_path, new_path)
    except Exception as e:
        print(f"处理文件失败: '{old_path}' -> '{new_path}': {e}")
        return False
    image.filepath = new_path
    image.reload()
    existing_image = bpy.data.images.get(new_name)
    if existing_image and existing_image != image:
        existing_image.user_remap(image)
        bpy.data.images.remove(existing_image)
    image.name = new_name
    tex_node.name = new_name
    print(f"贴图已重命名并重新链接: {new_name}")
    return True

# ===================================================================
# 2. UI 和操作符定义 (重构为以材质为中心)
# ===================================================================

class BRT_UniqueMaterialItem(PropertyGroup):
    """代表一个唯一的材质及其信息"""
    is_selected: BoolProperty(name="", default=True)
    material: PointerProperty(type=bpy.types.Material)
    users: StringProperty(name="使用者")

class BRT_OT_SelectHelper(Operator):
    bl_idname = "brt.select_helper"
    bl_label = "选择助手"
    select_all: BoolProperty()
    def execute(self, context):
        for item in context.scene.brt_unique_materials:
            item.is_selected = self.select_all
        return {'FINISHED'}

class BRT_OT_SmartBatchRename(Operator):
    bl_idname = "brt.smart_batch_rename"
    bl_label = "批量重命名贴图"
    bl_options = {'REGISTER', 'UNDO'}

    direct_execute: BoolProperty(default=False, options={'HIDDEN'})
    
    columns: IntProperty(
        name="列数",
        description="设置材质卡片的显示列数",
        default=2,
        min=1,
        max=8
    )
    
    def cancel(self, context):
        print("操作被用户取消。")
        unregister()
        return {'CANCELLED'}

    def invoke(self, context, event):
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "请先选择至少一个物体")
            unregister()
            return {'CANCELLED'}
        
        # ★ 核心改动：构建 材质 -> [使用者] 的映射
        material_map = defaultdict(list)
        for obj in selected_objects:
            for slot in obj.material_slots:
                if slot.material:
                    material_map[slot.material].append(obj.name)
        
        unique_materials = material_map.keys()
        
        if len(unique_materials) <= 1:
            self.report({'INFO'}, "检测到单个材质，直接执行。")
            self.direct_execute = True
            return self.execute(context)
        else:
            scene = context.scene
            scene.brt_unique_materials.clear()
            # 按照材质名称排序
            for mat in sorted(unique_materials, key=lambda m: m.name):
                item = scene.brt_unique_materials.add()
                item.material = mat
                # 截断过长的使用者列表以保持UI整洁
                user_list = material_map[mat]
                if len(user_list) > 3:
                    item.users = ", ".join(user_list[:3]) + f" 等{len(user_list)}个物体"
                else:
                    item.users = ", ".join(user_list)
            
            return context.window_manager.invoke_props_dialog(self, width=600)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        row = layout.row(align=True)
        op_all = row.operator(BRT_OT_SelectHelper.bl_idname, text="全选")
        op_all.select_all = True
        op_none = row.operator(BRT_OT_SelectHelper.bl_idname, text="全不选")
        op_none.select_all = False
        row.prop(self, "columns")
        
        layout.separator()
        
        # ★ 顶级的 grid_flow 用于排列唯一的材质卡片
        grid = layout.grid_flow(columns=self.columns, even_columns=True, align=False)

        for item in scene.brt_unique_materials:
            # 每个材质是一个独立的卡片 (box)
            box = grid.box()
            
            # 卡片上半部分：勾选框和材质名
            main_row = box.row()
            main_row.prop(item, "is_selected")
            main_row.label(text=item.material.name, icon='MATERIAL')
            
            # 卡片下半部分：使用者信息
            user_row = box.row()
            user_row.alignment = 'RIGHT' # 让图标和文字靠右一点
            user_row.label(text=f"使用者: {item.users}", icon='OBJECT_DATA')

    def _process_material(self, mat, unpack_path):
        print("-" * 40)
        print(f"正在处理材质: {mat.name}")
        if not mat.use_nodes or not mat.node_tree: return
        principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not principled: return
        base_name = sanitize_name(mat.name)
        for inp in principled.inputs:
            if not inp.is_linked: continue
            start_node = inp.links[0].from_node
            texture_nodes = traverse_node_tree(start_node)
            tex_type = texture_type_map.get(inp.name, 'Other')
            for i, tex_node in enumerate(texture_nodes):
                suffix = f"_{i}" if len(texture_nodes) > 1 else ""
                new_name = f"{base_name}_{tex_type}{suffix}"
                rename_and_relink_texture(tex_node, new_name, unpack_path)
    
    def execute(self, context):
        materials_to_process = set()
        if self.direct_execute:
            materials_to_process = {s.material for o in context.selected_objects for s in o.material_slots if s.material}
        else:
            # ★ 从新的唯一材质列表中收集
            for item in context.scene.brt_unique_materials:
                if item.is_selected and item.material:
                    materials_to_process.add(item.material)

        if not materials_to_process:
            self.report({'INFO'}, "没有材质被处理。")
        else:
            unpack_path = bpy.path.abspath("//textures/")
            os.makedirs(unpack_path, exist_ok=True)
            for mat in materials_to_process:
                self._process_material(mat, unpack_path)
            self.report({'INFO'}, f"处理完成！共处理了 {len(materials_to_process)} 个材质。")
        
        unregister()
        return {'FINISHED'}

# ===================================================================
# 3. 注册、注销与执行入口
# ===================================================================

_classes_to_register = [
    BRT_UniqueMaterialItem, # ★ 更新
    BRT_OT_SelectHelper,
    BRT_OT_SmartBatchRename,
]

def register():
    """临时注册所有需要的类和属性"""
    for cls in _classes_to_register:
        bpy.utils.register_class(cls)
    # ★ 使用新的 CollectionProperty
    bpy.types.Scene.brt_unique_materials = CollectionProperty(type=BRT_UniqueMaterialItem)
    print("智能重命名工具已临时注册。")

def unregister():
    """注销所有临时注册的类和属性"""
    print("正在自动注销智能重命名工具...")
    try:
        if hasattr(bpy.types.Scene, 'brt_unique_materials'): # ★ 更新
            del bpy.types.Scene.brt_unique_materials
    except Exception as e:
        print(f"注销属性时出错: {e}")
    for cls in reversed(_classes_to_register):
        try:
            bpy.utils.unregister_class(cls)
        except (RuntimeError, ValueError):
            pass
    print("工具已成功注销。")

if __name__ == "__main__":
    unregister()
    register()
    bpy.ops.brt.smart_batch_rename('INVOKE_DEFAULT')
