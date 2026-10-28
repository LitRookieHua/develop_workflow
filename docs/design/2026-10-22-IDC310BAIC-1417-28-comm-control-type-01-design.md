# ⚙️ 0x28 服务通信类型参数 01（常规应用报文）支持 需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | UDS 0x28 CommunicationControl 通信类型参数扩展 | **所属软件层级** | BSW (Diag Stack: Dcm + ComM) |
| **文档状态** | 🟡 待评审 | **安全与质量要求** | MISRA C:2012 ｜ 零警告 |
| **模块负责人 / 作者** | @Hua.Yao | **关联输入/输出** | 📑 IDC310BAICREQ-6178 需求单 |

> **📝 变更记录**
> * `2026-10-22`｜@Hua.Yao｜V1.0｜通信类型参数 01 由不支持改为支持的配置设计

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景与痛点**：客户规范表 23 更新——0x28 服务的通信类型参数（communicationControlType，请求第 2 字节）`01 常规应用报文` 由"不支持（N）"更新为"支持（Y）"。原实现（需求 IDC310BAICREQ-817 → Story IDC310BAIC-22）仅配置了 `03 常规应用报文和网络管理报文`，当前 `01` 请求会被 DCM 拒绝（NRC 0x31 requestOutOfRange）。
* **核心目标**：`01` 时仅对常规应用报文执行子功能指定的收/发控制，网络管理报文不受影响；`02` 仍不支持（NRC 0x31），`03` 行为保持不变。
* **设计原则**：仅调整 DCM 通信控制配置（`DcmDspComControl` 容器族），不改 DCM 代码逻辑。

### 1.2 适用范围 (Scope)

* **适用控制器/平台**：BAIC N60（J6 平台，工作区 `02_Workspace_J6`，仓库 `mcu_app_j6`）
* **核心职责**：0x28 请求 `communicationControlType` 分发——`01` → 仅应用通信控制；`03` → 应用 + 网管通信控制
* **范围边界**：不改子功能（表 22）行为，不改 0x28 会话/安全权限，不涉及 zos_msg / version_did 仓库

### 1.3 术语与缩略语

| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| controlType | communicationControlType | 0x28 请求第 2 字节：01/02/03 |
| NRC 0x31 | requestOutOfRange | 不支持的 controlType 值的否定响应 |

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | ISO 14229-1 (UDS) | 2020 | 0x28 服务语义 |
| R2 | [IDC310BAICREQ-6178](https://jira.imotion.ai:7070/browse/IDC310BAICREQ-6178) | — | 需求来源（replaces IDC310BAICREQ-817） |
| R3 | AUTOSAR DCM SWS | 4.x | DcmDspComControl 配置规格 |
| R4 | Obsidian《J6B DCM Configuration Analysis》 | — | DcmDspComControl 配置结构背景（J6B 同构参考） |

### 1.5 设计约束与假设

* **技术约束**：AUTOSAR 生成代码——人工修改必须加 `<N60PATCH P<id>>` 标记防生成覆盖（若改动落在 `cpj_*/autosar/` 生成产物）；改动在 DCM 配置（arxml/生成产物）层面完成
* **外部假设**：ComM 通道（如 CANFD 系）已配置应用/网管报文分类，`01` 控制路径可复用现有 `ComM_CommunicationAllowed` 调用链
* **假设的验证方式**：阶段 3 在服务器上读取 N60 当前 `DcmDspComControl` 实际配置核对；台架验证 `01` 时网管报文仍在发送

---

## 二、 架构设计与模块间交互 (Architecture & Interaction)

> 本需求仅涉及 DCM 配置参数调整，BSW 模块调用链不变，本章精简为调用链说明。

### 2.1 模块依赖关系与调用链

```text
Tester 发 28 <sub-function> <controlType>
  → Dcm (Dsd 服务表 ComControlClass 0x28, EXTENDED 会话)
    → controlType 校验（DcmDspComControlTypeRef 配置决定 01/02/03 支持性）
      → 01/03: ComM_CommunicationAllowed(<引用通道>, enable/disable)  → 应用报文收发控制
      → 03 额外: 网管控制路径
      → 02: 未配置 → NRC 0x31（保持）
```

* 上游：诊断请求（CAN/DoIP 诊断通道）；下游：ComM（通道级通信控制）
* 现有配置背景（J6B 同构参考，R4）：`DcmDspComControlAllChannel` 通过 `DcmDspAllComMChannelRef` 引用 ComM 通道；DCM 据此调用 `ComM_CommunicationAllowed`

---

## 三、 核心逻辑、状态机与参数规则 (Core Logic & Parameters)

> 本需求不改状态机与调度，仅改可配置参数。

### 3.1 可配置参数表 (Configurable Parameters)

| 参数分类 | 参数名称 (Parameter Name) | 可配置范围 | 目标值 | 参数作用 |
| :--- | :--- | :--- | :--- | :--- |
| 通信类型 | `DcmDspComControlType` 族（`DcmDspComControlNormalCom` 等，以 N60 实际配置项为准） | 配置/不配置 | 增加 controlType 01 的支持配置 | 决定 0x28 第 2 字节 01/02/03 的接受性与控制范围 |
| 通道引用 | `DcmDspAllComMChannelRef` | ComM 通道集合 | 复用现有通道引用 | `01` 控制的作用范围（与 03 一致的应用报文通道） |

### 3.2 请求行为规格（验收对账表）

| controlType | 期望行为 |
| :--- | :--- |
| 01 | 正响应；仅应用报文按子功能控制，网管报文不受影响 |
| 02 | NRC 0x31（不变） |
| 03 | 正响应；应用 + 网管报文均按子功能控制（不变） |

---

## 四、 模块详细设计 (Detailed Design)

### 4.1 影响分析结论（阶段 3 实测核对）

N60 当前 0x28 全链路：

1. **请求校验**（"01=N"的实现点）：`cpj_baic/dia_cfg/var/src/vehicle/n60/ov_dia_notification/ov_dia_notification.cpp` `ServiceRequestSupplierNotification_..._Indication()` 的 `case 0x28:` —— `RequestData[1] != 0x03` 即回 NRC 0x31（01/02 均被拒）
2. DCM 生成代码（`BswRta/src/bsw/Dcm/src/Dsp/Uds/DcmDspUds_CC.c`）：commType 1-3 全部走标准模式推导（`Dcm_Prv_GetCommModeType_u8` → DCM_*_NORM / _NM / _NORM_NM）
3. 模式传播链在 N60 上为应答层面：BswM 的 `BswM_MRP_DCM_ComControl_Can_Network_ETAS` 挂 0 条规则（RTA 日志亦警告 mode request port not used）；RTE 模式（`Rte_ModeCurrent_7`）无有效应用消费者；`DcmAppl_DcmSwitchCommunicationControl` / `DcmAppl_DcmCommControlConditionCheck` / `DcmAppl_DcmConfirmation` 均为空模板

即 0x28 在 N60 上的"支持"是对话框应答层面的（03=Y 的原实现同样只是正响应），01 放行后与 03 行为完全一致——满足表 23 更新要求。

### 4.2 修改点清单

| # | 文件 | 修改 | 属性 |
| :--- | :--- | :--- | :--- |
| 1 | `cpj_baic/dia_cfg/var/src/vehicle/n60/ov_dia_notification/ov_dia_notification.cpp` `case 0x28:` | commType 校验由整字节 `!= 0x03` 改为低 4 位掩码 `(RequestData[1] & 0x0F) != 0x01 && != 0x03`；NRC 0x22 检查移到 commType 校验之前（ISO 14229-1 Annex C 优先级）；注释同步更新 | dia_cfg 手写代码，无需 PATCH 标记 |

不改动：sub-function（表 22）校验（DCM 生成层已处理 0-3）、suppress 位行为（4023 已验证）、02 的拒绝（保持 NRC 0x31）、BswM/RTE/ComM 配置。

> 2026-10-22 PR 审核（OCR）修正：初版为整字节比较且 NRC 0x31 在 0x22 之前，评审指出与 ISO 14229-1 Annex C NRC 优先级（0x22 > 0x31）及 DcmDspUds_CC.c 的低 4 位掩码解码不一致，已采纳修复（develop c1f335a71 / B230 3ac19544b）。

---

## 六、 验证、测试与集成要求 (Verification & Integration)

### 6.1 验证方案

* **诊断自动验证**（`tools/DiagnosticTester`）：EXTENDED 会话下——
  1. `28 00 01` / `28 03 01` 等 sub-function 组合 → 期望正响应 `68 00 01`
  2. `28 00 02` → 期望 NRC `7F 28 31`
  3. `28 00 03` → 正响应（回归）
* **台架手动验证**（用户执行）：`01` 禁发后总线上应用报文停发、网管报文持续；`28 00 01` 恢复后应用报文恢复

### 6.2 验收标准

- [ ] 表 23 全组合行为符合 §3.2 规格（01 正响应、02 NRC 0x31、03 不回归）
- [ ] 台架确认 01 控制仅作用于应用报文
- [ ] 编译零错误零警告；develop 与 release B230 两分支均合入

---

## 附录A：需求追溯矩阵

本需求仅涉及 IDC310BAICREQ-6178 表 23 一项参数（01 N→Y），追溯：需求 → §1.1/§3.2 → §6.1 用例。

## 附录B：设计决策记录 (ADR 摘要)

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | 仅配置层修改，不改 DCM 源码 | 修改 Dcm.c 逻辑拦截 | AUTOSAR 标准配置项已覆盖该行为，代码侵入无必要 |
| 2 | develop 先行、release B230 cherry-pick | 两分支独立修改 | 遵循 workspace-setup.md §5 既定规则，避免双份手工修改漂移 |
