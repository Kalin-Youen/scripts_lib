# -*- coding: utf-8 -*-
# ──────────────────────────────────────────────────────────
#   管道顶点滑动累积动画生成器 v7.0 (双重反转 & 专业执行)
#   作者: 代码高手
#   功能: 支持物理反向/动画反转/自定义起始帧/自动帧范围。
#         在脚本编辑器中直接运行即可弹出设置窗口，提供专业的工作流。
# ──────────────────────────────────────────────────────────
import bpy
import numpy as np

def create_advanced_sliding_animation(context, total_steps=50, reverse=False, start_frame=1, auto_frame_range=True, reverse_animation=False):
    """创建高级滑动动画的核心函数"""
    active_obj = context.active_object
    original_start = context.scene.frame_start
    original_end = context.scene.frame_end

    try:
        if not active_obj or active_obj.type != 'MESH':
            return {'CANCELLED'}

        if bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # 清理现有的形态键
        if active_obj.data.shape_keys:
            for sk in active_obj.data.shape_keys.key_blocks[:]:
                if sk.name != 'Basis':
                    active_obj.shape_key_remove(sk)

        # 确保有基础形态键
        if not active_obj.data.shape_keys:
            active_obj.shape_key_add(name='Basis')

        basis_sk = active_obj.data.shape_keys.key_blocks['Basis']
        num_verts = len(basis_sk.data)
        if num_verts == 0:
            return {'CANCELLED'}

        # 获取顶点坐标
        basis_coords = np.empty(num_verts * 3, dtype=np.float32)
        basis_sk.data.foreach_get('co', basis_coords)
        basis_coords = basis_coords.reshape((num_verts, 3))

        # 确定主轴方向
        dimensions = active_obj.dimensions
        main_axis_index = np.argmax(dimensions)
        axis_coords = basis_coords[:, main_axis_index]

        min_coord_orig = np.min(axis_coords)
        max_coord_orig = np.max(axis_coords)

        # 处理反向参数
        if reverse:
            min_coord, max_coord = max_coord_orig, min_coord_orig
        else:
            min_coord, max_coord = min_coord_orig, max_coord_orig

        pipe_length = abs(max_coord - min_coord)
        if np.isclose(pipe_length, 0):
            return {'CANCELLED'}

        # 创建形态键动画
        new_shape_keys = []
        new_coords = np.copy(basis_coords)

        start_cap_mask = np.isclose(axis_coords, min_coord)
        last_known_target = np.mean(basis_coords[start_cap_mask], axis=0)

        for i in range(1, total_steps + 1):
            sk_name = f"Adv_Slide_{i:03d}"
            new_sk = active_obj.shape_key_add(name=sk_name, from_mix=False)
            new_shape_keys.append(new_sk)

            progress = i / total_steps
            threshold_current = min_coord + pipe_length * progress * (-1 if reverse else 1)
            verts_to_move_mask = basis_coords[:, main_axis_index] > threshold_current if reverse else basis_coords[:, main_axis_index] < threshold_current

            if i < total_steps:
                next_progress = (i + 1) / total_steps
                threshold_next = min_coord + pipe_length * next_progress * (-1 if reverse else 1)
                target_slice_mask = (axis_coords <= threshold_current) & (axis_coords > threshold_next) if reverse else (axis_coords >= threshold_current) & (axis_coords < threshold_next)
            else:
                target_slice_mask = np.isclose(axis_coords, max_coord)

            if np.any(target_slice_mask):
                target_position_step = np.mean(basis_coords[target_slice_mask], axis=0)
                last_known_target = target_position_step
            else:
                target_position_step = last_known_target

            new_coords[verts_to_move_mask] = target_position_step
            new_sk.data.foreach_set('co', new_coords.ravel())
            new_coords[verts_to_move_mask] = basis_coords[verts_to_move_mask]

        # 清理旧的动画数据
        if active_obj.data.shape_keys.animation_data:
            active_obj.data.shape_keys.animation_data_clear()

        # 设置关键帧动画
        keys_to_animate = new_shape_keys[:]
        if reverse_animation:
            keys_to_animate.reverse()

        for i, sk in enumerate(keys_to_animate):
            frame_num = start_frame + i
            sk.value = 0.0
            sk.keyframe_insert(data_path='value', frame=frame_num)
            sk.value = 1.0
            sk.keyframe_insert(data_path='value', frame=frame_num + 1)
            sk.value = 0.0
            sk.keyframe_insert(data_path='value', frame=frame_num + 2)

        # 处理最后一个关键帧
        if new_shape_keys and not reverse_animation:
            last_sk = new_shape_keys[-1]
            last_sk.value = 1.0
            last_sk.keyframe_insert(data_path='value', frame=start_frame + total_steps)

        # 设置关键帧插值模式
        if active_obj.data.shape_keys.animation_data and active_obj.data.shape_keys.animation_data.action:
            fcurves = active_obj.data.shape_keys.animation_data.action.fcurves
            for fcurve in fcurves:
                if 'value' in fcurve.data_path:
                    for kf in fcurve.keyframe_points:
                        kf.interpolation = 'CONSTANT'

        # 设置场景帧范围
        if auto_frame_range:
            context.scene.frame_start = start_frame
            context.scene.frame_end = start_frame + total_steps + 2

        return {'FINISHED'}

    finally:
        if not auto_frame_range:
            context.scene.frame_start = original_start
            context.scene.frame_end = original_end


class MESH_OT_advanced_sliding_collapse_popup(bpy.types.Operator):
    """管道高级滑动动画操作符"""
    bl_idname = "mesh.advanced_sliding_collapse_popup"
    bl_label = "管道高级滑动动画"
    bl_options = {'REGISTER', 'UNDO'}

    total_steps: bpy.props.IntProperty(
        name="动画节数",
        description="动画的总步数（帧数），数值越大动画越平滑",
        default=50,
        min=2,
        max=1000
    )
    
    start_frame: bpy.props.IntProperty(
        name="起始帧",
        description="动画开始播放的帧号",
        min=0
    )

    reverse: bpy.props.BoolProperty(
        name="反向(物理)",
        description="从另一端开始进行顶点塌陷",
        default=False
    )
    
    reverse_animation: bpy.props.BoolProperty(
        name="反转动画(时间)",
        description="反向播放关键帧，实现生长效果",
        default=False
    )

    auto_frame_range: bpy.props.BoolProperty(
        name="自动帧范围",
        description="自动设置场景播放范围以匹配动画",
        default=True
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        return create_advanced_sliding_animation(
            context,
            self.total_steps,
            self.reverse,
            self.start_frame,
            self.auto_frame_range,
            self.reverse_animation
        )

    def invoke(self, context, event):
        self.start_frame = context.scene.frame_current
        return context.window_manager.invoke_props_dialog(self)


def register():
    bpy.utils.register_class(MESH_OT_advanced_sliding_collapse_popup)


def unregister():
    bpy.utils.unregister_class(MESH_OT_advanced_sliding_collapse_popup)


if __name__ == "__main__":
    try:
        unregister()
    except (RuntimeError, AttributeError):
        pass

    register()

    # 尝试在3D视图中弹出对话框
    area = next((area for area in bpy.context.screen.areas if area.type == 'VIEW_3D'), None)
    if area:
        with bpy.context.temp_override(area=area):
            bpy.ops.mesh.advanced_sliding_collapse_popup('INVOKE_DEFAULT')