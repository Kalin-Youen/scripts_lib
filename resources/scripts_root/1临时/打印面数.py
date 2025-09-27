# script_id: 598adb10-c2d9-46d8-9480-fdb0b50f9ab6
import bpy

def print_objects_face_count():
    # 存放 (名字, 面数) 的列表
    obj_face_list = []

    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            # 使用 evaluated 版本以获取 modifiers 后的面数
            depsgraph = bpy.context.evaluated_depsgraph_get()
            eval_obj = obj.evaluated_get(depsgraph)
            mesh = eval_obj.to_mesh()
            face_count = len(mesh.polygons)
            obj_face_list.append((obj.name, face_count))
            eval_obj.to_mesh_clear()

    # 按面数从多到少排序
    obj_face_list.sort(key=lambda x: x[1], reverse=True)

    # 输出
    print("对象面数统计 (单位: 万面)")
    for name, count in obj_face_list:
        print(f"{name:<20}  {count/10000:.2f} 万面")

# 调用
print_objects_face_count()
