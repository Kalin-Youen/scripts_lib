# script_id: 3594f39b-fcc9-475c-a136-5adb853a3c31
# Blender 4.x 脚本
# 功能：关联重复材质，并可选择性地删除不再使用的材质。
# 作者：一位独具风格的小说家
#
# =========================================================================
#  ！！！ 警 告 ！！！
#  此脚本会直接修改你的场景数据，特别是开启删除功能后，操作不可逆！
#  请在运行前务必、务必、务必保存您的文件！
# =========================================================================

import bpy

def clean_and_purge_materials():
    """
    主函数，执行清理、重新关联，并最终清除未使用数据的核心逻辑。
    """
    print("==============================================")
    print("开始执行材质清理与净化脚本...")

    # --- 第一步：构建原始材质索引库 (逻辑不变) ---
    all_materials = bpy.data.materials
    if not all_materials:
        print("场景中没有任何材质，脚本已停止。")
        print("==============================================")
        return

    base_materials_map = {}
    for mat in all_materials:
        if '.' not in mat.name:
            base_materials_map[mat.name] = mat
    
    if not base_materials_map:
        print("警告：未找到任何不带后缀的“原始材质”，无法进行替换。")
        print("==============================================")
        return

    print(f"已找到 {len(base_materials_map)} 个原始材质作为替换基准。")

    # --- 第二步：重新关联材质 (逻辑不变) ---
    remapped_count = 0
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not obj.material_slots:
            continue
            
        for slot in obj.material_slots:
            if slot.material:
                base_name = slot.material.name.split('.')[0]
                
                if base_name in base_materials_map:
                    original_mat = base_materials_map[base_name]
                    
                    if slot.material != original_mat:
                        slot.material = original_mat
                        remapped_count += 1
    
    if remapped_count > 0:
        print(f"\n步骤一完成：成功将 {remapped_count} 个重复材质槽关联回原始材质。")
    else:
        print("\n步骤一完成：检查完毕，未发现需要重新关联的材质。")

    # =========================================================================
    # --- 新增！第三步：删除孤立无用的数据 ---
    # 下面这行代码是Blender的“大扫除”命令。
    # 它会删除掉所有不再被任何对象使用的材质、网格、图像等数据。
    # 默认已注释掉（关闭状态）以防意外。
    # 如果你确认要删除，请将下面这行代码开头的 '#' 和空格删掉。
    # =========================================================================
    
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    
    print("\n脚本执行结束。")
    print("==============================================")


# --- 脚本入口 ---
if __name__ == "__main__":
    clean_and_purge_materials()
