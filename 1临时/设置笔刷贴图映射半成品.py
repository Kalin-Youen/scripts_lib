# coding: utf-8
import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty

# =============================================================================
#  核心操作器 (Operators)
# =============================================================================


class PAINT_OT_SetBrushToFloorboardAction(bpy.types.Operator):
    """(内部) 设置笔刷为楼板模式 (模板贴图)"""
    bl_idname = "paint.set_brush_to_floorboard_action"
    bl_label = "2. 设置笔刷为楼板 (模板)"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        image_name = getattr(context.scene, "quick_brush_image_name", "")
        return image_name and image_name in bpy.data.images

    def execute(self, context):
        image_name = context.scene.quick_brush_image_name
        brush = context.tool_settings.image_paint.brush
        
        # ======================= 最终API修正：双重强制赋值 =======================
        
        # 1. 获取我们加载的图像数据块
        img_to_assign = bpy.data.images.get(image_name)
        if not img_to_assign:
            self.report({'ERROR'}, f"无法找到图像: {image_name}")
            return {'CANCELLED'}

        active_slot = brush.texture_slot
        

        new_tex_name = f"{image_name}_BrushTex"
        if new_tex_name in bpy.data.textures:
            tex = bpy.data.textures[new_tex_name]
        else:
            tex = bpy.data.textures.new(name=new_tex_name, type='IMAGE')
        
        tex.type = 'IMAGE'
        tex.image = img_to_assign
        
        active_slot.texture = tex

        brush.texture = tex
        
        print(f"   - 已将新纹理 '{tex.name}' 强制赋给画笔及其纹理槽。")
        
        # 6. 在纹理槽上设置映射模式
        active_slot.map_mode = 'STENCIL'
        #bpy.ops.image.open(filepath="C:\\Users\\31249\\Pictures\\械斗\\c1a2fd116eb4b7ee64848bc2c863873b.png")
        
        # =======================================================================

        # --- DEBUG 输出验证 ---
        print("\n=== DEBUG: 最终验证 ===")
        print(f"画笔 (Brush): '{brush.name}'")
        print(f"画笔的快捷方式纹理 (Brush.texture): {brush.texture.name if brush.texture else 'None'}")
        print(f"纹理槽内的纹理 (Slot.texture): {active_slot.texture.name if active_slot.texture else 'None'}")
        print(f"纹理内的图像 (Texture.image): {active_slot.texture.image.name if active_slot.texture and active_slot.texture.image else 'None'}")
        print(f"映射模式 (Map Mode): {active_slot.map_mode}")
        print("========================\n")

        self.report({'INFO'}, f"笔刷已设置为模板模式: {img_to_assign.name}")
        return {'FINISHED'}

# (脚本的其余部分，如其他类、注册函数等，都保持原样)





class PAINT_OT_SetBrushToViewplaneAction(bpy.types.Operator):
    """(内部) 设置笔刷为视图平面模式 (清除纹理)"""
    bl_idname = "paint.set_brush_to_viewplane_action"
    bl_label = "3. 清除纹理 (视图平面)"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        brush = context.tool_settings.image_paint.brush
        
        # 确保有纹理槽可以操作
        if brush.texture_slot:
            brush.texture_slot.map_mode = 'VIEW_PLANE'

        # 清空画笔的纹理引用，这是正确的做法
        brush.texture = None
            
        self.report({'INFO'}, "笔刷已恢复为常规模式")
        return {'FINISHED'}


class WM_OT_LoadImageAndStore(bpy.types.Operator, ImportHelper):
    """(内部) 打开文件浏览器加载图像并存储其名称"""
    bl_idname = "wm.load_image_and_store"
    bl_label = "1. 加载图像"
    bl_icon = 'FILE_IMAGE'
    bl_options = {'REGISTER', 'UNDO'}

    # 文件浏览器过滤器
    filter_glob: StringProperty(
        default='*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff;*.tga;*.exr',
        options={'HIDDEN'},
        maxlen=255,
    )

    def execute(self, context):
        try:
            # 使用绝对路径加载，更可靠
            img = bpy.data.images.load(self.filepath, check_existing=True)
            # 将加载的图像名称存储到场景属性中，方便其他操作器调用
            context.scene.quick_brush_image_name = img.name
            self.report({'INFO'}, f"已加载图像: {img.name}")
            
            # 加载成功后，自动调用设置模板的操作
            bpy.ops.paint.set_brush_to_floorboard_action()
            
        except Exception as e:
            self.report({'ERROR'}, f"加载图像失败: {e}")
            return {'CANCELLED'}
        
        return {'FINISHED'}


# =============================================================================
#  主对话框 (Main Dialog)
# =============================================================================

class WM_OT_QuickBrushDialog(bpy.types.Operator):
    """显示快速笔刷设置对话框"""
    bl_idname = "wm.quick_brush_dialog"
    bl_label = "快速笔刷设置"
    bl_options = {'REGISTER'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=320)

    def draw(self, context):
        layout = self.layout
        image_name = getattr(context.scene, "quick_brush_image_name", "")

        layout.label(text="快速设置纹理笔刷:")
        layout.separator()
        
        # 1. 加载图像按钮
        layout.operator(WM_OT_LoadImageAndStore.bl_idname)

        # 如果已经加载了图像，显示当前图像名称
        if image_name and image_name in bpy.data.images:
            box = layout.box()
            row = box.row(align=True)
            row.label(text="当前:", icon='IMAGE_DATA')
            row.label(text=image_name)

        layout.separator()

        # 2. 设置为模板模式按钮
        layout.operator(PAINT_OT_SetBrushToFloorboardAction.bl_idname)
        
        # 3. 恢复为普通笔刷按钮
        layout.operator(PAINT_OT_SetBrushToViewplaneAction.bl_idname)

        # 4. 添加一些使用提示
        layout.separator()
        box = layout.box()
        col = box.column(align=True)
        col.label(text="使用提示:", icon='INFO')
        col.label(text="• 模板模式: 用于贴花效果")
        col.label(text="• 按 Ctrl 可调整贴图位置")
        col.label(text="• 按 Shift+Ctrl 可调整大小")


# =============================================================================
#  注册与注销管理 (Registration Management)
# =============================================================================

classes_to_register = (
    PAINT_OT_SetBrushToFloorboardAction,
    PAINT_OT_SetBrushToViewplaneAction,
    WM_OT_LoadImageAndStore,
    WM_OT_QuickBrushDialog,
)

def register():
    if not hasattr(bpy.types.Scene, "quick_brush_image_name"):
        bpy.types.Scene.quick_brush_image_name = StringProperty()
    
    for cls in classes_to_register:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes_to_register):
        bpy.utils.unregister_class(cls)
    
    if hasattr(bpy.types.Scene, "quick_brush_image_name"):
        del bpy.types.Scene.quick_brush_image_name

# =============================================================================
#  脚本入口 (Script Entry Point)
# =============================================================================

if __name__ == "__main__":
    try:
        unregister()
    except Exception:
        pass
    register()

    if bpy.context.mode == 'PAINT_TEXTURE':
        bpy.ops.wm.quick_brush_dialog('INVOKE_DEFAULT')
