"""公用 arxml 序列化管线 (移植自 Dem_AutoGen_Etas/gen_dem_arxml/Create_DemDTCs.py, 含自闭合标签正则修复)."""

import re
from lxml import etree

AUTOSAR_NS = "http://autosar.org/schema/r4.0"

xml_decl_pattern = re.compile(
    rb'^<\?xml\s+version=["\'][^"\']*["\']\s+encoding=["\'][^"\']*["\']\s*(standalone=["\'][^"\']*["\'])?\s*\?>',
    re.MULTILINE
)


def ns_tag(local: str) -> str:
    """默认命名空间下的完整标签名 (Dcm arxml 无 ar: 前缀)."""
    return "{%s}%s" % (AUTOSAR_NS, local)


def parse_arxml(file_path):
    """读取并解析 arxml, 返回 (root, raw_content, original_xml_decl) 或 None."""
    try:
        with open(file_path, 'rb') as f:
            raw_content = f.read()
    except FileNotFoundError:
        print("错误：原始文件不存在 → %s" % file_path)
        return None
    except Exception as e:
        print("读取文件失败：%s" % str(e))
        return None

    original_xml_decl = extract_xml_declaration(raw_content)

    parser = etree.XMLParser(
        remove_blank_text=False,
        strip_cdata=False,
        resolve_entities=False,
        ns_clean=False
    )
    try:
        content_without_decl = xml_decl_pattern.sub(b'', raw_content, count=1)
        root = etree.fromstring(content_without_decl, parser)
    except etree.XMLSyntaxError as e:
        print("解析ARXML错误：%s" % str(e))
        return None
    return root, raw_content, original_xml_decl


def extract_xml_declaration(raw_content: bytes) -> str:
    """提取原始XML声明，避免lxml自动生成导致格式差异"""
    match = xml_decl_pattern.search(raw_content)
    return match.group(0).decode('utf-8', errors='replace') if match else '<?xml version="1.0" encoding="UTF-8"?>'


def preprocess_xml_tags(xml_str: str) -> str:
    """预处理：让每个XML标签单独成行（解决标签拥挤导致的缩进混乱）"""
    # 1. 将紧凑的标签分割（如"><"改为">\n<"）
    xml_str = re.sub(r'(?<=>)(?=<)', '\n', xml_str)
    # 2. 处理自闭合标签（含连字符标签名与属性, 如<ar:SUB-CONTAINERS/> → <ar:SUB-CONTAINERS>\n</ar:SUB-CONTAINERS>）
    xml_str = re.sub(r'<([A-Za-z_][\w.-]*:[A-Za-z_][\w.-]*)([^>]*)/>', r'<\1\2>\n</\1>', xml_str)
    return xml_str


def format_xml_indent(xml_content: str, indent: str = "  ") -> str:
    """
    精确计算缩进层级（2空格缩进）：
    - 开始标签（如<ECUC-CONTAINER-VALUE>）后层级+1
    - 结束标签（如</ECUC-CONTAINER-VALUE>）前层级-1
    - 文本内容（如<VALUE>0</VALUE>）按当前层级缩进
    """
    lines = xml_content.split('\n')
    formatted_lines = []
    current_level = 0

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:  # 跳过空行（避免多余空行）
            continue

        # 情况1：结束标签（如</PARAMETER-VALUES>）→ 先减层级再缩进
        if stripped_line.startswith('</'):
            current_level -= 1
            formatted_lines.append(f"{indent * current_level}{stripped_line}")

        # 情况2：单行标签（如<SHORT-NAME>DemEvent</SHORT-NAME>）→ 当前层级缩进，不改变层级
        elif '<' in stripped_line and '</' in stripped_line and stripped_line.endswith('>'):
            formatted_lines.append(f"{indent * current_level}{stripped_line}")

        # 情况3：开始标签（如<PARAMETER-VALUES>）→ 当前层级缩进，后增层级
        elif stripped_line.startswith('<') and not stripped_line.startswith('</'):
            formatted_lines.append(f"{indent * current_level}{stripped_line}")
            current_level += 1

        # 情况4：纯文本（如<VALUE>后的"0"）→ 当前层级缩进
        else:
            formatted_lines.append(f"{indent * current_level}{stripped_line}")

    return '\n'.join(formatted_lines)


def write_arxml(tree, output_path, raw_content: bytes, original_xml_decl: str) -> bool:
    """序列化树并写出 (2空格缩进、还原DOCTYPE、CRLF)."""
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
        with open(output_path, "w", encoding="utf-8", newline='\r\n') as f:
            f.write(final_content)
        return True
    except Exception as e:
        print("保存文件失败：%s" % str(e))
        return False
