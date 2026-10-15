"""MCU 日志采集桩：转发 tools/LogCollection/collect_j6b.py（需板子 A 核串口 + 板子在线）。

用法：
  python collect_mcu_log.py --port COM30 --project Rx            # 采集 /log/mcu
  python collect_mcu_log.py --port COM30 --project Rx --dry-run  # 仅列文件清单不下载

日志落盘：tools/LogCollection/logs/<项目>/mcu_<时间戳>/。
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LC = ROOT / "tools" / "LogCollection" / "collect_j6b.py"


def main():
    ap = argparse.ArgumentParser(description="LogCollection 采集转发桩")
    ap.add_argument("--port", required=True, help="板子 A 核串口 COM 号")
    ap.add_argument("--project", required=True, help="项目名（日志保存到 logs/<项目>/）")
    ap.add_argument("--dry-run", action="store_true", help="仅列文件清单")
    args, extra = ap.parse_known_args()
    cmd = [sys.executable, str(LC), "--port", args.port, "--project", args.project]
    if args.dry_run:
        cmd.append("--dry-run")
    cmd += extra
    print(f"[mcu_log] {' '.join(str(c) for c in cmd)}")
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
