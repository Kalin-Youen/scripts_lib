# script_id: dcf4a6b9-0ee7-4321-9c49-f3287810ce84
import bpy

def make_appear_for_selected():
    """
    让所有选中的物体在时间轴的当前帧“出现”。
    它会为每个物体在前一帧设置缩放为0，在当前帧恢复正常状态。
    """
    
    # 1. 获取上下文和所有选中的物体
    context = bpy.context
    selected_objects = context.selected_objects  # <--- 关键改动
    scene = context.scene

    # 2. 检查是否有任何物体被选中
    if not selected_objects:
        print("❌ 错误：请至少选择一个物体。")
        return

    # 3. 获取帧信息并检查边界 (只需检查一次)
    current_frame = scene.frame_current
    previous_frame = current_frame - 1

    if previous_frame < scene.frame_start:
        print(f"❌ 错误：无法在场景起始帧 ({scene.frame_start}) 之前插入关键帧。")
        return

    print(f"✨ 正在为 {len(selected_objects)} 个选中的物体创建出现动画...")

    # --- 关键改动：遍历所有选中的物体 ---
    for obj in selected_objects:
        print(f"   -> 正在处理 '{obj.name}'...")

        # 4. 保存该物体的原始变换状态
        original_loc = obj.location.copy()
        original_rot = obj.rotation_euler.copy()
        original_scale = obj.scale.copy()

        # 5. 在前一帧插入“消失状态”的关键帧
        #    以实现“原地出现”效果
        obj.scale = (0, 0, 0)
        obj.keyframe_insert(data_path="location", frame=previous_frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=previous_frame)
        obj.keyframe_insert(data_path="scale", frame=previous_frame)

        # 6. 在当前帧插入“正常状态”的关键帧
        #    恢复物体原始的变换
        obj.location = original_loc
        obj.rotation_euler = original_rot
        obj.scale = original_scale
        obj.keyframe_insert(data_path="location", frame=current_frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=current_frame)
        obj.keyframe_insert(data_path="scale", frame=current_frame)

        # 7. 操作完成后，将该物体的状态恢复到原始状态
        obj.location = original_loc
        obj.rotation_euler = original_rot
        obj.scale = original_scale

    print("✅ 所有选中物体的操作均已成功！")


# --- 主执行部分 ---
if __name__ == "__main__":
    make_appear_for_selected()