# script_id: 1f6b3ed9-5e09-4644-8537-d14ca915fce3
import bpy
import os
import numpy as np

def bake_alpha_to_image(base_image, alpha_multiplier, image_name):
    """
    将基础图像的Alpha通道与一个乘数相乘，并烘焙到一张新图像上。
    如果同名图像已存在，则直接复用。
    """
    existing_image = bpy.data.images.get(image_name)
    if existing_image:
        print(f"      复用现有图像: {image_name}")
        return existing_image

    print(f"      创建新图像: {image_name}")
    if not base_image:
        return None

    size_x, size_y = base_image.size
    baked_image = bpy.data.images.new(image_name, width=size_x, height=size_y, alpha=True)
    baked_image.alpha_mode = 'STRAIGHT'

    base_pixels = np.empty(size_x * size_y * 4, dtype=np.float32)
    base_image.pixels.foreach_get(base_pixels)

    pixels_rgba = base_pixels.reshape((-1, 4))
    pixels_rgba[:, 3] = np.clip(pixels_rgba[:, 3] * alpha_multiplier, 0.0, 1.0)
    baked_image.pixels.foreach_set(pixels_rgba.flatten())

    try:
        baked_image.pack()
    except RuntimeError as e:
        print(f"警告: 无法打包图像 {baked_image.name}: {e}")

    return baked_image


class OBJECT_OT_animated_alpha_fade(bpy.types.Operator):
    """
    为选中物体创建基于Alpha和缩放的逐帧渐隐/渐现动画。
    适用于GLB动画导出。
    """
    bl_idname = "object.animated_alpha_fade"
    bl_label = "GLB Alpha Fade Animation (Scale)"
    bl_options = {'REGISTER', 'UNDO'}

    fade_type: bpy.props.EnumProperty(
        name="Fade Type",
        description="选择动画类型",
        items=[('IN', 'Fade In', '从透明渐现'),
               ('OUT', 'Fade Out', '渐隐至透明'),
               ('BOTH', 'Fade In & Out', '先渐现后渐隐')],
        default='OUT'
    )
    steps: bpy.props.IntProperty(
        name="Steps",
        description="过渡的步数 (例如, 5步会创建5个不同透明度的物体)",
        default=5, min=2, max=100
    )
    interval: bpy.props.IntProperty(
        name="Frame Interval",
        description="每一步持续的帧数 (出现和消失的过渡会发生在此区间的首尾)",
        default=2, min=2 # 至少为2，以容纳一个出现和消失的过渡
    )
    start_frame: bpy.props.IntProperty(
        name="Start Frame",
        description="动画开始的帧",
        default=1
    )

    @classmethod
    def poll(cls, context):
        return context.selected_objects and context.mode == 'OBJECT'

    def invoke(self, context, event):
        self.start_frame = context.scene.frame_current
        return context.window_manager.invoke_props_dialog(self)

    def find_existing_collection(self, obj_name, steps):
        """按名称和步数查找现有集合。"""
        collection_name = f"{obj_name}_AlphaFade_{steps}steps"
        return bpy.data.collections.get(collection_name)

    def get_fade_objects_from_collection(self, collection, base_obj_name, steps):
        """从集合中按优化后的命名规则获取物体列表。"""
        if not collection: return []
        fade_objects = [None] * steps
        found_count = 0
        for i in range(steps):
            alpha_int = int(round((i / (steps - 1) if steps > 1 else 0.0) * 100))
            obj_name = f"{base_obj_name}_alpha_{alpha_int}"
            obj = collection.objects.get(obj_name)
            if obj:
                fade_objects[i] = obj
                found_count += 1
        
        if found_count == steps:
            return fade_objects
        else:
            print(f"    集合 '{collection.name}' 中的物体不完整或命名不匹配。将重新创建。")
            return []

    def execute(self, context):
        print("开始执行 Alpha Fade 动画生成...")
        original_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not original_objects:
            self.report({'WARNING'}, "没有选中任何网格物体。")
            return {'CANCELLED'}

        for obj in original_objects:
            print(f"  处理物体: {obj.name}")
            
            collection_name = f"{obj.name}_AlphaFade_{self.steps}steps"
            fade_collection = self.find_existing_collection(obj.name, self.steps)
            fade_objects = []

            if fade_collection:
                print(f"    发现现有集合: {fade_collection.name}, 尝试复用...")
                fade_objects = self.get_fade_objects_from_collection(fade_collection, obj.name, self.steps)

            if not fade_objects:
                if fade_collection:
                    for child_obj in list(fade_collection.objects): bpy.data.objects.remove(child_obj, do_unlink=True)
                    bpy.data.collections.remove(fade_collection)
                
                print(f"    创建新集合 '{collection_name}' 和物体...")
                fade_collection = bpy.data.collections.new(collection_name)
                context.scene.collection.children.link(fade_collection)
                
                for i in range(self.steps):
                    alpha_float = i / (self.steps - 1) if self.steps > 1 else 0.0
                    alpha_int = int(round(alpha_float * 100))
                    new_obj = obj.copy()
                    new_obj.data = obj.data.copy()
                    new_obj.animation_data_clear()
                    new_obj.name = f"{obj.name}_alpha_{alpha_int}"
                    new_obj.scale = (1, 1, 1) # 确保基础缩放是1
                    fade_collection.objects.link(new_obj)
                    fade_objects.append(new_obj)
            else:
                print(f"    成功复用 {len(fade_objects)} 个物体。")

            print(f"    处理材质Alpha...")
            for i, fade_obj in enumerate(fade_objects):
                alpha_float = i / (self.steps - 1) if self.steps > 1 else 0.0
                alpha_int = int(round(alpha_float * 100))
                
                if fade_obj.material_slots:
                    for slot in fade_obj.material_slots:
                        if not slot.material: continue
                        if slot.material.users > 1 or slot.material.library: slot.material = slot.material.copy()

                        mat = slot.material
                        mat.use_nodes = True
                        nodes = mat.node_tree.nodes
                        bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
                        if not bsdf: continue
                        
                        alpha_input = bsdf.inputs['Alpha']
                        mat.blend_method = 'BLEND'
                        
                        if not alpha_input.is_linked:
                            alpha_input.default_value = alpha_float
                        else:
                            from_node = alpha_input.links[0].from_node
                            if from_node.type == 'TEX_IMAGE' and from_node.image:
                                base_image = from_node.image
                                baked_image_name = f"{base_image.name}_alpha_{alpha_int}"
                                baked_image = bake_alpha_to_image(base_image, alpha_float, baked_image_name)
                                if baked_image and from_node.image.name != baked_image.name:
                                    from_node.image = baked_image
            
            print(f"    设置可见性动画 (通过缩放)...")
            for fade_obj in fade_objects:
                fade_obj.animation_data_clear()

            if self.fade_type == 'OUT':
                anim_order = list(reversed(fade_objects))
            elif self.fade_type == 'IN':
                anim_order = fade_objects
            else: # BOTH
                anim_order = fade_objects + list(reversed(fade_objects[:-1]))

            initial_hide_frame = self.start_frame - 1
            if initial_hide_frame >= context.scene.frame_start:
                for fade_obj in fade_objects:
                    fade_obj.scale = (0, 0, 0)
                    fade_obj.keyframe_insert('scale', frame=initial_hide_frame)

            current_frame = self.start_frame
            for fade_obj in anim_order:
                appear_frame = current_frame
                disappear_frame = current_frame + self.interval

                fade_obj.scale = (0, 0, 0)
                fade_obj.keyframe_insert(data_path="scale", frame=appear_frame - 1)
                
                fade_obj.scale = (1, 1, 1)
                fade_obj.keyframe_insert(data_path="scale", frame=appear_frame)
                
                fade_obj.keyframe_insert(data_path="scale", frame=disappear_frame - 1)

                fade_obj.scale = (0, 0, 0)
                fade_obj.keyframe_insert(data_path="scale", frame=disappear_frame)
                
                # --- 【【【核心修改】】】 将缩放关键帧的插值模式设置为'CONSTANT' ---
                # 这段代码会遍历刚刚为物体创建的动画数据，找到所有与'scale'相关的
                # 动画曲线（F-Curves），然后将曲线上所有关键帧的插值模式都设置为'CONSTANT'
                if fade_obj.animation_data and fade_obj.animation_data.action:
                    for fcurve in fade_obj.animation_data.action.fcurves:
                        if fcurve.data_path.startswith("scale"):
                            for kf_point in fcurve.keyframe_points:
                                kf_point.interpolation = 'CONSTANT'
                # --- 修改结束 ---

                current_frame += self.interval
            
            obj.hide_viewport = True
            obj.hide_render = True
            obj.select_set(False)

        self.report({'INFO'}, f"为 {len(original_objects)} 个物体生成了基于缩放的 Alpha Fade 动画。")
        print("Alpha Fade 动画生成/更新完成。")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(OBJECT_OT_animated_alpha_fade)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_animated_alpha_fade)

if __name__ == "__main__":
    try: unregister()
    except: pass
    register()
    bpy.ops.object.animated_alpha_fade('INVOKE_DEFAULT')
