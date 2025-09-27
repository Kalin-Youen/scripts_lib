# script_id: 21e1ccdc-5e6f-46d6-85c1-684a60813465
# -*- coding: utf-8 -*-

import bpy
from bpy.props import IntProperty, BoolProperty, StringProperty
import mathutils

def get_world_matrix(target):
    """获取物体或骨骼的世界变换矩阵"""
    if isinstance(target, bpy.types.PoseBone):
        return target.id_data.matrix_world @ target.matrix
    else:
        return target.matrix_world

def set_world_matrix(target, world_matrix):
    """根据世界变换矩阵设置物体或骨骼的局部变换"""
    if isinstance(target, bpy.types.PoseBone):
        armature_world = target.id_data.matrix_world
        target.matrix = armature_world.inverted_safe() @ world_matrix
    else:
        target.matrix_world = world_matrix


class FollowRelativeMotionOperator(bpy.types.Operator):
    """
    根据活动物体或骨骼的相对运动，为其他选中项进行K帧。
    智能识别模式，并在弹窗中提供清晰反馈。
    此操作器在执行后会自动注销。
    """
    bl_idname = "object.follow_relative_motion_kframe"
    bl_label = "跟随相对位移K帧"
    bl_options = {'REGISTER', 'UNDO'}

    start_frame: IntProperty(name="起始帧", default=1)
    end_frame: IntProperty(name="结束帧", default=100)
    use_location: BoolProperty(name="位置", default=True)
    use_rotation: BoolProperty(name="旋转", default=True)
    use_scale: BoolProperty(name="缩放", default=True)
    
    driver_name: StringProperty(name="驱动方")
    follower_names: StringProperty(name="跟随者")

    def get_targets(self, context):
        """智能识别模式并返回驱动方和跟随者列表"""
        mode = context.mode
        driver, followers = None, []

        if mode == 'OBJECT' and len(context.selected_objects) >= 2 and all(o.type == 'ARMATURE' for o in context.selected_objects):
            driver_arm = context.active_object
            follower_arms = [o for o in context.selected_objects if o != driver_arm]
            if not driver_arm.data.bones.active:
                self.report({'ERROR'}, f"驱动骨架 '{driver_arm.name}' 没有设置活动骨骼！")
                return None, None
            driver = driver_arm.pose.bones.get(driver_arm.data.bones.active.name)
            for arm in follower_arms:
                if not arm.data.bones.active:
                    self.report({'ERROR'}, f"跟随骨架 '{arm.name}' 没有设置活动骨骼！")
                    return None, None
                follower_bone = arm.pose.bones.get(arm.data.bones.active.name)
                if follower_bone:
                    followers.append(follower_bone)
            return driver, followers
        elif mode == 'POSE':
            driver = context.active_pose_bone
            followers = [pb for pb in context.selected_pose_bones if pb != driver]
            return driver, followers
        elif mode == 'OBJECT':
            driver = context.active_object
            followers = [obj for obj in context.selected_objects if obj != driver]
            return driver, followers
        return None, None

    def draw(self, context):
        """自定义弹窗UI，显示驱动/跟随信息"""
        layout = self.layout
        box = layout.box()
        box.label(text="当前操作目标:", icon='INFO')
        box.prop(self, "driver_name")
        box.prop(self, "follower_names")
        layout.separator()
        col = layout.column()
        col.prop(self, "start_frame")
        col.prop(self, "end_frame")
        row = layout.row()
        row.prop(self, "use_location")
        row.prop(self, "use_rotation")
        row.prop(self, "use_scale")

    def invoke(self, context, event):
        """调用时，准备UI信息并显示弹窗"""
        self.start_frame = context.scene.frame_current
        self.end_frame = context.scene.frame_end
        
        driver, followers = self.get_targets(context)
        if driver and followers:
            self.driver_name = f"{driver.name} ({'Bone' if isinstance(driver, bpy.types.PoseBone) else 'Object'})"
            self.follower_names = ", ".join([f.name for f in followers])
        else:
            self.report({'ERROR'}, "选择不满足要求或未找到活动骨骼。请检查您的选择。")
            return {'CANCELLED'}

        return context.window_manager.invoke_props_dialog(self, width=400)

    def execute(self, context):
        """核心K帧逻辑 - 已支持反向帧范围"""
        driver, followers = self.get_targets(context)
        if not driver or not followers:
            self.report({'ERROR'}, "未能正确识别驱动方和跟随者。")
            return {'CANCELLED'}

        original_frame = context.scene.frame_current
        
        # --- 优化：在循环开始前，先跳转到起始帧记录所有目标的初始世界变换矩阵 ---
        context.scene.frame_set(self.start_frame)
        initial_world_matrices = {}
        for target in [driver] + followers:
            initial_world_matrices[id(target)] = get_world_matrix(target).copy()

        # --- 核心修改：智能处理正向和反向帧范围 ---
        # 1. 判断方向，确定步长
        step = 1 if self.end_frame >= self.start_frame else -1
        # 2. 创建能处理正反向的迭代器
        frame_iterator = range(self.start_frame, self.end_frame + step, step)

        try:
            # 3. 遍历指定的帧范围
            for frame in frame_iterator:
                context.scene.frame_set(frame)
                
                # 获取驱动对象在当前帧的世界变换
                driver_current_world_matrix = get_world_matrix(driver)
                
                # 获取驱动对象在起始帧的世界变换
                driver_initial_world_matrix = initial_world_matrices[id(driver)]
                
                # 计算驱动对象相对于起始帧的变换矩阵
                driver_delta_matrix = driver_current_world_matrix @ driver_initial_world_matrix.inverted_safe()

                for follower in followers:
                    # 获取跟随对象在起始帧的世界变换
                    follower_initial_world_matrix = initial_world_matrices[id(follower)]
                    
                    # 计算跟随者的目标世界变换
                    target_follower_world_matrix = driver_delta_matrix @ follower_initial_world_matrix
                    
                    # 设置世界变换
                    set_world_matrix(follower, target_follower_world_matrix)
                    
                    # 根据用户选择进行K帧
                    if self.use_location:
                        follower.keyframe_insert(data_path="location", frame=frame)
                    if self.use_rotation:
                        if follower.rotation_mode == 'QUATERNION':
                            follower.keyframe_insert(data_path="rotation_quaternion", frame=frame)
                        else:
                            follower.keyframe_insert(data_path="rotation_euler", frame=frame)
                    if self.use_scale:
                        follower.keyframe_insert(data_path="scale", frame=frame)
                        
        finally:
            context.scene.frame_set(original_frame)
            direction = "正向" if step > 0 else "反向"
            self.report({'INFO'}, f"{direction}K帧完成: {self.start_frame} -> {self.end_frame}")
            
            bpy.app.timers.register(lambda: unregister_and_cleanup(self.__class__), first_interval=0.1)
            
        return {'FINISHED'}

# --- 自动注册和注销的辅助函数 ---
def unregister_and_cleanup(operator_class):
    try:
        bpy.utils.unregister_class(operator_class)
        print(f"操作器 {operator_class.bl_idname} 已成功注销。")
    except RuntimeError:
        pass

def register_and_run():
    # 确保旧的实例被清理，防止重复注册
    if hasattr(bpy.types, FollowRelativeMotionOperator.__name__):
        unregister_and_cleanup(FollowRelativeMotionOperator)
        
    bpy.utils.register_class(FollowRelativeMotionOperator)
    bpy.ops.object.follow_relative_motion_kframe('INVOKE_DEFAULT')

# --- 脚本主入口 ---
if __name__ == "__main__":
    register_and_run()
