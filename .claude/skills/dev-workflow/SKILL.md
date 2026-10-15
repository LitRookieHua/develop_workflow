---
name: dev-workflow
description: MCU 需求开发全流程工作流（Obsidian 笔记 → JIRA story → 确认项目/分支 → SSH 切 develop 建分支 → 改代码 → 编译 → 刷写 → 验证 → 上传 → Bitbucket PR → 关闭 JIRA/笔记 → 通知需求报告人，共 13 步）。Use this skill whenever the user mentions 开发工作流、走工作流、做需求、新需求、story 开发、开始开发, references a requirement or JIRA ticket (如 D3ACYI-xxxx) to develop in mcu_app_tda4 / mcu_app_j6 / mcu_app_j6_v2, or asks for any part of the flow — 切分支、编译代码、上传代码、提交 PR、总结笔记、关闭工单/JIRA — even if they only mention a single step.
---

# MCU 需求开发工作流（Obsidian → JIRA → 代码 → 编译 → 刷写 → 验证 → PR → 关闭 → 通知报告人）

13 步固定流程，适用于 TDA4 / J6 工作区的 mcu_app 需求开发。其中 **第 8 步手动验证是用户手动操作**，执行到该步时停下等用户确认。第 12-13 步在所有 PR 合并后**自动执行，无需用户确认**（见 10.3）。

开始前用 TaskCreate 为本次需求创建任务列表（每步一个任务），逐步勾选，随时可从任务列表恢复进度。

## 路径角色

| 路径 | 角色 |
| --- | --- |
| `D:\Workspace\01_Projects\02_Src` | 本地代码，**autosar 代码生成专用**（develop_workflow/tools/autosar_gen 生成目标） |
| `10.0.12.42:/comp/user_data/yaohua/01_Src` | 服务器，**编译/代码分析/代码修复** |
| `Y:\01_Src`（服务器映射，同一文件系统） | 服务器代码在 Windows 侧的编辑入口（改代码走 Y: 直编） |

---

## 开始前确认

从用户消息或笔记中确认以下信息，缺了就问：

1. **工作区**：TDA4（`Y:\01_Src\01_Workspace_TDA4`）还是 J6（`Y:\01_Src\02_Workspace_J6`）
2. **来源需求**：JIRA 单号/链接，或需求描述
3. **项目/变体**：如 V2XSEA、T1LFL1、T51、N60、J02
4. **待修改分支**：仅 develop，还是 develop + release（如 `release/Chery/V2XEU_D065/V460`）
5. **修改仓库**：mcu_app / zos_msg / version_did 中哪些仓库需要改动。J6 工作区的 mcu 仓库有 `mcu_app_j6` 和 `mcu_app_j6_v2` 两个，须按项目归属选定（见第 3 步（3））

## 流程总览

| 步骤 | 内容 | 执行者 |
| --- | --- | --- |
| 1 | 创建 Obsidian 笔记 | Claude |
| 2 | 创建 story JIRA 单 | Claude |
| 3 | 确认项目（TDA4/J6）+ 确认待修改分支（develop/release）+ 确认修改仓库（mcu/zos_msg/version_did） | Claude |
| 4 | SSH 切换 develop 最新代码，拉取并创建/切换分支（mcu/zos_msg/version_did） | Claude（SSH） |
| 5 | 修改代码 | Claude |
| 6 | 编译代码（imobuilder） | Claude（SSH） |
| 7 | 刷写固件到板子（仅 J6，tools/ProgramBoard 工具） | Claude（Windows 本地） |
| 8 | 手动验证 | **用户手动** |
| 9 | 提交 commit + push（SSH） | Claude（SSH） |
| 10 | 创建 Bitbucket PR + 飞书通知 owner | Claude |
| 11 | 总结 Obsidian 笔记 | Claude |
| 12 | 关闭 JIRA 单和笔记（PR 合并后） | Claude |
| 13 | 飞书通知需求报告人（PR 合并后） | Claude |

---

## 第 1 步：创建 Obsidian 笔记

- 笔记本：`D:\Workspace\21_ObsidianWorkspace\02_ClaudeCodeNote\ClaudeCodeNote`
- **笔记统一放 `Work Database\` 目录**
- 模板：`Templates\` 目录（通用模板 + 项目专属模板 IDC100/IDC300/…/PDCU，按 JIRA 项目选）
- 笔记正文要链接来源需求 JIRA 单

### 笔记结构

- frontmatter：`type / status / priority / created / start / completed / tags / jira_key / jira_url / project / issue_type / component / fix_version / due_date / variant / assignee / parent_requirements`
- 正文：H1 标题、Description（含来源需求链接）、JIRA 表格、Details、Subtasks（勾选框，含"PR 合并后：JIRA Story 转已解决"）、Notes（按日期的日志，如 `### 2026-09-10 开发记录`）、Attachments、Related Links

## 第 2 步：创建 JIRA story

用 REST API（不要用 MCP 工具，本环境未挂载）：

- 认证：PAT Bearer，token 在 `C:\Users\YH\.claude\.mcp.json` 的 `mcpServers.atlassian.env`（`JIRA_USER` / `JIRA_API_TOKEN`）
- `POST https://jira.imotion.ai:7070/rest/api/2/issue`，字段：project、issuetype=Story、summary、description、components、fixVersions、duedate、assignee
- **Variant（车型变体）= customfield_15000**，必填多选
- 创建成功后把 `jira_key` / `jira_url` 回填到笔记 frontmatter

## 第 3 步：确认项目 + 确认待修改分支 + 确认修改仓库

（1）**确认项目**（TDA4 or J6），修改 .imobuilder：

根据 `config/` 目录查找对应项目名称，修改本地 `.imobuilder` 的 `build_product`（Y: 盘直接改）：

- TDA4（`Y:\01_Src\01_Workspace_TDA4`）：T1LFL1 → `Chery/T1LFL1_D073/develop`；V2XSEA → `Chery/V2XSEA_D058/develop`
- J6（`Y:\01_Src\02_Workspace_J6`）：T51 → `Gac/T51_D088/develop`；N60 → `BAIC/N60_D109/develop`；J02 → `FAWVW/J02_C097/develop`

（2）**确认待修改分支**（develop 和 release）：

确认本次需求要修改的分支：仅 develop，还是 develop + release（如 `release/Chery/V2XEU_D065/V460`）。

**多分支规则**：若 develop 和 v460 等两个分支都需要修改，develop 分支先完整执行步骤 4-9，v460 分支再执行一遍步骤 4-9；第二个分支的代码修改可直接用 cherry-pick 移植 develop 分支的 commit（见第 5 步）。

（3）**确认修改仓库**（mcu / zos_msg / version_did 代码）：

确认本次需求要修改的仓库：mcu_app（TDA4 为 `mcu_app_tda4`；J6 为 `mcu_app_j6` 或 `mcu_app_j6_v2`，按项目归属选定）、`zos_msg`、`version_did` 等。第 4 步仅对这些仓库切分支、建分支。

**J6 双仓库规则**（2026-09-29 起 J6 工作区有两个 mcu 仓库）：

| 仓库 | 项目归属 |
| --- | --- |
| `mcu_app_j6` | 存量项目：T51（GAC）、N60（BAIC）、S52 等旧项目 |
| `mcu_app_j6_v2` | 新项目：J02（FAWVW，preset `cpj_fawvw_j02_d310`）、GWM 新项目（c06g/de09g）、HONDA（h3ata3pda）等 |

- 判断方法：看项目的 cpj 目录在哪个仓库下（如 `src/mcu_app_j6_v2/cpj_fawvw/veh_j02/`）；v2 仓库顶层只有 `cpj_fawvw / cpj_gwm / cpj_honda` 三个 cpj 目录
- ⚠️ 两仓库都有 `cpj_gwm` 目录，不能只按 OEM 判断；GWM 项目要按具体车型确认在哪个仓库
- 拿不准时问用户，不要默认选 `mcu_app_j6`

## 第 4 步：SSH 切换 develop 最新代码，拉取并创建/切换分支

分支由本流程统一创建并推送（2026-09-11 起，原"用户手动拉分支"步骤已合并到本步）。对第 3 步（3）确认的修改仓库（mcu_app_tda4 / mcu_app_j6 / mcu_app_j6_v2、zos_msg、version_did 等）逐一执行。

分支命名：`feature/<jira工单号>-<标题小写连字符>`（如 `feature/D3ACYI-1271-v2x-series-send-mcu-system-info`）。

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

**J6**（仓库在 `/comp/user_data/yaohua/01_Src/02_Workspace_J6/src/` 下，如 `mcu_app_j6`、`mcu_app_j6_v2`、`zos_msg`、`version_did`；mcu 仓库按第 3 步（3）的双仓库规则选定）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/02_Workspace_J6/src/<仓库>
# 后续命令同上
```

- 执行前如有未提交改动：先 `git -c core.filemode=false diff -- <files> > /tmp/backup.patch` 备份，切完后 `git apply` 恢复
- SSH 密钥认证已配好

### 4.1 release 分支合入的分支创建

需求需同时合入 release 分支时（如 `release/Chery/V2XEU_D065/V460`），develop 分支的步骤 4-9 完成后，从 **release 分支**基底创建独立 feature 分支：

```bash
git fetch origin
git checkout -b feature/<jira工单号>-<标题>-<release简易分支名> origin/<release分支名>
git push -u origin feature/<jira工单号>-<标题>-<release简易分支名>
```

- release 简易分支名 = release 分支名最后一节小写，如 `release/Chery/V2XEU_D065/V460` → `v460`（例：`feature/D3ACYI-1181-lateral-update-910-v460`）
- 该分支的代码修改可直接 cherry-pick develop 分支的 commit（见第 5 步），PR 目标为对应 release 分支
- 注意：develop 分支上的 mcal 符号链接等本地改动可能挡 checkout，按需先 `git checkout -- <文件>` 丢弃

## 第 5 步：修改代码

在 Y: 盘直接编辑（与服务器同一文件系统）。

- develop 分支：直接编辑代码
- release 分支（第二个分支）：可直接 cherry-pick develop 分支的 commit（SSH 执行 `git cherry-pick <commit-hash>`），冲突时手工解决（release 与 develop 代码有差异）

### 5.1 autosar 生成代码场景

Dcm/Dem/Nvm 配置类需求使用 `D:\Workspace\01_Projects\02_Src\11_AI\develop_workflow\tools\autosar_gen\` 下工具生成代码：

- 生成目标为 D: 本地路径（`D:\Workspace\01_Projects\02_Src`，autosar 专用）
- 产物需进入服务器仓库时，从 D: 拷贝同步到 Y: 对应仓库路径，再走第 9 步 SSH 提交

## 第 6 步：编译代码（SSH）

通过 SSH 在服务器上编译：

**TDA4**：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/01_Workspace_TDA4/
imobuilder clean mcu_app_tda4 -r
imobuilder build mcu_app_tda4 -r
```

**J6**（`-x parking_dr uper_app` 必须带，这两个包的远端仓库 `ip/parking_dr`、`ip/uper_app` 已不存在，不带会 clone 失败；`<mcu_app_j6 或 mcu_app_j6_v2>` 按第 3 步（3）选定的仓库，v2 同样带 `-x`，2026-09-29 用户确认）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/02_Workspace_J6/
imobuilder clean <mcu_app_j6|mcu_app_j6_v2> -r -x parking_dr uper_app
imobuilder build <mcu_app_j6|mcu_app_j6_v2> -r -x parking_dr uper_app
```

⚠️ **J6 的 clean 最后一步 `<仓库名>-clean_binary` 必定失败**（2026-09-11 实际发生，与 `-x` 无关）：imobuilder 把 `--build --preset pf-gcc-clean` 参数拼到仓库的 clean 命令（`rm -rf .../output`）末尾，rm 报 `unrecognized option '--build'`，clean 以 exit 4 结束。但此时 clean 的其余部分（workspace build 树、各依赖包目录、`src/<仓库>/build`）已删完，实际效果等于 clean 完成，只需手动补删残留目录再直接 build：

```bash
ssh yaohua@10.0.12.42 "rm -rf /comp/user_data/yaohua/01_Src/02_Workspace_J6/src/<仓库>/output"
ssh yaohua@10.0.12.42 "cd /comp/user_data/yaohua/01_Src/02_Workspace_J6/ && imobuilder build <mcu_app_j6|mcu_app_j6_v2> -r -x parking_dr uper_app"
```

编译耗时较长（可后台运行）。失败则根据报错修复代码后重试，通过后进入第 7 步刷写固件（仅 J6；TDA4 直接进入手动验证）。

⚠️ 后台运行编译时不要在命令后接 `| grep` 管道——会把真实退出码掩盖成 grep 的退出码（2026-09-11 实际发生：clean 致命失败却报 exit 0）。SSH 警告信息留在输出文件里即可。

### 6.1 固件问题排障（parking_dr / uper_app / MCU21，2026-10-14 用户指示）

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

⚠️ **编译前核对 workspace 各依赖仓库的分支**（2026-10-15 实际发生）：mcu 产品的构建会组合 workspace 里当前 checkout 的 zos_msg 等依赖仓库代码。develop/V460 两条分支交替开发时，切换 mcu 仓库后**必须把 zos_msg 等依赖仓库也切到对应分支**，否则出现接口不匹配类编译错误（如 `ipc_cfg_message.hpp: error: expected class name`，基类 `zos::park_dr::COdoAbstOutput` 找不到——develop mcu 配了 v460 的 zos_msg）。编译报「找不到类/接口不匹配」先查 `ssh yaohua@10.0.12.42 "cd <workspace>/src/<依赖仓库> && git branch --show-current"`。

## 第 7 步：刷写固件（仅 J6）—— Windows 本地执行

用 `D:\Workspace\01_Projects\02_Src\11_AI\develop_workflow\tools\ProgramBoard\` 的一键刷写工具（`ProgramBoard_j6b.py`）把第 6 步编译产物刷到板子，供第 8 步手动验证。**在本机 Windows 执行**（串口/电源 COM 口都在本机，不走 SSH）：

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/ProgramBoard
python ProgramBoard_j6b.py --port <A核串口> --psu-com COM44 --config configs/<项目>.json --img-dir Y:/01_Src/02_Workspace_J6/src/<仓库>/build/<preset>/rpu_arm_gcc
```

示例：

- N60（旧仓库）：`--config configs/n60_mcu.json --img-dir Y:/01_Src/02_Workspace_J6/src/mcu_app_j6/build/cpj_baic_n60_d310/rpu_arm_gcc`
- J02（v2 仓库）：`--config configs/j02_mcu.json --img-dir Y:/01_Src/02_Workspace_J6/src/mcu_app_j6_v2/build/cpj_fawvw_j02_d310/rpu_arm_gcc`（镜像文件 `int_rpu_arm8r5_arm_j02_gnu.img`）

- ⚠️ **`--img-dir` 必须显式传**：工具已从 `Y:\01_Src\tools\flash`（已删除）迁至 D 盘，脚本内置默认镜像路径指向 D 盘本地副本（无 build 产物），不传会找不到镜像；`--img-dir` 一律指向 Y: 盘上第 6 步的服务器编译输出
- A 核串口按 `USB-Enhanced-SERIAL-C` 描述识别（COM 号会因 USB 重枚举漂移，如 COM30/COM41，用 list_ports 查当前号），COM44 = KA3005P 电源；电源未接时省略 `--psu-com`（失败时提示人工断电）
- 全自动流程（约 35 秒/次）：断电冷启动 → 20ms 周期发空格打断 uboot → `fastboot udp` → `flash MCU_a`/`MCU_b` → `fastboot reboot`；任一步失败自动断电重来（默认重试 3 次），退出码 0 成功 / 1 失败
- 前提：板子 A 核串口 + 网线（与 PC 同网段）已接，供电走 KA3005P 输出（12V）
- 失败排查看 `logs/flash_*.log`（`[SER]` 前缀为串口原始数据）；换新板/新 uboot 版本先跑 `--dry-run` 校准，参数与板子特性详见目录下 `README.md`
- TDA4 工作区暂无自动刷写工具，跳过此步直接进入第 8 步

## 第 8 步：手动验证 —— 停下等待

用户手动验证（台架/功能验证）。验证通过后用户会说继续。

诊断功能验证用 `D:\Workspace\01_Projects\02_Src\11_AI\develop_workflow\tools\DiagnosticTester`：自己写 testcase（`testcase/<项目>/<用例>/<用例>.yaml`，写法见该目录 README.md），然后跑脚本验证：

```bash
python DiagnosticTester.py run testcase/<项目>/<用例>/<用例>.yaml --config configs/<项目>/<配置>.yaml
```

测试桩（转发器）见 `develop_workflow/tests/harness/diag_test/`。

## 第 9 步：提交 commit + push（SSH）

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/<工作区>/src/<仓库>
git add <files>
git commit -m "feat(模块名): [工单号] 项目名 + 描述"
git push
```

commit 格式（全局规则，所有仓库）：`feat(模块名): [工单号] 项目名 + 描述`，如 `feat(dia_cfg): [D3ACYI-1271] V2x add F187 part number to MCU system info IPC`。注意：给参考示例时只套用格式，内容如实描述本次改动。

push 后记下 commit hash（总结笔记要用）。

## 第 10 步：创建 Bitbucket PR + 飞书通知 owner

### 10.1 创建 PR

用 Bitbucket Server REST API 1.0（也可用 `/bb` 技能）：

- 认证：Bearer token（`BBDC-` 前缀），在 `C:\Users\YH\.claude\mcp.json` 的 `bitbucket-mcu_app_tda4.env.BITBUCKET_API_TOKEN`
- `POST https://bitbucket.imotion.ai:7990/rest/api/1.0/projects/MCU/repos/<repo>/pull-requests`
- 仓库：TDA4 → `mcu_app_tda4`；J6 → `mcu_app_j6` 或 `mcu_app_j6_v2`（按第 3 步（3）选定的仓库）
- 请求体：`{"title": "<commit 标题>", "description": "<commit 完整内容>", "fromRef": {"id": "refs/heads/<feature分支>"}, "toRef": {"id": "refs/heads/develop"}, "reviewers": [{"user": {"name": "Lucas.Han"}}, {"user": {"name": "Xiaorong.Tao"}}]}`
- **reviewers 必加 2 人**：韩乐乐 `Lucas.Han`、陶晓荣 `Xiaorong.Tao`（Bitbucket 用户名）。创建时漏加的，用 PR 编辑接口补：`PUT .../pull-requests/<id>`，请求体带 `title/description/version(GET到的)/fromRef/toRef/reviewers`（version 必须带，否则 400；participants 接口会 403 不可用）
- **mcu_app_tda4 / mcu_app_j6 / version_did 仓库额外加 1 人（2026-10-14 起，共 3 人）**：冯锡斌 `Xibin.Feng`（Bitbucket 用户名）。飞书通知也发他（mcu_app_j6_v2 维持 4 人名单不变）
- **mcu_app_j6_v2 仓库额外加 2 人（2026-10-08 起，共 4 人）**：戴杰 `jie.dai`、王涛 `Samuel.Wang`（Bitbucket 用户名）。飞书通知也发这 4 人
- **zos_msg 仓库的 reviewers**：曾健荣 `jianrong.zeng`、李翔 `xiang.li`（Bitbucket 用户名，2026-09-30 D1CYC-1670 确认；⚠️ Bitbucket `/rest/api/1.0/users?search=` 接口对中文/拼音查询无效，找不到用户名时从该仓库最近 PR 的 reviewers 列表里查）
- release 分支的 feature 分支，PR 的 `toRef` 为对应 release 分支（如 `refs/heads/release/Chery/V2XEU_D065/V460`）
- **PR 标题 = commit 标题，PR 内容 = commit 内容**

### 10.2 飞书通知 owner（PR 创建后）

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

### 10.3 PR 状态监控（每 10 分钟）

PR 创建 + 通知后，用 CronCreate 建一个每 10 分钟的定时任务（session-only，cron 用 `7-57/10 * * * *` 避开整点分钟），监控本 story 所有未合并 PR：

1. 查状态：`GET https://bitbucket.imotion.ai:7990/rest/api/1.0/projects/<PROJ>/repos/<repo>/pull-requests/<id>`（token 同 10.1），state == `MERGED` 即完成
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
3. **PR MERGED** → 飞书通知本人（姚华 `ou_1ec2bf00af2d4b80a88cc51ed6cdc6ee`，`lark-cli im +messages-send --as user`），该 PR 移出监控列表；监控列表为空（全部合并）→ 再通知本人「全部 PR 已合并」，CronDelete 停止监控，并**自动执行第 12、13 步（无需用户确认）**
4. **PR DECLINED** → 同样飞书通知本人，但**继续监控**其余 PR（不删任务，等用户处理）
5. **久未审批催审**（可选，用户要求时启用）：用状态文件计数，第 N 次（如 18 次）检测仍无审批 → 给韩乐乐发加急催审——先 `lark-cli im +messages-send --as bot --user-id <韩乐乐open_id> --text "..."`（加急要求 bot 是消息发送者），再 `lark-cli im messages urgent_app --message-id <id> --user-id-type open_id --data '{"user_id_list":["<韩乐乐open_id>"]}' --as bot`；bot 发送失败则降级 `--as user` 普通消息。加急只发一次（urgent_sent 标志）
6. 无变化则简短带过

**飞书通知格式（尽量详细）：第一行 `<具体功能>`，第二行 `<PR链接> + <状态>`**

- MERGED：`<具体功能>` 换行 `<PR链接> 已合并`
- DECLINED：`<具体功能>` 换行 `<PR链接> 被拒绝，原因：<原因>` — 原因从 PR 的 activities/comments 查：`GET .../pull-requests/<id>/activities`（token 同上），找最近的评审意见/评论；查不到具体原因就写「未见评审意见」

注意：定时任务仅在会话空闲时触发、会话关闭即停止（需跨会话监控时建 durable 任务并告知用户）；recurring 任务 7 天后自动过期，建任务时要向用户说明。

## 第 11 步：总结 Obsidian 笔记

更新笔记：

- `status: In Review`
- Subtasks 勾选完成项
- Notes 新增本次日期记录：commit hash、PR 链接、待办（PR 合并后转已解决）
- Related Links 加 PR 链接

## 第 12 步：关闭 JIRA 单和笔记（PR 合并后）

PR 监控确认全部 PR 已合并后自动执行（见 10.3），无需用户确认；PR 尚未全部合并时不要做这步：

1. **确认合并**：`GET .../pull-requests/<id>`，state == `MERGED`
2. **JIRA 转已解决**：「开放」状态没有直接的解决流转，需两步 POST `https://jira.imotion.ai:7070/rest/api/2/issue/<key>/transitions`（认证同第 2 步，⚠️ 必须 PAT Bearer 方式，Basic auth 会 401）：
   - `{"transition":{"id":"4"}}` → 开始进行（开放 → 处理中）
   - `{"transition":{"id":"5"}}` → 解决问题（处理中 → 已解决，resolution 自动为完成）
3. **关闭关联需求单/问题单**（2026-09-21 用户要求，漏关即收尾未完成）：除 story 外，笔记 frontmatter `parent_problems` / `parent_requirements` 及来源需求中列出的关联单都要一并关闭：
   - **Problem 单**（issuetype=Problem）三步流转，各步带必填字段：
     - `{"transition":{"id":"121"}}` → 开始分析（开放 → In Analysis）
     - `{"transition":{"id":"31"}}` → 分析完成，**必填** `customfield_12017`（英文根因描述）+ `duedate` + `fixVersions`（如 `[{"name":"T320"}]`，取 story 的修复版本）
     - `{"transition":{"id":"41"}}` → 已实现（终态），**必填** `customfield_12305`（Link to Bugfix，easy-links 格式 `[{"key":"<story单号>"}]`，传字符串数组会报 expected Object）
   - **需求单（Requirement 等）**：查看其可用 transitions（`GET .../issue/<key>/transitions`）选合适的关闭流转，有必填字段按报错补齐
4. **关闭笔记**：`status: Done`、填写 `completed` 日期、勾选关闭 Subtask、Notes 补关闭记录（PR 合并日期）

## 第 13 步：飞书通知需求报告人（PR 合并后）

查看**来源需求单**（parent requirement，如 `IDC310BAICREQ-4639`）的报告人，飞书通知其需求已完成：

1. **查报告人**（认证同第 2 步）：

```bash
curl -s -k -H "Authorization: Bearer <JIRA_TOKEN>" "https://jira.imotion.ai:7070/rest/api/2/issue/<来源需求单号>?fields=reporter"
```

取 `fields.reporter.displayName`（如 `Zhang San/张三`）。

2. **查 open_id**：`lark-cli contact +search-user --queries "<姓名>" --as user`
3. **发消息**（`--as user`，同 10.2）：

```bash
lark-cli im +messages-send --as user --user-id <ou_xxx> --text "<具体功能>已完成，并上传<分支列表>"
```

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
