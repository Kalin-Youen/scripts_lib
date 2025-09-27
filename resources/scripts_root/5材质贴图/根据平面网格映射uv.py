# script_id: ad2baa3f-7347-4392-a88f-bb67034d7358
import bpy
import bmesh
from mathutils import Vector, Matrix

def store_plane_data(context, data):
    context.scene['planar_projection_data'] = data

def load_plane_data(context):
    return context.scene.get('planar_projection_data')

class UV_OT_world_space_projector_worker(bpy.types.Operator):
    bl_idname = "uv.world_space_projector_worker"
    bl_label = "3D Planar UV Projector (Worker)"
    bl_options = {'REGISTER', 'UNDO'}

    action: bpy.props.EnumProperty(
        items=[
            ('SET_PLANE', "Set Plane", ""),
            ('PROJECT', "Project", "")
        ]
    )
    
    def execute(self, context):
        if self.action == 'SET_PLANE':
            return self.set_plane(context)
        elif self.action == 'PROJECT':
            return self.project_objects(context)
        return {'CANCELLED'}

    def set_plane(self, context):
        obj = context.active_object
        if not obj or obj.mode != 'EDIT':
            self.report({'ERROR'}, "请先选择一个物体，并进入编辑模式。")
            return {'CANCELLED'}
        
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        
        selected_faces = [f for f in bm.faces if f.select]
        if len(selected_faces) != 1:
            self.report({'ERROR'}, "请确保只选择了一个面。")
            bmesh.update_edit_mesh(mesh); return {'CANCELLED'}
        ref_face = selected_faces[0]

        uv_layer = bm.loops.layers.uv.active
        if not uv_layer:
            self.report({'ERROR'}, "活动物体没有UV层。")
            bmesh.update_edit_mesh(mesh); return {'CANCELLED'}
            
        if len(ref_face.loops) < 3:
            self.report({'ERROR'}, "参考面必须至少有3个顶点。")
            bmesh.update_edit_mesh(mesh); return {'CANCELLED'}

        # --- 算法：从UV反推3D坐标轴 ---
        loops = ref_face.loops
        p0 = obj.matrix_world @ loops[0].vert.co
        p1 = obj.matrix_world @ loops[1].vert.co
        p2 = obj.matrix_world @ loops[2].vert.co
        
        uv0 = loops[0][uv_layer].uv
        uv1 = loops[1][uv_layer].uv
        uv2 = loops[2][uv_layer].uv
        
        edge1_3d = p1 - p0
        edge2_3d = p2 - p0
        
        delta_uv1 = uv1 - uv0
        delta_uv2 = uv2 - uv0
        
        determinant = delta_uv1.x * delta_uv2.y - delta_uv1.y * delta_uv2.x
        if abs(determinant) < 1e-6:
            self.report({'ERROR'}, "参考面的UV是退化的（所有点在一条直线上），无法计算方向。")
            bmesh.update_edit_mesh(mesh); return {'CANCELLED'}
            
        inv_determinant = 1.0 / determinant
        # u_dir 和 v_dir 是UV的U轴和V轴在3D空间中的真实方向和长度
        u_dir = (edge1_3d * delta_uv2.y - edge2_3d * delta_uv1.y) * inv_determinant
        v_dir = (edge2_3d * delta_uv1.x - edge1_3d * delta_uv2.x) * inv_determinant

        # --- 【【【 终极修正：强制Y轴与V轴方向对齐 】】】 ---
        # 1. 建立基础坐标系
        face_normal = ref_face.normal.copy()
        face_normal.rotate(obj.matrix_world.to_quaternion())
        
        z_axis = -face_normal.normalized()
        x_axis = u_dir.normalized() # U方向作为X轴
        
        # 2. 计算一个临时的、正交的Y轴
        y_axis_temp = z_axis.cross(x_axis)
        
        # 3. 使用点积检查临时Y轴是否与真实的V方向同向
        if v_dir.dot(y_axis_temp) < 0:
            # 如果点积为负，说明它们反向，需要翻转我们的Y轴
            y_axis = -y_axis_temp.normalized()
        else:
            # 否则，方向正确
            y_axis = y_axis_temp.normalized()

        # 4. 创建一个100%与UV对齐的视图矩阵
        rot_mat = Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()
        view_matrix = rot_mat.inverted()

        # --- 后续逻辑不变 ---
        world_coords = [obj.matrix_world @ v.co for v in ref_face.verts]
        uv_coords = [loop[uv_layer].uv.copy() for loop in ref_face.loops]
        projected_2d_coords = [(view_matrix @ wc).xy for wc in world_coords]

        plane_data = {
            'object_name': obj.name,
            'view_matrix': [list(row) for row in view_matrix],
            'uv_min': [min(uv.x for uv in uv_coords), min(uv.y for uv in uv_coords)],
            'uv_max': [max(uv.x for uv in uv_coords), max(uv.y for uv in uv_coords)],
            'ref_2d_min': [min(p.x for p in projected_2d_coords), min(p.y for p in projected_2d_coords)],
            'ref_2d_max': [max(p.x for p in projected_2d_coords), max(p.y for p in projected_2d_coords)],
        }
        store_plane_data(context, plane_data)
        bmesh.update_edit_mesh(mesh)
        self.report({'INFO'}, f"成功设置参考平面 (基于UV精确对齐): '{obj.name}'")
        return {'FINISHED'}



    def project_objects(self, context):
        plane_data = load_plane_data(context)
        if not plane_data:
            self.report({'ERROR'}, "请先使用 '设置参考平面' 功能。")
            return {'CANCELLED'}

        obj = context.edit_object
        if not obj:
            self.report({'ERROR'}, "必须在编辑模式下执行此操作。")
            return {'CANCELLED'}

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        uv_layer = bm.loops.layers.uv.active
        if not uv_layer:
            self.report({'ERROR'}, "当前物体没有活动的UV图。")
            bmesh.update_edit_mesh(mesh); return {'CANCELLED'}

        selected_loops = [loop for face in bm.faces if face.select for loop in face.loops]
        if not selected_loops:
            self.report({'WARNING'}, "没有选择任何面用于投影。")
            bmesh.update_edit_mesh(mesh); return {'CANCELLED'}

        view_matrix = Matrix(plane_data['view_matrix'])
        uv_min = Vector(plane_data['uv_min'])
        uv_max = Vector(plane_data['uv_max'])
        ref_2d_min = Vector(plane_data['ref_2d_min'])
        ref_2d_max = Vector(plane_data['ref_2d_max'])
        
        uv_range = uv_max - uv_min
        ref_2d_range = ref_2d_max - ref_2d_min

        if abs(ref_2d_range.x) < 1e-6 or abs(ref_2d_range.y) < 1e-6:
            self.report({'ERROR'}, "参考平面在投影中没有面积，无法映射。")
            bmesh.update_edit_mesh(mesh); return {'CANCELLED'}

        for loop in selected_loops:
            vert = loop.vert
            world_co = obj.matrix_world @ vert.co
            proj_co_2d = (view_matrix @ world_co).xy
            
            norm_x = (proj_co_2d.x - ref_2d_min.x) / ref_2d_range.x
            norm_y = (proj_co_2d.y - ref_2d_min.y) / ref_2d_range.y
            
            # 【【【 修正 】】】
            # 因为我们的坐标系现在完美对齐UV，不再需要手动翻转Y轴了。
            final_uv_x = uv_min.x + norm_x * uv_range.x
            final_uv_y = uv_min.y + norm_y * uv_range.y
            
            loop[uv_layer].uv = (final_uv_x, final_uv_y)

        bmesh.update_edit_mesh(mesh)
        self.report({'INFO'}, "成功将选中面的UV进行精确映射。")
        return {'FINISHED'}


class TOOL_OT_planar_projector_popup(bpy.types.Operator):
    bl_idname = "tool.planar_projector_popup"
    bl_label = "3D转UV投影工具"
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        plane_data = load_plane_data(context)
        
        box = layout.box()
        if plane_data:
            box.label(text=f"来源: '{plane_data['object_name']}'", icon='CHECKMARK')
        else:
            box.label(text="状态: 未设置参考平面", icon='ERROR')
        
        layout.separator()
        col = layout.column(align=True)
        col.label(text="步骤 1: 定义画布")
        set_op = col.operator(UV_OT_world_space_projector_worker.bl_idname, text="设置参考平面", icon='RESTRICT_SELECT_ON')
        set_op.action = 'SET_PLANE'

        layout.separator()
        col = layout.column(align=True)
        col.label(text="步骤 2: 投射选中面")
        col.active = plane_data is not None and context.mode == 'EDIT_MESH'
        project_op = col.operator(UV_OT_world_space_projector_worker.bl_idname, text="映射选中项", icon='MOD_UVPROJECT')
        project_op.action = 'PROJECT'
        
    def execute(self, context):
        return {'FINISHED'}

if __name__ == '__main__':
    classes = (
        UV_OT_world_space_projector_worker,
        TOOL_OT_planar_projector_popup,
    )
    
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
            
    for cls in classes:
        bpy.utils.register_class(cls)

    area = next((a for a in bpy.context.screen.areas if a.type == 'VIEW_3D'), None)
    if area:
        with bpy.context.temp_override(area=area):
            bpy.ops.tool.planar_projector_popup('INVOKE_DEFAULT')

