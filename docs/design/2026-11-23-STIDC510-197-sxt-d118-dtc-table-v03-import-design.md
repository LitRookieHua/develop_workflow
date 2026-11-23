# ⚙️ Smartxtruck D118 EVM/DTC 表 V0.3 导入 需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | Dem 事件/DTC 配置导入（EVM 问卷表） | **所属软件层级** | BSW (Dem / 诊断应用层 evm_cfg) |
| **文档状态** | 🟢 开发中 | **安全与质量要求** | MISRA C:2012 ｜ 零警告 |
| **模块负责人 / 作者** | Hua.Yao / Claude | **关联输入/输出** | 📊 `IDC_EVM_Config_Smartxtrunk_D118_V0.3_20261118.xlsx` ｜ 📑 [STIDC510-197](https://jira.imotion.ai:7070/browse/STIDC510-197) / [IDC700ECT-450](https://jira.imotion.ai:7070/browse/IDC700ECT-450) |

> **📝 变更记录**
> * `2026-11-23`｜Hua.Yao / Claude｜V1.0｜初版：V0.2→V0.3 差异分析 + 导入设计

> 本需求为 EVM 配置表导入，按模板精简规则省略部分详细设计小节（无新增手写框架代码，追溯见附录A）。

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景**：智加（Smartxtruck）D118 项目（J6 平台一体机）诊断问卷由客户持续释放。V0.3（STIDC510-198，2026/11/19）在 V0.2 基础上**新增功能安全相关 DTC**。
* **核心目标**：将 V0.3 EVM 表导入 `mcu_app_j6 / cpj_smartxtruck`（变体 `sxt_a`），全量重生成 Dem 配置（Event 定义、Event↔DTC mapping、ECG、FiMFID、Dem_PrjSpecificControl），生成物覆盖 `cpj_smartxtruck` 对应文件。
* **设计原则**：完全复用既有 Dem 生成链（`Dem_AutoGen` 主入口），不新增任何手写框架代码；表为唯一真源。

### 1.2 适用范围 (Scope)

* **适用控制器/平台**：Smartxtruck D118（J6，`mcu_app_j6` 仓库，`cpj_smartxtruck`，变体 `sxt_a`）
* **范围边界**：
  - 本单**仅导入 EVM/DTC 表 V0.3**，不涉及 Dcm DID 变更、不涉及 A 核 IPC 映射表、不涉及 DemGeneral 侧容器（快照/使能条件组）改动。
  - 不做 NVM 新块；Dem 参数量变化由生成器自动承接。
  - **仅 `sxt_a` 变体**：D118 有 `sxt_a`/`sxt_b` 两变体，EVM 表只置于 `tools/sxt_a/e2e_dem`；`sxt_b` 的 Dem 配置为初版遗留（自 IDC510-5803 未随 DTC 表更新，V0.2 导入 IDC510-6178 亦仅动 `sxt_a`），本单沿用先例只重生成 `sxt_a`。

### 1.3 术语与缩略语

| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| EVM 表 | EVM Config 问卷 | `IDC_EVM_Config_*.xlsx`，Dem 生成的输入（Event/DTC/ECG/FiMFID 多 sheet） |
| SER | Serializer | 相机串行器链路；SER 类故障为功能安全相关事件 |
| ECG | Enable Condition Group | Dem 使能条件组，事件仅在条件满足时可用 |
| DTC | Diagnostic Trouble Code | 故障码（hex + UDS 32 位格式） |

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | [STIDC510-197 E2E导入](https://jira.imotion.ai:7070/browse/STIDC510-197) | — | 需求来源（Requirement） |
| R2 | [STIDC510-198 E2E版本释放](https://jira.imotion.ai:7070/browse/STIDC510-198) | V0.3（2026/11/19） | 问卷 xlsx 附件 / 版本历史 |
| R3 | [dtc-table-import.md](../../.claude/references/dtc-table-import.md) | — | DTC 表导入硬规则 |
| R4 | [autosar-code-generation.md](../../.claude/references/autosar-code-generation.md) | — | 生成路径/工具入口（主 python 入口） |
| R5 | [2026-10-30-F4CMC-70-rx-e2e-v3-import-design.md](2026-10-30-F4CMC-70-rx-e2e-v3-import-d107-soc-version-did-design.md) | — | 同族 RX 项目上一轮 EVM 导入先例（导入链/交付记录） |

### 1.5 设计约束与假设

* **技术约束**：autosar 生成一律在 10.0.13.10服务器执行（`ssh cp@10.0.13.10`），产物 scp 至 12.42 编译；Y: 盘禁止写源码。
* **外部假设**：V0.3 问卷已释放评审（R2）；表格无需修正（导入时如触发校验修正，按 R3 硬规则通知 Jason.Yu）。
* **工具配置缺口（本单补齐）**：Dem_AutoGen 无 `sxt_a.yaml`，committed `common.yaml` 默认 `jumpdown/jumpup=false`，而 V0.2 经旧 bat 生成时实际为 `true`（`Dem_arxml_Script.py` 双参缺省 true）。为保持行为一致，新增 `configs/sxt_a.yaml` 显式 `jumpdown/jumpup=true`，复用主入口 `Dem_AutoGen.py --config sxt_a`。

---

## 二、 架构设计与模块间交互 (Architecture & Interaction)

### 2.1 导入链

```
V0.3 xlsx（cpj_smartxtruck/tools/sxt_a/e2e_dem/，替换 V0.2 xlsx）
  → 10.0.13.10服务器 Dem_AutoGen 主入口
      (gen_dem_arxml → 紧接 ISOLAR headless BSW 重生成 → gen_event_ctrl → gen_fim_code)
  → 生成物（提交）：
      cpj_smartxtruck/autosar/sxt_a/BswRta/ecu_config/bsw/gen/J6B_Dem_EcucValues.arxml（+ Dem_Cfg_* / swcd / _fwd 派生 arxml）
      cpj_smartxtruck/autosar/sxt_a/BswRta/src/bsw/Dem/Dem_Cfg_*.h/.c（ISOLAR headless 重生成）
      cpj_smartxtruck/autosar/sxt_a/BswRta/src/bsw/Dcm/Dcm_Lcfg_DslDsd.h
  → 生成物（不提交，见 ADR #5）：evm_cfg/.../evm_cfg_FidCfg.hpp、zx_sys_evm_cfg_fimcfg.hpp、evm_cfg_iSysFidCfg.cpp
  → gen_event_ctrl=false：Dem_PrjSpecificControl.c 本单不生成
  → scp 到 12.42 对应路径 → 编译
```

### 2.2 模块影响

| BSW 模块 | 受影响配置 | 说明 |
| :--- | :--- | :--- |
| Dem | DemEventParameter / DemDTC / Debounce / ECG 引用 / DTC 属性 | 事件集合与映射按 V0.3 表全量重生成 |
| Dem | Dem_PrjSpecificControl.c | 由 gen_event_ctrl 生成 |
| evm_cfg（FiM 上报） | FidCfg.hpp / iSysFidCfg.cpp / zx_sys_evm_cfg_fimcfg.hpp | gen_fim_code 会生成，但**本单不提交**（基线陈旧，见 ADR #5 / 附录C #4） |

> 说明：本次以**配置数据**变更为主，另需对生成器做一处最小通用化修正——`merge_excel_sheets` 的 RCore_Event 表名按前缀自动识别（原硬编码 `d310`，SXT 为 `RCore_Event_d510`），涉及 `gen_dem_arxml/Dem_arxml_Script.py` 与 `gen_fim_code/Merge_ExcelSheets.py`，对 d310 项目零影响；committed 工具不含 `gen_dem_general`（DemGeneral 侧容器），V0.3 导入不触及 DemGeneral 段。

### 2.3 并发与调度上下文

不适用（配置静态数据，无新增运行期逻辑）。

### 2.4 初始化时序

不适用（Dem 初始化逻辑由 BSW 生成配置驱动，不改）。

---

## 三、 核心逻辑与参数规则

### 3.1 V0.2 → V0.3 差异（实测 diff，按 Event Name 对齐）

| Sheet | 变化 | 明细 |
| :--- | :--- | :--- |
| RCore_Event_d510 | **占位→实事件** | 删除 118 个 `DemEvent_mcu_Reserved_31..148` 占位事件；新增约 **339** 个功能安全相关事件（相机 SER：`SER_I2C_NACK_*` / `SER_VOLTAGE_ERR_*` / `SER_MIPI_ERR_*` 等，覆盖 Front30/Front120/RearL/RearR/OMS/LMS/SideFL/SideFR/DMS/AVMLeft/AVMFront/AVMRight），映射到共享的每相机 DTC（如 `0x5DC19B DemDTC_C1DC19B_Cam_Front30_SerError`）；行数净增 +357（含复用名多行） |
| RCore_Event_d510（既有事件） | **无实质变更** | 共享事件名的 DTC / UDS 值 0 处变化 |
| PF_Event / CPJ_Event_Net / 04_ECG / 05_Abbr_sheet / 06_FiMFID_list | **无变化** | 维度与内容一致 |
| History | 追加 V0.3 行 | 「新增功能安全DTC」 |

### 3.2 可配置参数表

| 参数分类 | 参数名 / 项 | 取值 | 作用 |
| :--- | :--- | :--- | :--- |
| 生成开关 | `gen_dem_table.enabled` | `true` | 生成 Dem ARXML + BSW |
| 生成开关 | `gen_dem_table.jumpdown/jumpup` | `true / true` | DemDebounceCounterJumpDown/JumpUp（对齐 V0.2 旧 bat 缺省，保持去抖行为一致） |
| 生成开关 | `gen_event_ctrl` / `gen_fim_code` | `false` / `true`（继承 common） | 事件控制 / FiM 三文件（gen_fim_code 会生成，但其产物不纳入本单提交，见 ADR #5） |

---

## 四、 模块详细设计 (Detailed Design)

> 本需求为配置导入，无新增函数/数据结构，按模板精简规则省略 4.2~4.4。

### 4.1 修改点清单（文件级）

| # | 仓库 | 文件 | 改动 |
| :--- | :--- | :--- | :--- |
| 1 | develop_workflow | `tools/autosar_gen/Dem_AutoGen/Dem_AutoGen_Etas/configs/sxt_a.yaml` | 新增：`gen_dem_table{jumpdown:true,jumpup:true}`（补齐 sxt_a 配置） |
| 2 | mcu_app_j6 | `cpj_smartxtruck/tools/sxt_a/e2e_dem/IDC_EVM_Config_Smartxtrunk_D118_V0.3_20261118.xlsx` | 新增 V0.3 表（删旧 V0.2 表，保留其它历史产物按仓库惯例） |
| 3 | mcu_app_j6 | `cpj_smartxtruck/autosar/sxt_a/BswRta/ecu_config/bsw/gen/J6B_Dem_EcucValues.arxml` | 生成（含 4 个子 arxml 视生成器输出） |
| 4 | mcu_app_j6 | `cpj_smartxtruck/autosar/sxt_a/BswRta/integration/src/bsw/Dem/user/Dem_PrjSpecificControl.c` | 生成 |
| 5 | mcu_app_j6 | `cpj_smartxtruck/evm_cfg/var/src/vehicle/sxt_a/_gen/evm_cfg_iSysFidCfg.cpp` | **不提交**（见 ADR #5：committed 基线陈旧，本单不动 evm_cfg） |
| 6 | mcu_app_j6 | `cpj_smartxtruck/evm_cfg/var/inc/vehicle/sxt_a/evm_cfg/evm_cfg_FidCfg.hpp` + `zx_sys_evm_cfg_fimcfg.hpp` | **不提交**（同 #5） |
| 7 | zos_msg | `Gen_evm_dem_Script/IDC_EVM_Config_Smartxtrunk_D118_V0.3_20261118.xlsx` | 上传 V0.3（替换现有 `..._D118_V1.0_20260727.xlsx`，按 R3 硬规则 2） |
| 8 | develop_workflow | `tools/autosar_gen/Dem_AutoGen/Dem_AutoGen_Etas/gen_dem_arxml/Dem_arxml_Script.py` | RCore_Event 表名按前缀自动识别（原硬编码 d310 → 支持 d510），向后兼容 d310 |
| 9 | develop_workflow | `tools/autosar_gen/Dem_AutoGen/Dem_AutoGen_Etas/gen_fim_code/Merge_ExcelSheets.py` | 同上：RCore_Event 表名按前缀自动识别 |

> map 表（dtc/event/fimfid map.yaml）按主入口 gen_map_yaml 输出到 Excel 同目录，随 mcu 提交（先例 F4CMC-70 同步了 map）。
>
> **实际提交文件集（生成后按先例核对收敛）**：取 IDC510-6178（V0.2 DTC 变更）+ IDC510-6514（dem event 变更）两次先例的并集——即 Dem 四 arxml（含 `_fwd/ecuc_configuration_values_fwd.arxml`，6514 有纳入）+ swcd + Dem `src/bsw/Dem/*` 9 文件 + `Dcm_Lcfg_DslDsd.h`（DTC 相关）。**排除**：① `src/bsw` 下 CanIf/CanSM/Com/WdgM/EcuM/StbM/BswM/FiM_PC 等非 Dem 模块被 ISOLAR 全量重生成时的漂移（其中 CanSM 等手写 TJA1145 patch 被覆盖，绝不能提交）；② `evm_cfg` 三文件（见 ADR #5）；③ `_log/*`、`spdx.json`、`.bak`。

---

## 五、 异常处理、容错与安全机制

| 场景 | 处理 |
| :--- | :--- |
| 表校验失败（4 条 check） | 修表不修工具；如需修正通知 Jason.Yu（R3 硬规则 1） |
| 生成器静默失败（insert 未落但 exit 0） | 主入口以 arxml mtime + 容器 DEF 锚点（DemEventParameter / DemDTC）做内容兜底 |
| BSW headless 生成失败 | 主入口降级 Cobra.exe；仍失败则停止并排查 `_log` |
| 既有手工 patch 被重生成覆盖 | 重生成后按 patch 标记（如 PduR `RXPATCH`）检索重放（R4 §1.4） |

---

## 六、 验证、测试与集成要求 (Verification & Integration)

### 6.1 资源消耗与性能基线

纯配置数据增长（事件行 +357），ROM 增量随事件/DTC 数线性，无新增 RAM 缓冲、无动态内存。

### 6.2 验收标准 (Acceptance Criteria)

1. Dem 生成源码编译通过（J6 preset，零警告）——**注**：整机 `J6_MCU_DEBUG.elf` 链接失败于 `Os_Entry_Pps_Icu2Isr` 未定义 + `__dso_handle` 未定义，经 A/B 确认属 IDC510-6471 遗留缺陷（clean develop 同样失败），与本单 Dem 配置无关（见附录C #5）；本单按「Dem 源编译通过即提交、台架验证待阻塞项修复后补」推进。
2. 生成 arxml 事件数与 V0.3 表一致：118 个 `Reserved_31..148` 已消失，功能安全 SER 事件已进入 Dem 配置
3. 既有事件 DTC/UDS 映射无回归（对照 V0.2 生成物，仅新增/占位替换）
4. zos_msg 已上传 V0.3 xlsx（与 mcu 导入配套）
5. 台架：编译固件刷写后可读 DTC/Dem 事件状态正常（用户手动验证）
6. 生成产物**不含 DemGeneral 段变更**：13.10 committed 工具无 `gen_dem_general`（无该目录、`dem_autogen_etas.py` 无 FEATURES 项、`common.yaml`/`sxt_a.yaml` 均不含该键），启用功能仅 `gen_dem_table -> gen_fim_code`

---

## 附录A：需求追溯矩阵

| 需求条目 | 设计章节 | 代码落点 |
| :--- | :--- | :--- |
| 导入 V0.3 EVM 表（新增功能安全 DTC） | §2.1 / §3.1 | cpj_smartxtruck Dem 生成物（§4.1 #3~#6） |
| 表上传 zos_msg | §4.1 #7 | zos_msg Gen_evm_dem_Script |

## 附录B：设计决策记录 (ADR 摘要)

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | 用主入口 Dem_AutoGen + 新增 sxt_a.yaml | 沿用旧 `gen_e2e_dem.bat` | R4 §3 禁用旧 bat（无 ISOLAR BSW 重生成）；新增 sxt_a.yaml 保持 jumpdown/jumpup=true 与 V0.2 一致 |
| 2 | sxt_a.yaml 仅设 jumpdown/jumpup，不涉 gen_dem_general | 继承 common 的 gen_dem_general | 13.10 生成机工具为 committed 版（无 gen_dem_general）；本单不改 DemGeneral 容器 |
| 3 | 删旧 V0.2 表、仅留 V0.3 | 并存两版 | 主入口 `discover_excel` 按前缀唯一匹配，同目录多表会歧义；旧 bat 的 pick_latest 逻辑同理 |
| 4 | RCore_Event 表名按前缀自动识别（改工具） | 改表把 d510 重命名为 d310 / 传配置参数 | `d510` 为 D118 正确平台标识，改表会污染释放问卷（违 R3「修表不修工具」本义）；按前缀识别对 d310 项目零影响，且无需新增配置 |
| 5 | evm_cfg（FidCfg/iSysFidCfg/fimcfg）不纳入本单提交 | 提交 gen_fim_code 重生成的三文件 | 实测 committed evm_cfg 为**陈旧基线**（`EvmCfg_Max_Number_Event_cu16=1107`、35 个 FID 组），早于 V0.2；V0.2（IDC510-6178）与 IDC510-6514 两次先例均未改动 evm_cfg。重生成会引入 1107→1800 事件、35→1 组的大幅漂移（FiMFID sheet V0.2/V0.3 均为 1 条未变），属历史漂移刷新而非本单表变更，风险与范围均超出 DTC 导入，故本单不动 evm_cfg，仅记录待另行评估（附录C #4） |

## 附录C：开放问题 (Open Issues)

| # | 问题描述 | 影响 | 状态 |
| :--- | :--- | :--- | :--- |
| 1 | map.yaml（dtc/event/fimfid）是否随 mcu 提交 | 影响提交范围 | 待确认（先例 F4CMC-70 同步，默认同步） |
| 2 | zos_msg 现有 `D118_V1.0_20260727.xlsx` 版本号与 V0.x 序列不一致 | 上传时删除/覆盖策略 | 按「删旧加新」上传 V0.3，删除 V1.0（待生成时核对 zos 侧引用） |
| 3 | `gen_event_ctrl` 子工具仍硬编码 `RCore_Event_d310`（本单 `gen_event_ctrl=false` 未触发） | 后续若启用 `gen_event_ctrl` 会失败 | 已知，暂不改（本单不启用）；后续启用时按同法按前缀识别 |
| 4 | committed `evm_cfg` 基线陈旧（1107 事件/35 FID 组，早于 V0.2），与 Dem 表长期不一致 | evm_cfg 侧 FID 上报映射可能与当前事件集不符 | 待评估：需确认 EVM FID 上报功能是否实际启用、是否需按 V0.3 刷新 evm_cfg（涉及 1107→1800 事件、35→1 组的大改，另行立项核对） |
| 5 | **sxt_a develop 构建链接失败（阻塞台架验证）**：`Os_Entry_Pps_Icu2Isr` 未定义（`os/gen/Os_Cfg.c` 向量表仅引用无定义）+ `__dso_handle` 未定义（`time_sync/sxt_a/.../time_sync_runnable_customer.cpp` 的 C++ 全局 `g_ins_timeSyncRtc` 静态构造，链接用 `-nostartfiles` 排除 crt） | 整机 `J6_MCU_DEBUG.elf` 无法链接，无法刷写台架 | **已 A/B 确认属 IDC510-6471（`6e5d2b9ea` regenerate RTA-OS with Pps_Icu2Isr）遗留缺陷，与 Dem 导入无关**（clean develop 同样失败）。本单按「Dem 源编译通过即提交、台架验证待阻塞项修复后补」推进；需另开单由 IDC510-6471 owner 修复（补 `Os_Entry_Pps_Icu2Isr` 定义 + 处理 C++ 全局 `__dso_handle`） |
