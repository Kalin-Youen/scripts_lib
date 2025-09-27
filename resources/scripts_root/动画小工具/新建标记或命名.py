# script_id: 06d5da65-e294-4180-bc7f-9e3743d4dc47
# 标记智能操作脚本（Blender 4.3+ 兼容）
# 功能：
# - 无选中标记 → 检查当前帧是否有标记 → 有则选中并重命名，无则新建标记
# - 选中1个标记 → 弹出重命名面板
# - 选中多个标记 → 自动设置帧范围（首尾帧）
# 一键运行，无需插件，自动适配上下文区域（Timeline/DopeSheet/Graph/NLA）

import bpy

scene = bpy.context.scene
current_frame = scene.frame_current

# 获取所有选中的标记
selected_markers = [m for m in scene.timeline_markers if m.select]

# 定义合法区域类型
VALID_AREA_TYPES = {'TIMELINE', 'DOPESHEET_EDITOR', 'GRAPH_EDITOR', 'NLA_EDITOR'}

def find_valid_context_override():
    context = bpy.context
    area = context.area

    if area and area.type in VALID_AREA_TYPES:
        override = context.copy()
        override['area'] = area
        override['region'] = area.regions[-1]
        return override

    for area in context.window.screen.areas:
        if area.type in VALID_AREA_TYPES:
            override = context.copy()
            override['area'] = area
            override['region'] = area.regions[-1]
            return override

    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type in VALID_AREA_TYPES:
                override = context.copy()
                override['window'] = window
                override['screen'] = window.screen
                override['area'] = area
                override['region'] = area.regions[-1]
                return override

    return None

override = find_valid_context_override()

if len(selected_markers) == 0:
    markers_at_current_frame = [m for m in scene.timeline_markers if m.frame == current_frame]
    if markers_at_current_frame:
        marker_to_select = markers_at_current_frame[0]
        marker_to_select.select = True
        selected_markers = [marker_to_select]
    else:
        if override:
            with bpy.context.temp_override(**override):
                bpy.ops.marker.add()

if len(selected_markers) == 1:
    if override:
        with bpy.context.temp_override(**override):
            bpy.ops.wm.call_panel(name="TOPBAR_PT_name_marker", keep_open=False)

elif len(selected_markers) > 1:
    frames = [m.frame for m in selected_markers]
    min_frame = min(frames)
    max_frame = max(frames)
    scene.frame_start = min_frame
    scene.frame_end = max_frame