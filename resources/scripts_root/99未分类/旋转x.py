# script_id: a085b370-a360-4d9b-b20d-c2ef491e2185
import bpy
from math import radians

# 确保在对象模式
if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

# 对所有选中物体，X 轴增加 10 度
angle = radians(10)
for obj in bpy.context.selected_objects:
    # 如果物体没有 Euler 旋转属性则跳过
    if hasattr(obj, "rotation_euler"):
        obj.rotation_euler.x += angle
