import bpy

# =============================================================================
#  核心更新函数 (Core Update Function)
# =============================================================================

def update_clip_marker(self, context):
    """
    智能更新时间轴标记，与UI中的片段数据保持同步。
    这是插件的核心逻辑，用于防止“幽灵标记”的出现。
    """
    if not hasattr(self, "name") or not context or not context.scene:
        return

    scene = context.scene
    markers = scene.timeline_markers

    old_name = self.marker_name_cache
    new_name = self.name.strip()

    if not new_name:
        if old_name:
            start_marker = markers.get(f"{old_name}s")
            end_marker = markers.get(f"{old_name}e")
            if start_marker: markers.remove(start_marker)
            if end_marker: markers.remove(end_marker)
        self.marker_name_cache = ""
        return

    start_marker = markers.get(f"{old_name}s") if old_name else None
    end_marker = markers.get(f"{old_name}e") if old_name else None

    if start_marker and end_marker:
        start_marker.name = f"{new_name}s"
        end_marker.name = f"{new_name}e"
        start_marker.frame = self.start
        end_marker.frame = self.end
    else:
        to_remove = [m for m in markers if m.name in [f"{new_name}s", f"{new_name}e"]]
        for marker in to_remove:
            markers.remove(marker)
        markers.new(name=f"{new_name}s", frame=self.start)
        markers.new(name=f"{new_name}e", frame=self.end)

    self.marker_name_cache = new_name


# =============================================================================
#  数据结构 (Data Structures)
# =============================================================================

class NLAClipItem(bpy.types.PropertyGroup):
    """代表一个动画片段，包含名称、起止帧以及与时间轴标记的链接"""
    name: bpy.props.StringProperty(name="名称", default="片段", update=update_clip_marker)
    start: bpy.props.IntProperty(name="起始帧", default=1, min=0, update=update_clip_marker)
    end: bpy.props.IntProperty(name="结束帧", default=50, min=0, update=update_clip_marker)
    marker_name_cache: bpy.props.StringProperty(options={'HIDDEN'})


class FrameRangePresetItem(bpy.types.PropertyGroup):
    """代表一个帧范围预设"""
    name: bpy.props.StringProperty(name="预设名称", default="预设")
    start: bpy.props.IntProperty(name="起始帧", default=1)
    end: bpy.props.IntProperty(name="结束帧", default=250)


class SmartNLASlicerData(bpy.types.PropertyGroup):
    """插件的主要数据容器，存储所有UI状态和列表"""
    clip_items: bpy.props.CollectionProperty(type=NLAClipItem)
    active_index: bpy.props.IntProperty()
    mode: bpy.props.EnumProperty(
        name="模式",
        items=[
            ('EDIT_MARKERS', "编辑标记", "仅在时间轴上创建和编辑起止标记"),
            ('GENERATE_NLA', "生成NLA", "根据标记将动画数据切分为NLA轨道"),
            ('MANAGE_FRAME_RANGE', "帧范围预设", "管理和应用常用的场景帧范围"),
        ],
        default='EDIT_MARKERS'
    )

    def initialize_from_markers(self):
        """从场景时间轴的标记初始化片段列表，并按起始帧排序。"""
        scene = bpy.context.scene
        markers = scene.timeline_markers
        frame_start = scene.frame_start
        frame_end = scene.frame_end

        clip_dict = {}
        for marker in markers:
            if not (frame_start <= marker.frame <= frame_end):
                continue
            name = marker.name.strip()
            if len(name) > 1:
                clip_name = name[:-1]
                if name.endswith("s"):
                    clip_dict.setdefault(clip_name, {})['start'] = marker.frame
                elif name.endswith("e"):
                    clip_dict.setdefault(clip_name, {})['end'] = marker.frame

        clips_to_sort = []
        for name, frames in clip_dict.items():
            if 'start' in frames and 'end' in frames:
                clips_to_sort.append({
                    'name': name,
                    'start': frames['start'],
                    'end': frames['end']
                })
        
        sorted_clips = sorted(clips_to_sort, key=lambda c: c['start'])

        self.clip_items.clear()
        for clip_data in sorted_clips:
            item = self.clip_items.add()
            item.name = clip_data['name']
            item.start = clip_data['start']
            item.end = clip_data['end']
            item.marker_name_cache = clip_data['name']


# =============================================================================
#  操作符 (Operators)
# =============================================================================

class SmartNLASlicerAddClipOperator(bpy.types.Operator):
    bl_idname = "object.smart_nla_slicer_add_clip"
    bl_label = "添加片段"

    def execute(self, context):
        data = context.window_manager.smart_nla_slicer_data
        item = data.clip_items.add()
        item.name = f"新片段.{len(data.clip_items)}"
        item.start = context.scene.frame_current
        item.end = context.scene.frame_current + 49
        update_clip_marker(item, context)
        data.active_index = len(data.clip_items) - 1
        return {'FINISHED'}


class SmartNLASlicerRemoveClipOperator(bpy.types.Operator):
    bl_idname = "object.smart_nla_slicer_remove_clip"
    bl_label = "删除片段"
    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        # ✅ 最终修复：检查 data.active_index (列表的当前选中项)
        data = context.window_manager.smart_nla_slicer_data
        return data.clip_items and 0 <= data.active_index < len(data.clip_items)

    def execute(self, context):
        data = context.window_manager.smart_nla_slicer_data
        if not (0 <= self.index < len(data.clip_items)):
            return {'CANCELLED'}
        clip_to_remove = data.clip_items[self.index]
        name_to_delete = clip_to_remove.marker_name_cache or clip_to_remove.name
        if name_to_delete:
            markers = context.scene.timeline_markers
            start_marker = markers.get(f"{name_to_delete}s")
            end_marker = markers.get(f"{name_to_delete}e")
            if start_marker: markers.remove(start_marker)
            if end_marker: markers.remove(end_marker)
        data.clip_items.remove(self.index)
        if data.active_index >= len(data.clip_items):
            data.active_index = len(data.clip_items) - 1
        return {'FINISHED'}


class SaveFrameRangePresetOperator(bpy.types.Operator):
    bl_idname = "scene.save_frame_range_preset"
    bl_label = "保存当前帧范围为预设"
    preset_name: bpy.props.StringProperty(name="预设名称", default="新预设")

    def execute(self, context):
        scene = context.scene
        preset = scene.frame_range_presets.add()
        preset.name = self.preset_name or "未命名预设"
        preset.start = scene.frame_start
        preset.end = scene.frame_end
        self.report({'INFO'}, f"已保存预设“{preset.name}”")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class ApplyFrameRangePresetOperator(bpy.types.Operator):
    bl_idname = "scene.apply_frame_range_preset"
    bl_label = "应用帧范围预设"
    index: bpy.props.IntProperty()
    
    @classmethod
    def poll(cls, context):
        # ✅ 最终修复：检查 scene.active_frame_preset_index
        scene = context.scene
        return scene.frame_range_presets and 0 <= scene.active_frame_preset_index < len(scene.frame_range_presets)

    def execute(self, context):
        scene = context.scene
        if not (0 <= self.index < len(scene.frame_range_presets)):
            return {'CANCELLED'}
        preset = scene.frame_range_presets[self.index]
        scene.frame_start = preset.start
        scene.frame_end = preset.end
        self.report({'INFO'}, f"已应用预设“{preset.name}”")
        context.window_manager.smart_nla_slicer_data.initialize_from_markers()
        return {'FINISHED'}


class RemoveFrameRangePresetOperator(bpy.types.Operator):
    bl_idname = "scene.remove_frame_range_preset"
    bl_label = "删除帧范围预设"
    index: bpy.props.IntProperty()
    
    @classmethod
    def poll(cls, context):
        # ✅ 最终修复：检查 scene.active_frame_preset_index
        scene = context.scene
        return scene.frame_range_presets and 0 <= scene.active_frame_preset_index < len(scene.frame_range_presets)

    def execute(self, context):
        scene = context.scene
        if not (0 <= self.index < len(scene.frame_range_presets)):
            return {'CANCELLED'}
        scene.frame_range_presets.remove(self.index)
        if scene.active_frame_preset_index >= len(scene.frame_range_presets):
            scene.active_frame_preset_index = max(0, len(scene.frame_range_presets) - 1)
        return {'FINISHED'}


class SmartNLASlicerOperator(bpy.types.Operator):
    bl_idname = "object.smart_nla_slicer"
    bl_label = "智能NLA切片器"
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        layout = self.layout
        data = context.window_manager.smart_nla_slicer_data
        scene = context.scene

        layout.prop(data, "mode", expand=True)
        layout.separator()

        if data.mode == 'MANAGE_FRAME_RANGE':
            layout.label(text="帧范围预设管理")
            row = layout.row()
            row.template_list(
                "UI_UL_list", "frame_preset_list",
                scene, "frame_range_presets",
                scene, "active_frame_preset_index",
                rows=5
            )
            col = row.column(align=True)
            col.operator(SaveFrameRangePresetOperator.bl_idname, icon='ADD', text="")
            op = col.operator(RemoveFrameRangePresetOperator.bl_idname, icon='REMOVE', text="")
            op.index = scene.active_frame_preset_index

            if scene.frame_range_presets and 0 <= scene.active_frame_preset_index < len(scene.frame_range_presets):
                preset = scene.frame_range_presets[scene.active_frame_preset_index]
                box = layout.box()
                box.label(text="编辑选中预设:")
                box.prop(preset, "name", text="名称")
                row = box.row(align=True)
                row.prop(preset, "start", text="起始帧")
                row.prop(preset, "end", text="结束帧")
                op = box.operator(ApplyFrameRangePresetOperator.bl_idname, text="应用到场景")
                op.index = scene.active_frame_preset_index
            
            layout.separator()
            box = layout.box()
            box.label(text="当前场景帧范围:")
            row = box.row(align=True)
            row.prop(scene, "frame_start", text="起始")
            row.prop(scene, "frame_end", text="结束")

        else: # EDIT_MARKERS or GENERATE_NLA mode
            box = layout.box()
            box.label(text=f"当前活动帧范围: {scene.frame_start} - {scene.frame_end}", icon='PREVIEW_RANGE')
            layout.label(text="动画片段列表")
            row = layout.row()
            row.template_list(
                "UI_UL_list", "clip_list",
                data, "clip_items",
                data, "active_index",
                rows=5
            )
            col = row.column(align=True)
            col.operator(SmartNLASlicerAddClipOperator.bl_idname, icon='ADD', text="")
            op = col.operator(SmartNLASlicerRemoveClipOperator.bl_idname, icon='REMOVE', text="")
            op.index = data.active_index

            if data.clip_items and 0 <= data.active_index < len(data.clip_items):
                item = data.clip_items[data.active_index]
                box = layout.box()
                box.label(text="编辑选中片段:")
                box.prop(item, "name", text="名称")
                row = box.row(align=True)
                row.prop(item, "start", text="起始帧")
                row.prop(item, "end", text="结束帧")

    def invoke(self, context, event):
        data = context.window_manager.smart_nla_slicer_data
        data.initialize_from_markers()
        return context.window_manager.invoke_props_dialog(self, width=600)

    def execute(self, context):
        data = context.window_manager.smart_nla_slicer_data
        if data.mode == 'EDIT_MARKERS':
            self.report({'INFO'}, "标记编辑完成。")
            return {'FINISHED'}
        
        if not data.clip_items:
            self.report({'ERROR'}, "未定义任何动画片段。")
            return {'CANCELLED'}

        sel_objs = context.selected_objects
        if not sel_objs:
            self.report({'ERROR'}, "请先选中物体。")
            return {'CANCELLED'}

        scene = context.scene
        frame_start = scene.frame_start
        frame_end = scene.frame_end

        clip_definitions = {}
        for item in data.clip_items:
            if not (item.start > frame_end or item.end < frame_start):
                clip_definitions[item.name] = (item.start, item.end)

        if not clip_definitions:
            self.report({'WARNING'}, "当前帧范围内无有效动画片段")
            return {'CANCELLED'}

        total_processed = 0
        for obj in sel_objs:
            processed = False
            if obj.animation_data:
                processed |= self.process_nla_for_animation_data(obj.animation_data, clip_definitions)
            if obj.type == 'MESH' and obj.data.shape_keys and obj.data.shape_keys.animation_data:
                processed |= self.process_nla_for_animation_data(obj.data.shape_keys.animation_data, clip_definitions)
            if processed:
                total_processed += 1

        self.report({'INFO'}, f"成功为 {total_processed} 个物体生成 NLA 轨道")
        return {'FINISHED'}

    def process_nla_for_animation_data(self, anim_data, clip_definitions):
        if not anim_data or not anim_data.action: return False
        source_action = anim_data.action
        while anim_data.nla_tracks:
            anim_data.nla_tracks.remove(anim_data.nla_tracks[0])
        for name, (start, end) in sorted(clip_definitions.items(), key=lambda x: x[1][0]):
            track = anim_data.nla_tracks.new()
            track.name = name
            strip = track.strips.new(name=name, start=start, action=source_action)
            strip.action_frame_start = start
            strip.action_frame_end = end
            strip.frame_end = start + (end - start)
            strip.extrapolation = 'NOTHING'
        anim_data.action = None
        return True


# =============================================================================
#  注册与注销 (Registration)
# =============================================================================

classes = (
    NLAClipItem,
    FrameRangePresetItem,
    SmartNLASlicerData,
    SmartNLASlicerAddClipOperator,
    SmartNLASlicerRemoveClipOperator,
    SaveFrameRangePresetOperator,
    ApplyFrameRangePresetOperator,
    RemoveFrameRangePresetOperator,
    SmartNLASlicerOperator,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.smart_nla_slicer_data = bpy.props.PointerProperty(type=SmartNLASlicerData)
    bpy.types.Scene.frame_range_presets = bpy.props.CollectionProperty(type=FrameRangePresetItem)
    bpy.types.Scene.active_frame_preset_index = bpy.props.IntProperty()


def unregister():
    try:
        del bpy.types.WindowManager.smart_nla_slicer_data
        del bpy.types.Scene.frame_range_presets
        del bpy.types.Scene.active_frame_preset_index
    except (AttributeError, TypeError):
        pass
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass


# =============================================================================
#  测试入口
# =============================================================================

if __name__ == "__main__":
    try: unregister()
    except Exception: pass
    register()
    bpy.ops.object.smart_nla_slicer('INVOKE_DEFAULT')
