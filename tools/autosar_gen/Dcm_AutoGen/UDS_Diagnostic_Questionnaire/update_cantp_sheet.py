# -*- coding: utf-8 -*-
"""新增/刷新 UDS 问卷 CanTp sheet + History 追加版本行.

用法:
  python update_cantp_sheet.py <xlsx_path> <mode>
    mode = j02      填入 J02 实际值 (CanTpGeneral/Config + 3 个 NSdu 容器)
    mode = template 仅表头 + 1 行空白样例

CanTp sheet 列 (第 1 行表头):
  Connection | PaddingByte(hex) | PaddingActivation | MainFunctionPeriod(ms) |
  BlockSize | STmin(ms) | N_As(ms) | N_Bs(ms) | N_Cs(ms) | N_Ar(ms) | N_Br(ms) |
  N_Cr(ms) | Remark

行分三类:
  CanTpGeneral  只填 PaddingByte(hex) + PaddingActivation
  CanTpConfig   只填 MainFunctionPeriod(ms)
  <容器 SHORT-NAME>  其余行填 NSdu 参数 (Rx: BS/STmin/N_Ar/N_Br/N_Cr;
                     Tx: N_As/N_Bs/N_Cs)
"""

import sys

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

SHEET = "CanTp"
HEADERS = ["Connection", "PaddingByte(hex)", "PaddingActivation",
           "MainFunctionPeriod(ms)", "BlockSize", "STmin(ms)", "N_As(ms)",
           "N_Bs(ms)", "N_Cs(ms)", "N_Ar(ms)", "N_Br(ms)", "N_Cr(ms)", "Remark"]
WIDTHS = [38, 16, 16, 20, 10, 10, 10, 10, 10, 10, 10, 10, 44]

HEAD_FILL = PatternFill('solid', fgColor='1F4E78')
HEAD_FONT = Font(name='宋体', bold=True, color='FFFFFF', size=10)
CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
THIN = Side(style='thin', color='B0B0B0')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

# J02 实际值 (per C097FAWVWREQ-95/98~105, v3 定案)
J02_ROWS = [
    # Connection, PaddingByte, PaddingAct, Period, BS, STmin, NAs, NBs, NCs, NAr, NBr, NCr, Remark
    ["CanTpGeneral", "0x00", "ON", None, None, None, None, None, None, None, None, None,
     "全局: PaddingByte=0x00, PaddingActivation 同时写 2 Rx + 2 Tx 容器"],
    ["CanTpConfig", None, None, 10, None, None, None, None, None, None, None, None,
     "CanTpMainFunctionPeriod = 10ms"],
    ["RX_UdsRxPhy_Can_Network_Channel", None, None, None, 0, 10, None, None, None, 1000, 60, 1000,
     "CanTpRxNSdu: Bs/STmin/N_Ar/N_Br/N_Cr"],
    ["RX_UdsRxFnc_Can_Network_Channel", None, None, None, 0, 10, None, None, None, 1000, 60, 1000,
     "CanTpRxNSdu: Bs/STmin/N_Ar/N_Br/N_Cr"],
    ["TX_UdsTxPhy_Can_Network_Channel", None, None, None, None, None, 1000, 1000, 60, None, None, None,
     "CanTpTxNSdu: N_As/N_Bs/N_Cs"],
]

TEMPLATE_LEGEND = [
    ["CanTpGeneral", None, None, None, None, None, None, None, None, None, None, None,
     "只填 PaddingByte(hex) + PaddingActivation (ON/OFF)"],
    ["CanTpConfig", None, None, None, None, None, None, None, None, None, None, None,
     "只填 MainFunctionPeriod(ms)"],
    ["<RX 容器 SHORT-NAME>", None, None, None, None, None, None, None, None, None, None, None,
     "Rx NSdu: BlockSize/STmin/N_Ar/N_Br/N_Cr (ms)"],
    ["<TX 容器 SHORT-NAME>", None, None, None, None, None, None, None, None, None, None, None,
     "Tx NSdu: N_As/N_Bs/N_Cs (ms)"],
]


def _build_sheet(wb):
    if SHEET in wb.sheetnames:
        idx = wb.sheetnames.index(SHEET)
        del wb[SHEET]
    else:
        idx = wb.sheetnames.index("General") + 1 if "General" in wb.sheetnames else 1
    ws = wb.create_sheet(SHEET, idx)

    for c, h in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.fill = HEAD_FILL; cell.font = HEAD_FONT
        cell.alignment = CENTER; cell.border = BORDER
    ws.row_dimensions[1].height = 30
    for i, w in enumerate(WIDTHS, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    return ws


def _write_rows(ws, rows, blank_row_after):
    for r, row in enumerate(rows, start=2):
        for c, v in enumerate(row, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.border = BORDER
            if c in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
                cell.alignment = CENTER
    last = 2 + len(rows)
    for r in range(last, last + blank_row_after):
        for c in range(1, len(HEADERS) + 1):
            ws.cell(row=r, column=c).border = BORDER
    ws.freeze_panes = "B2"
    # PaddingActivation 数据有效性 (ON/OFF)
    dv = DataValidation(type='list', formula1='"ON,OFF"', allow_blank=True,
                        errorStyle='warning')
    ws.add_data_validation(dv)
    dv.add("C2:C%d" % (last + blank_row_after))


def _bump_version(wb):
    """History 表末版本号 +1, 追加一行. 返回 (新增行号, 版本)."""
    ws = wb["History"]
    last_row = None
    last_ver = None
    for r in range(2, ws.max_row + 1):
        v = ws.cell(row=r, column=1).value
        if v is not None and str(v).strip().upper().startswith("V"):
            last_row = r
            last_ver = str(v).strip()
    if last_ver is None:
        raise SystemExit("History 表未找到版本行")
    # V1.4 -> V1.5
    body = last_ver[1:]
    if "." in body:
        major, minor = body.split(".", 1)
        new_ver = "V%s.%d" % (major, int(minor) + 1)
    else:
        new_ver = "V%d" % (int(body) + 1)

    author = ws.cell(row=last_row, column=3).value  # 复用上一行作者 (避免编码问题)
    new_row = last_row + 1
    ws.cell(row=new_row, column=1, value=new_ver)
    ws.cell(row=new_row, column=2, value="2026-11-27")
    ws.cell(row=new_row, column=3, value=author)
    ws.cell(row=new_row, column=4, value=(
        "Add CanTp sheet (CanTpGeneral/CanTpConfig + 3 NSdu containers): "
        "PaddingByte/PaddingActivation/MainFunctionPeriod + Rx/Tx timing/size params; "
        "Dcm_AutoGen gen_cantp_arxml consumes it to patch J6B_CanTp_EcucValues.arxml. "
        "Values per C097FAWVWREQ-95/98~105 (J02 v3)."))
    return new_row, new_ver


def main():
    if len(sys.argv) != 3 or sys.argv[2] not in ("j02", "template"):
        print("用法: python update_cantp_sheet.py <xlsx_path> <j02|template>")
        sys.exit(1)
    path, mode = sys.argv[1], sys.argv[2]

    wb = openpyxl.load_workbook(path)
    ws = _build_sheet(wb)
    if mode == "j02":
        _write_rows(ws, J02_ROWS, blank_row_after=0)
        new_row, new_ver = _bump_version(wb)
        wb.save(path)
        print("updated %s (mode=j02): CanTp sheet + History %s (row %d)"
              % (path, new_ver, new_row))
    else:
        _write_rows(ws, TEMPLATE_LEGEND, blank_row_after=1)
        wb.save(path)
        print("updated %s (mode=template): CanTp sheet only (History unchanged)" % path)


if __name__ == "__main__":
    main()
