"""根据解析后的 Excel 数据重建 DcmDsdService / DcmDsdSubService 容器 (参考 Dem_AutoGen_Etas Create_DemDTCs.py)."""

from lxml import etree

from arxml_pipeline import parse_arxml, write_arxml, ns_tag
from Clear_DcmServiceTable import SERVICE_TABLE_NAME, _find_service_tables

DCM_DEFS = "/AUTOSAR_Dcm/EcucModuleDefs/Dcm/DcmConfigSet/DcmDsd/DcmDsdServiceTable"
RTA_REFS = "/RTA_BIP/EcucModuleConfigurationValuess/Dcm/DcmConfigSet"

# 会话/安全列名 → arxml 引用目标 (顺序即生成顺序)
SESSION_MAP = [
    ("Default Session", "DEFAULT_SESSION"),
    ("Programming Session", "PROGRAMMING_SESSION"),
    ("Extended Session", "EXTENDED_DIAGNOSTIC_SESSION"),
]
SECURITY_MAP = [
    ("App Unlocked", "Unlocked_App"),
    ("Boot Unlocked", "Unlocked_Boot"),
    ("iMotion Unlocked", "Unlocked_Develop"),
]


def _add_definition_ref(parent, dest, text):
    el = etree.SubElement(parent, ns_tag("DEFINITION-REF"))
    el.set("DEST", dest)
    el.text = text


def _add_numerical_param(param_values, dest, definition, value):
    p = etree.SubElement(param_values, ns_tag("ECUC-NUMERICAL-PARAM-VALUE"))
    _add_definition_ref(p, dest, definition)
    v = etree.SubElement(p, ns_tag("VALUE"))
    v.text = str(value)


def _add_reference(ref_values, definition, value_ref):
    r = etree.SubElement(ref_values, ns_tag("ECUC-REFERENCE-VALUE"))
    _add_definition_ref(r, "ECUC-REFERENCE-DEF", definition)
    v = etree.SubElement(r, ns_tag("VALUE-REF"))
    v.set("DEST", "ECUC-CONTAINER-VALUE")
    v.text = value_ref


def _add_permission_refs(parent, service_def_path, subservice_def_path, sessions, sec_levels):
    """按模板顺序 (Security 在前、Session 在后) 平铺引用; 无引用时省略 REFERENCE-VALUES."""
    if not sessions and not sec_levels:
        return
    ref_values = etree.SubElement(parent, ns_tag("REFERENCE-VALUES"))
    for _, target in SECURITY_MAP:
        if target in sec_levels:
            _add_reference(ref_values,
                           subservice_def_path + "/DcmDsdSubServiceSecurityLevelRef"
                           if subservice_def_path else service_def_path + "/DcmDsdSidTabSecurityLevelRef",
                           "%s/DcmDsp/DcmDspSecurity/%s" % (RTA_REFS, target))
    for _, target in SESSION_MAP:
        if target in sessions:
            _add_reference(ref_values,
                           subservice_def_path + "/DcmDsdSubServiceSessionLevelRef"
                           if subservice_def_path else service_def_path + "/DcmDsdSidTabSessionLevelRef",
                           "%s/DcmDsp/DcmDspSession/%s" % (RTA_REFS, target))


def _create_subservice(parent, sub):
    c = etree.SubElement(parent, ns_tag("ECUC-CONTAINER-VALUE"))
    sn = etree.SubElement(c, ns_tag("SHORT-NAME"))
    sn.text = sub["name"]
    _add_definition_ref(c, "ECUC-PARAM-CONF-CONTAINER-DEF",
                        DCM_DEFS + "/DcmDsdService/DcmDsdSubService")
    param_values = etree.SubElement(c, ns_tag("PARAMETER-VALUES"))
    _add_numerical_param(param_values, "ECUC-INTEGER-PARAM-DEF",
                         DCM_DEFS + "/DcmDsdService/DcmDsdSubService/DcmDsdSubServiceId",
                         sub["sub_id"])
    _add_permission_refs(c, None, DCM_DEFS + "/DcmDsdService/DcmDsdSubService",
                         sub["sessions"], sub["sec_levels"])


def _create_service(parent, svc):
    c = etree.SubElement(parent, ns_tag("ECUC-CONTAINER-VALUE"))
    sn = etree.SubElement(c, ns_tag("SHORT-NAME"))
    sn.text = svc["name"]
    _add_definition_ref(c, "ECUC-PARAM-CONF-CONTAINER-DEF",
                        DCM_DEFS + "/DcmDsdService")
    param_values = etree.SubElement(c, ns_tag("PARAMETER-VALUES"))
    _add_numerical_param(param_values, "ECUC-BOOLEAN-PARAM-DEF",
                         DCM_DEFS + "/DcmDsdService/DcmDsdSidTabSubfuncAvail",
                         "true" if svc["has_sub"] else "false")
    _add_numerical_param(param_values, "ECUC-INTEGER-PARAM-DEF",
                         DCM_DEFS + "/DcmDsdService/DcmDsdSidTabServiceId",
                         svc["service_id"])
    if svc.get("callback"):
        fnc = etree.SubElement(param_values, ns_tag("ECUC-TEXTUAL-PARAM-VALUE"))
        _add_definition_ref(fnc, "ECUC-FUNCTION-NAME-DEF",
                            DCM_DEFS + "/DcmDsdService/DcmDsdSidTabFnc")
        v = etree.SubElement(fnc, ns_tag("VALUE"))
        v.text = svc["callback"]

    if not svc["has_sub"]:
        # 无子服务: 会话+安全权限写在 service 层
        _add_permission_refs(c, DCM_DEFS + "/DcmDsdService", None,
                             svc["sessions"], svc["sec_levels"])
    else:
        sub_containers = etree.SubElement(c, ns_tag("SUB-CONTAINERS"))
        for sub in svc["subs"]:
            _create_subservice(sub_containers, sub)


def insert_dcm_services_to_arxml(input_arxml, output_arxml, dcm_data) -> bool:
    """在 ETAS_ServiceTable_DoCAN 的 SUB-CONTAINERS 下重建全部 DcmDsdService."""
    parsed = parse_arxml(input_arxml)
    if parsed is None:
        return False
    root, raw_content, xml_decl = parsed

    tables = _find_service_tables(root)
    if len(tables) != 1:
        print("错误：%s 容器数量 %d (需唯一): %s" % (SERVICE_TABLE_NAME, len(tables), input_arxml))
        return False
    sub = tables[0].find(ns_tag("SUB-CONTAINERS"))
    if sub is None:
        print("错误：%s 下无 SUB-CONTAINERS (需先运行 Clear)" % SERVICE_TABLE_NAME)
        return False
    if len(sub):
        print("警告：%s 的 SUB-CONTAINERS 非空 (%d 个), 追加前请先 Clear" % (SERVICE_TABLE_NAME, len(sub)))

    for svc in dcm_data.services:
        _create_service(sub, svc)

    if not write_arxml(etree.ElementTree(root), output_arxml, raw_content, xml_decl):
        return False
    print("成功！生成 Dcm DsdServices Container (%d 个服务, %d 个子服务)!"
          % (len(dcm_data.services),
             sum(len(s["subs"]) for s in dcm_data.services)))
    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("用法: python Create_DcmDsdServices.py <input_arxml> <output_arxml> <解析后的数据需经入口脚本传入>")
        sys.exit(1)
    sys.exit(0)
