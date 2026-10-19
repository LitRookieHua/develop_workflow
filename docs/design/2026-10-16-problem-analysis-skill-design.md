# problem-analysis skill 设计

> ⚠️ **历史文档**：本文中"Y: 直编"等编码方式已于 2026-10-19 废止（Y: 盘仅许刷写读镜像/读代码/写 .imobuilder，代码写与 git 操作一律 SSH），设计文档模板也已重构——现行规则以 `CLAUDE.md` 与 skill 为准，本文仅作历史记录。

- 日期：2026-10-16
- 状态：已确认
- 背景：有些问题单不一定需要修改代码。先根据问题单分析清楚具体是什么问题，再决定去向：是问题 → 建 story + 走开发工作流；不是问题 → 在问题单上说明原因并走 refuse 关单。

## 1. 定位与入口

- 新建 `.claude/skills/problem-analysis/SKILL.md`，与 story-creation / dev-workflow 并列
- 定位：**开发流程的前置分流环节**——JIRA 问题单进来先分析，是问题 → story-creation + dev-workflow；不是问题 → JIRA 写明理由 + refuse 关单
- 触发词：问题分析、分析问题单、分析下这个 problem、refuse 等，或给出问题单号要求分析
- CLAUDE.md 的 skill 入口表加一行：问题分析（V2 工作区）→ `problem-analysis`

## 2. 与既有体系的关系

| 事项 | 约定 |
| --- | --- |
| 工作区 | **V2 工作区与老工作区并存**：V2（`01_Workspace_TDA4_V2` / `02_Workspace_J6_V2`）专用于问题分析，一般不提交代码；老工作区用于正式开发 |
| mcu 仓库 | TDA4_V2 → `mcu_app_tda4`；J6_V2 按项目归属选 `mcu_app_j6`（存量）/ `mcu_app_j6_v2`（新项目），双仓库规则同 dev-workflow（2026-10-16 评审修正：实测 V2 工作区两仓库并存，原"固定 mcu_app_j6_v2"假设不成立） |
| git/token 硬规则 | 与 dev-workflow 完全一致：git 写操作一律 SSH、本地 Y: 盘只读加 `-c core.filemode=false`、token 从 `C:\Users\YH\.claude\` 读取不内联（skill 内引用规则，不复制全文） |
| 后续流程 | 是问题 → `story-creation`（老工作区立项）→ `dev-workflow`（老工作区开发）；不是问题 → refuse 关单 |

## 3. 流程（6 步）

| 步骤 | 内容 | 说明 |
| --- | --- | --- |
| 1 | 拉问题单详情 | JIRA API（复用 story-creation 速查：PAT Bearer、端点）。description 的复现步骤/测试现象 + 评论 + 附件，**原样保存**作为分析依据，不能只写概括 |
| 2 | 确认项目/分支/工作区 | 从 fixVersions、变体字段、描述推断项目（如 v2xeu）和分支（默认 develop），拿不准用 AskUserQuestion 问；同时定工作区（TDA4_V2 / J6_V2）和 mcu 仓库 |
| 3 | V2 工作区切环境（SSH） | ① `.imobuilder` 的 `build_product` 按项目改（Y: 直改，值从 workspace `config/` 目录**现查**，不维护映射表）；② mcu 仓库 `git reset --hard` + `git clean -xdf` + `git checkout <branch>`；③ `version_did`、`zos_msg` 切到**与 mcu 相同的分支**（develop↔develop；编译前核对依赖仓分支，防接口不匹配） |
| 4 | 编译 MCU 固件 | `imobuilder clean/build`（SSH）。TDA4_V2：`cd 01_Workspace_TDA4_V2 && imobuilder clean/build mcu_app_tda4 -r`；J6_V2：`clean/build mcu_app_j6_v2 -r -x parking_dr uper_app`。只编译**不刷板不复现**，目的是保证分析对象是可编过的基线代码。固件类排障复用 dev-workflow 6.1 |
| 5 | 分析代码 | 按问题单描述定位相关模块/配置，读代码 + 对照复现步骤，得出结论（是问题/不是问题）及依据。遵循 CLAUDE.md「先检索再动手」：先查 `docs/analysis/` 同类问题 |
| 6 | 结论分流 | **先呈现结论等用户确认**，确认后才执行 §5 分流动作 |

## 4. 关键规则

- **V2 工作区只分析不提交**：不建 feature 分支、不 commit/push；`reset --hard` / `clean -xdf` 仅用于还原干净基线，一律 SSH 执行
- 编译相关注意事项（J6 `-x` 参数、clean 末步失败属正常、后台编译不要接 `| grep` 管道、parking_dr/uper_app/MCU21 排障）引用 dev-workflow 第 6 步规则，不复制

## 5. 产出物与分流

分析报告**三处沉淀**：

1. **docs/analysis/**：`YYYY-MM-DD-<问题单号>-<主题>.md`（个案报告，符合「先检索再动手」约定）
2. **Obsidian 笔记**：分析阶段建独立笔记（项目模板、Work Database/），Problem Analysis 章节填分析过程
3. **JIRA 问题单评论**：分析过程要点 + 结论

用户确认结论后分流：

- **是问题** → 分析笔记升级为 story 笔记（frontmatter `type: Story`），走 `story-creation` 建 JIRA Story（关联问题单）→ `dev-workflow` 老工作区开发
- **不是问题** → JIRA 问题单加评论写明「为什么不是问题」（引用报告结论）；`GET /rest/api/2/issue/<key>/transitions` 查可用流转，选 refuse/拒绝类关闭，必填字段按报错补齐（自适应方式，同 dev-workflow 关 Problem 单）；Obsidian 笔记 `status: Done`

## 6. 验证方式

skill 为纯文档，验证 = 人工走查 + 实际试用：

- 走查：SKILL.md 步骤完整覆盖需求功能点（切分支/.imobuilder/同步 version_did、zos_msg、编译、分析、refuse 分流），路径与命令和 dev-workflow 现行规则一致
- 试用：下次实际分析一个问题单时走一遍流程，按反馈迭代
