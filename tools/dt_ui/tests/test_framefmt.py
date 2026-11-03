from datetime import datetime

from ui.framefmt import diagnostic_ids, format_frame_line


def _frame(data: bytes, can_id: int = 0x70C):
    from can_driver import CanFrame
    return CanFrame(can_id, data, is_fd=False, bitrate_switch=False)


def test_format_classic_sf():
    line = format_frame_line(_frame(bytes.fromhex("021003")), False,
                             now=datetime(2026, 11, 3, 16, 24, 31, 123000))
    assert line == "[16:24:31.123] TX 70C SF 02 10 03"


def test_format_rx_ff():
    line = format_frame_line(_frame(bytes.fromhex("100E62F195"), 0x78C), True,
                             now=datetime(2026, 11, 3, 16, 24, 31, 125000))
    assert line == "[16:24:31.125] RX 78C FF 10 0E 62 F1 95"


def test_frame_type_cf_fc():
    assert "CF" in format_frame_line(_frame(bytes.fromhex("21AB")), False)
    assert "FC" in format_frame_line(_frame(bytes.fromhex("300000")), False)


def test_frame_type_fd_escape_sf():
    # 0x00 转义字节（FD 长格式 SF）也算 SF
    assert "SF" in format_frame_line(_frame(bytes.fromhex("000922F190")), False)


def test_diagnostic_ids_three():
    ids = diagnostic_ids({"request_id": 0x70E, "response_id": 0x78E,
                          "functional_id": 0x7DF})
    assert ids == frozenset({0x70E, 0x78E, 0x7DF})


def test_diagnostic_ids_no_functional():
    ids = diagnostic_ids({"request_id": 0x70C, "response_id": 0x78C,
                          "functional_id": None})
    assert ids == frozenset({0x70C, 0x78C})
