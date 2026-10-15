# gen_map_yaml 双模式扩展(Vector + ETAS) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gen_map_yaml.py 由仅适配 Vector DaVinci 扩展为同时适配 ETAS RTA,CLI 改为工程目录输入(SipAddon / BswRta),按目录结构自动判型,无模式开关。

**Architecture:** 单脚本双模式。容器遍历器(深度计数 + 一级迭代)两模式共用,抽取逻辑泛化为 `extract_map(text, 锚串, 值正则, 排除名)`,四种组合(Vector DTC/Event、ETAS DTC/Event)只是参数不同。ETAS 的 DTC 与 Event 分居两个文件(主 EcucValues arxml / _fwd arxml)。dem_autogen.py 仅改一处调用参数。

**Tech Stack:** Python 3.12, pathlib, re。无新增第三方依赖。

**Spec:** `docs/superpowers/specs/2026-09-19-gen-map-yaml-etas-design.md`

**工作目录:** `D:\Workspace\01_Projects\02_Src\10_tools\Dem_AutoGen_Davinci`

**验证用真实工程(只读):**
- Vector: `D:\Workspace\01_Projects\02_Src\01_Workspace_TDA4\src\mcu_app_tda4\cpj_chery\veh_v2xeu\microsar_cfg\d300e\build\SipAddon`(DTC 250 / Event 1800,已有基线输出可字节级对比)
- ETAS: `D:\Workspace\01_Projects\02_Src\02_Workspace_J6\src\mcu_app_j6\cpj_cmc\autosar\rx\BswRta`(DTC 75 / Event 603)

**关键防误判点(实现时必须遵守):**
- 容器判型锚串必须整串精确:`>/MICROSAR/Dem/DemConfigSet/DemDTCClass</DEFINITION-REF>`、`>/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTC</DEFINITION-REF>` 等(`>` 前缀 + `</DEFINITION-REF>` 后缀锚定;ETAS 的 `.../DemDTC</DEFINITION-REF>` 不会误配 `.../DemDTCAttributes</DEFINITION-REF>`,也不会误配 VALUE-REF 引用)
- ETAS 的 `*Dem_EcucValues.arxml` 必须排除 `RTA_BIP_` 前缀(RTA_BIP_Dem_EcucValues.arxml 是 1KB 的 BIP 默认值文件),匹配数必须恰为 1
- Vector Event 提取排除容器自身名为 `DemEventParameter` 的模板容器;ETAS(_fwd)无模板问题,不排除
- 容器内取第一个 SHORT-NAME(容器自身的)
- Event 值正则 `DemEventParameter/DemEventId</DEFINITION-REF>\s*<VALUE>(\d+)</VALUE>` 两种工程的完整路径不同但尾部一致,共用一个正则
- 已验证的结构事实:_fwd 中 DemConfigSet 的 DEFINITION-REF 与主 arxml 完全相同(`/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet`),其后紧跟 `<SUB-CONTAINERS>`,603 个事件容器均为一级;主 arxml 的 75 个 DemDTC 容器与事件容器同级(均为一级)

---

### Task 1: 重写 gen_map_yaml/gen_map_yaml.py 为双模式

**Files:**
- Modify: `gen_map_yaml/gen_map_yaml.py`(整文件重写)

- [x] **Step 1: 用以下完整内容覆盖原文件**

```python
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

dtc_map.yaml  : DTC 值 十六进制 (0x%X) -> DTC 容器名
event_map.yaml: DemEventId 十进制 -> Event 容器名
均按 key 数值升序, 根节点直接是映射, 无外层包裹.

用法:
  python gen_map_yaml.py <project_dir> <output_dir>
"""

import re
import sys
from pathlib import Path

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


def extract_map(text, config_set_ref, container_ref, value_re, exclude_names,
                label):
    """从 DemConfigSet 一级容器中提取一张映射.

    只统计 DEFINITION-REF 整串匹配 container_ref 的容器, 取容器第一个
    SHORT-NAME 与 value_re 匹配的整数值. 返回 {int key: 容器名}.
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
            raise ValueError("%s 容器 %s 中未找到目标参数值" % (label, name))
        key = int(m_val.group(1))
        if key in result:
            raise ValueError(
                "重复 %s 值 %d: %s 与 %s" % (label, key, result[key], name))
        result[key] = name
    return result


def extract_vector(project_dir):
    """Vector DaVinci: DTC 与 Event 在同一个 ecuc arxml."""
    text = (project_dir / VECTOR_ECUC_ARXML).read_bytes().decode("utf-8")
    dtcs = extract_map(text, VECTOR_CONFIG_SET_REF, VECTOR_DTC_REF,
                       VECTOR_DTC_VALUE_RE, (), "DTC")
    events = extract_map(text, VECTOR_CONFIG_SET_REF, VECTOR_EVENT_REF,
                         EVENT_ID_RE, ("DemEventParameter",), "Event")
    return dtcs, events


def extract_etas(project_dir):
    """ETAS RTA: DTC 在主 EcucValues arxml, Event 在 _fwd arxml."""
    gen_dir = project_dir / ETAS_GEN_DIR
    dtc_files = sorted(
        p for p in gen_dir.glob(ETAS_DTC_ARXML_GLOB)
        if not p.name.startswith(ETAS_DTC_ARXML_EXCLUDE))
    if len(dtc_files) != 1:
        raise ValueError(
            "%s 下 %s (排除 %s 前缀) 匹配到 %d 个, 应恰为 1 个"
            % (ETAS_GEN_DIR, ETAS_DTC_ARXML_GLOB, ETAS_DTC_ARXML_EXCLUDE,
               len(dtc_files)))
    fwd = gen_dir / ETAS_FWD_ARXML
    if not fwd.is_file():
        raise ValueError("未找到 %s" % ETAS_FWD_ARXML)

    dtc_text = dtc_files[0].read_bytes().decode("utf-8")
    fwd_text = fwd.read_bytes().decode("utf-8")
    dtcs = extract_map(dtc_text, ETAS_CONFIG_SET_REF, ETAS_DTC_REF,
                       ETAS_DTC_VALUE_RE, (), "DTC")
    events = extract_map(fwd_text, ETAS_CONFIG_SET_REF, ETAS_EVENT_REF,
                         EVENT_ID_RE, (), "Event")
    return dtcs, events


def write_map(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    if len(sys.argv) != 3:
        print("用法: python gen_map_yaml.py <project_dir> <output_dir>",
              file=sys.stderr)
        sys.exit(1)
    project_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    if not project_dir.is_dir():
        print("ERROR: 目录不存在: %s" % project_dir, file=sys.stderr)
        sys.exit(1)

    vector_arxml = project_dir / VECTOR_ECUC_ARXML
    etas_gen = project_dir / ETAS_GEN_DIR
    if vector_arxml.is_file() and etas_gen.is_dir():
        print("ERROR: 目录同时匹配 Vector 与 ETAS 结构: %s" % project_dir,
              file=sys.stderr)
        sys.exit(1)
    try:
        if vector_arxml.is_file():
            dtcs, events = extract_vector(project_dir)
        elif etas_gen.is_dir():
            dtcs, events = extract_etas(project_dir)
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


if __name__ == "__main__":
    main()
```

- [x] **Step 2: 语法检查**

```bash
cd "D:/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Davinci"
python -m py_compile gen_map_yaml/gen_map_yaml.py && echo SYNTAX-OK
```

Expected: `SYNTAX-OK`(删掉 py_compile 产生的 `__pycache__`)

---

### Task 2: Vector 回归(真实 SipAddon,输出临时目录,字节级对比)

**Files:** 无代码改动,只验证 Task 1

- [x] **Step 1: 错误路径探针**

```bash
cd "D:/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Davinci"
PYTHONIOENCODING=utf-8 python gen_map_yaml/gen_map_yaml.py; echo "exit=$?"
PYTHONIOENCODING=utf-8 python gen_map_yaml/gen_map_yaml.py no_such_dir /tmp; echo "exit=$?"
PYTHONIOENCODING=utf-8 python gen_map_yaml/gen_map_yaml.py . /tmp; echo "exit=$?"
```
Expected: 第一条 `用法: ...` exit=1;第二条 `ERROR: 目录不存在: ...` exit=1;第三条 `ERROR: 无法判型: ...`(工具仓库根既无 Config/ECUC arxml 也无 ecu_config)exit=1。

- [x] **Step 2: 对真实 SipAddon 跑(输出临时目录)**

```bash
TMP=$(mktemp -d)
PYTHONIOENCODING=utf-8 python gen_map_yaml/gen_map_yaml.py \
  "D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4/cpj_chery/veh_v2xeu/microsar_cfg/d300e/build/SipAddon" \
  "$TMP"
echo "TMPDIR=$TMP"
wc -l "$TMP/dtc_map.yaml" "$TMP/event_map.yaml"
```
Expected: `DTC 250 条`、`Event 1800 条`;两文件 250/1800 行。

- [x] **Step 3: 与现有基线字节级对比**

```bash
BASE="D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4/cpj_chery/veh_v2xeu/tools/Evm_Script/Evm_Config_Excel_To_Csv"
cmp "$TMP/dtc_map.yaml" "$BASE/dtc_map.yaml" && echo DTC-IDENTICAL
cmp "$TMP/event_map.yaml" "$BASE/event_map.yaml" && echo EVENT-IDENTICAL
```
Expected: `DTC-IDENTICAL` 与 `EVENT-IDENTICAL`(基线是双模式改造前版本生成的,字节一致证明 Vector 行为无回归)。

---

### Task 3: ETAS 验证(真实 BswRta,只读,输出临时目录)+ 提交

**Files:** 无代码改动,验证 + 提交 Task 1 的脚本

- [x] **Step 1: 对真实 BswRta 跑(输出临时目录)**

```bash
TMP2=$(mktemp -d)
PYTHONIOENCODING=utf-8 python gen_map_yaml/gen_map_yaml.py \
  "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/autosar/rx/BswRta" \
  "$TMP2"
echo "TMPDIR2=$TMP2"
wc -l "$TMP2/dtc_map.yaml" "$TMP2/event_map.yaml"
head -3 "$TMP2/dtc_map.yaml"; head -3 "$TMP2/event_map.yaml"
```
Expected: `DTC 75 条`、`Event 603 条`;dtc 首行 `0x330009: DemDTC_P330009_EMS_IimpError`;event 首行 `1: DemEvent_AEBEvl_Reserved1`。

- [x] **Step 2: 抽查换算**

```bash
python -c "print('%X' % 6653511)"
grep -n "^0x658647: " "$TMP2/dtc_map.yaml"
```
Expected: `658647`;grep 命中 `0x658647: DemDTC_C258647_Acore_Timeout`(主 arxml 中该容器 DemDtcValue=6653511)。

- [x] **Step 3: 与生成代码全量交叉核对**

```bash
PYTHONIOENCODING=utf-8 python - "$TMP2" <<'EOF'
import re, sys
tmp = sys.argv[1]
dem_dir = ("D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/"
           "cpj_cmc/autosar/rx/BswRta/src/bsw/Dem")
hdr = open(dem_dir + "/Dem_Cfg_EventId.h", encoding="utf-8",
           errors="replace").read()
csrc = open(dem_dir + "/Dem_Cfg_DTC_DataStructures.c", encoding="utf-8",
            errors="replace").read()
hdr_map = {int(m.group(2)): m.group(1) for m in re.finditer(
    r"#define\s+DemConf_DemEventParameter_(\S+)\s+(\d+)u", hdr)}
c_map = {int(m.group(1), 16): m.group(2) for m in re.finditer(
    r"0x([0-9A-Fa-f]{6})u&0xFFFFFFu\) << 0\) \},? /\* (\S+) \*/", csrc)}
ev = {int(k): v for k, v in
      (l.strip().split(": ", 1) for l in
       open(tmp + "/event_map.yaml", encoding="utf-8") if l.strip())}
dt = {int(k[2:], 16): v for k, v in
      (l.strip().split(": ", 1) for l in
       open(tmp + "/dtc_map.yaml", encoding="utf-8") if l.strip())}
print("Event: header %d 条, yaml %d 条, 一致=%s" % (len(hdr_map), len(ev),
                                              hdr_map == ev))
print("DTC  : 代码 %d 条, yaml %d 条, 一致=%s" % (len(c_map), len(dt),
                                              c_map == dt))
EOF
```
Expected: `Event: header 603 条, yaml 603 条, 一致=True`;`DTC : 代码 75 条, yaml 75 条, 一致=True`。任一 False 则停下排查,不得改数据迁就。

- [x] **Step 4: 提交脚本**

```bash
cd "D:/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Davinci"
git add gen_map_yaml/gen_map_yaml.py
git commit -m "$(cat <<'EOF'
feat(dem): [Dem_AutoGen] gen_map_yaml 双模式扩展, 适配 ETAS 工程 (目录输入自动判型)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: dem_autogen.py 集成改动

**Files:**
- Modify: `dem_autogen.py`(1 处)

- [x] **Step 1: Step 5/8d 参数改为 SipAddon 目录**

旧:
```python
        run_step("Step 5/8d 生成 map 表",
                 [sys.executable, str(GEN_MAP), str(paths.ecuc),
                  str(paths.evm_script / "Evm_Config_Excel_To_Csv")],
                 cwd=paths.evm_script)
```
新:
```python
        run_step("Step 5/8d 生成 map 表",
                 [sys.executable, str(GEN_MAP), str(paths.sipaddon),
                  str(paths.evm_script / "Evm_Config_Excel_To_Csv")],
                 cwd=paths.evm_script)
```

- [x] **Step 2: 语法与集成检查**

```bash
cd "D:/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Davinci"
python -m py_compile dem_autogen.py && echo SYNTAX-OK
PYTHONIOENCODING=utf-8 python dem_autogen.py --help > /dev/null && echo HELP-OK
grep -n "paths.sipaddon" dem_autogen.py
```
Expected: `SYNTAX-OK`、`HELP-OK`;grep 显示 Step 5/8d 调用处为 `str(paths.sipaddon)`(davinci_sync 等其他使用处不变)。删掉 `__pycache__`。

- [x] **Step 3: 提交集成**

```bash
git add dem_autogen.py
git commit -m "$(cat <<'EOF'
feat(dem): [Dem_AutoGen] Step 5/8d 改传 SipAddon 工程目录 (适配 gen_map_yaml 目录输入)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

不推送(用户未要求)。
