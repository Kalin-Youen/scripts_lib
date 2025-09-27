# script_id: 473005d5-2491-4775-b486-443d3a58ac6c
import os
import bpy

# 临时 Operator
class TEMP_OT_append_collections(bpy.types.Operator):
    """递归遍历指定目录，批量追加同名 Collection 并剔除重复对象"""
    bl_idname = "temp.append_collections"
    bl_label = "Batch Append Collections"
    bl_options = {'REGISTER', 'UNDO'}

    # 目录选择属性，支持 Blender 相对路径 (“//” 开头)
    folder_path: bpy.props.StringProperty(
        name="根目录",
        description="递归搜索 .blend 文件的根目录（可使用 // 作为 .blend 同级）",
        subtype='DIR_PATH',
        default=r"E:\files\work\blender\project\gongsi\解剖室\其他设备",
    )

    @classmethod
    def poll(cls, context):
        # 只有当前 .blend 已保存时才允许
        return True

    def invoke(self, context, event):
        # 弹出对话框让用户选目录
        return context.window_manager.invoke_props_dialog(self, width=600)

    def execute(self, context):
        # 1. 解析绝对路径
        root_dir = bpy.path.abspath(self.folder_path)
        if not os.path.isdir(root_dir):
            self.report({'ERROR'}, f"目录不存在: {root_dir}")
            self.unregister()
            return {'CANCELLED'}

        # 2. 记录场景下已有的 Collection 名称
        root_coll = context.scene.collection
        existing_colls = {c.name for c in root_coll.children}

        # 3. 遍历所有 .blend 文件
        total_appended = 0
        for root, dirs, files in os.walk(root_dir):
            for fname in files:
                if not fname.lower().endswith(".blend"):
                    continue
                blend_path = os.path.join(root, fname)
                coll_name = os.path.splitext(fname)[0]

                if coll_name in existing_colls:
                    print(f"跳过已存在 Collection: {coll_name}")
                    continue

                # 记录已有对象名，用于去重
                before_objs = set(bpy.data.objects.keys())

                # 从 .blend 链接/追加 Collection
                with bpy.data.libraries.load(blend_path, link=False) as (src, dst):
                    if coll_name in src.collections:
                        dst.collections = [coll_name]
                    else:
                        print(f"未在 {blend_path} 中找到 Collection '{coll_name}'")
                        continue

                new_coll = bpy.data.collections.get(coll_name)
                if not new_coll:
                    print(f"从 {blend_path} 导入 '{coll_name}' 失败")
                    continue

                # 删除与场景已有同名对象
                removed = 0
                for obj in list(new_coll.all_objects):
                    if obj.name in before_objs:
                        # 从所有 Collection 解绑并删除
                        for uc in list(obj.users_collection):
                            uc.objects.unlink(obj)
                        bpy.data.objects.remove(obj, do_unlink=True)
                        removed += 1

                # 挂到场景根 Collection
                root_coll.children.link(new_coll)
                existing_colls.add(coll_name)
                total_appended += 1
                print(f"追加 Collection '{coll_name}'（剔除重复 {removed} 个对象）")

        self.report({'INFO'}, f"共追加 {total_appended} 个 Collection")
        # 执行完毕后注销自己
        self.unregister()
        return {'FINISHED'}

    def cancel(self, context):
        # 用户取消时也注销
        self.unregister()
        return {'CANCELLED'}

    def unregister(self):
        try:
            bpy.utils.unregister_class(self.__class__)
        except Exception:
            pass


# 包装函数：注册并调用临时 Operator
def batch_append_collections():
    bpy.utils.register_class(TEMP_OT_append_collections)
    bpy.ops.temp.append_collections('INVOKE_DEFAULT')


# 脚本入口
if __name__ == "__main__":
    batch_append_collections()
