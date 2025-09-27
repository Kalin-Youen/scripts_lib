# script_id: b65b95d4-3bea-4210-a9c2-bbffcac9f230
import bpy
import re

def clean_and_rename_selected_objects():
    """
    遍历【当前选中】的对象，将带有 '.001', '.002' 等后缀的名称
    优化为更简洁的格式。

    示例:
    '3启闭机.004'          -> '3启闭机4'
    '3启闭机_LOD0.004'      -> '3启闭机4_LOD0'
    '3启闭机_LOD1.004'      -> '3启闭机4_LOD1'
    '3启闭机_LOD2.004'      -> '3启闭机4_LOD2'
    """
    
    print("--- 开始批量重命名选中的对象 ---")
    
    # ❗❗❗ **核心改动点** ❗❗❗
    # 获取【当前选中的】对象，而不是场景中的所有对象
    selected_objects = bpy.context.selected_objects
    
    if not selected_objects:
        print("没有选中任何对象，操作已取消。")
        return

    renamed_count = 0

    # 正则表达式保持不变，因为它完美地处理了名称匹配
    pattern = re.compile(r"^(.*?)((?:_LOD\d+)*)(\.\d{3,})$")

    # 遍历选中的对象列表
    for obj in selected_objects:
        original_name = obj.name
        
        match = pattern.match(original_name)
        
        if match:
            base_name = match.group(1)
            lod_part = match.group(2)
            suffix_part = match.group(3)

            number = int(suffix_part[1:])
            
            # 拼接成新的名称
            new_name = f"{base_name}{number}{lod_part}"
            
            try:
                # 执行重命名
                obj.name = new_name
                print(f"成功: '{original_name}' -> '{new_name}'")
                renamed_count += 1
            except Exception as e:
                print(f"失败: 无法将 '{original_name}' 重命名为 '{new_name}'。可能名称已存在。错误: {e}")

    print(f"--- 操作完成 ---")
    if renamed_count > 0:
        print(f"总共重命名了 {renamed_count} 个对象。")
    else:
        print("在选中的对象中没有找到符合命名规则的项。")

# --- 脚本主入口 ---
if __name__ == "__main__":
    clean_and_rename_selected_objects()
