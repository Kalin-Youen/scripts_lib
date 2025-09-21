import bpy


def load_bone_names_from_file(file_path):
    """
    从指定的文件路径加载骨骼名称。
    
    file_path: 文件的路径
    返回: 一个字典，键为骨骼的序号，值为骨骼的名称
    """
    bone_names = {}
    with open(file_path, 'r') as file:
        for line in file:
            number, name = line.strip().split(':')
            bone_names[int(number)] = name
    return bone_names

def swap_bone_names(bones_dict1, bones_dict2, armature):
    """
    根据两个字典中的骨骼名称互换骨骼名称。
    
    bones_dict1: 第一个文件中骨骼的字典
    bones_dict2: 第二个文件中骨骼的字典
    armature: 目标骨架对象
    """
    for bone_id, bone_name in bones_dict1.items():
        if bone_id in bones_dict2:
            # 确保骨骼存在于骨架中
            if bone_name in armature.data.bones:
                # 互换骨骼名称
                temp_name = armature.data.bones[bone_name].name
                armature.data.bones[bone_name].name = bones_dict2[bone_id]
                if temp_name in bones_dict2.values():
                    armature.data.bones[temp_name].name = temp_name
                    




def match_current_bones_with_file(armature, bone_names_file):
    match_count = 0
    for bone in armature.data.bones:
        if bone.name in bone_names_file.values():
            match_count += 1
    return match_count

# 假设已有函数 load_bone_names_from_file 和 swap_bone_names 如之前定义

# 加载骨骼名称
bone_names_file1 = load_bone_names_from_file(r"D:\BaiduSyncdisk\code\yxsjTools\脚本文件夹\产物\bone_hierarchy.txt")
bone_names_file2 = load_bone_names_from_file(r"D:\BaiduSyncdisk\code\yxsjTools\脚本文件夹\产物\bone_hierarchy1.txt")

# 获取当前选中的骨架
armature = bpy.context.object

# 确定当前骨骼名称与哪个文件匹配
match_count_file1 = match_current_bones_with_file(armature, bone_names_file1)
match_count_file2 = match_current_bones_with_file(armature, bone_names_file2)

# 根据匹配度决定互换方向
if match_count_file1 > match_count_file2:
    # 当前骨骼名称更接近文件1，故将骨骼名称互换到文件2的状态
    swap_bone_names(bone_names_file1, bone_names_file2, armature)
else:
    # 当前骨骼名称更接近文件2，故将骨骼名称互换到文件1的状态
    swap_bone_names(bone_names_file2, bone_names_file1, armature)
