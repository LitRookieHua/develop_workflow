# ⚙️ J02 EVM/DTC 表 V0.1 导入 需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | Dem 事件/DTC 配置导入（EVM 问卷表） | **所属软件层级** | BSW (Dem / 诊断应用层 evm_cfg) |
| **文档状态** | 🟢 开发中 | **安全与质量要求** | GHS 零警告 ｜ 生成器一致性 |
| **模块负责人 / 作者** | Hua.Yao / Claude | **关联输入/输出** | 📊 `IDC_EVM_Config_Jieda_J02_V0.1_20261119.xlsx` ｜ 📑 [C097FAWVWREQ-507](https://jira.imotion.ai:7070/browse/C097FAWVWREQ-507) / [C097FAWVW-35](https://jira.imotion.ai:7070/browse/C097FAWVW-35) |

> **📝 变更记录**
> * `2026-11-23`｜Hua.Yao / Claude｜V1.0｜初版：J02 首次 EVM 表导入设计（表结构 + 工具布局适配 + 双分支交付）

> 本需求为 EVM 配置表导入，无新增手写框架代码，按模板精简规则省略手写接口/并发/初始化小节（追溯见附录A）。

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景**：一汽捷达 J02（C097，J6B 一体机）首次释放 EVM/DTC 问卷 V0.1（2026/11/19，见 C097FAWVWREQ-472），表基线为 CMC_RX V3.0 的 J6B 一体机配置。
* **核心目标**：把 V0.1 表导入 `mcu_app_j6_v2 / cpj_fawvw / veh_j02`，全量重生成 Dem 配置（Event / DTC / DTC 属性 / Debounce / ECG / FiMFID 映射），并**同时交付 develop 与 J02 DV release 两个分支**。
* **设计原则**：复用既有 Dem 生成链（`Dem_AutoGen` 主入口），v2 仓库的变体式目录布局通过**向后兼容的工具扩展**支持，不修改任何表结构；表为唯一真源。

### 1.2 适用范围 (Scope)

* **适用控制器/平台**：J02（`mcu_app_j6_v2` 仓库，`cpj_fawvw` / 变体 `veh_j02`，preset `cpj_fawvw_j02_d310`，GHS 工具链）
* **范围边界**：
  - 本单**仅导入 EVM/DTC 表 V0.1**；不涉及 Dcm DID/UDS 问卷（C097FAWVWREQ 需求树另一路）、不涉及 NVM 新块。
  - **DemGeneral 容器（使能条件组 + 快照/扩展数据栈）暂不启用**（用户 2026-11-23 明确指定 false）：13.10 生成机的 committed 工具尚无 `gen_dem_general`，`configs/veh_j02.yaml` 不写入该键（工具对未知键直接报错，不写即等价 false）。
  - 交付 develop 与 `release/FAWVW/J02_C097/DV` 两个分支；两分支基线已分叉（DV 有 12 个 DV 专属提交、develop 领先 483 个提交），**各自独立生成、独立提交**。

### 1.3 术语与缩略语

| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| EVM 表 | EVM Config 问卷 | `IDC_EVM_Config_*.xlsx`，Dem 生成输入（Event/DTC/ECG/FiMFID 多 sheet） |
| ECG | Enable Condition Group | Dem 使能条件组 |
| DTC | Diagnostic Trouble Code | 故障码（hex + UDS 32 位格式） |
| v1 / v2 布局 | — | v1：`cpj_*/autosar/<config>/BswRta` + `cpj_*/evm_cfg/var/...`（mcu_app_j6）；v2：`cpj_*/<variant>/autosar/BswRta` + `cpj_*/<variant>/evm_cfg/{inc,src}`（mcu_app_j6_v2） |

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | [C097FAWVWREQ-507 EVM V0.1导入](https://jira.imotion.ai:7070/browse/C097FAWVWREQ-507) | — | 需求来源（Requirement） |
| R2 | [C097FAWVWREQ-472 E2E版本释放](https://jira.imotion.ai:7070/browse/C097FAWVWREQ-472) | V0.1（2026/11/19） | 问卷 xlsx 附件 / 版本历史 |
| R3 | [dtc-table-import.md](../../.claude/references/dtc-table-import.md) | — | DTC 表导入硬规则 |
| R4 | [autosar-code-generation.md](../../.claude/references/autosar-code-generation.md) | — | 生成路径/工具主入口 |
| R5 | [2026-11-23-STIDC510-197-sxt-d118-dtc-table-v03-import-design.md](2026-11-23-STIDC510-197-sxt-d118-dtc-table-v03-import-design.md) | — | 同族 EVM 导入先例（主入口 + 变体 yaml + 提交范围收敛） |
| R6 | [2026-11-18-C097FAWVW-29-j02-did-2a0c-internal-temperature-cluster-design.md](2026-11-18-C097FAWVW-29-j02-did-2a0c-internal-temperature-cluster-design.md) | — | J02 仓库/变体/GHS 编译事实 |

### 1.5 设计约束与假设

* **技术约束**：AUTOSAR 生成一律在 10.0.13.10（`ssh cp@`）执行，产物 scp 到 10.0.12.42 提交；J02 编译走 CI（12.42 无 GHS 工具链，见 C097FAWVW-27 结论）。
* **外部假设**：V0.1 问卷已正式释放（R2）；表中 `N.A` 行按既有生成器语义处理（保留事件/无 DTC），不做表修正。
* **工具配置缺口（本单补齐）**：
  1. `configs/veh_j02.yaml` 不存在 → 新增（显式 `gen_dem_table.enabled=true`；jumpdown/jumpup 继承 common 的 `false/false`，与 J02 现有 arxml 实测一致）。
  2. Dem_AutoGen 的 ETAS 路径解析只认 v1 布局 → 需扩展为**双布局自动识别**（对 mcu_app_j6 零影响）。

---

## 二、 架构设计与模块间交互 (Architecture & Interaction)

### 2.1 导入链

```
V0.1 xlsx（新目录 cpj_fawvw/veh_j02/tools/e2e_dem/）
  → 10.0.13.10 Dem_AutoGen 主入口（--repo mcu_app_j6_v2 --config veh_j02）
      (gen_dem_table → 紧接 ISOLAR headless BSW 重生成 → gen_fim_code → gen_map_yaml)
  → 生成物（按先例收敛后提交）：
      cpj_fawvw/veh_j02/autosar/BswRta/ecu_config/bsw/gen/J6B_Dem_EcucValues.arxml（+ Dem_Cfg_* / swcd / _fwd 派生 arxml）
      cpj_fawvw/veh_j02/autosar/BswRta/src/bsw/Dem/Dem_Cfg_*.h/.c（ISOLAR headless 重生成）
      cpj_fawvw/veh_j02/autosar/BswRta/src/bsw/Dcm/Dcm_Lcfg_DslDsd.h（DTC 相关）
      cpj_fawvw/veh_j02/tools/e2e_dem/{dtc,event,fimfid}_map.yaml（gen_map_yaml）
      cpj_fawvw/veh_j02/evm_cfg/...（gen_fim_code 三文件，是否提交见 ADR #4）
  → scp 到 12.42 对应分支 → commit/push → PR（CI 编译，GHS）
```

### 2.2 模块影响

| BSW 模块 | 受影响配置 | 说明 |
| :--- | :--- | :--- |
| Dem | DemEventParameter / DemDTC / Debounce / ECG 引用 / DTC 属性 / 扩展数据 | 事件集合与映射按 V0.1 表全量重生成 |
| Dem | Dem_PrjSpecificControl.c | `gen_event_ctrl=false`，本单不生成 |
| evm_cfg（FiM 上报） | FidCfg.hpp / iSysFidCfg.cpp / zx_sys_evm_cfg_fimcfg.hpp | gen_fim_code 会生成；提交与否按生成后与现基线比对决定（ADR #4） |

### 2.3 工具布局适配（v2 变体式目录）

`mcu_app_j6_v2` 所有客户均为变体式布局（实查：`cpj_gac/veh_v20/autosar`、`cpj_chery/veh_*/autosar`、`cpj_fawvw/veh_j02/autosar`），与 Dem_AutoGen 现有 glob 不符：

| 目标 | 现有（v1）glob | v2 实际 | 适配方案 |
| :--- | :--- | :--- | :--- |
| BswRta 定位 | `cpj_*/autosar/<config>/BswRta` | `cpj_*/<config>/autosar/BswRta` | 两个 pattern 合并后要求恰好 1 命中 |
| Excel 发现 | `cpj_*/tools/<config>/e2e_dem/` | `cpj_*/<config>/tools/e2e_dem/` | 同上 |
| evm_cfg 输出 | `cpj/evm_cfg/var/{src/vehicle/<config>/_gen,inc/vehicle/<config>/evm_cfg}` | `cpj/<config>/evm_cfg/{src/_gen,inc/evm_cfg}` | 以 `cpj/evm_cfg/var` 是否存在判定布局 |

改动文件：`Dem_AutoGen_Etas/dem_autogen_etas.py`（`resolve_repo_paths` / `discover_excel`）与 `Dem_AutoGen/Dem_AutoGen.py`（`etas_map_args`），纯路径识别，v1 行为不变。

---

## 三、 核心逻辑与参数规则

### 3.1 V0.1 表内容（首次导入，无前版差异）

| Sheet | 数据行（含表头） | 内容 |
| :--- | :--- | :--- |
| RCore_Event_d310 | 1720 × 44 | R 核事件：Event Name / DTC(hex) / DemUdsDTC / 可用条件 / 17 个 FiMFID 列 / 去抖 / ECG / 操作循环 / NVM 地址 / 快照 |
| PF_Event | 237 × 44 | PF 事件（同列结构） |
| CPJ_Event_Net | 614 × 66 | 网联/CPJ 事件（多出 20+ 空列） |
| 04_ECG | 13 × 4 | 12 组使能条件组（ECG_Voltage / ECG_Rcore / ECG_NET / ECG_Busoff 等） |
| 05_Abbr_sheet | 23 × 6 | 缩写表 |
| 06_FiMFID_list | 86 × 4 | 85 条 FiMFID（是否经 IPC 传 FM / 经 RTE 传 Driving Fusa Monitor） |
| History | 2 × 4 | `0.1 / zane.zhang / 初版释放（base J6B一体机项目 CMC_RX V3.0) / 2026.11.19` |

> 表中大量保留行（Event Name 或 DTC 为 `N.A`）按生成器既有语义处理（创建保留事件、不建 DTC）。合并单元格在 pandas 读取后按生成器逻辑展开，**以生成器打印的「合并后数据行数」与 arxml 容器数为准**做验收对账。

### 3.2 现有基线（导入前实测）

| 指标 | 值（`veh_j02` develop 分支） |
| :--- | :--- |
| arxml 唯一 DemEvent 名 | 603（其中 Reserved 90） |
| arxml 唯一 DemDTC 名 | 75 |
| DemDebounceCounterJumpDown/JumpUp | false / false |
| 引用 ECG | 6 组 |

### 3.3 可配置参数表

| 参数分类 | 参数名 / 项 | 取值 | 作用 |
| :--- | :--- | :--- | :--- |
| 生成开关 | `gen_dem_table.enabled` | `true` | 生成 Dem ARXML + ISOLAR BSW 重生成 |
| 生成开关 | `gen_dem_table.jumpdown/jumpup` | `false / false`（继承 common） | 与现基线一致 |
| 生成开关 | `gen_event_ctrl` / `gen_fim_code` | `false` / `true`（继承 common） | 事件控制不生成；FiM 三文件生成 |
| DemGeneral | （不写入配置） | 等价 `false` | 用户指定暂不启用；13.10 工具无该键 |

---

## 四、 模块详细设计 (Detailed Design)

### 4.1 修改点清单（文件级）

| # | 仓库 | 文件 | 改动 |
| :--- | :--- | :--- | :--- |
| 1 | develop_workflow | `tools/autosar_gen/Dem_AutoGen/Dem_AutoGen_Etas/configs/veh_j02.yaml` | 新增：`gen_dem_table.enabled=true` + DemGeneral 暂不启用注释 |
| 2 | develop_workflow | `.../Dem_AutoGen_Etas/dem_autogen_etas.py` | 路径解析支持 v2 变体式布局（BswRta / Excel / evm_cfg） |
| 3 | develop_workflow | `.../Dem_AutoGen/Dem_AutoGen.py` | `etas_map_args` 同步双布局 |
| 4 | mcu_app_j6_v2 | `cpj_fawvw/veh_j02/tools/e2e_dem/IDC_EVM_Config_Jieda_J02_V0.1_20261119.xlsx` | 新增表 + `*_map.yaml`（生成器输出） |
| 5 | mcu_app_j6_v2 | `.../autosar/BswRta/ecu_config/bsw/gen/J6B_Dem_EcucValues.arxml`（+ 派生 arxml：Dem_Cfg_DtcMcSupportData / Dem_Cfg_McSupportData / swcd / _fwd） | 生成 |
| 6 | mcu_app_j6_v2 | `.../autosar/BswRta/src/bsw/Dem/Dem_Cfg_*` | 生成（ISOLAR headless） |
| 7 | mcu_app_j6_v2 | `.../autosar/BswRta/src/bsw/Dcm/Dcm_Lcfg_DslDsd.h` | 生成（DTC/UDS 映射） |
| 8 | mcu_app_j6_v2 | `cpj_fawvw/veh_j02/evm_cfg/{src/_gen,inc/evm_cfg}/*` | 生成；提交范围按 ADR #4 比对后定 |
| 9 | zos_msg | `Gen_evm_dem_Script/IDC_EVM_Config_Jieda_J02_V0.1_20261119.xlsx` | 上传（硬规则 2） |

> **提交范围排除项**：ISOLAR 全量重生成会在 `src/bsw` 下产生 CanIf/CanSM/Com/WdgM/EcuM/StbM/BswM 等非 Dem 模块漂移（含手写 patch 被覆盖风险），一律不提交；`_log/*`、`spdx.json`、`.bak` 不提交。**两分支各自生成、各自按同一收敛规则挑文件提交。**

---

## 五、 异常处理、容错与安全机制

| 场景 | 处理 |
| :--- | :--- |
| 表校验问题（空 DTC / 事件名手误） | 本工具链 `check_dtc_table` 未引入（关闭）；如发现需修表，按 R3 硬规则通知需求创建人（Zane Zhang/章泽念） |
| 生成器静默失败（insert 未落但 exit 0） | 主入口以 arxml mtime + 容器 DEF 锚点（DemEventParameter / DemDTC）兜底 |
| BSW headless 生成失败 | 主入口降级 Cobra.exe（J02 已确认 `ecu_config/cobra/Cobra.exe` 存在） |
| 既有手工 patch 被重生成覆盖 | 生成后按 patch 标记检索重放（R4 §1.4）；J02 DV 分支含 T1 projGen token 修复等 DV 专属改动，**生成物挑文件提交时逐文件确认不误带** |
| 双分支生成物互相污染 | develop 与 DV 分支在各自分支工作区独立生成、独立提交，不跨分支 cherry-pick 生成物 |

---

## 六、 验证、测试与集成要求 (Verification & Integration)

### 6.1 资源消耗与性能基线

纯配置数据（Dem 事件/DTC 集合刷新），ROM 增量随事件/DTC 数变化，无新增 RAM 缓冲、无动态内存。

### 6.2 验收标准 (Acceptance Criteria)

1. Dem 生成源码编译通过：以 PR CI（GHS，preset `cpj_fawvw_j02_d310`）零错误为准（12.42 无本地 GHS）。
2. 生成 arxml 事件/DTC 数与 V0.1 表一致（生成器日志「合并后数据行数」+ arxml 容器计数对账）。
3. 既有事件 DTC/UDS 映射无意外回归（导入前 603 事件 / 75 DTC 基线对照）。
4. zos_msg 已上传 V0.1 xlsx（硬规则 2；J02 的 zos 产品配置当前不消费 EVM 表，上传仍为规范要求）。
5. 生成产物不含 DemGeneral 段变更（`gen_dem_general` 不启用）。
6. **双分支交付**：develop 与 `release/FAWVW/J02_C097/DV` 各一个 PR，均合并。
7. 台架：刷写后 DTC/Dem 事件读取正常（用户手动验证）。

---

## 附录A：需求追溯矩阵

| 需求条目 | 设计章节 | 代码落点 |
| :--- | :--- | :--- |
| 导入 V0.1 EVM 表 | §2.1 / §3.1 | `cpj_fawvw/veh_j02` Dem 生成物（§4.1 #4~#8） |
| 双分支交付（develop + DV） | §1.2 / §6.2 | 两分支独立生成/提交/PR |
| 表上传 zos_msg | §4.1 #9 | zos_msg Gen_evm_dem_Script |

## 附录B：设计决策记录 (ADR 摘要)

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | 用主入口 Dem_AutoGen + 新增 `veh_j02.yaml` | 沿用仓库遗留 `gen_e2e_dem.bat` 流程 | R4 禁用旧 bat（无 ISOLAR BSW 重生成） |
| 2 | 工具扩展支持 v2 变体式布局 | 在 v2 仓库造 v1 布局 | v2 全客户统一变体式布局，造目录会误导后续所有项目；双 pattern 合并对 v1 零影响 |
| 3 | DemGeneral 不启用（配置不写该键） | 写 `gen_dem_general.enabled: false` | 13.10 工具 FEATURES 不含该键且对未知键报错，写了会直接失败；用户亦指定暂不启用 |
| 4 | evm_cfg 三文件提交范围按生成后比对决定 | 固定提交 / 固定不提交 | J02 为首次 EVM 导入，现有 evm_cfg 可能同源基线；差异合理（事件集变化）则纳入，属历史漂移则按 SXT 先例排除并记录 |
| 5 | 两分支独立生成而非 cherry-pick | 一分支生成后 cherry-pick 到另一分支 | 两分支基线分叉（DV 12 个专属提交），生成物包含上下文 event 排序，cherry-pick 冲突且易漏改 |

## 附录C：开放问题 (Open Issues)

| # | 问题描述 | 影响 | 状态 |
| :--- | :--- | :--- | :--- |
| 1 | J02 zos 侧是否需要 EVM 接口生成（`product/FAWVW/J02_C097` 无 EVM 配置、CMake 未调用 Evm_Interface_Gen） | 若后续启用需配 `ZX_BSW_EVM_CFG_FILE_NAME`（build_config 现为 GAC_AY7 残留值） | 待确认（不阻塞本单，表照常上传 zos_msg） |
| 2 | evm_cfg 三文件与本单事件集的一致性 | FID 上报映射准确度 | 生成后比对（ADR #4） |
| 3 | 表中保留事件（DTC=N.A）在 DV 分支的既有基线差异 | 生成后事件总数与 develop 分支不同 | 生成后核对，分分支记录 |
