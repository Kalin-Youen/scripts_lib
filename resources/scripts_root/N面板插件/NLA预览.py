# -*- coding: utf-8 -*-

bl_info = {
"name": "NLA 播放器 (NLA Player)",
"author": "代码高手 (AI)",
"version": (1, 4, 0),
"blender": (3, 0, 0),
"location": "3D View > N-Panel > NLA Player",
"description": "智能排序NLA轨道，全面支持物体和形态键动画，一键清理、启用、播放并设置帧范围。",
"warning": "",
"doc_url": "",
"category": "Animation",
}

import bpy
from bpy.props import StringProperty, IntProperty, CollectionProperty, BoolProperty
from bpy.types import Operator, Panel, PropertyGroup

# --- 1. 数据结构 ---

class NLA_PG_TrackItem(PropertyGroup):
    """存储单个NLA轨道的信息，增加形态键标识"""
    name: StringProperty(name="Track Name")
    frame_start: IntProperty(name="Start Frame")
    frame_end: IntProperty(name="End Frame")
    is_shape_key: BoolProperty(name="Is Shape Key Track", default=False)


# --- 2. 操作员 (Operators) ---

class NLA_OT_ClearActiveActions(Operator):
    """清除场景中所有物体和形态键的活动Action"""
    bl_idname = "nla_player.clear_active_actions"
    bl_label = "清理活动动画"
    bl_description = "清除所有物体及其形态键的活动Action，防止其覆盖NLA播放"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj_count = 0
        sk_count = 0
        for obj in bpy.data.objects:
            if obj.animation_data and obj.animation_data.action:
                obj.animation_data.action = None
                obj_count += 1

            if obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys:
                shape_key_data = obj.data.shape_keys
                if shape_key_data.animation_data and shape_key_data.animation_data.action:
                    shape_key_data.animation_data.action = None
                    sk_count += 1

        self.report({'INFO'}, f"清理了 {obj_count} 个物体和 {sk_count} 个形态键的活动动画。")
        return {'FINISHED'}


class NLA_OT_EnableAllTracks(Operator):
    """★ 新增：解锁并启用所有NLA轨道"""
    bl_idname = "nla_player.enable_all_tracks"
    bl_label = "启用所有轨道"
    bl_description = "取消所有物体和形态键NLA轨道的静音，并启用NLA回放"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj_with_nla = 0
        sk_with_nla = 0

        for obj in bpy.data.objects:
            # 处理物体NLA
            if obj.animation_data and obj.animation_data.nla_tracks:
                obj.animation_data.use_nla = True
                for track in obj.animation_data.nla_tracks:
                    track.mute = False
                obj_with_nla += 1

            # 处理形态键NLA
            if obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys:
                sk_data = obj.data.shape_keys
                if sk_data.animation_data and sk_data.animation_data.nla_tracks:
                    sk_data.animation_data.use_nla = True
                    for track in sk_data.animation_data.nla_tracks:
                        track.mute = False
                    sk_with_nla += 1

        self.report({'INFO'}, f"已在 {obj_with_nla} 个物体和 {sk_with_nla} 个形态键上启用所有NLA轨道。")
        return {'FINISHED'}


class NLA_OT_RefreshList(Operator):
    """扫描并以智能顺序刷新NLA轨道列表，包含形态键轨道"""
    bl_idname = "nla_player.refresh_list"
    bl_label = "刷新轨道列表"
    bl_description = "智能刷新物体和形态键的NLA轨道列表"

    def execute(self, context):
        scene = context.scene
        nla_tracks_collection = scene.nla_player_tracks
        nla_tracks_collection.clear()

        unique_tracks = {}
        ordered_names = []
        active_obj = context.active_object

        # --- 物体轨道扫描 ---
        if active_obj and active_obj.animation_data and active_obj.animation_data.nla_tracks:
            for track in active_obj.animation_data.nla_tracks:
                if track.name not in unique_tracks and track.strips:
                    first_strip = track.strips[0]
                    unique_tracks[track.name] = {
                        "start": int(first_strip.frame_start),
                        "end": int(first_strip.frame_end),
                        "is_sk": False,
                    }
                    ordered_names.append(track.name)

        other_track_names = []
        for obj in bpy.data.objects:
            if obj.animation_data and obj.animation_data.nla_tracks:
                for track in obj.animation_data.nla_tracks:
                    if track.name not in unique_tracks and track.strips:
                        first_strip = track.strips[0]
                        unique_tracks[track.name] = {
                            "start": int(first_strip.frame_start),
                            "end": int(first_strip.frame_end),
                            "is_sk": False,
                        }
                        other_track_names.append(track.name)
                ordered_names.extend(sorted(other_track_names))

        # --- 形态键轨道扫描 ---
        sk_track_names = []
        for obj in bpy.data.objects:
            if obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys:
                shape_key_data = obj.data.shape_keys
                if shape_key_data.animation_data and shape_key_data.animation_data.nla_tracks:
                    for track in shape_key_data.animation_data.nla_tracks:
                        prefixed_name = f"[形态] {track.name}"
                        if prefixed_name not in unique_tracks and track.strips:
                            first_strip = track.strips[0]
                            unique_tracks[prefixed_name] = {
                                "start": int(first_strip.frame_start),
                                "end": int(first_strip.frame_end),
                                "is_sk": True,
                            }
                        sk_track_names.append(prefixed_name)
                ordered_names.extend(sorted(list(set(sk_track_names))))

        if not unique_tracks:
            self.report({'INFO'}, "场景中未找到任何NLA轨道。")
            return {'CANCELLED'}

        for track_name in ordered_names:
            track_data = unique_tracks[track_name]
            item = nla_tracks_collection.add()
            item.name = track_name
            item.frame_start = track_data["start"]
            item.frame_end = track_data["end"]
            item.is_shape_key = track_data["is_sk"]

        self.report({'INFO'}, f"找到 {len(nla_tracks_collection)} 个唯一的NLA轨道。")
        return {'FINISHED'}


class NLA_OT_PlayTrack(Operator):
    """播放指定的NLA轨道，同时控制物体和形态键"""
    bl_idname = "nla_player.play_track"
    bl_label = "播放NLA轨道"
    bl_description = "激活所有相关物体/形态键的该轨道，更新帧范围并播放"

    track_name: StringProperty()
    frame_start: IntProperty()
    frame_end: IntProperty()
    is_shape_key: BoolProperty()

    def execute(self, context):
        scene = context.scene
        if not self.track_name: return {'CANCELLED'}

        scene.frame_start = self.frame_start
        scene.frame_end = self.frame_end

        original_track_name = self.track_name.replace("[形态] ", "")

        for obj in bpy.data.objects:
            if obj.animation_data and obj.animation_data.nla_tracks:
                found_track = False
                for track in obj.animation_data.nla_tracks:
                    is_active = (not self.is_shape_key and track.name == original_track_name)
                    track.mute = not is_active
                    if is_active:
                        found_track = True
                if found_track:
                    obj.animation_data.use_nla = True

            if obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys:
                sk_data = obj.data.shape_keys
                if sk_data.animation_data and sk_data.animation_data.nla_tracks:
                    found_sk_track = False
                    for track in sk_data.animation_data.nla_tracks:
                        is_active = (self.is_shape_key and track.name == original_track_name)
                        track.mute = not is_active
                        if is_active:
                            found_sk_track = True
                    if found_sk_track:
                        sk_data.animation_data.use_nla = True

        scene.frame_set(self.frame_start)
        bpy.ops.screen.animation_cancel(restore_frame=False)
        bpy.ops.screen.animation_play()

        self.report({'INFO'}, f"正在播放: {self.track_name} (帧 {self.frame_start}-{self.frame_end})")
        return {'FINISHED'}


# --- 2. 操作员 (Operators) --- (在现有操作员之后添加)

class NLA_OT_ReverseSelectedTracks(Operator):
    """反转所选物体的NLA轨道顺序（包括形态键轨道）"""
    bl_idname = "nla_player.reverse_selected_tracks"
    bl_label = "反转轨道顺序"
    bl_description = "将所选物体的所有NLA轨道（包括形态键轨道）顺序反转"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = [obj for obj in context.selected_objects if obj.animation_data and obj.animation_data.nla_tracks]
        
        # 检查是否有选中物体
        if not context.selected_objects:
            self.report({'WARNING'}, "请先选择物体")
            return {'CANCELLED'}
        
        # 检查选中物体是否有NLA轨道
        if not selected_objects:
            # 检查是否有形态键轨道
            has_shape_key_tracks = False
            for obj in context.selected_objects:
                if obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys:
                    if obj.data.shape_keys.animation_data and obj.data.shape_keys.animation_data.nla_tracks:
                        has_shape_key_tracks = True
                        break
            
            if not has_shape_key_tracks:
                self.report({'WARNING'}, "所选物体没有NLA轨道或形态键NLA轨道")
                return {'CANCELLED'}
        
        total_reversed = 0
        sk_total_reversed = 0
        
        # 处理物体NLA轨道
        for obj in selected_objects:
            if obj.animation_data and obj.animation_data.nla_tracks:
                tracks = obj.animation_data.nla_tracks
                if len(tracks) <= 1:
                    continue
                
                # 保存轨道信息
                track_data = []
                for track in tracks:
                    track_info = {
                        'name': track.name,
                        'mute': track.mute,
                        'is_solo': track.is_solo,
                        'strips': []
                    }
                    # 保存strip信息
                    for strip in track.strips:
                        strip_info = {
                            'name': strip.name,
                            'action': strip.action,
                            'frame_start': strip.frame_start,
                            'frame_end': strip.frame_end,
                            'blend_type': strip.blend_type,
                            'influence': strip.influence,
                            'use_animated_influence': strip.use_animated_influence,
                            'influence_driver': None,
                            'extrapolation': strip.extrapolation,
                            'blend_in': strip.blend_in,
                            'blend_out': strip.blend_out,
                            'repeat': strip.repeat,
                            'scale': strip.scale,
                            'use_animated_time': strip.use_animated_time,
                            'use_animated_time_cyclic': strip.use_animated_time_cyclic,
                        }
                        # 保存影响驱动器（如果存在）
                        if strip.use_animated_influence and strip.animation_data and strip.animation_data.drivers:
                            drivers = []
                            for driver in strip.animation_data.drivers:
                                drivers.append({
                                    'data_path': driver.data_path,
                                    'expression': driver.driver.expression if driver.driver else "",
                                })
                            strip_info['influence_driver'] = drivers
                        
                        track_info['strips'].append(strip_info)
                    track_data.append(track_info)
                
                # 清空现有轨道
                while len(tracks) > 0:
                    tracks.remove(tracks[0])
                
                # 按反转顺序重新创建轨道
                for track_info in reversed(track_data):
                    new_track = tracks.new()
                    new_track.name = track_info['name']
                    new_track.mute = track_info['mute']
                    new_track.is_solo = track_info['is_solo']
                    
                    # 重新添加strip
                    for strip_info in track_info['strips']:
                        if strip_info['action']:  # 确保action存在
                            new_strip = new_track.strips.new(
                                strip_info['name'], 
                                int(strip_info['frame_start']), 
                                strip_info['action']
                            )
                            new_strip.frame_end = strip_info['frame_end']
                            new_strip.blend_type = strip_info['blend_type']
                            new_strip.influence = strip_info['influence']
                            new_strip.use_animated_influence = strip_info['use_animated_influence']
                            new_strip.extrapolation = strip_info['extrapolation']
                            new_strip.blend_in = strip_info['blend_in']
                            new_strip.blend_out = strip_info['blend_out']
                            new_strip.repeat = strip_info['repeat']
                            new_strip.scale = strip_info['scale']
                            new_strip.use_animated_time = strip_info['use_animated_time']
                            new_strip.use_animated_time_cyclic = strip_info['use_animated_time_cyclic']
                            
                            # 恢复影响驱动器
                            if strip_info['use_animated_influence'] and strip_info['influence_driver']:
                                for driver_data in strip_info['influence_driver']:
                                    if hasattr(new_strip, 'animation_data') and new_strip.animation_data:
                                        driver = new_strip.animation_data.drivers.new(driver_data['data_path'])
                                        if driver and driver.driver:
                                            driver.driver.expression = driver_data['expression']
                    
                    total_reversed += 1
        
        # 处理形态键的NLA轨道
        for obj in context.selected_objects:
            if obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys:
                sk_data = obj.data.shape_keys
                if sk_data.animation_data and sk_data.animation_data.nla_tracks:
                    tracks = sk_data.animation_data.nla_tracks
                    if len(tracks) <= 1:
                        continue
                    
                    # 保存形态键轨道信息
                    sk_track_data = []
                    for track in tracks:
                        track_info = {
                            'name': track.name,
                            'mute': track.mute,
                            'is_solo': track.is_solo,
                            'strips': []
                        }
                        # 保存strip信息
                        for strip in track.strips:
                            strip_info = {
                                'name': strip.name,
                                'action': strip.action,
                                'frame_start': strip.frame_start,
                                'frame_end': strip.frame_end,
                                'blend_type': strip.blend_type,
                                'influence': strip.influence,
                                'use_animated_influence': strip.use_animated_influence,
                                'influence_driver': None,
                                'extrapolation': strip.extrapolation,
                                'blend_in': strip.blend_in,
                                'blend_out': strip.blend_out,
                                'repeat': strip.repeat,
                                'scale': strip.scale,
                                'use_animated_time': strip.use_animated_time,
                                'use_animated_time_cyclic': strip.use_animated_time_cyclic,
                            }
                            # 保存影响驱动器（如果存在）
                            if strip.use_animated_influence and strip.animation_data and strip.animation_data.drivers:
                                drivers = []
                                for driver in strip.animation_data.drivers:
                                    drivers.append({
                                        'data_path': driver.data_path,
                                        'expression': driver.driver.expression if driver.driver else "",
                                    })
                                strip_info['influence_driver'] = drivers
                            
                            track_info['strips'].append(strip_info)
                        sk_track_data.append(track_info)
                    
                    # 清空现有轨道
                    while len(tracks) > 0:
                        tracks.remove(tracks[0])
                    
                    # 按反转顺序重新创建轨道
                    for track_info in reversed(sk_track_data):
                        new_track = tracks.new()
                        new_track.name = track_info['name']
                        new_track.mute = track_info['mute']
                        new_track.is_solo = track_info['is_solo']
                        
                        # 重新添加strip
                        for strip_info in track_info['strips']:
                            if strip_info['action']:  # 确保action存在
                                new_strip = new_track.strips.new(
                                    strip_info['name'], 
                                    int(strip_info['frame_start']), 
                                    strip_info['action']
                                )
                                new_strip.frame_end = strip_info['frame_end']
                                new_strip.blend_type = strip_info['blend_type']
                                new_strip.influence = strip_info['influence']
                                new_strip.use_animated_influence = strip_info['use_animated_influence']
                                new_strip.extrapolation = strip_info['extrapolation']
                                new_strip.blend_in = strip_info['blend_in']
                                new_strip.blend_out = strip_info['blend_out']
                                new_strip.repeat = strip_info['repeat']
                                new_strip.scale = strip_info['scale']
                                new_strip.use_animated_time = strip_info['use_animated_time']
                                new_strip.use_animated_time_cyclic = strip_info['use_animated_time_cyclic']
                                
                                # 恢复影响驱动器
                                if strip_info['use_animated_influence'] and strip_info['influence_driver']:
                                    for driver_data in strip_info['influence_driver']:
                                        if hasattr(new_strip, 'animation_data') and new_strip.animation_data:
                                            driver = new_strip.animation_data.drivers.new(driver_data['data_path'])
                                            if driver and driver.driver:
                                                driver.driver.expression = driver_data['expression']
                        
                        sk_total_reversed += 1
        
        self.report({'INFO'}, f"已反转 {total_reversed} 条物体NLA轨道和 {sk_total_reversed} 条形态键NLA轨道")
        return {'FINISHED'}


# --- 3. UI 面板 (Panel) --- (修改draw方法)

class NLA_PT_PlayerPanel(Panel):
    bl_label = "NLA 播放器"
    bl_idname = "NLA_PT_PlayerPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "NLA Player"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        nla_tracks_collection = scene.nla_player_tracks

        # ★ 优化布局：将功能按钮放在一行
        row = layout.row(align=True)
        row.operator(NLA_OT_ClearActiveActions.bl_idname, text="清理", icon='ACTION_TWEAK')
        row.operator(NLA_OT_EnableAllTracks.bl_idname, text="启用全部", icon='UNLOCKED')
        row.operator(NLA_OT_RefreshList.bl_idname, text="刷新", icon='FILE_REFRESH')
        
        # 添加反转轨道按钮
        row = layout.row(align=True)
        row.operator(NLA_OT_ReverseSelectedTracks.bl_idname, text="反转轨道", icon='ARROW_LEFTRIGHT')

        layout.separator()

        if not nla_tracks_collection:
            box = layout.box()
            box.label(text="请先刷新列表", icon='INFO')
        else:
            box = layout.box()
            row = box.row()
            row.label(text="动画轨道", icon='TRACKING_FORWARDS')
            row.label(text="帧范围")

            for track_item in nla_tracks_collection:
                row = box.row(align=True)

                icon = 'SHAPEKEY_DATA' if track_item.is_shape_key else 'OBJECT_DATAMODE'

                op = row.operator(NLA_OT_PlayTrack.bl_idname, text=track_item.name, icon=icon)
                op.track_name = track_item.name
                op.frame_start = track_item.frame_start
                op.frame_end = track_item.frame_end
                op.is_shape_key = track_item.is_shape_key

                range_text = f"{track_item.frame_start} - {track_item.frame_end}"
                row.label(text=range_text)


# --- 4. 注册与注销 --- (在classes元组中添加新类)

classes = (
    NLA_PG_TrackItem,
    NLA_OT_ClearActiveActions,
    NLA_OT_EnableAllTracks,
    NLA_OT_RefreshList,
    NLA_OT_PlayTrack,
    NLA_OT_ReverseSelectedTracks,  # ★ 添加新类
    NLA_PT_PlayerPanel,
)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError as e:
            print(f"Registration of {cls.__name__} failed: {e}")

    bpy.types.Scene.nla_player_tracks = CollectionProperty(type=NLA_PG_TrackItem)

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError as e:
            print(f"Unregistration of {cls.__name__} failed: {e}")
    
    if hasattr(bpy.types.Scene, 'nla_player_tracks'):
        del bpy.types.Scene.nla_player_tracks

if __name__ == "__main__":
    register()