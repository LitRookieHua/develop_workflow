# tests/harness — 测试桩

针对具体问题和工具功能的测试隔离桩：高度解耦、可独立重跑。

## 目录组织规范

- **通用测试手段**：`diag_test/`（DiagnosticTester 跑用例）和 `mcu_log/`（MCU 日志采集）两个通用目录，只放与具体问题无关的通用工具/示例。
- **问题专属 harness**：针对具体问题新建 `<模块名>_<harness描述>/` 目录（如 `dcm_sec_relock_1003`、`dcm_did_f190`）：
  - 根目录放 python 脚本（setup / execute / verify / teardown，越轻量越解耦越好）
  - `testcases/` 放测试用例（yaml 等）
  - `logs/` 放运行产物（run.log、trace.blf、串口采集等），问题取证证据也归档在这里；DiagnosticTester `run` 的产物自动落 `logs/<用例名>/<时间戳>/`（2026-10-28 起默认）

## diag_test/ — DiagnosticTester 跑测试用例（第 8 步诊断功能验证）

    cd tests/harness/diag_test
    python run_case.py --testcase case_example.yaml --config ../../tools/DiagnosticTester/configs/<项目>/<配置>.yaml

- 用例写法见 `tools/DiagnosticTester/README.md`（steps/on_fail/timing 三节）
- 新需求验证：在 diag_test/ 或工具 `testcase/<项目>/` 下写用例 yaml，换 `--config` 切项目
- 退出码：0 全 PASS / 1 有 FAIL/TIMEOUT / 2 配置错 / 3 运行期异常

## mcu_log/ — MCU 日志采集

    cd tests/harness/mcu_log
    python collect_mcu_log.py --port <A核串口COM号> --project <项目> [--dry-run]   # LogCollection：SFTP 拉 /log/mcu
    python capture_com68.py [baud=115200]                                          # COM68 调试串口实时采集（插桩日志）

- collect_mcu_log 需板子在线（A 核串口 + 板子 SSH 可达）；流程：串口 pfctl -d 使能 SSH → SFTP 拉 /log/mcu，落盘 `tools/LogCollection/logs/<项目>/mcu_<时间戳>/`
- capture_com68 落盘 `mcu_log/logs/com68_capture.log`，Ctrl-C 停止；配套 ECU 插桩（如 `uart_mcu10_printf_v`）做问题取证
- **A 核/R 核串口 COM 号按规则现查（COM 号会漂移）**：规则权威源 `.claude/references/serial-port-identification.md`

## dcm_sec_relock_1003/ — D3ACYI-1832：10 03 会话重入安全重锁压测（V2XEU）

    cd tests/harness/dcm_sec_relock_1003
    python stress_relock_after_1003_reentry.py [rounds=20] [keepalive_period_ms=150]

- 并发压测复现：后台线程 0x7DF 功能寻址 3E 80（间隔 45/90/180/300ms 轮转）+ 主线程 10 03 / 27 序列；判定重入后 27 01 返回零种子 / NRC 0x24 即 bug 复现
- `testcases/` 存放早期顺序负载用例（case_d3acyi1832_*.yaml，经 diag_test/run_case.py 跑）；`logs/` 存放压测产物（run.log + trace.blf）与插桩证据（com68_capture_20261016_evidence.log）
- 根因与修复结论见 Obsidian 笔记《V2xeu Fix Lock State Reset on 1003 Switch》
