import bpy
import re
import os
from collections import defaultdict

# 贴图类型映射（未改动）
texture_type_map = {
    'Specular IOR Level': 'Specular',
    'Specular Tint': 'SpecularTint',
    'Base Color': 'BaseColor',
    'Metallic': 'Metallic',
    'Specular': 'Specular',
    'Roughness': 'Roughness',
    'Normal': 'Normal',
    'Alpha': 'Opacity',
    'Emission': 'Emission',
    'Height': 'Height',
    'Subsurface': 'Subsurface',
    'Subsurface Color': 'SubsurfaceColor',
    'Subsurface Radius': 'SubsurfaceRadius',
    'Sheen': 'Sheen',
    'Sheen Tint': 'SheenTint',
    'Clearcoat': 'Clearcoat',
    'Clearcoat Roughness': 'ClearcoatRoughness',
    'IOR': 'IOR',
    'Transmission': 'Transmission',
    'Anisotropic': 'Anisotropic',
    'Anisotropic Rotation': 'AnisotropicRotation'
}

def sanitize_name(name):
    """清理非法字符并统一命名格式"""
    return re.sub(r'[^\w-]', '_', name.split('.')[0]).rstrip('_')

def traverse_node_tree(node, visited=None):
    """递归遍历节点树收集所有贴图节点"""
    visited = visited or set()
    if node in visited:
        return []
    visited.add(node)
    
    textures = []
    if node.type == 'TEX_IMAGE':
        textures.append(node)
    for input_socket in node.inputs:
        if input_socket.is_linked:
            upstream_node = input_socket.links[0].from_node
            textures += traverse_node_tree(upstream_node, visited)
    return textures

def rename_and_relink_texture(tex_node, new_name, unpack_path):
    """重命名文件并重新链接到 Blender（支持覆盖现有文件和图像）"""
    image = tex_node.image
    if not image:  # 添加检查：如果没有图像，跳过
        print(f"Skipping: No image found for node {tex_node.name}")
        return
    
    old_path = bpy.path.abspath(image.filepath)
    ext = ".jpg"  # 强制保存为 JPEG 格式
    
    new_filename = f"{new_name}{ext}"
    new_path = os.path.join(unpack_path, new_filename)
    
    # 如果目标路径已存在，先删除它以允许覆盖
    if os.path.exists(new_path):
        os.remove(new_path)
        print(f"Existing file removed for overwrite: {new_path}")
    
    try:
        if os.path.exists(old_path):
            # 如果文件存在，则直接重命名
            os.rename(old_path, new_path)
        else:
            # 如果文件不存在，则保存为 JPEG 格式
            original_settings = image.file_format  # 保存原始文件格式以便恢复
            image.file_format = 'JPEG'            # 修改文件格式为 JPEG
            image.save(filepath=new_path, quality=80)  # 保存图像，quality=80 以平衡大小和质量
            image.file_format = original_settings  # 恢复原始文件格式
    except Exception as e:
        print(f"Failed to save or rename image: {e}")
        return  # 如果保存失败，跳过以避免后续错误
    
    # 更新图像路径
    image.filepath = new_path
    image.reload()  # 重新加载图像，确保链接更新
    
    # 处理名称冲突：如果现有图像名称已存在，且不是当前图像，则移除它
    existing_image = bpy.data.images.get(new_name)
    if existing_image and existing_image != image:  # 关键修复：检查是否是同一个图像
        bpy.data.images.remove(existing_image)
        print(f"Existing image removed for overwrite: {new_name}")
    
    # 设置新名称（现在安全了，不会修改已移除的对象）
    image.name = new_name
    tex_node.image = image
    tex_node.name = new_name
    print(f"Texture renamed and relinked (overwritten if existed): {new_name}")

def rename_textures():
    """统一重命名所有纹理文件和引用"""
    processed_mats = set()
    
    unpack_path = bpy.path.abspath("//textures/")
    os.makedirs(unpack_path, exist_ok=True)  # 确保目录存在
    
    for obj in bpy.context.selected_objects:
        for slot in obj.material_slots:
            mat = slot.material
            if not mat or mat.name in processed_mats:
                continue
                
            processed_mats.add(mat.name)
            principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if not principled:
                continue
            
            base_name = sanitize_name(mat.name)
            
            for inp in principled.inputs:
                if not inp.is_linked:
                    continue
                
                start_node = inp.links[0].from_node
                texture_nodes = traverse_node_tree(start_node)
                
                tex_type = texture_type_map.get(inp.name, 'Other')
                
                for tex_node in texture_nodes:
                    if not tex_node.image:
                        continue
                    
                    new_name = f"{base_name}_{tex_type}"  # 固定名称，无后缀
                    
                    # 调用重命名和重新链接函数（支持覆盖）
                    rename_and_relink_texture(tex_node, new_name, unpack_path)

rename_textures()
