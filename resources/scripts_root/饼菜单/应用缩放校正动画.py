# -*- coding: utf-8 -*-

import bpy
from mathutils import Vector, Matrix, Euler, Quaternion

class OBJECT_OT_apply_transform_and_sync_keys(bpy.types.Operator):
    """
    在当前帧应用物体变换(位置/旋转/缩放)，并智能调整所有相关
    动画关键帧，以在视觉上保持原始动画不变。
    现已支持欧拉角和四元数旋转模式。
    """
    bl_idname = "object.apply_transform_and_sync_keys"
    bl_label = "应用变换并同步关键帧 (支持四元数)"
    bl_options = {'REGISTER', 'UNDO'}

    # --- 添加可配置的属性 ---
    apply_location: bpy.props.BoolProperty(
        name="位置",
        description="应用物体的位置，并同步所有位置关键帧",
        default=False
    )
    apply_rotation: bpy.props.BoolProperty(
        name="旋转",
        description="应用物体的旋转，并同步所有旋转关键帧",
        default=False
    )
    apply_scale: bpy.props.BoolProperty(
        name="缩放",
        description="应用物体的缩放，并同步所有缩放关键帧",
        default=True
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        # 必须有一个活动对象，且该对象有动画数据
        return obj and obj.animation_data and obj.animation_data.action

    def invoke(self, context, event):
        # 调用属性弹窗，让用户进行选择
        return context.window_manager.invoke_props_dialog(self)
        
    def draw(self, context):
        # 在弹窗中绘制UI元素
        layout = self.layout
        obj = context.active_object
        
        layout.label(text=f"将对 \"{obj.name}\" 执行以下操作:")
        
        col = layout.column()
        # 绘制三个复选框
        col.prop(self, "apply_location")
        col.prop(self, "apply_rotation")
        col.prop(self, "apply_scale")
        
        layout.separator()
        if obj.rotation_mode == 'QUATERNION':
            layout.label(text=f"模式: {obj.rotation_mode}", icon='INFO')
        else:
            layout.label(text=f"模式: {obj.rotation_mode}", icon='INFO')

        layout.separator()
        layout.label(text="这将在当前帧应用变换并修正所有关键帧。")


    def execute(self, context):
        # --- 1. 初始化和验证 ---
        if not (self.apply_location or self.apply_rotation or self.apply_scale):
            self.report({'INFO'}, "未选择任何变换类型，操作已取消。")
            return {'CANCELLED'}

        obj = context.active_object
        action = obj.animation_data.action
        current_frame = context.scene.frame_current
        depsgraph = context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)

        # --- 2. 获取当前帧的“应用”变换矩阵 ---
        # 我们需要一个完整的矩阵来处理L/R/S之间的相互影响
        
        # 获取要应用的变换，即使某些选项为False，我们也需要它们来构建完整的矩阵
        applied_loc = obj_eval.location.copy()
        # 根据旋转模式获取旋转值
        if obj.rotation_mode == 'QUATERNION':
            applied_rot = obj_eval.rotation_quaternion.copy()
        else:
            applied_rot = obj_eval.rotation_euler.copy()
        applied_scl = obj_eval.scale.copy()
        
        # 根据用户的选择来构建“应用”矩阵
        # 如果不应用某个变换，就使用其单位元（零向量/单位旋转/单位缩放）
        loc_mat = Matrix.Translation(applied_loc) if self.apply_location else Matrix()
        
        if self.apply_rotation:
            # 统一将旋转转换为矩阵
            if obj.rotation_mode == 'QUATERNION':
                rot_mat = applied_rot.to_matrix().to_4x4()
            else: # 所有欧拉角模式
                rot_mat = applied_rot.to_matrix().to_4x4()
        else:
            rot_mat = Matrix()

        scl_mat = Matrix.Scale(applied_scl[0], 4, (1, 0, 0)) @ \
                  Matrix.Scale(applied_scl[1], 4, (0, 1, 0)) @ \
                  Matrix.Scale(applied_scl[2], 4, (0, 0, 1)) if self.apply_scale else Matrix()
        
        # Blender的变换顺序是 Scale -> Rotation -> Location
        # M = T @ R @ S
        matrix_to_apply = loc_mat @ rot_mat @ scl_mat
        
        if self.apply_scale and (applied_scl.x == 0 or applied_scl.y == 0 or applied_scl.z == 0):
            self.report({'ERROR'}, "物体缩放包含0，无法计算逆矩阵，操作已取消。")
            return {'CANCELLED'}
        
        try:
            matrix_to_apply_inv = matrix_to_apply.inverted()
        except ValueError:
            self.report({'ERROR'}, "计算逆矩阵失败，请检查物体变换值。")
            return {'CANCELLED'}
            
        # --- 3. 应用变换 ---
        bpy.ops.object.transform_apply(
            location=self.apply_location,
            rotation=self.apply_rotation,
            scale=self.apply_scale
        )

        # --- 4. 搜集所有需要更新的关键帧 (已修复) ---
        all_fcurves = []
        if self.apply_location:
            all_fcurves.extend([fc for fc in [action.fcurves.find("location", index=i) for i in range(3)] if fc])
        if self.apply_rotation:
            if obj.rotation_mode == 'QUATERNION':
                all_fcurves.extend([fc for fc in [action.fcurves.find("rotation_quaternion", index=i) for i in range(4)] if fc])
            else: # 所有欧拉角模式
                all_fcurves.extend([fc for fc in [action.fcurves.find("rotation_euler", index=i) for i in range(3)] if fc])
        if self.apply_scale:
            all_fcurves.extend([fc for fc in [action.fcurves.find("scale", index=i) for i in range(3)] if fc])

        key_frames = set()
        for fcurve in all_fcurves:
            for key in fcurve.keyframe_points:
                key_frames.add(key.co[0])
        
        sorted_frames = sorted(list(key_frames))

        # --- 5. 遍历并修正所有关键帧 ---
        for frame in sorted_frames:
            # 5.1 获取该帧原始的局部变换矩阵
            # 为了健壮性，我们为可能不存在的F-Curve通道提供默认值
            def get_val(path, idx, frame, default_val):
                fc = action.fcurves.find(path, index=idx)
                return fc.evaluate(frame) if fc else default_val

            original_loc = Vector([get_val("location", i, frame, 0.0) for i in range(3)])
            original_scl = Vector([get_val("scale", i, frame, 1.0) for i in range(3)])

            # --- 处理旋转 (支持欧拉和四元数) ---
            if obj.rotation_mode == 'QUATERNION':
                # 四元数的单位元是 (w=1, x=0, y=0, z=0)
                quat_val = [
                    get_val("rotation_quaternion", 0, frame, 1.0), # W
                    get_val("rotation_quaternion", 1, frame, 0.0), # X
                    get_val("rotation_quaternion", 2, frame, 0.0), # Y
                    get_val("rotation_quaternion", 3, frame, 0.0)  # Z
                ]
                original_rot_mat = Quaternion(quat_val).to_matrix().to_4x4()
            else: # 所有欧拉角模式
                euler_val = [get_val("rotation_euler", i, frame, 0.0) for i in range(3)]
                original_rot_mat = Euler(euler_val, obj.rotation_mode).to_matrix().to_4x4()
            
            # 构建完整的原始局部矩阵
            loc_mat_old = Matrix.Translation(original_loc)
            scl_mat_old = Matrix.Scale(original_scl[0], 4, (1, 0, 0)) @ \
                          Matrix.Scale(original_scl[1], 4, (0, 1, 0)) @ \
                          Matrix.Scale(original_scl[2], 4, (0, 0, 1))
            
            matrix_old = loc_mat_old @ original_rot_mat @ scl_mat_old
            
            # 5.2 核心计算: 将“应用的变换”反向作用于每个关键帧
            matrix_new = matrix_to_apply_inv @ matrix_old
            
            # 5.3 从新矩阵分解出L/R/S
            new_loc, new_rot_quat, new_scl = matrix_new.decompose()

            # 5.4 将新的L/R/S值插入（或覆盖）到F-Curves中
            if self.apply_location:
                for i in range(3):
                    fc = action.fcurves.find("location", index=i)
                    if fc: fc.keyframe_points.insert(frame, new_loc[i], options={'REPLACE'})
            
            if self.apply_rotation:
                if obj.rotation_mode == 'QUATERNION':
                    # F-Curve顺序是 W, X, Y, Z
                    fc_w = action.fcurves.find("rotation_quaternion", index=0)
                    fc_x = action.fcurves.find("rotation_quaternion", index=1)
                    fc_y = action.fcurves.find("rotation_quaternion", index=2)
                    fc_z = action.fcurves.find("rotation_quaternion", index=3)
                    
                    if fc_w: fc_w.keyframe_points.insert(frame, new_rot_quat.w, options={'REPLACE'})
                    if fc_x: fc_x.keyframe_points.insert(frame, new_rot_quat.x, options={'REPLACE'})
                    if fc_y: fc_y.keyframe_points.insert(frame, new_rot_quat.y, options={'REPLACE'})
                    if fc_z: fc_z.keyframe_points.insert(frame, new_rot_quat.z, options={'REPLACE'})
                else: # 所有欧拉角模式
                    new_rot_euler = new_rot_quat.to_euler(obj.rotation_mode)
                    for i in range(3):
                        fc = action.fcurves.find("rotation_euler", index=i)
                        if fc: fc.keyframe_points.insert(frame, new_rot_euler[i], options={'REPLACE'})

            if self.apply_scale:
                for i in range(3):
                    fc = action.fcurves.find("scale", index=i)
                    if fc: fc.keyframe_points.insert(frame, new_scl[i], options={'REPLACE'})

        # --- 6. 更新曲线并确保当前帧为“干净”状态 ---
        for fc in all_fcurves:
            fc.update()

        # 在当前帧插入一个干净的关键帧，以匹配应用后的状态
        if self.apply_location:
            obj.location = (0, 0, 0)
            obj.keyframe_insert(data_path="location", frame=current_frame)
        if self.apply_rotation:
            if obj.rotation_mode == 'QUATERNION':
                obj.rotation_quaternion = (1, 0, 0, 0)
                obj.keyframe_insert(data_path="rotation_quaternion", frame=current_frame)
            else: # 所有欧拉角模式
                obj.rotation_euler = (0, 0, 0)
                obj.keyframe_insert(data_path="rotation_euler", frame=current_frame)
        if self.apply_scale:
            obj.scale = (1, 1, 1)
            obj.keyframe_insert(data_path="scale", frame=current_frame)

        self.report({'INFO'}, "变换已应用，关键帧已完美同步！")
        return {'FINISHED'}


# 注册和注销函数
def register():
    bpy.utils.register_class(OBJECT_OT_apply_transform_and_sync_keys)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_apply_transform_and_sync_keys)

# 主程序入口 (用于在Blender文本编辑器中直接运行)
if __name__ == "__main__":
    # 确保先注销，避免重复注册的错误
    try:
        unregister()
    except RuntimeError:
        pass
    register()
    
    # 可选：自动弹窗测试
    area = next((a for a in bpy.context.screen.areas if a.type == 'VIEW_3D'), None)
    if area:
        with bpy.context.temp_override(area=area):
            bpy.ops.object.apply_transform_and_sync_keys('INVOKE_DEFAULT')

