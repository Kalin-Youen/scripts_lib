import bpy

# 遍历当前场景的所有对象，同步渲染可见性
for obj in bpy.context.scene.objects:
    # 如果可见 (hide_viewport=False) 且启用 (hide_select=False)，则可渲染 (hide_render=False)
    if not obj.hide_viewport and not obj.hide_select:
        obj.hide_render = False
    # 否则（不可见），不渲染 (hide_render=True)
    else:
        obj.hide_render = True

print("渲染同步完成！所有对象已根据视口可见性设置渲染状态。")
