
import bpy
from math import atan2, degrees, radians
import math
import random
import bpy
import bmesh
from mathutils import Matrix,Vector
from mathutils import Quaternion
from bpy_extras.view3d_utils import location_3d_to_region_2d

def save_3d_view_settings():
    settings = {}
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            rv3d = area.spaces.active.region_3d
            settings['view_perspective'] = rv3d.view_perspective
            settings['view_rotation'] = rv3d.view_rotation.copy()
            settings['view_location'] = rv3d.view_location.copy()
            settings['view_distance'] = rv3d.view_distance
            break # 如果有多个3D视图，这将只保存找到的第一个
    return settings

def load_3d_view_settings(settings):
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            rv3d = area.spaces.active.region_3d
            rv3d.view_perspective = settings['view_perspective']
            rv3d.view_rotation = settings['view_rotation']
            rv3d.view_location = settings['view_location']
            rv3d.view_distance = settings['view_distance']
            area.tag_redraw()
            break  # 如果有多个3D视图，这将只加载至找到的第一个

def 选择三点(obj,context):
    
    # 获取当前对象的bmesh
    # obj = bpy.context.edit_object
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)

    # 更新bmesh的查找表
    bm.verts.ensure_lookup_table()

    # 获取所有未隐藏的顶点
    visible_verts = [v for v in bm.verts if not v.hide]

    # 找到端点
    end_verts = [v for v in visible_verts if len([e for e in v.link_edges if not e.other_vert(v).hide]) == 1]

    # 检查是否找到了两个端点
    if len(end_verts) == 2:
        # 选出连续线段的所有顶点
        def walk_vert_chain(vert, prev_vert=None):
            chain = [vert]
            while True:
                # 获取下一个顶点
                next_verts = [e.other_vert(vert) for e in vert.link_edges if not e.other_vert(vert).hide and e.other_vert(vert) != prev_vert]
                if next_verts:
                    prev_vert = vert
                    vert = next_verts[0]
                    chain.append(vert)
                else:
                    break
            return chain

        # 从一个端点走到另一个端点
        vert_chain = walk_vert_chain(end_verts[0])

        # 找到中间的顶点
        middle_index = len(vert_chain) // 2
        middle_vert = vert_chain[middle_index]

        # 选择中间的顶点和两个端点
        middle_vert.select = True
        end_verts[0].select = True
        end_verts[1].select = True

        # 更新网格以显示所做的选择
        
        v1=end_verts[0]
        v2=end_verts[1]
        v3=middle_vert
            
        # 计算平面法线和向量
        v1_v2 = (v2.co - v1.co).normalized()
        v1_v3 = (v3.co - v1.co).normalized()
        plane_normal = v1_v2.cross(v1_v3).normalized()
        
        if plane_normal.dot(v1_v3) > 0:
            plane_normal.negate()

        y_axis = plane_normal.cross(v1_v2)
        view_quat = y_axis.to_track_quat('Y', 'Z')

        # 应用视图旋转到顶点坐标
        view_matrix = view_quat.to_matrix().to_4x4()
        v1_view = view_matrix @ v1.co
        v2_view = view_matrix @ v2.co
        v3_view = view_matrix @ v3.co
        
        # 检查并调整视图，使得v3在视图上低于v1和v2
        if v3_view.y < v1_view.y or v3_view.y < v2_view.y:
            view_quat = view_quat @ Quaternion((0, 0, 1), math.pi)  # Z轴180度旋转

        # 设置3D视图
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                v3d = area.spaces[0]
                rv3d = v3d.region_3d
                rv3d.view_perspective = 'ORTHO'
                rv3d.view_rotation = view_quat
                rv3d.view_location = (v1.co + v2.co + v3.co) / 3
                # rv3d.view_distance = (v1.co - v2.co).length
                area.tag_redraw()
                # 更新场景，这样变化就立即生效了
                context.view_layer.update()
                break
            
            
            bmesh.update_edit_mesh(mesh)
        return context

    else:
        print("未找到两个端点或找到的端点数目不正确。")



bpy.ops.mesh.hide(unselected=True)

def 缩放(context):
    context.scene.transform_orientation_slots[0].type = 'VIEW'
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.002, use_unselected=False)
    # 设置缩放值，其中 X 轴为 0.03，Y 轴和 Z 轴为 1（不变）
    scale_factor = (0.001, 1, 0.001)
    # 调用缩放操作，并设置坐标系为视图 ('VIEW')
    bpy.ops.transform.resize(value=scale_factor, orient_type='VIEW')
    context.scene.transform_orientation_slots[0].type = 'GLOBAL'       


def 运行粘手切开():

    
    # 确保在编辑模式下
    if bpy.context.object.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
    
    # 获取当前活跃的3D视图
    # 这将确保我们可以获取正确的3D视图上下文
    space_data = None
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            space_data = area.spaces.active
            break
        
    if not space_data:
        raise RuntimeError("No active 3D View found")
    
    # 获取视图矩阵，这将用于世界空间和视图空间之间的转换
    view_matrix = space_data.region_3d.view_matrix
    inverse_view_matrix = view_matrix.inverted()
    
    # 获取当前对象的bmesh
    obj = bpy.context.edit_object
    bm = bmesh.from_edit_mesh(obj.data)
    
    # 更新bmesh的查找表
    bm.verts.ensure_lookup_table()
    
    # 获取所有未隐藏的顶点
    visible_verts = [v for v in bm.verts if not v.hide]
    
    # 找到端点：只连接一个未隐藏顶点的顶点
    end_verts = [v for v in visible_verts if len([e for e in v.link_edges if not e.other_vert(v).hide]) == 1]
    
    # 确保发现了两个端点
    if len(end_verts) != 2:
        print("Expected 2 endpoints, but found {}: {}".format(len(end_verts), end_verts))
    else:
        # 将端点从世界空间转换到视图空间
        view_space_endpoints = [view_matrix @ obj.matrix_world @ vert.co for vert in end_verts]
    
        # 获取Y轴的平均位置
        avg_y = sum(vert.y for vert in view_space_endpoints) / 2
    
        # 将端点的视图空间Y坐标设置为平均值
        for i, vert in enumerate(end_verts):
            view_space_endpoints[i].y = avg_y
    
            # 将视图空间坐标转换回世界空间坐标，并更新顶点位置
            vert.co = obj.matrix_world.inverted() @ inverse_view_matrix @ view_space_endpoints[i]
    
    
        # 更新bmesh
        bmesh.update_edit_mesh(obj.data)
        
        
    bpy.ops.object.mode_set(mode='EDIT')
    
    
    
    # 假设 bm, view_matrix, obj.matrix_world, inverse_view_matrix 已经定义
    
    # 获取所有未隐藏的顶点和边
    visible_verts = [v for v in bm.verts if not v.hide]
    visible_edges = [e for e in bm.edges if not e.hide]
    
    # 转换顶点坐标并找到y坐标最小的顶点
    view_space_verts = [(view_matrix @ obj.matrix_world @ vert.co, vert.index) for vert in visible_verts]
    lowest_vert_view_space, lowest_vert_index = min(view_space_verts, key=lambda x: x[0].y)
    world_space_lowest_vert = obj.matrix_world.inverted() @ inverse_view_matrix @ lowest_vert_view_space
    
    # 计算每条边的长度
    edge_lengths = {edge.index: edge.calc_length() for edge in visible_edges}
    
    # 获取每个顶点的连接信息
    visible_vert_indices = [vert.index for vert in visible_verts]
    connections = {
        vert.index: [v.index for e in vert.link_edges for v in e.verts if v.index != vert.index and v.index in visible_vert_indices]
        for vert in visible_verts
    }
    
    # 获取仅连接了一条边的顶点
    one_edge_verts = [v for v in visible_verts if len([e for e in v.link_edges if not e.other_vert(v).hide]) == 1]
    
    # 获取边与其连接顶点的映射关系
    edge_to_verts = {edge.index: [v.index for v in edge.verts] for edge in visible_edges}
    
    # 整理输出信息，
    output_info = {
        "最小Y坐标顶点索引": lowest_vert_index,
        "最小Y坐标顶点世界空间坐标": world_space_lowest_vert.to_tuple(),  # 转换为元组以便于阅读
        "边的长度": edge_lengths,
        "只连接一条边的顶点": one_edge_verts,
        "顶点的连接信息": connections,
        "边到顶点的映射": edge_to_verts,
    }
    
    # 打印字典格式的输出信息，确保换行
    for key, value in output_info.items():
        if isinstance(value, dict):  # 如果值是字典，进行格式化
            print(f"{key}: {{")
            for sub_key, sub_value in value.items():
                print(f"    {sub_key}: {sub_value},")
            print("}\n")
        else:
            print(f"{key}:\n{value}\n")
    
    
    # 我们假设 connections 和 edge_to_verts 字典已经被正确填充
    start_vertex = one_edge_verts[0].index
    end_vertex = one_edge_verts[1].index
    current_vertex = start_vertex
    path = [current_vertex]
    
    while current_vertex != end_vertex:
        # 获取与当前顶点相连的边
        edges = [k for k, v in edge_to_verts.items() if current_vertex in v]
        
        # 找到一个连接到新顶点的边
        for edge in edges:
            # 找到边的另一个顶点
            next_vertex = [v for v in edge_to_verts[edge] if v != current_vertex][0]
            # 如果这个顶点没有被访问过，则选择这个顶点
            if next_vertex not in path:
                selected_edge = edge
                selected_vertex = next_vertex
                break
            
        path.append(selected_edge)
        path.append(selected_vertex)
        current_vertex = selected_vertex
    
    print(path)
    
    # 找到共同顶点的索引
    split_index = path.index(lowest_vert_index)
    
    # 创建第一个路径段，从列表的开始到共同顶点（含共同顶点）
    path1 = path[:split_index+1]
    
    # 创建第二个路径段，从共同顶点到列表的结束
    path2 = path[split_index:]
    
    # 打印结果
    print("第一段路径:", path1)
    print("第二段路径:", path2)
    
    edges_in_path1 = path1[1::2]
    edges_in_path2 = path2[1::2]
    
    print("第一段路径:", edges_in_path1)
    print("第二段路径:", edges_in_path2)
    
    path1_edge_count = len(edges_in_path1)
    path2_edge_count = len(edges_in_path2)
    
    if path1_edge_count != path2_edge_count:
        # 确定边shao的路径
        if path1_edge_count > path2_edge_count:
            edge_count_difference = path1_edge_count - path2_edge_count
            edges_to_sort = edges_in_path2
        else:
            edge_count_difference = path2_edge_count - path1_edge_count
            edges_to_sort = edges_in_path1
        
        # 根据边的长度进行降序排序
        sorted_edges_by_length_desc = sorted(edges_to_sort, key=lambda edge: edge_lengths[edge], reverse=True)
        
        # 取出最长的n条边
        longest_n_edges_ids = sorted_edges_by_length_desc[:edge_count_difference]
    else:
        longest_n_edges_ids = []
        
    # 打印结果
    if longest_n_edges_ids:
        print(f"选出来的最长的{edge_count_difference}条边的编号为:", longest_n_edges_ids)
        
         
    else:
        print("两条路径的边数相同，不需要提取边。")
               
    
    # 切换到边选择模式
    bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
    
    
    if bpy.context.object.mode == 'EDIT':
        # 获取当前编辑网格的bmesh表示
        obj = bpy.context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        # 取消选择所有顶点/边/面
        for vert in bm.verts:
            vert.select = False
        for edge in bm.edges:
            edge.select = False
        for face in bm.faces:
            face.select = False

        # 更新BMesh到网格对象
        bmesh.update_edit_mesh(me)

        # 刷新界面显示
        bpy.context.view_layer.update()
    

    # 选择给定索引的边
    for edge in bm.edges:
        if edge.index in longest_n_edges_ids:
            edge.select = True

    
    # 在选中的边上进行一次细分
    bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if e.select], cuts=1)
    
  
    
    # 选择所有元素：顶点
    for v in bm.edges:
        v.select = True
        
    if "mesh_looptools" not in bpy.context.preferences.addons.keys():
        bpy.ops.preferences.addon_enable(module="mesh_looptools")
    # 调用 LoopTools 的空间命令
    bpy.ops.mesh.looptools_space(interpolation='linear')
    
    # 切换到点模式
    bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
            
    # 更新bmesh
    bmesh.update_edit_mesh(obj.data)
    
    # 确保 Blender 处于编辑模式
    bpy.ops.object.mode_set(mode='EDIT')
    
    # 获取当前活动对象和网格数据
    obj = bpy.context.active_object
    me = obj.data
    
    # 获取 bmesh 对象
    bm = bmesh.from_edit_mesh(me)
    
    # 清除之前的选择
    bm.select_mode = {'EDGE'}  # 设置选择模式为边
    for edge in bm.edges:
            edge.select = False
    
    
    
    # 选择所有边
    for edge in bm.edges:
        edge.select = True

    # 显示更新后的选择
    bmesh.update_edit_mesh(me)


    # 分离选中的边
    bpy.ops.mesh.edge_split()

    for edge in bm.verts:
            edge.select = False
            
            
    bm = bmesh.from_edit_mesh(me)
    bm.verts.ensure_lookup_table()  # 确保顶点索引表是最新的

    bm.select_mode = {'VERT'}
    
    

    bm.verts[start_vertex].select = True
    # 获取要设置为活动的顶点
    
    
    # 获取所有未隐藏的顶点
    visible_verts = [v for v in bm.verts if not v.hide]

    # 转换顶点坐标到视图空间
    view_space_verts = [(view_matrix @ obj.matrix_world @ vert.co, vert) for vert in visible_verts]

    # 找出y坐标最大的两个顶点（也就是视图空间中最上方的两个顶点）
    top_two_verts_view_space = sorted(view_space_verts, key=lambda x: x[0].y, reverse=True)[:2]

    # 获取这两个顶点的索引
    top_two_verts_indices = [vert_view_space[1].index for vert_view_space in top_two_verts_view_space]

    # 分别为v1和v2分配索引
    v1, v2 = top_two_verts_indices

    
    
    active_vertex = bm.verts[v1]

    # 设置为活动顶点
    bm.select_history.clear()
    bm.select_history.add(active_vertex)

    # 更新显示
    bmesh.update_edit_mesh(me)
    
    bpy.ops.mesh.shortest_path_pick(edge_mode='SELECT', use_fill=False, index=v2)


   

    # 必须在进行选择操作后，调用此函数来更新编辑网格的选择状态
    bmesh.update_edit_mesh(me)
    
    
    
    # 获取当前视图矩阵
    view_matrix = bpy.context.region_data.view_matrix
    
    # 计算视图X轴方向
    view_x_axis = view_matrix.inverted().to_3x3() @ Vector((1.0, 0.0, 0.0))
    
    # 定义移动顶点的函数
    def move_verts_along_view_x(verts, view_x_dir, distance):
        for vert in verts:
            if vert.select:
                vert.co += view_x_dir * distance
                
    # 确保自动合并关闭
    bpy.context.scene.tool_settings.use_mesh_automerge = False

    
    # 沿视图X轴移动顶点 0.004 单位
    move_verts_along_view_x(bm.verts, view_x_axis, 0.004)
    
    move_verts_along_view_x(visible_verts, view_x_axis, -0.002)
    
    
    visible_verts = [v for v in bm.verts if not v.hide]
    for v in visible_verts:
        v.select = True
        
    # 创建一个用于存放顶点的集合
    vertex_indices_to_select = {v.index for v in visible_verts}  # 假定我们要选中编号为0, 1, 2的顶点


            
    bpy.ops.mesh.remove_doubles(threshold=0.0015)
    

    bpy.ops.mesh.reveal()  # 显示全部网格

    # 执行三角化操作
    bpy.ops.mesh.quads_convert_to_tris()
    
    # 更新网格数据
    bmesh.update_edit_mesh(me)
    
    obj = bpy.context.edit_object
    me = obj.data
    bm = bmesh.from_edit_mesh(me)

    # 取消选择所有的顶点
    for v in bm.verts:
        v.select = False
    verts_to_merge = []
    
    for v in bm.verts:
        if len(v.link_edges) == 2:
            v.select = True
            verts_to_merge.append(v)
            
    # 选择我们之前找到的顶点
    for v in verts_to_merge:
        v.select = True
        
    # 更新显示所选顶点
    bmesh.update_edit_mesh(me)
    
    # 溶解已选择的顶点
    bpy.ops.mesh.dissolve_verts()

    bpy.context.space_data.shading.show_xray = False
    
    # set_front_view()

    # 清除所有顶点的选中状态
    for v in bm.verts:
        v.select = False
    # 确保选中状态得到更新
    bmesh.update_edit_mesh(me)
    # 确保查找表是最新的，这一步是必须的
    bm.verts.ensure_lookup_table()

    # 遍历集合并选中顶点
    for v_idx in vertex_indices_to_select:
        if v_idx < len(bm.verts):
            bm.verts[v_idx].select = True
    bpy.ops.mesh.vertices_smooth(factor=0.5)

    bpy.context.view_layer.update()


context=bpy.context
# 运行函数并打印结果
saved_settings = save_3d_view_settings()
obj=context.active_object
context=选择三点(obj,context)
# 建模相关工具.选择三点并旋转视图(obj)
缩放(context)


# 运行粘手切开()
# saved_settings = load_3d_view_settings(saved_settings)