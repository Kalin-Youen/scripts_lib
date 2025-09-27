# script_id: 04e2fc3f-985a-49da-b392-68c504d39d31
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
    【此函数核心混合逻辑完全保持原样，仅为新功能返回最终的形态键列表】
    """
    print("\n--- 阶段二: 开始形态键差分混合 ---")
    
    if not target_object.data.shape_keys:
        print(f"错误：'{target_object.name}' 上没有找到形态键数据。")
        return False, None

    skeys = target_object.data.shape_keys.key_blocks
    
    transferred_keys = sorted(
        [sk for sk in skeys if sk.name.endswith('.Transferred')],
        key=lambda sk: sk.name
    )

    if not transferred_keys:
        print("没有找到以 '.Transferred' 结尾的形态键进行处理。")
        return False, None
        
    print(f"找到待处理的形态键: {[sk.name for sk in transferred_keys]}")

    print("\n--- 准备混合: 设置 slider_min = -1 ---")
    for sk in transferred_keys:
        sk.slider_min = -1

    for sk in skeys:
        sk.value = 0

    first_key = transferred_keys[0]
    new_name_first = first_key.name.replace('.Transferred', '')
    first_key.name = new_name_first

    for i in range(1, len(transferred_keys)):
        previous_key_name = transferred_keys[i-1].name.replace('.Transferred', '')
        previous_key = skeys[previous_key_name]
        current_key = transferred_keys[i]
        
        previous_key.value = -1
        current_key.value = 1
        
        bpy.ops.object.shape_key_add(from_mix=True)
        new_mixed_key = skeys[-1]
        new_name = current_key.name.replace('.Transferred', '')
        new_mixed_key.name = new_name
        
        previous_key.value = 0
        current_key.value = 0
        
    print("\n--- 开始清理原始的 .Transferred 形态键 ---")
    keys_to_remove_names = [sk.name for sk in skeys if sk.name.endswith('.Transferred')]
    for key_name in keys_to_remove_names:
        target_object.shape_key_remove(key=skeys[key_name])

    print("\n--- 设置最终形态键状态 ---")
    final_keys = sorted(
        [sk for sk in skeys if sk.name != 'Basis' and not sk.name.endswith('.Transferred')],
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
    """
    print("\n--- 新功能: 开始创建形态键动画 ---")

    if not final_keys or len(frame_numbers) != len(final_keys) + 1:
        print("动画创建失败：形态键数量与帧数不匹配。")
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
        print(message)
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
    # 调用您的原始混合函数，并接收返回值
    success, _ = process_differential_blending(target_object)
    
    if success:
        print("-" * 40)
        print("多物体处理流程已成功完成！")
        bpy.ops.wm.show_message_box('INVOKE_DEFAULT', message="多物体处理流程已成功完成！")

# ================================================================
# 模式二: 单物体动画提取工作流 (通过操作符实现弹窗) - 【此部分逻辑完全未作任何修改】
# ================================================================
class WM_OT_ShapeKeyFromFrames(bpy.types.Operator):
    """从单个动画物体的指定帧创建差分形态键"""
    bl_idname = "wm.shape_key_from_frames_popup"
    bl_label = "从帧创建形态键"
    bl_options = {'REGISTER', 'UNDO'}

    frame_string: bpy.props.StringProperty(
        name="帧",
        description="输入用'-'分隔的帧号, 例如: 1-15-30",
        default="1-10-20"
    )

    keyframe_animation: bpy.props.BoolProperty(
        name="创建动画关键帧",
        description="在指定的帧上为生成的形态键K帧，实现连续变化",
        default=True
    )

    def execute(self, context):
        base_object = context.active_object
        original_frame = context.scene.frame_current

        try:
            frame_numbers = sorted([int(f.strip()) for f in self.frame_string.split('-') if f.strip()])
            if len(frame_numbers) < 2:
                self.report({'ERROR'}, "请输入至少两个有效的帧号。")
                return {'CANCELLED'}
        except ValueError:
            self.report({'ERROR'}, "输入无效，请确保只包含数字和'-'。")
            return {'CANCELLED'}

        snapshot_objects = []
        initial_transform_matrix = None
        print("--- 开始创建网格快照 ---")
        for i, frame in enumerate(frame_numbers):
            print(f"正在快照第 {frame} 帧...")
            context.scene.frame_set(frame)
            
            depsgraph = context.evaluated_depsgraph_get()
            eval_obj = base_object.evaluated_get(depsgraph)
            
            if i == 0:
                initial_transform_matrix = eval_obj.matrix_world.copy()

            mesh = bpy.data.meshes.new_from_object(eval_obj, depsgraph=depsgraph)
            
            snapshot_name = f"{frame:04d}_{base_object.name}"
            snapshot_obj = bpy.data.objects.new(snapshot_name, mesh)
            context.collection.objects.link(snapshot_obj)
            snapshot_objects.append(snapshot_obj)

        target_snapshot = snapshot_objects[0]
        source_snapshots = snapshot_objects[1:]

        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        target_snapshot.select_set(True)
        context.view_layer.objects.active = target_snapshot
        
        transfer_shapes_from_objects(target_snapshot, source_snapshots)
        success, final_keys = process_differential_blending(target_snapshot)
        
        print("\n--- 清理临时快照物体 ---")
        for obj in source_snapshots:
            bpy.data.meshes.remove(obj.data)
            
        if success:
            final_name = f"{base_object.name}_SK"
            target_snapshot.name = final_name
            print(f"最终物体已命名为: '{final_name}'")

            if initial_transform_matrix:
                print("--- 新功能: 同步原始物体变换 ---")
                target_snapshot.matrix_world = initial_transform_matrix
            
            if self.keyframe_animation:
                create_sequential_shape_key_animation(target_snapshot, final_keys, frame_numbers)
            
            self.report({'INFO'}, "单物体处理流程已成功完成！")
        else:
            self.report({'ERROR'}, "处理失败，请检查控制台信息。")

        context.scene.frame_set(original_frame)
        print("-" * 40)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

# ================================================================
# 主程序入口: 智能分发器 - 【修正了错误的弹窗调用】
# ================================================================
def main():
    """【仅修正了错误的弹窗调用，其他逻辑保持原样】"""
    if "MeshDataTransfer" not in bpy.context.preferences.addons:
        message = "错误：'Mesh Data Transfer' 插件未启用。"
        print(message)
        # 使用我们新定义的、正确的弹窗操作符
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
        print(message)
        # 使用我们新定义的、正确的弹窗操作符
        bpy.ops.wm.show_message_box('INVOKE_DEFAULT', message=message)

# ================================================================
# 插件注册/注销部分
# ================================================================
classes = (
    MESSAGE_OT_ShowMessageBox, # <-- 注册新的弹窗操作符
    WM_OT_ShapeKeyFromFrames,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    # 确保在运行前先注册所有需要的类
    register()
    main()
