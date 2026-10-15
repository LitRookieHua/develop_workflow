# tests/harness — 测试桩

针对具体问题和工具功能的测试隔离桩：高度解耦、可独立重跑。

## diag_test/ — DiagnosticTester 跑测试用例（第 8 步诊断功能验证）

    cd tests/harness/diag_test
    python run_case.py --testcase case_example.yaml --config ../../tools/DiagnosticTester/configs/<项目>/<配置>.yaml

- 用例写法见 `tools/DiagnosticTester/README.md`（steps/on_fail/timing 三节）
- 新需求验证：在 diag_test/ 或工具 `testcase/<项目>/` 下写用例 yaml，换 `--config` 切项目
- 退出码：0 全 PASS / 1 有 FAIL/TIMEOUT / 2 配置错 / 3 运行期异常

## mcu_log/ — LogCollection 采集 MCU 日志分析

    cd tests/harness/mcu_log
    python collect_mcu_log.py --port <A核串口COM号> --project <项目> [--dry-run]

- 需板子在线（A 核串口 + 板子 SSH 可达）；流程：串口 pfctl -d 使能 SSH → SFTP 拉 /log/mcu
- 日志落盘 `tools/LogCollection/logs/<项目>/mcu_<时间戳>/`
