# 清除选择物体所有材质
# 清理选中物体的所有材质
# 1材质
import bpy

selected_objects = bpy.context.selected_objects

if selected_objects:
    for obj in selected_objects:
        # 清除物体的所有材质
        obj.data.materials.clear()
