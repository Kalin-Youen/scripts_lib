# -*- coding: utf-8 -*-
# ──────────────────────────────────────────────────────────
#   Select Top-Level Parents and Set Active - v1.1
#   作者: Claude Code AI
#   功能: 仅选择所选物体对应的顶层父级，并设置其中一个为活动项。
# ──────────────────────────────────────────────────────────

import bpy

def select_top_level_parents_and_set_active():
    """
    仅选择所选物体对应的顶层父级（最高层级祖先），并设置其中一个为活动对象。
    
    脚本逻辑:
    1. 遍历当前选中的每个物体。
    2. 向上追溯至其最顶层的父级（即没有父级的祖先）。
    3. 收集所有唯一的顶层父级。
    4. 清除当前选择。
    5. 如果找到了顶层父级，则全部选中它们。
    6. [新增] 将其中一个新选中的物体设置为“活动对象”。
    """
    context = bpy.context
    if not context.selected_objects:
        print("没有选择任何物体。")
        return

    # 缓存视图层中的对象集合，用于快速判断是否可见
    view_layer_objects = set(context.view_layer.objects)
    
    top_level_parents = set()  # 使用集合避免重复

    for obj in context.selected_objects:
        current = obj
        # 沿着父级链一直向上找，直到没有父级为止
        while current.parent:
            current = current.parent
        
        # 此时 current 就是顶层父级
        # 确保该父级在当前视图层中是可见且存在的
        if current in view_layer_objects:
            top_level_parents.add(current)

    # 在进行任何操作前，先清除当前选择
    # 这样可以避免在选择为空时依然保持旧的活动对象
    bpy.ops.object.select_all(action='DESELECT')

    # 仅当找到顶层父级时才进行选择和设置活动项的操作
    if not top_level_parents:
        print("操作完成：未在当前视图层找到任何可见的顶层父级。")
        # 确保活动对象也被清空
        context.view_layer.objects.active = None
        return

    # 选择所有找到的顶层父级
    for parent_obj in top_level_parents:
        parent_obj.select_set(True)

    # --- 新增逻辑：设置活动对象 ---
    # 通常将集合中的最后一个元素或任意一个元素设为活动对象
    # 我们将列表中的第一个设为活动对象
    active_obj = list(top_level_parents)[0]
    context.view_layer.objects.active = active_obj

    # --- 更新输出信息 ---
    print(f"操作完成：共选中 {len(top_level_parents)} 个顶层父级。")
    print(f"已将 '{active_obj.name}' 设置为活动对象。")
    print("选中的顶层父级:")
    for obj in sorted(top_level_parents, key=lambda o: o.name): # 按名称排序输出，更清晰
        print(f"  - {obj.name}")


# --- 主程序入口 ---
if __name__ == "__main__":
    select_top_level_parents_and_set_active()

