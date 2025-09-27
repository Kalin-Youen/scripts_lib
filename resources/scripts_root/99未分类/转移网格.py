# script_id: 4470b63c-3139-4421-8834-a7a3ad41d04b
import bpy

def ensure_uv_map_name(obj_source, obj_target):
    """确保两个对象的 UV 名称一致，将源对象的 UV 名称修改为目标对象的 UV 名称。"""
    if obj_source.data.uv_layers and obj_target.data.uv_layers:
        source_uv_map = obj_source.data.uv_layers.active.name
        target_uv_map = obj_target.data.uv_layers.active.name
        
        # 如果名称不同，将源的 UV 名称改为目标对象的 UV 名称
        if source_uv_map != target_uv_map:
            obj_source.data.uv_layers[source_uv_map].name = target_uv_map
            print(f"将物体 {obj_source.name} 的 UV 名称由 {source_uv_map} 修改为 {target_uv_map}。")
        else:
            print(f"物体 {obj_source.name} 的 UV 名称已与物体 {obj_target.name} 一致。")

def separate_and_merge():
    # 当前活动物体为物体 a
    a = bpy.context.active_object

    # 确认是否处于编辑模式
    if a is None or a.mode != 'EDIT':
        print("请确保活动物体处于编辑模式。")
        return

    # 获取选中的其他物体作为物体 b
    selected_objects = [obj for obj in bpy.context.selected_objects if obj != a]
    if not selected_objects:
        print("请选择一个非活动物体作为物体 b。")
        return

    b = selected_objects[0]  # 假设选中了一个目标物体
    
    # 分离选中的网格（分离为物体 c）
    bpy.ops.object.mode_set(mode='EDIT')  # 确保处于编辑模式
    bpy.ops.mesh.separate(type='SELECTED')  # 分离选中的网格
    bpy.ops.object.mode_set(mode='OBJECT')  # 切换到对象模式

    # 获取分离产生的新物体 c
    c = bpy.context.scene.objects[-1]  # 新创建的物体通常是列表的最后一个

    # 确保 UV 名称一致
    ensure_uv_map_name(c, b)

    # 将物体 b 设置为活动物体，准备合并
    bpy.context.view_layer.objects.active = b
    b.select_set(True)  # 选中物体 b
    c.select_set(True)  # 选中物体 c

    # 合并物体 b 和物体 c
    bpy.ops.object.join()
    # 取消所有选择
    bpy.ops.object.select_all(action='DESELECT')

    # 切回到物体 a 并进入编辑模式
    bpy.context.view_layer.objects.active = a
    bpy.ops.object.mode_set(mode='EDIT')

    print("操作完成：分离网格并合并物体成功。")

# 调用函数
separate_and_merge()
