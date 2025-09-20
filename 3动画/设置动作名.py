import bpy

def set_action_name_to_object_name():
    # 遍历当前选中的物体
    for obj in bpy.context.selected_objects:
        # 检查物体是否有动作
        if obj.type == 'MESH' and obj.animation_data and obj.animation_data.action:
            # 获取物体的动作
            action = obj.animation_data.action
            # 设置动作名称为物体的名称
            action.name = obj.name
            print(f"Set action name for '{obj.name}' to '{action.name}'")

# 执行函数
set_action_name_to_object_name()
