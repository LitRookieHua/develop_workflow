# ⚙️ T1JFL3 E2E DTC Import V0.8 需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | T1JFL3 Dem/FiM DTC 表导入（E2E V0.8） | **所属软件层级** | BSW (Dem / FiM / E2E) |
| **文档状态** | 🟡 待评审 | **安全与质量要求** | 零警告编译 |
| **模块负责人 / 作者** | Hua.Yao / Claude | **关联输入/输出** | 📊 `IDC_EVM_Config_Chery_D100_T1JFL3_V0.8.xlsx` ｜ 📑 [D100-1072](https://jira.imotion.ai:7070/browse/D100-1072) / [D1CYC-2353](https://jira.imotion.ai:7070/browse/D1CYC-2353) |

> **📝 变更记录**
> * `2026-10-21`｜Hua.Yao｜V1.0｜T1JFL3 E2E V0.8 导入设计（摄像头内参 CRC 校验故障 mapping 更新）

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景**：客户侧（D100-1071）于 2026-10-21 释放 T1JFL3 诊断问卷 V0.8（`IDC_EVM_Config_Chery_D100_T1JFL3_V0.8.xlsx`），需求单 D100-1072 要求导入。历次导入：V0.4→D1CYC-67、V0.5→D1CYC-278、V0.7→D1CYC-926。
* **核心目标**：将 V0.8 问卷导入 `mcu_app_tda4` 仓库 `cpj_chery/veh_t1jfl3`，使 Dem（Event↔DTC mapping）与 FiM（Event↔FiMFID mapping）生成物与 V0.8 问卷一致。
* **设计原则**：纯 Excel→生成物导入，不手写业务逻辑；生成流程走 `tools/autosar_gen/Dem_AutoGen`（统一入口）。

### 1.2 适用范围 (Scope)

* **适用控制器/平台**：JETOUR T1J FL3（TDA4 平台，`cpj_chery/veh_t1jfl3`，microsar_cfg/d100a）
* **核心职责**：4 个摄像头内参生产数据 CRC 校验事件补齐 DTC 映射与 FiMFID 关联
* **范围边界**：RCore_Event_d100a / CPJ_Event_Net / FiMFID 三个 sheet 与 V0.7 完全一致，无变化；不涉及任何手写代码修改（除非编译暴露生成物与手写代码不一致，如 V0.7 曾需修 NetCom_Callout）

### 1.3 术语与缩略语

| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| E2E | End-to-End | 端到端通信保护（CRC/RC/Timeout 等校验事件） |
| EVM | Event Management | 诊断问卷（Event/DTC/FiMFID 配置表） |
| FiM | Fault Injection Manager | 故障管理，Event→FiMFID 功能降级 |
| IBS | In-Box Sensor（摄像头模组） | 内参 CRC 校验事件来源 |

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | [D100-1072 T1JFL3 E2E DTC Import V0.8](https://jira.imotion.ai:7070/browse/D100-1072) | — | 需求来源 |
| R2 | [D100-1071 E2E版本释放](https://jira.imotion.ai:7070/browse/D100-1071) | V0.8 | 诊断问卷附件 |
| R3 | [D1CYC-926 T1JFL3 update dtc table v0.7](https://jira.imotion.ai:7070/browse/D1CYC-926) | — | 上一版导入先例 |

### 1.5 设计约束与假设

* **技术约束**：生成工具 `Dem_AutoGen_Davinci`（Vector 链路）需要 CodeMeter license（USB over Network）；Dem arxml 生成经 DaVinci `DVCfgCmd`。代码写入一律 SSH 到服务器 10.0.12.42。
* **外部假设**：V0.8 问卷已完成评审（D100-1071 Released）；4 个 DTC 编号（5DC146/5DC246/5DC346/5DC446）与既有 OpDataCRC 事件共用，无需新增 DTC 存储块。
* **假设的验证方式**：`check_dtc_table` 前置校验 + 生成后 diff + 编译 + 台架手动验证。

---

## 二、 架构设计与模块间交互

> 本需求为纯配置数据导入，无新增运行时交互。

**数据流**：V0.8 xlsx →（Dem_AutoGen 统一入口）→ PF_Event + RCore_Event_d100a + CPJ_Event_Net 合并 → Dem arxml（DaVinci 生成 `Dem_Lcfg.c/h` 等）+ FiM 代码（`evm_cfg/src/_gen/`、`zx_sys_evm_cfg_fimcfg.hpp`）→ map yaml。

**V0.8 实际变更**（V0.7 vs V0.8 逐 cell 对比，仅 PF_Event sheet 4 行）：

| 事件（Dem Index 9-12） | 变更内容 |
| :--- | :--- |
| `DemEvent_IBS_TvCamEEPROMFront_ProductionParamCRCError` | DTC：N.A→`5DC146`（`DemDTC_C1DC146_TvCamFront_ParamGetError`）；新增 FiMFID 关联：`FiMFID_HMICAM_IsTvCamFrontFault`、`FiMFID_VehCom_IsAPAFault_Internal`、`FiMFID_VehCom_IsRAFault_Internal`、`FiMFID_VehCom_IsRPAFault_Internal`；补勾选（col10/28/29/32/105） |
| `DemEvent_IBS_TvCamEEPROMRear_ProductionParamCRCError` | 同上模式，DTC `5DC246`，`FiMFID_HMICAM_IsTvCamRearFault`，col106 |
| `DemEvent_IBS_TvCamEEPROMLeft_ProductionParamCRCError` | 同上模式，DTC `5DC346`，`FiMFID_HMICAM_IsTvCamLeftFault`，col107 |
| `DemEvent_IBS_TvCamEEPROMRight_ProductionParamCRCError` | 同上模式，DTC `5DC446`，`FiMFID_HMICAM_IsTvCamRightFault`，col108 |

注：DTC 编号与同摄像头 EEPROM 工作数据 CRC 事件（OpDataCRC，Dem Index 3-6）共用同一 DTC——同一故障表现（摄像头参数读取错误），不同触发源。

---

## 三、 BSW 模块影响分析与修改点清单

### 3.1 BSW 模块影响

| 模块 | 影响 | 说明 |
| :--- | :--- | :--- |
| **Dem**（`microsar_cfg/d100a`） | Event↔DTC mapping 变更 | 4 个 ProductionParamCRC 事件从无 DTC 变为有 DTC；影响 `StartApplication_Dem_Dem_ecuc.arxml`、`Dem_swc.arxml`、`FlatExtract.arxml`、`StartApplication_Rte_Rte_ecuc.arxml`（Rte 端口映射随事件集变化）、`src/GenData/Dem_Lcfg.c/h` |
| **FiM**（`evm_cfg`） | Event↔FiMFID mapping 变更 | 4 个事件新增 4×4 FiMFID 关联；影响 `evm_cfg/src/_gen/evm_cfg_iSysFidCfg.cpp`；`evm_cfg_FidCfg.hpp` 的 `EvmCfg_Max_Number_EventToMixedFID_Group_cu16` 可能需要扩容（V2xeu v1.0.7 先例 60→67），以生成结果为准 |
| **NvM** | 无新增块 | DTC 均复用既有存储（与 OpDataCRC 共用），无 NvM 改动 |
| **Dcm** | 间接 | 190A 读取结果随 Dem mapping 变化（4 个事件可上报 DTC），无 Dcm 配置改动 |

### 3.2 修改点清单（文件级）

| # | 文件 | 修改方式 |
| :--- | :--- | :--- |
| 1 | `cpj_chery/veh_t1jfl3/tools/Evm_Script/IDC_EVM_Config_Chery_D100_T1JFL3_V0.8.xlsx`（新增，删除 V0.7 xlsx） | 直接导入 |
| 2 | `cpj_chery/veh_t1jfl3/microsar_cfg/d100a/build/SipAddon/Config/ECUC/StartApplication_Dem_Dem_ecuc.arxml` | DaVinci 生成 |
| 3 | `cpj_chery/veh_t1jfl3/microsar_cfg/d100a/build/SipAddon/Config/ECUC/StartApplication_Rte_Rte_ecuc.arxml` | DaVinci 生成 |
| 4 | `cpj_chery/veh_t1jfl3/microsar_cfg/d100a/build/SipAddon/Config/ServiceComponents/Dem_swc.arxml` | DaVinci 生成 |
| 5 | `cpj_chery/veh_t1jfl3/microsar_cfg/d100a/build/SipAddon/Config/System/FlatExtract.arxml` | DaVinci 生成 |
| 6 | `cpj_chery/veh_t1jfl3/microsar_cfg/d100a/src/GenData/Dem_Lcfg.c / Dem_Lcfg.h` | DaVinci 生成 |
| 7 | `cpj_chery/veh_t1jfl3/evm_cfg/src/_gen/evm_cfg_iSysFidCfg.cpp`（及 `evm_cfg_FidCfg.hpp` 如需扩容） | FiM 生成 |
| 8 | `Evm_Script/Evm_Config_Excel_To_Csv/` 下 map 产物（dtc_map/event_map yaml） | gen_map_yaml |

### 3.3 分支与仓库

* 仓库：仅 `mcu_app_tda4`（TDA4 老工作区 `01_Workspace_TDA4`；V0.7 先例 zos_msg 无改动）
* 分支：`develop` + `Chery/T1JFL3_D100/T940`；develop 先做，T940 cherry-pick（V0.7 先例 `feature/D1CYC-926-t1jfl3-update-dtc-table-v0.7-t940` 同模式）
* feature 分支命名：`feature/D1CYC-2353-t1jfl3-update-dtc-table-v0.8`（+ `-t940`）

---

## 四、 验证方案

1. **前置校验**：`check_dtc_table`（Dem_AutoGen 步骤 1）通过
2. **生成后核对**：diff 生成物，确认仅 4 个事件的 DTC/FiMFID mapping 变化（对照 §二 变更表）
3. **编译**：SSH imobuilder 编译通过（develop + T940，零新增警告）
4. **台架手动验证**：用户台架确认——触发摄像头内参 CRC 故障后 190A 可读取到对应 DTC（5DC146/5DC246/5DC346/5DC446），FiM 降级行为符合 V0.8 问卷

### 验收标准（从 D100-1072 提取）

- 导入 T1JFL3 项目的 E2E V0.8 版本（详见 D100-1071）
- 导入内容包含：Event 结构体、Event 和 DTC 的 mapping、Event 和 FiMFID 的 mapping 等
- 4 个摄像头内参 CRC 校验事件按 V0.8 问卷完成 DTC 与 FiMFID mapping（History：更新摄像头内参CRC校验故障mapping）

---

## 附录B：设计决策记录 (ADR 摘要)

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | 全流程重跑 Dem+FiM 生成（不只改 FiM） | 仅 FiM（参照 V2xeu v1.0.7 首轮 `No_AutosarGen`） | 本次含 DTC 映射变更（4 事件补 DTC），Dem arxml 必须重新生成 |
| 2 | D1CYC fixVersion 取 T480v1.0 | C011（V0.7 先例） | jira-story-params.json D1CYC 节固定值（用户确认） |

## 附录C：开放问题

| # | 问题描述 | 影响 | 责任方 | 跟踪截止时间 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `EvmCfg_Max_Number_EventToMixedFID_Group_cu16` 是否需要扩容 | FiM 生成物正确性 | 开发（以生成结果为准） | 2026-10-28 |
