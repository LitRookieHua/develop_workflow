# Git 操作规则

所有 git 写操作（commit/push/分支管理）的统一规则。其他地方涉及 git 操作时一律指向本文档。

## 安全红线（先于一切）

- **Y: 盘不允许任何 git 操作（含只读）**：git 一律 `ssh yaohua@10.0.12.42` 在服务器工作区执行
- 代码修改禁止走 Y: 盘（写源码走 SSH：D: 暂存后 `scp` 推送，或 SSH heredoc）
- 代码修改按工作项类型分流：需求开发走 feature-development（V1 老工作区），问题修复走 problem-analysis（V2 工作区全流程交付）

## Commit 提交规则

### 格式

```
feat(模块名): [工单号] 项目名 + 改动描述
```

- **模块名**：本次改动所属模块，如 `dcm`、`dia_cfg`
- **工单号**：JIRA 工单号放方括号里，如 `[F4CMC-41]`（可从分支名 `feature/F4CMC-41-xxx` 获取）
- **描述**：先项目/变体名（如 `Rx`），再写实际改动内容

### 示例

```
feat(dcm): [F4CMC-41] Rx change security access and enable condition
```

### 规则

1. **commit 内容必须全部使用英文**——title 和 body 都不许出现中文
2. 用户给参考示例时只套用格式，内容如实描述本次改动，不照抄参考内容
3. type 按改动性质选：`feat`（新功能）/ `fix`（缺陷修复）/ `docs`（文档）/ `refactor`（重构）等
