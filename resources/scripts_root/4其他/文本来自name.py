# 文本来自name
# 文本来自name
# 8脚本
import bpy
import re

# 获取当前选中的对象
selected_objects = bpy.context.selected_objects

# 遍历选中的对象
for selected_object in selected_objects:
    # 检查对象类型是否为文本
    if selected_object.type == 'FONT':
        # 获取文本对象的名字
        text_name = selected_object.name
        
        # 去掉字符串中的'.0'及其后面的字符
        text_name = re.sub(r'\.0.*$', '', text_name)
        
        # 设置文本内容为处理后的名字
        selected_object.data.body = text_name
