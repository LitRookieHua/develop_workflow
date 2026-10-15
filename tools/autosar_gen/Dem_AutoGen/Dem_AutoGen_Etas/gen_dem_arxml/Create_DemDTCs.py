from lxml import etree
import os
import re




# 全局XML声明正则（提取原始声明，确保格式一致）
xml_decl_pattern = re.compile(
    rb'^<\?xml\s+version=["\'][^"\']*["\']\s+encoding=["\'][^"\']*["\']\s*(standalone=["\'][^"\']*["\'])?\s*\?>',
    re.MULTILINE
)


def uds_to_decimal(dtc_str: str) -> int:
    """
    从DemDTC字符串中提取7位UDS，转换后返回十进制数字
    步骤：提取7位UDS → 前缀映射转换 → 十六进制转十进制
    """
    # 前缀映射表
    prefix_map = {'U0': 'C', 'U1': 'D', 'U2': 'E', 'U3': 'F', 'P0': '0', 'P1': '1', 'P2': '2', 'P3': '3',
                  'C0': '4', 'C1': '5', 'C2': '6', 'C3': '7', 'B0': '8', 'B1': '9', 'B2': 'A', 'B3': 'B'}

    # 1. 提取7位UDS
    parts = dtc_str.split("_")
    if parts[0] != "DemDTC":
        raise ValueError(f"格式错误：{dtc_str} 需符合 'DemDTC_<7位UDS>_...'")
    uds = parts[1]
    if len(uds) != 7:
        raise ValueError(f"UDS需7位，实际为{len(uds)}位：{uds}")

    # 2. 转换UDS格式
    prefix = uds[:2]
    if prefix not in prefix_map:
        raise ValueError(f"无效前缀：{prefix}")
    transformed = prefix_map[prefix] + uds[2:]

    # 3. 转为十进制
    return int(transformed, 16)


def extract_xml_declaration(raw_content: bytes) -> str:
    """提取原始XML声明，避免lxml自动生成导致格式差异"""
    match = xml_decl_pattern.search(raw_content)
    return match.group(0).decode('utf-8', errors='replace') if match else '<?xml version="1.0" encoding="UTF-8"?>'


def preprocess_xml_tags(xml_str: str) -> str:
    """预处理：让每个XML标签单独成行（解决标签拥挤导致的缩进混乱）"""
    # 1. 将紧凑的标签分割（如"><"改为">\n<"）
    xml_str = re.sub(r'(?<=>)(?=<)', '\n', xml_str)
    # 2. 处理自闭合标签（如<SUB-CONTAINERS/> → <SUB-CONTAINERS>\n</SUB-CONTAINERS>）
    xml_str = re.sub(r'<([A-Za-z_][\w.-]*:[A-Za-z_][\w.-]*)([^>]*)/>', r'<\1\2>\n</\1>', xml_str)
    return xml_str


def format_xml_indent(xml_content: str, indent: str = "  ") -> str:
    """
    精确计算缩进层级：
    - 已将默认缩进从4个空格改为2个空格
    - 开始标签（如<ECUC-CONTAINER-VALUE>）后层级+1
    - 结束标签（如</ECUC-CONTAINER-VALUE>）前层级-1
    - 文本内容（如<VALUE>0</VALUE>）按当前层级缩进
    """
    lines = xml_content.split('\n')
    formatted_lines = []
    current_level = 0  # 当前缩进层级（初始为0）

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

    # 最后用换行符连接，确保格式统一
    return '\n'.join(formatted_lines)


def create_dem_dtc_container(parent_element, autosar_namespace: str, DemUdsDTC):
    """
    创建DemDTC容器，生成与示例格式一致的XML结构
    """
    # 根容器：ECUC-CONTAINER-VALUE（带S属性）
    dem_dtc_root = etree.SubElement(
        parent_element,
        etree.QName(autosar_namespace, "ECUC-CONTAINER-VALUE")
    )
    dem_dtc_root.set("S", "USER_GENERATED")

    # 1. SHORT-NAME（根容器的子元素）
    short_name = etree.SubElement(dem_dtc_root, etree.QName(autosar_namespace, "SHORT-NAME"))
    short_name.text = DemUdsDTC

    # 2. DEFINITION-REF（根容器的子元素）
    def_ref = etree.SubElement(dem_dtc_root, etree.QName(autosar_namespace, "DEFINITION-REF"))
    def_ref.set("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
    def_ref.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTC"

    # 3. PARAMETER-VALUES（根容器的子元素）
    param_values = etree.SubElement(dem_dtc_root, etree.QName(autosar_namespace, "PARAMETER-VALUES"))

    # 3.1 参数1：DemDtcValue（数值参数）
    num_param1 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_param1_def = etree.SubElement(num_param1, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_param1_def.set("DEST", "ECUC-INTEGER-PARAM-DEF")
    num_param1_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTC/DemDtcValue"
    num_param1_val = etree.SubElement(num_param1, etree.QName(autosar_namespace, "VALUE"))
    dec_val = uds_to_decimal(DemUdsDTC)
    num_param1_val.text = str(dec_val)

    # 3.2 参数2：DemDTCSeverity（文本参数）
    text_param1 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-TEXTUAL-PARAM-VALUE"))
    text_param1_def = etree.SubElement(text_param1, etree.QName(autosar_namespace, "DEFINITION-REF"))
    text_param1_def.set("DEST", "ECUC-ENUMERATION-PARAM-DEF")
    text_param1_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTC/DemDTCSeverity"
    text_param1_val = etree.SubElement(text_param1, etree.QName(autosar_namespace, "VALUE"))
    text_param1_val.text = "DEM_SEVERITY_NO_SEVERITY"

    # 3.3 参数3：DemNvStorageStrategy（文本参数）
    text_param2 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-TEXTUAL-PARAM-VALUE"))
    text_param2_def = etree.SubElement(text_param2, etree.QName(autosar_namespace, "DEFINITION-REF"))
    text_param2_def.set("DEST", "ECUC-ENUMERATION-PARAM-DEF")
    text_param2_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTC/DemNvStorageStrategy"
    text_param2_val = etree.SubElement(text_param2, etree.QName(autosar_namespace, "VALUE"))
    text_param2_val.text = "DURING_SHUTDOWN"

    # 4. REFERENCE-VALUES（根容器的子元素）
    ref_values = etree.SubElement(dem_dtc_root, etree.QName(autosar_namespace, "REFERENCE-VALUES"))

    # 4.1 引用1：DemDTCAttributesRef
    ref1 = etree.SubElement(ref_values, etree.QName(autosar_namespace, "ECUC-REFERENCE-VALUE"))
    ref1_def = etree.SubElement(ref1, etree.QName(autosar_namespace, "DEFINITION-REF"))
    ref1_def.set("DEST", "ECUC-REFERENCE-DEF")
    ref1_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTC/DemDTCAttributesRef"
    ref1_val = etree.SubElement(ref1, etree.QName(autosar_namespace, "VALUE-REF"))
    ref1_val.set("DEST", "ECUC-CONTAINER-VALUE")
    ref1_val.text = "/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemConfigSet/Attribute_" + DemUdsDTC

    return dem_dtc_root


def insert_dem_dtc_to_arxml(
        input_arxml: str,
        output_arxml: str,
        parent_xpath: str,
        dem_data
) -> bool:
    """主函数：插入DemEvent容器并确保缩进正确"""
    # 1. 读取原始文件
    try:
        with open(input_arxml, 'rb') as f:
            raw_content = f.read()
    except FileNotFoundError:
        print(f"错误：原始文件不存在 → {input_arxml}")
        return False
    except Exception as e:
        print(f"读取文件失败：{str(e)}")
        return False

    # 2. 提取原始XML声明
    original_xml_decl = extract_xml_declaration(raw_content)

    # 3. 配置解析器（保留原始空白，避免破坏格式参考）
    parser = etree.XMLParser(
        remove_blank_text=False,  # 关键：不删除空白，让lxml保留原始缩进结构
        strip_cdata=False,
        resolve_entities=False,
        ns_clean=False
    )

    # 4. 解析ARXML（先移除声明，避免解析冲突）
    try:
        content_without_decl = xml_decl_pattern.sub(b'', raw_content, count=1)
        root = etree.fromstring(content_without_decl, parser)
        tree = etree.ElementTree(root)
    except etree.XMLSyntaxError as e:
        print(f"解析ARXML错误：{str(e)}")
        return False

    # 5. 定位父容器（如DemConfigSet的SUB-CONTAINERS）
    autosar_ns = "http://autosar.org/schema/r4.0"  # 若为R4.2，改为对应命名空间
    ns_map = {"ar": autosar_ns}
    parent_container = root.find(parent_xpath, ns_map)

    if parent_container is None:
        print(f"错误：未找到父容器，请检查XPath → {parent_xpath}")
        print("正确XPath示例：")
        print("  1. DemConfigSet直接子容器：.//ar:ECUC-CONTAINER-VALUE[ar:SHORT-NAME='DemConfigSet']/ar:SUB-CONTAINERS")
        print(
            "  2. DemConfigSet下的DemEvents：.//ar:ECUC-CONTAINER-VALUE[ar:SHORT-NAME='DemConfigSet']/ar:SUB-CONTAINERS/ar:ECUC-CONTAINER-VALUE[ar:SHORT-NAME='DemEvents']/ar:SUB-CONTAINERS")
        return False

    # 定义需要排除的字符串（可根据实际数据扩展，如"NA"、"N/A"等）
    exclude_values = {"N.A", "n.a", "NA", "na", "N/A", "n/a"}
    # 过滤列表：保留所有不在排除集合中的元素
    filtered_dem_uds_dtc = [
        item for item in dem_data.DemUdsDTC
        if str(item).upper() not in {v.upper() for v in exclude_values}
    ]

    # 利用字典fromkeys()去重并保留顺序（键为列表元素，值默认None）
    unique_DemUdsDTC = list(dict.fromkeys(filtered_dem_uds_dtc))

    for i in range(len(unique_DemUdsDTC)):
        # 6. 创建并插入DemEvent容器
        try:
            create_dem_dtc_container(parent_container, autosar_ns, unique_DemUdsDTC[i])
        except Exception as e:
            print(f"创建容器失败：{str(e)}")
            return False

    # 7. 生成格式化的XML（核心：解决缩进问题）
    try:
        # 步骤1：生成原始XML字符串（禁用lxml自动格式化）
        xml_bytes = etree.tostring(
            tree,
            encoding="utf-8",
            pretty_print=False,  # 关闭自动格式化，避免干扰自定义缩进
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
        with open(output_arxml, "w", encoding="utf-8", newline='\r\n') as f:
            f.write(final_content)

        print(f"成功！生成Dem DTCs Container!")
        return True
    except Exception as e:
        print(f"保存文件失败：{str(e)}")
        return False

