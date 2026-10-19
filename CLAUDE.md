# develop_workflow 硬规则

## 安全红线

- **Y: 盘仅限三种操作：刷写（读 build 镜像）、读代码、写 `.imobuilder`。其余一律禁止**：
  - **git 操作（读和写都算）一律不允许在 Y: 执行**——全部 `ssh yaohua@10.0.12.42`
  - 代码修改（写源文件）也禁止走 Y:——改走 SSH（D: 暂存后 `scp` 推送，或 SSH heredoc 写服务器路径）
  - 原因 1：`Y:\01_Src` 是服务器 10.0.12.42（`/comp/user_data/yaohua/01_Src`）的网络映射，本地 git `core.autocrlf=true` 会把工作区文件改写成 CRLF 污染服务器仓库（曾实际污染 3432 个文件）
  - 原因 2：Y: 映射不保留文件执行位，经 Y: 写文件会把 mode 644→755 带进 commit（2026-10-19 J02 DoIP 实际发生）
- **Token 安全**：JIRA/Bitbucket token 从 `C:\Users\YH\.claude\` 下配置读取，绝不内联进任何会被提交的文件；`.imobuilder` 含 CI token，不要暴露其内容
- **commit 格式**（MCU 仓库，全局规则）：`feat(模块名): [工单号] 项目名 + 描述`

## 路径角色

| 路径 | 角色 |
| --- | --- |
| `D:\Workspace\01_Projects\02_Src` | 本地代码，**autosar 代码生成专用**（tools/autosar_gen 生成目标） |
| `10.0.12.42:/comp/user_data/yaohua/01_Src` | 服务器：**编译/代码分析/代码修复/git 全部操作** |
| `Y:\01_Src`（服务器映射，同一文件系统） | 仅：刷写读镜像、读代码、写 `.imobuilder` |

## 先检索再动手

分析问题时先查 `docs/analysis/` 是否有同类问题、`docs/design/` 是否有类似设计方案——有则复用/更新，无则新建沉淀（排障个案写进 analysis/，较大改动方案写进 design/）。

## 目录约定

- `docs/analysis/` 具体问题个案报告，**按 [problem-analysis-report-template.md](docs/analysis/problem-analysis-report-template.md) 模板写**；`docs/design/` 设计方案，**按 autosar-general-feature-design-template（MCU/AUTOSAR）或 general-functional-design-template（通用）模板写**
- `tests/harness/` 测试桩，两层结构（详见 `tests/harness/README.md`）：
  - **通用手段**：`diag_test/`（DiagnosticTester 跑用例）、`mcu_log/`（LogCollection / 调试串口采集）——只放与具体问题无关的通用工具
  - **问题专属**：`tests/harness/<模块名>_<harness描述>/`（如 `dcm_sec_relock_1003`、`dcm_did_f190`）——根目录放 python 脚本，`testcases/` 放用例，`logs/` 放运行产物与取证证据；越轻量、解耦越干净越好
- `tools/` 工具**运行时权威源**（10_tools 已冻结不再更新，工具迭代在这里做）

## skill 入口

- 立项（建 Obsidian 笔记 / 建 JIRA Story）→ `story-creation`
- 需求开发（5 阶段：需求解析与架构映射/分支/编码/验证/PR 收尾）→ `feature-development`
- 问题分析（V2 工作区，4 阶段：捕获回放/根因收敛/修复验证/沉淀分流）→ `problem-analysis`
