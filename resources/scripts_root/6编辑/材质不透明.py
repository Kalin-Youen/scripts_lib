# script_id: 9867c246-0e45-4b0f-93c5-15175d5d1dcb
# 创建/复用不透明材质并赋予
import bpy
import bmesh

def make_material_opaque(mat):
    if not mat or not mat.use_nodes:
        return
    node_tree = mat.node_tree
    principled_node = next((n for n in node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not principled_node:
        return
    alpha_input = principled_node.inputs.get("Alpha")
    if not alpha_input:
        return
    if alpha_input.is_linked:
        for link in alpha_input.links:
            node_tree.links.remove(link)
    alpha_input.default_value = 1.0

def main_logic(context):
    obj = context.edit_object
    if not obj or obj.type != 'MESH':
        return {'CANCELLED'}
    bm = bmesh.from_edit_mesh(obj.data)
    selected_faces = [f for f in bm.faces if f.select]
    if not selected_faces:
        bmesh.update_edit_mesh(obj.data)
        return {'CANCELLED'}
    opaque_material_map = {}
    for face in selected_faces:
        original_mat_index = face.material_index
        new_mat_index = -1
        if original_mat_index in opaque_material_map:
            new_mat_index = opaque_material_map[original_mat_index]
        else:
            if original_mat_index >= len(obj.material_slots) or not obj.material_slots[original_mat_index].material:
                continue
            original_mat = obj.material_slots[original_mat_index].material
            opaque_mat_name = original_mat.name + ".Opaque"
            new_mat = bpy.data.materials.get(opaque_mat_name)
            if not new_mat:
                new_mat = original_mat.copy()
                new_mat.name = opaque_mat_name
                make_material_opaque(new_mat)
            slot_index = obj.material_slots.find(new_mat.name)
            if slot_index == -1:
                obj.data.materials.append(new_mat)
                new_mat_index = len(obj.data.materials) - 1
            else:
                new_mat_index = slot_index
            opaque_material_map[original_mat_index] = new_mat_index
        if new_mat_index != -1:
            face.material_index = new_mat_index
    bmesh.update_edit_mesh(obj.data)
    return {'FINISHED'}

class MESH_OT_make_opaque_and_assign(bpy.types.Operator):
    bl_idname = "mesh.make_opaque_and_assign"
    bl_label = "创建/复用不透明材质并赋予"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and context.active_object is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return main_logic(context)

_classes = [MESH_OT_make_opaque_and_assign]

def register():
    for cls in _classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    try:
        unregister()
    except (RuntimeError, NameError):
        pass
    register()

    area = next((a for a in bpy.context.screen.areas if a.type == 'VIEW_3D'), None)
    if area:
        with bpy.context.temp_override(area=area):
            bpy.ops.mesh.make_opaque_and_assign()
    else:
        print("未找到'VIEW_3D'区域，无法弹出窗口。")
