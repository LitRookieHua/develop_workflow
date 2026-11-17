# ⚙️ T1JFL3 E2E DTC Import V0.9 需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | T1JFL3 Dem/FiM DTC 表导入（E2E V0.9） | **所属软件层级** | BSW (Dem / FiM / E2E) |
| **文档状态** | 🟡 待评审 | **安全与质量要求** | 零警告编译 |
| **模块负责人 / 作者** | Hua.Yao / Claude | **关联输入/输出** | 📊 `IDC_EVM_Config_Chery_D100_T1JFL3_V0.9.xlsx` ｜ 📑 [D100-1072](https://jira.imotion.ai:7070/browse/D100-1072) / [D1CYC-3335](https://jira.imotion.ai:7070/browse/D1CYC-3335) |

> **📝 变更记录**
> * `2026-11-10`｜Hua.Yao｜V1.0｜T1JFL3 E2E V0.9 导入设计（Dataloop 超时事件解绑 DTC）

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景**：客户侧（D100-1071）于 2026-11-09 释放 T1JFL3 诊断问卷 V0.9（`IDC_EVM_Config_Chery_D100_T1JFL3_V0.9.xlsx`），需求单 D100-1072 要求导入。历次导入：V0.4→D1CYC-67、V0.5→D1CYC-278、V0.7→D1CYC-926、V0.8→D1CYC-2353。
* **核心目标**：将 V0.9 问卷导入 `mcu_app_tda4` 仓库 `cpj_chery/veh_t1jfl3`，使 Dem（Event↔DTC mapping）与 FiM（Event↔FiMFID mapping）生成物与 V0.9 问卷一致。
* **设计原则**：纯 Excel→生成物导入，不手写业务逻辑；生成流程走 `tools/autosar_gen/Dem_AutoGen` 统一主入口（10.0.13.10 生成 → scp 12.42 → 编译 → 提交）。

### 1.2 适用范围 (Scope)

* **适用控制器/平台**：JETOUR T1J FL3（TDA4 平台，`cpj_chery/veh_t1jfl3`，microsar_cfg/d100a）
* **核心职责**：两个 Dataloop 监控事件解除 DTC 关联——`DemEvent_AppCrash_dataloop`（进程崩溃，另解除 FiMFID 关联）与 `DemEvent_AppComTimeout_dataloop`（进程间通讯超时）
* **范围边界**：RCore_Event_d100a / FiMFID 两个 sheet 与 V0.8 完全一致；CPJ_Event_Net 3 处变更（2 处空 DTC 补 N.A + 1 处事件名手误修正）均为上游对 V0.8 导入时已修正问题的吸收，无新功能；不涉及任何手写代码修改（除非编译暴露生成物与手写代码不一致）

### 1.3 术语与缩略语

| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| E2E | End-to-End | 端到端通信保护（CRC/RC/Timeout 等校验事件） |
| EVM | Event Management | 诊断问卷（Event/DTC/FiMFID 配置表） |
| FiM | Fault Injection Manager | 故障管理，Event→FiMFID 功能降级 |
| Dataloop | — | MCU 应用主数据环；超时由看门狗类事件 `DemEvent_AppCrash_dataloop` 上报 |

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | [D100-1072 T1JFL3 E2E DTC Import V0.9](https://jira.imotion.ai:7070/browse/D100-1072) | — | 需求来源 |
| R2 | [D100-1071 E2E版本释放](https://jira.imotion.ai:7070/browse/D100-1071) | V0.9 | 诊断问卷附件 |
| R3 | [D1CYC-2353 T1JFL3 update dtc table v0.8](https://jira.imotion.ai:7070/browse/D1CYC-2353) + [V0.8 设计](2026-10-21-D1CYC-2353-t1jfl3-e2e-dtc-import-v08-design.md) | — | 上一版导入先例 |
| R4 | `.claude/references/dtc-table-import.md` | — | DTC 表导入硬规则 |

### 1.5 设计约束与假设

* **技术约束**：生成工具 `Dem_AutoGen_Davinci`（Vector 链路）需 CodeMeter license（USB over Network）；Dem arxml 生成经 DaVinci `DVCfgCmd`。生成在 10.0.13.10，编译/commit 在 10.0.12.42（SSH）。
* **外部假设**：V0.9 问卷已释放（D100-1071，2026-11-09）；DTC `5DC553`（`DemDTC_C1DC553_ControllerFault_APP`）仍被其他约 23 个 AppCrash/ControllerFault 事件引用，DTC 定义与存储块保留，仅 dataloop 事件解除映射。
* **假设的验证方式**：`check_dtc_table` 前置校验 + 生成后 diff + 编译 + 台架手动验证。

---

## 二、 架构设计与模块间交互

> 本需求为纯配置数据导入，无新增运行时交互。

**数据流**：V0.9 xlsx →（Dem_AutoGen 统一入口）→ PF_Event + RCore_Event_d100a + CPJ_Event_Net 合并 → Dem arxml（DaVinci 生成 `Dem_Lcfg.c/h` 等）+ FiM 代码（`evm_cfg/src/_gen/`、`zx_sys_evm_cfg_fimcfg.hpp`）→ map yaml。

**V0.9 实际变更**（V0.8 vs V0.9 逐 cell 对比，PF_Event 2 行 + CPJ_Event_Net 3 处）：

| 变更 | 位置 | V0.8 | V0.9 |
| :--- | :--- | :--- | :--- |
| Dataloop 崩溃事件解绑 | PF_Event R289（Dem Index 287）`DemEvent_AppCrash_dataloop` | DTC `5DC553`/`DemDTC_C1DC553_ControllerFault_APP`；FiMFID：VehCom IsAPA/IsRA/IsRPAFault_Internal 等；col10/28/29/32 勾选 | DTC `N.A`；FiMFID 清空；勾选清空 |
| Dataloop 超时事件解绑 | PF_Event R304（Dem Index 302）`DemEvent_AppComTimeout_dataloop` | DTC `5DC553`/`DemDTC_C1DC553_ControllerFault_APP` | DTC `N.A` |
| 空 DTC 补 N.A | CPJ_Event_Net R50/R118（`TotalOdometer_km_OBDValidData_INVALID`、`ONEBOX_5_PilotParkBrkDecCtlAvl_INVALID`） | 空 | `N.A`（V0.8 导入时已本地修正，上游吸收） |
| 事件名修正 | CPJ_Event_Net R215 | `DemEvent_EV_CAN_VCU_11_GasPedalPositio_INVALID` | `...GasPedalPosition_INVALID`（同上，上游吸收） |

注：两个 dataloop 事件解绑后仍存在（无 DTC 事件），5DC553 继续由其余 AppCrash/AppComTimeout 事件上报。

---

## 三、 BSW 模块影响分析与修改点清单

### 3.1 BSW 模块影响

| 模块 | 影响 | 说明 |
| :--- | :--- | :--- |
| **Dem**（`microsar_cfg/d100a`） | Event↔DTC mapping 变更 | 两个 dataloop 事件从有 DTC 变为无 DTC；影响 `StartApplication_Dem_Dem_ecuc.arxml`、`Dem_swc.arxml`、`FlatExtract.arxml`、`StartApplication_Rte_Rte_ecuc.arxml`、`src/GenData/Dem_Lcfg.c/h`（`Dem_Cfg_CombinedEventIds[415]→[413]`）；DTC 5DC553 定义保留（其他事件仍用） |
| **FiM**（`evm_cfg`） | Event↔FiMFID mapping 变更 | `DemEvent_AppCrash_dataloop` 的 FiMFID 关联移除（`evmcfg_EventToMixedFidTable` 该行 6→0）；影响 `evm_cfg/src/_gen/evm_cfg_iSysFidCfg.cpp` |
| **NvM** | 无变更 | 5DC553 存储块保留（多事件共用） |
| **Dcm** | 间接 | 190A 读取结果随 Dem mapping 变化（dataloop 超时不再上报 5DC553），无 Dcm 配置改动 |
| **zos_msg** | xlsx 版本替换 | `Gen_evm_dem_Script/` V0.8→V0.9（硬规则：DTC 表导入必传 zos_msg，配套建 PR） |

### 3.2 修改点清单（文件级）

| # | 文件 | 修改方式 |
| :--- | :--- | :--- |
| 1 | `cpj_chery/veh_t1jfl3/tools/Evm_Script/IDC_EVM_Config_Chery_D100_T1JFL3_V0.9.xlsx`（新增，删除 V0.8 xlsx） | 直接导入 |
| 2 | `cpj_chery/veh_t1jfl3/microsar_cfg/d100a/build/SipAddon/Config/ECUC/StartApplication_Dem_Dem_ecuc.arxml` | DaVinci 生成 |
| 3 | `cpj_chery/veh_t1jfl3/microsar_cfg/d100a/build/SipAddon/Config/ECUC/StartApplication_Rte_Rte_ecuc.arxml` | DaVinci 生成 |
| 4 | `cpj_chery/veh_t1jfl3/microsar_cfg/d100a/build/SipAddon/Config/ServiceComponents/Dem_swc.arxml` | DaVinci 生成 |
| 5 | `cpj_chery/veh_t1jfl3/microsar_cfg/d100a/build/SipAddon/Config/System/FlatExtract.arxml` | DaVinci 生成 |
| 6 | `cpj_chery/veh_t1jfl3/microsar_cfg/d100a/src/GenData/Dem_Lcfg.c / Dem_Lcfg.h` | DaVinci 生成 |
| 7 | `cpj_chery/veh_t1jfl3/evm_cfg/src/_gen/evm_cfg_iSysFidCfg.cpp`（及 `evm_cfg_FidCfg.hpp` 如容量变化） | FiM 生成 |
| 8 | `Evm_Script/Evm_Config_Excel_To_Csv/` 下 map 产物（dtc_map/event_map yaml） | gen_map_yaml |
| 9 | zos_msg `Gen_evm_dem_Script/`（V0.8→V0.9 xlsx 替换，日期后缀命名） | 直接替换 |

### 3.3 分支与仓库

* 仓库：`mcu_app_tda4` + `zos_msg`（xlsx 上传，硬规则）
* 分支：`develop` + `Chery/T1JFL3_D100/T940`；develop 先做，T940 cherry-pick（V0.8 先例同模式）
* feature 分支命名：`feature/D1CYC-3335-t1jfl3-update-dtc-table-v0.9`（mcu，+ `-t940`）；zos_msg `feature/D1CYC-3335-evm-v0.9`（+ `-t940`）

---

## 四、 验证方案

1. **前置校验**：`check_dtc_table`（Dem_AutoGen 步骤 1）通过；FAIL 时修表不修工具，修正需飞书通知 Jason.Yu（本次预判无需修正——V0.9 已吸收 V0.8 两处修正）
2. **生成后核对**：diff 生成物，确认仅两个 dataloop 事件的 DTC/FiMFID mapping 变化 + R215 事件名修正（✅ 已核对：CSV 287/302 行、FiM 表 287 行 6→0、Dem_Lcfg.h CombinedEventIds 415→413、event_map.yaml 1514 事件名修正）
3. **编译**：SSH imobuilder 编译通过（develop，零新增警告；T940 cherry-pick 后不重复编译，V0.8 先例）
4. **台架手动验证**：用户台架确认——触发 Dataloop 崩溃/超时后 190A **不再**读到对应事件导致的 5DC553 上报（其余 AppCrash/AppComTimeout 源的 5DC553 不受影响），FiM 降级不再由 dataloop 崩溃事件触发

### 验收标准（从 D100-1072 提取）

- 导入 T1JFL3 项目的 E2E V0.9 版本（详见 D100-1071）
- 导入内容包含：Event 结构体、Event 和 DTC 的 mapping、Event 和 FiMFID 的 mapping 等
- Dataloop 超时不再关联 DTC（History，2026.11.09）

---

## 附录B：设计决策记录 (ADR 摘要)

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | 全流程重跑 Dem+FiM 生成 | 仅改 FiM | 含 DTC 映射变更（dataloop 解绑），Dem arxml 必须重新生成 |
| 2 | DTC 5DC553 定义保留 | 一并删除 | 5DC553 仍被约 23 个 AppCrash/ControllerFault 事件引用（PF_Event 20 行 + RCore 3 行） |
| 3 | zos_msg 配套上传 xlsx 并建 PR | 仅改 mcu（V0.7 先例没传） | 硬规则 dtc-table-import.md #2：EVM_CFG_FILE_NAME 前缀从 zos_msg 自己仓库找 xlsx，不传则脱节（V0.8 起执行） |
| 4 | D1CYC fixVersion 取 T480v1.0 | — | jira-story-params.json D1CYC 节固定值 |

## 附录C：开放问题

| # | 问题描述 | 影响 | 责任方 | 跟踪截止时间 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `EvmCfg_Max_Number_EventToMixedFID_Group_cu16` 是否缩容 | FiM 生成物正确性 | 开发（以生成结果为准） | 2026-11-14 |
