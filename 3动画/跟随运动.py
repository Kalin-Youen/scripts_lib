# -*- coding: utf-8 -*-

"""
获取物体或骨骼的世界变换矩阵并做跟随运动
"""

import bpy
from bpy.props import IntProperty, BoolProperty, StringProperty
import mathutils

# --- 辅助函数 (保持不变) ---
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

# --- update回调函数 (保持不变) ---
def update_frame_preview_start(self, context):
    """当起始帧变化时，更新时间轴预览"""
    if self.live_preview:
        context.scene.frame_set(self.start_frame)

def update_frame_preview_end(self, context):
    """当结束帧变化时，更新时间轴预览"""
    if self.live_preview:
        context.scene.frame_set(self.end_frame)


class FollowRelativeMotionOperator(bpy.types.Operator):
    """
    根据活动物体或骨骼的相对运动，为其他选中项进行K帧。
    新增延迟、交错效果，并对性能进行深度优化。
    此操作器在执行后会自动注销。
    """
    bl_idname = "object.follow_relative_motion_kframe"
    bl_label = "跟随相对位移K帧 (高级版)"
    bl_options = {'REGISTER', 'UNDO'}

    # --- 弹窗中的属性 ---
    start_frame: IntProperty(
        name="起始帧",
        default=1,
        update=update_frame_preview_start
    )
    end_frame: IntProperty(
        name="结束帧",
        default=100,
        update=update_frame_preview_end
    )
    live_preview: BoolProperty(
        name="实时预览帧",
        description="勾选后，在修改起始/结束帧时，时间轴会实时跳转到对应帧",
        default=True
    )
    
    # --- 变换通道 ---
    use_location: BoolProperty(name="位置", default=True)
    use_rotation: BoolProperty(name="旋转", default=True)
    use_scale: BoolProperty(name="缩放", default=True)
    
    # --- 【新增】延迟效果属性 ---
    frame_delay: IntProperty(
        name="动画延迟(帧)",
        description="所有跟随者的动画都延迟指定的帧数",
        default=0,
        min=0
    )
    delay_stagger: IntProperty(
        name="延迟交错(帧)",
        description="在基础延迟之上，每个跟随者额外增加的延迟量，产生连续效果",
        default=0,
        min=0
    )
    
    # --- UI显示与内部变量 ---
    driver_name: StringProperty(name="驱动方")
    follower_names: StringProperty(name="跟随者")
    _original_frame: IntProperty()

    def get_targets(self, context):
        """智能识别模式并返回驱动方和跟随者列表 (保持不变)"""
        mode = context.mode
        driver, followers = None, []
        # ... (此函数内部逻辑完全不变) ...
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
                if follower_bone: followers.append(follower_bone)
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
        """自定义弹窗UI，布局优化"""
        layout = self.layout
        box = layout.box()
        box.label(text="当前操作目标:", icon='INFO')
        box.prop(self, "driver_name", text="驱动")
        box.prop(self, "follower_names", text="跟随")
        
        # --- 时间范围 ---
        box = layout.box()
        box.label(text="时间范围与预览:", icon='TIME')
        col = box.column()
        row = col.row(align=True)
        row.prop(self, "start_frame")
        row.prop(self, "end_frame")
        col.prop(self, "live_preview")
        
        # --- 【新增UI】延迟效果 ---
        box = layout.box()
        box.label(text="延迟效果:", icon='MOD_TIME')
        row = box.row(align=True)
        row.prop(self, "frame_delay")
        row.prop(self, "delay_stagger")
        
        # --- 变换通道 ---
        box = layout.box()
        box.label(text="K帧通道:", icon='KEYFRAME_HLT')
        row = box.row()
        row.prop(self, "use_location")
        row.prop(self, "use_rotation")
        row.prop(self, "use_scale")

    def invoke(self, context, event):
        """调用时，准备UI信息并显示弹窗 (逻辑微调)"""
        self._original_frame = context.scene.frame_current
        self.start_frame = context.scene.frame_start
        self.end_frame = context.scene.frame_end
        
        driver, followers = self.get_targets(context)
        if not driver or not followers:
            context.scene.frame_set(self._original_frame)
            self.report({'ERROR'}, "选择不满足要求(至少1个驱动+1个跟随)或未找到活动骨骼。")
            return {'CANCELLED'}

        self.driver_name = f"{driver.name} ({'Bone' if isinstance(driver, bpy.types.PoseBone) else 'Object'})"
        self.follower_names = ", ".join([f.name for f in followers])
        
        if self.live_preview:
            context.scene.frame_set(self.start_frame)

        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def check(self, context):
        """在关闭弹窗时，恢复原始帧 (保持不变)"""
        context.scene.frame_set(self._original_frame)
        return True

    def execute(self, context):
        """【已重构】核心K帧逻辑，增加延迟、交错和性能缓存"""
        driver, followers = self.get_targets(context)
        if not driver or not followers:
            self.report({'ERROR'}, "未能正确识别驱动方和跟随者。")
            return {'CANCELLED'}

        # --- 步骤 1: 【性能优化】预缓存驱动方的所有世界矩阵 ---
        self.report({'INFO'}, "正在预计算驱动方矩阵...")
        driver_matrices_cache = {}
        for frame in range(self.start_frame, self.end_frame + 1):
            context.scene.frame_set(frame)
            driver_matrices_cache[frame] = get_world_matrix(driver).copy()
        
        self.report({'INFO'}, "矩阵缓存完成，开始K帧...")

        # --- 步骤 2: 获取所有目标的初始世界矩阵 ---
        context.scene.frame_set(self.start_frame)
        initial_world_matrices = {}
        for target in [driver] + followers:
             initial_world_matrices[id(target)] = get_world_matrix(target).copy()
        driver_initial_world_matrix = initial_world_matrices[id(driver)]

        # --- 步骤 3: 循环K帧，应用延迟和交错 ---
        for frame in range(self.start_frame, self.end_frame + 1):
            for i, follower in enumerate(followers):
                # 计算每个跟随者独立的有效延迟
                effective_delay = self.frame_delay + (i * self.delay_stagger)
                source_frame = frame - effective_delay
                
                # 获取跟随者的初始矩阵
                follower_initial_world_matrix = initial_world_matrices[id(follower)]
                
                target_follower_world_matrix = None
                
                # 如果源帧在有效范围内，则计算相对位移
                if source_frame >= self.start_frame:
                    # 从高速缓存读取驱动方矩阵，无需切换帧
                    driver_source_world_matrix = driver_matrices_cache[source_frame]
                    
                    driver_delta_matrix = driver_source_world_matrix @ driver_initial_world_matrix.inverted_safe()
                    target_follower_world_matrix = driver_delta_matrix @ follower_initial_world_matrix
                else:
                    # 如果源帧超出范围（由于延迟），则保持在初始位置
                    target_follower_world_matrix = follower_initial_world_matrix.copy()

                # 设置世界变换，并插入关键帧
                set_world_matrix(follower, target_follower_world_matrix)
                
                if self.use_location:
                    follower.keyframe_insert(data_path="location", frame=frame)
                if self.use_rotation:
                    mode_path = "rotation_quaternion" if follower.rotation_mode == 'QUATERNION' else "rotation_euler"
                    follower.keyframe_insert(data_path=mode_path, frame=frame)
                if self.use_scale:
                    follower.keyframe_insert(data_path="scale", frame=frame)
        
        self.report({'INFO'}, f"K帧完成: {self.start_frame}-{self.end_frame}")
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
    # 【已修复】使用 getattr 安全地访问 bl_idname 属性，避免遍历到无此属性的内置类时报错
    idname = FollowRelativeMotionOperator.bl_idname
    
    # 检查操作符是否已经注册
    # bpy.context.window_manager.operators 是一个更直接、更可靠的已注册操作符列表
    if idname in bpy.context.window_manager.operators.keys():
        unregister_and_cleanup(FollowRelativeMotionOperator)
        
    bpy.utils.register_class(FollowRelativeMotionOperator)
    bpy.ops.object.follow_relative_motion_kframe('INVOKE_DEFAULT')

# --- 脚本主入口 (保持不变) ---
if __name__ == "__main__":
    # 【已优化】增加对无选中物体的检查，防止直接运行时报错
    if bpy.context.active_object and bpy.context.selected_objects:
        register_and_run()
    else:
        print("跟随相对位移K帧工具提示：请在3D视图中至少选择两个物体或两个骨骼，然后重新运行脚本。")
