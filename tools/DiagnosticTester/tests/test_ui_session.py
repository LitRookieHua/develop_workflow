import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication

from ui.session import UiSession

CONFIG = """
can: {device: mock, channel: 0, fd: false, baudrate: 500000}
diagnostic: {request_id: 0x70C, response_id: 0x78C, functional_id: 0x7DF}
timing: {p2_ms: 100, p2star_ms: 1000, step_delay_ms: 0}
"""


def test_session_suspend_resume(tmp_path, monkeypatch):
    # 挂起清空 transport/uds，重建后单发链路仍可用（防 flow 双 pump 抢帧回归）
    _app = QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr("ui.session.LOGS_DIR", tmp_path)
    cfg_path = tmp_path / "proj.yaml"
    cfg_path.write_text(CONFIG, encoding="utf-8")

    s = UiSession(base_dir=tmp_path)
    s.connect(cfg_path)
    assert s.connected
    assert s.uds is not None

    s.suspend_transport()
    assert s._transport is None
    assert s._uds is None
    assert s.connected  # driver/rec 仍在，仅链路挂起

    s.resume_transport()
    assert s._transport is not None
    assert s._uds is not None

    r = s.uds.request(bytes.fromhex("1003"))  # mock 无应答，超时但不抛异常
    assert r.timeout

    s.disconnect()
    assert not s.connected
