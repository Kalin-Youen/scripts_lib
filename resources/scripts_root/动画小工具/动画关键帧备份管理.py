# script_id: 9a4428e4-a679-4c5a-b613-a709c7518afd
# -*- coding: utf-8 -*-
# ──────────────────────────────────────────────────────────
#   关键帧剪贴板管理器 V1.5 (修复版)
#   - 修复: 解决了恢复后的关键帧类型(Type)错误变为“极端”的问题。
#   - 升级: 现在可以完整备份和恢复关键帧的类型(普通/过渡/极端等)。
# ──────────────────────────────────────────────────────────
import bpy
import json
import uuid
from bpy.props import StringProperty, CollectionProperty, IntProperty, BoolProperty, EnumProperty

# =============================================================================
#   1. 核心数据结构 (Data Structures)
# =============================================================================
class KC_KeyframeClipItem(bpy.types.PropertyGroup):
    name: StringProperty(name="片段名称", default="新动画片段")
    owner_names_json: StringProperty(name="所属物体JSON")
    keyframe_data_json: StringProperty(name="关键帧数据JSON")
    unique_id: StringProperty(name="唯一ID")

class KC_ObjectListItem(bpy.types.PropertyGroup):
    name: StringProperty()

# =============================================================================
#   2. 核心功能函数 (Core Functions)
# =============================================================================
def get_selected_keyframes(context):
    """【已升级】同时获取物体变换和形态键的关键帧，并包含关键帧类型(type)"""
    clips_data = {}
    for obj in context.selected_objects:
        obj_data = {}
        
        # --- 提取函数，用于从Action中获取数据 ---
        def get_fcurves_data_from_action(action):
            fcurves_data = []
            for fcurve in action.fcurves:
                selected_points = []
                for k in fcurve.keyframe_points:
                    if k.select_control_point:
                        point_data = {
                            'co': tuple(k.co), 'handle_left': tuple(k.handle_left), 
                            'handle_right': tuple(k.handle_right), 'handle_left_type': k.handle_left_type,
                            'handle_right_type': k.handle_right_type, 'interpolation': k.interpolation,
                            'easing': k.easing,
                            # 【核心修复】备份关键帧的 type 属性
                            'type': k.type
                        }
                        selected_points.append(point_data)
                
                if selected_points:
                    fcurves_data.append({'data_path': fcurve.data_path, 'array_index': fcurve.array_index,
                                         'keyframe_points': selected_points})
            return fcurves_data

        # --- 获取物体变换动画 ---
        if obj.animation_data and obj.animation_data.action:
            object_fcurves_data = get_fcurves_data_from_action(obj.animation_data.action)
            if object_fcurves_data:
                obj_data['object_anim'] = {'fcurves': object_fcurves_data}

        # --- 获取形态键动画 ---
        if obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys and \
           obj.data.shape_keys.animation_data and obj.data.shape_keys.animation_data.action:
            shape_key_fcurves_data = get_fcurves_data_from_action(obj.data.shape_keys.animation_data.action)
            if shape_key_fcurves_data:
                obj_data['shape_key_anim'] = {'fcurves': shape_key_fcurves_data}
        
        if obj_data:
            clips_data[obj.name] = obj_data
            
    return clips_data

def delete_selected_keyframes(context):
    for obj in context.selected_objects:
        if obj.animation_data and obj.animation_data.action:
            for fcurve in obj.animation_data.action.fcurves:
                for k in reversed([k for k in fcurve.keyframe_points if k.select_control_point]): fcurve.keyframe_points.remove(k)
        if obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys and \
           obj.data.shape_keys.animation_data and obj.data.shape_keys.animation_data.action:
            for fcurve in obj.data.shape_keys.animation_data.action.fcurves:
                for k in reversed([k for k in fcurve.keyframe_points if k.select_control_point]): fcurve.keyframe_points.remove(k)

def get_key_range(fcurves_data):
    min_frame, max_frame = float('inf'), float('-inf')
    found_keys = False
    for fc_data in fcurves_data:
        for k_data in fc_data['keyframe_points']:
            found_keys = True
            frame = k_data['co'][0]
            min_frame = min(min_frame, frame); max_frame = max(max_frame, frame)
    return (int(round(min_frame)), int(round(max_frame))) if found_keys else None

def clear_keys_in_range(action, frame_range, channels_to_clear):
    if not action or not frame_range: return
    min_frame, max_frame = frame_range
    path_prefixes = set()
    if 'location' in channels_to_clear: path_prefixes.add('location')
    if 'rotation' in channels_to_clear: path_prefixes.add('rotation_euler'); path_prefixes.add('rotation_quaternion')
    if 'scale' in channels_to_clear: path_prefixes.add('scale')
    if 'shape_keys' in channels_to_clear: path_prefixes.add('key_blocks')
    for fcurve in action.fcurves:
        if any(fcurve.data_path.startswith(prefix) for prefix in path_prefixes):
            for k in reversed([k for k in fcurve.keyframe_points if min_frame <= k.co.x <= max_frame]):
                fcurve.keyframe_points.remove(k)

def restore_keyframes_from_clip(context, clip_item, options):
    try: clip_data = json.loads(clip_item.keyframe_data_json)
    except json.JSONDecodeError: print(f"错误：片段 '{clip_item.name}' 的数据已损坏。"); return 0
    
    restored_count = 0
    # --- 提取函数，用于向Action中恢复数据 ---
    def restore_fcurves_to_action(action, fcurves_data, clear_range_options, channel_filter):
        if clear_range_options['clear']:
            key_range = get_key_range(fcurves_data)
            clear_keys_in_range(action, key_range, clear_range_options['channels'])

        for fc_data in fcurves_data:
            data_path = fc_data['data_path']
            # 根据通道过滤
            passes_filter = (channel_filter is None) or \
                            (channel_filter.get('location') and data_path.startswith('location')) or \
                            (channel_filter.get('rotation') and data_path.startswith('rotation')) or \
                            (channel_filter.get('scale') and data_path.startswith('scale'))
            
            if passes_filter:
                fcurve = action.fcurves.find(data_path, index=fc_data['array_index'])
                if not fcurve: fcurve = action.fcurves.new(data_path, index=fc_data['array_index'])
                for k_data in fc_data.get('keyframe_points', []):
                    frame, value = k_data['co']
                    new_key = fcurve.keyframe_points.insert(frame, value, options={'NEEDED'})
                    new_key.handle_left, new_key.handle_right = k_data['handle_left'], k_data['handle_right']
                    new_key.handle_left_type, new_key.handle_right_type = k_data['handle_left_type'], k_data['handle_right_type']
                    new_key.interpolation, new_key.easing = k_data['interpolation'], k_data['easing']
                    # 【核心修复】恢复关键帧的 type 属性，并向后兼容
                    new_key.type = k_data.get('type', 'KEYFRAME')
    
    for obj_name, anim_data in clip_data.items():
        target_obj = context.scene.objects.get(obj_name)
        if not target_obj: continue
        
        # --- 恢复物体变换动画 ---
        if options['restore_transforms'] and 'object_anim' in anim_data:
            if not target_obj.animation_data: target_obj.animation_data_create()
            if not target_obj.animation_data.action: target_obj.animation_data.action = bpy.data.actions.new(name=f"{target_obj.name}_Action")
            
            clear_opts = {'clear': options['clear_range'], 'channels': {'location', 'rotation', 'scale'}}
            channel_opts = {'location': options['restore_location'], 'rotation': options['restore_rotation'], 'scale': options['restore_scale']}
            restore_fcurves_to_action(target_obj.animation_data.action, anim_data['object_anim']['fcurves'], clear_opts, channel_opts)
            
        # --- 恢复形态键动画 ---
        if options['restore_shape_keys'] and 'shape_key_anim' in anim_data:
            if target_obj.data and hasattr(target_obj.data, 'shape_keys') and target_obj.data.shape_keys:
                shape_keys = target_obj.data.shape_keys
                if not shape_keys.animation_data: shape_keys.animation_data_create()
                if not shape_keys.animation_data.action: shape_keys.animation_data.action = bpy.data.actions.new(name=f"{shape_keys.name}_Action")

                clear_opts = {'clear': options['clear_range'], 'channels': {'shape_keys'}}
                restore_fcurves_to_action(shape_keys.animation_data.action, anim_data['shape_key_anim']['fcurves'], clear_opts, None)
        
        restored_count +=1
    context.area.tag_redraw()
    return restored_count

# =============================================================================
#   3. 操作符 (Operators)
# =============================================================================
class KC_OT_StoreSelectedKeyframes(bpy.types.Operator):
    bl_idname = "scene.kc_store_selected_keyframes"; bl_label = "新建动画片段"; bl_options = {'REGISTER', 'UNDO'}
    name: StringProperty(name="片段名称", default="新动画片段")
    delete_keys: BoolProperty(name="删除原始关键帧", description="勾选后，保存片段的同时会删除时间轴上的原始关键帧", default=False)
    @classmethod
    def poll(cls, context):
        if not context.selected_objects: return False
        for obj in context.selected_objects:
            if obj.animation_data and obj.animation_data.action:
                if any(k.select_control_point for fc in obj.animation_data.action.fcurves for k in fc.keyframe_points): return True
            if obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys and obj.data.shape_keys.animation_data:
                 if any(k.select_control_point for fc in obj.data.shape_keys.animation_data.action.fcurves for k in fc.keyframe_points): return True
        return False
    def invoke(self, context, event): return context.window_manager.invoke_props_dialog(self)
    def draw(self, context): self.layout.prop(self, "name"); self.layout.prop(self, "delete_keys")
    def execute(self, context):
        clip_data = get_selected_keyframes(context)
        if not clip_data: self.report({'WARNING'}, "没有找到任何选中的关键帧。"); return {'CANCELLED'}
        new_clip = context.scene.keyframe_clipboard_items.add()
        new_clip.name, new_clip.unique_id = self.name, str(uuid.uuid4())
        new_clip.keyframe_data_json = json.dumps(clip_data, indent=2)
        new_clip.owner_names_json = json.dumps(list(clip_data.keys()))
        if self.delete_keys: delete_selected_keyframes(context); self.report({'INFO'}, f"已创建片段 '{self.name}' 并删除原关键帧。")
        else: self.report({'INFO'}, f"已创建片段 '{self.name}'。")
        return {'FINISHED'}

class KC_OT_UpdateKeyframeClip(bpy.types.Operator):
    bl_idname = "scene.kc_update_keyframe_clip"; bl_label = "从此选区更新片段"; bl_options = {'REGISTER', 'UNDO'}
    clip_unique_id: StringProperty()
    @classmethod
    def poll(cls, context): return KC_OT_StoreSelectedKeyframes.poll(context)
    def execute(self, context):
        clip_to_update = next((c for c in context.scene.keyframe_clipboard_items if c.unique_id == self.clip_unique_id), None)
        if not clip_to_update: self.report({'ERROR'}, "找不到要更新的片段。"); return {'CANCELLED'}
        clip_data = get_selected_keyframes(context)
        if not clip_data: self.report({'WARNING'}, "没有找到任何选中的关键帧以用于更新。"); return {'CANCELLED'}
        clip_to_update.keyframe_data_json = json.dumps(clip_data, indent=2)
        clip_to_update.owner_names_json = json.dumps(list(clip_data.keys()))
        self.report({'INFO'}, f"已用当前选区更新片段 '{clip_to_update.name}'。"); return {'FINISHED'}

class KC_OT_RestoreKeyframeClip(bpy.types.Operator):
    bl_idname = "scene.kc_restore_keyframe_clip"; bl_label = "恢复动画片段"; bl_options = {'REGISTER', 'UNDO'}
    clip_unique_id: StringProperty()
    restore_location: BoolProperty(name="位置", default=True); restore_rotation: BoolProperty(name="旋转", default=True)
    restore_scale: BoolProperty(name="缩放", default=True); restore_shape_keys: BoolProperty(name="形态键", default=True)
    clear_range: BoolProperty(name="先清除范围内关键帧", description="恢复前，先删除目标通道上与片段时间范围重叠的旧关键帧", default=True)
    def invoke(self, context, event): return context.window_manager.invoke_props_dialog(self)
    def draw(self, context):
        layout = self.layout; box = layout.box(); box.label(text="恢复通道:")
        row = box.row(align=True); row.prop(self, "restore_location"); row.prop(self, "restore_rotation"); row.prop(self, "restore_scale")
        box.prop(self, "restore_shape_keys"); layout.separator(); layout.prop(self, "clear_range")
    def execute(self, context):
        clip_to_restore = next((c for c in context.scene.keyframe_clipboard_items if c.unique_id == self.clip_unique_id), None)
        if not clip_to_restore: self.report({'ERROR'}, "找不到指定的动画片段。"); return {'CANCELLED'}
        options = {'restore_location': self.restore_location, 'restore_rotation': self.restore_rotation,
                   'restore_scale': self.restore_scale, 'restore_shape_keys': self.restore_shape_keys,
                   'restore_transforms': self.restore_location or self.restore_rotation or self.restore_scale,
                   'clear_range': self.clear_range}
        count = restore_keyframes_from_clip(context, clip_to_restore, options)
        self.report({'INFO'}, f"已从片段 '{clip_to_restore.name}' 恢复 {count} 个物体的动画。"); return {'FINISHED'}

class KC_OT_DeleteKeyframeClip(bpy.types.Operator):
    bl_idname = "scene.kc_delete_keyframe_clip"; bl_label = "删除动画片段"; bl_options = {'REGISTER', 'UNDO'}
    clip_unique_id: StringProperty()
    def execute(self, context):
        idx_to_remove = next((i for i, c in enumerate(context.scene.keyframe_clipboard_items) if c.unique_id == self.clip_unique_id), -1)
        if idx_to_remove != -1: context.scene.keyframe_clipboard_items.remove(idx_to_remove); self.report({'INFO'}, "已删除片段。")
        else: self.report({'ERROR'}, "找不到要删除的片段。")
        return {'FINISHED'}

# =============================================================================
#   4. UI 面板和列表 (UI Panel & List)
# =============================================================================
class KC_UL_ObjectList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index): layout.label(text=item.name, icon='OBJECT_DATA')
class KC_UL_KeyframeClipList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        real_clip = next((c for c in context.scene.keyframe_clipboard_items if c.unique_id == item.unique_id), None)
        if real_clip: layout.prop(real_clip, "name", text="", emboss=False, icon='ANIM_DATA')

def update_active_object_and_clips(self, context):
    if 0 <= self.object_list_active_index < len(self.object_list):
        target_obj = context.scene.objects.get(self.object_list[self.object_list_active_index].name)
        if target_obj: context.view_layer.objects.active = target_obj

class KC_WM_KeyframeClipboardManager(bpy.types.Operator):
    bl_idname = "wm.kc_clipboard_manager"; bl_label = "关键帧剪贴板管理器"
    object_list: CollectionProperty(type=KC_ObjectListItem)
    object_list_active_index: IntProperty(update=update_active_object_and_clips)
    clip_list_for_active_object: CollectionProperty(type=KC_KeyframeClipItem)
    clip_list_active_index: IntProperty()
    filter_mode: EnumProperty(name="物体列表过滤", default='SELECTED',
        items=[('SELECTED', "仅显示选中", ""), ('ALL_WITH_CLIPS', "所有(有片段)", ""), ('SELECTED_WITH_CLIPS', "选中(有片段)", "")])
    
    def get_owner_names(self, clip_item):
        try: return set(json.loads(clip_item.owner_names_json))
        except (json.JSONDecodeError, TypeError): return set()
    def invoke(self, context, event): return context.window_manager.invoke_props_dialog(self, width=650)
    def populate_object_list(self, context):
        active_obj_name = self.object_list[self.object_list_active_index].name if 0 <= self.object_list_active_index < len(self.object_list) else ""
        self.object_list.clear()
        if self.filter_mode == 'ALL_WITH_CLIPS':
            owner_names = set().union(*(self.get_owner_names(c) for c in context.scene.keyframe_clipboard_items))
            for name in sorted(list(owner_names)): self.object_list.add().name = name
        elif self.filter_mode == 'SELECTED':
            for obj in context.selected_objects: self.object_list.add().name = obj.name
        elif self.filter_mode == 'SELECTED_WITH_CLIPS':
            owner_names = set().union(*(self.get_owner_names(c) for c in context.scene.keyframe_clipboard_items))
            selected_names = {obj.name for obj in context.selected_objects}
            for name in sorted(list(owner_names.intersection(selected_names))): self.object_list.add().name = name
        new_idx = next((i for i, item in enumerate(self.object_list) if item.name == active_obj_name), -1)
        if new_idx != -1: self.object_list_active_index = new_idx
        elif len(self.object_list) > 0: self.object_list_active_index = 0
    def update_clip_list(self, context):
        self.clip_list_for_active_object.clear()
        if 0 <= self.object_list_active_index < len(self.object_list):
            obj_name = self.object_list[self.object_list_active_index].name
            for clip in context.scene.keyframe_clipboard_items:
                if obj_name in self.get_owner_names(clip): self.clip_list_for_active_object.add().unique_id = clip.unique_id
    def draw(self, context):
        layout = self.layout; scene = context.scene; self.populate_object_list(context); self.update_clip_list(context)
        row = layout.row(); row.label(text="动画片段库", icon='ANIM_DATA'); row.operator(KC_OT_StoreSelectedKeyframes.bl_idname, text="新建片段", icon='ADD')
        layout.separator(); split = layout.split(factor=0.4)
        col_left = split.column(); col_left.prop(self, "filter_mode", expand=True)
        col_left.template_list("KC_UL_ObjectList", "", self, "object_list", self, "object_list_active_index", rows=8)
        col_right = split.column()
        active_obj_name = self.object_list[self.object_list_active_index].name if 0 <= self.object_list_active_index < len(self.object_list) else ""
        col_right.label(text=f"'{active_obj_name}' 的片段:" if active_obj_name else "片段列表:")
        col_right.template_list("KC_UL_KeyframeClipList", "", self, "clip_list_for_active_object", self, "clip_list_active_index", rows=8)
        active_clip_id = self.get_active_clip_unique_id()
        if active_clip_id:
            active_clip = next((c for c in scene.keyframe_clipboard_items if c.unique_id == active_clip_id), None)
            if active_clip:
                box = layout.box(); box.prop(active_clip, "name", text="重命名")
                owner_names = self.get_owner_names(active_clip); box.label(text=f"所属物体: {', '.join(owner_names)}")
                box.separator(); op_row = box.row(align=True)
                op_row.operator(KC_OT_RestoreKeyframeClip.bl_idname, text="恢复", icon='PASTEDOWN').clip_unique_id = active_clip_id
                op_row.operator(KC_OT_UpdateKeyframeClip.bl_idname, text="更新", icon='FILE_REFRESH').clip_unique_id = active_clip_id
                op_row.operator(KC_OT_DeleteKeyframeClip.bl_idname, text="删除", icon='TRASH').clip_unique_id = active_clip_id
    def get_active_clip_unique_id(self):
        if 0 <= self.clip_list_active_index < len(self.clip_list_for_active_object):
            return self.clip_list_for_active_object[self.clip_list_active_index].unique_id
        return ""
    def execute(self, context): return {'FINISHED'}

# =============================================================================
#   5. 注册与注销 (Registration)
# =============================================================================
classes = (
    KC_KeyframeClipItem, KC_ObjectListItem, KC_OT_StoreSelectedKeyframes, KC_OT_UpdateKeyframeClip, 
    KC_OT_RestoreKeyframeClip, KC_OT_DeleteKeyframeClip, KC_UL_ObjectList, KC_UL_KeyframeClipList,
    KC_WM_KeyframeClipboardManager,
)
def register():
    for cls in classes: bpy.utils.register_class(cls)
    bpy.types.Scene.keyframe_clipboard_items = CollectionProperty(type=KC_KeyframeClipItem)
def unregister():
    if hasattr(bpy.types.Scene, 'keyframe_clipboard_items'): del bpy.types.Scene.keyframe_clipboard_items
    for cls in reversed(classes):
        try: bpy.utils.unregister_class(cls)
        except RuntimeError: pass
if __name__ == "__main__":
    idname = KC_WM_KeyframeClipboardManager.bl_idname
    if idname in bpy.context.window_manager.operators.keys(): unregister()
    register()
    bpy.ops.wm.kc_clipboard_manager('INVOKE_DEFAULT')

