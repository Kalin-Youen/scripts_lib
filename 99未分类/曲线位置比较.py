import bpy

def select_curves(axis='z', comparison='greater'):
    obj = bpy.context.active_object

    # 检查当前活动对象是否为曲线
    if obj.type != 'CURVE':
        print("当前活动对象不是曲线。")
        return

    # 检查是否处于编辑模式
    if obj.mode != 'EDIT':
        print("请切换到编辑模式。")
        return

    # 取消选中所有控制点
    bpy.ops.curve.select_all(action='DESELECT')

    # 访问曲线数据
    curve = obj.data

    for spline in curve.splines:
        # 确保spline有多个控制点
        if len(spline.bezier_points) > 1:
            start_point = spline.bezier_points[0]
            end_point = spline.bezier_points[-1]

            start_coord = getattr(start_point.co, axis)
            end_coord = getattr(end_point.co, axis)

            # 根据指定的比较方式选择曲线
            if (comparison == 'greater' and start_coord > end_coord) or \
               (comparison == 'less' and start_coord < end_coord):
                for point in spline.bezier_points:
                    point.select_control_point = True

# 使用示例：
# select_curves(axis='z', comparison='greater')
# select_curves(axis='x', comparison='less')

# 运行函数并进行所需的比较
select_curves(axis='z', comparison='greater')
