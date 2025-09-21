import bpy

def add_copy_transform_constraints():
    """为选中骨架添加复制变换约束"""
    
    # 检查是否选中了骨架
    obj = bpy.context.active_object
    if not obj or obj.type != 'ARMATURE':
        print("错误：请先选择一个骨架对象！")
        return
    
    print(f"开始为骨架 '{obj.name}' 添加约束...")
    
    # 骨骼约束映射字典 - 格式：{目标骨骼: 源骨骼}
    # 目标骨骼将复制源骨骼的变换
    constraint_mapping = {
        "foot.r": "foot_ik.r",
        "foot.l": "foot_ik.l", 
        "leg_fk.r": "leg_ik.r",
        "leg_fk.l": "leg_ik.l",
        "foot_dupli_001.l": "foot_ik_dupli_001.l",
        "foot_dupli_001.r": "foot_ik_dupli_001.r",
        "leg_fk_dupli_001.l": "leg_ik_dupli_001.l",
        "leg_fk_dupli_001.r": "leg_ik_dupli_001.r"
    }
    
    # 保存当前模式
    original_mode = obj.mode
    
    # 切换到姿势模式
    bpy.ops.object.mode_set(mode='POSE')
    
    # 统计信息
    success_count = 0
    error_count = 0
    errors = []
    
    # 遍历约束映射
    for target_bone_name, source_bone_name in constraint_mapping.items():
        try:
            # 检查目标骨骼是否存在
            if target_bone_name not in obj.pose.bones:
                error_msg = f"目标骨骼 '{target_bone_name}' 不存在"
                errors.append(error_msg)
                error_count += 1
                continue
            
            # 检查源骨骼是否存在
            if source_bone_name not in obj.pose.bones:
                error_msg = f"源骨骼 '{source_bone_name}' 不存在"
                errors.append(error_msg)
                error_count += 1
                continue
            
            # 获取目标骨骼
            target_bone = obj.pose.bones[target_bone_name]
            
            # 检查是否已经存在同名的复制变换约束
            existing_constraint = None
            for constraint in target_bone.constraints:
                if constraint.type == 'COPY_TRANSFORMS' and constraint.target == obj and constraint.subtarget == source_bone_name:
                    existing_constraint = constraint
                    break
            
            if existing_constraint:
                print(f"约束已存在：{target_bone_name} -> {source_bone_name}")
                continue
            
            # 添加复制变换约束
            constraint = target_bone.constraints.new(type='COPY_TRANSFORMS')
            constraint.name = f"Copy_{source_bone_name}"
            constraint.target = obj  # 目标对象是同一个骨架
            constraint.subtarget = source_bone_name  # 源骨骼名称
            
            # 设置约束属性（可根据需要调整）
            constraint.mix_mode = 'REPLACE'  # 替换模式
            constraint.target_space = 'POSE'  # 目标空间
            constraint.owner_space = 'POSE'   # 拥有者空间
            
            print(f"✓ 成功添加约束：{target_bone_name} -> {source_bone_name}")
            success_count += 1
            
        except Exception as e:
            error_msg = f"处理 {target_bone_name} -> {source_bone_name} 时出错：{str(e)}"
            errors.append(error_msg)
            error_count += 1
    
    # 回到原始模式
    bpy.ops.object.mode_set(mode=original_mode)
    
    # 打印结果
    print("=" * 60)
    print(f"约束添加完成！")
    print(f"成功添加: {success_count} 个约束")
    print(f"失败: {error_count} 个约束")
    
    if errors:
        print("\n错误详情:")
        for error in errors:
            print(f"  ✗ {error}")
    
    print("=" * 60)

def remove_copy_transform_constraints():
    """移除指定的复制变换约束"""
    
    # 检查是否选中了骨架
    obj = bpy.context.active_object
    if not obj or obj.type != 'ARMATURE':
        print("错误：请先选择一个骨架对象！")
        return
    
    # 骨骼约束映射字典（与添加时相同）
    constraint_mapping = {
        "foot.r": "foot_ik.r",
        "foot.l": "foot_ik.l", 
        "leg_fk.r": "leg_ik.r",
        "leg_fk.l": "leg_ik.l",
        "foot_dupli_001.l": "foot_ik_dupli_001.l",
        "foot_dupli_001.r": "foot_ik_dupli_001.r",
        "leg_fk_dupli_001.l": "leg_ik_dupli_001.l",
        "leg_fk_dupli_001.r": "leg_ik_dupli_001.r"
    }
    
    # 保存当前模式
    original_mode = obj.mode
    
    # 切换到姿势模式
    bpy.ops.object.mode_set(mode='POSE')
    
    removed_count = 0
    
    # 遍历约束映射
    for target_bone_name, source_bone_name in constraint_mapping.items():
        if target_bone_name in obj.pose.bones:
            target_bone = obj.pose.bones[target_bone_name]
            
            # 查找并移除相关约束
            constraints_to_remove = []
            for constraint in target_bone.constraints:
                if (constraint.type == 'COPY_TRANSFORMS' and 
                    constraint.target == obj and 
                    constraint.subtarget == source_bone_name):
                    constraints_to_remove.append(constraint)
            
            for constraint in constraints_to_remove:
                target_bone.constraints.remove(constraint)
                print(f"✓ 移除约束：{target_bone_name} -> {source_bone_name}")
                removed_count += 1
    
    # 回到原始模式
    bpy.ops.object.mode_set(mode=original_mode)
    
    print(f"移除了 {removed_count} 个约束")

# 主函数
if __name__ == "__main__":
    # 添加约束
    add_copy_transform_constraints()
    
    # 如果需要移除约束，取消下面这行的注释
    # remove_copy_transform_constraints()
