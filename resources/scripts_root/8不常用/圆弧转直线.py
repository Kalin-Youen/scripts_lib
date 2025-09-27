# script_id: a64951ae-e32a-4023-ac61-85f71eecc9ca
# script_id: f9619c22-29bc-49b3-812f-4e8307b887be
# script_id: a64951ae-e32a-4023-ac61-85f71eecc9ca
# script_id: f9619c22-29bc-49b3-812f-4e8307b887be
# script_id: 2a3f4eac-0e6f-4daf-9d17-262c0d94df55
# script_id: a64951ae-e32a-4023-ac61-85f71eecc9ca
# script_id: f9619c22-29bc-49b3-812f-4e8307b887be
# script_id: a64951ae-e32a-4023-ac61-85f71eecc9ca
# script_id: f9619c22-29bc-49b3-812f-4e8307b887be
import bpy
import bmesh
from math import atan2, sqrt, pi

# 确保 Blender 处于对象模式
bpy.ops.object.mode_set(mode='OBJECT')

def arc_to_line(obj):
    if obj.type == 'MESH':
        # 获取物体的网格数据
        mesh_data = obj.data
        
        # 使用 bpy 结构直接访问网格数据
        for vertex in mesh_data.vertices:
            # 原始的 x, y, z 坐标
            x, y, z = vertex.co
            
            # 计算角度 α，atan2 返回正确的象限角度
            alpha = atan2(y, x)
            
            # 更新 x 坐标为与角度 α 相关的值，此处直接使用角度 alpha
            # 由于 alpha 是弧度制，我们可能需要将其映射到一个合适的范围，例如 [0, 1] 或 [-pi, pi]
            vertex.co.x = -alpha*20
            
            # 更新 y 坐标为到原点的距离 d
            vertex.co.y = sqrt(x**2 + y**2)
            
            # z 坐标保持不变
            
        # 更新网格
        mesh_data.update()

        # 刷新场景，确保变更生效
        bpy.context.view_layer.update()
    else:
        print("Selected object is not a mesh.")

# 调用方法
selected_objs = bpy.context.selected_objects
for obj in selected_objs:
    # 调用方法
    arc_to_line(obj)
