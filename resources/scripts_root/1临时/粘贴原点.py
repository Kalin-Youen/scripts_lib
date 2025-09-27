# script_id: 60ee14dc-74eb-4d47-90c6-f55d68f74bb5
import bpy
import json
import mathutils
from mathutils import Vector

def get_all_mesh_descendants(parent):
    """递归收集所有网格子孙对象"""
    descendants = []

    def recurse(child):
        for obj in child.children:
            if obj.type == 'MESH':
                descendants.append(obj)
            recurse(obj)

    recurse(parent)
    return descendants

def compute_world_bounding_box_center(objects):
    """计算一组对象的世界空间包围盒中心"""
    if not objects:
        return mathutils.Vector((0, 0, 0))

    min_co = mathutils.Vector((float('inf'),) * 3)
    max_co = mathutils.Vector((float('-inf'),) * 3)

    for obj in objects:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            min_co = mathutils.Vector(tuple(min(a, b) for a, b in zip(min_co, world_corner)))
            max_co = mathutils.Vector(tuple(max(a, b) for a, b in zip(max_co, world_corner)))

    return (min_co + max_co) / 2

def process_empty_object(empty_obj, target_location):
    """处理空物体：移动到目标位置，保持子物体世界位置不变"""
    # 1. 获取所有直接子对象
    direct_children = [child for child in empty_obj.children]
    
    if not direct_children:
        # 如果没有子对象，直接移动空物体
        empty_obj.matrix_world.translation = target_location
        return
    
    # 2. 保存子对象的当前世界矩阵
    child_world_matrices = {child: child.matrix_world.copy() for child in direct_children}
    
    # 3. 解除父子关系
    for child in direct_children:
        child.parent = None
        child.matrix_world = child_world_matrices[child]
    
    # 4. 移动空物体到目标位置
    empty_obj.matrix_world.translation = target_location
    
    # 5. 重新设置父子关系并保持世界变换
    for child in direct_children:
        child.parent = empty_obj
        child.matrix_parent_inverse = empty_obj.matrix_world.inverted()
    
    print(f"✅ 已将空物体 {empty_obj.name} 移动到目标位置")

def process_mesh_object(mesh_obj, target_location):
    """处理网格物体：设置原点到目标位置"""
    # 保存当前3D游标位置
    original_cursor_location = bpy.context.scene.cursor.location.copy()
    
    # 设置3D游标到目标位置
    bpy.context.scene.cursor.location = target_location
    
    # 选中物体并设置原点到游标
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
    
    # 恢复3D游标位置
    bpy.context.scene.cursor.location = original_cursor_location
    
    print(f"✅ 已设置网格 {mesh_obj.name} 的原点位置")

def paste_origins_from_clipboard():
    """
    从剪切板粘贴原点位置到所选物体
    根据物体类型选择不同的处理方式
    """
    # 获取剪切板内容
    clipboard_content = bpy.context.window_manager.clipboard
    
    try:
        origins_data = json.loads(clipboard_content)
    except json.JSONDecodeError:
        print("❌ 剪切板中没有有效的原点数据！")
        return
    
    selected_objects = bpy.context.selected_objects
    
    if not selected_objects:
        print("❌ 没有选中任何物体！")
        return
    
    # 特殊情况：单对单
    if len(origins_data) == 1 and len(selected_objects) == 1:
        origin_info = list(origins_data.values())[0]
        obj = selected_objects[0]
        target_location = Vector(origin_info['location'])
        
        print(f"🔄 单对单模式：处理 {obj.name} ({obj.type})")
        
        if obj.type == 'EMPTY':
            process_empty_object(obj, target_location)
        else:
            process_mesh_object(obj, target_location)
    
    else:
        # 正常模式：按名称匹配
        success_count = 0
        
        for obj in selected_objects:
            if obj.name in origins_data:
                origin_info = origins_data[obj.name]
                target_location = Vector(origin_info['location'])
                
                # 根据物体类型选择处理方式
                if obj.type == 'EMPTY':
                    process_empty_object(obj, target_location)
                else:
                    process_mesh_object(obj, target_location)
                
                success_count += 1
            else:
                print(f"⚠️ 未找到 {obj.name} 的原点数据，跳过")
        
        if success_count > 0:
            print(f"\n📊 总计：成功处理 {success_count}/{len(selected_objects)} 个物体")
        else:
            print("❌ 没有匹配的物体名称")
    
    # 恢复原始选择
    bpy.ops.object.select_all(action='DESELECT')
    for obj in selected_objects:
        obj.select_set(True)
    
    print("✨ 操作完成")

# 执行脚本
paste_origins_from_clipboard()
