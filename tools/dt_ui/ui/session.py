"""连接会话：driver→recorder→transport→uds 生命周期 + 3E80 会话保持。

导入约定：本模块以 tools/dt_ui 为根（from ui.session import ...），且要求
tools/DiagnosticTester 在 sys.path 上（由 UI 入口脚本 DiagnosticTesterUI.py 注入）。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from DiagnosticTester import (LOGS_DIR, build_transport, config_project,
                              make_driver, new_run_dir)
from flow import load_config
from recorder import Recorder
from uds import UdsClient

from .keepalive import keepalive_frame


class UiSession(QObject):
    """一条 UI 连接会话。connect() 起链路并落盘（logs/<项目>_ui_<时间戳>/），
    disconnect() 逆序收尾；日志/状态变化经信号回主线程。"""

    log_line = Signal(str)
    state_changed = Signal(bool)  # True=已连接
    keepalive_failed = Signal(str)

    def __init__(self, base_dir: Path, parent=None):
        super().__init__(parent)
        self._base = Path(base_dir)
        self.cfg = None
        self._project = None
        self._driver = None
        self._rec = None
        self._transport = None
        self._uds = None
        self._timer = QTimer(self)
        self._timer.setInterval(2500)
        self._timer.timeout.connect(self._on_keepalive)

    @property
    def connected(self) -> bool:
        return self._driver is not None

    @property
    def driver(self):
        return self._driver

    @property
    def uds(self):
        return self._uds

    @property
    def project(self) -> str | None:
        return self._project

    @property
    def run_dir(self) -> Path | None:
        return self._rec.run_dir if self._rec is not None else None

    @property
    def is_fd(self) -> bool:
        return bool(self.cfg["can"]["fd"]) if self.cfg else False

    @property
    def functional_id(self):
        return self.cfg["diagnostic"].get("functional_id") if self.cfg else None

    def connect(self, config_path) -> None:
        if self.connected:
            return
        cfg = load_config(config_path)
        driver = make_driver(cfg)
        transport = rec = uds = None
        try:
            project = config_project(config_path)
            run_dir = new_run_dir(LOGS_DIR, prefix=f"{project}_ui")
            rec = Recorder(run_dir)
            transport = build_transport(cfg, driver, rec)
            uds = self._build_uds(cfg, transport)
        except Exception:
            # 半链失败按逆序收尾，不泄漏 pump 线程/记录文件/设备句柄
            if transport is not None:
                transport.stop()
            if rec is not None:
                rec.close()
            driver.close()
            raise
        self.cfg = cfg
        self._project = project
        self._driver, self._rec = driver, rec
        self._transport, self._uds = transport, uds
        self.log_line.emit(f"已连接 {project}，日志目录 {run_dir}")
        self.state_changed.emit(True)

    @staticmethod
    def _build_uds(cfg, transport) -> UdsClient:
        return UdsClient(transport, p2_ms=cfg["timing"]["p2_ms"],
                         p2star_ms=cfg["timing"]["p2star_ms"])

    def suspend_transport(self) -> None:
        """flow 运行前挂起会话 transport：run_flow 会自建 pump 独占 driver RX，
        双 pump 并发会在 driver.recv() 上抢帧导致响应丢失。"""
        if self._transport is not None:
            self._transport.stop()
        self._transport = None
        self._uds = None

    def resume_transport(self) -> None:
        """flow 结束后重建会话链路（单发/解锁继续可用）。"""
        if not self.connected or self._transport is not None:
            return
        try:
            transport = build_transport(self.cfg, self._driver, self._rec)
            self._transport = transport
            self._uds = self._build_uds(self.cfg, transport)
        except Exception as e:
            self.log_line.emit(f"会话链路重建失败：{e}（请断开重连）")

    def disconnect(self) -> None:
        if not self.connected:
            return
        self._timer.stop()
        if self._transport is not None:
            self._transport.stop()
        self._rec.close()
        self._driver.close()
        self._driver = self._rec = self._transport = self._uds = None
        self.cfg = None
        self._project = None
        self.log_line.emit("已断开")
        self.state_changed.emit(False)

    def set_keepalive(self, on: bool, period_ms: int | None = None) -> None:
        if on and (not self.connected or self.functional_id is None):
            return
        if period_ms is not None:
            self._timer.setInterval(period_ms)
        if on:
            self._timer.start()
        else:
            self._timer.stop()

    def _on_keepalive(self):
        # 直发 functional_id 单帧（不经 IsoTpTransport，不碰其收发状态机）；
        # 驱动 _tx_lock 保证与 pump 线程 FC 发送互斥
        frame = keepalive_frame(self.functional_id, self.is_fd)
        try:
            self._driver.send(frame)
        except Exception as e:
            self._timer.stop()
            self.keepalive_failed.emit(f"3E80 发送失败：{e}（会话保持已自动停止）")
            return
        self.log_line.emit(f"会话保持 3E80 → functional 0x{self.functional_id:03X}")
