# script_id: 1e30be3d-98e9-44d7-a1bc-55a3ef1cb6ba
# 属性探查器工具 —— 输入对象路径，打印其所有属性和方法
# 作者：Qwen
# 日期：2025年9月20日

import bpy

bl_info = {
    "name": "属性探查器 (Property Inspector)",
    "author": "Qwen",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Tool Tab",
    "description": "输入对象路径，探查其所有属性与方法",
    "category": "Development",
}

# ==============================
# 核心探查函数
# ==============================
def inspect_object(obj, obj_name="target", max_depth=3, current_depth=0, visited=None):
    """递归探查对象的属性和方法，避免循环引用"""
    if visited is None:
        visited = set()

    obj_id = id(obj)
    if obj_id in visited:
        return [f"⚠️ 循环引用: {obj_name}"]
    visited.add(obj_id)

    lines = []
    indent = "  " * current_depth

    if current_depth > max_depth:
        lines.append(f"{indent}... (深度限制)")
        return lines

    lines.append(f"{indent}🔍 {obj_name} → 类型: {type(obj).__name__}")

    try:
        attrs = dir(obj)
    except Exception as e:
        lines.append(f"{indent}❌ 无法获取属性: {e}")
        return lines

    for attr in attrs:
        if attr.startswith("__") and attr.endswith("__"):
            continue  # 跳过魔术方法，除非你想要

        try:
            value = getattr(obj, attr)
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:97] + "..."

            if callable(value):
                try:
                    # 尝试无参调用
                    result = value()
                    result_str = str(result)
                    if len(result_str) > 80:
                        result_str = result_str[:77] + "..."
                    lines.append(f"{indent}  🟢 方法 {attr}() → {result_str}")
                except Exception as e:
                    lines.append(f"{indent}  🔴 方法 {attr}() → 调用失败: {e}")
            else:
                lines.append(f"{indent}  🟡 属性 {attr} = {value_str}")

                # 如果是 bpy_prop_collection 或 list/tuple，递归探查前几个元素
                if hasattr(value, "__len__") and len(value) > 0 and current_depth < max_depth - 1:
                    if isinstance(value, (list, tuple)) or hasattr(value, "__getitem__"):
                        for i, item in enumerate(value[:3]):  # 只探查前3个
                            sub_name = f"{attr}[{i}]"
                            lines.extend(inspect_object(item, sub_name, max_depth, current_depth + 1, visited))
                        if len(value) > 3:
                            lines.append(f"{indent}    ... 共 {len(value)} 项，仅显示前3项")

        except Exception as e:
            lines.append(f"{indent}  ❌ 属性 {attr} 获取失败: {e}")

    return lines


# ==============================
# 弹窗输入操作器
# ==============================
class OBJECT_OT_inspect_popup(bpy.types.Operator):
    bl_idname = "object.inspect_popup"
    bl_label = "探查对象属性"
    bl_description = "输入对象路径（如 bpy.data.window_managers['WinMan'].pme），探查其结构"

    target_path: bpy.props.StringProperty(
        name="对象路径",
        description="输入要探查的对象路径",
        default="bpy.data.window_managers['WinMan']"
    )

    def execute(self, context):
        self.report({'INFO'}, f"探查路径: {self.target_path}")
        try:
            obj = eval(self.target_path)
        except Exception as e:
            self.report({'ERROR'}, f"路径解析失败: {e}")
            return {'CANCELLED'}

        print("\n" + "="*80)
        print(f"🔍 属性探查器结果 → 路径: {self.target_path}")
        print("="*80)

        lines = inspect_object(obj, obj_name=self.target_path)

        for line in lines:
            print(line)

        # 可选：将结果写入文本块，方便查看
        text_name = "属性探查结果"
        if text_name in bpy.data.texts:
            text_block = bpy.data.texts[text_name]
            text_block.clear()
        else:
            text_block = bpy.data.texts.new(text_name)

        text_block.write("\n".join(lines))
        self.report({'INFO'}, f"结果已写入文本块 '{text_name}'")

        # 自动打开文本编辑器（可选）
        # bpy.ops.screen.area_dupli('INVOKE_DEFAULT')
        # for area in context.screen.areas:
        #     if area.type == 'TEXT_EDITOR':
        #         area.spaces[0].text = text_block
        #         break

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "target_path")
        layout.label(text="示例: bpy.data.window_managers['WinMan'].pme 或 bpy.context.object")


# ==============================
# 面板：在侧边栏添加按钮
# ==============================
class VIEW3D_PT_inspector_panel(bpy.types.Panel):
    bl_label = "属性探查器"
    bl_idname = "VIEW3D_PT_inspector_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        layout.operator("object.inspect_popup", text="🔍 探查对象属性", icon='INFO')


# ==============================
# 注册 / 注销
# ==============================
classes = (
    OBJECT_OT_inspect_popup,
    VIEW3D_PT_inspector_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    print("✅ 属性探查器已注册！前往 3D视图 > 侧边栏 > Tool 查看按钮")

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()