# script_id: 30f4bc49-1179-40a8-a176-3a7b7cfec379
import bpy

def enumerate_bones(bone, bone_dict, counter=[1]):
    """
    递归函数，遍历所选骨骼及其所有子骨骼并赋予序号。
    bone: 当前骨骼对象
    bone_dict: 存储骨骼序号和名称的字典
    counter: 列表，用作可变对象来在递归调用中持续计数
    """
    # 分配序号给当前骨骼，并将其添加到字典中
    bone_dict[counter[0]] = bone.name
    # 更新序号
    counter[0] += 1
    
    # 遍历当前骨骼的所有子骨骼
    for child_bone in bone.children:
        enumerate_bones(child_bone, bone_dict, counter)

# 存储骨骼序号和名称的字典
bone_dict = {}

# 获取当前选中的骨骼
selected_bones = bpy.context.selected_pose_bones

# 对每个选中的骨骼及其子骨骼执行层级写入操作
for bone in selected_bones:
    enumerate_bones(bone, bone_dict)

# 保存结果到文件
output_file = r"D:\BaiduSyncdisk\code\yxsjTools\脚本文件夹\产物\bone_hierarchy1.txt"
with open(output_file, 'w') as file:
    for number, name in bone_dict.items():
        file.write(f"{number}:{name}\n")
        









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

