import bpy

def move_active_bone_to_end():
    # 确保我们在编辑模式下
    if bpy.context.object.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

    obj = bpy.context.object
    armature = obj.data
    active_bone = armature.edit_bones.active

    if active_bone and active_bone.parent:
        # 保存父骨骼的引用
        parent_bone = active_bone.parent
        # 临时解除父子关系
        active_bone.parent = None
        bpy.context.view_layer.update()
        # 重新设置父骨骼
        active_bone.parent = parent_bone
    else:
        print("没有活动的骨骼或骨骼没有父级。")

move_active_bone_to_end()
