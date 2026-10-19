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
