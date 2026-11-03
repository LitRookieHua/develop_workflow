"""主窗口：顶部工具条 + 双 Tab + 底部共享日志 + 状态栏。"""
from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QSplitter, QTabWidget,
    QVBoxLayout, QWidget,
)

from flow import ConfigError, load_testcase, parse_hex_bytes, run_flow
from dem import load_maps, run_dem
from security import UnlockError, perform_unlock
from uds import UdsResult

from .framefmt import format_frame_line
from .routine_tab import RoutineTab
from .scan import scan_configs, scan_routines
from .session import UiSession
from .singleshot_tab import SingleShotTab
from .workers import FuncThread


class MainWindow(QMainWindow):
    log_line = Signal(str)  # worker 线程日志入口（queued 连接回主线程）

    def __init__(self, base_dir: Path, parent=None):
        super().__init__(parent)
        self._base = Path(base_dir)
        self.setWindowTitle("DiagnosticTester")
        self.resize(1000, 680)
        self._flow_thread: FuncThread | None = None
        self._single_thread: FuncThread | None = None
        self._flow_stop: threading.Event | None = None

        self._session = UiSession(self._base)
        self._session.log_line.connect(self._append_log)
        self._session.state_changed.connect(self._on_state_changed)
        self._session.keepalive_failed.connect(self._on_keepalive_failed)
        self._session.frame_received.connect(self._on_frame)

        # 顶部工具条
        self._combo = QComboBox()
        for label, path in scan_configs(self._base / "configs"):
            self._combo.addItem(label, str(path))
        self._btn_connect = QPushButton("连接")
        self._label_conn = QLabel("○ 未连接")
        self._chk_keepalive = QCheckBox("会话保持 3E80")
        self._chk_keepalive.setEnabled(False)
        self._chk_keepalive.setToolTip("功能寻址周期发 3E80，需配置 functional_id")
        self._spin_period = QSpinBox()
        self._spin_period.setRange(500, 50000)
        self._spin_period.setValue(2500)
        self._spin_period.setSuffix(" ms")
        self._spin_period.setEnabled(False)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("配置:"))
        bar.addWidget(self._combo, 1)
        bar.addWidget(self._btn_connect)
        bar.addWidget(self._label_conn)
        bar.addStretch(2)
        bar.addWidget(self._chk_keepalive)
        bar.addWidget(self._spin_period)

        # Tab 区
        self._routine_tab = RoutineTab()
        self._single_tab = SingleShotTab()
        self._single_tab.set_busy(True)  # 未连接
        tabs = QTabWidget()
        tabs.addTab(self._routine_tab, "例程运行")
        tabs.addTab(self._single_tab, "单发调试")

        # 底部：日志/报文 双 Tab（各自独立自动滚动/清空）
        log_page, self._log_view, self._chk_log = self._make_view("日志")
        frame_page, self._frame_view, self._chk_frame = self._make_view("报文")
        view_tabs = QTabWidget()
        view_tabs.addTab(log_page, "日志")
        view_tabs.addTab(frame_page, "报文")

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(tabs)
        splitter.addWidget(view_tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.addLayout(bar)
        lay.addWidget(splitter)
        self.setCentralWidget(central)
        self.statusBar().showMessage("就绪")

        # 信号接线
        self.log_line.connect(self._append_log)
        self._btn_connect.clicked.connect(self._toggle_connect)
        self._chk_keepalive.toggled.connect(self._on_keepalive_toggled)
        self._spin_period.valueChanged.connect(self._on_period_changed)
        self._routine_tab.run_requested.connect(self._run_routine)
        self._routine_tab.stop_requested.connect(self._stop_flow)
        self._routine_tab.refresh_requested.connect(self._refresh_routines)
        self._routine_tab.browse_requested.connect(self._browse_routines)
        self._routine_tab.dem_requested.connect(self._run_dem)
        self._single_tab.send_requested.connect(self._send_single)
        self._single_tab.unlock_requested.connect(self._unlock)

    # ---- 日志 ----
    @staticmethod
    def _make_view(title: str):
        view = QPlainTextEdit()
        view.setReadOnly(True)
        view.setMaximumBlockCount(5000)
        view.setFont(QFont("Consolas"))
        chk = QCheckBox("自动滚动")
        chk.setChecked(True)
        btn = QPushButton("清空")
        row = QHBoxLayout()
        row.addWidget(QLabel(title))
        row.addStretch(1)
        row.addWidget(chk)
        row.addWidget(btn)
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(row)
        lay.addWidget(view)
        btn.clicked.connect(view.clear)
        return page, view, chk

    def _append_log(self, msg: str):
        # dem 分节空行不加时间戳，保持与 CLI rec.blank() 一致的视觉分隔
        self._log_view.appendPlainText(
            f"[{time.strftime('%H:%M:%S')}] {msg}" if msg else "")
        if self._chk_log.isChecked():
            sb = self._log_view.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _on_frame(self, frame, is_rx: bool):
        self._frame_view.appendPlainText(format_frame_line(frame, is_rx))
        if self._chk_frame.isChecked():
            sb = self._frame_view.verticalScrollBar()
            sb.setValue(sb.maximum())

    # ---- 连接 ----
    def _toggle_connect(self):
        if self._session.connected:
            self._session.disconnect()
            return
        path = self._combo.currentData()
        if not path:
            self.statusBar().showMessage("没有可选配置", 5000)
            return
        try:
            self._session.connect(path)
        except (ConfigError, RuntimeError, ValueError) as e:
            QMessageBox.critical(self, "连接失败", str(e))
            self.statusBar().showMessage(f"连接失败：{e}")

    def _on_state_changed(self, connected: bool):
        if connected:
            can = self._session.cfg["can"]
            self._label_conn.setText(
                f"● 已连接 {self._combo.currentText()} · {can['device']} ch{can['channel']}")
            self._btn_connect.setText("断开")
            self._combo.setEnabled(False)
            self._single_tab.set_levels(self._session.cfg["security_levels"])
            self._single_tab.set_busy(False)
            has_fid = self._session.functional_id is not None
            self._chk_keepalive.setEnabled(has_fid)
            self._spin_period.setEnabled(has_fid)
            self._refresh_routines()
            self.statusBar().showMessage(f"日志目录：{self._session.run_dir}")
        else:
            self._label_conn.setText("○ 未连接")
            self._btn_connect.setText("连接")
            self._combo.setEnabled(True)
            self._chk_keepalive.setChecked(False)
            self._chk_keepalive.setEnabled(False)
            self._spin_period.setEnabled(False)
            self._single_tab.set_levels([])
            self._single_tab.set_busy(True)
            self._routine_tab.set_status("（未连接）")

    # ---- 会话保持 ----
    def _on_keepalive_toggled(self, on: bool):
        self._session.set_keepalive(on, period_ms=self._spin_period.value())

    def _on_period_changed(self, value: int):
        if self._chk_keepalive.isChecked():
            self._session.set_keepalive(True, period_ms=value)

    def _on_keepalive_failed(self, msg: str):
        self._chk_keepalive.setChecked(False)
        self.statusBar().showMessage(msg, 10000)

    # ---- 例程运行 ----
    def _refresh_routines(self):
        project = self._session.project
        if project is None:
            self._routine_tab.set_entries([])
            return
        entries = scan_routines(self._base / "testcase", project)
        self._routine_tab.set_entries(entries)
        self._routine_tab.set_status(
            f"{len(entries)} 个例程" if entries
            else "testcase/ 下该项目暂无用例（可点「浏览…」选任意 yaml）")

    def _browse_routines(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择用例 yaml（可多选）",
            str(self._base / "testcase"), "YAML (*.yaml)")
        for p in paths:
            self._routine_tab.add_entry(Path(p))

    def _run_routine(self, path):
        if self._flow_thread is not None or self._single_thread is not None:
            return
        if not self._session.connected:
            self.statusBar().showMessage("请先连接", 5000)
            return
        try:
            tc = load_testcase(str(path), self._session.cfg)
        except ConfigError as e:
            QMessageBox.critical(self, "用例加载失败", str(e))
            return
        tc_path = Path(path).resolve()
        run_dir = new_run_dir_for(tc_path)
        self._append_log(f"运行目录：{run_dir}")
        stop_event = threading.Event()
        self._flow_stop = stop_event
        # 挂起会话 transport：run_flow 自建 pump 独占 driver，避免双 pump 抢响应帧
        self._session.suspend_transport()
        cfg = self._session.cfg
        driver = self._session.driver

        def job():
            return run_flow(cfg, tc, driver, run_dir,
                            log_hook=self.log_line.emit,
                            should_stop=stop_event.is_set,
                            frame_hook=self._session.frame_received.emit)

        self._routine_tab.set_running(True)
        self._routine_tab.set_status(f"运行中：{tc_path.stem}")
        self._single_tab.set_busy(True)
        self._btn_connect.setEnabled(False)
        self._flow_thread = FuncThread("flow", job, self)
        self._flow_thread.done.connect(lambda _n, res: self._flow_done(res, run_dir))
        self._flow_thread.start()

    def _flow_done(self, res, run_dir):
        self._flow_thread = None
        self._flow_stop = None
        self._session.resume_transport()
        self._routine_tab.set_running(False)
        self._single_tab.set_busy(not self._session.connected)
        self._btn_connect.setEnabled(True)
        if isinstance(res, Exception):
            self._routine_tab.set_status(f"运行异常：{res}")
            self._append_log(f"运行异常：{res}")
            return
        self._routine_tab.set_result(res, run_dir)
        ok = res["fail"] == 0 and res["timeout"] == 0
        self.statusBar().showMessage("运行完成" if ok else "存在失败/超时步骤")

    def _stop_flow(self):
        if self._flow_stop is not None:
            self._flow_stop.set()
            self._append_log("已请求停止：当前步骤完成后中止")

    # ---- 单发 ----
    def _send_single(self, text: str):
        if self._single_thread is not None or self._flow_thread is not None:
            return
        if not self._session.connected:
            self.statusBar().showMessage("请先连接", 5000)
            return
        try:
            req = parse_hex_bytes(text, "单发请求")
        except ConfigError as e:
            self.statusBar().showMessage(f"输入错误：{e}", 5000)
            return
        uds = self._session.uds

        def job():
            return uds.request(req)

        self._single_tab.set_busy(True)
        self._single_thread = FuncThread("single", job, self)
        self._single_thread.done.connect(lambda _n, res: self._single_done(req, res))
        self._single_thread.start()

    def _single_done(self, req, res):
        self._single_thread = None
        self._single_tab.set_busy(not self._session.connected)
        ts = time.strftime("%H:%M:%S")
        self._append_log(f"UDS TX: {req.hex().upper()}")
        if isinstance(res, Exception):
            self._single_tab.append_history(ts, req.hex().upper(), f"（异常：{res}）", "", 0)
            self._append_log(f"请求失败：{res}")
            return
        r: UdsResult = res
        rx = r.response.hex().upper() if r.response else "(timeout)"
        nrc = f"0x{r.nrc:02X}" if r.nrc is not None else ""
        self._single_tab.append_history(ts, req.hex().upper(), rx, nrc, r.elapsed_ms)
        self._append_log(
            f"UDS RX: {rx}"
            + (f"（NRC 0x{r.nrc:02X}）" if r.nrc is not None else "")
            + (f"  {r.elapsed_ms:.0f}ms" if r.response else ""))

    # ---- 解锁 ----
    def _unlock(self, level_name: str):
        if self._single_thread is not None or self._flow_thread is not None:
            return
        if not self._session.connected:
            self.statusBar().showMessage("请先连接", 5000)
            return
        level = self._session.cfg["security_levels"][level_name]
        uds = self._session.uds

        def job():
            return perform_unlock(uds, level, log=self.log_line.emit)

        self._single_tab.set_busy(True)
        self._single_thread = FuncThread("unlock", job, self)
        self._single_thread.done.connect(lambda _n, res: self._unlock_done(level_name, res))
        self._single_thread.start()

    def _unlock_done(self, level_name: str, res):
        self._single_thread = None
        self._single_tab.set_busy(not self._session.connected)
        if isinstance(res, UnlockError):
            self._append_log(f"解锁[{level_name}] 失败：{res}")
            self.statusBar().showMessage(f"解锁失败：{res}", 5000)
            return
        if isinstance(res, Exception):
            self._append_log(f"解锁[{level_name}] 异常：{res}")
            self.statusBar().showMessage(f"解锁异常：{res}", 5000)
            return
        seed, _key, result = res
        rx = result.response.hex().upper() if result.response else "超时无响应"
        self._append_log(
            f"UDS RX: {rx}"
            + (f"（NRC 0x{result.nrc:02X}）" if result.nrc is not None else ""))
        self.statusBar().showMessage("解锁成功" if result.ok else "解锁失败")

    # ---- DTC 读取 ----
    def _run_dem(self):
        if self._single_thread is not None or self._flow_thread is not None:
            return
        if not self._session.connected:
            self.statusBar().showMessage("请先连接", 5000)
            return
        cfg_path = Path(self._combo.currentData())
        try:
            maps = load_maps(cfg_path.parent)
        except ConfigError as e:
            QMessageBox.critical(self, "DTC map 加载失败", str(e))
            return
        unlock = self._session.cfg["security_levels"].get("develop")
        uds = self._session.uds

        def job():
            return run_dem(uds, maps, self.log_line.emit, unlock=unlock)

        self._single_tab.set_busy(True)
        self._routine_tab.set_dem_busy(True)
        self._btn_connect.setEnabled(False)
        self._single_thread = FuncThread("dem", job, self)
        self._single_thread.done.connect(lambda _n, res: self._dem_done(res))
        self._single_thread.start()

    def _dem_done(self, res):
        self._single_thread = None
        self._single_tab.set_busy(not self._session.connected)
        self._routine_tab.set_dem_busy(False)
        self._btn_connect.setEnabled(True)
        if isinstance(res, Exception):
            self._append_log(f"DTC 读取异常：{res}")
            self.statusBar().showMessage(f"DTC 读取异常：{res}", 5000)
            return
        self.statusBar().showMessage(
            "DTC 读取完成" if res == 0 else "DTC 读取完成（部分项失败）")

    # ---- 退出 ----
    def closeEvent(self, event):
        if self._flow_thread is not None and self._flow_thread.isRunning():
            if self._flow_stop is not None:
                self._flow_stop.set()
            self._append_log("关闭窗口：等待当前步骤结束（最多 2s）…")
            if not self._flow_thread.wait(2000):
                _detach_later(self._flow_thread)
        if self._single_thread is not None and self._single_thread.isRunning():
            if not self._single_thread.wait(2000):
                _detach_later(self._single_thread)
        self._session.disconnect()
        super().closeEvent(event)


def _detach_later(t: FuncThread) -> None:
    """关窗等待超时：解除父子关系并在线程结束后自毁，避免窗口析构摧毁运行中的线程。"""
    t.setParent(None)
    t.finished.connect(t.deleteLater)


def new_run_dir_for(tc_path: Path) -> Path:
    """与 CLI cmd_run 相同的 run_dir 规则：yaml 上级目录的 logs/<用例名>/ 下按时间戳建目录。"""
    from DiagnosticTester import new_run_dir
    return new_run_dir(tc_path.parent.parent / "logs" / tc_path.stem)
