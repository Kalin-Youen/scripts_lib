# script_id: 32786427-9e0d-4420-b3af-e14d3a67a8ae
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from bpy.props import IntProperty, BoolProperty, FloatProperty

bl_info = {
    "name": "智能柱体拟合 Rh (Smart Prism Fitter Rhodium)",
    "author": "你和你的AI小可爱! 💖 (Rhodium v6.0.0 铑金版)",
    "version": (6, 0, 0),
    "blender": (4, 0, 0),
    "location": "3D视图 > 编辑模式 > F3搜索 '智能柱体拟合'",
    "description": "铑金版！最终形态！引入位置偏移修正，让你在'理想中心'与'平均中心'之间自由移动柱体。",
    "category": "Mesh",
}

# ------------------------------------------------------------------------
# 核心功能: 铑金版智能分析与创建 (Rh)
# ------------------------------------------------------------------------
def create_prism_from_selection_rhodium(
        bm, selected_verts, segments, delete_original,
        core_percentile, height_fit_percentile, radius_fit_percentile,
        bias_offset_factor  # 新参数：位置偏移因子
):
    """
    钯金版 (Rhodium) 核心算法:
    1.  计算最稳健的【方向轴】。
    2.  计算【理想中心】(无偏置) 和 【平均中心】(有偏置)。
    3.  ✨ 核心修正 ✨: 根据【偏移修正因子】，在两个中心之间插值，得到【最终位移中心】。
    4.  所有尺寸计算均基于这个【最终位移中心】进行，实现位移而非缩放。
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

    core_center_for_pca = Vector(core_coords.mean(axis=0))
    centered_core_coords = core_coords - np.array(core_center_for_pca)

    try:
        if centered_core_coords.shape[0] < centered_core_coords.shape[1]:
            _, _, vh = np.linalg.svd(centered_core_coords, full_matrices=False)
            main_axis = Vector(vh[0]).normalized()
        else:
            covariance_matrix = np.cov(centered_core_coords, rowvar=False)
            eigenvalues, eigenvectors = np.linalg.eigh(covariance_matrix)
            main_axis = Vector(eigenvectors[:, np.argmax(eigenvalues)]).normalized()
    except np.linalg.LinAlgError:
        return False, "无法确定主方向，请检查核心顶点是否过于集中或共线。"

    # --- ✨ 步骤 2: 计算双中心并应用【位置偏移】 ✨ ---
    # 【平均中心】: 受离群点影响
    average_center = Vector(coords.mean(axis=0))
    # 【理想中心】: 投影得到的无偏置中心
    vec_to_avg_center = average_center - core_center_for_pca
    ideal_center = core_center_for_pca + vec_to_avg_center.dot(main_axis) * main_axis

    # 计算偏移向量
    bias_vector = average_center - ideal_center
    # 根据因子在“理想”和“平均”之间插值，得到最终的位移中心
    # 这是真正的位移控制点
    final_displaced_center = ideal_center + bias_vector * (bias_offset_factor / 100.0)

    # --- 步骤 3: 基于【位移后】的中心进行独立尺寸计算 ---
    # 所有后续计算都使用 final_displaced_center，确保整个坐标系被移动
    centered_all_coords = coords - np.array(final_displaced_center)
    projections_on_axis = np.dot(centered_all_coords, np.array(main_axis))

    # 高度计算
    lower_bound_p_h = (100.0 - height_fit_percentile) / 2.0
    upper_bound_p_h = 100.0 - lower_bound_p_h
    min_proj = float(np.percentile(projections_on_axis, lower_bound_p_h))
    max_proj = float(np.percentile(projections_on_axis, upper_bound_p_h))
    height = max_proj - min_proj
    if height < 1e-6:
        height = 0.2

    # 使用位移后的中心来确定顶部和底部位置
    bottom_center = final_displaced_center + main_axis * min_proj
    top_center = final_displaced_center + main_axis * max_proj

    # 半径计算
    axis_projection_points = np.outer(projections_on_axis, np.array(main_axis))
    radial_vectors = centered_all_coords - axis_projection_points
    radial_distances = np.linalg.norm(radial_vectors, axis=1)
    radius = float(np.percentile(radial_distances, radius_fit_percentile))
    if radius < 1e-6:
        radius = 0.2

    # --- 步骤 4: 删除与构建 ---
    if delete_original:
        bmesh.ops.delete(bm, geom=list(selected_verts), context='VERTS')

    ref_vec = Vector((1, 0, 0)) if abs(main_axis.dot(Vector((1, 0, 0)))) < 0.9 else Vector((0, 1, 0))
    u_vec = main_axis.cross(ref_vec).normalized()
    v_vec = main_axis.cross(u_vec).normalized()

    bottom_verts, top_verts = [], []
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        offset = radius * (u_vec * np.cos(angle) + v_vec * np.sin(angle))
        bottom_verts.append(bm.verts.new(bottom_center + offset))
        top_verts.append(bm.verts.new(top_center + offset))

    if segments > 2:
        bm.faces.new(bottom_verts)
        bm.faces.new(list(reversed(top_verts)))

    for i in range(segments):
        next_i = (i + 1) % segments
        bm.faces.new((bottom_verts[i], bottom_verts[next_i], top_verts[next_i], top_verts[i]))

    return True, f"铑金版拟合成功！生成 {segments} 边柱体。"

# ------------------------------------------------------------------------
# ✨ 标准操作符，带F9面板 (铑金版) ✨
# ------------------------------------------------------------------------
class MESH_OT_smart_prism_fitter_rh(bpy.types.Operator):
    """铑金版柱体拟合：在'理想中心'与'平均中心'之间自由移动柱体，实现终极控制"""
    bl_idname = "mesh.smart_prism_fitter_rh"
    bl_label = "智能柱体拟合 Rh"
    bl_options = {'REGISTER', 'UNDO'}

    segments: IntProperty(name="边数", default=8, min=3, max=256)
    core_percentile: FloatProperty(name="核心点云比例", description="用于确定【方向】的核心点云比例", default=95.0, min=50.0, max=100.0, subtype='PERCENTAGE', precision=1)
    height_fit_percentile: FloatProperty(name="长度紧密度", description="用于确定柱体【长度】的顶点百分比", default=98.0, min=50.0, max=100.0, subtype='PERCENTAGE', precision=1)
    radius_fit_percentile: FloatProperty(name="半径紧密度", description="用于确定柱体【半径】的顶点百分比", default=98.0, min=50.0, max=100.0, subtype='PERCENTAGE', precision=1)

    # ✨ 终极控制属性 ✨
    bias_offset_factor: FloatProperty(
        name="偏移修正",
        description="控制柱体位置在'理想中心'和'平均中心'之间的偏移程度。\n0% = 完美几何中心\n100% = 被离群点拉扯的平均中心",
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

        success, message = create_prism_from_selection_rhodium(
            bm=bm,
            selected_verts=selected_verts,
            segments=self.segments,
            delete_original=self.delete_original,
            core_percentile=self.core_percentile,
            height_fit_percentile=self.height_fit_percentile,
            radius_fit_percentile=self.radius_fit_percentile,
            bias_offset_factor=self.bias_offset_factor  # 传递新参数
        )

        if not success:
            self.report({'WARNING'}, message)
            bmesh.update_edit_mesh(obj.data)
            return {'CANCELLED'}

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, message)
        return {'FINISHED'}

# ------------------------------------------------------------------------
# 注册/注销 (标准模板)
# ------------------------------------------------------------------------
classes = (
    MESH_OT_smart_prism_fitter_rh,
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



