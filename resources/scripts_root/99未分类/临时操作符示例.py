# script_id: 75134b77-cb90-44fe-8ee1-785f2e807b8a
import bpy

class TEMP_OT_my_tool(bpy.types.Operator):
    """带参数的临时 Operator，执行完后自动注销自己"""
    bl_idname = "temp.my_tool"
    bl_label = "My Temp Tool"

    use_feature: bpy.props.BoolProperty(
        name="Use Feature",
        description="是否启用某功能",
        default=True,
    )
    threshold: bpy.props.FloatProperty(
        name="Threshold",
        description="数值阈值",
        default=0.5,
        min=0.0, max=1.0,
    )
    count: bpy.props.IntProperty(
        name="Count",
        description="重复次数",
        default=3,
        min=1, max=10,
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        # —— 真正的业务逻辑 —— 
        print("===== TEMP TOOL RUN =====")
        print("Use Feature:", self.use_feature)
        print("Threshold:", self.threshold)
        print("Count:", self.count)
        for i in range(self.count):
            for obj in context.selected_objects:
                obj.rotation_euler.rotate_axis("Z", self.threshold)
        print("===== DONE =====")

        # —— 业务做完后，注销自己 —— 
        bpy.utils.unregister_class(self.__class__)
        return {'FINISHED'}

    def invoke(self, context, event):
        # 弹窗让用户调整参数
        return context.window_manager.invoke_props_dialog(self)

    def cancel(self, context):
        # 如果用户在对话框里点 取消，也把自己卸载掉
        bpy.utils.unregister_class(self.__class__)
        return {'CANCELLED'}


def run_temp_tool(use_feature=True, threshold=0.3, count=5, invoke_dialog=False):
    # 1. 注册 Operator
    bpy.utils.register_class(TEMP_OT_my_tool)

    # 2. 调用 Operator
    if invoke_dialog:
        # 弹对话框
        bpy.ops.temp.my_tool('INVOKE_DEFAULT')
    else:
        # 直接传参执行
        bpy.ops.temp.my_tool(
            use_feature=use_feature,
            threshold=threshold,
            count=count
        )
    # —— 注意：不在这里立即注销，否则弹窗模式下会崩 ——


if __name__ == "__main__":
    # 直接执行模式：
    # run_temp_tool(use_feature=False, threshold=0.8, count=2, invoke_dialog=False)

    # 弹窗模式：
    run_temp_tool(invoke_dialog=True)
