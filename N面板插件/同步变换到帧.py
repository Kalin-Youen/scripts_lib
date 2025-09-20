import bpy
from bpy.types import Operator, Panel
from typing import Dict, Tuple, Set, Optional, List

# === 全局存储 ===
# 存储结构：{ obj_name: ( { frame: (loc, rot, sca) }, 选中的帧集合 ) }
_recorded_data: Dict[str, Tuple[Dict[int, Tuple], Set[int]]] = {}

# === 辅助函数 ===
def get_selected_keyframes(obj) -> Set[int]:
    """获取物体所有动画数据中被选中的关键帧帧号（去重）"""
    selected_frames = set()
    if not obj.animation_data or not obj.animation_data.action:
        return selected_frames
    for fcurve in obj.animation_data.action.fcurves:
        for kp in fcurve.keyframe_points:
            if kp.select_control_point:
                selected_frames.add(int(kp.co[0]))
    return selected_frames

def get_full_transform_at_frame_from_fcurves(obj, frame: int) -> Optional[Tuple]:
    """从 fcurve 读取指定帧的 loc/rot/sca 值（关键帧真实值）"""
    if not obj.animation_data or not obj.animation_data.action:
        return None
    loc, rot, sca = [0.0] * 3, [0.0] * 3, [1.0] * 3
    found_any = False
    for axis, default in [("location", loc), ("rotation_euler", rot), ("scale", sca)]:
        for j in range(3):
            fc = obj.animation_data.action.fcurves.find(data_path=axis, index=j)
            if fc:
                for kp in fc.keyframe_points:
                    if int(kp.co[0]) == frame:
                        default[j] = kp.co[1]
                        found_any = True
                        break
    return (tuple(loc), tuple(rot), tuple(sca)) if found_any else None

def apply_delta_to_keyframes_and_restore_selection(obj, delta_loc, delta_rot, delta_sca, target_frames: Set[int]):
    """将增量应用到目标关键帧，并在结束后恢复这些帧的选中状态"""
    if not obj.animation_data or not obj.animation_data.action:
        return

    action = obj.animation_data.action
    paths = [("location", delta_loc), ("rotation_euler", delta_rot), ("scale", delta_sca)]

    # Step 1: 应用增量
    for data_path, delta in paths:
        for j in range(3):
            fc = action.fcurves.find(data_path=data_path, index=j)
            if not fc:
                continue
            for kp in fc.keyframe_points:
                frame = int(kp.co[0])
                if frame in target_frames:
                    was_selected = kp.select_control_point
                    kp.co[1] += delta[j]
                    kp.handle_left[1] += delta[j]
                    kp.handle_right[1] += delta[j]
                    kp.select_control_point = was_selected
            fc.update()

    # Step 2: 同步后，强制重新选中 target_frames 的所有关键帧点
    for data_path in ["location", "rotation_euler", "scale"]:
        for j in range(3):
            fc = action.fcurves.find(data_path=data_path, index=j)
            if not fc:
                continue
            for kp in fc.keyframe_points:
                frame = int(kp.co[0])
                if frame in target_frames:
                    kp.select_control_point = True

    print(f"✅ 同步完成 {obj.name} → 帧: {sorted(target_frames)}")

# ========== OPERATORS ==========
class ANIM_OT_RecordCurrentFrame(Operator):
    bl_idname = "anim.record_current_frame"
    bl_label = "记录选中帧"
    bl_description = "记录当前选中物体上所有被选中的关键帧及其原始值"

    def execute(self, context):
        global _recorded_data
        _recorded_data.clear()
        selected_objects = [obj for obj in context.selected_objects if obj.type in {'MESH', 'EMPTY', 'ARMATURE', 'CURVE'}]

        for obj in selected_objects:
            selected_frames = get_selected_keyframes(obj)
            if not selected_frames:
                self.report({'WARNING'}, f"{obj.name} 无选中关键帧，跳过")
                continue

            # 记录每个选中帧的原始值
            frame_values = {}
            for frame in selected_frames:
                transform = get_full_transform_at_frame_from_fcurves(obj, frame)
                if transform:
                    frame_values[frame] = transform
                else:
                    self.report({'WARNING'}, f"{obj.name} 帧 {frame} 无完整变换关键帧，跳过记录")
                    continue

            if not frame_values:
                continue

            _recorded_data[obj.name] = (frame_values, selected_frames)
            print(f"📝 已记录 {obj.name} → 帧: {sorted(selected_frames)}")

        self.report({'INFO'}, f"已记录 {len(_recorded_data)} 个物体的选中帧组")
        return {'FINISHED'}

class ANIM_OT_SyncToSelectedFrames(Operator):
    bl_idname = "anim.sync_to_selected_frames"
    bl_label = "同步修改到记录帧"
    bl_description = "自动检测哪个记录帧被修改，以其为基准同步到其他记录帧"

    def execute(self, context):
        global _recorded_data
        if not _recorded_data:
            self.report({'ERROR'}, "请先点击【记录选中帧】！")
            return {'CANCELLED'}

        selected_objects = [obj for obj in context.selected_objects if obj.type in {'MESH', 'EMPTY', 'ARMATURE', 'CURVE'}]

        for obj in selected_objects:
            obj_key = obj.name
            if obj_key not in _recorded_data:
                self.report({'WARNING'}, f"{obj.name} 未被记录，跳过")
                continue

            orig_frame_values, target_frames = _recorded_data[obj_key]

            # 重新读取当前所有记录帧的值，对比找出被修改的帧
            modified_frames = []
            current_frame_values = {}

            for frame in target_frames:
                current_transform = get_full_transform_at_frame_from_fcurves(obj, frame)
                if not current_transform:
                    continue
                current_frame_values[frame] = current_transform

                orig_transform = orig_frame_values.get(frame)
                if not orig_transform:
                    continue

                # 比较是否修改
                current_loc, current_rot, current_sca = current_transform
                orig_loc, orig_rot, orig_sca = orig_transform

                delta = (
                    tuple(c - o for c, o in zip(current_loc, orig_loc)),
                    tuple(c - o for c, o in zip(current_rot, orig_rot)),
                    tuple(c - o for c, o in zip(current_sca, orig_sca))
                )

                if any(abs(x) > 1e-6 for x in delta[0] + delta[1] + delta[2]):
                    modified_frames.append((frame, delta))

            if len(modified_frames) == 0:
                self.report({'WARNING'}, f"{obj.name} 无任何记录帧被修改，跳过同步")
                continue
            elif len(modified_frames) > 1:
                frames = [f[0] for f in modified_frames]
                self.report({'ERROR'}, f"{obj.name} 有多个帧被修改 ({frames})，请只修改一个作为基准！")
                continue

            # 只有一个被修改的帧 → 用它作为基准
            modified_frame, (delta_loc, delta_rot, delta_sca) = modified_frames[0]
            frames_to_apply = {f for f in target_frames if f != modified_frame}

            if not frames_to_apply:
                self.report({'WARNING'}, f"{obj.name} 无其他目标帧可同步")
                continue

            apply_delta_to_keyframes_and_restore_selection(obj, delta_loc, delta_rot, delta_sca, frames_to_apply)
            print(f"🔁 以帧 {modified_frame} 为基准同步到 {sorted(frames_to_apply)}")

        self.report({'INFO'}, "✅ 同步完成！已应用到记录的目标帧并恢复选中状态")
        return {'FINISHED'}

# ========== PANEL ==========
class ANIM_PT_FrameSyncPanel(Panel):
    bl_label = "智能帧同步工具"
    bl_idname = "ANIM_PT_frame_sync_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        layout.label(text="自由记录 & 智能同步", icon='INFO')
        layout.label(text="1. 在 Graph Editor 选中多个关键帧")
        layout.label(text="2. 点击【记录选中帧】")
        layout.label(text="3. 修改其中任意一个关键帧")
        layout.label(text="4. 点击【同步修改到记录帧】")
        layout.separator()
        layout.operator("anim.record_current_frame", text="📥 记录选中帧", icon='REC')
        layout.operator("anim.sync_to_selected_frames", text="🔄 同步修改到记录帧", icon='KEYTYPE_KEYFRAME_VEC')

# ========== 注册 ==========
classes = (
    ANIM_OT_RecordCurrentFrame,
    ANIM_OT_SyncToSelectedFrames,
    ANIM_PT_FrameSyncPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    print("✅ 智能帧同步工具已注册 — 在 3D视图右侧 Tool 栏使用")

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    global _recorded_data
    _recorded_data.clear()

if __name__ == "__main__":
    register()