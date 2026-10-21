# JIRA 操作规则

JIRA 单的创建与状态流转统一权威源。其他地方涉及 JIRA 操作时一律指向本文档；配套参数配置：[jira-story-params.json](jira-story-params.json)（按项目分节，Story 创建参数）。认证方式见 [token-authentication.md](token-authentication.md)（PAT Bearer）。

## 1. 创建 Story 单

### 1.1 通用规则（所有项目）

- **summary 必须英文**（与笔记 H1 同名），description 正文可中文
- 中文 payload 必须写临时 JSON 文件 + `--data-binary @file.json`（直接 `-d` 会报 Invalid UTF-8 start byte；Windows python 看不到 git bash 的 `/tmp`，临时文件放项目 `.tmp/` 或用 `cat file | python -c` 解析）；python 打印中文前置 `PYTHONIOENCODING=utf-8`
- 创建端点：`POST /rest/api/2/issue`；关联链接：`POST /rest/api/2/issueLink`
- 创建成功后立即删除临时 payload 文件
- 遇到 HTTP 400 "xxx是必需的" = 项目特有必填字段缺失 → 把解决后的结论补进 jira-story-params.json 对应项目节

### 1.2 项目参数（配置文件）

**创建前必读 [jira-story-params.json](jira-story-params.json)**，按目标项目取参数。字段总表：

| 字段 | API 字段名 | 必填性 | 说明 |
| --- | --- | --- | --- |
| 项目 | `project` | 必填 | `{"key": "IDC310GAC"}` 等 |
| 问题类型 | `issuetype` | 必填 | Story = `{"id": "10001"}` |
| 概要 | `summary` | 必填 | 英文标题 |
| 描述 | `description` | 必填 | 正文 |
| 模块 | `components` | 必填 | 如 `[{"name": "Diagnostic"}]` |
| 修复的版本 | `fixVersions` | 必填 | 项目内版本名（版本 id 归属见 §2.3 排错链） |
| 截止日期 | `duedate` | 必填 | 创建日 + 7 天 |
| Vehicle Variant | `customfield_15000` | 按项目 | IDC310GAC 必填，数组格式 |
| 经办人 | `assignee` | 必填 | 默认 `{"name": "Hua.Yao"}` |
| Implements_JRQ | `issuelinks` | 选填 | 链接需求单（type `implemented`） |
| Link to Problems | `issuelinks` | 选填 | 链接问题单（type `is solved by`） |

已配置项目：**IDC310GAC**（含 fixVersion 换算规则、变体示例、模板单 7833）。其他项目参数后续总结时补进配置文件。

### 1.3 创建步骤

1. 从 jira-story-params.json 取目标项目参数，组装 payload 写入 `.tmp/` 下临时 JSON
2. `POST /rest/api/2/issue` 创建，记下返回的 key
3. 创建关联链接 `POST /rest/api/2/issueLink`（需求单/问题单方向按配置文件 `issuelinks` 节）
4. 删除临时文件，向用户汇报 Story key + 链接

## 2. 状态流转

流转是关单/交付类外部动作，执行前先向用户确认方向。Problem 单与 Story 单两条独立流转主干。

### 2.1 Problem 单状态流转

#### 路线一：走向实施解决（问题成立）

```
OPEN（开启/新建）→ IN_ANALYSIS（分析中）→ ANALYZED（已分析）→ IMPLEMENTED（已实施）
```

适用场景：经评估确认为有效问题，并完成了修复方案的落地实施。RESOLVED 由测试侧回归后关，不替测试关单。

#### 路线二：走向关闭拒绝（问题不成立）

```
OPEN（开启/新建）→ IN_ANALYSIS（分析中）→ ANALYZED（已分析）→ REJECTED（已拒绝）
```

适用场景：经技术或业务分析后，发现属于非缺陷、无法复现或无需处理，予以驳回/拒绝。

#### 返工与重开机制（Reopen）

- `RESOLVED → REOPENED`：后续测试验收、Code Review 或实际使用中发现 Bug/遗漏，重新打开
- `REOPENED → IN_PROGRESS`：重新打开后再次投入修复与开发，继续推进循环

### 2.2 Story 单状态主干流转

#### 核心推进路径

```
OPEN（开启/新建）→ IN_PROGRESS（进行中/开发中）→ RESOLVED（已解决/已完成）
```

- OPEN：团队或开发者接单后流转至 IN_PROGRESS
- IN_PROGRESS：开发与自测完成后，正常交付流转至 RESOLVED

#### IN_PROGRESS 分出的其他终态分支

- `IN_PROGRESS → REJECTED（已拒绝）`：需求变更等原因驳回
- `IN_PROGRESS → DUPLICATED（重复单）`：重复提单

#### 返工与重新打开（Reopen）机制

- 无论是 `RESOLVED`（正常到达）、`REJECTED` 还是 `DUPLICATED`（终止态），后续测试、评审或复核中需要返工均可流转回 `REOPENED`
- `REOPENED → IN_PROGRESS`：再次投入新一轮开发修复

### 2.3 实操备注

- API：`GET /rest/api/2/issue/<key>/transitions` 查可用流转，`POST .../transitions` body `{"transition":{"id":"<id>"}}` 执行；必填字段按 400 报错补齐
- 流转可用项随当前状态变化（如"开放"态只见 More Info Needed / Start Analysis，进入 In Analysis 后才出现 Duplicated 等）
- 实测先例（2026-10-20，IDC310GAC-5861 同类 0x27 单）：`开放 → In Analysis → Analyzed → Implemented → 已解决（RESOLVED，resolution=完成）`

#### Problem 三步流转的 transition id 与必填字段（IDC310GAC 项目实测）

| 步骤 | transition id | 流转 | 必填字段 |
| --- | --- | --- | --- |
| 1 | `121` | OPEN → In Analysis | 无 |
| 2 | `31` | In Analysis → Analyzed | `customfield_12017`（英文根因描述）+ `duedate` + `fixVersions` |
| 3 | `41` | Analyzed → Implemented | `customfield_12305`（Link to Bugfix，easy-links 格式 `[{"key":"<story单号>"}]`，传字符串数组会报 expected Object） |

#### Story 单两步流转的 transition id（「开放」态无直接解决流转）

| 步骤 | transition id | 流转 | 必填字段 |
| --- | --- | --- | --- |
| 1 | `4` | 开放 → 处理中 | 无 |
| 2 | `5` | 处理中 → 已解决 | 无（resolution 自动为完成） |

#### 流转 400 报错的排查链（2026-10-20 五张单实测踩坑）

1. **fixVersions 必须传单子所属项目的版本 id**：同名版本在不同项目 id 不同（实例：`T09-Y_G710v6_260915` 在 IDC310GAC 项目是 27818，传成其他项目的 27445 报无效值）。先 `GET /rest/api/2/issue/<key>?fields=fixVersions,versions` 或查项目版本列表拿本单项目的 id
2. **旧单可能残留跨项目无效字段值，先归一再流转**：6886 实例——components 残留无效 id 16068（跨项目）、versions 残留 27445，直接流转 400。先 `PUT /rest/api/2/issue/<key>` 归一（components 改有效 id 如 Diagnostic=20703、versions 清空 `[]`），再走三步流转
3. fixVersions 为必填不能传空——31 步报错时优先核对版本 id 归属，而非删字段
