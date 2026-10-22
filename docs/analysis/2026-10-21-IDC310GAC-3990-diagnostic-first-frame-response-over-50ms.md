# 🐞 [IDC310GAC-3990-诊断请求第一帧回复超50ms] 问题分析报告

| 文档基础属性 | 内容说明 | 分析与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **问题单号** | IDC310GAC-3990（代表）/ 4837 / 5857 / 5758 | **分析结论** | 🟢 是问题(转正式开发) |
| **问题主题** | 诊断请求第一帧回复时间超 50ms（P2max） | **缺陷类型** | 性能(时序) / 编码 |
| **分析人 / 日期** | @Hua.Yao / 2026-10-21 | **严重等级** | S3 一般(诊断时序规格违例，测试项阻塞) |
| **项目 / 变体** | GAC 全系（T68 为分析载体，修复覆盖 8 变体） | **优先级** | P2 高 |
| **发现阶段** | 台架诊断测试 | **分析状态** | 🔵 已修复 |
| **根因分类** | 编码（历史修复覆盖缺口） | **关联输出** | 🔗 [Story IDC310GAC-7888](https://jira.imotion.ai:7070/browse/IDC310GAC-7888) ｜ 📋 Obsidian 笔记《GAC fix diagnostic first frame response over 50ms》 |

> **📝 变更记录**
> * `2026-10-21`｜@Hua.Yao｜V1.0｜初版：现象固定、根因分析、修复与 A/B 验证结果

---

## 一、 缺陷概述 (Defect Summary)

### 1.1 问题描述

UDS 诊断请求（典型 0x14 ClearDTC、0x11 ECU Reset 等需多任务周期完成的服务）发出后，ECU **第一帧响应**（正响应首帧或 NRC 0x78 requestCorrectlyReceived-ResponsePending）超过 P2max=50ms 才发出，违反诊断时序规格，导致诊断测试项失败。此前两轮修复（Story 5594 首周期 pending 直接回 NRC78、Story 7306/6205 DCM DSL 状态机竞态修复）后报告人复测仍失败。

### 1.2 现象与复现(原样摘录)

**IDC310GAC-3990 Problem Description（customfield_12007，原样）**：

*Precondition:* 正常上电

1、版本：https://ci.imotion.ai/package/5948/detail

*Reproduce Steps:*

1、诊断测试

2、检测请求回复时间

*Expected result:*

2、第一帧回复时间不会超50ms

*Actual result:*

2、第一帧回复时间超50ms

{*}Probability of reproduce:{*}5-5

**报告人评论（关键新证据）**：

- 2026-08-31 刘四源：https://ci.imotion.ai/package/12636/detail 版本测试失败，11服务和14服务大概率的发生时间超50ms，大概是60ms-80ms之间
- 2026-10-16 刘四源：https://ci.imotion.ai/package/16903/detail 版本测试失败

**同类四单**：3990（T68_G450v2_260530，5-5）/ 4837（T51_G390_20260611_S.000，诊断压测 1101 请求回复超 50ms，1-121）/ 5857（T09_G150v8_260731，5-5）/ 5758（S52_G520v1_260620，5-5）。

**期望行为**：第一帧响应 ≤ 50ms（P2max，UDS 时序规格；`DCM_CFG_DEFAULT_P2MAX_TIME=50000u`）。
**实际行为**：60-80ms（报告人实测）／台架 BLF 实测 52.8-77.1ms + 偶发无首帧响应。

### 1.3 环境矩阵

| 项 | 版本/值 | 来源 |
| :--- | :--- | :--- |
| 固件版本 / commit | `mcu_app_j6@develop@545370bba`（基线）/ feature/IDC310GAC-7888-…（修复） | V2 工作区 02_Workspace_J6_V2 |
| 硬件版本 / 板卡 | J6B（uper_app, parking_dr preset） | V2 工作区 |
| 测试环境 | 台架，程控电源，CX-USBCANFD ch0（500k/2M），DiagnosticTester（python-can） | tests/harness/dcm_first_frame_p2 |
| 相关工具/诊断仪 | DiagnosticTester + BLF 首帧延迟解析 | 本仓库 tools/DiagnosticTester |
| 报告版本 | package 5948 / 12636 / 16903 | 问题单 |

### 1.4 分析输入与基线

| 输入 | 来源 | 说明 |
| :--- | :--- | :--- |
| 复现步骤/现象 | 问题单 customfield_12007 | 原样摘录于 §1.2 |
| 附件 | — | 无 |
| 评论补充 | 刘四源 8-31 / 10-16 复测评论 | 5594+7306 修复后仍失败 |
| 分析基线 | V2 工作区 | mcu_app_j6@develop@545370bba，编译通过，T68 变体 |

---

## 二、 复现性与数据回放 (Reproducibility & Replay)

### 2.1 可复现性

| 复现率 | 条件 | 样本 |
| :--- | :--- | :--- |
| 概率性（快节奏压测下高概率） | 0x14 连续请求 + ≤20ms 步进间隔，Dcm 10ms 任务周期与请求相位不利时 | 基线压测 20 轮中 2 轮 >50ms + 1 轮无首帧响应 |

* **首次/末次出现**：首次见 package 5948；两轮修复（5594/7306+6205）后 12636、16903 仍失败；develop 基线 545370bba 台架复现成功（见 §2.2）。

### 2.2 现象固定与回放（台架 A/B 复现，BLF 首帧延迟实测）

* **异常发生时的状态**：0x14 ClearDTC 为内部 DSP 服务，首轮 `DCM_E_PENDING`，在 Dcm 10ms 任务周期（`Core0_OsTask_BSW_10ms`，`DCM_CFG_TASK_TIME_US=10000u`，`DCM_CFG_OSTIMER_USE=FALSE` 纯周期计数）中等待 DSL P2ServerMax 到期才发 0x78。
* **报文/时序回放**（`tests/harness/dcm_first_frame_p2/testcases/` 运行目录，BLF + result.csv）：

| 用例 | 基线（develop@545370bba） | 补丁后 |
| :--- | :--- | :--- |
| 0x14 五轮（p2_first_frame_14_t68） | 6/6 PASS 但首帧 39.6-50.1ms——**零裕量** | — |
| 0x14 二十轮压测（p2_first_frame_14_stress_t68，步进 20ms） | 中位 42.5ms，最大 **77.1ms**（与报告人 60-80ms 吻合），2/20 >50ms + 1 轮 TIMEOUT | 中位 **21.3ms**，最大 **32.4ms**，0/20 >50ms，21/21 PASS |
| 0x11 对照（p2_first_frame_11_t68，外部分支已覆盖） | 首帧 8.3ms，3/3 PASS | 3/3 PASS |
| 内部服务冒烟（smoke_internal_services_t68） | — | 5/5 有响应无挂死 |

---

## 三、 根因分析 (Root Cause Analysis)

### 3.1 知识召回(看代码之前先做)

| 检索源 | 关键词 | 结果 |
| :--- | :--- | :--- |
| `docs/analysis/` 历史个案 | 3990 / 5594 / NRC78 / P2max | 无命中（本篇为首篇） |
| `docs/design/` 设计方案 | DCM / 首帧 | 无命中 |
| Obsidian Work Database 笔记 | IDC310GAC-5594 等 | 命中：[[GAC dcm response NRC7F and fix dcm bug]]（5594 首周期 NRC78 方案与 7306 竞态修复脉络） |

### 3.2 排查过程(假设-验证-排除链)

| # | 假设 | 验证手段 | 结果 |
| :--- | :--- | :--- | :--- |
| 1 | 5594 补丁未实际落地 | 服务器 grep 5594 转换代码 | 排除——外部分支首轮转换存在（`Dcm_Dsd_StateMachine.c:540-549`） |
| 2 | Dcm 任务周期抖动（RCA 旧结论） | 读调度配置 + BLF 时序 | 部分成立但非主因——10ms 周期本身在规格内，问题是**首轮 PENDING 静默等待 P2 定时器** |
| 3 | 0x11/0x14 走不同代码路径，0x14 未被 5594 覆盖 | 读 `Dcm_Lcfg_Dsd.c` 服务表 + `Dcm_CallService` | **命中**——0x14 是内部 DSP 服务（if 分支），0x11 是外部分支 |
| 4 | 台架能否复现报告人现象 | 5 轮 + 20 轮压测 BLF 实测 | 命中——零裕量基线，压测 2/20 超限 + 1 超时 |

### 3.3 5 Whys 深挖

| 层级 | 提问 | 回答 |
| :--- | :--- | :--- |
| Why 1 | 为什么首帧超 50ms？ | 0x14 首轮返回 `DCM_E_PENDING` 后静默等待 DSL P2ServerMax 到期才发 0x78，叠加 20ms `P2ServerTimeAdjust` 与 CanTp 周期 → 60-80ms |
| Why 2 | 为什么 5594 修复没覆盖它？ | 5594 只在外部分支（else，`internalDspService_b==FALSE`，如 0x11 idia handler）加了首轮 PENDING→FORCE_RCRRP 转换，内部分支（if）未加 |
| Why 3 | 为什么内外分支不对称？ | 5594 修复时只针对报告失效的 external 服务路径打补丁，未审计 `Dcm_CallService` 的对称分支 |
| Why 4 | 为什么评审没拦住？ | 补丁型修复缺少"同函数对称路径全覆盖"检查项 |
| Why 5 | — | 到 Why4 可落实防腐动作（§5.2） |

### 3.4 根因与依据

* **根因**：`Dcm_CallService()` 内部分支（`internalDspService_b == TRUE`，覆盖 0x14 ClearDTC、0x19 ReadDTCInfo 等 BIP 内置服务）首轮 `DCM_E_PENDING` 不做 NRC78 转换，静默等 DSL P2ServerMax（`P2ServerTimeAdjust=20000u` + 10ms 任务周期流水）到期，首帧 42.5ms 中位零裕量，压测相位不利时 52.8-77.1ms。
* **根因分类**：编码（历史修复覆盖缺口）。
* **代码依据**：`cpj_gac/autosar/<v>/BswRta/src/bsw/Dcm/src/Dsd/Dcm_Dsd_StateMachine.c`——if 分支（修复前无转换）vs 外部分支 5594 转换（540-549 行）；服务表 `Dcm_Lcfg_Dsd.c`（0x14 `Dcm_Prv_DspClearDiagnosticInformation` internal=TRUE，0x11 `idia_ecu_reset` internal=FALSE）；0x14 handler `DcmDspUds_Cdi.c` 首轮 `s_serviceRetVal_u8 = DCM_E_PENDING`。
* **责任归属**：本模块（DCM）缺陷。

### 3.5 影响范围评估

develop 上全部 GAC 变体（ay7/s52/s52-e046/t09/t51/t68/t75/t88）同一份生成代码，全部受影响——修复同步 8 变体；另按需求方指定同步三个 release 分支（T09Y/T75/T51 各自变体）。luna6 为 BSWEXT-853 不同基线、t996d/v20 已删除（IDC310GAC-7123），不在范围。

---

## 四、 分析结论与分流 (Conclusion & Triage)

**是问题**：内部 DSP 服务首轮 PENDING 缺少 NRC78 转换的代码覆盖缺口（5594 修复不对称），导致首帧超 P2max。修复走 Story [IDC310GAC-7888](https://jira.imotion.ai:7070/browse/IDC310GAC-7888)（V2 工作区全流程交付）。

---

## 五、 修复方案 (Fix Plan)

### 5.1 纠正措施(Corrective Action,治此件)

| # | 修改点 | 文件 | 改动说明 | 风险评估 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 内部分支首轮 PENDING→FORCE_RCRRP 转换（+18 行/变体，`<{PROJ}>PATCH P1` 标记） | `cpj_gac/autosar/<v>/BswRta/src/bsw/Dcm/src/Dsd/Dcm_Dsd_StateMachine.c`（t68 为 505-526 行） | `DCM_INITIAL == Dcm_SrvOpstatus_u8` 且首轮返回 `DCM_E_PENDING` 时转 `DCM_E_FORCE_RCRRP`，立即发 0x78，与外部分支 5594 转换对齐 | 低——后续轮次由 `Dcm_Prv_SendForcePendingResponse()` 三重节流（force-pending 标志 / TX 确认态 / 半 P2* 窗口）保证不重发；不消费 OpStatus 的 handler（如 0x27 异步 crypto）经冒烟验证无 0x78 风暴、无挂死 |

* **修复范围**：develop 全部 8 个 GAC 变体 + 三个 release 分支各自变体（`release/GAC/T09_Y1_D126/G710`→t09、`release/GAC/T75_D084/G270`→t75、`release/T51-D088/S.001`→t51；三个分支目标文件与 develop 基线逐字节一致，5594 外部补丁均已在内）。
* **正式开发关联**：Story IDC310GAC-7888；feature 分支 `feature/IDC310GAC-7888-gac-first-frame-response-50ms`（develop）及 `-g710 / -g270 / -s001`（release）。

### 5.2 预防措施(Preventive Action,治同类)

| # | 预防动作 | 落点 | 状态 |
| :--- | :--- | :--- | :--- |
| 1 | DCM 补丁型修改增加"同函数对称分支审计"检查（if/else 内外服务路径同改） | problem-analysis / feature-development 修复检查单 | 待办 |

---

## 六、 验证结果 (Verification)

* **验证性修复(V2 工作区, T68 变体)**：
  * 编译：`parking_dr uper_app` preset 通过
  * 刷写：ProgramBoard_j6b（fastboot UDP，COM65/COM44），2026-10-21
  * A/B 验证（同 testcase 互为对照，`tests/harness/dcm_first_frame_p2/testcases/`）：
    * 基线（红）：0x14 压测 20 轮，中位 42.5ms / 最大 77.1ms，2 轮 >50ms + 1 轮 TIMEOUT
    * 补丁（绿）：中位 21.3ms / 最大 32.4ms，0 轮 >50ms，21/21 PASS
  * 对照组：0x11（外部分支，旧补丁路径）补丁前后均 3/3 PASS、首帧 8.3ms——佐证根因定位
  * 冒烟（补丁最高风险目标）：0x27/0x19/0x22/0x3E 共 5/5 有响应、无挂死、无 0x78 风暴（`2703→7F2712`、`1902AF→5902FF`、`22F190→62F190`、`3E00→7E00`）
* **回归确认**：既有 t68 用例（6762/6763 功能寻址 func_10/func_3e）在基线与补丁固件上同样失败——已核实 PduR 网关修复链不在 develop（无 commit、无 PATCH 标记），属基线既有问题，与本补丁无关（0x10/0x3E 无首轮 PENDING）
* **正式提交后验证**：PR 合并后由测试侧按问题单回归（四单关联 Story 7888）

---

## 七、 关闭与生命周期 (Closure & Lifecycle)

### 7.1 可复用结论

* 首帧超 P2max 且"部分服务好部分服务坏"→ 先查 `Dcm_Lcfg_Dsd.c` 服务表 `internalDspService_b` 归属，再对照 `Dcm_CallService` 两分支的补丁覆盖是否对称；关键词：NRC78 / FORCE_RCRRP / P2max / 首帧。

### 7.2 缺陷生命周期记录

| 状态 | 日期 | 操作人 | 备注 |
| :--- | :--- | :--- | :--- |
| 发现(报告) | — | 刘四源 | 四问题单（3990/4837/5857/5758） |
| 分析开始 | 2026-10-21 | @Hua.Yao | V2 基线 develop@545370bba |
| 根因确认 | 2026-10-21 | @Hua.Yao | 用户确认，台架复现（红） |
| 修复验证通过 | 2026-10-21 | @Hua.Yao | A/B 红转绿 + 冒烟 5/5 |
| 正式提交 | 2026-10-21 | @Hua.Yao | commit/PR 见笔记台账 |
| 关闭 | — | — | PR 合并后四问题单推进 IMPLEMENTED |

---

## 附录:原始证据

* 用例与运行产物（BLF + result.csv）：`tests/harness/dcm_first_frame_p2/testcases/`（p2_first_frame_14_t68 / p2_first_frame_11_t68 / p2_first_frame_14_stress_t68 / smoke_internal_services_t68 及各自时间戳运行目录）
* 基线压测关键数据：中位 42.5ms、最大 77.1ms、2/20 >50ms + 1 TIMEOUT；补丁后：中位 21.3ms、最大 32.4ms、0/20
* 6762/6763 无关性核查记录：`tools/DiagnosticTester/testcase/t68/func_10_nrc13_stale_length/`、`func_3e_no_response_stale_length/`、`func_10_min_6762/`
