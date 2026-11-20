"""CMCRXJ6B-1385 V1.2 验证：EOL 标定 NRC22 三信号判据 + 车门信号退出回归。

板端前提：含 V1.2 修复的固件已刷写并上电（12V），CAN 卡接 RX 台架 CAN0。
先用创芯 CX（_cx 配置），CX 不可用换 ZLG（_zlg 配置）。

    cd tests/harness/dcm_eol_nrc22_v12
    python run_validation.py                          # 默认 rx_cx 配置
    python run_validation.py --config <其他 rx 配置>

原理：DiagnosticTester 只有 UDS 层步骤，置位 ETACS 信号需在总线上周期发送
ETACS 报文——本脚本复用 DiagnosticTester 的驱动/传输/安全访问模块，另起
TX 线程按 20ms 周期发 0x424/0x425/0x315 经典帧（FD 模式驱动下绕过 is_fd
守卫直调 SDK 经典发送，与诊断发送共用 _tx_lock）。

信号位位置（cpj_cmc J6B_Com_EcucValues.arxml，BIG_ENDIAN 单 bit，
2026-11-18 SSH 现查 02_Workspace_J6_V2 工作区）：
    HIBEAM_ON        0x424 bit50 -> byte6 0x20   （==1 -> NRC22）
    LOBEAM_ON        0x424 bit49 -> byte6 0x40   （==1 -> NRC22）
    HOOD_AJAR        0x425 bit14 -> byte1 0x02   （==1 -> NRC22）
    BCM_PSG_AJAR     0x425 bit10 -> byte1 0x20   （V1.2 已退出判据）
    BCM_DRV_AJAR_PR  0x315 bit23 -> byte2 0x01   （V1.2 已退出判据）

退出码：0 全过 / 1 有 FAIL / 2 配置或连接错误。
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
TOOLS = (HERE.parent.parent.parent / "tools" / "DiagnosticTester").resolve()
sys.path.insert(0, str(TOOLS))

from can_driver import CanFrame                      # noqa: E402
from flow import load_config                         # noqa: E402
from isotp import IsoTpTransport                     # noqa: E402
from recorder import Recorder                        # noqa: E402
from security import perform_unlock                  # noqa: E402
from uds import UdsClient                            # noqa: E402
from DiagnosticTester import build_transport, make_driver, new_run_dir  # noqa: E402

MSG_BASE = {
    0x424: bytes.fromhex("988404018D2D0000"),   # 实车 asc 样例（IG1 on / 灯全灭）
    0x425: bytes.fromhex("0000021000000000"),
    0x315: bytes.fromhex("280000FD89000000"),
}
SIGNALS = {
    "HIBEAM_ON":       (0x424, 6, 0x20),
    "LOBEAM_ON":       (0x424, 6, 0x40),
    "HOOD_AJAR":       (0x425, 1, 0x02),
    "BCM_PSG_AJAR":    (0x425, 1, 0x20),
    "BCM_DRV_AJAR_PR": (0x315, 2, 0x01),
}
TX_PERIOD_S = 0.02
SIG_SETTLE_S = 0.5


def make_classic_sender(driver, rec):
    """经典 CAN 帧发送（FD 驱动模式下绕过 is_fd 守卫直调 SDK 经典发送）。"""
    def blf(mid, data):
        rec.frame(CanFrame(mid, bytes(data), is_fd=False), is_rx=False)

    if not getattr(driver, "fd", False):
        def send(mid, data):
            driver.send(CanFrame(mid, data, is_fd=False))
            blf(mid, data)
        return send

    z = driver._z
    cx_types = hasattr(driver, "_cx")
    mod = driver._cx if cx_types else driver._zmod
    chn = driver._chn

    def send(mid, data):
        with driver._tx_lock:
            msgs = (mod.ZCAN_Transmit_Data * 1)()
            m = msgs[0]
            f = m.frame
            f.can_id = mid
            f.can_dlc = len(data)
            m.transmit_type = 0
            for i, b in enumerate(data):
                f.data[i] = b
            if z.Transmit(chn, msgs, 1) != 1:
                raise RuntimeError(f"经典 CAN 发送失败 0x{mid:X}")
        blf(mid, data)
    return send


class EtacsTx(threading.Thread):
    """周期发送 ETACS_OUT1/2/3，信号值可被主线程热改。"""

    def __init__(self, sender):
        super().__init__(daemon=True)
        self._sender = sender
        self._lock = threading.Lock()
        self._values = {name: 0 for name in SIGNALS}
        self._stop = threading.Event()
        self.tx_error = None

    def set(self, on_map):
        with self._lock:
            for name, on in on_map.items():
                self._values[name] = 1 if on else 0

    def _frames(self):
        with self._lock:
            payloads = dict(MSG_BASE)
            for name, (mid, byte_i, mask) in SIGNALS.items():
                if self._values[name]:
                    b = bytearray(payloads[mid])
                    b[byte_i] |= mask
                    payloads[mid] = bytes(b)
            return payloads

    def run(self):
        try:
            while not self._stop.is_set():
                t0 = time.monotonic()
                for mid, data in self._frames().items():
                    self._sender(mid, data)
                time.sleep(max(0.0, TX_PERIOD_S - (time.monotonic() - t0)))
        except Exception as e:
            self.tx_error = e

    def stop(self):
        self._stop.set()


def check(rec, seq, name, payload, res, expect, seq_no):
    """判定一步：expect = {"prefix": hex} 或 {"nrc": int} 或 {"nrc_not": int, "negative": True}。"""
    if expect.get("prefix") is not None:
        ok = bool(res.response) and not res.timeout \
            and res.response.hex().upper().startswith(expect["prefix"])
    elif expect.get("nrc") is not None:
        ok = res.nrc == expect["nrc"]
    elif expect.get("negative") and expect.get("nrc_not") is not None:
        ok = bool(res.response) and not res.timeout and res.response[0] == 0x7F \
            and res.nrc != expect["nrc_not"]
    else:
        ok = bool(res.response) and not res.timeout
    verdict = "PASS" if ok else "FAIL"
    rec.step(seq_no, name, "physical", payload, res, verdict)
    resp = res.response.hex().upper() if res.response else "超时无响应"
    nrc = f"（NRC 0x{res.nrc:02X}）" if res.nrc is not None else ""
    rec.event(f"步骤{seq_no} {name}: {payload} -> {resp}{nrc} [{verdict}]")
    return ok


def run_scenario(uds, rec, levels, tx, sc, seq_start):
    """跑一个场景，返回 (全过?, 下一个 seq_no)。"""
    name = sc["name"]
    expect = sc["expect"]
    rec.blank()
    rec.event(f"=== 场景 {name} 置位 {sc.get('set', {})} 期望 {expect['kind']} ===")
    tx.set({n: 0 for n in SIGNALS})
    tx.set(sc.get("set", {}))
    time.sleep(SIG_SETTLE_S)
    ok = True
    seq = seq_start

    def do(payload, expect_rule, label):
        nonlocal seq, ok
        res = uds.request(bytes.fromhex(payload))
        if not check(rec, seq, label, payload, res, expect_rule, seq):
            ok = False
        seq += 1
        return res

    if sc.get("default_session"):
        # 回归：默认会话 0x31 应被会话检查拦（负响应且非 NRC22）
        do("3101FE01", {"negative": True, "nrc_not": 0x22}, f"{name} 默认会话 31 01 FE 01")
        return ok, seq

    r = do("1003", {"prefix": "5003"}, f"{name} 进扩展会话")
    if r.timeout or (r.response or b"")[:2] != bytes.fromhex("5003"):
        rec.event(f"{name}: 进扩展会话失败，跳过本场景剩余步骤")
        return ok, seq
    try:
        _, _, ures = perform_unlock(uds, levels["app"], log=rec.event)
        rec.step(seq, f"{name} app 安全解锁", "physical", "27xx", ures,
                 "PASS" if ures.ok else "FAIL")
        if not ures.ok:
            ok = False
            rec.event(f"{name}: 安全解锁失败，跳过本场景剩余步骤")
            return ok, seq + 1
        seq += 1
    except Exception as e:
        rec.event(f"{name}: 安全解锁异常 {e!r}")
        return False, seq + 1

    kind = expect["kind"]
    if kind == "positive":
        do("3101FE01", {"prefix": "7101FE01"}, f"{name} 31 01 FE 01 放行")
    elif kind == "nrc22":
        do("3101FE01", {"nrc": 0x22}, f"{name} 31 01 FE 01 NRC22")
    else:
        raise ValueError(f"未知期望 {kind}")

    do("1101", {"prefix": "5101"}, f"{name} ECU reset 收尾")
    time.sleep(1.0)
    return ok, seq


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config",
                    default=str(TOOLS / "configs" / "rx" / "rx_cx.yaml"))
    ap.add_argument("--testcases", default=str(HERE / "testcases" / "scenarios.yaml"))
    args = ap.parse_args()

    cfg = load_config(args.config)
    scenarios = yaml.safe_load(Path(args.testcases).read_text(encoding="utf-8"))
    levels = cfg["security_levels"]

    driver = make_driver(cfg)
    run_dir = new_run_dir(HERE / "logs")
    print(f"运行目录：{run_dir}")
    passed = failed = 0
    with Recorder(run_dir) as rec:
        rec.event(f"配置：{args.config}；场景数：{len(scenarios)}")
        transport = build_transport(cfg, driver, rec)
        uds = UdsClient(transport, p2_ms=cfg["timing"]["p2_ms"],
                        p2star_ms=cfg["timing"]["p2star_ms"], log=rec.event)
        tx = EtacsTx(make_classic_sender(driver, rec))
        tx.start()
        try:
            seq = 1
            for sc in scenarios:
                ok, seq = run_scenario(uds, rec, levels, tx, sc, seq)
                passed += 1 if ok else 0
                failed += 0 if ok else 1
                if tx.tx_error:
                    rec.event(f"ETACS 发送线程异常：{tx.tx_error!r}")
                    print(f"ETACS 发送线程异常：{tx.tx_error!r}", file=sys.stderr)
                    failed += 1
                    break
        finally:
            tx.set({n: 0 for n in SIGNALS})
            tx.stop()
            transport.stop()
    print(f"场景 PASS {passed} / FAIL {failed} / 共 {len(scenarios)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
