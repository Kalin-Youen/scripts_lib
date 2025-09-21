import bpy
import os
from bpy.props import EnumProperty, BoolProperty
from mathutils import Vector
import subprocess

class WM_OT_export_fbx_dialog(bpy.types.Operator):
    bl_idname = "wm.export_fbx_dialog"
    bl_label = "导出 FBX 配置"
    bl_options = {'REGISTER', 'UNDO'}

    export_mode: EnumProperty(
        name="导出模式",
        description="选择导出方式",
        items=[
            ('OBJECT', "单独物体", "每个选中物体单独导出"),
            ('COLLECTION', "集合", "将活动集合一次性导出"),
            ('HIERARCHY', "父子级", "按父子层级分组导出")
        ],
        default='HIERARCHY'
    )
    zero_location: BoolProperty(
        name="位置归零",
        description="导出前将物体（或集合、根节点）移到原点，导出后再恢复",
        default=False
    )
    apply_modifiers: BoolProperty(
        name="应用修改器",
        description="导出时临时应用物体的所有修改器（不会改变原场景里的数据）",
        default=True
    )
    open_folder_after_export: BoolProperty(
        name="导出后打开文件夹",
        description="导出完成后自动打开目标文件夹",
        default=True
    )
    zero_rotation: BoolProperty(
        name="旋转归零",
        description="导出前将物体的旋转归零，导出后再恢复",
        default=False
    )
    zero_scale: BoolProperty(
        name="缩放归零",
        description="导出前将物体的缩放归零，导出后再恢复",
        default=False
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        # 1. 确保 .blend 已保存
        blend_fp = context.blend_data.filepath
        if not blend_fp:
            self.report({'ERROR'}, "请先保存 .blend 文件")
            return {'CANCELLED'}
        base_dir = os.path.dirname(blend_fp)
        target_folder = os.path.join(base_dir, "toUnity")
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        # 2. 缓存当前选中对象的 name 列表
        orig_selected_names = {o.name for o in context.selected_objects}

        # 3. 根据模式收集集合对象名或根节点名
        coll = None
        coll_objs_names = set()
        if self.export_mode == 'COLLECTION':
            layer_coll = context.view_layer.active_layer_collection
            coll = layer_coll.collection
            coll_objs_names = {o.name for o in coll.objects}

        roots_names = []
        if self.export_mode == 'HIERARCHY':
            roots_names = [o.name for o in context.selected_objects if o.parent is None or o.parent.name not in orig_selected_names]

        # 4. 位置归零备份（只记录 name 对应位置）
        loc_backup = {}
        rot_backup = {}
        scale_backup = {}
        if self.zero_location or self.zero_rotation or self.zero_scale:
            if self.export_mode == 'OBJECT':
                for name in orig_selected_names:
                    o = bpy.data.objects.get(name)
                    if o:
                        if self.zero_location:
                            loc_backup[name] = o.location.copy()
                            o.location = Vector((0, 0, 0))
                        if self.zero_rotation:
                            rot_backup[name] = o.rotation_euler.copy()
                            o.rotation_euler = Vector((0, 0, 0))
                        if self.zero_scale:
                            scale_backup[name] = o.scale.copy()
                            o.scale = Vector((1, 1, 1))

            elif self.export_mode == 'COLLECTION':
                # 计算集合中心
                vecs = []
                for name in coll_objs_names:
                    o = bpy.data.objects.get(name)
                    if o:
                        vecs.append(o.matrix_world.translation)
                if vecs:
                    cen = sum(vecs, Vector()) / len(vecs)
                    for name in coll_objs_names:
                        o = bpy.data.objects.get(name)
                        if o:
                            if self.zero_location:
                                loc_backup[name] = o.location.copy()
                                world_off = o.matrix_world.translation - cen
                                if o.parent:
                                    o.location = o.parent.matrix_world.inverted() @ world_off
                                else:
                                    o.location = world_off
                            if self.zero_rotation:
                                rot_backup[name] = o.rotation_euler.copy()
                                o.rotation_euler = Vector((0, 0, 0))
                            if self.zero_scale:
                                scale_backup[name] = o.scale.copy()
                                o.scale = Vector((1, 1, 1))

            else:  # HIERARCHY
                for name in roots_names:
                    o = bpy.data.objects.get(name)
                    if o:
                        if self.zero_location:
                            loc_backup[name] = o.location.copy()
                            o.location = Vector((0, 0, 0))
                        if self.zero_rotation:
                            rot_backup[name] = o.rotation_euler.copy()
                            o.rotation_euler = Vector((0, 0, 0))
                        if self.zero_scale:
                            scale_backup[name] = o.scale.copy()
                            o.scale = Vector((1, 1, 1))

        # 5. 清空场景选择
        bpy.ops.object.select_all(action='DESELECT')

        # 6. 导出参数
        fbx_kwargs = {
            "use_selection": True,
            "apply_unit_scale": True,
            "use_mesh_modifiers": self.apply_modifiers,
            "path_mode": 'COPY',
        }
        unity_kwargs = {
            "check_existing": False,
            "filter_glob": "*.fbx",
            "active_collection": False,
            "selected_objects": True,
            "deform_bones": False,
            "leaf_bones": False,
            "primary_bone_axis": 'Y',
            "secondary_bone_axis": 'X',
            "tangent_space": False,
            "triangulate_faces": False,
        }

        def export_both(fp):
            """导出标准 FBX 和 Unity FBX"""
            # 1) 标准 FBX
            try:
                result = bpy.ops.export_scene.fbx(filepath=fp, **fbx_kwargs)
                if 'FINISHED' not in result:
                    self.report({'WARNING'}, f"标准 FBX 导出警告（返回 {result}）")
            except Exception as e:
                self.report({'ERROR'}, f"标准 FBX 导出异常: {e}")
            
            # 2) Unity FBX
            try:
                unity_kwargs["filepath"] = fp
                unity_result = bpy.ops.export_scene.unity_fbx(**unity_kwargs)
                if 'FINISHED' not in unity_result:
                    self.report({'WARNING'}, f"Unity FBX 导出警告（返回 {unity_result}）")
            except Exception as e:
                self.report({'ERROR'}, f"Unity FBX 导出异常: {e}")


        # 7. 按模式循环导出
        if self.export_mode == 'OBJECT':
            for name in orig_selected_names:
                o = bpy.data.objects.get(name)
                if not o:
                    continue
                o.select_set(True)
                fp = os.path.join(target_folder, f"{name}.fbx")
                export_both(fp)
                self.report({'INFO'}, f"已导出 物体: {name}")
                o.select_set(False)

        elif self.export_mode == 'COLLECTION' and coll:
            for name in coll_objs_names:
                o = bpy.data.objects.get(name)
                if o:
                    o.select_set(True)
            fp = os.path.join(target_folder, f"{coll.name}.fbx")
            export_both(fp)
            self.report({'INFO'}, f"已导出 集合: {coll.name}")
            for name in coll_objs_names:
                o = bpy.data.objects.get(name)
                if o:
                    o.select_set(False)

        else:  # HIERARCHY
            def select_tree(o):
                o.select_set(True)
                for c in o.children:
                    if c.name in orig_selected_names:
                        select_tree(c)

            for name in roots_names:
                root = bpy.data.objects.get(name)
                if not root:
                    continue
                select_tree(root)
                fp = os.path.join(target_folder, f"{name}.fbx")
                export_both(fp)
                self.report({'INFO'}, f"已导出 层级: {name}")
                bpy.ops.object.select_all(action='DESELECT')

        # 8. 恢复原选中和位置
        for name in orig_selected_names:
            o = bpy.data.objects.get(name)
            if o:
                o.select_set(True)
        for name, loc in loc_backup.items():
            o = bpy.data.objects.get(name)
            if o:
                o.location = loc
        for name, rot in rot_backup.items():
            o = bpy.data.objects.get(name)
            if o:
                o.rotation_euler = rot
        for name, scale in scale_backup.items():
            o = bpy.data.objects.get(name)
            if o:
                o.scale = scale

        self.report({'INFO'}, "全部导出完成")

        # 打开文件夹
        if self.open_folder_after_export:
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(target_folder)
                elif os.name == 'posix':  # macOS and Linux
                    subprocess.Popen(['xdg-open', target_folder])
            except Exception as e:
                self.report({'WARNING'}, f"无法打开文件夹: {e}")

        unregister()
        return {'FINISHED'}


def register():
    bpy.utils.register_class(WM_OT_export_fbx_dialog)


def unregister():
    bpy.utils.unregister_class(WM_OT_export_fbx_dialog)


if __name__ == "__main__":
    register()
    bpy.ops.wm.export_fbx_dialog('INVOKE_DEFAULT')
