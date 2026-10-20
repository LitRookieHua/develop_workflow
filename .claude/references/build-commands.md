# build-commands：编译命令手册

SSH 在服务器上执行（编译全部在服务器，Y: 盘禁止任何 git/写操作，见 CLAUDE.md 安全红线）。

## 标准命令

**TDA4 工作区**（老工作区 `01_Workspace_TDA4` / V2 `01_Workspace_TDA4_V2` 同式）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/<01_Workspace_TDA4|01_Workspace_TDA4_V2>/
imobuilder clean mcu_app_tda4 -r
imobuilder build mcu_app_tda4 -r
```

**J6 工作区**（老工作区 `02_Workspace_J6` / V2 `02_Workspace_J6_V2` 同式；`<mcu_app_j6|mcu_app_j6_v2>` 按 J6 双仓库规则选定，见 [workspace-setup.md](workspace-setup.md)）：

```bash
ssh yaohua@10.0.12.42
cd /comp/user_data/yaohua/01_Src/<02_Workspace_J6|02_Workspace_J6_V2>/
imobuilder clean <mcu_app_j6|mcu_app_j6_v2> -r -x parking_dr uper_app
imobuilder build <mcu_app_j6|mcu_app_j6_v2> -r -x parking_dr uper_app
```

## 关键规则

- **J6 的 `-x parking_dr uper_app` 必须带**：这两个包的远端仓库 `ip/parking_dr`、`ip/uper_app` 已不存在，不带会 clone 失败（v2 仓库同样带，2026-09-29 用户确认）
- 编译耗时较长（可后台运行），但**不要接 `| grep` 管道**（会掩盖真实退出码）
- **编译前核对依赖仓库分支**：mcu 构建组合 workspace 当前 checkout 的 zos_msg 等依赖仓库代码，切 mcu 分支后必须同步切依赖仓库分支（develop↔develop、release↔release），否则接口不匹配类编译错误
- 编译失败排障 → [build-troubleshooting.md](build-troubleshooting.md)（J6 clean 末步失败属正常、固件排障、CI remote_build 轮询）
- 远端固件刷新（parking_dr / uper_app / MCU21）→ 同样见 build-troubleshooting.md 第 4 节
