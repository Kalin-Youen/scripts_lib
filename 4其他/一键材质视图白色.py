# 一键材质视图白色
# 一键材质视图白色
# 1材质
import bpy

# 遍历所有材质
for material in bpy.data.materials:
    # 确保材质存在
    if material:
        # 确保材质有视图显示设置
        if material.use_nodes:  # 如果材质使用节点
            # 设置 Viewport Display 颜色
            material.diffuse_color = (1, 1, 1, 1)  # 黑色 (R, G, B, Alpha)
        else:  # 如果材质没有节点
            material.diffuse_color = (1, 1, 1, 1)

print("所有材质的视图颜色已设置为黑色。")
