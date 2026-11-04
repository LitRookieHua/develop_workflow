from ui.keepalive import clamp_period_ms, keepalive_frame


def test_keepalive_frame_classic():
    f = keepalive_frame(0x7DF, is_fd=False)
    assert f.can_id == 0x7DF
    assert f.is_fd is False
    assert f.bitrate_switch is False
    assert f.data == bytes([2, 0x3E, 0x80]) + bytes(5)  # SF 补齐到 8 字节


def test_keepalive_frame_fd():
    f = keepalive_frame(0x7DF, is_fd=True)
    assert f.is_fd is True
    assert f.bitrate_switch is True  # FD 帧带 BRS 数据域加速
    assert f.data == bytes([2, 0x3E, 0x80]) + bytes(5)


def test_clamp_period_ms():
    assert clamp_period_ms(2500) == 2500
    assert clamp_period_ms(100) == 500
    assert clamp_period_ms(999999) == 50000
