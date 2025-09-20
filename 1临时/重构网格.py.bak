import bpy
import bmesh
import numpy as np
from mathutils import Vector
from bpy.props import IntProperty, EnumProperty

# --- 插件信息 ---
bl_info = {
    "name": "即时交互顶点拟合器",
    "author": "Your Super-Cute AI Assistant",
    "version": (3, 0),
    "blender": (4, 0, 0),
    "location": "在脚本编辑器中运行",
    "description": "运行后立即弹出对话框，并允许通过鼠标移动实时调整参数。",
    "category": "Mesh",
}

# ------------------------------------------------------------------------
# 核心拟合函数 (保持不变)
# ------------------------------------------------------------------------
def fit_to_bounding_box(verts):
    if not verts: return
    coords = np.array([v.co for v in verts])
    min_bound, max_bound = coords.min(axis=0), coords.max(axis=0)
    for v in verts:
        for i in range(3):
            v.co[i] = min_bound[i] if abs(v.co[i] - min_bound[i]) < abs(v.co[i] - max_bound[i]) else max_bound[i]

def fit_to_cylinder(verts, segments):
    if not verts or len(verts) < 3 or segments < 3: return
    coords = np.array([v.co for v in verts])
    center = Vector(coords.mean(axis=0))
    centered_coords = coords - center
    covariance_matrix = np.cov(centered_coords, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance_matrix)
    axis = Vector(eigenvectors[:, np.argmax(eigenvalues)])
    projections_on_axis = np.dot(centered_coords, axis)
    radius = np.linalg.norm(centered_coords - projections_on_axis[:, np.newaxis] * axis, axis=1).max()
    if radius < 1e-6: return
    
    for v in verts:
        vert_vec = v.co - center
        point_on_axis = center + vert_vec.dot(axis) * axis
        radial_vector = v.co - point_on_axis
        
        if radial_vector.length > 1e-6:
            radial_vector.normalize()
            ref_vec_x = Vector((1, 0, 0))
            if abs(ref_vec_x.dot(axis)) > 0.99: ref_vec_x = Vector((0, 1, 0))
            ref_vec_ortho = (axis.cross(ref_vec_x)).normalized()
            ref_vec_ortho_y = axis.cross(ref_vec_ortho).normalized()
            angle = np.arctan2(radial_vector.dot(ref_vec_ortho_y), radial_vector.dot(ref_vec_ortho))
            segment_angle = 2 * np.pi / segments
            quantized_angle = round(angle / segment_angle) * segment_angle
            new_radial_vector = (ref_vec_ortho * np.cos(quantized_angle) + ref_vec_ortho_y * np.sin(quantized_angle)) * radius
            v.co = point_on_axis + new_radial_vector

# ------------------------------------------------------------------------
# ✨ 模态交互操作符 (Modal Operator) ✨
# ------------------------------------------------------------------------
class MODAL_OT_interactive_fitter(bpy.types.Operator):
    """一个有弹出对话框和实时鼠标交互的顶点拟合工具"""
    bl_idname = "mesh.interactive_fitter"
    bl_label = "Interactive Vertex Fitter"
    # 添加 'UNDO' 很重要，这样取消操作才能恢复到初始状态
    bl_options = {'REGISTER', 'UNDO'}

    # --- 属性定义 (和之前一样) ---
    shape_type: EnumProperty(
        name="Shape Type",
        description="选择要拟合的形状",
        items=[('CUBE', "Cube", "拟合到立方体边界盒"),
               ('CYLINDER', "Cylinder", "拟合到圆柱体")],
        default='CYLINDER' # 默认圆柱体，这样交互更有趣
    )
    
    cylinder_segments: IntProperty(
        name="Segments",
        description="圆柱体的段数 (可通过鼠标左右移动调整)",
        default=16,
        min=3,
        max=256
    )

    # --- 用于模态操作的内部变量 ---
    initial_mouse_x: int
    initial_segments: int
    bm: object # bmesh 对象
    obj: object # 网格对象
    initial_vert_coords: dict # 存储顶点的初始位置，用于撤销

    def execute_fit(self):
        """核心执行逻辑，分离出来以便在模态中重复调用"""
        # 每次执行前，先恢复到初始状态，避免效果叠加
        for v_idx, co in self.initial_vert_coords.items():
            self.bm.verts.ensure_lookup_table() # 确保索引有效
            self.bm.verts[v_idx].co = co
        
        selected_verts = [self.bm.verts[v_idx] for v_idx in self.initial_vert_coords.keys()]

        if self.shape_type == 'CUBE':
            fit_to_bounding_box(selected_verts)
        elif self.shape_type == 'CYLINDER':
            fit_to_cylinder(selected_verts, self.cylinder_segments)
        
        # 更新网格，让更改在视图中可见
        bmesh.update_edit_mesh(self.obj.data)

    def modal(self, context, event):
        # --- 2. 模态循环：监听鼠标和键盘事件 ---
        context.area.tag_redraw() # 刷新视图

        if event.type == 'MOUSEMOVE':
            # 当鼠标移动时
            delta_x = event.mouse_x - self.initial_mouse_x
            # 将像素移动转换为段数变化，可以调整 sensitivity 来改变灵敏度
            sensitivity = 0.1 
            new_segments = self.initial_segments + int(delta_x * sensitivity)
            # 限制段数在有效范围内
            self.cylinder_segments = max(3, min(256, new_segments))
            # 重新执行拟合
            self.execute_fit()
            # 在左下角显示当前段数
            context.workspace.status_text_set(f"Segments: {self.cylinder_segments}")

        elif event.type in {'LEFTMOUSE'}:
            # 当点击左键时，结束操作，确认更改
            context.workspace.status_text_set(None) # 清除状态栏文本
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            # 当点击右键或按ESC时，取消操作
            # 恢复到最开始的状态
            for v_idx, co in self.initial_vert_coords.items():
                 self.bm.verts.ensure_lookup_table()
                 self.bm.verts[v_idx].co = co
            bmesh.update_edit_mesh(self.obj.data)
            context.workspace.status_text_set(None) # 清除状态栏文本
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        # --- 1. 入口：在执行前被调用 ---
        if context.mode != 'EDIT_MESH':
            self.report({'WARNING'}, "请在网格编辑模式下运行")
            return {'CANCELLED'}

        self.obj = context.edit_object
        self.bm = bmesh.from_edit_mesh(self.obj.data)
        
        # 存储选中的顶点及其初始坐标
        self.initial_vert_coords = {v.index: v.co.copy() for v in self.bm.verts if v.select}
        
        if not self.initial_vert_coords:
            self.report({'WARNING'}, "没有选择任何顶点")
            return {'CANCELLED'}
        
        # 打开那个你想要的“弹窗”！
        return context.window_manager.invoke_props_dialog(self)


    def execute(self, context):
        # --- 弹窗点击"OK"后，进入这里 ---
        self.initial_mouse_x = context.mouse_x # 记录当前鼠标X坐标
        self.initial_segments = self.cylinder_segments # 记录初始段数
        
        # 执行一次初始拟合
        self.execute_fit()

        # 添加模态处理器，让 modal() 方法开始工作
        context.window_manager.modal_handler_add(self)
        # 返回 'RUNNING_MODAL' 表示操作还未结束，将进入模态循环
        return {'RUNNING_MODAL'}


# ------------------------------------------------------------------------
# 注册与运行
# ------------------------------------------------------------------------
def register():
    bpy.utils.register_class(MODAL_OT_interactive_fitter)

def unregister():
    bpy.utils.unregister_class(MODAL_OT_interactive_fitter)

if __name__ == "__main__":
    # 用 try/except 来避免重复注册的错误
    try:
        unregister()
    except (RuntimeError, AttributeError):
        pass
    
    register()
    
    # 用 'INVOKE_DEFAULT' 来启动我们的操作符，这样会先调用 invoke() 方法
    bpy.ops.mesh.interactive_fitter('INVOKE_DEFAULT')

