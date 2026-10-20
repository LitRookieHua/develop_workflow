# JIRA 单状态流转规则

Problem 单与 Story 单两条独立流转主干。流转是关单/交付类外部动作，执行前先向用户确认方向。

## Problem 单状态流转

### 路线一：走向实施解决（问题成立）

```
OPEN（开启/新建）→ IN_ANALYSIS（分析中）→ ANALYZED（已分析）→ IMPLEMENTED（已实施）
```

适用场景：经评估确认为有效问题，并完成了修复方案的落地实施。

### 路线二：走向关闭拒绝（问题不成立）

```
OPEN（开启/新建）→ IN_ANALYSIS（分析中）→ ANALYZED（已分析）→ REJECTED（已拒绝）
```

适用场景：经技术或业务分析后，发现属于非缺陷、无法复现或无需处理，予以驳回/拒绝。

### 返工与重开机制（Reopen）

- `RESOLVED → REOPENED`：后续测试验收、Code Review 或实际使用中发现 Bug/遗漏，重新打开
- `REOPENED → IN_PROGRESS`：重新打开后再次投入修复与开发，继续推进循环

## Story 单状态主干流转

### 核心推进路径

```
OPEN（开启/新建）→ IN_PROGRESS（进行中/开发中）→ RESOLVED（已解决/已完成）
```

- OPEN：团队或开发者接单后流转至 IN_PROGRESS
- IN_PROGRESS：开发与自测完成后，正常交付流转至 RESOLVED

### IN_PROGRESS 分出的其他终态分支

- `IN_PROGRESS → REJECTED（已拒绝）`：需求变更等原因驳回
- `IN_PROGRESS → DUPLICATED（重复单）`：重复提单

### 返工与重新打开（Reopen）机制

- 无论是 `RESOLVED`（正常到达）、`REJECTED` 还是 `DUPLICATED`（终止态），后续测试、评审或复核中需要返工均可流转回 `REOPENED`
- `REOPENED → IN_PROGRESS`：再次投入新一轮开发修复

## 实操备注

- API：`GET /rest/api/2/issue/<key>/transitions` 查可用流转，`POST .../transitions` body `{"transition":{"id":"<id>"}}` 执行；必填字段按 400 报错补齐
- 流转可用项随当前状态变化（如"开放"态只见 More Info Needed / Start Analysis，进入 In Analysis 后才出现 Duplicated 等）
- 实测先例（2026-10-20，IDC310GAC-5861 同类 0x27 单）：`开放 → In Analysis → Analyzed → Implemented → 已解决（RESOLVED，resolution=完成）`

### Problem 三步流转的 transition id 与必填字段（IDC310GAC 项目实测）

| 步骤 | transition id | 流转 | 必填字段 |
| --- | --- | --- | --- |
| 1 | `121` | OPEN → In Analysis | 无 |
| 2 | `31` | In Analysis → Analyzed | `customfield_12017`（英文根因描述）+ `duedate` + `fixVersions` |
| 3 | `41` | Analyzed → Implemented | `customfield_12305`（Link to Bugfix，easy-links 格式 `[{"key":"<story单号>"}]`，传字符串数组会报 expected Object） |

### 流转 400 报错的排查链（2026-10-20 五张单实测踩坑）

1. **fixVersions 必须传单子所属项目的版本 id**：同名版本在不同项目 id 不同（实例：`T09-Y_G710v6_260915` 在 IDC310GAC 项目是 27818，传成其他项目的 27445 报无效值）。先 `GET /rest/api/2/issue/<key>?fields=fixVersions,versions` 或查项目版本列表拿本单项目的 id
2. **旧单可能残留跨项目无效字段值，先归一再流转**：6886 实例——components 残留无效 id 16068（跨项目）、versions 残留 27445，直接流转 400。先 `PUT /rest/api/2/issue/<key>` 归一（components 改有效 id 如 Diagnostic=20703、versions 清空 `[]`），再走三步流转
3. fixVersions 为必填不能传空——31 步报错时优先核对版本 id 归属，而非删字段
