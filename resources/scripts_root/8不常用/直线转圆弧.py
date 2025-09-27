# script_id: 6ef59390-141c-40e8-9905-5d56635ba502
# script_id: 50d3efcd-b034-459d-bb70-7e422eff0e63
# script_id: 6ef59390-141c-40e8-9905-5d56635ba502
# script_id: 50d3efcd-b034-459d-bb70-7e422eff0e63
# script_id: 401beab2-5127-4b3b-9bfb-e4d44c3b1039
# script_id: 6ef59390-141c-40e8-9905-5d56635ba502
# script_id: 50d3efcd-b034-459d-bb70-7e422eff0e63
# script_id: 6ef59390-141c-40e8-9905-5d56635ba502
# script_id: 50d3efcd-b034-459d-bb70-7e422eff0e63
import bpy
import bmesh
from math import atan2, sqrt, cos, sin

# 确保 Blender 处于对象模式
bpy.ops.object.mode_set(mode='OBJECT')


def convert_to_arc(obj):
    if obj.type == 'MESH':
        # 获取物体的网格数据
        mesh_data = obj.data
        
        # 使用 bpy 结构直接访问网格数据
        for vertex in mesh_data.vertices:
            # 新的 x, y 坐标
            x, y, z = vertex.co
            
            restored_alpha = -x / 20
            
            # 假设 restored_alpha 的值是在 [-pi, pi] 的范围
            # 那么我们可以用 cos 和 sin 来恢复原始的 x 和 y 坐标
            # 还需要用新的 y 坐标（即原来的距离 d）来缩放这些值
            d = y  # 新的 y 坐标即为原点到点的距离
            original_x = d * cos(restored_alpha)
            original_y = d * sin(restored_alpha)
            
            # 更新顶点坐标
            vertex.co.x = original_x
            vertex.co.y = original_y
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
    convert_to_arc(obj)
