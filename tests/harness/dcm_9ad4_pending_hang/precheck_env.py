"""环境预检：GAC T68 板 + SoC 到位后第一个跑，回答两个问题。

1. 标定失败模式时序：SoC 快速回错误 RESULT，还是不回、MCU 走 28s 超时
   （观察 3103 Running→终态 的时长与终态 status 值）
2. 失败后 SoC 是否仍发 CALI_MSG_PERMIT（观察 3101 NRC22 冷却窗口长度；
   若窗口无限长则 6659 场景需改为一轮一 1101 复位）

顺带验证 t68_cx.yaml 新增的 security 解锁配置（2701/2702 gac_shift_xor）。

用法：
  python precheck_env.py [--config ../../tools/DiagnosticTester/configs/t68/t68_cx.yaml]

输出：logs/precheck_<时间戳>/（run.log + trace.blf，可再喂 UdsLogAnalyzer）
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from common import TOOLS, Keepalive, REQ_3101, REQ_3103, classify, fmt, open_session

from DiagnosticTester import build_transport, make_driver  # noqa: E402
from flow import load_config  # noqa: E402
from recorder import Recorder  # noqa: E402
from uds import UdsClient  # noqa: E402

POLL_INTERVAL_S = 1.0
POLL_CAP_S = 40.0     # 28s EOL 超时 + 余量；超限说明环境异常
STORM_GAP_S = 0.2     # 许可窗口测量用 hammer 间隔（分辨率 0.2s 足够）
STORM_CAP_S = 180.0   # 窗口超限 → SoC 不回 PERMIT，环境结论


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=str(TOOLS / "configs" / "t68" / "t68_cx.yaml"))
    args = ap.parse_args()

    cfg = load_config(args.config)
    level = cfg["security_levels"]["app"]
    diag = cfg["diagnostic"]
    fd = cfg["can"]["fd"]

    run_dir = Path(__file__).parent / "logs" / f"precheck_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True)
    print(f"运行目录：{run_dir}")

    driver = make_driver(cfg)
    repro = []
    try:
        with Recorder(run_dir) as rec:
            transport = build_transport(cfg, driver, rec)
            try:
                uds = UdsClient(transport, p2_ms=cfg["timing"]["p2_ms"],
                                p2star_ms=cfg["timing"]["p2star_ms"], log=rec.event)

                def log(msg):
                    rec.event(msg)
                    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

                ka = Keepalive(driver, rec, diag["functional_id"], fd)
                ka.start()

                if not open_session(uds, level, log):
                    return 2

                r = uds.request(b"\x22\x9a\x59")
                log(f"22 9A59 标定模式 -> {fmt(r)}")

                # ---- 3101：接受或处冷却窗口 ----
                t0 = time.monotonic()
                r = uds.request(REQ_3101)
                kind, text = classify(r)
                log(f"3101 -> {kind}: {text}")
                if kind in ("swallow", "hang"):
                    repro.append(("3101", kind))
                elif kind == "nrc22":
                    log("处于 NRC22 冷却窗口，hammer 测量窗口长度……")
                    w0 = time.monotonic()
                    n22 = 1
                    while True:
                        if time.monotonic() - w0 > STORM_CAP_S:
                            log(f"!!! 冷却窗口超过 {STORM_CAP_S}s：SoC 疑似不回 PERMIT")
                            break
                        time.sleep(STORM_GAP_S)
                        r = uds.request(REQ_3101)
                        kind, text = classify(r)
                        if kind == "nrc22":
                            n22 += 1
                            continue
                        log(f"3101 -> {kind}: {text}（NRC22 ×{n22}，窗口 {time.monotonic()-w0:.1f}s）")
                        if kind in ("swallow", "hang"):
                            repro.append(("3101-storm", kind))
                        break
                if repro:
                    ka.stop()
                    return finish(repro, run_dir)

                # ---- 3103 轮询至终态：标定时长 + 终态 status ----
                t_cal = time.monotonic()
                terminal = None
                while True:
                    elapsed = time.monotonic() - t_cal
                    if elapsed > POLL_CAP_S:
                        log(f"!!! 3103 超过 {POLL_CAP_S}s 仍非终态（环境异常）")
                        break
                    time.sleep(POLL_INTERVAL_S)
                    r = uds.request(REQ_3103)
                    kind, text = classify(r)
                    if r.ok and r.response[:3] == b"\x71\x03\x9a":
                        status = r.response[4] if len(r.response) > 4 else None
                        if status == 0x01:
                            continue
                        terminal = status
                        log(f"3103 终态 status=0x{status:02X}（标定时长 {time.monotonic()-t_cal:.1f}s）：{text}")
                        break
                    log(f"3103 -> {kind}: {text}（{elapsed:.0f}s）")
                    if kind in ("swallow", "hang"):
                        repro.append(("3103", kind))
                        break
                    if r.nrc is not None:
                        break

                r = uds.request(b"\x22\x9a\x59")
                log(f"22 9A59 终态后 -> {fmt(r)}")

                # ---- 终态后再起一轮 3101：失败路径的许可窗口 ----
                if terminal is not None and not repro:
                    log("终态后 hammer 3101，测量失败后的许可窗口……")
                    w0 = time.monotonic()
                    n22 = 0
                    while True:
                        if time.monotonic() - w0 > STORM_CAP_S:
                            log(f"!!! 失败后冷却窗口超过 {STORM_CAP_S}s：SoC 疑似不回 PERMIT")
                            break
                        r = uds.request(REQ_3101)
                        kind, text = classify(r)
                        if kind == "nrc22":
                            n22 += 1
                            time.sleep(STORM_GAP_S)
                            continue
                        log(f"3101 -> {kind}: {text}（NRC22 ×{n22}，失败后窗口 {time.monotonic()-w0:.1f}s）")
                        if kind in ("swallow", "hang"):
                            repro.append(("3101-postfail", kind))
                        break

                ka.stop()
            finally:
                transport.stop()
    finally:
        driver.close()
    return finish(repro, run_dir)


def finish(repro, run_dir):
    print("\n========== 预检汇总 ==========")
    print(f"缺陷复现（swallow/hang）: {len(repro)}  {repro}")
    print(f"日志：{run_dir}")
    if repro:
        print("结论：环境可复现目标缺陷——直接进入 6659/6398 压测即可")
    else:
        print("结论：本次单轮未见缺陷（低概率属正常）；环境数据见上方时序")
    return 1 if repro else 0


if __name__ == "__main__":
    sys.exit(main())
