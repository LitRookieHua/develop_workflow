"""IDC310GAC-8402 简单例程（R 核诊断循环，data1/data2 交替写）：

每循环 = 两轮（2026-11-03 按用户流程改版，复刻原单触发上下文）：
  A 轮：1001 → 1003 → 27解锁 → 2E9A3E(data1) → [22反读] → 1101（期望5101）
        → 等60s → 轮询1001等诊断回网
  B 轮：1001 → 1003 → 27解锁 → 2E9A3E(data2) → [22反读] → 1101（期望5101）
        → 等60s → 轮询1001等诊断回网 → 下一循环

两轮 1101 后均等 60s（A 核完整启动）——每轮写都落在 A 核就绪窗口，走 IPC
成功（6E）+ 反读 OK，紧接 1101——即原单 8402 的触发上下文（PKI 写成功后
紧随 1101 复位）。单循环 ~125s。
RED 判定同 KPI 脚本（1101 零响应 = 无 pending/无 NRC）。
**命中黑洞（1001/1003/27/2E/1101 超时）不中止**：进入 90s 观察期（每 1s 发
1001 探测诊断通道恢复时序，与 trace.blf 的总线断档对照），观察完继续循环
积累样本；非超时类失败（意外 NRC/反读不符/120s 不回网）才中止。

用法：
  python smoke_8402_basic.py [cycles=5]

输出：本目录 logs/smoke_<时间戳>/（run.log + trace.blf）
退出码：0 全部循环 5101 正常 / 1 有异常 / 3 运行期异常
"""
import argparse
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

CONFIG = TOOLS / "configs" / "t09" / "t09_cx.yaml"

DID = 0x9A3E
DATA1 = b"192.168.1.239           12444 "
DATA2 = b"172.16.0.14             12443 "
WAIT_AFTER_RESET_A_S = 60.0  # A 轮 1101 后等 60s（A 核完整启动，Linux 10-30s）
WAIT_AFTER_RESET_B_S = 60.0  # B 轮 1101 后同样等 60s——下轮写也落在就绪窗口
REBOOT_POLL_S = 1.0          # 等诊断回网的轮询周期
REBOOT_TIMEOUT_S = 120.0     # 回网轮询上限
OBSERVE_S = 90.0             # 黑洞命中后的观察期时长
P2_1101_MS = 2000
P2STAR_MS = 30000
# 快速路径（1001/1003/27）用 1s：R 核偶发 50-90ms 时延尖峰（~1/860 请求，ECU 会迟到应答，
# BLF 取证见 cycle 649=85ms / cycle 1709=52ms）不是 8402 目标缺陷，50ms 紧 p2 会误停；
# 真黑洞（≥2s 零应答，如 cycle 305 / 原单 8402）在 1s 预算下照样触发
P2_FAST_MS = 1000


def fmt(r):
    if r.timeout:
        return "TIMEOUT"
    txt = r.response.hex().upper() if r.response else "EMPTY"
    if r.nrc is not None:
        txt += f" (NRC 0x{r.nrc:02X}, pendings={r.pendings})"
    return txt


def main():
    ap = argparse.ArgumentParser(description="8402 smoke: session+unlock+write+readback+1101 loop")
    ap.add_argument("cycles", nargs="?", type=int, default=5)
    args = ap.parse_args()

    cfg = load_config(CONFIG)
    diag = cfg["diagnostic"]
    fd = cfg["can"]["fd"]
    level = cfg["security_levels"]["app"]

    run_dir = Path(__file__).parent / "logs" / f"smoke_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True)
    print(f"运行目录：{run_dir}  cycles={args.cycles}")

    def log(msg):
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    driver = make_driver(cfg)
    transport = None
    anomalies = []
    recovery_times = []
    try:
        with Recorder(run_dir) as rec:
            transport = build_transport(cfg, driver, rec)
            uds = UdsClient(transport, p2_ms=cfg["timing"]["p2_ms"], p2star_ms=P2STAR_MS,
                            log=rec.event)

            # 3E80 keepalive（与原测试一致持续发）
            stop = threading.Event()
            ka_frames = [CanFrame(diag["functional_id"], f, is_fd=fd, bitrate_switch=fd)
                         for f in encode(b"\x3e\x80", fd)]

            def ka():
                while not stop.is_set():
                    for f in ka_frames:
                        try:
                            driver.send(f)
                            rec.frame(f, False)  # keepalive TX 补记入 BLF（transport 路径之外的发送不记录）
                        except Exception as exc:  # noqa: BLE001
                            log(f"keepalive send error: {exc!r}")
                    stop.wait(2.0)

            threading.Thread(target=ka, daemon=True, name="ka3e80").start()

            def observe(tag):
                """黑洞命中后的存活观察：每 1s 1001 探测，记录诊断恢复时序
                （与 trace.blf 中总线断档时刻对照，区分整机复位 vs 诊断链路挂死）。"""
                log(f"!!! {tag} 黑洞命中：观察期 {OBSERVE_S:.0f}s，每 1s 1001 探测")
                t_obs = time.monotonic()
                while time.monotonic() - t_obs < OBSERVE_S:
                    pr = uds.request(b"\x10\x01", timeout_ms=1000)
                    log(f"[observe t+{time.monotonic() - t_obs:5.1f}s] 1001 -> {fmt(pr)}")
                    time.sleep(1.0)

            def one_round(cyc, tag, data, wait_reset_s):
                """一轮：1001→1003→27解锁→2E9A3E(data)→[22反读]→1101→等
                wait_reset_s→轮询回网。反读校验 = 本轮写入的 data。
                返回 True 继续；False = 非超时类失败（应停）。黑洞超时观察后继续。"""
                r = uds.request(b"\x10\x01", timeout_ms=P2_FAST_MS)
                log(f"[{tag}] 1001 -> {fmt(r)}")
                if r.timeout:
                    anomalies.append((cyc, f"{tag}/1001", "blackhole zero-response"))
                    observe(f"{tag}/1001(cycle {cyc}) 零响应")
                    return True
                if not r.ok:
                    anomalies.append((cyc, f"{tag}/1001", fmt(r)))
                    return False
                r = uds.request(b"\x10\x03", timeout_ms=P2_FAST_MS)
                log(f"[{tag}] 1003 -> {fmt(r)}")
                if r.timeout:
                    anomalies.append((cyc, f"{tag}/1003", "blackhole zero-response"))
                    observe(f"{tag}/1003(cycle {cyc}) 零响应")
                    return True
                if not r.ok:
                    anomalies.append((cyc, f"{tag}/1003", fmt(r)))
                    return False

                rs = uds.request(level.seed_request(), timeout_ms=P2_FAST_MS)
                log(f"[{tag}] 27 seed -> {fmt(rs)}")
                if rs.timeout:
                    anomalies.append((cyc, f"{tag}/27-seed", "blackhole zero-response"))
                    observe(f"{tag}/27-seed(cycle {cyc}) 零响应")
                    return True
                if not rs.ok:
                    anomalies.append((cyc, f"{tag}/27-seed", fmt(rs)))
                    return False
                key = level.compute_key(rs.response[2:])
                rk = uds.request(bytes([0x27, level.key_sub]) + key, timeout_ms=P2_FAST_MS)
                log(f"[{tag}] 27 {level.key_sub:02X} -> {fmt(rk)}")
                if rk.timeout:
                    anomalies.append((cyc, f"{tag}/27-key", "blackhole zero-response"))
                    observe(f"{tag}/27-key(cycle {cyc}) 零响应")
                    return True
                if not (rk.ok and rk.response[:1] == b"\x67"):
                    anomalies.append((cyc, f"{tag}/27-key", fmt(rk)))
                    return False

                w = uds.request(b"\x2e" + DID.to_bytes(2, "big") + data, timeout_ms=P2STAR_MS)
                log(f"[{tag}] 2E9A3E -> {fmt(w)} ({data.decode(errors='replace')!r})")
                write_ok = w.ok and w.response[:1] == b"\x6e"
                if w.timeout:
                    # 诊断请求黑洞（pending 后无终态 / 全程零响应）——观察后继续，
                    # 积累命中样本（首例：2026-11-02 cycle 305，pending 至 09.645 后静默）
                    anomalies.append((cyc, f"{tag}/2E", f"blackhole pendings={w.pendings}"))
                    observe(f"{tag}/2E(cycle {cyc}, pendings={w.pendings})")
                    return True
                if not write_ok and w.nrc == 0x22:
                    if tag == "A":
                        # A 轮预期：复位后 ~3s A 核未就绪，IPC 5s 超时 → 0x22
                        log(f"[{tag}] NRC 0x22：A 核未就绪窗口，跳过反读，继续 1101")
                    else:
                        # B 轮在 60s 后 A 核应就绪：0x22 = 启动超时/IPC 异常，记异常继续
                        anomalies.append((cyc, f"{tag}/2E", "NRC 0x22 in A-core-ready window"))
                        log(f"[{tag}] NRC 0x22：A 核就绪窗口异常，跳过反读，继续 1101")
                elif not write_ok:
                    anomalies.append((cyc, f"{tag}/2E", fmt(w)))
                    return False

                if write_ok:
                    rd = uds.request(b"\x22" + DID.to_bytes(2, "big"), timeout_ms=P2_FAST_MS)
                    got = rd.response[3:3 + len(data)] if rd.ok else b""
                    log(f"[{tag}] 229A3E -> 反读 {'OK' if got == data else '不符: ' + repr(got)}")
                    if got != data:
                        anomalies.append((cyc, f"{tag}/22", fmt(rd)))
                        return False

                t1101 = time.monotonic()
                r = uds.request(b"\x11\x01", timeout_ms=P2_1101_MS)
                ms = (time.monotonic() - t1101) * 1000
                log(f"[{tag}] 1101 -> {fmt(r)} ({ms:.0f}ms, pendings={r.pendings})")
                if r.timeout and r.pendings == 0:
                    # 8402 原始签名：1101 零响应（无 pending/无 NRC）
                    anomalies.append((cyc, f"{tag}/1101", "zero-response (BUG RED)"))
                    log(f"!!! BUG RED：[{tag}] 1101 零响应")
                    observe(f"{tag}/1101(cycle {cyc}) 零响应")
                elif r.timeout:
                    # pending 后挂死（smoke cycle 305 在 2E 上见到的变体）
                    anomalies.append((cyc, f"{tag}/1101", f"pending-hang pendings={r.pendings}"))
                    observe(f"{tag}/1101(cycle {cyc}) pending 后静默")
                elif not (r.ok and r.response[:1] == b"\x51"):
                    anomalies.append((cyc, f"{tag}/1101", fmt(r)))
                    return False

                time.sleep(wait_reset_s)
                # 等 ECU 诊断回网（量复位恢复时间）
                t_rb = time.monotonic()
                while True:
                    pr = uds.request(b"\x10\x01", timeout_ms=1000)
                    if pr.ok:
                        rb = time.monotonic() - t_rb
                        recovery_times.append(round(rb, 2))
                        log(f"[{tag}] ECU 诊断回网：{rb:.2f}s（自 1101 后 {rb + wait_reset_s:.2f}s）")
                        return True
                    if time.monotonic() - t_rb > REBOOT_TIMEOUT_S:
                        anomalies.append((cyc, f"{tag}/reboot", "诊断超时未回网"))
                        log(f"!!! [{tag}] ECU 复位后诊断 120s 未回网")
                        return False
                    time.sleep(REBOOT_POLL_S)

            for cyc in range(1, args.cycles + 1):
                t0 = time.monotonic()
                log(f"===== cycle {cyc}/{args.cycles} A(data1) =====")
                if not one_round(cyc, "A", DATA1, WAIT_AFTER_RESET_A_S):
                    break
                log(f"===== cycle {cyc}/{args.cycles} B(data2) =====")
                if not one_round(cyc, "B", DATA2, WAIT_AFTER_RESET_B_S):
                    break
                log(f"cycle {cyc} 完成，耗时 {time.monotonic() - t0:.1f}s")

            stop.set()
    finally:
        if transport is not None:
            transport.stop()
        driver.close()

    print("\n========== 汇总 ==========")
    print(f"异常: {len(anomalies)}  {anomalies}")
    if recovery_times:
        print(f"复位后诊断回网耗时: min={min(recovery_times)}s max={max(recovery_times)}s n={len(recovery_times)}")
    return 1 if anomalies else 0


if __name__ == "__main__":
    sys.exit(main())
