# 实时翻转选中面
# 实时翻转选中面
# 2网格
import bpy
import bmesh

# 定义一个函数来翻转选中面的法向
def flip_selected_face_normals(context):
    obj = context.edit_object
    if obj is not None:
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        for face in bm.faces:
            if face.select:
                face.normal_flip()

        # 更新网格以显示更改
        bmesh.update_edit_mesh(me)

# 定义一个事件处理器，它会在每次选择改变时调用 flip_selected_face_normals
def on_selection_change(scene):
    flip_selected_face_normals(bpy.context)

# 自定义操作符，用于移除事件处理器
class RemoveEventHandlerOperator(bpy.types.Operator):
    """Remove the event handler for flipping normals on selection change"""
    bl_idname = "object.remove_event_handler"
    bl_label = "Remove Event Handler"

    def execute(self, context):
        # 检查事件处理器是否已经在列表中，如果是，则移除
        try:
            bpy.app.handlers.depsgraph_update_pre.remove(on_selection_change)
            self.report({'INFO'}, "事件处理器已移除。")
            return {'FINISHED'}
        except ValueError:
            self.report({'WARNING'}, "事件处理器未找到。")
            return {'CANCELLED'}

# 注册自定义操作符
addon_keymaps = []

def register():
    bpy.utils.register_class(RemoveEventHandlerOperator)
    bpy.app.handlers.depsgraph_update_pre.append(on_selection_change)
    print("脚本已启动，选中的面将自动翻转法向。")

    # 添加快捷键
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
        kmi = km.keymap_items.new(RemoveEventHandlerOperator.bl_idname, type='ESC', value='PRESS')
        addon_keymaps.append((km, kmi))

def unregister():
    try:
        bpy.app.handlers.depsgraph_update_pre.remove(on_selection_change)
    except ValueError:
        pass
    bpy.utils.unregister_class(RemoveEventHandlerOperator)
    print("事件处理器已移除。")

    # 移除快捷键
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

# 注册和注销函数
register()
