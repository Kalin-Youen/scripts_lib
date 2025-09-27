# script_id: 0c7badd2-48b2-446c-8247-39cfb5f3795d
# 材质贴图一键给box投影方式
# 材质贴图一键给box投影方式 
# 2网格
import bpy

active_material = bpy.context.object.active_material
if active_material is not None:
    node_tree = active_material.node_tree
    mat_name = active_material.name
    print(mat_name)
    for node in node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            # 将投影方式更改为方框
            node.projection = 'BOX'