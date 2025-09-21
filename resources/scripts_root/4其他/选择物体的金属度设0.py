# 选择物体的金属度设0
# 选择物体的金属度设0
# 1材质 
import bpy

# 遍历所有选定的对象
for obj in bpy.context.selected_objects:
    # 检查对象是否具有材质
    if obj.data.materials:
        # 遍历对象的所有材质
        for mat in obj.data.materials:
            # 跳过没有分配材质的情况
            if mat is None:
                continue
            # 检查材质是否使用节点
            if mat.use_nodes:
                # 获取节点树和Principled BSDF节点
                nodes = mat.node_tree.nodes
                principled_bsdf_node = next((node for node in nodes if node.type == 'BSDF_PRINCIPLED'), None)
                # 如果找到Principled BSDF节点，则设置高光和金属度为0
                if principled_bsdf_node:
                    #principled_bsdf_node.inputs[12].default_value = 0
                    principled_bsdf_node.inputs['Metallic'].default_value = 0
                    #principled_bsdf_node.inputs[17].default_value = 0

# 更新场景，以便看到更改
bpy.context.view_layer.update()
