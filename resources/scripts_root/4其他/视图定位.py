# 视图定位
# 视图定位
# 8脚本
import bpy

# 查找名为“定位点”的空物体
target_empty = bpy.data.objects.get("定位点")

# 如果没有找到，则创建一个新的空物体并将其命名为“定位点”
if target_empty is None:
    target_empty = bpy.data.objects.new("定位点", None)
    bpy.context.collection.objects.link(target_empty)
    target_empty.empty_display_size = 1.0  # 设置显示大小，可根据需要更改

# 移动“定位点”到 3D 光标的位置
target_empty.location = bpy.context.scene.cursor.location

# 获取当前场景
scene = bpy.context.scene
# 获取当前选择的对象
selected_objects = bpy.context.selected_objects
# 取消其他对象的选择
for obj in scene.objects:
    if obj not in selected_objects:
        obj.select_set(False)

# 将视图聚焦到“定位点”
bpy.context.view_layer.objects.active = target_empty
bpy.ops.view3d.view_selected()
