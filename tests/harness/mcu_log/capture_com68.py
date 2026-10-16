"""COM68 MCU 调试串口采集：原始数据全量落盘 + 控制台回显（插桩日志查看用）。"""
import sys
import time
from pathlib import Path

import serial

OUT = Path(__file__).parent / "logs" / "com68_capture.log"
OUT.parent.mkdir(parents=True, exist_ok=True)


def main():
    baud = int(sys.argv[1]) if len(sys.argv) > 1 else 115200
    ser = serial.Serial("COM68", baud, timeout=1)
    print(f"listening COM68 @ {baud}, ctrl-c to stop")
    with OUT.open("ab") as f:
        while True:
            try:
                data = ser.read(4096)
            except serial.SerialException as e:
                print("serial error:", e)
                break
            if not data:
                continue
            ts = time.strftime("%H:%M:%S")
            text = data.decode("utf-8", errors="replace")
            f.write(text.encode("utf-8", errors="replace"))
            f.flush()
            for line in text.splitlines():
                if line.strip():
                    print(f"[{ts}] {line}")


if __name__ == "__main__":
    main()
