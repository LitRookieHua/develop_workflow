"""解析 UDS 诊断问卷 Excel 的 Service List 表 (参考 Dem_AutoGen_Etas Parse_excel_list.py 风格)."""

import sys
from types import SimpleNamespace

import openpyxl

from Create_DcmDsdServices import SESSION_MAP, SECURITY_MAP

SHEET_NAME = "Service List"

REQUIRED_COLS = ["Service (Hex)", "Service (Name)", "Sub-function (Hex)", "Sub-function (Name)",
                 "Service Callback Function", "NRC22", "SPRMIB", "Addressing Mode",
                 "Default Session", "Programming Session",
                 "Extended Session", "Locked", "App Unlocked", "Boot Unlocked",
                 "iMotion Unlocked", "Remark"]

# 会话/安全列允许的取值
YN_VALUES = {"Y", "N"}
# Addressing Mode 列允许的取值 (P=仅物理, P/F=物理+功能)
ADDR_VALUES = {"P", "P/F", "PF"}
# Sub-function (Hex) 表示"无子服务"的占位值
NO_SUB_MARKERS = {"/", "", None}
# Remark 含该关键字符串的服务跳过 (不生成 DcmDsdService)
SKIP_REMARK_KEYWORD = "Docan不实现"


def _fail(msg):
    raise ValueError("Service List 解析错误: %s" % msg)


def _norm_name(name):
    """SHORT-NAME 规范化: 去首尾空白, 空格转下划线."""
    return str(name).strip().replace(" ", "_")


def _parse_hex(v, what):
    s = str(v).strip()
    try:
        return int(s, 16)
    except ValueError:
        _fail("%s 非法十六进制值: %r" % (what, s))


def _cell_yn(row, col_idx, header, what):
    v = row[col_idx[header]]
    s = str(v).strip().upper() if v is not None else ""
    if s not in YN_VALUES:
        _fail("%s 的 %s 列必须为 Y/N, 实际: %r" % (what, header, v))
    return s == "Y"


def _parse_sessions_and_security(row, col_idx, what):
    """读会话三列 + Locked + 安全三列, 返回 (sessions, sec_levels)."""
    sessions = set()
    for header, target in SESSION_MAP:
        if _cell_yn(row, col_idx, header, what):
            sessions.add(target)
    sec_levels = set()
    locked = _cell_yn(row, col_idx, "Locked", what)
    if not locked:
        for header, target in SECURITY_MAP:
            if _cell_yn(row, col_idx, header, what):
                sec_levels.add(target)
    return sessions, sec_levels


def _parse_nrc_columns(row, col_idx, what):
    """读 NRC22/SPRMIB/Addressing Mode 三列, 返回 (nrc22: bool, sprmib: bool, addressing: str)."""
    nrc22 = _cell_yn(row, col_idx, "NRC22", what)
    sprmib = _cell_yn(row, col_idx, "SPRMIB", what)
    addr_v = row[col_idx["Addressing Mode"]]
    addressing = str(addr_v).strip().upper() if addr_v is not None else ""
    if addressing not in ADDR_VALUES:
        _fail("%s 的 Addressing Mode 列必须为 P/P/F, 实际: %r" % (what, addr_v))
    return nrc22, sprmib, addressing


def parse_dcm_excel(excel_path) -> SimpleNamespace:
    """
    返回 SimpleNamespace(services=[...], service_count=N):
    services: [{name, service_id, callback, has_sub, subs, sessions, sec_levels}]
    subs:     [{name, sub_id, sessions, sec_levels}]
    """
    try:
        wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    except Exception as e:
        _fail("打开 Excel 失败 %s: %s" % (excel_path, e))
    if SHEET_NAME not in wb.sheetnames:
        _fail("缺少工作表 %r" % SHEET_NAME)
    ws = wb[SHEET_NAME]

    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if len(rows) < 2:
        _fail("工作表为空")

    # 第 1 行为标题 "UDS Service List", 第 2 行为表头
    header_row = rows[1]
    col_idx = {}
    for i, h in enumerate(header_row):
        if h is not None:
            col_idx[str(h).strip()] = i
    missing = [c for c in REQUIRED_COLS if c not in col_idx]
    if missing:
        _fail("缺少必需列: %s" % ", ".join(missing))

    # 跳过表头前缀行, 数据从第 3 行 (index 2) 开始
    services = []
    svc_by_id = {}
    skipped = []
    for ridx, row in enumerate(rows[2:], start=3):
        if row is None or all(v is None or str(v).strip() == "" for v in row):
            continue

        svc_hex = row[col_idx["Service (Hex)"]]
        if svc_hex is None or str(svc_hex).strip() == "":
            continue
        what = "第 %d 行" % ridx

        remark = row[col_idx["Remark"]]
        remark_str = str(remark) if remark is not None else ""
        if SKIP_REMARK_KEYWORD in remark_str:
            skipped.append("%s(0x%02X)" % (str(svc_hex).strip(), _parse_hex(svc_hex, what)))
            continue

        service_id = _parse_hex(svc_hex, what + " Service (Hex)")
        svc_name = _norm_name(row[col_idx["Service (Name)"]] or _fail("%s Service (Name) 为空" % what))
        callback = row[col_idx["Service Callback Function"]]
        callback = str(callback).strip() if callback is not None and str(callback).strip() != "" else None

        sub_hex = row[col_idx["Sub-function (Hex)"]]
        has_sub = str(sub_hex).strip() not in NO_SUB_MARKERS if sub_hex is not None else True

        row_nrc22, row_sprmib, row_addressing = _parse_nrc_columns(row, col_idx, what)

        if service_id not in svc_by_id:
            if any(s["name"] == svc_name for s in services):
                _fail("服务名重复: %s" % svc_name)
            svc = {"name": svc_name, "service_id": service_id, "callback": callback,
                   "has_sub": has_sub, "subs": [], "sessions": set(), "sec_levels": set(),
                   "addressing": row_addressing, "sprmib": row_sprmib, "nrc22": None}
            services.append(svc)
            svc_by_id[service_id] = svc
        else:
            svc = svc_by_id[service_id]

        # 同一服务多行: 校验一致性
        if svc["name"] != svc_name:
            _fail("服务 0x%02X 的名称不一致: %s vs %s" % (service_id, svc["name"], svc_name))
        if svc["callback"] != callback:
            _fail("服务 0x%02X (%s) 的回调不一致: %r vs %r"
                  % (service_id, svc_name, svc["callback"], callback))
        if svc["has_sub"] != has_sub:
            _fail("服务 0x%02X (%s) 的子服务有无不一致 (有的行有子功能, 有的没有)" % (service_id, svc_name))
        if svc["addressing"] != row_addressing:
            _fail("服务 0x%02X (%s) 的 Addressing Mode 不一致: %s vs %s"
                  % (service_id, svc_name, svc["addressing"], row_addressing))
        if svc["sprmib"] != row_sprmib:
            _fail("服务 0x%02X (%s) 的 SPRMIB 不一致" % (service_id, svc_name))

        if not has_sub:
            # 无子服务: 权限写在 service 层, 同服务多行权限取并集
            sessions, sec_levels = _parse_sessions_and_security(row, col_idx, what)
            svc["sessions"] |= sessions
            svc["sec_levels"] |= sec_levels
            if svc["nrc22"] is None:
                svc["nrc22"] = row_nrc22
            elif svc["nrc22"] != row_nrc22:
                _fail("服务 0x%02X (%s) 无子服务但多行 NRC22 不一致" % (service_id, svc_name))
        else:
            sub_name = _norm_name(row[col_idx["Sub-function (Name)"]]
                                  or _fail("%s Sub-function (Name) 为空" % what))
            if any(s["name"] == sub_name for s in svc["subs"]):
                _fail("服务 0x%02X (%s) 的子服务名重复: %s (请先在 Excel 中消歧)"
                      % (service_id, svc_name, sub_name))
            sub_id = _parse_hex(sub_hex, what + " Sub-function (Hex)")
            sessions, sec_levels = _parse_sessions_and_security(row, col_idx, what)
            svc["subs"].append({"name": sub_name, "sub_id": sub_id,
                                "sessions": sessions, "sec_levels": sec_levels,
                                "nrc22": row_nrc22})

    if skipped:
        print("已跳过 Remark 含 %r 的服务: %s" % (SKIP_REMARK_KEYWORD, ", ".join(skipped)))
    if not services:
        _fail("未解析到任何服务")

    return SimpleNamespace(services=services, service_count=len(services))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python Parse_dcm_excel.py <excel_path>")
        sys.exit(1)
    data = parse_dcm_excel(sys.argv[1])
    print("解析成功: %d 个服务" % data.service_count)
    for s in data.services:
        nrc22_desc = ("subs:%s" % ",".join("0x%02X" % x["sub_id"] for x in s["subs"] if x["nrc22"])
                      if s["has_sub"] else ("Y" if s["nrc22"] else "N"))
        print("  0x%02X %-32s subs=%d callback=%s addr=%s sprmib=%s nrc22=%s"
              % (s["service_id"], s["name"], len(s["subs"]), s["callback"],
                 s["addressing"], "Y" if s["sprmib"] else "N", nrc22_desc))
