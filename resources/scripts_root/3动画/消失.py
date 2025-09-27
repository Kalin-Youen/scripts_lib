# script_id: 89c42ee5-9bcc-450b-90eb-c7328380afec
import bpy

def make_disappear_for_selected():
    """
    让所有选中的物体在时间轴的当前帧“消失”。
    它会为每个物体在前一帧记录正常状态，在当前帧将其缩放设置为0。
    """

    # 1. 获取上下文和所有选中的物体
    context = bpy.context
    selected_objects = context.selected_objects # <--- 关键改动
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

    print(f"✨ 正在为 {len(selected_objects)} 个选中的物体创建消失动画...")

    # --- 关键改动：遍历所有选中的物体 ---
    for obj in selected_objects:
        
        print(f"   -> 正在处理 '{obj.name}'...")

        # 4. 保存该物体的原始变换状态
        original_loc = obj.location.copy()
        original_rot = obj.rotation_euler.copy()
        original_scale = obj.scale.copy()
        
        # 5. 在前一帧插入“正常状态”的关键帧
        obj.keyframe_insert(data_path="location", frame=previous_frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=previous_frame)
        obj.keyframe_insert(data_path="scale", frame=previous_frame)

        # 6. 在当前帧插入“消失状态”的关键帧
        obj.scale = (0, 0, 0)
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
    make_disappear_for_selected()

