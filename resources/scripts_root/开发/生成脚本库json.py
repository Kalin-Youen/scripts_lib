# -*- coding: utf-8 -*-
# =============================================================================
#  元数据生成器 (Metadata Generator) for Smart Script Manager
#  作者: 代码高手 AI
#  描述: 扫描指定的脚本目录，智能地创建或更新 metadata.json 文件。
# =============================================================================

import bpy
import os
import json
import uuid
import hashlib
from datetime import datetime

# --- 配置区 ---
# !!! 请根据你的实际路径修改这里 !!!
BASE_PATH = "E:\\files\\code\\BlenderAddonPackageTool-master\\addons\\quick_run_scripts\\resources"
SCRIPTS_ROOT_DIR = os.path.join(BASE_PATH, "scripts_root")
METADATA_FILE_PATH = os.path.join(BASE_PATH, "metadata.json")
# =============================================================================

def generate_unique_id():
    """生成一个简短且唯一的ID"""
    return uuid.uuid4().hex[:12] # 使用12位十六进制字符串，足够唯一

def calculate_sha(file_path):
    """计算文件的SHA256哈希值，作为版本指纹"""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except IOError:
        return ""

def create_default_script_entry(relative_path, sha):
    """为新脚本创建一个默认的元数据条目"""
    # 从文件名生成一个更易读的显示名称
    display_name = os.path.splitext(os.path.basename(relative_path))[0]
    display_name = display_name.replace('_', ' ').replace('-', ' ').title()

    # 从父文件夹名猜测标签
    parent_dir = os.path.basename(os.path.dirname(relative_path))
    tags = [parent_dir] if parent_dir else ["未分类"]

    return {
        "display_name": display_name,
        "tags": tags,
        "description": "请填写脚本描述...",
        "local_config": {
            "usage_count": 0,
            "last_used": "1970-01-01T00:00:00Z",
            "custom_priority": 50,
            "is_favorite": False
        },
        "remote_info": {
            "file_path": relative_path.replace('\\', '/'), # 确保路径使用'/'
            "sha": sha,
            "last_commit_date": datetime.now().isoformat(),
            "author": "YourName",
            "version": "1.0.0"
        }
    }

def scan_and_generate_metadata():
    """主函数：执行扫描和生成操作"""
    print("="*60)
    print("🚀 开始扫描脚本并生成元数据...")
    
    # 1. 检查路径是否存在
    if not os.path.isdir(SCRIPTS_ROOT_DIR):
        print(f"❌ 错误: 脚本根目录不存在! -> {SCRIPTS_ROOT_DIR}")
        return

    # 2. 扫描文件系统，获取所有.py文件
    found_scripts = {} # 存储 {relative_path: sha}
    for root, _, files in os.walk(SCRIPTS_ROOT_DIR):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, SCRIPTS_ROOT_DIR)
                sha = calculate_sha(full_path)
                found_scripts[relative_path] = sha
    
    print(f"✅ 在文件系统中找到 {len(found_scripts)} 个.py脚本。")

    # 3. 加载现有元数据 (如果存在)
    existing_metadata = {
        "version": "2.0",
        "metadata_last_updated": "",
        "scripts": {}
    }
    if os.path.exists(METADATA_FILE_PATH):
        try:
            with open(METADATA_FILE_PATH, 'r', encoding='utf-8') as f:
                existing_metadata = json.load(f)
            print("📖 已成功加载现有的 metadata.json 文件。")
        except json.JSONDecodeError:
            print("⚠️ 警告: 现有的 metadata.json 文件格式错误，将创建一个新的。")

    # 4. 智能合并
    
    # 创建一个查找映射，方便快速通过 file_path 找到 script_id
    path_to_id_map = {
        data['remote_info']['file_path']: script_id 
        for script_id, data in existing_metadata['scripts'].items()
    }
    
    final_scripts_data = existing_metadata['scripts'].copy()
    
    # -- 处理新增和更新的脚本 --
    for rel_path, sha in found_scripts.items():
        rel_path_posix = rel_path.replace('\\', '/') # 统一为 Posix 路径
        
        if rel_path_posix in path_to_id_map:
            # 脚本已存在，检查是否需要更新 SHA
            script_id = path_to_id_map[rel_path_posix]
            if final_scripts_data[script_id]['remote_info']['sha'] != sha:
                print(f"🔄 更新脚本: {rel_path_posix} (SHA值已改变)")
                final_scripts_data[script_id]['remote_info']['sha'] = sha
                final_scripts_data[script_id]['remote_info']['last_commit_date'] = datetime.now().isoformat()
        else:
            # 这是新脚本
            print(f"✨ 新增脚本: {rel_path_posix}")
            new_id = generate_unique_id()
            while new_id in final_scripts_data: # 确保ID不重复
                new_id = generate_unique_id()
            final_scripts_data[new_id] = create_default_script_entry(rel_path_posix, sha)

    # -- 处理被删除的脚本 --
    existing_paths = set(path_to_id_map.keys())
    found_paths = {p.replace('\\', '/') for p in found_scripts.keys()}
    deleted_paths = existing_paths - found_paths
    
    for path in deleted_paths:
        script_id_to_delete = path_to_id_map[path]
        print(f"🗑️ 删除脚本: {path} (文件不存在)")
        del final_scripts_data[script_id_to_delete]

    # 5. 准备最终的JSON对象
    final_metadata = {
        "version": "2.0",
        "metadata_last_updated": datetime.now().isoformat(),
        "scripts": final_scripts_data
    }

    # 6. 写入文件
    try:
        with open(METADATA_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(final_metadata, f, indent=4, ensure_ascii=False)
        print(f"\n✅ 元数据已成功生成/更新到: {METADATA_FILE_PATH}")
    except Exception as e:
        print(f"\n❌ 写入文件时发生错误: {e}")
        
    print("="*60)


# --- 在Blender中运行 ---
if __name__ == "__main__":
    scan_and_generate_metadata()
