# script_id: 307179a6-f677-4e5a-a862-a519119b18eb
import bpy
from bpy.props import BoolProperty, EnumProperty
from bpy.types import Operator

class ANIM_OT_quick_keyframe_or_delete(Operator):
    bl_idname = "anim.quick_keyframe_or_delete"
    bl_label = "快速关键帧 / 删除关键帧"
    bl_description = "为选中物体在当前帧插入或删除关键帧"

    mode: EnumProperty(
        name="模式",
        items=[
            ('KEYFRAME', "插入关键帧", ""),
            ('DELETE', "删除关键帧", "")
        ],
        default='KEYFRAME'
    )

    loc: BoolProperty(name="位置 (Location)", default=True)
    rot: BoolProperty(name="旋转 (Rotation)", default=True)
    scale: BoolProperty(name="缩放 (Scale)", default=True)
    shapekeys: BoolProperty(name="所有形态键 (All Shape Keys)", default=True)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "mode")

        box = layout.box()
        box.label(text="变换属性:")
        box.prop(self, "loc")
        box.prop(self, "rot")
        box.prop(self, "scale")

        box = layout.box()
        box.label(text="形态键:")
        box.prop(self, "shapekeys", text="全部形态键")

    def execute(self, context):
        scene = context.scene
        current_frame = scene.frame_current
        selected_objects = [obj for obj in context.selected_objects if obj]  # 排除 None

        if not selected_objects:
            self.report({'WARNING'}, "请先选择物体")
            return {'CANCELLED'}

        count_keyed = 0
        count_deleted = 0

        for obj in selected_objects:
            # 跳过不支持动画数据的物体类型（可选，但安全起见保留）
            if obj.type in {'CAMERA', 'LIGHT', 'SPEAKER', 'EMPTY', 'FORCE_FIELD'}:
                # 这些类型其实支持位置/旋转/缩放，但不支持形态键 → 只处理变换
                pass

            # --- 处理变换属性（在 Object 上）---
            if self.loc:
                if self.safe_keyframe(obj, "location", self.mode, current_frame, target_id=obj):
                    if self.mode == 'KEYFRAME': count_keyed += 1
                    else: count_deleted += 1
            if self.rot:
                rot_path = self.get_rotation_path(obj)
                if rot_path:
                    if self.safe_keyframe(obj, rot_path, self.mode, current_frame, target_id=obj):
                        if self.mode == 'KEYFRAME': count_keyed += 1
                        else: count_deleted += 1
            if self.scale:
                if self.safe_keyframe(obj, "scale", self.mode, current_frame, target_id=obj):
                    if self.mode == 'KEYFRAME': count_keyed += 1
                    else: count_deleted += 1

            # --- 处理形态键（仅限 Mesh，且必须有 shape_keys）---
            if self.shapekeys and obj.type == 'MESH':
                try:
                    mesh = obj.data
                    if not mesh or not hasattr(mesh, 'shape_keys') or not mesh.shape_keys:
                        continue
                    key_blocks = mesh.shape_keys.key_blocks
                    if not key_blocks:
                        continue

                    for sk in key_blocks:
                        if not sk:
                            continue
                        data_path = f'key_blocks["{sk.name}"].value'
                        if self.safe_keyframe(obj, data_path, self.mode, current_frame, target_id=mesh):
                            if self.mode == 'KEYFRAME': count_keyed += 1
                            else: count_deleted += 1

                except Exception as e:
                    print(f"[形态键处理错误] 物体: {obj.name}, 错误: {e}")
                    continue  # 跳过错误，不崩溃

        if self.mode == 'KEYFRAME':
            self.report({'INFO'}, f"✅ 已为 {len(selected_objects)} 个物体插入 {count_keyed} 个关键帧")
        else:
            self.report({'INFO'}, f"🗑️ 已从 {len(selected_objects)} 个物体删除 {count_deleted} 个关键帧")

        # 刷新动画编辑器
        for area in context.screen.areas:
            if area.type in {'DOPESHEET_EDITOR', 'GRAPH_EDITOR', 'TIMELINE'}:
                area.tag_redraw()

        return {'FINISHED'}

    def get_rotation_path(self, obj):
        """根据旋转模式返回正确的路径"""
        try:
            mode = obj.rotation_mode
            if mode in {'XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX'}:
                return "rotation_euler"
            elif mode == 'QUATERNION':
                return "rotation_quaternion"
            elif mode == 'AXIS_ANGLE':
                return "rotation_axis_angle"
        except:
            pass
        return "rotation_euler"  # 默认回退

    def safe_keyframe(self, obj, data_path, mode, frame, target_id):
        """安全插入/删除关键帧，避免崩溃"""
        try:
            if not target_id:
                return False

            if not hasattr(target_id, "animation_data"):
                return False

            if not target_id.animation_data:
                if mode == 'DELETE':
                    return False
                target_id.animation_data_create()

            action = target_id.animation_data.action
            if not action:
                if mode == 'DELETE':
                    return False
                action_name = f"{obj.name}_ShapeKeys" if target_id != obj else f"{obj.name}_Action"
                action = bpy.data.actions.new(name=action_name)
                target_id.animation_data.action = action

            if mode == 'KEYFRAME':
                target_id.keyframe_insert(data_path=data_path, frame=frame)
            else:
                # 删除关键帧
                for fcurve in action.fcurves:
                    if fcurve.data_path == data_path:
                        pts_to_remove = [i for i, kp in enumerate(fcurve.keyframe_points) if int(kp.co[0]) == frame]
                        for i in reversed(pts_to_remove):
                            fcurve.keyframe_points.remove(fcurve.keyframe_points[i])
                        if len(fcurve.keyframe_points) == 0:
                            action.fcurves.remove(fcurve)
                        else:
                            fcurve.update()
            return True

        except Exception as e:
            print(f"[关键帧错误] {obj.name} - {data_path}: {e}")
            return False

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)

# ==============================
# 注册 & 运行
# ==============================

def register():
    bpy.utils.register_class(ANIM_OT_quick_keyframe_or_delete)

def unregister():
    bpy.utils.unregister_class(ANIM_OT_quick_keyframe_or_delete)

if __name__ == "__main__":
    register()
    bpy.ops.anim.quick_keyframe_or_delete('INVOKE_DEFAULT')