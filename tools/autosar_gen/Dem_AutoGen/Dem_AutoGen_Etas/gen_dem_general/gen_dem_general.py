#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_dem_general - 生成 AUTOSAR Dem DemGeneral 侧容器 (使能条件组 + 快照/扩展数据栈).

背景: gen_dem_arxml 只生成 DemConfigSet 侧 (事件/DTC/属性), 其子脚本按固定名引用
DemGeneral 侧容器 (ExtendedDataClass_DTC_Properties / FreezeFrame_DTC_DidSet_TypeA|B /
DTC_Properties_FFRecNumClass / <ECG 组名>), 这些容器此前全靠手工维护 arxml.
本脚本从输入 Excel 的两个专用 sheet 读参数自动生成, 使能条件组来自 CMCRXJ6B-42/43
案例 (RX Dem 快照 DID 集 + 扩展数据单记录) 的配置结构.

sheet 格式 (列名必须一致, 见 docs/design/2026-11-20-dem-autogen-etas-gen-dem-general-design.md):
  enable_condition_group: No. | ItemKind(EC|ECG) | Name | Description | Status | Members
  extended_freeze_data:   No. | ItemKind(DATA-ELEMENT|DID-CLASS|FREEZE-FRAME-CLASS|
                                SNAPSHOT-RECORD|EXTENDED-RECORD|EXTENDED-DATA-CLASS|
                                FF-RECNUM-CLASS) | Name | DataType | Source |
                                InternalElement | DidHex | Number | Update | Trigger | Members

幂等策略: 先删除 DemGeneral 下「SHORT-NAME 在 sheet 中」或「属受管定义类型且
S="USER_GENERATED"」的旧容器再重建; 不在 sheet 中的手工容器 (如 SR_Vehicle_Speed)
不受影响.

用法:
  python gen_dem_general.py <DemGeneral配置表xlsx> <arxml> <ecg:true|false> <efd:true|false>

输入为独立的 DemGeneral 配置表 (IDC_DemGeneral_Config*.xlsx, 与 DTC 的 EVM 表分开放,
只含 enable_condition_group / extended_freeze_data 两个 sheet), 由
dem_autogen_etas.py 经 --excel-general 或目录自动发现传入.
"""

import os
import sys

import pandas as pd
from lxml import etree

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gen_dem_arxml"))
from Create_DemDTCs import (  # noqa: E402  序列化管线复用 (与 Clear_DemConfigSet 同先例)
    xml_decl_pattern,
    extract_xml_declaration,
    preprocess_xml_tags,
    format_xml_indent,
)

AUTOSAR_NS = "http://autosar.org/schema/r4.0"
NS_MAP = {"ar": AUTOSAR_NS}
DEM_GENERAL_DEF = "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemGeneral"
VALUE_REF_PREFIX = "/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemGeneral"

ECG_SHEET = "enable_condition_group"
ECG_COLS = ["No.", "ItemKind", "Name", "Description", "Status", "Members"]
EFD_SHEET = "extended_freeze_data"
EFD_COLS = ["No.", "ItemKind", "Name", "DataType", "Source", "InternalElement",
            "DidHex", "Number", "Update", "Trigger", "Members"]

# 各开关管辖的定义类型 (DEFINITION-REF 尾段)
ECG_MANAGED_TYPES = {"DemEnableCondition", "DemEnableConditionGroup"}
EFD_MANAGED_TYPES = {"DemDataElementClass", "DemDidClass", "DemFreezeFrameClass",
                     "DemFreezeFrameRecordClass", "DemExtendedDataRecordClass",
                     "DemExtendedDataClass", "DemFreezeFrameRecNumClass"}

EFD_KINDS = {"DATA-ELEMENT", "DID-CLASS", "FREEZE-FRAME-CLASS", "SNAPSHOT-RECORD",
             "EXTENDED-RECORD", "EXTENDED-DATA-CLASS", "FF-RECNUM-CLASS"}


def fail(msg):
    print("[gen_dem_general] ERROR: %s" % msg)
    sys.exit(1)


def read_sheet(excel_path, sheet, cols):
    """读 sheet 并校验表头; 返回逐行 dict 列表 (值已 strip, NaN -> '')."""
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, dtype=str)
    except ValueError:
        fail("Excel 缺少 sheet: %s (%s)" % (sheet, excel_path))
    actual = [str(c).strip() for c in df.columns]
    missing = [c for c in cols if c not in actual]
    if missing:
        fail("sheet %s 缺少列: %s (实际: %s)" % (sheet, ", ".join(missing), actual))
    df.columns = actual
    rows = []
    for _, r in df.iterrows():
        rows.append({c: ("" if pd.isna(r[c]) else str(r[c]).strip()) for c in cols})
    return rows


def load_ecg_rows(excel_path):
    rows = read_sheet(excel_path, ECG_SHEET, ECG_COLS)
    names, ecg_rows, ec_rows = set(), [], []
    for i, r in enumerate(rows):
        if not r["Name"]:
            fail("%s 第 %d 行 Name 为空" % (ECG_SHEET, i + 2))
        if r["Name"] in names:
            fail("%s Name 重复: %s" % (ECG_SHEET, r["Name"]))
        names.add(r["Name"])
        kind = r["ItemKind"].upper()
        members = r["Members"].split()
        if kind == "EC":
            if members:
                fail("%s EC 行不应有 Members: %s" % (ECG_SHEET, r["Name"]))
            ec_rows.append(r)
        elif kind == "ECG":
            if not members:
                fail("%s ECG 行 Members 为空: %s" % (ECG_SHEET, r["Name"]))
            if len(members) != len(set(members)):
                fail("%s ECG 行 Members 有重复: %s" % (ECG_SHEET, r["Name"]))
            ecg_rows.append(r)
        else:
            fail("%s ItemKind 只允许 EC/ECG: %r (行 %d)" % (ECG_SHEET, r["ItemKind"], i + 2))
    # ECG 成员解析: sheet 内 EC 名优先, 其次 DemGeneral 存活容器
    for r in ecg_rows:
        resolved = []
        for m in r["Members"].split():
            if m in names:
                resolved.append(("sheet", m))
            else:
                resolved.append(("existing", m))
        r["_members"] = resolved
    return ec_rows, ecg_rows


def load_efd_rows(excel_path):
    rows = read_sheet(excel_path, EFD_SHEET, EFD_COLS)
    names, out = set(), []
    for i, r in enumerate(rows):
        if not r["Name"]:
            fail("%s 第 %d 行 Name 为空" % (EFD_SHEET, i + 2))
        if r["Name"] in names:
            fail("%s Name 重复: %s" % (EFD_SHEET, r["Name"]))
        names.add(r["Name"])
        kind = r["ItemKind"].upper()
        if kind not in EFD_KINDS:
            fail("%s ItemKind 非法: %r (行 %d, 允许: %s)"
                 % (EFD_SHEET, r["ItemKind"], i + 2, ", ".join(sorted(EFD_KINDS))))
        r["ItemKind"] = kind
        members = r["Members"].split()
        need_members = kind in ("DID-CLASS", "FREEZE-FRAME-CLASS", "EXTENDED-RECORD",
                                "EXTENDED-DATA-CLASS", "FF-RECNUM-CLASS")
        if need_members and not members:
            fail("%s %s 行 Members 为空: %s" % (EFD_SHEET, kind, r["Name"]))
        if not need_members and members and kind != "SNAPSHOT-RECORD":
            fail("%s %s 行不应有 Members: %s" % (EFD_SHEET, kind, r["Name"]))
        if len(members) != len(set(members)):
            fail("%s Members 有重复: %s" % (EFD_SHEET, r["Name"]))
        if kind == "DATA-ELEMENT":
            src = r["Source"].lower()
            if src == "external":
                if r["DataType"] not in ("UINT8", "UINT16", "UINT32"):
                    fail("%s 外部 DATA-ELEMENT DataType 只允许 UINT8/16/32: %s (%r)"
                         % (EFD_SHEET, r["Name"], r["DataType"]))
            elif src == "internal":
                if not r["InternalElement"]:
                    fail("%s 内部 DATA-ELEMENT 缺 InternalElement: %s" % (EFD_SHEET, r["Name"]))
            else:
                fail("%s DATA-ELEMENT Source 只允许 External/Internal: %s (%r)"
                     % (EFD_SHEET, r["Name"], r["Source"]))
        if kind == "DID-CLASS":
            if not r["DidHex"].lower().startswith("0x"):
                fail("%s DID-CLASS DidHex 须为 0x 十六进制: %s (%r)"
                     % (EFD_SHEET, r["Name"], r["DidHex"]))
            int(r["DidHex"], 16)
        if kind in ("SNAPSHOT-RECORD", "EXTENDED-RECORD"):
            for col in ("Number", "Update", "Trigger"):
                if not r[col]:
                    fail("%s %s 行缺 %s: %s" % (EFD_SHEET, kind, col, r["Name"]))
            try:
                int(r["Number"])
            except ValueError:
                fail("%s Number 须为整数: %s (%r)" % (EFD_SHEET, r["Name"], r["Number"]))
        out.append(r)
    return out


def collect_managed_names(ecg_on, efd_on, ec_rows, ecg_rows, efd_rows):
    names = set()
    if ecg_on:
        names |= {r["Name"] for r in ec_rows} | {r["Name"] for r in ecg_rows}
    if efd_on:
        names |= {r["Name"] for r in efd_rows}
    return names


def delete_managed(sub_containers, managed_types, managed_names):
    """删除 DemGeneral 下受管旧容器: 名字在 sheet 中, 或属受管类型且 S=USER_GENERATED."""
    removed = []
    for c in list(sub_containers):
        if c.tag != etree.QName(AUTOSAR_NS, "ECUC-CONTAINER-VALUE"):
            continue
        name_el = c.find("ar:SHORT-NAME", NS_MAP)
        name = name_el.text if name_el is not None else ""
        def_el = c.find("ar:DEFINITION-REF", NS_MAP)
        tail = def_el.text.rsplit("/", 1)[-1] if def_el is not None else ""
        if name in managed_names or (tail in managed_types and c.get("S") == "USER_GENERATED"):
            removed.append(name)
            sub_containers.remove(c)
    return removed


def existing_general_names(root):
    return {c.findtext("ar:SHORT-NAME", "", NS_MAP)
            for c in root.findall(".//ar:ECUC-CONTAINER-VALUE[ar:SHORT-NAME='DemGeneral']"
                                  "/ar:SUB-CONTAINERS/ar:ECUC-CONTAINER-VALUE", NS_MAP)}


# ---------- 容器构建 (统一带 S="USER_GENERATED", ETAS 生成标记) ----------

def _text_param(parent, def_path, value, dest="ECUC-ENUMERATION-PARAM-DEF"):
    p = etree.SubElement(parent, etree.QName(AUTOSAR_NS, "ECUC-TEXTUAL-PARAM-VALUE"))
    p.set("S", "USER_GENERATED")
    d = etree.SubElement(p, etree.QName(AUTOSAR_NS, "DEFINITION-REF"))
    d.set("DEST", dest)
    d.text = def_path
    v = etree.SubElement(p, etree.QName(AUTOSAR_NS, "VALUE"))
    v.text = value
    return p


def _num_param(parent, def_path, value, dest="ECUC-INTEGER-PARAM-DEF"):
    p = etree.SubElement(parent, etree.QName(AUTOSAR_NS, "ECUC-NUMERICAL-PARAM-VALUE"))
    p.set("S", "USER_GENERATED")
    d = etree.SubElement(p, etree.QName(AUTOSAR_NS, "DEFINITION-REF"))
    d.set("DEST", dest)
    d.text = def_path
    v = etree.SubElement(p, etree.QName(AUTOSAR_NS, "VALUE"))
    v.text = value
    return p


def _ref_value(parent, def_path, target):
    r = etree.SubElement(parent, etree.QName(AUTOSAR_NS, "ECUC-REFERENCE-VALUE"))
    r.set("S", "USER_GENERATED")
    d = etree.SubElement(r, etree.QName(AUTOSAR_NS, "DEFINITION-REF"))
    d.set("DEST", "ECUC-REFERENCE-DEF")
    d.text = def_path
    vr = etree.SubElement(r, etree.QName(AUTOSAR_NS, "VALUE-REF"))
    vr.set("DEST", "ECUC-CONTAINER-VALUE")
    vr.text = "%s/%s" % (VALUE_REF_PREFIX, target)
    return r


def _container(parent, name, def_tail, choice=False):
    c = etree.SubElement(parent, etree.QName(AUTOSAR_NS, "ECUC-CONTAINER-VALUE"))
    c.set("S", "USER_GENERATED")
    n = etree.SubElement(c, etree.QName(AUTOSAR_NS, "SHORT-NAME"))
    n.text = name
    d = etree.SubElement(c, etree.QName(AUTOSAR_NS, "DEFINITION-REF"))
    d.set("DEST", "ECUC-CHOICE-CONTAINER-DEF" if choice else "ECUC-PARAM-CONF-CONTAINER-DEF")
    d.text = "%s/%s" % (DEM_GENERAL_DEF, def_tail)
    return c


def _params(container):
    """取 PARAMETER-VALUES (懒创建, 空参数的容器不落空包装元素)."""
    p = container.find("ar:PARAMETER-VALUES", NS_MAP)
    if p is None:
        p = etree.SubElement(container, etree.QName(AUTOSAR_NS, "PARAMETER-VALUES"))
    return p


def _refs(container):
    """取 REFERENCE-VALUES (懒创建, 空引用的容器不落空包装元素)."""
    r = container.find("ar:REFERENCE-VALUES", NS_MAP)
    if r is None:
        r = etree.SubElement(container, etree.QName(AUTOSAR_NS, "REFERENCE-VALUES"))
    return r


def _subcontainers(container):
    return etree.SubElement(container, etree.QName(AUTOSAR_NS, "SUB-CONTAINERS"))


def build_ec(parent, r):
    c = _container(parent, r["Name"], "DemEnableCondition")
    _num_param(_params(c), DEM_GENERAL_DEF + "/DemEnableCondition/DemEnableConditionStatus",
               r["Status"] or "false", dest="ECUC-BOOLEAN-PARAM-DEF")


def build_ecg(parent, r):
    c = _container(parent, r["Name"], "DemEnableConditionGroup")
    refs = _refs(c)
    for _, m in r["_members"]:
        _ref_value(refs, DEM_GENERAL_DEF + "/DemEnableConditionGroup/DemEnableConditionRef", m)


def build_data_element(parent, r):
    c = _container(parent, r["Name"], "DemDataElementClass", choice=True)
    subs = _subcontainers(c)
    if r["Source"].lower() == "external":
        inner = etree.SubElement(subs, etree.QName(AUTOSAR_NS, "ECUC-CONTAINER-VALUE"))
        inner.set("S", "USER_GENERATED")
        n = etree.SubElement(inner, etree.QName(AUTOSAR_NS, "SHORT-NAME"))
        n.text = "DemExternalSRDataElementClass"
        d = etree.SubElement(inner, etree.QName(AUTOSAR_NS, "DEFINITION-REF"))
        d.set("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
        d.text = DEM_GENERAL_DEF + "/DemDataElementClass/DemExternalSRDataElementClass"
        params = _params(inner)
        _text_param(params, d.text + "/DemDataElementEndianness", "OPAQUE")
        _text_param(params, d.text + "/DemDataElementDataType", r["DataType"])
    else:
        inner = etree.SubElement(subs, etree.QName(AUTOSAR_NS, "ECUC-CONTAINER-VALUE"))
        inner.set("S", "USER_GENERATED")
        n = etree.SubElement(inner, etree.QName(AUTOSAR_NS, "SHORT-NAME"))
        n.text = "DemInternalDataElementClass"
        d = etree.SubElement(inner, etree.QName(AUTOSAR_NS, "DEFINITION-REF"))
        d.set("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
        d.text = DEM_GENERAL_DEF + "/DemDataElementClass/DemInternalDataElementClass"
        params = _params(inner)
        _text_param(params, d.text + "/DemInternalDataElement", r["InternalElement"])
        _num_param(params, d.text + "/DemDataElementDataSize", "1")


def build_did_class(parent, r):
    c = _container(parent, r["Name"], "DemDidClass")
    params, refs = _params(c), _refs(c)
    _num_param(params, DEM_GENERAL_DEF + "/DemDidClass/DemDidIdentifier",
               str(int(r["DidHex"], 16)))
    for m in r["Members"].split():
        _ref_value(refs, DEM_GENERAL_DEF + "/DemDidClass/DemDidDataElementClassRef", m)


def build_freeze_frame_class(parent, r):
    c = _container(parent, r["Name"], "DemFreezeFrameClass")
    refs = _refs(c)
    for m in r["Members"].split():
        _ref_value(refs, DEM_GENERAL_DEF + "/DemFreezeFrameClass/DemDidClassRef", m)


def _record_container(parent, r, def_tail, update_def, number_def, trigger_def, ref_def):
    c = _container(parent, r["Name"], def_tail)
    params = _params(c)
    _text_param(params, update_def, r["Update"])
    _num_param(params, number_def, r["Number"])
    _text_param(params, trigger_def, r["Trigger"])
    members = r["Members"].split()
    if members:
        refs = _refs(c)
        for m in members:
            _ref_value(refs, ref_def, m)
    return c


def build_snapshot_record(parent, r):
    _record_container(
        parent, r, "DemFreezeFrameRecordClass",
        DEM_GENERAL_DEF + "/DemFreezeFrameRecordClass/DemFreezeFrameRecordUpdate",
        DEM_GENERAL_DEF + "/DemFreezeFrameRecordClass/DemFreezeFrameRecordNumber",
        DEM_GENERAL_DEF + "/DemFreezeFrameRecordClass/DemFreezeFrameRecordTrigger",
        None)


def build_extended_record(parent, r):
    _record_container(
        parent, r, "DemExtendedDataRecordClass",
        DEM_GENERAL_DEF + "/DemExtendedDataRecordClass/DemExtendedDataRecordUpdate",
        DEM_GENERAL_DEF + "/DemExtendedDataRecordClass/DemExtendedDataRecordNumber",
        DEM_GENERAL_DEF + "/DemExtendedDataRecordClass/DemExtendedDataRecordTrigger",
        DEM_GENERAL_DEF + "/DemExtendedDataRecordClass/DemDataElementClassRef")


def build_extended_data_class(parent, r):
    c = _container(parent, r["Name"], "DemExtendedDataClass")
    refs = _refs(c)
    for m in r["Members"].split():
        _ref_value(refs, DEM_GENERAL_DEF + "/DemExtendedDataClass/DemExtendedDataRecordClassRef", m)


def build_ff_recnum_class(parent, r):
    c = _container(parent, r["Name"], "DemFreezeFrameRecNumClass")
    refs = _refs(c)
    for m in r["Members"].split():
        _ref_value(refs, DEM_GENERAL_DEF + "/DemFreezeFrameRecNumClass/DemFreezeFrameRecordClassRef", m)


EFD_BUILDERS = {
    "DATA-ELEMENT": build_data_element,
    "DID-CLASS": build_did_class,
    "FREEZE-FRAME-CLASS": build_freeze_frame_class,
    "SNAPSHOT-RECORD": build_snapshot_record,
    "EXTENDED-RECORD": build_extended_record,
    "EXTENDED-DATA-CLASS": build_extended_data_class,
    "FF-RECNUM-CLASS": build_ff_recnum_class,
}


def resolve_or_fail(name, sheet_names, surviving, what, owner):
    if name in sheet_names or name in surviving:
        return name
    fail("%s %s 的 Members 引用不存在 (既不在 sheet 也不在 DemGeneral 存活容器): %s"
         % (what, owner, name))


def main():
    if len(sys.argv) != 5:
        print("用法: python gen_dem_general.py <原始xlsx> <arxml> <ecg:true|false> <efd:true|false>")
        sys.exit(1)
    excel_path, arxml_path = sys.argv[1], sys.argv[2]
    ecg_on = sys.argv[3].lower()
    efd_on = sys.argv[4].lower()
    for v in (ecg_on, efd_on):
        if v not in ("true", "false"):
            fail("ecg/efd 只接受 true/false, 实际 %r" % v)
    ecg_on, efd_on = ecg_on == "true", efd_on == "true"
    if not ecg_on and not efd_on:
        print("[gen_dem_general] 两个子开关均为 false, 跳过")
        return

    ec_rows, ecg_rows = (load_ecg_rows(excel_path) if ecg_on else ([], []))
    efd_rows = load_efd_rows(excel_path) if efd_on else []
    managed_names = collect_managed_names(ecg_on, efd_on, ec_rows, ecg_rows, efd_rows)

    # 读 arxml
    try:
        with open(arxml_path, "rb") as f:
            raw_content = f.read()
    except OSError as e:
        fail("读取 arxml 失败: %s" % e)
    original_xml_decl = extract_xml_declaration(raw_content)
    parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False,
                             resolve_entities=False, ns_clean=False)
    try:
        root = etree.fromstring(xml_decl_pattern.sub(b"", raw_content, count=1), parser)
    except etree.XMLSyntaxError as e:
        fail("解析 arxml 失败: %s" % e)

    subs = root.findall(".//ar:ECUC-CONTAINER-VALUE[ar:SHORT-NAME='DemGeneral']"
                        "/ar:SUB-CONTAINERS", NS_MAP)
    if len(subs) != 1:
        fail("DemGeneral/SUB-CONTAINERS 定位到 %d 个 (需恰好 1)" % len(subs))
    subs = subs[0]

    surviving = existing_general_names(root)  # 删除前快照 (成员引用解析用)
    removed = []
    if ecg_on:
        removed += delete_managed(subs, ECG_MANAGED_TYPES, managed_names)
    if efd_on:
        removed += delete_managed(subs, EFD_MANAGED_TYPES, managed_names)

    # 删除后存活集合 (引用解析以删除后为准, 防「sheet 删了被引用容器」悬空)
    surviving_after = existing_general_names(root)

    # 成员引用二次校验
    if ecg_on:
        for r in ecg_rows:
            for _, m in r["_members"]:
                resolve_or_fail(m, {x["Name"] for x in ec_rows}, surviving_after,
                                "ECG", r["Name"])
    if efd_on:
        sheet_names = {r["Name"] for r in efd_rows}
        dep = {"DID-CLASS": ("DATA-ELEMENT",), "FREEZE-FRAME-CLASS": ("DID-CLASS",),
               "EXTENDED-RECORD": ("DATA-ELEMENT",),
               "EXTENDED-DATA-CLASS": ("EXTENDED-RECORD",),
               "FF-RECNUM-CLASS": ("SNAPSHOT-RECORD",)}
        for r in efd_rows:
            allowed = dep.get(r["ItemKind"])
            for m in r["Members"].split():
                if m in surviving_after:
                    continue
                if allowed and any(x["Name"] == m and x["ItemKind"] in allowed
                                   for x in efd_rows):
                    continue
                fail("%s %s 的 Members %s 类型不符 (期望 %s) 或不存在"
                     % (EFD_SHEET, r["Name"], m, "/".join(allowed or ("<空>",))))

    # 构建并插入
    built = []
    if ecg_on:
        for r in ec_rows:
            build_ec(subs, r)
            built.append(r["Name"])
        for r in ecg_rows:
            build_ecg(subs, r)
            built.append(r["Name"])
    if efd_on:
        for r in efd_rows:
            EFD_BUILDERS[r["ItemKind"]](subs, r)
            built.append(r["Name"])

    # 序列化 (与 Create_* 同管线)
    tree = etree.ElementTree(root)
    xml_str = etree.tostring(tree, encoding="utf-8", pretty_print=False,
                             xml_declaration=False, standalone=None).decode("utf-8")
    xml_str = preprocess_xml_tags(xml_str)
    xml_str = format_xml_indent(xml_str)
    doctype = ""
    if b"<!DOCTYPE" in raw_content:
        doctype_start = raw_content.find(b"<!DOCTYPE")
        doctype_end = raw_content.find(b">", doctype_start) + 1
        doctype = raw_content[doctype_start:doctype_end].decode("utf-8") + "\n"
    with open(arxml_path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("%s\n%s%s" % (original_xml_decl, doctype, xml_str))

    print("[gen_dem_general] OK: 删除 %d 个旧容器, 生成 %d 个 (ecg=%s efd=%s)"
          % (len(removed), len(built), ecg_on, efd_on))
    if removed:
        print("[gen_dem_general]   removed: %s" % ", ".join(removed))


if __name__ == "__main__":
    main()
