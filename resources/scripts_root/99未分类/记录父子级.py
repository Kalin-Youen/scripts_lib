# script_id: 9a7f3d2a-c9ed-4e69-af51-a05a0f912496
import bpy
import json
from bpy.types import Operator
from bpy.props import EnumProperty
from mathutils import Matrix

class OBJECT_OT_manage_parent_relations(Operator):
    bl_idname = "object.manage_parent_relations"
    bl_label = "管理父子关系"
    bl_description = "记录或恢复场景中所有物体的父子关系，并在恢复时保持世界位置不变"
    bl_options = {'REGISTER', 'UNDO'}

    action: EnumProperty(
        name="操作",
        description="请选择“记录”或“恢复”父子关系",
        items=[
            ('RECORD', "记录", "记录每个物体的父对象名称及当前世界矩阵"),
            ('RESTORE', "恢复", "根据记录重新设置父子关系并还原世界矩阵"),
        ],
        default='RECORD'
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        scene = context.scene

        if self.action == 'RECORD':
            # --------------------------------------------------------
            # 1. “记录”阶段：遍历整个 bpy.data.objects
            #    - 保存每个对象的父对象名 ("" 表示无父)
            #    - 保存每个对象当时的 matrix_world（世界矩阵）
            #    最终把 { obj.name: [parent_name, 世界矩阵扁平列表(16)] } 存成 JSON
            # --------------------------------------------------------
            temp = {}
            for obj in bpy.data.objects:
                parent_name = obj.parent.name if obj.parent else ""
                # 将 matrix_world 拆成 16 个 float
                mw = obj.matrix_world
                flat = [mw[i][j] for i in range(4) for j in range(4)]
                temp[obj.name] = {"parent": parent_name, "world_matrix": flat}

            scene["parent_relations_data"] = json.dumps(temp)
            self.report({'INFO'}, f"已记录 {len(temp)} 个物体的父子关系及世界矩阵")
        
        else:  # RESTORE
            # --------------------------------------------------------
            # 2. “恢复”阶段
            #    - 先从场景自定义属性里读回 JSON，如果不存在就取消
            #    - 将 JSON 反序列化为字典 saved_data
            #    - 计算每个物体在 saved_data 中的“深度” (depth)：无父 depth=0，其子 depth=1，以此类推
            #    - 第一遍：遍历所有对象，obj.parent = None（此时矩阵不变，只是断开父子关系）
            #    - 按 depth 从小到大排序后，给每个有父的对象 依次重设 parent
            #        • 在设置 parent 之前，先暂存它应还原的 world_matrix
            #        • 设置 parent → 然后直接把 obj.matrix_world 赋回存的那个世界矩阵
            #          （这样 Blender 会自动计算出正确的 local 矩阵，从而保证子对象位置不动）
            #    - 完成后清除操作符
            # --------------------------------------------------------
            json_str = scene.get("parent_relations_data")
            if not json_str:
                self.report({'WARNING'}, "没有可用的记录，请先执行“记录”操作")
                bpy.utils.unregister_class(OBJECT_OT_manage_parent_relations)
                return {'CANCELLED'}

            try:
                saved_data = json.loads(json_str)
            except Exception as e:
                self.report({'ERROR'}, f"读取记录时出错：{e}")
                bpy.utils.unregister_class(OBJECT_OT_manage_parent_relations)
                return {'CANCELLED'}

            # 1) 先计算所有对象的 depth（从顶层到子层递归）
            depths = {}
            def get_depth(obj_name):
                if obj_name not in saved_data:
                    return 0
                parent_name = saved_data[obj_name]["parent"]
                if parent_name == "" or parent_name not in saved_data:
                    depths[obj_name] = 0
                    return 0
                if obj_name in depths:
                    return depths[obj_name]
                d = 1 + get_depth(parent_name)
                depths[obj_name] = d
                return d

            for name in saved_data.keys():
                get_depth(name)

            # 2) 第一遍：断开所有对象的 parent，但保持世界矩阵不变
            for obj in bpy.data.objects:
                obj.parent = None

            # 3) 排序：depth 小的先处理
            names_sorted = sorted(saved_data.keys(), key=lambda n: depths.get(n, 0))

            restored = 0
            for name in names_sorted:
                entry = saved_data[name]
                parent_name = entry["parent"]
                if parent_name == "":
                    continue  # 顶层，不需要设置 parent
                obj = bpy.data.objects.get(name)
                parent_obj = bpy.data.objects.get(parent_name)
                if obj is None or parent_obj is None:
                    continue

                # 把存储的 world_matrix 还原成 Matrix
                flat = entry["world_matrix"]
                wm = Matrix((
                    (flat[0],  flat[1],  flat[2],  flat[3]),
                    (flat[4],  flat[5],  flat[6],  flat[7]),
                    (flat[8],  flat[9],  flat[10], flat[11]),
                    (flat[12], flat[13], flat[14], flat[15]),
                ))

                # 先设置 parent（此时 Blender 会自动生成一个新的 matrix_parent_inverse，
                # 但我们马上要用赋值 world_matrix 的方式覆盖本地矩阵）
                obj.parent = parent_obj

                # 直接把存的世界矩阵写回
                obj.matrix_world = wm

                restored += 1

            self.report({'INFO'}, f"已恢复 {restored} 个物体的父子关系，并还原世界矩阵")

        # 操作完成后，注销操作符
        bpy.utils.unregister_class(OBJECT_OT_manage_parent_relations)
        return {'FINISHED'}


def register():
    bpy.utils.register_class(OBJECT_OT_manage_parent_relations)


def unregister():
    if hasattr(bpy.types, OBJECT_OT_manage_parent_relations.__name__):
        bpy.utils.unregister_class(OBJECT_OT_manage_parent_relations)


if __name__ == "__main__":
    register()
    bpy.ops.object.manage_parent_relations('INVOKE_DEFAULT')
