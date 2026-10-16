# problem-analysis Skill 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `problem-analysis` skill——JIRA 问题单先分析再分流：是问题 → story-creation + dev-workflow；不是问题 → JIRA 说明理由 + refuse 关单。

**Architecture:** 纯文档变更。新建 `.claude/skills/problem-analysis/SKILL.md`（6 步流程，V2 工作区专用、只分析不提交），CLAUDE.md skill 入口表加一行。git/token 硬规则引用 dev-workflow 现行规则，不复制。

**Tech Stack:** Claude Code 项目级 skill（Markdown 文档），JIRA REST API，SSH + imobuilder。

**设计文档:** `docs/design/2026-10-16-problem-analysis-skill-design.md`

---

### Task 1: 创建 problem-analysis SKILL.md

**Files:**
- Create: `.claude/skills/problem-analysis/SKILL.md`

- [ ] **Step 1: 写入 SKILL.md 完整内容**

创建 `.claude/skills/problem-analysis/SKILL.md`，内容如下（frontmatter 的 description 含触发词，风格对齐 story-creation/dev-workflow）：

````markdown
---
name: problem-analysis
description: JIRA 问题单分析分流流程：拉问题单 → 确认项目/分支 → V2 工作区切环境（.imobuilder + mcu/version_did/zos_msg 三仓库）→ 编译 MCU 固件 → 分析代码 → 结论分流（是问题 → story-creation + dev-workflow 建单开发；不是问题 → JIRA 写明理由 + refuse 关单）。当用户提到 问题分析、分析问题单、分析下这个 problem、refuse，或给出问题单号（如 D3ACYI-xxxx）要求先分析时使用，即使用户只提到其中一个环节。注意：本 skill 在 V2 工作区（01_Workspace_TDA4_V2 / 02_Workspace_J6_V2）分析，只分析不提交代码；正式开发走 dev-workflow（老工作区）。
---

# JIRA 问题单分析分流流程（拉单 → 切环境 → 编译 → 分析 → 分流）

有些问题单不一定需要修改代码。本流程先根据问题单分析清楚具体是什么问题，再决定去向：**是问题 → 建 story + 走 dev-workflow；不是问题 → 在问题单上说明原因并走 refuse 关单**。

6 步流程。**第 6 步结论必须先呈现给用户确认**，确认后才执行分流动作。

开始前用 TaskCreate 为本次分析创建任务列表（每步一个任务），逐步勾选，随时可从任务列表恢复进度。

## 路径角色（V2 工作区，与老工作区并存）

| 路径 | 角色 |
| --- | --- |
| `10.0.12.42:/comp/user_data/yaohua/01_Src/01_Workspace_TDA4_V2` | TDA4 V2 工作区（问题分析专用） |
| `10.0.12.42:/comp/user_data/yaohua/01_Src/02_Workspace_J6_V2` | J6 V2 工作区（问题分析专用） |
| `Y:\01_Src\01_Workspace_TDA4_V2` / `Y:\01_Src\02_Workspace_J6_V2` | 上述工作区在 Windows 侧的编辑入口（改 .imobuilder、读代码走 Y: 直改） |

- V2 工作区与老工作区（01_Workspace_TDA4 / 02_Workspace_J6）**并存**：V2 只做问题分析，**一般不提交代码**；正式开发在老工作区走 dev-workflow
- mcu 仓库：TDA4_V2 → `mcu_app_tda4`；J6_V2 → `mcu_app_j6_v2`

## 第 1 步：拉问题单详情

用 JIRA REST API（认证与端点见 story-creation skill 的「JIRA API 速查」，PAT Bearer）：

- `GET https://jira.imotion.ai:7070/rest/api/2/issue/<问题单号>?fields=summary,description,status,fixVersions,components,assignee,reporter,issuelinks,attachment`
- description 里的**复现步骤与测试现象原样保存**——这是后续分析和结论的依据，不能只写概括；description 为空时查评论（`GET .../issue/<key>/comment`）
- 有附件则下载留存（分析时看）
- 记录 fixVersions、变体字段（customfield_15000）、components——第 2 步推断项目用

## 第 2 步：确认项目/分支/工作区

1. **项目**：从 fixVersions、变体字段、description 推断（如 fixVersion 提到 v2xeu 相关版本、描述里写车型）；拿不准用 AskUserQuestion 问
2. **分支**：默认 develop；问题单描述/评论提到特定版本（如 V460 基线）时用对应 release 分支，拿不准就问
3. **工作区**：按项目定——TDA4 项目 → `01_Workspace_TDA4_V2`，J6 项目 → `02_Workspace_J6_V2`；mcu 仓库随之确定（TDA4 → `mcu_app_tda4`，J6 → `mcu_app_j6_v2`）

## 第 3 步：V2 工作区切环境（SSH）

**（1）改 `.imobuilder` 的 build_product**（Y: 盘直接改）：

从 workspace `config/` 目录**现查**该项目的 preset/build_product 值（如 `ls Y:\01_Src\01_Workspace_TDA4_V2\config\`），**不维护写死的映射表**。查到后把 `.imobuilder` 的 `build_product` 改为对应值。

**（2）切 mcu 仓库分支**（SSH 执行，git 写操作禁止 Windows 本地执行）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/<01_Workspace_TDA4_V2|02_Workspace_J6_V2>/src/<mcu仓库>
git reset --hard
git clean -xdf
git checkout <branch_name>
git pull
```

**（3）version_did 和 zos_msg 同步切到相同分支**（与 mcu 同分支，develop↔develop，防接口不匹配）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/<工作区>/src/version_did
git reset --hard && git clean -xdf && git checkout <branch_name> && git pull
cd ../zos_msg
git reset --hard && git clean -xdf && git checkout <branch_name> && git pull
```

- ⚠️ 编译前核对各依赖仓库分支：`ssh yaohua@10.0.12.42 "cd <workspace>/src/<仓库> && git branch --show-current"`，必须与 mcu 一致
- `reset --hard` / `clean -xdf` 仅用于还原干净基线（V2 工作区只分析不提交，无私有改动需要保留）

## 第 4 步：编译 MCU 固件（SSH，只编译不刷板）

编译目的是保证分析对象是**可编过的基线代码**。不刷板、不复现。

**TDA4_V2**：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/01_Workspace_TDA4_V2/
imobuilder clean mcu_app_tda4 -r
imobuilder build mcu_app_tda4 -r
```

**J6_V2**（`-x parking_dr uper_app` 必须带，理由同 dev-workflow 第 6 步）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/02_Workspace_J6_V2/
imobuilder clean mcu_app_j6_v2 -r -x parking_dr uper_app
imobuilder build mcu_app_j6_v2 -r -x parking_dr uper_app
```

编译规则与排障**引用 dev-workflow skill 第 6 步**（不在此重复）：J6 clean 末步 `-clean_binary` 失败属正常、后台编译不要接 `| grep` 管道、parking_dr/uper_app/MCU21 固件排障（6.1）。编译失败先按报错判断是环境问题还是代码问题——代码编译错误本身可能就是问题单的答案。

## 第 5 步：分析代码

- 遵循「先检索再动手」：先查 `docs/analysis/` 是否有同类问题、`docs/design/` 是否有相关设计
- 按问题单描述定位相关模块/配置（components、复现步骤提到的功能），在 Y: 盘读代码
- 对照复现步骤走读代码逻辑，形成结论：**是问题**（代码缺陷/配置错误，需修改）或**不是问题**（行为符合设计/规格、测试方法不当、非本模块问题等），并整理依据（代码位置、逻辑链、规格出处）
- 拿不准时列出疑点与需要的信息（问用户或查更多代码），不要硬下结论

## 第 6 步：结论分流 —— 先呈现结论等用户确认

向用户呈现分析结论（是/不是问题 + 依据），**等用户确认后**才执行对应分流。

### 6.0 分析报告三处沉淀（呈现结论时同步做）

1. **docs/analysis/**：`docs/analysis/YYYY-MM-DD-<问题单号>-<主题>.md`——问题单摘要（复现步骤/现象原样）、分析过程、结论与依据
2. **Obsidian 笔记**：按项目模板在 `ClaudeCodeNote/Work Database/` 建独立分析笔记（frontmatter `jira_key` 指向问题单、`type: Problem`、`status: In Analysis`），Problem Analysis 章节填分析过程；结构参照 story-creation Stage 1
3. **JIRA 问题单评论**：`POST /rest/api/2/issue/<key>/comment`，写分析过程要点 + 结论（中文 JSON 用 `--data-binary @file.json`，认证同第 1 步）

### 6.1 是问题 → 转 story 开发（老工作区）

1. 分析笔记升级为 story 笔记：frontmatter `type: Story`、`status: Todo`
2. 走 `story-creation` skill 建 JIRA Story（关联问题单，Link to Problems 行填问题单号），笔记按 Stage 3 回写
3. 走 `dev-workflow` skill 在**老工作区**完成开发（分支/编译/刷写/验证/PR/收尾）

### 6.2 不是问题 → refuse 关单

1. JIRA 问题单加评论（若 6.0 未写过则此时写）：**为什么不是问题**——引用分析报告结论（行为符合设计/规格出处、测试方法问题等）
2. 查可用流转：`GET https://jira.imotion.ai:7070/rest/api/2/issue/<key>/transitions`，选 refuse/拒绝类流转（名称或目标状态含 refuse/拒绝/Declined 之类）
3. 执行流转：`POST .../issue/<key>/transitions`，body `{"transition":{"id":"<id>"}}`；必填字段按 400 报错补齐（自适应，同 dev-workflow 第 12 步关 Problem 单的方式）
4. Obsidian 笔记收尾：`status: Done`、`completed: 今天`、Notes 补分析结论与关单记录

## ⚠️ 关键规则

与 dev-workflow 完全一致，详见该 skill「关键规则」与「Token 与安全」：

- git 写操作（reset/clean/checkout/commit/push）一律 `ssh yaohua@10.0.12.42` 执行；本地 Y: 盘 git 仅只读且必须 `-c core.filemode=false`
- **V2 工作区只分析不提交**：不建 feature 分支、不 commit/push
- Token 从 `C:\Users\YH\.claude\` 配置读取，绝不内联进任何会被提交的文件；`.imobuilder` 含 CI token，不要暴露其内容
````

- [ ] **Step 2: 核对内容完整性**

走查 SKILL.md 是否覆盖需求全部功能点：切分支 + .imobuilder、version_did/zos_msg 同步切换、编译、分析、refuse 分流。确认无 "TBD/待定" 类占位。

### Task 2: 更新 CLAUDE.md skill 入口表

**Files:**
- Modify: `CLAUDE.md`（「## skill 入口」一节）

- [ ] **Step 1: 在 skill 入口表加一行**

在 `## skill 入口` 一节的列表末尾（dev-workflow 那行之后）追加：

```markdown
- 问题分析（V2 工作区，分析/refuse 分流）→ `problem-analysis`
```

修改后的完整小节：

```markdown
## skill 入口

- 立项（建 Obsidian 笔记 / 建 JIRA Story）→ `story-creation`
- 开发全流程（分支/编译/刷写/验证/PR/收尾）→ `dev-workflow`
- 问题分析（V2 工作区，分析/refuse 分流）→ `problem-analysis`
```

### Task 3: 验证与提交

**Files:**
- 无新增，验证 Task 1/2 产物

- [ ] **Step 1: 引用一致性检查**

1. `Glob .claude/skills/problem-analysis/SKILL.md` 确认文件存在
2. 核对 SKILL.md 中路径拼写与设计文档 §2 一致：`01_Workspace_TDA4_V2` / `02_Workspace_J6_V2` / `mcu_app_tda4` / `mcu_app_j6_v2`
3. 核对引用的 skill 名（story-creation、dev-workflow）与 `.claude/skills/` 下实际目录名一致
4. 确认 SKILL.md 无 JIRA/Bitbucket token 等敏感值内联（只有路径指引）

- [ ] **Step 2: 提交**

```bash
git add .claude/skills/problem-analysis/SKILL.md CLAUDE.md
git commit -m "feat(skill): add problem-analysis skill for JIRA problem triage"
```
