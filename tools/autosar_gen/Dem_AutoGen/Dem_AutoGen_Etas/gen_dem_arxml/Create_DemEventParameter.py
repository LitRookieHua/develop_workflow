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


def create_dem_event_container(parent_element, autosar_namespace: str, DEM_Index, EventName, EventKind, DtcRef, OprationCycle, ECG, Recoverable, DebounceAlgorithm):
    """
    创建DemEvent容器
    """
    # 1. 根容器：ECUC-CONTAINER-VALUE（带S属性）
    dem_event_root = etree.SubElement(
        parent_element,
        etree.QName(autosar_namespace, "ECUC-CONTAINER-VALUE")
    )
    dem_event_root.set("S", "USER_GENERATED")

    # 1.1 SHORT-NAME（根容器的子元素，层级+1）
    short_name = etree.SubElement(dem_event_root, etree.QName(autosar_namespace, "SHORT-NAME"))
    short_name.text = EventName

    # 1.2 DEFINITION-REF（根容器的子元素，层级+1）
    def_ref = etree.SubElement(dem_event_root, etree.QName(autosar_namespace, "DEFINITION-REF"))
    def_ref.set("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
    def_ref.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter"

    # 2. PARAMETER-VALUES（根容器的子元素，层级+1）
    param_values = etree.SubElement(dem_event_root, etree.QName(autosar_namespace, "PARAMETER-VALUES"))

    # 2.1 参数1：DemRbIgnorePFCCycleQualificationForPDTCRemoval（层级+2）
    num_param1 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_param1.set("S", "USER_GENERATED")
    num_param1_def = etree.SubElement(num_param1, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_param1_def.set("DEST", "ECUC-BOOLEAN-PARAM-DEF")
    num_param1_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemRbIgnorePFCCycleQualificationForPDTCRemoval"
    num_param1_val = etree.SubElement(num_param1, etree.QName(autosar_namespace, "VALUE"))
    num_param1_val.text = "0"

    # 2.2 参数2：DemCausalityDelayTime（层级+2）
    num_param2 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_param2.set("S", "USER_GENERATED")
    num_param2_def = etree.SubElement(num_param2, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_param2_def.set("DEST", "ECUC-FLOAT-PARAM-DEF")
    num_param2_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemCausalityDelayTime"
    num_param2_val = etree.SubElement(num_param2, etree.QName(autosar_namespace, "VALUE"))
    num_param2_val.text = "0.0"

    # 2.3 参数3：DemEventAvailableInVariant（层级+2）
    num_param3 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_param3.set("S", "USER_GENERATED")
    num_param3_def = etree.SubElement(num_param3, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_param3_def.set("DEST", "ECUC-BOOLEAN-PARAM-DEF")
    num_param3_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemEventAvailableInVariant"
    num_param3_val = etree.SubElement(num_param3, etree.QName(autosar_namespace, "VALUE"))
    num_param3_val.text = "1"

    # 2.4 参数4：DemEventConfirmationThreshold（层级+2）
    num_param4 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_param4.set("S", "USER_GENERATED")
    num_param4_def = etree.SubElement(num_param4, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_param4_def.set("DEST", "ECUC-INTEGER-PARAM-DEF")
    num_param4_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemEventConfirmationThreshold"
    num_param4_val = etree.SubElement(num_param4, etree.QName(autosar_namespace, "VALUE"))
    num_param4_val.text = "1"

    # 2.5 参数5：DemEventFailureCycleCounterThresholdAdaptable（层级+2）
    num_param5 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_param5.set("S", "USER_GENERATED")
    num_param5_def = etree.SubElement(num_param5, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_param5_def.set("DEST", "ECUC-BOOLEAN-PARAM-DEF")
    num_param5_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemEventFailureCycleCounterThresholdAdaptable"
    num_param5_val = etree.SubElement(num_param5, etree.QName(autosar_namespace, "VALUE"))
    num_param5_val.text = "true"

    # 2.6 参数6：DemEventRecoverableInSameOperationCycle（层级+2）
    num_param6 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_param6.set("S", "USER_GENERATED")
    num_param6_def = etree.SubElement(num_param6, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_param6_def.set("DEST", "ECUC-BOOLEAN-PARAM-DEF")
    num_param6_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemEventRecoverableInSameOperationCycle"
    num_param6_val = etree.SubElement(num_param6, etree.QName(autosar_namespace, "VALUE"))
    if Recoverable == True:
        num_param6_val.text = "1"
    else:
        num_param6_val.text = "0"

    # 2.7 参数7：DemFFPrestorageSupported（层级+2）
    num_param7 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_param7.set("S", "USER_GENERATED")
    num_param7_def = etree.SubElement(num_param7, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_param7_def.set("DEST", "ECUC-BOOLEAN-PARAM-DEF")
    num_param7_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemFFPrestorageSupported"
    num_param7_val = etree.SubElement(num_param7, etree.QName(autosar_namespace, "VALUE"))
    num_param7_val.text = "0"

    # 2.8 参数8：DemReportBehavior（文本参数，层级+2）
    text_param1 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-TEXTUAL-PARAM-VALUE"))
    text_param1.set("S", "USER_GENERATED")
    text_param1_def = etree.SubElement(text_param1, etree.QName(autosar_namespace, "DEFINITION-REF"))
    text_param1_def.set("DEST", "ECUC-ENUMERATION-PARAM-DEF")
    text_param1_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemReportBehavior"
    text_param1_val = etree.SubElement(text_param1, etree.QName(autosar_namespace, "VALUE"))
    text_param1_val.text = "REPORT_AFTER_INIT"

    # 2.9 参数9：DemEventAvailable（层级+2）
    num_param8 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_param8_def = etree.SubElement(num_param8, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_param8_def.set("DEST", "ECUC-BOOLEAN-PARAM-DEF")
    num_param8_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemEventAvailable"
    num_param8_val = etree.SubElement(num_param8, etree.QName(autosar_namespace, "VALUE"))
    num_param8_val.text = "true"

    # 2.10 参数10：DemEventKind（文本参数，层级+2）
    text_param2 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-TEXTUAL-PARAM-VALUE"))
    text_param2_def = etree.SubElement(text_param2, etree.QName(autosar_namespace, "DEFINITION-REF"))
    text_param2_def.set("DEST", "ECUC-ENUMERATION-PARAM-DEF")
    text_param2_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemEventKind"
    text_param2_val = etree.SubElement(text_param2, etree.QName(autosar_namespace, "VALUE"))
    if EventKind == "BSW":
        text_param2_val.text = "DEM_EVENT_KIND_BSW"
    else:
        text_param2_val.text = "DEM_EVENT_KIND_SWC"

    # 2.11 参数11：DemEventAssociatedIdentification（层级+2）
    num_param9 = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_param9_def = etree.SubElement(num_param9, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_param9_def.set("DEST", "ECUC-INTEGER-PARAM-DEF")
    num_param9_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemEventAssociatedIdentification"
    num_param9_val = etree.SubElement(num_param9, etree.QName(autosar_namespace, "VALUE"))
    num_param9_val.text = str(DEM_Index)

    # 3. REFERENCE-VALUES（根容器的子元素，层级+1）
    ref_values = etree.SubElement(dem_event_root, etree.QName(autosar_namespace, "REFERENCE-VALUES"))

    # 3.1 引用1：DemOperationCycleRef（层级+2）
    ref1 = etree.SubElement(ref_values, etree.QName(autosar_namespace, "ECUC-REFERENCE-VALUE"))
    ref1_def = etree.SubElement(ref1, etree.QName(autosar_namespace, "DEFINITION-REF"))
    ref1_def.set("DEST", "ECUC-REFERENCE-DEF")
    ref1_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemOperationCycleRef"
    ref1_val = etree.SubElement(ref1, etree.QName(autosar_namespace, "VALUE-REF"))
    ref1_val.set("DEST", "ECUC-CONTAINER-VALUE")
    ref1_val.text = f"/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemGeneral/{OprationCycle}"

    # 3.2 引用2：DemStorageConditionGroupRef（层级+2）
    ref2 = etree.SubElement(ref_values, etree.QName(autosar_namespace, "ECUC-REFERENCE-VALUE"))
    ref2_def = etree.SubElement(ref2, etree.QName(autosar_namespace, "DEFINITION-REF"))
    ref2_def.set("DEST", "ECUC-REFERENCE-DEF")
    ref2_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemStorageConditionGroupRef"
    ref2_val = etree.SubElement(ref2, etree.QName(autosar_namespace, "VALUE-REF"))
    ref2_val.set("DEST", "ECUC-CONTAINER-VALUE")
    ref2_val.text = "/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemGeneral/DiagnosticStorageConditionGroup"

    # 3.3 引用3：DemEnableConditionGroupRef（层级+2）
    ref3 = etree.SubElement(ref_values, etree.QName(autosar_namespace, "ECUC-REFERENCE-VALUE"))
    ref3_def = etree.SubElement(ref3, etree.QName(autosar_namespace, "DEFINITION-REF"))
    ref3_def.set("DEST", "ECUC-REFERENCE-DEF")
    ref3_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemEnableConditionGroupRef"
    ref3_val = etree.SubElement(ref3, etree.QName(autosar_namespace, "VALUE-REF"))
    ref3_val.set("DEST", "ECUC-CONTAINER-VALUE")
    #ref3_val.text = "/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemGeneral/ECG_Supply"
    ref3_val.text = f"/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemGeneral/{ECG}"

    if "N.A" != DtcRef:
        # 3.4 引用4：DemDTCRef（层级+2）
        ref4 = etree.SubElement(ref_values, etree.QName(autosar_namespace, "ECUC-REFERENCE-VALUE"))
        ref4_def = etree.SubElement(ref4, etree.QName(autosar_namespace, "DEFINITION-REF"))
        ref4_def.set("DEST", "ECUC-REFERENCE-DEF")
        ref4_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemDTCRef"
        ref4_val = etree.SubElement(ref4, etree.QName(autosar_namespace, "VALUE-REF"))
        ref4_val.set("DEST", "ECUC-CONTAINER-VALUE")
        #ref4_val.text = "/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemConfigSet/DemDTC_FLS_Sensl_OpenLoad"
        ref4_val.text = f"/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemConfigSet/{DtcRef}"

    # 4. SUB-CONTAINERS（根容器的子元素，层级+1）
    sub_containers = etree.SubElement(dem_event_root, etree.QName(autosar_namespace, "SUB-CONTAINERS"))

    # 4.1 嵌套容器1：DemDebounceAlgorithmClass_0（层级+2）
    sub1 = etree.SubElement(sub_containers, etree.QName(autosar_namespace, "ECUC-CONTAINER-VALUE"))
    sub1.set("S", "USER_GENERATED")
    sub1_short = etree.SubElement(sub1, etree.QName(autosar_namespace, "SHORT-NAME"))
    sub1_short.text = "DemDebounceAlgorithmClass_0"
    sub1_def = etree.SubElement(sub1, etree.QName(autosar_namespace, "DEFINITION-REF"))
    sub1_def.set("DEST", "ECUC-CHOICE-CONTAINER-DEF")
    sub1_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemDebounceAlgorithmClass"

    # 4.1.1 嵌套容器1的子容器：DemDebounceCounterBased_0（层级+3）
    sub1_sub = etree.SubElement(sub1, etree.QName(autosar_namespace, "SUB-CONTAINERS"))
    sub1_sub_cont = etree.SubElement(sub1_sub, etree.QName(autosar_namespace, "ECUC-CONTAINER-VALUE"))
    sub1_sub_cont_short = etree.SubElement(sub1_sub_cont, etree.QName(autosar_namespace, "SHORT-NAME"))
    if DebounceAlgorithm == "CounterBase":
        sub1_sub_cont_short.text = "DemDebounceCounterBased_0"
    else:
        sub1_sub_cont_short.text = "DemDebounceTimeBase_0"
    sub1_sub_cont_def = etree.SubElement(sub1_sub_cont, etree.QName(autosar_namespace, "DEFINITION-REF"))
    sub1_sub_cont_def.set("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
    if DebounceAlgorithm == "CounterBase":
        sub1_sub_cont_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemDebounceAlgorithmClass/DemDebounceCounterBased"
    else:
        sub1_sub_cont_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemDebounceAlgorithmClass/DemDebounceTimeBase"

    # 4.1.2 嵌套容器1子容器的引用（层级+4）
    sub1_sub_ref = etree.SubElement(sub1_sub_cont, etree.QName(autosar_namespace, "REFERENCE-VALUES"))
    sub1_sub_ref_val = etree.SubElement(sub1_sub_ref, etree.QName(autosar_namespace, "ECUC-REFERENCE-VALUE"))
    sub1_sub_ref_val_def = etree.SubElement(sub1_sub_ref_val, etree.QName(autosar_namespace, "DEFINITION-REF"))
    sub1_sub_ref_val_def.set("DEST", "ECUC-REFERENCE-DEF")
    if DebounceAlgorithm == "CounterBase":
        sub1_sub_ref_val_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemDebounceAlgorithmClass/DemDebounceCounterBased/DemDebounceCounterBasedClassRef"
    else:
        sub1_sub_ref_val_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemDebounceAlgorithmClass/DemDebounceTimeBase/DemDebounceTimeBaseRef"
    sub1_sub_ref_val_val = etree.SubElement(sub1_sub_ref_val, etree.QName(autosar_namespace, "VALUE-REF"))
    sub1_sub_ref_val_val.set("DEST", "ECUC-CONTAINER-VALUE")

    if DebounceAlgorithm == "CounterBase":
        sub1_sub_ref_val_val.text = "/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemConfigSet/DebCntBas_"+EventName
    else:
        sub1_sub_ref_val_val.text = "/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemConfigSet/DebTimBas_"+EventName

    # 4.2 嵌套容器2：DemRbEventClass_0（层级+2）
    sub2 = etree.SubElement(sub_containers, etree.QName(autosar_namespace, "ECUC-CONTAINER-VALUE"))
    sub2.set("S", "USER_GENERATED")
    sub2_short = etree.SubElement(sub2, etree.QName(autosar_namespace, "SHORT-NAME"))
    sub2_short.text = "DemRbEventClass_0"
    sub2_def = etree.SubElement(sub2, etree.QName(autosar_namespace, "DEFINITION-REF"))
    sub2_def.set("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
    sub2_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemRbEventClass"

    # 4.2.1 嵌套容器2的参数（层级+3）
    sub2_param = etree.SubElement(sub2, etree.QName(autosar_namespace, "PARAMETER-VALUES"))
    sub2_param_val = etree.SubElement(sub2_param, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    sub2_param_val.set("S", "USER_GENERATED")
    sub2_param_val_def = etree.SubElement(sub2_param_val, etree.QName(autosar_namespace, "DEFINITION-REF"))
    sub2_param_val_def.set("DEST", "ECUC-BOOLEAN-PARAM-DEF")
    sub2_param_val_def.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter/DemRbEventClass/DemRbEventStatusBitStorageTestFailed"
    sub2_param_val_val = etree.SubElement(sub2_param_val, etree.QName(autosar_namespace, "VALUE"))
    sub2_param_val_val.text = "false"

    return dem_event_root


def insert_dem_event_to_arxml(
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

    for i in range(dem_data.data_count):
        # 6. 创建并插入DemEvent容器
        try:
            create_dem_event_container(parent_container,
                                       autosar_ns,
                                       dem_data.DEM_Index[i],
                                       dem_data.EventName[i],
                                       dem_data.EventKind[i],
                                       dem_data.DemUdsDTC[i],
                                       dem_data.OprationCycle[i],
                                       dem_data.ECG[i],
                                       dem_data.Recoverable[i],
                                       dem_data.DebounceAlgorithm[i]
                                       )
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

        print(f"成功！生成Dem Event Container!")
        return True
    except Exception as e:
        print(f"保存文件失败：{str(e)}")
        return False

