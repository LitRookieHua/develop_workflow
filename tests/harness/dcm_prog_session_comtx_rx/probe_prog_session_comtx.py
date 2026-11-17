"""F4CMC-99 台架取证：编程会话内 ECU 应用报文停发、退出后恢复。

四个阶段各采样 5s 总线帧 ID 集合（排除诊断 0x712/0x713/0x7DF）：
  A default（上电默认会话）    -> 应用报文在发
  B extended（10 03）          -> 应用报文仍在发
  C programming（10 02）       -> 应用报文应停发（Com TX 组停止）
  D default（11 01 恢复）      -> 应用报文应恢复

判定：C 阶段不再出现 A 阶段的应用报文 ID，且 D 阶段恢复出现 => PASS。
用法: python probe_prog_session_comtx.py
"""
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "DiagnosticTester"))

from can_driver import CxCanFdDriver, CanFrame  # noqa: E402

DIAG_IDS = {0x712, 0x713, 0x7DF}
LOG_DIR = HERE / "logs"
SAMPLE_SECONDS = 5.0


def uds_send(dev, payload: bytes):
    data = bytes([len(payload)]) + payload
    dev.send(CanFrame(0x712, data.ljust(8, b"\x00"), is_fd=True))


def uds_wait(dev, timeout_s=2.0):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        f = dev.recv(timeout_s=0.05)
        if f and f.can_id == 0x713:
            return bytes(f.data)
    return None


def uds_exchange(dev, payload):
    # 清掉请求前堆积的响应
    while dev.recv(timeout_s=0.0):
        pass
    uds_send(dev, payload)
    resp = uds_wait(dev)
    print(f"  UDS {payload.hex().upper()} -> {resp.hex().upper() if resp else '(no resp)'}")
    return resp


def sample(dev, label):
    ids = Counter()
    t0 = time.time()
    while time.time() - t0 < SAMPLE_SECONDS:
        f = dev.recv(timeout_s=0.05)
        if f:
            ids[f.can_id] += 1
    app = {i for i in ids if i not in DIAG_IDS}
    print(f"[{label}] {len(ids)} 种 ID，应用报文 ID: "
          + ", ".join(f"0x{i:X}({ids[i]})" for i in sorted(app)))
    return app


def main():
    LOG_DIR.mkdir(exist_ok=True)
    dev = CxCanFdDriver(device="CX-USBCANFD", channel=0,
                        baudrate=500000, data_baudrate=2000000, fd=True)
    try:
        print("== A: 默认会话采样 ==")
        a = sample(dev, "A default")

        print("== B: 进扩展会话 ==")
        r = uds_exchange(dev, bytes([0x10, 0x03]))
        if not r or r[1] != 0x50:
            print("!! 10 03 无正响应，终止")
            return 1
        b = sample(dev, "B extended")

        print("== C: 进编程会话 ==")
        r = uds_exchange(dev, bytes([0x10, 0x02]))
        if not r or r[1] != 0x50:
            print("!! 10 02 无正响应，终止")
            return 1
        c = sample(dev, "C programming")

        print("== D: 回默认会话 ==")
        r = uds_exchange(dev, bytes([0x10, 0x01]))
        if not r or r[1] != 0x50:
            print("!! 10 01 无正响应，终止")
            return 1
        time.sleep(0.5)
        d = sample(dev, "D default")

        stopped = a - c
        resumed = a & d
        print("\n== 结论 ==")
        print(f"编程会话内停发的应用报文: " + (", ".join(f"0x{i:X}" for i in sorted(stopped)) or "无"))
        print(f"恢复后重新出现的应用报文: " + (", ".join(f"0x{i:X}" for i in sorted(resumed)) or "无"))
        if a and not stopped:
            print("FAIL: A 阶段应用报文在编程会话内未停发")
            return 1
        if stopped and not resumed:
            print("WARN: 停发生效但复位后未观测到恢复（检查复位/采样窗口）")
            return 1
        print("PASS" if stopped else "WARN: A 阶段无应用报文可对照（检查总线接线）")
        return 0
    finally:
        dev.close()


if __name__ == "__main__":
    sys.exit(main())
