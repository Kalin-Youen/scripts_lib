import bpy
import os
import re
import sys          # 导入 sys 模块，用于判断操作系统
import subprocess   # 导入 subprocess 模块，用于执行系统命令

# EXPORT_SETTINGS 字典保持不变，与您提供的一致
EXPORT_SETTINGS = dict(
    export_format='GLB',
    use_selection=True,
    export_apply=False,
    ui_tab='GENERAL',
    export_copyright='',
    export_image_format='AUTO',
    export_image_add_webp=False,
    export_image_webp_fallback=False,
    export_texture_dir='',
    export_jpeg_quality=75,
    export_image_quality=75,
    export_keep_originals=False,
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
    export_animations=True,
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
    export_skins=True,
    export_influence_nb=4,
    export_all_influences=False,
    export_morph=True,
    export_morph_normal=True,
    export_morph_tangent=False,
    export_morph_animation=True,
    export_morph_reset_sk_data=True,
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

# +++ 新增函数：用于跨平台打开文件夹 +++
def open_folder(path):
    """
    根据当前操作系统，打开指定的文件夹路径。
    """
    if not os.path.isdir(path):
        print(f"Error: Folder not found at '{path}'")
        return

    try:
        if sys.platform == "win32":
            # Windows
            os.startfile(path)
        elif sys.platform == "darwin":
            # macOS
            subprocess.Popen(["open", path])
        else:
            # Linux and other Unix-like systems
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"Error opening folder: {e}")


def sanitize(name: str) -> str:
    """
    清理文件名中的非法字符。
    """
    return re.sub(r'[\\/:*?"<>|]', '_', name)


def selected_roots():
    """
    从当前选择的物体中，找出所有层级的根物体。
    """
    sel = bpy.context.selected_objects
    if not sel:
        return []
    names = {o.name for o in sel}
    return [o for o in sel if o.parent is None or o.parent.name not in names]


def select_hierarchy(obj, selected_set):
    """
    递归选择一个物体和它的所有子物体。
    """
    obj.select_set(True)
    selected_set.add(obj)
    for c in obj.children:
        select_hierarchy(c, selected_set)


def export_hierarchy_to_glb():
    """
    主函数：将选择的每个物体层级导出为独立的 GLB 文件。
    """
    # 检查 .blend 文件是否已保存
    if not bpy.data.is_saved:
        bpy.context.window_manager.popup_menu(
            lambda s, c: s.layout.label(text="请先保存您的 .blend 文件！"),
            title="错误", icon='ERROR')
        return {'CANCELLED'}

    # 获取选择的根物体
    roots = selected_roots()
    if not roots:
        bpy.context.window_manager.popup_menu(
            lambda s, c: s.layout.label(text="请至少选择一个物体！"),
            title="错误", icon='ERROR')
        return {'CANCELLED'}

    # 准备输出目录
    blend_dir = os.path.dirname(bpy.data.filepath)
    out_dir = os.path.join(blend_dir, "GLB")
    os.makedirs(out_dir, exist_ok=True)

    # 保存原始选择
    original_selection = list(bpy.context.selected_objects)
    
    # 循环导出每个根物体的层级
    for r in roots:
        # 清空选择，然后仅选择当前层级
        bpy.ops.object.select_all(action='DESELECT')
        temp_sel = set()
        select_hierarchy(r, temp_sel)
        
        # 定义并导出文件
        filepath = os.path.join(out_dir, f"{sanitize(r.name)}.glb")
        try:
            bpy.ops.export_scene.gltf(filepath=filepath, **EXPORT_SETTINGS)
            print(f"成功导出: {filepath}")
        except Exception as e:
            print(f"导出 '{r.name}' 时发生错误: {e}")

    # 恢复原始选择
    bpy.ops.object.select_all(action='DESELECT')
    for o in original_selection:
        o.select_set(True)
        
    # --- 核心改动：在所有操作完成后，打开输出文件夹 ---
    print(f"批量导出完成。正在打开文件夹: {out_dir}")
    open_folder(out_dir)

    return {'FINISHED'}


# 当脚本被直接运行时，执行主函数
if __name__ == "__main__":
    export_hierarchy_to_glb()
