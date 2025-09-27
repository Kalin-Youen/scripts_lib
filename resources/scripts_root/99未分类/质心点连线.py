# script_id: 2949e810-f71e-4fad-97f2-ddf234fec7f1
import bpy
import bmesh
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree

def create_mesh_from_loose_parts(obj, max_connections=2):
    if obj.type != 'MESH':
        print("请选择一个网格对象！")
        return

    # 获取对象的世界变换矩阵
    world_matrix = obj.matrix_world

    # 创建一个独立的 bmesh 副本，用于操作网格
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    # 查找松散块
    loose_parts = []
    visited_verts = set()
    
    for vert in bm.verts:
        if vert.index not in visited_verts:
            connected_verts = set()
            stack = [vert]
            
            while stack:
                current_vert = stack.pop()
                if current_vert.index not in visited_verts:
                    visited_verts.add(current_vert.index)
                    connected_verts.add(current_vert)
                    stack.extend([edge.other_vert(current_vert) for edge in current_vert.link_edges])
            
            loose_parts.append(connected_verts)

    # 计算每个松散块的质心（在世界坐标系中）
    centroids = []
    for loose_part in loose_parts:
        centroid = Vector((0, 0, 0))
        for vert in loose_part:
            centroid += world_matrix @ vert.co
        centroid /= len(loose_part)
        centroids.append(centroid)

    # 创建KD树用于最近邻搜索
    kd = KDTree(len(centroids))
    for i, centroid in enumerate(centroids):
        kd.insert(centroid, i)
    kd.balance()

    # 创建新的网格
    mesh = bpy.data.meshes.new(name=f"{obj.name}_LooseParts_Mesh")
    mesh_obj = bpy.data.objects.new(f"{obj.name}_LooseParts_Mesh", mesh)
    bpy.context.scene.collection.objects.link(mesh_obj)

    bm_new = bmesh.new()

    # 添加顶点
    vertices = [bm_new.verts.new(centroid) for centroid in centroids]

    # 添加边
    edges_added = set()
    for i, v in enumerate(vertices):
        for (co, index, dist) in kd.find_n(centroids[i], max_connections + 1):
            if index != i and index > i:
                edge_key = tuple(sorted([i, index]))
                if edge_key not in edges_added:
                    bm_new.edges.new((vertices[i], vertices[index]))
                    edges_added.add(edge_key)

    bm_new.to_mesh(mesh)
    bm_new.free()

    mesh.update()
    
    print(f"已创建网格连接松散块")

    # 清除原始 bmesh 数据
    bm.free()

def main():
    obj = bpy.context.active_object
    if obj:
        create_mesh_from_loose_parts(obj)
    else:
        print("请先选择一个物体")

# if __name__ == "__main__":
main()
