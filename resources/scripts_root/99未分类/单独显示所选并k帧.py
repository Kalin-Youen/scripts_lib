# script_id: c5fa4de6-b464-4f76-ac84-20f0fa46d104
import bpy

# 确保在场景中创建并检查标记属性
def ensure_visibility_marker():
    if "VisibilityMarker" not in bpy.context.scene:
        bpy.context.scene["VisibilityMarker"] = 0

def store_visibility_state():
    """存储当前场景中物体在视图中的可见状态"""
    visibility_state = {}
    for obj in bpy.data.objects:
        visibility_state[obj.name] = {
            "hide_viewport": obj.hide_viewport,
            "hide_render": obj.hide_render
        }
    bpy.context.scene["StoredVisibilityState"] = visibility_state
    print("已存储当前的物体视图和渲染可见状态")

def restore_visibility_state():
    """恢复存储的视图可见状态"""
    visibility_state = bpy.context.scene.get("StoredVisibilityState", None)
    if visibility_state is None:
        print("没有存储的可见状态，无法恢复")
        return
    
    for obj in bpy.data.objects:
        if obj.name in visibility_state:
            obj.hide_viewport = visibility_state[obj.name]["hide_viewport"]
            obj.hide_render = visibility_state[obj.name]["hide_render"]
    print("已恢复存储的物体视图和渲染可见状态")

def set_visibility_marker(value):
    """设置标记值"""
    bpy.context.scene["VisibilityMarker"] = value

def insert_keyframes_for_visibility(obj, frame):
    """为对象的隐藏属性插入关键帧"""
    obj.keyframe_insert(data_path="hide_viewport", frame=frame)
    obj.keyframe_insert(data_path="hide_render", frame=frame)

def toggle_visibility():
    """切换标记并执行操作"""
    ensure_visibility_marker()
    marker = bpy.context.scene["VisibilityMarker"]
    current_frame = bpy.context.scene.frame_current

    if marker == 0:
        # 存储当前物体状态并设置标记为 1
        store_visibility_state()
        # 隐藏所有物体的视图和渲染，并插入关键帧
        for obj in bpy.data.objects:
            if obj not in bpy.context.selected_objects:
                obj.hide_viewport = True
                obj.hide_render = True
                insert_keyframes_for_visibility(obj, current_frame)

        # 仅显示选中的物体的视图和渲染，并插入关键帧
        for obj in bpy.context.selected_objects:
            obj.hide_viewport = False
            obj.hide_render = False
            insert_keyframes_for_visibility(obj, current_frame)

        set_visibility_marker(1)
        print(f"已设置标记为 1，仅显示选中的物体，并在第 {current_frame} 帧插入关键帧")
        
    elif marker == 1:
        # 恢复存储的状态并将标记重置为 0
        restore_visibility_state()
        set_visibility_marker(0)
        # 插入关键帧以记录恢复的状态
        for obj in bpy.data.objects:
            insert_keyframes_for_visibility(obj, current_frame)
        print(f"标记已重置为 0，恢复存储状态，并在第 {current_frame} 帧插入关键帧")

# 运行脚本
toggle_visibility()



