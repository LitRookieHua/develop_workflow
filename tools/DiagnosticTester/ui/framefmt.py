"""报文页格式化：总线原始帧 → 等宽文本行（无 Qt 依赖，可单测）。"""
from __future__ import annotations

from datetime import datetime

from can_driver import CanFrame


def _frame_type(data: bytes) -> str:
    """ISO-TP 帧类型：首字节高半字节 1=FF 2=CF 3=FC，其余（含 0x00 转义）为 SF。"""
    if not data:
        return "??"
    b0 = data[0]
    if b0 & 0xF0 == 0x10:
        return "FF"
    if b0 & 0xF0 == 0x20:
        return "CF"
    if b0 & 0xF0 == 0x30:
        return "FC"
    return "SF"


def format_frame_line(frame: CanFrame, is_rx: bool,
                      now: datetime | None = None) -> str:
    """[HH:MM:SS.mmm] 方向 CANID 类型 数据字节…（now 仅供测试注入）。"""
    t = now if now is not None else datetime.now()
    ts = t.strftime("%H:%M:%S.%f")[:-3]
    arrow = "RX" if is_rx else "TX"
    data = " ".join(f"{b:02X}" for b in frame.data)
    return f"[{ts}] {arrow} {frame.can_id:03X} {_frame_type(frame.data)} {data}"


def diagnostic_ids(diag: dict) -> frozenset[int]:
    """报文页过滤集合：diagnostic 节的 request/response/functional 三 ID
    （functional 缺省时仅两个）。总线其余流量不进报文页，仅落 BLF。"""
    return frozenset(v for v in (diag.get("request_id"), diag.get("response_id"),
                                 diag.get("functional_id"))
                     if v is not None)
