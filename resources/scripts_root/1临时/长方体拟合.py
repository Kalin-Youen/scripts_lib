# script_id: baf77dc3-614f-4002-aaf9-8c71899f471f
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix
# ❗❗❗ 修复点在这里：导入缺失的属性模块 ❗❗❗
from bpy.props import FloatProperty, BoolProperty

bl_info = {
    "name": "智能长方体拟合 Rh (Smart Box Fitter Rhodium)",
    "author": "你和你的AI小可爱! 💖 (修复版)",
    "version": (6, 0, 1),
    "blender": (4, 0, 0),
    "location": "3D视图 > 编辑模式 > F3搜索 '智能长方体拟合 Rh'",
    "description": "铑金版！根据点云生成一个完美朝向的长方体，并可在'理想中心'与'平均中心'之间自由移动。",
    "category": "Mesh",
}

# ------------------------------------------------------------------------
# 核心功能: 铑金版智能分析与创建长方体 (Rh)
# (这部分代码无需改动)
# ------------------------------------------------------------------------
def create_box_from_selection_rhodium(
        bm, selected_verts, delete_original,
        core_percentile, size_fit_percentile,
        bias_offset_factor
):
    """
    铑金版 (Rhodium) 核心算法，用于生成长方体:
    1.  计算最稳健的【三个主方向轴】(长/宽/高方向)。
    2.  计算【理想中心】(无偏置) 和 【平均中心】(有偏置)。
    3.  ✨ 核心修正 ✨: 根据【偏移修正因子】，在两个中心之间插值，得到【最终位移中心】。
    4.  基于【最终位移中心】和【三个主方向轴】计算尺寸，实现位移而非缩放。
    """
    if not selected_verts or len(selected_verts) < 3:
        return False, "至少需要选择3个顶点才能进行稳健的拟合。"

    coords = np.array([v.co for v in selected_verts])

    # --- 步骤 1: 稳健分析 - 确定【方向】 ---
    if len(coords) > 3:
        median_center = np.median(coords, axis=0)
        distances_from_median = np.linalg.norm(coords - median_center, axis=1)
        distance_threshold = np.percentile(distances_from_median, core_percentile)
        core_coords = coords[distances_from_median <= distance_threshold]
    else:
        core_coords = coords
    
    if len(core_coords) < 3:
        core_coords = coords

    core_center_for_pca = Vector(core_coords.mean(axis=0))
    centered_core_coords = core_coords - np.array(core_center_for_pca)

    try:
        if centered_core_coords.shape[0] < centered_core_coords.shape[1]:
             _, _, vh = np.linalg.svd(centered_core_coords, full_matrices=False)
             axes = vh
        else:
            covariance_matrix = np.cov(centered_core_coords, rowvar=False)
            eigenvalues, eigenvectors = np.linalg.eigh(covariance_matrix)
            sorted_indices = np.argsort(eigenvalues)[::-1]
            axes = eigenvectors[:, sorted_indices].T
    except np.linalg.LinAlgError:
        return False, "无法确定主方向，请检查核心顶点是否过于集中或共线。"
    
    axis_x, axis_y, axis_z = Vector(axes[0]).normalized(), Vector(axes[1]).normalized(), Vector(axes[2]).normalized()

    # --- ✨ 步骤 2: 计算双中心并应用【位置偏移】 ✨ ---
    average_center = Vector(coords.mean(axis=0))
    vec_to_avg_center = average_center - core_center_for_pca
    ideal_center = core_center_for_pca \
                   + vec_to_avg_center.dot(axis_x) * axis_x \
                   + vec_to_avg_center.dot(axis_y) * axis_y \
                   + vec_to_avg_center.dot(axis_z) * axis_z

    bias_vector = average_center - ideal_center
    final_displaced_center = ideal_center + bias_vector * (bias_offset_factor / 100.0)

    # --- 步骤 3: 基于【位移后】的中心和新坐标系计算【尺寸】 ---
    centered_all_coords = coords - np.array(final_displaced_center)
    projections_x, projections_y, projections_z = (
        np.dot(centered_all_coords, np.array(axis_x)),
        np.dot(centered_all_coords, np.array(axis_y)),
        np.dot(centered_all_coords, np.array(axis_z))
    )

    lower_bound_p = (100.0 - size_fit_percentile) / 2.0
    upper_bound_p = 100.0 - lower_bound_p
    
    min_x, max_x = np.percentile(projections_x, lower_bound_p), np.percentile(projections_x, upper_bound_p)
    min_y, max_y = np.percentile(projections_y, lower_bound_p), np.percentile(projections_y, upper_bound_p)
    min_z, max_z = np.percentile(projections_z, lower_bound_p), np.percentile(projections_z, upper_bound_p)
    
    # --- 步骤 4: 删除与构建 ---
    if delete_original:
        bmesh.ops.delete(bm, geom=list(selected_verts), context='VERTS')

    cube_op_result = bmesh.ops.create_cube(bm, size=1.0)
    verts = cube_op_result['verts']

    size_vec = Vector((max_x - min_x, max_y - min_y, max_z - min_z))
    local_center_offset = axis_x * (min_x + max_x) / 2.0 + \
                          axis_y * (min_y + max_y) / 2.0 + \
                          axis_z * (min_z + max_z) / 2.0
    world_center = final_displaced_center + local_center_offset
    rotation_matrix = Matrix((axis_x, axis_y, axis_z)).transposed().to_4x4()
    
    for v in verts:
        v.co.x *= size_vec.x if size_vec.x > 1e-6 else 0
        v.co.y *= size_vec.y if size_vec.y > 1e-6 else 0
        v.co.z *= size_vec.z if size_vec.z > 1e-6 else 0
        v.co = rotation_matrix @ v.co
        v.co += world_center

    return True, "铑金版长方体拟合成功！"

# ------------------------------------------------------------------------
# ✨ 标准操作符，带F9面板 (铑金版长方体) ✨
# (这部分代码无需改动)
# ------------------------------------------------------------------------
class MESH_OT_smart_box_fitter_rh(bpy.types.Operator):
    """铑金版长方体拟合：在'理想中心'与'平均中心'之间自由移动长方体，实现终极控制"""
    bl_idname = "mesh.smart_box_fitter_rh"
    bl_label = "智能长方体拟合 Rh"
    bl_options = {'REGISTER', 'UNDO'}

    core_percentile: FloatProperty(name="核心点云比例", description="用于确定【方向】的核心点云比例", default=50.0, min=30.0, max=100.0, subtype='PERCENTAGE', precision=1)
    size_fit_percentile: FloatProperty(name="尺寸紧密度", description="用于确定长方体【长宽高】的顶点百分比", default=100.0, min=50.0, max=100.0, subtype='PERCENTAGE', precision=1)

    bias_offset_factor: FloatProperty(
        name="偏移修正",
        description="控制长方体位置在'理想中心'和'平均中心'之间的偏移程度。\n0% = 完美几何中心\n100% = 被离群点拉扯的平均中心",
        default=0.0,
        min=0.0, max=100.0,
        subtype='PERCENTAGE',
        precision=1
    )

    delete_original: BoolProperty(name="删除原顶点", default=True)

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and context.active_object is not None

    def execute(self, context):
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        selected_verts = [v for v in bm.verts if v.select]
        bm.verts.ensure_lookup_table()

        success, message = create_box_from_selection_rhodium(
            bm=bm,
            selected_verts=selected_verts,
            delete_original=self.delete_original,
            core_percentile=self.core_percentile,
            size_fit_percentile=self.size_fit_percentile,
            bias_offset_factor=self.bias_offset_factor
        )

        if not success:
            self.report({'WARNING'}, message)
        else:
            self.report({'INFO'}, message)

        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}

# ------------------------------------------------------------------------
# 注册/注销 (标准模板)
# ------------------------------------------------------------------------
classes = (
    MESH_OT_smart_box_fitter_rh,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    print(f"'{bl_info['name']}' 已成功注册。")

def unregister():
    for cls in reversed(classes):
        if hasattr(bpy.types, cls.bl_idname.upper()):
            bpy.utils.unregister_class(cls)
    print(f"'{bl_info['name']}' 已成功注销。")

if __name__ == "__main__":
    try:
        unregister()
    except Exception:
        pass
    register()

