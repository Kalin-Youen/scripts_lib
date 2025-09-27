# script_id: aebca242-92ec-4af3-8b7c-fd340fed80a4
import os
import bpy

# —— 1. 定义临时 Operator —— 
class TEMP_OT_unpack_images(bpy.types.Operator):
    """将所有已打包图片解包并以指定格式保存到 Blend 文件同级的子目录"""
    bl_idname = "temp.unpack_images"
    bl_label = "Unpack Images to Folder"
    bl_options = {'UNDO'}

    # 用户可设定的参数
    subfolder: bpy.props.StringProperty(
        name="目标子文件夹",
        description="相对于 Blend 文件所在目录的子文件夹",
        default="unpacked_images",
    )
    file_format: bpy.props.EnumProperty(
        name="输出格式",
        description="解包后图片的文件格式",
        items=[
            ('PNG', 'PNG', '保存为 PNG 格式'),
            ('JPEG', 'JPEG', '保存为 JPEG 格式'),
            ('TARGA', 'Targa', '保存为 Targa (.tga)'),
        ],
        default='PNG',
    )
    replace_existing: bpy.props.BoolProperty(
        name="覆盖已存在文件",
        description="如果目标路径已有同名文件，是否覆盖",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        # 只有当已经保存过 Blend 文件时才允许
        return bpy.data.filepath != ""

    def invoke(self, context, event):
        # 弹出属性对话框
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        # 计算目标目录
        blend_dir = os.path.dirname(bpy.data.filepath)
        target_dir = os.path.join(blend_dir, self.subfolder)
        os.makedirs(target_dir, exist_ok=True)

        count = 0
        for img in bpy.data.images:
            # 只处理已打包的图片，或者所有图片？可自行改逻辑
            if img.packed_file:
                # 保存前暂存原格式
                orig_fmt = img.file_format
                img.file_format = self.file_format

                # 构造文件名（确保合法）
                name = bpy.path.clean_name(img.name)
                ext = self.file_format.lower() if self.file_format != 'JPEG' else 'jpg'
                filename = f"{name}.{ext}"
                fullpath = os.path.join(target_dir, filename)

                # 如果不覆盖且文件存在就跳过
                if not self.replace_existing and os.path.exists(fullpath):
                    print(f"跳过已存在：{filename}")
                else:
                    try:
                        # 将图片保存到磁盘
                        # 推荐使用 save_render，兼容大多数类型
                        img.save_render(fullpath)
                        count += 1
                        print(f"Saved: {fullpath}")
                    except Exception as e:
                        self.report({'WARNING'}, f"保存失败: {filename} -> {e}")
                    finally:
                        # 恢复原始格式设置
                        img.file_format = orig_fmt

        self.report({'INFO'}, f"共解包并保存 {count} 张图片到：{self.subfolder}")
        # 执行完毕后注销自己
        bpy.utils.unregister_class(self.__class__)
        return {'FINISHED'}

    def cancel(self, context):
        # 用户在对话框中取消也要注销自己
        bpy.utils.unregister_class(self.__class__)
        return {'CANCELLED'}


# —— 2. 注册→调用的包装函数 —— 
def unpack_images_interactive():
    bpy.utils.register_class(TEMP_OT_unpack_images)
    # 弹出对话框
    bpy.ops.temp.unpack_images('INVOKE_DEFAULT')


# —— 3. 脚本入口 —— 
if __name__ == "__main__":
    unpack_images_interactive()
