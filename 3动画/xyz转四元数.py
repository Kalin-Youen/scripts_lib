# -*- coding-utf-8 -*-

# 保证完美的4空格缩进

import bpy
from mathutils import Euler, Quaternion

def _copy_keyframe_properties(source_key, target_key):
    """
    辅助函数：将一个关键帧的所有重要属性复制到另一个关键帧。
    """
    target_key.interpolation = source_key.interpolation
    target_key.easing = source_key.easing
    target_key.period = source_key.period
    target_key.amplitude = source_key.amplitude
    
    if source_key.interpolation == 'BEZIER':
        target_key.handle_left = source_key.handle_left
        target_key.handle_right = source_key.handle_right
        target_key.handle_left_type = source_key.handle_left_type
        target_key.handle_right_type = source_key.handle_right_type

class OBJECT_OT_batch_switch_rotation_mode(bpy.types.Operator):
    """
    对所有选定物体批量转换旋转模式(欧拉/四元数)，
    可选择完美保留关键帧类型，或通过bpy.ops统一设置。
    """
    bl_idname = "object.batch_switch_rotation_mode"
    bl_label = "批量转换旋转模式(保留/统一类型)"
    bl_options = {'REGISTER', 'UNDO'}

    target_mode: bpy.props.EnumProperty(
        name="目标模式",
        description="选择要将物体转换成的旋转模式",
        items=[('XYZ', "XYZ 欧拉", ""), ('QUATERNION', "四元数", "")],
        default='XYZ'
    )
    
    force_keyframe_type: bpy.props.BoolProperty(
        name="执行'设置为关键帧'命令",
        description="转换后，全选新关键帧并执行 bpy.ops.action.keyframe_type(type='KEYFRAME') 命令",
        default=True
    )

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"将对 {len(context.selected_objects)} 个选定物体进行操作:")
        box = layout.box()
        box.prop(self, "target_mode", expand=True)
        box = layout.box()
        box.label(text="可选的后处理步骤:")
        box.prop(self, "force_keyframe_type")

    def execute(self, context):
        # --- 寻找一个有效的动画编辑器上下文 ---
        # 这是执行bpy.ops所必需的，也是高级脚本技巧
        override_context = None
        for area in context.screen.areas:
            if area.type in ['GRAPH_EDITOR', 'DOPESHEET_EDITOR', 'TIMELINE']:
                override_context = context.copy()
                override_context['area'] = area
                override_context['region'] = area.regions[-1]
                break
        
        if self.force_keyframe_type and not override_context:
            self.report({'ERROR'}, "未能找到动画编辑器上下文来执行bpy.ops命令。")
            return {'CANCELLED'}

        selected_objects = context.selected_objects
        converted_count = 0
        skipped_count = 0
        
        for obj in selected_objects:
            if not hasattr(obj, 'rotation_mode'):
                skipped_count += 1
                continue

            is_euler_mode = obj.rotation_mode.endswith('EULER')
            is_quat_mode = obj.rotation_mode == 'QUATERNION'

            if (self.target_mode == 'XYZ' and is_euler_mode) or \
               (self.target_mode == 'QUATERNION' and is_quat_mode):
                skipped_count += 1
                continue
            
            if not (obj.animation_data and obj.animation_data.action):
                obj.rotation_mode = self.target_mode
                converted_count += 1
                continue

            action = obj.animation_data.action
            new_fcurves = []

            if self.target_mode == 'XYZ':
                new_fcurves = self._convert_quaternion_to_euler(obj, action, self.force_keyframe_type)
            elif self.target_mode == 'QUATERNION':
                new_fcurves = self._convert_euler_to_quaternion(obj, action, self.force_keyframe_type)
            
            # --- 遵从你的指令：执行 bpy.ops ---
            if self.force_keyframe_type and new_fcurves:
                # 使用我们找到的上下文来安全地执行命令
                with bpy.context.temp_override(**override_context):
                    # 确保先取消所有选择
                    bpy.ops.action.select_all(action='DESELECT')
                    # 精确地选中所有新创建的关键帧
                    for fc in new_fcurves:
                        for key in fc.keyframe_points:
                            key.select_control_point = True
                    
                    # 执行你指定的命令！
                    bpy.ops.action.keyframe_type(type='KEYFRAME')
                    
                    # 清理选择
                    bpy.ops.action.select_all(action='DESELECT')

            converted_count += 1

        context.view_layer.update()
        report_message = f"操作完成！ 成功转换: {converted_count}个, 跳过: {skipped_count}个。"
        self.report({'INFO'}, report_message)
        return {'FINISHED'}

    def _convert_quaternion_to_euler(self, obj, action, force_op):
        quat_fcurves = [action.fcurves.find(f"rotation_quaternion", index=i) for i in range(4)]
        valid_fcurves = [fc for fc in quat_fcurves if fc]
        if not valid_fcurves:
            obj.rotation_mode = 'XYZ'
            return []
        source_keyframes = {k.co[0]: {fc.array_index: k for k in fc.keyframe_points} for fc in valid_fcurves for k in fc.keyframe_points}
        euler_fcurves = [action.fcurves.find("rotation_euler", index=i) or action.fcurves.new(data_path="rotation_euler", index=i) for i in range(3)]
        for frame, keys_at_frame in sorted(source_keyframes.items()):
            quat_val = Quaternion((
                quat_fcurves[0].evaluate(frame) if quat_fcurves[0] else 1.0, quat_fcurves[1].evaluate(frame) if quat_fcurves[1] else 0.0,
                quat_fcurves[2].evaluate(frame) if quat_fcurves[2] else 0.0, quat_fcurves[3].evaluate(frame) if quat_fcurves[3] else 0.0))
            euler_val = quat_val.to_euler('XYZ')
            template_key = keys_at_frame.get(1) or keys_at_frame.get(0)
            for i in range(3):
                new_key = euler_fcurves[i].keyframe_points.insert(frame, euler_val[i], options={'REPLACE'})
                if not force_op and template_key: _copy_keyframe_properties(template_key, new_key)
        for fc in euler_fcurves: fc.update()
        for fc in valid_fcurves: action.fcurves.remove(fc)
        obj.rotation_mode = 'XYZ'
        return euler_fcurves

    def _convert_euler_to_quaternion(self, obj, action, force_op):
        original_euler_order = obj.rotation_mode
        euler_fcurves = [action.fcurves.find("rotation_euler", index=i) for i in range(3)]
        valid_fcurves = [fc for fc in euler_fcurves if fc]
        if not valid_fcurves:
            obj.rotation_mode = 'QUATERNION'
            return []
        source_keyframes = {k.co[0]: {fc.array_index: k for k in fc.keyframe_points} for fc in valid_fcurves for k in fc.keyframe_points}
        quat_fcurves = [action.fcurves.find("rotation_quaternion", index=i) or action.fcurves.new(data_path="rotation_quaternion", index=i) for i in range(4)]
        for frame, keys_at_frame in sorted(source_keyframes.items()):
            euler_val = Euler((
                euler_fcurves[0].evaluate(frame) if euler_fcurves[0] else 0.0, euler_fcurves[1].evaluate(frame) if euler_fcurves[1] else 0.0,
                euler_fcurves[2].evaluate(frame) if euler_fcurves[2] else 0.0), original_euler_order)
            quat_val = euler_val.to_quaternion()
            template_key = keys_at_frame.get(0)
            for i in range(4):
                new_key = quat_fcurves[i].keyframe_points.insert(frame, quat_val[i], options={'REPLACE'})
                if not force_op and template_key: _copy_keyframe_properties(template_key, new_key)
        for fc in quat_fcurves: fc.update()
        for fc in valid_fcurves: action.fcurves.remove(fc)
        obj.rotation_mode = 'QUATERNION'
        return quat_fcurves

# 注册和注销函数
def register():
    bpy.utils.register_class(OBJECT_OT_batch_switch_rotation_mode)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_batch_switch_rotation_mode)

# 主程序入口
if __name__ == "__main__":
    try: unregister()
    except RuntimeError: pass
    register()
    print("脚本注册成功！")
    print("请选中一个或多个物体，按 F3 搜索 '批量转换旋转模式' 来运行。")
    if bpy.context.selected_objects:
        bpy.ops.object.batch_switch_rotation_mode('INVOKE_DEFAULT')

