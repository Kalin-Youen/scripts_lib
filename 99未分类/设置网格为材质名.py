import bpy

def rename_single_material_objects():
    # 统计信息
    renamed = 0
    skipped_multi = 0
    skipped_none = 0
    skipped_nonmesh = 0

    for obj in bpy.context.selected_objects:
        # 仅处理网格
        if obj.type != 'MESH':
            skipped_nonmesh += 1
            continue

        # 获取非空材质列表
        mats = [m for m in obj.data.materials if m is not None]

        if len(mats) == 1:
            new_name = mats[0].name
            if obj.name != new_name:
                obj.name = new_name
                renamed += 1
        elif len(mats) == 0:
            skipped_none += 1
        else:
            skipped_multi += 1

    # 输出统计
    print(f"重命名完成：{renamed} 个对象已改名。")
    if skipped_multi:
        print(f"跳过 {skipped_multi} 个拥有多个材质的对象。")
    if skipped_none:
        print(f"跳过 {skipped_none} 个未分配材质的对象。")
    if skipped_nonmesh:
        print(f"跳过 {skipped_nonmesh} 个非网格对象。")

# 运行
rename_single_material_objects()
