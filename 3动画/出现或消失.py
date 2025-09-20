import bpy

# 定义我们操作符的唯一ID
OPERATOR_IDNAME = "object.animate_appear_disappear_ephemeral"

class SM_OT_AnimateAppearDisappear(bpy.types.Operator):
    """
    一个临时的多功能操作符，根据所选物体的数量执行不同操作：
    - 1个物体: 创建出现/消失动画（变换对齐）
    - 2个物体: 让活动物体出现，非活动物体消失（变换对齐）
    - 多个物体: 批量对齐缩放为0的关键帧的变换（智能检测）
    它会在执行后或取消后自动注销自己。
    """
    bl_idname = OPERATOR_IDNAME
    bl_label = "智能出现/消失/对齐动画"
    bl_options = {'REGISTER', 'UNDO'}

    # --- 属性定义 (仅在选中1个物体时使用) ---
    effect_type: bpy.props.EnumProperty(
        name="效果类型",
        description="选择是让物体出现还是消失",
        items=[
            ('APPEAR', "出现", "在当前帧出现 (前一帧缩放为0)"),
            ('DISAPPEAR', "消失", "在当前帧消失 (当前帧缩放为0)"),
        ],
        default='APPEAR',
    )

    # --- 内部辅助函数 ---
    def _create_appear(self, context, obj, frame):
        """为指定物体在指定帧创建'出现'动画（变换对齐版）"""
        previous_frame = frame - 1

        # 【核心】保存用户当前帧的变换信息，作为唯一基准
        original_loc = obj.location.copy()
        original_rot = obj.rotation_euler.copy()
        original_scale = obj.scale.copy()

        # 1. 在前一帧，使用基准的位置/旋转，但缩放为0
        context.scene.frame_set(previous_frame)
        obj.location = original_loc
        obj.rotation_euler = original_rot
        obj.scale = (0, 0, 0)
        obj.keyframe_insert(data_path="location", frame=previous_frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=previous_frame)
        obj.keyframe_insert(data_path="scale", frame=previous_frame)

        # 2. 在当前帧，恢复完整的基准变换
        context.scene.frame_set(frame)
        obj.location = original_loc
        obj.rotation_euler = original_rot
        obj.scale = original_scale
        obj.keyframe_insert(data_path="location", frame=frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        obj.keyframe_insert(data_path="scale", frame=frame)

        self.report({'INFO'}, f"为 '{obj.name}' 创建了“出现”动画 (变换已对齐)")

    def _create_disappear(self, context, obj, frame):
        """为指定物体在指定帧创建'消失'动画（变换对齐版）"""
        previous_frame = frame - 1

        # 【核心】保存用户当前帧的变换信息，作为唯一基准
        original_loc = obj.location.copy()
        original_rot = obj.rotation_euler.copy()
        original_scale = obj.scale.copy()

        # 1. 在前一帧，使用完整的基准变换
        context.scene.frame_set(previous_frame)
        obj.location = original_loc
        obj.rotation_euler = original_rot
        obj.scale = original_scale
        obj.keyframe_insert(data_path="location", frame=previous_frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=previous_frame)
        obj.keyframe_insert(data_path="scale", frame=previous_frame)

        # 2. 在当前帧，使用基准的位置/旋转，但缩放为0
        context.scene.frame_set(frame)
        obj.location = original_loc
        obj.rotation_euler = original_rot
        obj.scale = (0, 0, 0)
        obj.keyframe_insert(data_path="location", frame=frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        obj.keyframe_insert(data_path="scale", frame=frame)

        self.report({'INFO'}, f"为 '{obj.name}' 创建了“消失”动画 (变换已对齐)")

    def _unify_transform_at_zero_scale(self, context, obj):
        """找到缩放为0的帧，并将其位置/旋转与前一帧对齐 (智能版)"""
        if not obj.animation_data or not obj.animation_data.action:
            return

        fcurves = obj.animation_data.action.fcurves
        scale_curves = [fc for fc in fcurves if fc.data_path == "scale"]
        if not scale_curves:
            return

        zero_scale_frames = set()
        for fc in scale_curves:
            for kf in fc.keyframe_points:
                if abs(kf.co[1]) < 0.0001:
                    zero_scale_frames.add(int(round(kf.co[0])))

        if not zero_scale_frames:
            self.report({'WARNING'}, f"物体 '{obj.name}' 没有找到缩放为0的关键帧")
            return

        processed_count = 0
        for frame in sorted(list(zero_scale_frames)):
            previous_frame = frame - 1

            context.scene.frame_set(previous_frame)
            scale_at_prev = obj.scale

            if all(abs(s) < 0.0001 for s in scale_at_prev):
                continue

            loc_from_prev = obj.location.copy()
            rot_from_prev = obj.rotation_euler.copy()

            context.scene.frame_set(frame)
            obj.location = loc_from_prev
            obj.rotation_euler = rot_from_prev
            obj.keyframe_insert(data_path="location", frame=frame)
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)
            processed_count += 1

        if processed_count > 0:
            self.report({'INFO'}, f"为 '{obj.name}' 智能对齐了 {processed_count} 个关键帧的变换")

    # --- 核心执行逻辑 ---
    def execute(self, context):
        selected_objects = context.selected_objects
        active_object = context.active_object
        num_selected = len(selected_objects)

        if num_selected == 0:
            self.report({'WARNING'}, "没有选择任何物体")
            bpy.utils.unregister_class(self.__class__)
            return {'CANCELLED'}

        current_frame = context.scene.frame_current

        # 模式一：选中1个物体
        if num_selected == 1:
            obj = active_object
            if self.effect_type == 'APPEAR':
                self._create_appear(context, obj, current_frame)
            else: # DISAPPEAR
                self._create_disappear(context, obj, current_frame)

        # 模式二：选中2个物体
        elif num_selected == 2:
            other_object = [obj for obj in selected_objects if obj != active_object][0]
            self._create_appear(context, active_object, current_frame)
            self._create_disappear(context, other_object, current_frame)

        # 模式三：选中超过2个物体
        else: # num_selected > 2
            for obj in selected_objects:
                self._unify_transform_at_zero_scale(context, obj)

        context.scene.frame_set(current_frame)

        print(f"操作符 {self.bl_idname} 执行完毕，自动注销。")
        bpy.utils.unregister_class(self.__class__)
        return {'FINISHED'}

    def invoke(self, context, event):
        if len(context.selected_objects) == 1:
            return context.window_manager.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def cancel(self, context):
        print(f"操作符 {self.bl_idname} 被取消，自动注销。")
        bpy.utils.unregister_class(self.__class__)


# ================================================================
# 主执行部分
# ================================================================
def run_ephemeral_operator():
    """封装"注册 -> 调用 -> (自动注销)"的流程。"""
    try:
        bpy.utils.unregister_class(SM_OT_AnimateAppearDisappear)
    except RuntimeError:
        pass 

    bpy.utils.register_class(SM_OT_AnimateAppearDisappear)

    view3d_area = next((area for area in bpy.context.screen.areas if area.type == 'VIEW_3D'), None)
    if view3d_area:
        with bpy.context.temp_override(area=view3d_area):
            bpy.ops.object.animate_appear_disappear_ephemeral('INVOKE_DEFAULT')
    else:
        bpy.ops.object.animate_appear_disappear_ephemeral('INVOKE_DEFAULT')


if __name__ == "__main__":
    run_ephemeral_operator()