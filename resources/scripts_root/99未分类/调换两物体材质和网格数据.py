import bpy

# 获取当前选中的两个对象
selected_objs = bpy.context.selected_objects

# 检查确保只选中了两个网格对象
if len(selected_objs) != 2 or not all(obj.type == 'MESH' for obj in selected_objs):
    print("Error: Need to select exactly two mesh objects.")
else:
    obj1, obj2 = selected_objs

    # 交换网格数据
    obj1.data, obj2.data = obj2.data, obj1.data
    
    # 交换材质
    materials1 = [slot.material for slot in obj1.material_slots]
    materials2 = [slot.material for slot in obj2.material_slots]
    
    for i, material in enumerate(materials1):
        if i < len(obj2.material_slots):
            obj2.material_slots[i].material = material
            
    for i, material in enumerate(materials2):
        if i < len(obj1.material_slots):
            obj1.material_slots[i].material = material

    print("Successfully swapped mesh data and materials between the two selected objects.")
