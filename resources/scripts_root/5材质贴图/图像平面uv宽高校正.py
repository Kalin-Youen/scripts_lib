import bpy
import bmesh
import re
import numpy as np

def parse_k_to_pixels(k_string):
    """将 '2k', '4k' 等字符串解析为像素值"""
    k_string = k_string.lower().strip()
    match = re.match(r"(\d*\.?\d+)\s*k", k_string)
    if match:
        try:
            k_value = float(match.group(1))
            return int(k_value * 1024)
        except (ValueError, IndexError):
            return None
    try:
        return int(k_string)
    except ValueError:
        return None

def find_base_color_image_node(material):
    """智能查找连接到 Principled BSDF 的 Base Color 输入的图像纹理节点"""
    if not material or not material.use_nodes: return None
    output_node = next((n for n in material.node_tree.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output), None)
    if not output_node: return None
    surface_input = output_node.inputs.get('Surface')
    if not surface_input or not surface_input.is_linked: return None
    shader_node = surface_input.links[0].from_node
    base_color_input = shader_node.inputs.get('Base Color')
    if not base_color_input: return None
    def trace_back(socket):
        if not socket.is_linked: return None
        from_node = socket.links[0].from_node
        if from_node.type == 'TEX_IMAGE' and from_node.image: return from_node
        for input_socket in from_node.inputs:
            if input_socket.type in ('RGBA', 'VECTOR'):
                result = trace_back(input_socket)
                if result: return result
        return None
    return trace_back(base_color_input)

class IMAGE_OT_smart_fill_to_square(bpy.types.Operator):
    bl_idname = "image.smart_fill_to_square"
    bl_label = "Smart Fill to Square & Fix UVs"
    bl_description = "Finds Base Color texture, scales/fills it to a square, then fixes UVs"
    bl_options = {'REGISTER', 'UNDO'}

    target_size_k: bpy.props.StringProperty(
        name="Target Size",
        description="Enter the target square size (e.g., '2k', '4096')",
        default="2k"
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        target_size = parse_k_to_pixels(self.target_size_k)
        if not target_size or target_size <= 0:
            self.report({'ERROR'}, "无效尺寸. 请输入 '2k' 或 '2048' 等。")
            return {'CANCELLED'}

        obj = context.active_object
        if not obj or not obj.active_material:
            self.report({'ERROR'}, "活动物体没有材质。")
            return {'CANCELLED'}

        image_texture_node = find_base_color_image_node(obj.active_material)
        if not image_texture_node:
            self.report({'ERROR'}, "未能在材质中找到连接到'Base Color'的图像纹理。")
            return {'CANCELLED'}
        source_image = image_texture_node.image

        W, H = source_image.size
        if W == 0 or H == 0:
            self.report({'ERROR'}, "源图像尺寸为零。")
            return {'CANCELLED'}

        # --- 【【【 核心修正：使用 Image API + Numpy，放弃渲染 】】】 ---
        
        # 1. 计算缩放后的尺寸
        aspect = W / H
        if W >= H:
            scaled_w, scaled_h = target_size, int(target_size / aspect)
        else:
            scaled_w, scaled_h = int(target_size * aspect), target_size

        # 2. 复制并缩放图像 (在内存中操作，非常快)
        scaled_copy = source_image.copy()
        scaled_copy.scale(scaled_w, scaled_h)
        
        # 3. 创建最终的正方形画布
        new_image_name = f"{source_image.name}_scaled_{target_size}"
        new_image = bpy.data.images.new(name=new_image_name, width=target_size, height=target_size, alpha=True)
        
        # 4. 使用 Numpy 将缩放后的图像像素粘贴到画布中心
        new_pixels_np = np.zeros((target_size * target_size, 4), dtype=np.float32)
        scaled_pixels_np = np.array(scaled_copy.pixels)
        
        x_offset = (target_size - scaled_w) // 2
        y_offset = (target_size - scaled_h) // 2

        # 创建一个2D的索引网格
        y, x = np.mgrid[y_offset:y_offset + scaled_h, x_offset:x_offset + scaled_w]
        # 将2D索引转换为1D索引
        flat_indices = y * target_size + x
        # 直接赋值
        new_pixels_np[flat_indices.ravel()] = scaled_pixels_np.reshape(scaled_h * scaled_w, 4)
        
        new_image.pixels = new_pixels_np.ravel()
        new_image.pack()
        
        # 5. 清理内存中的副本
        bpy.data.images.remove(scaled_copy)

        # 6. 替换材质节点中的图像
        image_texture_node.image = new_image

        # 7. UV重映射 (逻辑不变)
        u_start = x_offset / target_size
        v_start = y_offset / target_size
        u_range = scaled_w / target_size
        v_range = scaled_h / target_size
        
        is_edit_mode = (obj.mode == 'EDIT')
        if not is_edit_mode: bpy.ops.object.mode_set(mode='EDIT')
            
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        uv_layer = bm.loops.layers.uv.verify()

        for face in bm.faces:
            for loop in face.loops:
                uv_coord = loop[uv_layer]
                uv_coord.uv.x = u_start + uv_coord.uv.x * u_range
                uv_coord.uv.y = v_start + uv_coord.uv.y * v_range

        bmesh.update_edit_mesh(mesh)
        
        if not is_edit_mode: bpy.ops.object.mode_set(mode='OBJECT')

        self.report({'INFO'}, f"成功！图像已适配并填充到 {target_size}px 画布。")
        return {'FINISHED'}


if __name__ == '__main__':
    try:
        bpy.utils.unregister_class(IMAGE_OT_smart_fill_to_square)
    except RuntimeError:
        pass
    bpy.utils.register_class(IMAGE_OT_smart_fill_to_square)

    active_obj = bpy.context.active_object
    if active_obj and active_obj.type == 'MESH':
        area = next((a for a in bpy.context.screen.areas if a.type == 'VIEW_3D'), None)
        if area:
            with bpy.context.temp_override(area=area):
                bpy.ops.image.smart_fill_to_square('INVOKE_DEFAULT')
