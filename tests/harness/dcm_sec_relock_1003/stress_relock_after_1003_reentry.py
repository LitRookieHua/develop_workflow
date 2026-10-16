"""D3ACYI-1832 复现压测：10 03 会话重入后安全状态应重锁，并发负载下验证。

复现原始 BLF 环境：测试仪后台周期任务向 0x7DF 发 3E 80，与 10 03 / 27
序列真并发（顺序用例步骤间无重叠，无法复现冲突）。

核心判定：重入 10 03 后的 27 01 若返回零种子或 NRC 0x24（request
SequenceError），即「重入未重锁」bug 复现；正常应为非零种子。

用法：
  python stress_relock_after_1003_reentry.py [rounds=20] [keepalive_period_ms=150]

输出：本目录 logs/stress_<时间戳>/（run.log 由 Recorder 落盘 + 控制台），
与 mcu_log 串口采集（capture_com68.py）的 com68_capture.log [D1832] 行按时间戳对照。
"""
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[3] / "tools" / "DiagnosticTester"
sys.path.insert(0, str(TOOLS))

from can_driver import CanFrame  # noqa: E402
from DiagnosticTester import build_transport, make_driver  # noqa: E402
from flow import load_config  # noqa: E402
from isotp import encode  # noqa: E402
from recorder import Recorder  # noqa: E402
from uds import UdsClient  # noqa: E402

CONFIG = TOOLS / "configs" / "v2xeu" / "v2xeu_cx.yaml"

# 每个请求前的最小间隔：响应后贴身到达的请求会被 ECU 丢弃，且可能杀掉
# 上一响应未完成的 Tx 确认（S10Post/S27Post 走 NOT_OK 分支）。实验：主流程
# 用大间隔让确认完成，判定步用小间隔制造竞争
REQ_GAP_MS = 400

# 判定步（重入后的 27 01）间隔：50ms 恒定——须落在丢弃窗口之外确保被
# 处理；重入 5003 的确认由 keepalive 密集帧撞进窗口杀掉（模拟原始 BLF）
VERDICT_GAPS_MS = [50]

# keepalive 间隔轮转（ms）：模拟原始 BLF 的 3E 80 密集簇（0.044~0.9s），
# 密集帧撞进响应确认窗口 → 杀掉 Tx 确认 → S10Post NOT_OK → 重锁跳过
KA_INTERVALS_MS = [45, 90, 180, 300]


def fmt(r):
    if r.timeout:
        return "TIMEOUT"
    if r.response is None:
        return "EMPTY"
    txt = r.response.hex().upper()
    if r.nrc is not None:
        txt += f" (NRC 0x{r.nrc:02X})"
    return txt


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    period_ms = float(sys.argv[2]) if len(sys.argv) > 2 else 150.0

    cfg = load_config(CONFIG)
    levels = cfg["security_levels"]
    level = levels["app"]
    diag = cfg["diagnostic"]
    fd = cfg["can"]["fd"]

    run_dir = Path(__file__).parent / "logs" / f"stress_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True)
    print(f"运行目录：{run_dir}")
    print(f"rounds={rounds} keepalive={KA_INTERVALS_MS}ms "
          f"req_gap={REQ_GAP_MS}ms verdict_gap={VERDICT_GAPS_MS}ms")

    driver = make_driver(cfg)
    repro = []
    anomalies = []
    try:
        with Recorder(run_dir) as rec:
            transport = build_transport(cfg, driver, rec)
            try:
                uds = UdsClient(transport, p2_ms=cfg["timing"]["p2_ms"],
                                p2star_ms=cfg["timing"]["p2star_ms"], log=rec.event)

                def log(msg):
                    rec.event(msg)
                    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

                ka_frames = [CanFrame(diag["functional_id"], f, is_fd=fd,
                                      bitrate_switch=fd)
                             for f in encode(b"\x3e\x80", fd)]
                stop = threading.Event()

                def keepalive():
                    next_t = time.monotonic()
                    k = 0
                    while not stop.is_set():
                        for f in ka_frames:
                            try:
                                driver.send(f)
                                rec.frame(f, False)
                            except Exception as exc:  # noqa: BLE001
                                rec.event(f"keepalive send error: {exc!r}")
                        interval = KA_INTERVALS_MS[k % len(KA_INTERVALS_MS)]
                        k += 1
                        next_t += interval / 1000.0
                        delay = next_t - time.monotonic()
                        if delay > 0:
                            stop.wait(delay)
                        else:
                            next_t = time.monotonic()

                ka = threading.Thread(target=keepalive, daemon=True)
                ka.start()
                log(f"keepalive thread started: 3E80 -> 0x{diag['functional_id']:X} "
                    f"every {period_ms}ms")

                for i in range(1, rounds + 1):
                    gap = VERDICT_GAPS_MS[(i - 1) % len(VERDICT_GAPS_MS)]
                    log(f"--- round {i}/{rounds} verdict_gap={gap}ms ---")

                    time.sleep(REQ_GAP_MS / 1000.0)
                    r1 = uds.request(b"\x10\x03")
                    log(f"[{i}] 1003 -> {fmt(r1)}")
                    if not r1.ok:
                        anomalies.append((i, "1003", fmt(r1)))
                        continue

                    time.sleep(REQ_GAP_MS / 1000.0)
                    rs = uds.request(level.seed_request())
                    log(f"[{i}] 27 {level.seed_sub:02X} -> {fmt(rs)}")
                    if not rs.ok:
                        anomalies.append((i, "seed", fmt(rs)))
                        continue
                    seed = rs.response[2:]
                    if set(seed) == {0}:
                        log(f"[{i}] !!! 首次解锁前即零种子（会话状态异常）")
                        repro.append((i, "zero-seed-before-unlock"))

                    key = level.compute_key(seed)
                    time.sleep(REQ_GAP_MS / 1000.0)
                    rk = uds.request(bytes([0x27, level.key_sub]) + key)
                    log(f"[{i}] 27 {level.key_sub:02X} -> {fmt(rk)}")
                    if not rk.ok:
                        anomalies.append((i, "key", fmt(rk)))
                        continue

                    time.sleep(REQ_GAP_MS / 1000.0)
                    r2 = uds.request(b"\x10\x03")
                    log(f"[{i}] 1003 reenter -> {fmt(r2)}")
                    if not r2.ok:
                        anomalies.append((i, "1003-reenter", fmt(r2)))
                        continue

                    time.sleep(gap / 1000.0)

                    rv = uds.request(level.seed_request())
                    log(f"[{i}] 27 {level.seed_sub:02X} verdict -> {fmt(rv)}")
                    if rv.timeout:
                        anomalies.append((i, "verdict-seed", "TIMEOUT"))
                    elif rv.nrc == 0x24:
                        log(f"[{i}] !!! BUG 复现：NRC 0x24（重入后仍处于解锁态）")
                        repro.append((i, "nrc24"))
                    elif rv.ok:
                        vseed = rv.response[2:]
                        if set(vseed) == {0}:
                            log(f"[{i}] !!! BUG 复现：零种子（重入后仍处于解锁态）")
                            repro.append((i, "zero-seed"))
                        else:
                            log(f"[{i}] 正常重锁（非零种子）")
                    else:
                        anomalies.append((i, "verdict-seed", fmt(rv)))

                    time.sleep(0.3)

                stop.set()
                ka.join(timeout=2)
            finally:
                transport.stop()
    finally:
        driver.close()

    print("\n========== 汇总 ==========")
    print(f"rounds: {rounds}, keepalive {period_ms}ms")
    print(f"BUG 复现: {len(repro)}  {repro}")
    print(f"其他异常: {len(anomalies)}  {anomalies}")
    return 1 if repro else 0


if __name__ == "__main__":
    sys.exit(main())
