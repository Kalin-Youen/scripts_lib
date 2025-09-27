# script_id: 26a57e15-51ce-403c-971a-95c0c27c850d
import bpy
import os
import ast

# --- 配置 ---
# PME 插件的文件夹名，通常是 'pie_menu_editor'
ADDON_NAME = 'pie_menu_editor'
# 需要被重命名的 item 的目标名称
TARGET_ITEM_NAME = 'Run the script'


def rename_all_pme_script_runners():
    """
    自动扫描所有 PME 菜单。
    查找名称为 'Run the script' 的槽位 (item)。
    并根据其命令中的 'filepath' 路径，将其重命名为对应的脚本文件名。
    如果解析失败，则安全跳过。
    """
    print(f"\n{'='*70}")
    print(f"--- 开始自动重命名所有 PME 菜单中名为 '{TARGET_ITEM_NAME}' 的项目 ---")
    print(f"{'='*70}\n")

    updated_count = 0
    scanned_menus = 0

    try:
        # 1. 获取 PME 插件的设置
        prefs = bpy.context.preferences.addons[ADDON_NAME].preferences
        
        if not prefs.pie_menus:
            print("信息: PME 中没有找到任何已配置的菜单。")
            return

        # 2. 遍历 PME 中的每一个菜单 (menu)
        for menu in prefs.pie_menus:
            scanned_menus += 1
            print(f"[*] 正在扫描菜单: '{menu.name}'")

            # 3. 遍历菜单中的所有槽位 (item)
            for item in menu.pmis:

                # 4. 检查 item 的名称是否是我们想找的目标
                if item.name == TARGET_ITEM_NAME:
                    
                    # 从 item.text 获取命令字符串 (根据您的代码，PME将命令存在了.text里)
                    command_str = item.text
                    
                    # 检查命令是否有效
                    if not command_str or 'filepath' not in command_str:
                        print(f"  [!] 警告: 找到一个匹配项，但其命令中不含'filepath'，已跳过。")
                        continue

                    try:
                        # 5. 使用 ast 安全地解析命令字符串以提取 filepath
                        tree = ast.parse(command_str)
                        # 定位到函数调用节点
                        call_node = tree.body[0].value

                        filepath = None
                        # 遍历调用中的所有关键字参数
                        for kw in call_node.keywords:
                            if kw.arg == 'filepath':
                                # kw.value.s 是字符串字面量的值
                                filepath = kw.value.s
                                break

                        if filepath:
                            # 6. 从文件路径中提取不带扩展名的文件名
                            base_name = os.path.basename(filepath)
                            new_name = os.path.splitext(base_name)[0]

                            # 7. 更新 item 的名称，并打印成功信息
                            print(f"  [✓] 成功: 正在将 '{item.name}' -> '{new_name}'")
                            item.name = new_name
                            updated_count += 1
                        else:
                            print(f"  [!] 警告: 成功解析命令，但未找到'filepath'参数，已跳过。")


                    except (SyntaxError, IndexError, AttributeError) as e:
                        # 8. 如果解析失败，打印警告并安全跳过 (pass)
                        print(f"  [!] 警告: 解析命令时出错，已跳过。")
                        print(f"      命令: '{command_str}'")
                        print(f"      错误: {e}")

    except KeyError:
        print(f"错误: 无法找到插件 '{ADDON_NAME}'。请确保它已启用。")
        return
    except Exception as e:
        print(f"发生未知严重错误: {e}")
        return

    # --- 9. 打印最终的总结报告 ---
    print(f"\n--- {'处理完成':^64} ---")
    print(f"总共扫描了 {scanned_menus} 个菜单。")
    if updated_count > 0:
        print(f"成功更新了 {updated_count} 个项目的名称！")
        print("\n提示: 请检查PME设置界面，确认更改是否生效。可能需要手动保存PME设置。")
    else:
        print("在所有菜单中，均未找到需要重命名的项目。")

# --- 运行主函数 ---
# 建议在运行前备份您的PME设置！
rename_all_pme_script_runners()

