import bpy

def sync_by_constraints():
    # 只取选中的 Armature 对象
    armatures = [o for o in bpy.context.selected_objects if o.type == 'ARMATURE']
    if len(armatures) != 2:
        raise RuntimeError("请在 3D 视图中选中 EXACTLY 2 个 Armature 对象。")

    src = bpy.context.active_object
    if not src or src.type != 'ARMATURE':
        raise RuntimeError("Active Object 必须是一个 Armature，作为源骨架。")
    # 另一根就是目标
    tgt = armatures[0] if armatures[1] == src else armatures[1]

    # 确保两者都有 pose 数据
    if not src.pose or not tgt.pose:
        raise RuntimeError("源或目标骨架没有 Pose 数据。")

    # 遍历目标骨架的每根 pose bone
    for tgt_pb in tgt.pose.bones:
        # 只有源骨架存在同名骨骼才处理
        if tgt_pb.name in src.pose.bones:
            # 尝试复用已存在的 Copy Transforms 约束
            cons = next((c for c in tgt_pb.constraints
                         if c.type == 'COPY_TRANSFORMS'
                         and c.subtarget == tgt_pb.name), None)
            if not cons:
                cons = tgt_pb.constraints.new('COPY_TRANSFORMS')
            # 设置目标指向源骨架
            cons.target    = src
            cons.subtarget = tgt_pb.name
            # 也可以按需修改空间
            cons.owner_space  = 'POSE'
            cons.target_space = 'POSE'

    print(f"已在目标骨架 '{tgt.name}' 上添加 Copy Transforms 约束，跟随源骨架 '{src.name}'。")

# 运行
if __name__ == "__main__":
    try:
        sync_by_constraints()
    except Exception as e:
        self = None
        print("同步失败：", e)
