import bpy

def clear_nla_tracks(obj):
    """
    清除物体动画数据，包括形态键的NLA轨道。
    """
    # 清除对象本身的NLA轨道
    if obj.animation_data and obj.animation_data.nla_tracks:
        for track in obj.animation_data.nla_tracks[:]:  # 使用副本避免迭代问题
            obj.animation_data.nla_tracks.remove(track)
        print(f"已成功清除 {obj.name} 的所有 NLA 轨道。")
    
    # 检查并清除对象数据（形态键）的NLA轨道
    if hasattr(obj.data, "shape_keys") and obj.data.shape_keys is not None:
        if obj.data.shape_keys.animation_data:
            for track in obj.data.shape_keys.animation_data.nla_tracks[:]:
                obj.data.shape_keys.animation_data.nla_tracks.remove(track)
            print(f"已成功清除 {obj.name} 的形态键 NLA 轨道。")
    else:
        print(f"{obj.name} 没有形态键。")

# 示例：对选定对象进行操作
for obj in bpy.context.selected_objects:
    clear_nla_tracks(obj)
