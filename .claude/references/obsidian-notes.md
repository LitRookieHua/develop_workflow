# Obsidian 笔记操作规则

工作项笔记（Obsidian）的创建与更新统一权威源。其他地方涉及笔记操作一律指向本文档；配套：JIRA 单操作见 [jira-operation.md](jira-operation.md)。

分工总原则：**笔记是工作项台账**——只回答「这个单是什么、现在什么状态、证据在哪」；深度内容一律沉淀在 develop_workflow 仓库，笔记对应章节只放一行指针，不复制内容。

## 1. 定位与分工

| 内容 | 存放位置 |
| --- | --- |
| 工作项台账（状态 / 时间线 / 指针索引） | Obsidian 笔记 |
| 问题分析报告 | 仓库 `docs/analysis/`（按 problem-analysis-report-template.md） |
| 设计文档 | 仓库 `docs/design/` |
| 验证数据、取证证据（BLF/log 等） | 用例目录 `logs/`（如 `tools/DiagnosticTester/testcase/<项目>/<用例>/`） |

## 2. 路径与统一模板

- 库根：`D:\Workspace\21_ObsidianWorkspace\02_ClaudeCodeNote\ClaudeCodeNote\`
- **统一模板：`Templates/Work Item Template.md`**——所有新工作项笔记（Story / Problem）一律用此模板，**不再按项目选模板**。项目差异体现在 JIRA 单参数（[jira-story-params.json](jira-story-params.json)），不体现在笔记结构
- 历史项目 Story Template（IDC310GAC / IDC310BAIC / IDC510 / IDC300 等）仅服务于已存在的旧笔记，新建笔记不使用
- 笔记位置：`Work Database/<英文文件名>.md`
- JIRA 来源附件（确有保存价值时）：下载到 `Work Database/assets/<NoteName>/`，路径记入 Related Links；大取证文件（BLF/log）放用例目录 `logs/`，不放 Obsidian

## 3. 命名与语言

- 文件名、H1 标题必须英文；H1 与 JIRA summary 同名；正文内容可中文
- 正文注释用 `%% ... %%`（Obsidian 渲染时忽略）；frontmatter 是 YAML，注释用 `#`——`%%` 写进 frontmatter 会破坏解析

## 4. frontmatter 字段

| 字段 | 取值 / 说明 |
| --- | --- |
| `type` | `Story` / `Problem` |
| `status` | `Todo` / `In Analysis` / `In Review` / `Done` |
| `created` / `completed` | 创建 / 完成日期，`YYYY-MM-DD` |
| `tags` | 自由 |
| `jira_url` | 主 JIRA 单链接；**单据信息以该单为准，不在笔记里复制**。立项时暂指向来源需求/问题单，Story 建好后回写为新 Story |

JIRA 侧信息（fix version、due date、variant、assignee）**不进笔记**——创建/流转单据走 jira-operation.md。

## 5. 章节语义与填写时机

| 章节 | 填写时机 | 内容 |
| --- | --- | --- |
| Details | 立项 | 一句话概述打头；复现步骤 / 需求描述**原样**同步（问题单来自 `customfield_12007`，需求单来自 description），不能只写概括；另确认修改分支（develop / release/...），不允许留"待确认" |
| Problem Analysis | 分析完成 | 一行指针 `分析报告：docs/analysis/YYYY-MM-DD-<单号>-<主题>.md` + 结论一句话（是问题：根因 / 不是问题：理由） |
| Design | 设计完成 | 一行指针 `设计文档：docs/design/YYYY-MM-DD-<工单号>-<主题>-design.md` |
| Code Changes | commit 后 | 台账式记录：`<commit-hash> \`feat(模块): [工单号] 项目 描述\` — <分支>`；PR 链接 |
| Test Result | 验证后 | 一行指针 `验证：tools/DiagnosticTester/testcase/<项目>/<用例>/` + N/N PASS + 日期；A/B 结论一句话（基线红 → 修复绿） |
| Status Updates | 流转时 | 每条一行时间线（立项 / 根因确认 / 验证 PASS / PR 合并 / 关单） |
| Related Links | 随时 | 需求/问题/Story/PR/docs 链接 + `[[相关笔记]]` 跨工作项互链 + 附件路径 |

## 6. 各 skill 的笔记操作职责

| 环节 | skill | 笔记动作 |
| --- | --- | --- |
| 立项 | story-creation | 按模板建笔记（Details / Related Links）→ 建 JIRA Story → 回写 `jira_url`、Related Links 置顶 Story 链接、Status Updates 补立项行 |
| 问题分析 | problem-analysis | 按 `jira_url` 检索已有笔记；定性为问题后走 story-creation 立项；分析过程写 docs/analysis/ 报告，笔记只放指针 + 结论 |
| 开发/问题修复 | feature-development / problem-analysis | 更新 Design / Code Changes / Test Result / Status Updates；PR 全部合并后 `status: Done`、`completed` 填日期、Status Updates 补关单记录 |

## 7. 检索与关联

- 按 JIRA 单号检索：`jira_url` 中含单号（如 `IDC310GAC-6366`），grep 单号即可命中笔记
- 跨工作项关联用 `[[笔记文件名]]` 互链（Related Links 章节）
- 深度内容检索先查仓库 `docs/analysis/`、`docs/design/`（CLAUDE.md「先检索再动手」），笔记只是索引入口

## 8. 状态流转

```
Todo →（开始分析/开发）In Analysis →（代码就绪/评审中）In Review →（PR 合并、关单）Done
```

status 与 JIRA 单状态不强绑定——JIRA 流转以 jira-operation.md 路线为准，笔记 status 由各 skill 在对应环节更新。
