# A 核 / R 核串口识别规则

COM 号随 USB 重枚举漂移（J6 EVM 的 A 核见过 COM30→COM41→COM33），**不能记死 COM 号，每次刷写/采集前按规则现判**。

电源口（KA3005P）独立于板卡串口，用 `tools/PowerControl` 的 `power_control.py --port <COM> id` 能应答即确认（当前 COM44），先排除。

## J6 项目（波特率全部 921600）

- **CH9114 四口芯片**（枚举出 4 个 `USB-Enhanced-SERIAL-{A,B,C,D}`）：
  - **SERIAL-C = A 核串口**（刷写 `ProgramBoard_j6b.py --port` 用）
  - **SERIAL-D = R 核串口**（MCU RTOS 调试/插桩日志采集用，参照 `tests/harness/mcu_log/capture_com68.py`）
- **普通 USB Serial Port**（设备描述为 `USB Serial Port`）：按 **COM 号从小到大排序，第 3 个 = A 核串口，第 4 个 = R 核串口**

## TDA4 项目（波特率全部 115200）

- 都是 `USB Serial Port`，共两组串口（各 4 个连续的串口）：
  1. **先确认哪个是 A 核组**（有四个连续的串口）→ 该组**第 1 个** = A 核串口
  2. **另一个是 R 核组**（有四个连续的串口）→ 该组**第 2 个** = R 核串口

## 现场快查步骤

1. 列口：`tools/PowerControl` 的 `list_ports`（或 `python -c "from serial.tools import list_ports; ..."`）
2. 电源口用 `power_control.py --port <COM> id` 应答排除
3. 按上述规则定位 A 核 / R 核口
4. 验证（J6）：对判定的 A 核口跑 `ProgramBoard_j6b.py --dry-run`——能打断 uboot 进 fastboot 即确认

## 实测映射（仅同板同接线有效，换板必须重新按规则判定）

| 板 | A 核 | R 核 | 备注 |
|---|---|---|---|
| J6 EVM（CH9114） | SERIAL-C（最初 COM30 → COM41 → 当前 COM33） | SERIAL-D（最初 COM27 → 当前 COM32） | N60/T75 等 J6 项目刷写板 |
| T09 板（普通 USB Serial Port，COM63-66） | COM65（升序第 3 个，2026-10-20 用户实测+刷写验证） | COM66（升序第 4 个） | 诊断 CANFD1(500k/2M) 接 CX ch0 |

（2026-10-19 由用户提供权威规则，替代此前"抓上电 banner 分类"的临时识别法）
