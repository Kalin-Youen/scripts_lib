# 一键设置选择物体的normal强度为0.025
# 一键设置选择物体的normal强度为0.025
# 3节点
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
                    # principled_bsdf_node.inputs[12].default_value = 0
                    # principled_bsdf_node.inputs['Metallic'].default_value = 0
                    # principled_bsdf_node.inputs[17].default_value = 0
                    print(123123)
                    try:
                        # normal_map_node = principled_bsdf_node.inputs['Normal'].links[0].from_node
                        normal_map_node = principled_bsdf_node.inputs['Normal'].links[0].from_node
                        # 如果存在
                        
                    
                        # 获取normal map节点的normal strength设置0.025
                        normal_map_node.inputs['Strength'].default_value = 0.025
                    except:
                        pass
                        

# 更新场景，以便看到更改
bpy.context.view_layer.update()
