import bpy
import json
from mathutils import Vector    # 仅为将来拆分时可能用到，这里先保留

# ------------------------------------------------------------------------------
# 1.  清空顶点组
# ------------------------------------------------------------------------------
def clear_all_vertex_groups():
    selected_objects = bpy.context.selected_objects
    if not selected_objects:
        msg = "No objects selected!"
        print(msg)
        bpy.context.window_manager.popup_menu(
            lambda s, c: s.layout.label(text=msg),
            title="Abort",
            icon='ERROR')
        return

    total_groups = 0
    cleared_objs = 0
    for obj in selected_objects:
        if obj.vertex_groups:
            n = len(obj.vertex_groups)
            obj.vertex_groups.clear()
            total_groups += n
            cleared_objs += 1
            print(f"  ✓ Cleared {n} vertex groups on '{obj.name}'")
        else:
            print(f"  - Object '{obj.name}' has no vertex groups, skipped")

    final_msg = (f"Done! Cleared {total_groups} vertex groups "
                 f"on {cleared_objs} objects." if cleared_objs
                 else "Done, but no vertex groups found on the selection.")
    print(final_msg)
    bpy.context.window_manager.popup_menu(
        lambda s, c: s.layout.label(text=final_msg),
        title="Report",
        icon='CHECKMARK' if cleared_objs else 'INFO')


# ------------------------------------------------------------------------------
# 2.  为选中的每个网格对象创建顶点组、记录原点与材质，并合并
# ------------------------------------------------------------------------------
def 添加顶点组并合并():
    """
    • 为每个选中的网格对象创建一个与对象同名的顶点组并把全部顶点加入该组  
    • 记录每个对象的世界原点位置(origin_locations)  
    • 记录每个对象所使用的所有材质(material_info)  
    • 最后把选中的对象合并为一个
    """
    scene = bpy.context.scene
    sel_objs = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not sel_objs:
        print("❗ Please select at least one mesh object.")
        return

    # ---------- 2.1 记录原点 ----------
    origin_dict = {}
    for obj in sel_objs:
        world_loc = obj.matrix_world.to_translation()
        origin_dict[obj.name] = [world_loc.x, world_loc.y, world_loc.z]
    scene["origin_locations"] = json.dumps(origin_dict)
    print(f"✅ Stored origins for {len(origin_dict)} objects → scene['origin_locations']")

    # ---------- 2.2 记录材质信息 --------------  ## ← new
    material_dict = {}
    for obj in sel_objs:
        mat_names = [slot.material.name for slot in obj.material_slots
                     if slot.material is not None]
        material_dict[obj.name] = {
            "material_names": mat_names,       # 仅名称列表，后续拆分时用来判断保留
            "active_index": obj.active_material_index
        }
    scene["material_info"] = json.dumps(material_dict)
    print(f"✅ Stored material data for {len(material_dict)} objects → scene['material_info']")

    # ---------- 2.3 为每个对象新建顶点组 ----------
    for obj in sel_objs:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='OBJECT')

        if obj.vertex_groups.get(obj.name):
            obj.vertex_groups.remove(obj.vertex_groups[obj.name])

        vg = obj.vertex_groups.new(name=obj.name)
        vg.add([v.index for v in obj.data.vertices], 1.0, 'REPLACE')

    # ---------- 2.4 合并 ----------
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in sel_objs:
        o.select_set(True)
    bpy.ops.object.join()
    print("✅ Merge finished and vertex groups added.")


# ------------------------------------------------------------------------------
# 3.  主入口
# ------------------------------------------------------------------------------
def main():
    clear_all_vertex_groups()
    添加顶点组并合并()
    merged_obj = bpy.context.active_object          # join 后的活动对象
    merged_obj.name = "合并的顶点组物体"             # ← 你想要的名字

if __name__ == "__main__":
    main()
