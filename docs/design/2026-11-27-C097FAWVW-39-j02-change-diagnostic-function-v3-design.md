# ⚙️ J02 Change Diagnostic Function V3 需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | J02 诊断功能变更第三批次（Dem 快照/扩展数据 + DCM 会话时间 + CanTP 网络层参数） | **所属软件层级** | BSW (Dem / Dcm / CanTp) + EcuAb 数据采集 |
| **文档状态** | 🟡 待评审 | **安全与质量要求** | QM ｜ GHS 编译零新增警告 |
| **模块负责人 / 作者** | @Hua.Yao | **关联输入/输出** | 📑 C097FAWVWREQ-722/723/112/113/114/95/98~105 ｜ 📊 `IDC_DemGeneral_Config_J02_V0.1_20261123.xlsx`、`UDS_Diagnostic_Questionnaire_J02.xlsx` |

> **📝 变更记录**
> * `2026-11-27`｜@Hua.Yao｜V1.0｜完成三组诊断变更的参数规范、Dem 配置建模与数据采集设计
> * 关联 Story：C097FAWVW-39（implemented 关联 14 张需求单）；前序批次 C097FAWVW-38（V2，已解决）

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景**：J02 项目诊断功能按客户诊断问卷持续迭代（V1 已导入基础服务，V2 C097FAWVW-38 已交付 27 解锁延时/019C/2B37~2B39/F193/E2EConfig）。本批次（V3）补齐客户问卷中的 Dem 快照/扩展数据定义、DCM 会话时间参数与 CanTP 网络层时序参数。
* **核心目标**：
  1. Dem：快照记录 01/02/FF 支持 4 个新 DID（0x2B50~0x2B53）；扩展数据记录 01（2B）/02（10B），`$19 06` 支持 01/02/FF 读取
  2. Dcm：P2Server=50ms（已满足）；P2*Server=5000ms；S3Server=5000ms（已满足）
  3. CanTp：未使用字节填充 0x00、BS=0、STmin=10ms、N_As/N_Bs/N_Ar/N_Cr=1000ms、N_Cs/N_Br=60ms
* **设计原则**：
  1. **表为唯一真源**：Dem 配置全部经 `IDC_DemGeneral_Config_J02` 表驱动 `gen_dem_general` 生成，禁止绕过表手改 arxml 受管容器
  2. **复用 RX 先例**：快照 DID 只允许外部数据元素、扩展记录可混用内部数据元素（F4CMC-100/101 实测结论）；SR 读回调按 `Dcm_DemGetSRData_<容器名>` 命名由 Dcm 侧约定

### 1.2 适用范围 (Scope)

* **适用控制器/平台**：J02（FAWVW C097），J6 平台 `mcu_app_j6_v2` 仓库 `veh_j02` 配置
* **核心职责**：Dem DemGeneral 配置容器重建 + 采集代码、Dcm 会话时间问卷参数、CanTp EcucValues 参数
* **范围边界**：
  * 不改动 DTC 属性定义（Create_DemDTCAttributes 输入不变）
  * 不改动 0x0500/0x9A5D 之外的既有 DID 语义（旧快照 DID 0x0500/0x9A5D 随本次重建移除，由新 DID 0x2B50~0x2B53 取代——旧容器为客户 V0 早期配置，新问卷已定义完整快照集）
  * STmin 不区分 APP/boot（REQ-99 备注已确认 10ms 平配，无 CANFD 刷写需求）

### 1.3 术语与缩略语

| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| Snapshot | DTCSnapshotRecord | DTC 冻结帧快照，记录号 01/02/FF |
| ExtendedData | DTC ExtendedDataRecord | DTC 扩展数据，`$19 06` 读取 |
| OCCCTR | Occurrence Counter | Dem 内部发生次数计数器 |
| AGINGCTR | Aging Counter (up-counter) | Dem 内部老化计数器 |
| MFK | — | 客户缩写，指本 ECU 诊断实现 |
| FDC | Fault Detection Counter | 故障检测计数器 |

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | C097FAWVWREQ-722 / 723 | — | Dem 快照/扩展数据定义（含位打包表） |
| R2 | C097FAWVWREQ-112 / 113 / 114 | — | DCM 会话时间参数 |
| R3 | C097FAWVWREQ-95 / 98~105 | — | CanTP 网络层参数 |
| R4 | `docs/design/2026-11-18-F4CMC-100-101-rx-dem-snapshot-extended-data-design.md` | — | RX 同类先例：ETAS 校验规则、回调命名、内部/外部元素约束 |
| R5 | `docs/design/2026-11-20-dem-autogen-etas-gen-dem-general-design.md` | — | gen_dem_general 生成器设计与幂等验证方法 |
| R6 | `docs/design/2026-11-26-C097FAWVW-38-j02-change-diagnostic-function-v2-design.md` | — | V2 批次先例（分支/流程） |

### 1.5 设计约束与假设

* **技术约束**：
  * ETAS ISOLAR（RTA-CAR 12.7.0）校验：**快照 DID 不得引用内部数据元素**；扩展数据记录允许内部元素（R4 实测）
  * `gen_dem_general` 删除规则：SHORT-NAME 在表内 OR 受管类型容器且容器级 `S="USER_GENERATED"`；固定名契约 `ExtendedDataClass_DTC_Properties`、`FreezeFrame_DTC_DidSet_TypeA/TypeB`、`DTC_Properties_FFRecNumClass` 被 `Create_DemDTCAttributes.py` 按名引用，不可改名
  * CanTp EcucValues 为 arxml 手改参数（无专用问卷表），**必须在跑 Dem/Dcm AutoGen（触发 ISOLAR BSW 重生成）之前改完**，否则重生成会消费旧值
  * BSW 重生成按 §1.5 收敛规则处理（autosar-code-generation.md §1.5）：仅保留目标模块产物，回退无关附带改动，补回丢失的未标记手改 patch
* **外部假设**：
  * `g_CAN0_iBRS_01_st` / `g_CAN0_Diagnose_01_st` / `g_CAN0_BDU_TiInfo_st` 全局信号已由 Com/NetCom 侧周期接收（已核实 NetCom_Notification_Can.cpp 既有接收代码）
  * `GetVoltValue(ADC_VBAT_FILT)` 返回 mV 单位（Mcu_Adc.c 已核实）
* **假设的验证方式**：编译通过 + 台架 `$19` 读回验证数据正确性（阶段 4）

---

## 二、 架构设计与模块间交互 (Architecture & Interaction)

### 2.1 模块依赖关系与调用链

* **上游调用者**：Tester（`$19 04` 读快照、`$19 06` 读扩展数据）
* **核心调用链（快照/扩展数据读取）**：

```
Tester $19 04/06
  ➡️ Dcm (Dcm_ReadDataByDTCDid/ExtendedDataRecord)
  ➡️ Dem (EventMemory 检索 SnapshotRecord/ExtendedDataRecord)
  ➡️ 内部元素: Dem 直接取 OCCCTR/AGINGCTR/DEM_DTC_PRIORITY
  ➡️ 外部元素: Dem_CallSRDataElement_<SR> ➡️ Dcm_DemGetSRData_<容器名> (evm_cfg_freezeframe_data.cpp)
  ➡️ 数据源: GetVoltValue(ADC) / g_CAN0_*_st (Com→NetCom 周期接收缓存)
```

* **配置生成链**：`IDC_DemGeneral_Config_J02.xlsx`（表）→ `gen_dem_general.py` → `J6B_Dem_EcucValues.arxml`；`UDS_Diagnostic_Questionnaire_J02.xlsx`（DcmDspSession sheet）→ Dcm_AutoGen → Dcm 配置产物；CanTp EcucValues 直接手改

### 2.2 接口规范定义 (APIs & Callouts)

| 接口类型 | 函数原型 / 接口名称 | 输入/输出 | 核心职责与调用时机 |
| :--- | :--- | :--- | :--- |
| **Callback (Dcm→EcuAb)** | `Dcm_DemGetSRData_SR_Supply_Voltage(uint16 start, uint8 *buf, uint16 len)` | 读 2B | 快照/无，0x2B50 元素；Dem 检索快照时调用 |
| **Callback** | `Dcm_DemGetSRData_SR_Vehicle_Speed(...)` | 读 2B | 0x2B51 元素 |
| **Callback** | `Dcm_DemGetSRData_SR_Odometer_Reserved(...)` / `SR_Odometer_Mileage(...)` | 各读 2B/1B… | 0x2B52 拆分元素 |
| **Callback** | `Dcm_DemGetSRData_SR_Date_Time_TimeStamp(...)` 系列 | 拆分元素 | 0x2B53 与扩展记录 02 共用 |
| **Callback** | `Dcm_DemGetSRData_SR_ExtData_TimeIndication(...)` | 读 1B | 扩展记录 02 byte5，恒返 0 |
| **BSW API** | `gen_dem_general.py <表> <arxml> <ecg> <efd>` | CLI | 表 → DemGeneral 容器生成，`<efd>=true` 启用快照/扩展重建 |

> 回调签名与既有 `Dcm_DemGetSRData_SR_*` 保持一致（参照 evm_cfg_freezeframe_data.cpp 既有实现）；具体拆分元素命名见 §4.2。

### 2.3 并发与调度上下文

| 接口 / 共享资源 | 执行上下文 | 临界区保护方式 | 备注 |
| :--- | :--- | :--- | :--- |
| `Dcm_DemGetSRData_*` | Dcm 任务上下文（DCM_MainFunction 链路） | 读全局 Com 信号缓存单值，天然原子（32bit 内） | 与既有快照回调一致，无新增保护 |
| `g_CAN0_*_st` 写入方 | Com Rx indication（任务上下文） | 既有 NetCom 接收代码，本设计不改动 | 数据新鲜度取决于报文周期 |

* **禁止事项**：回调内不得调用 Dcm/Dem API、不得阻塞等待总线信号刷新。

### 2.4 初始化时序

* 无新增初始化。数据采集回调读取的 `g_CAN0_*_st` 与 `GetVoltValue` 均为既有初始化产物。

---

## 三、 核心逻辑与参数规则 (Core Logic & Parameters)

### 3.1 Dem 配置建模（表 → 容器）

**改动模式**：同名行在表中重新定义 → 生成器删除旧容器后按表重建；表中未出现的旧容器（非 S 标记）保留为孤儿 → 生成后手工删除。

**extended_freeze_data sheet（本次新增行，`veh_j02.yaml` 的 `extended_freeze_data: false → true` 启用）**：

| 行类型 | SHORT-NAME | 关键参数 | 说明 |
| :--- | :--- | :--- | :--- |
| data_element | SR_Supply_Voltage | External UINT16 OPAQUE | 0x2B50，f(x)=0.1x，物理 0~25V |
| data_element | SR_Vehicle_Speed | External UINT16 OPAQUE | 0x2B51，f(x)=0.01x |
| data_element | SR_Odometer_Reserved | External UINT8 OPAQUE | 0x2B52 byte1 bits23-20 恒 0 |
| data_element | SR_Odometer_Mileage | External UINT16 OPAQUE | 0x2B52 bytes2-3，bits19-0 |
| data_element | SR_Date_Time_TimeStamp | External UINT32 OPAQUE | 0x2B53 bytes1-4（bits39-8） |
| data_element | SR_Date_Time_Second | External UINT8 OPAQUE | 0x2B53 byte5（bits7-0） |
| data_element | SR_ExtData_TimeIndication | External UINT8 OPAQUE | 扩展记录 02 byte5 恒 0 |
| data_element | SR_ExtendedDataRecord_Fault_occurrence_counter | Internal DEM_OCCCTR size=1 | 同名行重定义（内容不变，复用旧名） |
| data_element | SR_ExtendedDataRecord_Ageing_Counter | Internal DEM_AGINGCTR_UPCNT size=1 | 同名行重定义（内容不变，复用旧名） |
| data_element | SR_ExtendedDataRecord_DTC_Priority | Internal DEM_DTC_PRIORITY size=1 | 扩展记录 01 byte1（bits7-4 默认 0 + bits3-0 DTC priority，单字节自然满足） |
| data_element | SR_ExtendedDataRecord_Mileage | External UINT8 OPAQUE | 扩展记录 02 mileage 高字节（bits23-16） |
| data_element | SR_ExtendedDataRecord_Mileage_Low | External UINT16 OPAQUE | 扩展记录 02 mileage 低 16 位 |
| data_element | SR_ExtendedDataRecord_TimeIndication | External UINT8 OPAQUE | 同 TimeIndication（记录 02 byte5） |
| data_element | SR_ExtendedDataRecord_Date_Time | External UINT32 OPAQUE | 记录 02 时间戳高 4 字节 |
| data_element | SR_ExtendedDataRecord_Date_Time_Sec | External UINT8 OPAQUE | 记录 02 时间戳秒字节 |
| did_class | DidClass_DID_0x2B50 | DID=0x2B50 | 引用 SR_Supply_Voltage |
| did_class | DidClass_DID_0x2B51 | DID=0x2B51 | 引用 SR_Vehicle_Speed |
| did_class | DidClass_DID_0x2B52 | DID=0x2B52 | 引用 SR_Odometer_Reserved + SR_Odometer_Mileage |
| did_class | DidClass_DID_0x2B53 | DID=0x2B53 | 引用 SR_Date_Time_TimeStamp + SR_Date_Time_Second |
| freeze_frame_class | FreezeFrame_DTC_DidSet_TypeA | 引用上 4 个 DidClass | 固定名契约；NumberOfIdentifiers=0x04 自然成立（4 个 DidClassRef） |
| freeze_frame_class | FreezeFrame_DTC_DidSet_TypeB | 引用上 4 个 DidClass | 同上 |
| freeze_frame_record | Rec_SnapshotRec_1 | **Update=DEM_UPDATE_RECORD_NO**，Trigger=DEM_TRIGGER_ON_CONFIRMED，RecNum=1 | 01=故障**第一次**发生数据，不再更新 |
| freeze_frame_record | Rec_SnapshotRec_2 | Update=DEM_UPDATE_RECORD_YES，同上，RecNum=2 | 02=故障**最近一次**发生数据 |
| extended_data_record | Record_ExtendedDataRecord0x01 | Trigger=DEM_TRIGGER_ON_CONFIRMED，Update=YES，RecNum=1 | 引用 SR_ExtendedDataRecord_DTC_Priority + Fault_occurrence_counter（2B） |
| extended_data_record | Record_ExtendedDataRecord0x02 | 同上，RecNum=2 | 引用 Ageing_Counter + Mileage(2 个) + TimeIndication + Date_Time(2 个)（10B） |
| extended_data_class | ExtendedDataClass_DTC_Properties | 引用 Record 0x01 + 0x02 | 固定名契约 |
| freeze_frame_rec_num | DTC_Properties_FFRecNumClass | 引用 Rec_1 + Rec_2 | 固定名契约 |

**孤儿清理（生成后手工删，非生成器职责）**：旧 `DidClass_DID_0x0500`、`DidClass_DID_0x9A5D`、旧 11 个快照 SR 容器（`SR_Vehicle_Speed`…`SR_Vehicle_abnormal_messagesOrsignals`，见表外未复用名清单）——均为客户 V0 早期问卷遗留，被新 DID 集取代。

**位打包映射（非字节对齐数据的拆分）**：

| DID/记录 | 需求位定义 | 拆分实现 |
| :--- | :--- | :--- |
| 0x2B52 (3B) | bits23-20 Reserved；bits19-0 Mileage | UINT8 = `(mileage >> 16) & 0x0F`；UINT16 = `mileage & 0xFFFF` |
| 0x2B53 (5B) | bits39-33 Resv；32-26 Year(=x+2000)；25-22 Mon；21-17 Day；16-12 Hour；11-6 Min；5-0 Sec | 40 位值 `V40` 大端打包：UINT32 = `V40 >> 8`；UINT8 = `V40 & 0xFF` |
| 扩展记录 01 byte1 | bits7-4 默认 0；bits3-0 DTC priority | 单字节 `DEM_DTC_PRIORITY`（Dem 内部返回所配优先级 ≤15，高 4 位自然为 0） |
| 扩展记录 02 bytes2-4 | bits23-20 Resv；bits19-0 Mileage | 同 0x2B52 拆分（独立 SR 行，避免复用快照 SR 造成触发/更新语义耦合） |

### 3.2 DCM / CanTP 参数表

| 参数 | 当前值 | 目标值 | 载体 | 对应需求 |
| :--- | :---: | :---: | :--- | :--- |
| DcmDspSession.P2ServerMax | 0.05 s | 0.05 s（✅不变） | 问卷 DcmDspSession sheet | REQ-112 |
| DcmDspSession.P2StarServerMax（3 行） | 2.0 s | **5.0 s** | 问卷 DcmDspSession sheet（V1.5 History 行） | REQ-113 |
| DcmTimStrP2StarServerAdjust | 0.1 | 0.1（✅0x78 间隔 ≈4.9s ≥ 1500ms） | 既有配置 | REQ-113 |
| S3Server | ISO 默认 5s（DcmS3ServerTimeoutOverwrite 未配置） | 5000 ms（✅不变） | 既有配置 | REQ-114 |
| CanTpPaddingByte | 0xAA (170) | **0x00** | CanTp EcucValues 手改 | REQ-95 |
| CanTpBs（Rx N-Sdu） | 8 | **0** | 同上 | REQ-98 |
| CanTpSTmin | 0.02 s | **0.01 s** | 同上 | REQ-99 |
| CanTpNar | 0.07 s | **1.0 s** | 同上 | REQ-103 |
| CanTpNbr | 0.01 s | **0.06 s** | 同上 | REQ-104 |
| CanTpNcr | 0.15 s | **1.0 s** | 同上 | REQ-105 |
| Tx CanTpNas | 0.07 s | **1.0 s** | 同上 | REQ-100 |
| Tx CanTpNbs | 0.15 s | **1.0 s** | 同上 | REQ-101 |
| Tx CanTpNcs | 0.01 s | **0.06 s** | 同上 | REQ-102 |

> CanTp padding activation 两个 N-Sdu 均已开启（保持）；物理/功能寻址 2 个 Rx N-Sdu + 1 个 Tx N-Sdu 全部生效上述参数。

---

## 四、 模块详细设计 (Detailed Design)

### 4.1 模块划分与职责

| 子模块/源文件 | 职责 | 对外接口 | 内部依赖 |
| :--- | :--- | :--- | :--- |
| `tools/autosar_gen/Dem_AutoGen/.../configs/veh_j02.yaml` | `gen_dem_general.extended_freeze_data: true` | — | — |
| `cpj_fawvw/veh_j02/tools/e2e_dem/IDC_DemGeneral_Config_J02_V0.1_20261123.xlsx` | extended_freeze_data sheet 建模（§3.1） | gen_dem_general 输入 | — |
| `tools/autosar_gen/Dcm_AutoGen/.../UDS_Diagnostic_Questionnaire_J02.xlsx` | DcmDspSession sheet P2StarServerMax 2→5 + History V1.5 行 | Dcm_AutoGen 输入 | — |
| `veh_j02/autosar/.../gen/J6B_CanTp_EcucValues.arxml` | 9 参数手改（§3.2） | ISOLAR 重生成输入 | — |
| `veh_j02/evm_cfg/src/evm_cfg_freezeframe_data.cpp` | 新 SR 读回调 + 旧回调/旧采集代码清理 | `Dcm_DemGetSRData_*` | GetVoltValue、g_CAN0_*_st |
| `cpj_*/autosar/.../Dcm/user/Dcm_Dem.h`（integration 手维文件） | 新回调 extern 声明 | — | evm_cfg_freezeframe_data.cpp |

### 4.2 函数级处理流程

```text
Dcm_DemGetSRData_SR_Supply_Voltage(start, buf, len)   // 0x2B50, 2B, f(x)=0.1x
1. u32mv = GetVoltValue(ADC_VBAT_FILT)                 // mV
2. u16  = (u16)(u32mv / 100)                           // 0.1 V/bit
3. clamp(u16, 0, 250)                                  // 物理 0~25V 上限
4. 大端写入 buf

Dcm_DemGetSRData_SR_Vehicle_Speed(start, buf, len)     // 0x2B51, 2B, f(x)=0.01x
1. 若 iBRS_VehSpdVD_u8 无效 或 update_flag 未置 → 写 0xFFFF（无效值）
2. 否则 u16 = (u16)(iBRS_VehSpd_f32 * 100 + 0.5)，clamp(0, 32767)
3. 大端写入 buf

Dcm_DemGetSRData_SR_Odometer_Reserved(...)             // 0x2B52 byte1
1. 写 (uint8)((mileage >> 16) & 0x0F)                  // bits23-20，恒 0（mileage ≤ 0xFFFFF）

Dcm_DemGetSRData_SR_Odometer_Mileage(...)              // 0x2B52 bytes2-3
1. u32 = KBI_Kilometerstand_u32                        // 0xFFFFE=Initial, 0xFFFFF=Error 原样透传
2. 写 (uint16)(u32 & 0xFFFF)，大端

Dcm_DemGetSRData_SR_Date_Time_TimeStamp(...)           // 0x2B53 bytes1-4
1. V40 = ((u64)(BDU_DateYr_u16 - 2000) << 26) | (Mon << 22) | (Day << 17)
       | (Hr << 12) | (Min << 6) | Sec                 // 各字段先 clamp 到需求范围
2. 写 (uint32)(V40 >> 8)，大端
Dcm_DemGetSRData_SR_Date_Time_Second(...)              // 0x2B53 byte5
1. 写 (uint8)(V40 & 0xFF)                              // V40 复用同一打包值

SR_ExtData_TimeIndication / SR_ExtendedDataRecord_TimeIndication:
1. 恒写 0x00

SR_ExtendedDataRecord_Mileage / _Low:
1. 同 0x2B52 拆分（数据源相同，独立实现避免语义耦合）

SR_ExtendedDataRecord_Date_Time / _Sec:
1. 同 0x2B53 打包（数据源相同，独立实现）
```

> 扩展记录 01 的 byte1（`DEM_DTC_PRIORITY`）与 byte2（OCCCTR）、记录 02 byte1（AGINGCTR）为 Dem 内部元素，无需采集代码；DTC priority 值随 Create_DemDTCAttributes 的既有 DTC 属性配置。

**代码清理**：旧快照 SR 回调（`SR_Vehicle_Speed`、`SR_ECU_Voltage`…）随容器删除一并移除实现与 extern；`Evm_CollectFreezeframeData()` 内被注释的旧总线信号采集代码段一并清理（新数据源为实时读取回调，无需周期采集缓存）。

### 4.3 内部数据结构设计

无新增结构。各回调复用 `CEvmFreezeframeData::evm_getInstance()` 单例既有成员访问模式；0x2B53 的 40 位打包在回调栈内以 `uint64` 计算后拆分写入，不落全局。

### 4.4 消息级时序

```text
Tester                       Dcm                    Dem                  EcuAb回调
  |--$19 04 (DTC, rec=01/02/FF)-->|                   |                     |
  |                               |--RetrieveSnapshot-->|                    |
  |                               |                    |--内/外元素读取----->|
  |                               |                    |<--buf(大端)--------|
  |<-------$59 04 + records-------|<-- 组包            |                     |
```

---

## 五、 异常处理、容错与安全机制 (Error Handling & Safety)

| 异常/边界场景 | 潜在风险 | 防御与降级策略 |
| :--- | :--- | :--- |
| 总线信号未收到/无效（车速、里程、时间） | 快照读出垃圾值 | 车速用 `iBRS_VehSpdVD_u8` 有效位判无效返 0xFFFF；里程 0xFFFFE/0xFFFFF 特殊值透传（需求定义）；时间字段 clamp 到需求范围 |
| ADC 电压超量程 | 0x2B50 溢出 | clamp 0~250（0.1V/bit × 25V） |
| 年份异常（BDU_DateYr_u16 含 +2000 偏移） | 打包越界 | `(year - 2000)` 后 clamp 0~99 |
| 生成器重复执行 | 容器重复/误删 | 幂等验证：连续跑两遍，第二遍 0 删 0 增 + diff 为零（dem-general-config-table.md 验证规则） |

---

## 六、 验证、测试与集成要求 (Verification & Integration)

### 6.1 资源消耗与性能基线

| 指标 | 预算/基线 | 测量方法 |
| :--- | :--- | :--- |
| NVM | 扩展数据每 DTC 条目 2B → 12B（+10B），快照总量近似持平（12B→12B/记录） | Dem EventMemory 配置核对；编译后 RAM/ROM 对比 |
| 编译 | GHS 零新增警告 | 10.0.12.42 编译输出核对 |

### 6.2 验收标准

- [ ] Dem 配置生成幂等：`gen_dem_general` 连跑两遍第二遍 0 删 0 增，arxml diff 为零；孤儿容器已手工清除；ISOLAR 校验通过
- [ ] 编译通过（12.42，veh_j02 preset，零新增警告）
- [ ] `$19 04 FF` 读回 0x2B50~0x2B53 四个 DID，字节数 2/2/3/5，字段打包与需求表一致（台架注入总线信号核对）
- [ ] `$19 06` 读记录 01（2B）/02（10B）/FF，字段正确；记录 01 快照在故障首次确认后不再随复现更新（Rec_1 Update=NO）
- [ ] `$10 03`/`$10 02` 响应时间 P2*Server 表现为 5000ms 档（0x78 重试间隔 ≥1500ms）
- [ ] CanTP：多帧响应未使用字节填充 0x00；流控帧 BS=0、STmin=10ms；`$27`/`$22` 长数据连续帧间隔观测 ≈10ms
- [ ] 手动验证（用户，阶段 4）：台架逐项核对上述诊断响应

---

## 附录A：需求追溯矩阵

| 需求编号 | 需求摘要 | 设计章节 | 验证章节/用例 |
| :--- | :--- | :--- | :--- |
| C097FAWVWREQ-722 | 快照记录 01/02/FF + DID 0x2B50~0x2B53 | §3.1 | §6.2 |
| C097FAWVWREQ-723 | 扩展记录 01(2B)/02(10B)，MFK 支持 01/02/FF | §3.1 | §6.2 |
| C097FAWVWREQ-112 | P2Server=50ms | §3.2（已满足，核对项） | §6.2 |
| C097FAWVWREQ-113 | P2*Server=5000ms，0x78 间隔≥1500ms | §3.2 | §6.2 |
| C097FAWVWREQ-114 | S3Server=5000ms | §3.2（已满足，核对项） | §6.2 |
| C097FAWVWREQ-95 | 未使用字节填充 0x00 | §3.2 | §6.2 |
| C097FAWVWREQ-98 | BS=0 | §3.2 | §6.2 |
| C097FAWVWREQ-99 | STmin=10ms（平配，无 CANFD 刷写） | §3.2 / §1.2 | §6.2 |
| C097FAWVWREQ-100~105 | N_As/N_Bs=1000ms、N_Cs/N_Br=60ms、N_Ar/N_Cr=1000ms | §3.2 | §6.2 |

## 附录B：设计决策记录 (ADR 摘要)

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | 快照 SR 全部外部元素 + 读回调实时取数 | 周期采集缓存（旧 Evm_Collect 模式） | 总线信号实时读回调更简单；旧采集代码本就是注释掉的 stub；RX 先例同样走实时回调 |
| 2 | 非对齐字段拆多 SR（UINT8+UINT16 / UINT32+UINT8） | 单 OPAQUE 大元素手撕位 | ETAS 外部元素以 ApplicationDataType 定型，2/4 字节整型原生支持；拆分在回调内完成对 Tester 透明（Dem 按容器序拼接） |
| 3 | 扩展记录 01 byte1 用 `DEM_DTC_PRIORITY` 内部元素 | 外部 SR 每单查表 | DEM_DTC_PRIORITY 原生返回所配 DTC 优先级，语义吻合且扩展记录允许内部元素（RX 实测） |
| 4 | 记录 02 里程/时间戳独立 SR 行不复用快照容器 | 复用同一 SR 容器 | 拆复用会耦合快照/扩展两组触发语义；复用仅省几个容器，可读性代价高 |
| 5 | CanTp arxml 手改且置于 Dem/Dcm AutoGen 之前 | 生成后再改 | ISOLAR BSW 重生成消费 EcucValues，后改会被下次重生成冲掉 |
| 6 | STmin 平配 10ms 不分 APP/boot | APP 10ms / boot 1ms | REQ-99 备注（26/11/11）明确当前实现 10ms 平配、无 CANFD 刷写需求 |

## 附录C：开放问题 (Open Issues)

| # | 问题描述 | 影响 | 责任方 | 跟踪截止时间 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 旧快照 DID 0x0500/0x9A5D 移除是否影响客户侧既有测试脚本 | 若客户脚本仍读 0x0500 需同步知会 | 需求方（zane.zhang） | 阶段 4 验证前 |
