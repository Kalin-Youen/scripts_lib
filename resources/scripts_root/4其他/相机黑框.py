# 所有相机外框黑
# 所有相机外框黑
# 4相机
import bpy

# 遍历场景中的所有对象
for obj in bpy.data.objects:
    # 检查对象是否为相机
    if obj.type == 'CAMERA':
        # 设置相机的外边框为1
        obj.data.passepartout_alpha = 1