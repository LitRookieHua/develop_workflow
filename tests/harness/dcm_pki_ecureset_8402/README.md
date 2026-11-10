# dcm_pki_ecureset_8402：诊断请求黑洞复现与取证工具链

GAC T09-Y PKI 落盘压测中 1101/2E 复位与写请求偶发零响应（诊断请求黑洞，无 pending 无 NRC）。
本 harness 承担：bench 复现（smoke / 完整压测）、CanTp/Dcm 链路插桩取证、BLF 事后分析。

- 问题单：[IDC310GAC-8402](https://jira.imotion.ai:7070/browse/IDC310GAC-8402)（报告人邵庆丽）
- Story：[IDC310GAC-8553](https://jira.imotion.ai:7070/browse/IDC310GAC-8553)
- 阶段：2 根因收敛（机理已收敛到 CanTp 通道级 vs DCM DSL busy 门控两层之一，待 A 核日志区分）

## 目录结构

```
smoke_8402_basic.py        bench 快速循环压测（黑洞命中不中止：观察期探测 + 继续循环）
repro_8402_pki_stress.py   5605 完整复刻压测（KPI 用；SSH 启动 DUT A 核 PKI server）
patch/                     CanTp/Dcm 14 日志点插桩（.patch + 日志点目录 + 判别矩阵）
analysis/                  BLF 取证脚本族（见下）
logs/                      运行产物与取证证据（gitignore，仅本地）
*.blf                      整车原始取证（8.5GB 全量 + 失败窗口抽取，gitignore，仅本地）
```

## 压测运行

```bash
# smoke：每循环 1001→1003→27 解锁→2E9A3E 写 PKI→229a3e 回读→1101 复位→2s→回网
python smoke_8402_basic.py <循环数>

# 完整复刻（需 DUT A 核 SSH 启动 PKI server）
set DUT_SSH_PASSWORD=...           # 或 --ssh-password / 交互输入，脚本不内置口令
python repro_8402_pki_stress.py
```

要点：
- `P2_FAST_MS=1000`：快速路径超时已放宽（1001/1003/27）。早期 50ms 紧 p2 会把 R 核 50-90ms
  正常抖动放大成假失败（历史教训：cycle 649/1709 均为良性时延尖峰）
- 真黑洞判定 = ≥2s 零应答；黑洞命中后 smoke 进入观察期（1001 探测）再继续，不中止录制
- BLF 中客户端 TX 经 transport tap 记录；直发 driver.send 的帧不记录（keepalive 已修）

## 固件与刷写

插桩固件映射见 [patch/README.md](patch/README.md)。刷写（板卡手册见仓库 `.claude/references/flashing.md`）：

```bash
cd tools/ProgramBoard
python ProgramBoard_j6b.py --port <A核串口> --psu-com <电源COM> --config configs/t09_mcu.json \
  --img-dir "Y:/01_Src/02_Workspace_J6_V2/src/mcu_app_j6/build/cpj_gac_t09_d310/rpu_arm_gcc"
```

## A 核日志拉取（插桩输出）

```bash
# DUT A 核：172.16.0.14 root（口令经 DUT_SSH_PASSWORD / 交互输入，不落盘）
grep -E "CTP |DCM " /log/mcu/message
```

黑洞命中后按命中时刻窗口过滤，对照 patch/README.md 判别矩阵定层。
注：2026-11-04 插桩固件 cycle 7 命中时板卡离线未能拉取，现场日志待补。

## 黑洞签名目录（截至 2026-11-10）

| 族 | 签名 | 证据（logs/ 本地） |
| --- | --- | --- |
| 1. 2E pending 后断档 | pending 正常若干个后全总线静默 2.48s（标准复位黑屏 0.38s），恢复后响应链死亡，app 报文存活 | smoke_20261102_174328 cycle 305（~1/305） |
| 2. post-reset 请求吞 | 复位回网后首个请求被吞（bench 39ms / 整车 66.65s 静默窗口后裸 1101），无总线事件，app 存活 | smoke_20261102_210916 cycle 1431；整车 8402 第 895 个 1101（1/895） |
| 3. 2E 楔死 + 全静默吞 | 2E9A3E 后 7F2E78 每 1.015s × 254 个（= MaxNumRespPend 255）→ 7F2E10 终态；期间所有并发 1001 零响应（连 NRC 0x21 都无）；3E80 无断档；R 核 DCM 定时器与 TX 全程活着 | smoke_20261104_144814 cycle 7（插桩固件首跑命中） |
| 良性 | 时延尖峰 50-90ms，ECU 迟到应答在 BLF 中可见，自愈 | smoke_20261103_002521 cycle 649/1709 |

## 命中后取证流程

1. BLF 时间线：`python analysis/hit_tail.py`（尾部窗口 + FD 感知解码）、`analysis/hit_pending_stats.py`（pending 计数/节拍/wedge 窗口请求配对）
2. 判族：对照上表签名（pending 节拍断档？终态 NRC？并发请求有无应答？3E80/周期报文断档？）
3. A 核日志：拉 `/log/mcu/message` 按命中窗口 grep `CTP |DCM `，用判别矩阵定层
4. 若为族 3：重点查 IpcDiagSvc GET_REQUEST_STATE 为何持续 BUSY（5s IPC 超时未触发 → Tick 上下文或 A 核持续回 BUSY）

## 整车取证脚本（analysis/）

- `scan2_diag.py`：8.5GB BLF 流式扫描，全 0x7xx 帧统计 + 诊断帧时间线导出
- `count_1101.py`：1101 完整结局分布统计（895 个 = 894 OK + 1 零响应）
- `dut_ids.py` / `dut_reset_check.py`：提取 DUT 周期 app ID 集 → 整车 BLF 验证复位是否执行（黑屏同步检查）
- `extract_failwin.py` / `failwin_diag_timeline.py`：失败窗口 BLF 抽取 + 诊断时间线还原
- 脚本内路径为当时取证硬编码（.tmp/ 中间产物），复用时按需改路径
