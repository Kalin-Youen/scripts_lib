import bpy
import requests
import os
import json

# 从剪切板读取JSON字符串
json_str = bpy.context.window_manager.clipboard

# 将JSON字符串解析为Python字典
data = json.loads(json_str)

# 提取图像和OBJ文件的URL
output_img_url = data['data']['output_img']
output_obj_url = data['data']['output_obj']

# 获取Blender文件所在目录
blender_file_path = bpy.data.filepath
blender_dir = os.path.dirname(blender_file_path)

# 下载图像文件
img_response = requests.get(output_img_url)
img_file_path = os.path.join(blender_dir, 'output_image.png')
if img_response.status_code == 200:
    with open(img_file_path, 'wb') as img_file:
        img_file.write(img_response.content)
    print("Image downloaded successfully.")
else:
    print(f"Failed to download image. Status code: {img_response.status_code}")

# 下载OBJ文件
obj_response = requests.get(output_obj_url)
obj_file_path = os.path.join(blender_dir, 'output_model.obj')
if obj_response.status_code == 200:
    with open(obj_file_path, 'wb') as obj_file:
        obj_file.write(obj_response.content)
    print("OBJ file downloaded successfully.")
else:
    print(f"Failed to download OBJ file. Status code: {obj_response.status_code}")

# 导入OBJ文件到Blender场景
bpy.ops.import_scene.obj(filepath=obj_file_path)

# 获取导入的对象
imported_objects = bpy.context.selected_objects
if imported_objects:
    imported_obj = imported_objects[0]
    
    # 创建新的材质
    mat = bpy.data.materials.new(name="ImportedMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    
    # 创建图像纹理节点
    tex_image = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex_image.image = bpy.data.images.load(img_file_path)
    
    # 连接图像纹理节点到BSDF Shader
    mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])
    
    # 将材质赋予导入的对象
    if imported_obj.data.materials:
        # 如果已经有材质槽位，替换材质
        imported_obj.data.materials[0] = mat
    else:
        # 如果没有材质槽位，添加一个
        imported_obj.data.materials.append(mat)
    
    print("Material applied successfully.")
else:
    print("No object imported.")

print("Script completed.")
