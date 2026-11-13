# J02 DV ECU Reset Allow Default Session 需求与设计说明文档

| 项 | 内容 |
| --- | --- |
| 工单 | [C097FAWVW-25](https://jira.imotion.ai:7070/browse/C097FAWVW-25) |
| 项目/变体 | FAWVW C097 / J02 |
| 日期 | 2026-11-13 |
| 分支 | release/FAWVW/J02_C097/DV（仅 DV，不合 develop） |
| fixVersion | I210v1 |
| 状态 | 设计评审中 |

## 一、概述

### 1.1 功能背景与目标

J02 DV 台架无解锁环境（无法完成 27 服务安全解锁），而当前 0x11 ECU Reset 配置要求「扩展/编程会话 + 三档安全解锁之一」，导致 DV 台架无法通过诊断复位 ECU（NRC 0x33）。本需求放开 0x11 的会话与安全门控：**默认会话 + 未解锁即可执行**。

### 1.2 适用范围

- 仓库：仅 `mcu_app_j6_v2`
- 分支：仅 `release/FAWVW/J02_C097/DV`（DV 调试专用行为差异，**明确不合入 develop**，develop 保持客户需求树定义的原始门控）
- 不含：0x11 复位流程本身（状态机/NVM WriteAll 逻辑不动）、其他服务门控

### 1.3 术语

| 术语 | 含义 |
| --- | --- |
| Locked=Y | 问卷 Service List 列值；Dcm_AutoGen 对 Locked=Y 的行不生成 DcmDsdSubServiceSecurityLevelRef，即 DCM 不做安全等级检查（未解锁放行） |
| DV-only | 仅存在于 DV 验证分支的行为差异，问卷 Remark 标注防误同步 |

### 1.4 参考文档

- 前置：C097FAWVW-24（J02 Change DID Function，DV 分支现有问卷 V1.4 与 DID 功能基础，PR 415/739 已合并）
- 先例：无同类「DV-only 门控放开」先例（知识召回无命中）

### 1.5 约束与假设

- Dcm 配置由问卷经 Dcm_AutoGen 生成，人工不直接改生成区（arxml/BSW 代码）
- 问卷权威存放位置：`cpj_fawvw/veh_j02/dia_cfg/doc/UDS_Diagnostic_Questionnaire_J02.xlsx`（DV 分支副本，本单起 DV 与 develop 问卷有意分叉）
- DV 台架验证后 DV 分支继续承载 C097FAWVW-24 等单的 cherry-pick，本单生成物需耐受后续合并

## 二、架构设计与生成链

```
UDS_Diagnostic_Questionnaire_J02.xlsx (DV 分支副本)
  Service List: 0x11 两行 Def N→Y、Locked N→Y、Remark 标注
        │
        └─ Dcm_AutoGen.py --repo <mcu_app_j6_v2@DV> --config j02 --excel <问卷>
              ├─ gen_dcm_arxml：J6B_Dcm_EcucValues.arxml — 0x11 子服务
              │    SessionLevelRef 增 DEFAULT_SESSION、SecurityLevelRef 三项删除
              │    → ISOLAR BSW 生成（Dcm C 配置代码随 arxml 再生）
              └─ gen_did_code/gen_nrc_code/gen_rid_code：DID/RID 表不变（问卷 DID List 未动）
```

- 并发上下文：0x11 在 Dcm 任务上下文同步处理，复位状态机走 ov_dia 周期任务，本单不改变
- 会话/安全检查位置：DCM BSW 模块配置表（由 EcucValues arxml 经 RTA-CGE 生成 C 代码），非 dia_cfg lookup table（该表仅覆盖 0x22/0x2E DID）

## 三、核心配置变更

### 3.1 问卷 Service List 修改（仅 DV 分支副本）

| 行 | 列 | 现值 → 新值 | 说明 |
| --- | --- | --- | --- |
| 0x11 ECU Hardware Reset | Default Session | N → Y | 默认会话放行 |
| 0x11 ECU Hardware Reset | Locked | N → Y | 不生成安全等级引用，未解锁放行 |
| 0x11 ECU Hardware Reset | Remark | 空 → DV only: allow default session + unlocked (no unlock env on DV bench) | 防误同步回 develop |
| 0x11 ECU KL15 Reset | 同上三列 | 同上 | 同上 |

Programming/Extended Session 保持 Y（仅放开，不收紧；最小改动）。

### 3.2 生成物变更（Dcm_AutoGen 驱动）

| 文件 | 变更 |
| --- | --- |
| `dia_cfg/doc/UDS_Diagnostic_Questionnaire_J02.xlsx` | §3.1（本单源） |
| `autosar/.../gen/J6B_Dcm_EcucValues.arxml` | 0x11 子服务 SessionLevelRef + DEFAULT_SESSION、SecurityLevelRef ×3 删除 |
| ISOLAR 再生的 Dcm BSW 代码 | 随 arxml（会话/安全配置表） |
| 其余生成外溢文件 | 按 C097FAWVW-24 ADR-3 同法：`git checkout HEAD` 恢复，仅保留本变更驱动文件 |

## 四、异常处理与容错

- 复位流程不变：0x11 仍走 DCM_E_PENDING 两拍响应 + ov_dia 周期状态机（Dem_Shutdown → NVM WriteAll → 强制复位，含 180s 超时兜底）
- 默认会话执行复位的安全影响：仅 DV 分支存在；develop/量产分支门控不变，无生产风险
- 问卷 DV/develop 分叉：Remark 显式标注 DV-only；若未来 develop 问卷同步到 DV，需保留本两行差异（收尾在笔记 Status Updates 记录）

## 五、验证方案

1. 编译通过（SSH 12.42，DV 分支）
2. 刷写 DV 固件后 DiagnosticTester：默认会话上电直发 `1101` → 预期 `5101`（未解锁、默认会话）；ECU 实际复位（重新上电恢复）
3. 用户台架手动验证（阶段 4 停下等确认）
4. 验收标准：DV 台架默认会话未解锁 11 服务可执行并完成复位；develop 分支零改动

## 附录A：需求追溯矩阵

| 需求 | 动作 |
| --- | --- |
| 用户 DV 台架需求（C097FAWVW-25） | 0x11 默认会话+未解锁放行，仅 DV 分支 |
| C097FAWVWREQ 需求树 32 条 | 不涉及（DV-only 差异，不改客户需求语义） |

## 附录B：ADR

- **ADR-1 DV-only 差异落在问卷而非手改生成物**：手改 arxml 无法打 patch 标记、后续再生成会静默丢失；改 DV 分支问卷副本 + Dcm_AutoGen 重生成自洽可复现，Remark 标注防误同步。代价：DV 与 develop 问卷有意分叉；收益：门控语义单一权威源仍是问卷。
- **ADR-2 不合入 develop**：用户明确 DV-only；develop 门控由客户需求树定义（安全评估属客户域），本单不改变量产行为。

## 附录C：开放问题

1. ~~KL15 Reset（0x02）是否也需要放开~~：按用户「11 服务允许默认会话和未解锁」表述，两行一并放开（0x11 服务的全部子服务），设计评审时如有异议仅保留 0x01。
