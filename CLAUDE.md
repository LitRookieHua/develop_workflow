# develop_workflow 硬规则

## 安全红线

- **git 写操作禁止 Windows 本地执行**：`Y:\01_Src` 是服务器 10.0.12.42（`/comp/user_data/yaohua/01_Src`）的网络映射，本地 git `core.autocrlf=true` 会把工作区文件改写成 CRLF 污染服务器仓库（曾实际污染 3432 个文件）。reset/clean/checkout/commit/push 一律 `ssh yaohua@10.0.12.42` 执行
- 本地 Y: 盘 git 命令仅限只读，且必须加 `-c core.filemode=false`
- **Token 安全**：JIRA/Bitbucket token 从 `C:\Users\YH\.claude\` 下配置读取，绝不内联进任何会被提交的文件；`.imobuilder` 含 CI token，不要暴露其内容
- **commit 格式**（MCU 仓库，全局规则）：`feat(模块名): [工单号] 项目名 + 描述`

## 路径角色

| 路径 | 角色 |
| --- | --- |
| `D:\Workspace\01_Projects\02_Src` | 本地代码，**autosar 代码生成专用**（tools/autosar_gen 生成目标） |
| `10.0.12.42:/comp/user_data/yaohua/01_Src` | 服务器：**编译/代码分析/代码修复** |
| `Y:\01_Src`（服务器映射，同一文件系统） | 服务器代码在 Windows 侧的编辑入口 |

## 先检索再动手

分析问题时先查 `docs/analysis/` 是否有同类问题、`docs/design/` 是否有类似设计方案——有则复用/更新，无则新建沉淀（排障个案写进 analysis/，较大改动方案写进 design/）。

## 目录约定

- `docs/analysis/` 具体问题个案报告；`docs/design/` 设计方案
- `tests/harness/` 测试桩：DiagnosticTester 跑测试用例、LogCollection 采集 MCU 日志分析
- `tools/` 工具**运行时权威源**（10_tools 已冻结不再更新，工具迭代在这里做）

## skill 入口

- 立项（建 Obsidian 笔记 / 建 JIRA Story）→ `story-creation`
- 开发全流程（分支/编译/刷写/验证/PR/收尾）→ `dev-workflow`
