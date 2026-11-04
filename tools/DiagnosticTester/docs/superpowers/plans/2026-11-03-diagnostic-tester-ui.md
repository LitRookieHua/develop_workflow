# DiagnosticTester PySide6 UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 DiagnosticTester 新增 PySide6 GUI（配置选择/例程运行/单发调试/3E80 会话保持/共享日志），CLI 零破坏，在 `tools/dt_ui/` + `feature/dt-ui` 分支开发，完成后合并进 `tools/DiagnosticTester/`。

**Architecture:** UI 作为新入口复用 DiagnosticTester 全部底层模块（flow/isotp/uds/security/can_driver/recorder）。唯一底层改动是 `run_flow` 增加两个可选参数（`log_hook`/`should_stop`，缺省行为与 CLI 完全一致）。线程模型：Qt 主线程（UI + 3E80 QTimer 直发 functional 单帧）+ 既有 pump 线程 + 每操作一个短命 FuncThread（结果经 Qt signal 队列回主线程）。

**Tech Stack:** Python 3 (64-bit) + PySide6 + pytest（纯逻辑单测不起 Qt 事件循环，UI 层走 example_mock 手动冒烟）。

**Spec:** `docs/superpowers/specs/2026-11-03-diagnostic-tester-ui-design.md`（布局稿见仓库 `.superpowers/brainstorm/10108-1793685042/content/`，已 gitignore）

**约定（全程有效）：**
- 所有路径以 `tools/` 为根：`DiagnosticTester/`（现有工具）、`dt_ui/`（开发期新目录）
- 所有 git 命令在 `D:\Workspace\01_Projects\02_Src\11_AI\develop_workflow` 仓库根或其子目录执行
- commit 全英文，格式对齐仓库惯例（`feat(diag_test): …` / `feat(dt_ui): …`）
- 纯逻辑（scan/keepalive/run_flow 新参数）走 TDD；Qt 控件层（session/workers/tabs/main_window）语法检查 + 手动冒烟（Task 12），不起 pytest-qt

---

### Task 1: 分支与开发骨架

**Files:**
- Create: `tools/dt_ui/ui/__init__.py`（空文件）
- Create: `tools/dt_ui/tests/conftest.py`

- [ ] **Step 1: 建分支与目录**

```bash
cd "D:\Workspace\01_Projects\02_Src\11_AI\develop_workflow"
git checkout -b feature/dt-ui
mkdir -p tools/dt_ui/ui tools/dt_ui/tests
```

- [ ] **Step 2: 安装 PySide6**

```bash
python -m pip install "PySide6>=6.6"
```

Expected: 安装成功（约 200MB，仅本机，不改 requirements.txt——合并期 Task 13 才改）。

- [ ] **Step 3: 写 conftest（dt_ui 测试的导入引导）**

`tools/dt_ui/tests/conftest.py`：

```python
import sys
from pathlib import Path

UI_DIR = Path(__file__).resolve().parents[1]
DT_DIR = UI_DIR.parent / "DiagnosticTester"
for p in (str(DT_DIR), str(UI_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)
```

`tools/dt_ui/ui/__init__.py`：空文件（Write 空内容）。

- [ ] **Step 4: 提交**

```bash
git add tools/dt_ui/
git commit -m "feat(dt_ui): scaffold UI dev folder with import bootstrap"
```

---

### Task 2: run_flow 新参数 log_hook / should_stop

**Files:**
- Modify: `tools/DiagnosticTester/flow.py:253-281`（函数签名 + log 闭包 + 步骤循环头）
- Test: `tools/DiagnosticTester/tests/test_run_flow.py`（追加）

- [ ] **Step 1: 写失败测试**

在 `tools/DiagnosticTester/tests/test_run_flow.py` 末尾追加（沿用文件既有 `load()`/`MockCanDriver` 模式）：

```python
def test_log_hook_tees_events(tmp_path):
    # log_hook 与 run.log 落盘同时发生（tee 而非替代），事件顺序完整
    cfg, tc = load(tmp_path)
    mock = MockCanDriver()
    mock.on_send = lambda f: mock.push_rx(0x78C, bytes([4]) + bytes.fromhex("50030032"))
    events = []
    summary = run_flow(cfg, tc, mock, tmp_path, log_hook=events.append)
    assert summary == {"total": 2, "pass": 2, "fail": 0, "timeout": 0}
    assert any("Flow start" in e for e in events)
    assert any("UDS TX: 1003" in e for e in events)
    assert any("Result: PASS" in e for e in events)
    assert (tmp_path / "run.log").exists()  # hook 不影响落盘


def test_should_stop_before_any_step(tmp_path):
    # 每步开始前检查：恒 True → 一步不发，汇总全 0
    cfg, tc = load(tmp_path)
    mock = MockCanDriver()
    summary = run_flow(cfg, tc, mock, tmp_path, should_stop=lambda: True)
    assert summary == {"total": 0, "pass": 0, "fail": 0, "timeout": 0}
    assert mock.sent == []


def test_should_stop_between_steps(tmp_path):
    # 第一步前 False、第二步前 True：第一步照常执行并 PASS，第二步不再发
    cfg, tc = load(tmp_path)
    mock = MockCanDriver()
    mock.on_send = lambda f: mock.push_rx(0x78C, bytes([4]) + bytes.fromhex("50030032"))
    calls = {"n": 0}

    def should_stop():
        calls["n"] += 1
        return calls["n"] > 1

    summary = run_flow(cfg, tc, mock, tmp_path, should_stop=should_stop)
    assert summary == {"total": 1, "pass": 1, "fail": 0, "timeout": 0}
    assert len(mock.sent) == 1
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd tools/DiagnosticTester
python -m pytest tests/test_run_flow.py -v -k "log_hook or should_stop"
```

Expected: 3 个 FAIL（`TypeError: run_flow() got an unexpected keyword argument 'log_hook'`）。

- [ ] **Step 3: 改 flow.py**

`tools/DiagnosticTester/flow.py` 中 `run_flow` 签名与 docstring（第 253-254 行附近）：

```python
def run_flow(cfg: dict, testcase: dict, driver, run_dir, log_hook=None,
             should_stop=None):
    """执行流程，返回汇总 dict（total/pass/fail/timeout）。driver 为已就绪的 CanDriver。

    log_hook(msg)：事件 tee 回调，与 run.log 落盘同时发生（UI 日志流用，缺省不启用）。
    should_stop()：每步开始前检查，True 则中止流程，已执行步骤照常汇总（UI 停止按钮用）。
    两参数均可选，缺省时行为与原 CLI 完全一致。
    """
```

函数体内 `log` 闭包（`with Recorder(run_dir) as rec:` 之后、`def tap` 附近）改为：

```python
        def log(msg):
            rec.event(msg)
            if log_hook is not None:
                log_hook(msg)
```

步骤循环头（`for i, step in enumerate(steps, 1):` 之后、`counters["total"] += 1` 之前）插入：

```python
                if should_stop is not None and should_stop():
                    log("Flow stopped by request, aborting before next step")
                    break
```

- [ ] **Step 4: 跑新旧测试全部通过**

```bash
cd tools/DiagnosticTester
python -m pytest tests/ -v
```

Expected: 全部 PASS（含既有用例，证明缺省行为不变）。

- [ ] **Step 5: 提交**

```bash
git add tools/DiagnosticTester/flow.py tools/DiagnosticTester/tests/test_run_flow.py
git commit -m "feat(diag_test): add log_hook and should_stop options to run_flow"
```

---

### Task 3: ui/scan.py — scan_configs

**Files:**
- Create: `tools/dt_ui/ui/scan.py`
- Test: `tools/dt_ui/tests/test_scan.py`

- [ ] **Step 1: 写失败测试**

`tools/dt_ui/tests/test_scan.py`：

```python
from ui.scan import scan_configs


def test_scan_configs_root_and_nested(tmp_path):
    cfg = tmp_path / "configs"
    (cfg / "n60").mkdir(parents=True)
    (cfg / "n60" / "n60_zlg.yaml").write_text("can: {}", encoding="utf-8")
    (cfg / "n60" / "n60_cx.yaml").write_text("can: {}", encoding="utf-8")
    (cfg / "n60" / "dtc_map.yaml").write_text("{}", encoding="utf-8")  # map 排除
    (cfg / "example_mock.yaml").write_text("can: {}", encoding="utf-8")
    entries = scan_configs(cfg)
    labels = [label for label, _p in entries]
    assert labels == ["example_mock", "n60/n60_cx", "n60/n60_zlg"]
    assert entries[1][1] == cfg / "n60" / "n60_cx.yaml"


def test_scan_configs_excludes_map_files(tmp_path):
    cfg = tmp_path / "configs"
    cfg.mkdir()
    for name in ("dtc_map.yaml", "event_map.yaml", "fimfid_map.yaml", "dem_dids.yaml"):
        (cfg / name).write_text("{}", encoding="utf-8")
    assert scan_configs(cfg) == []


def test_scan_configs_missing_dir(tmp_path):
    assert scan_configs(tmp_path / "nope") == []
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd tools/dt_ui
python -m pytest tests/test_scan.py -v
```

Expected: FAIL（`ModuleNotFoundError: No module named 'scan'`）。

- [ ] **Step 3: 写实现**

`tools/dt_ui/ui/scan.py`：

```python
"""纯逻辑扫描：configs 配置列表与 testcase 例程树（无 Qt 依赖，可单测）。"""
from __future__ import annotations

from pathlib import Path

# dem 子命令的 map 文件不是项目配置，扫描时排除
MAP_FILES = {"dtc_map.yaml", "event_map.yaml", "fimfid_map.yaml", "dem_dids.yaml"}


def scan_configs(configs_dir) -> list[tuple[str, Path]]:
    """扫 configs/ 全部配置 yaml（含子目录），返回 (显示名, 路径) 列表。

    显示名 = 相对 configs 的路径去 .yaml（正斜杠，如 n60/n60_cx、example_mock），
    map 文件排除，按显示名排序。
    """
    root = Path(configs_dir)
    out: list[tuple[str, Path]] = []
    if not root.is_dir():
        return out
    for p in root.rglob("*.yaml"):
        if p.name in MAP_FILES:
            continue
        rel = p.relative_to(root).with_suffix("")
        out.append((rel.as_posix(), p))
    return sorted(out)


def scan_routines(testcase_root, project: str) -> list[tuple[str, Path]]:
    """扫 testcase/<项目>/ 下全部用例 yaml（含子目录），返回 (显示名, 路径) 列表。

    显示名 = 相对 testcase_root/<项目> 的路径去 .yaml；项目目录不存在返回 []。
    """
    root = Path(testcase_root)
    base = root / project
    if not base.is_dir():
        return []
    out = []
    for p in base.rglob("*.yaml"):
        rel = p.relative_to(base).with_suffix("")
        out.append((rel.as_posix(), p))
    return sorted(out)
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd tools/dt_ui
python -m pytest tests/test_scan.py -v
```

Expected: 3 PASS。

- [ ] **Step 5: 提交**

```bash
git add tools/dt_ui/ui/scan.py tools/dt_ui/tests/test_scan.py
git commit -m "feat(dt_ui): add config and testcase scanning helpers"
```

---

### Task 4: ui/scan.py — scan_routines 测试

**Files:**
- Test: `tools/dt_ui/tests/test_scan.py`（追加）

- [ ] **Step 1: 追加失败测试**

`tools/dt_ui/tests/test_scan.py` 追加（import 行改为 `from ui.scan import scan_configs, scan_routines`）：

```python
def test_scan_routines_lists_yaml_recursive(tmp_path):
    tc = tmp_path / "testcase"
    (tc / "n60" / "smoke_cycle305").mkdir(parents=True)
    (tc / "n60" / "smoke_cycle305" / "smoke_cycle305.yaml").write_text("steps: []", encoding="utf-8")
    (tc / "n60" / "27unlock.yaml").write_text("steps: []", encoding="utf-8")
    entries = scan_routines(tc, "n60")
    labels = [label for label, _p in entries]
    assert labels == ["27unlock", "smoke_cycle305/smoke_cycle305"]
    assert entries[0][1] == tc / "n60" / "27unlock.yaml"


def test_scan_routines_missing_project(tmp_path):
    (tmp_path / "testcase").mkdir()
    assert scan_routines(tmp_path / "testcase", "nope") == []
```

- [ ] **Step 2: 跑测试确认通过**

```bash
cd tools/dt_ui
python -m pytest tests/test_scan.py -v
```

Expected: 5 PASS（scan_routines 实现已在 Task 3 一并写入，此处验证行为）。

- [ ] **Step 3: 提交**

```bash
git add tools/dt_ui/tests/test_scan.py
git commit -m "test(dt_ui): cover recursive testcase scanning"
```

---

### Task 5: ui/keepalive.py — 3E80 帧构造

**Files:**
- Create: `tools/dt_ui/ui/keepalive.py`
- Test: `tools/dt_ui/tests/test_keepalive.py`

- [ ] **Step 1: 写失败测试**

`tools/dt_ui/tests/test_keepalive.py`：

```python
from ui.keepalive import clamp_period_ms, keepalive_frame


def test_keepalive_frame_classic():
    f = keepalive_frame(0x7DF, is_fd=False)
    assert f.can_id == 0x7DF
    assert f.is_fd is False
    assert f.bitrate_switch is False
    assert f.data == bytes([2, 0x3E, 0x80]) + bytes(5)  # SF 补齐到 8 字节


def test_keepalive_frame_fd():
    f = keepalive_frame(0x7DF, is_fd=True)
    assert f.is_fd is True
    assert f.bitrate_switch is True  # FD 帧带 BRS 数据域加速
    assert f.data == bytes([2, 0x3E, 0x80]) + bytes(5)


def test_clamp_period_ms():
    assert clamp_period_ms(2500) == 2500
    assert clamp_period_ms(100) == 500
    assert clamp_period_ms(999999) == 50000
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd tools/dt_ui
python -m pytest tests/test_keepalive.py -v
```

Expected: FAIL（`ModuleNotFoundError: No module named 'keepalive'`）。

- [ ] **Step 3: 写实现**

`tools/dt_ui/ui/keepalive.py`：

```python
"""3E80 会话保持：帧构造与周期约束（纯逻辑，Qt 定时器在 session.py）。"""
from __future__ import annotations

from can_driver import CanFrame
from isotp import encode

MIN_PERIOD_MS = 500
MAX_PERIOD_MS = 50000


def keepalive_frame(functional_id: int, is_fd: bool) -> CanFrame:
    """TesterPresent(0x3E 0x80) 单帧：SF 直发 functional_id，不经 IsoTpTransport。

    0x80 抑制正响应，不等待 RX。encode() 自动把 SF 补齐到 8 字节（目标 ECU 要求）。
    """
    data = encode(bytes.fromhex("3E80"), is_fd)[0]
    return CanFrame(functional_id, data, is_fd=is_fd, bitrate_switch=is_fd)


def clamp_period_ms(v: int) -> int:
    return max(MIN_PERIOD_MS, min(MAX_PERIOD_MS, int(v)))
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd tools/dt_ui
python -m pytest tests/test_keepalive.py -v
```

Expected: 3 PASS。

- [ ] **Step 5: 提交**

```bash
git add tools/dt_ui/ui/keepalive.py tools/dt_ui/tests/test_keepalive.py
git commit -m "feat(dt_ui): add 3E80 keepalive frame builder"
```

---

### Task 6: ui/session.py — 连接会话

**Files:**
- Create: `tools/dt_ui/ui/session.py`（Qt 控件层，无单测，Task 12 冒烟覆盖）

- [ ] **Step 1: 写实现**

`tools/dt_ui/ui/session.py`：

```python
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
            uds = UdsClient(transport, p2_ms=cfg["timing"]["p2_ms"],
                            p2star_ms=cfg["timing"]["p2star_ms"])
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
```

- [ ] **Step 2: 语法检查**

```bash
cd tools/dt_ui
python -m py_compile ui/session.py
```

Expected: 无输出（编译通过）。

- [ ] **Step 3: 提交**

```bash
git add tools/dt_ui/ui/session.py
git commit -m "feat(dt_ui): add UI connection session with keepalive timer"
```

---

### Task 7: ui/workers.py — FuncThread

**Files:**
- Create: `tools/dt_ui/ui/workers.py`（Qt 控件层，冒烟覆盖）

- [ ] **Step 1: 写实现**

`tools/dt_ui/ui/workers.py`：

```python
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
```

- [ ] **Step 2: 语法检查**

```bash
cd tools/dt_ui
python -m py_compile ui/workers.py
```

- [ ] **Step 3: 提交**

```bash
git add tools/dt_ui/ui/workers.py
git commit -m "feat(dt_ui): add FuncThread worker for background requests"
```

---

### Task 8: ui/routine_tab.py — 例程运行 Tab

**Files:**
- Create: `tools/dt_ui/ui/routine_tab.py`（Qt 控件层，冒烟覆盖）

- [ ] **Step 1: 写实现**

`tools/dt_ui/ui/routine_tab.py`：

```python
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
        self._btn_open = QPushButton("打开运行目录")
        self._btn_open.setEnabled(False)
        self._label = QLabel("（未连接）")
        self._label.setWordWrap(True)

        row = QHBoxLayout()
        for b in (self._btn_refresh, self._btn_browse, self._btn_run, self._btn_stop):
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
        for b in (self._btn_run, self._btn_refresh, self._btn_browse, self._list):
            b.setEnabled(not running)
        self._btn_stop.setEnabled(running)

    def set_status(self, text: str):
        self._label.setText(text)

    def set_result(self, counters: dict, run_dir: Path):
        self._run_dir = Path(run_dir)
        self._btn_open.setEnabled(True)
        self._label.setText(
            f"PASS {counters['pass']} / FAIL {counters['fail']}"
            f" / TIMEOUT {counters['timeout']} / 共 {counters['total']}\n"
            f"运行目录：{run_dir}")
```

- [ ] **Step 2: 语法检查**

```bash
cd tools/dt_ui
python -m py_compile ui/routine_tab.py
```

- [ ] **Step 3: 提交**

```bash
git add tools/dt_ui/ui/routine_tab.py
git commit -m "feat(dt_ui): add routine run tab widget"
```

---

### Task 9: ui/singleshot_tab.py — 单发调试 Tab

**Files:**
- Create: `tools/dt_ui/ui/singleshot_tab.py`（Qt 控件层，冒烟覆盖）

- [ ] **Step 1: 写实现**

`tools/dt_ui/ui/singleshot_tab.py`：

```python
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
```

- [ ] **Step 2: 语法检查**

```bash
cd tools/dt_ui
python -m py_compile ui/singleshot_tab.py
```

- [ ] **Step 3: 提交**

```bash
git add tools/dt_ui/ui/singleshot_tab.py
git commit -m "feat(dt_ui): add single-shot debug tab widget"
```

---

### Task 10: ui/main_window.py — 主窗口

**Files:**
- Create: `tools/dt_ui/ui/main_window.py`（Qt 控件层，冒烟覆盖）

- [ ] **Step 1: 写实现**

`tools/dt_ui/ui/main_window.py`：

```python
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
from security import UnlockError, perform_unlock
from uds import UdsResult

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

        # 底部共享日志
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(5000)
        self._log_view.setFont(QFont("Consolas"))
        self._chk_autoscroll = QCheckBox("自动滚动")
        self._chk_autoscroll.setChecked(True)
        self._btn_clear = QPushButton("清空")
        log_row = QHBoxLayout()
        log_row.addWidget(QLabel("Log"))
        log_row.addStretch(1)
        log_row.addWidget(self._chk_autoscroll)
        log_row.addWidget(self._btn_clear)
        log_panel = QWidget()
        log_lay = QVBoxLayout(log_panel)
        log_lay.setContentsMargins(0, 0, 0, 0)
        log_lay.addLayout(log_row)
        log_lay.addWidget(self._log_view)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(tabs)
        splitter.addWidget(log_panel)
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
        self._btn_clear.clicked.connect(self._log_view.clear)
        self._routine_tab.run_requested.connect(self._run_routine)
        self._routine_tab.stop_requested.connect(self._stop_flow)
        self._routine_tab.refresh_requested.connect(self._refresh_routines)
        self._routine_tab.browse_requested.connect(self._browse_routines)
        self._single_tab.send_requested.connect(self._send_single)
        self._single_tab.unlock_requested.connect(self._unlock)

    # ---- 日志 ----
    def _append_log(self, msg: str):
        self._log_view.appendPlainText(f"[{time.strftime('%H:%M:%S')}] {msg}")
        if self._chk_autoscroll.isChecked():
            sb = self._log_view.verticalScrollBar()
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
        cfg = self._session.cfg
        driver = self._session.driver

        def job():
            return run_flow(cfg, tc, driver, run_dir,
                            log_hook=self.log_line.emit,
                            should_stop=stop_event.is_set)

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
```

- [ ] **Step 2: 语法检查**

```bash
cd tools/dt_ui
python -m py_compile ui/main_window.py
```

- [ ] **Step 3: 提交**

```bash
git add tools/dt_ui/ui/main_window.py
git commit -m "feat(dt_ui): add main window wiring toolbar tabs and log panel"
```

---

### Task 11: 入口 DiagnosticTesterUI.py

**Files:**
- Create: `tools/dt_ui/DiagnosticTesterUI.py`

- [ ] **Step 1: 写入口**

`tools/dt_ui/DiagnosticTesterUI.py`：

```python
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
```

- [ ] **Step 2: 导入冒烟（不起事件循环）**

```bash
cd tools/dt_ui
python -c "import DiagnosticTesterUI; print('import ok')"
```

Expected: `import ok`（PySide6 与底层模块全部可导入，无循环导入）。

- [ ] **Step 3: 提交**

```bash
git add tools/dt_ui/DiagnosticTesterUI.py
git commit -m "feat(dt_ui): add GUI entry point DiagnosticTesterUI"
```

---

### Task 12: README/requirements/手动冒烟验收

**Files:**
- Modify: `tools/DiagnosticTester/requirements.txt`
- Modify: `tools/DiagnosticTester/README.md`（文首「快速上手」之后新增 UI 章节）
- Create: `tools/DiagnosticTester/testcase/example_mock/ui_smoke.yaml`（本地用例，testcase/ 已 gitignore 不入库）

- [ ] **Step 1: requirements.txt 追加 PySide6**

`tools/DiagnosticTester/requirements.txt` 末尾追加一行：

```
PySide6>=6.6
```

- [ ] **Step 2: README 增加 UI 章节**

在 `tools/DiagnosticTester/README.md` 的「## 快速上手」小节之后插入：

```markdown
## UI 图形界面

    python -m pip install -r requirements.txt
    python DiagnosticTesterUI.py

- 工具条选配置（扫 `configs/`，一项即确定项目+卡型+诊断参数）→ 点「连接」
- 双 Tab：**例程运行**（扫 `testcase/<项目>/`，也可靠「浏览…」选任意 yaml）/
  **单发调试**（hex 收发 + 0x27 安全解锁，类 chat）
- 底部共享 Log 面板；会话保持 3E80：连接后可开关、周期可调（默认 2500ms，
  功能寻址直发、需配置 `functional_id`）
- 例程运行产物落盘规则与 CLI `run` 一致；连接会话另落盘
  `logs/<项目>_ui_<时间戳>/`（run.log/result.csv/trace.blf）
- CLI 六命令不受影响；「运行中」时单发/解锁/换配置被禁用，「停止」在当前步完成后中止
```

- [ ] **Step 3: 准备 mock 冒烟用例**

`tools/DiagnosticTester/testcase/example_mock/ui_smoke.yaml`（功能寻址步骤 mock 无需应答即 PASS）：

```yaml
steps:
  - {name: 功能寻址探测, request: "1003", addressing: functional}
on_fail: continue
```

- [ ] **Step 4: 手动冒烟（example_mock 配置，免硬件）**

```bash
cd tools/dt_ui
python DiagnosticTesterUI.py
```

按清单逐项验收（mock 驱动无 ECU 应答，单发/解锁的「超时/失败」是预期链路验证）：

- [ ] 窗口打开：工具条/双 Tab/底部 Log/状态栏齐全，配置下拉含 `example_mock`
- [ ] 选 `example_mock` → 连接 → 状态 `● 已连接`，状态栏显示 `logs/example_mock_ui_<ts>/`
- [ ] 勾选 3E80 → Log 每 2.5s 出现「会话保持 3E80 → functional 0x7DF」；调周期立即生效
- [ ] 例程 Tab 刷新 → `ui_smoke` 可见 → 运行 → 汇总 `PASS 1 / FAIL 0 / TIMEOUT 0 / 共 1`，「打开运行目录」能开 `testcase/logs/ui_smoke/<ts>/`
- [ ] 运行中：单发/解锁/连接按钮禁用；点停止 → 当前步完成后中止且汇总正常
- [ ] 单发输入 `22F195` 回车 → 历史表新增行 `TX=22F195 RX=(timeout)`（mock 无应答，预期）
- [ ] 单发输入 `XYZ` → 状态栏「输入错误」提示，历史不新增
- [ ] 解锁 `develop` → Log 出现种子请求记录 → 「解锁失败：seed request timeout」（预期）
- [ ] 双击历史行 → TX 回填
- [ ] 断开 → 状态 `○ 未连接`、3E80 停、单发禁用；`logs/example_mock_ui_<ts>/` 下三个产物文件齐全
- [ ] 关窗：无报错退出，进程结束（任务管理器确认 python 进程消失）

- [ ] **Step 5: 全量测试**

```bash
cd tools/DiagnosticTester
python -m pytest tests/ -v
cd ../dt_ui
python -m pytest tests/ -v
```

Expected: 两处全 PASS。

- [ ] **Step 6: 提交**

```bash
git add tools/DiagnosticTester/requirements.txt tools/DiagnosticTester/README.md
git commit -m "feat(diag_test): document GUI entry and add PySide6 dependency"
```

---

### Task 13: 合并回 DiagnosticTester

**Files:**
- Move: `tools/dt_ui/DiagnosticTesterUI.py` → `tools/DiagnosticTester/DiagnosticTesterUI.py`
- Move: `tools/dt_ui/ui/` → `tools/DiagnosticTester/ui/`
- Move: `tools/dt_ui/tests/test_scan.py` → `tools/DiagnosticTester/tests/test_ui_scan.py`
- Move: `tools/dt_ui/tests/test_keepalive.py` → `tools/DiagnosticTester/tests/test_ui_keepalive.py`
- Delete: `tools/dt_ui/`（其余：conftest 不再需要——DiagnosticTester/tests/conftest.py 已做同款引导）
- Modify: `tools/DiagnosticTester/DiagnosticTesterUI.py`（去掉跨目录 sys.path 引导）

- [ ] **Step 1: 移动文件（git mv 保留历史）**

```bash
cd "D:\Workspace\01_Projects\02_Src\11_AI\develop_workflow"
git mv tools/dt_ui/DiagnosticTesterUI.py tools/DiagnosticTester/DiagnosticTesterUI.py
git mv tools/dt_ui/ui tools/DiagnosticTester/ui
git mv tools/dt_ui/tests/test_scan.py tools/DiagnosticTester/tests/test_ui_scan.py
git mv tools/dt_ui/tests/test_keepalive.py tools/DiagnosticTester/tests/test_ui_keepalive.py
git rm tools/dt_ui/tests/conftest.py
```

残留空目录 `tools/dt_ui/` 手工删除（git 不跟踪空目录）。

- [ ] **Step 2: 调整入口 sys.path（同目录后无需跨目录引导）**

`tools/DiagnosticTester/DiagnosticTesterUI.py` 头部（docstring 之后的 BASE/DT_DIR 段）替换为：

```python
BASE = Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
```

同时 docstring 中的「开发期位于 dt_ui/，合并后随 ui/ 移入 DiagnosticTester/」一句删除。

- [ ] **Step 3: 全量测试（合并形态）**

```bash
cd tools/DiagnosticTester
python -m pytest tests/ -v
```

Expected: 全 PASS（含新 `test_ui_scan.py` / `test_ui_keepalive.py`，由既有 conftest 引导导入）。

- [ ] **Step 4: 合并形态 UI 启动冒烟**

```bash
cd tools/DiagnosticTester
python -c "import DiagnosticTesterUI; print('import ok')"
python DiagnosticTesterUI.py
```

Expected: 窗口正常打开，选 `example_mock` 连接走通（同 Task 12 清单快速复查 3 项：连接/3E80/单发）。

- [ ] **Step 5: 提交并合回 master**

```bash
git add -A tools/DiagnosticTester tools/dt_ui
git commit -m "feat(diag_test): merge dt_ui GUI into DiagnosticTester"
git checkout master
git merge --no-ff feature/dt-ui -m "merge feature/dt-ui: PySide6 GUI for DiagnosticTester"
python -m pytest tools/DiagnosticTester/tests/ -q
```

Expected: 合并完成、master 上全量测试通过。`feature/dt-ui` 分支保留（不删，用户确认后处置）。

- [ ] **Step 6: 汇报**

向用户报告：合并完成、测试结果、冒烟结论；询问是否 push 远端与是否删除 feature 分支（均需用户确认，不自行执行）。

---

## Self-Review 记录

- **Spec 覆盖**：§1 架构/合并流程→Task 1/13；§2 线程模型→Task 6/7/10；§3 界面结构→Task 8/9/10；§4 功能行为（连接/例程/单发/3E80）→Task 6/10/12；§5 run_flow 改动→Task 2；§6 错误处理→Task 6/10（弹窗/状态栏/信号）+ Task 10 closeEvent；§7 测试→Task 2-5/12/13；§8 非目标未引入。
- **占位符**：无 TBD/TODO；所有代码步骤均含完整代码。
- **类型一致性**：`scan_configs`/`scan_routines` 返回 `list[tuple[str, Path]]`（Task 3/4 测试与 Task 10 使用一致）；`keepalive_frame(functional_id, is_fd) -> CanFrame`（Task 5/6 一致）；`FuncThread(name, fn, parent)` + `done(str, object)`（Task 7/10 一致）；`UiSession.cfg/driver/uds/project/functional_id/is_fd/run_dir`（Task 6 定义与 Task 10 使用一致）；`RoutineTab.set_entries/add_entry/set_running/set_status/set_result`、`SingleShotTab.set_levels/set_busy/append_history`（Task 8/9 定义与 Task 10 使用一致）。

---

## 追加任务（2026-11-03 用户反馈与新需求）

原计划 T1–T13 执行中追加的任务，记录于本节（详细规格见设计文档修订处）：

- **T14（1466a17）**：`run_flow` / `build_transport` 增加可选 `frame_hook`（原始帧
  tee，与 recorder 同步），CLI 缺省行为不变
- **T15（56c5e27）**：`ui/framefmt.py` 原始 CAN 帧行格式化（纯逻辑，SF/FF/CF/FC
  分类，FD 0x00 转义按 SF）
- **T14b（c84da1f）**：`dem.run_dem` 增加可选 `unlock` 参数：10 03 后、DTC 读取前
  执行 perform_unlock（失败不阻断，退出码 1）
- **T16（c5a3387 + e7fdd10）**：底部「日志/报文」双 Tab（原始帧视图，不做 UDS 转换）；
  例程 Tab「读DTC」按钮（读DTC/连接按钮任务期间禁用；3E80 同步落 BLF）
- **459d9e0**：修复双 pump 抢帧——例程运行前 `suspend_transport`、结束后
  `resume_transport`（UI 跑例程间歇超时、CLI 全过的根因）
- **T17（本次提交）**：README UI 章节 + 设计文档修订同步（报文页/读DTC/
  suspend-resume/改动清单）

追加任务全部经两阶段审查（规格合规 + 代码质量）；质量审查 APPROVED，其 Important
项（dem 任务期间可断开）与 Minor #1/#4/#5 已随 e7fdd10 修复。
- **6f1d877**：报文页按 diagnostic 三 ID 过滤（用户反馈：仅显示诊断相关报文；
  isotp tap 在 rx_id 过滤前回调，故在 UI 层过滤，BLF 仍全量记录）
- **T18（本次提交）**：主窗口背景图 + 窗口图标（用户反馈：`image/
  shenlilinghua.png`；cover 缩放绘制、缺失静默降级，图片落位
  DiagnosticTester/image/ 以便合并后路径不变）
- **T19（本次提交）**：Tab 重组为「手动发送 / 固定例程 / 配置例程」（用户需求：
  单发调试→手动发送并移除解锁；新建固定例程 = 会话切换 1001/1002/1003 + 安全
  解锁 + 读DTC；例程运行→配置例程并移除读DTC）
- **T20（本次提交）**：布局改版（用户需求：例程区不独占——三 Tab 左半·上 2/5，
  日志/报文左半·下 3/5，右半留空透出右上对齐的背景图；固定例程下拉框改为
  内容自适应宽度不再拉伸）
