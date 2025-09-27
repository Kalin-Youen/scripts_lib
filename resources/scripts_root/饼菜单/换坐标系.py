# script_id: 475cdabf-d289-4617-83b4-43fb4f6f82cb
# 文件名: quick_transform_toggle_popup_fixed.py
import bpy
from bpy.props import EnumProperty

class VIEW3D_OT_QuickTransformToggle(bpy.types.Operator):
    bl_idname = "view3d.quick_transform_toggle"
    bl_label = "快速变换模式切换"
    bl_options = {'REGISTER', 'UNDO'}

    pivot_items = [
        ('MEDIAN_POINT', "质心点", "Median Point"),
        ('CURSOR', "3D游标", "3D Cursor"),
        ('INDIVIDUAL_ORIGINS', "各自的原点", "Individual Origins"),
        ('ACTIVE_ELEMENT', "活动元素", "Active Element"),
        ('BOUNDING_BOX_CENTER', "边界盒中心", "Bounding Box Center"),
    ]

    orientation_items = [
        ('LOCAL', "局部", "Local"),
        ('GLOBAL', "全局", "Global"),
        ('NORMAL', "法向", "Normal"),
        ('GIMBAL', "万向", "Gimbal"),
        ('VIEW', "视图", "View"),
    ]

    mode_a_pivot: EnumProperty(
        name="模式A 旋转中心",
        items=pivot_items,
        default='MEDIAN_POINT'
    )
    mode_a_orientation: EnumProperty(
        name="模式A 坐标系",
        items=orientation_items,
        default='LOCAL'
    )
    mode_b_pivot: EnumProperty(
        name="模式B 旋转中心",
        items=pivot_items,
        default='CURSOR'
    )
    mode_b_orientation: EnumProperty(
        name="模式B 坐标系",
        items=orientation_items,
        default='LOCAL'
    )
    no_selection_pivot: EnumProperty(
        name="无选择时 旋转中心",
        items=pivot_items,
        default='MEDIAN_POINT'
    )
    no_selection_orientation: EnumProperty(
        name="无选择时 坐标系",
        items=orientation_items,
        default='GLOBAL'
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        tool_settings = context.scene.tool_settings
        orientation_slots = context.scene.transform_orientation_slots
        
        if context.selected_objects:
            current_pivot = tool_settings.transform_pivot_point
            current_orientation = orientation_slots[0].type
            
            is_mode_a = (current_pivot == self.mode_a_pivot and
                         current_orientation == self.mode_a_orientation)
            
            if is_mode_a:
                tool_settings.transform_pivot_point = self.mode_b_pivot
                orientation_slots[0].type = self.mode_b_orientation
                self.report({'INFO'}, f"切换到: {self.mode_b_pivot}, {self.mode_b_orientation}")
            else:
                tool_settings.transform_pivot_point = self.mode_a_pivot
                orientation_slots[0].type = self.mode_a_orientation
                self.report({'INFO'}, f"切换到: {self.mode_a_pivot}, {self.mode_a_orientation}")
        else:
            tool_settings.transform_pivot_point = self.no_selection_pivot
            orientation_slots[0].type = self.no_selection_orientation
            self.report({'INFO'}, f"无选择: {self.no_selection_pivot}, {self.no_selection_orientation}")
            
        return {'FINISHED'}

if __name__ == '__main__':
    try:
        bpy.utils.unregister_class(VIEW3D_OT_QuickTransformToggle)
    except Exception:
        pass
    
    bpy.utils.register_class(VIEW3D_OT_QuickTransformToggle)
    
    view3d_area = next((area for area in bpy.context.screen.areas if area.type == 'VIEW_3D'), None)

    if view3d_area:
        with bpy.context.temp_override(area=view3d_area):
            #bpy.ops.view3d.quick_transform_toggle('INVOKE_DEFAULT')
            bpy.ops.view3d.quick_transform_toggle()

