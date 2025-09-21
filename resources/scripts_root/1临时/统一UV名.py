# Blender 4.x 脚本
# 功能：将所选物体的活动UV贴图名称，统一为活动物体的活动UV贴图名称。
# 作者：一位独具风格的小说家

import bpy

def unify_active_uv_names():
    """
    统一所选物体的活动UV名称。
    """
    context = bpy.context
    active_obj = context.active_object
    selected_objs = context.selected_objects

    # --- 步骤一：前置检查，确保万无一失 ---
    if not active_obj or not selected_objs:
        print("错误：请至少选择一个物体，并确保有一个活动物体（最后选中，亮橙色轮廓）。")
        return

    # 检查活动物体是否为网格且有UV数据
    if not hasattr(active_obj.data, 'uv_layers'):
        print(f"错误：活动物体 '{active_obj.name}' 不是网格或没有UV数据，无法作为命名基准。")
        return

    # 获取活动物体的活动UV层
    active_uv_layer = active_obj.data.uv_layers.active
    if not active_uv_layer:
        print(f"错误：活动物体 '{active_obj.name}' 没有活动的UV层。请在'对象数据属性'面板中选择一个UV贴图。")
        return

    # --- 步骤二：确定目标名称并开始循环 ---
    target_name = active_uv_layer.name
    print(f"目标UV名称已确定为: '{target_name}' (来自活动物体 '{active_obj.name}')")

    processed_count = 0
    # 遍历所有选中的物体
    for obj in selected_objs:
        # <-- 从这里开始，下面的代码块属于 for 循环，必须缩进！
        if obj.type != 'MESH' or not hasattr(obj.data, 'uv_layers'):
            continue  # 跳过非网格物体或没有UV数据的物体

        # 获取当前循环中物体的活动UV层
        uv_layer_to_rename = obj.data.uv_layers.active
        
        # 如果它有活动UV层，并且名字和目标不一致，就改名
        if uv_layer_to_rename and uv_layer_to_rename.name != target_name:
            uv_layer_to_rename.name = target_name
            processed_count += 1
            print(f"  -> 已将物体 '{obj.name}' 的活动UV贴图重命名为 '{target_name}'")

    # --- 步骤三：汇报结果 ---
    print(f"\n处理完成！共统一了 {processed_count} 个物体的活动UV贴图名称。")
    if processed_count == 0:
        print("所有选中物体的活动UV名称已是最新，无需更改。")


# --- 脚本入口 ---
# 这一部分不属于上面的函数，所以不缩进
if __name__ == "__main__":
    unify_active_uv_names()

