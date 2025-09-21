import bpy
import os

# —— 1. 获取当前 .blend 文件名 —— 
blend_path = bpy.data.filepath
if not blend_path:
    print("请先保存 .blend 文件！")
else:
    file_name = os.path.splitext(os.path.basename(blend_path))[0]

    # —— 2. 查找或创建同名 Collection —— 
    if file_name in bpy.data.collections:
        target_coll = bpy.data.collections[file_name]
    else:
        target_coll = bpy.data.collections.new(file_name)
        # 挂到场景根 Collection 下
        bpy.context.scene.collection.children.link(target_coll)
        print(f"已创建 Collection '{file_name}'")

    # —— 3. 移动选中物体到目标 Collection —— 
    sel_objs = bpy.context.selected_objects
    if not sel_objs:
        print("当前没有选中的物体。")
    else:
        moved = 0
        for obj in sel_objs:
            # 可选：先从所有原 Collection 中解绑（如果想保留原有 Collection，可注释下面两行）
            for col in list(obj.users_collection):
                col.objects.unlink(obj)
            # 链接到目标 Collection
            target_coll.objects.link(obj)
            moved += 1
        print(f"已将 {moved} 个物体移动到 Collection '{file_name}'")
