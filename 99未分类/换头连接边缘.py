import bpy
import bmesh
import random
def 连接边缘():
    
    # 确保在编辑模式下
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
    obj = bpy.context.object
    bm = bmesh.from_edit_mesh(obj.data)
    bpy.ops.mesh.select_all(action='SELECT')
    # 获取所有当前选中的边
    所有边 = [e for e in bm.edges if e.select]
    # 取消选择所有边
    for e in 所有边:
        e.select = False
    # 从所有边中随机选择一条边
    random_edge = random.choice(所有边)
    random_edge.select = True
    bpy.ops.mesh.select_linked(delimit=set())
    bpy.ops.mesh.remove_doubles(threshold=0.008)
    圈1_1 = [v for v in bm.edges if v.select]
    bpy.ops.mesh.select_all(action='INVERT')
    bpy.ops.mesh.remove_doubles(threshold=0.008)
    圈2_1 = [v for v in bm.edges if v.select]
    # 更新bmesh到mesh数据
    bmesh.update_edit_mesh(obj.data)
    def 计算边长度(edge):
        # 计算并返回边的长度
        return (edge.verts[0].co - edge.verts[1].co).length
    def 两组变数量保持一致(edges1, edges2):
        longest_n_edges = []
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
        if len(edges1) != len(edges2):
            # 确定边少的路径
            if len(edges1) > len(edges2):
                edge_count_difference = len(edges1) - len(edges2)
                edges_to_sort = edges2
            else:
                edge_count_difference = len(edges2) - len(edges1)
                edges_to_sort = edges1
            # 自动计算边的长度并进行降序排序
            边_降序列 = sorted(edges_to_sort, key=计算边长度, reverse=True)
            # 取出最长的n条边
            longest_n_edges = 边_降序列[:edge_count_difference]
        else:
            longest_n_edges = []
        if longest_n_edges:
            print(f"选出来的最长的{len(longest_n_edges)}条边为:", longest_n_edges)
        else:
            print("两边数相同，不需要提取边。")
        # 获取当前编辑网格的bmesh表示
        obj = bpy.context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        # 取消选择所有边
        bpy.ops.mesh.select_all(action='DESELECT')
        bm.select_flush(False)
        # 选择给定边
        for edge in bm.edges:
            if edge in longest_n_edges:
                bpy.ops.mesh.select_all(action='DESELECT')
                edge.select = True
                bpy.ops.mesh.subdivide(number_cuts=1)
        
        bpy.ops.mesh.select_linked(delimit=set())
        圈1 = [e for e in bm.edges if e.select]
        bpy.ops.mesh.looptools_circle()
        bpy.ops.mesh.select_all(action='INVERT')
        圈2 = [e for e in bm.edges if e.select]
        bpy.ops.mesh.looptools_circle()
        return 圈1, 圈2
        
        
    圈1, 圈2=两组变数量保持一致(圈1_1,圈2_1)
  
    # 更新bmesh到mesh数据
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.mesh.select_all(action='SELECT')
    obj = bpy.context.object
    bm = bmesh.from_edit_mesh(obj.data)
    两圈 = [v for v in bm.edges if v.select]
    bpy.ops.mesh.bridge_edge_loops()
    bpy.ops.mesh.select_all(action='SELECT')
    # 取消选择所有选中的边
    for edge in 两圈:
        edge.select = False
    # 更新bmesh到mesh数据
    bmesh.update_edit_mesh(obj.data)
    
    def 合并点到中心():
        obj = bpy.context.object
        bm = bmesh.from_edit_mesh(obj.data)
        edges_to_merge = [e for e in bm.edges if e.select]
        for edge in edges_to_merge:
            center = (edge.verts[0].co + edge.verts[1].co) / 2
            bmesh.ops.pointmerge(bm, verts=edge.verts[:], merge_co=center)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
        bmesh.update_edit_mesh(obj.data)
        bpy.ops.mesh.select_all(action='DESELECT')
    合并点到中心()
    # 处理边,加选三角化并平滑
    bpy.ops.mesh.reveal()
    bpy.ops.mesh.select_all(action='INVERT')
    bpy.ops.mesh.select_more()
    bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
    bpy.ops.mesh.vertices_smooth(factor=1)
    

连接边缘()