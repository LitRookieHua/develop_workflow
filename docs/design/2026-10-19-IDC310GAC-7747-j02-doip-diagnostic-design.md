# ⚙️ J02 DoIP 诊断(Rcore DCM 侧 IPC 传输链路)需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | J02 DoIP 诊断(Acore DoIP → IPC → Rcore DCM) | **所属软件层级** | BSW (Diag Stack: Cdd / PduR / Dcm) |
| **文档状态** | 🟢 开发中(编码与编译完成,待 J02 板台架验证) | **安全与质量要求** | 通道互斥模块按 DCM-MUTEX-022 以 ASIL-B 约束设计,其余 QM ｜ 编译零错误 |
| **模块负责人 / 作者** | @Hua Yao / 姚华 | **关联输入/输出** | 📋 JIRA [IDC310GAC-7747] ｜ 📄 GWM de09g 参考实现 ｜ 📄 `J6M平台R核DCM诊断通道互斥访问控制软件需求.md`(随代码带入) |
| **关联 AUTOSAR 规范** | AUTOSAR CP R4.4(SWS_Dcm / SWS_PduR)+ ISO 14229-1(UDS)+ ISO 13400(DoIP,Acore 侧) | **平台** | Horizon J6M / ARM Cortex-R52(Rcore) |

> **📝 变更记录**
> * `2026-10-19`｜@Hua Yao｜V1.0｜初版(自由结构技术方案)
> * `2026-10-19`｜@Hua Yao｜V2.0｜按 `autosar-general-feature-design-template` 重构;修改点清单同步为阶段 3 实际落地状态
> * `2026-10-19`｜@Hua Yao｜V3.0｜按模板 V2(含详细设计/追溯矩阵/ADR/开放问题)重写

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景与痛点**:J02(一汽 FAWVW)新增 DoIP 诊断。DoIP 协议层在 Acore(QNX/Linux,另一仓库)实现,UDS 具体实现在 Rcore(MCU 侧 DCM)。若不搭建核间通道,DoIP 请求无法到达 Rcore 的既有 UDS 实现;同时 DoIP(以太网)与 DoCAN(总线)双诊断通道并存,若无互斥控制会话会错乱。
* **核心目标**:在 Acore 与 Rcore 之间搭建 IPC 诊断通道——Acore 收到 DoIP 请求后去 DoIP 头,将 UDS 帧经 IPC 送 Rcore DCM 处理,响应原路返回;DoIP/DoCAN 通道互斥;TesterPresent 经独立通道维持 Rcore 侧 S3 会话不掉。
* **设计原则**:
  1. **参考移植优先**:核心机制按 GWM de09g(`cpj_gwm/veh_de09g`,与 c06g 同源)已验证实现移植,按 J02 单连接形态裁剪,不发明新机制
  2. **不侵入生成代码语义**:对 ETAS 生成的 PduR/Dcm 只做最小手工补丁,并全部纳入 `restore_handedit` 白名单管理

### 1.2 适用范围 (Scope)

* **适用控制器/平台**:J02(`cpj_fawvw/veh_j02`,仓库 `mcu_app_j6_v2`)
* **核心职责**:
  1. IPC 接收 Acore 转发的 UDS 请求并送 DCM 处理
  2. DCM 响应按通道分流回发(DoIP→IPC / DoCAN→CanTp)
  3. DoIP/DoCAN 诊断通道互斥(需求 DCM-MUTEX-001~029)
  4. TesterPresent 经独立 IPC 通道维持 Rcore 侧 S3
* **范围边界**:本 Story 只做 Rcore(MCU)侧;Acore 侧 DoIP 协议栈在另一仓库(跨仓库契约见 §2.2 与附录 C)。UDS 清单暂按 de09g 全量参考。

### 1.3 术语与缩略语

| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| DoIP | Diagnostics over Internet Protocol | 以太网诊断(ISO 13400),J02 中在 Acore 实现 |
| DoCAN | Diagnostics over CAN | 总线诊断,经 CanTp,J02 既有链路 |
| DCM | Diagnostic Communication Manager | AUTOSAR 诊断通信管理(Rcore 侧 UDS 实现) |
| DSL/DSD | Diagnostic Session/Service Layer | DCM 会话层/服务层 |
| DSC | Diagnostic Session Control | UDS 服务 0x10 |
| NRC | Negative Response Code | UDS 否定响应码(0x21 忙重复/0x78 响应挂起) |
| S3 | S3Server Timer | 非默认会话保持定时器,超时回默认会话 |
| CDD | Complex Device Driver | AUTOSAR 复杂设备驱动(本设计指 `Cdd_PduR_IpcTp2Dcm`) |
| Cat1/Cat2 | ISR Category 1/2 | OSEK 中断分类;Cat1 禁调 AUTOSAR BSW/禁阻塞临界区 |
| MDMA | Memory DMA | J6 MCAL IPC 底层核间 DMA,RX 完成回调跑在 Cat1 |
| Ins6Ch2 / Ins7Ch0 | IPC Instance 6 Channel 2 / Instance 7 Channel 0 | UDS 请求通道 / TesterPresent 通道(跨仓库契约) |
| OTA owner | OTA 所有权 | 互斥状态机中 owner=IPC 且编程会话的占用状态 |
| de09g | GWM 项目的项目代号 | DoIP IPC 链路参考实现(`cpj_gwm/veh_de09g`) |

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | ISO 14229-1 (UDS) | 2020 | 会话/安全访问/NRC 语义 |
| R2 | AUTOSAR CP R4.4 SWS_Dcm / SWS_PduR | R4.4 | DCM/PduR 接口语义 |
| R3 | JIRA [IDC310GAC-7747](https://jira.imotion.ai:7070/browse/IDC310GAC-7747) | — | 本 Story 需求来源 |
| R4 | `autosar/Cdd/Adc_Gw/src/J6M平台R核DCM诊断通道互斥访问控制软件需求.md` | 随代码 | DCM-MUTEX-001~029 需求矩阵(从 de09g 带入) |
| R5 | GWM de09g DiagReqSpec §5.2-5.3 | — | UDS 服务路由清单参考(附录 B) |
| R6 | Obsidian 笔记 `J02 Add DoIP diagnostic function.md` | — | 工作记录主载体 |

### 1.5 设计约束与假设

* **技术约束**:
  * Cat1(MDMA 完成 ISR)上下文禁止调用 DCM 接口、禁止 `SchM` 阻塞临界区 → 收包只能拷贝+置标志,任务上下文转发(§4.2)
  * ETAS 代码生成会整文件覆盖 `BswRta/src/bsw/` 下手工补丁 → 必须走 `restore_handedit.bat` 白名单恢复机制
  * J02 构建双轨:Cdd/Adc_Gw 走 scons(yaml 目录自动收集,新文件免注册);ipc_cfg/os_cfg 走 CMake(新文件须显式入编)
  * 内存:静态缓冲为主(FIFO 2×2066 + 延迟槽 2×2066 + Diag_Message ~2KB),无动态内存
* **外部假设**:
  * A1:Acore 侧 DoIP 栈按 §2.2 契约(消息格式/通道号)实现——**联调前须与 Acore 团队核对**(开放问题 O1)
  * A2:MCAL IPC Instance 6/7 配置与 de09g 一致(已核对:`Ipc_ShmCfgInstances6/7` 各 8 通道、RecvIrqUsed TRUE,J02 已具备,无需 MCAL 改动)
  * A3:FAWVW 正式 UDS 清单最终以 de09g 为基线做少量差异调整(开放问题 O2)
* **假设的验证方式**:A1 在 Acore 联调阶段通道对通时验证;A2 已在阶段 2/3 构建核对完成;A3 由需求方在 FAWVW 清单下发后确认。

---

## 二、 架构设计与模块间交互 (Architecture & Interaction)

### 2.1 模块依赖关系与调用链

* **上游调用者 / 触发源**:Acore DoIP 栈(经 MCAL IPC:Ins6Ch2 = UDS 请求,Ins7Ch0 = TesterPresent);DoCAN Tester(经 CanTp→PduR)
* **下游被调 / 支撑模块**:Dcm(dia_cfg 服务表,复用为主,IDC310GAC-7008 已配 0x22/2E/31/27 等)、CanTp(DoCAN 响应回发)、MCAL IPC(MDMA 核间 DMA,Instance 6/7)
* **核心交互时序 / 数据流向**:

  请求:`DoIP Tester` ➡️(以太网)`Acore DoIP 去头` ➡️ `IPC Ins6Ch2(Cat1 MDMA 完成 ISR → Cdd_PduR_IPC_EnqueueDeferred 仅拷贝+置标志)` ➡️ `10ms 任务 Cdd_PduR_IPC_ProcessDeferred` ➡️ `Dcm_CheckChannelAccess(互斥检查)` ➡️ `DCM`

  响应:`DCM` ➡️ `PduR_DcmTransmit(PduR_UpTp.c 手工补丁,按 IpcTp_Transport_State 分流)` ➡️ FREE→CanTp(DoCAN)/ 否则→`PduR_Dcm2IpcTpTransmit` ➡️ `IPC` ➡️ `Acore` ➡️ `DoIP Tester`

  保活:`Acore 0x3E` ➡️ `IPC Ins7Ch0` ➡️ Rcore 刷新 S3,响应一律抑制,忙时丢弃不入 FIFO

* **调度注册**(`os_cfg_core0.c` 的 `RE_HRTgt_10ms`,顺序固定):`Cdd_PduR_IPC_ProcessDeferred()` → `Cdd_PduR_IPCTP_Watchdog()` → `Cdd_PduR_IPCTP_Fillin_Conflict_Frame()`

### 2.2 接口规范定义 (APIs & Callouts)

| 接口类型 | 函数原型 / 接口名称 | 输入/输出参数说明 | 核心职责与调用时机 |
| :--- | :--- | :--- | :--- |
| **CDD API** | `Cdd_PduR_IPC_EnqueueDeferred()` | IN: data, length, channel(0=UDS, 1=TesterPresent) | Cat1 MDMA ISR 收包入口:仅拷贝进 per-channel 延迟槽+置标志,不调 DCM |
| **CDD API** | `Cdd_PduR_IPC_ProcessDeferred()` | 无 | 10ms 任务:将 pending 请求经 SetIpcRxChannel + Cdd_PduR_TP_Dcm_Transmit 转发进 DCM |
| **CDD API** | `Cdd_PduR_IPCTP_Watchdog()` | 无 | 10ms 任务:ONRX 卡死强制回 FREE、owner=IPC 但 DCM 已回默认会话时强制释放 |
| **CDD API** | `Cdd_PduR_IPCTP_Fillin_Conflict_Frame()` | 无 | 10ms 任务:重放 FIFO 中被 0x78 挂起的 DoIP 请求进 DCM |
| **CDD API** | `Cdd_PduR_TP_Dcm_Transmit()` / `Cdd_PduR_SetIpcRxChannel()` | IN: data, length, isFromFifo / channel | IPC 请求注入 DCM(RxPduId 0 物理口)/ 记录当前请求通道供响应抑制决策 |
| **CDD API** | `PduR_Dcm2IpcTpTransmit()` | IN: id, info | DCM 响应经 IPC 回发 Acore |
| **Mutex API** | `Dcm_CheckChannelAccess()` | IN: channel, serviceId, subFunction → OUT: OK/DENIED/PENDING | 互斥检查+非 01 DSC 请求原子获取所有权(响应 0x21/0x78 决策点) |
| **Mutex API** | `Dcm_ChannelMutex_NotifyResponseSent()` | IN: channel, responseData, length | 响应发出后确认/释放所有权(0x50 02/03 确认,0x50 01/0x7F 10 释放) |
| **Mutex API** | `Dcm_ChannelMutex_NotifySessionTimeout()` 等 | 见 `Dcm_ChannelMutex.h` | S3 超时释放 / IPC 断连释放 / in-flight 标志管理 / 看门狗强制恢复 |
| **DSL 查询** | `Dcm_IsRequestProcessing()` / `Dcm_GetActiveServiceId()` / `Dcm_IsActiveRequestFunctional()` | 无 → boolean/uint8 | DSL 状态查询(实现在 `Dcm_Prv_General.c` 手工补丁),供互斥与分流决策 |
| **CDD 钩子** | `PduR_0x22Process()` / `PduR_0x2EProcess()` | IN: SduData, length → OUT: ResponseData, ResponseLength → HANDLED/NOT_HANDLED | 项目 bypass DID 拦截钩子;J02 stub 一律 NOT_HANDLED(全路由 DCM) |
| **跨仓库契约** | `Diag_Message_Type` | m_target_addr / m_command_u32(SID) / m_cmdRet_u32(NRC) / m_seq_u32 / m_info_len_u32 / m_info[2049] | IPC 消息格式,命令头固定 20 字节(`PDUR_DIAG_MESSAGE_COMMAND_LENGTH`),包长上限 2066;与 Acore 对齐 |

### 2.3 并发与调度上下文

| 接口 / 共享资源 | 执行上下文 | 临界区保护方式 | 备注 |
| :--- | :--- | :--- | :--- |
| `Cdd_PduR_IPC_EnqueueDeferred` | Cat1 MDMA 完成 ISR | 单写者(ISR)单读者(10ms 任务),per-channel 延迟槽 + 标志位 | ISR 内禁止调 DCM/禁止阻塞 |
| `IpcTp_Transport_State` / 互斥状态 | 10ms 任务 + Cat1 ISR + DoCAN RX 任务 | `SuspendAllInterrupts/ResumeAllInterrupts` 原子(DCM-MUTEX-010) | Check-and-grant 原子,消除 TOCTOU |
| `PduR_UpTp.c` 响应分流 | DCM TX 上下文 | 只读快照 `IpcTp_Transport_State` | FREE→DoCAN / 否则→IPC |
| `Cdd_PduR_IPCTP_Fillin_Conflict_Frame` | 10ms 任务 | 与 ISR 顺序约束(调度注册顺序固定) | 必须在 Watchdog 之后 |
| DoCAN RX(RxIndication/StartOfReception) | CanTp RX 上下文 | `Dcm_CheckChannelAccess` 检查 | owner=IPC 时拒绝(0x21)或边界 DROP |

* **禁止事项**:Cat1 上下文不得调用 DCM 任何接口、不得进入 `SchM_Dcm_Global` 阻塞区;FIFO 重放不得在 ISR 中触发。

### 2.4 初始化时序

* `Dcm_ChannelMutex_Init()` 在 ECU 启动诊断链路初始化时调用(owner=NONE/默认会话)
* IPC 通道(Ins6Ch2/Ins7Ch0)依赖 `Ipc_Init` + `IpcAdpr_InitIpc()`(既有 `RE_HRTrgtInit` 流程,无新增依赖)
* 10ms runnable 依赖 `StartScheduleTableRel` 调度已起(`RE_HRTrgtInit` 尾部),自然满足

---

## 三、 核心逻辑、状态机与参数规则 (Core Logic & Parameters)

### 3.1 核心状态机设计

**IPC 传输对象状态**(`IpcTp_Transport_State`,位图):`FREE(0x00)` / `ONRX(0x01)` / `RX_END(0x02)` / `PREPTX(0x04)` / `ONTX(0x08)` / `READY(0x10)` / `RESERVED(0x20)`。`PduR_UpTp.c` 响应分流仅判 `FREE` 与否。

**通道互斥状态机**(owner ∈ `NONE/DOCAN/IPC`,完整需求矩阵见 R4):

| 当前状态 | 目标状态 | 触发条件 (Guard) | 动作 (Action) |
| :--- | :--- | :--- | :--- |
| `NONE` | `DOCAN`/`IPC`(tentative) | 该通道非 01 的 0x10 请求被接受 | 原子获取所有权(grantConfirmed=FALSE),等待 0x50 确认 |
| owner(tentative) | owner(confirmed) | 0x50 02/03 响应发出(NotifyResponseSent) | 确认获取,刷新会话 |
| owner(confirmed) | `NONE` | 0x50 01 响应 / 未确认的 0x7F 10 / S3 超时 / IPC 断连 | 释放所有权,回默认会话 |
| `DOCAN` owner + DoIP 请求 | — | DoIP 请求到达且 DoCAN 未回默认会话 | 互斥拒绝:NRC 0x21(边界拒绝)或 0x78(挂起入 FIFO) |
| `IPC` owner(卡死) | `FREE`/`NONE` | 看门狗 10ms 检测:ONRX 卡死 / owner=IPC 且 DCM 已回默认会话 | 强制恢复(ForceClearIpcInFlight / ForceReleaseOta) |

**J02 相对 de09g 的裁剪**(单 DoCAN 连接,无 CAN/CANFD 双连接):跳过 `Dcm_Prv_IsRequestFromSameProtocolRow()` 协议行亲和放宽与 GWM SPRMB 正响应抑制矩阵;FAWVW bypass DID 暂未定义,`Cdd_PrjSpecificExtData.c` 为全路由 DCM 的 stub。

### 3.2 可配置参数表

| 参数分类 | 参数名称 | 可配置范围 | 默认值 | 参数作用与影响 |
| :--- | :--- | :--- | :---: | :--- |
| **缓冲** | `IPCTP_FIFO_DEPTH` | 编译期宏 | `2` | 冲突帧 FIFO 深度;UDS 一问一答,2 深足够,丢帧=时序问题 |
| **缓冲** | `UDS_PACKET_MAX_LEN` | 编译期宏 | `2066` | 单包上限(2048 扩展载荷+18 开销),支持超长 19 0A 响应 |
| **协议** | `PDUR_DIAG_MESSAGE_COMMAND_LENGTH` | 编译期宏 | `20` | IPC 消息命令头固定长度(跨仓库契约,改动须与 Acore 同步) |
| **重试** | `PDUR_IPC_FIFO_MAX_RETRY_COUNT` / `PDUR_IPC_FIFO_RETRY_INTERVAL_MS` | 编译期宏 | `50`/`100ms` | FIFO 冲突帧重放上限与节流,超限丢弃并计 Frame_Loss_Count |
| **通道** | IPC Instance/Channel | `IpcAdpr_cfg.c` RX 表 | Ins6Ch2 / Ins7Ch0 | UDS 请求与 TesterPresent 通道号(跨仓库契约) |
| **时序** | 延迟转发延迟 | 由 10ms 调度决定 | 0..10ms | Cat1 ISR→10ms 任务转发,远小于 P2=50ms |
| **调试** | `DCM_DOCAN_LOG_ENABLE` | STD_ON/OFF | `STD_ON` | DoCAN/DoIP 十六进制 trace;量产置 OFF 全部编译剔除 |

---

## 四、 模块详细设计 (Detailed Design)

### 4.1 模块划分与职责

| 子模块/源文件 | 职责 | 对外接口 | 内部依赖 |
| :--- | :--- | :--- | :--- |
| `Cdd_PduR_IpcTp2Dcm.c`(新增) | IPC↔DCM 传输层 CDD:延迟队列 + 传输对象状态 + FIFO 冲突处理 + 看门狗 | §2.2 全部 CDD API | `Dcm_ChannelMutex`、MCAL IPC |
| `Dcm_ChannelMutex.c`(新增) | DoIP/DoCAN 通道互斥状态机(DCM-MUTEX-001~029) | `Dcm_CheckChannelAccess` 等 Mutex API | DCM DSL 查询(手工补丁提供) |
| `IpcUdsSvc.cpp/.hpp`(新增) | Acore UDS RX 端点 + 3E TesterPresent 通道 + bypass 状态机 | `IpcAdpr_UDS_Service` / `IpcAdpr_TesterPresent_Service` 回调 | `Cdd_PduR_IpcTp2Dcm` |
| `Cdd_PrjSpecificExtData.c`(新增 stub) | 项目 bypass DID 拦截钩子 | `PduR_0x22Process/0x2EProcess` | 无(J02 全 NOT_HANDLED) |
| `PduR_UpTp.c`(手工补丁) | DCM 响应按通道分流 | `PduR_DcmTransmit` 内部改写 | `IpcTp_Transport_State` |
| `Dcm` 5 文件(手工补丁) | 互斥钩子 / DSL 查询 / DoCAN trace / NRC 0x21 | `DcmCore_DslDsd_Pub.h` 新增 3 查询 | `Dcm_ChannelMutex` |
| `IpcAdpr_cfg.c`(修改) | RX 通道表注册 | — | — |
| `os_cfg_core0.c`(修改) | 10ms 调度注册 3 runnable | — | — |

### 4.2 函数级处理流程

```text
Cdd_PduR_IPC_EnqueueDeferred(data, length, channel)   [Cat1 ISR 上下文]
1. 若 length 超界(>UDS_PACKET_MAX_LEN): 计数丢弃, return
2. memcpy 进 Deferred[channel] 槽, 记录长度
3. 置 Pending[channel] 标志
4. return (全程不调 DCM)

Cdd_PduR_IPC_ProcessDeferred()   [10ms 任务]
1. 对 channel = 0..1:
   1.1 若 Pending[channel] 未置位: continue
   1.2 清 Pending[channel]
   1.3 若 channel=1(TesterPresent):
       - 忙(IpcTp_Transport_State != FREE)则丢弃不入 FIFO
       - 刷新 S3, 响应抑制, continue
   1.4 Cdd_PduR_SetIpcRxChannel(channel)
       + Cdd_PduR_TP_Dcm_Transmit(槽数据, 长度, FALSE)
       → 内部先 Dcm_CheckChannelAccess:
         OK      → 注入 DCM(RxPduId 0 物理口), NotifyIpcRequestAccepted
         DENIED  → NRC 0x21 直接回发
         PENDING → Cdd_PduR_IPCTP_Inset_Conflict_Frame 入 FIFO(0x78 语义)

Cdd_PduR_IPCTP_Watchdog()   [10ms 任务, 在 Fillin 之前]
1. 若 ActiveConnection 卡 ONRX 超过阈值(请求进 DCM 无响应):
   强制回 FREE + Dcm_ChannelMutex_ForceClearIpcInFlight()
2. 若 owner==IPC 且 Dcm_DsldGetActiveSessionMask_u32()==默认会话掩码
   (S3 不再触发的不可自愈态):
   Dcm_ChannelMutex_ForceReleaseOta()

Cdd_PduR_IPCTP_Fillin_Conflict_Frame()   [10ms 任务]
1. 遍历 FIFO 两槽: 未占用 continue
2. 节流检查(距上次重试 < RETRY_INTERVAL_MS 则跳过)
3. 重试 Cdd_PduR_TP_Dcm_Transmit(..., isFromFifo=TRUE)
4. 成功 → 释放槽; 失败 → Retry_Count++, 超过 MAX_RETRY_COUNT 丢弃
   并 Frame_Loss_Count++
```

### 4.3 内部数据结构设计

```c
/* 延迟槽: Cat1 ISR 单写 / 10ms 任务单读, 免锁 */
typedef struct {
    uint8  buf[UDS_PACKET_MAX_LEN];   /* 2066B × 2 通道 */
    uint16 len;
    uint8  pending;                   /* 标志位 */
} IpcDeferredSlotType;                /* 2 × ~2067B ≈ 4.1KB */

/* 冲突帧 FIFO(结构定义于 Cdd_PduR_IpcTP2Dcm.h) */
typedef struct {
    uint8  Ipc_Fifo[IPCTP_FIFO_DEPTH][UDS_PACKET_MAX_LEN];  /* 2×2066B */
    uint32 Fifo_used_length[IPCTP_FIFO_DEPTH];
    uint8  Fifo_Filled[IPCTP_FIFO_DEPTH];
    uint32 Conflict_Frame_Count;      /* 监控计数 */
    uint32 Frame_Loss_Count;
    uint32 Fifo_Retry_Count[IPCTP_FIFO_DEPTH];
    uint32 Fifo_Last_Retry_Time[IPCTP_FIFO_DEPTH];
} PduR_IPC_FIFO_Type;                 /* ≈ 4.2KB */
```

* **容量论证**:`IPCTP_FIFO_DEPTH=2`——UDS 严格一问一答,冲突帧只可能来自"DoIP 抢占挂起(0x78)期间又来一帧",2 深覆盖正常交互;更深 FIFO 只会掩盖时序问题(丢帧=交互时序需优化,而非加深)。`UDS_PACKET_MAX_LEN=2066` 覆盖 2048 字节扩展载荷+18 开销(超长 19 0A 响应)。总静态 RAM 增量约 10.5KB(延迟槽 4.1K + FIFO 4.2K + Diag_Message 临时对象 ~2K),无动态分配。

### 4.4 消息级时序

```text
DoIP 请求(正常)                     Cat1 ISR        10ms Task          DCM
Tester --以太网--> Acore 去头 --IPC Ins6Ch2-->
                                     |--拷贝+置标志-->|
                                     |               |--CheckChannelAccess--OK-->| 注入
                                     |               |<-------------0x50 响应-------|
                                     |<--PduR_Dcm2IpcTpTransmit--IPC--Acore--Tester

DoIP 抢占(DoCAN 忙)   [DCM-MUTEX-005/011]
  DoIP 请求 → CheckChannelAccess = PENDING → NRC 0x78 回发 + 入 FIFO
  → DoCAN 回默认会话/释放 → Fillin_Conflict_Frame 重放 → 正常处理

DoCAN 在 DoIP 会话中请求   [DCM-MUTEX-007 / DCM-MUTEX-CLOSE]
  StartOfReception 边界: owner==IPC 且非 IPC pending → BUFREQ_E_NOT_OK(DROP)
  功能寻址 3E80: owner==IPC → 标记 INEFFECTIVE, 不刷新 S3

看门狗恢复(异常)   [fix #1 / fix #2]
  ONRX 卡死 → Watchdog 强制 FREE → 下一请求可入
  owner=IPC + 默认会话 → ForceReleaseOta → owner=NONE
```

---

## 五、 异常处理、容错与安全机制 (Error Handling & Safety)

| 异常/边界场景 | 潜在风险 | 通用防御与降级策略 |
| :--- | :--- | :--- |
| **Cat1 ISR 上下文不能调 DCM** | ISR 内直调 DCM 重入/死锁 | 延迟队列模式:ISR 只拷贝+置标志,10ms 任务 ProcessDeferred 转发(§4.2) |
| **DoIP/DoCAN 并发请求** | 双通道同时占有 DCM 会话错乱 | 互斥:非 owner 请求 0x21(边界拒绝)或 0x78(挂起入 FIFO);DoCAN 在 StartOfReception 边界 DROP(DCM-MUTEX-CLOSE);3E80 在 owner=IPC 时 INEFFECTIVE(DCM-MUTEX-007) |
| **ActiveConnection 卡 ONRX** | IPC 通道 wedge 到复位 | Watchdog 强制回 FREE + `ForceClearIpcInFlight`(fix #1) |
| **owner=IPC 但 DCM 已回默认会话**(S3 重载竞态) | 所有权永不释放 | Watchdog `ForceReleaseOta` 原子清除 OtaMode/owner/会话/in-flight(fix #2) |
| **FIFO 满或冲突帧长期重放失败** | 请求丢失无痕迹 | 重试 50 次(100ms 节流)后丢弃;Conflict_Frame_Count / Frame_Loss_Count 计数可监控 |
| **ETAS 代码生成覆盖手工补丁** | PduR/Dcm 互斥补丁丢失 | `tools/restore_handedit.bat` 白名单(6 文件)`git checkout HEAD` 整文件恢复;重新生成后必跑 |
| **FAWVW bypass DID 清单未定** | CDD 越权拦截错误 DID | `Cdd_PrjSpecificExtData.c` stub 全部 NOT_HANDLED,全路由 DCM;清单明确后逐 DID 增加 |

* **安全机制追溯**:DCM-MUTEX-022(ASIL-B)→ 互斥状态原子操作(SuspendAllInterrupts);DCM-MUTEX-018 → `Dcm_CheckChannelAccess` < 5us。

---

## 六、 验证、测试与集成要求 (Verification & Integration)

### 6.1 资源消耗与性能基线

| 指标 | 预算/基线 | 测量方法 |
| :--- | :--- | :--- |
| CPU 负载(10ms runnable,常态空转) | < 数 us/周期 | 台架 DWT/示波器 GPIO 翻转实测(待板到位) |
| CPU 负载(最坏单帧转发+重放) | 远小于 10ms 周期 | 同上 |
| RAM 增量 | ~10.5KB(§4.3 论证) | map 文件对比基线版本(待做) |
| 端到端延迟(ISR→DCM) | 0..10ms < P2=50ms | DoIP 仪 response timeout 配置验证 |

### 6.2 验收标准 (Acceptance Criteria)

- [x] **编译零错误**:imobuilder build `mcu_app_j6_v2`(preset `cpj_fawvw_j02_d310`),2026-10-19 通过
- [ ] **J02 板刷写**:ProgramBoard_j6b(`configs/j02_mcu.json`,镜像 `int_rpu_arm8r5_arm_j02_gnu.img`)——待 J02 板到位
- [ ] **台架 DoIP 验证(用户手动)**:DoIP 诊断仪经以太网发请求 → Acore 转 IPC → Rcore DCM 响应;覆盖 0x10 会话切换、0x27 安全访问(35/36)、0x22/0x2E DID 读写、0x19/0x14、0x3E 周期保活不掉会话、DoIP 会话中 DoCAN 互斥(0x21/0x78)
- [ ] **DoCAN 回归**:既有 CAN 诊断(IDC310GAC-7008 的 0x22/2E/31/27)无回归
- [ ] **Acore 联调**:通道号(Ins6Ch2/Ins7Ch0)与消息格式(20 字节头/2066 上限)两端一致

---

## 附录A:需求追溯矩阵

| 需求编号 | 需求摘要 | 设计章节 | 验证章节/用例 |
| :--- | :--- | :--- | :--- |
| DCM-MUTEX-001~003 | 通道定义/会话记录 | §2.2 / §3.1 | §6.2 台架用例(互斥) |
| DCM-MUTEX-004/005 | 访问检查/0x10 01 释放 | §3.1 / §4.2 | §6.2 台架用例(0x10/互斥) |
| DCM-MUTEX-006/007 | 非 owner 拒绝 NRC 0x21 / 3E80 无效 | §4.4 时序 3 | §6.2 台架用例(DoCAN 互斥) |
| DCM-MUTEX-008 | S3 超时释放(含 IPC 抑制竞态) | §3.1 / §4.2 Watchdog | §6.2 台架用例(0x3E) |
| DCM-MUTEX-009 | IPC 断连释放 | §2.2 | 联调 |
| DCM-MUTEX-010 | 原子性 | §2.3 | 代码评审 |
| DCM-MUTEX-013~017 | 公共 API | §2.2 | 代码评审 |
| DCM-MUTEX-018/019 | 性能(<5us/<1us) | §5 追溯 | §6.1 实测 |
| DCM-MUTEX-021 | Init | §2.4 | 启动日志 |
| DCM-MUTEX-022 | ASIL-B | §5 追溯 | 代码评审 |
| IDC310GAC-7747 验收 1~5(§1.1 验收标准) | 双向链路/UDS 清单/互斥保活/无回归/编译刷写验证 | 全文 | §6.2 |

## 附录B:UDS 服务路由清单(参考 de09g DiagReqSpec §5.2-5.3)

- **A核→IPC→R核 DCM**:0x10(SF02 A核自处理,仅通知 R核)/ 0x11 / 0x14 / 0x19 / 0x22 / 0x2E / 0x27(35/36 仅 DoIP)/ 0x28 / 0x31 / 0x85
- **A核 DoIP 自处理(刷写类)**:0x34 / 0x35 / 0x36 / 0x37 / 0x38
- **0x3E TesterPresent**:A核 DM 直接应答上位机;同时经 Ins7Ch0 送 Rcore 保活(S3),Rcore 响应一律抑制,忙时丢弃不入 FIFO
- **不支持**:0x2F(by-design)
- FAWVW 正式需求明确后差异项再调整

## 附录C:设计决策记录 (ADR 摘要)

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | ISR 延迟队列转发(拷贝+标志) | Cat1 直调 DCM / 改 Cat2 中断 | Cat1 不可阻塞不可调 BSW,改中断类别属 MCAL 层大改 |
| 2 | 跳过 de09g 协议行亲和放宽 | 照搬 `IsRequestFromSameProtocolRow` | J02 单 DoCAN 连接,无 CAN/CANFD 双连接场景,放宽反引入不可测路径 |
| 3 | 跳过 GWM SPRMB 抑制矩阵 | 照搬 | 客户特有正响应抑制策略,FAWVW 未要求 |
| 4 | bypass DID stub(全 NOT_HANDLED) | 按 de09g 移植 F190/F18C 等 NVM 读 | FAWVW bypass 清单未定(开放问题 O2),先保证全路由 DCM 正确性 |
| 5 | 互斥补丁手工维护+restore 白名单 | 修改 ETAS 生成配置纳入 arxml | 生成工具不开放该层钩子;de09g 同机制已验证,31 文件版裁剪为 J02 所需 6 文件 |
| 6 | TesterPresent 独立通道(Ins7Ch0)+ 响应抑制 | 复用 UDS 通道透传 0x3E | 忙时 0x3E 不能入 FIFO 占位(会顶掉真实请求);保活与请求解耦 |
| 7 | FIFO 深度 2 | 更深 FIFO / 无 FIFO 直接丢 | UDS 一问一答,丢帧=时序问题;de09g 实测 2 深足够 |

## 附录D:开放问题 (Open Issues)

| # | 问题描述 | 影响 | 责任方 | 跟踪截止时间 |
| :--- | :--- | :--- | :--- | :--- |
| O1 | Acore 侧 IPC 契约(通道号/消息格式)未联调核对 | 双向链路可能不通 | Acore 团队 + 本模块 | 联调前 |
| O2 | FAWVW 正式 UDS 清单(会话/安全矩阵、bypass DID)未定 | 0x27 35/36、bypass DID 范围待调整 | 需求方 | 待 FAWVW 下发 |
| O3 | J02 板暂缺 | 刷写/台架验证/性能实测(§6.1)延后 | 硬件资源 | 待板到位 |

## 附录E:修改点清单(阶段 3 实际落地)

目标 `cpj_fawvw/veh_j02/`,源 `cpj_gwm/veh_de09g/`:

| # | 操作 | 文件 | 说明 |
| :--- | :--- | :--- | :--- |
| 1 | 新增 | `autosar/Cdd/Adc_Gw/src/Cdd_PduR_IpcTp2Dcm.c` + `inc/Cdd_PduR_IpcTP2Dcm.h` | IPC↔DCM 传输层 CDD |
| 2 | 新增 | `autosar/Cdd/Adc_Gw/src/Dcm_ChannelMutex.c` + `inc/Dcm_ChannelMutex.h` | 通道互斥 |
| 3 | 新增 | `ipc_cfg/src/IpcUdsSvc.cpp` + `ipc_cfg/inc/ipc_cfg/IpcUdsSvc.hpp` | Acore UDS RX 端点 |
| 4 | 新增 | `autosar/Cdd/Adc_Gw/src/Cdd_PrjSpecificExtData.c` | bypass DID stub |
| 5 | 修改 | `ipc_cfg/src/IpcAdpr_cfg.c` | RX 通道表加 Ins6Ch2/Ins7Ch0 |
| 6 | 修改 | `ipc_cfg/CMakeLists.txt` | `IpcUdsSvc.cpp` 入编 |
| 7 | 修改 | `os_cfg/src/os_cfg_core0.c` | 10ms 注册 3 runnable |
| 8 | 手工补丁 | `BswRta/src/bsw/` 6 文件(PduR 1 + Dcm 5) | 分流/互斥钩子/DSL 查询/trace |
| 9 | 新增 | `tools/restore_handedit.bat` | 生成后恢复 handedit(6 文件白名单) |
| 10 | 随代码带入 | `J6M平台R核DCM诊断通道互斥访问控制软件需求.md` | 互斥需求文档(R4) |
