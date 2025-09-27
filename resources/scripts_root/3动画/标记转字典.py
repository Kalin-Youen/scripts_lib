# script_id: eef328c4-e4c1-4e15-ae05-7b5b3fcefb5e
import bpy

# 获取当前场景
scene = bpy.context.scene
markers = scene.timeline_markers

# 收集所有标记，按帧排序
sorted_markers = sorted(markers, key=lambda m: m.frame)

# 构建字典：名称 -> {start, end}
clip_dict = {}

for marker in sorted_markers:
    name = marker.name.strip()
    if len(name) > 1:  # 至少两个字符，避免单字母标记
        if name.endswith("s"):
            clip_name = name[:-1]  # 去掉末尾的 "s"
            if clip_name not in clip_dict:
                clip_dict[clip_name] = {}
            clip_dict[clip_name]['start'] = marker.frame
        elif name.endswith("e"):
            clip_name = name[:-1]  # 去掉末尾的 "e"
            if clip_name not in clip_dict:
                clip_dict[clip_name] = {}
            clip_dict[clip_name]['end'] = marker.frame

# 过滤出有完整起止的片段
valid_clips = []
for name, frames in clip_dict.items():
    if 'start' in frames and 'end' in frames:
        valid_clips.append((name, frames['start'], frames['end']))
    else:
        print(f"⚠️ 警告: 标记 '{name}' 缺少开始或结束标记，已跳过。")

# 按开始帧排序
valid_clips.sort(key=lambda x: x[1])

if not valid_clips:
    print("❌ 未找到有效的 s/e 标记对。")
else:
    # 生成 Python 字典字符串
    lines = ["ANIMATION_CLIPS = {"]
    for name, start, end in valid_clips:
        # 对齐格式，中文支持完美
        line = f'    "{name}":    ({start}, {end}),'
        lines.append(line)
    lines.append("    # 在这里添加更多动画片段...")
    lines.append("}")

    result_text = "\n".join(lines)

    # 写入剪贴板
    bpy.context.window_manager.clipboard = result_text

    print(f"✅ 已导出 {len(valid_clips)} 个动画片段到剪贴板！")
    print("\n📋 已复制内容如下：\n")
    print(result_text)