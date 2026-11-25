"""J02 EVM V0.1 DTC 表导入验证（C097FAWVWREQ-507 / C097FAWVW-35）。

验证内容（全部经 UDS 从 ECU 实读）：
  1. 19 0A：ECU 支持的 DTC 全表与 dtc_map（42 条）逐条比对
  2. 19 02 FF：状态位非零的 DTC 及状态位解码（未测试的 DTC 状态为 0x00，不出现）
  3. 22 2A0D/2A0E/2A0F：event 位图（当前/本周期/历史）解码 event_map
  4. 22 2A1D：FiMFID 位图解码 fimfid_map
  5. 85 02 / 85 01：DTC 设置控制服务响应（正响应 0xC5）
  可选 --clear：14 FFFFFF 清码后复查 19 02 FF（验证清码与状态回落）

前置：扩展会话 10 03 + develop 解锁（2A0D/2A0E/2A0F/2A1D 需解锁）。
用法：python verify_dem_table.py [--config <j02_cx.yaml>] [--clear]
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TOOLS = ROOT / "tools" / "DiagnosticTester"
sys.path.insert(0, str(TOOLS))

from dem import decode_status, load_maps, parse_bitmap  # noqa: E402
from flow import load_config  # noqa: E402
from recorder import Recorder  # noqa: E402
from security import UnlockError, perform_unlock  # noqa: E402
from uds import UdsClient  # noqa: E402
from DiagnosticTester import build_transport, make_driver, new_run_dir  # noqa: E402


def hexs(b):
    return " ".join(f"{x:02X}" for x in b)


def parse_dtc_list(resp, sub):
    """59 <sub> <mask> (<DTC3><status>)* 解析。"""
    if not resp or resp[0] != 0x59 or resp[1] != sub:
        raise ValueError(f"不是 59 {sub:02X} 正响应：{hexs(resp) if resp else '无响应'}")
    body = resp[3:]
    if len(body) % 4:
        raise ValueError(f"DTC 记录长度不是 4 的倍数：{hexs(resp)}")
    return resp[2], [(int.from_bytes(body[i:i + 3], "big"), body[i + 3])
                     for i in range(0, len(body), 4)]


class Session:
    def __init__(self, cfg):
        self.driver = make_driver(cfg)
        self.rec = Recorder(new_run_dir(HERE / "logs"))
        self.transport = build_transport(cfg, self.driver, self.rec)
        self.uds = UdsClient(self.transport,
                             p2_ms=cfg["timing"]["p2_ms"],
                             p2star_ms=cfg["timing"]["p2star_ms"],
                             log=self.rec.event)

    def close(self):
        self.transport.stop()
        self.rec.close()
        self.driver.close()

    def req(self, hexstr, timeout_ms=None):
        r = self.uds.request(bytes.fromhex(hexstr), timeout_ms=timeout_ms)
        tx = " ".join(hexstr[i:i + 2] for i in range(0, len(hexstr), 2))
        if r.timeout:
            rx = "(timeout)"
        else:
            rx = hexs(r.response) + (f"  NRC 0x{r.nrc:02X}" if r.nrc is not None else "")
        print(f"  TX {tx}  ->  RX {rx}")
        self.rec.event(f"UDS TX: {tx}")
        self.rec.event(f"UDS RX: {rx}")
        return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(TOOLS / "configs" / "j02" / "j02_cx.yaml"))
    ap.add_argument("--clear", action="store_true", help="执行 14 FFFFFF 清码并复查")
    args = ap.parse_args()

    cfg = load_config(args.config)
    maps = load_maps(Path(args.config).parent)
    dtc_map, event_map, fimfid_map = maps["dtc_map"], maps["event_map"], maps["fimfid_map"]
    print(f"配置: {args.config}")
    print(f"dtc_map {len(dtc_map)} 条 / event_map {len(event_map)} 条 / fimfid_map {len(fimfid_map)} 条")

    ok = True
    s = Session(cfg)
    print(f"运行目录: {s.rec.run_dir}")
    try:
        print("\n[1] 10 03 扩展会话")
        r = s.req("1003")
        ok &= r.response is not None and r.response.startswith(b"\x50\x03")

        print("\n[2] 27 61/62 develop 解锁")
        try:
            _seed, _key, ur = perform_unlock(s.uds, cfg["security_levels"]["develop"])
            print(f"  key -> RX {hexs(ur.response) if ur.response else '(timeout)'}")
            ok &= ur.response is not None and ur.response.startswith(b"\x67\x62")
        except UnlockError as e:
            print(f"  解锁失败: {e}")
            ok = False

        print("\n[3] 19 0A  报告支持的 DTC 全表（与 dtc_map 逐条比对）")
        r = s.req("190A", timeout_ms=2000)
        ecu_set = set()
        try:
            mask, recs = parse_dtc_list(r.response, 0x0A)
            ecu_set = {d for d, _ in recs}
            print(f"  statusAvailabilityMask=0x{mask:02X}，共 {len(recs)} 条")
            for dtc, st in recs:
                name = dtc_map.get(dtc, "（未在 dtc_map 中）")
                print(f"  {dtc:06X}  {name}  0x{st:02X} {'|'.join(decode_status(st))}")
        except ValueError as e:
            print(f"  解析失败: {e}")
            ok = False
        missing = sorted(set(dtc_map) - ecu_set)
        extra = sorted(ecu_set - set(dtc_map))
        print(f"  比对: 表{len(dtc_map)} / ECU{len(ecu_set)} / 缺失{len(missing)} / 多余{len(extra)}")
        for d in missing:
            print(f"    缺失 {d:06X} {dtc_map[d]}")
        for d in extra:
            print(f"    多余 {d:06X}（dtc_map 未定义）")
        ok &= not missing and not extra and len(dtc_map) == len(ecu_set)

        print("\n[4] 19 02 FF  按状态掩码读 DTC（当前有效故障视图，仅供信息）")
        r = s.req("1902FF", timeout_ms=2000)
        try:
            _m, recs02 = parse_dtc_list(r.response, 0x02)
            print(f"  共 {len(recs02)} 条（状态位非零的 DTC），其余支持但未测试的 DTC 不在其中")
            for dtc, st in recs02:
                name = dtc_map.get(dtc, "（未在 dtc_map 中）")
                print(f"  {dtc:06X}  {name}  0x{st:02X} {'|'.join(decode_status(st))}")
            extra02 = {d for d, _ in recs02} - set(dtc_map)
            if extra02:
                print(f"  19 02 出现 dtc_map 未定义的 DTC: {sorted(extra02)}")
                ok = False
        except ValueError as e:
            print(f"  解析失败: {e}")
            ok = False

        print("\n[5] event 位图（2A0D 当前 / 2A0E 本周期 / 2A0F 历史）")
        for did, label in [("2A0D", "当前"), ("2A0E", "本周期"), ("2A0F", "历史")]:
            r = s.req(f"22{did}", timeout_ms=3000)
            if r.response is None or not r.response.startswith(bytes.fromhex(f"62{did}")):
                print(f"  {did} 读取失败")
                ok = False
                continue
            nums = parse_bitmap(r.response[3:])
            print(f"  {label}: {len(nums)} 个置位")
            for n in nums:
                print(f"    {n}: {event_map.get(n, '（未在 event_map 中）')}")

        print("\n[6] FiMFID 位图（2A1D）")
        r = s.req("222A1D", timeout_ms=3000)
        if r.response is None or not r.response.startswith(b"\x62\x2A\x1D"):
            print("  2A1D 读取失败")
            ok = False
        else:
            nums = parse_bitmap(r.response[3:])
            print(f"  置位 {len(nums)} 个")
            for n in nums:
                print(f"    {n}: {fimfid_map.get(n, '（未在 fimfid_map 中）')}")

        print("\n[7] 85 02 / 85 01  DTC 设置控制（正响应 0xC5）")
        r = s.req("8502")
        ok &= r.response is not None and r.response.startswith(b"\xC5\x02")
        r = s.req("8501")
        ok &= r.response is not None and r.response.startswith(b"\xC5\x01")

        if args.clear:
            print("\n[8] 14 FFFFFF 清码 + 复查")
            r = s.req("14FFFFFF", timeout_ms=2000)
            ok &= r.response is not None and r.response.startswith(b"\x59\x14")
            r = s.req("1902FF", timeout_ms=2000)
            try:
                _m, recs = parse_dtc_list(r.response, 0x02)
                print(f"  清码后 {len(recs)} 条记录")
            except ValueError as e:
                print(f"  复查解析失败: {e}")
                ok = False
    finally:
        s.close()

    print("\n===== 结果:", "PASS" if ok else "FAIL", "=====")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
