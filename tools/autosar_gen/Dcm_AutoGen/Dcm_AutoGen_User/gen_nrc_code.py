"""gen_nrc_code - 根据 UDS 诊断问卷 Service List 重新生成 ov_dia_notification.cpp 的 NRC 检查逻辑.

三条规则 (Excel 列 → switch(SID) case 内检查, 顺序即 NRC 优先级):
  1. 功能寻址不回复     Addressing Mode = P (仅物理寻址)
  2. 抑制肯定响应 NRC12  SPRMIB = N 且该服务有子功能 (bit7 置位 → NRC 0x12)
  3. NRC22 条件检查      NRC22 = Y (电压+车速条件; 部分子服务 Y 时按子功能值门控)

替换范围: ..._Indication 函数内的整个 switch (SID) 语句, 用 AUTO-GENERATED 标记对包裹,
函数其余部分 (include/宏/全局变量/doc 注释/Confirmation) 逐字节保留.

用法:
  python gen_nrc_code.py <excel_path> <cpp_path>   (原地修改 cpp)
"""

import sys
from pathlib import Path

GEN_TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(GEN_TOOLS.parent / "Dcm_AutoGen_Etas" / "gen_dcm_arxml"))
from Parse_dcm_excel import parse_dcm_excel  # noqa: E402

INDICATION_FUNC = "ServiceRequestSupplierNotification_DcmDsdServiceRequestSupplierNotification_Indication"
MARK_BEGIN = "/* ===== NRC AUTO-GENERATED BEGIN (source: UDS Diagnostic Questionnaire Service List) ===== */"
MARK_END = "/* ===== NRC AUTO-GENERATED END ===== */"

# 检查块模板 (相对缩进: 首行 0, 续行按嵌套层级; 生成时统一加基础缩进)
FUNC_CHECK = """if (ReqType == DCM_FUNCTIONAL_REQUEST)
{
    l_DcmReturn_e = DCM_E_REQUEST_NOT_ACCEPTED;
}"""

NRC12_CHECK = """if ((DataSize > idia::E_CONST_VALUE_ZERO)&&(((RequestData[0]) & 0x80) != 0))
{
    *ErrorCode    = DCM_E_SUBFUNCTIONNOTSUPPORTED;
    l_DcmReturn_e = E_NOT_OK;
}"""

NRC22_CONDITION = """if(((KL30_GetVoltValue() < 9000) || (KL30_GetVoltValue() > 16000))
    ||(ov_dia::Cov_diaRunnable::ov_dia_getInstance()->GetVehicleSpeed() > 3.0f))
{
    *ErrorCode    = DCM_E_CONDITIONSNOTCORRECT;
    l_DcmReturn_e = E_NOT_OK;
}"""


def _indent(block, spaces):
    return "\n".join((" " * spaces + line) if line else line for line in block.split("\n"))


def _sub_test(sub_id):
    return "(((RequestData[0]) & 0x7F) == 0x%02X)" % sub_id


def build_checks(svc):
    """按三条规则生成一个服务的检查块列表 [(注释, 代码)] ; 空列表 = 不生成 case."""
    checks = []

    # 规则1: 仅物理寻址 → 功能寻址不回复
    if svc["addressing"] == "P":
        checks.append(("Functional addressing not supported (Addressing Mode = P): no response",
                       FUNC_CHECK))

    # 规则2: SPRMIB=N 且有子功能 → bit7 置位上报 NRC 0x12
    if not svc["sprmib"] and svc["has_sub"]:
        checks.append(("NRC 0x12: suppress positive response bit not supported (SPRMIB = N)",
                       NRC12_CHECK))

    # 规则3: NRC22 条件检查
    if svc["has_sub"]:
        nrc22_subs = [x for x in svc["subs"] if x["nrc22"]]
        if nrc22_subs:
            if len(nrc22_subs) == len(svc["subs"]):
                checks.append(("NRC 0x22: voltage and vehicle speed conditions",
                               NRC22_CONDITION))
            else:
                sub_ids = " / ".join("0x%02X" % x["sub_id"] for x in nrc22_subs)
                tests = [_sub_test(x["sub_id"]) for x in nrc22_subs]
                gate = tests[0] if len(tests) == 1 else "(%s)" % " || ".join(tests)
                checks.append((
                    "NRC 0x22: voltage and vehicle speed conditions, only for sub-function %s" % sub_ids,
                    "if %s\n{\n%s\n}" % (gate, _indent(NRC22_CONDITION, 4)),
                ))
    elif svc["nrc22"]:
        checks.append(("NRC 0x22: voltage and vehicle speed conditions", NRC22_CONDITION))

    return checks


def _format_check(check_code, first):
    """链首用 if, 其后 else if; 基础缩进 8 (case 体层级), 续行保留相对缩进."""
    lines = check_code.split("\n")
    head = "        " + lines[0] if first else "        else " + lines[0]
    return head + "\n" + _indent("\n".join(lines[1:]), 8)


def build_switch(services):
    """生成整棵 switch (SID) 语句文本 (含标记对, LF 行尾; 由调用方统一转目标换行符)."""
    parts = ["    " + MARK_BEGIN,
             "    switch (SID)",
             "    {"]
    n_cases = 0
    for svc in sorted(services, key=lambda s: s["service_id"]):
        checks = build_checks(svc)
        if not checks:
            continue
        n_cases += 1
        parts.append("    case 0x%02X:" % svc["service_id"])
        for i, (comment, code) in enumerate(checks, 1):
            parts.append("        /* %d. %s */" % (i, comment))
            parts.append(_format_check(code, first=(i == 1)))
        parts.append("        break;")
        parts.append("")
    parts.append("    default:")
    parts.append("        break;")
    parts.append("    }")
    parts.append("    " + MARK_END)
    return "\n".join(parts), n_cases


def _find_switch_region(text):
    """在 Indication 函数体内定位 switch (SID) 语句所在行的 [start, end) 区间 (花括号配对, 跳过注释/字符串)."""
    # 跳过 extern "C" 里的函数声明: 取函数实现 (最后一次出现的签名)
    fn_pos = text.rfind(INDICATION_FUNC)
    if fn_pos < 0:
        raise RuntimeError("未找到函数 %s" % INDICATION_FUNC)
    sw_pos = text.find("switch (SID)", fn_pos)
    if sw_pos < 0:
        raise RuntimeError("函数内未找到 switch (SID)")
    open_pos = text.find("{", sw_pos)
    if open_pos < 0:
        raise RuntimeError("switch 后未找到 '{'")

    depth = 0
    i = open_pos
    in_block_comment = in_line_comment = in_string = False
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
        elif in_line_comment:
            if ch == "\n":
                in_line_comment = False
        elif in_string:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_string = False
        else:
            if ch == "/" and nxt == "*":
                in_block_comment = True
                i += 2
                continue
            if ch == "/" and nxt == "/":
                in_line_comment = True
                i += 2
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    line_start = text.rfind("\n", 0, sw_pos) + 1
                    return line_start, i + 1
        i += 1
    raise RuntimeError("switch 语句的花括号未配对")


def _line_start_of(text, pos):
    """回退到 pos 所在行首, 并校验行内 pos 前只有空白."""
    line_start = text.rfind("\n", 0, pos) + 1
    if text[line_start:pos].strip():
        raise RuntimeError("位置 %d 前有非空白内容: %r" % (pos, text[line_start:pos]))
    return line_start


def regenerate_cpp(text, services):
    """返回 (新文本, case 数) ; 保持原换行符, 函数其余部分逐字节保留."""
    nl = "\r\n" if "\r\n" in text else "\n"
    new_switch, n_cases = build_switch(services)
    new_switch = new_switch.replace("\n", nl)

    if MARK_BEGIN in text:
        if text.count(MARK_BEGIN) != 1 or text.count(MARK_END) != 1:
            raise RuntimeError("AUTO-GENERATED 标记不配对 (BEGIN=%d, END=%d)"
                               % (text.count(MARK_BEGIN), text.count(MARK_END)))
        start = _line_start_of(text, text.index(MARK_BEGIN))
        end = text.index(MARK_END) + len(MARK_END)
    else:
        start, end = _find_switch_region(text)

    return text[:start] + new_switch + text[end:], n_cases


def main():
    if len(sys.argv) != 3:
        print("用法: python gen_nrc_code.py <excel_path> <cpp_path>")
        print("示例: python gen_nrc_code.py UDS_Diagnostic_Questionnaire_J02.xlsx ov_dia_notification.cpp")
        sys.exit(1)
    excel_path, cpp_path = sys.argv[1], sys.argv[2]

    try:
        dcm_data = parse_dcm_excel(excel_path)
    except ValueError as e:
        print("错误：%s" % e)
        sys.exit(1)

    try:
        with open(cpp_path, encoding="utf-8", newline="") as f:
            text = f.read()
    except FileNotFoundError:
        print("错误：cpp 不存在: %s" % cpp_path)
        sys.exit(1)

    try:
        new_text, n_cases = regenerate_cpp(text, dcm_data.services)
    except RuntimeError as e:
        print("错误：%s" % e)
        sys.exit(1)

    with open(cpp_path, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)

    print("=== 生成摘要 (共 %d 个 case) ===" % n_cases)
    for svc in sorted(dcm_data.services, key=lambda s: s["service_id"]):
        checks = build_checks(svc)
        if checks:
            rules = " + ".join(c[0].split(":")[0] for c in checks)
            print("  0x%02X %-30s %s" % (svc["service_id"], svc["name"], rules))
        else:
            print("  0x%02X %-30s 无规则命中, 不生成 case" % (svc["service_id"], svc["name"]))
    print("已写入: %s" % cpp_path)


if __name__ == "__main__":
    main()
