# script_id: 6cf4dd84-697d-4271-9beb-af9ac6f09fc9
import bpy
import re

def extract_lod_info(name):
    """
    从物体名称中提取基础名称和LOD级别
    返回: (base_name, lod_number)
    例如: "Cube_LOD1" -> ("Cube", 1)
         "Tree" -> ("Tree", 0)  # 默认为LOD0
    """
    # 使用正则表达式匹配 _LOD 后跟数字的模式
    match = re.search(r'(.+?)_LOD(\d+)$', name, re.IGNORECASE)
    if match:
        base_name = match.group(1)
        lod_number = int(match.group(2))
        return base_name, lod_number
    else:
        # 如果没有LOD后缀，默认为LOD0
        return name, 0

def apply_all_modifiers(obj):
    """安全地应用物体的所有修改器"""
    if not obj.modifiers:
        return True
    
    # 确保物体是活动的并且被选中
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # 逐个应用修改器（从前往后）
    modifier_names = [mod.name for mod in obj.modifiers]
    
    success_count = 0
    for mod_name in modifier_names:
        try:
            # 检查修改器是否仍然存在
            if mod_name in obj.modifiers:
                bpy.ops.object.modifier_apply(modifier=mod_name)
                print(f"    ✓ 已应用修改器: '{mod_name}'")
                success_count += 1
        except Exception as e:
            print(f"    ✗ 应用修改器 '{mod_name}' 失败: {e}")
    
    return success_count > 0

def remove_all_modifiers(obj):
    """安全地删除物体的所有修改器"""
    if not obj.modifiers:
        return
    
    removed_count = 0
    # 从后往前删除，避免索引问题
    for modifier in reversed(obj.modifiers):
        modifier_name = modifier.name
        obj.modifiers.remove(modifier)
        print(f"    ✓ 已删除修改器: '{modifier_name}'")
        removed_count += 1
    
    print(f"    总共删除了 {removed_count} 个修改器")

# === 主要逻辑 ===

# 获取当前选中的所有物体（创建列表副本避免迭代时修改）
selected_objects = list(bpy.context.selected_objects)

# 检查是否有选中的物体
if not selected_objects:
    print("❌ 错误：没有选中任何物体。")
else:
    processed_count = 0
    
    print(f"📋 开始处理 {len(selected_objects)} 个选中的物体...")
    print("=" * 50)
    
    # 遍历每个选中的物体
    for original_obj in selected_objects:
        # 检查物体是否有任何修改器
        if not original_obj.modifiers:
            print(f"⏭️  物体 '{original_obj.name}' 没有修改器，跳过处理。")
            continue
        
        # 解析物体名称，获取基础名称和当前LOD级别
        base_name, current_lod = extract_lod_info(original_obj.name)
        next_lod = current_lod + 1
        
        print(f"🔧 处理物体: '{original_obj.name}'")
        print(f"   基础名称: '{base_name}', 当前LOD: {current_lod}, 下一级LOD: {next_lod}")

        # --- 步骤 1: 复制物体 ---
        bpy.ops.object.select_all(action='DESELECT')
        original_obj.select_set(True)
        bpy.context.view_layer.objects.active = original_obj
        
        # 复制物体
        bpy.ops.object.duplicate_move()
        
        # 获取复制出来的物体
        copied_obj = None
        for obj in bpy.context.selected_objects:
            if obj != original_obj:
                copied_obj = obj
                break
        
        if copied_obj is None:
            print(f"  ❌ 错误: 无法获取 '{original_obj.name}' 的副本。")
            continue
        
        # --- 步骤 2: 处理复制的物体（下一级LOD - 应用修改器）---
        bpy.ops.object.select_all(action='DESELECT')
        copied_obj.select_set(True)
        bpy.context.view_layer.objects.active = copied_obj
        
        # 先重命名复制的物体
        copied_obj.name = f"{base_name}_LOD{next_lod}"
        
        print(f"  📦 处理 {copied_obj.name} (应用修改器):")
        #if apply_all_modifiers(copied_obj):
        #    print(f"  ✅ 成功创建: '{copied_obj.name}' (已应用修改器)")
        #else:
        #    print(f"  ⚠️  警告: '{copied_obj.name}' 修改器应用可能有问题")

        # --- 步骤 3: 处理原始物体（当前LOD - 删除修改器）---
        bpy.ops.object.select_all(action='DESELECT')
        original_obj.select_set(True)
        bpy.context.view_layer.objects.active = original_obj
        
        # 重命名原始物体（确保有正确的LOD后缀）
        original_obj.name = f"{base_name}_LOD{current_lod}"
        
        print(f"  📦 处理 {original_obj.name} (删除修改器):")
        #remove_all_modifiers(original_obj)
        print(f"  ✅ 成功处理: '{original_obj.name}' (已删除修改器)")
        
        processed_count += 1
        print()  # 空行分隔

    print("=" * 50)
    print(f"🎉 处理完成！总共处理了 {processed_count} 个有修改器的物体。")
    
    if processed_count > 0:
        print("\n📝 总结:")
        print("   • 原始物体：保留当前LOD级别，删除所有修改器")
        print("   • 复制物体：升级到下一LOD级别，应用所有修改器")
