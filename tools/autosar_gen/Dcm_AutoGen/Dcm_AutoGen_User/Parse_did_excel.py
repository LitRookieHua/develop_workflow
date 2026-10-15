"""解析 UDS 诊断问卷的 DID List / NVM List 表 (供 gen_did_code 使用).

DID List 权限列记法 "22:Yes 2E:No": 22 = $22 读权限, 2E = $2E 写权限,
7 列 (三会话 + Locked/App/Boot/iMotion Unlocked) 分别给出该模式下读写是否允许.

用法:
  python Parse_did_excel.py <excel_path>
"""

import re
import sys
from types import SimpleNamespace

import openpyxl

DID_SHEET = "DID List"
NVM_SHEET = "NVM List"

DID_REQUIRED_COLS = [
    "DID (Hex)", "Name", "Support $22", "Support $2E", "Data Type", "Data Source",
    "Default Value", "Data Length (Byte)",
    "Default Session", "Programming Session", "Extended Session",
    "Locked", "App Unlocked", "Boot Unlocked", "iMotion Unlocked",
    "JIRA", "Remark",
]
NVM_REQUIRED_COLS = ["Name", "Block Length", "DID (Hex)", "Remark"]

DID_SOURCES = {"iMotionDid", "VersionDid", "NvmDid", "DynamicDid"}

# 会话/安全列名 → 内部位名 (生成枚举组合用)
SESSION_COLS = [("Default Session", "DEFAULT"),
                ("Programming Session", "PROGRAMMING"),
                ("Extended Session", "EXTENDED")]
# 内部位名须与 gen_did_code.SEC_ORDER 一致 (NORMAL_UNLOCK 等), 否则组合枚举会退化为 LOCK
SEC_COLS = [("Locked", "LOCK"),
            ("App Unlocked", "NORMAL_UNLOCK"),
            ("Boot Unlocked", "PROGRAMMING_UNLOCK"),
            ("iMotion Unlocked", "DEVELOPMENT_UNLOCK")]

PERM_RE = re.compile(r"^22:\s*(Yes|No)\s+2E:\s*(Yes|No)$")
SKIP_REMARK_KEYWORD = "Docan不实现"


def _fail(msg):
    raise ValueError("DID 问卷解析错误: %s" % msg)


def _parse_hex(v, what):
    s = str(v).strip()
    try:
        return int(s, 16)
    except ValueError:
        _fail("%s 非法十六进制值: %r" % (what, s))


def _cell_perm(row, col_idx, header, what):
    """解析 '22:Yes 2E:No' 单元格, 返回 (allow_22, allow_2e)."""
    v = row[col_idx[header]]
    s = str(v).strip() if v is not None else ""
    m = PERM_RE.match(s)
    if not m:
        _fail("%s 的 %s 列必须形如 '22:Yes 2E:No', 实际: %r" % (what, header, v))
    return m.group(1) == "Yes", m.group(2) == "Yes"


def _cell_yn(row, col_idx, header, what):
    v = row[col_idx[header]]
    s = str(v).strip() if v is not None else ""
    if s not in ("Yes", "No"):
        _fail("%s 的 %s 列必须为 Yes/No, 实际: %r" % (what, header, v))
    return s == "Yes"


def _header_index(rows, sheet):
    if len(rows) < 3:
        _fail("%s 工作表为空" % sheet)
    col_idx = {}
    for i, h in enumerate(rows[1]):
        if h is not None:
            col_idx[str(h).strip()] = i
    return col_idx, len(rows[1])


def _iter_data_rows(ws, sheet):
    """返回 (行号, 补齐宽度的值列表); 第 1 行标题, 第 2 行表头, 第 3 行起数据."""
    rows = list(ws.iter_rows(values_only=True))
    col_idx, width = _header_index(rows, sheet)
    for ridx, row in enumerate(rows[2:], start=3):
        if row is None:
            continue
        vals = list(row) + [None] * (width - len(row))
        yield ridx, vals, col_idx


def parse_did_excel(excel_path) -> SimpleNamespace:
    """
    返回 SimpleNamespace(dids=[...], nvm_blocks={...}):
    dids:       [{did, name, support_22, support_2e, data_type, source,
                  default_value, length, nvm_block,
                  read_sessions:set, write_sessions:set, read_sec:set, write_sec:set}]
    nvm_blocks: {did: (block_name, block_length)}
    """
    try:
        wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    except Exception as e:
        _fail("打开 Excel 失败 %s: %s" % (excel_path, e))

    if DID_SHEET not in wb.sheetnames:
        _fail("缺少工作表 %r" % DID_SHEET)
    if NVM_SHEET not in wb.sheetnames:
        _fail("缺少工作表 %r" % NVM_SHEET)

    dids = []
    did_by_id = {}
    skipped = []

    for ridx, row, col_idx in _iter_data_rows(wb[DID_SHEET], DID_SHEET):
        did_hex = row[col_idx["DID (Hex)"]]
        if did_hex is None or str(did_hex).strip() == "":
            continue
        what = "第 %d 行" % ridx

        remark = row[col_idx["Remark"]]
        if remark is not None and SKIP_REMARK_KEYWORD in str(remark):
            skipped.append(str(did_hex).strip())
            continue

        did = _parse_hex(did_hex, what + " DID (Hex)")
        if did in did_by_id:
            _fail("DID 重复: 0x%04X (第 %d 行)" % (did, ridx))

        name_v = row[col_idx["Name"]]
        name = str(name_v).strip() if name_v is not None else ""
        if not name:
            _fail("0x%04X 的 Name 为空" % did)

        support_22 = _cell_yn(row, col_idx, "Support $22", what)
        support_2e = _cell_yn(row, col_idx, "Support $2E", what)

        source_v = row[col_idx["Data Source"]]
        source = str(source_v).strip() if source_v is not None else ""
        if source not in DID_SOURCES:
            _fail("0x%04X 的 Data Source 必须为 %s, 实际: %r"
                  % (did, "/".join(sorted(DID_SOURCES)), source_v))

        data_type_v = row[col_idx["Data Type"]]
        data_type = str(data_type_v).strip() if data_type_v is not None else ""

        default_v = row[col_idx["Default Value"]]
        default_value = str(default_v) if default_v is not None else ""

        length_v = row[col_idx["Data Length (Byte)"]]
        try:
            length = int(length_v)
        except (TypeError, ValueError):
            _fail("0x%04X 的 Data Length (Byte) 非法: %r" % (did, length_v))
        if length <= 0:
            _fail("0x%04X 的 Data Length (Byte) 必须为正: %d" % (did, length))

        read_sessions, write_sessions = set(), set()
        for header, _part in SESSION_COLS:
            a22, a2e = _cell_perm(row, col_idx, header, what)
            if a22:
                read_sessions.add(_part)
            if a2e:
                write_sessions.add(_part)
        read_sec, write_sec = set(), set()
        for header, part in SEC_COLS:
            a22, a2e = _cell_perm(row, col_idx, header, what)
            if a22:
                read_sec.add(part)
            if a2e:
                write_sec.add(part)

        if not support_22 and (read_sessions or read_sec):
            _fail("0x%04X Support $22=No 但权限列有 22:Yes" % did)
        if not support_2e and (write_sessions or write_sec):
            _fail("0x%04X Support $2E=No 但权限列有 2E:Yes" % did)

        entry = {"did": did, "name": name, "support_22": support_22, "support_2e": support_2e,
                 "data_type": data_type, "source": source, "default_value": default_value,
                 "length": length, "nvm_block": None,
                 "read_sessions": read_sessions, "write_sessions": write_sessions,
                 "read_sec": read_sec, "write_sec": write_sec}
        dids.append(entry)
        did_by_id[did] = entry

    nvm_blocks = {}
    for ridx, row, col_idx in _iter_data_rows(wb[NVM_SHEET], NVM_SHEET):
        did_hex = row[col_idx["DID (Hex)"]]
        if did_hex is None or str(did_hex).strip() == "":
            continue
        what = "NVM List 第 %d 行" % ridx
        did = _parse_hex(did_hex, what + " DID (Hex)")
        name_v = row[col_idx["Name"]]
        block_name = str(name_v).strip() if name_v is not None else ""
        if not block_name:
            _fail("NVM List 0x%04X 的 Name 为空" % did)
        try:
            block_len = int(row[col_idx["Block Length"]])
        except (TypeError, ValueError):
            _fail("NVM List 0x%04X 的 Block Length 非法: %r" % (did, row[col_idx["Block Length"]]))
        if did in nvm_blocks:
            _fail("NVM List DID 重复: 0x%04X" % did)
        nvm_blocks[did] = (block_name, block_len)

    wb.close()

    if skipped:
        print("已跳过 Remark 含 %r 的 DID: %s" % (SKIP_REMARK_KEYWORD, ", ".join(skipped)))
    if not dids:
        _fail("未解析到任何 DID")

    return SimpleNamespace(dids=dids, nvm_blocks=nvm_blocks)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python Parse_did_excel.py <excel_path>")
        sys.exit(1)
    try:
        data = parse_did_excel(sys.argv[1])
    except ValueError as e:
        print("错误：%s" % e)
        sys.exit(1)
    print("解析成功: %d 个 DID, %d 个 NVM block" % (len(data.dids), len(data.nvm_blocks)))
    for d in sorted(data.dids, key=lambda x: x["did"]):
        rs = "/".join(sorted(d["read_sessions"])) or "-"
        ws = "/".join(sorted(d["write_sessions"])) or "-"
        rsec = "/".join(sorted(d["read_sec"])) or "-"
        wsec = "/".join(sorted(d["write_sec"])) or "-"
        print("  0x%04X %-30s len=%-3d %-10s 22=%d 2E=%d read[%s|%s] write[%s|%s]"
              % (d["did"], d["name"], d["length"], d["source"],
                 d["support_22"], d["support_2e"], rs, rsec, ws, wsec))
    for did, (name, length) in sorted(data.nvm_blocks.items()):
        print("  NVM 0x%04X -> %s (%dB)" % (did, name, length))
