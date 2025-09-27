# script_id: 3d5f917c-aa24-4ac3-84bb-71ed701912ba
import bpy
import re

def smart_rename_follower_enhanced():
    """
    智能跟随命名脚本 (增强版):
    将选中的非活动对象的名称，改成活动对象的名称，并智能地处理序号。
    
    使用条件：
    - 必须正好选中两个对象。
    - 其中一个必须是活动对象 (active_object)。
    
    处理逻辑:
    1. 如果活动对象名称符合 '..._LOD<数字>' 格式 (如 '..._LOD0'):
       - 新名称为 '..._LOD<数字+1>' (如 '..._LOD1')
    2. 如果活动对象名称不符合该格式 (如 'MyObjectName'):
       - 新名称为 'MyObjectName1'
    """
    
    context = bpy.context
    
    # --- 步骤 1: 获取选中对象并进行安全检查 ---
    selected_objects = context.selected_objects
    active_object = context.active_object
    
    if not active_object:
        message = "错误: 没有活动对象。"
        print(message)
        bpy.context.workspace.status_text_set(message)
        return

    if len(selected_objects) != 2:
        message = f"错误: 需要正好选中2个对象，当前选中了 {len(selected_objects)} 个。"
        print(message)
        bpy.context.workspace.status_text_set(message)
        return

    # --- 步骤 2: 识别源对象和目标对象 ---
    target_object = active_object
    source_object = [obj for obj in selected_objects if obj != active_object][0]
    
    original_source_name = source_object.name
    target_name = target_object.name
    
    print(f"目标模板对象: '{target_name}'")
    print(f"要重命名的源对象: '{original_source_name}'")

    # --- 步骤 3: 【核心改动】智能解析目标名称 ---
    # 定义匹配 '_LOD<数字>' 的正则表达式
    lod_pattern = re.compile(r"^(.*_LOD)(\d+)$")
    lod_match = lod_pattern.match(target_name)
    
    base_name = ""
    new_number = 1  # 默认新序号为1

    if lod_match:
        # --- 情况1: 名称符合_LOD格式 ---
        print("检测到LOD命名格式。")
        base_name = lod_match.group(1)      # '..._LOD'
        lod_number = int(lod_match.group(2))
        new_number = lod_number + 1
        
    else:
        # --- 情况2: 名称不符合_LOD格式 ---
        print("未检测到LOD命名格式，将使用完整名称作为基础。")
        # 将完整的目标名称作为基础名称
        base_name = target_name
        # 此时新序号保持默认值 1
    
    # --- 步骤 4: 生成新名称 ---
    new_name = f"{base_name}{new_number}"
    
    # --- 步骤 5: 重命名源对象 ---
    try:
        source_object.name = new_name
        success_message = f"成功: '{original_source_name}' -> '{new_name}'"
        print(success_message)
        bpy.context.workspace.status_text_set(success_message)
    except Exception as e:
        error_message = f"失败: 无法重命名为 '{new_name}'。可能名称已存在。错误: {e}"
        print(error_message)
        bpy.context.workspace.status_text_set(error_message)


# --- 脚本主入口 ---
if __name__ == "__main__":
    smart_rename_follower_enhanced()

