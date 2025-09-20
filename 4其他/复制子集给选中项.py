# 复制子集给选中项
# 子集作为激活项
# 8脚本
import bpy

# 获取当前场景
scene = bpy.context.scene

# 获取选中的物体
selected = bpy.context.selected_objects

if len(selected) > 1:
    # 获取活动对象
    active_object = bpy.context.active_object

    # 移除活动对象，保留其作为复制模板
    selected.remove(active_object)

    for obj in selected:
        # 复制活动对象
        copy = active_object.copy()
        copy.data = active_object.data.copy()
        copy.animation_data_clear()

        # 添加复制对象到场景
        bpy.context.collection.objects.link(copy)

        # 设置复制对象的父级
        copy.parent = obj

        # 设置复制对象的世界坐标系下的位置
        copy.matrix_world.translation = obj.matrix_world.translation

else:
    print("请至少选中两个物体，且确保有一个是活动对象")
