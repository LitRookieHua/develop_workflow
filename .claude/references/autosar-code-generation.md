# AUTOSAR 代码生成规格（autosar-code-generation）

> 权威源：本文档是 AUTOSAR 生成代码人工修改规则的唯一权威源。CLAUDE.md 与其他文档只指向这里；规则更新时改本文档，不改指向处。

## 1. AUTOSAR patch 标记规则

**任何对 AUTOSAR 生成代码（`cpj_*/autosar/` 下源码）的人工修改，必须在改动前后加 patch 标记**——否则下次生成 autosar 代码会直接覆盖丢失人工提交。

### 1.1 标记格式

```c
/* <{项目名}PATCH P{id}> */
<修改的代码行>
/* </{项目名}PATCH P{id}> */
```

- `{项目名}`：该文件所属 autosar 项目子目录名**大写**（如 `t68` → `T68`，`s52-e046` → `S52-E046`，连字符保留）
- `{id}`：本文件内 patch 编号；新 patch 取文件中已有最大编号 +1，从 `P1` 起
- 多行改动共用一对标记（包裹整段改动，不逐行标记）；同一文件多处独立改动用不同 id

### 1.2 示例

`t68` 项目的 `PduR_Gateway_TpDcmTx.c` 首个 patch（IDC310GAC-7835）：

```c
/* <T68PATCH P1> */
TpSduLength = (info != NULL_PTR) ? info->SduLength : SessionPtr->SduLength_auo[SessionPtr->Rx_FifoInstanceUsed_u8];
/* </T68PATCH P1> */
```

### 1.3 打 patch 前的检查

1. 先 grep 该文件已有的 PATCH 标记（`grep -n 'PATCH P' <file>`），确定下一个 id
2. 确认改动行未被既有 patch 包裹（避免嵌套/重叠）

### 1.4 代码生成后的 patch 重放

回归生成 autosar 代码后，按标记检索并人工重放：

```bash
grep -rn '<T68PATCH P' cpj_gac/autosar/t68/
grep -rn '<S52E046PATCH P' cpj_gac/autosar/s52-e046/
```

生成工具覆盖文件后，被覆盖丢失的 patch 需按标记逐条对照重打（先例：分析报告 `docs/analysis/` 与 Story 笔记中记录的 patch 内容）。

## 2. 路径

### （1）10.0.13.10服务器

- **账号**：`cp`
- **mcu 代码路径**：
  - mcu_app_tda4：`D:\Workspace\01_Projects\02_Src\01_Workspace_TDA4\src\mcu_app_tda4`（DaVinci/Vector；跑时需 CodeMeter license，见 Dem_AutoGen_Davinci 流程）
  - mcu_app_j6 / mcu_app_j6_v2：`D:\Workspace\01_Projects\02_Src\02_Workspace_J6\src\`（ETAS）
- **工具路径**：`D:\Workspace\01_Projects\02_Src\11_AI\develop_workflow\tools\autosar_gen\`
- **工具链**：ETAS RTA-CAR 12.7.0 在 `C:\ETAS\RTA-CAR_12.7.0`；usbclncmd（license 客户端）在 `C:\Program Files\USB over Network\`

### （2）本地（备用）

- **mcu 代码路径**（与服务器同构）：
  - mcu_app_tda4：`D:\Workspace\01_Projects\02_Src\01_Workspace_TDA4\src\mcu_app_tda4`
  - mcu_app_j6 / mcu_app_j6_v2：`D:\Workspace\01_Projects\02_Src\02_Workspace_J6\src\`
- **工具路径**：`D:\Workspace\01_Projects\02_Src\11_AI\develop_workflow\tools\autosar_gen\`
- **工具链**：ETAS RTA-CAR 12.7.0 在 `D:\ETAS\RTA-CAR_12.7.0`；usbclncmd 在 `D:\Program Files\USB over Network\`；DVCfgCmd（DaVinci）在 repo 内 `microsar_tools_tda4\DaVinciConfigurator\Core\DVCfgCmd.exe`（随 submodule，两台机器相同）；ISOLAR 启动器 `<RTA-CAR>\ISOLAR-AB_12.7.0\ISOLAR-AB.cmd`（由 RTA-CAR 根自动发现）
- **坑**：fresh clone 的 mcu_app_tda4 缺 `ComponentLicense_DaVinciConfigurator.lic`（不进 git，需人工部署）

## 3. 流程

服务器分工（10.0.28.98 已弃用）：

| 服务器 | 账号 | 角色 |
| --- | --- | --- |
| 10.0.13.10 | cp | **ETAS/J6 + DaVinci/TDA4 autosar 代码生成**（双平台） |
| 10.0.12.42 | yaohua | **编译** + git commit（`/comp/user_data/yaohua/01_Src`） |

修改 autosar 生成代码的标准流程：

1. `ssh cp@10.0.13.10`，在 10.0.13.10服务器的 mcu 仓库切到相应分支后运行 autosar_gen 工具生成
2. 生成的改动文件从 10.0.13.10服务器 `scp` 推送到 10.0.12.42 对应仓库路径
3. 在 12.42 上编译验证
4. 编译通过后在 12.42 上提交 commit（格式见 git-rules.md）

**工具入口（2026-10-30 定规）**：一律使用 autosar_gen 对应工具的**主 python 文件**，不要直接调子工具（漏 map 表等步骤）、不要用仓库内遗留 bat（如 `cpj_*/tools/<变体>/e2e_dem/gen_e2e_dem.bat`——只跑 4 个 python 脚本，无 ISOLAR BSW 代码生成，产物不完整；RX V3.0 导入实际踩坑）。三个主入口：

| 工具 | 主入口 | 用法 | 说明 |
| --- | --- | --- | --- |
| Dem | `tools\autosar_gen\Dem_AutoGen\Dem_AutoGen.py` | `python Dem_AutoGen.py --repo <mcu仓库> --config <变体>` | 自动判型（ETAS J6 / Davinci TDA4）转发子工具 + 统一跑 gen_map_yaml（dtc/event/fimfid map，输出到 Excel 同目录） |
| Dcm | `tools\autosar_gen\Dcm_AutoGen\Dcm_AutoGen.py` | `python Dcm_AutoGen.py --repo <mcu_app_j6路径> --config <变体> [--excel <UDS问卷xlsx>] [--json <version_did JSON>]` | J6 ETAS 专用：gen_dcm_arxml → gen_nrc_code → gen_did_code（DID 查找表/0x22/0x2E handler + version_did JSON）→ gen_rid_code → ISOLAR BSW 生成；Excel/JSON 缺省自动发现 |
| Nvm | `tools\autosar_gen\Nvm_AutoGen\Nvm_AutoGen.py` | `python Nvm_AutoGen.py --repo <mcu仓库> --config <变体> [子工具参数]` | 自动判型（同 Dem），参数原样转发子工具 |

代码为探测式 D:→C:，两台机器零配置通用，`RTA_CAR_HOME` 环境变量仍可显式覆盖。

历史：2026-10-30 前生成本地 D: 完成后 scp 推服务器；10.0.28.98 曾作为 DaVinci 生成服务器，现已弃用。

## 4. 变更记录

| 日期 | 变更 | 来源 |
| --- | --- | --- |
| 2026-10-20 | 初版：patch 标记规则从 CLAUDE.md 迁入并扩充（检查/重放流程） | IDC310GAC-7835 交付（用户定规） |
| 2026-10-30 | 生成迁移 10.0.13.10服务器（双平台），28.98 弃用；标准流程改为 10.0.13.10服务器生成 → scp 12.42 → 编译 → 12.42 提交；路径章节重构为「服务器 + 本地备用」 | 用户定规（远程生成体系落地） |
| 2026-10-30 | 定规工具入口：autosar 生成一律用各 AutoGen 主 python 入口（含 map 表），禁用仓库遗留 bat / 直接调子工具 | 用户定规（RX V3.0 导入踩坑：bat 无 ISOLAR 生成） |
