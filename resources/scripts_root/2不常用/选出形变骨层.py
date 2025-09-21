import bpy

# --- 可配置项 ---
# 如果一个顶点的权重小于这个值，我们就忽略它。
# 您可以根据需要调整这个值，例如 0.01 或更小。
WEIGHT_THRESHOLD = 0.001

def isolate_deform_bones_to_collection_with_threshold():
    """
    此脚本将选定网格物体中，权重值大于指定阈值的顶点组所对应的骨骼，
    移动到一个名为“形变骨骼层”的骨骼集合中。
    Blender 4.x 适用。
    """
    # --- 1. 获取并验证选择 ---
    selected_objects = bpy.context.selected_objects
    
    armature_obj = None
    mesh_objs = []

    if len(selected_objects) < 2:
        print("错误：请至少选择一个骨架和一个网格物体。")
        bpy.context.window_manager.popup_menu(lambda self, context: self.layout.label(text="错误：请至少选择一个骨架和一个网格物体。"), title="提示", icon='ERROR')
        return {'CANCELLED'}

    for obj in selected_objects:
        if obj.type == 'ARMATURE':
            if armature_obj is None:
                armature_obj = obj
            else:
                print("错误：请不要选择多个骨架。")
                bpy.context.window_manager.popup_menu(lambda self, context: self.layout.label(text="错误：请不要选择多个骨架。"), title="提示", icon='ERROR')
                return {'CANCELLED'}
        elif obj.type == 'MESH':
            mesh_objs.append(obj)

    if not armature_obj:
        print("错误：在您的选择中没有找到骨架物体。")
        bpy.context.window_manager.popup_menu(lambda self, context: self.layout.label(text="错误：在您的选择中没有找到骨架物体。"), title="提示", icon='ERROR')
        return {'CANCELLED'}
    
    if not mesh_objs:
        print("错误：在您的选择中没有找到网格物体。")
        bpy.context.window_manager.popup_menu(lambda self, context: self.layout.label(text="错误：在您的选择中没有找到网格物体。"), title="提示", icon='ERROR')
        return {'CANCELLED'}

    print(f"找到骨架: {armature_obj.name}")
    print(f"找到网格: {[m.name for m in mesh_objs]}")

    # --- 2. 收集所有权重高于阈值的顶点组名称 ---
    active_vertex_group_names = set()

    for mesh_obj in mesh_objs:
        if not mesh_obj.vertex_groups:
            continue
            
        group_index_to_name = {vg.index: vg.name for vg in mesh_obj.vertex_groups}

        for vertex in mesh_obj.data.vertices:
            for group in vertex.groups:
                # !!! 核心改动在这里 !!!
                # 只有当权重高于我们设定的阈值时，才认为它有效
                if group.weight > WEIGHT_THRESHOLD:
                    group_name = group_index_to_name.get(group.group)
                    if group_name:
                        active_vertex_group_names.add(group_name)

    if not active_vertex_group_names:
        print("信息：在选中的网格上没有找到任何权重足够大的顶点组。")
        bpy.context.window_manager.popup_menu(lambda self, context: self.layout.label(text="没有找到有效的顶点组。"), title="提示", icon='INFO')
        return {'FINISHED'}
        
    print(f"找到以下有效的形变顶点组: {list(active_vertex_group_names)}")

    # --- 3. 操作骨架 ---
    original_mode = armature_obj.mode
    bpy.context.view_layer.objects.active = armature_obj
    
    if armature_obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

    armature_data = armature_obj.data
    edit_bones = armature_data.edit_bones
    
    deform_collection_name = "形变骨骼层"

    deform_bone_collection = armature_data.collections.get(deform_collection_name)
    if deform_bone_collection is None:
        deform_bone_collection = armature_data.collections.new(deform_collection_name)
        print(f"创建了新的骨骼集合: '{deform_collection_name}'")

    # --- 4. 移动骨骼到新的集合 ---
    moved_bones_count = 0
    for bone in edit_bones:
        if bone.name in active_vertex_group_names:
            for coll in armature_data.collections:
                if bone.name in coll.bones:
                   coll.unassign(bone)
            
            deform_bone_collection.assign(bone)
            moved_bones_count += 1
            print(f"已将骨骼 '{bone.name}' 移动到 '{deform_collection_name}'")

    # --- 5. 清理和收尾 ---
    bpy.ops.object.mode_set(mode=original_mode)
    
    success_message = f"操作完成！移动了 {moved_bones_count} 根骨骼。"
    print(f"\n{success_message}")
    bpy.context.window_manager.popup_menu(lambda self, context: self.layout.label(text=success_message), title="成功", icon='INFO')
    
    return {'FINISHED'}


# --- 运行脚本 ---
if __name__ == "__main__":
    isolate_deform_bones_to_collection_with_threshold()
