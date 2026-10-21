# delivery：交付与合流手册

代码验证通过后的交付收尾统一权威源，feature-development（阶段 5）与 problem-analysis（阶段 4）共用。步骤：commit/push → 创建 PR → 技术沉淀（docs + 笔记）→ （PR 全部合并后）关单 → 通知报告人。各步细则见对应权威源（git-rules / pr-merge / obsidian-notes / jira-operation），本手册只管编排顺序与两 skill 的差异点。

## 1. commit + push（SSH）

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/<工作区>/src/<仓库>
git add <files>
git commit -m "feat(模块名): [工单号] 项目名 + 描述"
git push
```

commit 格式与全英文规则一律查 [git-rules.md](git-rules.md)（权威源）。push 后记下 commit hash（技术沉淀的笔记台账要用）。多分支/release 合入时第二个分支用 cherry-pick 移植（规则见 [workspace-setup.md](workspace-setup.md) §5）。

## 2. 创建 PR + 飞书通知 owner + PR 监控

⚠️ **关卡：创建 PR 前必读 [pr-merge.md](pr-merge.md)**（PR 创建 API、reviewers 名单、飞书通知对象与 open_id、PR 监控循环细则）。PR 标题 = commit 标题，PR 内容 = commit 内容；创建后按 pr-merge.md 发飞书通知并建每 10 分钟的 PR 监控（审批通过自动 merge、CI 失败处置、合并/拒绝通知本人）。

## 3. 技术沉淀（仓库 docs + Obsidian 笔记）

与开始时的知识召回（CLAUDE.md「先检索再动手」）成闭环：深度内容一律沉淀在仓库 docs/，笔记只放指针（分工见 [obsidian-notes.md](obsidian-notes.md) §1）。

**仓库 docs 沉淀（两 skill 差异）**：

| skill | docs 沉淀内容 | 时机 |
| --- | --- | --- |
| feature-development | `docs/design/YYYY-MM-DD-<工单号>-<主题>-design.md` 设计文档（按仓库设计模板，阶段 1 已写，交付前核对完整性） | 阶段 1 |
| problem-analysis | `docs/analysis/YYYY-MM-DD-<问题单号>-<主题>.md` 个案报告（按 problem-analysis-report-template.md，七章标准缺陷报告）；较大修复方案另写 `docs/design/` 设计文档 | 阶段 4 commit 前 |

**Obsidian 笔记总结（两 skill 共用，push 后做）**——操作规则见 [obsidian-notes.md](obsidian-notes.md)（权威源）：

- `status: In Review`
- Code Changes 新增台账行：commit hash + message + 分支
- Status Updates 新增本次日期记录：commit hash、PR 链接、待办（PR 合并后转已解决）
- Related Links 加 PR 链接 + 本次 docs 文档指针

（problem-analysis 的 Problem Analysis / Design / Test Result 指针章节在该 skill 阶段 4 commit 前写入，见其 SKILL.md；本步只补台账章节。）

## 4. 关闭 JIRA 单和笔记（PR 全部合并后自动执行，无需用户确认）

PR 监控确认全部 PR 已合并后执行；PR 尚未全部合并时不要做这步。transition id 与必填字段一律查 [jira-operation.md](jira-operation.md)（权威源）：

1. **确认合并**：`GET .../pull-requests/<id>`，state == `MERGED`
2. **Story 单转已解决**：两步流转（开放 →(4) 处理中 →(5) 已解决）
3. **关闭关联单**（漏关即收尾未完成）：除 story 外，JIRA Story 的 issuelinks、笔记 Related Links 及来源单中列出的关联单都要一并关闭：
   - **Problem 单**（issuetype=Problem）：三步流转沿路线一推进到 IMPLEMENTED；RESOLVED 由测试侧回归后关，不替测试关单
   - **需求单（Requirement 等）**：查看其可用 transitions（`GET .../issue/<key>/transitions`）选合适的关闭流转，有必填字段按报错补齐
4. **关闭笔记**：`status: Done`、`completed` 填 PR 合并日期、Status Updates 补关闭记录

## 5. 飞书通知报告人（PR 合并后自动执行）

查**来源单**的报告人并飞书通知已完成（命令格式见 [pr-merge.md](pr-merge.md) §2，`--as user`）：

1. **查报告人**：`GET https://jira.imotion.ai:7070/rest/api/2/issue/<来源单号>?fields=reporter`（认证见 [token-authentication.md](token-authentication.md)），取 `fields.reporter.displayName`
2. **查 open_id**：`lark-cli contact +search-user --queries "<姓名>" --as user`
3. **发消息**，格式：`<具体功能>已完成，并上传<分支列表>分支`
   - 具体功能 = 来源单/笔记的功能描述（如 `N60 DTC表V4.0更新`）
   - 分支列表 = 本流程全部 PR 的目标分支：`develop`，有 release 合入时一并列出（如 `develop、release/Chery/V2XEU_D065/V460`）

## 6. 两 skill 的差异点

技术沉淀差异见 §3 表格，其余差异如下：

| 差异 | feature-development（需求开发） | problem-analysis（问题修复） |
| --- | --- | --- |
| 通知报告人来源 | 来源需求单（parent requirement） | 来源问题单 |
| 关联单 | 来源需求单 + 关联问题单 | 来源问题单（路线一到 IMPLEMENTED） |
| 工作区 | V1 老工作区 | V2 工作区 |
