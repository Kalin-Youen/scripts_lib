# 给所有材质加工程名前缀
# 给所有材质加工程名前缀
# 1材质
import bpy
import os

def add_project_prefix_to_materials():
    # 获取项目名（.blend 文件名，不含扩展名）
    project_name = bpy.path.display_name_from_filepath(bpy.data.filepath)

    if not project_name:
        print("无法获取项目名，请确保已保存 .blend 文件。")
        return

    # 遍历所有材质
    for material in bpy.data.materials:
        if material.users > 0:  # 确保材质被使用
            # 检查是否已经有项目名作为前缀
            if not material.name.startswith(f"{project_name}_"):
                material.name = f"{project_name}_{material.name}"  # 添加前缀
                print(f"更新材质名为: {material.name}")
            else:
                print(f"材质名已更新过: {material.name}")

# 执行脚本
add_project_prefix_to_materials()
