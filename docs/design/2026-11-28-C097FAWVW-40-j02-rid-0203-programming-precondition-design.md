# ⚙️ J02 RID 0x0203 编程前置条件检查 需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | 统一诊断服务 / RoutineControl RID 0x0203 | **所属软件层级** | CDD (dia_cfg 0x31) + Dcm 配置 |
| **文档状态** | 🟢 开发中 | **安全与质量要求** | MISRA C:2012 ｜ 零警告 |
| **模块负责人 / 作者** | @Hua.Yao | **关联输入/输出** | 📊 `UDS_Diagnostic_Questionnaire_J02.xlsx` ｜ 📑 C097FAWVWREQ-724 / C097FAWVWREQ-33 |

> **📝 变更记录**
> * `2026-11-28`｜@Hua.Yao｜V1.0｜完成 RID 0x0203 编程前置条件检查设计（问卷新增 RID + 0x31 处理体 + gen_rid_code 保留增强）

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标
* **业务背景与痛点**：J02（一汽捷达 C097，J6 平台）实现 DoIP 预编程流程。诊断仪在进入编程前用 RoutineControl（$31）RID 0x0203 检查 ECU 的安全前提条件；ECU 以位掩码返回未满足项列表，全部满足时响应不含状态字节。当前 J02 的 0x31 处理体只实现 RID 0x8510/0x8511，无 0x0203。
* **核心目标**：
  1. 在 Extended / Locked / App Unlocked 会话下响应 `31 01 02 03`；全部满足返回 3 字节 `71 01 02 03`，否则追加 1 字节 routineStatus 位掩码（4 字节响应）。
  2. 位掩码按需求定义：bit0 车速<3km/h、bit1 发动机转速（固定 0）、bit2 T15 ON、bit3 9V<电压≤16V、bit4 换挡在 P、bit5 电驱就绪 off、bit6-7 固定 0（bit=1 表示未满足）。
* **设计原则**：
  1. **高内聚低耦合**：前置条件判定集中在一个静态辅助函数内，处理体只做取值/组包，不改动既有 RID 逻辑。
  2. **可生成性**：RID 的定义（会话/安全/长度）由问卷 + Dcm_AutoGen 生成，人工代码限定在自动生成区之外，配合 gen_rid_code 保留机制避免重生成覆盖。

### 1.2 适用范围 (Scope)
* **适用控制器/平台**：J02（`cpj_fawvw/veh_j02`，J6 平台）。
* **核心职责**：RID 0x0203 StartRoutine 的前置条件位掩码计算与响应组包。
* **范围边界**：不实现 StopRoutine（0x02）/RequestRoutineResults（0x03）的业务逻辑（问卷中 0x02/0x03 与 0x0203 记录按需求单仅登记 0x01）；不改动 DoIP 刷写流程其余部分。

### 1.3 术语与缩略语
| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| RID | Routine Identifier | 例程标识符，本需求为 0x0203 |
| T15 | Terminal 15 | 点火 ON 状态，J02 由 `BDU_VehPwrMod` 反映（0x02 Standby / 0x03 Driving） |
| VD | Valid Flag | 信号有效标志，`iBRS_VehSpdVD`，0x01=Valid |
| Precondition | Programming Precondition | 编程前置条件（REQ-33 定义的 6 项） |

### 1.4 参考文档
| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | C097FAWVWREQ-724（RID 0x0203 需求单） | — | 会话矩阵、响应位定义、可变长度 |
| R2 | C097FAWVWREQ-33（编程前置条件需求单） | — | 6 项前置条件定义、信号表达式、"不可用视为满足" |
| R3 | C097FAWVW-4（DoIP 刷写 Story） | — | REQ-33 的既有实现单，预编程流程上下文 |
| R4 | ISO 14229-1 | 2020 | $31 RoutineControl 语义 |
| R5 | J02 CAN 矩阵 `RG-003287_FVW_ADAS_CANFD_Matrix_V3.3.dbc` | V3.3 | 信号接收方定义 |

### 1.5 设计约束与假设
* **技术约束**：Classic AUTOSAR；0x31 处理体位于 `dia_cfg/src/0x31/*.cpp`（CPP，人工 + 生成混合）；Dcm 配置由 Dcm_AutoGen 从 UDS 问卷生成，问卷三副本（工具副本 / mcu `dia_cfg/doc/` / 模板）需同步。
* **外部假设**：
  1. `iBRS_01`（`iBRS_VehSpd`/`iBRS_VehSpdVD`）、`BDU_0`（`BDU_VehPwrMod`）、`VCU_VehInfo`（`VCU_LoglGearStsAct`）由 Com 正常接收并更新 `update_flag`。
  2. `VCU_PtRdy` 在矩阵 V3.3 接收方为 `Vector__XXX`，本 ECU 未接收、结构体无该字段（见附录 C 开放问题）。
* **假设的验证方式**：台架用固定帧模拟 DBC 信号，按位掩码逐项验证；未接收信号用"信号缺失 → bit 保持 0"验证。

---

## 二、 架构设计与模块间交互 (Architecture & Interaction)

### 2.1 模块依赖关系与调用链
* **上游调用者 / 依赖模块**：Dcm → 0x31 处理体分发；信号来自 Com 的 `valin_cfg_pdu_types.hpp` 端口结构体；供电电压来自 `VoltM`（`KL30_GetVoltValue()`）。
* **下游被调 / 支撑模块**：`VoltM`（KL30 电压），Com 端口数据（`net_cfg` 更新）。
* **核心交互时序 / 依赖方向**：
  `Dcm 收到 31 01 02 03` ➡️ `RID 分发表 → 0x0203 处理体` ➡️ `读 Com 端口 + VoltM 电压 → 计算位掩码` ➡️ `组 resData / resDataLen` ➡️ `Dcm 组正响应`

### 2.2 接口规范定义 (APIs & Callouts)
| 接口类型 (API / Callback) | 函数原型 / 接口名称 | 输入/输出参数说明 | 核心职责与调用时机 |
| :--- | :--- | :--- | :--- |
| **Dcm 处理体** | `ov_dia_0x31_rid_check_programming_preconditions::m_fillResponseBufferStartReqCustomer(...)` | IN: 请求/长度；OUT: `resData`/`resDataLen`/NRC | StartRoutine 0x01 处理：计算前置条件位掩码并组包 |
| **内部辅助** | `static uint8_t CalcProgrammingPreconditionStatus(void)` | OUT: 位掩码（bit=1 未满足） | 集中读取信号并计算状态，放在自动生成区之外 |
| **依赖 API** | `KL30_GetVoltValue()` | OUT: 供电电压 mV | 读取自身 KL30 电压（`ADC_VBAT_FILT`） |

### 2.3 并发与调度上下文
| 接口 / 共享资源 | 执行上下文 (Task/ISR Cat1/Cat2) | 临界区保护方式 | 备注 |
| :--- | :--- | :--- | :--- |
| 0x0203 处理体 | Dcm 诊断 Task（Cat2） | 无需额外临界区 | 仅读取 Com 端口快照与 VoltM 单值，无写共享状态 |
| `update_flag` | Com 接收上下文写、诊断 Task 读 | 单字节读写，原子 | 表示信号自上次读后是否更新过（见 §4.2） |

* **禁止事项**：处理体内不得调用阻塞 API；不得写 Com 端口数据。

### 2.4 初始化时序
* **Init 调用顺序**：无新增初始化。0x0203 处理体在 Dcm 完成初始化后由分发调用；Com 端口在 `Com_Init` 后开始更新。
* **依赖就绪条件**：电压读取依赖 VoltM 初始化完成；首帧前 `update_flag=0`，按"信号不可用 → 视为满足"处理。

---

## 三、 核心逻辑、状态机与参数规则 (Core Logic & Parameters)

### 3.1 核心状态机设计 (State Machine)
本需求无状态机；RID 为单次查询语义，每次请求独立计算位掩码。

### 3.2 可配置参数表 (Configurable Parameters / Pre-Compile)
| 参数分类 | 参数名称 (Parameter Name) | 可配置范围 | 默认推荐值 | 参数作用与对系统性能的影响 |
| :--- | :--- | :--- | :---: | :--- |
| 阈值 | 车速上限 | 固定 3.0 km/h | `3.0f` | 车速<3km/h 视为满足 (bit0=0) |
| 阈值 | 电压下限 | 固定 9000 mV | `9000` | 9V<电压 视为满足 (bit3=0)，严格大于 |
| 阈值 | 电压上限 | 固定 16000 mV | `16000` | 电压≤16V 视为满足 (bit3=0)，含等于 |

---

## 四、 模块详细设计 (Detailed Design)

### 4.1 模块划分与职责
| 子模块/源文件 | 职责 | 对外接口 | 内部依赖 |
| :--- | :--- | :--- | :--- |
| `dia_cfg/src/0x31/ov_dia_0x31_routine_by_identifier_handler.cpp` | RID 注册表 + 处理体；本需求新增 RID 0x0203 类和处理体 | Dcm 分发调用 | `valin_cfg_pdu_types.hpp`、`VoltM_cfg.h` |
| `tools/autosar_gen/Dcm_AutoGen/Dcm_AutoGen_User/gen_rid_code.py` | RID 代码生成器；增强为保留已有方法体 | 生成 4 个自动区 | 问卷 RID 表 |
| `UDS_Diagnostic_Questionnaire_J02.xlsx`（RID List） | 新增 RID 0x0203 行 | Dcm_AutoGen 输入 | — |

### 4.2 函数级处理流程

```text
CalcProgrammingPreconditionStatus() -> uint8 status (bit=1 未满足)
0. status = 0
1. bit0 车速<3km/h:
   若 iBRS_01.update_flag 且 (iBRS_VehSpdVD == 1) 且 非(iBRS_VehSpd < 3.0f) -> status |= 0x01
   （update_flag=0 或 VD!=Valid -> 信息不可用 -> 视为满足，不置位）
2. bit1 发动机转速: 固定 0（不判断）
3. bit2 T15 ON:
   若 BDU_0.update_flag 且 非(BDU_VehPwrMod==0x02 或 0x03) -> status |= 0x04
   （update_flag=0 -> 视为满足）
4. bit3 供电电压 9V<U<=16V:
   v = KL30_GetVoltValue() // mV，自身电压始终可用，必判
   若 非(9000 < v && v <= 16000) -> status |= 0x08
5. bit4 换挡 P:
   若 VCU_VehInfo.update_flag 且 (VCU_LoglGearStsActQlfr != 2 /*Invalid*/) 且 非(VCU_LoglGearStsAct==0x01) -> status |= 0x10
   （update_flag=0 或 Qlfr=Invalid -> 视为满足）
6. bit5 电驱就绪 off: 固定 0（VCU_PtRdy 未接收，见附录C）
7. bit6-7: 固定 0
8. return status
```

```text
m_fillResponseBufferStartReqCustomer():
1. status = CalcProgrammingPreconditionStatus()
2. if status == 0:
     resDataLen = 3u;   // 71 01 02 03
   else:
     resData[3] = status; resDataLen = 4u;  // 71 01 02 03 <status>
3. *dataNegRespCode_u8 = idia::E_POSITIVE_RESPONSE
4. 返回 OK
```

### 4.3 内部数据结构设计
复用 Com 端口结构体（`valin_cfg_pdu_types.hpp`）：

```c
/* Com 端口结构（既有，示意关键字段） */
CAN0_iBRS_01_PortType   : update_flag, iBRS_VehSpdVD_u8, iBRS_VehSpd_f32, ...
CAN0_BDU_0_PortType     : update_flag, BDU_VehPwrMod_u8, ...
CAN0_VCU_VehInfo_PortType: update_flag, VCU_LoglGearStsAct_u8, VCU_LoglGearStsActQlfr_u8, ...
```
* **容量/预算论证**：本需求无新增缓冲；响应最多 4 字节，栈上临时变量即可。

### 4.4 消息级时序

```text
Dcm Task
  |--31 01 02 03--> RID 分发 --> m_fillResponseBufferStartReqCustomer
  |                                   |--Calc...: 读 Com 端口快照 + KL30 电压
  |                                   |--组 resData(3/4B), resDataLen
  |<------ 71 01 02 03 [status] ------|
```

---

## 五、 异常处理、容错与安全机制 (Error Handling & Safety)

| 异常/边界场景 | 潜在风险 | 通用防御与降级策略 |
| :--- | :--- | :--- |
| 前置条件信号丢失（`update_flag=0` / VD 非 Valid / Qlfr=Invalid） | 误判为不满足导致禁止刷写 | 按 REQ-33"无信息则视为满足"：不置位 |
| 电压超范围 | 编程风险 | bit3 置位（电压自身可用，必判） |
| 未接收信号（VCU_PtRdy） | 编译失败 / 误判 | 不引用未定义字段；bit5 固定 0（视为满足） |
| Dcm 会话/安全不支持 | 越权执行 | 问卷登记会话/安全矩阵：Default N / Programming N / Extended Y / Locked Y / App Unlocked Y / Boot Unlocked N / iMotion N |

* **安全机制追溯**：REQ-33 编程前置条件 → §4.2 位掩码计算；REQ-724 响应格式 → §4.2 组包。

---

## 六、 验证、测试与集成要求 (Verification & Integration)

### 6.1 资源消耗与性能基线
| 指标 | 预算/基线 | 测量方法 |
| :--- | :--- | :--- |
| CPU 负载 | < 10 us / 调用 | 结构简单，单次查询 |
| RAM / ROM | 无新增静态 RAM；ROM 增加 < 2 KB | map 文件对比 |

### 6.2 验收标准 (Acceptance Criteria)
- [x] 编译通过（J6 编译，零警告）。
- [x] Extended 会话解锁后 `31 01 02 03`：
  - 全部满足 → 响应 `71 01 02 03`（3 字节）；
  - 任一未满足 → 响应 `71 01 02 03 <status>`（4 字节），对应 bit 置位。
- [ ] 逐位验证：bit0 车速、bit2 T15、bit3 电压、bit4 挡位；bit1/bit5/bit6/bit7 恒 0。
- [x] 会话/安全矩阵验证：Default/Programming 下拒绝（NRC），Extended + 解锁后通过。
- [x] 问卷新增行的 Dcm 配置（会话/安全/长度）与需求单一致。

### 6.3 台架验证结果 (2026-11-28, J02 cpj_fawvw_j02_d310 / J6B EVM PLUS)
| 项 | 手段 | 结果 |
| :--- | :--- | :--- |
| 会话/安全矩阵、正响应 3 字节、NRC13 | `DiagnosticTester` 用例 `testcase/j02/rid_0203_precondition/rid_0203_precondition.yaml` | 8/8 PASS（Default/Prog NRC31、Ext 未解锁正响应、App 解锁正响应、超长 NRC13） |
| bit3 电压 | 程控电源调到 8 V，用例 `volt_check.yaml` | PASS，响应 `71 01 02 03 08` |
| bit2 T15 | `tests/harness/dcm_rid_0203_precondition/inject_and_query.py` 注入 BDU_0 `BDU_VehPwrMod=0` | PASS，响应 `71 01 02 03 04` |
| bit0 车速 / bit4 挡位 | 同上，注入 iBRS_01 车速 5 km/h、VCU_VehInfo 挡位 D | **无效**：被注入帧未改变状态字（bit0/bit4 保持 0）。bit2 同通道注入即生效，说明通道与发送本身正常；怀疑 iBRS_01 / VCU_VehInfo 在本变体的 Com 收信配置或信号位定位与 DBC 不一致，停在待查（用户指示先走合流）。 |
| bit1 / bit5 / bit6 / bit7 | 代码路径固定 0 | 静态确认 |

> bit0/bit4 后续排查方向：核对 `Com` 收信 PDU 中 iBRS_01、VCU_VehInfo 的 signal 起始位与更新标志位，确认注入帧的 byte/bit 定位（当前按 DBC Intel 起始位推算）。

---

## 附录A：需求追溯矩阵
| 需求编号 | 需求摘要 | 设计章节 | 验证章节/用例 |
| :--- | :--- | :--- | :--- |
| REQ-724 | RID 0x0203 StartRoutine、会话矩阵、可变长度响应 | §3.2 / §4.2 / §5 | §6.2 |
| REQ-33 §1 | 6 项前置条件定义与表达式 | §4.2 | §6.2 逐位验证 |
| REQ-33 §2 | 未满足列表位掩码、bit1 固定 0 | §4.2 组包 | §6.2 |
| REQ-33 备注 | 无信息视为满足 | §4.2 / §5 | §6.2 信号丢失用例 |

## 附录B：设计决策记录 (ADR 摘要)
| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | VCU_PtRdy 未接收 → bit5 恒 0（视为满足） | 请求整车补发 / 改用其他信号 | 矩阵 V3.3 接收方为 Vector__XXX，本 ECU 无该信号；REQ-33 允许"不可用视为满足"（用户确认，记开放项） |
| 2 | 位掩码计算抽为自动生成区外的静态辅助函数 | 直接写进处理体 | 处理体处于 gen_rid_code 自动生成区，重生成会覆盖 |
| 3 | 增强 gen_rid_code 保留已有方法体 | 每次手工重填 / 加 patch 标记 | 与 gen_did_code 保留机制一致，幂等重生成不破坏人工逻辑 |
| 4 | 电压严格 9000 < mV <= 16000 | 含下限 / 用 9.0/16.0 浮点 | 需求写"9V＜供电电压≤16V"，严格大于 9V、含等于 16V |

## 附录C：开放问题 (Open Issues)
| # | 问题描述 | 影响 | 责任方 | 跟踪截止时间 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `VCU_PtRdy` 在矩阵 V3.3 接收方为 Vector__XXX，本 ECU 未接收，bit5 恒 0 | 电驱就绪条件无法真实校验，按"不可用视为满足"处理 | 需求方 / 矩阵维护方 | 待需求方确认是否需补接收 |
| 2 | 电压阈值取 mV 整数比较（9000/16000） | 与浮点阈值边界一致性 | 本方 | 已按 `ov_dia_notification.cpp` 既有阈值实现 |
