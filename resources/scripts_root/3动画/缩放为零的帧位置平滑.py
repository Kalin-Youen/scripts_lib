import bpy
from mathutils import Vector

class OBJECT_OT_smooth_zero_scale_location(bpy.types.Operator):
    bl_idname = "object.smooth_zero_scale_location"
    bl_label = "Smooth Location at Zero Scale"
    bl_options = {'REGISTER', 'UNDO'}

    start_frame: bpy.props.IntProperty(
        name="Start Frame",
        description="Frame range to scan for zero-scale keys",
        default=0
    )
    end_frame: bpy.props.IntProperty(
        name="End Frame",
        description="Frame range to scan for zero-scale keys",
        default=100
    )
    search_limit: bpy.props.IntProperty(
        name="Search Limit",
        description="Max frames to search for neighbor location keys",
        default=3,
        min=1
    )
    threshold: bpy.props.FloatProperty(
        name="Zero Threshold",
        description="Scale values below this are considered zero",
        default=0.0001,
        min=0.0,
        subtype='FACTOR'
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def invoke(self, context, event):
        scene = context.scene
        self.start_frame = scene.frame_start
        self.end_frame = scene.frame_end
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.active_object
        if not obj.animation_data or not obj.animation_data.action:
            self.report({'WARNING'}, "Object has no animation data.")
            return {'CANCELLED'}

        action = obj.animation_data.action
        loc_fcurves = [fc for fc in action.fcurves if fc.data_path == "location"]
        scale_fcurves = [fc for fc in action.fcurves if fc.data_path == "scale"]

        if not scale_fcurves or not loc_fcurves:
            self.report({'WARNING'}, "Missing location or scale keyframes.")
            return {'CANCELLED'}

        all_loc_keyframes = {int(round(kp.co.x)) for fc in loc_fcurves for kp in fc.keyframe_points}
        all_scale_keyframes = {int(round(kp.co.x)) for fc in scale_fcurves for kp in fc.keyframe_points}
        
        scale_keyframes_in_range = sorted([
            f for f in all_scale_keyframes if self.start_frame <= f <= self.end_frame
        ])
        
        zero_scale_frames_to_check = []
        for frame in scale_keyframes_in_range:
            current_scale = Vector([fc.evaluate(frame) for fc in scale_fcurves])
            if current_scale.length < self.threshold:
                zero_scale_frames_to_check.append(frame)
        
        if not zero_scale_frames_to_check:
            self.report({'INFO'}, "No zero-scale frames found in range.")
            return {'FINISHED'}
            
        modified_frames = []
        for frame in zero_scale_frames_to_check:
            left_neighbor_frame = None
            right_neighbor_frame = None
            
            for i in range(1, self.search_limit + 1):
                if (frame - i) in all_loc_keyframes:
                    left_neighbor_frame = frame - i
                    break
            
            for i in range(1, self.search_limit + 1):
                if (frame + i) in all_loc_keyframes:
                    right_neighbor_frame = frame + i
                    break

            new_pos = None
            if left_neighbor_frame is not None and right_neighbor_frame is not None:
                left_pos = Vector([fc.evaluate(left_neighbor_frame) for fc in loc_fcurves])
                right_pos = Vector([fc.evaluate(right_neighbor_frame) for fc in loc_fcurves])
                new_pos = (left_pos + right_pos) / 2.0
            elif left_neighbor_frame is not None:
                new_pos = Vector([fc.evaluate(left_neighbor_frame) for fc in loc_fcurves])
            elif right_neighbor_frame is not None:
                new_pos = Vector([fc.evaluate(right_neighbor_frame) for fc in loc_fcurves])
            
            if new_pos is not None:
                obj.location = new_pos
                obj.keyframe_insert(data_path="location", frame=frame)
                modified_frames.append(frame)
                
        self.report({'INFO'}, f"Operation finished. Modified {len(modified_frames)} frames.")
        return {'FINISHED'}

if __name__ == '__main__':
    try:
        bpy.utils.unregister_class(OBJECT_OT_smooth_zero_scale_location)
    except (RuntimeError, AttributeError):
        pass
    
    bpy.utils.register_class(OBJECT_OT_smooth_zero_scale_location)
    
    area = next((a for a in bpy.context.screen.areas if a.type == 'VIEW_3D'), None)
    if area:
        with bpy.context.temp_override(area=area):
            bpy.ops.object.smooth_zero_scale_location('INVOKE_DEFAULT')
