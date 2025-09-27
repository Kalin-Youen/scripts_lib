# script_id: 6675817a-0ccb-4c10-9bfe-129a1d57101b
# reload_addon.py
#
# 在 Blender Text Editor 中打开本文件并 Run Script
# 即可对目标插件进行“热重载”（相当于禁用→重新加载→启用）。
# ------------------------------------------------------------------

import bpy
import importlib
import sys

# 1. 把下面的名字改成你的插件模块名（文件名去掉 .py）
ADDON_NAME = "blender-to-unity-fbx-exporter"      # 例如你的脚本叫 unity_fbx_format.py

# ------------------------------------------------------------------
# 如果插件是一个 package（文件夹）而非单文件，请把此值设成包的根名字，
# 比如文件结构 my_addon/__init__.py  ->  ADDON_NAME = "my_addon"
# ------------------------------------------------------------------

def _reload_package(root_name: str):
    """递归 reload 整个包（包括子模块），保持导入顺序"""
    # 先收集所有以 root_name 开头的模块
    modules = {name: mod for name, mod in sys.modules.items()
               if name == root_name or name.startswith(root_name + ".")}

    # 按模块层级深度倒序 reload（先子后父，防止依赖出错）
    for name in sorted(modules, key=lambda n: n.count("."), reverse=True):
        try:
            importlib.reload(modules[name])
        except Exception as e:
            print(f"[Reload] 重新加载 {name} 失败:", e)


def reload_addon(addon_name: str):
    """禁用→reload→启用 指定插件"""
    prefs = bpy.context.preferences

    try:
        # 1) 若已启用，则禁用
        if addon_name in prefs.addons:
            bpy.ops.preferences.addon_disable(module=addon_name)
            print(f"[Reload] Add-on '{addon_name}' disabled")

        # 2) importlib.reload（支持单文件或包）
        if addon_name in sys.modules:
            mod = sys.modules[addon_name]
            # 判断是包还是单文件
            if hasattr(mod, "__path__"):
                _reload_package(addon_name)
            else:
                importlib.reload(mod)
            print(f"[Reload] Module '{addon_name}' reloaded")
        else:
            # 第一次加载
            __import__(addon_name)
            print(f"[Reload] Module '{addon_name}' imported first time")

        # 3) 重新启用
        bpy.ops.preferences.addon_enable(module=addon_name)
        print(f"[Reload] Add-on '{addon_name}' enabled")

        # 可选：保存用户偏好，以便下次 Blender 启动后保持启用
        # bpy.ops.wm.save_userpref()
    except Exception as exc:
        print(f"[Reload] 重新载入插件 '{addon_name}' 时出现异常：\n", exc)


# ------------------------------------------------------------------
# 直接运行
# ------------------------------------------------------------------
if __name__ == "__main__":
    reload_addon(ADDON_NAME)
