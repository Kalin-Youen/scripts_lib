# script_id: 6973ba6f-b78d-46b4-aaa4-06d636f1d21f
# -*- coding: utf-8 -*-
#
#  脚本: 选择所选物体及其所有子级 (递归方法)
#
import bpy

def select_children_recursive(parent_obj):
    """
    一个递归函数，用于选中一个给定物体的所有后代 (子级、孙子级等)。
    """
    # 遍历该物体的直接子级
    for child in parent_obj.children:
        # 选中这个子级
        child.select_set(True)
        
        # 如果这个子级自己还有子级，就对它重复这个过程
        if child.children:
            select_children_recursive(child)

def select_with_descendants():
    """
    主函数：遍历当前选中的物体，并选中它们的所有后代。
    """
    print("✨ 开始选择物体及其所有子级...")
    
    # 获取当前选中的物体。
    # 关键：必须在一开始就将其转换为列表，因为在循环中 `bpy.context.selected_objects` 会动态变化。
    initial_selection = list(bpy.context.selected_objects)
    
    if not initial_selection:
        print("信息: 没有选中任何物体。")
        return

    # 遍历最初选中的每一个物体
    for obj in initial_selection:
        # 调用递归函数来选中它的所有后代
        select_children_recursive(obj)
            
    # 报告最终结果
    final_count = len(bpy.context.selected_objects)
    print(f"操作完成！总共选中了 {final_count} 个物体。")

# --- 脚本执行入口 ---
if __name__ == "__main__":
    select_with_descendants()
