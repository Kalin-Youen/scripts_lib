# 根据材质名重命名
# 根据材质名重命名
# 8脚本
import bpy

# 获取当前选中的物体
selected_objects = bpy.context.selected_objects

# 遍历每一个选中的物体
for obj in selected_objects:
    # 确保物体是 mesh 类型并且有材质
    if obj.type == 'MESH' and obj.data.materials:
        # 获取第一个材质槽的材质
        first_material = obj.data.materials[0]
        if first_material:
            # 设置物体的名字为第一个材质槽的材质名
            obj.name = first_material.name
        else:
            print(f"物体 {obj.name} 没有有效的材质")
    else:
        print(f"物体 {obj.name} 没有材质或不是网格物体")
