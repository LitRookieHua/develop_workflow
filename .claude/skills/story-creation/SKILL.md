---
name: story-creation
description: 需求创建/工作项立项全流程：需求来源（JIRA 需求单/JIRA 问题单/手动输入）→ 创建 Obsidian 工作笔记（Work Database + 项目模板）→ 创建 JIRA Story 并关联来源单 → 回写笔记。这是一个跨系统的工作项创建过程，笔记和 JIRA 单都是产出物。当用户给出 JIRA 需求或问题单链接（如 IDC310BAICREQ-1158）要求"创建笔记"、说"建个 Story"、"新需求要立项/开发"、提供需求描述要落地时使用，即使用户只提到其中一个环节（只说建笔记或只说建 JIRA 单）。项目范围：IDC310BAIC(N60)/IDC310(GAC)/IDC510/D3ACYI(IDC300)/D1CYC(JETOUR)/F4CMC(CMC)/PDCU 等车型项目。注意：本 skill 只管立项创建；立项后的开发全流程（分支/编译/验证/PR）用 dev-workflow skill。
---

# Story 创建工作流（需求 → Obsidian 笔记 → JIRA）

从需求来源创建新工作项的完整过程，最终产出两样东西：一份 Obsidian 工作笔记 + 一张关联好的 JIRA Story。笔记是工作项的主载体（后续开发记录都在笔记里），JIRA 单是协作入口——两者一起创建、互相链接。

## 流程总览

1. **解析输入**（Stage 0）：拿到需求/问题的完整信息
2. **创建 Obsidian 笔记**（Stage 1）：按项目模板，放 Work Database/
3. **创建 JIRA Story**（Stage 2）：默认值 + 项目必填字段
4. **回写笔记**（Stage 3）：jira_key、JIRA 表、Related Links

---

## Stage 0：解析输入

### 来源 A：JIRA 需求单（xxxREQ-xxx）

用户给 URL 或 key。用 API 拉详情（见文末速查）：

- 提取：`summary`、`description`、`status`、`fixVersions`、`components`、`issuelinks`、`duedate`
- 查 `issuelinks`：若已有 implemented 关联的 Story，本次是**变更需求**——看 changelog 确认需求描述近期是否更新过（变更通常源于需求更新，新 Story 描述要写明与原实现的差异）
- 需求的 description 里通常有功能明细（会话/安全矩阵、NVM、默认值等），原样整理进笔记 Details

### 来源 B：JIRA 问题单（Problem/BugFix）

同样拉详情，作为笔记 JIRA 表 `Link to Problems` 行和 Story 关联的来源。

- 问题单 description 里的**测试流程（复现步骤）与测试现象**必须原样同步到笔记 Details——这是后续问题分析和验证的依据，不能只写概括；description 为空时查评论

### 来源 C：手动输入需求

- 询问缺失信息：项目（决定 JIRA 项目 key 和笔记模板）、概要、描述、**修改分支（develop / release/...，用户没给就问，不能留"待确认"）**
- 不要问 fix version / due date / assignee——Stage 2 有固定默认值，问了用户会烦

---

## Stage 1：创建 Obsidian 笔记

规则：

- 文件名英文；**笔记标题（H1）和 JIRA Story summary 也必须英文**，正文内容可中文
- 路径：`ClaudeCodeNote/Work Database/<英文文件名>.md`
- **先读模板再写**：从 `ClaudeCodeNote/Templates/` 按项目选择（N60 story template / T51 story template / IDC310 / IDC510 / IDC300 / IDC100 / IFC4 Story Template）
- **结构严格跟模板**——章节和 frontmatter 字段一致，不要混用其他模板结构。统一结构：Description / JIRA（含 Customer Variants、Vehicle Variant、Implements_JRQ、Link to Problems 行）/ Details（问题/需求描述+确认修改分支）/ Problem Analysis / Design / Code Changes / Test Result / Attachments / Related Links（没有 Subtasks 和 Notes）
- JIRA 表必含两行：`Implements_JRQ`（需求来源链接）、`Link to Problems`（问题来源，无则写"无"）；变体字段按项目命名（如 T51 模板的 Customer Variants / Vehicle Variant 两行）
- **修改分支必须确认**：写笔记前确认修改分支（develop / release/... / 多分支）——用户消息里已给就直接用，没给就用 AskUserQuestion 问，Details 的"修改分支"不允许留"待确认"
- frontmatter 关键字段：`type: Story`、`status: Todo`、`created: 今天`、`jira_key`（暂指向来源单，Stage 3 回写）、`fix_version`、`due_date: 今天+7天`、`variant`、`assignee: Hua Yao / 姚华`
- **章节内容语义**（T51 模板的标准定义，其他项目模板同理）：
  - **Details**：清晰描述问题或需求 + 确认修改分支（如 develop / release/... 分支）
  - **Problem Analysis / Design**：设计思路 / 问题分析流程
  - **Code Changes**：代码改动 + commit（开发阶段补充）
  - **Test Result**：测试结果（开发阶段补充）
  - **Attachments**：查来源 JIRA 需求单/问题单是否有附件，**有则下载**到 `ClaudeCodeNote/Work Database/assets/<NoteName>/`
  - **Related Links**：需求单/问题单/Story 链接，以及 JIRA 单描述/评论中出现的相关链接 + `[[相关笔记]]`（如原实现的笔记）

---

## Stage 2：创建 JIRA Story

### 默认值（不要问用户）

- **Fix Version** = 笔记 frontmatter 的 `fix_version`
- **Due Date** = 创建日期 + 7 天
- **Assignee** = `Hua.Yao`

仅当笔记缺 `fix_version` 时才询问版本。

### 项目必填字段

每个项目的 Variant 字段、fixVersion 系列、链接方式都不同，**创建前必须查 [references/projects.md](references/projects.md)**。通用必填（所有项目 Story）：project、summary、issuetype、description、components、fixVersions、duedate。

### 创建步骤

1. payload 写入临时 JSON 文件——中文内容必须用 `--data-binary @file.json`，直接 `-d` 会报 Invalid UTF-8 start byte
2. `POST /rest/api/2/issue` 创建，记下返回的 key
3. 创建关联链接 `POST /rest/api/2/issueLink`：
   - 需求单：type `implemented`，`outwardIssue`=需求单，`inwardIssue`=新 Story
   - 问题单：type `is solved by`（方向等细节见 projects.md）
4. 删除临时文件

---

## Stage 3：回写笔记

- frontmatter：`jira_key`/`jira_url` 改为新 Story，补 `due_date`
- JIRA 表：Key/URL/类型/修复版本/截止日期行更新为新 Story
- Related Links：新 Story 链接放最前
- 向用户汇报：Story key + 链接 + 关联结果

## 边界：立项之后的开发流程不在本 skill 范围

立项后笔记会持续补充：实现分支、Code Changes、验证结果、PR 链接等。完整开发流程（切分支、编译、刷写、验证、提 PR、关闭工单）走 `dev-workflow` skill。

---

## JIRA API 速查

- Base：`https://jira.imotion.ai:7070`
- 认证：`Authorization: Bearer <token>`，token 在 `~/.claude/.mcp.json` → `mcpServers.atlassian.env.JIRA_API_TOKEN`
- 常用端点：
  - 详情：`GET /rest/api/2/issue/{key}`
  - changelog：`GET /rest/api/2/issue/{key}?expand=changelog`
  - 附件列表：`GET /rest/api/2/issue/{key}?fields=attachment`（取 `content` URL 下载）
  - 创建：`POST /rest/api/2/issue`
  - 链接：`POST /rest/api/2/issueLink`
- Story issue type id = `10001`；JQL/字段里 issuetype、status 用 id 或英文名，中文值会被拒

### Windows bash 陷阱

- 中文 JSON payload：`--data-binary @file.json`（不能 `-d` 内联）
- Windows python 看不到 git bash 的 `/tmp`——解析临时 JSON 用 `cat file | python -c` 或把文件放在项目目录
- python 打印中文：前置 `PYTHONIOENCODING=utf-8`

### 遇到新项目约束时

创建失败（HTTP 400 "xxx是必需的"）通常是项目特有必填字段，把解决后的结论更新到 [references/projects.md](references/projects.md)，并考虑存入项目记忆。
