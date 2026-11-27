"""解析 UDS 诊断问卷 CanTp 表 (CanTp sheet), 供 CanTp arxml 参数打补丁.

sheet 首行即表头, 列 = Connection + 各参数字段 + Remark. 空单元格 = 不改该参数.

行分三类 (按 Connection 列取值):
  CanTpGeneral  只消费 PaddingByte(hex) + PaddingActivation 两列
                (PaddingActivation 为全局开关, 打补丁时写两个 Rx / 两个 Tx 容器)
  CanTpConfig   只消费 MainFunctionPeriod(ms) 列
  <容器 SHORT-NAME>  其余行按 arxml 容器 SHORT-NAME 定位, 合法列由容器类型
                (CanTpRxNSdu / CanTpTxNSdu) 在 Patch_CanTpParams 中校验

单位换算: 所有 (ms) 列按 ms/1000 转成秒 (arxml FLOAT 参数单位).
"""

import sys
from types import SimpleNamespace

import openpyxl

SHEET = "CanTp"

COL_CONN = "Connection"
COL_PAD_BYTE = "PaddingByte(hex)"
COL_PAD_ACT = "PaddingActivation"
COL_PERIOD = "MainFunctionPeriod(ms)"
COL_BS = "BlockSize"
COL_STMIN = "STmin(ms)"
COL_NAS = "N_As(ms)"
COL_NBS = "N_Bs(ms)"
COL_NCS = "N_Cs(ms)"
COL_NAR = "N_Ar(ms)"
COL_NBR = "N_Br(ms)"
COL_NCR = "N_Cr(ms)"
COL_REMARK = "Remark"

HEADERS = [COL_CONN, COL_PAD_BYTE, COL_PAD_ACT, COL_PERIOD, COL_BS, COL_STMIN,
           COL_NAS, COL_NBS, COL_NCS, COL_NAR, COL_NBR, COL_NCR, COL_REMARK]

# 以 ms 为单位、需要 /1000 转秒的列
MS_COLUMNS = [COL_PERIOD, COL_STMIN, COL_NAS, COL_NBS, COL_NCS,
              COL_NAR, COL_NBR, COL_NCR]
# NSdu 行可用列 (BS 整数; 其余时序列 ms->秒)
NSDU_COLUMNS = [COL_BS, COL_STMIN, COL_NAS, COL_NBS, COL_NCS,
                COL_NAR, COL_NBR, COL_NCR]

GENERAL_ROW = "CanTpGeneral"
CONFIG_ROW = "CanTpConfig"


def _fail(msg):
    raise ValueError("CanTp 表解析错误: %s" % msg)


def _is_blank(v):
    return v is None or str(v).strip() == ""


def _to_int(v, what):
    if isinstance(v, bool):
        _fail("%s 必须是整数, 实际: %r" % (what, v))
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        if v != int(v):
            _fail("%s 必须是整数, 实际: %r" % (what, v))
        return int(v)
    s = str(v).strip()
    try:
        return int(s, 10)
    except ValueError:
        _fail("%s 必须是整数, 实际: %r" % (what, v))


def _to_hex_int(v, what):
    """PaddingByte(hex): 0xNN 前缀按 16 进制, 纯数字按 10 进制, 含字母按 16 进制."""
    if isinstance(v, bool):
        _fail("%s 必须是整数, 实际: %r" % (what, v))
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        if v != int(v):
            _fail("%s 必须是整数, 实际: %r" % (what, v))
        return int(v)
    s = str(v).strip()
    try:
        if s.lower().startswith("0x"):
            return int(s, 16)
        try:
            return int(s, 10)
        except ValueError:
            return int(s, 16)
    except ValueError:
        _fail("%s 必须是 16 进制整数, 实际: %r" % (what, v))


def _to_float(v, what):
    if isinstance(v, bool):
        _fail("%s 必须是数值, 实际: %r" % (what, v))
    try:
        return float(v)
    except (TypeError, ValueError):
        _fail("%s 必须是数值, 实际: %r" % (what, v))


def _to_padding_activation(v, what):
    s = str(v).strip().upper()
    if s in ("ON", "CANTP_ON", "TRUE", "1"):
        return "CANTP_ON"
    if s in ("OFF", "CANTP_OFF", "FALSE", "0"):
        return "CANTP_OFF"
    _fail("%s 必须是 ON/OFF (或 CANTP_ON/CANTP_OFF), 实际: %r" % (what, v))


def _convert(col, v, what):
    """按列名把单元格值转成 arxml 写入值 (ms 列已换算为秒)."""
    if col == COL_BS:
        return _to_int(v, what)
    if col in MS_COLUMNS:
        return _to_float(v, what) / 1000.0
    if col == COL_PAD_BYTE:
        return _to_hex_int(v, what)
    if col == COL_PAD_ACT:
        return _to_padding_activation(v, what)
    return str(v).strip()


def parse_cantp_excel(excel_path) -> SimpleNamespace:
    """解析 CanTp 表, 返回 SimpleNamespace.

    padding_byte: int|None            (CanTpGeneral 行 PaddingByte)
    padding_activation: str|None      (全局 CANTP_ON/CANTP_OFF)
    main_function_period: float|None  (秒)
    nsdu_rows: [{"name": SHORT-NAME, "values": {列名: 类型化值}}, ...]
    row_count: int                    (数据行总数, 含 General/Config)
    """
    try:
        wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    except Exception as e:
        _fail("打开 Excel 失败 %s: %s" % (excel_path, e))
    if SHEET not in wb.sheetnames:
        wb.close()
        _fail("缺少工作表 %r" % SHEET)
    ws = wb[SHEET]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        _fail("工作表 %r 为空" % SHEET)

    header = rows[0]
    col_idx = {}
    for i, h in enumerate(header):
        if h is not None and str(h).strip():
            col_idx[str(h).strip()] = i
    missing = [c for c in HEADERS if c != COL_REMARK and c not in col_idx]
    if missing:
        _fail("%r 缺少必需列: %s" % (SHEET, ", ".join(missing)))

    padding_byte = None
    padding_activation = None
    main_function_period = None
    nsdu_rows = []
    seen = set()
    data_rows = 0

    for ridx, row in enumerate(rows[1:], start=2):
        if all(_is_blank(v) for v in row):
            continue
        data_rows += 1
        what = "%r 第 %d 行" % (SHEET, ridx)

        name_v = row[col_idx[COL_CONN]]
        if _is_blank(name_v):
            _fail("%s 的 %s 列为空" % (what, COL_CONN))
        name = str(name_v).strip()
        if name in seen:
            _fail("%s 行名重复: %s" % (what, name))
        seen.add(name)

        def cell(col):
            i = col_idx.get(col)
            if i is None or i >= len(row):
                return None
            return row[i]

        if name == GENERAL_ROW:
            for col in NSDU_COLUMNS + [COL_PERIOD]:
                if not _is_blank(cell(col)):
                    _fail("%s (%s) 不允许填 %s 列, 该行只消费 %s + %s"
                          % (what, GENERAL_ROW, col, COL_PAD_BYTE, COL_PAD_ACT))
            if not _is_blank(cell(COL_PAD_BYTE)):
                padding_byte = _convert(COL_PAD_BYTE, cell(COL_PAD_BYTE),
                                        "%s 的 %s" % (what, COL_PAD_BYTE))
            if not _is_blank(cell(COL_PAD_ACT)):
                padding_activation = _convert(COL_PAD_ACT, cell(COL_PAD_ACT),
                                              "%s 的 %s" % (what, COL_PAD_ACT))
            continue

        if name == CONFIG_ROW:
            for col in NSDU_COLUMNS + [COL_PAD_BYTE, COL_PAD_ACT]:
                if not _is_blank(cell(col)):
                    _fail("%s (%s) 不允许填 %s 列, 该行只消费 %s"
                          % (what, CONFIG_ROW, col, COL_PERIOD))
            if not _is_blank(cell(COL_PERIOD)):
                main_function_period = _convert(
                    COL_PERIOD, cell(COL_PERIOD), "%s 的 %s" % (what, COL_PERIOD))
            continue

        # NSdu 行: 按容器 SHORT-NAME, 只允许 NSdu 参数列
        for col in [COL_PAD_BYTE, COL_PAD_ACT, COL_PERIOD]:
            if not _is_blank(cell(col)):
                _fail("%s (%s) 不允许填 %s 列, 该列为 %s/%s 专用"
                      % (what, name, col, GENERAL_ROW, CONFIG_ROW))
        values = {}
        for col in NSDU_COLUMNS:
            if not _is_blank(cell(col)):
                values[col] = _convert(col, cell(col), "%s 的 %s" % (what, col))
        if not values:
            _fail("%s (%s) 除行名外全部参数为空" % (what, name))
        nsdu_rows.append({"name": name, "values": values})

    if data_rows == 0:
        _fail("工作表 %r 未解析到任何数据行" % SHEET)
    if (padding_byte is None and padding_activation is None
            and main_function_period is None and not nsdu_rows):
        _fail("工作表 %r 未解析到任何可写入参数 (全部为空)" % SHEET)

    return SimpleNamespace(
        padding_byte=padding_byte,
        padding_activation=padding_activation,
        main_function_period=main_function_period,
        nsdu_rows=nsdu_rows,
        row_count=data_rows,
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python Parse_cantp_excel.py <excel_path>")
        sys.exit(1)
    try:
        data = parse_cantp_excel(sys.argv[1])
    except ValueError as e:
        print("错误：%s" % e)
        sys.exit(1)
    print("解析成功: %d 个数据行, %d 个 NSdu 行" % (data.row_count, len(data.nsdu_rows)))
    print("  PaddingByte        : %r" % data.padding_byte)
    print("  PaddingActivation  : %r" % data.padding_activation)
    print("  MainFunctionPeriod : %r s" % data.main_function_period)
    for r in data.nsdu_rows:
        print("  [NSdu] %-40s %s" % (r["name"], r["values"]))
