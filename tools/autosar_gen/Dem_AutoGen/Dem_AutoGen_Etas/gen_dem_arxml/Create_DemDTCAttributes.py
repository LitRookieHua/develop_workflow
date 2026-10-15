from lxml import etree
import os
import re

# 全局XML声明正则（提取原始声明，确保格式一致）
xml_decl_pattern = re.compile(
    rb'^<\?xml\s+version=["\'][^"\']*["\']\s+encoding=["\'][^"\']*["\']\s*(standalone=["\'][^"\']*["\'])?\s*\?>',
    re.MULTILINE
)


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


def create_dem_dtc_attributes_container(parent_element, autosar_namespace: str, DemUdsDTC, DTC_Priority, Aging, OprationCycle, SnapshotType):
    """
    创建DemDTCAttributes容器，生成与示例格式完全一致的XML结构
    对应SHORT-NAME：DemDTCAttributes_FLS_Sensl_OpenLoad
    """
    # 1. 根容器：ECUC-CONTAINER-VALUE（带S="USER_GENERATED"属性）
    dtc_attr_root = etree.SubElement(
        parent_element,
        etree.QName(autosar_namespace, "ECUC-CONTAINER-VALUE")
    )
    dtc_attr_root.set("S", "USER_GENERATED")

    # 1.1 SHORT-NAME（根容器子元素）
    short_name = etree.SubElement(dtc_attr_root, etree.QName(autosar_namespace, "SHORT-NAME"))
    short_name.text = "Attribute_" + DemUdsDTC

    # 1.2 DEFINITION-REF
    def_ref = etree.SubElement(dtc_attr_root, etree.QName(autosar_namespace, "DEFINITION-REF"))
    def_ref.set("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
    def_ref.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTCAttributes"

    # 2. PARAMETER-VALUES
    param_values = etree.SubElement(dtc_attr_root, etree.QName(autosar_namespace, "PARAMETER-VALUES"))

    # 2.1 参数1：DemAgingAllowed（带S属性）
    num_param1 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_param1.set("S", "USER_GENERATED")
    num_param1_def = etree.SubElement(num_param1, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_param1_def.set("DEST", "ECUC-BOOLEAN-PARAM-DEF")
    num_param1_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTCAttributes/DemAgingAllowed"
    num_param1_val = etree.SubElement(num_param1, etree.QName(autosar_namespace, "VALUE"))
    num_param1_val.text = "true"

    # 2.2 参数2：DemDTCPriority（无S属性）
    num_param2 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_param2_def = etree.SubElement(num_param2, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_param2_def.set("DEST", "ECUC-INTEGER-PARAM-DEF")
    num_param2_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTCAttributes/DemDTCPriority"
    num_param2_val = etree.SubElement(num_param2, etree.QName(autosar_namespace, "VALUE"))
    num_param2_val.text = str(DTC_Priority)

    # 2.3 参数3：DemAgingCycleCounterThreshold（无S属性）
    num_param3 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_param3_def = etree.SubElement(num_param3, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_param3_def.set("DEST", "ECUC-INTEGER-PARAM-DEF")
    num_param3_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTCAttributes/DemAgingCycleCounterThreshold"
    num_param3_val = etree.SubElement(num_param3, etree.QName(autosar_namespace, "VALUE"))
    num_param3_val.text = str(Aging)

    # 2.4 参数4：DemImmediateNvStorage（无S属性）
    num_param4 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_param4_def = etree.SubElement(num_param4, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_param4_def.set("DEST", "ECUC-BOOLEAN-PARAM-DEF")
    num_param4_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTCAttributes/DemImmediateNvStorage"
    num_param4_val = etree.SubElement(num_param4, etree.QName(autosar_namespace, "VALUE"))
    num_param4_val.text = "false"

    # 2.5 参数5：DemMaxNumberFreezeFrameRecords（无S属性）
    num_param5 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_param5_def = etree.SubElement(num_param5, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_param5_def.set("DEST", "ECUC-INTEGER-PARAM-DEF")
    num_param5_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTCAttributes/DemMaxNumberFreezeFrameRecords"
    num_param5_val = etree.SubElement(num_param5, etree.QName(autosar_namespace, "VALUE"))
    num_param5_val.text = "2"

    # 3. REFERENCE-VALUES
    ref_values = etree.SubElement(dtc_attr_root, etree.QName(autosar_namespace, "REFERENCE-VALUES"))

    # 3.1 引用1：DemMemoryDestinationRef
    ref1 = etree.SubElement(ref_values, etree.QName(autosar_namespace, "ECUC-REFERENCE-VALUE"))
    ref1_def = etree.SubElement(ref1, etree.QName(autosar_namespace, "DEFINITION-REF"))
    ref1_def.set("DEST", "ECUC-CHOICE-REFERENCE-DEF")
    ref1_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTCAttributes/DemMemoryDestinationRef"
    ref1_val = etree.SubElement(ref1, etree.QName(autosar_namespace, "VALUE-REF"))
    ref1_val.set("DEST", "ECUC-CONTAINER-VALUE")
    ref1_val.text = "/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemGeneral/DemEventMemorySet/DemPrimaryMemory"

    # 3.2 引用2：DemAgingCycleRef
    ref2 = etree.SubElement(ref_values, etree.QName(autosar_namespace, "ECUC-REFERENCE-VALUE"))
    ref2_def = etree.SubElement(ref2, etree.QName(autosar_namespace, "DEFINITION-REF"))
    ref2_def.set("DEST", "ECUC-REFERENCE-DEF")
    ref2_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTCAttributes/DemAgingCycleRef"
    ref2_val = etree.SubElement(ref2, etree.QName(autosar_namespace, "VALUE-REF"))
    ref2_val.set("DEST", "ECUC-CONTAINER-VALUE")
    ref2_val.text = f"/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemGeneral/{OprationCycle}"

    # 3.3 引用3：DemExtendedDataClassRef
    ref3 = etree.SubElement(ref_values, etree.QName(autosar_namespace, "ECUC-REFERENCE-VALUE"))
    ref3_def = etree.SubElement(ref3, etree.QName(autosar_namespace, "DEFINITION-REF"))
    ref3_def.set("DEST", "ECUC-REFERENCE-DEF")
    ref3_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTCAttributes/DemExtendedDataClassRef"
    ref3_val = etree.SubElement(ref3, etree.QName(autosar_namespace, "VALUE-REF"))
    ref3_val.set("DEST", "ECUC-CONTAINER-VALUE")
    ref3_val.text = "/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemGeneral/ExtendedDataClass_DTC_Properties"

    # 3.4 引用4：DemFreezeFrameClassRef
    ref4 = etree.SubElement(ref_values, etree.QName(autosar_namespace, "ECUC-REFERENCE-VALUE"))
    ref4_def = etree.SubElement(ref4, etree.QName(autosar_namespace, "DEFINITION-REF"))
    ref4_def.set("DEST", "ECUC-REFERENCE-DEF")
    ref4_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTCAttributes/DemFreezeFrameClassRef"
    ref4_val = etree.SubElement(ref4, etree.QName(autosar_namespace, "VALUE-REF"))
    ref4_val.set("DEST", "ECUC-CONTAINER-VALUE")
    if SnapshotType == "B":
        ref4_val.text = "/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemGeneral/FreezeFrame_DTC_DidSet_TypeB"
    else:
        ref4_val.text = "/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemGeneral/FreezeFrame_DTC_DidSet_TypeA"

    # 3.5 引用5：DemFreezeFrameRecNumClassRef
    ref5 = etree.SubElement(ref_values, etree.QName(autosar_namespace, "ECUC-REFERENCE-VALUE"))
    ref5_def = etree.SubElement(ref5, etree.QName(autosar_namespace, "DEFINITION-REF"))
    ref5_def.set("DEST", "ECUC-REFERENCE-DEF")
    ref5_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTCAttributes/DemFreezeFrameRecNumClassRef"
    ref5_val = etree.SubElement(ref5, etree.QName(autosar_namespace, "VALUE-REF"))
    ref5_val.set("DEST", "ECUC-CONTAINER-VALUE")
    ref5_val.text = "/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemGeneral/DTC_Properties_FFRecNumClass"

    return dtc_attr_root


def insert_dem_dtc_attributes_to_arxml(
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
    # 预处理排除集合为大写，减少重复计算
    exclude_set = {v.upper() for v in exclude_values}

    # 过滤列表：同时保留DTC和对应的DEM_Index，过滤排除值
    filtered_pairs = [
        (dtc, idx) for dtc, idx in zip(dem_data.DemUdsDTC, dem_data.DEM_Index)
        if str(dtc).upper() not in exclude_set
    ]

    # 去重：保留DTC首次出现的配对（保持顺序），生成unique列表
    seen_dtc = set()
    unique_DemUdsDTC = []
    unique_DemUdsDTCIndex = []
    for dtc, idx in filtered_pairs:
        if dtc not in seen_dtc:
            seen_dtc.add(dtc)
            unique_DemUdsDTC.append(dtc)
            unique_DemUdsDTCIndex.append(idx)

    # 1. 空集合：用于记录已处理过的字符串
    processed = set()
    i = 0
    # 2. 循环遍历原列表，只处理未重复的项
    for dtc in unique_DemUdsDTC:
        # 关键判断：仅当字符串未处理过时，才执行逻辑
        if dtc not in processed:
            # 6. 创建并插入DemEvent容器
            try:
                idx = unique_DemUdsDTCIndex[i] - 1
                create_dem_dtc_attributes_container(parent_container, autosar_ns, dtc, dem_data.DTC_Priority[idx], dem_data.Aging[idx], dem_data.OprationCycle[idx],dem_data.SnapshotType[idx])
                i += 1
            except Exception as e:
                print(f"创建容器失败：{str(e)}")
                return False

            # 处理完后，将该字符串加入集合，标记为“已处理”
            processed.add(dtc)



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

        print(f"成功！生成Dem DTC Attributes Container!")
        return True
    except Exception as e:
        print(f"保存文件失败：{str(e)}")
        return False


