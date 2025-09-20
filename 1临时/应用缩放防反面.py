import bpy
import bmesh
from mathutils import Vector

def preserve_face_normals_and_apply_transform():
    # 获取所有选中的物体
    selected_objects = bpy.context.selected_objects.copy()
    
    if not selected_objects:
        print("请至少选择一个物体")
        return
    
    print(f"找到 {len(selected_objects)} 个选中的物体")
    
    # 分别处理每个物体
    for obj in selected_objects:
        print(f"\n处理物体: {obj.name} (类型: {obj.type})")
        
        # 清除所有选择，只选中当前物体
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        if obj.type == 'MESH':
            # 对网格物体进行面朝向保护处理
            process_mesh_object(obj)
        else:
            # 对非网格物体只应用变换
            process_non_mesh_object(obj)
    
    # 处理完成后，重新选择所有原本选中的物体
    bpy.ops.object.select_all(action='DESELECT')
    for obj in selected_objects:
        obj.select_set(True)
    
    print("\n所有物体处理完成！")

def process_mesh_object(obj):
    """处理网格物体 - 保护面朝向"""
    try:
        print(f"  -> 网格物体，执行面朝向保护...")
        
        # 确保在编辑模式
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 从编辑网格获取bmesh
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        
        # 记录每个面的法向量（世界坐标系）
        face_normals = []
        world_matrix = obj.matrix_world.copy()
        
        for face in bm.faces:
            # 将局部法向量转换为世界坐标系
            world_normal = world_matrix.to_3x3() @ face.normal
            world_normal.normalize()
            face_normals.append(world_normal.copy())
        
        print(f"  -> 记录了 {len(face_normals)} 个面的法向量")
        
        # 退出编辑模式
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # 应用变换（旋转和缩放）- 此时只有当前物体被选中
        print("  -> 应用变换...")
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        
        # 重新进入编辑模式
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        
        # 检查并恢复面的朝向
        flipped_count = 0
        
        for i, face in enumerate(bm.faces):
            if i < len(face_normals):
                current_normal = face.normal.copy()
                target_normal = face_normals[i]
                
                # 计算当前法向量与目标法向量的夹角
                dot_product = current_normal.dot(target_normal)
                
                # 如果夹角大于90度，说明面被翻转了
                if dot_product < 0:
                    # 翻转面
                    face.normal_flip()
                    flipped_count += 1
        
        print(f"  -> 翻转了 {flipped_count} 个面")
        
        # 更新网格
        bmesh.update_edit_mesh(obj.data)
        
        # 退出编辑模式
        bpy.ops.object.mode_set(mode='OBJECT')
        
        print(f"  -> 网格物体 {obj.name} 处理完成")
        
    except Exception as e:
        print(f"  -> 处理网格物体 {obj.name} 时出错: {e}")
        # 确保退出编辑模式
        if bpy.context.mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

def process_non_mesh_object(obj):
    """处理非网格物体 - 只应用变换"""
    try:
        print(f"  -> 非网格物体，只应用变换...")
        
        # 确保在物体模式
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # 应用变换（旋转和缩放）- 此时只有当前物体被选中
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        
        print(f"  -> 非网格物体 {obj.name} 变换应用完成")
        
    except Exception as e:
        print(f"  -> 处理非网格物体 {obj.name} 时出错: {e}")

def main():
    """主函数 - 直接运行脚本"""
    try:
        preserve_face_normals_and_apply_transform()
    except Exception as e:
        print(f"脚本执行出错: {e}")
        import traceback
        traceback.print_exc()

# 直接运行
if __name__ == "__main__":
    main()
