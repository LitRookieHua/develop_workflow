# flashing：J6 刷写手册（ProgramBoard）

Windows 本地执行（串口/电源 COM 口都在本机，不走 SSH）。用 `tools/ProgramBoard/` 一键刷写工具（`ProgramBoard_j6b.py`）把编译产物刷到板子。

## 命令

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/ProgramBoard
python ProgramBoard_j6b.py --port <A核串口> --psu-com <电源COM> --config configs/<项目>.json --img-dir <编译输出>/rpu_arm_gcc
```

- `--img-dir` 语义：工作区（老工作区或 V2）编译输出的 `build/<preset>/rpu_arm_gcc` 目录，如：
  - 老工作区 J6：`Y:/01_Src/02_Workspace_J6/src/<仓库>/build/<preset>/rpu_arm_gcc`
  - V2 工作区 J6：`Y:/01_Src/02_Workspace_J6_V2/src/<仓库>/build/<preset>/rpu_arm_gcc`
- 示例：N60（旧仓库）`--config configs/n60_mcu.json --img-dir Y:/01_Src/02_Workspace_J6/src/mcu_app_j6/build/cpj_baic_n60_d310/rpu_arm_gcc`；J02（v2 仓库）`--config configs/j02_mcu.json --img-dir Y:/01_Src/02_Workspace_J6/src/mcu_app_j6_v2/build/cpj_fawvw_j02_d310/rpu_arm_gcc`（镜像文件 `int_rpu_arm8r5_arm_j02_gnu.img`）

## 关键规则

- ⚠️ **`--img-dir` 必须显式传**：工具已从 `Y:\01_Src\tools\flash`（已删除）迁至 D 盘，脚本内置默认镜像路径指向 D 盘本地副本（无 build 产物），不传会找不到镜像；一律指向 Y: 盘上对应工作区的编译输出
- A 核/R 核串口识别——**规则权威源 [serial-port-identification.md](serial-port-identification.md)**（J6/TDA4 判定规则 + 现场快查步骤 + 实测映射表）。COM 号随 USB 重枚举漂移，换板后必须按权威源重新判定
- 电源口（KA3005P）用 `tools/PowerControl` 的 `power_control.py --port <COM> id` 应答确认（独立于板卡串口）；电源未接时省略 `--psu-com`（失败时提示人工断电）
- 全自动流程（约 35 秒/次）：断电冷启动 → 20ms 周期发空格打断 uboot → `fastboot udp` → `flash MCU_a`/`MCU_b` → `fastboot reboot`；任一步失败自动断电重来（默认重试 3 次），退出码 0 成功 / 1 失败
- 刷写前无需另行电源 `cycle`（断电冷启动已由工具内置完成）；验证方法与电源配套见 [validation-methods.md](validation-methods.md)
- 前提：板子 A 核串口 + 网线（与 PC 同网段）已接，供电走 KA3005P 输出（12V）
- 失败排查看 `logs/flash_*.log`（`[SER]` 前缀为串口原始数据）；换新板/新 uboot 版本先跑 `--dry-run` 校准，参数与板子特性详见目录下 `README.md`
- TDA4 工作区（含 V2）暂无自动刷写工具，跳过刷写直接进入手动验证
