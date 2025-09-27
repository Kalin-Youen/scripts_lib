# script_id: 0524a568-f01a-4f82-b381-9a6922570869
"""
Split the active mesh object by vertex-groups, restore each part’s origin,
and (crucially) remove every material slot that is **not** listed in the
scene-stored “material_info” dictionary.  
Works in Blender 2.80+.

Prerequisite:  
在合并阶段你应已写入  
    scene["origin_locations"] : {"ObjName":[x,y,z], …}  
    scene["material_info"]    : {"ObjName":{"material_names":[…]}, …}
"""

import bpy
import json
from mathutils import Vector


# -----------------------------------------------------------------------------#
#   Helper : physically delete material slots that are NOT in keep_names       #
# -----------------------------------------------------------------------------#
def purge_unused_slots(obj, keep_names: set) -> int:
    """
    Keep only the materials whose names are in keep_names.
    Return the number of removed slots.
    Uses bpy.ops.object.material_slot_remove() so polygon.material_index
    will be remapped properly.
    """
    if obj.type != 'MESH':
        return 0

    bpy.ops.object.mode_set(mode='OBJECT')

    # indices to remove (descending order)
    remove_idx = [
        i for i, slot in enumerate(obj.material_slots)
        if slot.material and slot.material.name not in keep_names
    ]
    if not remove_idx:
        return 0
    remove_idx.sort(reverse=True)

    # store current context selection / active object
    view_layer = bpy.context.view_layer
    prev_active = view_layer.objects.active
    prev_selected = {o for o in view_layer.objects if o.select_get()}

    # make obj selected & active
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    view_layer.objects.active = obj

    for idx in remove_idx:
        obj.active_material_index = idx
        bpy.ops.object.material_slot_remove()

    # restore previous selection / active
    bpy.ops.object.select_all(action='DESELECT')
    for o in prev_selected:
        o.select_set(True)
    view_layer.objects.active = prev_active

    return len(remove_idx)


# -----------------------------------------------------------------------------#
#   Main : split by vertex-groups, restore origin, clean materials             #
# -----------------------------------------------------------------------------#
def split_mesh_by_vertex_groups():
    scene = bpy.context.scene

    # -- read origin_locations -------------------------------------------------
    origin_data = {}
    try:
        origin_data = json.loads(scene.get("origin_locations", "{}"))
    except Exception as e:
        print(f"⚠ origin_locations JSON parse error: {e}")

    # -- read material_info ----------------------------------------------------
    material_data = {}
    try:
        material_data = json.loads(scene.get("material_info", "{}"))
    except Exception as e:
        print(f"⚠ material_info JSON parse error: {e}")

    # -- sanity check active object -------------------------------------------
    src = bpy.context.active_object
    if not src or src.type != 'MESH':
        print("❗ please activate a mesh object before running.")
        return
    if not src.vertex_groups:
        print("❗ active object has no vertex-groups.")
        return

    bpy.ops.object.mode_set(mode='OBJECT')
    vgroups = list(src.vertex_groups)
    print(f"🚀 splitting '{src.name}' into {len(vgroups)} objects …")

    src_loc = src.location.copy()
    src_rot = src.rotation_euler.copy()
    cursor_backup = scene.cursor.location.copy()

    for vg in vgroups:
        g_name  = vg.name
        g_index = vg.index

        verts = [v.index for v in src.data.vertices
                 if any(g.group == g_index for g in v.groups)]
        if not verts:
            print(f"  - skip empty group '{g_name}'")
            continue

        # duplicate object
        bpy.ops.object.select_all(action='DESELECT')
        src.select_set(True)
        bpy.context.view_layer.objects.active = src
        bpy.ops.object.duplicate(linked=False)
        obj = bpy.context.active_object
        obj.name = g_name
        obj.location = src_loc
        obj.rotation_euler = src_rot

        # keep only this vertex-group
        for g in [g for g in obj.vertex_groups if g.name != g_name]:
            obj.vertex_groups.remove(g)
        obj.vertex_groups.active_index = obj.vertex_groups[g_name].index

        # delete unselected verts
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.select_all(action='INVERT')
        bpy.ops.mesh.delete(type='VERT')
        bpy.ops.object.mode_set(mode='OBJECT')

        if not obj.data.vertices:
            bpy.data.objects.remove(obj)
            print(f"  ⚠ '{g_name}' became empty and was removed.")
            continue

        # -------- material cleanup --------------------------------------------
        keep_set = set(material_data.get(g_name, {})
                                  .get("material_names", []))
        removed = purge_unused_slots(obj, keep_set)
        print(f"  🎨 '{g_name}': removed {removed} slot(s)")

        # -------- restore origin ----------------------------------------------
        if g_name in origin_data and len(origin_data[g_name]) == 3:
            scene.cursor.location = Vector(origin_data[g_name])
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        scene.cursor.location = cursor_backup  # restore cursor

        print(f"  ✅ finished piece '{g_name}'")

    # delete source object
    bpy.ops.object.select_all(action='DESELECT')
    src.select_set(True)
    bpy.ops.object.delete()
    print("🎉 split done, source object removed.")


# -----------------------------------------------------------------------------#
#   Execute                                                                    #
# -----------------------------------------------------------------------------#
if __name__ == "__main__":
    split_mesh_by_vertex_groups()
