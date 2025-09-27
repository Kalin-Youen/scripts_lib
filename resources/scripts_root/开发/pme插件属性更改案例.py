# script_id: 3e2914d9-5395-4622-82e5-620e993e0182

# 强大的pme属性探查
import bpy

wm = bpy.data.window_managers["WinMan"]

# 检查 pme 是否存在
if not hasattr(wm, "pme"):
    print("❌ Pie Menu Editor (PME) 插件未启用或未安装")
else:
    pme = wm.pme
    print("✅ 找到 PME 对象:", pme)

    # 获取所有属性/方法名
    all_attrs = dir(pme)

    print("\n🔍 所有属性和方法（前50个）:")
    for i, attr in enumerate(all_attrs[:50]):
        print(f"  {i+1:2d}. {attr}")
    if len(all_attrs) > 50:
        print(f"  ... 还有 {len(all_attrs) - 50} 个未显示")

    # 查找“可疑”方法：包含 current, get, active, selected, idx, index 等关键词
    keywords = ["current", "get", "active", "selected", "idx", "index", "link", "item"]
    print(f"\n🔎 查找包含关键词 {keywords} 的属性/方法:")

    for attr in all_attrs:
        if any(kw in attr.lower() for kw in keywords):
            value = getattr(pme, attr)
            if callable(value):
                # 尝试调用无参方法（安全起见用 try）
                try:
                    result = value()
                    print(f"  🟢 方法 {attr}() → {result}")
                except Exception as e:
                    print(f"  🔴 方法 {attr}() 调用失败: {e}")
            else:
                print(f"  🟡 属性 {attr} = {value}")

    # 特别检查 links_idx 和 links（通常是一对）
    print(f"\n📌 当前 links_idx = {getattr(pme, 'links_idx', 'N/A')}")
    if hasattr(pme, "links"):
        links = pme.links
        idx = getattr(pme, "links_idx", 0)
        if 0 <= idx < len(links):
            current_item = links[idx]
            print(f"📌 当前选中项 links[{idx}] = {current_item}")
            # 打印当前项的属性（如果是 bpy_struct）
            if hasattr(current_item, "__slots__"):
                print("    属性:")
                for slot in current_item.__slots__:
                    try:
                        v = getattr(current_item, slot)
                        print(f"      {slot} = {v}")
                    except:
                        pass
        else:
            print(f"⚠️  links_idx 超出范围 ({idx} >= {len(links)})")



# 找到当前活动的菜单
import bpy

ADDON_NAME = "pie_menu_editor"

def find_pie_menu_by_name(menu_name):
    if ADDON_NAME not in bpy.context.preferences.addons:
        print("❌ PME 插件未启用")
        return None

    prefs = bpy.context.preferences.addons[ADDON_NAME].preferences

    for i, menu in enumerate(prefs.pie_menus):
        if menu.name == menu_name:
            return menu, i
    return None, -1

# 🎯 获取当前链接项
wm = bpy.data.window_managers["WinMan"]
if not hasattr(wm, "pme"):
    print("❌ 未找到 PME 数据")
else:
    pme = wm.pme
    link = pme.links[pme.get_links_idx()]
    target_menu_name = link.pm_name  # ← "物体D二级"

    print(f"🔗 当前链接项属于菜单: '{target_menu_name}'")

    # 🔍 查找这个菜单
    menu, menu_index = find_pie_menu_by_name(target_menu_name)

    if menu is None:
        print(f"❌ 未找到名为 '{target_menu_name}' 的菜单")
    else:
        print(f"✅ 找到菜单 '{menu.name}' (索引 {menu_index})，共 {len(menu.pmis)} 项:")
        print("-" * 60)

        for idx, pmi in enumerate(menu.pmis):
            print(f"ButtonItem[{idx:2d}]:")
            print(f"    name: {pmi.name}")
            print(f"    text: {pmi.text}")
            print(f"    icon: {pmi.icon}")
            print(f"    mode: {pmi.mode}")
            print("")



# 更改脚本命令

import bpy

ADDON_NAME = "pie_menu_editor"

def modify_pie_menu_item_by_index(menu_index=63, item_index=7, new_name="lod父级", new_cmd=None):
    if not new_cmd:
        new_cmd = 'bpy.ops.sm.run_script(filepath="D:\\\\yangding\\\\app\\\\blender4Addons\\\\addons\\\\quick_run_scripts\\\\addons\\\\quick_run_scripts\\\\resources\\\\scripts_root\\\\1临时\\\\lod父级.py")'

    if ADDON_NAME not in bpy.context.preferences.addons:
        print("❌ PME 插件未启用")
        return False

    prefs = bpy.context.preferences.addons[ADDON_NAME].preferences

    if menu_index >= len(prefs.pie_menus):
        print(f"❌ 菜单索引 {menu_index} 超出范围")
        return False

    menu = prefs.pie_menus[menu_index]

    if item_index >= len(menu.pmis):
        print(f"❌ 项索引 {item_index} 超出范围，当前菜单只有 {len(menu.pmis)} 项")
        return False

    pmi = menu.pmis[item_index]

    # 备份旧值
    old_name = pmi.name
    old_text = pmi.text

    # 执行修改
    pmi.name = new_name
    pmi.text = new_cmd
    pmi.icon = ""  # 设置脚本图标 'FILE_SCRIPT'
    pmi.mode = 'COMMAND'      # 确保是命令模式

    print(f"✅ 成功修改菜单 '{menu.name}' (索引 {menu_index}) 的第 {item_index} 项:")
    print(f"    旧名称: {old_name}")
    print(f"    新名称: {pmi.name}")
    print(f"    旧命令: {old_text}")
    print(f"    新命令: {pmi.text}")

    # 强制UI刷新
    for area in bpy.context.screen.areas:
        area.tag_redraw()

    return True

# 🎯 执行修改！
modify_pie_menu_item_by_index(menu_index=63, item_index=7)