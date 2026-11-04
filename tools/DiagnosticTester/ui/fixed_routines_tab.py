"""固定例程 Tab：会话切换 / 安全解锁 / 读取DTC（内置固定动作，非 yaml 用例）。"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget,
)

# 下拉顺序即展示顺序；默认选中扩展会话（解锁/读DTC 等前置步骤最常用）
SESSIONS = (
    ("默认会话 10 01", "1001"),
    ("扩展会话 10 03", "1003"),
    ("编程会话 10 02", "1002"),
)
DEFAULT_SESSION = "1003"


class FixedRoutinesTab(QWidget):
    session_requested = Signal(str)   # 请求 hex（如 "1003"）
    unlock_requested = Signal(str)    # security 等级名
    dem_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._combo_session = QComboBox()
        # 按内容自适应宽度，不随半宽窗口拉伸
        self._combo_session.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._combo_session.setSizePolicy(QSizePolicy.Policy.Maximum,
                                          QSizePolicy.Policy.Fixed)
        for label, req in SESSIONS:
            self._combo_session.addItem(label, req)
        self._combo_session.setCurrentIndex(
            self._combo_session.findData(DEFAULT_SESSION))
        self._btn_session = QPushButton("切换")
        self._combo_level = QComboBox()
        self._combo_level.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._combo_level.setSizePolicy(QSizePolicy.Policy.Maximum,
                                        QSizePolicy.Policy.Fixed)
        self._btn_unlock = QPushButton("解锁")
        self._btn_dem = QPushButton("读取")
        self._btn_dem.setToolTip(
            "10 03 进扩展会话 → develop 解锁 → 19 02 0F + event DID + fimfid")
        self._label = QLabel("（未连接）")
        self._label.setWordWrap(True)

        # 下拉框按内容自适应宽度（不随半宽窗口拉伸）
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("会话切换"))
        r1.addWidget(self._combo_session)
        r1.addWidget(self._btn_session)
        r1.addStretch(1)
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("安全解锁（0x27）"))
        r2.addWidget(self._combo_level)
        r2.addWidget(self._btn_unlock)
        r2.addStretch(1)
        r3 = QHBoxLayout()
        r3.addWidget(QLabel("读取DTC"))
        r3.addWidget(self._btn_dem)
        r3.addStretch(1)
        lay = QVBoxLayout(self)
        lay.addLayout(r1)
        lay.addLayout(r2)
        lay.addLayout(r3)
        lay.addStretch(1)
        lay.addWidget(self._label)

        self._btn_session.clicked.connect(self._emit_session)
        self._btn_unlock.clicked.connect(self._emit_unlock)
        self._btn_dem.clicked.connect(self.dem_requested.emit)

    def _emit_session(self):
        req = self._combo_session.currentData()
        if req:
            self.session_requested.emit(req)

    def _emit_unlock(self):
        level = self._combo_level.currentText()
        if level:
            self.unlock_requested.emit(level)

    def set_levels(self, levels):
        self._combo_level.clear()
        self._combo_level.addItems(sorted(levels))

    def set_busy(self, busy: bool):
        for w in (self._btn_session, self._btn_unlock, self._btn_dem,
                  self._combo_session, self._combo_level):
            w.setEnabled(not busy)

    def set_status(self, text: str):
        self._label.setText(text)
