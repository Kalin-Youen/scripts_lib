import bpy

def cleanup_action_smarter(action, threshold=0.001):
    """
    一个更智能的清理函数，使用阈值来移除几乎不变的冗余关键帧。
    它能更好地保留动画的节奏和"保持"姿势。
    """
    if not action or not action.fcurves:
        return

    print(f"    - 启动智能清理，动作: '{action.name}', 容差: {threshold}")
    total_removed = 0

    for fcurve in action.fcurves:
        keyframe_points = fcurve.keyframe_points
        if len(keyframe_points) < 3:
            continue

        # 创建一个要删除的关键帧索引列表
        indices_to_remove = []
        
        # 我们需要一个动态的"前一个"关键帧，以处理连续删除的情况
        prev_kf = keyframe_points[0]

        # 从第二个点开始，到倒数第二个点结束
        for i in range(1, len(keyframe_points) - 1):
            current_kf = keyframe_points[i]
            next_kf = keyframe_points[i + 1]

            # ---------------- 智能判断逻辑 ----------------
            # 使用线性插值（lerp）来预测当前帧的值应该是什么
            # t 是当前帧在前后两个关键帧之间的时间比例
            time_diff = next_kf.co.x - prev_kf.co.x
            if time_diff == 0: continue # 避免除以零
            
            t = (current_kf.co.x - prev_kf.co.x) / time_diff
            
            # 根据前后两个点的值，预测中间点的值
            predicted_value = prev_kf.co.y + t * (next_kf.co.y - prev_kf.co.y)
            
            # 如果实际值与预测值的差异在阈值之内，则认为是冗余的
            if abs(current_kf.co.y - predicted_value) < threshold:
                indices_to_remove.append(i)
            else:
                # 如果这个点不是冗余的，它就成为下一次比较的"前一个"点
                prev_kf = current_kf
        
        # 从后往前删除，避免索引错乱
        if indices_to_remove:
            for index in sorted(indices_to_remove, reverse=True):
                keyframe_points.remove(keyframe_points[index])
            total_removed += len(indices_to_remove)

    print(f"    - ✅ 智能清理完成。移除了 {total_removed} 个冗余关键帧。")


def check_if_already_baked(obj, action_type="obj_pose"):
    """
    检查物体是否已经被烘焙过。
    判断标准：
    1. 有一个包含 "_baked" 后缀的动作
    2. 所有NLA轨道都是静音的
    3. 当前活动动作就是烘焙后的动作
    """
    if action_type == "obj_pose":
        if not obj.animation_data:
            return False
        
        # 检查是否有烘焙后的动作名称
        expected_baked_name = f"{obj.name}_obj_pose_baked"
        current_action = obj.animation_data.action
        
        # 如果当前动作就是烘焙后的动作
        if current_action and (current_action.name == expected_baked_name or "_baked" in current_action.name):
            # 检查所有NLA轨道是否都被静音
            all_muted = all(track.mute for track in obj.animation_data.nla_tracks)
            if all_muted:
                return True
                
    elif action_type == "shapekey":
        if not obj.data or not hasattr(obj.data, 'shape_keys'):
            return False
        shape_keys = obj.data.shape_keys
        if not shape_keys or not shape_keys.animation_data:
            return False
            
        expected_baked_name = f"{obj.name}_shapekey_baked"
        current_action = shape_keys.animation_data.action
        
        if current_action and (current_action.name == expected_baked_name or "_baked" in current_action.name):
            all_muted = all(track.mute for track in shape_keys.animation_data.nla_tracks)
            if all_muted:
                return True
    
    return False


def needs_baking(obj):
    """
    判断物体是否需要烘焙。
    需要烘焙的条件：
    1. 有NLA轨道
    2. 至少有一个NLA轨道是未静音的（活动的）
    3. 还没有被烘焙过
    """
    needs_obj_bake = False
    needs_shapekey_bake = False
    
    # 检查物体/姿态动画
    if obj.animation_data and obj.animation_data.nla_tracks:
        # 有NLA轨道，并且至少有一个是活动的
        has_active_tracks = any(not track.mute for track in obj.animation_data.nla_tracks)
        if has_active_tracks and not check_if_already_baked(obj, "obj_pose"):
            needs_obj_bake = True
    
    # 检查形态键动画
    if obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys:
        shape_keys = obj.data.shape_keys
        if shape_keys.animation_data and shape_keys.animation_data.nla_tracks:
            has_active_tracks = any(not track.mute for track in shape_keys.animation_data.nla_tracks)
            if has_active_tracks and not check_if_already_baked(obj, "shapekey"):
                needs_shapekey_bake = True
    
    return needs_obj_bake, needs_shapekey_bake


def bake_shape_keys_perfectly(obj, start_frame, end_frame):
    print("    - 启动完美形态键烘焙模式...")
    shape_keys = obj.data.shape_keys
    if not shape_keys or not shape_keys.animation_data:
        print("    - 未发现形态键动画数据。")
        return

    new_name = f"{obj.name}_shapekey_baked"
    if new_name in bpy.data.actions:
        bpy.data.actions.remove(bpy.data.actions[new_name])
    new_action = bpy.data.actions.new(name=new_name)

    key_blocks_to_bake = [kb for kb in shape_keys.key_blocks if kb != shape_keys.key_blocks[0]]
    if not key_blocks_to_bake: return

    original_frame = bpy.context.scene.frame_current
    try:
        for frame in range(start_frame, end_frame + 1):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update() 
            for kb in key_blocks_to_bake:
                data_path = f'key_blocks["{kb.name}"].value'
                fcurve = new_action.fcurves.find(data_path) or new_action.fcurves.new(data_path)
                fcurve.keyframe_points.insert(frame, kb.value)
    finally:
        bpy.context.scene.frame_set(original_frame)

    # 调用新的智能清理函数！
    cleanup_action_smarter(new_action, threshold=0.001)
            
    shape_keys.animation_data.action = None
    for track in shape_keys.animation_data.nla_tracks: 
        track.mute = True
    shape_keys.animation_data.action = new_action
            
    print(f"    - ✅ 形态键已完美烘焙并智能清理到动作: '{new_action.name}'")


def get_total_animation_range(obj):
    min_frame, max_frame = float('inf'), float('-inf')
    has_anim = False
    
    # 物体/姿态动画 - 只统计未静音的轨道
    if obj.animation_data:
        ad = obj.animation_data
        if ad.action:
            min_frame = min(min_frame, ad.action.frame_range[0])
            max_frame = max(max_frame, ad.action.frame_range[1])
            has_anim = True
        for track in ad.nla_tracks:
            if not track.mute and track.strips:  # 只统计未静音的
                has_anim = True
                for strip in track.strips:
                    min_frame = min(min_frame, strip.frame_start)
                    max_frame = max(max_frame, strip.frame_end)

    # 形态键动画 - 只统计未静音的轨道
    if obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys and obj.data.shape_keys.animation_data:
        sk_ad = obj.data.shape_keys.animation_data
        if sk_ad.action:
            min_frame = min(min_frame, sk_ad.action.frame_range[0])
            max_frame = max(max_frame, sk_ad.action.frame_range[1])
            has_anim = True
        for track in sk_ad.nla_tracks:
            if not track.mute and track.strips:  # 只统计未静音的
                has_anim = True
                for strip in track.strips:
                    min_frame = min(min_frame, strip.frame_start)
                    max_frame = max(max_frame, strip.frame_end)
                    
    if not has_anim: 
        return None
    return int(min_frame), int(max_frame)


def bake_and_clean_all_animations_smart():
    """
    智能版主函数：
    - 跳过没有NLA轨道的物体
    - 跳过已经烘焙过的物体
    - 保护已有的烘焙结果
    """
    selected_objects = bpy.context.selected_objects
    if not selected_objects:
        print("❌ 请先选择物体。")
        return {'CANCELLED'}

    original_active_object = bpy.context.view_layer.objects.active
    
    # 统计信息
    skipped_no_nla = []
    skipped_already_baked = []
    successfully_baked = []
    
    for obj in selected_objects:
        print(f"\n--- 检查物体: {obj.name} ---")
        
        # 检查是否需要烘焙
        needs_obj_bake, needs_shapekey_bake = needs_baking(obj)
        
        if not needs_obj_bake and not needs_shapekey_bake:
            # 进一步判断跳过原因
            has_nla = False
            if obj.animation_data and obj.animation_data.nla_tracks:
                has_nla = True
            if obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys:
                if obj.data.shape_keys.animation_data and obj.data.shape_keys.animation_data.nla_tracks:
                    has_nla = True
            
            if not has_nla:
                print(f"    ⏩ 跳过：没有NLA轨道")
                skipped_no_nla.append(obj.name)
            else:
                print(f"    ⏩ 跳过：已经烘焙过或所有NLA轨道都已静音")
                skipped_already_baked.append(obj.name)
            continue
        
        # 获取动画范围
        anim_range = get_total_animation_range(obj)
        if not anim_range:
            print(f"    ⚠️ 未找到有效的活动动画帧")
            continue
        
        start_frame, end_frame = anim_range
        print(f"    - 动画范围: {start_frame} 到 {end_frame}")

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # 1. 处理物体变换和骨架姿态动画
        if needs_obj_bake:
            bake_types = set()
            if obj.type == 'ARMATURE': 
                bake_types.add('POSE')
            if obj.animation_data:
                bake_types.add('OBJECT')
            
            if bake_types:
                print("    - 正在烘焙物体/姿态动画...")
                original_scene_start = bpy.context.scene.frame_start
                original_scene_end = bpy.context.scene.frame_end
                try:
                    bpy.context.scene.frame_start = start_frame
                    bpy.context.scene.frame_end = end_frame
                    bpy.ops.nla.bake(
                        only_selected=True, 
                        visual_keying=True,
                        use_current_action=True, 
                        bake_types=bake_types
                    )
                finally:
                    bpy.context.scene.frame_start = original_scene_start
                    bpy.context.scene.frame_end = original_scene_end
                
                if obj.animation_data.action:
                    new_action = obj.animation_data.action
                    new_action.name = f"{obj.name}_obj_pose_baked"
                    cleanup_action_smarter(new_action, threshold=0.001)
                    print(f"    - ✅ 物体/姿态已烘焙到: '{new_action.name}'")

        # 2. 独立处理形态键动画
        if needs_shapekey_bake:
            bake_shape_keys_perfectly(obj, start_frame, end_frame)
        
        successfully_baked.append(obj.name)
        print(f"✅ '{obj.name}' 烘焙完成！")

    # 恢复原始活动物体
    bpy.context.view_layer.objects.active = original_active_object
    
    # 打印统计信息
    print("\n" + "="*50)
    print("🎯 烘焙任务完成！统计信息：")
    print("="*50)
    
    if successfully_baked:
        print(f"\n✅ 成功烘焙 ({len(successfully_baked)} 个):")
        for name in successfully_baked:
            print(f"    - {name}")
    
    if skipped_already_baked:
        print(f"\n⏩ 跳过-已烘焙 ({len(skipped_already_baked)} 个):")
        for name in skipped_already_baked:
            print(f"    - {name}")
    
    if skipped_no_nla:
        print(f"\n⏩ 跳过-无NLA ({len(skipped_no_nla)} 个):")
        for name in skipped_no_nla:
            print(f"    - {name}")
    
    print("\n" + "="*50)
    print(f"总计: {len(selected_objects)} 个物体")
    print(f"  - 成功烘焙: {len(successfully_baked)}")
    print(f"  - 跳过(已烘焙): {len(skipped_already_baked)}")
    print(f"  - 跳过(无NLA): {len(skipped_no_nla)}")
    print("="*50)
    
    return {'FINISHED'}


# --- 主执行入口 ---
if __name__ == "__main__":
    bake_and_clean_all_animations_smart()
