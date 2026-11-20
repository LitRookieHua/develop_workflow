# ⚙️ RX A核故障码映射 V0.0.1 导入与 HCT IPC FaultMgr 三通道 需求与设计说明文档

| 文档属性 | 内容 | 文档属性 | 内容 |
| :--- | :--- | :--- | :--- |
| **工单号** | [F4CMC-109](https://jira.imotion.ai:7070/browse/F4CMC-109)（来源需求 [CMCRXJ6B-1403](https://jira.imotion.ai:7070/browse/CMCRXJ6B-1403)，reporter Jason.Yu） | **设计人 / 日期** | Hua.Yao / Claude / 2026-11-17 |
| **项目 / 变体** | CMC_RX_J6B（仓库 `cpj_cmc`，R核 MCU 诊断） | **版本** | V1.0 |
| **影响模块** | `dia_cfg/var/src/vehicle/rx/hct_ipc_diag/`（集成层，手工维护，非 DEXT 生成代码） | **关联输出** | 🔗 F4CMC-109 ｜ 📄 交互规范 [V0.0.1_20261117 附件](https://jira.imotion.ai:7070/secure/attachment/206847/) |

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

CMC_RX A_R 核交互规范 V0.0.1（20261116）定义了 R核（MCU）与 A核（HCT App）之间的故障诊断交互。需求两件事：

1. **导入「A核故障码」页签映射表**（FaultName / FaultID / DTC(hex) / Event Name，约 26 条有效映射）——A核通过 IPC 将故障码上报 R核，R核查表映射到 Dem 事件并置位/恢复
2. **实现「IPC 内容to Faultmgr」页签三个 IPC 通道**：1030 周期下发 / 0301 A核故障上报 / 1015 IDPS_EVENT

**范围收窄（2026-11-17 用户确认）**：本次只做 **A核上报 event 功能及其 IPC 通道（0301）**——即映射表导入 + 通道 2；通道 1/3 不在本次范围。

### 1.2 适用范围 (Scope)

- **范围内**：`hct_ipc_diag` 模块的映射表更新（`hct_ipc_table.cpp` HctEventTable 按 V0.0.1 全量替换）；通道 2（Ins3ch1）报文格式与 V0.0.1 符合性核对（现有逻辑不动，仅换表）
- **范围外**：通道 3（IDPS_EVENT）实现（等语义澄清后二次迭代）、通道 1 FiMFID 表刷新（见开放问题 #2）、Dem 配置层（DEXT）DTC 分配调整（见开放问题 #1）、A核侧实现

### 1.3 术语与缩略语

| 术语 | 说明 |
| :--- | :--- |
| A核 / R核 | HCT App（SOC Linux）/ MCU（本仓库固件） |
| FaultID | A核故障标识，module_id(2B) + event_id(2B)，如 0x41060001 |
| FiMFID | R核故障信息上报 A核的条目（module/event/status） |
| IDPS | 通道 1015 的事件上报业务（A核→R核事件结构体列表） |
| IPC | IpcAdpr 收发（`IpcAdpr_Send_Func` / RxCallback，instance+channel 寻址） |

### 1.4 参考文档

| 文档 | 说明 |
| :--- | :--- |
| CMC_RX ZX&HCT 故障诊断A_R核交互规范 V0.0.1_20261117.xlsx | A核故障码 / 故障码FiMFID / IPC 内容to Faultmgr 三页签（20261117 修订版，较 20261116 删除 SOC_TEMP_OVERLOAD 行） |
| `dia_cfg/var/src/vehicle/rx/hct_ipc_diag/` | 现有实现基线（2025-06 移植自 N60/AY7 同族） |
| [[N60 Change fault id map function]] | 同族先例（BAIC N60 fimid 页签导入） |

### 1.5 设计约束与假设

- 通道 1/2 的 IPC 头格式（ElementId/GroupId/Priority/Length/CRC16）、SubFunc 编码与 V0.0.1 一致，已由现有代码实现并与 A核联调过 SSH 通道验证——本设计不改协议格式
- A核上报 wire 载荷为 3 字节 DTC（High-Middle-Low）+ 1 字节 status（规范 A核故障码 页签头部说明）
- 事件置位策略（规范原文）：A核点火周期内故障置 1 发一次、恢复置 0 再发一次；R核收到置 1 后**一直保持**对应 event 置 1，直至收到置 0

## 二、 架构设计与模块间交互 (Architecture & Interaction)

### 2.1 模块依赖关系与调用链

```
A核(HCT App) --IPC(Ins3ch1)--> IpcAdpr_RxCallback_HCT_Event（通道2，已有）
   └─> HctIpcDiagManager::ipcRxCallbackUds ─ groupId 分发
         └─ HCT_EVENTS(0x0301) ─ handleReceiveHctDtc：DTC 查 HctEventTable → 缓存状态
                                 sendUdsEventReportResponse（6E 应答）
HctIpcFaultMgrRun（10ms 周期）
   └─ handlePeriodicTasks（每 100ms）
         └─ localSetEventStatus：KL15 ON 时按缓存状态 Dem_SetEventStatus（已有）
（通道 1 Ins1ch3 周期下发 / 通道 3 Ins5ch4 IDPS：本期不实现，链路不变）
```

### 2.2 接口规范定义 (APIs & Callouts)

| 接口 | 方向 | 说明 |
| :--- | :--- | :--- |
| `IpcAdpr_RxCallback_HCT_Event` | A核→R核 | Ins3ch1，已有；通道 2 入口（本期唯一改动面为查表数据） |
| `Dem_SetEventStatus` | R核内部 | 按 HctEventTable 缓存状态置位/恢复 Dem 事件 |
| `HctIpcFaultMgrInit/Run` | 调度 | os_cfg_core0 初始化/周期调用（已有，不动） |

### 2.3 并发与调度上下文

- IPC 接收回调与 `HctIpcFaultMgrRun` 不在同一上下文：`handleReceiveHctDtc` 仅写 `HctEventTable[].EventStatus`（单字节，天然原子），`localSetEventStatus` 在周期任务里读——与现有实现一致的弱同步模式，不改
- 通道 3 应答在接收回调上下文直接发送（与通道 2 的 `sendUdsEventReportResponse` 一致）

### 2.4 初始化时序

不变：`HctIpcFaultMgrInit` → manager initialize；通道 3 无新增初始化状态。

## 三、 核心逻辑、状态机与参数规则 (Core Logic & Parameters)

### 3.1 核心状态机设计 (State Machine)

无新增状态机。通道 2 事件状态沿用「收到什么存什么、KL15 ON 周期下放」模型（与规范置位策略一致）。

### 3.2 可配置参数表 (Configurable Parameters / Pre-Compile)

**A核故障码 映射表（HctEventTable，V0.0.1 全量替换）**——key 为 DTC(hex)（wire 载荷），value 为 DemEvent：

| DTC(hex) | Event Name | DemEvent（已核对存在于 RX Dem_Cfg_EventId.h） |
| :--- | :--- | :--- |
| 02C552 | CAMERA_FRONT_INIT_FAIL | DemEvent_CAMERA_INIT_ID_Cam_Front120 |
| 02C513 | CAMERA_FRONT_120FOV_DES_UNLOCK | DemEvent_DES_UNLOCK_Cam_Front120 |
| 02C531 | CAMERA_FRONT_120FOV_DES_VIDEO_UNLOCK | DemEvent_DES_Video_UNLOCK_Cam_Front120 |
| 02C544 | CAMERA_FRONT_BUF_EMPTY | DemEvent_DES_LMO_ERR_Cam_Front120 |
| 02C529 | CAMERA_FRONT_SYS_EXCEPTION | DemEvent_DES_LCRC_ERR_Cam_Front120 |
| 02C52A | CAMERA_FRONT_120FOV_DES_MAC_CRC | DemEvent_DES_MAC_CRC_Cam_Front120 |
| 02C52B | CAMERA_FRONT_120FOV_DES_ROUTING_OVERFLOW | DemEvent_DES_Rounting_Overflow_Cam_Front120 |
| 02C52C | CAMERA_FRONT_120FOV_DES_ADAPTOR_OVERFLOW_TX | DemEvent_DES_Adaptor_Tx_Overflow_Cam_Front120 |
| 02C52D | CAMERA_FRONT_120FOV_DES_ADAPTOR_OVERFLOW_RX | DemEvent_DES_Adaptor_Rx_Overflow_Cam_Front120 |
| 02C599 | CAMERA_FRONT_120FOV_VOLTAGE | DemEvent_SENSOR_VOLTAGE_ID_Cam_Front120 |
| 02C598 | CAMERA_FRONT_120FOV_TEMPERATURE | DemEvent_SENSOR_TEMPER_ID_Cam_Front120 |
| 02C594 | CAMERA_FRONT_120FOV_ROW_COL_ID | DemEvent_SENSOR_ROW_COLUMN_ID_Cam_Front120 |
| 02C592 | CAMERA_FRONT_120FOV_PLL_CLOCK | DemEvent_SENSOR_PLL_CLOCK_ID_Cam_Front120 |
| 02C59A | CAMERA_FRONT_120FOV_RAM_CRC | DemEvent_SENSOR_RAM_CRC_ID_Cam_Front120 |
| 02C59B | CAMERA_FRONT_120FOV_ROM_CRC | DemEvent_SENSOR_ROM_CRC_ID_Cam_Front120 |
| 02C591 | SENSOR_CENTER（0x01011005(7)） | DemEvent_SENSOR_FCNT_ID_Cam_Front120 |
| 03C554 | CALIB_SRV_FRONT_WIDE_GET_IEXTRINSIC_PARAMS_FAILED | DemEvent_HCTDTC_CalibMissing_Cam_Front120 |
| 03C591 | CALIB_SRV（0x02060505(7)） | DemEvent_HCTDTC_CalibIntrinsicsError_Cam_Front120 |
| 03C562 | FRONT_CAMERA_PARAM_OUT_OF_TOLERANCE_CHECK_FAILED | DemEvent_HCTDTC_FLC_Wide_ParamFault |
| 03C531 | CAMERA_FRONT_DATA_DISCONNECT | DemEvent_HCTDTC_SensorCenterNoImgInput_Cam_Front120 |
| 03C597 | FRONT_IMAGR_BLOCK_ERROR/IMAGE_QUALITY_BAD（0x10400007(3)） | DemEvent_HCTDTC_CamBlind_Cam_Front120 |
| 01A047 | SOC_CPU_OVERLOAD | DemEvent_CPULoadHigh |
| 01A045 | SATURNV_SW_BSW_SOC_MEM_OVERLOAD | DemEvent_MemoryUsageHigh |
| 01A148 | MODEL_INFERENCE（无 FaultID） | DemEvent_HCTDTC_PerceptionFault |
| 01A348 | DEVM（0x44011004(6/8/11)） | DemEvent_HCTDTC_Driving_SWFault |
| 01A448 | FAULTMGR（0x02200001(2/7/15/11)） | DemEvent_HCTDTC_FuncError |
| 01A548 | （无 FaultName/FaultID） | DemEvent_HCTDTC_SWError |
| 01A767 | PROCESS_AEBEVL_CRASH | DemEvent_IMOAcore_AEBEvl_Crash |
| 01A967 | PROCESS_IMAGEPRIENCODER_CRASH | DemEvent_IMOAcore_ImagePriEncoder_Crash |
| 01AA67 | PROCESS_IMO_SM_CRASH | DemEvent_IMOAcore_StateManager_Crash |
| 01AB67 | PROCESS_IMO_IPC_CRASH | DemEvent_IMOAcore_ipcManager_Crash |
| 01AA63 | StateManager_HEARTBEAT_LOST | DemEvent_IMOAcore_StateManager_Timeout |
| 01AB63 | ipcManager_HEARTBEAT_LOST | DemEvent_IMOAcore_ipcManager_Timeout |

> 33 条映射的 DemEvent 已全部核对存在于 RX Dem_Cfg_EventId.h；带 `(n)` 后缀的 FaultID 表示多备选值，映射同一 DTC/事件，表内不加行（FaultID 不参与 R核查表）。
>
> **修订说明（2026-11-17）**：规范更新为 V0.0.1_20261117（附件 206847，Jason 上传），较 20261116 版唯一变化为**删除 SOC_TEMP_OVERLOAD（01A04B / DemEvent_TEMPERATURE_OT_WARNING）行**——即原开放问题 #1 中映射目标缺失的条目，删除后映射目标缺失问题关闭；其余 33 条 DTC→Event 映射与 FaultID 均未变，IPC 内容to Faultmgr 页签逐行比对无差异。

## 四、 模块详细设计 (Detailed Design)

### 4.1 模块划分与职责

| 文件 | 改动 |
| :--- | :--- |
| `hct_ipc_table.cpp` | HctEventTable 按 §3.2 全量替换（旧 0x010000 系 → V0.0.1 DTC hex） |

通道 2 收发逻辑（`handleReceiveHctDtc` / `sendUdsEventReportResponse` / `localSetEventStatus`）不动——报文格式与 V0.0.1 一致，仅映射表换新。通道 3（IDPS_EVENT）本期不实现，设计留档见附录 B ADR #2。

### 4.2 函数级处理流程

无新增函数。`handleReceiveHctDtc`（已有）按 3 字节 DTC 查 HctEventTable，命中则缓存 status，未命中 LOGD；`localSetEventStatus` 周期下放。

### 4.3 内部数据结构设计

无新增结构。HctEventTable 结构不变（Dtc / Event / EventStatus）。

### 4.4 消息级时序

三通道报文格式均已在规范页签定义且通道 1/2 现有实现一致，不重复。通道 3 ack 重发（1s×3）为 A核侧行为，R核被动应答不涉及。

## 五、 异常处理、容错与安全机制 (Error Handling & Safety)

| 场景 | 处理 |
| :--- | :--- |
| DTC 查表未命中 | LOGD 留痕（现实现已如此），仍应答 6E——与现行为一致 |
| faultNum 超上限 | 截断到 HCT_EVENT_MAX_NUM（现实现已如此） |
| KL15 OFF | localSetEventStatus 跳过 Dem 置位（现实现已如此） |

## 六、 验证、测试与集成要求 (Verification & Integration)

### 6.1 资源消耗与性能基线

无新增周期任务、无 NVM、无堆分配；静态表替换（行数 24→33，约 +90B ROM）。

### 6.2 验收标准 (Acceptance Criteria)

1. 编译通过（J6 preset）
2. A核故障码 33 条映射逐条与规范页签一致（含 DTC hex 与 DemEvent 对应）
3. 通道 2 报文格式与 V0.0.1 页签字段级一致（GroupId 0x0301/SubFunc 0x02/SID 2E→6E/3B DTC+1B status 载荷）
4. 台架具备 A核联调条件时：A核上报故障 → R核 Dem 事件置位并 6E 应答 → 恢复上报后清除

**验证手段说明**：台架无 A核环境，通道级报文验证依赖 A核联调；R核侧可先以编译 + 代码走读 + TRACE32 断点（注入回调）验证查表与置位逻辑，A核联调项在用户手动验证阶段确认。

## 附录A：需求追溯矩阵

| 需求条目 | 设计章节 | 代码落点 |
| :--- | :--- | :--- |
| 导入 A核故障码 mapping 表 | §3.2 | hct_ipc_table.cpp HctEventTable |
| 通道 0301 A核故障上报 + 6E | §2.1/§6.2-3 | 已有 handleEventReportsGroup（表更新） |
| 通道 1030 周期下发 | 范围外 | 不动（开放问题 #2 留档） |
| 通道 1015 IDPS_EVENT | 范围外 | 不实现（开放问题 #3 留档） |

## 附录B：设计决策记录 (ADR 摘要)

| # | 决策 | 理由 |
| :--- | :--- | :--- |
| 1 | HctEventTable 以 DTC(hex) 为 key（沿用现实现），FaultID 不参与 R核查表 | wire 载荷是 3 字节 DTC（规范头部说明），FaultID 的 `(n)` 备选后缀无法唯一编码；与现实现/A核联调基础兼容 |
| 2 | 通道 3（IDPS_EVENT）本期不实现 | 2026-11-17 用户范围收窄：仅 A核上报 event；且 V0.0.1 未定义 IDPS 事件到 Dem 的映射，留待语义澄清后二次迭代 |
| 3 | 通道 1 FiMFID 73 条结构保留 | 需求文本未点名 FiMFID 页签刷新；104 条差异涉及 EVM FiM 字段映射，确认后另行处理 |

## 附录C：开放问题 (Open Issues)

| # | 问题 | 影响 | 状态 |
| :--- | :--- | :--- | :--- |
| 1 | ~~**规范 DTC 列与 RX Dem 配置不一致**~~ **已确认（2026-11-17 Jason.Yu 回复）**：规范 DTC 列（02C552/01A047 等）与 RX Dem 配置实际 DTC（C258700/C258348 等）本就不同——19 服务读出的 DTC 与规范显示码不一致是预期行为，无需 DEXT 层同步 | IPC 层按规范 DTC 查表不受影响；19 服务读码与规范显示码不同属预期 | ✅ 已关闭，接受现状 |
| 2 | 通道 1 payload 规范指向「故障码FiMFID」页签 104 条，现表 73 条（fault_id 编码一致，条目有增） | 周期下发条目数与规范不符 | 范围外，待确认后另行处理 |
| 3 | 通道 3 IDPS 事件收到后 R核侧语义（仅应答？是否置位 Dem/转发）规范未写 | 通道 3 深度行为 | 范围外，待澄清后二次迭代 |
| 4 | MODEL_INFERENCE / P01A548 行无 FaultID，规范表格留空 | 不影响查表（key 为 DTC），仅记录 | 接受现状 |
