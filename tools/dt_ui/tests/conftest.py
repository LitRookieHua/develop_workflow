import sys
from pathlib import Path

UI_DIR = Path(__file__).resolve().parents[1]
DT_DIR = UI_DIR.parent / "DiagnosticTester"
for p in (str(DT_DIR), str(UI_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)
