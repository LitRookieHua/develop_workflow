# 双链路工作流重构实现计划（feature-development + problem-analysis）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 `docs/design/2026-10-16-workflow-two-track-refactor-design.md` 新建 feature-development skill（骨架+3 references）替换并删除 dev-workflow，重写 problem-analysis 为 4 阶段，清理全部交叉引用。

**Architecture:** 纯文档变更，不涉及代码/工具/服务器状态。规则内容从 dev-workflow 原文搬移重组、零删改；references 拆分排障细则与名单映射；交叉引用（CLAUDE.md / story-creation / module_router）同步指向新 skill 名。

**Tech Stack:** Markdown skill 文件（frontmatter + 正文）；验证手段为 grep 内容核对（无测试框架）。

**基准与红线：**

- 权威源：`.claude/skills/dev-workflow/SKILL.md`（迁移前原文，本计划所有"原文"均指它）
- 规则内容零丢失零删改，仅重组结构与标题层级
- 原文中 `develop_workflow`（不含 `_refactor`）的路径字符串按原文保留，不在本次修正
- docs/design/ 历史文档不动；本仓库在 D 盘本地，git 操作无 Y: 盘红线问题
- commit 风格沿用本仓库现有格式（`feat(skill): ...` / `docs(design): ...`，无工单号）

---

### Task 1: 创建 feature-development/references/workspace-setup.md

**Files:**
- Create: `.claude/skills/feature-development/references/workspace-setup.md`

- [ ] **Step 1: 写入文件**

```markdown
# workspace-setup：项目/仓库确认手册（feature-development 阶段 2 前必读）

建分支不可逆，建错仓库/改错 build_product 会污染错误基线。本手册覆盖三件事：.imobuilder 项目映射、J6 双仓库归属判断、切分支时的依赖仓库同步。

## 1. .imobuilder 的 build_product 映射

根据 workspace `config/` 目录查找对应项目名称，修改本地 `.imobuilder` 的 `build_product`（Y: 盘直接改）：

- TDA4（`Y:\01_Src\01_Workspace_TDA4`）：T1LFL1 → `Chery/T1LFL1_D073/develop`；V2XSEA → `Chery/V2XSEA_D058/develop`
- J6（`Y:\01_Src\02_Workspace_J6`）：T51 → `Gac/T51_D088/develop`；N60 → `BAIC/N60_D109/develop`；J02 → `FAWVW/J02_C097/develop`

⚠️ 上表是已知项目的速查，新项目/拿不准时一律 `ls Y:/01_Src/<工作区>/config/` 现查，不凭记忆猜。

## 2. J6 双仓库规则（2026-09-29 起 J6 工作区有两个 mcu 仓库）

| 仓库 | 项目归属 |
| --- | --- |
| `mcu_app_j6` | 存量项目：T51（GAC）、N60（BAIC）、S52 等旧项目 |
| `mcu_app_j6_v2` | 新项目：J02（FAWVW，preset `cpj_fawvw_j02_d310`）、GWM 新项目（c06g/de09g）、HONDA（h3ata3pda）等 |

- 判断方法：看项目的 cpj 目录在哪个仓库下（如 `src/mcu_app_j6_v2/cpj_fawvw/veh_j02/`）；v2 仓库顶层只有 `cpj_fawvw / cpj_gwm / cpj_honda` 三个 cpj 目录
- ⚠️ 两仓库都有 `cpj_gwm` 目录，不能只按 OEM 判断；GWM 项目要按具体车型确认在哪个仓库
- 拿不准时问用户，不要默认选 `mcu_app_j6`

## 3. 切分支时的依赖仓库同步

mcu 产品的构建会组合 workspace 里当前 checkout 的 zos_msg 等依赖仓库代码。切换 mcu 仓库分支后**必须把 zos_msg 等依赖仓库也切到对应分支**（develop↔develop、release↔release），否则出现接口不匹配类编译错误。核对命令与实际案例见 build-troubleshooting.md「编译前核对依赖仓库分支」。
```

- [ ] **Step 2: 验证关键内容在位**

Run: `grep -c "cpj_fawvw\|build_product\|V2XSEA_D058" .claude/skills/feature-development/references/workspace-setup.md`
Expected: `3`（三个关键词各至少 1 次）

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/feature-development/references/workspace-setup.md
git commit -m "feat(skill): add workspace-setup reference for feature-development"
```

---

### Task 2: 创建 feature-development/references/build-troubleshooting.md

**Files:**
- Create: `.claude/skills/feature-development/references/build-troubleshooting.md`

- [ ] **Step 1: 写入文件**（内容 = 原文第 6 步三条 ⚠️ + 6.1 全文，重组为独立手册）

```markdown
# build-troubleshooting：编译排障手册

编译失败先读本手册再动手。按现象对号入座，全部为实际发生过的案例。

## 1. J6 clean 末步 `-clean_binary` 必定失败（属正常，勿重复 clean）

（2026-09-11 实际发生，与 `-x` 无关）imobuilder 把 `--build --preset pf-gcc-clean` 参数拼到仓库的 clean 命令（`rm -rf .../output`）末尾，rm 报 `unrecognized option '--build'`，clean 以 exit 4 结束。但此时 clean 的其余部分（workspace build 树、各依赖包目录、`src/<仓库>/build`）已删完，实际效果等于 clean 完成，只需手动补删残留目录再直接 build：

```bash
ssh yaohua@10.0.12.42 "rm -rf /comp/user_data/yaohua/01_Src/02_Workspace_J6/src/<仓库>/output"
ssh yaohua@10.0.12.42 "cd /comp/user_data/yaohua/01_Src/02_Workspace_J6/ && imobuilder build <mcu_app_j6|mcu_app_j6_v2> -r -x parking_dr uper_app"
```

## 2. 后台编译不要接 `| grep` 管道

会把真实退出码掩盖成 grep 的退出码（2026-09-11 实际发生：clean 致命失败却报 exit 0）。SSH 警告信息留在输出文件里即可。

## 3. 编译前核对依赖仓库分支

（2026-10-15 实际发生）mcu 产品的构建会组合 workspace 里当前 checkout 的 zos_msg 等依赖仓库代码。develop/V460 两条分支交替开发时，切换 mcu 仓库后**必须把 zos_msg 等依赖仓库也切到对应分支**，否则出现接口不匹配类编译错误（如 `ipc_cfg_message.hpp: error: expected class name`，基类 `zos::park_dr::COdoAbstOutput` 找不到——develop mcu 配了 v460 的 zos_msg）。

编译报「找不到类/接口不匹配」先查：

```bash
ssh yaohua@10.0.12.42 "cd <workspace>/src/<依赖仓库> && git branch --show-current"
```

## 4. 固件问题排障（parking_dr / uper_app / MCU21，2026-10-14 用户指示）

编译阶段遇到以下问题按对应方案处理：

- **遇到 parking_dr / uper_app 的问题 → 更新 parking_dr 和 uper_app 固件**（这两个包是远端预编译产物，本地缓存的旧固件会导致链接结果异常，如 final bin 超大小限制）：
  1. 清空 download 目录内容：TDA4 为 workspace 下 `output/armv7-r-generic-tda4-r5f-llvm/release/download`；J6 为 `output/armv8-r-generic-gcc-r52/release/download`
  2. `imobuilder configure --ci_service_token 'Bearer <jwt>'`（⚠️ Bearer 和 token 之间必须有空格，拼成 `BearereyJ...` 或裸 JWT 都会 401；jwt 取自 `.imobuilder` 里的 CI token，不要暴露）
  3. `imobuilder remote_build parking_dr` 和 `imobuilder remote_build uper_app`，各返回一个 build_id
  4. 等构建完成（约 10 分钟）后 `imobuilder download target-<build_id> --build_id <build_id>` 下载两个固件
- **遇到 MCU21 固件的问题 → 重新编译 MCU21 固件**（uss_app_tda4 仓库，⚠️ 先确认该仓库在正确分支，残留旧分支会 API 不匹配编不过）：

```bash
imobuilder clean uss_app_tda4 -r -x parking_dr uper_app
imobuilder build uss_app_tda4 -r -x parking_dr uper_app
```

修完后重新 build mcu 仓库。2026-10-14 实际案例：v2xeu develop 基线 final bin 超 3456KB 限制，根因是 parking_dr/uper_app 为 9月4 旧固件 + uss_app_tda4 在错误分支，按上述流程刷新后 3329040 字节通过。
```

- [ ] **Step 2: 验证关键内容在位**

Run: `grep -c "unrecognized option\|ipc_cfg_message.hpp\|3329040" .claude/skills/feature-development/references/build-troubleshooting.md`
Expected: `3`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/feature-development/references/build-troubleshooting.md
git commit -m "feat(skill): add build-troubleshooting reference for feature-development"
```

---

### Task 3: 创建 feature-development/references/pr-merge.md

**Files:**
- Create: `.claude/skills/feature-development/references/pr-merge.md`

- [ ] **Step 1: 写入文件**（内容 = 原文 10.1 reviewers 细节 + 10.2 全文 + 10.3 全文）

````markdown
# pr-merge：reviewers 名单与 PR 监控手册（创建 PR 前必读）

reviewers 漏加 PR 就废（补加要走 PR 编辑接口且必须带 version）。本手册覆盖：reviewers 名单、飞书通知对象与 open_id、PR 状态监控循环、CI 失败处置。

## 1. reviewers 名单（按仓库）

PR reviewers 必加 2 人：韩乐乐 `Lucas.Han`、陶晓荣 `Xiaorong.Tao`（Bitbucket 用户名）。在此基础上：

- **mcu_app_tda4 / mcu_app_j6 / version_did 仓库额外加 1 人（2026-10-14 起，共 3 人）**：冯锡斌 `Xibin.Feng`。飞书通知也发他（mcu_app_j6_v2 维持 4 人名单不变）
- **mcu_app_j6_v2 仓库额外加 2 人（2026-10-08 起，共 4 人）**：戴杰 `jie.dai`、王涛 `Samuel.Wang`。飞书通知也发这 4 人
- **zos_msg 仓库的 reviewers**：曾健荣 `jianrong.zeng`、李翔 `xiang.li`（2026-09-30 D1CYC-1670 确认；⚠️ Bitbucket `/rest/api/1.0/users?search=` 接口对中文/拼音查询无效，找不到用户名时从该仓库最近 PR 的 reviewers 列表里查）

**创建时漏加 reviewers 的补救**：用 PR 编辑接口补：`PUT .../pull-requests/<id>`，请求体带 `title/description/version(GET到的)/fromRef/toRef/reviewers`（version 必须带，否则 400；participants 接口会 403 不可用）。

## 2. 飞书通知 owner（PR 创建后）

用 `lark-cli im +messages-send`（注意：**不要用 `lark-cli api POST /open-apis/im/v1/messages`，会 404**）：

```bash
lark-cli im +messages-send --as user --user-id <ou_xxx> --text "<具体功能>
<PR链接> 帮忙PR下"
```

- 具体功能 = 本次需求的功能描述（同笔记/来源需求，如 `N60 DTC表V4.0更新`）
- 身份必须 `--as user`（应用身份会显示为 bot）
- open_id 查询：`lark-cli contact +search-user --queries "名字1,名字2" --as user`

按仓库通知对应 owner：

| 仓库 | 通知对象 | 消息格式 |
| --- | --- | --- |
| mcu_app_tda4 / mcu_app_j6 / version_did | 韩乐乐、陶晓荣、冯锡斌（2026-10-14 起三人都通知） | `具体功能 + PR链接 + 帮忙PR下` |
| mcu_app_j6_v2 | 韩乐乐、陶晓荣、戴杰、王涛（2026-10-08 起 4 人都通知） | `具体功能 + PR链接 + 帮忙PR下` |
| zos_msg | 曾健荣、李翔 | `具体功能 + PR链接 + 帮忙PR下` |
| zos_msg（额外） | 张飞（2026-10-14 起接替秦晋文） | `具体功能 + PR链接 + 帮忙强行合入` |

owner open_id（已解析，可直接用）：

- 韩乐乐 `ou_a438e91570fe6a9ec9eb4b820e2c1cbe`、陶晓荣 `ou_100ffeadd913f05918c99ebc7f5a12b9`、冯锡斌 `ou_7da5be388d18719b695b746f4e90fbbd`（mcu_app_tda4 / mcu_app_j6 / version_did）
- 戴杰 `ou_9d0c6482bd2b855cbde67c6e70d8f38e`、王涛 `ou_897cc603826a1a002fd40dc9309ed17f`（mcu_app_j6_v2 专用）
- 曾健荣 `ou_225dc258fbed3172ff4a8c85ba7aebe9`、李翔 `ou_785c07e443037ff2aa9e30317bf9060b`、张飞 `ou_de2437f578fd662e8aae533e78395265`（负责强行合入通知；2026-09-29 曾改为秦晋文，2026-10-14 起改回张飞）

## 3. PR 状态监控（每 10 分钟）

PR 创建 + 通知后，用 CronCreate 建一个每 10 分钟的定时任务（session-only，cron 用 `7-57/10 * * * *` 避开整点分钟），监控本 story 所有未合并 PR：

1. 查状态：`GET https://bitbucket.imotion.ai:7990/rest/api/1.0/projects/<PROJ>/repos/<repo>/pull-requests/<id>`（token 同 PR 创建），state == `MERGED` 即完成
2. **审批通过即自动 merge**：state == `OPEN` 且任意一位人工 reviewer（排除 bot_ci 等 bot 账号）`approved == true` → 立即 `POST .../pull-requests/<id>/merge?version=<GET到的version>` 自动合入（2026-09-21 用户确认：一人通过即可 merge，无需两位 reviewer 都通过）。merge 失败打印错误继续下轮监控
   - **所有仓库（含 mcu_app_tda4，2026-10-14 实际发生）：imoci（bot_ci）CI 审批是强制要求**：人工 reviewer 全部 approved，merge 仍会被 veto（`Not all required reviewers have approved yet | imoci must review and approve`；CI 失败时还会加 `Some reviewers have requested changes: imoci`），必须等 CI 跑完 bot_ci 自动批后再 merge（CI 审批可能耗时 1 小时以上，期间监控轮次只需简短带过继续等）
   - **CI 失败（imoci NEEDS_WORK）的处置（2026-10-14 经验）**：
     - 查失败任务：`GET https://ci.imotion.ai/api/v1/build-tasks/<task_id>`（认证用 .imobuilder 里的 CI token，`Authorization: Bearer <jwt>`；task_id 从 Bitbucket build-status 的 url 取，如 `ci.imotion.ai/task/1349908/detail`），`data.detail.progress.build.<repo>.snapshots[0].commit_hash` 可看实际构建输入
     - **并发 flake 识别**：同一 agent（agent_id 相同）时间窗口重叠的多个构建、同输入一成一败、矩阵 fail-fast 连带 CANCELLED 兄弟任务 → 是 flake 不是代码问题，重触发即可
     - **重触发方法**：往 feature 分支推空 commit（`git commit --allow-empty -m 'chore(模块): [工单号] retrigger CI' && git push`），新 head 会重新触发 PR 的 OCR + CI
     - **mcu/zos 成对 PR 的依赖顺序**：PR 的 CI 构建用「目标分支的 zos_msg + mcu PR 补丁」组合（zos_msg 构建时按 EVM_CFG_FILE_NAME 前缀从自己仓库的 Gen_evm_dem_Script 找 xlsx 生成代码）。EVM 表导入类需求 mcu 生成的代码依赖 zos 仓库的新表 → **必须先合 zos PR，再重触发 mcu PR**，否则 mcu CI 会因新旧表不匹配失败
     - ⚠️ 推空 commit 前确认当前分支：checkout 被未跟踪文件挡住而失败时，后续 commit 会落在原分支（2026-10-14 实际推错过分支）。先看 checkout 输出再 commit；未跟踪的 `ti_j721s2_mcu_mcal/` 目录挡 checkout 时直接 `rm -rf` 掉（构建产物）
   - **zos_msg develop 分支仅允许 fast-forward merge**：develop 有新提交时 merge 会被 veto（Control Freak 提示 must rebase），需 SSH 执行 `git fetch origin && git checkout <feature分支> && git rebase origin/develop && git push --force-with-lease`，rebase 后 CI 会重新触发、bot_ci 审批重置，需重新等待
   - merge 409 报 `PullRequestOutOfDateException` 时用响应体里的 `currentVersion` 重试；veto 详细原因在错误响应体的 `errors[].vetoes[].summaryMessage`
3. **PR MERGED** → 飞书通知本人（姚华 `ou_1ec2bf00af2d4b80a88cc51ed6cdc6ee`，`lark-cli im +messages-send --as user`），该 PR 移出监控列表；监控列表为空（全部合并）→ 再通知本人「全部 PR 已合并」，CronDelete 停止监控，并**自动执行收尾（关单+通知报告人，无需用户确认）**
4. **PR DECLINED** → 同样飞书通知本人，但**继续监控**其余 PR（不删任务，等用户处理）
5. **久未审批催审**（可选，用户要求时启用）：用状态文件计数，第 N 次（如 18 次）检测仍无审批 → 给韩乐乐发加急催审——先 `lark-cli im +messages-send --as bot --user-id <韩乐乐open_id> --text "..."`（加急要求 bot 是消息发送者），再 `lark-cli im messages urgent_app --message-id <id> --user-id-type open_id --data '{"user_id_list":["<韩乐乐open_id>"]}' --as bot`；bot 发送失败则降级 `--as user` 普通消息。加急只发一次（urgent_sent 标志）
6. 无变化则简短带过

**飞书通知格式（尽量详细）：第一行 `<具体功能>`，第二行 `<PR链接> + <状态>`**

- MERGED：`<具体功能>` 换行 `<PR链接> 已合并`
- DECLINED：`<具体功能>` 换行 `<PR链接> 被拒绝，原因：<原因>` — 原因从 PR 的 activities/comments 查：`GET .../pull-requests/<id>/activities`（token 同上），找最近的评审意见/评论；查不到具体原因就写「未见评审意见」

注意：定时任务仅在会话空闲时触发、会话关闭即停止（需跨会话监控时建 durable 任务并告知用户）；recurring 任务 7 天后自动过期，建任务时要向用户说明。
````

- [ ] **Step 2: 验证关键内容在位**

Run: `grep -c "ou_a438e91570fe6a9ec9eb4b820e2c1cbe\|PullRequestOutOfDateException\|urgent_app" .claude/skills/feature-development/references/pr-merge.md`
Expected: `3`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/feature-development/references/pr-merge.md
git commit -m "feat(skill): add pr-merge reference for feature-development"
```

---

### Task 4: 创建 feature-development/SKILL.md（5 阶段骨架）

**Files:**
- Create: `.claude/skills/feature-development/SKILL.md`

- [ ] **Step 1: 写入文件**（frontmatter 触发词继承 dev-workflow 原文；正文 = 5 阶段骨架 + 日常命令 + 硬规则，排障细节指向 references）

````markdown
---
name: feature-development
description: MCU 需求开发全流程工作流（5 阶段：需求解析与架构映射 → 任务准备与环境隔离 → 核心配置与编码 → SIL 与台架隔离验证 → 审查与合流；Obsidian 笔记 → JIRA story → 设计方案 → 建分支 → 改代码 → 编译 → 刷写 → 验证 → 上传 → Bitbucket PR → 关闭 JIRA/笔记 → 通知需求报告人）。Use this skill whenever the user mentions 开发工作流、走工作流、做需求、新需求、story 开发、开始开发, references a requirement or JIRA ticket (如 D3ACYI-xxxx) to develop in mcu_app_tda4 / mcu_app_j6 / mcu_app_j6_v2, or asks for any part of the flow — 切分支、编译代码、上传代码、提交 PR、总结笔记、关闭工单/JIRA — even if they only mention a single step.
---

# MCU 需求开发工作流（Feature Development，5 阶段）

5 阶段固定流程，适用于 TDA4 / J6 工作区的 mcu_app 需求开发。其中**阶段 4 的手动验证是用户手动操作**，执行到该处停下等用户确认。收尾（关 JIRA/笔记、通知报告人）在所有 PR 合并后**自动执行，无需用户确认**（见阶段 5）。

开始前用 TaskCreate 为本次需求创建任务列表（**每阶段一个任务，共 5 个**），逐步勾选，随时可从任务列表恢复进度。

## 路径角色

| 路径 | 角色 |
| --- | --- |
| `D:\Workspace\01_Projects\02_Src` | 本地代码，**autosar 代码生成专用**（tools/autosar_gen 生成目标） |
| `10.0.12.42:/comp/user_data/yaohua/01_Src` | 服务器，**编译/代码分析/代码修复** |
| `Y:\01_Src`（服务器映射，同一文件系统） | 服务器代码在 Windows 侧的编辑入口（改代码走 Y: 直编） |

---

## 开始前确认

从用户消息或笔记中确认以下信息，缺了就问：

1. **工作区**：TDA4（`Y:\01_Src\01_Workspace_TDA4`）还是 J6（`Y:\01_Src\02_Workspace_J6`）
2. **来源需求**：JIRA 单号/链接，或需求描述
3. **项目/变体**：如 V2XSEA、T1LFL1、T51、N60、J02
4. **待修改分支**：仅 develop，还是 develop + release（如 `release/Chery/V2XEU_D065/V460`）
5. **修改仓库**：mcu_app / zos_msg / version_did 中哪些仓库需要改动。J6 工作区的 mcu 仓库有 `mcu_app_j6` 和 `mcu_app_j6_v2` 两个，须按项目归属选定（判断规则见 [references/workspace-setup.md](references/workspace-setup.md)）

## 流程总览

| 阶段 | 内容 | 执行者 |
| --- | --- | --- |
| 1 | 需求解析与架构映射：story-creation 立项 + docs/design 技术方案 | Claude |
| 2 | 任务准备与环境隔离：确认项目/分支/仓库，SSH 切 develop 建分支 | Claude（SSH） |
| 3 | 核心配置与编码：Y: 直编、autosar 生成、SSH 编译 | Claude（SSH） |
| 4 | SIL 与台架隔离验证：刷写（仅 J6）+ 手动验证 | 刷写 Claude / 验证**用户手动** |
| 5 | 审查与合流：commit/push、PR、监控合并、总结笔记、关单、通知 | Claude |

---

## 阶段 1：需求解析与架构映射

1. **立项**：走 `story-creation` skill——创建 Obsidian 笔记（Work Database/ + 项目模板）+ 创建 JIRA Story 并互相关联，细则全在该 skill
2. **技术方案（所有需求必写）**：`docs/design/YYYY-MM-DD-<工单号>-<主题>-design.md`，内容含：
   - 需求摘要与验收标准（从 JIRA 需求单 description 提取，原样整理）
   - **BSW 模块影响分析**：明确影响的具体模块与参数（如 Dcm 的 DID/RID、Dem 的 Debouncing 策略、PduR 路由表、Nvm 块）
   - 修改点清单（文件/模块级别）
   - 验证方案（用什么手段验证）
3. Obsidian 笔记 **Design 章节链接**该设计文档

> 后续迭代：AI/脚本自动从 JIRA 提取验收标准。

## 阶段 2：任务准备与环境隔离

⚠️ **关卡：建分支前必读 [references/workspace-setup.md](references/workspace-setup.md)**（.imobuilder 项目映射、J6 双仓库归属判断、依赖仓库同步）。

1. **改 .imobuilder**：按 workspace `config/` 目录现查项目的 preset/build_product，改 `.imobuilder` 的 `build_product`（Y: 直改；速查表见 workspace-setup.md）
2. **建分支**（对本阶段确认的修改仓库逐一执行）。分支命名：`feature/<jira工单号>-<标题小写连字符>`（如 `feature/D3ACYI-1271-v2x-series-send-mcu-system-info`）

**TDA4**（仓库在 `/comp/user_data/yaohua/01_Src/01_Workspace_TDA4/src/` 下，如 `mcu_app_tda4`、`zos_msg`、`version_did`）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/01_Workspace_TDA4/src/<仓库>/
git reset --hard
git clean -xdf
git checkout develop
git pull
git fetch origin
git checkout -b feature/<jira工单号>-<标题> origin/develop
git push -u origin feature/<jira工单号>-<标题>
```

**J6**（仓库在 `/comp/user_data/yaohua/01_Src/02_Workspace_J6/src/` 下，如 `mcu_app_j6`、`mcu_app_j6_v2`、`zos_msg`、`version_did`；mcu 仓库按 workspace-setup.md 双仓库规则选定）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/02_Workspace_J6/src/<仓库>
# 后续命令同上
```

- 执行前如有未提交改动：先 `git -c core.filemode=false diff -- <files> > /tmp/backup.patch` 备份，切完后 `git apply` 恢复
- SSH 密钥认证已配好

**多分支规则**：若 develop 和 v460 等两个分支都需要修改，develop 分支先完整执行阶段 2-5，v460 分支再执行一遍；第二个分支的代码修改可直接用 cherry-pick 移植 develop 分支的 commit（见阶段 3）。

**release 分支合入的分支创建**：需求需同时合入 release 分支时（如 `release/Chery/V2XEU_D065/V460`），develop 分支的阶段 2-5 完成后，从 **release 分支**基底创建独立 feature 分支：

```bash
git fetch origin
git checkout -b feature/<jira工单号>-<标题>-<release简易分支名> origin/<release分支名>
git push -u origin feature/<jira工单号>-<标题>-<release简易分支名>
```

- release 简易分支名 = release 分支名最后一节小写，如 `release/Chery/V2XEU_D065/V460` → `v460`（例：`feature/D3ACYI-1181-lateral-update-910-v460`）
- 该分支的代码修改可直接 cherry-pick develop 分支的 commit（见阶段 3），PR 目标为对应 release 分支
- 注意：develop 分支上的 mcal 符号链接等本地改动可能挡 checkout，按需先 `git checkout -- <文件>` 丢弃

## 阶段 3：核心配置与编码

在 Y: 盘直接编辑（与服务器同一文件系统）。

- develop 分支：直接编辑代码
- release 分支（第二个分支）：可直接 cherry-pick develop 分支的 commit（SSH 执行 `git cherry-pick <commit-hash>`），冲突时手工解决（release 与 develop 代码有差异）

**autosar 生成代码场景**（Dcm/Dem/Nvm 配置类需求）：使用 `tools/autosar_gen/` 下工具生成代码：

- 生成目标为 D: 本地路径（`D:\Workspace\01_Projects\02_Src`，autosar 专用）
- 产物需进入服务器仓库时，从 D: 拷贝同步到 Y: 对应仓库路径，再走阶段 5 SSH 提交

**编译**（SSH）：

**TDA4**：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/01_Workspace_TDA4/
imobuilder clean mcu_app_tda4 -r
imobuilder build mcu_app_tda4 -r
```

**J6**（`-x parking_dr uper_app` 必须带，这两个包的远端仓库 `ip/parking_dr`、`ip/uper_app` 已不存在，不带会 clone 失败；`<mcu_app_j6 或 mcu_app_j6_v2>` 按阶段 2 选定的仓库，v2 同样带 `-x`，2026-09-29 用户确认）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/02_Workspace_J6/
imobuilder clean <mcu_app_j6|mcu_app_j6_v2> -r -x parking_dr uper_app
imobuilder build <mcu_app_j6|mcu_app_j6_v2> -r -x parking_dr uper_app
```

编译耗时较长（可后台运行）。**编译失败 → 读 [references/build-troubleshooting.md](references/build-troubleshooting.md)**（J6 clean 末步失败属正常、勿接 `| grep` 管道、parking_dr/uper_app/MCU21 固件排障、依赖仓库分支核对）。失败修复后重试，通过后进入阶段 4。

> 后续迭代：零警告（Zero-warning）与 MISRA 静态规范本地强制检查。

## 阶段 4：SIL 与台架隔离验证

**刷写固件（仅 J6，Windows 本地执行）**：用 `tools/ProgramBoard/` 一键刷写工具（`ProgramBoard_j6b.py`）把阶段 3 编译产物刷到板子。**在本机 Windows 执行**（串口/电源 COM 口都在本机，不走 SSH）：

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/ProgramBoard
python ProgramBoard_j6b.py --port <A核串口> --psu-com COM44 --config configs/<项目>.json --img-dir Y:/01_Src/02_Workspace_J6/src/<仓库>/build/<preset>/rpu_arm_gcc
```

示例：

- N60（旧仓库）：`--config configs/n60_mcu.json --img-dir Y:/01_Src/02_Workspace_J6/src/mcu_app_j6/build/cpj_baic_n60_d310/rpu_arm_gcc`
- J02（v2 仓库）：`--config configs/j02_mcu.json --img-dir Y:/01_Src/02_Workspace_J6/src/mcu_app_j6_v2/build/cpj_fawvw_j02_d310/rpu_arm_gcc`（镜像文件 `int_rpu_arm8r5_arm_j02_gnu.img`）

- ⚠️ **`--img-dir` 必须显式传**：工具已从 `Y:\01_Src\tools\flash`（已删除）迁至 D 盘，脚本内置默认镜像路径指向 D 盘本地副本（无 build 产物），不传会找不到镜像；`--img-dir` 一律指向 Y: 盘上阶段 3 的服务器编译输出
- A 核串口按 `USB-Enhanced-SERIAL-C` 描述识别（COM 号会因 USB 重枚举漂移，如 COM30/COM41，用 list_ports 查当前号），COM44 = KA3005P 电源；电源未接时省略 `--psu-com`（失败时提示人工断电）
- 全自动流程（约 35 秒/次）：断电冷启动 → 20ms 周期发空格打断 uboot → `fastboot udp` → `flash MCU_a`/`MCU_b` → `fastboot reboot`；任一步失败自动断电重来（默认重试 3 次），退出码 0 成功 / 1 失败
- 前提：板子 A 核串口 + 网线（与 PC 同网段）已接，供电走 KA3005P 输出（12V）
- 失败排查看 `logs/flash_*.log`（`[SER]` 前缀为串口原始数据）；换新板/新 uboot 版本先跑 `--dry-run` 校准，参数与板子特性详见目录下 `README.md`
- TDA4 工作区暂无自动刷写工具，跳过刷写直接进入手动验证

**手动验证 —— 停下等待**：用户手动验证（台架/功能验证）。验证通过后用户会说继续。

诊断功能验证用 `tools/DiagnosticTester`：自己写 testcase（`testcase/<项目>/<用例>/<用例>.yaml`，写法见该目录 README.md），然后跑脚本验证：

```bash
python DiagnosticTester.py run testcase/<项目>/<用例>/<用例>.yaml --config configs/<项目>/<配置>.yaml
```

测试桩（转发器）见 `tests/harness/diag_test/`。

> 后续迭代：x86 SIL 无硬件隔离验证（黑白盒）、LDC/OOP 配置一致性校验器接入。

## 阶段 5：审查与合流

**提交 commit + push（SSH）**：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/<工作区>/src/<仓库>
git add <files>
git commit -m "feat(模块名): [工单号] 项目名 + 描述"
git push
```

commit 格式（全局规则，所有仓库）：`feat(模块名): [工单号] 项目名 + 描述`，如 `feat(dia_cfg): [D3ACYI-1271] V2x add F187 part number to MCU system info IPC`。注意：给参考示例时只套用格式，内容如实描述本次改动。

push 后记下 commit hash（总结笔记要用）。

**创建 Bitbucket PR + 飞书通知 owner**：

⚠️ **关卡：创建 PR 前必读 [references/pr-merge.md](references/pr-merge.md)**（reviewers 名单、飞书通知对象与 open_id、PR 监控循环细则）。

用 Bitbucket Server REST API 1.0（也可用 `/bb` 技能）：

- 认证：Bearer token（`BBDC-` 前缀），在 `C:\Users\YH\.claude\mcp.json` 的 `bitbucket-mcu_app_tda4.env.BITBUCKET_API_TOKEN`
- `POST https://bitbucket.imotion.ai:7990/rest/api/1.0/projects/MCU/repos/<repo>/pull-requests`
- 仓库：TDA4 → `mcu_app_tda4`；J6 → `mcu_app_j6` 或 `mcu_app_j6_v2`（按阶段 2 选定的仓库）
- 请求体：`{"title": "<commit 标题>", "description": "<commit 完整内容>", "fromRef": {"id": "refs/heads/<feature分支>"}, "toRef": {"id": "refs/heads/develop"}, "reviewers": [...按 pr-merge.md 名单...]}`
- release 分支的 feature 分支，PR 的 `toRef` 为对应 release 分支（如 `refs/heads/release/Chery/V2XEU_D065/V460`）
- **PR 标题 = commit 标题，PR 内容 = commit 内容**
- PR 创建后按 pr-merge.md 发飞书通知，并建每 10 分钟的 PR 监控（审批通过自动 merge、CI 失败处置、合并/拒绝通知本人）

**总结 Obsidian 笔记**：

- `status: In Review`
- Subtasks 勾选完成项
- Notes 新增本次日期记录：commit hash、PR 链接、待办（PR 合并后转已解决）
- Related Links 加 PR 链接

**关闭 JIRA 单和笔记（PR 合并后自动执行，无需用户确认）**。PR 监控确认全部 PR 已合并后执行；PR 尚未全部合并时不要做这步：

1. **确认合并**：`GET .../pull-requests/<id>`，state == `MERGED`
2. **JIRA 转已解决**：「开放」状态没有直接的解决流转，需两步 POST `https://jira.imotion.ai:7070/rest/api/2/issue/<key>/transitions`（认证见 story-creation「JIRA API 速查」，⚠️ 必须 PAT Bearer 方式，Basic auth 会 401）：
   - `{"transition":{"id":"4"}}` → 开始进行（开放 → 处理中）
   - `{"transition":{"id":"5"}}` → 解决问题（处理中 → 已解决，resolution 自动为完成）
3. **关闭关联需求单/问题单**（2026-09-21 用户要求，漏关即收尾未完成）：除 story 外，笔记 frontmatter `parent_problems` / `parent_requirements` 及来源需求中列出的关联单都要一并关闭：
   - **Problem 单**（issuetype=Problem）三步流转，各步带必填字段：
     - `{"transition":{"id":"121"}}` → 开始分析（开放 → In Analysis）
     - `{"transition":{"id":"31"}}` → 分析完成，**必填** `customfield_12017`（英文根因描述）+ `duedate` + `fixVersions`（如 `[{"name":"T320"}]`，取 story 的修复版本）
     - `{"transition":{"id":"41"}}` → 已实现（终态），**必填** `customfield_12305`（Link to Bugfix，easy-links 格式 `[{"key":"<story单号>"}]`，传字符串数组会报 expected Object）
   - **需求单（Requirement 等）**：查看其可用 transitions（`GET .../issue/<key>/transitions`）选合适的关闭流转，有必填字段按报错补齐
4. **关闭笔记**：`status: Done`、填写 `completed` 日期、勾选关闭 Subtask、Notes 补关闭记录（PR 合并日期）

**飞书通知需求报告人（PR 合并后自动执行）**：查看**来源需求单**（parent requirement，如 `IDC310BAICREQ-4639`）的报告人，飞书通知其需求已完成：

1. **查报告人**（认证同上）：

```bash
curl -s -k -H "Authorization: Bearer <JIRA_TOKEN>" "https://jira.imotion.ai:7070/rest/api/2/issue/<来源需求单号>?fields=reporter"
```

取 `fields.reporter.displayName`（如 `Zhang San/张三`）。

2. **查 open_id**：`lark-cli contact +search-user --queries "<姓名>" --as user`
3. **发消息**（`--as user`，命令格式见 pr-merge.md §2）：

消息格式：`<具体功能>已完成，并上传<分支列表>分支`

- 具体功能 = 来源需求/笔记的功能描述（如 `N60 DTC表V4.0更新`）
- 分支列表 = 本流程全部 PR 的目标分支：`develop`，有 release 合入时一并列出（如 `develop、release/Chery/V2XEU_D065/V460`）
- 示例：`N60 DTC表V4.0更新已完成，并上传develop分支`

---

## ⚠️ 关键规则：git 写操作禁止在 Windows 本地执行

**Y:\01_Src 是服务器 10.0.12.42 磁盘 `/comp/user_data/yaohua/` 的网络映射（同一文件系统）**，但 Windows 本地 git 配置了 `core.autocrlf=true`，本地执行 reset/checkout 会把工作区文件改写成 CRLF，污染服务器端仓库（2026-09-10 实际发生：3432 个文件被污染，需服务器端 reset --hard 修复）。

因此：

- 所有 git 写操作（reset / clean / checkout / commit / push）一律通过 `ssh yaohua@10.0.12.42` 执行
- 本地 Y: 盘的 git 命令仅用于只读查看，且必须加 `-c core.filemode=false`（否则 mode 位噪音淹没输出）

## Token 与安全

- JIRA token：`C:\Users\YH\.claude\.mcp.json`（atlassian 配置）
- Bitbucket token：`C:\Users\YH\.claude\mcp.json`（bitbucket-mcu_app_tda4 配置，`BBDC-` 前缀）
- 从文件读取使用，**绝不内联到任何会被提交的文件里**
- `.imobuilder` 含 CI bearer token，不要暴露其内容
````

- [ ] **Step 2: 验证关键结构在位**

Run: `grep -c "^## 阶段" .claude/skills/feature-development/SKILL.md && grep -c "references/workspace-setup.md\|references/build-troubleshooting.md\|references/pr-merge.md" .claude/skills/feature-development/SKILL.md`
Expected: `5` 和 `≥3`（5 个阶段标题；3 个 references 均被引用）

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/feature-development/SKILL.md
git commit -m "feat(skill): add feature-development skill (5-phase, replaces dev-workflow)"
```

---

### Task 5: 删除 dev-workflow skill 目录

**Files:**
- Delete: `.claude/skills/dev-workflow/`（整个目录，仅含 SKILL.md）

- [ ] **Step 1: 删除前核对零丢失**

Run: `grep -c "第 1[23] 步\|4\.1\|5\.1\|6\.1\|10\.1\|10\.2\|10\.3" .claude/skills/dev-workflow/SKILL.md`
Expected: 大于 0（原文在位，供 Task 8 逐项核对）

再人工核对：原文 step3 的 .imobuilder 映射/J6 双仓库表已进 workspace-setup.md；step6 ⚠️×3 + 6.1 已进 build-troubleshooting.md；step10/12/13 细则已进 SKILL.md 或 pr-merge.md。

- [ ] **Step 2: 删除**

```bash
git rm -r .claude/skills/dev-workflow
```

- [ ] **Step 3: Commit**

```bash
git commit -m "refactor(skill): remove dev-workflow superseded by feature-development"
```

---

### Task 6: 重写 problem-analysis/SKILL.md 为 4 阶段

**Files:**
- Modify: `.claude/skills/problem-analysis/SKILL.md`（整文件重写）

- [ ] **Step 1: 写入文件**（覆盖全文）

````markdown
---
name: problem-analysis
description: JIRA 问题单分析与修复工作流（4 阶段：现场捕获与数据回放 → 知识召回与根因收敛 → 方案验证与精准修复 → 经验沉淀与流程防腐）。V2 工作区分析 + 验证性修复（不建分支不提交代码）；是问题 → 转 feature-development 正式开发，不是问题 → JIRA 写明理由 + refuse 关单。当用户提到 问题分析、分析问题单、分析下这个 problem、refuse，或给出问题单号（如 D3ACYI-xxxx）要求先分析时使用，即使用户只提到其中一个环节。注意：本 skill 在 V2 工作区（01_Workspace_TDA4_V2 / 02_Workspace_J6_V2）分析与验证，只验证不提交；正式开发走 feature-development（老工作区）。
---

# JIRA 问题单分析与修复工作流（4 阶段）

有些问题单不一定需要修改代码。本流程先根据问题单分析清楚具体是什么问题，再决定去向：**是问题 → V2 验证性修复 + 转 feature-development 正式开发；不是问题 → 在问题单上说明原因并走 refuse 关单**。

4 阶段流程。**阶段 2 末的结论必须先呈现给用户确认**，确认后才进入阶段 3（修复）或阶段 4（直接 refuse）。阶段 4 的关单/通知动作同样先经用户确认分流方向。

开始前用 TaskCreate 为本次分析创建任务列表（**每阶段一个任务，共 4 个**），逐步勾选，随时可从任务列表恢复进度。

## 路径角色（V2 工作区，与老工作区并存）

| 路径 | 角色 |
| --- | --- |
| `10.0.12.42:/comp/user_data/yaohua/01_Src/01_Workspace_TDA4_V2` | TDA4 V2 工作区（问题分析专用） |
| `10.0.12.42:/comp/user_data/yaohua/01_Src/02_Workspace_J6_V2` | J6 V2 工作区（问题分析专用） |
| `Y:\01_Src\01_Workspace_TDA4_V2` / `Y:\01_Src\02_Workspace_J6_V2` | 上述工作区在 Windows 侧的编辑入口（改 .imobuilder、改代码走 Y: 直改） |

- V2 工作区与老工作区（01_Workspace_TDA4 / 02_Workspace_J6）**并存**：V2 做分析 + 验证性修复，**不建分支、不 commit、不 push**（改动留在 V2 工作区，git reset 可还原）；正式开发在老工作区走 feature-development
- mcu 仓库：TDA4_V2 → `mcu_app_tda4`；J6_V2 按项目归属选 `mcu_app_j6`（存量项目：T51、N60、S52 等）或 `mcu_app_j6_v2`（新项目：J02、GWM 新项目、HONDA 等），判断规则见 feature-development 的 [references/workspace-setup.md](../feature-development/references/workspace-setup.md)（J6 双仓库规则）：看项目的 cpj 目录在哪个仓库下，⚠️ 两仓库都有 `cpj_gwm`，不能只按 OEM 判断，拿不准时问用户

## 阶段 1：现场捕获与数据回放

**拉问题单详情**——用 JIRA REST API（认证与端点见 story-creation skill 的「JIRA API 速查」，PAT Bearer）：

- `GET https://jira.imotion.ai:7070/rest/api/2/issue/<问题单号>?fields=summary,description,status,fixVersions,components,assignee,reporter,issuelinks,attachment,customfield_15000`
- description 里的**复现步骤与测试现象原样保存**——这是后续分析和结论的依据，不能只写概括；description 为空时查评论（`GET .../issue/<key>/comment`）
- 有附件则下载留存（分析时看）
- 记录 fixVersions、变体字段（customfield_15000）、components——阶段 2 推断项目用

**现象固定**：整理异常发生时的软硬件状态记录（报错上下文、堆栈/日志、发生条件），与复现步骤一起作为分析输入。

> 后续迭代：PSA 报文回放工具、MCAP 日志解码器——实车/台架通信时序（如 CanTp 多帧传输失败、流控制超时）脱机复现。当前手段为问题单 description / 附件 / 日志。

## 阶段 2：知识召回与根因收敛

**（1）知识召回——看代码之前先做**：

- 检索 `docs/analysis/` 历史个案报告（关键词：问题单号、模块名、现象关键词）
- 检索 `docs/design/` 相关设计方案
- 检索 Obsidian `ClaudeCodeNote/Work Database/` 笔记（frontmatter jira_key、正文关键词）
- 命中同类问题 → 直接复用/更新历史结论，加速收敛；无命中 → 继续

**（2）确认项目/分支/工作区**：

1. **项目**：从 fixVersions、变体字段、description 推断（如 fixVersion 提到 v2xeu 相关版本、描述里写车型）；拿不准用 AskUserQuestion 问
2. **分支**：默认 develop；问题单描述/评论提到特定版本（如 V460 基线）时用对应 release 分支，拿不准就问
3. **工作区**：按项目定——TDA4 项目 → `01_Workspace_TDA4_V2`，J6 项目 → `02_Workspace_J6_V2`；mcu 仓库随之确定（见路径角色表）

**（3）V2 工作区切环境（SSH）**：

改 `.imobuilder` 的 `build_product`（Y: 盘直接改）：从 workspace `config/` 目录**现查**该项目的 preset/build_product 值（如 `ls Y:/01_Src/01_Workspace_TDA4_V2/config/`），**不维护写死的映射表**。查到后改 `.imobuilder` 的 `build_product`。

切 mcu 仓库分支（SSH 执行，git 写操作禁止 Windows 本地执行）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/<01_Workspace_TDA4_V2|02_Workspace_J6_V2>/src/<mcu仓库>
git reset --hard
git clean -xdf
git checkout <branch_name>
git pull
```

version_did 和 zos_msg 同步切到相同分支（与 mcu 同分支，develop↔develop，防接口不匹配）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/<工作区>/src/version_did
git reset --hard && git clean -xdf && git checkout <branch_name> && git pull
cd ../zos_msg
git reset --hard && git clean -xdf && git checkout <branch_name> && git pull
```

- ⚠️ 编译前核对各依赖仓库分支：`ssh yaohua@10.0.12.42 "cd <workspace>/src/<仓库> && git branch --show-current"`，必须与 mcu 一致（详见 feature-development/references/build-troubleshooting.md「编译前核对依赖仓库分支」）
- `reset --hard` / `clean -xdf` 仅用于还原干净基线；**阶段 3 有验证性修复改动后不要再 reset**，需要还原基线时先确认修复已交付老工作区

**（4）编译 MCU 固件（SSH）**——保证分析对象是**可编过的基线代码**：

**TDA4_V2**：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/01_Workspace_TDA4_V2/
imobuilder clean mcu_app_tda4 -r
imobuilder build mcu_app_tda4 -r
```

**J6_V2**（`<mcu_app_j6|mcu_app_j6_v2>` 为（2）按项目归属选定的仓库；`-x parking_dr uper_app` 必须带，理由同 feature-development 阶段 3）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/02_Workspace_J6_V2/
imobuilder clean <mcu_app_j6|mcu_app_j6_v2> -r -x parking_dr uper_app
imobuilder build <mcu_app_j6|mcu_app_j6_v2> -r -x parking_dr uper_app
```

**编译失败 → 读 feature-development 的 [references/build-troubleshooting.md](../feature-development/references/build-troubleshooting.md)**（J6 clean 末步失败属正常、后台编译不要接 `| grep` 管道、固件排障、依赖仓库分支核对）。编译失败先按报错判断是环境问题还是代码问题——**代码编译错误本身可能就是问题单的答案**。

**（5）分析代码**：

- 按问题单描述定位相关模块/配置（components、复现步骤提到的功能），在 Y: 盘读代码
- 对照复现步骤走读代码逻辑，形成结论：**是问题**（代码缺陷/配置错误，需修改）或**不是问题**（行为符合设计/规格、测试方法不当、非本模块问题等），并整理依据（代码位置、逻辑链、规格出处）
- 拿不准时列出疑点与需要的信息（问用户或查更多代码），不要硬下结论

> 后续迭代：二分法隔离（Harness 切断可疑模块上下联系）、故障注入（伪造输入确认状态机翻转位置）。

**（6）呈现结论，停下等用户确认**：向用户呈现分析结论（是/不是问题 + 依据）。**是问题** → 确认后进入阶段 3 修复验证；**不是问题** → 确认后跳过阶段 3 直接进入阶段 4 refuse。

## 阶段 3：方案验证与精准修复（仅"是问题"，V2 工作区）

在 V2 工作区做**验证性修复**：Y: 直编修复 → 编译 → 刷板 → 验证。**不建分支、不 commit、不 push**——改动留在 V2 工作区作为验证证据，正式代码由 feature-development 在老工作区重做提交。

1. **最小化修复**：在确定的根因点修改代码/配置，避免涟漪效应（Y: 盘直编）
2. **编译**：命令同阶段 2（4），排障同 feature-development/references/build-troubleshooting.md
3. **刷写（仅 J6，Windows 本地执行）**：用 feature-development 同款工具 `tools/ProgramBoard`，`--img-dir` 指向 **V2 工作区**的编译输出：

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/ProgramBoard
python ProgramBoard_j6b.py --port <A核串口> --psu-com COM44 --config configs/<项目>.json --img-dir Y:/01_Src/02_Workspace_J6_V2/src/<仓库>/build/<preset>/rpu_arm_gcc
```

（工具用法细节、COM 口识别、失败排查同 feature-development 阶段 4。TDA4_V2 无自动刷写工具，跳过刷写直接手动验证。）

4. **验证 —— 停下等待**：用户按问题单复现步骤手动验证修复效果。验证通过后用户会说继续；验证不通过则回到修复点迭代。

## 阶段 4：经验沉淀与流程防腐

### 4.0 分析报告三处沉淀（呈现结论/完成验证时同步做）

1. **docs/analysis/**：`docs/analysis/YYYY-MM-DD-<问题单号>-<主题>.md`——问题单摘要（复现步骤/现象原样）、分析过程、根因与依据、修复方案与验证结果
2. **Obsidian 笔记**：按项目模板在 `ClaudeCodeNote/Work Database/` 建独立分析笔记（frontmatter `jira_key` 指向问题单、`type: Problem`、`status: In Analysis`），Problem Analysis 章节填分析过程；结构参照 story-creation Stage 1
3. **JIRA 问题单评论**：`POST /rest/api/2/issue/<key>/comment`，写分析过程要点 + 结论（中文 JSON 用 `--data-binary @file.json`，认证同阶段 1）

### 4.1 是问题 → 转 feature-development 正式开发（老工作区）

1. 分析笔记升级为 story 笔记：frontmatter `type: Story`、`status: Todo`
2. 走 `story-creation` skill 建 JIRA Story（关联问题单，Link to Problems 行填问题单号），笔记按 Stage 3 回写
3. 走 `feature-development` skill 在**老工作区**完成开发（设计/分支/编码/验证/PR/收尾）。**交接物：V2 已验证的修复代码位置**（工作区/仓库/改动文件清单）——feature-development 阶段 3 编码时对照 V2 改动移植（拷贝或对照重写），V2 改动本身不直接提交
4. 正式提交完成后，V2 工作区的验证性修复可 `git reset --hard` 还原（还原前确认老工作区已包含全部修复）

### 4.2 不是问题 → refuse 关单

1. JIRA 问题单加评论（若 4.0 未写过则此时写）：**为什么不是问题**——引用分析报告结论（行为符合设计/规格出处、测试方法问题等）
2. 查可用流转：`GET https://jira.imotion.ai:7070/rest/api/2/issue/<key>/transitions`，选 refuse/拒绝类流转（名称或目标状态含 refuse/拒绝/Declined 之类）
3. 执行流转：`POST .../issue/<key>/transitions`，body `{"transition":{"id":"<id>"}}`；必填字段按 400 报错补齐（自适应，同 feature-development 阶段 5 关 Problem 单的方式）
4. Obsidian 笔记收尾：`status: Done`、`completed: 今天`、Notes 补分析结论与关单记录

## ⚠️ 关键规则

与 feature-development 完全一致，详见该 skill「关键规则」与「Token 与安全」：

- git 写操作（reset/clean/checkout/commit/push）一律 `ssh yaohua@10.0.12.42` 执行；本地 Y: 盘 git 仅只读且必须 `-c core.filemode=false`
- **V2 工作区只分析+验证性修复，不提交**：不建 feature 分支、不 commit/push；唯一例外是老工作区正式提交完成后才可还原 V2 改动
- Token 从 `C:\Users\YH\.claude\` 配置读取，绝不内联进任何会被提交的文件；`.imobuilder` 含 CI token，不要暴露其内容
````

- [ ] **Step 2: 验证关键结构在位**

Run: `grep -c "^## 阶段" .claude/skills/problem-analysis/SKILL.md && grep -c "dev-workflow" .claude/skills/problem-analysis/SKILL.md`
Expected: `4` 和 `0`（4 个阶段标题；旧 skill 名清零）

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/problem-analysis/SKILL.md
git commit -m "refactor(skill): restructure problem-analysis into 4-phase fix workflow"
```

---

### Task 7: 清理 story-creation / CLAUDE.md / module_router 交叉引用

**Files:**
- Modify: `.claude/skills/story-creation/SKILL.md`（2 处）
- Modify: `CLAUDE.md`（skill 入口 2 行）
- Check: `.claude/hooks/module_router.py`

- [ ] **Step 1: 查 module_router.py 是否引用 skill 名**

Run: `grep -n "dev-workflow\|dev_workflow" .claude/hooks/module_router.py`
Expected: 无输出（预计无引用）。**有输出则同步替换为 feature-development 后再继续**。

- [ ] **Step 2: 改 story-creation/SKILL.md 两处**

第 3 行 frontmatter description 中的：`立项后的开发全流程（分支/编译/验证/PR）用 dev-workflow skill` → `立项后的开发全流程（5 阶段：设计/分支/编码/验证/PR）用 feature-development skill`

第 97 行（边界章节）：`完整开发流程（切分支、编译、刷写、验证、提 PR、关闭工单）走 `dev-workflow` skill。` → `完整开发流程（切分支、编译、刷写、验证、提 PR、关闭工单）走 `feature-development` skill。`

- [ ] **Step 3: 改 CLAUDE.md skill 入口**

```
- 立项（建 Obsidian 笔记 / 建 JIRA Story）→ `story-creation`
- 需求开发（5 阶段：需求解析与架构映射/分支/编码/验证/PR 收尾）→ `feature-development`
- 问题分析（V2 工作区，4 阶段：捕获回放/根因收敛/修复验证/沉淀分流）→ `problem-analysis`
```

- [ ] **Step 4: 验证活跃文件中 dev-workflow 清零**

Run: `grep -rn "dev-workflow" .claude/ CLAUDE.md`
Expected: 无输出

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/story-creation/SKILL.md CLAUDE.md .claude/hooks/module_router.py
git commit -m "refactor(workflow): point cross-references to feature-development"
```

（module_router.py 无改动时不加入 add 列表）

---

### Task 8: 终验（零丢失核对 + 引用闭环 + 触发词）

**Files:** 无新建/修改，纯验证

- [ ] **Step 1: 零丢失核对表**（逐项 grep 新结构，每项都应有命中）

| 原文规则（dev-workflow） | 新落点 | 验证 grep（在 `.claude/skills/feature-development/` 下） |
| --- | --- | --- |
| 开始前确认 5 项 | SKILL.md | `grep -n "开始前确认" SKILL.md` |
| .imobuilder 项目映射 | references/workspace-setup.md | `grep -n "T1LFL1_D073" references/workspace-setup.md` |
| J6 双仓库规则表 | references/workspace-setup.md | `grep -n "mcu_app_j6_v2" references/workspace-setup.md` |
| SSH 建分支命令 + backup patch | SKILL.md 阶段 2 | `grep -n "backup.patch" SKILL.md` |
| 4.1 release 分支创建（v460 命名） | SKILL.md 阶段 2 | `grep -n "release简易分支名" SKILL.md` |
| 5.1 autosar 生成 | SKILL.md 阶段 3 | `grep -n "autosar" SKILL.md` |
| 编译命令 TDA4/J6 | SKILL.md 阶段 3 | `grep -n "imobuilder clean" SKILL.md` |
| J6 clean 末步失败 + 补删命令 | references/build-troubleshooting.md | `grep -n "unrecognized option" references/build-troubleshooting.md` |
| `\| grep` 管道陷阱 | references/build-troubleshooting.md | `grep -n "管道" references/build-troubleshooting.md` |
| 6.1 固件排障（parking_dr/uper_app/MCU21） | references/build-troubleshooting.md | `grep -n "remote_build" references/build-troubleshooting.md` |
| 依赖仓库分支核对（ipc_cfg 案例） | references/build-troubleshooting.md | `grep -n "ipc_cfg_message" references/build-troubleshooting.md` |
| 刷写命令 + 示例 N60/J02 + 全部 ⚠️ | SKILL.md 阶段 4 | `grep -n "ProgramBoard_j6b" SKILL.md` |
| DiagnosticTester 验证 | SKILL.md 阶段 4 | `grep -n "DiagnosticTester.py" SKILL.md` |
| commit 格式规则 | SKILL.md 阶段 5 | `grep -n "feat(模块名)" SKILL.md` |
| PR 创建 API + 标题=commit | SKILL.md 阶段 5 | `grep -n "pull-requests" SKILL.md` |
| reviewers 名单（3 仓库差异）+ 补加方法 | references/pr-merge.md | `grep -n "Xibin.Feng" references/pr-merge.md` |
| 飞书通知 + owner 表 + open_id 全表 | references/pr-merge.md | `grep -n "ou_a438e91570fe6a9ec9eb4b820e2c1cbe" references/pr-merge.md` |
| 10.3 监控循环（自动 merge/imoci/CI 失败/flake/retrigger/zos rebase/409/催审） | references/pr-merge.md | `grep -n "imoci\|retrigger\|force-with-lease" references/pr-merge.md` |
| 笔记总结字段 | SKILL.md 阶段 5 | `grep -n "In Review" SKILL.md` |
| JIRA 关单流转（4/5/121/31/41 + 必填字段） | SKILL.md 阶段 5 | `grep -n "customfield_12305" SKILL.md` |
| 通知报告人（查 reporter + 消息格式） | SKILL.md 阶段 5 | `grep -n "reporter" SKILL.md` |
| git CRLF 红线 + token 安全 | SKILL.md 尾部 | `grep -n "3432" SKILL.md` |

- [ ] **Step 2: 引用闭环**

Run: `ls .claude/skills/feature-development/references/ && grep -rn "references/" .claude/skills/feature-development/SKILL.md .claude/skills/problem-analysis/SKILL.md | grep -o "references/[a-z-]*\.md" | sort -u`
Expected: 3 个文件存在（workspace-setup.md / build-troubleshooting.md / pr-merge.md），且两个 SKILL.md 引用的路径与实际文件一致（problem-analysis 用相对路径 `../feature-development/references/...`）

- [ ] **Step 3: 触发词覆盖**

Run: `grep -o "开发工作流\|走工作流\|做需求\|新需求\|story 开发\|开始开发\|切分支\|编译代码\|上传代码\|提交 PR\|总结笔记\|关闭工单" .claude/skills/feature-development/SKILL.md | sort -u | wc -l`
Expected: `12`（旧触发词全部保留）

- [ ] **Step 4: 全仓终验**

Run: `grep -rn "dev-workflow" .claude/ CLAUDE.md && echo FOUND || echo CLEAN`
Expected: `CLEAN`

Run: `git log --oneline -8`
Expected: 本次 6-7 个新 commit，工作区干净

- [ ] **Step 5: 新会话冒烟（需用户配合）**

重开 Claude Code 会话，确认 skills 列表出现 `feature-development`、`problem-analysis`（`dev-workflow` 消失）。此步需人工确认后勾选。

- [ ] **Step 6: 收尾 commit（如有零星修正）**

```bash
git status --short   # 应为空；有修正则 add + commit
```
