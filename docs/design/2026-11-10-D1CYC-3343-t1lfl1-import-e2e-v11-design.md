# ⚙️ T1LFL1 E2E Import V1.1 需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | T1LFL1 Dem/FiM DTC 表导入（E2E V1.1） | **所属软件层级** | BSW (Dem / FiM / E2E) |
| **文档状态** | 🟡 待评审 | **安全与质量要求** | 零警告编译 |
| **模块负责人 / 作者** | Hua.Yao / Claude | **关联输入/输出** | 📊 `IDC_EVM_Config_Chery_D073_T1LFL1_V1.1.xlsx` ｜ 📑 [T1LFL1-463](https://jira.imotion.ai:7070/browse/T1LFL1-463) / [D1CYC-3343](https://jira.imotion.ai:7070/browse/D1CYC-3343) |

> **📝 变更记录**
> * `2026-11-10`｜Hua.Yao｜V1.0｜T1LFL1 E2E V1.1 导入设计（TvCamEEPROM 内参事件关联 DTC + Dataloop 事件解绑 DTC）

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景**：客户侧（T1LFL1-462）于 2026-11-09 释放 T1LFL1（D073，新架构）诊断问卷 V1.1（`IDC_EVM_Config_Chery_D073_T1LFL1_V1.1.xlsx`），需求单 T1LFL1-463 要求导入。版本历史：V0.4 导入（PDCU-33788，旧流程）→ V1.0（Reset 机制加入）→ V1.1（本次）。
* **核心目标**：将 V1.1 问卷导入 `mcu_app_tda4` 仓库 `cpj_chery/veh_t1lfl1`，使 Dem（Event↔DTC mapping）与 FiM（Event↔FiMFID mapping）生成物与 V1.1 问卷一致。
* **设计原则**：纯 Excel→生成物导入，不手写业务逻辑；生成流程走 `tools/autosar_gen/Dem_AutoGen` 统一主入口（10.0.13.10 生成 → scp 12.42 → 编译 → 提交）。

### 1.2 适用范围 (Scope)

* **适用控制器/平台**：JETOUR T1L FL1（TDA4 平台新架构，`cpj_chery/veh_t1lfl1`，Chery/T1LFL1_D073）
* **核心职责**：
  1. 4 个 TvCamEEPROM 内参 CRCError 事件关联 DTC（5B2046/5B2146/5B2246/5B2346）+ FiMFID 关联
  2. 2 个 Dataloop 监控事件解除 DTC 关联（`DemEvent_AppCrash_dataloop`、`DemEvent_AppComTimeout_dataloop`，原 DTC 5B2452）
* **范围边界**：RCore_Event_d100a / FiMFID 两个 sheet 与 V1.0 完全一致；CPJ_Event_Net 仅 1 处事件名重命名；不涉及任何手写代码修改（除非编译暴露生成物与手写代码不一致）

### 1.3 术语与缩略语

| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| E2E | End-to-End | 端到端通信保护（CRC/RC/Timeout 等校验事件） |
| EVM | Event Management | 诊断问卷（Event/DTC/FiMFID 配置表） |
| FiM | Fault Injection Manager | 故障管理，Event→FiMFID 功能降级 |
| TvCamEEPROM | 环视摄像头 EEPROM | 内参（ProductionParam）存于摄像头 EEPROM，CRCError 事件反映内参读取校验失败 |
| Dataloop | — | MCU 应用主数据环；崩溃/超时由看门狗类事件上报 |

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | [T1LFL1-463 E2E导入V1.1版本](https://jira.imotion.ai:7070/browse/T1LFL1-463) | — | 需求来源 |
| R2 | [T1LFL1-462 E2E版本释放](https://jira.imotion.ai:7070/browse/T1LFL1-462) | V1.1 | 诊断问卷附件（2026-11-09 释放） |
| R3 | [D1CYC-3335 T1JFL3 update dtc table v0.9](https://jira.imotion.ai:7070/browse/D1CYC-3335) + [V0.9 设计](2026-11-10-D1CYC-3335-t1jfl3-e2e-dtc-import-v09-design.md) | — | 同类导入先例（同日，同款 dataloop 解绑变更） |
| R4 | `.claude/references/dtc-table-import.md` | — | DTC 表导入硬规则 |

### 1.5 设计约束与假设

* **技术约束**：生成工具 `Dem_AutoGen_Davinci`（Vector 链路）需 CodeMeter license（USB over Network）；Dem arxml 生成经 DaVinci `DVCfgCmd`。生成在 10.0.13.10，编译/commit 在 10.0.12.42（SSH）。
* **外部假设**：V1.1 问卷已释放（T1LFL1-462，2026-11-09）；新 DTC 5B2046~5B2346（`DemDTC_C1B2xx46_TvCamxxx_ParamGetError`）与 5B2452 在 V1.1 导入后的引用情况以生成结果为准——5B2452 解绑后若无其他事件引用，其 DTC 定义与存储块是否保留由生成工具决定，生成后 diff 核对。
* **假设的验证方式**：`check_dtc_table` 前置校验 + 生成后 diff + 编译 + 台架手动验证。

---

## 二、 架构设计与模块间交互

> 本需求为纯配置数据导入，无新增运行时交互。

**数据流**：V1.1 xlsx →（Dem_AutoGen 统一入口）→ PF_Event + RCore_Event_d100a + CPJ_Event_Net 合并 → Dem arxml（DaVinci 生成 `Dem_Lcfg.c/h` 等）+ FiM 代码（`evm_cfg/src/_gen/`）→ map yaml。

**V1.1 实际变更**（V1.0 vs V1.1 逐 cell 对比，PF_Event 6 行 + CPJ_Event_Net 1 处）：

| 变更 | 位置 | V1.0 | V1.1 |
| :--- | :--- | :--- | :--- |
| TvCam Front 内参事件关联 DTC | PF_Event R11（Dem Index 9）`DemEvent_IBS_TvCamEEPROMFront_ProductionParamCRCError` | DTC `N.A`，无 FiMFID | DTC `5B2046`/`DemDTC_C1B2046_TvCamFront_ParamGetError`；FiMFID：HMICAM_IsTvCamFrontFault + VehCom IsAPA/IsRA/IsRPAFault_Internal；col8/10/28/29/32/105 勾选 |
| TvCam Rear 内参事件关联 DTC | PF_Event R12（Dem Index 10）`DemEvent_IBS_TvCamEEPROMRear_ProductionParamCRCError` | DTC `N.A`，无 FiMFID | DTC `5B2146`/`DemDTC_C1B2146_TvCamRear_ParamGetError`；FiMFID：HMICAM_IsTvCamRearFault + 同上 3 项；col8/10/28/29/32/106 勾选 |
| TvCam Left 内参事件关联 DTC | PF_Event R13（Dem Index 11）`DemEvent_IBS_TvCamEEPROMLeft_ProductionParamCRCError` | DTC `N.A`，无 FiMFID | DTC `5B2246`/`DemDTC_C1B2246_TvCamLeft_ParamGetError`；FiMFID：HMICAM_IsTvCamLeftFault + 同上 3 项；col8/10/28/29/32/107 勾选 |
| TvCam Right 内参事件关联 DTC | PF_Event R14（Dem Index 12）`DemEvent_IBS_TvCamEEPROMRight_ProductionParamCRCError` | DTC `N.A`，无 FiMFID | DTC `5B2346`/`DemDTC_C1B2346_TvCamRight_ParamGetError`；FiMFID：HMICAM_IsTvCamRightFault + 同上 3 项；col8/10/28/29/32/108 勾选 |
| Dataloop 崩溃事件解绑 | PF_Event R289（Dem Index 287）`DemEvent_AppCrash_dataloop` | DTC `5B2452`/`DemDTC_C1B2452_ControllerFault_APP` | DTC `N.A`（DTC Name 同步清空） |
| Dataloop 超时事件解绑 | PF_Event R304（Dem Index 302）`DemEvent_AppComTimeout_dataloop` | DTC `5B2452`；col8 勾选 | DTC `N.A`（DTC Name 清空）；col8 勾选清空 |
| 事件名重命名 | CPJ_Event_Net R25（TCU） | `DemEvent_EV_CAN_TCU_2_7DCT_TO`（描述 TCU_2_7DCT(0x300) 连续丢失 500ms） | `DemEvent_EV_CAN_TCU_2_TO`（描述 TCU_2(0x300) 连续丢失 500ms） |

注：History 新增 1 行（1.1｜Jason｜dataloop 不关联 DTC + TvCamEEPROMxx 关联内参读取 DTC｜2026.11.09），与表格变更完全对应。

---

## 三、 BSW 模块影响分析与修改点清单

### 3.1 BSW 模块影响

| 模块 | 影响 | 说明 |
| :--- | :--- | :--- |
| **Dem**（`cpj_chery/veh_t1lfl1`） | Event↔DTC mapping 变更 | 4 个 TvCamEEPROM 事件从无 DTC 变为关联 5B20xx（新增 DTC 定义）；2 个 dataloop 事件解除 5B2452 关联；影响 Dem arxml（`Dem_ecuc.arxml` 等）、`Dem_Lcfg.c/h`（CombinedDTC/CombinedEventIds 数量随新增 DTC 变化）；5B2452 若无其他事件引用，生成后确认其定义保留情况 |
| **FiM**（`evm_cfg`） | Event↔FiMFID mapping 变更 | 4 个 TvCamEEPROM 事件新增 FiMFID 关联（各 4 项：HMICAM_IsTvCamXxxFault + VehCom IsAPA/IsRA/IsRPAFault_Internal）；影响 `evm_cfg/src/_gen/evm_cfg_iSysFidCfg.cpp` |
| **NvM** | 待生成确认 | 新 DTC 5B20xx 的存储块配置以生成结果为准 |
| **Dcm** | 间接 | 190A 读取结果随 Dem mapping 变化，无 Dcm 配置改动 |
| **zos_msg** | xlsx 版本替换 | `Gen_evm_dem_Script/` V1.0→V1.1（硬规则：DTC 表导入必传 zos_msg，配套建 PR） |

### 3.2 修改点清单（文件级）

| # | 文件 | 修改方式 |
| :--- | :--- | :--- |
| 1 | `cpj_chery/veh_t1lfl1/tools/Evm_Script/IDC_EVM_Config_Chery_D073_T1LFL1_V1.1.xlsx`（新增，删除 V1.0 xlsx） | 直接导入 |
| 2 | `cpj_chery/veh_t1lfl1` 下 Dem arxml（DaVinci 生成，以实际生成 diff 为准） | DaVinci 生成 |
| 3 | `cpj_chery/veh_t1lfl1` 下 `Dem_Lcfg.c/h` | DaVinci 生成 |
| 4 | `evm_cfg/src/_gen/` FiM 生成物（iSysFidCfg.cpp 等） | FiM 生成 |
| 5 | `Evm_Script/Evm_Config_Excel_To_Csv/` 下 map 产物（dtc_map/event_map yaml） | gen_map_yaml |
| 6 | zos_msg `Gen_evm_dem_Script/`（V1.0→V1.1 xlsx 替换，日期后缀命名） | 直接替换 |
| 7 | `cpj_chery/veh_t1lfl1/microsar_cfg/d100a/build/SipAddon/Config/ECUC/StartApplication_Dem_Dem_ecuc.arxml`：`DemOBDPermanentChronologyMaxNumberEvents` 补 `<VALUE>1</VALUE>`（对齐 t1jfl3） | 生成前置修复 |

> 具体生成物文件清单以阶段 3 实际生成 diff 为准（V1.0 先例中包含 RteCache/Rte_ecuc.arxml/FlatExtract.arxml 等）。

### 3.3 分支与仓库

* 仓库：`mcu_app_tda4` + `zos_msg`（xlsx 上传，硬规则）
* 分支：`develop` + `Chery/T1LFL1_D073/T480`；develop 先做，T480 cherry-pick（V0.9/T940 先例同模式）
* feature 分支命名：`feature/D1CYC-3343-t1lfl1-import-e2e-v1.1`（mcu，+ `-t480`）；zos_msg `feature/D1CYC-3343-evm-v1.1`（+ `-t480`）

---

## 四、 验证方案

1. **前置校验**：`check_dtc_table`（Dem_AutoGen 步骤 1）通过；FAIL 时修表不修工具，修正需飞书通知 Jason.Yu
2. **生成后核对**：diff 生成物，确认仅 6 个事件的 DTC/FiMFID mapping 变化 + CPJ R25 事件名重命名；5B2452 引用清零后其定义/存储块保留情况核对
3. **编译**：SSH imobuilder 编译通过（develop，零新增警告；T480 cherry-pick 后不重复编译，先例模式）
4. **台架手动验证**：用户台架确认——TvCamEEPROM 内参 CRCError 触发后 190A 读到对应 5B20xx DTC 且 FiM 降级动作生效；Dataloop 崩溃/超时后不再上报 5B2452

### 验收标准（从 T1LFL1-463 提取）

- 导入 T1L 项目的新架构 E2E V1.1 版本（详见 T1LFL1-462）
- 导入内容包含：Event 和 DTC 的 mapping、Event 和 FiMFID 的 mapping 等
- History 变更项落地：dataloop 不关联 DTC；TvCamEEPROMxx 关联内参读取 DTC（2026.11.09）

---

## 附录B：设计决策记录 (ADR 摘要)

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | 全流程重跑 Dem+FiM 生成 | 仅改 FiM | 同时含 DTC 新增（TvCam 4 事件）与解绑（dataloop 2 事件），Dem arxml 必须重新生成 |
| 2 | zos_msg 配套上传 xlsx 并建 PR | 仅改 mcu | 硬规则 dtc-table-import.md #2：EVM_CFG_FILE_NAME 前缀从 zos_msg 自己仓库找 xlsx，不传则脱节（V0.8 起执行） |
| 3 | D1CYC fixVersion 取 T480v1.0 | T430v1.0（需求单 fixVersion） | jira-story-params.json D1CYC 节固定值 T480v1.0；合入分支亦为 T480（用户指定），fixVersion 与合入分支对齐 |
| 4 | `DemOBDPermanentChronologyMaxNumberEvents` 补值 1 | 上报外部团队修源头 | 该参数在 t1lfl1 工程外部迁入时即缺 `<VALUE>`（git initial commit 基线已缺），DaVinci 校验 Cfg00022 拒绝启动 Dem 生成器；本环境首次对 t1lfl1 生成故暴露。取同平台 t1jfl3 同参数值 1 对齐，随本次导入一并提交 |

## 附录C：开放问题

| # | 问题描述 | 影响 | 责任方 | 跟踪截止时间 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | ~~5B2452 解绑后是否仍被其他事件引用；若无，DTC 定义与存储块是否随生成移除~~ **已关闭（2026-11-10，生成结果核实）**：解绑后无事件引用 5B2452，生成工具保留 DTC 定义与存储块（`DemDTC_C1B2452_ControllerFault_APP` 定义仍在，`Dem_Lcfg.c` 中 ControllerFault_APP 剩余引用均为 DTC 定义自身），不影响 Dem/NvM 生成物正确性 | Dem/NvM 生成物正确性 | 开发（以生成结果为准） | 2026-11-17 |
