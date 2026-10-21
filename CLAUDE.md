# develop_workflow 硬规则

## 安全红线

- **Y: 盘仅限三种操作：刷写（读 build 镜像）、读代码、写 `.imobuilder`。其余一律禁止**：
  - **git 操作（读和写都算）一律不允许在 Y: 执行**——全部 `ssh yaohua@10.0.12.42`
  - 代码修改（写源文件）也禁止走 Y:——改走 SSH（D: 暂存后 `scp` 推送，或 SSH heredoc 写服务器路径）
  - 原因 1：`Y:\01_Src` 是服务器 10.0.12.42（`/comp/user_data/yaohua/01_Src`）的网络映射，本地 git `core.autocrlf=true` 会把工作区文件改写成 CRLF 污染服务器仓库（曾实际污染 3432 个文件）
  - 原因 2：Y: 映射不保留文件执行位，经 Y: 写文件会把 mode 644→755 带进 commit（2026-10-19 J02 DoIP 实际发生）
- **令牌安全与认证**：token 只从 `C:\Users\YH\.claude\` 下配置读取，绝不内联进任何会被提交的文件；`.imobuilder` 含 CI token，不要暴露其内容。CI / JIRA / Bitbucket 的 token 存放位置、认证方式（Bearer 前缀拼接、`\r\n` 剥离等踩坑）一律先查 [token-authentication.md](.claude/references/token-authentication.md)（权威源）
- **commit 格式**（MCU 仓库，全局规则）：`feat(模块名): [工单号] 项目名 + 描述`，**commit 内容必须全部英文**——完整规则见 [git-rules.md](.claude/references/git-rules.md)（权威源）
- **JIRA 状态流转**：流转路线、transition id、必填字段、400 排错链一律先查 [jira-operation.md](.claude/references/jira-operation.md)（权威源：创建参数配置 jira-story-params.json + 状态流转），不要凭记忆猜 transition id；API 实测值与该文档冲突时以文档为准并及时更新文档
- **AUTOSAR 生成代码**：`cpj_*/autosar/` 下源码的人工修改规则（patch 标记防生成覆盖等）一律先查 [autosar-code-generation.md](.claude/references/autosar-code-generation.md)（权威源，名称：autosar 代码生成规格；patch 规则是其中一个章节）

## 路径角色

| 路径 | 角色 |
| --- | --- |
| `D:\Workspace\01_Projects\02_Src` | 本地代码，**autosar 代码生成专用**（tools/autosar_gen 生成目标）+ scp 推送暂存 |
| `10.0.12.42:/comp/user_data/yaohua/01_Src` | 服务器：**编译/代码分析/代码修复/git 全部操作/代码写入** |
| `Y:\01_Src`（服务器映射，同一文件系统） | 仅：刷写读镜像、读代码、写 `.imobuilder` |
| V1 工作区（`01_Workspace_TDA4` / `02_Workspace_J6`） | **需求开发**（feature-development skill） |
| V2 工作区（`01_Workspace_TDA4_V2` / `02_Workspace_J6_V2`） | **问题分析修复全流程**（problem-analysis skill） |

## 先检索再动手（知识召回 → 沉淀闭环）

任何工作项（需求开发 / 问题分析）开始时先做**知识召回**：查 `docs/analysis/` 同类个案、`docs/design/` 类似设计方案、Obsidian `Work Database/` 笔记（检索规则见 [obsidian-notes.md](.claude/references/obsidian-notes.md) §7）——有则复用/更新历史结论，无命中再新建。结束时**沉淀回 docs/ 与笔记**（交付收尾见 [delivery.md](.claude/references/delivery.md) §3 技术沉淀）：排障个案写进 analysis/，较大改动方案写进 design/，笔记只放指针。

## 目录约定

- **Obsidian 工作项笔记**（`ClaudeCodeNote/Work Database/`）是工作项台账，深度内容只进仓库 docs/ 和用例 logs/；创建/更新规则（统一 Work Item Template、frontmatter、章节语义）一律先查 [obsidian-notes.md](.claude/references/obsidian-notes.md)（权威源）
- `docs/analysis/` 具体问题个案报告，**按 [problem-analysis-report-template.md](docs/analysis/problem-analysis-report-template.md) 模板写**；`docs/design/` 设计方案，**按 autosar-general-feature-design-template（MCU/AUTOSAR）或 general-functional-design-template（通用）模板写**
- `tests/harness/` 测试桩，两层结构（详见 `tests/harness/README.md`）：
  - **通用手段**：`diag_test/`（DiagnosticTester 跑用例）、`mcu_log/`（LogCollection / 调试串口采集）——只放与具体问题无关的通用工具
  - **问题专属**：`tests/harness/<模块名>_<harness描述>/`（如 `dcm_sec_relock_1003`、`dcm_did_f190`）——根目录放 python 脚本，`testcases/` 放用例，`logs/` 放运行产物与取证证据；越轻量、解耦越干净越好
- `tools/` 工具**运行时权威源**（10_tools 已冻结不再更新，工具迭代在这里做）
- `.tmp/` 临时文件（JIRA API 响应转储、取数中间产物等，不进 git）——**会话内产生的临时文件一律写 `.tmp/`，禁止落在仓库根目录**；`.tmp/` 内容可随时清理，重要结论要沉淀进 docs/ 或笔记后再清

## skill 入口

- 立项（建 Obsidian 笔记 / 建 JIRA Story）→ `story-creation`
- 需求开发（V1 工作区，5 阶段：需求解析与架构映射/分支/编码/验证/PR 收尾）→ `feature-development`
- 问题分析（V2 工作区全流程交付，4 阶段：捕获回放与问题定性/根因收敛/修复验证/审查合流）→ `problem-analysis`
