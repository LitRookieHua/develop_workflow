#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_map_yaml - 从 Dem ecuc arxml 提取 DTC/Event 映射, 生成 dtc_map.yaml / event_map.yaml.

支持两种工程, 按工程目录结构自动判型 (无 CLI 开关):
  Vector DaVinci: 传 SipAddon 目录, DTC 与 Event 都在
                  Config/ECUC/StartApplication_Dem_Dem_ecuc.arxml
  ETAS RTA:       传 BswRta 目录, DTC 在 ecu_config/bsw/gen/*Dem_EcucValues.arxml
                  (排除 RTA_BIP_ 前缀), Event 在
                  ecu_config/bsw/gen/_fwd/ecuc_configuration_values_fwd.arxml
                  (ETAS 的 DemEventId 由 ID 生成器回填到 _fwd 文件, 主 arxml 中没有)

dtc_map.yaml   : DTC 值 十六进制 (0x%X) -> DTC 容器名
event_map.yaml : DemEventId 十进制 -> Event 容器名
fimfid_map.yaml: FiMFID 序号 (1 起) -> FiMFID 名; 数据源为 dsmFidGen 生成的
                 zx_sys_evm_cfg_fimcfg.hpp 中 EvmPf_FuncPermission 结构体
                 (结构体 /// 序号从 0 起, yaml 键 = 序号 + 1), 仅在传入该
                 hpp 路径 (可选第 3 参数) 时生成.
均按 key 数值升序, 根节点直接是映射, 无外层包裹.

生成的 map 同时拷贝一份到 diag 工具变体目录 (10_tools/diag/configs/<变体>/);
变体名由工程路径推导 (ETAS: autosar/<变体>/BswRta 取父目录名;
Vector: <customer>/<变体>/microsar_cfg/... 取 microsar_cfg 父目录名去 veh_ 前缀),
diag 目录不存在/未收录该变体时仅提示跳过.

用法:
  python gen_map_yaml.py <project_dir> <output_dir> [fimcfg_hpp]
"""

import re
import shutil
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
DIAG_CONFIGS_DIR = SCRIPT_ROOT.parent.parent / "diag" / "configs"

SUB_OPEN = "<SUB-CONTAINERS>"
SUB_CLOSE = "</SUB-CONTAINERS>"
CTR_OPEN = "<ECUC-CONTAINER-VALUE"
CTR_CLOSE = "</ECUC-CONTAINER-VALUE>"

EVENT_ID_RE = re.compile(
    r"DemEventParameter/DemEventId</DEFINITION-REF>\s*<VALUE>(\d+)</VALUE>")
SHORT_NAME_RE = re.compile(r"<SHORT-NAME>([^<]+)</SHORT-NAME>")

# --- Vector DaVinci (MICROSAR) ---
VECTOR_CONFIG_SET_REF = (
    '<DEFINITION-REF DEST="ECUC-PARAM-CONF-CONTAINER-DEF">'
    "/MICROSAR/Dem/DemConfigSet</DEFINITION-REF>"
)
VECTOR_DTC_REF = ">/MICROSAR/Dem/DemConfigSet/DemDTCClass</DEFINITION-REF>"
VECTOR_EVENT_REF = ">/MICROSAR/Dem/DemConfigSet/DemEventParameter</DEFINITION-REF>"
VECTOR_DTC_VALUE_RE = re.compile(
    r"DemDTCClass/DemUdsDTC</DEFINITION-REF>\s*<VALUE>(\d+)</VALUE>")
VECTOR_ECUC_ARXML = Path("Config/ECUC/StartApplication_Dem_Dem_ecuc.arxml")

# --- ETAS RTA (AUTOSAR_Dem) ---
ETAS_CONFIG_SET_REF = (
    '<DEFINITION-REF DEST="ECUC-PARAM-CONF-CONTAINER-DEF">'
    "/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet</DEFINITION-REF>"
)
ETAS_DTC_REF = (
    ">/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTC</DEFINITION-REF>")
ETAS_EVENT_REF = (
    ">/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter"
    "</DEFINITION-REF>")
ETAS_DTC_VALUE_RE = re.compile(
    r"DemDTC/DemDtcValue</DEFINITION-REF>\s*<VALUE>(\d+)</VALUE>")
ETAS_GEN_DIR = Path("ecu_config/bsw/gen")
ETAS_DTC_ARXML_GLOB = "*Dem_EcucValues.arxml"
ETAS_DTC_ARXML_EXCLUDE = "RTA_BIP_"
ETAS_FWD_ARXML = Path("_fwd/ecuc_configuration_values_fwd.arxml")

# --- FiMFID (zx_sys_evm_cfg_fimcfg.hpp) ---
# 成员形如 "zos::uint8_t m_FiMFID_xxx;    /// N", N 从 0 起;
# 个别成员名与分号之间会换行 (Excel 列名带换行所致), 故用 \s* 容纳.
FIM_MEMBER_RE = re.compile(r"m_(\S+)\s*;\s*///\s*(\d+)")
FIM_SIZE_RE = re.compile(r"EvmPf_FidsSize_cu8\s*=\s*(\d+)u")
FIM_STRUCT = "struct EvmPf_FuncPermission"


def find_matching_close(text, open_pos, open_tag, close_tag):
    """从 open_pos 处的 open_tag 起, 深度计数返回匹配 close_tag 的起始位置."""
    depth = 0
    pos = open_pos
    while True:
        next_open = text.find(open_tag, pos)
        next_close = text.find(close_tag, pos)
        if next_close < 0:
            raise ValueError("未找到匹配的 %s" % close_tag)
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + len(open_tag)
        else:
            depth -= 1
            if depth == 0:
                return next_close
            pos = next_close + len(close_tag)


def iter_top_level_containers(inner):
    """遍历 SUB-CONTAINERS 内容区的一级 ECUC-CONTAINER-VALUE, 逐个返回 (start, end)."""
    pos = 0
    while True:
        tag_start = inner.find(CTR_OPEN, pos)
        if tag_start < 0:
            return
        close_start = find_matching_close(inner, tag_start, CTR_OPEN, CTR_CLOSE)
        start = inner.rfind("\n", 0, tag_start) + 1
        end = close_start + len(CTR_CLOSE)
        yield start, end
        pos = end


def extract_map(text, config_set_ref, container_ref, value_re, param,
                exclude_names, label):
    """从 DemConfigSet 一级容器中提取一张映射.

    只统计 DEFINITION-REF 整串匹配 container_ref 的容器, 取容器第一个
    SHORT-NAME 与 value_re 匹配的整数值. 返回 {int key: 容器名}.
    param: 参数名 (报错用, 如 DemUdsDTC).
    exclude_names: 需跳过的容器自身名 (如 Vector 的 DemEventParameter 模板).
    """
    ref_pos = text.find(config_set_ref)
    if ref_pos < 0:
        raise ValueError("未找到 DemConfigSet 的 DEFINITION-REF")
    sub_open = text.find(SUB_OPEN, ref_pos)
    if sub_open < 0:
        raise ValueError("DemConfigSet 后未找到 <SUB-CONTAINERS>")
    sub_close_start = find_matching_close(text, sub_open, SUB_OPEN, SUB_CLOSE)
    inner_start = text.find("\n", sub_open) + 1
    close_line_start = text.rfind("\n", inner_start, sub_close_start) + 1
    inner = text[inner_start:close_line_start]

    result = {}
    for start, end in iter_top_level_containers(inner):
        block = inner[start:end]
        if container_ref not in block:
            continue
        m_name = SHORT_NAME_RE.search(block)
        if m_name is None:
            continue
        name = m_name.group(1)
        if name in exclude_names:
            continue
        m_val = value_re.search(block)
        if m_val is None:
            raise ValueError("%s 容器 %s 中未找到 %s" % (label, name, param))
        key = int(m_val.group(1))
        if key in result:
            key_str = "0x%X" % key if label == "DTC" else "%d" % key
            raise ValueError(
                "重复 %s 值 %s: %s 与 %s" % (label, key_str, result[key], name))
        result[key] = name
    return result


def extract_vector(project_dir):
    """Vector DaVinci: DTC 与 Event 在同一个 ecuc arxml."""
    text = (project_dir / VECTOR_ECUC_ARXML).read_bytes().decode("utf-8")
    dtcs = extract_map(text, VECTOR_CONFIG_SET_REF, VECTOR_DTC_REF,
                       VECTOR_DTC_VALUE_RE, "DemUdsDTC", (), "DTC")
    events = extract_map(text, VECTOR_CONFIG_SET_REF, VECTOR_EVENT_REF,
                         EVENT_ID_RE, "DemEventId", ("DemEventParameter",),
                         "Event")
    return dtcs, events


def extract_etas(project_dir):
    """ETAS RTA: DTC 在主 EcucValues arxml, Event 在 _fwd arxml."""
    gen_dir = project_dir / ETAS_GEN_DIR
    dtc_files = sorted(
        p for p in gen_dir.glob(ETAS_DTC_ARXML_GLOB)
        if not p.name.startswith(ETAS_DTC_ARXML_EXCLUDE))
    if len(dtc_files) != 1:
        msg = ("%s 下 %s (排除 %s 前缀) 匹配到 %d 个, 应恰为 1 个"
               % (ETAS_GEN_DIR, ETAS_DTC_ARXML_GLOB, ETAS_DTC_ARXML_EXCLUDE,
                  len(dtc_files)))
        if dtc_files:
            msg += ": " + ", ".join(p.name for p in dtc_files)
        raise ValueError(msg)
    fwd = gen_dir / ETAS_FWD_ARXML
    if not fwd.is_file():
        raise ValueError("未找到 %s" % (ETAS_GEN_DIR / ETAS_FWD_ARXML))

    dtc_text = dtc_files[0].read_bytes().decode("utf-8")
    fwd_text = fwd.read_bytes().decode("utf-8")
    dtcs = extract_map(dtc_text, ETAS_CONFIG_SET_REF, ETAS_DTC_REF,
                       ETAS_DTC_VALUE_RE, "DemDtcValue", (), "DTC")
    events = extract_map(fwd_text, ETAS_CONFIG_SET_REF, ETAS_EVENT_REF,
                         EVENT_ID_RE, "DemEventId", (), "Event")
    return dtcs, events


def extract_fimfid_map(hpp_path):
    """从 zx_sys_evm_cfg_fimcfg.hpp 提取 FiMFID 映射.

    取 EvmPf_FuncPermission 结构体成员 (m_<FiMFID名>; /// N),
    N 从 0 起, 返回 {N+1: FiMFID名} (yaml 键从 1 起).
    校验: 序号不重复不跳号, 成员数与 EvmPf_FidsSize_cu8 一致.
    """
    text = hpp_path.read_bytes().decode("utf-8", errors="replace")
    m_size = FIM_SIZE_RE.search(text)
    start = text.find(FIM_STRUCT)
    if m_size is None or start < 0:
        raise ValueError("未找到 EvmPf_FuncPermission 结构体或 EvmPf_FidsSize_cu8")
    end = text.find("};", start)
    if end < 0:
        raise ValueError("EvmPf_FuncPermission 结构体未闭合")
    result = {}
    for m in FIM_MEMBER_RE.finditer(text[start:end]):
        key = int(m.group(2)) + 1
        if key in result:
            raise ValueError(
                "重复 FiMFID 序号 %d: %s 与 %s" % (key, result[key], m.group(1)))
        result[key] = m.group(1)
    if not result:
        raise ValueError("EvmPf_FuncPermission 中未提取到 FiMFID 成员")
    if sorted(result) != list(range(1, len(result) + 1)):
        raise ValueError(
            "FiMFID 序号不连续: %d 个成员, 序号范围 %d-%d"
            % (len(result), min(result), max(result)))
    if len(result) != int(m_size.group(1)):
        raise ValueError(
            "FiMFID 成员数 %d 与 EvmPf_FidsSize_cu8 %s 不一致"
            % (len(result), m_size.group(1)))
    return result


def write_map(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def derive_vector_variant(project_dir):
    """Vector: <customer>/<变体>/microsar_cfg/<cfg>/build/SipAddon -> 变体名.

    取 microsar_cfg 父目录名并去掉 veh_ 前缀 (与 diag/configs 下的变体名一致),
    路径链中无 microsar_cfg 时返回 None.
    """
    for parent in project_dir.parents:
        if parent.name == "microsar_cfg":
            variant = parent.parent.name
            return variant[4:] if variant.startswith("veh_") else variant
    return None


def sync_maps_to_diag(variant, maps_dir, with_fimfid):
    """把生成的 map yaml 拷贝到 diag 工具变体目录 (diag/configs/<变体>/).

    variant 为 None (路径无法推导变体) 或目录不存在时仅提示跳过.
    """
    if variant is None:
        print("[gen_map_yaml] 注意: 无法推导变体名, 跳过拷贝到 diag")
        return
    target = DIAG_CONFIGS_DIR / variant
    if not target.is_dir():
        print("[gen_map_yaml] 注意: %s 不存在, 跳过拷贝到 diag" % target)
        return
    names = ["dtc_map.yaml", "event_map.yaml"]
    if with_fimfid:
        names.append("fimfid_map.yaml")
    for name in names:
        src = maps_dir / name
        if not src.is_file():
            print("[gen_map_yaml] 注意: %s 不存在, 未拷贝" % src)
            continue
        shutil.copy2(src, target / name)
        print("[gen_map_yaml] 已拷贝 %s -> %s" % (name, target))


def main():
    if len(sys.argv) not in (3, 4):
        print("用法: python gen_map_yaml.py <project_dir> <output_dir> "
              "[fimcfg_hpp]", file=sys.stderr)
        sys.exit(1)
    project_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    fimcfg = Path(sys.argv[3]) if len(sys.argv) == 4 else None
    if not project_dir.is_dir():
        print("ERROR: 路径不存在或不是目录: %s" % project_dir, file=sys.stderr)
        sys.exit(1)
    if fimcfg is not None and not fimcfg.is_file():
        print("ERROR: 文件不存在: %s" % fimcfg, file=sys.stderr)
        sys.exit(1)

    vector_arxml = project_dir / VECTOR_ECUC_ARXML
    etas_gen = project_dir / ETAS_GEN_DIR
    if vector_arxml.is_file() and etas_gen.is_dir():
        print("ERROR: 目录同时匹配 Vector 与 ETAS 结构: %s" % project_dir,
              file=sys.stderr)
        sys.exit(1)
    variant = None   # ETAS: autosar/<变体>/BswRta; Vector: microsar_cfg 父目录去 veh_
    try:
        if vector_arxml.is_file():
            dtcs, events = extract_vector(project_dir)
            variant = derive_vector_variant(project_dir)
        elif etas_gen.is_dir():
            dtcs, events = extract_etas(project_dir)
            variant = project_dir.parent.name
        else:
            print("ERROR: 无法判型: %s\n"
                  "  Vector 需传 SipAddon 目录 (含 %s)\n"
                  "  ETAS 需传 BswRta 目录 (含 %s)"
                  % (project_dir, VECTOR_ECUC_ARXML, ETAS_GEN_DIR),
                  file=sys.stderr)
            sys.exit(1)
    except ValueError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        sys.exit(1)

    fimfids = None
    if fimcfg is not None:
        try:
            fimfids = extract_fimfid_map(fimcfg)
        except ValueError as e:
            print("ERROR: %s" % e, file=sys.stderr)
            sys.exit(1)

    if not dtcs:
        print("ERROR: 未提取到任何 DTC 容器", file=sys.stderr)
        sys.exit(1)
    if not events:
        print("ERROR: 未提取到任何 Event 容器", file=sys.stderr)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    dtc_map = out_dir / "dtc_map.yaml"
    event_map = out_dir / "event_map.yaml"

    print("[gen_map_yaml] DTC   %d 条 -> %s" % (len(dtcs), dtc_map))
    print("[gen_map_yaml] Event %d 条 -> %s" % (len(events), event_map))
    write_map(dtc_map, ["0x%X: %s" % (k, v) for k, v in sorted(dtcs.items())])
    write_map(event_map, ["%d: %s" % (k, v) for k, v in sorted(events.items())])
    if fimfids is not None:
        fimfid_map = out_dir / "fimfid_map.yaml"
        print("[gen_map_yaml] FiMFID %d 条 -> %s" % (len(fimfids), fimfid_map))
        write_map(fimfid_map,
                  ["%d: %s" % (k, v) for k, v in sorted(fimfids.items())])
    sync_maps_to_diag(variant, out_dir, fimfids is not None)


if __name__ == "__main__":
    main()
