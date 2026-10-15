"""诊断测试桩：转发 tools/DiagnosticTester 跑指定测试用例（第 8 步诊断功能验证用）。

用法（真板在线）：
  python run_case.py --testcase case_example.yaml --config <DT目录>/configs/rx/rx_cx.yaml
  python run_case.py --testcase <用例.yaml> --config <配置.yaml> [DiagnosticTester 额外参数透传]

退出码透传 DiagnosticTester（0 全 PASS / 1 有 FAIL / 2 配置错 / 3 运行期异常）。
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DT = ROOT / "tools" / "DiagnosticTester" / "DiagnosticTester.py"


def main():
    ap = argparse.ArgumentParser(description="DiagnosticTester 用例转发桩")
    ap.add_argument("--testcase", required=True, help="测试用例 yaml 路径")
    ap.add_argument("--config", required=True, help="项目配置 yaml 路径")
    args, extra = ap.parse_known_args()
    cmd = [sys.executable, str(DT), "run", args.testcase, "--config", args.config, *extra]
    print(f"[diag_test] {' '.join(str(c) for c in cmd)}")
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
