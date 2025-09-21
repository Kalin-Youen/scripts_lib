# -*- coding: utf-8 -*-
#删除空形态键
import bpy

# --- 辅助函数，用于安全地注销类 ---
def unregister_and_cleanup(cls):
    try:
        bpy.utils.unregister_class(cls)
    except RuntimeError:
        pass

# --- 1. 定义核心操作符 ---
class TEMP_OT_delete_empty_shapekeys(bpy.types.Operator):
    """
    一个临时的操作符，用于查找并删除空形态键。
    执行后会自动注销自己。
    """
    bl_idname = "object.temp_delete_empty_shapekeys"
    bl_label = "删除空形态键"
    bl_options = {'REGISTER', 'UNDO'}

    only_selected: bpy.props.BoolProperty(
        name="仅作用于选中物体",
        description="如果勾选，则只处理当前选中的物体；否则处理场景中所有物体",
        default=True
    )
    tolerance: bpy.props.FloatProperty(
        name="容差",
        description="判断顶点位置是否相同的容差值。用于处理浮点数精度问题",
        default=0.00001,
        min=0.0,
        precision=6
    )

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        if self.only_selected:
            objects_to_check = context.selected_objects
        else:
            objects_to_check = context.scene.objects

        deleted_count = 0
        processed_objects = 0
        mesh_objects = [o for o in objects_to_check if o.type == 'MESH' and o.data.shape_keys]

        if not mesh_objects:
            self.report({'WARNING'}, "没有找到带有形态键的网格物体")
            bpy.app.timers.register(lambda: unregister_and_cleanup(self.__class__))
            return {'CANCELLED'}

        for obj in mesh_objects:
            skeys_collection = obj.data.shape_keys.key_blocks
            if len(skeys_collection) < 2:
                continue

            basis_key_data = skeys_collection[0].data
            keys_to_delete = []

            for i in range(1, len(skeys_collection)):
                key = skeys_collection[i]
                is_empty = True
                for j in range(len(basis_key_data)):
                    if (basis_key_data[j].co - key.data[j].co).length > self.tolerance:
                        is_empty = False
                        break
                if is_empty:
                    keys_to_delete.append(key.name)

            if keys_to_delete:
                processed_objects += 1
                for key_name in keys_to_delete:
                    # --- 【最终修正】---
                    # 通过名称找到索引，因为每次删除后索引都会变化，所以按名称查找最可靠
                    key_index = skeys_collection.find(key_name)
                    if key_index != -1:
                        # 操作符作用于物体的 "active" 形态键，所以我们先设置它
                        obj.active_shape_key_index = key_index
                        
                        # 使用 temp_override 创建一个临时的、安全的操作上下文
                        with bpy.context.temp_override(object=obj):
                            bpy.ops.object.shape_key_remove()
                        
                        deleted_count += 1
        
        if deleted_count > 0:
            self.report({'INFO'}, f"操作完成：从 {processed_objects} 个物体中删除了 {deleted_count} 个空形态键")
        else:
            self.report({'INFO'}, "没有找到任何空的形态键")
        
        bpy.app.timers.register(lambda: unregister_and_cleanup(self.__class__))
        return {'FINISHED'}

    def cancel(self, context):
        bpy.app.timers.register(lambda: unregister_and_cleanup(self.__class__))
        self.report({'INFO'}, "操作已取消")


# --- 2. 脚本的主入口：注册并立即运行 ---
if __name__ == "__main__":
    unregister_and_cleanup(TEMP_OT_delete_empty_shapekeys)
    bpy.utils.register_class(TEMP_OT_delete_empty_shapekeys)
    bpy.ops.object.temp_delete_empty_shapekeys('INVOKE_DEFAULT')
