# 设置所有normal贴图的色彩空间
# 设置所有normal贴图的色彩空间
# 3节点
import bpy

def main():
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
                        # 找到normal map节点
                        normal_map_node = next((node for node in nodes if node.type == 'NORMAL_MAP'), None)
                        # 如果找到normal map节点，则设置strength为0
                        if normal_map_node:
                            # 找到normal map节点input的贴图节点 颜色接口
                            normal_map_node_input = normal_map_node.inputs[1]
                            # 另一端的图片节点
                            # 如果是图片节点，则设置色彩空间为非彩色'Non-Color'
                            if normal_map_node_input.links and normal_map_node_input.links[0].from_node.type == 'TEX_IMAGE':
                                normal_map_node_input_image = normal_map_node_input.links[0].from_node.image
                                # 设置色彩空间为非彩色'Non-Color'
                                normal_map_node_input_image.colorspace_settings.name = "Non-Color"

    # 更新场景，以便看到更改
    bpy.context.view_layer.update()

# 在脚本中调用 main() 函数
main()
