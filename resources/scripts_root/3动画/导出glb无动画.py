# script_id: 87ca0a9d-41d3-4140-8e57-10f064fa12b7
# -*- coding: utf-8 -*-
import bpy
import os

def export_active_object_with_custom_settings():
    """
    将当前活动物体导出为 GLB 文件。
    - 文件名基于活动物体的名称。
    - 保存在 .blend 文件同级目录下的 "GLB" 文件夹中。
    - 使用您提供的全套自定义参数进行导出。
    """
    # --- 1. 安全检查 ---
    if not bpy.data.is_saved:
        bpy.context.window_manager.popup_menu(
            lambda self, context: self.layout.label(text="请先保存 .blend 文件！"),
            title="操作失败", icon='ERROR'
        )
        return {'CANCELLED'}

    active_obj = bpy.context.active_object
    if not active_obj:
        bpy.context.window_manager.popup_menu(
            lambda self, context: self.layout.label(text="请先选择一个物体！"),
            title="操作失败", icon='ERROR'
        )
        return {'CANCELLED'}

    # --- 2. 准备动态路径和文件名 (这是脚本的核心优势) ---
    blend_file_dir = os.path.dirname(bpy.data.filepath)
    export_folder = os.path.join(blend_file_dir, "GLB")
    
    if not os.path.exists(export_folder):
        os.makedirs(export_folder)
        print(f"已创建文件夹: {export_folder}")

    # 使用活动物体的名称作为文件名 (忽略您提供的硬编码文件名)
    file_name = f"{active_obj.name}.glb"
    export_path = os.path.join(export_folder, file_name)

    # --- 3. 使用您的全部自定义设置执行导出 ---
    print(f"准备导出 '{active_obj.name}' 到: {export_path}")

    bpy.ops.export_scene.gltf(
        # 动态文件路径 (关键！)
        filepath=export_path,
        
        # ▼▼▼ 以下是您提供的全部自定义参数 ▼▼▼
        export_format='GLB',
        use_selection=True,
        export_apply=False, # 注意：您的设置是False，通常建议为True来应用修改器
        
        # General
        ui_tab='GENERAL',
        export_copyright='',
        export_image_format='AUTO',
        export_image_add_webp=False,
        export_image_webp_fallback=False,
        export_texture_dir='',
        export_jpeg_quality=75,
        export_image_quality=75,
        export_keep_originals=False,
        
        # Mesh
        export_texcoords=True,
        export_normals=True,
        export_gn_mesh=False,
        export_draco_mesh_compression_enable=False,
        export_draco_mesh_compression_level=6,
        export_draco_position_quantization=14,
        export_draco_normal_quantization=10,
        export_draco_texcoord_quantization=12,
        export_draco_color_quantization=10,
        export_draco_generic_quantization=12,
        export_tangents=False,
        export_materials='EXPORT',
        export_unused_images=False,
        export_unused_textures=False,
        export_vertex_color='MATERIAL',
        export_all_vertex_colors=True,
        export_active_vertex_color_when_no_material=True,
        export_attributes=False,
        
        # Object
        use_mesh_edges=False,
        use_mesh_vertices=False,
        export_cameras=False,
        use_visible=False,
        use_renderable=False,
        use_active_collection_with_nested=True,
        use_active_collection=False,
        use_active_scene=False,
        at_collection_center=False,
        export_extras=False,
        export_yup=True,
        export_shared_accessors=False,
        
        # Animation
        export_animations=False,
        export_frame_range=False,
        export_frame_step=1,
        export_force_sampling=True,
        export_pointer_animation=False,
        export_animation_mode='NLA_TRACKS',
        export_nla_strips_merged_animation_name='Animation',
        export_def_bones=True,
        export_hierarchy_flatten_bones=False,
        export_hierarchy_flatten_objs=False,
        export_armature_object_remove=False,
        export_leaf_bone=False,
        export_optimize_animation_size=True,
        export_optimize_animation_keep_anim_armature=True,
        export_optimize_animation_keep_anim_object=True,
        export_optimize_disable_viewport=False,
        export_negative_frame='CROP',
        export_anim_slide_to_zero=True,
        export_bake_animation=False,
        export_anim_single_armature=True,
        export_reset_pose_bones=True,
        export_current_frame=True,
        export_rest_position_armature=True,
        export_anim_scene_split_object=True,
        
        # Skinning
        export_skins=True,
        export_influence_nb=4,
        export_all_influences=False,
        
        # Shape Keys
        export_morph=True,
        export_morph_normal=True,
        export_morph_tangent=False,
        export_morph_animation=True,
        export_morph_reset_sk_data=True,
        
        # Others
        export_lights=False,
        export_try_sparse_sk=True,
        export_try_omit_sparse_sk=False,
        export_gpu_instances=False,
        export_action_filter=False,
        export_convert_animation_pointer=False,
        export_nla_strips=True,
        export_original_specular=False,
        export_hierarchy_full_collections=False,
        export_extra_animations=False
    )
    
    print("=" * 40)
    print(f"成功导出！文件保存在: {export_path}")
    print("=" * 40)

    return {'FINISHED'}

# --- 当在 Blender 文本编辑器中点击 "运行脚本" 时，执行此函数 ---
if __name__ == "__main__":
    export_active_object_with_custom_settings()

