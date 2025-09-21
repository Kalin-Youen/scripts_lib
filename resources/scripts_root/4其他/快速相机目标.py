# 快速相机目标
# 快速相机目标
# 4相机
import bpy

# 获取当前选中的相机对象
selected_cameras = [obj for obj in bpy.context.selected_objects if obj.type == 'CAMERA']
object_collection = selected_cameras[0].users_collection[0] if selected_cameras[0].users_collection else None
if selected_cameras:
    # 获取第一个选中的相机对象
    active_camera = selected_cameras[0]

    # 在相机所在的集合中创建一个空物体
    empty = bpy.data.objects.new("Empty", None)
    empty.name = active_camera.name+"跟随点"
    object_collection.objects.link(empty)
    # original_cursor_location = bpy.context.scene.cursor.location.copy()
    empty.location = selected_cameras.location
    # 复制相机的旋转给空物体
    empty.rotation_euler = selected_cameras.rotation_euler
    # 给相机添加一个追踪约束
    track_constraint = active_camera.constraints.new('DAMPED_TRACK')
    track_constraint.target = empty
    track_constraint.track_axis = 'TRACK_NEGATIVE_Z'


    # 设置约束的跟随和目标

    track_constraint.target = empty
