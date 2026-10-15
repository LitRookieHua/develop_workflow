import os
import shutil


def remove_demconfigset_subcontainers(file_path):
    """
    备份ARXML文件，并删除DemConfigSet下的所有SUB-CONTAINERS内容

    参数:
        file_path: ARXML文件路径
    """
    # 1. 创建备份文件
    #backup_path = f"{file_path}.backup"
    #shutil.copy2(file_path, backup_path)
    #print(f"已创建备份文件: {backup_path}")

    # 2. 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 3. 查找DemConfigSet节点及其SUB-CONTAINERS
    in_dem_config_set = False
    in_sub_containers = False
    dem_indent_level = 0
    sub_containers_indent_level = 0
    result = []

    for line in lines:
        # 计算当前行的缩进级别（假设使用空格缩进）
        indent_level = len(line) - len(line.lstrip())

        # 检查是否进入DemConfigSet节点
        if '<SHORT-NAME>DemConfigSet</SHORT-NAME>' in line:
            in_dem_config_set = True
            # 记录DemConfigSet的缩进级别（上一级的缩进）
            dem_indent_level = indent_level - 2  # 假设SHORT-NAME比容器节点多缩进2个空格

        # 当在DemConfigSet节点中时，查找SUB-CONTAINERS
        if in_dem_config_set and not in_sub_containers:
            if '<SUB-CONTAINERS>' in line:
                in_sub_containers = True
                sub_containers_indent_level = indent_level
                result.append(line)  # 保留SUB-CONTAINERS标签
                continue

        # 在SUB-CONTAINERS内部时，跳过所有子节点直到遇到同级的闭合标签
        if in_sub_containers:
            # 检查是否到达SUB-CONTAINERS的闭合标签
            if '</SUB-CONTAINERS>' in line and indent_level == sub_containers_indent_level:
                in_sub_containers = False
                in_dem_config_set = False  # 退出DemConfigSet处理
                result.append(line)  # 保留闭合标签
            # 跳过SUB-CONTAINERS内部的所有内容
            continue

        # 其他行正常保留
        result.append(line)

    # 4. 写入修改后的内容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(result)

    print(f"已成功删除DemConfigSet下的所有SUB-CONTAINERS内容")


# 使用示例
if __name__ == "__main__":
    # 请替换为你的ARXML文件路径
    arxml_file_path = "J6B_Dem_EcucValues.arxml"

    # 检查文件是否存在
    if not os.path.exists(arxml_file_path):
        print(f"错误: 文件 '{arxml_file_path}' 不存在")
    else:
        remove_demconfigset_subcontainers(arxml_file_path)
