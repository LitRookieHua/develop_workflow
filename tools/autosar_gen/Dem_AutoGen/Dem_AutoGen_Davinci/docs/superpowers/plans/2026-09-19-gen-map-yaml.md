# gen_map_yaml (Step 5/8d) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新脚本 `gen_map_yaml.py` 从生成的 Dem ecuc arxml 提取 DTC/Event 映射生成 `dtc_map.yaml` + `event_map.yaml`,并作为 dem_autogen 主流程 Step 5/8d 执行。

**Architecture:** 容器级正则扫描(复用 `clear_dem_arxml.py` 已验证的 find_matching_close / iter_top_level_containers 模式),单遍流式读 23MB arxml;纯文本写两张按 key 升序的映射表;dem_autogen.py 加 GEN_MAP 常量与 Step 5/8d 调用。

**Tech Stack:** Python 3.12, pathlib, re。无新增第三方依赖,无测试框架(验证方式按 spec 第 4 节)。

**Spec:** `docs/superpowers/specs/2026-09-19-gen-map-yaml-design.md`

**工作目录:** `D:\Workspace\01_Projects\02_Src\10_tools\Dem_AutoGen_Davinci`

**真实 arxml(用于 standalone 验证,只读):** `D:\Workspace\01_Projects\02_Src\01_Workspace_TDA4\src\mcu_app_tda4\cpj_chery\veh_v2xeu\microsar_cfg\d300e\build\SipAddon\Config\ECUC\StartApplication_Dem_Dem_ecuc.arxml`

**关键防误判点(实现时必须遵守):**
- 容器判型用**整串精确匹配**:`>/MICROSAR/Dem/DemConfigSet/DemDTCClass</DEFINITION-REF>` 与 `>/MICROSAR/Dem/DemConfigSet/DemEventParameter</DEFINITION-REF>`(前缀 `>` 后缀 `</DEFINITION-REF>` 锚定,避免误匹配参数级引用如 `.../DemEventParameter/DemEventId`)
- 排除 SHORT-NAME 字面为 `DemEventParameter` 的模板容器(判容器自身名 `name == "DemEventParameter"`,不用块内子串匹配,防误伤含同名嵌套子容器的真实 Event)
- 容器内取**第一个** SHORT-NAME(容器自身的,嵌套子容器名在后)

---

### Task 1: 创建 gen_map_yaml/gen_map_yaml.py

**Files:**
- Create: `gen_map_yaml/gen_map_yaml.py`

- [x] **Step 1: 写入以下完整内容**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_map_yaml - 从 Dem ecuc arxml 提取 DTC/Event 映射, 生成 dtc_map.yaml / event_map.yaml.

dtc_map.yaml  : DemUdsDTC 十六进制 (0x%X) -> DemDTC 容器名
event_map.yaml: DemEventId 十进制 -> DemEvent 容器名
均按 key 数值升序, 根节点直接是映射, 无外层包裹.

用法:
  python gen_map_yaml.py <ecuc_arxml> <output_dir>
"""

import re
import sys
from pathlib import Path

DEM_CONFIG_SET_REF = (
    '<DEFINITION-REF DEST="ECUC-PARAM-CONF-CONTAINER-DEF">'
    "/MICROSAR/Dem/DemConfigSet</DEFINITION-REF>"
)
SUB_OPEN = "<SUB-CONTAINERS>"
SUB_CLOSE = "</SUB-CONTAINERS>"
CTR_OPEN = "<ECUC-CONTAINER-VALUE"
CTR_CLOSE = "</ECUC-CONTAINER-VALUE>"

DTC_CLASS_REF = ">/MICROSAR/Dem/DemConfigSet/DemDTCClass</DEFINITION-REF>"
EVENT_PARAM_REF = ">/MICROSAR/Dem/DemConfigSet/DemEventParameter</DEFINITION-REF>"

DTC_VALUE_RE = re.compile(
    r"DemDTCClass/DemUdsDTC</DEFINITION-REF>\s*<VALUE>(\d+)</VALUE>")
EVENT_ID_RE = re.compile(
    r"DemEventParameter/DemEventId</DEFINITION-REF>\s*<VALUE>(\d+)</VALUE>")
SHORT_NAME_RE = re.compile(r"<SHORT-NAME>([^<]+)</SHORT-NAME>")


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


def extract_maps(text):
    """提取映射, 返回 (dtcs, events). dtcs: {int DemUdsDTC: name}, events: {int DemEventId: name}."""
    ref_pos = text.find(DEM_CONFIG_SET_REF)
    if ref_pos < 0:
        raise ValueError("未找到 DemConfigSet 的 DEFINITION-REF")
    sub_open = text.find(SUB_OPEN, ref_pos)
    if sub_open < 0:
        raise ValueError("DemConfigSet 后未找到 <SUB-CONTAINERS>")
    sub_close_start = find_matching_close(text, sub_open, SUB_OPEN, SUB_CLOSE)
    inner_start = text.find("\n", sub_open) + 1
    close_line_start = text.rfind("\n", inner_start, sub_close_start) + 1
    inner = text[inner_start:close_line_start]

    dtcs, events = {}, {}
    for start, end in iter_top_level_containers(inner):
        block = inner[start:end]
        m_name = SHORT_NAME_RE.search(block)
        if m_name is None:
            continue
        name = m_name.group(1)
        if DTC_CLASS_REF in block:
            m_val = DTC_VALUE_RE.search(block)
            if m_val is None:
                raise ValueError("DTC 容器 %s 中未找到 DemUdsDTC" % name)
            key = int(m_val.group(1))
            if key in dtcs:
                raise ValueError(
                    "重复 DTC 值 0x%X: %s 与 %s" % (key, dtcs[key], name))
            dtcs[key] = name
        elif EVENT_PARAM_REF in block:
            if name == "DemEventParameter":
                continue
            m_val = EVENT_ID_RE.search(block)
            if m_val is None:
                raise ValueError("Event 容器 %s 中未找到 DemEventId" % name)
            key = int(m_val.group(1))
            if key in events:
                raise ValueError(
                    "重复 DemEventId %d: %s 与 %s" % (key, events[key], name))
            events[key] = name
    return dtcs, events


def write_map(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    if len(sys.argv) != 3:
        print("用法: python gen_map_yaml.py <ecuc_arxml> <output_dir>",
              file=sys.stderr)
        sys.exit(1)
    arxml = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    if not arxml.is_file():
        print("ERROR: 文件不存在: %s" % arxml, file=sys.stderr)
        sys.exit(1)

    try:
        text = arxml.read_bytes().decode("utf-8")
        dtcs, events = extract_maps(text)
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

Expected: `SYNTAX-OK`(py_compile 产生的 `__pycache__` 删掉)

---

### Task 2: standalone 验证(真实 arxml,只读;输出到临时目录)

**Files:** 无代码改动,只验证 Task 1 的脚本

- [x] **Step 1: 错误路径探针(不读大文件)**

```bash
cd "D:/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Davinci"
python gen_map_yaml/gen_map_yaml.py; echo "exit=$?"
python gen_map_yaml/gen_map_yaml.py no_such.arxml /tmp; echo "exit=$?"
```
Expected: 第一条输出 `用法: python gen_map_yaml.py <ecuc_arxml> <output_dir>` exit=1;第二条输出 `ERROR: 文件不存在: ...` exit=1。

- [x] **Step 2: 对真实 arxml 跑提取(输出到临时目录)**

```bash
TMP=$(mktemp -d)
PYTHONIOENCODING=utf-8 python gen_map_yaml/gen_map_yaml.py \
  "D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4/cpj_chery/veh_v2xeu/microsar_cfg/d300e/build/SipAddon/Config/ECUC/StartApplication_Dem_Dem_ecuc.arxml" \
  "$TMP"
echo "TMPDIR=$TMP"
wc -l "$TMP/dtc_map.yaml" "$TMP/event_map.yaml"
head -3 "$TMP/dtc_map.yaml"; head -3 "$TMP/event_map.yaml"
```
Expected: 两行统计(`DTC 250 条`、`Event N 条`);dtc_map.yaml 恰 250 行;行格式 `0x600016: DemDTC_...`、`1801: DemEvent_...`,升序。

- [x] **Step 3: 条数与内容交叉核对(独立于脚本统计)**

```bash
ARXML="D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4/cpj_chery/veh_v2xeu/microsar_cfg/d300e/build/SipAddon/Config/ECUC/StartApplication_Dem_Dem_ecuc.arxml"
echo "arxml 中 DemDTC_ 容器名数: $(grep -c "<SHORT-NAME>DemDTC_" "$ARXML")"
echo "arxml 中 DemEvent_ 容器名数: $(grep -c "<SHORT-NAME>DemEvent_" "$ARXML")"
echo "yaml DTC 行数 / Event 行数: $(wc -l < "$TMP/dtc_map.yaml") / $(wc -l < "$TMP/event_map.yaml")"
```
Expected: DTC 名数 = yaml DTC 行数(均应为 250);DemEvent_ 名数 = yaml Event 行数(模板与 DemEventClass 均不进表;`<SHORT-NAME>DemEvent_` 计数已天然排除模板 `DemEventParameter`,因为模板名无下划线后缀)。

- [x] **Step 4: 抽查条目与 arxml 一致**

```bash
ARXML="D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4/cpj_chery/veh_v2xeu/microsar_cfg/d300e/build/SipAddon/Config/ECUC/StartApplication_Dem_Dem_ecuc.arxml"
head -1 "$TMP/dtc_map.yaml"
grep -n "DemDTC_C200016_KL30_TooLow" "$ARXML" | head -1
grep -n -A8 "<SHORT-NAME>DemDTC_C200016_KL30_TooLow" "$ARXML" | grep -A1 "DemUdsDTC</DEFINITION-REF>" | head -2
head -1 "$TMP/event_map.yaml"
```
Expected: yaml 首行 DTC 的十六进制值与 arxml 中该容器的 `DemUdsDTC` 十进制换算一致(6291478 ↔ 0x600016);event 首行 id 与 arxml 中首个 DemEvent_ 容器一致(实测为 1;注意模板容器 DemEventParameter 的 DemEventId=1801 不入表)。手工核对换算: `python -c "print(0x%X % 6291478)"` → `600016`。

- [x] **Step 5: 排序与格式检查**

```bash
sort -c <(cut -d: -f1 "$TMP/dtc_map.yaml" | sed "s/0x//;s/./&/" | tr "abcdef" "ABCDEF") 2>/dev/null && echo SORTCHECK-skipped || true
```
(排序由脚本 `sorted()` 保证;此步用肉眼核对 head/tail 各 3 行升序即可,复杂 shell 排序检查不做。)
Expected: head 与 tail 均严格升序。

- [x] **Step 6: 提交脚本**

```bash
cd "D:/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Davinci"
git add gen_map_yaml/gen_map_yaml.py
git commit -m "$(cat <<'EOF'
feat(dem): [Dem_AutoGen] 新增 gen_map_yaml 脚本, 从 Dem arxml 提取 DTC/Event 生成 map 表

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: dem_autogen.py 集成 Step 5/8d

**Files:**
- Modify: `dem_autogen.py`(4 处)

- [x] **Step 1: docstring 流程行更新**

旧(第 10 行):
```
  5. 依次执行 excel_to_csv -> gen_dtc_arxml -> gen_event_arxml
```
新:
```
  5. 依次执行 excel_to_csv -> gen_dtc_arxml -> gen_event_arxml -> gen_map_yaml
```

- [x] **Step 2: 新增 GEN_MAP 常量**

在 `CHECK_EXCEL = ...` 行之后新增一行:
```python
GEN_MAP = GEN_TOOLS / "gen_map_yaml" / "gen_map_yaml.py"
```

- [x] **Step 3: 启动检查列表加入 GEN_MAP**

旧:
```python
    for f in (excel, paths.ecuc, paths.dpa, paths.dvcfg_cmd, USBCLNCMD,
              CLEAR_SCRIPT, EXCEL_TO_CSV, GEN_DTC, GEN_EVENT, CHECK_EXCEL):
```
新:
```python
    for f in (excel, paths.ecuc, paths.dpa, paths.dvcfg_cmd, USBCLNCMD,
              CLEAR_SCRIPT, EXCEL_TO_CSV, GEN_DTC, GEN_EVENT, CHECK_EXCEL,
              GEN_MAP):
```

- [x] **Step 4: 插入 Step 5/8d 调用**

在 5c 的 `for csv in TEMP_CSVS:` 循环之后、`# 6. DaVinci 自动 sync` 注释之前插入:
```python
        run_step("Step 5/8d 生成 map 表",
                 [sys.executable, str(GEN_MAP), str(paths.ecuc),
                  str(paths.evm_script / "Evm_Config_Excel_To_Csv")],
                 cwd=paths.evm_script)
```

- [x] **Step 5: 语法与集成检查**

```bash
python -m py_compile dem_autogen.py && echo SYNTAX-OK
python dem_autogen.py --help > /dev/null && echo HELP-OK
grep -n "GEN_MAP\|Step 5/8d" dem_autogen.py
```
Expected: `SYNTAX-OK`、`HELP-OK`;grep 显示 4 处(常量定义、检查列表、run_step 标题、命令行)。py_compile 产生的 `__pycache__` 删掉。

- [x] **Step 6: 提交集成**

```bash
git add dem_autogen.py
git commit -m "$(cat <<'EOF'
feat(dem): [Dem_AutoGen] 主流程集成 Step 5/8d 生成 dtc_map/event_map 表

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

不推送(用户未要求)。
