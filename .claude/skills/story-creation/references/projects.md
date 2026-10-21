# 项目差异速查表

创建 JIRA Story 前按项目核对本表。来源：历史验证结论（项目记忆）。字段选项可能随 JIRA 配置变化，创建失败时先看 400 报错内容，通常是必填字段缺失或格式错误（数组 vs 单对象）。

**JIRA 创建参数的权威源是 `.claude/references/jira-story-params.json`**（已配 IDC310GAC，其他项目逐步迁入）；本表聚焦各项目的笔记模板与历史踩坑知识，JIRA 字段参数以配置文件为准。

通用 Story 必填（所有项目）：project、summary、issuetype (Story=10001)、description、components、fixVersions、duedate。

---

## IDC310BAIC（北汽 iDC310 — Execution）

- **笔记模板**：`Templates/IDC310BAIC story template.md`（原 N60 story template，2026-10-20 更名）
- **Variant**：customfield_15000，必须**数组**格式 `[{"value": "BAIC N60"}]`（传单对象报 "data was not an array"）。选项：BAIC N60 / BAIC N53 / BAIC B81VS
- **fixVersion**：`B110/B120/B130/B210/B220/B230/B310/B320/B330/B420/B430` 系列，sw-cp Story 常用 B220/B230
- **components**：常见 `sw-cp`、`sw-bsw`、`sw-ap`、`sw-data-loop`、`feature-*`
- **cf_12025**：本项目不接受，不要传
- **需求链接**：type `implemented`，outwardIssue=需求单，inwardIssue=Story
- **Problem 链接**：type `is solved by` (id 10600)，outwardIssue=Story，inwardIssue=Problem
- **Story 工作流**：开放 →(4) 处理中 →(5) 已解决（Resolution=完成）
- **D1CYC / IDC100PFDEV 共用此工作流**

## IDC310（GAC — P034_iDC310_develop）

- **笔记模板**：`Templates/IDC310GAC Story Template.md`（原 IDC310 Story Template，2026-10-20 更名并按 IDC310GAC-7833 调参；IDC310 P034 老项目也用此模板，JIRA 表参数按实际单填）
- **Variant**：cf_12025 级联（GAC/T09、GAC/T51 等），格式 `{"value": "GAC", "child": {"value": "T51"}}`
- **T51 额外字段**（参考 IDC310-7990）：cf_15000 = `GAC T51` 数组 `[{"value": "GAC T51"}]`；cf_14803 = `GAC-Aion-T51-CN-Base-iDC310`；fixVersion `T51_G320_260214`
- **Problem 链接**：`is solved by`

## IDC310GAC（广汽 iDC310 — Execution，J6B 需求落地项目）

- J6BREQ / IR 广丰需求单的 Story 落在本项目（如 J6BREQ-12817 → IDC310GAC-7252）
- **笔记模板**：`Templates/IDC310GAC Story Template.md`（统一；**创建参数参考模板单 [IDC310GAC-7833](https://jira.imotion.ai:7070/browse/IDC310GAC-7833)**，2026-10-20 用户确认）
- **JIRA 创建参数**（Variant / fixVersion 换算 / components / 链接方向）：一律查 `.claude/references/jira-story-params.json` 的 IDC310GAC 节（权威源）
- cf_15000 在 JQL 中不可用 `cf_15000 =`，用 `"Vehicle Variant" = "GAC T75-G1"`

## IDC510（Smartxtruck — iDC510_Platform_Dev）

- **笔记模板**：`Templates/IDC510 Story Template.md`
- **Variant**：cf_12025 级联 Smartxtruck/STIDC510
- **fixVersions**：必填；Problem 用 `is solved by` 链接

## D3ACYI（IDC300 — iCAR V2X）

- **笔记模板**：`Templates/IDC300 Story Template.md`
- **Variant**：cf_15000 **多选数组**，iCAR V2X 相关 5 个选项
- **工作流**：Story 4→5 已解决；Problem 转 Implemented 前必填 RCA（cf_12017）

## D1CYC（JETOUR T1JFL3）

- **fixVersion**：`C011` 系列（注意 D100 的 T910 V1.0 不在 D1CYC）
- **component**：`sw-cp`
- **cf_15000**：JETOUR T1JFL3（id=17933）

## F4CMC（CMC RX）

- **笔记模板**：`Templates/IDC310 Story Template.md`（变体字段参考）
- **Variant**：cf_15000 = `CMC RX` **多选数组**（id=17947）；"RX" 只存在于 CMC 父选项下
- **fixVersion**：`M110/M120/M130` + `Z010V2`（Z010 诊断需求线）
- **Problem 关闭**：需 RCA + 版本 + 截止日期后 121→31→41
- **CMCRXJ6B 需求变更**：已 Implemented 的需求单可再 implemented 关联新 Story（F4CMC-59 → CMCRXJ6B-830/831/832）

## PDCU（CHERY T1JFL2）

- **笔记模板**：无（用户已删除 PDCU Story Template，需要时参考其他模板）
- **Variant**：CHERY/T1JFL2（T1JFL3 车型用 T1JFL2 选项）
- **无 issue link 权限**：不能用 issueLink 关联，改用 D3ACYI 的 cf_12305 (Link to Bugfix) 字段关联 Story

---

## 遗留约束（历史踩坑）

- **CMCRXJ6B**：hua.yao 无 Delete Issues 权限，创建错的单删不掉，创建前确认参数
- **CMCRXJ6B 开放状态 Requirement**：Hua.Yao 无可用流转，需有权限者先转 Reviewed
- **R4J 文件夹**（easeRequirements）：folder 查询用 customfield_14400；文件夹分配只能 web UI 拖拽，API 做不到
- **JIRA Server 9.x**：无 dashboard REST API（白名单拦截）
