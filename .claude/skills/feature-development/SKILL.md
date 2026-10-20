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
| `D:\Workspace\01_Projects\02_Src` | 本地代码，**autosar 代码生成专用**（tools/autosar_gen 生成目标）+ scp 推送暂存 |
| `10.0.12.42:/comp/user_data/yaohua/01_Src` | 服务器，**编译/代码分析/代码修复/git 全部操作/代码写入** |
| `Y:\01_Src`（服务器映射，同一文件系统） | **仅限：刷写读 build 镜像、读代码、写 `.imobuilder`**。代码写和 git 读写一律 SSH（见 CLAUDE.md 安全红线） |

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
| 3 | 核心配置与编码：SSH 写代码（scp 推送）、autosar 生成、SSH 编译 | Claude（SSH） |
| 4 | SIL 与台架隔离验证：刷写（仅 J6）+ 手动验证 | 刷写 Claude / 验证**用户手动** |
| 5 | 审查与合流：commit/push、PR、监控合并、总结笔记、关单、通知 | Claude |

---

## 阶段 1：需求解析与架构映射

1. **立项**：走 `story-creation` skill——创建 Obsidian 笔记（Work Database/ + 项目模板）+ 创建 JIRA Story 并互相关联，细则全在该 skill
2. **技术方案（所有需求必写）**：`docs/design/YYYY-MM-DD-<工单号>-<主题>-design.md`，**按仓库模板写**（MCU/AUTOSAR BSW 功能 → [autosar-general-feature-design-template.md](../../docs/design/autosar-general-feature-design-template.md)；通用功能 → [general-functional-design-template.md](../../docs/design/general-functional-design-template.md)；模板含属性表/术语/参考文档/约束假设/架构交互含并发上下文/详细设计/异常容错/验收标准/追溯矩阵/ADR/开放问题，小改动按模板内使用说明精简）。技术内容至少覆盖：
   - 需求摘要与验收标准（从 JIRA 需求单 description 提取，原样整理）
   - **BSW 模块影响分析**：明确影响的具体模块与参数（如 Dcm 的 DID/RID、Dem 的 Debouncing 策略、PduR 路由表、Nvm 块）
   - 修改点清单（文件/模块级别，作为附录）
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

**代码修改一律经 SSH 在服务器上写**（Y: 盘禁止写源码：mode 位会被映射破坏 644→755，且本地工具链有 CRLF 风险）。可选方式：

1. **scp 推送**（推荐）：文件先写到 D: 本地暂存（或直接 heredoc 生成），再 `scp` 推到服务器对应路径
2. **SSH heredoc/服务器端编辑**：小改动直接 `ssh yaohua@10.0.12.42 "cat > <服务器路径> <<'EOF' ... EOF"`
3. **autosar 生成产物**：生成目标为 D: 本地（`D:\Workspace\01_Projects\02_Src`），再 `scp -r` 同步到服务器对应仓库路径

- develop 分支：如上修改
- release 分支（第二个分支）：可直接 cherry-pick develop 分支的 commit（SSH 执行 `git cherry-pick <commit-hash>`），冲突时手工解决（release 与 develop 代码有差异）

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

**电源操作规则**：刷写和验证都需要操作电源（程控电源，用 `tools/PowerControl/`，COM 号会漂移、用 list_ports 现查，当前 KA3005P 为 COM44）：

- **刷写/验证之前**：重启电源——`python power_control.py --port <COM> cycle`（J6 刷写的断电冷启动已由 ProgramBoard 工具内置完成，刷写前无需重复执行）
- **刷写/验证之后**：关闭电源——`python power_control.py --port <COM> off`

命令在 `tools/PowerControl/` 目录下 Windows 本地执行。TDA4 无刷写工具，验证前后的电源操作同样适用；台架无程控电源时提示用户手动断电/上电。

**刷写固件（仅 J6，Windows 本地执行）**：用 `tools/ProgramBoard/` 一键刷写工具（`ProgramBoard_j6b.py`）把阶段 3 编译产物刷到板子。**在本机 Windows 执行**（串口/电源 COM 口都在本机，不走 SSH）：

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/ProgramBoard
python ProgramBoard_j6b.py --port <A核串口> --psu-com COM44 --config configs/<项目>.json --img-dir Y:/01_Src/02_Workspace_J6/src/<仓库>/build/<preset>/rpu_arm_gcc
```

示例：

- N60（旧仓库）：`--config configs/n60_mcu.json --img-dir Y:/01_Src/02_Workspace_J6/src/mcu_app_j6/build/cpj_baic_n60_d310/rpu_arm_gcc`
- J02（v2 仓库）：`--config configs/j02_mcu.json --img-dir Y:/01_Src/02_Workspace_J6/src/mcu_app_j6_v2/build/cpj_fawvw_j02_d310/rpu_arm_gcc`（镜像文件 `int_rpu_arm8r5_arm_j02_gnu.img`）

- ⚠️ **`--img-dir` 必须显式传**：工具已从 `Y:\01_Src\tools\flash`（已删除）迁至 D 盘，脚本内置默认镜像路径指向 D 盘本地副本（无 build 产物），不传会找不到镜像；`--img-dir` 一律指向 Y: 盘上阶段 3 的服务器编译输出
- A 核串口识别——**规则权威源 [references/serial-port-identification.md](references/serial-port-identification.md)**（J6/TDA4 判定规则 + 现场快查步骤 + 实测映射表）。COM 号随 USB 重枚举漂移，换板后必须按权威源重新判定；COM44 = KA3005P 电源（`power_control.py id` 可应答验证）；电源未接时省略 `--psu-com`（失败时提示人工断电）
- 全自动流程（约 35 秒/次）：断电冷启动 → 20ms 周期发空格打断 uboot → `fastboot udp` → `flash MCU_a`/`MCU_b` → `fastboot reboot`；任一步失败自动断电重来（默认重试 3 次），退出码 0 成功 / 1 失败
- 前提：板子 A 核串口 + 网线（与 PC 同网段）已接，供电走 KA3005P 输出（12V）
- 失败排查看 `logs/flash_*.log`（`[SER]` 前缀为串口原始数据）；换新板/新 uboot 版本先跑 `--dry-run` 校准，参数与板子特性详见目录下 `README.md`
- TDA4 工作区暂无自动刷写工具，跳过刷写直接进入手动验证

**手动验证 —— 停下等待**：用户手动验证（台架/功能验证）。验证通过后用户会说继续。

**验证方法统一入口：[references/validation-methods.md](references/validation-methods.md)**——诊断相关验证用 `tools/DiagnosticTester` 自动执行（1. 编写 testcase → 2. 运行验证）；采集 log 用 `tools/LogCollection`；电源操作配套见该文档。后续新增验证方法一律补充到该文档，其他地方只指向它。

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

commit 格式（全局规则，所有仓库）：`feat(模块名): [工单号] 项目名 + 描述`，如 `feat(dia_cfg): [D3ACYI-1271] V2x add F187 part number to MCU system info IPC`。**commit 内容必须全部使用英文**（title 和 body）。完整规则（含安全红线）见 [references/git-rules.md](references/git-rules.md)——其他地方查 git/commit 规则时一律指向该文档。注意：给参考示例时只套用格式，内容如实描述本次改动。

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
   - 状态机全貌（Problem/Story 两条主干、Reopen 机制）见 [references/jira-workflow-transitions.md](references/jira-workflow-transitions.md)——其他地方查流转时一律指向该文档
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

## ⚠️ 关键规则：Y: 盘只许刷写读镜像/读代码/写 .imobuilder，其余一律 SSH

**Y:\01_Src 是服务器 10.0.12.42 磁盘 `/comp/user_data/yaohua/` 的网络映射（同一文件系统）**，但从 Windows 侧操作有两重破坏性：

1. 本地 git `core.autocrlf=true`：本地执行 reset/checkout 会把工作区文件改写成 CRLF，污染服务器端仓库（2026-09-10 实际发生：3432 个文件被污染，需服务器端 reset --hard 修复）
2. Y: 映射不保留文件执行位：经 Y: 写源文件会把 mode 644→755 带进 commit（2026-10-19 J02 DoIP 实际发生，产生一笔需 force-push 撤回的 mode 修正 commit）

因此（2026-10-19 用户定规）：

- **允许的 Y: 操作**：刷写读 build 镜像（`--img-dir Y:/...`）、读代码（Read/Grep/Glob）、写 `.imobuilder`
- **禁止的 Y: 操作**：
  - git 操作（读和写都算，含只读查询）——全部 `ssh yaohua@10.0.12.42` 执行
  - 代码写（Edit/Write 源文件）——改走 SSH：D: 暂存后 `scp` 推送，或 SSH heredoc 写入服务器路径

## Token 与安全

- JIRA token：`C:\Users\YH\.claude\.mcp.json`（atlassian 配置）
- Bitbucket token：`C:\Users\YH\.claude\mcp.json`（bitbucket-mcu_app_tda4 配置，`BBDC-` 前缀）
- 从文件读取使用，**绝不内联到任何会被提交的文件里**
- `.imobuilder` 含 CI bearer token，不要暴露其内容
