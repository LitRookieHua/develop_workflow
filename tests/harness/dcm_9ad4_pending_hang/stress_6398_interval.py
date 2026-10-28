"""IDC310GAC-6398（T51）复现压测：61s 间隔仅发 3101，不发 3103。

原始复现步骤（customfield_12007 原样）：
  以61s的时间间隔连续触发标定（只进行3101请求，不进行3103请求），
  第83次3101请求只回复一个NRC78后不再响应（概率 1-376）

判定：每条 3101 必须在 P2* 窗口内拿到最终响应（正响应或明确 NRC）；
swallow（完全无响应）/ hang（NRC78 后无最终响应）= 缺陷复现。
NRC22（许可冷却）为预期负响应；3101 被再次接受会启动新一轮标定，属正常。

当前环境适配（预检实测：标定失败终态后 SoC 不回 PERMIT）：
- 原环境 61s 间隔刚好覆盖 28s 标定 + ~30s 许可冷却，每条 3101 都被接受；
  当前环境许可不复原，故 NRC22 后 1101 复位恢复开机许可再继续计数
  （每次复位后的首条 3101 即缺陷竞态窗口的采样点）

忠实模式（2026-10-23 对齐原始命中 BLF 实测形态，.tmp/blf/6398_83.blf）：
- 每轮重新认证：1003（重进会话=安全重锁）→ 2701/2702（再解锁）→ 2.4s → 3101
  （原始：2702-OK 后 2.45s 发 3101；此交互面与"每轮只发 3101"不同，
   之前 311 次采样均未覆盖）
- 保活 3E80 @ 0.9s（原始实测周期），此前为 2s
- 3101 间隔仍锚定 61s

用法：
  python stress_6398_interval.py [--count 100] [--interval 61]
                                  [--hold-minutes 10] [--config <t68_cx.yaml>]

输出：logs/stress6398_<时间戳>/；复现时保持现场供 TRACE32 附加。
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from common import (TOOLS, Keepalive, REQ_3101, REPRO_KINDS,
                    classify, fmt, hold_for_t32, open_session)

from DiagnosticTester import build_transport, make_driver  # noqa: E402
from flow import load_config  # noqa: E402
from recorder import Recorder  # noqa: E402
from uds import UdsClient  # noqa: E402

P2STAR_MS = 2000
RETRY_AFTER_TIMEOUT = 3
KEEPALIVE_MS = 900        # 原始 BLF：3E80 @ ~0.90s
GAP_AFTER_UNLOCK_S = 2.4  # 原始 BLF：2702-OK → 3101 = 2.45s


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--interval", type=float, default=61.0)
    ap.add_argument("--hold-minutes", type=float, default=10.0)
    ap.add_argument("--config", default=str(TOOLS / "configs" / "t68" / "t68_cx.yaml"))
    args = ap.parse_args()

    cfg = load_config(args.config)
    level = cfg["security_levels"]["app"]
    diag = cfg["diagnostic"]
    fd = cfg["can"]["fd"]

    run_dir = Path(__file__).parent / "logs" / f"stress6398_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True)
    print(f"运行目录：{run_dir}")
    print(f"count={args.count} interval={args.interval}s "
          f"（预计总时长 {args.count * args.interval / 60:.0f} 分钟）")

    driver = make_driver(cfg)
    repro = []
    stats = {}
    try:
        with Recorder(run_dir) as rec:
            transport = build_transport(cfg, driver, rec)
            try:
                uds = UdsClient(transport, p2_ms=cfg["timing"]["p2_ms"],
                                p2star_ms=P2STAR_MS, log=rec.event)

                def log(msg):
                    rec.event(msg)
                    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

                ka = Keepalive(driver, rec, diag["functional_id"], fd,
                               period_ms=KEEPALIVE_MS)
                ka.start()

                if not open_session(uds, level, log):
                    return 2

                for i in range(1, args.count + 1):
                    # 忠实模式：每轮 1003 重进（安全重锁）→ 2701/2702 再解锁
                    # → 2.4s → 3101（原始 6398 命中 BLF 的逐轮形态）
                    if not open_session(uds, level, log, allow_unlocked=True):
                        return 2
                    time.sleep(GAP_AFTER_UNLOCK_S)

                    t0 = time.monotonic()
                    r = uds.request(REQ_3101)
                    kind, text = classify(r)
                    stats[kind] = stats.get(kind, 0) + 1

                    if kind in REPRO_KINDS:
                        log(f"[{i}] !!! 3101 -> {kind}: {text}")
                        confirmed = kind
                        for _ in range(RETRY_AFTER_TIMEOUT):
                            time.sleep(1.0)
                            r = uds.request(REQ_3101)
                            kind, text = classify(r)
                            log(f"[{i}] 3101 重试 -> {kind}: {text}")
                            if kind in REPRO_KINDS:
                                confirmed = kind
                            else:
                                confirmed = None
                                stats[kind] = stats.get(kind, 0) + 1
                                break
                        if confirmed:
                            repro.append((i, confirmed))
                            break
                        continue
                    if kind == "accepted":
                        log(f"[{i}] 3101 接受（新一轮标定启动）：{text}")
                        remain = args.interval - (time.monotonic() - t0)
                        if remain > 0:
                            time.sleep(remain)
                        continue

                    # NRC22（或其他 NRC）：当前环境许可不复原 → 1101 复位
                    # 恢复开机许可；复位后首条 3101 即下一采样点
                    log(f"[{i}] 3101 -> {kind}: {text}，1101 复位恢复许可")
                    r = uds.request(b"\x11\x01")
                    log(f"[{i}] 1101 -> {fmt(r)}")
                    if not open_session(uds, level, log):
                        return 2
                    stats["resets"] = stats.get("resets", 0) + 1

                if repro:
                    hold_for_t32(ka, log, args.hold_minutes)
                ka.stop()
            finally:
                transport.stop()
    finally:
        driver.close()

    print("\n========== 压测汇总 ==========")
    print(f"响应分布: {stats}")
    print(f"缺陷复现: {len(repro)}  {repro}")
    print(f"日志：{run_dir}（trace.blf 可喂 UdsLogAnalyzer 复核）")
    return 1 if repro else 0


if __name__ == "__main__":
    sys.exit(main())
