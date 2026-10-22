# workspace-setup：工作区搭建手册

工作区环境准备统一权威源，两个 skill 共用：feature-development 阶段 2（V1 老工作区）与 problem-analysis 阶段 2（V2 工作区）——都按工单建 feature 分支（problem-analysis 用立项新 Story 工单号），区别只在所在工作区。建分支不可逆，建错仓库/改错 build_product 会污染错误基线。

## 1. 确认项目/分支/工作区

1. **项目**：从 fixVersions、变体字段、description 推断（如 fixVersion 提到 v2xeu 相关版本、描述里写车型）；feature-development 立项时通常已确认；拿不准用 AskUserQuestion 问，不要猜
2. **分支**：默认 develop；单据描述/评论提到特定版本基线（如 V460）时用对应 release 分支；feature-development 的多分支/release 合入规则见 §5
3. **工作区**：按项目定——TDA4 项目 → `01_Workspace_TDA4` 系，J6 项目 → `02_Workspace_J6` 系：
   - feature-development（开发）用老工作区：`01_Workspace_TDA4` / `02_Workspace_J6`
   - problem-analysis（分析）用 V2 工作区：`01_Workspace_TDA4_V2` / `02_Workspace_J6_V2`
   - mcu 仓库随之确定（TDA4 → `mcu_app_tda4`；J6 双仓库见 §3）

## 2. .imobuilder 的 build_product

根据 workspace `config/` 目录查找对应项目名称（如 `ls Y:/01_Src/<工作区>/config/`），修改本地 `.imobuilder` 的 `build_product`（Y: 盘直接改）。已知项目速查：

- TDA4（`Y:\01_Src\01_Workspace_TDA4`）：T1LFL1 → `Chery/T1LFL1_D073/develop`；V2XSEA → `Chery/V2XSEA_D058/develop`
- J6（`Y:\01_Src\02_Workspace_J6`）：T51 → `Gac/T51_D088/develop`；N60 → `BAIC/N60_D109/develop`；J02 → `FAWVW/J02_C097/develop`

⚠️ 速查表仅供参考，**一律 `ls config/` 现查确认**，不凭记忆猜（V2 工作区同理）。

## 3. J6 双仓库规则（2026-09-29 起 J6 工作区有两个 mcu 仓库）

| 仓库 | 项目归属 |
| --- | --- |
| `mcu_app_j6` | 存量项目：T51（GAC）、N60（BAIC）、S52 等旧项目 |
| `mcu_app_j6_v2` | 新项目：J02（FAWVW，preset `cpj_fawvw_j02_d310`）、GWM 新项目（c06g/de09g）、HONDA（h3ata3pda）等 |

- 判断方法：看项目的 cpj 目录在哪个仓库下（如 `src/mcu_app_j6_v2/cpj_fawvw/veh_j02/`）；v2 仓库顶层只有 `cpj_fawvw / cpj_gwm / cpj_honda` 三个 cpj 目录
- ⚠️ 两仓库都有 `cpj_gwm` 目录，不能只按 OEM 判断；GWM 项目要按具体车型确认在哪个仓库
- 拿不准时问用户，不要默认选 `mcu_app_j6`

## 4. SSH 切分支 / 建 feature 分支

git 写操作一律 SSH 在服务器执行（`ssh yaohua@10.0.12.42`，Windows 本地/Y: 盘禁止）。

**reset 前先查残留改动**：`git -c core.filemode=false status --short`——存在未提交改动时不要直接 reset 销毁：

- V2 工作区（problem-analysis）：可能是上一问题单未完成交付的残留修复 → 先问用户如何处理（继续交付/丢弃/暂存）
- 老工作区（feature-development）：先 `git -c core.filemode=false diff -- <files> > /tmp/backup.patch` 备份，切完后 `git apply` 恢复

**切到已有分支**（基线切换，两 skill 通用——如 V2 工作区从上一单的分支回到 develop，或核对依赖仓库当前所在分支）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/<工作区>/src/<mcu仓库>
git reset --hard
git clean -xdf
git checkout <branch_name>
git pull
```

**建 feature 分支**（feature-development 与 problem-analysis 都执行，对本阶段确认的修改仓库逐一执行；problem-analysis 用阶段 1 立项的新 Story 工单号）。分支命名 `feature/<jira工单号>-<标题小写连字符>`（如 `feature/D3ACYI-1271-v2x-series-send-mcu-system-info`）。**问题单的 fixVersions 对应 release 基线时，feature 分支从对应 release 分支创建**（命令同 §5，PR 目标也为该 release 分支）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/<工作区>/src/<仓库>/
git reset --hard
git clean -xdf
git checkout develop
git pull
git fetch origin
git checkout -b feature/<jira工单号>-<标题> origin/develop
git push -u origin feature/<jira工单号>-<标题>
```

**依赖仓库同步**：mcu 产品的构建会组合 workspace 里当前 checkout 的 zos_msg 等依赖仓库代码。切 mcu 仓库分支后**必须把 version_did、zos_msg 等依赖仓库也切到对应分支**（develop↔develop、release↔release），否则接口不匹配类编译错误（案例见 [build.md](build.md)「编译前核对依赖仓库分支」）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/<工作区>/src/version_did
git reset --hard && git clean -xdf && git checkout <branch_name> && git pull
cd ../zos_msg
git reset --hard && git clean -xdf && git checkout <branch_name> && git pull
```

## 5. 多分支与 release 分支规则（feature-development）

- **多分支**：若 develop 和 v460 等两个分支都需要修改，develop 分支先完整执行阶段 2-5，v460 分支再执行一遍；第二个分支的代码修改可直接用 cherry-pick 移植 develop 分支的 commit
- **release/第二分支的 cherry-pick 硬规则**：develop 分支修改完成并**验证 OK**（编译+台架验证通过）后，release 分支（或 T940 等第二目标分支）**直接 cherry-pick develop 分支的 commit 并提交即可，无需在第二分支重新编译验证**（2026-10-21 用户确认；冲突时才需要手工解决）
- **release 分支合入**：需求需同时合入 release 分支（如 `release/Chery/V2XEU_D065/V460`）时，develop 分支的阶段 2-5 完成后，从 **release 分支**基底创建独立 feature 分支：

```bash
git fetch origin
git checkout -b feature/<jira工单号>-<标题>-<release简易分支名> origin/<release分支名>
git push -u origin feature/<jira工单号>-<标题>-<release简易分支名>
```

- release 简易分支名 = release 分支名最后一节小写，如 `release/Chery/V2XEU_D065/V460` → `v460`（例：`feature/D3ACYI-1181-lateral-update-910-v460`）
- 该分支的代码修改可直接 cherry-pick develop 分支的 commit，PR 目标为对应 release 分支
- 注意：develop 分支上的 mcal 符号链接等本地改动可能挡 checkout，按需先 `git checkout -- <文件>` 丢弃

## 6. 代码写入方式（SSH）

**代码修改一律经 SSH 在服务器上写**（Y: 盘禁止写源码：mode 位会被映射破坏 644→755，且本地工具链有 CRLF 风险；git 写操作同 §4）。SSH 密钥认证已配好。可选方式：

1. **scp 推送**（推荐）：文件先写到 D: 本地暂存（或直接 heredoc 生成），再 `scp` 推到服务器对应路径（老工作区 / V2 工作区同理）
2. **SSH heredoc/服务器端编辑**：小改动直接 `ssh yaohua@10.0.12.42 "cat > <服务器路径> <<'EOF' ... EOF"`
3. **autosar 生成产物**（仅 feature-development）：生成目标为 D: 本地（`D:\Workspace\01_Projects\02_Src`），再 `scp -r` 同步到服务器对应仓库路径
