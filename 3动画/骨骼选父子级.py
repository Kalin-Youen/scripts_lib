import bpy

def select_root_bone_and_kin():
    """
    此乃“血脉追溯”之法。
    在姿态模式下，选中任意一根“灵骨”，此法便能追本溯源，
    锁定其最上位的“根骨”，并以其为中心，号令其下所有“衍骨”一同响应。
    """
    # --- 法术前摇：确认天时地利人和 ---
    
    # 确认当前是否处于“内视”之境（姿态模式）
    if bpy.context.mode != 'POSE':
        print("道法不合，此术仅可在姿态模式下施展。")
        return

    # 锁定天命所归的“法身”（活动骨架）
    armature_obj = bpy.context.active_object
    if not armature_obj or armature_obj.type != 'ARMATURE':
        print("神念无凭，未曾锁定任何骨架法身。")
        return

    # 探查神念是否已锁定至少一根“灵骨”
    if not bpy.context.selected_pose_bones:
        print("神念空悬，未曾锁定任何灵骨。")
        return

    # 准备一个“天机簿”，记录已经探查过的“根骨”，免得重复施法，耗费心神
    processed_roots = set()
    
    # --- 核心施法：追本溯源，号令血脉 ---
    print("--- “血脉追溯”之法，启动 ---")

    # 遍历神念所及的每一根灵骨，即便选中了不同经络的分支
    # 我们要为每一道分支找到它的源头
    # 注意：以list()复制一份，防止在循环中修改选中状态导致迭代错乱，此乃稳固道心之举
    for selected_bone in list(bpy.context.selected_pose_bones):
        
        # 追本溯源，上溯经络，直至找到无上位的“根骨”
        root_bone = selected_bone
        while root_bone.parent:
            root_bone = root_bone.parent
            
        # 若此“根骨”的因果已被探查，则无需再扰
        if root_bone in processed_roots:
            continue
            
        processed_roots.add(root_bone)

        # --- 洞察并敕令 ---
        
        # 确认“根骨”本身是否显化于形（未被隐藏），若在，则打入第一道“敕令”
        if not root_bone.bone.hide:
            root_bone.bone.select = True
            print(f"已锁定根骨: {root_bone.name}")
        else:
            print(f"根骨 '{root_bone.name}' 已被隐藏，跳过敕令。")

        # 现在，开始号令这位“根骨”座下的所有血脉后裔
        selected_kin_count = 0
        skipped_kin_count = 0
        
        # 遍历其所有“衍骨”，无论层级深浅
        for child_bone in root_bone.children_recursive:
            # 洞察此“衍骨”是否显化于形
            if not child_bone.bone.hide:
                # 若在，则施展“号令”神通，打入敕令使其响应
                child_bone.bone.select = True
                selected_kin_count += 1
            else:
                # 若不在，则记下，不强求，此乃宗师风范
                skipped_kin_count += 1
        
        print(f"对 '{root_bone.name}' 血脉的操作完成: 选中 {selected_kin_count} 根衍骨, 跳过 {skipped_kin_count} 根隐藏的衍骨。")

    print("--- 法术完毕，经络已明 ---")

# --- 运行此神通 ---
select_root_bone_and_kin()
