# 显示选中图片在图片编辑器
# blender有时候会无法显示 这个可以帮助
# 8脚本


def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


    #Shows a message box with a message, custom title, and a specific icon
    
import bpy

# 获取当前激活的对象
obj = bpy.context.active_object

# 检查对象是否存在且是一个网格对象
if obj and obj.type == 'MESH':
    # 获取激活对象的材质
    material_slots = obj.material_slots
    active_material_index = obj.active_material_index

    if 0 <= active_material_index < len(material_slots):
        active_material = material_slots[active_material_index].material

        # 检查材质是否存在且有节点树
        if active_material and active_material.use_nodes:
            # 获取材质节点树
            node_tree = active_material.node_tree

            # 遍历节点找到激活的节点
            active_node = None
            for node in node_tree.nodes:
                if node.select:
                    active_node = node
                    break

            # 检查节点是否是图像纹理节点
            if active_node and active_node.type == 'TEX_IMAGE':
                # 获取图像节点的图像
                image = active_node.image

                # 检查图像是否存在
                if image:
                    # 尝试查找当前打开的图像编辑器
                    image_editor = None
                    for area in bpy.context.screen.areas:
                        print(area.type)
                        if area.type == 'IMAGE_EDITOR':
                            area.spaces.active.image = image
                            image_editor = 1
                    if not image_editor:
                        ShowMessageBox("未打开图片编辑器", "未打开图片编辑器", 'ERROR')

