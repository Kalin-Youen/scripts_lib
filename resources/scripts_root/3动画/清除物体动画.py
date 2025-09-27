# script_id: 72836481-1dd5-4ccc-8f56-eec730bde35e
# script_id: 2ea4a1e3-ca38-4cb1-9013-a2c522532aa5
# script_id: 72836481-1dd5-4ccc-8f56-eec730bde35e
# script_id: 2ea4a1e3-ca38-4cb1-9013-a2c522532aa5
# script_id: d3babd11-c3da-4351-ba15-38bc8f91ae3e
# script_id: 72836481-1dd5-4ccc-8f56-eec730bde35e
# script_id: 2ea4a1e3-ca38-4cb1-9013-a2c522532aa5
# script_id: 72836481-1dd5-4ccc-8f56-eec730bde35e
# script_id: 2ea4a1e3-ca38-4cb1-9013-a2c522532aa5
# -*- coding: utf-8 -*-
#
#  脚本: 清除所选物体的物体动画 (不影响形态键动画)
#
import bpy

def clear_object_animation_only():
    """
    遍历所有选中的物体，并清除它们的物体级别动画数据
    (位移, 旋转, 缩放等)，但保留形态键动画。
    """
    print("✨ 开始清除所选物体的物体动画...")
    
    # 获取所有当前选中的物体
    selected_objects = bpy.context.selected_objects
    
    if not selected_objects:
        print("信息: 没有选中任何物体。")
        return

    cleared_count = 0
    
    # 遍历每一个选中的物体
    for obj in selected_objects:
        # 检查物体自身是否有动画数据
        # obj.animation_data 存储的是物体变换动画
        # obj.data.shape_keys.animation_data 存储的是形态键动画
        # 我们只处理前者。
        if obj.animation_data:
            
            # animation_data_clear() 是一个高层级的安全方法，
            # 它会移除Action、NLA轨道、驱动等，但只作用于这个数据块。
            obj.animation_data_clear()
            
            print(f"  ✔ 已清除 '{obj.name}' 的物体动画。")
            cleared_count += 1
        else:
            print(f"  - '{obj.name}' 本身没有物体动画，已跳过。")
            
    print("-" * 40)
    if cleared_count > 0:
        print(f"操作完成！成功清除了 {cleared_count} 个物体的物体动画。")
    else:
        print("操作完成，选中的物体均无物体动画可清除。")
    print("形态键动画（如果存在）已被完好保留。")
    print("-" * 40)

# --- 脚本执行入口 ---
if __name__ == "__main__":
    # 确保我们在对象模式下执行，以避免潜在的上下文错误
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
        
    clear_object_animation_only()
