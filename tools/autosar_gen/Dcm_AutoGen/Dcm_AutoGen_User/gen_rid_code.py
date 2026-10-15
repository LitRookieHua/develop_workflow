# -*- coding: utf-8 -*-
"""根据 UDS 问卷 RID List 生成 0x31 处理器 (纯 NRC 骨架).

生成内容 (4 个标记区, 区外逐字节保留):
  cpp: RID REGISTRY (ROUTINE_NUMBER/对象/注册表/getter) + RID HANDLER (per-RID 类方法)
  hpp: RID ENUM (ERoutineIDs) + RID CLASS (per-RID 类声明)

每个 RID 类实现 NRC13 (长度) / NRC31 (会话) / NRC33 (安全) 校验;
NRC22 留空 TODO; excute/fill 为 TODO 骨架, 业务逻辑手动接入。

用法:
  python gen_rid_code.py <excel> <vehicle_dir>
    vehicle_dir = dia_cfg/var/src/vehicle/<variant> 目录 (如 ...\\cpj_fawvw\\dia_cfg\\var\\src\\vehicle\\j02)
"""

import argparse
import re
import sys
from pathlib import Path

from Parse_rid_excel import VALID_CONTROL, parse_rid_excel
from gen_did_code import (_line_start, _match_brace, _read_file, _regen_region,
                          _write_file)

RID_SOURCE = "source: UDS Diagnostic Questionnaire RID List"

# Control Type 集合 -> idia::ESubfunctionSupported (idia_dcm_helper.hpp)
SUBFUNC_MAP = {
    frozenset({0x01}): "E_START_SUPPORTED",
    frozenset({0x02}): "E_STOP_SUPPORTED",
    frozenset({0x03}): "E_RESULTS_SUPPORTED",
    frozenset({0x01, 0x02}): "E_START_STOP_SUPPORTED",
    frozenset({0x01, 0x03}): "E_START_RESULT_SUPPORTED",
    frozenset({0x01, 0x02, 0x03}): "E_START_STOP_RESULT_SUPPORTED",
}

# 会话列 -> 会话宏 (idia_dcm_helper.hpp)
SESSION_MACRO = {"DEFAULT": "DEFAULT_SESSION",
                 "PROGRAMMING": "PROGRAMMING_SESSION",
                 "EXTENDED": "EXTENDED_SESSION"}
SESSION_ORDER = ["DEFAULT", "PROGRAMMING", "EXTENDED"]

# 安全列 -> 安全等级表达式 (DcmDspSecurityLevel 按 27 子功能配对: seed/key=2n-1/2n -> level n;
# J02: App 0x03/0x04 -> E_SECURITY_LEVEL_2, Boot 0x11/0x12 -> E_SECURITY_LEVEL_9)
SEC_LEVEL = {"LOCK": "idia::E_SECURITY_LEVEL_NULL",
             "APP": "idia::E_SECURITY_LEVEL_2",
             "BOOT": "idia::E_SECURITY_LEVEL_9",
             "IMOTION": "idia::E_SECURITY_LEVEL_49"}
SEC_ORDER = ["LOCK", "APP", "BOOT", "IMOTION"]

IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _fail(msg):
    print("错误：%s" % msg)
    sys.exit(1)


# ---------------------------------------------------------------- 命名派生

def _derive_names(name, rid):
    words = [w for w in re.split(r"[\s/_-]+", str(name).strip()) if w]
    if not words:
        _fail("0x%04X 的 Name 无法派生标识符: %r" % (rid, name))
    for w in words:
        if not IDENT_RE.match(w):
            _fail("0x%04X 的 Name 含非法标识符字符: %r" % (rid, w))
    camel = "".join(w[0].upper() + w[1:] for w in words)
    return {"cls": "C" + camel,
            "enum": "E_RID_ROUTINE_" + "_".join(w.upper() for w in words),
            "obj": "l_" + camel + "_obj"}


def _sec_exprs(sec_set):
    out = []
    for part in SEC_ORDER:
        if part in sec_set:
            out.append(SEC_LEVEL[part])
    return out


# ---------------------------------------------------------------- 区域定位

def _locate_registry(text):
    m = re.search(r"^[ \t]*#define ROUTINE_NUMBER", text, re.M)
    g = re.search(r"\bidia::getRoutineHandler\s*\(\s*\)", text)
    if not m:
        raise RuntimeError("未找到 #define ROUTINE_NUMBER")
    if not g:
        raise RuntimeError("未找到 idia::getRoutineHandler()")
    brace = text.find("{", g.end())
    if brace < 0:
        raise RuntimeError("getRoutineHandler 后未找到 '{'")
    return _line_start(text, m.start()), _match_brace(text, brace)


def _locate_handlers(text):
    m = re.search(r"^[ \t]*(?:void|idia::ERoutineStatus)\s+ov_dia::C(?!Cus)\w+::", text, re.M)
    if not m:
        raise RuntimeError("未找到 per-RID 类方法定义区")
    # 回退到方法上方连续注释块 (banner) 的首行, 避免 banner 半截残留在区外
    pos = _line_start(text, m.start())
    while pos > 0:
        prev_end = pos - 1
        if prev_end > 0 and text[prev_end - 1] == "\r":
            prev_end -= 1
        prev_start = _line_start(text, prev_end - 1) if prev_end > 0 else 0
        if text[prev_start:prev_end].lstrip().startswith("//"):
            pos = prev_start
        else:
            break
    stop = len(text)
    while stop > pos and text[stop - 1] in "\r\n":
        stop -= 1
    return pos, stop


def _locate_enum(text):
    close = text.find("} ERoutineIDs;")
    if close < 0:
        raise RuntimeError("未找到 ERoutineIDs 枚举")
    open_ = text.rfind("typedef enum", 0, close)
    if open_ < 0:
        raise RuntimeError("ERoutineIDs 枚举缺少 typedef enum")
    return _line_start(text, open_), close + len("} ERoutineIDs;")


def _locate_classes(text):
    m = re.search(r"^[ \t]*//[^\n]*\(RID 0x", text, re.M)
    cm = re.search(r"^[ \t]*class C\w+ : public ov_dia::CCusRoutineControl", text, re.M)
    if m:
        banner = text.rfind("//====", 0, m.start())
        start = _line_start(text, banner if banner >= 0 else m.start())
    elif cm:
        start = _line_start(text, cm.start())
    else:
        raise RuntimeError("未找到 per-RID 类声明区")
    ns = text.find("} // namespace ov_dia")
    if ns < 0 or ns < start:
        raise RuntimeError("未找到 '} // namespace ov_dia' 或顺序异常")
    ls = _line_start(text, ns)
    return start, ls - 2 if text[ls - 2:ls] == "\r\n" else ls - 1


# ---------------------------------------------------------------- cpp 生成

def _registry_inner(entries):
    lines = ["#define ROUTINE_NUMBER (%d)" % len(entries),
             "// handler object for routine control",
             "ov_dia::CCusRoutineControlProcessing l_routineHandler_obj;",
             "",
             "// Object for obj"]
    for e in entries:
        lines.append("    static ov_dia::%s" % e["cls"])
        lines.append("    %s(ov_dia::%s, idia::%s);" % (e["obj"], e["enum"], e["subfunc"]))
        lines.append("")
    lines += ["// registry handler for supported routines",
              "ov_dia::CCusHandlerRegistry<ROUTINE_NUMBER> l_registry_obj;",
              "} // namespace ov_dia",
              "",
              "template <zos::uint8_t RegistrySize>",
              "ov_dia::CCusHandlerRegistry<RegistrySize>::CCusHandlerRegistry()",
              "{",
              "",
              "    // Update the supported routines with Registry"]
    for i, e in enumerate(entries):
        lines.append("    m_routineHandlers[%d]  = &%s;" % (i, e["obj"]))
    lines += ["}",
              "",
              "template <zos::uint8_t RegistrySize>",
              "zos::Array<idia::ICRoutineandIOControl*, RegistrySize>",
              "ov_dia::CCusHandlerRegistry<RegistrySize>::m_getIdentifierHandlerArray()",
              "{",
              "    return m_routineHandlers;",
              "}",
              "",
              "// getRegsitryHandler - Spelling changed because of definition in 0x2f as well",
              "idia::ICHandlerRegistry* idia::getRegsitryHandler() { return &ov_dia::l_registry_obj; }",
              "",
              "idia::ICRoutineandIOControlProcessing* idia::getRoutineHandler()"
              " { return &ov_dia::l_routineHandler_obj; }"]
    return "\n".join(lines)


def _method_sig(cls, ret, method):
    return ["%s ov_dia::%s::%s(" % (ret, cls, method),
            "    Dcm_MsgContextType*&          f_MsgContext_p,",
            "    Dcm_NegativeResponseCodeType* dataNegRespCode_u8)"]


def _excute_method(cls, name):
    lines = _method_sig(cls, "void", "m_excute%sCustomer" % name)
    lines += ["{",
              "    // TODO: 接入业务逻辑 (%s)" % name,
              "}"]
    return "\n".join(lines)


def _fill_method(cls, kind, resp_size):
    lines = _method_sig(cls, "void", "m_fillResponseBuffer%sReqCustomer" % kind)
    lines.append("{")
    if resp_size > 0:
        lines.append("    // TODO: 按实际结果填充响应数据")
        for i in range(resp_size):
            lines.append("    f_MsgContext_p->resData[%d] = 0x00u;" % (3 + i))
        lines.append("    f_MsgContext_p->resDataLen = 3 + %d;"
                     " /* 3: subFunction + RID, %d: response data */" % (resp_size, resp_size))
    else:
        lines.append("    // TODO: 按实际结果填充响应数据 (Response Data Size = 0)")
    lines.append("}")
    return "\n".join(lines)


def _cyclic_method(cls):
    return "\n".join([
        "idia::ERoutineStatus ov_dia::%s::m_updateCurrentStatusCyclicCustomer()" % cls,
        "{",
        "    // TODO: 接入业务逻辑后按实际进度返回",
        "    return idia::E_ROUTINE_FINISHED_OK;",
        "}"])


def _nrc22_method(cls):
    lines = _method_sig(cls, "void", "m_validateNRC_22")
    lines += ["{",
              "    // TODO: NRC22 (conditionsNotCorrect) 暂不实现",
              "}"]
    return "\n".join(lines)


def _nrc13_method(cls, controls):
    lines = _method_sig(cls, "void", "m_validateNRC_13")
    lines += ["{",
              "    // NRC_13 validation for total length check",
              "    uint16_t l_reqLength_u16 = static_cast<uint16_t>(f_MsgContext_p->reqDataLen);",
              "    uint8_t  l_subService_u8 = static_cast<uint8_t>(f_MsgContext_p->reqData[0]);",
              "",
              '    LogSync("NRC13 check length , length: %d, subService: %d\\r\\n",'
              " l_reqLength_u16, l_subService_u8);"]
    ctrls = sorted(controls)
    for i, ctrl in enumerate(ctrls):
        req = controls[ctrl]["req_size"]
        kw = "if" if i == 0 else "else if"
        lines += ["    %s (0x%02X == l_subService_u8)" % (kw, ctrl),
                  "    {",
                  "        if (l_reqLength_u16 != (3u + %du))"
                  " /* 3u: format length, %du: request data length */" % (req, req),
                  "        {",
                  "            *dataNegRespCode_u8 = idia::E_INCORRECT_MESSAGE_LENGTH_OR_INVALID_FORMAT;",
                  "        }",
                  "    }"]
    lines += ["    else",
              "    {",
              "        /* Do Nothing */",
              "    }",
              "}"]
    return "\n".join(lines)


def _neq_chain(var, values):
    if len(values) == 1:
        return "%s != %s" % (var, values[0])
    return "(" + " && ".join("%s != %s" % (var, v) for v in values) + ")"


def _nrc31_method(cls, sessions):
    lines = _method_sig(cls, "void", "m_validateNRC_31")
    lines.append("{")
    if not sessions:
        lines.append("    // 问卷所有会话列均为 N, 不做会话校验")
        lines.append("}")
        return "\n".join(lines)
    macros = [SESSION_MACRO[p] for p in SESSION_ORDER if p in sessions]
    lines += ["    Dcm_SesCtrlType SessionID = 0;",
              "",
              "    (void)Dcm_GetSesCtrlType(&SessionID);",
              '    LogSync("NRC31 check session id, session id: %d\\r\\n", SessionID);',
              "    if (%s)" % _neq_chain("SessionID", macros),
              "    {",
              "        *dataNegRespCode_u8 = idia::E_REQUEST_OUT_OF_RANGE;",
              "    }",
              "}"]
    return "\n".join(lines)


def _nrc33_method(cls, sec):
    lines = _method_sig(cls, "void", "m_validateNRC_33")
    lines.append("{")
    if not sec:
        lines.append("    // 问卷所有安全列均为 N, 不做安全校验")
        lines.append("}")
        return "\n".join(lines)
    exprs = _sec_exprs(sec)
    lines += ["    Dcm_SecLevelType SecurityLevel = 0;",
              "",
              "    (void)Dcm_GetSecurityLevel(&SecurityLevel);",
              '    LogSync("NRC33 check security level, security level: %d\\r\\n", SecurityLevel);',
              "    if (%s)" % _neq_chain("SecurityLevel", exprs),
              "    {",
              "        *dataNegRespCode_u8 = idia::E_SECURITY_ACCESS_DENIED;",
              "    }",
              "}"]
    return "\n".join(lines)


def _handlers_inner(entries):
    blocks = []
    for e in entries:
        ctrls = e["controls"]
        banner = ["//****************************************************************************************************************************************",
                  "// Functions of %s  (RID 0x%04X - %s)" % (e["cls"], e["rid"], e["name"]),
                  "// Control : " + " ".join(
                      "0x%02X %s(req %dB, resp %dB)" % (c, VALID_CONTROL[c],
                                                        ctrls[c]["req_size"], ctrls[c]["resp_size"])
                      for c in sorted(ctrls)),
                  "//****************************************************************************************************************************************"]
        methods = []
        if 0x01 in ctrls:
            methods.append(_excute_method(e["cls"], "Start"))
        if 0x02 in ctrls:
            methods.append(_excute_method(e["cls"], "Stop"))
        for ctrl, kind in [(0x01, "Start"), (0x02, "Stop"), (0x03, "Result")]:
            if ctrl in ctrls:
                methods.append(_fill_method(e["cls"], kind, ctrls[ctrl]["resp_size"]))
        methods.append(_cyclic_method(e["cls"]))
        methods.append(_nrc22_method(e["cls"]))
        methods.append(_nrc13_method(e["cls"], ctrls))
        methods.append(_nrc31_method(e["cls"], e["sessions"]))
        methods.append(_nrc33_method(e["cls"], e["sec"]))
        blocks.append("\n".join(banner) + "\n\n" + "\n\n".join(methods))
    return "\n\n".join(blocks)


# ---------------------------------------------------------------- hpp 生成

def _enum_inner(entries):
    lines = ["    typedef enum", "    {"]
    for e in entries:
        lines.append("        %s = 0x%04X," % (e["enum"], e["rid"]))
    lines += ["    } ERoutineIDs;"]
    return "\n".join(lines)


def _proto(ret, method):
    if method == "m_updateCurrentStatusCyclicCustomer":
        return ["    virtual idia::ERoutineStatus m_updateCurrentStatusCyclicCustomer();"]
    if ret == "void" and (method.startswith("m_excute") or method.startswith("m_validateNRC_")):
        return ["    virtual void",
                "    %s(Dcm_MsgContextType*& f_MsgContext_p, Dcm_NegativeResponseCodeType* dataNegRespCode_u8);"
                % method]
    return ["    virtual %s %s(" % (ret, method),
            "        Dcm_MsgContextType*&          f_MsgContext_p,",
            "        Dcm_NegativeResponseCodeType* dataNegRespCode_u8);"]


def _classes_inner(entries):
    blocks = []
    for e in entries:
        ctrls = e["controls"]
        banner = "//======================================================\n" \
                 "// %s  (RID 0x%04X - %s)\n" % (e["cls"], e["rid"], e["name"]) + \
                 "//======================================================"
        lines = ["class %s : public ov_dia::CCusRoutineControl" % e["cls"],
                 "{",
                 "  public:",
                 "    %s(zos::uint16_t f_myId_u16, idia::ESubfunctionSupported f_subfunctionSupport_e)"
                 % e["cls"],
                 "        : ov_dia::CCusRoutineControl(f_myId_u16, f_subfunctionSupport_e)",
                 "    {",
                 "    }",
                 ""]
        protos = []
        if 0x01 in ctrls:
            protos += _proto("void", "m_excuteStartCustomer")
        if 0x02 in ctrls:
            protos += _proto("void", "m_excuteStopCustomer")
        for ctrl, kind in [(0x01, "Start"), (0x02, "Stop"), (0x03, "Result")]:
            if ctrl in ctrls:
                protos += _proto("void", "m_fillResponseBuffer%sReqCustomer" % kind)
        protos += _proto("idia::ERoutineStatus", "m_updateCurrentStatusCyclicCustomer")
        for nrc in ("22", "13", "31", "33"):
            protos += _proto("void", "m_validateNRC_%s" % nrc)
        lines += protos
        lines += ["",
                  "    virtual ~%s() {}" % e["cls"],
                  "    zos::uint8_t m_result_u8;",
                  "",
                  "  private:",
                  "    %s(const %s&);" % (e["cls"], e["cls"]),
                  "    %s& operator=(const %s&);" % (e["cls"], e["cls"]),
                  "};"]
        blocks.append(banner + "\n" + "\n".join(lines))
    return "\n\n\n".join(blocks)


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(description="根据 UDS 问卷 RID List 生成 0x31 处理器骨架")
    ap.add_argument("excel")
    ap.add_argument("vehicle_dir", help="dia_cfg/var/src/vehicle/<variant> 目录")
    args = ap.parse_args()

    try:
        data = parse_rid_excel(args.excel)
    except ValueError as e:
        _fail(str(e))

    vd = Path(args.vehicle_dir).resolve()
    if not vd.is_dir():
        _fail("vehicle_dir 不存在: %s" % vd)
    cpp = vd / "0x31" / "ov_dia_0x31_routine_by_identifier_handler.cpp"
    if (vd.parent / "inc" / "ov_dia").is_dir():
        # v2 布局: vehicle_dir = cpj_*/veh_<变体>/dia_cfg/src, hpp 同级 dia_cfg/inc
        # (0x31 hpp 已于 2026-09-30 从 cpj 级迁至 veh 级, 同 0x22/0x2e)
        hpp = vd.parent / "inc" / "ov_dia" / "0x31" / \
            "ov_dia_0x31_routine_by_identifier_handler.hpp"
    else:
        # 旧布局: hpp 在 cpj_*/dia_cfg/inc/ov_dia/0x31
        hpp = vd.parents[3] / "inc" / "ov_dia" / "0x31" / \
            "ov_dia_0x31_routine_by_identifier_handler.hpp"
    for name, p in [("0x31 cpp", cpp), ("0x31 hpp", hpp)]:
        if not p.is_file():
            _fail("目标文件不存在 (%s): %s" % (name, p))

    entries = []
    for r in data.rids:
        ctrl_set = frozenset(r["controls"])
        if ctrl_set not in SUBFUNC_MAP:
            _fail("0x%04X 的 Control Type 组合暂不支持: %s"
                  % (r["rid"], "/".join("0x%02X" % c for c in sorted(ctrl_set))))
        e = dict(r)
        e.update(_derive_names(r["name"], r["rid"]))
        e["subfunc"] = SUBFUNC_MAP[ctrl_set]
        entries.append(e)

    cpp_text = _read_file(cpp)
    hpp_text = _read_file(hpp)
    old_enum_cnt = len(re.findall(r"E_RID_\w+\s*=\s*0x", hpp_text))

    wrap = lambda inner: (lambda b, e: b + "\n" + inner + "\n" + e)

    try:
        cpp_text = _regen_region(cpp_text, "RID REGISTRY", "", _registry_inner(entries),
                                 _locate_registry, wrap(_registry_inner(entries)),
                                 source=RID_SOURCE)
        cpp_text = _regen_region(cpp_text, "RID HANDLER", "", _handlers_inner(entries),
                                 _locate_handlers, wrap(_handlers_inner(entries)),
                                 source=RID_SOURCE)
        hpp_text = _regen_region(hpp_text, "RID ENUM", "", _enum_inner(entries),
                                 _locate_enum, wrap(_enum_inner(entries)),
                                 source=RID_SOURCE)
        hpp_text = _regen_region(hpp_text, "RID CLASS", "", _classes_inner(entries),
                                 _locate_classes, wrap(_classes_inner(entries)),
                                 source=RID_SOURCE)
    except RuntimeError as e:
        _fail(str(e))

    _write_file(cpp, cpp_text)
    _write_file(hpp, hpp_text)

    # ---- 摘要 ----
    print("=== 生成摘要 (RID %d 项, 原 %d 项) ===" % (len(entries), old_enum_cnt))
    for e in entries:
        ss = "/".join(SESSION_MACRO[p] for p in SESSION_ORDER if p in e["sessions"]) or "-"
        sc = "|".join(_sec_exprs(e["sec"])) or "-"
        print("  0x%04X %-30s %s  sessions[%s] sec[%s]" % (e["rid"], e["name"], e["subfunc"], ss, sc))
        for c in sorted(e["controls"]):
            info = e["controls"][c]
            print("    0x%02X %-22s req=%dB resp=%dB NRC13(3u+%du)"
                  % (c, VALID_CONTROL[c], info["req_size"], info["resp_size"], info["req_size"]))
        if not e["sec"]:
            print("    警告: 安全列全 N, NRC33 未生成校验")
        if not e["sessions"]:
            print("    警告: 会话列全 N, NRC31 未生成校验")
    print("NRC22 留空 TODO; excute/fill 为业务骨架, 请手动接入")
    print("已写入: %s" % cpp)
    print("        %s" % hpp)


if __name__ == "__main__":
    main()
