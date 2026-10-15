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


def create_debounce_time_based_container(
    parent_element,
    autosar_namespace: str,
    EventName: str,
    Debounce_Time_Failed,
    Debounce_Time_Passed
):
    """
    创建“基于时间的Debounce配置容器”，生成与示例格式一致的XML结构
    对应AUTOSAR Dem模块的DemDebounceTimeBaseClass
    """
    # 根容器：ECUC-CONTAINER-VALUE（带S="USER_GENERATED"属性）
    debounce_time_root = etree.SubElement(
        parent_element,
        etree.QName(autosar_namespace, "ECUC-CONTAINER-VALUE")
    )
    debounce_time_root.set("S", "USER_GENERATED")  # 时间基类容器需加S属性

    # 1. SHORT-NAME：格式为 "DebTimBas_事件名"
    short_name = etree.SubElement(debounce_time_root, etree.QName(autosar_namespace, "SHORT-NAME"))
    short_name.text = f"DebTimBas_{EventName}"  # 与示例格式对齐（如DebTimBas_DemEvent_ETH_Linkdown）

    # 2. DEFINITION-REF：指向时间基类的定义路径（固定）
    def_ref = etree.SubElement(debounce_time_root, etree.QName(autosar_namespace, "DEFINITION-REF"))
    def_ref.set("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
    def_ref.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDebounceTimeBaseClass"  # 时间基类路径

    # 3. PARAMETER-VALUES：参数容器（存放3个核心参数）
    param_values = etree.SubElement(debounce_time_root, etree.QName(autosar_namespace, "PARAMETER-VALUES"))

    # 3.1 文本参数：DemDebounceBehavior（去抖动行为，固定为DEM_DEBOUNCE_FREEZE）
    textual_param = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-TEXTUAL-PARAM-VALUE"))
    textual_def_ref = etree.SubElement(textual_param, etree.QName(autosar_namespace, "DEFINITION-REF"))
    textual_def_ref.set("DEST", "ECUC-ENUMERATION-PARAM-DEF")
    textual_def_ref.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDebounceTimeBaseClass/DemDebounceBehavior"
    textual_val = etree.SubElement(textual_param, etree.QName(autosar_namespace, "VALUE"))
    textual_val.text = "DEM_DEBOUNCE_FREEZE"  # 与示例一致的去抖动行为

    # 3.2 数值参数1：DemDebounceTimeFailedThreshold（故障时间阈值，浮点型）
    num_param_failed = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_failed_def_ref = etree.SubElement(num_param_failed, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_failed_def_ref.set("DEST", "ECUC-FLOAT-PARAM-DEF")  # 注意：时间基类是FLOAT类型
    num_failed_def_ref.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDebounceTimeBaseClass/DemDebounceTimeFailedThreshold"
    num_failed_val = etree.SubElement(num_param_failed, etree.QName(autosar_namespace, "VALUE"))
    num_failed_val.text = str(Debounce_Time_Failed / 1000)

    # 3.3 数值参数2：DemDebounceTimePassedThreshold（正常时间阈值，浮点型）
    num_param_passed = etree.SubElement(param_values, etree.QName(autosar_namespace, "ECUC-NUMERICAL-PARAM-VALUE"))
    num_passed_def_ref = etree.SubElement(num_param_passed, etree.QName(autosar_namespace, "DEFINITION-REF"))
    num_passed_def_ref.set("DEST", "ECUC-FLOAT-PARAM-DEF")  # 与故障阈值类型一致
    num_passed_def_ref.text = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDebounceTimeBaseClass/DemDebounceTimePassedThreshold"
    num_passed_val = etree.SubElement(num_param_passed, etree.QName(autosar_namespace, "VALUE"))
    num_passed_val.text = str(Debounce_Time_Passed / 1000)

    return debounce_time_root


def insert_debounce_time_based_to_arxml(
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
        # 新增条件：仅当去抖动算法为"TimeBase"时，才创建计数器基类容器
        if dem_data.DebounceAlgorithm[i] == "TimeBase":
            # 创建并插入DemEvent的计数器基类去抖动容器
            try:
                create_debounce_time_based_container(
                    parent_element=parent_container,
                    autosar_namespace=autosar_ns,
                    EventName=dem_data.EventName[i],
                    Debounce_Time_Failed=dem_data.Debounce_Falied[i],
                    Debounce_Time_Passed=dem_data.Debounce_Pass[i]
                )
                #print(f"成功创建事件 {dem_data.EventName[i]} 的TimeBase去抖动容器")
            except Exception as e:
                print(f"创建事件 {dem_data.EventName[i]} 的TimeBase容器失败：{str(e)}")

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

        print(f"成功！生成Dem Counter Debounce Container!")
        return True
    except Exception as e:
        print(f"保存文件失败：{str(e)}")
        return False

