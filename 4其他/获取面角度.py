# 获取面角度
# 获取面角度
# 2网格
import bpy
import math
import mathutils

def angle_between_vectors(v1, v2):
    dot_product = v1.dot(v2)
    cos_angle = dot_product / (v1.length * v2.length)
    angle = math.acos(min(max(cos_angle, -1.0), 1.0))
    return math.degrees(angle)

def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)



# 获取当前激活的对象（假设是网格对象）
obj = bpy.context.active_object

# 检查是否在编辑模式下
if bpy.context.mode == 'EDIT_MESH':
    # 获取编辑模式下的网格数据
    mesh = bpy.context.edit_object.data

    # 获取所选面的索引
    selected_faces = [f.index for f in mesh.polygons if f.select]

    # 获取法线
    for face_index in selected_faces:
        normal = mesh.polygons[face_index].normal
        x=normal.x
        y=normal.y
        z=normal.z
        angle_x = angle_between_vectors(normal, mathutils.Vector((1, 0, 0)))
        angle_y = angle_between_vectors(normal, mathutils.Vector((0, 1, 0)))

        a = f"面 {face_index} 的法线：{x},{y},{z}\n与X轴的角度：{angle_x} 度\n与Y轴的角度：{angle_y} 度"
        
        ShowMessageBox(a, "获取面角度", 'INFO')
else:
    ShowMessageBox("编辑模式下", "编辑模式下", 'ERROR')
