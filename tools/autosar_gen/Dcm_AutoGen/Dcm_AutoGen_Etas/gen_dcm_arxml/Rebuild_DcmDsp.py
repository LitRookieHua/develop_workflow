"""清空并重建 DcmDspSession / DcmDspSecurity 容器的 SUB-CONTAINERS (数据来自 Excel DcmDsp 表).

只动 SUB-CONTAINERS 下的行容器; DcmDspSecurity 容器自身的 PARAMETER-VALUES
(DcmRbDspSecurityStoreSeed 等) 与其余兄弟容器逐字节保留.
"""

from lxml import etree

from arxml_pipeline import parse_arxml, write_arxml, ns_tag
from Create_DcmDsdServices import _add_definition_ref

DCM_DSP_DEFS = "/AUTOSAR_Dcm/EcucModuleDefs/Dcm/DcmConfigSet/DcmDsp"

SESSION_CONTAINER = "DcmDspSession"
SECURITY_CONTAINER = "DcmDspSecurity"

# (Excel 列名=参数定义名, 值类型); 顺序 = 基线 arxml 行内参数生成顺序
SESSION_ROW_PARAMS = [
    ("DcmDspSessionForBoot", "ENUMERATION"),
    ("DcmDspSessionP2ServerMax", "FLOAT"),
    ("DcmDspSessionP2StarServerMax", "FLOAT"),
    ("DcmDspSessionLevel", "INTEGER"),
]
SECURITY_ROW_PARAMS = [
    ("DcmDspSecurityLevel", "INTEGER"),
    ("DcmDspSecurityKeySize", "INTEGER"),
    ("DcmDspSecurityDelayTimeOnBoot", "FLOAT"),
    ("DcmRbDspSecurityNumAttLock", "INTEGER"),
    ("DcmDspSecurityDelayTime", "FLOAT"),
    ("DcmDspSecurityUsePort", "ENUMERATION"),
    ("DcmDspSecurityAttemptCounterEnabled", "BOOLEAN"),
    ("DcmDspSecurityNumAttDelay", "INTEGER"),
    ("DcmDspSecuritySeedSize", "INTEGER"),
    ("DcmDspSecurityGetSeedFnc", "FUNCTION"),
    ("DcmDspSecurityCompareKeyFnc", "FUNCTION"),
    ("DcmDspSecurityGetAttemptCounterFnc", "FUNCTION"),
    ("DcmDspSecuritySetAttemptCounterFnc", "FUNCTION"),
    ("DcmDspSecurityADRSize", "INTEGER"),
]

# 值类型 -> (参数元素标签, DEFINITION-REF 的 DEST)
_KIND_ELEMENT = {
    "INTEGER": ("ECUC-NUMERICAL-PARAM-VALUE", "ECUC-INTEGER-PARAM-DEF"),
    "FLOAT": ("ECUC-NUMERICAL-PARAM-VALUE", "ECUC-FLOAT-PARAM-DEF"),
    "BOOLEAN": ("ECUC-NUMERICAL-PARAM-VALUE", "ECUC-BOOLEAN-PARAM-DEF"),
    "ENUMERATION": ("ECUC-TEXTUAL-PARAM-VALUE", "ECUC-ENUMERATION-PARAM-DEF"),
    "FUNCTION": ("ECUC-TEXTUAL-PARAM-VALUE", "ECUC-FUNCTION-NAME-DEF"),
}


def _find_containers(root, short_name):
    """定位所有 SHORT-NAME=short_name 的 ECUC 容器."""
    hits = []
    for c in root.iter(ns_tag("ECUC-CONTAINER-VALUE")):
        sn = c.find(ns_tag("SHORT-NAME"))
        if sn is not None and sn.text == short_name:
            hits.append(c)
    return hits


def _format_value(kind, v):
    if kind == "INTEGER":
        return str(int(v))
    if kind == "FLOAT":
        # 10 -> "10.0", 2 -> "2.0", 0.05 -> "0.05" (对齐基线 arxml 浮点渲染)
        return str(float(v))
    if kind == "BOOLEAN":
        return "true" if v else "false"
    return str(v)


def _create_row(parent, container_name, row, row_params):
    c = etree.SubElement(parent, ns_tag("ECUC-CONTAINER-VALUE"))
    sn = etree.SubElement(c, ns_tag("SHORT-NAME"))
    sn.text = row["name"]
    row_def = "%s/%s/%sRow" % (DCM_DSP_DEFS, container_name, container_name)
    _add_definition_ref(c, "ECUC-PARAM-CONF-CONTAINER-DEF", row_def)
    param_values = etree.SubElement(c, ns_tag("PARAMETER-VALUES"))
    for param, kind in row_params:
        if row.get(param) is None:
            continue
        element, dest = _KIND_ELEMENT[kind]
        p = etree.SubElement(param_values, ns_tag(element))
        _add_definition_ref(p, dest, "%s/%s" % (row_def, param))
        v = etree.SubElement(p, ns_tag("VALUE"))
        v.text = _format_value(kind, row[param])


def _rebuild_container(root, container_name, row_params, rows) -> bool:
    """清空 SHORT-NAME=container_name 容器的 SUB-CONTAINERS 并按 rows 重建.

    防御性检查: 容器唯一; 容器自身及现有子容器的 DEFINITION-REF 后缀匹配,
    防止误清兄弟容器 (同 Clear_DcmServiceTable 风格).
    """
    hits = _find_containers(root, container_name)
    if len(hits) == 0:
        print("错误：未找到 SHORT-NAME=%s 容器" % container_name)
        return False
    if len(hits) > 1:
        print("错误：%s 容器出现 %d 个 (需唯一)" % (container_name, len(hits)))
        return False
    container = hits[0]

    container_def = "%s/%s" % (DCM_DSP_DEFS, container_name)
    def_ref = container.find(ns_tag("DEFINITION-REF"))
    if def_ref is None or not (def_ref.text or "").endswith(container_def):
        print("错误：%s 容器的 DEFINITION-REF 异常: %s"
              % (container_name, def_ref.text if def_ref is not None else "无DEFINITION-REF"))
        return False

    sub = container.find(ns_tag("SUB-CONTAINERS"))
    if sub is None:
        print("错误：%s 下无 SUB-CONTAINERS" % container_name)
        return False

    row_def = "%s/%sRow" % (container_def, container_name)
    removed = 0
    for child in list(sub):
        d = child.find(ns_tag("DEFINITION-REF"))
        if d is None or not (d.text or "").endswith(row_def):
            print("错误：%s 的 SUB-CONTAINERS 内含非 %sRow 容器 (%s), 拒绝清空"
                  % (container_name, container_name,
                     d.text if d is not None else "无DEFINITION-REF"))
            return False
        sub.remove(child)
        removed += 1

    for row in rows:
        _create_row(sub, container_name, row, row_params)
    print("已重建 %s 的 SUB-CONTAINERS (清除 %d 行, 生成 %d 行)"
          % (container_name, removed, len(rows)))
    return True


def rebuild_dcm_dsp_containers(input_arxml, output_arxml, dsp_data) -> bool:
    """清空并重建 DcmDspSession / DcmDspSecurity 的 SUB-CONTAINERS."""
    parsed = parse_arxml(input_arxml)
    if parsed is None:
        return False
    root, raw_content, xml_decl = parsed

    if not _rebuild_container(root, SESSION_CONTAINER, SESSION_ROW_PARAMS,
                              dsp_data.session_rows):
        return False
    if not _rebuild_container(root, SECURITY_CONTAINER, SECURITY_ROW_PARAMS,
                              dsp_data.security_rows):
        return False

    if not write_arxml(etree.ElementTree(root), output_arxml, raw_content, xml_decl):
        return False
    print("成功！重建 DcmDspSession (%d 行) / DcmDspSecurity (%d 行)!"
          % (dsp_data.session_count, dsp_data.security_count))
    return True


if __name__ == "__main__":
    import sys
    print("用法: 经 Dcm_arxml_Script.py 入口调用 (需 Excel 解析数据)")
    sys.exit(1)
