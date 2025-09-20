import bpy
from mathutils import Matrix, Vector

bl_info = {
    "name": "智能解除父子关系 (自适应采样)",
    "author": "Your Code Master",
    "version": (2, 1, 0),
    "blender": (3, 0, 0),
    "location": "在文本编辑器中运行 -> 自动弹出",
    "description": "在解除父子关系时，使用自适应采样来精确保留动画曲线，支持多物体操作和多层级解绑。",
    "category": "Animation",
}

def get_objects_for_operation(context):
    """获取选中的对象，活动对象作为父级，其他选中对象作为子级"""
    selected_objects = context.selected_objects
    if len(selected_objects) < 2:
        return None, []
    
    active_obj = context.view_layer.objects.active
    if not active_obj or active_obj not in selected_objects:
        # 如果没有活动对象，取最后选中的作为父级
        active_obj = selected_objects[-1]
    
    # 子对象是除活动对象外的所有选中对象
    child_objects = [obj for obj in selected_objects if obj != active_obj]
    
    if not child_objects:
        return None, []
    
    return active_obj, child_objects

def get_all_ancestors(obj):
    """获取对象的所有祖先（父级、祖父级等）"""
    ancestors = []
    current = obj.parent
    while current:
        ancestors.append(current)
        current = current.parent
    return ancestors

def get_direct_parent_child_pairs(child_objects, parent_obj):
    """获取直接的父子关系对"""
    pairs = []
    for child in child_objects:
        # 检查是否是直接父子关系
        if child.parent == parent_obj:
            pairs.append((parent_obj, child))
    return pairs

def get_all_parent_child_pairs_for_unparent(child_objects):
    """获取所有层级的父子关系对用于解绑"""
    pairs = []
    for child in child_objects:
        current = child
        while current.parent:
            pairs.append((current.parent, current))
            current = current.parent
    return pairs

class OBJECT_OT_adaptive_unparent(bpy.types.Operator):
    bl_idname = "object.adaptive_unparent_popup"
    bl_label = "智能父子关系操作"
    bl_options = {'REGISTER', 'UNDO'}

    # === 操作模式选择 ===
    operation_mode: bpy.props.EnumProperty(
        name="操作模式",
        description="选择是解除父子关系还是建立父子关系",
        items=[
            ('UNPARENT', "解除父子关系", "解除父子关系，保留世界空间动画"),
            ('PARENT', "绑定到父对象", "将选中对象绑定到活动对象，保留世界空间动画")
        ],
        default='UNPARENT'
    )

    # === 自适应采样开关 ===
    use_adaptive_sampling: bpy.props.BoolProperty(
        name="启用自适应采样",
        description="启用后会根据容差自动插入必要关键帧以保持动画精度。关闭则仅在原始关键帧处采样。",
        default=True
    )

    # === 容差阈值（仅在解除父子关系时使用）===
    location_threshold: bpy.props.FloatProperty(
        name="位置容差",
        description="当预测位置与实际位置的偏差超过此值时，插入新关键帧。值越小，越精确，关键帧越多。",
        default=0.01, min=0.0, soft_max=1.0, unit='LENGTH', precision=4
    )
    rotation_threshold: bpy.props.FloatProperty(
        name="旋转容差",
        description="当预测旋转与实际旋转的偏差超过此值时(弧度)，插入新关键帧。",
        default=0.05, min=0.0, soft_max=3.14, subtype='ANGLE', precision=4
    )
    scale_threshold: bpy.props.FloatProperty(
        name="缩放容差",
        description="当预测缩放与实际缩放的偏差超过此值时，插入新关键帧。",
        default=0.01, min=0.0, soft_max=1.0, precision=4
    )

    @classmethod
    def poll(cls, context):
        if context.mode != 'OBJECT':
            return False
        selected = context.selected_objects
        if len(selected) < 2:
            return False
        return True

    def invoke(self, context, event):
        # 根据当前选择智能预设模式
        parent_obj, child_objects = get_objects_for_operation(context)
        if not parent_obj or not child_objects:
            self.report({'ERROR'}, "请选择至少两个对象：先选子对象，最后选父对象（活动对象）")
            return {'CANCELLED'}
        
        # 检查是否存在直接的父子关系
        direct_pairs = get_direct_parent_child_pairs(child_objects, parent_obj)
        
        if self.operation_mode == 'UNPARENT':
            # 如果没有直接父子关系，检查是否有任何层级的父子关系
            any_parent_child = False
            for child in child_objects:
                if child.parent:
                    any_parent_child = True
                    break
            
            if not any_parent_child:
                self.report({'INFO'}, "选中的对象间没有父子关系，将执行绑定操作")
                self.operation_mode = 'PARENT'
        else:  # PARENT模式
            # 检查是否已经存在父子关系
            if direct_pairs:
                self.report({'INFO'}, "选中的对象间已存在父子关系，将执行解除操作")
                self.operation_mode = 'UNPARENT'
        
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        scene = context.scene
        depsgraph = context.evaluated_depsgraph_get()

        if self.operation_mode == 'UNPARENT':
            return self.execute_unparent(context, scene, depsgraph)
        else:
            return self.execute_parent(context, scene, depsgraph)

    def execute_unparent(self, context, scene, depsgraph):
        parent_obj, child_objects = get_objects_for_operation(context)
        if not parent_obj or not child_objects:
            self.report({'ERROR'}, "请选择至少两个对象：先选子对象，最后选父对象（活动对象）")
            return {'CANCELLED'}

        # 获取所有需要解除的父子关系对（支持多层级）
        if parent_obj in child_objects:
            # 如果父对象也在子对象列表中（可能是误选），只解除直接关系
            parent_child_pairs = get_direct_parent_child_pairs(child_objects, parent_obj)
        else:
            # 否则解除所有层级的父子关系
            parent_child_pairs = get_all_parent_child_pairs_for_unparent(child_objects)

        if not parent_child_pairs:
            self.report({'INFO'}, "选中的对象间没有父子关系可解除")
            return {'FINISHED'}

        total_original_frames = 0
        total_final_frames = 0
        processed_pairs = 0

        for parent, child in parent_child_pairs:
            # 1. 收集原始关键帧
            initial_frames = set()
            for obj in [parent, child]:
                if obj.animation_data and obj.animation_data.action:
                    for fc in obj.animation_data.action.fcurves:
                        for kp in fc.keyframe_points:
                            initial_frames.add(int(round(kp.co.x)))

            total_original_frames += len(initial_frames)
            
            if not initial_frames:
                # 无动画，直接解除父子关系
                bpy.ops.object.select_all(action='DESELECT')
                child.select_set(True)
                context.view_layer.objects.active = child
                bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
                processed_pairs += 1
                continue

            sorted_initial_frames = sorted(list(initial_frames))

            # 2. 根据开关决定是否进行自适应采样
            if self.use_adaptive_sampling:
                frames_to_bake = set(sorted_initial_frames)

                check_queue = []
                for i in range(len(sorted_initial_frames) - 1):
                    check_queue.append((sorted_initial_frames[i], sorted_initial_frames[i+1]))

                wm = context.window_manager
                wm.progress_begin(0, 100)
                progress = 0

                while check_queue:
                    start_frame, end_frame = check_queue.pop(0)

                    progress += 1
                    if progress > 1000:  # 防止无限循环
                        wm.progress_update(50)

                    if end_frame <= start_frame + 1:
                        continue

                    mid_frame = (start_frame + end_frame) // 2

                    scene.frame_set(start_frame)
                    start_matrix = child.evaluated_get(depsgraph).matrix_world.copy()
                    scene.frame_set(end_frame)
                    end_matrix = child.evaluated_get(depsgraph).matrix_world.copy()
                    scene.frame_set(mid_frame)
                    actual_mid_matrix = child.evaluated_get(depsgraph).matrix_world.copy()

                    interp_factor = (mid_frame - start_frame) / (end_frame - start_frame)
                    predicted_mid_matrix = start_matrix.lerp(end_matrix, interp_factor)

                    p_loc, p_rot, p_scl = predicted_mid_matrix.decompose()
                    a_loc, a_rot, a_scl = actual_mid_matrix.decompose()

                    loc_diff = (p_loc - a_loc).length
                    rot_diff = p_rot.rotation_difference(a_rot).angle
                    scl_diff = (p_scl - a_scl).length

                    if (loc_diff > self.location_threshold or
                        rot_diff > self.rotation_threshold or
                        scl_diff > self.scale_threshold):

                        frames_to_bake.add(mid_frame)
                        check_queue.append((start_frame, mid_frame))
                        check_queue.append((mid_frame, end_frame))

                wm.progress_end()
            else:
                frames_to_bake = set(sorted_initial_frames)

            total_final_frames += len(frames_to_bake)

            # 3. 烘焙世界空间动画
            sorted_bake_frames = sorted(list(frames_to_bake))
            world_matrices = {}
            original_frame = scene.frame_current

            for frame in sorted_bake_frames:
                scene.frame_set(frame)
                world_matrices[frame] = child.evaluated_get(depsgraph).matrix_world.copy()

            # 4. 解除父子关系并应用动画
            if child.animation_data:
                child.animation_data_clear()

            bpy.ops.object.select_all(action='DESELECT')
            child.select_set(True)
            context.view_layer.objects.active = child
            bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

            for frame, matrix in world_matrices.items():
                child.matrix_world = matrix
                child.keyframe_insert(data_path="location", frame=frame)
                child.keyframe_insert(data_path="rotation_quaternion", frame=frame)
                child.keyframe_insert(data_path="rotation_euler", frame=frame)
                child.keyframe_insert(data_path="scale", frame=frame)

            processed_pairs += 1

        # 5. 恢复状态
        scene.frame_set(scene.frame_current)
        
        if processed_pairs > 0:
            avg_original = total_original_frames // processed_pairs if processed_pairs > 0 else 0
            avg_final = total_final_frames // processed_pairs if processed_pairs > 0 else 0
            self.report({'INFO'}, f"✅ 解除完成！处理了 {processed_pairs} 对父子关系，平均每对: {avg_original} → {avg_final} 帧。")
        else:
            self.report({'INFO'}, "没有找到需要解除的父子关系。")
            
        return {'FINISHED'}

    def execute_parent(self, context, scene, depsgraph):
        parent_obj, child_objects = get_objects_for_operation(context)
        if not parent_obj or not child_objects:
            self.report({'ERROR'}, "请选择至少两个对象：先选子对象，最后选父对象（活动对象）")
            return {'CANCELLED'}

        # 绑定只支持单层，不支持多层级绑定
        processed_count = 0
        total_original_frames = 0
        total_final_frames = 0

        for child in child_objects:
            # 1. 收集原始关键帧（只看子对象，因为我们要保留它的世界动画）
            initial_frames = set()
            if child.animation_data and child.animation_data.action:
                for fc in child.animation_data.action.fcurves:
                    for kp in fc.keyframe_points:
                        initial_frames.add(int(round(kp.co.x)))

            total_original_frames += len(initial_frames)

            if not initial_frames:
                # 子对象无动画，直接建立父子关系
                child.parent = parent_obj
                child.matrix_parent_inverse = parent_obj.matrix_world.inverted()
                processed_count += 1
                continue

            sorted_initial_frames = sorted(list(initial_frames))

            # 2. 是否自适应采样
            if self.use_adaptive_sampling:
                frames_to_bake = set(sorted_initial_frames)

                check_queue = []
                for i in range(len(sorted_initial_frames) - 1):
                    check_queue.append((sorted_initial_frames[i], sorted_initial_frames[i+1]))

                wm = context.window_manager
                wm.progress_begin(0, 100)
                progress = 0

                while check_queue:
                    start_frame, end_frame = check_queue.pop(0)

                    progress += 1
                    if progress > 1000:
                        wm.progress_update(50)

                    if end_frame <= start_frame + 1:
                        continue

                    mid_frame = (start_frame + end_frame) // 2

                    # 获取子对象的世界矩阵（目标）
                    scene.frame_set(start_frame)
                    child_start_world = child.evaluated_get(depsgraph).matrix_world.copy()
                    scene.frame_set(end_frame)
                    child_end_world = child.evaluated_get(depsgraph).matrix_world.copy()
                    scene.frame_set(mid_frame)
                    child_actual_mid_world = child.evaluated_get(depsgraph).matrix_world.copy()

                    # 插值预测
                    interp_factor = (mid_frame - start_frame) / (end_frame - start_frame)
                    predicted_mid_world = child_start_world.lerp(child_end_world, interp_factor)

                    p_loc, p_rot, p_scl = predicted_mid_world.decompose()
                    a_loc, a_rot, a_scl = child_actual_mid_world.decompose()

                    loc_diff = (p_loc - a_loc).length
                    rot_diff = p_rot.rotation_difference(a_rot).angle
                    scl_diff = (p_scl - a_scl).length

                    if (loc_diff > self.location_threshold or
                        rot_diff > self.rotation_threshold or
                        scl_diff > self.scale_threshold):

                        frames_to_bake.add(mid_frame)
                        check_queue.append((start_frame, mid_frame))
                        check_queue.append((mid_frame, end_frame))

                wm.progress_end()
            else:
                frames_to_bake = set(sorted_initial_frames)

            total_final_frames += len(frames_to_bake)

            # 3. 计算每帧的局部矩阵
            sorted_bake_frames = sorted(list(frames_to_bake))
            local_matrices = {}
            original_frame = scene.frame_current

            for frame in sorted_bake_frames:
                scene.frame_set(frame)
                child_world = child.evaluated_get(depsgraph).matrix_world.copy()
                parent_world = parent_obj.evaluated_get(depsgraph).matrix_world.copy()
                local_matrix = parent_world.inverted() @ child_world
                local_matrices[frame] = local_matrix

            # 4. 清除子对象动画，建立父子关系，插入局部关键帧
            if child.animation_data:
                child.animation_data_clear()

            child.parent = parent_obj
            child.matrix_parent_inverse = parent_obj.matrix_world.inverted()  # 初始绑定

            for frame, local_matrix in local_matrices.items():
                # 应用局部矩阵
                child.matrix_local = local_matrix
                child.keyframe_insert(data_path="location", frame=frame)
                child.keyframe_insert(data_path="rotation_quaternion", frame=frame)
                child.keyframe_insert(data_path="rotation_euler", frame=frame)
                child.keyframe_insert(data_path="scale", frame=frame)

            processed_count += 1

        # 5. 恢复当前帧
        scene.frame_set(scene.frame_current)

        if processed_count > 0:
            avg_original = total_original_frames // processed_count if processed_count > 0 else 0
            avg_final = total_final_frames // processed_count if processed_count > 0 else 0
            self.report({'INFO'}, f"✅ 绑定完成！处理了 {processed_count} 个对象，平均每个: {avg_original} → {avg_final} 帧。")
        else:
            self.report({'INFO'}, "没有对象需要绑定。")
            
        return {'FINISHED'}


def register():
    bpy.utils.register_class(OBJECT_OT_adaptive_unparent)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_adaptive_unparent)


if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register()

    # 弹窗执行逻辑
    override_context = None
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                override_context = bpy.context.copy()
                override_context.update({
                    'window': window,
                    'screen': screen,
                    'area': area,
                    'region': next((r for r in area.regions if r.type == 'WINDOW'), None)
                })
                break
        if override_context:
            break

    if override_context:
        with bpy.context.temp_override(**override_context):
            bpy.ops.object.adaptive_unparent_popup('INVOKE_DEFAULT')
    else:
        print("错误: 未找到有效的3D视图以上下文来运行脚本。")