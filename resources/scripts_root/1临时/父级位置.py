# script_id: 846619f8-93e9-4fe3-949c-4b277ac02535
"""
设置空物体父级的位置，多种模式可选
"""
import bpy
import mathutils

class OBJECT_OT_recenter_parent_empty_popup(bpy.types.Operator):
    bl_idname = "object.recenter_parent_empty_popup"
    bl_label = "Recenter Parent Empty"
    bl_options = {'REGISTER', 'UNDO'}

    mode: bpy.props.EnumProperty(
        name="定位模式",
        description="选择空物体的新位置",
        items=[
            ('BOUNDS',        "包围盒中心",    "移动到所有子孙网格的包围盒中心"),
            ('CHILDREN',      "子级中心",      "移动到直接子对象位置的平均中心"),
            ('BOTTOM',        "子级底部",      "移动到子级中心的底部（脚底对齐）"),
            ('WORLD_ORIGIN',  "世界原点",      "移动到世界坐标原点 (0,0,0)"),
            ('ACTIVE_CHILD',  "活动项子级原点", "移动到当前活动对象的世界位置"),
            ('CURSOR',        "3D游标位置",    "移动到3D游标所在位置"),
            ('ORIGIN',        "保持原点",      "不移动空物体，仅刷新父子关系（归一化）")
        ],
        default='BOUNDS'
    )

    def get_all_mesh_descendants(self, parent):
        descendants = []
        def recurse(obj):
            for child in obj.children:
                if child.type == 'MESH':
                    descendants.append(child)
                recurse(child)
        recurse(parent)
        return descendants

    def compute_world_bounding_box_center(self, objects):
        if not objects:
            return mathutils.Vector((0, 0, 0))
        min_co = mathutils.Vector((float('inf'),) * 3)
        max_co = mathutils.Vector((float('-inf'),) * 3)
        for obj in objects:
            for corner in obj.bound_box:
                world_corner = obj.matrix_world @ mathutils.Vector(corner)
                min_co = mathutils.Vector(tuple(min(a, b) for a, b in zip(min_co, world_corner)))
                max_co = mathutils.Vector(tuple(max(a, b) for a, b in zip(max_co, world_corner)))
        return (min_co + max_co) / 2

    def compute_children_center(self, children):
        if not children:
            return mathutils.Vector((0, 0, 0))
        world_locs = [child.matrix_world.translation for child in children]
        return sum(world_locs, mathutils.Vector()) / len(world_locs)

    def process_parent_empty(self, parent_empty):
        direct_children = [child for child in parent_empty.children]
        if not direct_children:
            return

        context = bpy.context
        new_center_world = mathutils.Vector((0, 0, 0))

        if self.mode == 'BOUNDS':
            mesh_descendants = self.get_all_mesh_descendants(parent_empty)
            new_center_world = self.compute_world_bounding_box_center(mesh_descendants)

        elif self.mode == 'CHILDREN':
            new_center_world = self.compute_children_center(direct_children)

        elif self.mode == 'BOTTOM':
            center_xy = self.compute_children_center(direct_children)
            min_z = min(child.matrix_world.translation.z for child in direct_children)
            new_center_world = mathutils.Vector((center_xy.x, center_xy.y, min_z))

        elif self.mode == 'WORLD_ORIGIN':
            new_center_world = mathutils.Vector((0, 0, 0))

        elif self.mode == 'ACTIVE_CHILD':
            active = context.active_object
            if active and active in direct_children:
                new_center_world = active.matrix_world.translation
            else:
                self.report({'WARNING'}, f"活动对象不是子级，使用原位置")
                new_center_world = parent_empty.matrix_world.translation

        elif self.mode == 'CURSOR':
            new_center_world = context.scene.cursor.location.copy()

        elif self.mode == 'ORIGIN':
            new_center_world = parent_empty.matrix_world.translation

        child_world_matrices = {child: child.matrix_world.copy() for child in direct_children}

        for child in direct_children:
            child.parent = None
            child.matrix_world = child_world_matrices[child]

        parent_empty.matrix_world.translation = new_center_world

        for child in direct_children:
            child.parent = parent_empty
            child.matrix_parent_inverse = parent_empty.matrix_world.inverted()

    def execute(self, context):
        processed_parents = set()

        for obj in context.selected_objects:
            if obj.parent and obj.parent.type == 'EMPTY':
                processed_parents.add(obj.parent)

        for obj in context.selected_objects:
            if obj.type == 'EMPTY':
                processed_parents.add(obj)

        if not processed_parents:
            self.report({'INFO'}, "未找到空物体父级或选中的空物体")
            return {'CANCELLED'}

        for parent_empty in processed_parents:
            self.process_parent_empty(parent_empty)

        mode_labels = {
            'BOUNDS': "包围盒中心",
            'CHILDREN': "子级中心",
            'BOTTOM': "子级底部",
            'WORLD_ORIGIN': "世界原点",
            'ACTIVE_CHILD': "活动项子级原点",
            'CURSOR': "3D游标位置",
            'ORIGIN': "保持原点"
        }
        self.report({'INFO'}, f"已处理 {len(processed_parents)} 个空物体 [{mode_labels.get(self.mode)}]")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):
        layout = self.layout
        layout.label(text="选择空物体的新位置：", icon='ORIENTATION_GLOBAL')
        layout.separator()

        # 第一行：包围盒、子级中心、子级底部
        row1 = layout.row(align=True)
        row1.scale_y = 1.3
        row1.prop_enum(self, "mode", 'BOUNDS')
        row1.prop_enum(self, "mode", 'CHILDREN')
        row1.prop_enum(self, "mode", 'BOTTOM')

        # 第二行：世界原点、活动子级、游标位置
        row2 = layout.row(align=True)
        row2.scale_y = 1.3
        row2.prop_enum(self, "mode", 'WORLD_ORIGIN')
        row2.prop_enum(self, "mode", 'ACTIVE_CHILD')
        row2.prop_enum(self, "mode", 'CURSOR')  # 已修复拼写错误

        # 第三行：保持原点（单独居中）
        layout.separator()
        row3 = layout.row()
        row3.alignment = 'CENTER'
        row3.scale_y = 1.1
        row3.prop_enum(self, "mode", 'ORIGIN')

        layout.separator()


# ================== 注册并运行 ==================
# 防止重复注册
try:
    bpy.utils.unregister_class(OBJECT_OT_recenter_parent_empty_popup)
except:
    pass

bpy.utils.register_class(OBJECT_OT_recenter_parent_empty_popup)

# 弹出窗口
bpy.ops.object.recenter_parent_empty_popup('INVOKE_DEFAULT')