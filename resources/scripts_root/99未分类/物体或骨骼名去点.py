# script_id: 82dd4fb0-d5ca-4bb6-8922-dd5f99f78511
import bpy

# 获取所有选中的物体
selected_objects = bpy.context.selected_objects

# 遍历选中的物体
for obj in selected_objects:
    # 获取物体所有的材质
    materials = obj.materials
    
    # 遍历物体的所有材质
    for mat in materials:
        # 获取材质的原理化节点
        principled_bsdf = mat.node_tree.nodes["Principled BSDF"]
        
        # 获取基本色贴图节点
        base_color_tex = principled_bsdf.inputs['Base Color'].links[0].from_node
        
        # 检查是否是指定的贴图节点
        if base_color_tex.name.find('.') != -1:
            # 替换贴图名称中的点为空字符
            new_name = base_color_tex.name.replace('.', '')
            base_color_tex.name = new_name
            print(f"修改了材质 '{mat.name}' 的基本色贴图名称从 '{base_color_tex.name}' 到 '{new_name}'")

# 执行脚本后，Blender不会自动刷新视图，需要手动刷新或者重新渲染视图以查看更改
bpy.context.view_layer.update()
