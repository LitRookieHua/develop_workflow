"""手动发送 Tab：TX hex 输入 + 收发历史。"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .background import make_translucent

_COLS = ("时间", "TX", "RX", "NRC", "耗时")


class SingleShotTab(QWidget):
    send_requested = Signal(str)  # 原始 hex 输入

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tx = QLineEdit()
        self._tx.setPlaceholderText("如 22F195（回车发送）")
        self._tx.setFont(QFont("Consolas"))
        self._btn_send = QPushButton("发送")

        self._history = QTableWidget(0, len(_COLS))
        make_translucent(self._history)
        self._history.setHorizontalHeaderLabels(list(_COLS))
        self._history.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._history.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._history.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        self._history.horizontalHeader().setStretchLastSection(True)
        self._history.verticalHeader().setVisible(False)
        self._history.cellDoubleClicked.connect(self._refill)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("发送（hex）"))
        row1.addWidget(self._tx, 1)
        row1.addWidget(self._btn_send)
        lay = QVBoxLayout(self)
        lay.addLayout(row1)
        lay.addWidget(QLabel("收发历史（双击回填）"))
        lay.addWidget(self._history, 1)

        self._btn_send.clicked.connect(self._emit_send)
        self._tx.returnPressed.connect(self._emit_send)

    def _emit_send(self):
        text = self._tx.text().strip()
        if text:
            self.send_requested.emit(text)

    def _refill(self, row: int, _col: int):
        item = self._history.item(row, 1)
        if item is not None:
            self._tx.setText(item.text())

    def set_busy(self, busy: bool):
        for w in (self._btn_send, self._tx):
            w.setEnabled(not busy)

    def append_history(self, ts: str, tx: str, rx: str, nrc: str, elapsed_ms):
        row = self._history.rowCount()
        self._history.insertRow(row)
        for col, v in enumerate((ts, tx, rx, nrc, f"{elapsed_ms:.0f}ms")):
            self._history.setItem(row, col, QTableWidgetItem(str(v)))
        self._history.scrollToBottom()
