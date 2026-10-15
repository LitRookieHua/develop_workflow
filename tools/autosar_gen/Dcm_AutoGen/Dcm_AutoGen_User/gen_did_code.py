"""gen_did_code - 根据 UDS 诊断问卷 DID List 重新生成 j02 的 DID 查找表 / 0x22 / 0x2E 处理器,
并回填 version_did JSON 值.

四类 Data Source 处理规则 (所有 DID 一律生成表条目 + handler):
  iMotionDid   复用现有 0x22 cpp handler 原文 (缺失报错)
  VersionDid   有 version_did 模板落点 (g_DidData 数组) → 生成读 handler + 写 JSON 值;
               无落点 → 骨架 handler (TODO 注明原因)
  NvmDid       语义映射现有 Z block + pdm_cfg.h 校验 (宏存在且长度 == Excel Data Length)
               → 生成读/写 handler; 不满足 → 骨架 handler (TODO 注明原因)
  DynamicDid   现有代码有实现则复用; 没有 → 骨架 handler (TODO 注明需手动实现)
骨架 handler 返回 idia::E_DID_ERROR; Support $2E=Yes 但无有效 NVM block 时
同样生成写骨架 (不再报错退出).

替换范围: 6 处 AUTO-GENERATED 标记区 (查找表 / 0x22 handler / 0x22 宏 / 0x22 原型 /
0x2e handler / 0x2e 原型), 文件其余部分逐字节保留. JSON 逐 key 回填, 非目标 key 保留.

用法:
  python gen_did_code.py <excel> <vehicle_dir> <json> [--pdm-cfg <pdm_cfg.h>] [--vd-template <version_did.cpp.in>]
  vehicle_dir = ...\\dia_cfg\\var\\src\\vehicle\\<variant>
"""

import argparse
import re
import sys
from pathlib import Path

GEN_TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(GEN_TOOLS))
from Parse_did_excel import parse_did_excel  # noqa: E402

MARK_SOURCE = "source: UDS Diagnostic Questionnaire DID List"

# NvmDid 语义映射: DID → 现有 pdm Z block (None = 无对应 block)
NVM_BLOCK_MAP = {
    0xF190: "Z003_VIN",
    0xF15A: "Z004_FingerPrint",
    0xF18C: "Z002_ECUSerialNumber",
    0xF15B: "Z004_FingerPrint",
    0x2EE2: None,
}

# version_did 模板 (templates/version_did.cpp.in) 中有 g_DidData_<DID>_au8 数组的 DID 集合
# (--vd-template 给定时从模板重新提取覆盖)
VERSION_DID_LANDING = {
    "0101", "0106", "2001", "2002", "B010", "D001", "D19A",
    "F005", "F006", "F010", "F011", "F012", "F013", "F016", "F017", "F018", "F019",
    "F031", "F032", "F089", "F100", "F101", "F107", "F10A", "F10B", "F10D",
    "F112", "F17F", "F180", "F181", "F183", "F184", "F187", "F188", "F189",
    "F18A", "F18B", "F18C", "F18E", "F191", "F192", "F193", "F194", "F195",
    "F197", "F19E", "F1A0", "F1A1", "F1A2", "F1B0", "F1B1", "F1B2", "F1B3",
    "F1B6", "F1C8", "F1D9", "F1EF", "F289", "F301",
}

SESSION_ORDER = ["DEFAULT", "PROGRAMMING", "EXTENDED"]
SEC_ORDER = ["LOCK", "NORMAL_UNLOCK", "PROGRAMMING_UNLOCK", "DEVELOPMENT_UNLOCK"]

# j02 ov_dia_did_lookup_table.hpp 中实际定义的安全组合 (会话 8 种组合齐全, 不需校验表)
VALID_SEC = {
    "E_DIA_SECLEVEL_NULL", "E_DIA_SECLEVEL_LOCK", "E_DIA_SECLEVEL_NORMAL_UNLOCK",
    "E_DIA_SECLEVEL_PROGRAMMING_UNLOCK", "E_DIA_SECLEVEL_DEVELOPMENT_UNLOCK",
    "E_DIA_SECLEVEL_LOCK_NORMAL_UNLOCK", "E_DIA_SECLEVEL_LOCK_PROGRAMMING_UNLOCK",
    "E_DIA_SECLEVEL_NORMAL_PROGRAMMING_UNLOCK", "E_DIA_SECLEVEL_LOCK_NORMAL_PROGRAMMING_UNLOCK",
    "E_DIA_SECLEVEL_LOCK_NORMAL_DEVELOPMENT_UNLOCK",
    "E_DIA_SECLEVEL_LOCK_NORMAL_PROGRAMMING_DEVELOPMENT_UNLOCK",
}

READ_SIG = r"^[ \t]*idia::EDidResult\s+gType_ov_dia_DID_ReadHandler_0x%04X\s*\("
WRITE_SIG = r"^[ \t]*idia::EDidResult\s+gType_ov_dia_DID_WriteHandler_0x%04X\s*\("
READ_ANY_SIG = r"^[ \t]*idia::EDidResult\s+gType_ov_dia_DID_ReadHandler_0x[0-9A-F]{4}\s*\("
WRITE_ANY_SIG = r"^[ \t]*idia::EDidResult\s+gType_ov_dia_DID_WriteHandler_0x[0-9A-F]{4}\s*\("


# ---------------------------------------------------------------- 文本工具

def _detect_nl(text):
    return "\r\n" if "\r\n" in text else "\n"


def _line_start(text, pos):
    return text.rfind("\n", 0, pos) + 1


def _line_start_checked(text, pos):
    """回退到 pos 所在行首, 并校验行内 pos 前只有空白."""
    start = text.rfind("\n", 0, pos) + 1
    if text[start:pos].strip():
        raise RuntimeError("位置 %d 前有非空白内容: %r" % (pos, text[start:pos]))
    return start


def _match_brace(text, open_pos):
    """从 '{' 起配对到 '}', 返回 '}' 之后的位置 (跳过注释/字符串)."""
    depth = 0
    i = open_pos
    in_block = in_line = in_str = False
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_block:
            if ch == "*" and nxt == "/":
                in_block = False
                i += 2
                continue
        elif in_line:
            if ch == "\n":
                in_line = False
        elif in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_str = False
        else:
            if ch == "/" and nxt == "*":
                in_block = True
                i += 2
                continue
            if ch == "/" and nxt == "/":
                in_line = True
                i += 2
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i + 1
        i += 1
    raise RuntimeError("花括号未配对 (起始于 %d)" % open_pos)


def _marks(label, indent, source=None):
    begin = "%s/* ===== %s AUTO-GENERATED BEGIN (%s) ===== */" % (indent, label, source or MARK_SOURCE)
    end = "%s/* ===== %s AUTO-GENERATED END ===== */" % (indent, label)
    return begin, end


def _regen_region(text, label, indent, inner, locate, first_run_wrap, source=None):
    """幂等替换一个标记区. inner: 区内内容 (LF, 末尾不带换行).

    有标记: 替换 [BEGIN 行首, END 行尾] 为 BEGIN+inner+END.
    无标记: 用 locate 定位区域, 替换为 first_run_wrap(begin, end) 生成的完整块.
    """
    nl = _detect_nl(text)
    begin, end = _marks(label, indent, source)
    if begin in text:
        if text.count(begin) != 1 or text.count(end) != 1:
            raise RuntimeError("%s 标记不配对 (BEGIN=%d, END=%d)"
                               % (label, text.count(begin), text.count(end)))
        start = _line_start_checked(text, text.index(begin))
        stop = text.index(end) + len(end)
        block = begin + "\n" + inner + "\n" + end
        # END 标记后未紧跟换行符时补一个 (自愈早期版本遗留的紧贴 '}'):
        # 补入后下轮运行此条件不再成立, 结果稳定
        if stop < len(text) and text[stop] not in "\r\n":
            block += "\n"
    else:
        start, stop = locate(text)
        block = first_run_wrap(begin, end)
    block = block.replace("\n", nl)
    return text[:start] + block + text[stop:]


def _extract_handler(text, kind, did):
    """从现有 cpp 提取 handler 原文 (签名行首到配对 '}'), 没有则返回 None."""
    sig = re.search((READ_SIG if kind == "Read" else WRITE_SIG) % did, text, re.M)
    if not sig:
        return None
    start = _line_start(text, sig.start())
    brace = text.find("{", sig.end())
    if brace < 0 or text[sig.end():brace].count("\n") > 1:
        raise RuntimeError("0x%04X %s handler 签名后未找到 '{'" % (did, kind))
    close = _match_brace(text, brace)
    # 统一为 LF, 由 _regen_region 在写回时统一转目标换行符 (否则 CRLF 会被再叠一层 \r)
    return text[start:close].rstrip().replace("\r\n", "\n")


# ---------------------------------------------------------------- 枚举组合

def _session_enum(parts):
    ordered = [p for p in SESSION_ORDER if p in parts]
    if not ordered:
        return "E_DIA_SESSION_NULL"
    return "E_DIA_SESSION_" + "_".join(ordered)


def _sec_enum(parts):
    ordered = [p for p in SEC_ORDER if p in parts]
    if not ordered:
        return "E_DIA_SECLEVEL_NULL"
    names = [p[:-len("_UNLOCK")] if i < len(ordered) - 1 and p.endswith("_UNLOCK") else p
             for i, p in enumerate(ordered)]
    return "E_DIA_SECLEVEL_" + "_".join(names)


# ---------------------------------------------------------------- 区域定位

def _locate_lookup_table(text):
    m = re.search(r"^[ \t]*const idia::CDiaDidLookupTableEntry g_dia_did_lookup_table_ast\[\] *=",
                  text, re.M)
    if not m:
        raise RuntimeError("未找到 g_dia_did_lookup_table_ast 声明")
    brace = text.find("{", m.end())
    if brace < 0:
        raise RuntimeError("查找表声明后未找到 '{'")
    close = _match_brace(text, brace)
    m2 = re.compile(r"\s*;").match(text, close)
    if not m2:
        raise RuntimeError("查找表 '}' 后未紧跟 ';'")
    return _line_start(text, m.start()), m2.end()


def _locate_to_namespace_end(text, sig_re):
    m = re.search(sig_re, text, re.M)
    if not m:
        raise RuntimeError("未找到 handler 区起点 (%s)" % sig_re)
    ns_close = text.find("} // namespace ov_dia")
    if ns_close < 0 or ns_close < m.start():
        raise RuntimeError("未找到 '} // namespace ov_dia' 或顺序异常")
    # stop 放在 namespace 行的换行符之前, 保证 END 标记独占一行
    ls = _line_start(text, ns_close)
    return _line_start(text, m.start()), ls - 2 if text[ls - 2:ls] == "\r\n" else ls - 1


def _locate_hpp_macros(text):
    lines = text.split("\n")
    idxs = [i for i, l in enumerate(lines) if l.startswith("#define DID_LENGTH_")]
    if not idxs:
        raise RuntimeError("未找到 DID_LENGTH 宏区")
    first, last = idxs[0], idxs[-1]
    for i in range(first, last + 1):
        if not lines[i].startswith("#define DID_LENGTH_"):
            raise RuntimeError("DID_LENGTH 宏区不连续 (第 %d 行)" % (i + 1))
    start = sum(len(l) + 1 for l in lines[:first])
    stop = start + len("\n".join(lines[first:last + 1]))
    if text[stop - 1] == "\r":  # CRLF 时不含末行 \r, 保留原换行符
        stop -= 1
    return start, stop


def _locate_hpp_protos(text, sig_re):
    m = re.search(sig_re, text, re.M)
    if not m:
        raise RuntimeError("未找到原型区起点 (%s)" % sig_re)
    endif = text.find("#endif")
    if endif < 0:
        raise RuntimeError("未找到 #endif")
    close = text.rfind("\n}", m.start(), endif)
    if close < 0:
        raise RuntimeError("未找到 namespace 关闭 '}'")
    # stop 放在 '}' 行的换行符之前, 保证 END 标记独占一行
    ls = close + 1
    return _line_start(text, m.start()), ls - 2 if text[ls - 2:ls] == "\r\n" else ls - 1


# ---------------------------------------------------------------- 生成模板

def _read_handler_version(did):
    arr = "%04X" % did
    return """    idia::EDidResult gType_ov_dia_DID_ReadHandler_0x%04X(zos::uint16_t f_index_u16, zos::uint8_t * const f_readDataBuffer_u8_p)
    {
        zos::uint8_t l_data_au8[256] = {0x00};

        memset(l_data_au8, 0x20, sizeof(l_data_au8));
        memcpy(l_data_au8, g_DidData_%s_au8, strlen((const char *)g_DidData_%s_au8));
        memcpy(f_readDataBuffer_u8_p, l_data_au8, DID_LENGTH_0x%04X);

        return(idia::E_DID_OK);
    }""" % (did, arr, arr, did)


def _read_handler_nvm(did, block):
    return """    idia::EDidResult gType_ov_dia_DID_ReadHandler_0x%04X(zos::uint16_t f_index_u16, zos::uint8_t * const f_readDataBuffer_u8_p)
    {
        zos::uint8_t l_data_au8[DID_LENGTH_0x%04X] = {0};
        idia::idiaIdBasedReadWrite(
            NvMConf_NvMBlockDescriptor_SWC_NVM_ID_%s,
            idia::E_DIA_READ_REQUEST,
            l_data_au8,
            NVM_CFG_NV_BLOCK_LENGTH_NVM_PDM_%s);
        memcpy(f_readDataBuffer_u8_p, l_data_au8, DID_LENGTH_0x%04X);
        return(idia::E_DID_OK);
    }""" % (did, did, block, block, did)


def _write_handler_nvm(did, block):
    return """    idia::EDidResult gType_ov_dia_DID_WriteHandler_0x%04X(zos::uint16_t f_index_u16 , zos::uint8_t const * const f_writeDataBuffer_pu8 )
    {
        return gType_ov_dia_DID_WriteHandler(
            NvMConf_NvMBlockDescriptor_SWC_NVM_ID_%s,
            idia::E_DIA_WRITE_REQUEST,
            f_writeDataBuffer_pu8,
            NVM_CFG_NV_BLOCK_LENGTH_NVM_PDM_%s);
    }""" % (did, block, block)


def _read_handler_stub(did, reason):
    return """    idia::EDidResult gType_ov_dia_DID_ReadHandler_0x%04X(zos::uint16_t f_index_u16, zos::uint8_t * const f_readDataBuffer_u8_p)
    {
        // TODO: 未实现 - %s
        return(idia::E_DID_ERROR);
    }""" % (did, reason)


def _write_handler_stub(did, reason):
    return """    idia::EDidResult gType_ov_dia_DID_WriteHandler_0x%04X(zos::uint16_t f_index_u16 , zos::uint8_t const * const f_writeDataBuffer_pu8 )
    {
        // TODO: 未实现 - %s
        return(idia::E_DID_ERROR);
    }""" % (did, reason)


def _table_entry(d, write_handler):
    return ("        {0x%04X, %3d, DCOM_CFG_DID_NOT_IN_PDM,   gType_ov_dia_DID_ReadHandler_0x%04X,    %s,    "
            "{ idia::gType_idia_noCheckRangeOfDIDData, %s,    %s,   %s,    %s} },"
            % (d["did"], d["length"], d["did"], write_handler,
               _session_enum(d["read_sessions"]), _session_enum(d["write_sessions"]),
               _sec_enum(d["read_sec"]), _sec_enum(d["write_sec"])))


# ---------------------------------------------------------------- JSON 回填

_JSON_LINE_RE = re.compile(r'^(\s*)"([^"]+)"\s*:\s*"(.*)"\s*,?\s*$')


def update_version_json(json_path, updates):
    """updates: {ZX_DID_XXXX: value}; 逐行解析后按键排序重建, 非目标 key 原样保留."""
    with open(json_path, encoding="utf-8", newline="") as f:
        text = f.read()
    nl = _detect_nl(text)
    trailing_nl = text.endswith("\n")

    entries = {}
    for line in text.split("\n"):
        m = _JSON_LINE_RE.match(line)
        if m:
            entries[m.group(2)] = m.group(3)
    if not entries:
        raise RuntimeError("JSON 未解析到任何 key: %s" % json_path)

    changed = []
    for key, value in updates.items():
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        if key not in entries or entries[key] != escaped:
            changed.append((key, entries.get(key, "<新增>"), escaped))
        entries[key] = escaped

    lines = ["{"]
    ordered = sorted(entries)
    for i, key in enumerate(ordered):
        comma = "," if i < len(ordered) - 1 else ""
        lines.append('    "%s": "%s"%s' % (key, entries[key], comma))
    lines.append("}")
    new_text = nl.join(lines) + (nl if trailing_nl else "")

    with open(json_path, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)
    return changed


# ---------------------------------------------------------------- 主流程

def _derive_paths(vehicle_dir, pdm_cfg_arg):
    vd = Path(vehicle_dir).resolve()
    if not vd.is_dir():
        raise RuntimeError("vehicle_dir 不存在: %s" % vd)
    variant = vd.name
    if (vd.parent / "inc" / "ov_dia").is_dir():
        # v2 布局: vehicle_dir = cpj_*/veh_<变体>/dia_cfg/src
        # inc 在 dia_cfg/inc, pdm_cfg 在 veh_<变体>/pdm_cfg
        inc_dir = vd.parent / "inc"
        pdm_default = vd.parents[1] / "pdm_cfg" / "inc" / "pdm_cfg" / "pdm_cfg.h"
    else:
        # 旧布局: vehicle_dir = cpj_*/dia_cfg/var/src/vehicle/<变体>
        var_dir = vd.parents[2]  # var/src/vehicle/<variant> -> var
        inc_dir = var_dir / "inc" / "vehicle" / variant
        pdm_default = vd.parents[4] / "pdm_cfg" / variant / "inc" / "pdm_cfg" / "pdm_cfg.h"

    paths = {
        "lookup_cpp": vd / "did_lookup_table" / "ov_dia_did_lookup_table.cpp",
        "read_cpp": vd / "0x22" / "ov_dia_0x22_read_data_by_identifier_handler.cpp",
        "write_cpp": vd / "0x2e" / "ov_dia_0x2e_write_data_by_identifier_handler.cpp",
        "read_hpp": inc_dir / "ov_dia" / "0x22" / "ov_dia_0x22_read_data_by_identifier_handler.hpp",
        "write_hpp": inc_dir / "ov_dia" / "0x2e" / "ov_dia_0x2e_write_data_by_identifier_handler.hpp",
    }
    for name, p in paths.items():
        if not p.is_file():
            raise RuntimeError("目标文件不存在 (%s): %s" % (name, p))

    pdm_cfg = Path(pdm_cfg_arg) if pdm_cfg_arg else pdm_default
    return paths, pdm_cfg


def _parse_pdm_cfg(path):
    """返回 ({block_name: block_id}, {block_name: length}); 文件缺失返回 (None, None)."""
    if not path.is_file():
        return None, None
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    ids = {m.group(1) for m in re.finditer(
        r"#define NvMConf_NvMBlockDescriptor_SWC_NVM_ID_(\w+)", text)}
    lens = {m.group(1): int(m.group(2)) for m in re.finditer(
        r"#define NVM_CFG_NV_BLOCK_LENGTH_NVM_PDM_(\w+)\s+\((\d+)u\)", text)}
    return ids, lens


def _load_landing(template_arg):
    if not template_arg:
        return VERSION_DID_LANDING
    with open(template_arg, encoding="utf-8", errors="replace") as f:
        text = f.read()
    return {m.group(1).upper() for m in re.finditer(r"g_DidData_([0-9A-Fa-f]{4})_au8", text)}


def _read_file(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _write_file(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser(description="根据 UDS 问卷 DID List 生成 DID 查找表/0x22/0x2E 代码")
    ap.add_argument("excel")
    ap.add_argument("vehicle_dir", help="dia_cfg/var/src/vehicle/<variant> 目录")
    ap.add_argument("json", help="version_did modules JSON (如 J02_C097.json)")
    ap.add_argument("--pdm-cfg", default=None, help="pdm_cfg.h (默认从 vehicle_dir 推导)")
    ap.add_argument("--vd-template", default=None, help="version_did.cpp.in (默认用内置模板落点集合)")
    args = ap.parse_args()

    try:
        data = parse_did_excel(args.excel)
    except ValueError as e:
        print("错误：%s" % e)
        sys.exit(1)

    try:
        paths, pdm_cfg = _derive_paths(args.vehicle_dir, args.pdm_cfg)
    except RuntimeError as e:
        print("错误：%s" % e)
        sys.exit(1)

    landing = _load_landing(args.vd_template)
    nvm_ids, nvm_lens = _parse_pdm_cfg(pdm_cfg)
    read_cpp_text = _read_file(paths["read_cpp"])

    planned = []   # 生成表条目的 DID (dict + 补充字段)
    stubbed = []   # (did, name, reason) 未实现转骨架的 DID
    json_updates = {}

    for d in sorted(data.dids, key=lambda x: x["did"]):
        did = d["did"]
        if d["source"] == "iMotionDid":
            body = _extract_handler(read_cpp_text, "Read", did)
            if body is None:
                print("错误：iMotionDid 0x%04X (%s) 在现有 0x22 cpp 中无实现" % (did, d["name"]))
                sys.exit(1)
            d["read_body"] = body
            planned.append(d)
        elif d["source"] == "VersionDid":
            if ("%04X" % did) not in landing:
                reason = "version_did 模板无 g_DidData_%04X 数组" % did
                d["read_body"] = _read_handler_stub(did, reason)
                d["stub"] = True
                stubbed.append((did, d["name"], reason))
                planned.append(d)
                continue
            d["read_body"] = _read_handler_version(did)
            if d["default_value"]:
                json_updates["ZX_DID_%04X" % did] = d["default_value"]
            else:
                print("警告：0x%04X (%s) Default Value 为空, JSON 未回填 (handler 已生成)"
                      % (did, d["name"]))
            planned.append(d)
        elif d["source"] == "NvmDid":
            block = NVM_BLOCK_MAP.get(did)
            if block is None:
                reason = "无对应 NVM block 映射 (语义映射表)"
            elif nvm_ids is None:
                reason = "pdm_cfg.h 不存在: %s" % pdm_cfg
            elif block not in nvm_ids or block not in nvm_lens:
                reason = "pdm_cfg.h 无 block 宏: %s" % block
            elif nvm_lens[block] != d["length"]:
                reason = "长度不一致 (NVM block %s=%dB vs DID %dB)" % (block, nvm_lens[block], d["length"])
            else:
                d["nvm_block"] = block
                d["read_body"] = _read_handler_nvm(did, block)
                planned.append(d)
                continue
            d["read_body"] = _read_handler_stub(did, reason)
            d["stub"] = True
            stubbed.append((did, d["name"], reason))
            planned.append(d)
        elif d["source"] == "DynamicDid":
            body = _extract_handler(read_cpp_text, "Read", did)
            if body is None:
                reason = "DynamicDid 需手动实现"
                d["read_body"] = _read_handler_stub(did, reason)
                d["stub"] = True
                stubbed.append((did, d["name"], reason))
            else:
                d["read_body"] = body
            planned.append(d)

    # 校验安全组合枚举存在 (hpp 不在生成目标内)
    for d in planned:
        for name in (_sec_enum(d["read_sec"]), _sec_enum(d["write_sec"])):
            if name not in VALID_SEC:
                print("错误：安全组合 %s 在 ov_dia_did_lookup_table.hpp 中未定义 (0x%04X), 请先在 hpp 补枚举"
                      % (name, d["did"]))
                sys.exit(1)

    write_dids = [d for d in planned if d["support_2e"]]
    write_stubbed = []
    for d in write_dids:
        if d["source"] != "NvmDid" or not d.get("nvm_block"):
            reason = "Support $2E=Yes 但 Data Source %s 无有效 NVM block, 写 handler 待接入" % d["source"]
            d["write_body"] = _write_handler_stub(d["did"], reason)
            write_stubbed.append((d["did"], d["name"], reason))
        else:
            d["write_body"] = _write_handler_nvm(d["did"], d["nvm_block"])

    # ---- 组装各生成区 (统一 LF, 写回时转目标换行符) ----
    table_inner = "\n".join(_table_entry(
        d, ("gType_ov_dia_DID_WriteHandler_0x%04X" % d["did"]) if d["support_2e"]
        else "idia::gType_idia_DID_noWriteHandler") for d in planned)

    read_handlers = "\n\n".join(d["read_body"] for d in planned)
    write_handlers = "\n\n".join(d["write_body"] for d in write_dids)

    macros = "\n".join("#define DID_LENGTH_0x%04X %du" % (d["did"], d["length"]) for d in planned)
    read_protos = "\n".join(
        "    idia::EDidResult gType_ov_dia_DID_ReadHandler_0x%04X(zos::uint16_t f_index_u16, "
        "zos::uint8_t * const f_readDataBuffer_u8_p);" % d["did"] for d in planned)
    write_protos = "\n".join(
        "    idia::EDidResult gType_ov_dia_DID_WriteHandler_0x%04X(zos::uint16_t f_index_u16, "
        "zos::uint8_t const * const f_writeDataBuffer_pu8);" % d["did"] for d in write_dids)

    try:
        # lookup cpp: 标记包裹表条目 (声明/花括号在标记外层, 幂等)
        text = _read_file(paths["lookup_cpp"])
        text = _regen_region(
            text, "DID LOOKUP TABLE", "        ", table_inner, _locate_lookup_table,
            lambda b, e: ("    const idia::CDiaDidLookupTableEntry g_dia_did_lookup_table_ast[] =\n"
                          "    {\n" + b + "\n" + table_inner + "\n" + e + "\n    };"))
        _write_file(paths["lookup_cpp"], text)

        # 0x22 cpp
        text = _read_file(paths["read_cpp"])
        text = _regen_region(text, "DID READ HANDLER", "    ", read_handlers,
                             lambda t: _locate_to_namespace_end(t, READ_ANY_SIG),
                             lambda b, e: b + "\n" + read_handlers + "\n" + e)
        _write_file(paths["read_cpp"], text)

        # 0x2e cpp
        text = _read_file(paths["write_cpp"])
        text = _regen_region(text, "DID WRITE HANDLER", "    ", write_handlers,
                             lambda t: _locate_to_namespace_end(t, WRITE_ANY_SIG),
                             lambda b, e: b + "\n" + write_handlers + "\n" + e)
        _write_file(paths["write_cpp"], text)

        # 0x22 hpp: 宏区 + 原型区 两对标记
        text = _read_file(paths["read_hpp"])
        text = _regen_region(text, "DID LENGTH MACRO", "", macros, _locate_hpp_macros,
                             lambda b, e: b + "\n" + macros + "\n" + e)
        text = _regen_region(text, "DID READ PROTOTYPE", "    ", read_protos,
                             lambda t: _locate_hpp_protos(t, READ_ANY_SIG),
                             lambda b, e: b + "\n" + read_protos + "\n" + e)
        _write_file(paths["read_hpp"], text)

        # 0x2e hpp
        text = _read_file(paths["write_hpp"])
        text = _regen_region(text, "DID WRITE PROTOTYPE", "    ", write_protos,
                             lambda t: _locate_hpp_protos(t, WRITE_ANY_SIG),
                             lambda b, e: b + "\n" + write_protos + "\n" + e)
        _write_file(paths["write_hpp"], text)
    except RuntimeError as e:
        print("错误：%s" % e)
        sys.exit(1)

    try:
        json_changed = update_version_json(args.json, json_updates)
    except RuntimeError as e:
        print("错误：%s" % e)
        sys.exit(1)

    # ---- 摘要 ----
    print("=== 生成摘要 (表 %d 项 / 读 handler %d / 写 handler %d) ==="
          % (len(planned), len(planned), len(write_dids)))
    for d in planned:
        if d.get("stub"):
            tag = "骨架 (未实现, 见 TODO)"
        elif d["source"] in ("iMotionDid", "DynamicDid"):
            tag = "复用现有实现"
        elif d["source"] == "VersionDid":
            tag = "生成 (version_did)"
        else:
            tag = "生成 (NVM block %s)" % d["nvm_block"]
        print("  0x%04X %-40s len=%-3d %-10s %s" % (d["did"], d["name"], d["length"], d["source"], tag))
    all_stubbed = stubbed + write_stubbed
    if all_stubbed:
        print("=== 未实现骨架 %d 项 (handler 内 TODO 注明原因) ===" % len(all_stubbed))
        for did, name, reason in all_stubbed:
            print("  0x%04X %-40s %s" % (did, name, reason))
    if json_changed:
        print("=== JSON 更新 %d 项 ===" % len(json_changed))
        for key, old, new in json_changed:
            print("  %s: %r -> %r" % (key, old, new))
    else:
        print("JSON 无变更 (值已一致)")
    print("pdm_cfg.h: %s" % pdm_cfg)
    print("已写入: %s" % ", ".join(str(p) for p in paths.values()))


if __name__ == "__main__":
    main()
