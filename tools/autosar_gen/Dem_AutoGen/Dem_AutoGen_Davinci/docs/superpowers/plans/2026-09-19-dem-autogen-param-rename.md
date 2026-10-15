# Dem_AutoGen 参数化与重命名实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** MCU 仓库路径改为必填参数 `--repo`,全部脚本/目录统一 snake_case 重命名,工具与工作区路径解耦。

**Architecture:** 主入口 `dem_autogen.py` 新增 `resolve_repo_paths()` 集中推导仓库内路径;`main()` 通过 `--repo` 参数构建路径命名空间并传给各步骤函数;子脚本仅做文件名/import 连带改名,逻辑不动。

**Tech Stack:** Python 3.12, pathlib, argparse。本仓库无测试框架,验证方式按 spec 第 4 节(py_compile / --help / 路径推导检查),不引入 pytest。

**Spec:** `docs/superpowers/specs/2026-09-19-dem-autogen-param-rename-design.md`

**提交策略:** 按用户要求,上轮未提交的旧路径修复与本轮重命名**合并为一个提交**(Task 5 验证通过后统一提交)。中间状态不提交。

**工作目录:** `D:\Workspace\01_Projects\02_Src\10_tools\Dem_AutoGen_Davinci`

---

### Task 1: 清理 __pycache__ 并重命名全部目录与文件

**Files:**
- 删除: 所有 `__pycache__/` 目录(4 处)
- 重命名: 5 个目录 + 9 个文件(用 `git mv`,保留未提交改动的重命名追踪)

- [ ] **Step 1: 删除 __pycache__ 目录**

```bash
cd "D:/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Davinci"
find . -type d -name "__pycache__" -exec rm -rf {} +
```

- [ ] **Step 2: 重命名 5 个目录**

```bash
git mv Check_Excel_Script check_dtc_table
git mv Gen_Clear_ARXML_Script clear_dem_arxml
git mv Gen_DTC_ARXML_Script gen_dtc_arxml
git mv Gen_Event_ARXML_Script gen_event_arxml
git mv Gen_Excel_To_Csv_Script excel_to_csv
```

- [ ] **Step 3: 重命名 9 个脚本文件**

```bash
git mv check_dtc_table/Check_Excel.py check_dtc_table/check_dtc_table.py
git mv clear_dem_arxml/Dem_ClearDtcEvent.py clear_dem_arxml/clear_dem_arxml.py
git mv gen_dtc_arxml/Gen_DTC_ARXML.py gen_dtc_arxml/gen_dtc_arxml.py
git mv gen_dtc_arxml/Merge_Excel.py gen_dtc_arxml/merge_excel.py
git mv gen_dtc_arxml/ModifyDtcExcel.py gen_dtc_arxml/modify_dtc_excel.py
git mv gen_dtc_arxml/ProcessArxml.py gen_dtc_arxml/process_arxml.py
git mv gen_event_arxml/Gen_Event_ARXML.py gen_event_arxml/gen_event_arxml.py
git mv gen_event_arxml/Merge_Excel.py gen_event_arxml/merge_excel.py
git mv gen_event_arxml/ProcessArxml.py gen_event_arxml/process_arxml.py
git mv excel_to_csv/Excel_To_Csv.py excel_to_csv/excel_to_csv.py
git mv Dem_AutoGen.py dem_autogen.py
```

- [ ] **Step 3b: 修正 .gitignore 的 backup 规则**

目录改名后原规则 `Gen_Clear_ARXML_Script/backup/` 失效,改为:

```
old: Gen_Clear_ARXML_Script/backup/
new: clear_dem_arxml/backup/
```

- [ ] **Step 4: 确认 rename 状态正确**

```bash
git status --short
```

Expected: 所有行首为 `R`(renamed),`Dem_AutoGen.py` 与 `Gen_Clear_ARXML_Script/Dem_ClearDtcEvent.py` 为 `RM`(rename + 保留上轮未提交修改);无 `??` 未跟踪残留(backup/、Excel_Table/ 已在 git 管理或忽略)。

---

### Task 2: dem_autogen.py 参数化重构

**Files:**
- Modify: `dem_autogen.py`(全量重写,以下为完整新文件内容)

- [ ] **Step 1: 用以下完整内容覆盖 dem_autogen.py**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dem_autogen - Vector Dem 自动生成工具 (一键流程).

流程:
  1. 检查 DTC 表 (check_dtc_table/check_dtc_table.py, 失败则中止, 不占用 license)
  2. 连接 license (USB over Network Client -> CodeMeter-Stick)
  3. 清除 DTC/Event : 调用 clear_dem_arxml/clear_dem_arxml.py
  4. DaVinci 自动 sync (DVCfgCmd --syncSystemDescription --saveProject)
  5. 依次执行 excel_to_csv -> gen_dtc_arxml -> gen_event_arxml
  6. DaVinci 自动 sync
  7. 生成 Dem 代码 (DVCfgCmd --generate --modulesToGenerate /MICROSAR/Dem)
  8. 断开 license (无论中间步骤成败, 都会释放加密狗)

用法:
  python dem_autogen.py <DTC表.xlsx> --repo <mcu_app_tda4路径>
  python dem_autogen.py <DTC表.xlsx> --repo <mcu_app_tda4路径> --skip-gen
        # --skip-gen: 只更新 arxml, 不生成 Dem 代码
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

GEN_TOOLS = Path(__file__).resolve().parent

VARIANT = "veh_v2xeu"
CFG_DIR = "d300e"
SHEET = "RCore_Event_d300e"

CLEAR_SCRIPT = GEN_TOOLS / "clear_dem_arxml" / "clear_dem_arxml.py"
EXCEL_TO_CSV = GEN_TOOLS / "excel_to_csv" / "excel_to_csv.py"
GEN_DTC = GEN_TOOLS / "gen_dtc_arxml" / "gen_dtc_arxml.py"
GEN_EVENT = GEN_TOOLS / "gen_event_arxml" / "gen_event_arxml.py"
CHECK_EXCEL = GEN_TOOLS / "check_dtc_table" / "check_dtc_table.py"

# license: USB over Network Client 连接服务器上的 WIBU CodeMeter-Stick
USBCLNCMD = Path(r"D:\Program Files\USB over Network\usbclncmd.exe")
LICENSE_SRV_ID = "0"
LICENSE_VID_PID_REV = "064f:2af9:0100"
LICENSE_SERIAL = "000005243417"

TEMP_CSVS = ["Merger_Total_Event_Temporary.csv", "DTC_Message.csv"]


def resolve_repo_paths(repo: Path):
    """由 --repo 参数推导 MCU 仓库内的所有目标路径."""
    evm_script = repo / "cpj_chery" / VARIANT / "tools" / "Evm_Script"
    sipaddon = (
        repo / "cpj_chery" / VARIANT / "microsar_cfg" / CFG_DIR
        / "build" / "SipAddon"
    )
    return SimpleNamespace(
        repo=repo,
        evm_script=evm_script,
        sipaddon=sipaddon,
        ecuc=sipaddon / "Config" / "ECUC" / "StartApplication_Dem_Dem_ecuc.arxml",
        dpa=sipaddon / "Demo.dpa",
        dvcfg_cmd=(repo / "microsar_tools_tda4" / "DaVinciConfigurator"
                   / "Core" / "DVCfgCmd.exe"),
    )


def run_step(title, cmd, cwd, tail_on_fail=25, check=True):
    print("[dem_autogen] ==> %s" % title)
    t0 = time.time()
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    dt = time.time() - t0
    if check and proc.returncode != 0:
        print(proc.stdout[-3000:] if proc.stdout else "")
        print(proc.stderr[-3000:] if proc.stderr else "")
        print("[dem_autogen] FAILED (exit %d, %.0fs): %s"
              % (proc.returncode, dt, title))
        sys.exit(1)
    print("[dem_autogen]     OK (%.0fs)" % dt)
    return proc


def check_dtc_table(excel):
    """调用 check_dtc_table.py 校验 DTC 表, 失败则中止."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_dtc_table", CHECK_EXCEL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print("[dem_autogen] ==> Step 1/8 检查 DTC 表 (%s)" % excel.name)
    error_count = mod.check_excel(str(excel))
    if error_count:
        print("[dem_autogen] ERROR: DTC 表校验失败, 共 %d 个错误, 已中止 (未连接 license)"
              % error_count)
        sys.exit(1)
    print("[dem_autogen]     OK, DTC 表校验通过")


def davinci_sync(step_title, paths):
    """sync + save. clear 后的中间态会有大量 reference 校验错误, 属预期, 不作为失败依据.

    判定失败: sync 未完成 / 工程被 UI 锁定 / save 未完成.
    注意: 结果信息只写进 DVCfgCmd.log (每次运行覆盖), stdout 不含关键行.
    """
    run_step(
        step_title + " (DaVinci sync)",
        [str(paths.dvcfg_cmd), "--project", str(paths.dpa),
         "--syncSystemDescription", "--saveProject", "--validate"],
        cwd=paths.sipaddon, check=False,
    )
    log = (paths.sipaddon / "DVCfgCmd.log").read_text(encoding="utf-8", errors="replace")
    if "could not be saved" in log:
        print("[dem_autogen] ERROR: 工程被锁定, 请关闭 DaVinci Configurator UI 后重试")
        sys.exit(1)
    if "Action 'Synchronizing System Description...' successfully finished" not in log:
        print("[dem_autogen] ERROR: System Description 同步未完成, 详见 %s"
              % (paths.sipaddon / "DVCfgCmd.log"))
        sys.exit(1)
    if "Project saved" not in log:
        print("[dem_autogen] ERROR: 工程保存失败, 详见 %s"
              % (paths.sipaddon / "DVCfgCmd.log"))
        sys.exit(1)
    import re
    m = re.search(r"(Validation and Generation result summary:\s*[\r\n]+.*)", log)
    if m:
        print("[dem_autogen]     %s" % " ".join(m.group(1).split()))


def license_connect(repo):
    run_step(
        "Step 2/8 连接 license (CodeMeter-Stick %s)" % LICENSE_SERIAL,
        [str(USBCLNCMD), "connect", LICENSE_SRV_ID,
         "-a", LICENSE_VID_PID_REV, "-s", LICENSE_SERIAL],
        cwd=repo,
    )


def license_disconnect(repo):
    run_step(
        "Step 8/8 断开 license",
        [str(USBCLNCMD), "disconnect", LICENSE_SRV_ID,
         "-a", LICENSE_VID_PID_REV, "-s", LICENSE_SERIAL],
        cwd=repo,
    )


def main():
    parser = argparse.ArgumentParser(description="Vector Dem auto generation tool")
    parser.add_argument("excel", help="DTC 表 xlsx 路径")
    parser.add_argument("--repo", required=True,
                        help="mcu_app_tda4 仓库根目录 (绝对或相对路径)")
    parser.add_argument("--sheet", default=SHEET, help="Excel sheet 名 (默认 %s)" % SHEET)
    parser.add_argument("--skip-gen", action="store_true",
                        help="只更新 arxml, 不执行 Dem 代码生成")
    args = parser.parse_args()

    excel = Path(args.excel).resolve()
    repo = Path(args.repo).resolve()
    paths = resolve_repo_paths(repo)

    for f in (excel, paths.ecuc, paths.dpa, paths.dvcfg_cmd, USBCLNCMD,
              CLEAR_SCRIPT, EXCEL_TO_CSV, GEN_DTC, GEN_EVENT, CHECK_EXCEL):
        if not f.is_file():
            print("[dem_autogen] ERROR: 文件不存在: %s" % f)
            sys.exit(1)

    print("[dem_autogen] DTC 表    : %s" % excel.name)
    print("[dem_autogen] MCU 仓库  : %s" % repo)
    print("[dem_autogen] 目标 arxml: %s" % paths.ecuc)
    print("[dem_autogen] DaVinci   : %s" % paths.dpa)

    check_dtc_table(excel)
    license_connect(repo)
    try:
        # 3. 清除 DTC 和 Event
        run_step("Step 3/8 清除 DTC/Event",
                 [sys.executable, str(CLEAR_SCRIPT), str(paths.ecuc)], cwd=repo)

        # 4. DaVinci 自动 sync
        davinci_sync("Step 4/8", paths)

        # 5. 执行 dem arxml 生成脚本
        run_step("Step 5/8a Excel 转 CSV",
                 [sys.executable, str(EXCEL_TO_CSV), excel.name, "Evm_Config_Excel_To_Csv"],
                 cwd=paths.evm_script)
        run_step("Step 5/8b 生成 DTC ARXML",
                 [sys.executable, str(GEN_DTC), excel.name, args.sheet, str(paths.ecuc)],
                 cwd=paths.evm_script)
        for csv in TEMP_CSVS:
            (paths.evm_script / csv).unlink(missing_ok=True)
        run_step("Step 5/8c 生成 Event ARXML",
                 [sys.executable, str(GEN_EVENT), excel.name, args.sheet, str(paths.ecuc)],
                 cwd=paths.evm_script)
        for csv in TEMP_CSVS:
            (paths.evm_script / csv).unlink(missing_ok=True)

        # 6. DaVinci 自动 sync
        davinci_sync("Step 6/8", paths)

        # 7. 生成 Dem 代码
        if args.skip_gen:
            print("[dem_autogen] --skip-gen: 跳过 Dem 代码生成")
        else:
            run_step("Step 7/8 生成 Dem 代码",
                     [str(paths.dvcfg_cmd), "--project", str(paths.dpa),
                      "--generate", "--modulesToGenerate", "/MICROSAR/Dem"],
                     cwd=paths.sipaddon)
    finally:
        license_disconnect(repo)

    print("[dem_autogen] 全部完成")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 语法检查**

```bash
cd "D:/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Davinci"
python -m py_compile dem_autogen.py && echo SYNTAX-OK
```

Expected: `SYNTAX-OK`

---

### Task 3: clear_dem_arxml.py 接口修改

**Files:**
- Modify: `clear_dem_arxml/clear_dem_arxml.py`

- [ ] **Step 1: 更新 docstring 用法说明**

旧:
```python
用法:
  python Dem_ClearDtcEvent.py [ecuc_arxml_path]
  不带参数时使用默认的 v2xeu 目标文件
```

新:
```python
用法:
  python clear_dem_arxml.py <ecuc_arxml_path>
```

- [ ] **Step 2: 删除 DEFAULT_TARGET 常量块**

删除以下整块(含其上方注释行 `# 工具位于仓库外 (10_tools), 仓库在 <02_Src>/...`):
```python
DEFAULT_TARGET = Path(__file__).resolve().parents[3] / (
    r"01_Workspace_TDA4\src\mcu_app_tda4\cpj_chery\veh_v2xeu\microsar_cfg\d300e\build\SipAddon\Config\ECUC"
    r"\StartApplication_Dem_Dem_ecuc.arxml"
)
```

- [ ] **Step 3: main() 改为必填参数**

旧:
```python
def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET
    if not target.is_file():
        print("ERROR: 文件不存在: %s" % target, file=sys.stderr)
        sys.exit(1)
    clear_dtc_events(target)
```

新:
```python
def main():
    if len(sys.argv) != 2:
        print("用法: python clear_dem_arxml.py <ecuc_arxml_path>", file=sys.stderr)
        sys.exit(1)
    target = Path(sys.argv[1])
    if not target.is_file():
        print("ERROR: 文件不存在: %s" % target, file=sys.stderr)
        sys.exit(1)
    clear_dtc_events(target)
```

- [ ] **Step 4: 日志前缀改名**

文件内 5 处 `[Dem_ClearDtcEvent]` 全部替换为 `[clear_dem_arxml]`(用 replace_all)。

- [ ] **Step 5: 语法检查**

```bash
python -m py_compile clear_dem_arxml/clear_dem_arxml.py && echo SYNTAX-OK
```

Expected: `SYNTAX-OK`

---

### Task 4: gen_dtc_arxml.py / gen_event_arxml.py 连带改名

**Files:**
- Modify: `gen_dtc_arxml/gen_dtc_arxml.py`
- Modify: `gen_event_arxml/gen_event_arxml.py`

**注意:** 替换必须用下面精确的 old_string,不能全局替换 `Merge_Excel` —— 文件里有常量 `DEM_REF_Merge_Excel_Path` 含该子串,误替换会破坏代码。`ProcessArxml.ProcessArxml(` 中前者是模块名(要改)后者是函数名(不改)。

- [ ] **Step 1: gen_dtc_arxml.py import 与调用点改名(6 处精确替换)**

| 旧字符串 | 新字符串 |
|---|---|
| `import ProcessArxml` | `import process_arxml` |
| `import Merge_Excel` | `import merge_excel` |
| `import ModifyDtcExcel` | `import modify_dtc_excel` |
| `ProcessArxml.ProcessArxml(` | `process_arxml.ProcessArxml(` |
| `Merge_Excel.Merge_Sheet` | `merge_excel.Merge_Sheet` |
| `ModifyDtcExcel.GetDTCMessage` | `modify_dtc_excel.GetDTCMessage` |

- [ ] **Step 2: gen_dtc_arxml.py 删除死常量**

删除行:
```python
DEM_ARXML_FILE_PATH = r"..\..\..\cpj_eezi\microsar_cfg\build\SipAddon\Config\ECUC\StartApplication_Dem_Dem_ecuc.arxml"
```
(该常量被 `main` 块中 `DEM_ARXML_FILE_PATH = sys.argv[3]` 覆盖,后者保留不动。)

- [ ] **Step 3: gen_event_arxml.py import 与调用点改名(4 处精确替换)**

| 旧字符串 | 新字符串 |
|---|---|
| `import ProcessArxml` | `import process_arxml` |
| `import Merge_Excel` | `import merge_excel` |
| `ProcessArxml.ProcessArxml(` | `process_arxml.ProcessArxml(` |
| `Merge_Excel.Merge_Sheet` | `merge_excel.Merge_Sheet` |

- [ ] **Step 4: gen_event_arxml.py 删除死常量**

删除行(该脚本中的同名 `DEM_ARXML_FILE_PATH`,内容为旧仓库相对路径;`main` 块中 `DEM_ARXML_FILE_PATH = sys.argv[3]` 保留)。

- [ ] **Step 5: 语法检查两个脚本**

```bash
python -m py_compile gen_dtc_arxml/gen_dtc_arxml.py gen_event_arxml/gen_event_arxml.py && echo SYNTAX-OK
```

Expected: `SYNTAX-OK`

---

### Task 5: 全量验证

- [ ] **Step 1: py_compile 全部脚本**

```bash
cd "D:/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Davinci"
python -m py_compile dem_autogen.py check_dtc_table/check_dtc_table.py clear_dem_arxml/clear_dem_arxml.py excel_to_csv/excel_to_csv.py gen_dtc_arxml/gen_dtc_arxml.py gen_dtc_arxml/merge_excel.py gen_dtc_arxml/modify_dtc_excel.py gen_dtc_arxml/process_arxml.py gen_event_arxml/gen_event_arxml.py gen_event_arxml/merge_excel.py gen_event_arxml/process_arxml.py && echo ALL-OK
```

Expected: `ALL-OK`

- [ ] **Step 2: --help 输出确认**

```bash
python dem_autogen.py --help
```

Expected: usage 行含 `--repo`,且标注 `(required)`。

- [ ] **Step 3: 缺 --repo 时报错**

```bash
python dem_autogen.py some.xlsx; echo "exit=$?"
```

Expected: argparse 报错 `the following arguments are required: --repo`,`exit=2`。

- [ ] **Step 4: 路径推导检查(真实 repo,不连 license、不写文件)**

```bash
python -c "
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('dem_autogen', 'dem_autogen.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
p = mod.resolve_repo_paths(Path(r'D:\Workspace\01_Projects\02_Src\01_Workspace_TDA4\src\mcu_app_tda4'))
ok = True
for name in ('ecuc', 'dpa', 'dvcfg_cmd', 'evm_script'):
    v = getattr(p, name); e = v.exists(); ok = ok and e
    print('%-10s %-6s %s' % (name, 'OK' if e else 'MISS', v))
for name in ('CLEAR_SCRIPT', 'EXCEL_TO_CSV', 'GEN_DTC', 'GEN_EVENT', 'CHECK_EXCEL'):
    v = getattr(mod, name); e = v.is_file(); ok = ok and e
    print('%-12s %-6s %s' % (name, 'OK' if e else 'MISS', v))
assert ok, 'HAS MISSING PATH'
print('ALL-PATHS-OK')
"
```

Expected: 9 行全 OK,末尾 `ALL-PATHS-OK`。

- [ ] **Step 5: clear_dem_arxml.py 无参数报错**

```bash
python clear_dem_arxml/clear_dem_arxml.py; echo "exit=$?"
```

Expected: 输出 `用法: python clear_dem_arxml.py <ecuc_arxml_path>`,`exit=1`。

---

### Task 6: 提交(合并旧路径修复)

- [ ] **Step 1: 检查最终状态**

```bash
git status --short && git diff --stat
```

Expected: 全部为 rename + modify,无未跟踪残留。

- [ ] **Step 2: 提交**

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor(dem): [Dem_AutoGen] mcu repo 改为 --repo 必填参数并统一 snake_case 命名

- 仓库路径与工具解耦: 删除 REPO/DEFAULT_TARGET 硬编码, dem_autogen.py 新增 --repo 必填参数
- 路径推导集中到 resolve_repo_paths()
- 全部脚本与目录重命名: Dem_AutoGen->dem_autogen, Check_Excel->check_dtc_table,
  Dem_ClearDtcEvent->clear_dem_arxml, Gen_DTC_ARXML->gen_dtc_arxml, Gen_Event_ARXML->gen_event_arxml,
  Excel_To_Csv->excel_to_csv, Merge_Excel->merge_excel, ModifyDtcExcel->modify_dtc_excel,
  ProcessArxml->process_arxml
- clear_dem_arxml.py ecuc 路径改为必填参数
- 删除被 argv 覆盖的死常量 DEM_ARXML_FILE_PATH
- 日志前缀统一为新脚本名

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

注: 工单号栏按仓库现状无对应 JIRA 工单,置 `[Dem_AutoGen]` 标识;如需改为工单号,执行时询问用户。

- [ ] **Step 3: 确认提交**

```bash
git log --oneline -2 && git status --short
```

Expected: 新提交在顶部,工作区干净。不推送(用户未要求)。
