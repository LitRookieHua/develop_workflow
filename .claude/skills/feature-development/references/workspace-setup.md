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
