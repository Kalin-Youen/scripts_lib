# -*- coding: utf-8 -*-
import bpy
import os

# --- 1. 设置导出路径 ---
# 你可以直接在这里指定一个绝对路径
export_directory = "C:\\temp\\exported"

# 或者，你也可以使用当前 .blend 文件所在的目录
# 注意：如果 .blend 文件还未保存，bpy.data.filepath 会为空
# if bpy.data.filepath:
#     export_directory = os.path.dirname(bpy.data.filepath)
# else:
#     # 提供一个默认的备用路径
#     export_directory = "C:\\temp\\default_export"
#     print(f"警告: .blend 文件未保存，将使用默认路径: {export_directory}")

# --- 2. 设置导出的文件名 ---
# 你可以自定义导出的文件名
export_file_name = "Combined_Export.obj"

# --- 3. 确保导出目录存在 ---
if not os.path.exists(export_directory):
    os.makedirs(export_directory)
    print(f"已创建导出目录: {export_directory}")

# 最终的完整导出路径
export_filepath = os.path.join(export_directory, export_file_name)


# --- 4. 获取当前选中的物体 ---
selected_objects = bpy.context.selected_objects

if not selected_objects:
    print("错误: 没有选中任何物体。请先在3D视图中选择要导出的物体。")
    # 如果你想在界面上弹出提示，可以使用下面这行
    # bpy.context.window_manager.popup_menu(lambda self, context: self.layout.label(text="没有选中物体!"), title="导出失败", icon='ERROR')
else:
    print(f"准备将 {len(selected_objects)} 个选中的物体导出到单个文件中...")
    
    # --- 5. 执行导出操作 ---
    # 确保所有目标物体都处于选中状态 (实际上我们不需要改变选择状态)
    # bpy.ops.wm.obj_export 函数会处理好 'export_selected_objects'
    
    bpy.ops.wm.obj_export(
        filepath=export_filepath,
        # 这个参数是关键，它告诉Blender只导出当前选中的物体
        export_selected_objects=True  
    )
    
    print("\n" + "="*50)
    print("✅ 导出完成！")
    print(f"   文件已保存至: {export_filepath}")
    print("="*50)

