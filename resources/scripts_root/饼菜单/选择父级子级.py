# script_id: add8ce41-ffc9-4f7b-afb6-1a167a9af950
import bpy

def select_meaningful_branch():
    """
    智能选择组件层级。
    
    脚本逻辑:
    1. 从当前选择的物体开始，向上追溯其父级。
    2. 找到第一个“有意义的、可见的”父级。
    3. 将这个找到的父级（组件）及其所有后代全部选中。
    """
    context = bpy.context
    if not context.selected_objects:
        print("没有选择任何物体。")
        return

    # 缓存当前视图层的所有物体，以加速查找
    view_layer_objects = set(context.view_layer.objects)
    
    # --- 核心逻辑：找到所有需要处理的“组件根” ---
    # 使用 set 自动处理重复情况，例如同时选中了同一组件下的多个零件
    meaningful_roots = set()

    for obj in context.selected_objects:
        current = obj
        branch_root = obj # 默认情况下，如果物体没有父级，它自己就是根

        # 向上追溯，寻找那个“有意义的”根
        while current.parent:
            parent = current.parent
            
            # 判断条件：如果父级是隐藏的（无论是自身隐藏还是视图禁用），
            # 那么当前物体 `current` 就是我们能找到的“最有意义的可见根”。
            # 这个 `current` 就是我们要找的分支起点，比如 “生物机能实验室”。
            if parent.hide_get() or parent.hide_viewport:
                branch_root = current
                break # 找到了，停止向上追溯
            
            # 如果父级可见，继续向上追溯
            current = parent
            
            # 如果已经到了最顶层，那么最顶层的这个可见父级就是根
            branch_root = current
            
        meaningful_roots.add(branch_root)

    # --- 执行选择 ---
    if not meaningful_roots:
        print("未能从当前选择中确定任何有效的组件根。")
        return

    # 先清空当前所有选择，以确保结果干净、可预测
    bpy.ops.object.select_all(action='DESELECT')

    total_selected_count = 0
    for root in meaningful_roots:
        print(f"正在选择组件: '{root.name}' 及其所有子级...")
        
        # 准备要选择的物体列表：根 + 所有后代
        hierarchy_to_select = [root] + list(root.children_recursive)
        
        for obj_in_hierarchy in hierarchy_to_select:
            # 只选择在当前视图层中存在的物体
            if obj_in_hierarchy in view_layer_objects:
                obj_in_hierarchy.select_set(True)
                total_selected_count += 1
                
    print(f"\n操作完成: 共选中 {len(meaningful_roots)} 个组件，总计 {total_selected_count} 个物体。")


# --- 主程序入口 ---
if __name__ == "__main__":
    select_meaningful_branch()
