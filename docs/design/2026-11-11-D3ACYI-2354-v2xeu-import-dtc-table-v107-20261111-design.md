# ⚙️ V2xeu DTC 表导入 V1.0.7_20261111 需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | V2XEU Dem/FiM DTC 表导入（V1.0.7_20261111） | **所属软件层级** | BSW (Dem / FiM / E2E) |
| **文档状态** | 🟢 已实现 | **安全与质量要求** | 零警告编译 |
| **模块负责人 / 作者** | Hua.Yao / Claude | **关联输入/输出** | 📊 `IDC_EVM_Config_Chery_D065_V2XEU_V1.0.7_20261111.xlsx` ｜ 📑 [D3ACYIREQ-32944](https://jira.imotion.ai:7070/browse/D3ACYIREQ-32944) / [D3ACYI-2354](https://jira.imotion.ai:7070/browse/D3ACYI-2354) |

> **📝 变更记录**
> * `2026-11-11`｜Hua.Yao｜V1.0｜V1.0.7_20261111 导入设计（4 个影像类事件新增 AEB/FCW FiMFID 关联）

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景**：客户侧 2026-11-11 释放 V2XEU 诊断问卷 V1.0.7_20261111 版（表内 History 版本号 1.0.8，作者安辉辉），需求单 D3ACYIREQ-32944 要求导入。版本链：V1.0.5 → V1.0.6_20260928（D3ACYI-1675）→ V1.0.7_20261013（D3ACYI-1803，含 AUTOSAR 补跑）→ 本次。
* **核心目标**：将 20261111 版问卷导入 `mcu_app_tda4` 仓库 `cpj_chery/veh_v2xeu`，使 FiM（Event↔FiMFID mapping）生成物与该版问卷一致。

### 1.2 适用范围 (Scope)

* **适用控制器/平台**：iCAR V2X EU（D065，TDA4 平台，`cpj_chery/veh_v2xeu`）
* **核心职责**：RCore_Event_d300e 4 个影像类 PerceptionError 事件新增 AEB/FCW FiMFID 关联
* **范围边界**：PF_Event / CPJ_Event_Net / FiMFID 三个 sheet 与 20261013 版完全一致；Dem Event↔DTC mapping 无变化

### 1.3 术语与缩略语

| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| EVM | Event Management | 诊断问卷（Event/DTC/FiMFID 配置表） |
| FiM | Fault Inhibition Manager | 故障管理，Event→FiMFID 功能降级 |
| RCore | — | Region Core 事件组（d300e 域控），本次变更所在 sheet |

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | [D3ACYIREQ-32944](https://jira.imotion.ai:7070/browse/D3ACYIREQ-32944) | — | 需求来源（v2xeu_E2E_20261111，报告人 Yaowei Hu/胡耀伟；原立项挂 32943，该单 Cancelled 后迁移） |
| R2 | [[V2xeu import dtc table v1.0.7 20261013]]（D3ACYI-1803） | — | 直接前版导入（含 v2xeu.yaml 全量生成确立） |
| R3 | `.claude/references/dtc-table-import.md` | — | DTC 表导入硬规则 |

### 1.5 设计约束与假设

* **技术约束**：生成走 `tools/autosar_gen/Dem_AutoGen` 统一入口，10.0.13.10 执行；编译在 10.0.12.42（SSH）
* **外部假设**：AEB/FCW 4 个 FiMFID 已存在于 FiMFID sheet（本次无变化），仅 Event 侧新增关联
* **假设的验证方式**：check_dtc_table 前置校验 + 生成后 diff + 编译 + 台架手动验证

---

## 二、 架构设计与模块间交互

> 本需求为纯配置数据导入，无新增运行时交互。

**数据流**：V1.0.7_20261111 xlsx →（Dem_AutoGen，config `v2xeu.yaml` 全开）→ PF_Event + RCore_Event_d300e + CPJ_Event_Net 合并 → Dem 生成物（PF_Event 无变化，预期 diff 仅 FiM 侧）+ FiM 代码（`evm_cfg/src/_gen/`）→ map yaml。

**20261111 vs 20261013 实际变更**（逐 cell diff，仅 RCore_Event_d300e 4 行 + History 新增 1 行）：

| 变更 | 位置 | 内容 |
| :--- | :--- | :--- |
| Freezed 新增 External FiMFID | RCore R285（DEM Index 284）`DemEvent_HB_PerceptionError_Image_Freezed` | 关联列新增 `FiMFID_VehCom_IsAEBFault_External` + `FiMFID_VehCom_IsFCWFault_External`，勾选列置 Y |
| Covered 新增 Internal FiMFID | RCore R286（DEM Index 285）`DemEvent_HB_PerceptionError_Image_Covered` | 关联列新增 `FiMFID_VehCom_IsAEBFault_Internal` + `FiMFID_VehCom_IsFCWFault_Internal`，勾选列置 Y |
| Blurred 新增 External FiMFID | RCore R287（DEM Index 286）`DemEvent_HB_PerceptionError_Image_Blurred` | 同 Freezed |
| Glare 新增 External FiMFID | RCore R288（DEM Index 287）`DemEvent_HB_PerceptionError_Image_Glare` | 同 Freezed |

History 新增：1.0.8｜安辉辉｜与表格变更完全对应。**注意**：每个影像事件的 FiMFID 关联数由 10 增至 12（External 组）/ 12（Internal 组），`evm_cfg_FidCfg.hpp` 的 `EvmCfg_Max_Number_EventToMixedFID_Group_cu16` 可能需随之增大（v1.0.7_20261013 先例：60→67），以生成后编译结果为准。

---

## 三、 BSW 模块影响分析与修改点清单

### 3.1 BSW 模块影响

| 模块 | 影响 | 说明 |
| :--- | :--- | :--- |
| **FiM**（`evm_cfg`） | Event↔FiMFID mapping 变更 | 4 个影像事件各新增 2 项 AEB/FCW 关联；影响 `evm_cfg/src/_gen/evm_cfg_iSysFidCfg.cpp`（FID 表重排/加长），可能影响 `evm_cfg_FidCfg.hpp` 容量常量 |
| **Dem** | 无 | PF_Event 无变化，Dem Event↔DTC mapping 不变；全量生成下 Dem 生成物预期 diff 为空或仅缓存类文件 |
| **NvM / Dcm** | 无 | 无 DTC 增删、无 DID 变化 |
| **zos_msg** | xlsx 版本替换 | `Gen_evm_dem_Script/` 20261013→20261111（硬规则：DTC 表导入必传 zos_msg） |

### 3.2 修改点清单（文件级）

| # | 文件 | 修改方式 |
| :--- | :--- | :--- |
| 1 | `cpj_chery/veh_v2xeu/tools/Evm_Script/IDC_EVM_Config_Chery_D065_V2XEU_V1.0.7_20261111.xlsx`（新增，删除 20261013 版） | 直接导入 |
| 2 | `evm_cfg/src/_gen/evm_cfg_iSysFidCfg.cpp` 等 FiM 生成物 | FiM 生成 |
| 3 | `evm_cfg/inc/evm_cfg/evm_cfg_FidCfg.hpp`（如容量常量需调） | 手工（生成器不改的 handwritten 常量） |
| 4 | `Evm_Script/Evm_Config_Excel_To_Csv/` 下 CSV 与 map yaml | gen_map_yaml |
| 5 | zos_msg `Gen_evm_dem_Script/`（20261013→20261111 替换） | 直接替换 |

> 以阶段 3 实际生成 diff 为准；Dem GenData 若无实质 diff 则不带入 commit。

### 3.3 分支与仓库

* 仓库：`mcu_app_tda4` + `zos_msg`
* 分支：`develop` + `release/Chery/V2XEU_D065/V460`；develop 先做，V460 cherry-pick（v1.0.7 先例同模式，冲突取 develop 侧——纯 Excel 生成物与分支无关）
* feature 分支命名：`feature/D3ACYI-2354-v2xeu-import-dtc-table-v107-20261111`（mcu，+`-v460`）；zos_msg `feature/D3ACYI-2354-evm-v107-20261111`（+`-v460`）

---

## 四、 验证方案

1. **前置校验**：`check_dtc_table`（Dem_AutoGen 步骤 1）通过；FAIL 时修表不修工具，修正需飞书通知表格作者安辉辉（经需求报告人胡耀伟转达）
2. **生成后核对**：diff 生成物，确认仅 FiM 侧 4 事件 mapping 变化；Dem 生成物无实质变化
3. **编译**：SSH imobuilder 编译通过（develop 与 V460 各一次，零新增警告；注意 V460 产品配置为 `Chery/V2XEU_D065/release/Chery_V2XEU_D065_V460`）
4. **台架手动验证**：用户台架确认——影像类 PerceptionError 事件触发后，FiM 对 AEB/FCW（External/Internal 对应组）降级动作生效

### 验收标准（从 D3ACYIREQ-32944 提取）

- 导入 v2xeu E2E 行车需求更新（V1.0.7_20261111 表，详见附件）
- 上传 develop 和 release/Chery/V2XEU_D065/V460 分支

---

## 附录B：设计决策记录 (ADR 摘要)

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | 全量生成（v2xeu.yaml 全开） | 仅 FiM 生成（v2xeu_No_AutosarGen.yaml） | v1.0.7_20261013 先例首轮仅 FiM 后补跑全量（2026-10-15），直接全量一次到位 |
| 2 | zos_msg 配套上传 xlsx 并建 PR | 仅改 mcu | 硬规则 dtc-table-import.md #2：EVM_CFG_FILE_NAME 前缀从 zos_msg 自己仓库找 xlsx |
| 3 | Story fixVersion 取 V2XEU_V470v1_1106~1120 | V2XEU_V460v1（jira-story-params 固定值） | 需求单 fixVersion V2XEU_V460v7_1010~1130 在 D3ACYI 项目不存在；D3ACYI 当前周期版本为 V470v1_1106~1120（覆盖今天），与 D3ACYI-1803「取当前周期版本」先例一致 |
| 4 | `EvmCfg_Max_Number_EventToMixedFID_Group_cu16` 不调整 | 容量常量 10→12 增大 | 实际生成后 hpp 未改动、编译通过——生成器按组内 FID 总数重新布局，未触碰该上限 |

## 附录C：开放问题

| # | 问题描述 | 影响 | 责任方 | 跟踪截止时间 |
| :--- | :--- | :--- | :--- | :--- |
| ~~1~~ | `EvmCfg_Max_Number_EventToMixedFID_Group_cu16` 是否需随每事件 FID 数 10→12 增大 | FiM 编译/运行正确性 | 开发（以生成+编译结果为准） | ~~2026-11-18~~ 已关闭（2026-11-11）：生成后 hpp 无 diff、编译通过，见 ADR #4 |
