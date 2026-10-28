"""IDC310GAC-6659（T68）复现压测：连续 10 次标定 → 1101 复位 → 等 61s 为一轮。

原始复现步骤（customfield_12007 原样翻译）：
  进行压测（连续10次EOL标定(9AD4)，1101复位，等待61s）；标定中发送3101

BLF 实测节奏对齐（2026-10-23 修正，对齐原始 6659 BLF 实测）：
- 冷却窗口期间 3101 以 ~1s 间隔重发（原始实测 NRC22 重试间隔 ~1s；
  此前 20ms 风暴与原始节奏不符）
- 每条 3101 由 UdsClient 在 P2*(2s) 窗口内等最终响应
- 标定启动后 3103 密集轮询（20ms，原始实测 ~20-25ms）至终态
- 默认不发 3E80 保活（原始 6659 无保活帧，密集请求自身维持 S3）
- NRC22 = 预期负响应，不算失败
- 判定只看 swallow（无响应被吞）/ hang（NRC78 后无最终响应）

当前环境适配（预检实测：标定失败 27.6s 终态后 SoC 不回 PERMIT）：
- 每轮实际形态 = 1 次标定 → 终态后 3101 重试窗口（60s）无接受 → 1101
  复位恢复开机许可 → 下一轮；SoC 许可恢复正常的环境下同一脚本自动
  变为连续多次标定（窗口内接受即起下一轮标定），无需改参数

用法：
  python stress_6659_rounds.py [--rounds 8] [--calibs 10] [--storm-gap-ms 1000]
                                [--hold-minutes 10] [--keepalive]
                                [--config <t68_cx.yaml>]

输出：logs/stress6659_<时间戳>/；复现时保持现场供 TRACE32 附加。
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from common import (TOOLS, Keepalive, REQ_3101, REQ_3103, REPRO_KINDS,
                    classify, fmt, hold_for_t32, open_session)

from DiagnosticTester import build_transport, make_driver  # noqa: E402
from flow import load_config  # noqa: E402
from recorder import Recorder  # noqa: E402
from uds import UdsClient  # noqa: E402

P2STAR_MS = 2000    # ECU 实测 P2*（DCM_CFG_DEFAULT_P2STARMAX_TIME 2s）
POLL_INTERVAL_S = 0.02  # 原始 6659 BLF：3103 轮询 ~20-25ms
POLL_CAP_S = 40.0
RUNNING_LOG_INTERVAL_S = 5.0
STORM_CAP_S = 60.0
RETRY_AFTER_TIMEOUT = 3   # 超时后补发次数（3×~2s ≈ 6s 无最终响应 = 复现）


def start_calibration(uds, log, storm_gap_s):
    """发 3101 直至被接受；返回 (state, kind)，state: ok/repro/giveup。"""
    n22 = 0
    t0 = time.monotonic()
    while True:
        r = uds.request(REQ_3101)
        kind, text = classify(r)
        if kind == "nrc22":
            n22 += 1
            if n22 % 10 == 0:
                log(f"3101 NRC22 ×{n22}（{time.monotonic()-t0:.0f}s）")
            if time.monotonic() - t0 > STORM_CAP_S:
                log(f"!!! 冷却窗口超 {STORM_CAP_S}s（环境异常，放弃本轮）")
                return "giveup", kind
            time.sleep(storm_gap_s)
            continue
        if kind in REPRO_KINDS:
            log(f"!!! 3101 -> {kind}: {text}")
            for _ in range(RETRY_AFTER_TIMEOUT):
                time.sleep(1.0)
                r = uds.request(REQ_3101)
                kind, text = classify(r)
                log(f"3101 重试 -> {kind}: {text}")
                if kind not in REPRO_KINDS:
                    break
            if kind in REPRO_KINDS:
                return "repro", kind
            if kind == "accepted":
                log(f"3101 重试后接受：{text}")
                return "ok", kind
            continue
        if kind == "accepted":
            log(f"3101 接受：{text}" + (f"（前置 NRC22 ×{n22}，窗口 {time.monotonic()-t0:.1f}s）" if n22 else ""))
            return "ok", kind
        log(f"3101 -> {kind}: {text}（1s 后重试）")
        time.sleep(1.0)


def wait_calibration_end(uds, log):
    """3103 密集轮询至终态（10ms，对齐 BLF 轮询节奏）。

    单次超时先确认（1s×3）再判挂死——密集轮询下偶发慢响应不应误报；
    3 次确认仍无响应 = swallow/hang 复现。
    """
    t0 = time.monotonic()
    n_polls = 0
    timeouts = 0
    last_log = t0
    while True:
        elapsed = time.monotonic() - t0
        if elapsed > POLL_CAP_S:
            log(f"!!! 3103 超 {POLL_CAP_S}s 仍非终态（环境异常）")
            return "giveup", None
        r = uds.request(REQ_3103)
        n_polls += 1
        kind, text = classify(r)
        if kind in REPRO_KINDS:
            timeouts += 1
            log(f"!!! 3103 -> {kind}: {text}（确认中 {timeouts}/{RETRY_AFTER_TIMEOUT}）")
            if timeouts >= RETRY_AFTER_TIMEOUT:
                return "repro", kind
            time.sleep(1.0)
            continue
        timeouts = 0
        if r.ok and r.response[:3] == b"\x71\x03\x9a" and len(r.response) > 4:
            status = r.response[4]
            if status != 0x01:
                log(f"标定终态 status=0x{status:02X}（时长 {time.monotonic()-t0:.1f}s，轮询 {n_polls} 次）")
                return "ok", status
            if time.monotonic() - last_log >= RUNNING_LOG_INTERVAL_S:
                last_log = time.monotonic()
                log(f"3103 Running（{elapsed:.0f}s，已轮询 {n_polls}）")
            time.sleep(POLL_INTERVAL_S)
            continue
        log(f"3103 -> {kind}: {text}（{elapsed:.0f}s）")
        if r.nrc is not None:
            return "giveup", None
        time.sleep(POLL_INTERVAL_S)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--calibs", type=int, default=10)
    ap.add_argument("--storm-gap-ms", type=float, default=1000.0)
    ap.add_argument("--keepalive", action="store_true",
                    help="发 3E80 保活（原始 6659 无保活帧，默认不发）")
    ap.add_argument("--hold-minutes", type=float, default=10.0)
    ap.add_argument("--config", default=str(TOOLS / "configs" / "t68" / "t68_cx.yaml"))
    args = ap.parse_args()

    cfg = load_config(args.config)
    level = cfg["security_levels"]["app"]
    diag = cfg["diagnostic"]
    fd = cfg["can"]["fd"]

    run_dir = Path(__file__).parent / "logs" / f"stress6659_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True)
    print(f"运行目录：{run_dir}")
    print(f"rounds={args.rounds} calibs/round={args.calibs} storm-gap={args.storm_gap_ms}ms")

    driver = make_driver(cfg)
    repro = []
    try:
        with Recorder(run_dir) as rec:
            transport = build_transport(cfg, driver, rec)
            try:
                uds = UdsClient(transport, p2_ms=cfg["timing"]["p2_ms"],
                                p2star_ms=P2STAR_MS, log=rec.event)

                def log(msg):
                    rec.event(msg)
                    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

                ka = Keepalive(driver, rec, diag["functional_id"], fd)
                if args.keepalive:
                    ka.start()

                # 预检已消耗开机后的首次许可；以 1101 复位起始，对齐
                # 「每轮以复位+61s 等待开始」的原始节奏
                if not open_session(uds, level, log):
                    return 2
                r = uds.request(b"\x11\x01")
                log(f"初始 1101 复位 -> {fmt(r)}，等待 61s")
                time.sleep(61.0)

                for rnd in range(1, args.rounds + 1):
                    log(f"===== round {rnd}/{args.rounds} =====")
                    if not open_session(uds, level, log):
                        return 2
                    for cal in range(1, args.calibs + 1):
                        state, kind = start_calibration(uds, log, args.storm_gap_ms / 1000.0)
                        if state == "repro":
                            repro.append((rnd, cal, "3101", kind))
                            break
                        if state == "giveup":
                            break
                        state, status = wait_calibration_end(uds, log)
                        if state == "repro":
                            repro.append((rnd, cal, "3103", kind))
                            break
                        if state == "giveup":
                            break
                    if repro:
                        break
                    r = uds.request(b"\x11\x01")
                    log(f"1101 复位 -> {fmt(r)}，等待 61s")
                    time.sleep(61.0)

                if repro:
                    hold_for_t32(ka, log, args.hold_minutes)
                ka.stop()
            finally:
                transport.stop()
    finally:
        driver.close()

    print("\n========== 压测汇总 ==========")
    print(f"缺陷复现: {len(repro)}  {repro}")
    print(f"日志：{run_dir}（trace.blf 可喂 UdsLogAnalyzer 复核）")
    return 1 if repro else 0


if __name__ == "__main__":
    sys.exit(main())
