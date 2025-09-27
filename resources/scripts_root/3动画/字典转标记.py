# script_id: 16513abc-e0e1-4138-b66a-a1bde21b0b7f
import bpy
import ast
import re

# 从剪贴板读取内容
clipboard_content = bpy.context.window_manager.clipboard.strip()

if not clipboard_content:
    print("❌ 剪贴板为空！请先复制 ANIMATION_CLIPS 相关字典内容。")
else:
    # 正则匹配：ANIMATION_CLIPS[可选数字或下划线数字] = { ... }
    pattern = r'ANIMATION_CLIPS[_\d]*\s*=\s*(\{[^}]*\}|\{.*?\})'
    matches = re.findall(pattern, clipboard_content, re.DOTALL)

    if not matches:
        print("⚠️ 未找到 ANIMATION_CLIPS... = {...} 格式的内容，尝试直接解析整个剪贴板为字典...")
        matches = [clipboard_content]  # 尝试直接解析整段

    all_clips = {}

    for match in matches:
        try:
            # 安全解析字典
            d = ast.literal_eval(match.strip())
            if isinstance(d, dict):
                all_clips.update(d)  # 合并字典
                print(f"✅ 成功加载 {len(d)} 个动画片段")
            else:
                print(f"⚠️ 跳过非字典内容: {str(match)[:50]}...")
        except (SyntaxError, ValueError) as e:
            print(f"⚠️ 解析失败: {e} ← 内容: {str(match)[:50]}...")

    if not all_clips:
        print("❌ 未成功加载任何动画片段。请检查剪贴板格式。")
    else:
        scene = bpy.context.scene
        markers = scene.timeline_markers

        # 🔁 可选：清除旧的 s/e 标记（避免重复）
        # 如果你不想清除，注释掉下面这个 for 循环
        for marker in list(markers):
            name = marker.name.strip()
            if len(name) > 1 and (name.endswith('s') or name.endswith('e')):
                markers.remove(marker)
                print(f"🗑️ 已移除旧标记: {name}")

        # ✅ 创建新标记
        created_count = 0
        for clip_name, frames in all_clips.items():
            if not isinstance(frames, (tuple, list)) or len(frames) != 2:
                print(f"⚠️ 跳过无效条目: {clip_name}: {frames}")
                continue

            start_frame, end_frame = frames

            # 创建开始标记
            start_marker_name = str(clip_name) + "s"
            markers.new(name=start_marker_name, frame=start_frame)
            print(f"✅ 创建标记: {start_marker_name} @ {start_frame}")

            # 创建结束标记
            end_marker_name = str(clip_name) + "e"
            markers.new(name=end_marker_name, frame=end_frame)
            print(f"✅ 创建标记: {end_marker_name} @ {end_frame}")

            created_count += 2

        print(f"\n🎉 共创建 {created_count} 个标记！")
        print("请在时间轴（Timeline 或 Dope Sheet）中查看标记。")