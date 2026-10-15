from lxml import etree
import os

from Create_DemDTCs import (
    xml_decl_pattern,
    extract_xml_declaration,
    preprocess_xml_tags,
    format_xml_indent,
)

AUTOSAR_NS = "http://autosar.org/schema/r4.0"


def clear_demconfigset_subcontainers(file_path) -> bool:
    """
    用XML解析器删除所有DemConfigSet容器SUB-CONTAINERS下的全部子容器

    与Delete_DemConfigSet.py功能相同，但不依赖缩进假设：
    通过XPath精确定位SHORT-NAME='DemConfigSet'的容器，清空其SUB-CONTAINERS
    （保留SUB-CONTAINERS开闭标签本身，供后续insert_*脚本填充）。

    参数:
        file_path: ARXML文件路径

    返回:
        True=成功写入, False=失败（文件未改动或解析失败）
    """
    # 1. 读取原始文件
    try:
        with open(file_path, 'rb') as f:
            raw_content = f.read()
    except FileNotFoundError:
        print(f"错误：原始文件不存在 → {file_path}")
        return False
    except Exception as e:
        print(f"读取文件失败：{str(e)}")
        return False

    # 2. 提取原始XML声明（复用Create_DemDTCs的序列化管线）
    original_xml_decl = extract_xml_declaration(raw_content)

    # 3. 解析ARXML（保留原始空白，先移除声明避免解析冲突）
    parser = etree.XMLParser(
        remove_blank_text=False,
        strip_cdata=False,
        resolve_entities=False,
        ns_clean=False
    )
    try:
        content_without_decl = xml_decl_pattern.sub(b'', raw_content, count=1)
        root = etree.fromstring(content_without_decl, parser)
        tree = etree.ElementTree(root)
    except etree.XMLSyntaxError as e:
        print(f"解析ARXML错误：{str(e)}")
        return False

    # 4. 定位所有DemConfigSet容器并清空其SUB-CONTAINERS
    ns_map = {"ar": AUTOSAR_NS}
    config_sets = root.findall(
        ".//ar:ECUC-CONTAINER-VALUE[ar:SHORT-NAME='DemConfigSet']", ns_map
    )
    if not config_sets:
        print("警告：未找到DemConfigSet容器，文件未改动")
        return False

    cleared_count = 0
    removed_count = 0
    for config_set in config_sets:
        sub_containers = config_set.find("ar:SUB-CONTAINERS", ns_map)
        if sub_containers is None:
            continue
        children = list(sub_containers)
        for child in children:
            sub_containers.remove(child)
        cleared_count += 1
        removed_count += len(children)

    if cleared_count == 0:
        print("警告：DemConfigSet下无SUB-CONTAINERS，文件未改动")
        return False

    # 5. 生成格式化的XML（与Create_DemDTCs相同管线）
    try:
        # 步骤1：生成原始XML字符串（禁用lxml自动格式化）
        xml_bytes = etree.tostring(
            tree,
            encoding="utf-8",
            pretty_print=False,
            xml_declaration=False,
            standalone=None
        )
        xml_str = xml_bytes.decode("utf-8")

        # 步骤2：预处理标签（让每个标签单独成行）
        xml_str = preprocess_xml_tags(xml_str)

        # 步骤3：按层级计算缩进（子元素2空格）
        xml_str = format_xml_indent(xml_str)

        # 步骤4：还原DOCTYPE（lxml默认不保留）
        doctype = ""
        if b"<!DOCTYPE" in raw_content:
            doctype_start = raw_content.find(b"<!DOCTYPE")
            doctype_end = raw_content.find(b">", doctype_start) + 1
            doctype = raw_content[doctype_start:doctype_end].decode("utf-8") + "\n"

        # 步骤5：组合最终内容并保存
        final_content = f"{original_xml_decl}\n{doctype}{xml_str}"
        with open(file_path, "w", encoding="utf-8", newline='\r\n') as f:
            f.write(final_content)

        print(f"已成功删除DemConfigSet下的所有SUB-CONTAINERS内容"
              f"（{cleared_count}个DemConfigSet，共移除{removed_count}个子容器）")
        return True
    except Exception as e:
        print(f"保存文件失败：{str(e)}")
        return False


if __name__ == "__main__":
    # 请替换为你的ARXML文件路径
    arxml_file_path = "J6B_Dem_EcucValues.arxml"

    # 检查文件是否存在
    if not os.path.exists(arxml_file_path):
        print(f"错误: 文件 '{arxml_file_path}' 不存在")
    else:
        clear_demconfigset_subcontainers(arxml_file_path)
