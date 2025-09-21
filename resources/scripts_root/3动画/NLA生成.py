# -*- coding: utf-8 -*-
# ──────────────────────────────────────────────────────────
#   智能 NLA 切片工具 (整合版) - v1.0
#   自动为选中物体的常规动画和形态键动画创建 NLA 片段
# ──────────────────────────────────────────────────────────
import bpy

# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
# ------------------------- 可调参数 -------------------------

# 在这里定义你的动画片段，它将同时用于常规动画和形态键动画
# 格式： "片段名称": (起始帧, 结束帧)
ANIMATION_CLIPS = {
    "第3天正常活动":    (1, 100),

    
    
    
    # 在这里添加更多动画片段...
}

# -------------------------------------------------------------
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲


def process_nla_for_animation_data(anim_data, clip_definitions, owner_name, anim_type="常规"):
    """
    一个通用的处理函数，用于为任何类型的动画数据创建 NLA 片段。
    :param anim_data: 动画数据 (例如 obj.animation_data 或 obj.data.shape_keys.animation_data)
    :param clip_definitions: 包含片段名称和帧范围的字典
    :param owner_name: 物体名称，用于打印日志
    :param anim_type: 动画类型字符串 ("常规" 或 "形态键")，用于打印日志
    """
    if not anim_data or not anim_data.action:
        return False

    print(f"  - 正在处理 '{owner_name}' 的【{anim_type}动画】...")
    source_action = anim_data.action

    # 1. 清空现有的 NLA 轨道
    if anim_data.nla_tracks:
        for i in reversed(range(len(anim_data.nla_tracks))):
            anim_data.nla_tracks.remove(anim_data.nla_tracks[i])
    
    # 2. 按顺序创建 NLA 片段
    sorted_clips = sorted(clip_definitions.items(), key=lambda item: item[1][0])
    
    for clip_name, (start_frame, end_frame) in sorted_clips:
        new_track = anim_data.nla_tracks.new()
        new_track.name = clip_name

        new_strip = new_track.strips.new(name=clip_name, start=start_frame, action=source_action)
        
        # 3. 配置片段属性
        new_strip.action_frame_start = start_frame
        new_strip.action_frame_end = end_frame
        new_strip.frame_end = new_strip.frame_start + (end_frame - start_frame)
        new_strip.extrapolation = 'NOTHING'
        
        print(f"    ✓ 已创建【{anim_type}】片段: '{clip_name}' (帧 {start_frame}-{end_frame})")

    # 4. 从激活槽中移除源动作
    anim_data.action = None
    return True


def intelligent_nla_slicer():
    """
    主函数：智能地为选中物体创建 NLA 片段
    """
    sel_objs = bpy.context.selected_objects
    if not sel_objs:
        print("!! 错误: 请先选中一个或多个带有动画的物体。")
        bpy.context.window_manager.popup_menu(
            lambda self, context: self.layout.label(text="请先选择物体！"), 
            title="操作失败", icon='ERROR'
        )
        return {'CANCELLED'}

    if not ANIMATION_CLIPS:
        print("!! 错误: `ANIMATION_CLIPS` 为空，请先定义要切分的动画片段。")
        bpy.context.window_manager.popup_menu(
            lambda self, context: self.layout.label(text="请先定义动画片段！"), 
            title="操作失败", icon='ERROR'
        )
        return {'CANCELLED'}

    total_processed_count = 0
    print("\n" + "="*50)
    print("      开始智能 NLA 切片处理...")
    print("="*50)

    for obj in sel_objs:
        print(f"\n正在检查物体: '{obj.name}'")
        
        processed_regular = False
        processed_shapekey = False

        # --- 第一步: 处理常规动画 (物体变换、骨骼等) ---
        if obj.animation_data:
            processed_regular = process_nla_for_animation_data(
                obj.animation_data,
                ANIMATION_CLIPS,
                obj.name,
                "常规"
            )

        # --- 第二步: 处理形态键动画 ---
        if obj.type == 'MESH' and obj.data.shape_keys:
            processed_shapekey = process_nla_for_animation_data(
                obj.data.shape_keys.animation_data,
                ANIMATION_CLIPS,
                obj.name,
                "形态键"
            )

        # --- 报告结果 ---
        if processed_regular or processed_shapekey:
            total_processed_count += 1
        else:
            print("  -> 未发现可处理的动画数据。")
            
    # --- 最终总结 ---
    print("\n" + "="*50)
    if total_processed_count > 0:
        print(f"✅ 操作完成！成功为 {total_processed_count} 个物体创建了 NLA 片段。")
    else:
        print("- 操作结束，没有在选中的物体中找到可处理的动画。")
    print("="*50 + "\n")
        
    return {'FINISHED'}


# --- 运行脚本 ---
if __name__ == "__main__":
    intelligent_nla_slicer()
