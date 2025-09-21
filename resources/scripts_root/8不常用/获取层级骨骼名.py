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
output_file = r"D:\BaiduSyncdisk\code\yxsjTools\脚本文件夹\产物\bone_hierarchy.txt"
with open(output_file, 'w') as file:
    for number, name in bone_dict.items():
        file.write(f"{number}:{name}\n")
