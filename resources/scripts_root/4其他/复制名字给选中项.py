# 复制名字给选中项
# 激活项为名字来源
# 8脚本
import bpy

# 获取活动对象的名称
active_object_name = bpy.context.active_object.name

# 获取选定的对象
selected_objects = bpy.context.selected_objects

# 检查是否有选定的对象
if selected_objects:
    # 循环遍历选定的对象，并将它们的名称设置为活动对象的名称
    for obj in selected_objects:
        obj.name = active_object_name
