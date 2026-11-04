"""会话 worker：在独立 QThread 里跑一个可调用对象，结果/异常统一经 done 信号回主线程。"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThread, Signal


class FuncThread(QThread):
    done = Signal(str, object)  # (name, 结果或异常)

    def __init__(self, name: str, fn: Callable, parent=None):
        super().__init__(parent)
        self._name = name
        self._fn = fn

    def run(self):
        try:
            result = self._fn()
        except Exception as e:
            self.done.emit(self._name, e)
        else:
            self.done.emit(self._name, result)
