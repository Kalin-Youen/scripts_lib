# Blender 4.x 脚本
# 功能：为选中的所有物体，在子级中心创建一个新的父级。
#      父级的名称基于活动物体的名称（并移除_LODx后缀）。
#      如果所选物体原本有父级，新空物体会成为原父级的子级。


import bpy
import re
from mathutils import Vector

import bpy
import mathutils

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

def process_parent_empty(parent_empty):
    # 1. 获取所有直接子对象
    direct_children = [child for child in parent_empty.children]

    if not direct_children:
        return

    # 2. 收集所有网格子孙
    mesh_descendants = get_all_mesh_descendants(parent_empty)
    new_center_world = compute_world_bounding_box_center(mesh_descendants)

    # 3. 保存子对象的当前世界矩阵
    child_world_matrices = {child: child.matrix_world.copy() for child in direct_children}

    # 4. 解除父子关系（非 bpy.ops）
    for child in direct_children:
        child.parent = None
        # Blender 会自动保持 world matrix，但我们可以显式设置以确保
        child.matrix_world = child_world_matrices[child]

    # 5. 移动父级空物体到新中心
    parent_empty.matrix_world.translation = new_center_world

    # 6. 重新设置父子关系并保持世界变换
    for child in direct_children:
        child.parent = parent_empty
        # 设置 matrix_parent_inverse 以保持世界变换
        child.matrix_parent_inverse = parent_empty.matrix_world.inverted()

# 主函数
def main():
    processed_parents = set()
    selected_objects = bpy.context.selected_objects

    # 1. 收集所有符合条件的父级空物体
    for obj in selected_objects:
        if obj.parent and obj.parent.type == 'EMPTY':
            processed_parents.add(obj.parent)

    # 2. 处理每个父级空物体
    for parent_empty in processed_parents:
        process_parent_empty(parent_empty)



def compute_objects_bounding_box_center(objects):
    """计算一组对象的世界空间包围盒中心"""
    if not objects:
        return Vector((0, 0, 0))

    # 初始化边界值
    min_co = Vector((float('inf'), float('inf'), float('inf')))
    max_co = Vector((float('-inf'), float('-inf'), float('-inf')))

    for obj in objects:
        # 检查对象是否有效
        if not obj or not hasattr(obj, 'bound_box'):
            continue
            
        # 计算对象的世界空间包围盒
        world_matrix = obj.matrix_world
        for corner in obj.bound_box:
            world_corner = world_matrix @ Vector(corner)
            
            # 更新边界值
            for i in range(3):
                min_co[i] = min(min_co[i], world_corner[i])
                max_co[i] = max(max_co[i], world_corner[i])

    # 检查是否找到了有效的边界
    if min_co.x == float('inf'):
        return Vector((0, 0, 0))
    
    return (min_co + max_co) * 0.5

def determine_target_parent(objects, active_object):
    """
    确定新空物体应该使用的父级
    逻辑：
    1. 如果所有物体都有相同父级，使用该父级
    2. 如果有多个不同父级，使用活动物体的父级
    3. 如果活动物体没有父级，返回None
    """
    if not objects:
        return None, "无物体"
    
    # 收集所有不同的父级
    parents = set()
    for obj in objects:
        parents.add(obj.parent)
    
    # 如果所有对象都有同一个父级（包括都没有父级的情况）
    if len(parents) == 1:
        parent = parents.pop()
        if parent:
            return parent, f"所有物体共享父级: {parent.name}"
        else:
            return None, "所有物体都没有父级"
    else:
        # 有多个不同父级，使用活动物体的父级
        active_parent = active_object.parent if active_object else None
        if active_parent:
            return active_parent, f"多个不同父级，使用活动物体的父级: {active_parent.name}"
        else:
            return None, "多个不同父级，但活动物体没有父级"

def create_parent_at_center():
    """
    为选中物体在其中心创建一个新的父级，
    并根据活动物体的名字智能命名。
    如果所选物体有共同父级，新空物体会成为该父级的子级。
    """
    context = bpy.context
    
    # 步骤一：检查前置条件
    selected_objects = list(context.selected_objects)
    active_object = context.active_object

    if not selected_objects:
        print("错误：请至少选择一个物体。")
        return {'CANCELLED'}

    print(f"开始为 {len(selected_objects)} 个物体创建父级...")

    # 步骤二：计算所选物体的包围盒中心
    center_location = compute_objects_bounding_box_center(selected_objects)
    print(f"计算出的中心位置: ({center_location.x:.3f}, {center_location.y:.3f}, {center_location.z:.3f})")

    # 步骤三：确定目标父级
    target_parent, parent_info = determine_target_parent(selected_objects, active_object)
    print(f"父级策略: {parent_info}")

    # 步骤四：智能生成父级名称
    base_name = active_object.name if active_object else "Object"
    cleaned_name = re.sub(r'_LOD\d+$', '', base_name, flags=re.IGNORECASE)
    
    if not cleaned_name:
        cleaned_name = "Parent_Group"
    
    print(f"基于 '{base_name}' 生成父级名称: '{cleaned_name}'")

    # 步骤五：先清除选择，避免影响空物体创建
    bpy.ops.object.select_all(action='DESELECT')

    # 步骤六：在计算出的中心位置创建新的父级（空物体）
    bpy.ops.object.empty_add(
        type='PLAIN_AXES',
        align='WORLD',
        location=center_location,
        scale=(1, 1, 1)
    )

    # 新创建的空物体现在是唯一的活动对象
    new_parent = context.active_object
    new_parent.name = cleaned_name

    # 步骤七：如果有目标父级，让新空物体成为该父级的子级
    if target_parent:
        print(f"将新空物体 '{cleaned_name}' 设为 '{target_parent.name}' 的子级")
        new_parent.parent = target_parent
        new_parent.parent_type = 'OBJECT'

    # 步骤八：保存所选物体的世界变换矩阵
    world_matrices = {}
    for obj in selected_objects:
        world_matrices[obj] = obj.matrix_world.copy()

    # 步骤九：建立父子关系并保持变换
    # 1. 重新选择原来选中的物体
    for obj in selected_objects:
        obj.select_set(True)
    
    # 2. 确保新的父级是"活动"对象
    context.view_layer.objects.active = new_parent

    # 3. 执行父子化操作
    bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
    
    # 步骤十：验证并修正变换（以防万一）
    for obj in selected_objects:
        if obj.parent == new_parent:
            # 确保世界变换保持不变
            obj.matrix_world = world_matrices[obj]

    # 步骤十一：完成并汇报
    parent_info_suffix = f" (作为 '{target_parent.name}' 的子级)" if target_parent else ""
    print(f"成功！已为 {len(selected_objects)} 个物体创建了父级 '{cleaned_name}'{parent_info_suffix}。")
    
    # 更新场景
    context.view_layer.update()
    
    return {'FINISHED'}


# --- 脚本入口 ---
if __name__ == "__main__":

    
    create_parent_at_center()
    main()
