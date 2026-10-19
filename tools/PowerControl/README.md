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
