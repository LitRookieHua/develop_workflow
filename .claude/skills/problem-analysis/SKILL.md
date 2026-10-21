---
name: problem-analysis
description: JIRA 问题单分析与修复工作流（4 阶段：现场捕获与数据回放+问题定性 → 知识召回与根因收敛 → 方案验证与精准修复 → 审查与合流）。在 V2 工作区完成全流程：分析 + 验证性修复 + 建分支 + commit + push + PR + 关单；是问题 → 立项（story-creation）后在 V2 直接修复交付，不是问题 → JIRA 写明理由 + refuse 关单。当用户提到 问题分析、分析问题单、分析下这个 problem、refuse，或给出问题单号（如 D3ACYI-xxxx）要求先分析时使用，即使用户只提到其中一个环节。V2 工作区（01_Workspace_TDA4_V2 / 02_Workspace_J6_V2）问题修复全流程；V1 老工作区用于需求开发（feature-development skill）。
---

# JIRA 问题单分析与修复工作流（4 阶段）

本流程先根据问题单分析清楚是不是问题，再决定去向：**是问题 → 立项后在 V2 工作区完成修复交付全流程（建分支/commit/push/PR/关单）；不是问题 → 在问题单上说明原因并走 refuse 关单**。

4 阶段流程。**阶段 1 的问题定性结论必须先呈现给用户确认**，确认后才立项进入阶段 2。阶段 4 的关单/通知动作在 PR 全部合并后自动执行。

开始前用 TaskCreate 为本次分析创建任务列表（**每阶段一个任务，共 4 个**），逐步勾选，随时可从任务列表恢复进度。

## 路径角色与工作区

路径角色表见 CLAUDE.md「路径角色」（Y: 盘红线同 CLAUDE.md 安全红线）。本 skill 用 **V2 工作区**（`01_Workspace_TDA4_V2` / `02_Workspace_J6_V2`）完成问题修复全流程；需求开发（V1 老工作区）走 feature-development skill。

- mcu 仓库：TDA4_V2 → `mcu_app_tda4`；J6_V2 按项目归属选 `mcu_app_j6`（存量项目）或 `mcu_app_j6_v2`（新项目），判断规则（J6 双仓库归属）一律查共用手册 [workspace-setup.md](../../references/workspace-setup.md)；拿不准时问用户

## 阶段 1：现场捕获、数据回放与问题定性

**拉问题单详情**——用 JIRA REST API（认证见 [token-authentication.md](../../references/token-authentication.md)，PAT Bearer；端点见 story-creation skill 的「JIRA API 速查」）：

- `GET https://jira.imotion.ai:7070/rest/api/2/issue/<问题单号>?fields=summary,description,status,fixVersions,components,assignee,reporter,issuelinks,attachment,customfield_15000,customfield_12007,customfield_12006`
- **问题描述（复现步骤）在自定义字段 Problem Description = `customfield_12007`**——问题单的问题描述都放在该属性中，标准 description 字段经常为空；相邻有用字段：`customfield_12006` Problem Type、`customfield_12017` Root Cause Analysis。字段 id 可用 `?expand=names` 查全量字段名
- Problem Description 里的**复现步骤与测试现象原样保存**——这是后续分析和结论的依据，不能只写概括；该字段也为空时查评论（`GET .../issue/<key>/comment`）
- 有附件则下载留存（分析时看）
- 记录 fixVersions、变体字段（customfield_15000）、components——阶段 2 推断项目用

**现象固定**：整理异常发生时的软硬件状态记录（报错上下文、堆栈/日志、发生条件），与复现步骤一起作为分析输入。

**问题定性——是/不是问题，结论呈现后停下等用户确认**：基于单据信息、回放数据与必要的代码走读（Y: 盘读代码）判断：

- **是问题**（代码缺陷/配置错误/行为不符规格）→ 整理依据（代码位置、逻辑链、规格出处）
- **不是问题**（行为符合设计/规格、测试方法不当、非本模块问题等）→ 整理依据

> 后续迭代：PSA 报文回放工具、MCAP 日志解码器——实车/台架通信时序（如 CanTp 多帧传输失败、流控制超时）脱机复现。当前手段为问题单 description / 附件 / 日志。

**定性后的分流**：

- **是问题 → 立项**：用户确认后走 `story-creation` skill——创建 Obsidian 工作笔记 + 创建 JIRA Story 并关联问题单（Link to Problems）。新 Story 工单号即阶段 2 建 feature 分支、阶段 4 commit/PR 用的工单号。立项后进入阶段 2
- **不是问题 → refuse 关单**（流程终点，不进后续阶段）：
  1. 沉淀分析报告：`docs/analysis/YYYY-MM-DD-<问题单号>-<主题>.md`，按 [problem-analysis-report-template.md](../../../docs/analysis/problem-analysis-report-template.md) 模板写（修复方案与验证结果两章写"不适用"）
  2. JIRA 问题单加评论：**为什么不是问题**——引用分析报告结论（认证同上，中文 JSON 用 `--data-binary @file.json`）
  3. 按 Problem 单状态流转规则沿**路线二**（OPEN → IN_ANALYSIS → ANALYZED → REJECTED）推进到拒绝终态——权威源 [jira-operation.md](../../references/jira-operation.md)（transition id、必填字段、400 排错链）
  4. Obsidian 笔记收尾：`status: Done`、`completed: 今天`、Status Updates 补分析结论与关单记录（规则见 [obsidian-notes.md](../../references/obsidian-notes.md)）

## 阶段 2：知识召回与根因收敛

**（1）知识召回——看代码之前先做**：

- 检索 `docs/analysis/` 历史个案报告（关键词：问题单号、模块名、现象关键词）
- 检索 `docs/design/` 相关设计方案
- 检索 Obsidian `ClaudeCodeNote/Work Database/` 笔记（frontmatter `jira_url` 含单号、正文关键词；规则见 [obsidian-notes.md](../../references/obsidian-notes.md)）
- 命中同类问题 → 直接复用/更新历史结论，加速收敛；无命中 → 继续

**（2）确认项目/分支/工作区 + V2 切环境（SSH）**：**直接使用阶段 1 立项的新 JIRA 单建 feature 分支**，操作同 feature-development 阶段 2——按 [workspace-setup.md](../../references/workspace-setup.md)（权威源）在 **V2 工作区**搭建：确认项目（从 fixVersions/变体/描述推断）→ 改 `.imobuilder`（`ls config/` 现查）→ **建 feature 分支**（分支名 `feature/<新Story工单号>-<标题小写连字符>`，reset 前残留改动检查见手册 §4）→ version_did/zos_msg 等依赖仓库同步（手册 §4）。

- `reset --hard` / `clean -xdf` 仅在建分支前用于还原干净基线；**feature 分支上已有修复改动后不要再 reset**

**（3）编译 MCU 固件（SSH）**——保证分析对象是**可编过的基线代码**。标准命令一律查 **[build.md](../../references/build.md)**（权威源：命令 / 关键规则 / 排障 / 固件刷新），V2 工作区路径同文内命令形式。

**编译失败 → 读 [build.md](../../references/build.md)**（J6 clean 末步失败属正常、后台编译不要接 `| grep` 管道、固件排障、依赖仓库分支核对）。编译失败先按报错判断是环境问题还是代码问题——**代码编译错误本身可能就是问题单的答案**。

**（4）根因定位**：

- 按问题单描述定位相关模块/配置（components、复现步骤提到的功能），在 Y: 盘读代码
- 对照复现步骤走读代码逻辑，收敛到具体根因点（代码缺陷/配置错误的确切位置），并整理依据（代码位置、逻辑链、规格出处）
- 拿不准时列出疑点与需要的信息（问用户或查更多代码），不要硬下结论

> 后续迭代：二分法隔离（Harness 切断可疑模块上下联系）、故障注入（伪造输入确认状态机翻转位置）。

**（4.5）bench 复现（改码前，有条件必做）**：

基线编译通过后、动代码之前，先在基线固件上复现问题——**默认选 case (a) 完整 A/B 复现**（基线跑红 → 修复后跑绿，同一 testcase 互为对照），仅当**无测试环境**（板子/台架不在手）或**很难复现**（低概率、依赖特殊工况）才降级 case (b)（不做改前复现，以问题单附件 BLF/日志作为改前证据），降级时在结论里说明原因。

1. **写复现 testcase**：按复现步骤编写 DiagnosticTester 用例（写法见 validation-methods.md）；testcase 即阶段 3 修复后的回归用例，一次编写两处使用
2. **基线刷板 → 跑 testcase，期望复现失败（红）**：刷写方法同阶段 3（3）；复现成功 = 拿到第一手失败证据，进入下一步；复现失败（用例通过）说明复现条件没找对或问题不复存在——回到（4）重新审视，不要带着没复现过的现象去改代码
3. 复现结论并入（5）的分析结论一起呈现

```
（3）基线编译 → （4）根因定位 → （4.5）bench 复现（红） → （5）呈现结论
阶段 3：修复 → 编译 → 刷板 → 同一 testcase 跑绿 → 用户确认
```

**（5）呈现根因与修复方案，停下等用户确认**：向用户呈现根因结论（根因点 + 依据 + 复现结果）与修复方案（改哪里、怎么改）。确认后进入阶段 3。

## 阶段 3：方案验证与精准修复（V2 工作区 feature 分支）

**电源操作规则**：刷板/验证前 `cycle` 重启、之后 `off` 关闭，无程控电源时提示用户手动断电/上电——命令与 COM 号见 [validation-methods.md](../../references/validation-methods.md)「电源操作」节；J6 刷写的断电冷启动已由工具内置（[flashing.md](../../references/flashing.md)），刷板前无需重复 `cycle`。

在 V2 工作区的 feature 分支上做修复：SSH 写修复代码 → 编译 → 刷板 → 验证。

1. **最小化修复**：在确定的根因点修改代码/配置，避免涟漪效应。代码写入方式（SSH，Y: 盘禁止写源码；scp / heredoc）见 [workspace-setup.md](../../references/workspace-setup.md) §6；涉及 autosar 生成代码时先查 [autosar-code-generation.md](../../references/autosar-code-generation.md)（patch 标记规则）
2. **编译**：命令与排障一律查 [build.md](../../references/build.md)
3. **刷写（仅 J6，Windows 本地执行）**：命令、示例、`--img-dir` 规则、串口/电源 COM 识别、失败排查一律查 **[flashing.md](../../references/flashing.md)**（权威源）；`--img-dir` 指向 **V2 工作区**的编译输出（`Y:/01_Src/02_Workspace_J6_V2/src/<仓库>/build/<preset>/rpu_arm_gcc`）。TDA4_V2 无自动刷写工具，跳过刷写直接手动验证。

4. **验证 —— 停下等待**：跑**阶段 2（4.5）的复现 testcase，期望通过（绿）**——与改前的红形成 A/B 对照；用户按问题单复现步骤手动验证修复效果；**可自动化的验证按 [validation-methods.md](../../references/validation-methods.md) 执行**——诊断相关验证用 DiagnosticTester（编写 testcase → 运行验证），采集 log 用 LogCollection，在线调试用 TRACE32（J6B `/t32-j6b-connect`、TDA4 `/t32-tda4-connect`，断点/内存/任务调度时序等内部状态取证），电源操作配套见该文档。验证通过后用户会说继续；验证不通过则回到修复点迭代。

## 阶段 4：审查与合流

**交付收尾统一走 [delivery.md](../../references/delivery.md)**（权威源：commit/push → 创建 PR → 技术沉淀（docs + 笔记）→ PR 全部合并后关单 → 通知报告人；与 feature-development 共用）。本 skill 的差异点：

- **技术沉淀（commit 前做 docs 沉淀与笔记指针章节；push 后的笔记台账总结统一按 delivery.md §3）**：
  1. **docs/analysis/**：`docs/analysis/YYYY-MM-DD-<问题单号>-<主题>.md`——**按 [problem-analysis-report-template.md](../../../docs/analysis/problem-analysis-report-template.md) 模板写**（七章标准缺陷报告主轴：缺陷概述含环境矩阵/复现性与回放/根因分析含知识召回+排除链+5Whys/分析结论与分流/修复方案含纠正与预防/验证结果/关闭与生命周期）；较大修复方案另写 `docs/design/YYYY-MM-DD-<工单号>-<主题>-design.md`（按仓库设计模板）
  2. **Obsidian 笔记**：Problem Analysis 章节放一行指针 + 结论一句话；Design 章节（如有设计文档）一行指针；Test Result 一行指针 + N/N PASS + A/B 结论（基线红 → 修复绿）；操作规则见 [obsidian-notes.md](../../references/obsidian-notes.md)（权威源）
  3. **JIRA 问题单评论**：`POST /rest/api/2/issue/<key>/comment`，写分析过程要点 + 根因 + 修复结论（中文 JSON 用 `--data-binary @file.json`，认证同阶段 1）
- **通知报告人**：对象为**来源问题单**的 reporter
- **关联单关闭**：来源问题单沿路线一推进到 IMPLEMENTED（RESOLVED 由测试侧回归后关）

## ⚠️ 关键规则

- **Y: 盘不允许任何 git 操作（含只读）**，也禁止写源码（仅许刷写读镜像/读代码/写 `.imobuilder`）：git 一律 `ssh yaohua@10.0.12.42` 执行，代码写走 SSH（scp/heredoc），详见 CLAUDE.md 安全红线
- **问题修复在 V2 工作区全流程交付**：建 feature 分支（新 Story 工单号）→ 修复 → commit/push → PR → 关单，本 skill 独立完成，**不再转 feature-development 重做**；需求开发（V1 老工作区）才走 feature-development
- Token 存放位置、认证方式、踩坑规则见 [token-authentication.md](../../references/token-authentication.md)（权威源）；红线：绝不内联进任何会被提交的文件
