import bpy

def set_alpha_blend_no_overlap(material):
    if material is None:
        return
    material.blend_method = 'BLEND'                 # Alpha Blend
    if hasattr(material, "show_transparent_back"):  # Blender ≥3.6
        material.show_transparent_back = True      # Disable overlap sorting
    else:                                           # Older versions
        material.use_backface_culling = False        # Approx. same effect

# iterate over selected objects
for obj in bpy.context.selected_objects:
    if obj.type != 'MESH':
        continue
    for slot in obj.material_slots:
        set_alpha_blend_no_overlap(slot.material)
