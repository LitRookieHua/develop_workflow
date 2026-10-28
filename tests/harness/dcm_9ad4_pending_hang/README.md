# dcm_9ad4_pending_hang — IDC310GAC-7994 复现与回归 harness

EOL 标定（9AD4）压测中 0x31 例程控制两缺陷的 bench 复现与 A/B 回归：

- **swallow（请求被吞）**：3101 发出后 ECU 完全无响应（6659 第 8 轮，5.1s 静默）
- **hang（PENDING 挂死）**：3101 收到 `7F3178` 后无最终响应（6398 第 83 次，11s 无下文）

问题单：IDC310GAC-6659（主验证，T68）/ 4796 / 5999 / 6398（四单同源）。
Story：IDC310GAC-7994。分析结论与根因见 `docs/analysis/`（立项分析报告）。

## 判定口径

| 响应 | 判定 | 说明 |
| --- | --- | --- |
| `71 01 9AD4`（~1s 早期正响应） | PASS | 9AD4=START+RESULTS 掩码（0x05），接受即正响应，例程后台跑 |
| `7F 31 22`（NRC22） | PASS | SoC 许可冷却窗口的设计内负响应（BLF 实测 ~30s） |
| 3103 结果 error/timeout | 不判 | **当前环境标定失败属预期**，判定只看 3101 生命周期 |
| 完全无响应（P2 超时） | **FAIL** | swallow 复现 |
| `7F3178` 后 P2*(2s) 内无最终响应，重试 3 次仍无 | **FAIL** | hang 复现 |

## 环境前提

- GAC T68 板 + SoC（**须是对应项目的环境**——SoC 参与许可窗口/标定状态机交互）
- CX-USBCANFD 卡，通道 0（`t68_cx.yaml`）
- 基线固件：V2 工作区 `feature/IDC310GAC-7994-routine-pending-hang` 分支编译输出
  （`src/mcu_app_j6/build/cpj_gac_t68_d310/rpu_arm_gcc`；TRACE32 ELF 用
  `output/armv8-r-generic-gcc-r52/release/target/bin/int_rpu_arm8r5_arm_gnu.elf`）

## 用例与运行顺序

```bash
cd tests/harness/dcm_9ad4_pending_hang

# 1. 环境预检（板子到位后第一个跑，~3 分钟）
#    回答：失败模式时序（快速失败 vs 28s 超时）、失败后 SoC 是否回 PERMIT
python precheck_env.py

# 2. 6659 场景压测：10 次标定→1101→等 61s 一轮（默认 8 轮，~1.5h）
python stress_6659_rounds.py --rounds 8

# 3. 6398 场景压测：61s 间隔仅 3101（默认 100 次，~1.7h；BLF 命中在第 83 次）
python stress_6398_interval.py --count 100

# 冒烟（DiagnosticTester run 命令直接跑，快速验证环境+解锁配置）
python ../../../tools/DiagnosticTester/DiagnosticTester.py run \
  testcases/smoke_9ad4_start_t68.yaml --config ../../../tools/DiagnosticTester/configs/t68/t68_cx.yaml
```

两个压测脚本默认参数对齐 BLF 实测节奏（3101 storm 间隔 20ms、3103 密集轮询
10ms、P2*=2s、3E80 保活 2s）。复现时脚本自动停发请求、保持 3E80 保活现场
10 分钟，供 TRACE32 附加取证（`--hold-minutes` 可调）。

## 当前环境适配（预检实测 2026-10-22）

当前台架标定失败（status=0x03，27.6s ≈ 28s EOL 超时）且 SoC 失败后不回
CALI_MSG_PERMIT（NRC22 锤击 180s 许可不复原）。两个脚本已适配：

- 6659：每轮实际形态 = 1 次标定 → 终态后 60s 风暴窗口无接受 → 1101 复位
  （复位恢复开机许可）→ 61s 等待 → 下一轮；SoC 许可恢复正常的环境下
  同一脚本自动变回连续多次标定
- 6398：NRC22 即 1101 复位 + 重解锁后继续计数（复位后首条 3101 即采样点）

## TRACE32 取证（复现现场）

复现停住后 attach（ELF 见上），重点变量：

- 0x31 服务状态 `m_serviceProcessingState_e`（预期卡 `E_DIA_SM_RUNNING`）
- 9AD4 例程 `m_diaSMCurrentState_e` / `m_cyclicFeedbackRoutineState_e`
- `ov_dia_calibration`：`m_calibStep` / `m_calibPermetFlag`
- DCM DSL 层：挂死请求的 Tx 确认状态（swallow 场景）

## 离线复核（UdsLogAnalyzer 闭环）

每次运行的 `logs/<run>/trace.blf` 用分析器复核（判定口径同上）：

```bash
python tools/UdsLogAnalyzer/uds_log_analyzer.py \
  tests/harness/dcm_9ad4_pending_hang/logs/<run>/trace.blf --ignore-nrc 22
```

检出「请求无响应」或「NRC78 PENDING 挂死」即与脚本在线判定互证。

## 已知简化

- 6659 的 S3 会话回落连锁后果不复现（脚本全程 3E80 保活）——它是缺陷后果
  而非缺陷本身，保活能让现场保持更久便于取证
