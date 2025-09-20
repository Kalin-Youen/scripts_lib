# 关键帧/标记智能跳转脚本
# 逻辑：
# 1. 有选中关键帧 → 跳转最小帧，多选则设帧范围
# 2. 无关键帧但有选中标记 → 单标记跳转，多标记设范围并跳转
# 3. 都无 → 提示未选中

import bpy

def get_selected_keyframe_frames():
    """获取所有选中物体中被选中的关键帧帧号（全局去重）"""
    selected_frames = set()
    for obj in bpy.context.selected_objects:
        if not obj.animation_data or not obj.animation_data.action:
            continue
        action = obj.animation_data.action
        for fcurve in action.fcurves:
            for kp in fcurve.keyframe_points:
                if kp.select_control_point:
                    selected_frames.add(int(kp.co[0]))
    return selected_frames

scene = bpy.context.scene
selected_frames = get_selected_keyframe_frames()

if selected_frames:
    min_frame = min(selected_frames)
    max_frame = max(selected_frames)
    scene.frame_current = min_frame

    if len(selected_frames) > 1:
        scene.frame_start = min_frame
        scene.frame_end = max_frame

else:
    # 检查是否有选中的标记
    selected_markers = [m for m in scene.timeline_markers if m.select]
    if selected_markers:
        frames = [m.frame for m in selected_markers]
        min_frame = min(frames)
        max_frame = max(frames)
        scene.frame_current = min_frame

        if len(selected_markers) > 1:
            scene.frame_start = min_frame
            scene.frame_end = max_frame
    else:
        # 无关键帧、无标记 → 保持原提示（可选删除）
        pass  # 此处可移除 print，如需完全静音