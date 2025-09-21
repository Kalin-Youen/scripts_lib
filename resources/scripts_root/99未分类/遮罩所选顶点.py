import bpy
import bmesh
import re

def add_mask_modifier_with_vertex_group():
    # 获取活动对象并检查是否为网格
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        raise Exception("请选择网格对象")

    # 保存当前模式
    original_mode = obj.mode
    
    # 进入编辑模式获取选中的顶点
    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
    
    # 使用 bmesh 获取选中的顶点索引
    bm = bmesh.from_edit_mesh(obj.data)
    selected_verts = [v.index for v in bm.verts if v.select]
    bm.free()
    
    # 没有选中顶点时提示
    if not selected_verts:
        bpy.ops.object.mode_set(mode=original_mode)
        raise Exception("未选中任何顶点")
    
    # 返回对象模式
    bpy.ops.object.mode_set(mode='OBJECT')

    # 生成自动递增的顶点组名称
    existing_groups = obj.vertex_groups
    max_num = 0
    pattern = re.compile(r"^mask_(\d+)$")
    
    for group in existing_groups:
        match = pattern.match(group.name)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)
    
    new_group_name = f"mask_{max_num + 1}"

    # 创建新顶点组并分配顶点
    vertex_group = obj.vertex_groups.new(name=new_group_name)
    for index in selected_verts:
        vertex_group.add([index], 1.0, 'REPLACE')

    # 添加遮罩修改器并设置反转
    mask_mod = obj.modifiers.new(name="Mask", type='MASK')
    mask_mod.vertex_group = new_group_name
    mask_mod.invert_vertex_group = True

    # 恢复原始模式
    bpy.ops.object.mode_set(mode=original_mode)
    print(f"已创建顶点组 '{new_group_name}' 并添加反转遮罩修改器")

# 执行函数
add_mask_modifier_with_vertex_group()