# script_id: d1227f5a-9960-4e34-a4c9-2ac903594b9c
import bpy

#---------------------------------------------------
#      【批量时间加速 · 弹窗设置版】
#
# 功能: 对所有选中的物体，剪掉从指定帧之后的一段动画时间，
#      实现动画的“快进”或“加速”效果。
#
# ==> 使用方法 <==
# 1. 在3D视图中，按住Shift选中所有你想要操作的物体。
# 2. 直接点击“运行脚本”按钮（播放图标）。
# 3. ✅ 会弹出窗口，让你设置【起始帧】和【剪切帧数】
# 4. 点击 OK 即可完成批量加速！
#
# By: 你无所不能又可爱的AI助手 (弹窗Pro版!)
#---------------------------------------------------

class OBJECT_OT_batch_time_accelerate(bpy.types.Operator):
    """批量剪切动画时间，实现“快进”效果。支持物体和形变键动画。"""
    bl_idname = "object.batch_time_accelerate"
    bl_label = "批量时间加速（弹窗版）"
    bl_options = {'REGISTER', 'UNDO'}

    # 可编辑属性（会显示在弹窗中）
    start_frame: bpy.props.IntProperty(
        name="起始帧",
        description="从这一帧之后开始剪切动画（本帧保留）",
        default=460,
        min=0
    )

    duration_to_remove: bpy.props.IntProperty(
        name="剪切帧数",
        description="要删除多少帧的动画？这些帧将被跳过",
        default=20,
        min=1
    )

    def invoke(self, context, event):
        # 默认使用当前帧作为起始帧
        self.start_frame = context.scene.frame_current
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text="设置加速参数：", icon='PREFERENCES')
        layout.prop(self, "start_frame")
        layout.prop(self, "duration_to_remove")
        layout.separator()
        layout.label(text="提示：起始帧之后的动画将被前移", icon='INFO')

    def execute(self, context):
        start_frame = self.start_frame
        duration_to_remove = self.duration_to_remove

        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "⚠️ 请先选择至少一个物体！")
            return {'CANCELLED'}

        # 总指挥函数（原 batch_accelerate_time 内容）
        print(f"--- 🚀 开始批量时间加速，共 {len(selected_objects)} 个物体 ---")
        print(f"将从第 {start_frame} 帧后，剪切掉 {duration_to_remove} 帧。")

        cut_end_frame = start_frame + duration_to_remove

        processed_count = 0
        for obj in selected_objects:
            print(f"\n处理: '{obj.name}' (类型: {obj.type})")
            processed_something = False

            # --- 处理主动画 ---
            if obj.animation_data and obj.animation_data.action:
                self.process_action(obj.animation_data.action, start_frame, cut_end_frame)
                print("  -> 已处理 [物体/骨架] 动画")
                processed_something = True

            # --- 处理形变键动画 ---
            if (hasattr(obj.data, 'shape_keys') and 
                obj.data.shape_keys and 
                obj.data.shape_keys.animation_data and 
                obj.data.shape_keys.animation_data.action):
                self.process_action(obj.data.shape_keys.animation_data.action, start_frame, cut_end_frame)
                print("  -> 已处理 [形态键] 动画")
                processed_something = True

            if processed_something:
                processed_count += 1

        # 操作完成后跳转到起始帧，方便查看
        context.scene.frame_set(start_frame)
        self.report({'INFO'}, f"✅ 批量加速完成！共处理 {processed_count} 个物体。")

        return {'FINISHED'}

    def process_action(self, action, start_frame, cut_end_frame):
        """
        处理单个 Action：删除指定区间的关键帧，并前移后续帧
        """
        for fcurve in action.fcurves:
            keyframes_to_delete = []

            # 遍历所有关键帧
            for kf in fcurve.keyframe_points:
                frame = kf.co[0]

                # 条件1：在剪切区间内 -> 标记删除（保留 start_frame，所以 > start_frame）
                if start_frame < frame <= cut_end_frame:
                    keyframes_to_delete.append(kf)

                # 条件2：在剪切区间之后 -> 向前移动
                elif frame > cut_end_frame:
                    kf.co[0] -= (cut_end_frame - start_frame)  # 即 duration_to_remove
                    try:
                        kf.handle_left[0] -= (cut_end_frame - start_frame)
                        kf.handle_right[0] -= (cut_end_frame - start_frame)
                    except:
                        pass

            # 统一删除标记的关键帧（倒序删除更安全）
            for kf in reversed(keyframes_to_delete):
                fcurve.keyframe_points.remove(kf)


# ========================
#     注册并运行函数
# ========================

def register_and_run():
    try:
        bpy.utils.unregister_class(OBJECT_OT_batch_time_accelerate)
    except:
        pass
    bpy.utils.register_class(OBJECT_OT_batch_time_accelerate)
    bpy.ops.object.batch_time_accelerate('INVOKE_DEFAULT')


# ========================
#      脚本主入口
# ========================

if __name__ == "__main__":
    register_and_run()