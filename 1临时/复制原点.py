import bpy
import json

def copy_origins_to_clipboard():
    """
    复制所选物体的原点位置和类型到剪切板
    """
    selected_objects = bpy.context.selected_objects
    
    if not selected_objects:
        print("❌ 没有选中任何物体！")
        return
    
    # 收集原点信息
    origins_data = {}
    for obj in selected_objects:
        # 获取物体的世界坐标原点位置
        origin_world = obj.matrix_world.translation.copy()
        origins_data[obj.name] = {
            'location': [origin_world.x, origin_world.y, origin_world.z],
            'object_name': obj.name,
            'object_type': obj.type  # 记录物体类型
        }
    
    # 转换为JSON字符串
    json_data = json.dumps(origins_data, indent=2)
    
    # 复制到剪切板
    bpy.context.window_manager.clipboard = json_data
    
    print(f"✅ 已复制 {len(selected_objects)} 个物体的原点位置到剪切板")
    for name, data in origins_data.items():
        print(f"  - {name} ({data['object_type']})")
    
    return origins_data

# 执行脚本
copy_origins_to_clipboard()
