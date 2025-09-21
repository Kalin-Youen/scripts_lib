import bpy

def select_objects_in_collection_and_children(collection):
    for obj in collection.objects:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
    for child_col in collection.children:
        select_objects_in_collection_and_children(child_col)

# 替换这里的集合名称为你想要选择的集合
collection_name = "曲线阵列"

if collection_name in bpy.data.collections:
    # 获取指定集合
    target_collection = bpy.data.collections[collection_name]

    # 取消选择所有对象
    bpy.ops.object.select_all(action='DESELECT')

    # 选中指定集合及其所有子集合中的对象
    select_objects_in_collection_and_children(target_collection)
else:
    print(f"Collection '{collection_name}' not found.")
