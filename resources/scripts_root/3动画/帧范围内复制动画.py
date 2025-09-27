# script_id: 31ce79cd-d399-41fd-9adb-ae2f796c29d9
# -*- coding: utf-8 -*-
# ──────────────────────────────────────────────────────────
#   智能动画复制工具 V3.2
#   - 新增功能: 在粘贴模式下，提供一个“再次复制”的选项，可以直接覆盖剪贴板并复制当前物体的动画。
#   - 修复了在新版Blender中的API兼容性问题。
#   - 选中多个物体: 将活动物体的动画批量复制到其他选中物体。
#   - 选中一个物体:
#     - 若剪贴板有数据: 切换为粘贴模式（可选择再次复制）。
#     - 若剪贴板无数据: 切换为复制模式。
# ──────────────────────────────────────────────────────────
import bpy
import json

# --- 核心功能 ---

def transfer_animation(source_action, target_obj, data_block_type, start_frame, end_frame):
    """通用核心函数：将源Action数据在指定帧范围内，应用到目标物体上。"""
    if not source_action: return

    target_data_block = None
    if data_block_type == 'OBJECT':
        target_data_block = target_obj
    elif data_block_type == 'SHAPE_KEY':
        if target_obj.data and hasattr(target_obj.data, 'shape_keys') and target_obj.data.shape_keys:
            target_data_block = target_obj.data.shape_keys
        else:
            return # 无形态键则静默失败

    if not target_data_block.animation_data: target_data_block.animation_data_create()
    if not target_data_block.animation_data.action:
        action_name = f"{target_obj.name}_{data_block_type}_Action"
        target_data_block.animation_data.action = bpy.data.actions.new(name=action_name)
    target_action = target_data_block.animation_data.action

    for source_fcurve in source_action.fcurves:
        # 【*** 已修正 ***】 'index' 参数必须作为关键字参数传入
        target_fcurve = target_action.fcurves.find(
            data_path=source_fcurve.data_path, 
            index=source_fcurve.array_index
        )
        if not target_fcurve:
            target_fcurve = target_action.fcurves.new(
                data_path=source_fcurve.data_path, 
                index=source_fcurve.array_index
            )

        keys_to_remove = [k for k in target_fcurve.keyframe_points if start_frame <= k.co.x <= end_frame]
        for k in reversed(keys_to_remove): target_fcurve.keyframe_points.remove(k)

        keys_to_copy = [k for k in source_fcurve.keyframe_points if start_frame <= k.co.x <= end_frame]
        if not keys_to_copy: continue

        for k in keys_to_copy:
            new_key = target_fcurve.keyframe_points.insert(k.co.x, k.co.y)
            new_key.interpolation, new_key.easing = k.interpolation, k.easing
            new_key.handle_left_type, new_key.handle_right_type = k.handle_left_type, k.handle_right_type
            new_key.handle_left, new_key.handle_right = k.handle_left.copy(), k.handle_right.copy()

def serialize_action(action):
    """将Action对象序列化为字典"""
    if not action: return None
    return {'fcurves': [{
        'data_path': fc.data_path, 'array_index': fc.array_index,
        'keyframe_points': [{'co': list(k.co), 'handle_left': list(k.handle_left),
                             'handle_right': list(k.handle_right), 'handle_left_type': k.handle_left_type,
                             'handle_right_type': k.handle_right_type, 'interpolation': k.interpolation,
                             'easing': k.easing} for k in fc.keyframe_points]
    } for fc in action.fcurves]}

def deserialize_action(data_dict, name):
    """将字典反序列化为新的Action对象"""
    if not data_dict or 'fcurves' not in data_dict: return None
    action = bpy.data.actions.new(name=name)
    for fc_data in data_dict['fcurves']:
        fc = action.fcurves.new(fc_data['data_path'], index=fc_data['array_index'])
        for k_data in fc_data['keyframe_points']:
            k = fc.keyframe_points.insert(k_data['co'][0], k_data['co'][1])
            k.handle_left, k.handle_right = k_data['handle_left'], k_data['handle_right']
            k.handle_left_type, k.handle_right_type = k_data['handle_left_type'], k_data['handle_right_type']
            k.interpolation, k.easing = k_data['interpolation'], k_data['easing']
    return action

def get_clipboard_animation_data():
    """安全地获取并验证剪贴板数据"""
    try:
        data = json.loads(bpy.context.window_manager.clipboard)
        if isinstance(data, dict) and ('transform_action' in data or 'shapekey_action' in data):
            return data
    except (json.JSONDecodeError, Exception):
        pass
    return None

# --- 主操作员 (THE ONLY OPERATOR YOU NEED) ---

class WM_OT_SmartAnimationCopy(bpy.types.Operator):
    """智能动画复制工具，根据选择和剪贴板状态自动切换模式"""
    bl_idname = "wm.smart_animation_copy"
    bl_label = "智能动画复制"
    bl_options = {'REGISTER', 'UNDO'}

    start_frame: bpy.props.IntProperty(name="起始帧")
    end_frame: bpy.props.IntProperty(name="结束帧")

    # 【新增】用于在粘贴模式下强制执行复制操作的选项
    override_and_copy: bpy.props.BoolProperty(
        name="再次复制 (覆盖剪贴板)",
        description="勾选此项以强制执行复制操作，即使剪贴板已有数据",
        default=False
    )
    
    # 内部属性，用于控制UI和执行逻辑
    mode: bpy.props.StringProperty(internal=True)

    @classmethod
    def poll(cls, context):
        return context.active_object and context.selected_objects

    def invoke(self, context, event):
        num_selected = len(context.selected_objects)
        
        # --- 逻辑判断核心 ---
        if num_selected >= 2:
            self.mode = 'DIRECT_COPY'
            self.start_frame = context.scene.frame_start
            self.end_frame = context.scene.frame_end
        else: # num_selected == 1
            clipboard_data = get_clipboard_animation_data()
            if clipboard_data:
                self.mode = 'PASTE_CLIPBOARD'
                # 从剪贴板智能读取默认帧范围
                self.start_frame, self.end_frame = clipboard_data.get('frame_range', 
                                                                    (context.scene.frame_start, context.scene.frame_end))
            else:
                self.mode = 'COPY_CLIPBOARD'
                self.start_frame = context.scene.frame_start
                self.end_frame = context.scene.frame_end

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        
        # --- UI动态绘制 ---
        if self.mode == 'DIRECT_COPY':
            num_others = len(context.selected_objects) - 1
            layout.label(text=f"将 '{context.active_object.name}' 动画复制到其它 {num_others} 个物体", icon='COPY_ID')
        elif self.mode == 'PASTE_CLIPBOARD':
            layout.label(text=f"从剪贴板粘贴动画到 '{context.active_object.name}'", icon='PASTEDOWN')
            # 【新增UI】在粘贴模式下显示此选项
            layout.prop(self, "override_and_copy")
        elif self.mode == 'COPY_CLIPBOARD':
            layout.label(text=f"复制 '{context.active_object.name}' 动画到剪贴板", icon='COPYDOWN')

        box = layout.box()
        row = box.row()
        row.prop(self, "start_frame")
        row.prop(self, "end_frame")

    def _execute_copy_to_clipboard(self, context, is_override=False):
        """【重构】将复制到剪贴板的逻辑提取为独立方法"""
        obj = context.active_object
        clipboard_data = {'frame_range': (self.start_frame, self.end_frame)}
        
        # 复制物体变换动画
        if obj.animation_data and obj.animation_data.action:
            clipboard_data['transform_action'] = serialize_action(obj.animation_data.action)
        
        # 复制形态键动画
        sk = obj.data.shape_keys if hasattr(obj.data, 'shape_keys') else None
        if sk and sk.animation_data and sk.animation_data.action:
            clipboard_data['shapekey_action'] = serialize_action(sk.animation_data.action)
        
        if len(clipboard_data) == 1: # 只有frame_range
            self.report({'WARNING'}, "没有找到可复制的动画数据。")
            return {'CANCELLED'}

        context.window_manager.clipboard = json.dumps(clipboard_data, indent=2)
        
        report_message = "已覆盖剪贴板并重新复制动画。" if is_override else "动画已复制到剪贴板。"
        self.report({'INFO'}, report_message)
        return {'FINISHED'}

    def execute(self, context):
        # --- 逻辑执行核心 ---
        if self.mode == 'DIRECT_COPY':
            source_obj = context.active_object
            target_objs = [obj for obj in context.selected_objects if obj != source_obj]
            for target_obj in target_objs:
                # 复制物体变换动画
                if source_obj.animation_data and source_obj.animation_data.action:
                    transfer_animation(source_obj.animation_data.action, target_obj, 'OBJECT', self.start_frame, self.end_frame)
                # 复制形态键动画
                source_sk = source_obj.data.shape_keys if hasattr(source_obj.data, 'shape_keys') else None
                if source_sk and source_sk.animation_data and source_sk.animation_data.action:
                    transfer_animation(source_sk.animation_data.action, target_obj, 'SHAPE_KEY', self.start_frame, self.end_frame)
            self.report({'INFO'}, f"已将动画从 '{source_obj.name}' 复制到 {len(target_objs)} 个物体。")

        elif self.mode == 'COPY_CLIPBOARD':
            return self._execute_copy_to_clipboard(context)

        elif self.mode == 'PASTE_CLIPBOARD':
            # 【新增逻辑】检查复选框状态
            if self.override_and_copy:
                # 如果勾选，则执行复制操作，并传递一个标记用于显示不同的提示信息
                return self._execute_copy_to_clipboard(context, is_override=True)
            else:
                # 否则，执行原来的粘贴操作
                obj = context.active_object
                clipboard_data = get_clipboard_animation_data()
                if not clipboard_data:
                    self.report({'ERROR'}, "剪贴板数据无效或已丢失。")
                    return {'CANCELLED'}
                
                if 'transform_action' in clipboard_data:
                    action = deserialize_action(clipboard_data['transform_action'], f"Pasted_Transform_{obj.name}")
                    transfer_animation(action, obj, 'OBJECT', self.start_frame, self.end_frame)
                if 'shapekey_action' in clipboard_data:
                    action = deserialize_action(clipboard_data['shapekey_action'], f"Pasted_ShapeKey_{obj.name}")
                    transfer_animation(action, obj, 'SHAPE_KEY', self.start_frame, self.end_frame)
                self.report({'INFO'}, f"已从剪贴板粘贴动画到 '{obj.name}'。")

        return {'FINISHED'}


# --- 注册 ---
def register():
    bpy.utils.register_class(WM_OT_SmartAnimationCopy)

def unregister():
    bpy.utils.unregister_class(WM_OT_SmartAnimationCopy)

if __name__ == "__main__":
    # 方便测试：如果脚本已注册，先注销再注册，避免报错
    if "WM_OT_SmartAnimationCopy" in dir(bpy.types):
        unregister()
    register()
    
    # 【最终修复】在调用操作符前，完整地模拟poll()方法的检查逻辑。
    # 必须同时存在活动物体和选中物体列表，才能调用操作符。
    if bpy.context.active_object and bpy.context.selected_objects:
        # 模拟调用操作符，打开UI面板
        bpy.ops.wm.smart_animation_copy('INVOKE_DEFAULT')
    else:
        # 如果没有选中物体，则在系统控制台打印清晰的提示信息
        print("智能动画复制工具提示：请在3D视图中至少选择一个物体，然后重新运行脚本进行测试。")

