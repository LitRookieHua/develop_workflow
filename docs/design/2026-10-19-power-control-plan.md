# PowerControl 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `tools/PowerControl/` 统一电源控制工具(基类 + korad 驱动 + CLI),并将 ProgramBoard/ota 两个刷写工具迁移到该工具,删除原 `tools/ProgramBoard/korad.py`。

**Architecture:** 扁平单目录两文件:`power_control.py`(PowerSupply 基类 + PowerControlError + 工厂 + CLI)、`korad.py`(KA3005P 驱动,继承基类)。设计文档:`docs/design/2026-10-19-power-control-design.md`。

**Tech Stack:** Python 3 + pyserial,无第三方测试框架(仓库 tools/ 无 pytest 基建,验证走 CLI 冒烟 + 真机手动)。

**与设计文档的一处实现偏差(已确认合理):** 设计写 `DRIVERS = {"korad": KoradKA3005P}` 顶层注册表,但 korad.py 需 import power_control 的 `PowerSupply`/`PowerControlError`,顶层互相 import 会循环。改为**工厂函数内懒加载驱动**,扩展时在工厂加一个分支即可,代价相同、无循环陷阱。

---

### Task 1: 创建 tools/PowerControl/korad.py(驱动,自 ProgramBoard 迁入)

**Files:**
- Create: `tools/PowerControl/korad.py`

- [ ] **Step 1: 写入驱动文件**

内容 = 原 `tools/ProgramBoard/korad.py` 全部逻辑,三处改动:文件头注释、`KoradError` 继承 `PowerControlError`、`KoradKA3005P` 继承 `PowerSupply`。完整文件:

```python
"""KORAD KA3005P 电源驱动：仅开关（电压固定 12V，不做设置）。"""
import re
import time

import serial

from power_control import PowerControlError, PowerSupply


class KoradError(PowerControlError):
    pass


class KoradKA3005P(PowerSupply):
    def __init__(self, port: str):
        try:
            self._ser = serial.Serial(port, 115200, timeout=1.0)
        except serial.SerialException as e:
            raise KoradError(f"无法打开电源串口 {port}: {e}") from e

    def _cmd(self, cmd: str) -> str:
        self._ser.reset_input_buffer()
        self._ser.write((cmd + "\n").encode())
        if cmd.endswith("?"):
            return self._ser.read(64).decode(errors="ignore").strip()
        return ""

    def identify(self) -> str:
        idn = self._cmd("*IDN?")
        if not idn:
            raise KoradError("*IDN? 无响应——请检查 --psu-com 是否填成了板子串口")
        return idn

    def output_on(self):
        self._cmd("OUT1")

    def output_off(self):
        self._cmd("OUT0")

    def measure_voltage(self) -> float:
        raw = self._cmd("VOUT1?")
        m = re.search(r"\d+(?:\.\d+)?", raw)
        if not m:
            raise KoradError(f"VOUT1? 返回异常: {raw!r}")
        return float(m.group())

    def power_cycle(self, delay: float = 3.0) -> float:
        """OUT0 → 放电 → OUT1 → 回读确认输出拉起。返回实测电压。"""
        self.output_off()
        time.sleep(delay)
        self.output_on()
        time.sleep(1.0)
        v = self.measure_voltage()
        if v < 1.0:
            raise KoradError(f"OUT1 后输出未拉起 (VOUT={v}V)")
        return v

    def close(self):
        self._ser.close()
```

注意:此时 `power_control.py` 尚不存在,`from power_control import ...` 会失败——本任务只写文件不运行,Task 2 完成后整个包才可导入。原文件 `tools/ProgramBoard/korad.py` 暂不删除(Task 5 迁移完再删)。

- [ ] **Step 2: 不提交,继续 Task 2**

(单 commit 会在 Task 2 末尾一起做,避免提交一个 import 不了的状态)

---

### Task 2: 创建 tools/PowerControl/power_control.py(基类 + 工厂 + CLI)

**Files:**
- Create: `tools/PowerControl/power_control.py`

- [ ] **Step 1: 写入主文件**

```python
"""PowerControl 统一电源控制：基类 + 驱动工厂 + CLI。

用法:
  python power_control.py --port COM44 [--type korad] <on|off|cycle|id> [--delay 3]

新电源接入:本目录加一个驱动文件(继承 PowerSupply,错误抛 PowerControlError
子类),在 create_power_supply 的懒加载分支加一行,README 加一节。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


class PowerControlError(Exception):
    pass


class PowerSupply:
    """电源统一接口（最小接口，电压固定不做设置）。"""

    def identify(self) -> str:
        raise NotImplementedError

    def output_on(self):
        raise NotImplementedError

    def output_off(self):
        raise NotImplementedError

    def measure_voltage(self) -> float:
        raise NotImplementedError

    def power_cycle(self, delay: float = 3.0) -> float:
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


def create_power_supply(psu_type: str, port: str) -> PowerSupply:
    # 驱动在工厂内懒加载：驱动模块要 import 本文件的 PowerSupply/PowerControlError，
    # 顶层互相 import 会循环
    if psu_type == "korad":
        from korad import KoradKA3005P
        return KoradKA3005P(port)
    raise PowerControlError(f"未知电源类型 {psu_type!r}，可用: korad")


def main() -> int:
    ap = argparse.ArgumentParser(description="PowerControl 统一电源控制")
    ap.add_argument("--port", required=True, help="电源串口 COM 号")
    ap.add_argument("--type", default="korad", dest="psu_type",
                    help="电源类型（默认 korad）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("on", help="上电")
    sub.add_parser("off", help="断电")
    p_cycle = sub.add_parser("cycle", help="断电重启")
    p_cycle.add_argument("--delay", type=float, default=3.0,
                         help="断电放电时间（秒，默认 3）")
    sub.add_parser("id", help="识别 + 回读电压")
    args = ap.parse_args()

    try:
        psu = create_power_supply(args.psu_type, args.port)
        print(f"电源: {args.port} ({psu.identify()})")
        if args.cmd == "on":
            psu.output_on()
            print("已上电")
        elif args.cmd == "off":
            psu.output_off()
            print("已断电")
        elif args.cmd == "cycle":
            print(f"断电冷启动（放电 {args.delay}s）...")
            v = psu.power_cycle(args.delay)
            print(f"已上电 (VOUT={v}V)")
        else:  # id
            print(f"VOUT: {psu.measure_voltage()} V")
        psu.close()
        return 0
    except PowerControlError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 无硬件冒烟——--help**

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/PowerControl
python power_control.py --help
```

预期:打印用法,子命令列表含 `on/off/cycle/id`,退出码 0。

- [ ] **Step 3: 无硬件冒烟——未知类型报错**

```bash
python power_control.py --port COM44 --type foo on
```

预期:stderr 打印 `❌ 未知电源类型 'foo'，可用: korad`,退出码 1。

- [ ] **Step 4: 无硬件冒烟——缺子命令报错**

```bash
python power_control.py --port COM44
```

预期:argparse 报 `the following arguments are required: cmd`,退出码 2。

- [ ] **Step 5: 提交 Task 1+2**

```bash
git add tools/PowerControl/korad.py tools/PowerControl/power_control.py
git commit -m "feat(tools): add PowerControl unified power supply tool with korad driver"
```

---

### Task 3: 创建 tools/PowerControl/README.md

**Files:**
- Create: `tools/PowerControl/README.md`

- [ ] **Step 1: 写入 README**

```markdown
# PowerControl 电源控制工具

统一电源控制：当前支持 KORAD KA3005P，后续新电源按驱动接入。可单独用作 CLI，
也作为库被 `tools/ProgramBoard/`（刷写/OTA）引用。

## 前提

- 电源 USB 串口接 PC（KA3005P 当前为 COM44，COM 号可能漂移，用 list_ports 查）
- 刷写板供电接电源输出（12V）

## CLI 用法

    cd tools/PowerControl
    python power_control.py --port COM44 [--type korad] <on|off|cycle|id> [--delay 3]

| 命令 | 作用 |
| --- | --- |
| `on` | 上电 |
| `off` | 断电 |
| `cycle` | 断电重启（`--delay` 放电秒数，默认 3） |
| `id` | 识别电源 + 回读实测电压 |

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--port` | 必填 | 电源串口 COM 号 |
| `--type` | `korad` | 电源类型 |

退出码：0 成功 / 1 失败（错误打印到 stderr）。

## 库用法

    from power_control import PowerControlError, create_power_supply
    psu = create_power_supply("korad", "COM44")
    psu.power_cycle(3.0)
    psu.close()

（`tools/ProgramBoard/ProgramBoard_j6b.py`、`ota_j6b.py` 即此用法，`--psu-com`
填电源串口、`--psu-type` 选类型。）

## 新电源接入

1. 本目录新建驱动文件：继承 `PowerSupply`（`power_control.py`），实现
   identify / output_on / output_off / measure_voltage / power_cycle / close，
   错误抛 `PowerControlError` 子类
2. `power_control.py` 的 `create_power_supply` 懒加载分支加一行
3. 本 README 的 CLI 参数表与前提一节补充新电源信息
```

- [ ] **Step 2: 提交**

```bash
git add tools/PowerControl/README.md
git commit -m "docs(tools): add PowerControl README"
```

---

### Task 4: 迁移 ProgramBoard_j6b.py

**Files:**
- Modify: `tools/ProgramBoard/ProgramBoard_j6b.py:15-16`(import)、`:35`(参数)、`:166`(实例化)、`:186`(异常)

- [ ] **Step 1: 改 import(15-16 行)**

```python
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "PowerControl"))
from power_control import PowerControlError, create_power_supply
from uboot_console import UbootConsole, UbootTimeout
from fastboot_runner import FastbootError, run_fastboot, run_fastboot_with_connect_retry
```

(第一行 sys.path.insert 保留——uboot_console/fastboot_runner 仍在本目录。)

- [ ] **Step 2: 加 --psu-type 参数(35 行 `--psu-com` 之后)**

```python
    ap.add_argument("--psu-com", default=None, help="电源串口 COM 号（不填则提示人工断电）")
    ap.add_argument("--psu-type", default="korad", dest="psu_type",
                    help="电源类型（默认 korad，见 tools/PowerControl）")
```

- [ ] **Step 3: 改实例化(166 行)**

```python
        psu = create_power_supply(args.psu_type, args.psu_com)
```

- [ ] **Step 4: 改异常捕获(186 行)**

```python
        except (UbootTimeout, FastbootError, PowerControlError) as e:
```

- [ ] **Step 5: 无硬件冒烟**

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/ProgramBoard
python ProgramBoard_j6b.py --help
```

预期:用法正常,参数表出现 `--psu-com` 和 `--psu-type`,退出码 0(工具未接硬件时不执行主流程,--help 不触发串口)。

- [ ] **Step 6: 提交**

```bash
git add tools/ProgramBoard/ProgramBoard_j6b.py
git commit -m "refactor(tools): migrate ProgramBoard to PowerControl library"
```

---

### Task 5: 迁移 ota_j6b.py + 删除旧 korad.py

**Files:**
- Modify: `tools/ProgramBoard/ota_j6b.py:29-30`(import)、`:61-62`(参数)、`:410`(实例化)、`:427`(异常)
- Delete: `tools/ProgramBoard/korad.py`

- [ ] **Step 1: 改 import(29-30 行)**

```python
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "PowerControl"))
from power_control import PowerControlError, create_power_supply
```

- [ ] **Step 2: 加 --psu-type 参数(61-62 行 `--psu-com` 之后)**

```python
    ap.add_argument("--psu-com", default=None,
                    help="电源串口 COM 号（不填则假定板子已上电启动）")
    ap.add_argument("--psu-type", default="korad", dest="psu_type",
                    help="电源类型（默认 korad，见 tools/PowerControl）")
```

- [ ] **Step 3: 改实例化(410 行)**

```python
        psu = create_power_supply(args.psu_type, args.psu_com)
```

- [ ] **Step 4: 改异常捕获(427 行)**

```python
        except (OtaError, PowerControlError, paramiko.SSHException, OSError) as e:
```

- [ ] **Step 5: 删除旧驱动(此时两刷写工具均已迁移,删除不再破坏 import)**

```bash
git rm tools/ProgramBoard/korad.py
```

- [ ] **Step 6: 无硬件冒烟**

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/ProgramBoard
python ota_j6b.py --help
python -c "import ProgramBoard_j6b" 2>/dev/null || python -c "
import sys; sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('m', 'ProgramBoard_j6b.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print('ProgramBoard_j6b import OK')
spec2 = importlib.util.spec_from_file_location('o', 'ota_j6b.py')
o = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(o)
print('ota_j6b import OK')
"
```

预期:`ota_j6b.py --help` 正常显示 `--psu-com`/`--psu-type`;两个模块 import OK(证明 korad.py 删除后无残留引用)。

- [ ] **Step 7: 提交**

```bash
git add tools/ProgramBoard/ota_j6b.py
git commit -m "refactor(tools): migrate ota_j6b to PowerControl library and remove legacy korad.py"
```

(git rm 已暂存 korad.py 删除,随本 commit 一并入库。)

---

### Task 6: 更新 tools/ProgramBoard/README.md + 全仓收尾核对

**Files:**
- Modify: `tools/ProgramBoard/README.md:37`、`:100`(参数表)、`:127`(模块表)

- [ ] **Step 1: 改参数表两处(37、100 行)**

37 行(ProgramBoard 参数表):

```markdown
| `--psu-com` | 无 | 电源串口 COM 号（不填走人工断电模式；电源工具见 `../PowerControl/`） |
| `--psu-type` | `korad` | 电源类型（见 `../PowerControl/`） |
```

100 行(ota 参数表):

```markdown
| `--psu-com` | 无 | 电源串口 COM 号（不填则假定板子已上电启动） |
| `--psu-type` | `korad` | 电源类型（见 `../PowerControl/`） |
```

- [ ] **Step 2: 删模块表 korad.py 行(127 行)**

删除 `korad.py           KA3005P 电源控制（仅开关，电压固定 12V）` 一行。

- [ ] **Step 3: 全仓核对无残留引用**

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow
git grep -n "from korad import" -- ':!docs' ':!.claude'
ls tools/ProgramBoard/korad.py
```

预期:grep 无输出(`.claude/skills/` 与 `docs/` 里的 KA3005P 硬件描述性提及不算代码引用,保留);`ls` 报文件不存在。

- [ ] **Step 4: 提交**

```bash
git add tools/ProgramBoard/README.md
git commit -m "docs(tools): update ProgramBoard README for PowerControl migration"
```

---

### Task 7: 真机验证(用户手动,阻塞项)

**Files:** 无代码改动

- [ ] **Step 1: 请用户接好 KA3005P(COM44)+ 刷写板,真机跑 CLI**

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/PowerControl
python power_control.py --port COM44 id
python power_control.py --port COM44 cycle
```

预期:`id` 打印 IDN + VOUT ≈ 12V;`cycle` 断电重启后 VOUT 确认拉起。

- [ ] **Step 2: 请用户跑一次 ProgramBoard 全流程刷写(带 --psu-com COM44)**

预期:断电冷启动 → fastboot 刷写 → 重启,全流程无电源相关报错,证明迁移无回归。

- [ ] **Step 3: 真机验证不通过则回到对应任务修复,通过后本计划完成**

真机验证通过后无需额外 commit;不通过时修复代码另起 fix commit。
