"""DiagnosticTester GUI 入口（开发期位于 dt_ui/，合并后随 ui/ 移入 DiagnosticTester/）。

用法：python DiagnosticTesterUI.py
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
DT_DIR = BASE.parent / "DiagnosticTester"
for p in (str(DT_DIR), str(BASE)):
    if p not in sys.path:
        sys.path.insert(0, p)

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow(base_dir=DT_DIR)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
