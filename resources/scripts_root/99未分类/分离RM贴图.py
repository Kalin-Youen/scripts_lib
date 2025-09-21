import bpy
import os
import numpy as np
from mathutils import Vector

# ---------- 若 .blend 未保存则弹窗并退出 ----------
def abort_if_blend_unsaved():
    if not bpy.data.filepath:
        def draw(self, _):
            self.layout.label(text="⚠ 当前 .blend 文件尚未保存！")
            self.layout.label(text="请先 File → Save，再运行脚本。")
        bpy.context.window_manager.popup_menu(draw, title="未保存提示", icon='ERROR')
        return True
    return False

# ---------- 创建 / 覆盖灰度 JPG ----------
def make_gray_jpg(img_name, channel, w, h, out_path):
    # 若已经存在同名 Image，直接复用而不是另起 .001
    img = bpy.data.images.get(img_name)
    if img is None:
        img = bpy.data.images.new(img_name, width=w, height=h,
                                  alpha=False, float_buffer=False)
    rgba = np.zeros((h, w, 4), dtype=np.float32)
    g = channel / 255.0
    rgba[:, :, 0:3] = g[:, :, None]
    rgba[:, :, 3]   = 1.0
    img.pixels[:]    = rgba.flatten()
    img.filepath_raw = out_path
    img.file_format  = 'JPEG'
    img.save()
    return img

def split_rm_auto(out_dir):
    if abort_if_blend_unsaved():
        return

    # ---------- 找到 RM / ORM 贴图节点 ----------
    img_node = getattr(bpy.context, "active_node", None)

    def is_rm(node):
        return (node.type == 'TEX_IMAGE' and node.image and
                any(k in node.image.name.lower()
                    for k in ("_rm", "orm", "occroughmetal", "occluderoughmetal")))

    if img_node is None or not is_rm(img_node):
        obj = bpy.context.object
        mat = obj.active_material if obj else None
        if mat and mat.use_nodes:
            img_node = next((n for n in mat.node_tree.nodes if is_rm(n)), None)

    if img_node is None:
        print("❌ 没找到 RM/ORM Image Texture 节点")
        return

    img = img_node.image
    w, h = img.size
    arr = (np.array(img.pixels[:]).reshape(h, w, 4) * 255).astype(np.uint8)
    rough = arr[:, :, 2]          # B → Roughness
    metal = arr[:, :, 1]          # G → Metallic

    os.makedirs(out_dir, exist_ok=True)

    mat = bpy.context.object.active_material if bpy.context.object else None
    prefix = mat.name if mat else "Material"

    # ---------- 统一命名 ----------
    rough_img_name  = f"{prefix}_Roughness"
    metal_img_name  = f"{prefix}_Metallic"
    rough_path      = os.path.join(out_dir, f"{rough_img_name}.jpg")
    metal_path      = os.path.join(out_dir, f"{metal_img_name}.jpg")

    rough_img = make_gray_jpg(rough_img_name, rough, w, h, rough_path)
    metal_img = make_gray_jpg(metal_img_name, metal, w, h, metal_path)

    nt = img_node.id_data
    r_node = nt.nodes.new("ShaderNodeTexImage")
    m_node = nt.nodes.new("ShaderNodeTexImage")
    r_node.image  = rough_img
    m_node.image  = metal_img
    for n in (r_node, m_node):
        n.image.colorspace_settings.name = 'Non-Color'
        n.label = n.name = n.image.name    # ★ 节点名称/标签同步

    r_node.location = img_node.location + Vector((300,  40))
    m_node.location = img_node.location + Vector((300, -40))

    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf:
        for sock in (bsdf.inputs['Roughness'], bsdf.inputs['Metallic']):
            for link in list(sock.links):
                nt.links.remove(link)
        nt.links.new(r_node.outputs['Color'], bsdf.inputs['Roughness'])
        nt.links.new(m_node.outputs['Color'], bsdf.inputs['Metallic'])
        print("✅ 已输出并连线：", rough_path, metal_path)
    else:
        print("⚠️ 找不到 Principled BSDF，贴图已生成但未连线")

# -------------------- 调 用 --------------------
blend_dir = bpy.path.abspath("//")
out_dir   = os.path.join(blend_dir, "分离的贴图_JPG")
split_rm_auto(out_dir)
