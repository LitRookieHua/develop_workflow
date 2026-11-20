# ⚙️ RX Dem 快照 DID 与扩展数据记录配置（CMCRXJ6B-42/43）需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | Dem 环境数据配置：故障快照 DID 集与扩展数据记录 | **所属软件层级** | AUTOSAR BSW（Dem，DEXT 配置层） |
| **文档状态** | 🟡 待评审 | **安全与质量要求** | MISRA C:2012 ｜ 零警告 |
| **模块负责人 / 作者** | Hua.Yao / Claude（配置修改：用户本人） | **关联输入/输出** | 📑 [CMCRXJ6B-42](https://jira.imotion.ai:7070/browse/CMCRXJ6B-42) / [43](https://jira.imotion.ai:7070/browse/CMCRXJ6B-43) ｜ 🐞 [F4CMC-100](https://jira.imotion.ai:7070/browse/F4CMC-100) / [101](https://jira.imotion.ai:7070/browse/F4CMC-101) |

> **📝 变更记录**
> * `2026-11-18`｜Hua.Yao / Claude｜V1.0｜初版：快照 DID 集 GAC 遗留替换 + 扩展数据补 Aged counter（根因定性复用 F4CMC-105 分析结论）
> * `2026-11-19`｜Hua.Yao / Claude｜V2.0｜需求修订重做（round-3）：逐事件字段全部改固定值（EventPriority/Count/ErrorName/SystemState/Aged counter=0x00、SoftwareVer="V1.0 "）；温度编码改 (t+50)×100；快照收敛单记录（记录号 0x01）、扩展数据收敛单记录 0x01（3 计数器各 1 B）；实现路径改 EcucValues 脚本修改 + ISOLAR 重生成 + evm 常量 SR 回调（round-1 内部元素方案被 ETAS 校验禁止，round-2 钩子方案因需求固定值化作废）

> 本需求为 DEXT 配置层小改动（无应用代码逻辑），按模板精简规则省略部分详细设计小节，追溯见 JIRA。

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景**：RX (CMC_RX_J6B) 实车测试（版本包 21180）暴露 Dem 环境数据配置为 GAC 遗留——0x19 快照读出的 DID 集为 0x0500/0x9A5D（GAC 项目遗留），扩展数据仅 2 记录（缺 Aged counter）。F4CMC-105 分析已定性为 DEXT 配置层问题并转出（问题单 F4CMC-100/101，当时约定由需求创建人手动改，未落地）。
* **核心目标**：
  * **CMCRXJ6B-42（快照）**：Snapshot Record 01/FF 的 DID 集改为 0x15A0 / 0x0601 / 0x15A2（EventPriority、Date&ODO、故障快照状态信息）
  * **CMCRXJ6B-43（扩展数据）**：0x19 06 扩展数据改为 3 计数器——Fault Occurance Counter / Aging counter / Aged counter（Record 0x01/0xFF）
* **设计原则**：仅 Dem 环境数据配置（DEXT + 重生成产物），不动 Dem 应用代码、不动 Dcm、不动 NVM 块结构。

### 1.2 适用范围 (Scope)

* **适用控制器/平台**：CMC_RX_J6B 一体机（J6 平台，仓库 `mcu_app_j6` / `cpj_cmc`，M 核诊断）
* **范围边界**：仅 `cpj_cmc/autosar/rx/BswRta` 下 Dem 环境数据 DEXT 配置及其生成物；不涉及 Dcm 配置、Dem 业务代码、其他项目变体。

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | [CMCRXJ6B-42 Snapshot Data List](https://jira.imotion.ai:7070/browse/CMCRXJ6B-42) | — | 快照 DID 表（信号与字节映射原文） |
| R2 | [CMCRXJ6B-43 Extended Data List](https://jira.imotion.ai:7070/browse/CMCRXJ6B-43) | — | 扩展数据 3 计数器定义 |
| R3 | [F4CMC-105 分析报告](../analysis/2026-11-17-F4CMC-105-cmc-rx-prog-session-seca-dem-fixes.md) | V1.1 | 根因定性（DEXT GAC 遗留）与验证环境 |
| R4 | ISO 14229-1 (UDS) | 2020 | 0x19 02/04/06 语义、RecordNumber 0x01/0xFF |

### 1.5 设计约束与假设

* **流程约束**：代码修改由**用户本人手动执行**；本工作流负责立项/环境/定位/验证/合流。若走 DEXT 工具链重生成，autosar 生成环境为 10.0.13.10（[autosar-code-generation.md](../../.claude/references/autosar-code-generation.md)）；若直接手改生成文件，必须加 `<{项目名}PATCH P{id}>` 标记防生成覆盖。
* **外部假设**：0x15A2 内各信号（AMB_TEMP_MET、VEH_SPEED_S_PR、MTR_ENG_On_Time、ENGINE_STATUS 等）已由 Com → NetCom 链路可用；SoftwareVer 取 DID 0xF181 同源数据。

---

## 二、 架构设计与模块间交互 (Architecture & Interaction)

### 2.1 调用链（读路径，全部既有）

```text
Tester: 19 02/04 <DTC> <SnapshotRecordNumber>  → Dcm → Dem_ReturnGetFrozenFrame（快照 DID 集合序列化）
Tester: 19 06 <DTC> <ExtendedDataRecordNumber> → Dcm → Dem 扩展数据记录序列化
配置数据来源：DEXT（RTA_BIP_DEXT_v86.arxml）→ 生成 Dem_Cfg_Env*.h → Dem 运行时按 DTC 关联存储/读取
```

### 2.2 需求映射（R1/R2 修订版，2026-11-19 用户修订 JIRA 后原样整理）

**快照（CMCRXJ6B-42，单记录：记录号 0x01，0xFF 读同一条）**：

| DID | 名称 | Size | 内容（修订版） |
| :--- | :--- | :--- | :--- |
| 0x15A0 | Event Priority | 1 B | **固定 0x00** |
| 0x0601 | Date and ODO | 6 B | ODO_SCALE（bit0，0x0:Km / 0x1:Mile，0x154）、ODO（byte1~3，实时）、**Count（byte4~5，固定 0x0000）** |
| 0x15A2 | 故障快照状态信息 | 20 B | EcuTemperature×2（NTC CH2/CH3，**编码 (t+50)×100，恰好填满 0~65535**）、OutSideTemperature（0x311 AMB_TEMP_MET，offset -40，无效 0xFF）、VehicleSpeed（0x328 VEH_SPEED_S_PR，0.02 km/h/bit，无效 0xFFFF）、SystemRunTime（0x34E MTR_ENG_On_Time，0~86399 s，无效 0xFFFFFF）、Battery Voltage（KL30 采样，0.1 V/bit）、**Error Name(Code)（固定 0x0000）**、**SystemState（固定 0x00）**、Engine Status（0x101 ENGINE_STATUS，0~3）、**SoftwareVer（固定 "V1.0 "，5 字符含尾空格）** |

**扩展数据（CMCRXJ6B-43，单记录 0x01 共 3 B：occ + aging + aged 各 1 B）**：

| 元素 | 名称 | 语义（修订版） |
| :--- | :--- | :--- |
| 1 | Fault Occurance Counter | 自上次清 DTC 以来故障发生次数（Dem 内部 OCCCTR，实时） |
| 2 | Aging counter | 老化计数（Dem 内部 AGINGCTR_UPCNT，实时） |
| 3 | Aged counter | **固定 0x00**（ aged 规则下一版 EVM 导入表格定义） |

> 0xFF 语义：遍历该 DTC 的所有快照/扩展数据记录（既有机制，配置层不变）。

### 2.3 BSW 模块影响分析

| 模块 | 影响点 | 变化 |
| :--- | :--- | :--- |
| Dem | 环境数据配置（DEXT snapshot DID class / extended data records） | 快照 DID 集 0x0500/0x9A5D → **0x15A0/0x0601/0x15A2**；扩展数据 2 记录 → **3 计数器（补 Aged counter）** |
| Dem（生成物） | `Dem_Cfg_EnvDid.h` / `Dem_Cfg_EnvDataElement*.h` / `Dem_Cfg_EnvFreezeFrame.h` / `Dem_Cfg_EnvFFRecNumeration.h` / `Dem_Cfg_EnvExtendedData*.h` / `Dem_Cfg_EnvMain.h` | 随 DEXT 重生成 |
| 其余模块 | Dcm / Nvm / PduR | 不涉及（NVM 存储容量按既有 0x15A2 20B 上限评估，无块结构变化） |

### 2.4 并发与调度上下文

纯配置变化，不引入新的运行时上下文；快照/扩展数据的存储与读取路径沿用 Dem 既有机制。

---

## 三、 核心逻辑设计

### 3.1 修改方式

**实际路径（round-3 落地）**：脚本修改 `J6B_Dem_EcucValues.arxml`（Dem 模块配置值）→ 本地 D: ISOLAR headless 重生成（Dem_AutoGen.py --repo <mcu_app_j6> --config rx）→ 仅 Dem 相关生成物 + 手写文件 scp 推 12.42（D: 树 CRLF，推送前统一转 LF）→ 编译刷板。

**关键约束（round-1 教训）**：ETAS 校验禁止快照 DID 引用内部数据元素（DEM_DTC_PRIORITY 等）——因此 0x15A0/Count/ErrorName 等固定值字段全部走**外部 SR 回调**（常量函数，函数名由容器 SHORT-NAME 派生为 `Dcm_DemGetSRData_<容器名>`，arxml 无需回调名参数）；扩展数据记录内允许内部元素（OCCCTR/AGINGCTR_UPCNT）。

**已废弃方案**：round-1 DID 引内部元素（ETAS 校验拒绝）；round-2 逐事件真值钩子 + DTC→(eventId,priority) 映射表（需求改固定值后无必要）。

### 3.2 修改点清单（附录，round-3 实际）

| # | 文件/位置 | 修改 |
| :--- | :--- | :--- |
| 1 | `cpj_cmc/autosar/rx/BswRta/ecu_config/bsw/gen/J6B_Dem_EcucValues.arxml` | 新增外部 SR 元素 SR_Event_Priority(UINT8)/SR_ODO_Count(UINT16)/SR_Error_Name(UINT16)；DemDidClass_0x15A0（id 5536=0x15A0）改引 SR_Event_Priority 并入 TypeB/TypeA 快照 DID 集；0x0601 追加 ODO_Count、0x15A2 在 Battery 后插 Error_Name；快照收敛单记录（删 Rec_SnapshotRec_2，DemMaxNumberFreezeFrameRecords 76 处 2→1）；扩展数据收敛记录 0x01（occ+aging+aged 三元素），删记录 0x02~0x05 及内部元素 Event_Priority/Event_Id |
| 2 | `cpj_cmc/autosar/rx/BswRta/src/bsw/Dem/`（生成物） | 随 #1 ISOLAR 重生成（Dem_Cfg_Env*.h、env/*.c 等） |
| 3 | `cpj_cmc/autosar/rx/BswRta/integration/src/bsw/Dem/user/Dcm_Dem.h` | 追加 3 条 SR 回调 extern 声明 |
| 4 | `cpj_cmc/evm_cfg/var/src/vehicle/rx/evm_cfg_freezeframe_data.cpp` + 同名 hpp | 新增 3 个常量 SR 回调（Event_Priority/ODO_Count/Error_Name=0）；SW 版本改常量 "V1.0 "（删 McuVersion 依赖）；System_State/Aged counter 改常量 0；温度改 (t+50)×100 clamp 0~65535；删失效成员 m_System_State_u8/m_Software_Version_5b/m_Aged_Counter_u8 |

### 3.3 异常容错

配置层无新增失败路径；0x19 02/04/06 对不支持记录号的 NRC 行为沿用 Dem 既有实现（31）。

---

## 六、 验证方案

* DiagnosticTester（`configs/rx_mcu.json`，复用 F4CMC-105 验证环境）：
  1. 触发任一测试故障 → `19 02 <DTC> FF`：应答含 DID **0x15A0 / 0x0601 / 0x15A2**，且 0x0601 的 ODO_SCALE/ODO/Count 字节布局符合 R1；0x15A2 的 20 B 各字段按 §2.2 布局
  2. `19 04 <DTC> FF` 同样核对快照内容
  3. `19 06 <DTC> 01` / `19 06 <DTC> FF`：扩展数据 **3 计数器**（FaultOccurance / Aging / Aged），多次触发故障与老化后计数递增
  4. 回归：F4CMC-102/103 用例（seed 稳定性、attempt counter）不受影响
* J6 刷写后用户手动台架验证（阶段 4）。

## 附录B：ADR 摘要

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | DEXT 配置源 + 重生成（首选） | 手改生成文件 + patch 标记 | 工具链是权威路径；手改仅在工具链不可用时作等效降级，且必须 RXPATCH 标记 |
| 2 | 单分支单 PR 覆盖 F4CMC-100/101 | 两单各自分支 | 同一处 DEXT 配置改动同时满足两单，拆分无意义 |
| 3 | Record 0x01/0xFF 编号沿用需求定义 | 重排记录号 | 需求 R1/R2 明确 01/FF 语义，0xFF 遍历为既有机制 |
| 4 | 固定值字段走外部 SR 常量回调 | 内部数据元素 / 钩子+映射表 | ETAS 校验禁止快照 DID 引内部元素（round-1 死结）；需求修订后字段全固定，常量回调最简且无时序风险（round-2 钩子方案作废） |
| 5 | 快照/扩展数据各收敛单记录 0x01 | 多记录布局 | 2026-11-19 需求修订拍板：0xFF 读同一条；DemMaxNumberFreezeFrameRecords 2→1（生成 C 中该参数打包为单 bit，1/2 等价，arxml 以 1 为准） |
