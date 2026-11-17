# 🐞 [IDC310GAC-8995] 1101 复位后诊断请求偶现不回复（rxpduId 越界空指针防护）问题分析报告

| 文档基础属性 | 内容说明 | 分析与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **问题单号** | IDC310GAC-8995 | **分析结论** | 🟢 是问题(转正式开发) |
| **问题主题** | 诊断压测：1101 复位后等待 7s 偶现诊断请求不回复，有异常重启 | **缺陷类型** | 功能 |
| **分析人 / 日期** | @Hua.Yao / `2026-11-14` | **严重等级** | S2 严重(主要功能失效) |
| **项目 / 变体** | GAC T68（波及 GAC 全变体） | **优先级** | P3 中(与 JIRA 对齐) |
| **发现阶段** | 台架集成测试（诊断压测） | **分析状态** | 🔵 已修复 |
| **根因分类** | 编码 | **关联输出** | 🔗 [IDC310GAC-8995](https://jira.imotion.ai:7070/browse/IDC310GAC-8995) ｜ Story [IDC310GAC-9151](https://jira.imotion.ai:7070/browse/IDC310GAC-9151) ｜ 📋 Obsidian 分析笔记 |

> **📝 变更记录**
> * `2026-11-14`｜@Hua.Yao｜V1.0｜初版：定性、根因、修复与分支同步

---

## 一、 缺陷概述 (Defect Summary)

### 1.1 问题描述

> GAC T68 诊断压测中，1101 复位后等待约 7s 发起诊断请求偶现不回复（约 1/500），并伴随异常重启——DCM 接收路径 `Dcm_Prv_GetMainConnection` 对越界 `rxpduId` 返回 `NULL_PTR`，调用方裸解引用导致空指针异常。

### 1.2 现象与复现(原样摘录)

**复现步骤**(问题单 Problem Description 原样):

> *Precondition:* 正常上电
> 1、版本：https://ci.imotion.ai/package/20425/detail
> 2、全部外设
> 1、进行所有服务的诊断压测
>
> *Expected result:*
> 1、无异常
> *Actual result:*
> 1、1101复位后等待7s偶现诊断请求不回复
> Probability of reproduce: 1-500

**期望行为**：复位回网后所有诊断请求正常响应。
**实际行为**：复位后约 7s 的请求无响应，偶发异常重启。

### 1.3 环境矩阵

| 项 | 版本/值 | 来源 |
| :--- | :--- | :--- |
| 固件版本 | ci package 20425（T68 release/GAC/T68Y_G460/0710 系） | 问题单 |
| 项目 / 变体 | GAC T68（customfield_15000 = GAC T68） | JIRA |
| 测试环境 | 台架诊断压测（全部服务压测） | 问题单 |

### 1.4 分析输入与基线

| 输入 | 来源 | 说明 |
| :--- | :--- | :--- |
| 复现步骤/现象 | 问题单 customfield_12007 | 原样摘录于 §1.2 |
| 附件 | 问题单 attachment | 无 |
| 评论补充 | 无 | — |
| 分析基线 | mcu_app_j6 各目标分支（blob 校验） | develop + 5 条 release 分支 × 9 个 GAC 变体 |

---

## 二、 复现性与数据回放 (Reproducibility & Replay)

### 2.1 可复现性

| 复现率 | 条件 | 样本 |
| :--- | :--- | :--- |
| 概率性（约 1/500） | 1101 复位后等待 ~7s 发起诊断请求 | 压测统计（问题单） |

* **首次/末次出现**：T68 压测发现；同一缺陷缺口存在于全部 GAC 变体（见 §3.5）。

### 2.2 现象固定与回放

* 无 BLF/日志附件；现象（复位后窗口请求被吞 + 异常重启）与 IDC310GAC-8402 案中 bench cycle 1431（复位回网后 39ms 请求被吞）同相位——post-reset 窗口族。
* 异常重启与空指针解引用的故障表现吻合（任务上下文访存异常 → 异常处理 → 重启），与用户给出的修复方向一致。

---

## 三、 根因分析 (Root Cause Analysis)

### 3.1 知识召回(看代码之前先做)

| 检索源 | 关键词 | 结果 |
| :--- | :--- | :--- |
| auto memory | IDC310GAC 四单同源 | 命中 `project_idc310gac_6398.md`：4796/5999/6659/6398 同源（3101 NRC78→无下文→会话回退→3103 NRC7F），修复链锚点 7306/7822/7162/6205 已落位 |
| `docs/analysis/` | Dcm / rxpduId / 复位 | 无直接命中 |
| git 历史 | Dcm_Prv_GetMainConnection | 命中 commit 461080625（IDC310-4528，2026-08-24）：t09 已加同一钳位，cherry-pick 自 S52 修复 2dba6bb5 |

### 3.2 排查过程(假设-验证-排除链)

| # | 假设 | 验证手段 | 结果 |
| :--- | :--- | :--- | :--- |
| 1 | Dcm 接收路径缺 rxpduId 越界防护 | 逐分支逐变体取 `Dcm_Prv_General.c` blob 走读 `Dcm_Prv_GetMainConnection`（develop + 5 release × 9 变体） | 命中：除 t09 外全部变体的该函数越界时返回 `NULL_PTR` |
| 2 | 调用方是否校验 NULL | 走读调用点 | 命中：大量裸解引用——`Dcm_Dsl_StateMachine.c:636-637`、`Dcm_Dsl_Authentication.c:426`、`Dcm_Prv_General.c:530/536/542/549/605` 等（MR12 注释声称"PduId 必有效"，前提不成立于异常输入） |
| 3 | t09 为何无此问题 | `git log` 该文件 | t09 在 IDC310-4528 已加钳位 `rxpduId>=DCM_CFG_TOTAL_RX_PDUID → rxpduId=0`，且无 patch 标记（随源码更新落位） |

### 3.3 5 Whys 深挖

| 层级 | 提问 | 回答 |
| :--- | :--- | :--- |
| Why 1 | 为什么复位后诊断请求偶现不回复/异常重启？ | `Dcm_Prv_GetMainConnection` 收到越界 `rxpduId` 时返回 `NULL_PTR`，调用方裸解引用 → 空指针访存异常 |
| Why 2 | 为什么返回 NULL_PTR？ | 函数内越界分支未钳位，直接跳过查表返回 NULL 初始值 |
| Why 3 | 为什么调用方不判 NULL？ | 生成代码按"输入 PduId 必有效"假设设计（MR12 豁免注释），防御责任落在函数入口却未闭合 |
| Why 4 | 为什么只有 t09 防住了？ | IDC310-4528 修复时只在 t09/S52 侧加了钳位，未回灌到其余 GAC 变体与老 release 分支 |
| Why 5 | 为什么变体间会漂移？ | 多变体目录各自持有生成代码副本，跨变体修复同步依赖人工（本次 9151 同步即补该缺口） |

### 3.4 根因与依据

* **根因**：`Dcm_Prv_GetMainConnection`（`cpj_gac/autosar/<变体>/BswRta/src/bsw/Dcm/src/General/Dcm_Prv_General.c:356`）对 `rxpduId >= DCM_CFG_TOTAL_RX_PDUID` 返回 `NULL_PTR`，而 DSL/DSM 层调用方不判空直接解引用，复位后窗口期异常 `rxpduId` 触发空指针异常 → 请求无响应/异常重启。
* **根因分类**：编码
* **代码依据**：`Dcm_Prv_General.c:356-370`（函数体）；裸解引用点 `Dcm_Dsl_StateMachine.c:636`、`Dcm_Dsl_Authentication.c:426`、`Dcm_Prv_General.c:530/536/542/549/605`；t09 已修版本 = blob 4c2ffbc0a（commit 461080625）
* **责任归属**：本模块缺陷（生成代码防御缺口），修复方向用户已确认

### 3.5 影响范围评估

* 波及清单：develop 全部 GAC 变体中 **t51/t68/t75/s52/t88/ay7/s52-e046/luna6 共 8 个**缺钳位（t09 已带）；release 分支中 T75_D084/G270(t75)、T51-D088/S.001(t51)、T68Y_G460/0710(t68)、S52_D110/G540(s52) 缺钳位；T09_Y1_D126/G710 的 t09 文件（blob 4c2ffbc0a）已带钳位，无需处理。
* 同类防护缺口不在 CanTp/PduR 侧（本次不扩散）。

---

## 四、 分析结论与分流 (Conclusion & Triage)

**是问题**：生成代码防御缺口（越界返回 NULL + 调用方裸解引用），1/500 压测复现 + 异常重启，需修复 → 同步 t09 已验证的钳位修复到全部受影响分支。

**遗留疑点**：越界 `rxpduId` 的确切产生源（复位窗口内 CanTp/PduR 传入的无效 PduId 或 `Dcm_RxPduIdInProcess` 残留值）无日志可证；钳位保证即使出现也不崩溃，属防御性修复（与 t09 4528 同口径）。

---

## 五、 修复方案(仅"是问题") (Fix Plan)

### 5.1 纠正措施(Corrective Action,治此件)

| # | 修改点 | 文件 | 改动说明 | 风险评估 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 越界钳位 | `cpj_gac/autosar/<变体>/BswRta/src/bsw/Dcm/src/General/Dcm_Prv_General.c:362` | 函数入口加 `if (rxpduId >= DCM_CFG_TOTAL_RX_PDUID) { rxpduId = 0; }`（与 t09 4528 版本逐字一致，+4 行） | 仅影响越界异常路径；正常路径零改动。t09 同文本已在 develop/2 条 release 稳定运行 3 个月 |

* **交接物**：git plumbing 同步（无 checkout），源分支 `feature/idc310gac-9151-rxpdu-clamp-{develop,t75,t51,t68,s52}`，每变体插桩锚点唯一性校验（`mainConnection_pcast = NULL_PTR` 全文件唯一）+ 基线 blob 预校验 + T68Y release 保留原 100755 文件 mode。
* **正式开发关联**：Story IDC310GAC-9151（问题单 8995 is solved by 9151）

### 5.2 预防措施(Preventive Action,治同类)

| # | 预防动作 | 落点 | 状态 |
| :--- | :--- | :--- | :--- |
| 1 | 跨变体修复同步时先做"逐分支逐变体 blob 比对"确定波及清单（本次已实践） | problem-analysis skill 阶段 2 | 已实践，沉淀于本报告 §3.5 |

---

## 六、 验证结果(仅"是问题") (Verification)

* **验证性修复**：本修复为 t09 已验证文本（IDC310-4528，2026-08-24 起 t09 侧稳定运行）的跨变体同步，未在 bench 单独复现 1/500 低概率现象（无板卡在线 + 低概率工况，降级 case (b)：以问题单现象 + t09 修复先例作为改前/改后依据）。
* **编译验证**：由 Bitbucket CI（imoci）在各 PR 上执行，全部 PR CI 通过后合入。
* **回归确认**：改动仅新增越界分支钳位，正常路径（`rxpduId < DCM_CFG_TOTAL_RX_PDUID`）逻辑不变。

---

## 七、 关闭与生命周期 (Closure & Lifecycle)

### 7.1 可复用结论

* 检索关键词：`rxpduId`、`Dcm_Prv_GetMainConnection`、`空指针`、`复位后不回复`、`GAC 变体同步` → 命中本篇。
* GAC 跨变体同步修复的标准姿势：先逐分支逐变体验证基线 blob → 单一锚点文本替换 → plumbing 提交（保留原文件 mode）→ 源分支 + PR。同模式案例：8553 日志插桩同步（2026-11-10）。

### 7.2 缺陷生命周期记录

| 状态 | 日期 | 操作人 | 备注 |
| :--- | :--- | :--- | :--- |
| 发现(报告) | 2026-11-14 | Siyuan Liu | 问题单创建（T68 压测 1/500） |
| 分析开始 | 2026-11-14 | @Hua.Yao | 拉单 + 四单同源召回 + 逐分支 blob 走读 |
| 根因确认 | 2026-11-14 | @Hua.Yao | 用户直接给出修复点（与 t09 4528 钳位一致） |
| 正式提交 | 2026-11-14 | @Hua.Yao | PR #2058(develop 8 文件) / #2059(T75) / #2060(T51) / #2061(T68) / #2062(S52)；T09 release 已带钳位无需 PR |
| 修复验证通过 | 待 CI + 回归 | — | — |
| 关闭 | 待 PR 合并后 | — | 问题单流转 IMPLEMENTED |

---

## 附录：PR 清单

| PR | 目标分支 | 内容 |
| --- | --- | --- |
| [#2058](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/2058) | `develop` | 8 变体 × 1 文件，+32 行 |
| [#2059](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/2059) | `release/GAC/T75_D084/G270` | t75，+4 行 |
| [#2060](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/2060) | `release/T51-D088/S.001` | t51，+4 行 |
| [#2061](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/2061) | `release/GAC/T68Y_G460/0710` | t68，+4 行（保留 100755 mode） |
| [#2062](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/2062) | `release/GAC/S52_D110/G540` | s52，+4 行 |
| — | `release/GAC/T09_Y1_D126/G710` | t09 文件已带钳位（IDC310-4528），无需 PR |
