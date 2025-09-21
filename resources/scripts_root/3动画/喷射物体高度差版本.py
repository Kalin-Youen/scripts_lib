import bpy
import random
import math
from mathutils import Vector, Euler

class OBJECT_OT_quick_eruption(bpy.types.Operator):
    """
    为选中物体快速创建依次喷发的爆炸动画效果
    """
    bl_idname = "object.quick_eruption"
    bl_label = "快速喷发效果"
    bl_options = {'REGISTER', 'UNDO'}

    # --- 可调整的参数 ---
    count: bpy.props.IntProperty(
        name="数量",
        description="要复制并喷发的物体数量",
        default=6,
        min=1,
        max=1000
    )
    
    start_frame: bpy.props.IntProperty(
        name="起始帧",
        description="喷发动画开始的帧",
        default=1
    )

    animation_duration: bpy.props.IntProperty(
        name="动画时长",
        description="每个物体从发射到消失的总帧数",
        default=60,
        min=20
    )
    
    fade_out_duration: bpy.props.IntProperty(
        name="淡出时长(帧)",
        description="物体在动画末尾缩小至消失所需的时间",
        default=1,
        min=1,
    )

    launch_stagger: bpy.props.IntProperty(
        name="发射延迟(帧)",
        description="在多少帧内完成所有物体的发射，用于创建'依次'的效果",
        default=20,
        min=0
    )

    # --- 物理与轨迹参数 ---
    launch_speed: bpy.props.FloatProperty(
        name="发射速度",
        description="物体喷发的初始力量",
        default=10.0,
        min=0.0
    )
    
    spread_angle: bpy.props.FloatProperty(
        name="扩散角度",
        description="喷发的锥形扩散角度。0度=垂直向上，180度=半球形扩散",
        default=9.0,
        min=0.0,
        max=180.0,
        subtype='ANGLE'
    )
    
    gravity: bpy.props.FloatProperty(
        name="重力",
        description="向下的加速度，模拟重力效果",
        default=12.0,
        min=0.0
    )

    # 【【【新增：高度控制参数】】】
    height_consistency: bpy.props.FloatProperty(
        name="高度一致性",
        description="控制所有物体达到相似高度的程度。1.0=完全相同高度，0.0=完全随机高度",
        default=0.85,
        min=0.0,
        max=1.0,
        subtype='FACTOR'
    )
    
    target_max_height: bpy.props.FloatProperty(
        name="目标最大高度",
        description="物体应该达到的理想最大高度（仅在高度一致性>0时有效）",
        default=7.0,
        min=1.0
    )

    # --- 噪波/随机性参数 ---
    trajectory_noise: bpy.props.FloatProperty(
        name="速度噪波",
        description="为每个物体的初始发射速度增加随机扰动",
        default=0.2,
        min=0.0,
        max=1.0,
        subtype='FACTOR'
    )

    rotation_speed_noise: bpy.props.FloatProperty(
        name="旋转速度噪波",
        description="随机旋转速度的最大值 (度/秒)",
        default=7.0,
        min=0.0,
        subtype='ANGLE',
        unit='ROTATION'
    )

    scale_noise: bpy.props.FloatProperty(
        name="缩放噪波",
        description="最终物体大小的随机变化范围 (例如0.5表示大小在0.5到1.5倍之间)",
        default=0.3,
        min=0.0
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.mode == 'OBJECT'

    def invoke(self, context, event):
        self.start_frame = context.scene.frame_current
        return context.window_manager.invoke_props_dialog(self)

    def calculate_required_speed_for_height(self, direction_vector, target_height):
        """
        根据目标高度和重力，计算达到该高度所需的初始速度
        使用物理公式：v² = 2gh (在最高点时速度为0)
        """
        if self.gravity <= 0:
            return self.launch_speed  # 无重力时使用默认速度
        
        # 计算垂直分量需要的速度
        required_vertical_speed = math.sqrt(2 * self.gravity * target_height)
        
        # 根据方向向量的Z分量，计算总速度
        vertical_component = abs(direction_vector.z)
        
        if vertical_component < 0.1:  # 几乎水平发射
            return self.launch_speed
        
        required_total_speed = required_vertical_speed / vertical_component
        return required_total_speed

    def execute(self, context):
        original_obj = context.active_object
        scene = context.scene
        fps = scene.render.fps
        
        collection_name = f"{original_obj.name}_Eruption"
        eruption_collection = bpy.data.collections.new(collection_name)
        scene.collection.children.link(eruption_collection)

        for i in range(self.count):
            new_obj = original_obj.copy()
            new_obj.data = original_obj.data.copy()
            eruption_collection.objects.link(new_obj)

            launch_frame_offset = 0
            if self.count > 1 and self.launch_stagger > 0:
                 launch_frame_offset = (i / (self.count - 1)) * self.launch_stagger
            launch_frame = self.start_frame + launch_frame_offset
            
            end_frame = launch_frame + self.animation_duration
            fade_start_frame = end_frame - self.fade_out_duration

            # --- 生成方向向量 ---
            cone_angle_rad = math.radians(self.spread_angle / 2.0)
            cos_theta_max = math.cos(cone_angle_rad)
            
            z = random.uniform(cos_theta_max, 1.0)
            phi = random.uniform(0, 2 * math.pi)
            sqrt_one_minus_z_sq = math.sqrt(1 - z*z)
            x = sqrt_one_minus_z_sq * math.cos(phi)
            y = sqrt_one_minus_z_sq * math.sin(phi)
            direction_vector = Vector((x, y, z))
            
            # --- 【【【新的速度计算逻辑】】】 ---
            if self.height_consistency > 0.0:
                # 计算达到目标高度所需的速度
                target_speed = self.calculate_required_speed_for_height(direction_vector, self.target_max_height)
                
                # 在目标速度和原始速度之间插值
                consistent_speed = target_speed * self.height_consistency + self.launch_speed * (1.0 - self.height_consistency)
                
                # 应用噪波
                final_speed = consistent_speed * random.uniform(1.0 - self.trajectory_noise, 1.0 + self.trajectory_noise)
            else:
                # 完全使用原始的随机速度逻辑
                final_speed = self.launch_speed * random.uniform(1.0 - self.trajectory_noise, 1.0 + self.trajectory_noise)
            
            velocity = direction_vector * final_speed
            
            # --- 旋转和缩放的随机计算（保持不变）---
            rot_speed_x = random.uniform(-self.rotation_speed_noise, self.rotation_speed_noise) / fps
            rot_speed_y = random.uniform(-self.rotation_speed_noise, self.rotation_speed_noise) / fps
            rot_speed_z = random.uniform(-self.rotation_speed_noise, self.rotation_speed_noise) / fps
            final_scale_multiplier = 1.0 + random.uniform(-self.scale_noise, self.scale_noise)
            final_scale = original_obj.scale * final_scale_multiplier

            # --- 设置关键帧 ---
            new_obj.rotation_mode = 'XYZ'
            current_rotation = Euler((0,0,0), 'XYZ')

            new_obj.scale = (0, 0, 0)
            new_obj.keyframe_insert(data_path="scale", frame=launch_frame - 1)
            new_obj.location = original_obj.location
            new_obj.keyframe_insert(data_path="location", frame=launch_frame - 1)

            # 遍历生命周期
            for f_offset in range(self.animation_duration + 1):
                frame = launch_frame + f_offset
                time_since_launch = f_offset / fps

                pos_offset = velocity * time_since_launch + 0.5 * Vector((0, 0, -self.gravity)) * (time_since_launch**2)
                new_obj.location = original_obj.location + pos_offset
                new_obj.keyframe_insert(data_path="location", frame=frame)
                
                current_rotation.x += rot_speed_x
                current_rotation.y += rot_speed_y
                current_rotation.z += rot_speed_z
                new_obj.rotation_euler = current_rotation
                new_obj.keyframe_insert(data_path="rotation_euler", frame=frame)

            # 单独处理缩放关键帧
            new_obj.scale = final_scale
            new_obj.keyframe_insert(data_path="scale", frame=launch_frame)
            if fade_start_frame > launch_frame:
                new_obj.keyframe_insert(data_path="scale", frame=fade_start_frame)
            new_obj.scale = (0,0,0)
            new_obj.keyframe_insert(data_path="scale", frame=end_frame)

        original_obj.hide_viewport = True
        original_obj.hide_render = True

        self.report({'INFO'}, f"成功创建了 {self.count} 个物体的喷发效果！高度一致性: {self.height_consistency:.1f}")
        return {'FINISHED'}


# --- 注册与运行 ---
def register():
    bpy.utils.register_class(OBJECT_OT_quick_eruption)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_quick_eruption)

if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register()

    bpy.ops.object.quick_eruption('INVOKE_DEFAULT')
