import bpy
import os

# 获取当前Blender文件的路径
# blend_file_path = bpy.data.filepath
# directory = os.path.dirname(blend_file_path)
directory ="C:\\temp\\exported"
# 目标文件夹名称
# target_folder = "toUe"

# 确保目标文件夹存在
# target_path = os.path.join(directory, target_folder)
target_path = directory
if not os.path.exists(target_path):
    os.makedirs(target_path)

# 获取当前选择的物体
selected_objects = bpy.context.selected_objects

# 暂时取消所有物体的选择
bpy.ops.object.select_all(action='DESELECT')

# 逐一导出物体
for obj in selected_objects:
    # 只选择当前迭代的物体
    obj.select_set(True)
    
    # 定义导出文件的名称和路径
    export_file_name = f"{obj.name}.obj"
    custom_path = os.path.join(target_path, export_file_name)
    
    # 导出为.obj格式
    bpy.ops.wm.obj_export(
        filepath=custom_path,
        export_selected_objects = True
    )
    
    # 控制台打印导出信息
    print(f"Exported {obj.name} to {custom_path}")
    
    # 取消当前物体的选择，为选择下一个物体做准备
    obj.select_set(False)

# 重新选择原本选中的物体
for obj in selected_objects:
    obj.select_set(True)

print("Exporting selected objects to obj format complete.")


