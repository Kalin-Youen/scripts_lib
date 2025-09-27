# script_id: 8f45e490-c326-4a7c-b5ba-ddc036da38f3
import bpy

def cleanup_action_smarter(action, threshold=0.001):
    """
    智能清理指定动作（Action）中的冗余关键帧。
    仅删除严格处于前后关键帧线性插值范围内的中间帧。
    保留所有非线性、保持（CONSTANT）、跳跃或缓动的关键帧。
    
    参数:
        action (bpy.types.Action): 要清理的动作
        threshold (float): 判断冗余的容差值（推荐 0.001 用于形态键，0.0001~0.01 用于变换）
    """
    if not action or not action.fcurves:
        print(f"⚠️ 动作 '{action.name}' 无 F-Curves，跳过清理。")
        return

    print(f"🧹 开始清理动作: '{action.name}' (阈值: {threshold})")
    total_removed = 0

    for fcurve in action.fcurves:
        keyframes = list(fcurve.keyframe_points)
        num_keys = len(keyframes)
        
        if num_keys < 3:
            continue  # 至少需要3帧才能删中间

        to_remove = []  # 存储要删除的索引
        anchor_idx = 0  # 上一个“锚点”关键帧索引（不能被删除的帧）

        # 遍历中间帧（从第1个到倒数第2个）
        for i in range(1, num_keys - 1):
            prev_kf = keyframes[anchor_idx]
            curr_kf = keyframes[i]
            next_kf = keyframes[i + 1]

            # === 1. 时间比例 t ===
            frame_delta = next_kf.co.x - prev_kf.co.x
            if frame_delta == 0:
                continue  # 时间重叠，跳过（异常情况）

            t = (curr_kf.co.x - prev_kf.co.x) / frame_delta

            # === 2. 线性预测值 ===
            predicted_value = prev_kf.co.y + t * (next_kf.co.y - prev_kf.co.y)

            # === 3. 判断是否接近线性 ===
            if abs(curr_kf.co.y - predicted_value) < threshold:
                # 即使值在线性上，还要看插值类型！
                if curr_kf.interpolation == 'CONSTANT':
                    # 🔒 这是“保持帧”，不能删！必须保留
                    anchor_idx = i  # 更新锚点为当前帧
                else:
                    # 是线性中间帧，且不是保持帧 → 可删
                    to_remove.append(i)
            else:
                # 值不在线性上 → 是重要帧（拐点、缓动等）
                anchor_idx = i  # 更新锚点

        # === 批量删除（从后往前）===
        for idx in sorted(to_remove, reverse=True):
            fcurve.keyframe_points.remove(fcurve.keyframe_points[idx])
        total_removed += len(to_remove)

    print(f"✅ 清理完成！共移除 {total_removed} 个冗余关键帧。")


# ===========================
# ✅ 使用示例（可删除或注释）
# ===========================

# 示例1：清理当前选中物体的动作
if __name__ == "__main__":
    obj = bpy.context.active_object
    if obj and obj.animation_data and obj.animation_data.action:
        cleanup_action_smarter(obj.animation_data.action, threshold=0.001)
    else:
        print("❌ 无活动物体或无动作数据。")

# 示例2：清理所有动作（谨慎使用）
# for action in bpy.data.actions:
#     cleanup_action_smarter(action, threshold=0.001)