# script_id: 9641df69-b941-4787-9b70-6170f075afe8
# -*- coding: utf-8 -*-
# =============================================================================
#  GitHub 仓库目录扫描器 for Blender (高速版 + 内容预览)
#  作者: 代码高手 (AI)
#  描述: 使用 'git/trees' API 快速扫描目录，并自动获取第一个子目录中
#        第一个文件的内容进行打印。
# =============================================================================

import bpy
import json
from urllib import request, error, parse # 增加了 parse 用于URL编码

# --- 配置区 ---
REPO_OWNER = "Kalin-Youen"
REPO_NAME = "scripts_root"
# 使用我们最终确定的正确分支名
BRANCH_NAME = "main"
# =============================================================================

def fetch_github_api(api_url):
    """
    (已有函数) 发送请求到 GitHub API 并返回 JSON 数据。
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = request.Request(api_url, headers=headers)
        
        with request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                data = response.read().decode('utf-8')
                return json.loads(data)
            else:
                print(f"❌ API 请求失败，状态码: {response.status}")
                return None
    except error.HTTPError as e:
        print(f"❌ HTTP 错误: {e.code} - {e.reason}")
        if e.code == 404:
            print("   - 404 Not Found: 请检查分支名是否正确，或仓库Git树是否为空。")
        return None
    except Exception as e:
        print(f"❌ 发生未知错误: {type(e).__name__} - {e}")
        return None

# ======================= 新增函数 =======================
def fetch_raw_content(owner, repo, branch, file_path):
    """
    获取 GitHub 仓库中指定文件的原始文本内容。
    """
    try:
        # 对文件路径进行URL编码，以正确处理中文、空格等特殊字符
        encoded_path = parse.quote(file_path)
        
        # 构建获取原始文件内容的URL
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{encoded_path}"
        
        print(f"🌐 正在请求文件内容: {raw_url}")
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = request.Request(raw_url, headers=headers)

        with request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                # 使用 utf-8 解码，以支持包含中文注释的 .py 或 .json 文件
                return response.read().decode('utf-8')
            else:
                print(f"❌ 获取文件内容失败，状态码: {response.status}")
                return None
                
    except Exception as e:
        print(f"❌ 获取文件内容时发生错误: {type(e).__name__} - {e}")
        return None
# ========================================================


def scan_repo_and_print_first_file(owner, repo, branch):
    """
    主函数：扫描仓库，打印目录树，然后打印第一个文件的内容。
    """
    print("\n" + "="*60)
    print(f"🚀 开始扫描 GitHub 仓库: {owner}/{repo} (高速模式)")
    print(f"   分支: {branch}")
    print("="*60)

    # 1. 获取目录结构
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    print(f"\n🌐 正在发起单次高速请求: {api_url}\n")
    data = fetch_github_api(api_url)
    
    if not data or 'tree' not in data:
        print("❌ 未能获取到仓库的文件树数据。流程终止。")
        return

    file_paths = [item['path'] for item in data['tree']]
    
    # 2. 构建并打印目录树
    tree = {}
    for path in sorted(file_paths):
        parts = path.split('/')
        current_level = tree
        for part in parts:
            if part not in current_level:
                current_level[part] = {}
            current_level = current_level[part]
            
    print("🌳 仓库文件目录结构:\n")
    print(f"📁 {repo}")
    print_tree(tree)
    print("\n" + "="*60)
    print("✅ 目录扫描完成！")
    print("="*60)

    # 3. 查找第一个文件并打印其内容
    target_file_path = None
    for path in sorted(file_paths):
        # 查找第一个包含'/'的路径，这表示它在某个文件夹内
        if '/' in path:
            target_file_path = path
            break # 找到后立即停止搜索
    
    if target_file_path:
        print(f"\n📄 将打印第一个子目录文件的内容: '{target_file_path}'\n")
        
        content = fetch_raw_content(owner, repo, branch, target_file_path)
        
        if content:
            print(f"--- [ {target_file_path} ] 的内容开始 ---")
            print("-" * (len(target_file_path) + 16))
            print(content)
            print("-" * (len(target_file_path) + 14))
            print(f"--- [ {target_file_path} ] 的内容结束 ---")
        else:
            print(f"❌ 未能获取文件 '{target_file_path}' 的内容。")
    else:
        print("\nℹ️ 仓库中未发现任何子目录下的文件。")


def print_tree(tree_dict, prefix=""):
    """
    (已有函数) 递归函数，用于以树状格式打印文件结构。
    """
    items = sorted(tree_dict.items(), key=lambda x: not bool(x[1]))
    for i, (name, subtree) in enumerate(items):
        is_last = (i == len(items) - 1)
        connector = "└── " if is_last else "├── "
        try:
            print(prefix + connector + name)
        except UnicodeEncodeError:
            safe_name = name.encode('utf-8', 'replace').decode('utf-8')
            print(prefix + connector + safe_name)
        if subtree:
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(subtree, new_prefix)


if __name__ == "__main__":
    scan_repo_and_print_first_file(owner=REPO_OWNER, repo=REPO_NAME, branch=BRANCH_NAME)