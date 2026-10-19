# PowerControl 电源控制工具设计

- 日期:2026-10-19
- 状态:已确认
- 背景:现 `tools/ProgramBoard/korad.py` 只支持 KORAD KA3005P 一种电源,且与刷写工具耦合。抽出独立的 `tools/PowerControl/` 工具,提供统一电源抽象,当前接入 korad 驱动,后续可扩展其他电源。

## 1. 目标

1. 新建 `tools/PowerControl/`:统一电源接口 + korad 驱动 + CLI(手动开关电/断电重启)
2. 同时作为库供 `ProgramBoard_j6b.py` / `ota_j6b.py` 引用,删除原 `tools/ProgramBoard/korad.py`(git 历史即存档)
3. 新电源接入成本低:加一个驱动文件 + 注册表一行 + README 一节

## 2. 已确认的关键决策

| 决策点 | 结论 |
| --- | --- |
| 工具形态 | CLI + 库(独立目录,既可单独跑,也可被 import) |
| 接口范围 | 最小接口(identify / output_on / output_off / measure_voltage / power_cycle / close),电压固定 12V 不做设置 |
| 类型选择 | CLI/调用方显式传 `--type` / `psu_type`(默认 `korad`),不做 IDN 自动识别 |
| 现有工具迁移 | 同步迁移,ProgramBoard/ota 改用 PowerControl,删原 korad.py,单一实现不留两份 |
| 内部架构 | 方案 A 扁平单目录:基类 + 字典注册表 + CLI 合在 `power_control.py`,驱动各自一个文件;不上 ABC/自动发现(驱动规模 2~3 个以内,YAGNI) |
| CLI 子命令 | 四命令:`on` / `off` / `cycle --delay N` / `id` |

## 3. 目录结构

```
tools/PowerControl/
├── README.md           # 用法说明(风格同 ProgramBoard/README.md)
├── power_control.py    # PowerSupply 基类 + PowerControlError + 注册表 + create_power_supply() + CLI 入口
└── korad.py            # KoradKA3005P(自 tools/ProgramBoard/korad.py 迁入,继承基类)
```

## 4. 统一接口

`PowerSupply` 基类为普通类(非 ABC),方法抛 `NotImplementedError`,仅作接口文档约定:

| 方法 | 说明 |
| --- | --- |
| `identify() -> str` | 返回识别串 |
| `output_on()` / `output_off()` | 开/关输出 |
| `measure_voltage() -> float` | 实测电压 |
| `power_cycle(delay: float = 3.0) -> float` | 断电 → 放电 → 上电 → 回读确认拉起,返回实测电压 |
| `close()` | 关串口 |

异常体系:新增 `PowerControlError(Exception)` 基类;`KoradError` 改为继承 `PowerControlError`——现有 `except KoradError` 仍兼容,上层工具迁移后改 catch `PowerControlError`。

工厂函数:

```python
def create_power_supply(psu_type: str, port: str) -> PowerSupply:
    if psu_type == "korad":
        from korad import KoradKA3005P   # 工厂内懒加载
        return KoradKA3005P(port)
    ...
```

> 实现偏差(相对本节初稿的 `DRIVERS = {...}` 顶层注册表):korad.py 需 import 本文件的 `PowerSupply`/`PowerControlError`,顶层互相 import 会循环,故驱动在工厂内懒加载——扩展成本相同(工厂加一个分支),已随实现落地。

未知类型报错并列出可用类型名。

## 5. CLI 设计

```bash
cd tools/PowerControl
python power_control.py --port COM44 --type korad on      # 上电
python power_control.py --port COM44 off                  # 断电(--type 默认 korad)
python power_control.py --port COM44 cycle --delay 3      # 断电重启
python power_control.py --port COM44 id                   # 识别 + 回读电压
```

- 每次执行自动打印 `电源: COM44 (<identify 结果>)`,风格同 ProgramBoard 日志
- 退出码 0 成功 / 1 失败(同 ProgramBoard 约定);驱动层错误统一捕获打印后退出 1
- `--delay` 仅 `cycle` 有效,默认 3.0 秒

## 6. 现有工具迁移

- `ProgramBoard_j6b.py` / `ota_j6b.py`:
  - `from korad import KoradError, KoradKA3005P` → `sys.path.insert(0, <PowerControl 目录>)` 后 `from power_control import PowerControlError, create_power_supply`
  - 实例化走工厂;异常 catch 改 `PowerControlError`
  - 新增 `--psu-type` 参数(默认 `korad`),与 CLI 对称
- 删除 `tools/ProgramBoard/korad.py`
- `tools/ProgramBoard/README.md`:模块表删 korad.py 行;`--psu-com` 说明改为指向 PowerControl 工具;补充 `--psu-type` 说明

## 7. 新电源接入方式(README 落地)

1. `tools/PowerControl/` 下新建驱动文件,实现 `PowerSupply` 全部方法,错误抛 `PowerControlError` 子类
2. `power_control.py` 注册表加一行
3. README 加一节驱动说明

## 8. 验证方案

- 无硬件冒烟:CLI `--help`、未知 `--type` 报错、子命令参数解析
- 真机验证(用户手动):COM44 + KA3005P 跑一次 `id` 和 `cycle`;ProgramBoard 全流程刷写一次确认迁移无回归

## 9. 不做的事

- 不做 IDN 自动识别电源型号
- 不做 set_voltage / set_current 等扩展接口
- 不做 ABC 强制约束、驱动目录自动发现
- 不动 `tools/ProgramBoard` 其他模块(fastboot_runner / uboot_console / ota 流程逻辑)
