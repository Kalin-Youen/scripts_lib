import bpy

def unlock_and_show_all_bones():
    """解锁并显示所选骨架的全部骨骼"""
    
    # 检查是否选中了骨架
    obj = bpy.context.active_object
    if not obj or obj.type != 'ARMATURE':
        print("错误：请先选择一个骨架对象！")
        return
    
    print(f"开始处理骨架: {obj.name}")
    
    # 保存当前模式
    original_mode = obj.mode
    
    # 1. 处理骨骼可见性（根据Blender版本）
    armature = obj.data
    
    # 检查Blender版本
    if bpy.app.version >= (4, 0, 0):
        # Blender 4.0+ 使用骨骼集合
        print("显示所有骨骼集合...")
        if hasattr(armature, 'collections'):
            for collection in armature.collections:
                collection.is_visible = True
    elif bpy.app.version >= (3, 0, 0):
        # Blender 3.0+ 可能没有layers属性
        print("Blender 3.x 版本，跳过层设置...")
    else:
        # 旧版本使用layers
        print("显示所有骨骼层...")
        if hasattr(armature, 'layers'):
            for i in range(32):
                armature.layers[i] = True
    
    # 2. 进入姿势模式处理骨骼锁定状态
    bpy.ops.object.mode_set(mode='POSE')
    
    # 统计信息
    unlocked_count = 0
    
    # 3. 遍历所有姿势骨骼并解锁
    for pbone in obj.pose.bones:
        # 显示骨骼（确保骨骼不被隐藏）
        pbone.bone.hide = False
        
        # 解锁位置
        if any(pbone.lock_location):
            pbone.lock_location = (False, False, False)
            unlocked_count += 1
            
        # 解锁旋转
        if any(pbone.lock_rotation):
            pbone.lock_rotation = (False, False, False)
            unlocked_count += 1
            
        # 解锁四元数旋转
        if pbone.lock_rotation_w:
            pbone.lock_rotation_w = False
            unlocked_count += 1
            
        # 解锁缩放
        if any(pbone.lock_scale):
            pbone.lock_scale = (False, False, False)
            unlocked_count += 1
    
    # 4. 在编辑模式下确保所有骨骼可见
    bpy.ops.object.mode_set(mode='EDIT')
    
    hidden_bones_count = 0
    for ebone in armature.edit_bones:
        if ebone.hide:
            ebone.hide = False
            hidden_bones_count += 1
        # 确保骨骼在所有视图中可见
        ebone.hide_select = False
    
    # 5. 回到原始模式
    bpy.ops.object.mode_set(mode=original_mode)
    
    # 6. 刷新视图
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()
    
    # 打印结果
    print("=" * 50)
    print(f"处理完成！")
    print(f"Blender版本: {bpy.app.version_string}")
    print(f"解锁的骨骼属性: {unlocked_count}")
    print(f"显示的隐藏骨骼: {hidden_bones_count}")
    print(f"总骨骼数: {len(armature.bones)}")
    print("=" * 50)

# 直接执行
if __name__ == "__main__":
    unlock_and_show_all_bones()
