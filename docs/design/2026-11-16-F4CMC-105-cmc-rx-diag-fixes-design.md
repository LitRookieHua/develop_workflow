# ⚙️ CMC RX 诊断修复（编程会话停发/0x27 seed与计数器/Dem 配置）设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | CMC_RX_J6B 诊断修复合集（0x10 会话通信控制 / 0x27 SecurityAccess / Dem 环境数据） | **所属软件层级** | 诊断应用层（ov_dia / dia_cfg）+ BSW 集成层（Dcm integration）+ Dcm Lcfg（生成代码 patch） |
| **文档状态** | 🟡 待评审 | **安全与质量要求** | MISRA C:2012 ｜ 零警告 |
| **模块负责人 / 作者** | Hua.Yao / Claude | **关联输入/输出** | 🐞 [F4CMC-99](https://jira.imotion.ai:7070/browse/F4CMC-99) / [100](https://jira.imotion.ai:7070/browse/F4CMC-100) / [101](https://jira.imotion.ai:7070/browse/F4CMC-101) / [102](https://jira.imotion.ai:7070/browse/F4CMC-102) / [103](https://jira.imotion.ai:7070/browse/F4CMC-103) ｜ 📑 [F4CMC-105](https://jira.imotion.ai:7070/browse/F4CMC-105) ｜ 需求 [CMCRXJ6B-26](https://jira.imotion.ai:7070/browse/CMCRXJ6B-26) / [28](https://jira.imotion.ai:7070/browse/CMCRXJ6B-28) / [42](https://jira.imotion.ai:7070/browse/CMCRXJ6B-42) / [43](https://jira.imotion.ai:7070/browse/CMCRXJ6B-43) |

> **📝 变更记录**
> * `2026-11-16`｜Hua.Yao / Claude｜V1.0｜初版：五问题合一修复 Story，99/102/103 修复方案 + 100/101 可行性评估（用户手动改）

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

实车测试（版本包 ci.imotion.ai/package/21180，2026-11-16 reportor Siyuan.Liu）暴露五个诊断问题（5-5 必现），五合一 Story F4CMC-105 修复：

| # | 问题 | 根因 | 修复归属 |
| :--- | :--- | :--- | :--- |
| 99 | 0x10 02 进编程会话不停发应用报文 | BswM 会话→Com 控制规则未接线 | **本 Story 修复**（Dcm 集成回调） |
| 102 | 0x27 连续请求 seed 不相同 | `AppSecurityGetSeed()` 累加式生成 | **本 Story 修复**（App 层） |
| 103 | 3 败+延迟到期后错误计数被清零 | `ResetAttemptCounter_b = TRUE` | **本 Story 修复**（Dcm Lcfg patch） |
| 100 | 快照 DID 为 GAC 遗留配置 | DEXT Dem 配置未按 RX 需求更新 | **用户手动改**（DEXT+重生成） |
| 101 | 扩展数据缺 Aged counter | 同上 | **用户手动改**（DEXT+重生成） |

### 1.2 适用范围 (Scope)

* **适用控制器**：CMC_RX_J6B 一体机（仓库 `mcu_app_j6` / `cpj_cmc`，M 核诊断）
* **范围边界（99/102/103）**：`cpj_cmc/autosar/rx/BswRta/integration/.../DcmAppl_DcmSesCtrlChangeIndication.c`（集成者模板，重生成不覆盖）、`cpj_cmc/dia_cfg/src/0x27/ov_dia_0x27_security_access.cpp`（hand-written）、`cpj_cmc/autosar/rx/BswRta/src/bsw/Dcm/Dcm_Lcfg_DspUds.c`（生成代码，patch 标记）。不涉及 BswM DEXT 重配置、Dem 配置（100/101 另行处理）、autosar 全量重生成。

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | CMCRXJ6B-26 / 28 / 42 / 43 | — | 需求原文 |
| R2 | ISO 14229-1 (UDS) | 2020 | 0x10/0x27 语义、NRC 35/36/37 |

### 1.5 设计约束与假设

* **技术约束**：代码修改一律 SSH 在 10.0.12.42 执行；MISRA / 零警告；autosar 生成代码改动必须加 patch 标记（[autosar-code-generation.md](../../.claude/references/autosar-code-generation.md)）。
* **外部假设**：诊断报文（Dcm→CanTp→CanIf）不经 Com IPDU 组，停 Com TX 组不影响诊断通信（已核对 Com 层职责划分）。

---

## 二、 架构设计与模块间交互 (Architecture & Interaction)

### 2.1 F4CMC-99 调用链

```text
Tester: 10 02 (编程会话)
  → Dcm Dsc → Dcm_Dsl_Session.c:92 Dcm_SesCtrlChangeIndication(old,new)
      → DcmAppl_DcmSesCtrlChangeIndication()   ← 本次修改点（原空模板）
          → new==PROGRAMMING: Com_IpduGroupStop(CAN0_Tx / CAN1_Tx)
          → old==PROGRAMMING: Com_IpduGroupStart(CAN0_Tx / CAN1_Tx, FALSE)
  → Com TX 组停 → 应用周期报文（ACCS_FCM 等）停发；诊断 RX/TX 不经 Com 组不受影响
```

* BswM 路线评估（已否决）：`BswM_Cfg_Rule_cast[10]` 仅 10 条 ESH 规则，DCM 会话 MRP 关联规则数 0；会话条件/LE/动作列表均定义但零引用——补 BswM 规则需 DEXT+ISOLAR 整包重生成，与集成回调等价但成本高一个量级。
* S3 超时回默认会话同样走该回调，TX 恢复路径自动覆盖。

### 2.2 F4CMC-102/103 调用链

```text
27 01 → DcmDspUds_Seca.c
  seed 请求: NRC 判定(:104 借用/锁, :110 延迟未到 NRC37)
            → 延迟已到期且 ResetAttemptCounter_b==TRUE → 清计数(:117-125) ← 103 缺陷点
            → AppSecurityGetSeed()（ov_dia_0x27）← 102 缺陷点（累加）
  key 请求: CompareKey 失败 → HandleNRCForCompareKey(:331-373)
            → 计数<3 → NRC35；计数≥3 → 重装延迟 + NRC36(NRC0x36MAXDELAYCOUNT=ON)
```

---

## 三、 核心逻辑设计

### 3.1 F4CMC-99：会话切换停/恢复 Com TX

```c
void DcmAppl_DcmSesCtrlChangeIndication(Dcm_SesCtrlType SesCtrlTypeOld, Dcm_SesCtrlType SesCtrlTypeNew)
{
    if (SesCtrlTypeNew == DCM_PROGRAMMING_SESSION)
    {
        Com_IpduGroupStop(ComConf_ComIPduGroup_ComIPduGroup_Can_Network_CAN0_Tx);
        Com_IpduGroupStop(ComConf_ComIPduGroup_ComIPduGroup_Can_Network_CAN1_Tx);
    }
    else if (SesCtrlTypeOld == DCM_PROGRAMMING_SESSION)
    {
        Com_IpduGroupStart(ComConf_ComIPduGroup_ComIPduGroup_Can_Network_CAN0_Tx, FALSE);
        Com_IpduGroupStart(ComConf_ComIPduGroup_ComIPduGroup_Can_Network_CAN1_Tx, FALSE);
    }
}
```

* include：`Com.h`（API）+ `Com_Cfg_SymbolicNames.h`（组 id 宏 CAN0_Tx=2 / CAN1_Tx=3）。
* `Start(..., FALSE)`：不初始化缓冲，恢复既有发送节奏（与 BswM 非重初始化路径一致）。

### 3.2 F4CMC-102：seed 稳定语义（App 层重写）

> **2026-11-17 GAC 对比结论**（用户要求对比 GAC 0x27 后定案）：GAC 与 RX 算法层不兼容（GAC 4 字节 seed + `computeKey()`，RX 2 字节 + `seedToKeyApp/Boot()` mask 表）——**算法保持 RX**；GAC 的 seed 生成同为累加式（不能修复 102），stable-seed 修复保留；GAC 特有的 Z016 manufactory 模式检查（RX 中被注释）**评估后不启用**（用户指示 NVM 不添加）。最终 0x27 方案即下述 stable-seed + 已解锁回 0，无 NVM 改动。

```text
AppSecurityGetSeed():
  if 已解锁（Dcm_GetSecurityLevel == L1(0x01)）:
      seed = 0
  else if g_seedValid == FALSE:
      g_seedApp_au8 = 随机生成（imo_GetRandom_u16，0→0x0001，非累加）
      g_seedValid = TRUE
  返回 g_seedApp_au8

AppSecurityCompareKey():
  key 错误 → g_seedValid = FALSE（下次请求重生成，需求「解锁尝试后重生成」）
  key 正确 → g_seedValid = FALSE + 已解锁（后续 GetSeed 回 0）
```

* `g_seedValid` 为文件级静态标志；Boot 级同构（level==L3(0x09) 回 0 + stable-seed）。
* NVM 读 manufactory 分支的被注释代码维持注释（102 需求不含该项，用户确认不启用）。

### 3.3 F4CMC-103：ResetAttemptCounter_b = FALSE（生成代码 patch）

```c
/* <RXPATCH P1> */
FALSE /*  Enable reset attempt counter on timeout */
/* </RXPATCH P1> */
```

* `Dcm_Lcfg_DspUds.c` 两处：Unlocked_L1（:107）、Unlocked_L3（:133）。
* 效果：延迟到期后 Dcm 不清计数（:117-125 分支不再命中）→ 错 key 仍 NRC36（:355-373，计数≥3 走 NRC0x36MAXDELAYCOUNT=ON 路径）→ 再 2701 因计数≥NumAttDelay(3) 且延迟未到 → NRC37。与需求期望序列 NRC37→NRC36→NRC37 完全一致。
* 重生成后按标记重放（autosar-code-generation.md §1.4）。

### 3.4 F4CMC-100/101：用户手动改（可行性评估，本 Story 只跟踪）

* **落点**：DEXT/ISOLAR Dem 环境数据配置——快照 DID 集 0x0500/0x9A5D → 0x15A0（EventPriority 1B）/ 0x0601（Date&ODO 6B）/ 0x15A2（状态信息 20B）；扩展数据 2 记录 → 3 计数器（补 Aged counter）。重生成 `Dem_Cfg_EnvDid.h / EnvFFRecNumeration.h / EnvExtendedDataRec.h`。
* **配套**：0x15A2 各数据元素信号源对接（EcuTemp×2/OutSideTemp/VehSpd/SystemRunTime/BatteryVoltage/ErrorName/SystemState/EngineStatus/SoftwareVer）；快照布局变化 → Dem 事件 NVM 块尺寸同步 + 存量数据失效（刷后清 NVM）。
* **风险**：Dem 重生成波及全套 Dem_Cfg；升级后旧快照格式不兼容。建议在 10.0.13.10 走 ETAS 生成流程，不与本 Story 代码混 PR。

---

## 六、 验证方案

1. **编译**：`CMC/RX_C088/develop` preset 零错误。
2. **DiagnosticTester 用例**（复现 testcase 即回归用例，A/B 对照）：
   * 102-a：1003 → 连续 2701 ×3 → 三次 seed 相同（基线：三次全不同）
   * 102-b：seed → 错 key → 2701 → seed 已重生成（≠旧值）；2701 → 同值
   * 102-c：解锁成功后 2701 → seed=0
   * 103-a：错 key ×3（NRC35×2 + NRC36）→ 2701 → NRC37 → 等 10s → 错 key → **NRC36**（基线：NRC35）→ 2701 → **NRC37**（基线：6701）
   * 99-a：1003 → 1002 → 抓 CAN 应用报文（ACCS_FCM 等）停发（基线：继续发送）；1001 或 S3 超时 → 报文恢复
   * 99-b：编程会话内 34/36/37 诊断流正常（诊断不经 Com 组的佐证）
3. **台架**：刷写后用户手动验证五项（100/101 由手动改方自行验证）。

## 附录B：ADR 摘要

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | F4CMC-99 走 Dcm 集成回调 + Com_IpduGroupStop | BswM DEXT 补规则接线 + 整包重生成 | 回调是集成者所有文件（重生成不覆盖）；调用点已存在；诊断流量不经 Com 组零副作用；BswM 路线需 ISOLAR 重生成成本高一个量级 |
| 2 | F4CMC-103 直接 patch 生成文件（标记） | DEXT 改参数 + 重生成 | 单布尔参数改动；patch 标记 + 重放流程成熟；避免整包生成波动 |
| 3 | 102 的 seed 状态机仅会话内（不放 NVM） | seed 持久化 | 需求原文只约束「连续请求相同/解锁后为0」，跨下电无要求；保持最小改动 |
