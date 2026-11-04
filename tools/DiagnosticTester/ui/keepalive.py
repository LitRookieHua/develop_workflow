"""3E80 会话保持：帧构造与周期约束（纯逻辑，Qt 定时器在 session.py）。"""
from __future__ import annotations

from can_driver import CanFrame
from isotp import encode

MIN_PERIOD_MS = 500
MAX_PERIOD_MS = 50000


def keepalive_frame(functional_id: int, is_fd: bool) -> CanFrame:
    """TesterPresent(0x3E 0x80) 单帧：SF 直发 functional_id，不经 IsoTpTransport。

    0x80 抑制正响应，不等待 RX。encode() 自动把 SF 补齐到 8 字节（目标 ECU 要求）。
    """
    data = encode(bytes.fromhex("3E80"), is_fd)[0]
    return CanFrame(functional_id, data, is_fd=is_fd, bitrate_switch=is_fd)


def clamp_period_ms(v: int) -> int:
    return max(MIN_PERIOD_MS, min(MAX_PERIOD_MS, int(v)))
