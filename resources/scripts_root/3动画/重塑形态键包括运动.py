# -*- coding: utf-8 -*-
import bpy

# ================================================================
# 新增: 一个标准、可靠的弹窗操作符，用来替换错误的调用
# ================================================================
class MESSAGE_OT_ShowMessageBox(bpy.types.Operator):
    bl_idname = "wm.show_message_box"
    bl_label = "提示"
    bl_options = {'INTERNAL'}

    message: bpy.props.StringProperty(name="Message", default="这是一个提示")

    def execute(self, context):
        self.report({'INFO'}, self.message)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        # 将消息文本按行分割，实现自动换行显示
        lines = self.message.split('\n')
        for line in lines:
            layout.label(text=line)

# ================================================================
# 核心功能模块 (可重用) - 【此部分逻辑完全未作任何修改】
# ================================================================

def transfer_shapes_from_objects(target_object, source_objects):
    """
    一个可重用的函数，负责将源物体列表的形态传输到目标物体。
    【此函数完全保持原样】
    """
    print("--- 阶段一: 开始数据传输 ---")
    
    bpy.context.view_layer.objects.active = target_object
    
    for source_object in source_objects:
        print(f"正在传输: 从 '{source_object.name}' -> 到 '{target_object.name}'")
        props = target_object.mesh_data_transfer_object
        props.search_method = 'TOPOLOGY'
        props.attributes_to_transfer = 'SHAPE'
        props.transfer_shape_as_key = True
        props.mesh_source = source_object
        bpy.ops.object.transfer_mesh_data()
        
        new_key = target_object.data.shape_keys.key_blocks[-1]
        new_key.name = f"{source_object.name}.Transferred"
        
    print("数据传输完成！")


def process_differential_blending(target_object):
    """
    一个可重用的函数，负责对目标物体上的形态键进行差分混合和清理。
    【此函数完全保持原样】
    """
    print("\n--- 阶段二: 开始形态键差分混合 ---")
    
    if not target_object.data.shape_keys:
        return False, None

    skeys = target_object.data.shape_keys.key_blocks
    
    transferred_keys = sorted(
        [sk for sk in skeys if sk.name.endswith('.Transferred')],
        key=lambda sk: sk.name
    )

    if not transferred_keys:
        return False, None
        
    print(f"找到待处理的形态键: {[sk.name for sk in transferred_keys]}")

    for sk in transferred_keys:
        sk.slider_min = -1

    for sk in skeys:
        sk.value = 0

    first_key = transferred_keys[0]
    first_key.name = first_key.name.replace('.Transferred', '')

    for i in range(1, len(transferred_keys)):
        previous_key_name = transferred_keys[i-1].name
        previous_key = skeys[previous_key_name]
        current_key = transferred_keys[i]
        
        previous_key.value = -1
        current_key.value = 1
        
        bpy.ops.object.shape_key_add(from_mix=True)
        new_mixed_key = skeys[-1]
        new_mixed_key.name = current_key.name.replace('.Transferred', '')
        
        previous_key.value = 0
        current_key.value = 0
        
    keys_to_remove = [sk for sk in skeys if sk.name.endswith('.Transferred')]
    for key in keys_to_remove:
        target_object.shape_key_remove(key=key)

    final_keys = sorted(
        [sk for sk in skeys if sk.name != 'Basis'],
        key=lambda sk: sk.name
    )

    for sk in final_keys:
        sk.value = 0 
        sk.slider_min = 0 
    
    return True, final_keys

# ================================================================
# 新增功能模块: 动画创建 - 【此部分逻辑完全未作任何修改】
# ================================================================

def create_sequential_shape_key_animation(target_object, final_keys, frame_numbers):
    """
    为目标物体上的形态键，在指定的帧上创建连续的动画。
    【此函数完全保持原样】
    """
    print("\n--- 新功能: 开始创建形态键动画 ---")

    if not final_keys or len(frame_numbers) != len(final_keys) + 1:
        return

    if not target_object.data.shape_keys.animation_data:
        target_object.data.shape_keys.animation_data_create()

    start_frame = frame_numbers[0]
    for sk in final_keys:
        sk.value = 0
        sk.keyframe_insert(data_path='value', frame=start_frame)

    for i, sk in enumerate(final_keys):
        key_frame = frame_numbers[i + 1]
        sk.value = 1
        sk.keyframe_insert(data_path='value', frame=key_frame)
        
        if i + 1 < len(final_keys):
             next_sk = final_keys[i+1]
             next_sk.value = 0
             next_sk.keyframe_insert(data_path='value', frame=key_frame)

    print(f"已在帧 {frame_numbers} 上成功创建了动画。")


# ================================================================
# 模式一: 多物体批处理工作流 - 【此部分逻辑完全未作任何修改】
# ================================================================
def run_multi_object_pipeline():
    """【此函数完全保持原样】"""
    print("检测到多个物体，启动多物体批处理模式...")
    selected_objects = bpy.context.selected_objects
    numbered_objects = [obj for obj in selected_objects if obj.name[0].isdigit() and obj.type == 'MESH']
    
    if len(numbered_objects) < 2:
        message="错误：请至少选择两个以数字开头的网格物体。"
        bpy.ops.wm.show_message_box('INVOKE_DEFAULT', message=message)
        return

    sorted_objects = sorted(numbered_objects, key=lambda obj: obj.name)
    target_object = sorted_objects[0]
    source_objects = sorted_objects[1:]
    
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    target_object.select_set(True)
    bpy.context.view_layer.objects.active = target_object
    
    transfer_shapes_from_objects(target_object, source_objects)
    success, _ = process_differential_blending(target_object)
    
    if success:
        print("多物体处理流程已成功完成！")
        bpy.ops.wm.show_message_box('INVOKE_DEFAULT', message="多物体处理流程已成功完成！")

# ================================================================
# 模式二: 单物体动画提取工作流 - 【已按要求优化】
# ================================================================
class WM_OT_ShapeKeyFromFrames(bpy.types.Operator):
    """从单个动画物体的指定帧创建差分形态键"""
    bl_idname = "wm.shape_key_from_frames_popup"
    bl_label = "从帧创建形态键"
    bl_options = {'REGISTER', 'UNDO'}

    # --- 保留原有手动输入方式 ---
    frame_string: bpy.props.StringProperty(
        name="帧序列 (手动输入)",
        description="输入用'-'分隔的帧号, 例如: 1-15-30",
        default="1-10-20"
    )

    # --- 新增范围模式参数 ---
    use_range_mode: bpy.props.BoolProperty(
        name="启用范围模式",
        description="勾选后，使用起始帧/步长/结束帧自动生成帧序列",
        default=False
    )

    start_frame: bpy.props.IntProperty(
        name="起始帧",
        description="开始采样的帧号",
        default=1
    )

    step: bpy.props.IntProperty(
        name="步长",
        description="每隔多少帧采样一次",
        default=1,
        min=1
    )

    end_frame: bpy.props.IntProperty(
        name="结束帧",
        description="采样结束的帧号",
        default=100
    )

    keyframe_animation: bpy.props.BoolProperty(
        name="创建动画关键帧",
        description="在指定的帧上为生成的形态键K帧，实现连续变化",
        default=True
    )

    def __init__(self):
        # 初始化时动态设置默认值
        scene = bpy.context.scene
        self.start_frame = scene.frame_current
        self.end_frame = scene.frame_end

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "use_range_mode")

        if self.use_range_mode:
            box = layout.box()
            box.label(text="范围模式参数:")
            box.prop(self, "start_frame")
            box.prop(self, "step")
            box.prop(self, "end_frame")
            # 预览生成的帧序列
            try:
                frames = list(range(self.start_frame, self.end_frame + 1, self.step))
                if len(frames) < 2:
                    box.label(text="⚠️ 至少需要2帧", icon='ERROR')
                else:
                    preview_text = "预览: " + " - ".join(map(str, frames[:10])) + ("..." if len(frames) > 10 else "")
                    box.label(text=preview_text, icon='INFO')
            except:
                box.label(text="参数无效", icon='ERROR')
        else:
            layout.prop(self, "frame_string")
            layout.label(text="示例: 1-15-30-45", icon='INFO')

        layout.separator()
        layout.prop(self, "keyframe_animation")

    def execute(self, context):
        base_object = context.active_object
        original_frame = context.scene.frame_current
        original_active = context.view_layer.objects.active

        # --- 根据模式生成 frame_numbers ---
        if self.use_range_mode:
            if self.start_frame > self.end_frame:
                self.report({'ERROR'}, "起始帧不能大于结束帧！")
                return {'CANCELLED'}
            if self.step < 1:
                self.report({'ERROR'}, "步长必须 ≥ 1！")
                return {'CANCELLED'}
            frame_numbers = list(range(self.start_frame, self.end_frame + 1, self.step))
            if len(frame_numbers) < 2:
                self.report({'ERROR'}, "范围模式下至少需要生成2帧！")
                return {'CANCELLED'}
        else:
            try:
                frame_numbers = sorted([int(f.strip()) for f in self.frame_string.split('-') if f.strip()])
                if len(frame_numbers) < 2:
                    self.report({'ERROR'}, "请输入至少两个有效的帧号。")
                    return {'CANCELLED'}
            except ValueError:
                self.report({'ERROR'}, "输入无效，请确保只包含数字和'-'。")
                return {'CANCELLED'}

        snapshot_objects = []
        print("--- 开始创建并烘焙网格快照 ---")
        
        bpy.ops.object.select_all(action='DESELECT')
        
        # --- 核心优化发生在此循环内 ---
        for frame in frame_numbers:
            print(f"正在处理第 {frame} 帧...")
            context.scene.frame_set(frame)
            depsgraph = context.evaluated_depsgraph_get()
            eval_obj = base_object.evaluated_get(depsgraph)
            
            # 创建副本
            mesh = bpy.data.meshes.new_from_object(eval_obj, depsgraph=depsgraph)
            snapshot_name = f"{frame:04d}_{base_object.name}"
            snapshot_obj = bpy.data.objects.new(snapshot_name, mesh)
            context.collection.objects.link(snapshot_obj)
            
            # --- 【开始执行您的优化指令】 ---
            # 1. 将副本的变换设置为与当前帧的动画物体完全一致
            snapshot_obj.matrix_world = eval_obj.matrix_world.copy()
            
            # 2. 清除副本可能继承的任何动画数据
            if snapshot_obj.animation_data:
                snapshot_obj.animation_data_clear()
            
            # 3. 应用全部变换，将世界变换烘焙进顶点数据
            context.view_layer.objects.active = snapshot_obj
            snapshot_obj.select_set(True)
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True, properties=True)
            snapshot_obj.select_set(False)
            # --- 【优化指令执行完毕】 ---
            
            snapshot_objects.append(snapshot_obj)
        
        # 恢复操作前的激活对象状态
        context.view_layer.objects.active = original_active
        
        # --- 后续流程完全不变 ---
        target_snapshot = snapshot_objects[0]
        source_snapshots = snapshot_objects[1:]

        target_snapshot.select_set(True)
        context.view_layer.objects.active = target_snapshot
        
        transfer_shapes_from_objects(target_snapshot, source_snapshots)
        success, final_keys = process_differential_blending(target_snapshot)
        
        print("\n--- 清理临时的源快照物体 ---")
        for obj in source_snapshots:
            bpy.data.meshes.remove(obj.data)
            
        if success:
            final_name = f"{base_object.name}_SK"
            target_snapshot.name = final_name
            print(f"最终物体已命名为: '{final_name}'")
            print("注意：物体位于世界原点，其位移动画已烘焙到形态键中。")

            if self.keyframe_animation:
                create_sequential_shape_key_animation(target_snapshot, final_keys, frame_numbers)
            
            self.report({'INFO'}, "单物体处理流程已成功完成！")
        else:
            self.report({'ERROR'}, "处理失败，请检查控制台信息。")
            bpy.data.meshes.remove(target_snapshot.data)

        context.scene.frame_set(original_frame)
        print("-" * 40)
        return {'FINISHED'}

    def invoke(self, context, event):
        # 初始化默认值
        scene = context.scene
        self.start_frame = scene.frame_current
        self.end_frame = scene.frame_end
        return context.window_manager.invoke_props_dialog(self, width=400)

# ================================================================
# 主程序入口: 智能分分发器 - 【此部分逻辑完全未作任何修改】
# ================================================================
def main():
    """【此函数完全保持原样】"""
    if "MeshDataTransfer" not in bpy.context.preferences.addons:
        message = "错误：'Mesh Data Transfer' 插件未启用。"
        bpy.ops.wm.show_message_box('INVOKE_DEFAULT', message=message)
        return

    selected_count = len(bpy.context.selected_objects)

    if selected_count > 1:
        run_multi_object_pipeline()
    elif selected_count == 1:
        print("检测到单个物体，启动单物体动画提取模式...")
        bpy.ops.wm.shape_key_from_frames_popup('INVOKE_DEFAULT')
    else:
        message = "错误：请至少选择一个物体。"
        bpy.ops.wm.show_message_box('INVOKE_DEFAULT', message=message)

# ================================================================
# 插件注册/注销部分 - 【此部分逻辑完全未作任何修改】
# ================================================================
classes = (
    MESSAGE_OT_ShowMessageBox,
    WM_OT_ShapeKeyFromFrames,
)

def register():
    for cls in classes:
        # 添加检查防止重复注册
        if not hasattr(bpy.types, cls.__name__):
            bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        if hasattr(bpy.types, cls.__name__):
            bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
    main()