# AUTOSAR 代码生成规格（autosar-code-generation）

> 权威源：本文档是 AUTOSAR 生成代码人工修改规则的唯一权威源。CLAUDE.md 与其他文档只指向这里；规则更新时改本文档，不改指向处。

## 1. AUTOSAR patch 标记规则

**任何对 AUTOSAR 生成代码（`cpj_*/autosar/` 下源码）的人工修改，必须在改动前后加 patch 标记**——否则下次生成 autosar 代码会直接覆盖丢失人工提交。

### 1.1 标记格式

```c
/* <{项目名}PATCH P{id}> */
<修改的代码行>
/* </{项目名}PATCH P{id}> */
```

- `{项目名}`：该文件所属 autosar 项目子目录名**大写**（如 `t68` → `T68`，`s52-e046` → `S52-E046`，连字符保留）
- `{id}`：本文件内 patch 编号；新 patch 取文件中已有最大编号 +1，从 `P1` 起
- 多行改动共用一对标记（包裹整段改动，不逐行标记）；同一文件多处独立改动用不同 id

### 1.2 示例

`t68` 项目的 `PduR_Gateway_TpDcmTx.c` 首个 patch（IDC310GAC-7835）：

```c
/* <T68PATCH P1> */
TpSduLength = (info != NULL_PTR) ? info->SduLength : SessionPtr->SduLength_auo[SessionPtr->Rx_FifoInstanceUsed_u8];
/* </T68PATCH P1> */
```

### 1.3 打 patch 前的检查

1. 先 grep 该文件已有的 PATCH 标记（`grep -n 'PATCH P' <file>`），确定下一个 id
2. 确认改动行未被既有 patch 包裹（避免嵌套/重叠）

### 1.4 代码生成后的 patch 重放

回归生成 autosar 代码后，按标记检索并人工重放：

```bash
grep -rn '<T68PATCH P' cpj_gac/autosar/t68/
grep -rn '<S52E046PATCH P' cpj_gac/autosar/s52-e046/
```

生成工具覆盖文件后，被覆盖丢失的 patch 需按标记逐条对照重打（先例：分析报告 `docs/analysis/` 与 Story 笔记中记录的 patch 内容）。

## 2. 生成目标与路径（既有约定）

- autosar 代码生成目标：`D:\Workspace\01_Projects\02_Src`（本地，tools/autosar_gen）
- 生成产物同步到服务器仓库：D: 暂存后 `scp -r` 推送（Y: 盘禁止写源码，见 CLAUDE.md 安全红线）
- 服务器仓库内 `cpj_*/autosar/` 为编译实际使用的一份——patch 必须打在服务器仓库文件上

## 3. 变更记录

| 日期 | 变更 | 来源 |
| --- | --- | --- |
| 2026-10-20 | 初版：patch 标记规则从 CLAUDE.md 迁入并扩充（检查/重放流程） | IDC310GAC-7835 交付（用户定规） |
