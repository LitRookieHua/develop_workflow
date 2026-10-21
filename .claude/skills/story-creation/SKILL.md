---
name: story-creation
description: 需求创建/工作项立项全流程：需求来源（JIRA 需求单/JIRA 问题单/手动输入）→ 创建 Obsidian 工作笔记（Work Database + Work Item Template）→ 创建 JIRA Story 并关联来源单 → 回写笔记。这是一个跨系统的工作项创建过程，笔记和 JIRA 单都是产出物。当用户给出 JIRA 需求或问题单链接（如 IDC310BAICREQ-1158）要求"创建笔记"、说"建个 Story"、"新需求要立项/开发"、提供需求描述要落地时使用，即使用户只提到其中一个环节（只说建笔记或只说建 JIRA 单）。项目范围：IDC310BAIC(N60)/IDC310(GAC)/IDC310GAC/J6BREQ/IDC510/D3ACYI(IDC300)/D1CYC(JETOUR)/F4CMC(CMC)/PDCU 等车型项目。注意：本 skill 只管立项创建；立项后的开发——需求开发走 feature-development skill（V1 工作区 5 阶段），问题修复走 problem-analysis skill（V2 工作区全流程）。
---

# Story 创建工作流（需求 → Obsidian 笔记 → JIRA）

从需求来源创建新工作项的完整过程，最终产出两样东西：一份 Obsidian 工作笔记 + 一张关联好的 JIRA Story。笔记是工作项台账（状态、时间线、证据指针），JIRA 单是协作入口——两者一起创建、互相链接。

**本 skill 依赖以下权威源，涉及这些内容一律查权威源，不在本文件重复**：

| 内容 | 权威源 |
| --- | --- |
| 笔记创建/更新（路径、统一模板、frontmatter、章节语义、检索） | `.claude/references/obsidian-notes.md` |
| JIRA 创建/关联（通用必填、payload 陷阱、创建步骤、状态流转） | `.claude/references/jira-operation.md` 第 1 节 |
| 各项目创建参数（变体字段、fixVersion、components、链接方向） | `.claude/references/jira-story-params.json` |

## 流程总览

1. **解析输入**（Stage 0）：拿到需求/问题的完整信息
2. **创建 Obsidian 笔记**（Stage 1）
3. **创建 JIRA Story**（Stage 2）：默认值 + 项目必填字段
4. **回写笔记**（Stage 3）

---

## Stage 0：解析输入

### 来源 A：JIRA 需求单（xxxREQ-xxx）

用户给 URL 或 key。用 API 拉详情（见文末速查）：

- 提取：`summary`、`description`、`status`、`fixVersions`、`components`、`issuelinks`、`duedate`
- 查 `issuelinks`：若已有 implemented 关联的 Story，本次是**变更需求**——看 changelog 确认需求描述近期是否更新过（变更通常源于需求更新，新 Story 描述要写明与原实现的差异）
- 需求的 description 里通常有功能明细（会话/安全矩阵、NVM、默认值等），原样整理进笔记 Details

### 来源 B：JIRA 问题单（Problem/BugFix）

同样拉详情，作为 Story `Link to Problems` 关联的来源（笔记 `jira_url` 立项时指向它）。

- **复现步骤与测试现象在 Problem Description 字段（`customfield_12007`），标准 description 常为空**——原样同步到笔记 Details，这是后续问题分析和验证的依据，不能只写概括；该字段也为空时查评论（完整规则见 problem-analysis skill 阶段 1）

### 来源 C：手动输入需求

- 询问缺失信息：项目（决定 JIRA 项目 key 和创建参数）、概要、描述、**修改分支（develop / release/...，用户没给就问，不能留"待确认"）**
- 不要问 fix version / due date / assignee——Stage 2 有固定默认值，问了用户会烦

---

## Stage 1：创建 Obsidian 笔记

按 [obsidian-notes.md](../../references/obsidian-notes.md)（权威源）创建，本阶段要点：

- 统一用 `ClaudeCodeNote/Templates/Work Item Template.md`，放 `ClaudeCodeNote/Work Database/<英文文件名>.md`；H1 与 JIRA Story summary 同名（英文），正文可中文
- frontmatter：`type: Story`、`status: Todo`、`created: 今天`、`jira_url` 暂指向来源单（Stage 3 回写为新 Story）
- **Details**：一句话概述打头 + 来源单描述**原样**同步（需求单 description / 问题单 `customfield_12007`）+ 确认修改分支——用户消息里已给就直接用，没给就用 AskUserQuestion 问，不允许留"待确认"
- **Related Links**：来源单链接，以及 JIRA 单描述/评论中出现的相关链接 + `[[相关笔记]]`（如原实现的笔记）
- 来源单附件确有保存价值时下载到 `Work Database/assets/<NoteName>/`，路径记入 Related Links（大取证文件放仓库用例目录 logs/，不放 Obsidian）

---

## Stage 2：创建 JIRA Story

创建规则全文（通用必填、payload 陷阱、创建步骤）见 [jira-operation.md](../../references/jira-operation.md) 第 1 节（权威源）。项目参数从 [jira-story-params.json](../../references/jira-story-params.json) 取：**已配置项目用对应项目节；未配置项目用 `_general` 基线**（参照 IDC310GAC 提炼，遇 400 按报错逐项调整），调整通过后把实测参数沉淀到该项目节。

### 默认值（不要问用户）

- **Fix Version** = 来源需求单/问题单的 fixVersions，按 jira-story-params.json 的换算规则转成 Story 项目内版本
- **Due Date** = 创建日期 + 7 天
- **Assignee** = `Hua.Yao`

仅当来源单没有可用版本时才询问用户。

---

## Stage 3：回写笔记

- frontmatter：`jira_url` 改为新 Story
- Related Links：新 Story 链接放最前
- Status Updates：补一行立项记录（日期 + Story 创建/关联结果）
- 向用户汇报：Story key + 链接 + 关联结果

## 边界：立项之后的开发流程不在本 skill 范围

立项后笔记会持续补充：实现分支、Code Changes、验证结果、PR 链接等。完整开发流程（切分支、编译、刷写、验证、提 PR、关闭工单）走 `feature-development` skill。

---

## JIRA API 速查

- Base：`https://jira.imotion.ai:7070`
- 认证：PAT Bearer，token 位置与踩坑规则见 [token-authentication.md](../../references/token-authentication.md)（权威源）
- **创建单/状态流转规则**：见 [jira-operation.md](../../references/jira-operation.md)（权威源，含 jira-story-params.json 参数配置）
- 本 skill 常用端点：
  - 详情：`GET /rest/api/2/issue/{key}`
  - changelog：`GET /rest/api/2/issue/{key}?expand=changelog`
  - 附件列表：`GET /rest/api/2/issue/{key}?fields=attachment`（取 `content` URL 下载）
- Story issue type id = `10001`；JQL/字段里 issuetype、status 用 id 或英文名，中文值会被拒

### Windows bash 陷阱

中文 payload / 临时文件 / python 中文打印的踩坑规则一律查 [jira-operation.md](../../references/jira-operation.md) §1.1（权威源）。

### 遇到新项目约束时

创建失败（HTTP 400 "xxx是必需的"）通常是项目特有必填字段，把**实测验证过**的 JIRA 参数更新到 `.claude/references/jira-story-params.json` 对应项目节（权威源，仅收实测确认的参数，不从未验证的资料转录），并考虑存入项目记忆。项目未配置时先向用户确认参数再创建。
