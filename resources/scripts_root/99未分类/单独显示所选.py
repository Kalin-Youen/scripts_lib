# script_id: 14dbd3af-98d2-4d7c-820b-bb55df0ea0dd
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

def toggle_visibility():
    """切换标记并执行操作"""
    ensure_visibility_marker()
    marker = bpy.context.scene["VisibilityMarker"]

    if marker == 0:
        # 存储当前物体状态并设置标记为 1
        store_visibility_state()
        # 隐藏所有物体的视图和渲染
        for obj in bpy.data.objects:
            if obj not in bpy.context.selected_objects:
                obj.hide_viewport = True
                obj.hide_render = True

        # 仅显示选中的物体的视图和渲染
        for obj in bpy.context.selected_objects:
            obj.hide_viewport = False
            obj.hide_render = False

        set_visibility_marker(1)
        print("已设置标记为 1，仅显示选中的物体")
        
    elif marker == 1:
        # 恢复存储的状态并将标记重置为 0
        restore_visibility_state()
        set_visibility_marker(0)
        print("标记已重置为 0，恢复存储状态")

# 运行脚本
toggle_visibility()
