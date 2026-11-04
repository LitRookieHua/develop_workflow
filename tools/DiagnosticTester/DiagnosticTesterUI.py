"""DiagnosticTester GUI 入口。

用法：python DiagnosticTesterUI.py
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow(base_dir=BASE)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
