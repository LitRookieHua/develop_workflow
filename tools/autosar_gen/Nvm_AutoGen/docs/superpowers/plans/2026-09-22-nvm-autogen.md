# Nvm_AutoGen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建三层 Nvm_AutoGen 工具（统一入口 + Davinci/ETAS 子工具），实现 NVM arxml 更新、BSW 代码生成、PDM 代码生成的一键流程。

**Architecture:** 完全对齐 Dem_AutoGen 三层结构。`Nvm_AutoGen/Nvm_AutoGen.py` 按仓库目录结构判型（ETAS: `cpj_*/autosar/<config>/BswRta`；Davinci: `*/(<config>|veh_<config>)/microsar_cfg`）后参数转发给子工具；子工具由 configs/ yaml 三开关（check_nvm_table OFF / gen_nvm_arxml ON / gen_pdm_code ON）控制流程。源脚本从两个 MCU 仓库拷贝，仅 J6 CrmGen.py 做参数化改造。

**Tech Stack:** Python 3 + PyYAML + openpyxl/pandas（源脚本既有依赖）；DaVinci DVCfgCmd（TDA4）；ISOLAR-AB headless + Cobra.exe（J6）。

**注意：**
- `10_tools` **不是 git 仓库**，所有任务跳过 commit 步骤，以验证命令代替。
- 路径约定（下文 `$TOOLS` = `D:/Workspace/01_Projects/02_Src/10_tools`）：
  - `$TDA4` = `D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4`
  - `$J6` = `D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6`
- 与 Dem 的结构差异：子工具放在 `Nvm_AutoGen/` 入口目录**内**（Dem 的实际工作结构；顶层重复副本是历史遗留，不复制这种混乱）。
- J6 的 `CrmGen.py` 输出含 `replace_time` 时间戳替换，每次运行产物必有时间戳行差异——git diff 验证时这是预期结果。

---

### Task 1: 拷贝 TDA4 源脚本到 Nvm_AutoGen_Davinci

**Files:**
- Create: `$TOOLS/Nvm_AutoGen/Nvm_AutoGen_Davinci/gen_nvm_arxml/{ExcelAnalize.py,GenPdmARXML.py,ProcessArxml.py}`
- Create: `$TOOLS/Nvm_AutoGen/Nvm_AutoGen_Davinci/gen_pdm_code/{CrmGen.py,ExcelAnalize.py,Merge_Excel.py,TemplateFile.py}`
- Create: `$TOOLS/Nvm_AutoGen/Nvm_AutoGen_Davinci/gen_pdm_code/template/{pdm_cfg_T.h,pdm_cfg_dataitem_config_T.cpp,pdmdb_T.cpp,pdmdb_T.h}`

**Files:**
- 源：`$TDA4/tools/Gen_Pdm_Script/NvM_Develop_Gen_ARXML_Script/`（3 个 .py）
- 源：`$TDA4/tools/Gen_Pdm_Script/PDM_Gen_Crm_Script/`（4 个 .py + template/ 4 个模板）
- 零改动拷贝（TDA4 两个脚本均已参数化）

- [ ] **Step 1: 拷贝 gen_nvm_arxml**

```bash
mkdir -p "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Davinci/gen_nvm_arxml"
cp "D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4/tools/Gen_Pdm_Script/NvM_Develop_Gen_ARXML_Script/ExcelAnalize.py" \
   "D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4/tools/Gen_Pdm_Script/NvM_Develop_Gen_ARXML_Script/GenPdmARXML.py" \
   "D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4/tools/Gen_Pdm_Script/NvM_Develop_Gen_ARXML_Script/ProcessArxml.py" \
   "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Davinci/gen_nvm_arxml/"
```

- [ ] **Step 2: 拷贝 gen_pdm_code（含 template/）**

```bash
mkdir -p "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Davinci/gen_pdm_code"
cp -r "D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4/tools/Gen_Pdm_Script/PDM_Gen_Crm_Script/ExcelAnalize.py" \
      "D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4/tools/Gen_Pdm_Script/PDM_Gen_Crm_Script/CrmGen.py" \
      "D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4/tools/Gen_Pdm_Script/PDM_Gen_Crm_Script/Merge_Excel.py" \
      "D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4/tools/Gen_Pdm_Script/PDM_Gen_Crm_Script/TemplateFile.py" \
      "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Davinci/gen_pdm_code/"
cp -r "D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4/tools/Gen_Pdm_Script/PDM_Gen_Crm_Script/template" \
      "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Davinci/gen_pdm_code/"
```

- [ ] **Step 3: 验证拷贝完整 + 可编译**

```bash
ls "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Davinci/gen_nvm_arxml" \
   "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Davinci/gen_pdm_code" \
   "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Davinci/gen_pdm_code/template"
python -m py_compile \
   "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Davinci/gen_nvm_arxml/GenPdmARXML.py" \
   "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Davinci/gen_pdm_code/CrmGen.py"
```

Expected: gen_nvm_arxml 下 3 个 .py；gen_pdm_code 下 4 个 .py + template/ 下 4 个模板；py_compile 无输出（exit 0）。

---

### Task 2: 拷贝 J6 源脚本到 Nvm_AutoGen_Etas

**Files:**
- Create: `$TOOLS/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_nvm_arxml/GenPdmARXML.py`
- Create: `$TOOLS/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_pdm_code/{CrmGen.py,ExcelAnalize.py,Merge_Excel.py,TemplateFile.py,SRU_crm_RteServices.h}`
- Create: `$TOOLS/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_pdm_code/template/{SRU_crm_RteServices_T.h,pdm_cfg_BswAdapter_T.c,pdm_cfg_BswAdapter_T.h,pdm_cfg_T.h,pdm_cfg_dataitem_config_T.cpp}`

**Files:**
- 源：`$J6/cpj_cmc/pdm_cfg/rx/Pdm_Script/NvM_Develop_Gen_ARXML_Script/GenPdmARXML.py`（跳过 .bat）
- 源：`$J6/cpj_cmc/pdm_cfg/rx/Pdm_Script/PDM_Gen_Crm_Script/`（跳过 .bat；`SRU_crm_RteServices.h` 是生成输出兼后续输入，一并拷贝）
- 零改动拷贝（J6 GenPdmARXML 自带 argparse）

- [ ] **Step 1: 拷贝 gen_nvm_arxml**

```bash
mkdir -p "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_nvm_arxml"
cp "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/pdm_cfg/rx/Pdm_Script/NvM_Develop_Gen_ARXML_Script/GenPdmARXML.py" \
   "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_nvm_arxml/"
```

- [ ] **Step 2: 拷贝 gen_pdm_code（含 SRU_crm_RteServices.h 与 template/）**

```bash
mkdir -p "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_pdm_code"
cp "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/pdm_cfg/rx/Pdm_Script/PDM_Gen_Crm_Script/CrmGen.py" \
   "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/pdm_cfg/rx/Pdm_Script/PDM_Gen_Crm_Script/ExcelAnalize.py" \
   "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/pdm_cfg/rx/Pdm_Script/PDM_Gen_Crm_Script/Merge_Excel.py" \
   "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/pdm_cfg/rx/Pdm_Script/PDM_Gen_Crm_Script/TemplateFile.py" \
   "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/pdm_cfg/rx/Pdm_Script/PDM_Gen_Crm_Script/SRU_crm_RteServices.h" \
   "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_pdm_code/"
cp -r "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/pdm_cfg/rx/Pdm_Script/PDM_Gen_Crm_Script/template" \
      "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_pdm_code/"
```

- [ ] **Step 3: 验证拷贝完整 + 可编译**

```bash
ls "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_nvm_arxml" \
   "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_pdm_code" \
   "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_pdm_code/template"
python -m py_compile \
   "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_nvm_arxml/GenPdmARXML.py" \
   "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_pdm_code/CrmGen.py"
```

Expected: gen_nvm_arxml 下 1 个 .py；gen_pdm_code 下 4 个 .py + SRU_crm_RteServices.h + template/ 下 5 个模板；py_compile exit 0。

---

### Task 3: J6 CrmGen.py 参数化改造 + 产物一致性验证

**Files:**
- Modify: `$TOOLS/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_pdm_code/CrmGen.py:286-293`（仅 `__main__` 块；config area 与 CRM_Gen 不动）

改造原因：现状输出路径全部写死为脚本相对目录（`..\..\inc\pdm_cfg\...`），被 10_tools 主流程调用时必须显式传参。模板路径（`template\...`）保持相对脚本目录，不参数化。

- [ ] **Step 1: 修改 `__main__` 块**

将 `$TOOLS/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_pdm_code/CrmGen.py` 末尾的：

```python
if __name__ == '__main__':
    argc = len(sys.argv)
    if argc < 3:
        print("Error found!!!!Please input correct parameters")
    else :
        __Platform_excel_name = sys.argv[1]
        __NvM_Cfg_h_Path = sys.argv[2]
    CRM_Gen()
```

替换为：

```python
if __name__ == '__main__':
    argc = len(sys.argv)
    if argc != 9:
        print("Error found!!!!Please input correct parameters:")
        print("  <excel> <sheet> <NvM_Cfg.h> <BswAdapter.h> <BswAdapter.c>")
        print("  <dataitem_config.cpp> <SRU_crm_RteServices.h> <pdm_cfg.h>")
        sys.exit(1)
    else:
        __Platform_excel_name = sys.argv[1]
        __PDM_List_Sheet = sys.argv[2]
        __NvM_Cfg_h_Path = sys.argv[3]
        __pdmdbH_Path = sys.argv[4]
        __pdmdbC_Path = sys.argv[5]
        __ov_pdm_dataitem_config_Path = sys.argv[6]
        __pdmRte_Path = sys.argv[7]
        __pdm_cfg_Path = sys.argv[8]
    CRM_Gen()
```

说明：`__main__` 块在模块作用域，直接给模块全局赋值，`CRM_Gen()` 内引用的就是覆盖后的值（原脚本同机制）。`argc < 3` 时原脚本不退出仍执行是隐患，改造后参数错误即 exit 1。

- [ ] **Step 2: 语法检查**

```bash
python -m py_compile "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_pdm_code/CrmGen.py"
```

Expected: exit 0。

- [ ] **Step 3: 在 J6 仓库跑一次并验证产物一致**

前置：`$J6` 是 git 仓库。先确认工作区状态（若 pdm_cfg 相关文件本有未提交改动，记录下来再继续）。

```bash
cd "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6" && git status --short -- cpj_cmc/pdm_cfg
```

Expected: 无输出（干净）或仅有已知改动。

- [ ] **Step 4: 用改造后的 CrmGen 实跑（目标路径与原 bat 一致）**

```bash
cd "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_pdm_code" && python CrmGen.py \
  "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/pdm_cfg/rx/Pdm_Script/RX_NVM_List.xlsx" \
  01_NVM_List \
  "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/autosar/rx/BswRta/src/bsw/NvM/NvM_Cfg.h" \
  "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/pdm_cfg/rx/inc/pdm_cfg/pdm_cfg_BswAdapter.h" \
  "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/pdm_cfg/rx/src/pdm_cfg_BswAdapter.c" \
  "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/pdm_cfg/rx/src/pdm_cfg_dataitem_config.cpp" \
  "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Etas/gen_pdm_code/SRU_crm_RteServices.h" \
  "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/pdm_cfg/rx/inc/pdm_cfg/pdm_cfg.h"
```

Expected: 尾部打印 `Success done`。

注意：`SRU_crm_RteServices.h` 此处写到 10_tools 拷贝目录（与 J6 仓库内原位置解耦）；J6 仓库内 `Pdm_Script/PDM_Gen_Crm_Script/SRU_crm_RteServices.h` 保持不动。

- [ ] **Step 5: git diff 验证产物范围**

```bash
cd "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6" && git diff --stat -- cpj_cmc/pdm_cfg
```

Expected: 只有 4 个文件变化（BswAdapter.h / BswAdapter.c / dataitem_config.cpp / pdm_cfg.h），且每个文件内**只有时间戳行差异**（`replace_time` 替换产物）。

```bash
cd "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6" && git diff -U0 -- cpj_cmc/pdm_cfg | grep "^[+-]" | grep -v "^[+-][+-]" | grep -vi "time\|2026\|datetime" || echo "仅时间戳差异, 通过"
```

Expected: `仅时间戳差异, 通过`（或剩余行全部是时间戳样式，人工确认）。

- [ ] **Step 6: 恢复 J6 仓库工作区（生成验证用，不留在仓库改动里）**

```bash
cd "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6" && git checkout -- cpj_cmc/pdm_cfg
```

（若 Step 3 发现本有未提交改动，则只恢复本次生成的 4 个文件。）

---

### Task 4: Nvm_AutoGen_Davinci configs + 主流程

**Files:**
- Create: `$TOOLS/Nvm_AutoGen/Nvm_AutoGen_Davinci/configs/common.yaml`
- Create: `$TOOLS/Nvm_AutoGen/Nvm_AutoGen_Davinci/configs/v2xsea.yaml`
- Create: `$TOOLS/Nvm_AutoGen/Nvm_AutoGen_Davinci/Nvm_AutoGen.py`

- [ ] **Step 1: 写 configs/common.yaml**

```yaml
# nvm_autogen 功能开关 - 通用默认配置
# 三个功能: check_nvm_table / gen_nvm_arxml / gen_pdm_code
# 取值: ON / OFF
check_nvm_table: OFF   # 脚本尚未引入, 开启即报错中止, 保持 OFF
gen_nvm_arxml: ON
gen_pdm_code: ON
```

- [ ] **Step 2: 写 configs/v2xsea.yaml（当前与 common 一致，供变体级覆盖）**

```yaml
# v2xsea 变体功能开关 (深覆盖 common.yaml)
check_nvm_table: OFF
gen_nvm_arxml: ON
gen_pdm_code: ON
```

- [ ] **Step 3: 写 Nvm_AutoGen.py 主流程（完整代码）**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nvm_autogen - Vector NvM/PDM 自动生成工具 (一键流程).

流程分三个功能, 由 configs/ 下的 yaml 开关控制 (缺省 configs/common.yaml):
  check_nvm_table: 检查 NVM 表 (脚本尚未引入, 开启即报错中止)
  gen_nvm_arxml  : 1. 连接 license (USB over Network Client -> CodeMeter-Stick)
                   2. 更新 NVM arxml (gen_nvm_arxml/GenPdmARXML.py:
                      NVM_SWC_1.arxml + DataTypes.arxml)
                   3. DaVinci 自动 sync (DVCfgCmd --syncSystemDescription
                      --saveProject)
                   4. 生成 NvM 代码 (DVCfgCmd --generate
                      --modulesToGenerate /MICROSAR/NvM; --skip-gen 跳过)
                   5. 断开 license (无论中间步骤成败, 都会释放加密狗)
  gen_pdm_code   : 6. 生成 PDM 代码 (gen_pdm_code/CrmGen.py, 纯 Excel->代码,
                   无需 license; 读步骤 4 产物 microsar_cfg/<cfg>/src/GenData/
                   NvM_Cfg.h, 输出 <变体>/pdm_cfg 的 4 个文件)

用法:
  python Nvm_AutoGen.py --repo <mcu_app_tda4路径> --config v2xsea
        # 由配置名推导 variant (v2xsea -> veh_v2xsea), 按该配置的功能开关执行
  python Nvm_AutoGen.py --repo <mcu_app_tda4路径> --variant veh_v2xsea
        # 显式指定变体, 缺省 common.yaml 全流程
  加 --dry-run: 只打印推导路径与将执行的命令, 不实际运行
  加 --skip-gen: gen_nvm_arxml 中只更新 arxml, 不生成 NvM 代码

参数由 --variant 或配置名从目录结构自动推导:
  variant  = --variant, 或由配置名推导 (配置名 == 变体名或 veh_+配置名, 全仓库唯一)
  customer = 仓库根下唯一含 <variant>/microsar_cfg 的一级目录 (--customer 覆盖)
  cfg_dir  = <customer>/<variant>/microsar_cfg 的唯一子目录
  excel    = <customer>/<variant>/tools/ 下唯一 *NVM_List*.xlsx, 回退仓库
             tools/Gen_Pdm_Script/ (--excel 覆盖)
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import yaml

GEN_TOOLS = Path(__file__).resolve().parent

SHEET = "01_NVM_List"
EXCEL_GLOB = "*NVM_List*.xlsx"

GEN_NVM_SCRIPT = GEN_TOOLS / "gen_nvm_arxml" / "GenPdmARXML.py"
CRM_GEN_SCRIPT = GEN_TOOLS / "gen_pdm_code" / "CrmGen.py"

# license: USB over Network Client 连接服务器上的 WIBU CodeMeter-Stick
USBCLNCMD = Path(r"D:\Program Files\USB over Network\usbclncmd.exe")
LICENSE_SRV_ID = "0"
LICENSE_VID_PID_REV = "064f:2af9:0100"
LICENSE_SERIAL = "000005243417"

DRY = False


def resolve_repo_paths(repo: Path, customer: str, variant: str, cfg_dir: str):
    """由 --repo/--variant 推导 MCU 仓库内的所有目标路径."""
    variant_dir = repo / customer / variant
    microsar = variant_dir / "microsar_cfg" / cfg_dir
    sipaddon = microsar / "build" / "SipAddon"
    pdm_inc = variant_dir / "pdm_cfg" / "inc" / "pdm_cfg"
    pdm_src = variant_dir / "pdm_cfg" / "src"
    return SimpleNamespace(
        repo=repo,
        customer=customer,
        variant=variant,
        cfg_dir=cfg_dir,
        variant_tools=variant_dir / "tools",
        nvm_swc=(sipaddon / "Config" / "Developer" / "ComponentTypes"
                 / "NVM_SWC_1.arxml"),
        datatype=sipaddon / "Config" / "Developer" / "DataTypes.arxml",
        nvm_cfg_h=microsar / "src" / "GenData" / "NvM_Cfg.h",
        pdm_cfg_h=pdm_inc / "pdm_cfg.h",
        pdmdb_h=pdm_inc / "pdmdb.h",
        pdmdb_cpp=pdm_src / "pdmdb.cpp",
        pdm_dataitem_cpp=pdm_src / "pdm_cfg_dataitem_config.cpp",
        sipaddon=sipaddon,
        dpa=sipaddon / "Demo.dpa",
        dvcfg_cmd=(repo / "microsar_tools_tda4" / "DaVinciConfigurator"
                   / "Core" / "DVCfgCmd.exe"),
    )


def discover_customer(repo: Path, variant: str):
    """customer = 仓库根下唯一含 <variant>/microsar_cfg 的一级目录."""
    matches = sorted(p for p in repo.iterdir()
                     if p.is_dir() and (p / variant / "microsar_cfg").is_dir())
    if len(matches) != 1:
        msg = ("%s 下含 %s/microsar_cfg 的一级目录应恰为 1 个, 实际 %d 个"
               " (可用 --customer 指定)" % (repo, variant, len(matches)))
        if matches:
            msg += ": " + ", ".join(p.name for p in matches)
        raise ValueError(msg)
    return matches[0].name


def discover_variant(repo: Path, config_stem: str, customer=None):
    """--variant 缺省时由配置名推导变体: 变体目录名 == 配置名或 veh_+配置名,
    全仓库 (或指定 customer 下) 唯一匹配, 返回 (customer, variant)."""
    wanted = (config_stem, "veh_" + config_stem)
    cust_dirs = ([repo / customer] if customer
                 else sorted(p for p in repo.iterdir() if p.is_dir()))
    matches = []
    for cust in cust_dirs:
        if not cust.is_dir():
            continue
        for var in sorted(cust.iterdir()):
            if (var.is_dir() and (var / "microsar_cfg").is_dir()
                    and var.name in wanted):
                matches.append((cust.name, var.name))
    if len(matches) != 1:
        msg = ("配置名 %s 未能唯一对应变体目录 (%s 或 veh_%s), 匹配 %d 个, "
               "请显式传入 --variant"
               % (config_stem, config_stem, config_stem, len(matches)))
        if matches:
            msg += ": " + ", ".join("%s/%s" % m for m in matches)
        raise ValueError(msg)
    return matches[0]


def discover_cfg_dir(repo: Path, customer: str, variant: str):
    """cfg_dir = <customer>/<variant>/microsar_cfg 的唯一子目录."""
    microsar = repo / customer / variant / "microsar_cfg"
    cfg_dirs = (sorted(p.name for p in microsar.iterdir() if p.is_dir())
                if microsar.is_dir() else [])
    if len(cfg_dirs) != 1:
        raise ValueError(
            "%s 下应恰有 1 个配置子目录 (cfg_dir), 实际 %d 个: %s"
            % (microsar, len(cfg_dirs), ", ".join(cfg_dirs)))
    return cfg_dirs[0]


def discover_excel(paths, excel_arg):
    """--excel 优先; 否则先在变体 tools/ 下找唯一 *NVM_List*.xlsx,
    回退仓库 tools/Gen_Pdm_Script/."""
    if excel_arg:
        excel = Path(excel_arg).resolve()
        if not excel.is_file():
            raise ValueError("Excel 不存在: %s" % excel)
        return excel
    searched = []
    for base in (paths.variant_tools, paths.repo / "tools" / "Gen_Pdm_Script"):
        searched.append(base)
        hits = sorted(base.glob(EXCEL_GLOB)) if base.is_dir() else []
        if len(hits) > 1:
            raise ValueError(
                "%s 下 %s 匹配 %d 个, 请 --excel 指定: %s"
                % (base, EXCEL_GLOB, len(hits), [p.name for p in hits]))
        if len(hits) == 1:
            return hits[0]
    raise ValueError(
        "未找到 %s (搜索: %s), 请 --excel 指定"
        % (EXCEL_GLOB, ", ".join(str(s) for s in searched)))


FEATURES = ("check_nvm_table", "gen_nvm_arxml", "gen_pdm_code")


def load_config(config_arg):
    """加载功能开关配置 (yaml), 返回 (配置文件路径, {feature: bool})."""
    if config_arg:
        candidates = [Path(config_arg), Path(config_arg + ".yaml"),
                      GEN_TOOLS / "configs" / config_arg,
                      GEN_TOOLS / "configs" / (config_arg + ".yaml")]
        path = next((p for p in candidates if p.is_file()), None)
        if path is None:
            path = GEN_TOOLS / "configs" / "common.yaml"
            available = ", ".join(
                p.stem for p in sorted((GEN_TOOLS / "configs").glob("*.yaml"))
            ) if (GEN_TOOLS / "configs").is_dir() else "无"
            print("[nvm_autogen] 未找到配置 %s, 回退 common.yaml "
                  "(configs/ 下可用: %s)" % (config_arg, available))
    else:
        path = GEN_TOOLS / "configs" / "common.yaml"
    if not path.is_file():
        raise ValueError("未找到默认配置 %s" % path)

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    unknown = sorted(set(data) - set(FEATURES))
    if unknown:
        raise ValueError("%s 含未知功能项: %s (可用: %s)"
                         % (path, ", ".join(unknown), ", ".join(FEATURES)))
    missing = sorted(set(FEATURES) - set(data))
    if missing:
        raise ValueError("%s 缺少功能项: %s" % (path, ", ".join(missing)))

    cfg = {}
    for key in FEATURES:
        val = data[key]
        if isinstance(val, bool):
            cfg[key] = val
        elif isinstance(val, str) and val.upper() in ("ON", "OFF"):
            cfg[key] = val.upper() == "ON"
        else:
            raise ValueError("%s 中 %s 的值应为 ON 或 OFF" % (path, key))
    return path, cfg


def run_step(title, cmd, cwd, tail_on_fail=25, check=True):
    print("[nvm_autogen] ==> %s" % title)
    if DRY:
        print("[nvm_autogen]     [dry-run] %s"
              % " ".join(str(c) for c in cmd))
        return None
    t0 = time.time()
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    dt = time.time() - t0
    if check and proc.returncode != 0:
        print(proc.stdout[-3000:] if proc.stdout else "")
        print(proc.stderr[-3000:] if proc.stderr else "")
        print("[nvm_autogen] FAILED (exit %d, %.0fs): %s"
              % (proc.returncode, dt, title))
        sys.exit(1)
    print("[nvm_autogen]     OK (%.0fs)" % dt)
    return proc


def davinci_sync(step_title, paths):
    """sync + save. 中间态可能有 reference 校验错误, 属预期, 不作为失败依据.

    判定失败: sync 未完成 / 工程被 UI 锁定 / save 未完成.
    注意: 结果信息只写进 DVCfgCmd.log (每次运行覆盖), stdout 不含关键行.
    """
    run_step(
        step_title + " (DaVinci sync)",
        [str(paths.dvcfg_cmd), "--project", str(paths.dpa),
         "--syncSystemDescription", "--saveProject", "--validate"],
        cwd=paths.sipaddon, check=False,
    )
    if DRY:
        return
    log = (paths.sipaddon / "DVCfgCmd.log").read_text(encoding="utf-8", errors="replace")
    if "could not be saved" in log:
        print("[nvm_autogen] ERROR: 工程被锁定, 请关闭 DaVinci Configurator UI 后重试")
        sys.exit(1)
    if "Action 'Synchronizing System Description...' successfully finished" not in log:
        print("[nvm_autogen] ERROR: System Description 同步未完成, 详见 %s"
              % (paths.sipaddon / "DVCfgCmd.log"))
        sys.exit(1)
    if "Project saved" not in log:
        print("[nvm_autogen] ERROR: 工程保存失败, 详见 %s"
              % (paths.sipaddon / "DVCfgCmd.log"))
        sys.exit(1)
    import re
    m = re.search(r"(Validation and Generation result summary:\s*[\r\n]+.*)", log)
    if m:
        print("[nvm_autogen]     %s" % " ".join(m.group(1).split()))


def license_connect(repo):
    run_step(
        "连接 license (CodeMeter-Stick %s)" % LICENSE_SERIAL,
        [str(USBCLNCMD), "connect", LICENSE_SRV_ID,
         "-a", LICENSE_VID_PID_REV, "-s", LICENSE_SERIAL],
        cwd=repo,
    )


def license_disconnect(repo):
    run_step(
        "断开 license",
        [str(USBCLNCMD), "disconnect", LICENSE_SRV_ID,
         "-a", LICENSE_VID_PID_REV, "-s", LICENSE_SERIAL],
        cwd=repo,
    )


def main():
    parser = argparse.ArgumentParser(description="Vector NvM/PDM auto generation tool")
    parser.add_argument("--repo", required=True,
                        help="mcu_app_tda4 仓库根目录 (绝对或相对路径)")
    parser.add_argument("--variant",
                        help="车型变体目录名 (如 veh_v2xsea; 缺省由配置名推导)")
    parser.add_argument("--customer",
                        help="客户一级目录名 (缺省自动发现唯一含 "
                             "<variant>/microsar_cfg 的目录)")
    parser.add_argument("--excel",
                        help="NVM 表 xlsx 路径 (缺省自动发现唯一的 %s)" % EXCEL_GLOB)
    parser.add_argument("--sheet",
                        help="Excel sheet 名 (缺省 %s)" % SHEET)
    parser.add_argument("--config",
                        help="功能开关配置 (configs/ 下的配置名或 yaml 路径, "
                             "缺省 common.yaml; 未找到时回退 common.yaml)")
    parser.add_argument("--skip-gen", action="store_true",
                        help="只更新 arxml, 不执行 NvM 代码生成")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印推导路径与将执行的命令, 不实际运行")
    args = parser.parse_args()
    global DRY
    DRY = args.dry_run

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print("[nvm_autogen] ERROR: 路径不存在或不是目录: %s" % repo)
        sys.exit(1)
    try:
        cfg_path, cfg = load_config(args.config)
        if args.variant:
            customer = args.customer or discover_customer(repo, args.variant)
            variant = args.variant
        else:
            stem = Path(args.config).stem if args.config else cfg_path.stem
            customer, variant = discover_variant(repo, stem, args.customer)
        cfg_dir = discover_cfg_dir(repo, customer, variant)
        paths = resolve_repo_paths(repo, customer, variant, cfg_dir)
        excel = discover_excel(paths, args.excel)
    except ValueError as e:
        print("[nvm_autogen] ERROR: %s" % e)
        sys.exit(1)
    sheet = args.sheet or SHEET

    needed = []
    if any(cfg[k] for k in FEATURES):
        needed.append(excel)
    if cfg["gen_nvm_arxml"]:
        needed += [paths.nvm_swc, paths.datatype, paths.dpa, paths.dvcfg_cmd,
                   USBCLNCMD, GEN_NVM_SCRIPT]
    if cfg["gen_pdm_code"]:
        needed += [CRM_GEN_SCRIPT, CRM_GEN_SCRIPT.parent / "template"]
        if not DRY and not paths.nvm_cfg_h.is_file():
            print("[nvm_autogen] ERROR: NvM_Cfg.h 不存在: %s\n"
                  "  gen_nvm_arxml 为 OFF 且仓库无历史产物, 请先开启 gen_nvm_arxml"
                  % paths.nvm_cfg_h)
            sys.exit(1)
    for f in needed:
        if not f.is_file():
            print("[nvm_autogen] ERROR: 文件不存在: %s" % f)
            sys.exit(1)

    print("[nvm_autogen] 变体      : %s/%s (cfg %s)"
          % (customer, variant, cfg_dir))
    print("[nvm_autogen] 配置      : %s" % cfg_path.name)
    print("[nvm_autogen] 功能开关  : %s" % ", ".join(
        "%s=%s" % (k, "ON" if cfg[k] else "OFF") for k in FEATURES))
    print("[nvm_autogen] NVM 表    : %s" % excel)
    print("[nvm_autogen] Sheet     : %s" % sheet)
    print("[nvm_autogen] MCU 仓库  : %s" % repo)
    print("[nvm_autogen] 目标 arxml: %s" % paths.nvm_swc)
    print("[nvm_autogen] DaVinci   : %s" % paths.dpa)
    if DRY:
        print("[nvm_autogen] *** DRY-RUN 模式, 只打印命令不执行 ***")

    # 功能 1: 检查 NVM 表 (脚本尚未引入)
    if cfg["check_nvm_table"]:
        print("[nvm_autogen] ERROR: check_nvm_table 脚本尚未引入, "
              "请将配置改为 OFF")
        sys.exit(1)

    # 功能 2: 更新 NVM arxml + NvM 代码生成 (license 全程持有)
    if cfg["gen_nvm_arxml"]:
        license_connect(repo)
        try:
            t0 = time.time()
            run_step("更新 NVM arxml (NVM_SWC_1 + DataTypes)",
                     [sys.executable, str(GEN_NVM_SCRIPT), str(excel), sheet,
                      str(paths.nvm_swc), str(paths.datatype)],
                     cwd=GEN_NVM_SCRIPT.parent)
            # 子脚本静默失败兜底: arxml 应被重写且仍含 RAM-BLOCK 容器
            if not DRY:
                if paths.nvm_swc.stat().st_mtime < t0 - 1:
                    print("[nvm_autogen] ERROR: 脚本声称成功但 arxml 未被重写: %s"
                          % paths.nvm_swc)
                    sys.exit(1)
                text = paths.nvm_swc.read_text(
                    encoding="utf-8", errors="replace")
                if "<RAM-BLOCK " not in text:
                    print("[nvm_autogen] ERROR: arxml 缺少 RAM-BLOCK 容器 "
                          "(子脚本静默失败?): %s" % paths.nvm_swc)
                    sys.exit(1)

            davinci_sync("同步 System Description", paths)

            if args.skip_gen:
                print("[nvm_autogen] --skip-gen: 跳过 NvM 代码生成")
            else:
                run_step("生成 NvM 代码",
                         [str(paths.dvcfg_cmd), "--project", str(paths.dpa),
                          "--generate", "--modulesToGenerate", "/MICROSAR/NvM"],
                         cwd=paths.sipaddon)
        finally:
            license_disconnect(repo)
    else:
        print("[nvm_autogen] 配置 OFF: 跳过 gen_nvm_arxml (不占用 license)")

    # 功能 3: 生成 PDM 代码 (纯 Excel -> 代码, 无需 license; cwd 用临时目录,
    #        使 CrmGen 产生的中间文件 Excel_To_Csv/ 随临时目录清除)
    if cfg["gen_pdm_code"]:
        pdm_tmp = Path(tempfile.mkdtemp(prefix="nvm_crm_"))
        try:
            run_step("生成 PDM 代码 (pdm_cfg.h/pdmdb.h/pdmdb.cpp/dataitem_config.cpp)",
                     [sys.executable, str(CRM_GEN_SCRIPT), str(excel), sheet,
                      str(paths.nvm_cfg_h), str(paths.pdm_cfg_h),
                      str(paths.pdmdb_h), str(paths.pdmdb_cpp),
                      str(paths.pdm_dataitem_cpp),
                      str(CRM_GEN_SCRIPT.parent / "template")],
                     cwd=pdm_tmp)
        finally:
            shutil.rmtree(pdm_tmp, ignore_errors=True)
    else:
        print("[nvm_autogen] 配置 OFF: 跳过 gen_pdm_code")

    print("[nvm_autogen] 全部完成")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 语法检查**

```bash
python -m py_compile "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Davinci/Nvm_AutoGen.py"
```

Expected: exit 0。

- [ ] **Step 5: dry-run 验证路径推导**

前置：TDA4 仓库目前没有 `*NVM_List*.xlsx`（`CHERY_V2xSEA_NVM_List.xlsx` 不在仓库中），需 `--excel` 指定本地表路径（若用户手头没有，用任意 xlsx 路径验证报错信息亦可，但完整 dry-run 需要真实文件）。

```bash
python "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Davinci/Nvm_AutoGen.py" \
  --repo "D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4" \
  --config v2xsea --dry-run --excel <NVM_List.xlsx 路径>
```

Expected: 打印 `变体: cpj_chery/veh_v2xsea (cfg d300e)`、功能开关、目标 arxml 路径（`.../NVM_SWC_1.arxml`），随后各步骤均为 `[dry-run] python ...` 命令行，无任何实际执行、不连 license。

再验证无 --excel 时的报错：

```bash
python "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Davinci/Nvm_AutoGen.py" \
  --repo "D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4" \
  --config v2xsea --dry-run
```

Expected: `ERROR: 未找到 *NVM_List*.xlsx (搜索: ...) 请 --excel 指定`。

---

### Task 5: Nvm_AutoGen_Etas configs + 主流程

**Files:**
- Create: `$TOOLS/Nvm_AutoGen/Nvm_AutoGen_Etas/configs/common.yaml`
- Create: `$TOOLS/Nvm_AutoGen/Nvm_AutoGen_Etas/configs/rx.yaml`
- Create: `$TOOLS/Nvm_AutoGen/Nvm_AutoGen_Etas/nvm_autogen_etas.py`

- [ ] **Step 1: 写 configs/common.yaml（ETAS 风格布尔值，对齐 Dem_Etas）**

```yaml
# nvm_autogen_etas 功能开关 - 通用默认配置
# 三个功能: check_nvm_table / gen_nvm_arxml / gen_pdm_code
check_nvm_table: false   # 脚本尚未引入, 开启即报错中止
gen_nvm_arxml: true
gen_pdm_code: true
```

- [ ] **Step 2: 写 configs/rx.yaml（当前与 common 一致，供变体级覆盖）**

```yaml
# rx 变体功能开关 (深合并覆盖 common.yaml)
check_nvm_table: false
gen_nvm_arxml: true
gen_pdm_code: true
```

- [ ] **Step 3: 写 nvm_autogen_etas.py 主流程（完整代码）**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nvm_autogen_etas - ETAS NvM/PDM 自动生成工具 (一键流程).

流程 (按 configs/*.yaml 深合并配置启停):
  check_nvm_table  校验 NVM 表            (脚本尚未引入, 开启即报错)
  gen_nvm_arxml    更新 J6B_NvM_EcucValues.arxml (gen_nvm_arxml/GenPdmARXML.py
                   原地更新) + 紧接 BSW 代码生成 (ISOLAR headless, 失败降级 Cobra)
  gen_pdm_code     生成 PDM 代码 (gen_pdm_code/CrmGen.py, 纯 Excel->代码,
                   读 BswRta/src/bsw/NvM/NvM_Cfg.h, 输出 cpj_*/pdm_cfg/<变体>
                   的 4 个文件 + 脚本目录 SRU_crm_RteServices.h)

用法:
  python nvm_autogen_etas.py --repo <mcu_app_j6路径> --config rx [--excel <表>] [--dry-run]
"""

import argparse
import os
import re
import subprocess
import sys
import time
import yaml
from pathlib import Path
from types import SimpleNamespace

GEN_TOOLS = Path(__file__).resolve().parent

GEN_NVM_SCRIPT = GEN_TOOLS / "gen_nvm_arxml" / "GenPdmARXML.py"
CRM_GEN_SCRIPT = GEN_TOOLS / "gen_pdm_code" / "CrmGen.py"
CONFIGS_DIR = GEN_TOOLS / "configs"

SHEET = "01_NVM_List"
EXCEL_GLOB = "*_NVM_List*.xlsx"

FEATURES = ("check_nvm_table", "gen_nvm_arxml", "gen_pdm_code")

RTA_CAR_HOME_DEFAULT = Path(r"D:/ETAS/RTA-CAR_12.7.0")
BSW_TIMEOUT_S = 3600   # 全量 BSW 生成上限 60 分钟
BSW_POLL_S = 15
ERRORS_RE = re.compile(r"Errors:\s*(\d+)\s*,\s*Warnings:\s*(\d+)")
LICENSE_FAIL_RE = re.compile(
    r"Please set COBRA_LIC_PATH|No valid license", re.IGNORECASE)
OUTPUT_FAIL_RE = re.compile(r"\[ERROR\]|^\s*Error:|Execution failed", re.IGNORECASE)

# arxml 内容兜底锚点: NvMBlockDescriptor 参数容器 (静默失败 = 锚点缺失)
ARXML_ANCHOR = ("NvM/EcucModuleDefs/NvM/NvMBlockDescriptor/"
                "NvMBlockManagementType</DEFINITION-REF>")

DRY = False


def fail(msg):
    print("[nvm_autogen_etas] ERROR: %s" % msg)
    sys.exit(1)


def deep_merge(base: dict, override: dict) -> dict:
    """dict 递归合并, 标量直接覆盖 (override 优先)."""
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_feature_config(project: str):
    """读 configs/common.yaml + configs/<project>.yaml 深合并, 返回 (cfg, 来源名)."""
    common_path = CONFIGS_DIR / "common.yaml"
    if not common_path.is_file():
        fail("缺少 %s" % common_path)
    try:
        cfg = yaml.safe_load(common_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        fail("YAML 解析失败 %s: %s" % (common_path, e))
    if not isinstance(cfg, dict) or any(k not in cfg for k in FEATURES):
        fail("%s 必须包含全部功能键: %s" % (common_path, ", ".join(FEATURES)))
    source = "common"
    proj_path = CONFIGS_DIR / ("%s.yaml" % project)
    if proj_path.is_file():
        try:
            override = yaml.safe_load(proj_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            fail("YAML 解析失败 %s: %s" % (proj_path, e))
        if not isinstance(override, dict):
            fail("%s 内容必须是映射" % proj_path)
        cfg = deep_merge(cfg, override)
        source = project
    unknown = [k for k in cfg if k not in FEATURES]
    if unknown:
        fail("配置含未知键: %s (允许: %s)"
             % (", ".join(sorted(map(str, unknown))), ", ".join(FEATURES)))
    for k in FEATURES:
        if not isinstance(cfg[k], bool):
            fail("%s 必须是布尔" % k)
    return cfg, source


def resolve_repo_paths(repo: Path, project: str):
    """由 --repo + --config 推导所有目标路径 (glob, 无硬编码)."""
    hits = sorted(repo.glob("cpj_*/autosar/%s/BswRta" % project))
    if len(hits) != 1:
        fail("cpj_*/autosar/%s/BswRta 匹配 %d 个 (需恰好 1): %s"
             % (project, len(hits), [str(h) for h in hits]))
    bswrta = hits[0].resolve()
    arxml_hits = [p for p in sorted(bswrta.glob("ecu_config/bsw/gen/*NvM_EcucValues.arxml"))
                  if not p.name.startswith("RTA_BIP_")]
    if len(arxml_hits) != 1:
        fail("ecu_config/bsw/gen/*NvM_EcucValues.arxml (排除 RTA_BIP_) 匹配 %d 个 (需恰好 1)"
             % len(arxml_hits))
    cpj = bswrta.parent.parent.parent  # cpj_x/autosar/<proj>/BswRta -> cpj_x
    pdm_inc = cpj / "pdm_cfg" / project / "inc" / "pdm_cfg"
    pdm_src = cpj / "pdm_cfg" / project / "src"
    return SimpleNamespace(
        repo=repo,
        bswrta=bswrta,
        arxml=arxml_hits[0],
        nvm_cfg_h=bswrta / "src" / "bsw" / "NvM" / "NvM_Cfg.h",
        bsw_adapter_h=pdm_inc / "pdm_cfg_BswAdapter.h",
        bsw_adapter_c=pdm_src / "pdm_cfg_BswAdapter.c",
        dataitem_cpp=pdm_src / "pdm_cfg_dataitem_config.cpp",
        pdm_cfg_h=pdm_inc / "pdm_cfg.h",
        rte_h=CRM_GEN_SCRIPT.parent / "SRU_crm_RteServices.h",
        cobra=bswrta / "ecu_config" / "cobra" / "Cobra.exe",
        confgen_log=bswrta / "_log" / "BSW_ConfGen_ECUGeneration.txt",
        bsw_log=bswrta / "_log" / "rta-bsw.log",
    )


def discover_excel(repo: Path, project: str, excel_arg):
    """定位输入 Excel: --excel 指定优先, 否则在 cpj_*/pdm_cfg/<变体>/Pdm_Script/
    下自动发现唯一 *_NVM_List*.xlsx (排除 *_merged.xlsx 中间产物)."""
    if excel_arg:
        p = Path(excel_arg).resolve()
        if not p.is_file():
            fail("Excel 不存在: %s" % p)
        return p
    hits = [p for p in sorted(repo.glob("cpj_*/pdm_cfg/%s/Pdm_Script/%s" % (project, EXCEL_GLOB)))
            if not p.name.endswith("_merged.xlsx")]
    if len(hits) != 1:
        fail("cpj_*/pdm_cfg/%s/Pdm_Script/ 下 %s (排除 _merged) 匹配 %d 个 (需恰好 1): %s%s"
             % (project, EXCEL_GLOB, len(hits), [str(h) for h in hits],
                "" if hits else " (该变体目录不存在或无 Excel, 可用 --excel 手动指定)"))
    return hits[0].resolve()


def _has_isolar_launcher(d: Path) -> bool:
    """ISOLAR-AB.cmd 为当前启动器; 旧名 ISOLAR-B.cmd 已 deprecated, 仅兜底."""
    return (d / "ISOLAR-AB.cmd").is_file() or (d / "ISOLAR-B.cmd").is_file()


def find_isolar_b(root: Path):
    """在 RTA-CAR 安装目录下找 ISOLAR 启动器所在目录 (移植 bsw_gen.ps1 Find-IsolarB)."""
    if not root.is_dir():
        return None
    if _has_isolar_launcher(root):
        return root
    cands = sorted((d for d in root.iterdir() if d.is_dir()
                    and (re.match(r"^ISOLAR-AB_\d", d.name) or re.match(r"^RTA-OS_", d.name))),
                   key=lambda d: d.name, reverse=True)
    for c in cands:
        if _has_isolar_launcher(c):
            return c
        for s in sorted((d for d in c.iterdir() if d.is_dir()
                        and re.match(r"^ISOLAR-AB_\d", d.name)),
                        key=lambda d: d.name, reverse=True):
            if _has_isolar_launcher(s):
                return s
    for depth in (1, 2, 3):
        hits = [p.parent for p in root.glob("*/" * depth + "ISOLAR-AB.cmd")]
        hits += [p.parent for p in root.glob("*/" * depth + "ISOLAR-B.cmd")]
        if hits:
            return sorted(hits, reverse=True)[0]
    return None


def isolar_cmd_path(isolar_dir: Path) -> Path:
    """优先 ISOLAR-AB.cmd (ISOLAR-B.cmd 已 deprecated)."""
    ab = isolar_dir / "ISOLAR-AB.cmd"
    return ab if ab.is_file() else isolar_dir / "ISOLAR-B.cmd"


def run_step(title, cmd, cwd):
    """跑一个子步骤, 失败打印输出尾部并 exit 1."""
    print("[nvm_autogen_etas] ==> %s" % title)
    if DRY:
        print("[nvm_autogen_etas]     [dry-run] %s"
              % " ".join(str(c) for c in cmd))
        return
    t0 = time.time()
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if proc.returncode != 0:
        print(proc.stdout[-3000:] if proc.stdout else "")
        print(proc.stderr[-3000:] if proc.stderr else "")
        print("[nvm_autogen_etas] FAILED (exit %d, %.0fs): %s"
              % (proc.returncode, time.time() - t0, title))
        sys.exit(1)
    print("[nvm_autogen_etas]     OK (%.0fs)" % (time.time() - t0))


def parse_confgen_errors(log_path: Path):
    """解析 BSW_ConfGen_ECUGeneration.txt 里的 'Errors: N, Warnings: M' (取最后一次出现)."""
    if not log_path.is_file():
        return None
    last = None
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = ERRORS_RE.search(line)
        if m:
            last = (int(m.group(1)), int(m.group(2)))
    return last


def confgen_log_fresh(log_path: Path, t0: float):
    """本次运行是否重写了 ConfGen 日志 (防静默失败误判为成功)."""
    return log_path.is_file() and log_path.stat().st_mtime >= t0


def output_has_failure_marker(lines) -> bool:
    """扫描工具输出行, 是否含显式失败标记."""
    return any(OUTPUT_FAIL_RE.search(l) for l in lines)


def gen_bsw_headless(paths, isolar_cmd: Path):
    """ISOLAR-B headless: -generate -p=<BswRta> -t=BSW. 等进程自然退出, 超时杀进程树."""
    print("[nvm_autogen_etas] ==> 生成 BSW 代码 (ISOLAR headless, 属 gen_nvm_arxml)")
    t0 = time.time()
    out_path = paths.bswrta / "_log" / "nvm_autogen_etas.headless.out"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(isolar_cmd), "-generate", "-p=%s" % paths.bswrta, "-t=BSW"]
    with open(out_path, "w", encoding="utf-8", errors="replace") as out:
        proc = subprocess.Popen(cmd, cwd=str(isolar_cmd.parent),
                                 stdout=out, stderr=subprocess.STDOUT)
        deadline = time.time() + BSW_TIMEOUT_S
        last_beat = time.time()
        while proc.poll() is None and time.time() < deadline:
            time.sleep(BSW_POLL_S)
            if time.time() - last_beat >= 60:
                print("[nvm_autogen_etas]     ... 仍在运行 (%.0fs)"
                      % (time.time() - t0))
                last_beat = time.time()
        if proc.poll() is None:
            print("[nvm_autogen_etas]     超过 %ds 未完成, 终止 ISOLAR 进程树" % BSW_TIMEOUT_S)
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True)
            try:
                proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                pass
            return False
    time.sleep(10)
    out_lines = out_path.read_text(
        encoding="utf-8", errors="replace").splitlines()
    failed_marker = output_has_failure_marker(out_lines)
    bsw_fresh = confgen_log_fresh(paths.bsw_log, t0)
    print("[nvm_autogen_etas]     ISOLAR exit code: %s, rta-bsw.log fresh: %s (%.0fs)"
          % (proc.returncode, bsw_fresh, time.time() - t0))
    if failed_marker:
        for line in out_lines:
            if OUTPUT_FAIL_RE.search(line):
                print("    %s" % line)
        return False
    return proc.returncode == 0 and bsw_fresh


def gen_bsw_cobra(paths, isolar_dir: Path):
    """Cobra.exe 降级: 与 ISOLAR GUI 'Generate BSW Code' 1:1 (ConfGen+BSWGen+hooks)."""
    print("[nvm_autogen_etas] ==> 生成 BSW 代码 (Cobra.exe 降级, 属 gen_nvm_arxml)")
    if not paths.cobra.is_file():
        print("[nvm_autogen_etas]     ERROR: Cobra.exe 不存在: %s" % paths.cobra)
        return False
    t0 = time.time()
    cmd = [str(paths.cobra), "--ProjectPath=.",
           "--isolarPath=%s" % isolar_dir, "--isolarARRoot=RTA_BIP"]
    try:
        proc = subprocess.run(cmd, cwd=str(paths.bswrta), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=BSW_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        print("[nvm_autogen_etas]     ERROR: Cobra 超过 %ds 未完成" % BSW_TIMEOUT_S)
        return False
    lines = [l for l in (proc.stdout or "").splitlines()
             + (proc.stderr or "").splitlines() if l.strip()]
    for line in lines[-12:]:
        print("    %s" % line)
    if any(LICENSE_FAIL_RE.search(l) for l in lines):
        print("[nvm_autogen_etas]     ERROR: Cobra license 检查失败")
        return False
    if 0 < len(lines) < 30:
        print("[nvm_autogen_etas]     ERROR: Cobra 输出仅 %d 行, 疑似静默失败" % len(lines))
        return False
    errs = parse_confgen_errors(paths.confgen_log)
    print("[nvm_autogen_etas]     Cobra exit code: %s, ConfGen: %s (%.0fs)"
          % (proc.returncode, errs, time.time() - t0))
    if output_has_failure_marker(lines):
        for line in lines:
            if OUTPUT_FAIL_RE.search(line):
                print("    %s" % line)
        return False
    return (proc.returncode == 0
            and confgen_log_fresh(paths.confgen_log, t0)
            and (errs is None or errs[0] == 0))


def main():
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="ETAS NvM/PDM auto generation tool")
    parser.add_argument("--repo", required=True, help="mcu_app_j6 仓库根目录")
    parser.add_argument("--config", required=True,
                        help="变体名 (如 rx, 对应 configs/<变体名>.yaml 与 cpj_*/pdm_cfg/<变体>/)")
    parser.add_argument("--excel", default=None,
                        help="*_NVM_List.xlsx 路径 (缺省自动发现; 变体目录下有多个表时必须指定)")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印推导路径与将执行的命令, 不实际运行")
    args = parser.parse_args()
    global DRY
    DRY = args.dry_run

    repo = Path(args.repo).resolve()

    cfg, cfg_source = load_feature_config(args.config)

    needed_scripts = {
        "gen_nvm_arxml": GEN_NVM_SCRIPT,
        "gen_pdm_code": CRM_GEN_SCRIPT,
    }
    for feat, script in needed_scripts.items():
        if cfg[feat] and not script.is_file():
            fail("脚本不存在: %s" % script)

    paths = resolve_repo_paths(repo, args.config)
    excel = discover_excel(repo, args.config, args.excel)

    print("[nvm_autogen_etas] Excel     : %s" % excel)
    print("[nvm_autogen_etas] MCU 仓库  : %s" % repo)
    print("[nvm_autogen_etas] 车型      : %s" % args.config)
    print("[nvm_autogen_etas] BswRta    : %s" % paths.bswrta)
    print("[nvm_autogen_etas] 目标 arxml: %s" % paths.arxml)
    print("[nvm_autogen_etas] 配置      : %s (%s)" % (CONFIGS_DIR, cfg_source))
    print("[nvm_autogen_etas] 启用功能  : %s"
          % " -> ".join(k for k in FEATURES if cfg[k]))
    if DRY:
        print("[nvm_autogen_etas] *** DRY-RUN 模式, 只打印命令不执行 ***")

    if cfg["check_nvm_table"]:
        fail("check_nvm_table 脚本尚未引入")

    if cfg["gen_nvm_arxml"]:
        t0 = time.time()
        run_step("更新 NvM arxml (原地)",
                 [sys.executable, str(GEN_NVM_SCRIPT), "-i", str(paths.arxml),
                  "-e", str(excel), "-o", str(paths.arxml)],
                 cwd=GEN_NVM_SCRIPT.parent)
        # 子脚本静默失败兜底: arxml 应被重写且仍含 NvMBlockDescriptor 容器
        if not DRY:
            if paths.arxml.stat().st_mtime < t0 - 1:
                fail("gen_nvm_arxml 声称成功但 arxml 未被重写: %s (子脚本静默失败?)"
                     % paths.arxml)
            text = paths.arxml.read_text(encoding="utf-8", errors="replace")
            if ARXML_ANCHOR not in text:
                fail("gen_nvm_arxml 后 arxml 缺少 NvMBlockDescriptor 容器 "
                     "(子脚本静默失败?): %s" % paths.arxml)

        rta_home = Path(os.environ.get("RTA_CAR_HOME", str(RTA_CAR_HOME_DEFAULT)))
        isolar_dir = find_isolar_b(rta_home)
        if isolar_dir is None:
            fail("ISOLAR-AB.cmd 未找到 (RTA_CAR_HOME=%s)" % rta_home)
        isolar_cmd = isolar_cmd_path(isolar_dir)
        print("[nvm_autogen_etas] ISOLAR    : %s" % isolar_cmd)
        if DRY:
            print("[nvm_autogen_etas]     [dry-run] %s -generate -p=%s -t=BSW"
                  % (isolar_cmd, paths.bswrta))
            print("[nvm_autogen_etas]     [dry-run] 失败时降级: %s --ProjectPath=. "
                  "--isolarPath=%s --isolarARRoot=RTA_BIP" % (paths.cobra, isolar_dir))
        else:
            ok = gen_bsw_headless(paths, isolar_cmd)
            if not ok:
                print("[nvm_autogen_etas] headless 失败, 降级 Cobra.exe ...")
                ok = gen_bsw_cobra(paths, isolar_dir)
            if not ok:
                fail("BSW 生成失败, 详见 %s 及 %s 目录下日志"
                     % (paths.confgen_log, paths.bswrta / "_log"))

    if cfg["gen_pdm_code"]:
        if not DRY and not paths.nvm_cfg_h.is_file():
            fail("NvM_Cfg.h 不存在: %s\n  gen_nvm_arxml 为 OFF 且仓库无历史产物, "
                 "请先开启 gen_nvm_arxml 生成" % paths.nvm_cfg_h)
        run_step("生成 PDM 代码 (BswAdapter.h/.c + dataitem_config.cpp + pdm_cfg.h + RteServices.h)",
                 [sys.executable, str(CRM_GEN_SCRIPT), str(excel), SHEET,
                  str(paths.nvm_cfg_h), str(paths.bsw_adapter_h),
                  str(paths.bsw_adapter_c), str(paths.dataitem_cpp),
                  str(paths.rte_h), str(paths.pdm_cfg_h)],
                 cwd=CRM_GEN_SCRIPT.parent)

    print("[nvm_autogen_etas] 全部完成")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 语法检查**

```bash
python -m py_compile "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Etas/nvm_autogen_etas.py"
```

Expected: exit 0。

- [ ] **Step 5: dry-run 验证（J6 有真实 Excel，可完整验证）**

```bash
python "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen_Etas/nvm_autogen_etas.py" \
  --repo "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6" \
  --config rx --dry-run
```

Expected:
- Excel: `.../cpj_cmc/pdm_cfg/rx/Pdm_Script/RX_NVM_List.xlsx`
- 目标 arxml: `.../cpj_cmc/autosar/rx/BswRta/ecu_config/bsw/gen/J6B_NvM_EcucValues.arxml`
- 启用功能: `gen_nvm_arxml -> gen_pdm_code`
- 各步骤打印 `[dry-run]` 命令（含 ISOLAR/Cobra 降级命令），无实际执行

---

### Task 6: 顶层统一入口 Nvm_AutoGen/Nvm_AutoGen.py

**Files:**
- Create: `$TOOLS/Nvm_AutoGen/Nvm_AutoGen.py`

- [ ] **Step 1: 写统一入口（完整代码）**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nvm_AutoGen - Vector(TDA4)/ETAS(J6) NvM/PDM 生成统一入口.

按 MCU 仓库目录结构自动判型, 参数转发给对应子工具执行:
  ETAS (mcu_app_j6)    : 仓库下存在 cpj_*/autosar/<config>/BswRta
                         -> Nvm_AutoGen_Etas/nvm_autogen_etas.py
  Vector (mcu_app_tda4): 仓库下存在 */(<config>|veh_<config>)/microsar_cfg
                         -> Nvm_AutoGen_Davinci/Nvm_AutoGen.py

子工具的其余参数 (--excel/--variant/--customer/--sheet/--skip-gen 等)
原样转发; 两个子工具自身的功能开关仍由各自 configs/ 下的 yaml 控制.

用法:
  python Nvm_AutoGen.py --repo <mcu仓库路径> --config <配置名> [子工具参数...]
  加 --dry-run: 只打印将执行的命令, 不实际运行
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

TOOL_ROOT = Path(__file__).resolve().parent

DAVINCI_MAIN = TOOL_ROOT / "Nvm_AutoGen_Davinci" / "Nvm_AutoGen.py"
ETAS_MAIN = TOOL_ROOT / "Nvm_AutoGen_Etas" / "nvm_autogen_etas.py"


def fail(msg):
    print("[Nvm_AutoGen] ERROR: %s" % msg)
    sys.exit(1)


def extra_value(extra, flag):
    """从转发的参数表取 flag 的值 (--flag value 或 --flag=value), 无则 None."""
    for i, a in enumerate(extra):
        if a == flag and i + 1 < len(extra):
            return extra[i + 1]
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return None


def davinci_microsar_hits(repo: Path, config: str, extra):
    """Davinci 变体定位: */(<variant>)/microsar_cfg, --variant/--customer 收窄."""
    variant = extra_value(extra, "--variant")
    customer = extra_value(extra, "--customer")
    cust_pat = customer if customer else "*"
    var_names = (variant,) if variant else (config, "veh_" + config)
    hits = []
    for v in var_names:
        hits += sorted(repo.glob("%s/%s/microsar_cfg" % (cust_pat, v)))
    return hits


def main():
    # 重定向到日志文件时保持行缓冲, 使本脚本与子进程输出顺序一致
    sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(
        description="Vector(TDA4)/ETAS(J6) NvM/PDM 生成统一入口")
    parser.add_argument("--repo", required=True,
                        help="MCU 仓库根目录 (mcu_app_tda4 或 mcu_app_j6)")
    parser.add_argument("--config", required=True,
                        help="配置/车型名 (如 v2xsea, rx)")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印将执行的命令, 不实际运行 (转发给子工具)")
    args, extra = parser.parse_known_args()

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        fail("路径不存在或不是目录: %s" % repo)

    etas = bool(list(repo.glob("cpj_*/autosar/%s/BswRta" % args.config)))
    davinci = bool(davinci_microsar_hits(repo, args.config, extra))
    if etas and davinci:
        fail("仓库同时匹配 ETAS 与 Davinci 结构, 无法判型: %s" % repo)
    if etas:
        platform, sub_main = "ETAS", ETAS_MAIN
    elif davinci:
        platform, sub_main = "Davinci", DAVINCI_MAIN
    else:
        fail("无法判型 (config=%s):\n"
             "  ETAS    需 cpj_*/autosar/%s/BswRta\n"
             "  Davinci 需 */(%s 或 veh_%s)/microsar_cfg"
             % (args.config, args.config, args.config, args.config))
    if not sub_main.is_file():
        fail("子工具不存在: %s" % sub_main)

    sub_cmd = [sys.executable, str(sub_main),
               "--repo", str(repo), "--config", args.config] + extra
    if args.dry_run:
        sub_cmd.append("--dry-run")

    print("[Nvm_AutoGen] 平台     : %s" % platform)
    print("[Nvm_AutoGen] MCU 仓库 : %s" % repo)
    print("[Nvm_AutoGen] 配置     : %s" % args.config)
    print("[Nvm_AutoGen] 子工具   : %s" % sub_main)

    if args.dry_run:
        print("[Nvm_AutoGen] --dry-run, 将执行:")
        print("  %s" % " ".join(sub_cmd))
        return

    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    print("[Nvm_AutoGen] ==> 运行子工具 %s" % sub_main.name)
    rc = subprocess.run(sub_cmd, env=env).returncode
    if rc != 0:
        print("[Nvm_AutoGen] ERROR: 子工具失败 (exit %d)" % rc)
        sys.exit(rc)
    print("[Nvm_AutoGen] 全部完成")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 语法检查**

```bash
python -m py_compile "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen.py"
```

Expected: exit 0。

---

### Task 7: 端到端 dry-run 验证

**Files:** 无新增，只验证。

- [ ] **Step 1: J6 全链路 dry-run（可完整验证）**

```bash
python "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen.py" \
  --repo "D:/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6" \
  --config rx --dry-run
```

Expected: 顶层打印 `平台: ETAS`、`子工具: ...nvm_autogen_etas.py`，子工具 dry-run 输出与 Task 5 Step 5 一致，exit 0。

- [ ] **Step 2: TDA4 全链路 dry-run（需 --excel，表不在仓库）**

```bash
python "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen.py" \
  --repo "D:/Workspace/01_Projects/02_Src/01_Workspace_TDA4/src/mcu_app_tda4" \
  --config v2xsea --dry-run --excel <NVM_List.xlsx 路径>
```

Expected: 顶层打印 `平台: Davinci`、`子工具: ...Nvm_AutoGen_Davinci\Nvm_AutoGen.py`，子工具 dry-run 输出与 Task 4 Step 5 一致，exit 0。

- [ ] **Step 3: 判型失败路径验证**

```bash
python "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen/Nvm_AutoGen.py" \
  --repo "D:/Workspace/01_Projects/02_Src/10_tools" --config nonexistent --dry-run
```

Expected: `ERROR: 无法判型 (config=nonexistent)` + 两个平台所需的目录结构提示，exit 1。

- [ ] **Step 4: 汇报冒烟测试待办（需 license，留给用户决定时机）**

向用户说明：实跑验证（TDA4 需 CodeMeter license + NVM 表入库；J6 需 ISOLAR/RTA-CAR 环境）建议在真实需求开发时进行首次冒烟：
- J6: `python Nvm_AutoGen.py --repo $J6 --config rx`
- TDA4: `python Nvm_AutoGen.py --repo $TDA4 --config v2xsea`

---

## Self-Review 结果

1. **Spec 覆盖**：目录结构（Task 1/2 拷贝、Task 4/5 主流程、Task 6 入口）、三开关 configs（Task 4/5 Step 1-2）、check_nvm_table OFF 占位（Task 4/5 主流程报错分支）、BSW 生成复用 Dem 流程（Task 4 的 DVCfgCmd + license、Task 5 的 headless→Cobra）、Excel 自动发现（Task 4/5 的 discover_excel）、J6 CrmGen 参数化 + git diff 验证（Task 3）、dry-run（Task 4/5/6/7）——全部有对应任务。
2. **占位符扫描**：无 TBD/TODO；Task 4 Step 5 与 Task 7 Step 2 的 `<NVM_List.xlsx 路径>` 是运行时用户输入占位（TDA4 表不在仓库，无法预知），已在步骤文字中说明原因。
3. **类型/命名一致性**：`GEN_NVM_SCRIPT`/`CRM_GEN_SCRIPT` 两子工具同名同义；`DRY` 全局 + `run_step` 守卫在两个子工具中行为一致；J6 CrmGen 8 参数顺序与 Task 3 usage 文本、Task 5 调用一致（excel/sheet/NvM_Cfg.h/BswAdapter.h/BswAdapter.c/dataitem.cpp/RteServices.h/pdm_cfg.h）。
