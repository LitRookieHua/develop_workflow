"""例程运行 Tab：例程列表 + 刷新/浏览/运行/停止 + 结果汇总。"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget,
)


class RoutineTab(QWidget):
    run_requested = Signal(object)  # Path：选中的用例 yaml
    stop_requested = Signal()
    refresh_requested = Signal()
    browse_requested = Signal()
    dem_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[Path] = []
        self._run_dir: Path | None = None
        self._list = QListWidget()
        self._btn_refresh = QPushButton("刷新")
        self._btn_browse = QPushButton("浏览…")
        self._btn_run = QPushButton("运行")
        self._btn_stop = QPushButton("停止")
        self._btn_stop.setEnabled(False)
        self._btn_dem = QPushButton("读DTC")
        self._btn_open = QPushButton("打开运行目录")
        self._btn_open.setEnabled(False)
        self._label = QLabel("（未连接）")
        self._label.setWordWrap(True)

        row = QHBoxLayout()
        for b in (self._btn_refresh, self._btn_browse, self._btn_run, self._btn_stop, self._btn_dem):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(self._btn_open)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("例程（testcase/<项目>/）"))
        lay.addWidget(self._list, 1)
        lay.addLayout(row)
        lay.addWidget(self._label)

        self._btn_refresh.clicked.connect(self.refresh_requested)
        self._btn_browse.clicked.connect(self.browse_requested)
        self._btn_run.clicked.connect(self._on_run)
        self._btn_stop.clicked.connect(self.stop_requested)
        self._btn_dem.clicked.connect(self.dem_requested)
        self._btn_open.clicked.connect(self._open_dir)

    def _on_run(self):
        idx = self._list.currentRow()
        if 0 <= idx < len(self._entries):
            self.run_requested.emit(self._entries[idx])

    def _open_dir(self):
        if self._run_dir is not None and self._run_dir.exists():
            os.startfile(str(self._run_dir))

    def set_entries(self, entries: list[tuple[str, Path]]):
        self._entries = [p for _label, p in entries]
        self._list.clear()
        for label, _p in entries:
            self._list.addItem(label)

    def add_entry(self, path: Path):
        self._entries.append(Path(path))
        self._list.addItem(Path(path).stem)
        self._list.setCurrentRow(self._list.count() - 1)

    def set_running(self, running: bool):
        for b in (self._btn_run, self._btn_refresh, self._btn_browse, self._btn_dem, self._list):
            b.setEnabled(not running)
        self._btn_stop.setEnabled(running)

    def set_dem_busy(self, busy: bool):
        """DTC 读取运行期间只锁读DTC按钮（不动停止按钮，停止只作用于例程）。"""
        self._btn_dem.setEnabled(not busy)

    def set_status(self, text: str):
        self._label.setText(text)

    def set_result(self, counters: dict, run_dir: Path):
        self._run_dir = Path(run_dir)
        self._btn_open.setEnabled(True)
        self._label.setText(
            f"PASS {counters['pass']} / FAIL {counters['fail']}"
            f" / TIMEOUT {counters['timeout']} / 共 {counters['total']}\n"
            f"运行目录：{run_dir}")
