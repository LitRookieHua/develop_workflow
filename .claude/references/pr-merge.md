# pr-merge：PR 创建、reviewers 名单与 PR 监控手册（创建 PR 前必读）

reviewers 漏加 PR 就废（补加要走 PR 编辑接口且必须带 version）。本手册覆盖：PR 创建 API、reviewers 名单、飞书通知对象与 open_id、PR 状态监控循环、CI 失败处置。

## 0. PR 创建（Bitbucket Server REST API 1.0，也可用 `/bb` 技能）

- 认证：Bearer token（`BBDC-` 前缀），在 `C:\Users\YH\.claude\mcp.json` 的 `bitbucket-mcu_app_tda4.env.BITBUCKET_API_TOKEN`
- `POST https://bitbucket.imotion.ai:7990/rest/api/1.0/projects/MCU/repos/<repo>/pull-requests`
- 仓库：TDA4 → `mcu_app_tda4`；J6 → `mcu_app_j6` 或 `mcu_app_j6_v2`（按工作区选定的仓库）
- 请求体：`{"title": "<commit 标题>", "description": "<commit 完整内容>", "fromRef": {"id": "refs/heads/<feature分支>"}, "toRef": {"id": "refs/heads/develop"}, "reviewers": [...按 §1 名单...]}`
- release 分支的 feature 分支，PR 的 `toRef` 为对应 release 分支（如 `refs/heads/release/Chery/V2XEU_D065/V460`）
- **PR 标题 = commit 标题，PR 内容 = commit 内容**
- 创建后按 §2 发飞书通知，并按 §3 建 PR 监控

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

1. 查状态：`GET https://bitbucket.imotion.ai:7990/rest/api/1.0/projects/<PROJ>/repos/<repo>/pull-requests/<id>`（认证见 [token-authentication.md](token-authentication.md)），state == `MERGED` 即完成
2. **审批通过即自动 merge**：state == `OPEN` 且任意一位人工 reviewer（排除 bot_ci 等 bot 账号）`approved == true` → 立即 `POST .../pull-requests/<id>/merge?version=<GET到的version>` 自动合入（2026-09-21 用户确认：一人通过即可 merge，无需两位 reviewer 都通过）。merge 失败打印错误继续下轮监控
   - **所有仓库（含 mcu_app_tda4，2026-10-14 实际发生）：imoci（bot_ci）CI 审批是强制要求**：人工 reviewer 全部 approved，merge 仍会被 veto（`Not all required reviewers have approved yet | imoci must review and approve`；CI 失败时还会加 `Some reviewers have requested changes: imoci`），必须等 CI 跑完 bot_ci 自动批后再 merge（CI 审批可能耗时 1 小时以上，期间监控轮次只需简短带过继续等）
   - **CI 失败（imoci NEEDS_WORK）的处置（2026-10-14 经验）**：
     - 查失败任务：`GET https://ci.imotion.ai/api/v1/build-tasks/<task_id>`（认证用 tokens.md 的 CI service token，见 [token-authentication.md](token-authentication.md)；task_id 从 Bitbucket build-status 的 url 取，如 `ci.imotion.ai/task/1349908/detail`），`data.detail.progress.build.<repo>.snapshots[0].commit_hash` 可看实际构建输入
     - **并发 flake 识别**：同一 agent（agent_id 相同）时间窗口重叠的多个构建、同输入一成一败、矩阵 fail-fast 连带 CANCELLED 兄弟任务 → 是 flake 不是代码问题，重触发即可
     - **重触发方法**：往 feature 分支推空 commit（`git commit --allow-empty -m 'chore(模块): [工单号] retrigger CI' && git push`），新 head 会重新触发 PR 的 OCR + CI
     - **mcu/zos 成对 PR 的依赖顺序**：PR 的 CI 构建用「目标分支的 zos_msg + mcu PR 补丁」组合（zos_msg 构建时按 EVM_CFG_FILE_NAME 前缀从自己仓库的 Gen_evm_dem_Script 找 xlsx 生成代码）。EVM 表导入类需求 mcu 生成的代码依赖 zos 仓库的新表 → **必须先合 zos PR，再重触发 mcu PR**，否则 mcu CI 会因新旧表不匹配失败
     - ⚠️ 推空 commit 前确认当前分支：checkout 被未跟踪文件挡住而失败时，后续 commit 会落在原分支（2026-10-14 实际推错过分支）。先看 checkout 输出再 commit；未跟踪的 `ti_j721s2_mcu_mcal/` 目录挡 checkout 时直接 `rm -rf` 掉（构建产物）
   - **zos_msg develop 分支仅允许 fast-forward merge**：develop 有新提交时 merge 会被 veto（Control Freak 提示 must rebase），需 SSH 执行 `git fetch origin && git checkout <feature分支> && git rebase origin/develop && git push --force-with-lease`，rebase 后 CI 会重新触发、bot_ci 审批重置，需重新等待
   - merge 409 报 `PullRequestOutOfDateException` 时用响应体里的 `currentVersion` 重试；veto 详细原因在错误响应体的 `errors[].vetoes[].summaryMessage`
3. **PR MERGED** → 飞书通知本人（姚华 `ou_1ec2bf00af2d4b80a88cc51ed6cdc6ee`，`lark-cli im +messages-send --as user`），该 PR 移出监控列表；监控列表为空（全部合并）→ 再通知本人「全部 PR 已合并」，CronDelete 停止监控，并**自动执行 SKILL.md 阶段 5 收尾步骤（关单+通知报告人，无需用户确认）**
4. **PR DECLINED** → 同样飞书通知本人，但**继续监控**其余 PR（不删任务，等用户处理）
5. **久未审批催审**（可选，用户要求时启用）：用状态文件计数，第 N 次（如 18 次）检测仍无审批 → 给韩乐乐发加急催审——先 `lark-cli im +messages-send --as bot --user-id <韩乐乐open_id> --text "..."`（加急要求 bot 是消息发送者），再 `lark-cli im messages urgent_app --message-id <id> --user-id-type open_id --data '{"user_id_list":["<韩乐乐open_id>"]}' --as bot`；bot 发送失败则降级 `--as user` 普通消息。加急只发一次（urgent_sent 标志）
6. 无变化则简短带过

**飞书通知格式（尽量详细）：第一行 `<具体功能>`，第二行 `<PR链接> + <状态>`**

- MERGED：`<具体功能>` 换行 `<PR链接> 已合并`
- DECLINED：`<具体功能>` 换行 `<PR链接> 被拒绝，原因：<原因>` — 原因从 PR 的 activities/comments 查：`GET .../pull-requests/<id>/activities`（token 同上），找最近的评审意见/评论；查不到具体原因就写「未见评审意见」

注意：定时任务仅在会话空闲时触发、会话关闭即停止（需跨会话监控时建 durable 任务并告知用户）；recurring 任务 7 天后自动过期，建任务时要向用户说明。
