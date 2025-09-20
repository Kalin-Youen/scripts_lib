import bpy

# 遍历所有选中的物体
for obj in bpy.context.selected_objects:
    # 确保物体有数据可以被命名
    if obj.data:
        # 将网格数据块重命名为物体的名字（如果它们的名字不一样）
        if obj.data.name != obj.name:
            obj.data.name = obj.name
    
    # # 对物体的所有材质做同样的处理
    if obj.material_slots and len(obj.material_slots) == 1:
        for slot in obj.material_slots:
            if slot.material and slot.material.name != obj.name:
                slot.material.name = obj.name

    # 还可以根据需要为其他类型的数据块添加类似的代码
    # 例如，粒子系统、形状键等等

# 更新场景，以确保所有更改都被正确显示
bpy.context.view_layer.update()
