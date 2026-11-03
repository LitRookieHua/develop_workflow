"""单发调试 Tab：TX 输入 + 0x27 安全解锁 + 收发历史。"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

_COLS = ("时间", "TX", "RX", "NRC", "耗时")


class SingleShotTab(QWidget):
    send_requested = Signal(str)    # 原始 hex 输入
    unlock_requested = Signal(str)  # 等级名

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tx = QLineEdit()
        self._tx.setPlaceholderText("如 22F195（回车发送）")
        self._tx.setFont(QFont("Consolas"))
        self._btn_send = QPushButton("发送")
        self._combo_level = QComboBox()
        self._btn_unlock = QPushButton("解锁")

        self._history = QTableWidget(0, len(_COLS))
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
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("安全解锁（0x27）"))
        row2.addWidget(self._combo_level)
        row2.addWidget(self._btn_unlock)
        row2.addStretch(1)
        lay = QVBoxLayout(self)
        lay.addLayout(row1)
        lay.addLayout(row2)
        lay.addWidget(QLabel("收发历史（双击回填）"))
        lay.addWidget(self._history, 1)

        self._btn_send.clicked.connect(self._emit_send)
        self._tx.returnPressed.connect(self._emit_send)
        self._btn_unlock.clicked.connect(self._emit_unlock)

    def _emit_send(self):
        text = self._tx.text().strip()
        if text:
            self.send_requested.emit(text)

    def _emit_unlock(self):
        level = self._combo_level.currentText()
        if level:
            self.unlock_requested.emit(level)

    def _refill(self, row: int, _col: int):
        item = self._history.item(row, 1)
        if item is not None:
            self._tx.setText(item.text())

    def set_levels(self, levels):
        self._combo_level.clear()
        self._combo_level.addItems(sorted(levels))

    def set_busy(self, busy: bool):
        for w in (self._btn_send, self._btn_unlock, self._tx):
            w.setEnabled(not busy)

    def append_history(self, ts: str, tx: str, rx: str, nrc: str, elapsed_ms):
        row = self._history.rowCount()
        self._history.insertRow(row)
        for col, v in enumerate((ts, tx, rx, nrc, f"{elapsed_ms:.0f}ms")):
            self._history.setItem(row, col, QTableWidgetItem(str(v)))
        self._history.scrollToBottom()
