# -*- coding: utf-8 -*-
"""RID 0x0203 bit-mask bench validation (C097FAWVW-40) by injecting precondition frames.

Send iBRS_01 (0x0A0), BDU_0 (0x400), VCU_VehInfo (0x0A9) at 20 ms while querying
31 01 02 03 over the same CX-USBCANFD channel, one phase per precondition bit.

bit = 1 means the precondition is NOT met. Baseline injects "all satisfied":
speed 0 km/h + VD valid, BDU_VehPwrMod = 2 (Standby), gear = 1 (P) + Qlfr valid.
The voltage bit (0x08) depends on the supply, so it is taken from the baseline
measurement and expected to stay constant across phases.

ECU prerequisites: flashed build with RID 0x0203, extended session reachable.

    python inject_and_query.py [--phase-delay 0.3] [--verbose]
"""
import argparse
import sys
import threading
import time
from pathlib import Path

TOOL = Path(__file__).resolve().parents[3] / "tools" / "DiagnosticTester"
sys.path.insert(0, str(TOOL))

from can_driver import CanFrame, CxCanFdDriver  # noqa: E402
from isotp import IsoTpTransport  # noqa: E402

TX_ID, RX_ID = 0x754, 0x75C
PERIOD_S = 0.02

BIT_SPEED, BIT_ENGINE, BIT_T15, BIT_VOLT, BIT_GEAR = 0x01, 0x02, 0x04, 0x08, 0x10


def frame_ibrs(speed_kmh: float, valid: bool = True) -> CanFrame:
    data = bytearray(16)
    raw = int(round(speed_kmh * 100.0))
    data[6] = raw & 0xFF              # iBRS_VehSpd @ bit48 15bit, factor 0.01
    data[7] = (raw >> 8) & 0x7F
    if valid:
        data[1] |= 1 << 4             # iBRS_VehSpdVD @ bit12 2bit
    return CanFrame(0x0A0, bytes(data), is_fd=True, bitrate_switch=True)


def frame_bdu(pwr_mod: int) -> CanFrame:
    data = bytearray(4)
    data[2] = pwr_mod & 0x07          # BDU_VehPwrMod @ bit16 3bit
    return CanFrame(0x400, bytes(data), is_fd=True, bitrate_switch=True)


def frame_vcu(gear: int, qlfr: int) -> CanFrame:
    data = bytearray(8)
    data[4] = (gear & 0x0F) | ((qlfr & 0x03) << 4)  # gear @ bit32, qlfr @ bit36
    return CanFrame(0x0A9, bytes(data), is_fd=True, bitrate_switch=True)


class Injector:
    def __init__(self, driver: CxCanFdDriver):
        self.driver = driver
        self._frames = []
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def set(self, speed_kmh, speed_valid, pwr_mod, gear, qlfr):
        with self._lock:
            self._frames = [frame_ibrs(speed_kmh, speed_valid),
                            frame_bdu(pwr_mod),
                            frame_vcu(gear, qlfr)]

    def _run(self):
        while not self._stop.is_set():
            with self._lock:
                frames = self._frames
            for f in frames:
                self.driver.send(f)
            time.sleep(PERIOD_S)

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=1.0)


def query_status(tp: IsoTpTransport, verbose: bool):
    tp.send_payload(bytes([0x10, 0x03]))
    resp = tp.recv_payload(1.0)
    if resp is None or not resp.startswith(b"\x50\x03"):
        return None, resp
    tp.send_payload(bytes([0x31, 0x01, 0x02, 0x03]))
    resp = tp.recv_payload(1.0)
    if verbose:
        print("    RX:", resp.hex().upper() if resp else "None")
    if resp is None or not resp.startswith(b"\x71\x01\x02\x03"):
        return None, resp
    return (resp[4] if len(resp) >= 5 else 0x00), resp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase-delay", type=float, default=0.3,
                    help="settle time after switching injected values (s)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    driver = CxCanFdDriver(channel=0, baudrate=500000, data_baudrate=2000000, fd=True)
    tp = IsoTpTransport(driver, tx_id=TX_ID, rx_id=RX_ID, is_fd=True)
    tp.start()
    inj = Injector(driver)
    inj.start()
    failures = 0
    try:
        phases = [
            ("baseline       ", (0.0, True,  2, 1, 1), None),
            ("speed 5 km/h   ", (5.0, True,  2, 1, 1), "base|0x01"),
            ("speed VD=0     ", (5.0, False, 2, 1, 1), "base"),
            ("T15 off (pwr 0)", (0.0, True,  0, 1, 1), "base|0x04"),
            ("gear D (2)     ", (0.0, True,  2, 2, 1), "base|0x10"),
            ("gear qlfr inv  ", (0.0, True,  2, 2, 2), "base"),
            ("all unmet      ", (5.0, True,  0, 2, 1), "base|0x15"),
        ]
        base = None
        print("phase             expected  actual  result")
        for name, vals, expect in phases:
            inj.set(*vals)
            time.sleep(args.phase_delay)
            status, raw = query_status(tp, args.verbose)
            if status is None:
                print(f"{name}  unexpected response {raw.hex().upper() if raw else 'None'}")
                failures += 1
                continue
            if base is None:
                base = status & BIT_VOLT          # voltage bit is supply-dependent
                expected = base
            else:
                expected = base if expect == "base" else base | int(expect.split("|")[1], 16)
            ok = status == expected
            failures += 0 if ok else 1
            print(f"{name}  0x{expected:02X}      0x{status:02X}    {'PASS' if ok else 'FAIL'}")
        # leave the ECU with all-satisfied frame values
        inj.set(0.0, True, 2, 1, 1)
        time.sleep(0.2)
    finally:
        inj.stop()
        tp.stop()
        driver.close()
    print(f"done: {len(locals().get('phases', []))} phases, failures={failures}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
