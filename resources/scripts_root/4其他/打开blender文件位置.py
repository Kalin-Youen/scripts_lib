import bpy
import os
import sys
import subprocess

def open_current_blend_folder():
    """
    打开当前.blend文件所在的文件夹。
    如果文件尚未保存，则显示错误提示。
    """
    # 检查文件是否已保存
    if not bpy.data.is_saved or not bpy.data.filepath:
        bpy.context.window_manager.popup_menu(
            lambda s, c: s.layout.label(text="请先保存.blend文件！"),
            title="提示", icon='INFO')
        print("错误：当前文件尚未保存，无法确定文件夹位置。")
        return {'CANCELLED'}

    # 获取.blend文件所在的目录
    blend_filepath = bpy.data.filepath
    blend_directory = os.path.dirname(blend_filepath)
    
    # 确认目录是否存在
    if not os.path.isdir(blend_directory):
        bpy.context.window_manager.popup_menu(
            lambda s, c: s.layout.label(text="文件夹路径无效！"),
            title="错误", icon='ERROR')
        print(f"错误：文件夹不存在 - {blend_directory}")
        return {'CANCELLED'}

    # 根据操作系统打开文件夹
    try:
        if sys.platform == "win32":
            # Windows
            os.startfile(blend_directory)
        elif sys.platform == "darwin":
            # macOS
            subprocess.Popen(["open", blend_directory])
        else:
            # Linux 和其他类Unix系统
            subprocess.Popen(["xdg-open", blend_directory])
            
        print(f"已打开文件夹: {blend_directory}")
        return {'FINISHED'}
        
    except Exception as e:
        bpy.context.window_manager.popup_menu(
            lambda s, c: s.layout.label(text="无法打开文件夹！"),
            title="错误", icon='ERROR')
        print(f"打开文件夹时出错: {e}")
        return {'CANCELLED'}


# --- 定义Blender操作符（可选，但推荐用于集成到UI中） ---
class FILE_OT_open_current_folder(bpy.types.Operator):
    """打开当前.blend文件所在的文件夹"""
    bl_idname = "file.open_current_folder"
    bl_label = "打开当前文件夹"
    bl_options = {'REGISTER'}

    def execute(self, context):
        return open_current_blend_folder()

# --- 注册操作符 ---
def register():
    bpy.utils.register_class(FILE_OT_open_current_folder)

def unregister():
    bpy.utils.unregister_class(FILE_OT_open_current_folder)

# --- 主程序入口 ---
if __name__ == "__main__":
    # 如果直接运行脚本，先注册操作符
    register()
    
    # 然后直接执行打开文件夹的功能
    open_current_blend_folder()
