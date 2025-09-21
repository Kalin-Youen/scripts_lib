import bpy
import difflib

def rename_bones_to_match(armature1, armature2):
    """
    将第二套骨骼的名称改为与第一套骨骼相匹配。
    
    :param armature1: 第一套骨骼的名称或对象。
    :param armature2: 第二套骨骼的名称或对象。
    """
    
    # 获取骨骼对象
    if isinstance(armature1, str):
        armature1 = bpy.data.objects[armature1]
    if isinstance(armature2, str):
        armature2 = bpy.data.objects[armature2]
    
    # 确保两个对象都是骨骼
    if armature1.type != 'ARMATURE' or armature2.type != 'ARMATURE':
        print("Both objects need to be armatures.")
        return
    
    # 获取两套骨骼的名字列表
    bones1_names = [bone.name for bone in armature1.data.bones]
    bones2_names = [bone.name for bone in armature2.data.bones]
    
    # 为armature2中的每个骨骼找到最匹配的骨骼名称并重命名
    for bone2_name in bones2_names:
        # 使用difflib找到最相似的骨骼名称
        best_match = difflib.get_close_matches(bone2_name, bones1_names, n=1, cutoff=0.1)
        if best_match:
            # 如果找到匹配，重命名骨骼
            armature2.data.bones[bone2_name].name = best_match[0]
        else:
            print(f"No close match found for {bone2_name}")

# 使用示例
# 请确保将'Armature1'和'Armature2'替换为实际的骨骼对象名称
rename_bones_to_match('rig', 'A0011')
