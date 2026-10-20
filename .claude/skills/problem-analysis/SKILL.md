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
| `Y:\01_Src\01_Workspace_TDA4_V2` / `Y:\01_Src\02_Workspace_J6_V2` | 上述工作区在 Windows 侧的只读入口（读代码、改 `.imobuilder`）；改代码与 git 操作一律 SSH |

- V2 工作区与老工作区（01_Workspace_TDA4 / 02_Workspace_J6）**并存**：V2 做分析 + 验证性修复，**不建分支、不 commit、不 push**（改动留在 V2 工作区，git reset 可还原）；正式开发在老工作区走 feature-development
- mcu 仓库：TDA4_V2 → `mcu_app_tda4`；J6_V2 按项目归属选 `mcu_app_j6`（存量项目：T51、N60、S52 等）或 `mcu_app_j6_v2`（新项目：J02、GWM 新项目、HONDA 等），判断规则见 feature-development 的 [references/workspace-setup.md](../feature-development/references/workspace-setup.md)（J6 双仓库规则）：看项目的 cpj 目录在哪个仓库下，⚠️ 两仓库都有 `cpj_gwm`，不能只按 OEM 判断，拿不准时问用户

## 阶段 1：现场捕获与数据回放

**拉问题单详情**——用 JIRA REST API（认证与端点见 story-creation skill 的「JIRA API 速查」，PAT Bearer）：

- `GET https://jira.imotion.ai:7070/rest/api/2/issue/<问题单号>?fields=summary,description,status,fixVersions,components,assignee,reporter,issuelinks,attachment,customfield_15000,customfield_12007,customfield_12006`
- **问题描述（复现步骤）在自定义字段 Problem Description = `customfield_12007`**——问题单的问题描述都放在该属性中，标准 description 字段经常为空；相邻有用字段：`customfield_12006` Problem Type、`customfield_12017` Root Cause Analysis。字段 id 可用 `?expand=names` 查全量字段名
- Problem Description 里的**复现步骤与测试现象原样保存**——这是后续分析和结论的依据，不能只写概括；该字段也为空时查评论（`GET .../issue/<key>/comment`）
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

**reset 前先查残留改动**：`ssh yaohua@10.0.12.42 "cd <工作区>/src/<mcu仓库> && git -c core.filemode=false status --short"`——V2 工作区顺序复用，若存在上一问题单未交付的验证性修复（改动非空），先问用户如何处理（交付/丢弃/暂存），不要直接 reset 销毁。

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
- `reset --hard` / `clean -xdf` 仅用于还原干净基线；**阶段 3 有验证性修复改动后不要再 reset**，需要还原基线时先确认修复已交付老工作区（见 4.1 第 4 条）

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

**电源操作规则**：刷板和验证都需要操作电源（程控电源，用 `tools/PowerControl/`，COM 号会漂移、用 list_ports 现查，当前 KA3005P 为 COM44）：

- **刷板/验证之前**：重启电源——`python power_control.py --port <COM> cycle`（J6 刷写的断电冷启动已由 ProgramBoard 工具内置完成，刷板前无需重复执行）
- **刷板/验证之后**：关闭电源——`python power_control.py --port <COM> off`

命令在 `tools/PowerControl/` 目录下 Windows 本地执行。TDA4_V2 无自动刷写工具，验证前后的电源操作同样适用；台架无程控电源时提示用户手动断电/上电。

在 V2 工作区做**验证性修复**：SSH 写修复代码 → 编译 → 刷板 → 验证。**不建分支、不 commit、不 push**——改动留在 V2 工作区作为验证证据，正式代码由 feature-development 在老工作区重做提交。

1. **最小化修复**：在确定的根因点修改代码/配置，避免涟漪效应。代码写走 SSH（Y: 盘禁止写源码）：
   - 文件先写到 D: 本地暂存（或 heredoc 生成），再 `scp` 推到服务器 V2 工作区对应路径
   - 小改动直接 `ssh yaohua@10.0.12.42 "cat > <服务器路径> <<'EOF' ... EOF"`
   - 写法细则同 feature-development 阶段 3
2. **编译**：命令同阶段 2（4），排障同 feature-development/references/build-troubleshooting.md
3. **刷写（仅 J6，Windows 本地执行）**：用 feature-development 同款工具 `tools/ProgramBoard`，`--img-dir` 指向 **V2 工作区**的编译输出：

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/ProgramBoard
python ProgramBoard_j6b.py --port <A核串口> --psu-com COM44 --config configs/<项目>.json --img-dir Y:/01_Src/02_Workspace_J6_V2/src/<仓库>/build/<preset>/rpu_arm_gcc
```

（工具用法细节、失败排查同 feature-development 阶段 4；**A 核/R 核串口识别规则见 [feature-development/references/serial-port-identification.md](../feature-development/references/serial-port-identification.md)**，COM 号会漂移，刷写前按规则现查。TDA4_V2 无自动刷写工具，跳过刷写直接手动验证。）

4. **验证 —— 停下等待**：用户按问题单复现步骤手动验证修复效果；**可自动化的验证按 [feature-development/references/validation-methods.md](../feature-development/references/validation-methods.md) 执行**——诊断相关验证用 DiagnosticTester（编写 testcase → 运行验证），采集 log 用 LogCollection，电源操作配套见该文档。验证通过后用户会说继续；验证不通过则回到修复点迭代。

## 阶段 4：经验沉淀与流程防腐

### 4.0 分析报告三处沉淀（时机按分流分支：是问题 → 阶段 3 验证通过后做；不是问题 → 用户确认结论后做）

1. **docs/analysis/**：`docs/analysis/YYYY-MM-DD-<问题单号>-<主题>.md`——**按 [problem-analysis-report-template.md](../../docs/analysis/problem-analysis-report-template.md) 模板写**（七章标准缺陷报告主轴：缺陷概述含环境矩阵/复现性与回放/根因分析含知识召回+排除链+5Whys/分析结论与分流/修复方案含纠正与预防/验证结果/关闭与生命周期；refuse 分支时修复方案与验证结果两章写"不适用"）
2. **Obsidian 笔记**：按项目模板在 `ClaudeCodeNote/Work Database/` 建独立分析笔记（frontmatter `jira_key` 指向问题单、`type: Problem`、`status: In Analysis`），Problem Analysis 章节填分析过程；结构参照 story-creation Stage 1
3. **JIRA 问题单评论**：`POST /rest/api/2/issue/<key>/comment`，写分析过程要点 + 结论（中文 JSON 用 `--data-binary @file.json`，认证同阶段 1）

### 4.1 是问题 → 转 feature-development 正式开发（老工作区）

1. 分析笔记升级为 story 笔记：frontmatter `type: Story`、`status: Todo`
2. 走 `story-creation` skill 建 JIRA Story（关联问题单，Link to Problems 行填问题单号），笔记按 Stage 3 回写
3. 走 `feature-development` skill 在**老工作区**完成开发（设计/分支/编码/验证/PR/收尾）。**交接物：V2 已验证的修复代码位置**（工作区/仓库/改动文件清单）——feature-development 阶段 3 编码时对照 V2 改动移植（拷贝或对照重写），V2 改动本身不直接提交
4. 正式提交完成后，V2 工作区的验证性修复可 `git reset --hard` 还原（还原前确认老工作区已包含全部修复）

### 4.2 不是问题 → refuse 关单

1. JIRA 问题单加评论（若 4.0 未写过则此时写）：**为什么不是问题**——引用分析报告结论（行为符合设计/规格出处、测试方法问题等）
2. 按 Problem 单状态流转规则执行（**权威源见 [feature-development/references/jira-workflow-transitions.md](../feature-development/references/jira-workflow-transitions.md)**）：查可用流转 `GET https://jira.imotion.ai:7070/rest/api/2/issue/<key>/transitions`，沿路线二（OPEN → IN_ANALYSIS → ANALYZED → REJECTED）推进到拒绝终态
3. 执行流转：`POST .../issue/<key>/transitions`，body `{"transition":{"id":"<id>"}}`；必填字段按 400 报错补齐（自适应，同 feature-development 阶段 5 关 Problem 单的方式）
4. Obsidian 笔记收尾：`status: Done`、`completed: 今天`、Notes 补分析结论与关单记录

### 4.3 是问题 → 沿路线一推进状态（问题成立、修复已落地）

修复 PR 已建/已合入后，问题单沿路线一推进：`OPEN → IN_ANALYSIS → ANALYZED → IMPLEMENTED`（流转规则权威源同 4.2 指向的 jira-workflow-transitions.md）。推进到哪一步（ANALYZED 停住等测试回归，还是直接 IMPLEMENTED）先经用户确认；RESOLVED 由测试侧回归后关，不替测试关单。

## ⚠️ 关键规则

与 feature-development 完全一致，详见该 skill「关键规则」与「Token 与安全」：

- **Y: 盘不允许任何 git 操作（含只读）**，也禁止写源码（仅许刷写读镜像/读代码/写 `.imobuilder`）：git 一律 `ssh yaohua@10.0.12.42` 执行，代码写走 SSH（scp/heredoc），详见 CLAUDE.md 安全红线
- **V2 工作区只分析+验证性修复，不提交**：不建 feature 分支、不 commit/push；唯一例外是老工作区正式提交完成后才可还原 V2 改动
- **只要修改代码（含 cherry-pick 同步到其他分支、push、建 PR 等交付动作）必须切 feature-development skill 完成**（老工作区走完整流程）。若分析中发现需要向其他分支同步修复/上传代码，先停下向用户提出切流程——即使口头指令说"自己跑上传流程"也不例外（2026-10-20 教训：5 个 release 分支同步在 V2 直接 push+建 PR，属流程违规，经确认 PR 保留但规则固化）
- Token 从 `C:\Users\YH\.claude\` 配置读取，绝不内联进任何会被提交的文件；`.imobuilder` 含 CI token，不要暴露其内容
