# script_id: aca0bc2a-076f-4ecc-a6cd-ad15254dabd0
# -*- coding: utf-8 -*-
import bpy
from collections import Counter

# -----------------------------------------------------------
# 工具函数：把 Action 某个槽的 name_display 改为 new_name
# -----------------------------------------------------------
def rename_slot(action, new_name):
    """
    先尝试 slots['OBLegacy Slot']；
    若无，则用 slots[0]；
    如果 action 上根本没有 slots 属性或集合为空，则返回 False
    """
    if not action or not hasattr(action, "slots"):
        return False

    slot = action.slots.get("OBLegacy Slot")
    if slot is None and len(action.slots) > 0:
        slot = action.slots[0]          # 退而求其次——第 1 个槽

    if slot and hasattr(slot, "name_display"):
        slot.name_display = new_name
        return True

    return False


# -----------------------------------------------------------
# 主函数：逐物体设置活动动作 + 改槽名
# -----------------------------------------------------------
def set_active_action_per_object_v7():
    selected_objects = bpy.context.selected_objects
    if not selected_objects:
        print("❌ 请选择物体后再运行脚本。")
        return {'CANCELLED'}

    print("\n=== 开始逐一设置活动动作 (V7) ===")

    for obj in selected_objects:
        print(f"\n--- 处理物体: '{obj.name}' ---")

        act_reg, act_shape = None, None
        got_reg_by_sel, got_shp_by_sel = False, False

        # ---------- 1) 优先：被选中的 NLA 片段 ----------
        if obj.animation_data and obj.animation_data.nla_tracks:
            for tr in obj.animation_data.nla_tracks:
                for st in tr.strips:
                    if st.select and st.action:
                        act_reg = st.action
                        got_reg_by_sel = True
                        break
                if got_reg_by_sel:
                    break

        if obj.type == 'MESH' and obj.data.shape_keys:
            sk_anim = obj.data.shape_keys.animation_data
            if sk_anim and sk_anim.nla_tracks:
                for tr in sk_anim.nla_tracks:
                    for st in tr.strips:
                        if st.select and st.action:
                            act_shape = st.action
                            got_shp_by_sel = True
                            break
                    if got_shp_by_sel:
                        break

        # ---------- 2) 猜测：出现频率最多 ----------
        if not act_reg and obj.animation_data and obj.animation_data.nla_tracks:
            cnt = Counter(s.action for t in obj.animation_data.nla_tracks
                                      for s in t.strips if s.action)
            if cnt:
                act_reg = cnt.most_common(1)[0][0]

        if (not act_shape and obj.type == 'MESH' and obj.data.shape_keys and
                obj.data.shape_keys.animation_data):
            sk_anim = obj.data.shape_keys.animation_data
            cnt = Counter(s.action for t in sk_anim.nla_tracks
                                      for s in t.strips if s.action) if sk_anim else {}
            if cnt:
                act_shape = cnt.most_common(1)[0][0]

        # ---------- 3) 应用并改槽名 ----------
        if act_reg:
            obj.animation_data.action = act_reg
            ok = rename_slot(act_reg, obj.name)
            mode = "选中片段" if got_reg_by_sel else "智能猜测"
            print(f"  ✓ [{mode}] 常规动作 → '{act_reg.name}' "
                  f"{'(槽已改名)' if ok else '(无槽可改)'}")

        if act_shape:
            obj.data.shape_keys.animation_data.action = act_shape
            ok = rename_slot(act_shape, obj.name)
            mode = "选中片段" if got_shp_by_sel else "智能猜测"
            print(f"  ✓ [{mode}] 形态键动作 → '{act_shape.name}' "
                  f"{'(槽已改名)' if ok else '(无槽可改)'}")

        if not (act_reg or act_shape):
            print("  - 未找到可设置的 NLA 动作。")

    print("\n✅ 全部处理完毕。")
    return {'FINISHED'}

import bpy

def clear_nla_tracks(obj):
    """
    清除物体动画数据，包括形态键的NLA轨道。
    """
    # 清除对象本身的NLA轨道
    if obj.animation_data and obj.animation_data.nla_tracks:
        for track in obj.animation_data.nla_tracks[:]:  # 使用副本避免迭代问题
            obj.animation_data.nla_tracks.remove(track)
        print(f"已成功清除 {obj.name} 的所有 NLA 轨道。")
    
    # 检查并清除对象数据（形态键）的NLA轨道
    if hasattr(obj.data, "shape_keys") and obj.data.shape_keys is not None:
        if obj.data.shape_keys.animation_data:
            for track in obj.data.shape_keys.animation_data.nla_tracks[:]:
                obj.data.shape_keys.animation_data.nla_tracks.remove(track)
            print(f"已成功清除 {obj.name} 的形态键 NLA 轨道。")
    else:
        print(f"{obj.name} 没有形态键。")



# -------------------- 运行脚本 --------------------
if __name__ == "__main__":
    set_active_action_per_object_v7()
    # 示例：对选定对象进行操作
    for obj in bpy.context.selected_objects:
        clear_nla_tracks(obj)
