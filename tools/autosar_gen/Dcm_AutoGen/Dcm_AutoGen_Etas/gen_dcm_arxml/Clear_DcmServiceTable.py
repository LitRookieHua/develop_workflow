"""清空 ETAS_ServiceTable_DoCAN 服务表的 SUB-CONTAINERS (参考 Dem_AutoGen_Etas Clear_DemConfigSet.py)."""

from lxml import etree

from arxml_pipeline import parse_arxml, write_arxml, ns_tag

SERVICE_TABLE_NAME = "ETAS_ServiceTable_DoCAN"
DCM_SERVICE_DEF_SUFFIX = "/Dcm/DcmConfigSet/DcmDsd/DcmDsdServiceTable/DcmDsdService"


def _find_service_tables(root):
    """定位所有 SHORT-NAME=ETAS_ServiceTable_DoCAN 的 DcmDsdServiceTable 容器."""
    tables = []
    for c in root.iter(ns_tag("ECUC-CONTAINER-VALUE")):
        sn = c.find(ns_tag("SHORT-NAME"))
        if sn is not None and sn.text == SERVICE_TABLE_NAME:
            tables.append(c)
    return tables


def clear_service_table_subcontainers(input_arxml, output_arxml) -> bool:
    """
    清空 ETAS_ServiceTable_DoCAN 下 SUB-CONTAINERS 的全部子容器 (保留标签本身).

    防御性检查: 表必须唯一; SUB-CONTAINERS 内必须是 DcmDsdService 定义,
    防止误清兄弟容器 (如 DcmDsdServiceRequestSupplierNotification).

    返回: True=成功写入, False=失败 (输出文件未改动)
    """
    parsed = parse_arxml(input_arxml)
    if parsed is None:
        return False
    root, raw_content, xml_decl = parsed

    tables = _find_service_tables(root)
    if len(tables) == 0:
        print("错误：未找到 SHORT-NAME=%s 容器: %s" % (SERVICE_TABLE_NAME, input_arxml))
        return False
    if len(tables) > 1:
        print("错误：%s 容器出现 %d 个 (需唯一)" % (SERVICE_TABLE_NAME, len(tables)))
        return False

    sub = tables[0].find(ns_tag("SUB-CONTAINERS"))
    if sub is None:
        print("警告：%s 下无 SUB-CONTAINERS, 文件未改动" % SERVICE_TABLE_NAME)
        return False

    removed = 0
    for child in list(sub):
        def_ref = child.find(ns_tag("DEFINITION-REF"))
        if def_ref is None or not (def_ref.text or "").endswith(DCM_SERVICE_DEF_SUFFIX):
            print("错误：%s 的 SUB-CONTAINERS 内含非 DcmDsdService 容器 (%s), 拒绝清空"
                  % (SERVICE_TABLE_NAME, def_ref.text if def_ref is not None else "无DEFINITION-REF"))
            return False
        sub.remove(child)
        removed += 1

    if not write_arxml(etree.ElementTree(root), output_arxml, raw_content, xml_decl):
        return False
    print("已清空 %s 的 SUB-CONTAINERS (移除 %d 个 DcmDsdService)" % (SERVICE_TABLE_NAME, removed))
    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("用法: python Clear_DcmServiceTable.py <input_arxml> <output_arxml>")
        sys.exit(1)
    sys.exit(0 if clear_service_table_subcontainers(sys.argv[1], sys.argv[2]) else 1)
