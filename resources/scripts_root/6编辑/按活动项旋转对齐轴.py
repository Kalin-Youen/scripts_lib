import bpy
import bmesh
from mathutils import Vector, Matrix

class MESH_OT_align_selection_to_axis(bpy.types.Operator):
    bl_idname = "mesh.align_selection_to_axis"
    bl_label = "Align Selection to Axis"
    bl_options = {'REGISTER', 'UNDO'}

    target_axis: bpy.props.EnumProperty(
        name="Target Axis",
        description="选择要对齐的目标世界轴向",
        items=[
            ('POSITIVE_X', "+X", "对齐到世界坐标 +X 轴"),
            ('NEGATIVE_X', "-X", "对齐到世界坐标 -X 轴"),
            ('POSITIVE_Y', "+Y", "对齐到世界坐标 +Y 轴"),
            ('NEGATIVE_Y', "-Y", "对齐到世界坐标 -Y 轴"),
            ('POSITIVE_Z', "+Z", "对齐到世界坐标 +Z 轴"),
            ('NEGATIVE_Z', "-Z", "对齐到世界坐标 -Z 轴"),
        ],
        default='POSITIVE_Z',
    )
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.edit_object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        active_element = bm.select_history.active
        if active_element is None:
            self.report({'WARNING'}, "没有活动的元素")
            return {'CANCELLED'}

        pivot_co = Vector()
        source_normal = Vector()

        if isinstance(active_element, bmesh.types.BMVert):
            pivot_co = active_element.co.copy()
            source_normal = active_element.normal.copy()
        elif isinstance(active_element, bmesh.types.BMEdge):
            pivot_co = (active_element.verts[0].co + active_element.verts[1].co) / 2.0
            if active_element.link_faces:
                source_normal = sum((f.normal for f in active_element.link_faces), Vector()).normalized()
            else:
                 self.report({'WARNING'}, "边没有连接面，无法确定法线")
                 return {'CANCELLED'}
        elif isinstance(active_element, bmesh.types.BMFace):
            pivot_co = active_element.calc_center_median()
            source_normal = active_element.normal.copy()
        else:
            self.report({'ERROR'}, "未知的活动元素类型")
            return {'CANCELLED'}

        axis_map = {
            'POSITIVE_X': Vector((1, 0, 0)),
            'NEGATIVE_X': Vector((-1, 0, 0)),
            'POSITIVE_Y': Vector((0, 1, 0)),
            'NEGATIVE_Y': Vector((0, -1, 0)),
            'POSITIVE_Z': Vector((0, 0, 1)),
            'NEGATIVE_Z': Vector((0, 0, -1)),
        }
        target_axis_world = axis_map[self.target_axis]

        inv_matrix_world = obj.matrix_world.inverted()
        target_axis_local = inv_matrix_world.to_3x3() @ target_axis_world
        target_axis_local.normalize()

        quat_rotation = source_normal.rotation_difference(target_axis_local)
        rot_matrix = quat_rotation.to_matrix()

        selected_verts = [v for v in bm.verts if v.select]
        
        bmesh.ops.rotate(
            bm,
            verts=selected_verts,
            cent=pivot_co,
            matrix=rot_matrix
        )

        bmesh.update_edit_mesh(mesh)
        return {'FINISHED'}


if __name__ == '__main__':
    classes = (MESH_OT_align_selection_to_axis,)

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
            bpy.ops.mesh.align_selection_to_axis('INVOKE_DEFAULT')

