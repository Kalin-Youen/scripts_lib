# script_id: ccbab5f9-75b3-4a5d-ac16-c80adcb5fabb
# script_id: aff4bbac-615c-48c0-8560-7d397835b6d0
# script_id: ccbab5f9-75b3-4a5d-ac16-c80adcb5fabb
# script_id: aff4bbac-615c-48c0-8560-7d397835b6d0
# script_id: adffc84e-659b-4628-b214-dad91af6a5ea
# script_id: ccbab5f9-75b3-4a5d-ac16-c80adcb5fabb
# script_id: aff4bbac-615c-48c0-8560-7d397835b6d0
# script_id: ccbab5f9-75b3-4a5d-ac16-c80adcb5fabb
# script_id: aff4bbac-615c-48c0-8560-7d397835b6d0
import bpy
import bmesh

def select_uv_edges(mode='non_straight', tolerance=1e-5):
    obj = bpy.context.active_object

    if obj.mode != 'EDIT':
        print("Please switch to Edit Mode.")
        return

    # Ensure we are in edit mode and use the active UV layer
    bpy.context.tool_settings.mesh_select_mode = (False, True, False)
    bpy.ops.mesh.select_all(action='DESELECT')

    bm = bmesh.from_edit_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.active

    if not uv_layer:
        print("No active UV layer found.")
        return

    for edge in bm.edges:
        if not edge.is_valid:
            continue

        try:
            uv1 = edge.verts[0].link_loops[0][uv_layer].uv
            uv2 = edge.verts[1].link_loops[0][uv_layer].uv
        except IndexError:
            # Skip edges where UV data is not available for vertices
            continue

        if mode == 'non_straight':
            # Check if the edge is not horizontal or vertical within the tolerance
            if not (abs(uv1.x - uv2.x) <= tolerance or abs(uv1.y - uv2.y) <= tolerance):
                edge.select = True
        elif mode == 'horizontal':
            # Check if the edge is approximately horizontal within the tolerance
            if abs(uv1.y - uv2.y) <= tolerance and abs(uv1.x - uv2.x) > tolerance:
                edge.select = True
        elif mode == 'vertical':
            # Check if the edge is approximately vertical within the tolerance
            if abs(uv1.x - uv2.x) <= tolerance and abs(uv1.y - uv2.y) > tolerance:
                edge.select = True

    bmesh.update_edit_mesh(obj.data)

    # Ensure we are in the UV Editor to perform UV operations
    override = bpy.context.copy()
    for area in bpy.context.screen.areas:
        if area.type == 'IMAGE_EDITOR':
            override['area'] = area
            override['region'] = area.regions[-1]
            break

    bpy.ops.uv.select_mode(override, type='EDGE')

# Run the function with the desired mode: 'non_straight', 'horizontal', or 'vertical'
select_uv_edges(mode='vertical', tolerance=0.01)
