# Nvm_AutoGen 设计

日期：2026-09-22
状态：已确认（方案 A：完全对齐 Dem_AutoGen 三层结构）

## 背景与目标

NVM/PDM 生成目前散落在两个 MCU 仓库的手工脚本中，无统一入口、无配置开关、
流程（更新 arxml → BSW 代码生成 → PDM 代码）需人工逐步执行。参照
Dem_AutoGen 三层结构（统一入口 + Davinci/ETAS 子工具）构建 Nvm_AutoGen，
实现一键流程。

三个功能（configs yaml 开关控制）：

| 开关 | 默认 | 说明 |
|---|---|---|
| `check_nvm_table` | **OFF** | 检查 nvm 表。脚本尚未引入，ON 即报错中止（同 Dem_Etas 处理） |
| `gen_nvm_arxml` | ON | 更新 NVM arxml + BSW 代码生成 |
| `gen_pdm_code` | ON | 生成 PDM 代码（纯 Excel→代码，无需 license） |

与 Dem 的差异：无 gen_map_yaml 步骤，子工具成功即结束。

## 目录结构

```
10_tools/
└── Nvm_AutoGen/                   # 子工具放入口目录内 (Dem 实际工作结构, 避免顶层重复副本)
    ├── Nvm_AutoGen.py              # 统一入口：判型 + 参数转发
    ├── docs/superpowers/specs/     # 本 spec
    ├── Nvm_AutoGen_Davinci/
    │   ├── Nvm_AutoGen.py          # 子工具主流程
    │   ├── configs/{common,v2xsea}.yaml
    │   ├── gen_nvm_arxml/              # ← 拷贝自 mcu_app_tda4/tools/Gen_Pdm_Script/NvM_Develop_Gen_ARXML_Script
    │   │   ├── ExcelAnalize.py         #   (ExcelAnalize.py / GenPdmARXML.py / ProcessArxml.py，零改动)
    │   │   ├── GenPdmARXML.py
    │   │   └── ProcessArxml.py
    │   └── gen_pdm_code/               # ← 拷贝自 mcu_app_tda4/tools/Gen_Pdm_Script/PDM_Gen_Crm_Script
    │       ├── CrmGen.py               #   (CrmGen.py / ExcelAnalize.py / Merge_Excel.py /
    │       ├── ExcelAnalize.py         #    TemplateFile.py / template/ 4 个 _T 模板，零改动)
    │       ├── Merge_Excel.py
    │       ├── TemplateFile.py
    │       └── template/
    └── Nvm_AutoGen_Etas/
        ├── nvm_autogen_etas.py         # 子工具主流程
        ├── configs/{common,rx}.yaml
        ├── gen_nvm_arxml/              # ← 拷贝自 mcu_app_j6/cpj_cmc/pdm_cfg/rx/Pdm_Script/NvM_Develop_Gen_ARXML_Script
        │   └── GenPdmARXML.py          #   (argparse -i/-e/-o，零改动)
        └── gen_pdm_code/               # ← 拷贝自 mcu_app_j6/cpj_cmc/pdm_cfg/rx/Pdm_Script/PDM_Gen_Crm_Script
            ├── CrmGen.py               #   ★ 唯一需改造的脚本：输出路径参数化
            ├── ExcelAnalize.py / Merge_Excel.py / TemplateFile.py
            ├── SRU_crm_RteServices.h   #   RteServices 是输出而非模板，保留
            └── template/               #   5 个 _T 模板
```

## 顶层入口 Nvm_AutoGen/Nvm_AutoGen.py

与 Dem_AutoGen/Dem_AutoGen.py 同构：

- 参数：`--repo <mcu仓库> --config <配置名> [--dry-run]`，其余参数（--excel/
  --variant/--customer/--sheet/--skip-gen 等）原样转发给子工具
- 判型（互斥，双匹配报错）：
  - ETAS (mcu_app_j6)：仓库下存在 `cpj_*/autosar/<config>/BswRta`
  - Davinci (mcu_app_tda4)：仓库下存在 `*/(<config>|veh_<config>)/microsar_cfg`
- 转发：`python <子工具main> --repo <repo> --config <config> <extra...>`
- 与 Dem 的区别：子工具成功后直接结束（无 map 生成步骤）
- `--dry-run`：只打印将执行的命令

## Nvm_AutoGen_Davinci（TDA4 / Vector）

### 参数

`--repo --config/--variant --customer --excel --sheet --skip-gen`（对齐 Dem_AutoGen_Davinci）

### 路径推导（复用 Dem 的发现逻辑）

- config `v2xsea` → 变体 `cpj_chery/veh_v2xsea`（`<customer>/<variant>/microsar_cfg`
  全仓库唯一匹配；`--variant/--customer` 收窄）
- cfg_dir = `microsar_cfg` 的唯一子目录（如 `d300e`）
- SipAddon = `<customer>/<variant>/microsar_cfg/<cfg_dir>/build/SipAddon`
- arxml = `SipAddon/Config/Developer/ComponentTypes/NVM_SWC_1.arxml`（已验证存在）
- datatype arxml = `SipAddon/Config/Developer/DataTypes.arxml`（已验证存在）
- dpa = `SipAddon/Demo.dpa`；DVCfgCmd = `<repo>/microsar_tools_tda4/DaVinciConfigurator/Core/DVCfgCmd.exe`
- PDM 输出 = `<customer>/<variant>/pdm_cfg/{inc/pdm_cfg, src}`（已验证存在）
- Excel 自动发现：`<customer>/<variant>/tools/` 下唯一 `*NVM_List*.xlsx`，回退
  仓库 `tools/Gen_Pdm_Script/`；`--excel` 覆盖。
  ⚠️ `CHERY_V2xSEA_NVM_List.xlsx` 目前不在仓库中，表入库后此规则可能需调整。

### gen_nvm_arxml ON 时的流程

1. 连接 license（USB over Network Client → CodeMeter-Stick，常量同 Dem）
2. 更新 arxml：`GenPdmARXML.py <excel> 01_NVM_List <NVM_SWC_1.arxml> <DataTypes.arxml>`
   （源脚本已支持 4 参数 argv）
3. DaVinci sync：`DVCfgCmd --project <dpa> --syncSystemDescription --saveProject --validate`，
   log 三段式失败判定（锁定/同步未完成/保存失败），逻辑照搬 Dem 的 `davinci_sync`
4. 生成 NvM 代码：`DVCfgCmd --project <dpa> --generate --modulesToGenerate /MICROSAR/NvM`
   （`--skip-gen` 时跳过）
5. `finally` 断开 license（无论成败）

arxml 更新后以 `NvMBlock` 容器锚点做内容兜底（防子脚本静默失败）。

### gen_pdm_code ON 时

`CrmGen.py <excel> 01_NVM_List <NvM_Cfg.h> <pdm_cfg.h> <pdmdb.h> <pdmdb.cpp> <pdm_cfg_dataitem_config.cpp> <template目录>`

- 源脚本已支持 8 参数 argv，零改动
- `NvM_Cfg.h` = `<customer>/<variant>/microsar_cfg/<cfg_dir>/src/GenData/NvM_Cfg.h`
  （gen_nvm_arxml 步骤 4 的产物 → gen_pdm_code 依赖 gen_nvm_arxml 先跑）

## Nvm_AutoGen_Etas（J6 / ETAS）

### 参数

`--repo --config --excel`

### 路径推导

- `cpj_*/autosar/<config>/BswRta` 唯一匹配（如 `cpj_cmc/autosar/rx/BswRta`）
- arxml = `BswRta/ecu_config/bsw/gen/J6B_NvM_EcucValues.arxml`（排除 `RTA_BIP_` 前缀，
  唯一匹配；已验证存在）
- `NvM_Cfg.h` = `BswRta/src/bsw/NvM/NvM_Cfg.h`（已验证存在）
- PDM 输出 = `cpj_*/pdm_cfg/<config>/{inc/pdm_cfg, src}`（已验证存在）
- Cobra = `BswRta/ecu_config/cobra/Cobra.exe`；ConfGen log = `BswRta/_log/BSW_ConfGen_ECUGeneration.txt`；
  BSW log = `BswRta/_log/rta-bsw.log`
- Excel 自动发现：`cpj_*/pdm_cfg/<config>/Pdm_Script/*_NVM_List.xlsx`（排除 `_merged`），
  `--excel` 覆盖（如 `RX_NVM_List.xlsx`，已验证存在）

### gen_nvm_arxml ON 时的流程

1. 更新 arxml：`GenPdmARXML.py -i <arxml> -e <excel> -o <arxml>`（原地更新，
   同现有 GenPdmARXML.bat；脚本自带 argparse）
2. BSW 生成：ISOLAR headless（`ISOLAR-AB.cmd -generate -p=<BswRta> -t=BSW`，
   3600s 超时杀进程树 + rta-bsw.log 新鲜度判定 + 失败标记扫描）失败降级
   Cobra.exe（`--ProjectPath=. --isolarPath=<isolar> --isolarARRoot=RTA_BIP`，
   license 失败/静默失败/ConfGen 错误数判定）——整段逻辑照搬 Dem_Etas
   （`gen_bsw_headless` / `gen_bsw_cobra` / `find_isolar_b` / `isolar_cmd_path`，
   `RTA_CAR_HOME` 环境变量，默认 `D:/ETAS/RTA-CAR_12.7.0`）

### gen_pdm_code ON 时

J6 的 `CrmGen.py` 现状输出路径全部写死为脚本相对目录，**需参数化改造**：

```
CrmGen.py <excel> 01_NVM_List <NvM_Cfg.h> <BswAdapter.h> <BswAdapter.c> <dataitem_config.cpp> <SRU_crm_RteServices.h> <pdm_cfg.h>
```

- 模板路径（`template\*_T.*`）保持相对脚本目录，不参数化
- 输出映射（bat 现状 → 参数化后由主流程传入）：
  - `pdm_cfg/<config>/inc/pdm_cfg/pdm_cfg_BswAdapter.h`
  - `pdm_cfg/<config>/src/pdm_cfg_BswAdapter.c`
  - `pdm_cfg/<config>/src/pdm_cfg_dataitem_config.cpp`
  - `<脚本目录>/SRU_crm_RteServices.h`（保持原位，参数仍显式传入）
  - `pdm_cfg/<config>/inc/pdm_cfg/pdm_cfg.h`
- 这是本次唯一有实质改动的脚本

## 配置加载

- **Davinci**：对齐 Dem_Davinci——`--config` 探测（原路径/加 .yaml/configs/<名>/
  configs/<名>.yaml），未找到回退 common.yaml 并提示；未知键/缺键/值非 ON/OFF 报错
- **ETAS**：对齐 Dem_Etas——common.yaml + `<config>.yaml` 深合并，二级键校验
  （本工具无二级配置，仅三个布尔开关）
- `check_nvm_table: ON` 时：报"脚本尚未引入"并 exit 1（占位，同 Dem_Etas）

## 错误处理

**前置校验**（任一失败 `ERROR` + exit 1，不占 license）：

- repo/config 路径不存在、判型失败或双匹配
- yaml 含未知键 / 缺键 / 值非法
- 依赖文件不存在：Excel、arxml、DataTypes.arxml（仅 TDA4）、dpa、DVCfgCmd、
  ISOLAR 启动器、Cobra（降级时才检查）
- `gen_pdm_code` 依赖的 `NvM_Cfg.h` 不存在（gen_nvm_arxml OFF 且仓库无产物时）
  报错提示先跑 gen_nvm_arxml

**运行中失败**：

- 子步骤非零退出：打印 stdout/stderr 尾部 3000 字符 + exit 1（`run_step` 照搬）
- TDA4 DaVinci sync：log 三段判定 + Validation 摘要打印
- TDA4 arxml 更新后：`NvMBlock` 容器锚点内容兜底
- ETAS BSW：headless 失败 → 降级 Cobra → 双失败才报错；超时 taskkill 进程树
- TDA4 license：`try/finally` 保证断开

## 验证方式

1. 顶层与子工具均支持 `--dry-run`：打印推导出的全部路径 + 将执行的子命令，
   不实际运行（无 license 环境下验证路径推导）
2. 冒烟测试（需 license，实施后手工跑）：
   - TDA4：`Nvm_AutoGen.py --repo <tda4> --config v2xsea --dry-run` → 实跑
   - J6：`Nvm_AutoGen.py --repo <j6> --config rx --dry-run` → 实跑
3. J6 CrmGen 改造验证：用 `RX_NVM_List.xlsx` 实跑一次，`git diff` 对比 5 个输出
   文件与改造前 bat 方式的产物一致

## 明确不做（YAGNI）

- 不写单元测试（流程编排型脚本，Dem 同类工具也没有）
- 不实现 check_nvm_table（明确 OFF，ON 即报错）
- 不做 map 表生成类似物（NVM 无 map 需求）
- TDA4/J6 源脚本除 J6 CrmGen 参数化外零改动（保持与仓库原版可 diff）
