# script_id: fd45dda1-bc95-4fc7-8e24-b554b877608f
import bpy
import bmesh
from bpy.props import FloatProperty, BoolProperty

# 定义操作类
class MoveVertsNormalOperator(bpy.types.Operator):
    """Move Vertices along Normal"""
    bl_idname = "mesh.move_verts_normal_operator"
    bl_label = "Move Vertices Along Normal"
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    factor: FloatProperty(
        name="Factor",
        description="Distance to move along normal",
        default=0.04,
        min=-1000.0,
        max=1000.0,
        soft_min=-10.0,
        soft_max=10.0
    )

    prop_select: BoolProperty(
        name="Select Result",
        description="Select the resulting vertices after move",
        default=False
    )

    def get_bm(self):
        obj = bpy.context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        return bm

    def execute(self, context):
        self.process(context)
        return {'FINISHED'}

    def process(self, context):
        ob = bpy.context.object
        me = ob.data
        bm = self.get_bm()

        for v in bm.verts:
            if v.select:
                v.co += v.normal * self.factor  # Move along normal direction

        bmesh.update_edit_mesh(me)

        if self.prop_select:
            for v in bm.verts:
                if v.select:
                    v.select = True

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return (active_object is not None and
                active_object.type == 'MESH' and
                context.mode == 'EDIT_MESH')

    def invoke(self, context, event):
        if context.mode == 'EDIT_MESH':
            self.factor = 0.04  # Default factor
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            return {'CANCELLED'}

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'Q' and event.value == 'PRESS':
            self.restore()
            return {'CANCELLED'}
        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.process(context)
            return {'FINISHED'}
        elif event.type == 'MOUSEMOVE':
            self.on_move(context, event)
            return {'PASS_THROUGH'}
        elif event.type == 'ESC' and event.value == 'PRESS':
            self.restore()
            return {'CANCELLED'}
        return {'PASS_THROUGH'}

    def on_move(self, context, event):
        region = context.region
        mx, my = event.mouse_region_x, event.mouse_region_y
        region_width = region.width

        # 基于鼠标移动的比例来调整 factor
        # 对鼠标位置做适当的平滑缩放
        scale_factor = 0.02  # 缩放因子，控制数值变化的敏感度
        self.factor = (mx / region_width - 0.5) * scale_factor  # 让 factor 的变化范围更加平滑
        self.process(context)

    def restore(self):
        bpy.ops.object.mode_set(mode='OBJECT')
        me = bpy.context.active_object.data
        bmesh.update_edit_mesh(me)
        bpy.ops.object.mode_set(mode='EDIT')

# 定义面板类
class VIEW3D_PT_move_verts_normal_panel(bpy.types.Panel):
    """Panel for Move Vertices Along Normal"""
    bl_label = "Move Vertices Along Normal"
    bl_idname = "VIEW3D_PT_move_verts_normal_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'  # 定义面板所在的类别

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # 添加操作按钮到面板
        layout.operator("mesh.move_verts_normal_operator", text="Move Vertices Along Normal")

# 注册操作类和面板类
def register():
    bpy.utils.register_class(MoveVertsNormalOperator)
    bpy.utils.register_class(VIEW3D_PT_move_verts_normal_panel)

def unregister():
    bpy.utils.unregister_class(MoveVertsNormalOperator)
    bpy.utils.unregister_class(VIEW3D_PT_move_verts_normal_panel)

if __name__ == "__main__":
    register()
