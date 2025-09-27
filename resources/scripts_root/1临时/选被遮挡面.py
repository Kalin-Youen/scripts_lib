# script_id: f1d946f1-6398-4ad8-8a9e-33ddbba24a54
# ===================================================================================
# ==                                                                               ==
# ==         高性能·预览选择版·可见面分析脚本 v4.1                             ==
# ==                                                                               ==
# ===================================================================================
#
# 新功能：不再直接删除！脚本会高亮【选中】所有被完全遮挡的面，并停留在
# 编辑模式下，让你亲自检查和决定是否删除。
#
# 使用方法:
# 1. 打开 Blender，切换到 "Scripting" 工作区。
# 2. 将此脚本的全部内容粘贴到文本编辑器中。
# 3. 在3D视图中，选择你想要处理的一个或多个物体。
# 4. 回到文本编辑器，点击右上角的 "▶" (运行脚本) 按钮。
# 5. 脚本运行完毕后，会自动切换到编辑模式，并选中所有被遮挡的面。
#
# 作者: 一个贴心听取用户需求的可爱AI
#
# ===================================================================================

import bpy
import bmesh
from mathutils import Vector
import math
import time

# ===================================================================================
# ==                           【可调参数】                                        ==
# ===================================================================================

# 射线密度：数值越高，越能精准捕捉到微小可见部分，但总时间越长。
LATITUDE_STEPS = 32
LONGITUDE_STEPS = 64
RAYS_PER_ITERATION = 500
SPHERE_SCALE = 2.0
TIMER_DELAY = 0.001


# ===================================================================================
# ==                 【异步处理器核心操作符】                                      ==
# ===================================================================================

class CUTE_OT_preview_visibility_processor(bpy.types.Operator):
    """
    高性能·预览选择版·可见面分析器
    """
    bl_idname = "object.cute_preview_visibility_processor"
    bl_label = "运行可见面分析 (预览选择)"
    bl_options = {'REGISTER'} # UNDO is handled by Blender's edit mode history

    timer: bpy.props.PointerProperty(type=bpy.types.Timer)
    
    objects_to_process: list
    total_objects: int
    current_object_index: int
    
    obj: object
    rays_iterator: object
    visible_face_indices: set
    processed_ray_count: int
    total_rays_for_current_object: int
    
    start_time: float

    def invoke(self, context, event):
        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
            
        self.objects_to_process = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not self.objects_to_process:
            self.report({'WARNING'}, "请先选择至少一个网格物体！")
            return {'CANCELLED'}

        self.total_objects = len(self.objects_to_process)
        self.current_object_index = -1
        self.obj = None
        
        self.start_time = time.time()
        print(f"--- 预览选择版分析开始！共 {self.total_objects} 个物体。---")

        self.timer = context.window_manager.event_timer_add(TIMER_DELAY, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            if not self.obj:
                if not self.next_object(context):
                    return self.finish(context)

            depsgraph = context.evaluated_depsgraph_get()
            
            for _ in range(RAYS_PER_ITERATION):
                try:
                    ray_origin, ray_direction = next(self.rays_iterator)
                except StopIteration:
                    self.finalize_object(context)
                    self.obj = None
                    break

                self.processed_ray_count += 1
                
                is_hit, _, _, face_index, hit_object, _ = context.scene.ray_cast(
                    depsgraph, origin=ray_origin, direction=ray_direction
                )

                if is_hit and hit_object == self.obj:
                    self.visible_face_indices.add(face_index)

            if self.obj and self.total_rays_for_current_object > 0:
                progress = (self.processed_ray_count / self.total_rays_for_current_object) * 100
                status_msg = (
                    f"处理中 ({self.current_object_index + 1}/{self.total_objects}): {self.obj.name} "
                    f"| 射线: {self.processed_ray_count}/{self.total_rays_for_current_object} ({progress:.1f}%)"
                )
                context.workspace.status_text_set(status_msg)

        return {'PASS_THROUGH'}

    def next_object(self, context):
        self.current_object_index += 1
        if self.current_object_index >= self.total_objects:
            return False
            
        self.obj = self.objects_to_process[self.current_object_index]
        print(f"\n[{self.current_object_index + 1}/{self.total_objects}] 开始分析: {self.obj.name}")
        
        if not self.obj.data or not hasattr(self.obj.data, 'polygons') or len(self.obj.data.polygons) == 0:
            print(f"    - 物体 {self.obj.name} 没有面，已跳过。")
            self.obj = None
            return True

        rays = []
        center = self.obj.matrix_world.translation
        radius = max(self.obj.dimensions) / 2 * SPHERE_SCALE if max(self.obj.dimensions) > 0 else SPHERE_SCALE
        
        for i in range(LATITUDE_STEPS):
            phi = math.pi * (i + 0.5) / LATITUDE_STEPS
            for j in range(LONGITUDE_STEPS):
                theta = 2 * math.pi * j / LONGITUDE_STEPS
                x, y, z = radius * math.sin(phi) * math.cos(theta), radius * math.sin(phi) * math.sin(theta), radius * math.cos(phi)
                ray_origin_local = Vector((x, y, z))
                rays.append((center + ray_origin_local, -ray_origin_local.normalized()))

        self.rays_iterator = iter(rays)
        self.visible_face_indices = set()
        self.processed_ray_count = 0
        self.total_rays_for_current_object = len(rays)
        print(f"    - 已为 {self.obj.name} 生成 {self.total_rays_for_current_object} 条射线进行照射。")
        
        return True

    def finalize_object(self, context):
        """核心修改点：从删除变为选择"""
        if not self.obj: return

        print(f"    - 照射完成！在 {self.obj.name} 上共找到 {len(self.visible_face_indices)} 个可见面。")

        context.view_layer.objects.active = self.obj
        # 确保进入编辑模式
        if self.obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        
        bm = bmesh.from_edit_mesh(self.obj.data)
        bm.faces.ensure_lookup_table()
        
        faces_to_select = [face for face in bm.faces if face.index not in self.visible_face_indices]
        
        # 先取消所有选择，保证一个干净的状态
        bpy.ops.mesh.select_all(action='DESELECT')

        if faces_to_select:
            print(f"    - 正在【选中】{len(faces_to_select)} 个完全被遮挡的面...")
            # 激活面选择模式，以便用户能看到选择
            bpy.context.tool_settings.mesh_select_mode = (False, False, True)

            # 选中所有目标面
            for face in faces_to_select:
                face.select = True
        else:
            print("    - 未找到任何被完全遮挡的面。")
        
        # 将bmesh的更改写回，并释放资源
        bmesh.update_edit_mesh(self.obj.data)
        bm.free()
        
        # 【重要】我们不再切换回对象模式，让用户留在编辑模式下检查

    def finish(self, context):
        context.window_manager.event_timer_remove(self.timer)
        end_time = time.time()
        
        final_msg = f"所有任务完成！已选中隐藏面。总耗时: {end_time - self.start_time:.2f} 秒。请检查！"
        print(f"\n--- {final_msg} ---")
        context.workspace.status_text_set(final_msg)
        
        # 脚本结束时，用户会停留在最后一个被处理的物体的编辑模式下
        return {'FINISHED'}

    def cancel(self, context):
        if self.timer:
            context.window_manager.event_timer_remove(self.timer)
        print("\n--- 操作被用户取消。---")
        context.workspace.status_text_set("操作已取消")
        # 如果取消时在编辑模式，切换回对象模式以清理状态
        if context.active_object and context.active_object.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')

# ===================================================================================
# ==                            【脚本启动入口】                                     ==
# ===================================================================================

def register():
    bpy.utils.register_class(CUTE_OT_preview_visibility_processor)

def unregister():
    bpy.utils.unregister_class(CUTE_OT_preview_visibility_processor)

if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register()
    
    bpy.ops.object.cute_preview_visibility_processor('INVOKE_DEFAULT')

