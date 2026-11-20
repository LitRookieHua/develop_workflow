"""判别实验：全候选位（Motorola+Intel 两种掩码并集）置 1，看是否回 NRC22。

byte6=0x66 覆盖 HIBEAM/LOBEAM 的 Motor/Intel 候选；
byte1=0x26 覆盖 HOOD/PSG 候选；byte2=0x81 覆盖 DRV 候选。
若全置位仍 7101FE01 -> 信号未落入 ECU（或固件未检查），而非掩码问题。
"""
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = (HERE.parent.parent.parent / "tools" / "DiagnosticTester").resolve()
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(HERE))

from recorder import Recorder
from uds import UdsClient
from security import perform_unlock
from DiagnosticTester import build_transport, make_driver, new_run_dir, load_config
from run_validation import MSG_BASE, make_classic_sender, EtacsTx

OVERRIDE = {
    0x424: bytes.fromhex("988404018D2D0066"),
    0x425: bytes.fromhex("0000261000000000"),
    0x315: bytes.fromhex("280081FD89000000"),
}

cfg = load_config(str(TOOLS / "configs" / "rx" / "rx_cx.yaml"))
driver = make_driver(cfg)
run_dir = new_run_dir(HERE / "logs")
print(f"运行目录：{run_dir}")
with Recorder(run_dir) as rec:
    transport = build_transport(cfg, driver, rec)
    uds = UdsClient(transport, p2_ms=cfg["timing"]["p2_ms"],
                    p2star_ms=cfg["timing"]["p2star_ms"], log=rec.event)
    sender = make_classic_sender(driver, rec)
    stop = threading.Event()

    def tx_loop():
        while not stop.is_set():
            for mid, data in OVERRIDE.items():
                sender(mid, data)
            time.sleep(0.02)

    t = threading.Thread(target=tx_loop, daemon=True)
    t.start()
    time.sleep(0.5)
    try:
        r = uds.request(bytes.fromhex("1003"))
        print("1003:", r.response.hex().upper() if r.response else "超时")
        _, _, ur = perform_unlock(uds, cfg["security_levels"]["app"], log=rec.event)
        print("unlock:", ur.response.hex().upper() if ur.response else "超时")
        r = uds.request(bytes.fromhex("3101FE01"))
        print("3101FE01:", r.response.hex().upper() if r.response else "超时",
              f"NRC=0x{r.nrc:02X}" if r.nrc is not None else "")
        r = uds.request(bytes.fromhex("1101"))
        print("1101:", r.response.hex().upper() if r.response else "超时")
    finally:
        stop.set()
        transport.stop()
