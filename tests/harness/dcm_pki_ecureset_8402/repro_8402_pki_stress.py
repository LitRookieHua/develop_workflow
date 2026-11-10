"""IDC310GAC-8402 复现压测：PKI 落盘(DID 9A3E 写 A 核 PerStorage) + 1101 复位，
第 4 个 1101（A 核 rm -rf PerStorage + 3x sync 完成后 ~1s）偶现零响应。

复刻报告人 5605_广汽项目IP地址自恢复压测脚本 的完整迭代流程
（trace + 脚本日志还原）：

  A. 1001 → 1003 → 27解锁 → 2E9A3E(data1) → 229A3E反读 → 1101#1
     → 等60s → SSH查 master.json 含 data1 → SSH rm+sync×3
  B. 1101#2 → 等60s → SSH查 master.json 含 data1(自恢复) → 1003 → 27解锁
     → 229A3E(=data1) → 2E9A3E(data2) → 229A3E反读 → 1101#3
     → 等60s → SSH查 master.json 含 data2 → SSH rm+sync×3
  C. 1101#4  ← RED 点：期望 5101；复现 = 零响应(无 pending/无 NRC)
     → 等60s → SSH查 master.json 含 data2(自恢复)

与原测试的差异（增强取证，原测试缺失的证据）：
  1. trace.blf 记录通道上**全部** CAN 帧（不限诊断 ID）→ RED 后可判 ECU 整机存活
  2. RED 后不立即停：存活观察期（默认 10 分钟）——每 5s 发 1001 探测诊断通道，
     每 15s SSH 读 /proc/uptime 探测 A 核，3E80 keepalive 与全帧记录持续
  3. 每个 1101 记录时延/pending 数（根因余量分析；对比 4839 修复后
     ~957-1017ms 防抖基线）

RED 判定：1101 请求 timeout 且 pendings=0（零响应）。1101 的 P2 放宽到
2000ms（正常周期首次 pending 14-31ms；压测下 5101 总时延观测最大 13.3s，
P2* 用 30s）。任何步骤失败即停（对应原脚本"遇错即停"）并进入观察期。

用法（bench：CX-USBCANFD 接诊断总线，DUT = GAC T09-Y 整机，A 核 SSH 可达）：
  set DUT_SSH_PASSWORD=...            # 或 --ssh-password / 交互输入，脚本不内置口令
  python repro_8402_pki_stress.py [--iterations 1000] [--observe-min 10]
      [--config <path>] [--ssh-host 172.16.0.14] [--ssh-user root]

输出：本目录 logs/repro_<时间戳>/（run.log + trace.blf + stats.csv）
退出码：0 全部迭代完成 / 1 命中 RED / 3 运行期异常
"""
import argparse
import getpass
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[3] / "tools" / "DiagnosticTester"
sys.path.insert(0, str(TOOLS))

from can_driver import CanFrame  # noqa: E402
from DiagnosticTester import build_transport, make_driver  # noqa: E402
from flow import load_config  # noqa: E402
from isotp import encode  # noqa: E402
from recorder import Recorder  # noqa: E402
from uds import UdsClient  # noqa: E402

try:
    import paramiko  # noqa: E402
except ImportError:
    paramiko = None

DEFAULT_CONFIG = TOOLS / "configs" / "t09" / "t09_cx.yaml"

DID = 0x9A3E
DATA1 = b"192.168.1.239           12444 "
DATA2 = b"172.16.0.14             12443 "
MASTER_JSON = "/app_param/property/kvs/PerStorage/master.json"
RM_CMDS = ("rm -rf /app_param/property/kvs/PerStorage", "sync", "sync", "sync")

WAIT_60_S = 60.0          # 1101 后等待（原脚本 after_ecu_reset = 60）
KA_INTERVAL_MS = 2000     # 3E80 周期（原 trace 全程 2s 一帧）
RESET_GAP_MS = 1000       # rm+sync 完成 → 1101#4 的间隔（原测试 ~1.0s）
P2_1101_MS = 2000         # 1101 的 P2 放宽值
P2STAR_MS = 30000         # pending 总窗口（观测最大 13.3s + 余量）
PROBE_PERIOD_S = 5        # 观察期诊断探测周期
SSH_PROBE_PERIOD_S = 15   # 观察期 A 核探测周期


def fmt(r):
    if r.timeout:
        return "TIMEOUT"
    if r.response is None:
        return "EMPTY"
    txt = r.response.hex().upper()
    if r.nrc is not None:
        txt += f" (NRC 0x{r.nrc:02X}, pendings={r.pendings})"
    return txt


class Ssh:
    """A 核操作：读 master.json / rm+sync 批次（复刻原脚本每次新建连接）/ 探活。"""

    def __init__(self, host, user, password):
        self.host, self.user, self.password = host, user, password
        if paramiko is None:
            raise RuntimeError("paramiko 未安装：python -m pip install paramiko")

    def _connect(self):
        cli = paramiko.SSHClient()
        cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        cli.connect(self.host, username=self.user, password=self.password,
                    timeout=10, banner_timeout=15)
        return cli

    def read_master(self):
        cli = self._connect()
        try:
            _, stdout, _ = cli.exec_command(f"cat {MASTER_JSON}", timeout=30)
            return stdout.read().decode("utf-8", errors="replace")
        finally:
            cli.close()

    def rm_sync(self):
        """逐条 exec（与原脚本一致），返回 (各命令耗时, 总耗时)。"""
        costs = []
        t0 = time.monotonic()
        cli = self._connect()
        try:
            for cmd in RM_CMDS:
                t = time.monotonic()
                _, stdout, _ = cli.exec_command(cmd, timeout=60)
                stdout.read()
                costs.append(round(time.monotonic() - t, 3))
        finally:
            cli.close()
        return costs, round(time.monotonic() - t0, 3)

    def uptime(self):
        cli = self._connect()
        try:
            _, stdout, _ = cli.exec_command("cat /proc/uptime", timeout=10)
            return stdout.read().decode("utf-8", errors="replace").strip()
        finally:
            cli.close()


class Harness:
    def __init__(self, cfg, run_dir, ssh):
        self.diag = cfg["diagnostic"]
        self.fd = cfg["can"]["fd"]
        self.level = cfg["security_levels"]["app"]
        self.run_dir = run_dir
        self.ssh = ssh
        self.stats = []      # (iter, step, sid, ok, timeout, nrc, pendings, total_ms)
        self.red_events = []
        self.stop = threading.Event()
        self.uds = None
        self.driver = None

    def log(self, msg):
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    def req(self, it, step, payload, p2_ms=None):
        t0 = time.monotonic()
        r = self.uds.request(payload, timeout_ms=p2_ms)
        total_ms = round((time.monotonic() - t0) * 1000, 1)
        self.stats.append((it, step, payload[:3].hex().upper(), int(r.ok),
                           int(r.timeout), r.nrc if r.nrc is not None else "",
                           r.pendings, total_ms))
        return r, total_ms

    def ecu_reset(self, it, tag):
        """1101 → 期望 5101。RED：timeout 且 pendings=0（零响应）。"""
        r, ms = self.req(it, tag, b"\x11\x01", p2_ms=P2_1101_MS)
        if r.ok and r.response[:1] == b"\x51":
            self.log(f"[iter {it}] {tag} ECU复位成功 5101 ({ms:.0f}ms, pendings={r.pendings})")
            return True
        if r.timeout and r.pendings == 0:
            self.red_events.append((it, tag, "1101 zero-response"))
            self.log(f"[iter {it}] {tag} !!! BUG RED 复现：1101 零响应（无 pending/无 NRC）")
        else:
            self.red_events.append((it, tag, f"1101 abnormal: {fmt(r)}"))
            self.log(f"[iter {it}] {tag} !!! 1101 异常: {fmt(r)} ({ms:.0f}ms)")
        return False

    def session(self, it, tag, payload, desc):
        r, _ = self.req(it, tag, payload)
        if r.ok:
            self.log(f"[iter {it}] {desc}成功")
            return True
        self.red_events.append((it, tag, f"{desc}失败: {fmt(r)}"))
        self.log(f"[iter {it}] {desc}失败: {fmt(r)}")
        return False

    def unlock(self, it):
        rs, _ = self.req(it, "27-seed", self.level.seed_request())
        if not rs.ok:
            self.red_events.append((it, "27-seed", f"seed失败: {fmt(rs)}"))
            self.log(f"[iter {it}] 27 seed 失败: {fmt(rs)}")
            return False
        seed = rs.response[2:]
        rk, _ = self.req(it, "27-key", bytes([0x27, self.level.key_sub]) + self.level.compute_key(seed))
        if rk.ok and rk.response[:1] == b"\x67":
            self.log(f"[iter {it}] App1解锁成功")
            return True
        self.red_events.append((it, "27-key", f"key失败: {fmt(rk)}"))
        self.log(f"[iter {it}] 27 key 失败: {fmt(rk)}")
        return False

    def did_write(self, it, data, tag):
        payload = b"\x2e" + DID.to_bytes(2, "big") + data
        r, ms = self.req(it, tag, payload)
        if r.ok and r.response[:1] == b"\x6e":
            self.log(f"[iter {it}] 写入9A3E {data.decode(errors='replace')!r} 成功 "
                     f"({ms:.0f}ms, pendings={r.pendings})")
            return True
        self.red_events.append((it, tag, f"2E失败: {fmt(r)}"))
        self.log(f"[iter {it}] 写入9A3E 失败: {fmt(r)}")
        return False

    def did_read(self, it, expect, tag):
        r, _ = self.req(it, tag, b"\x22" + DID.to_bytes(2, "big"))
        if r.ok and r.response[:3] == b"\x62\x9a\x3e" and r.response[3:3 + len(expect)] == expect:
            self.log(f"[iter {it}] 反读9A3E 成功: {expect.decode(errors='replace')!r}")
            return True
        got = r.response[3:3 + len(expect)] if r.response else b""
        self.red_events.append((it, tag, f"22失败/不符: {fmt(r)} got={got!r}"))
        self.log(f"[iter {it}] 反读9A3E 失败/不符: {fmt(r)} got={got!r}")
        return False

    def wait_60(self, it, tag):
        self.log(f"[iter {it}] {tag} 等待 {WAIT_60_S:.0f}s（3E80 keepalive 持续）")
        time.sleep(WAIT_60_S)

    def file_check(self, it, tag, expect_pair):
        text = self.ssh.read_master()
        ok = all(s in text for s in expect_pair)
        if ok:
            self.log(f"[iter {it}] {tag} master.json 检查通过（含 {'/'.join(expect_pair)}）")
        else:
            self.red_events.append((it, tag, f"master.json check fail: {expect_pair}"))
            self.log(f"[iter {it}] {tag} !!! master.json 检查失败（期望含 {'/'.join(expect_pair)}）\n{text}")
        return ok

    def start_keepalive(self):
        frames = [CanFrame(self.diag["functional_id"], f, is_fd=self.fd, bitrate_switch=self.fd)
                  for f in encode(b"\x3e\x80", self.fd)]

        def loop():
            while not self.stop.is_set():
                for f in frames:
                    try:
                        self.driver.send(f)
                    except Exception as exc:  # noqa: BLE001
                        self.log(f"keepalive send error: {exc!r}")
                self.stop.wait(KA_INTERVAL_MS / 1000.0)

        t = threading.Thread(target=loop, daemon=True, name="ka3e80")
        t.start()
        return t

    def observe(self, minutes):
        """RED 后存活观察：诊断探测 + A 核探测 + 全帧记录持续（trace.blf）。"""
        self.log(f"===== 存活观察期 {minutes} 分钟：每 {PROBE_PERIOD_S}s 1001 探测诊断，"
                 f"每 {SSH_PROBE_PERIOD_S}s SSH /proc/uptime 探测 A 核 =====")
        deadline = time.monotonic() + minutes * 60
        last_ssh = 0.0
        while time.monotonic() < deadline and not self.stop.is_set():
            t0 = time.monotonic()
            r = self.uds.request(b"\x10\x01", timeout_ms=1000)
            dt = time.monotonic() - t0
            if r.timeout:
                self.log(f"[observe] 1001 -> 无响应 ({dt:.3f}s)  诊断通道离线")
            else:
                self.log(f"[observe] 1001 -> {fmt(r)} ({dt:.3f}s)")
            if time.monotonic() - last_ssh > SSH_PROBE_PERIOD_S:
                last_ssh = time.monotonic()
                try:
                    self.log(f"[observe] A核 uptime: {self.ssh.uptime()}")
                except Exception as exc:  # noqa: BLE001
                    self.log(f"[observe] A核 SSH 探测失败: {exc!r}")
            time.sleep(PROBE_PERIOD_S)

    def dump_stats(self):
        import csv
        with open(self.run_dir / "stats.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["iteration", "step", "sid", "ok", "timeout", "nrc", "pendings", "total_ms"])
            w.writerows(self.stats)
        r1101 = [s for s in self.stats if s[2] == "1101"]
        lats = [s[7] for s in r1101 if s[3]]
        if lats:
            self.log(f"1101 统计：n={len(lats)} min={min(lats):.0f}ms max={max(lats):.0f}ms")


def run_iteration(h, it):
    """一个完整 5605 迭代（A/B/C 三段）。返回 False = 出现异常（应停）。"""

    def fail():
        return len(h.red_events) > 0

    # A 段
    h.session(it, "A/1001", b"\x10\x01", "进入默认会话")
    h.session(it, "A/1003", b"\x10\x03", "进入扩展会话")
    if fail():
        return False
    if not h.unlock(it):
        return False
    if not (h.did_write(it, DATA1, "A/2E") and h.did_read(it, DATA1, "A/22")):
        return False
    if not h.ecu_reset(it, "A/reset1(1101#1)"):
        return False
    h.wait_60(it, "A")
    h.file_check(it, "A/check1", DATA1.decode().split())
    costs, total = h.ssh.rm_sync()
    h.log(f"[iter {it}] A/rm+sync 完成 各命令 {costs}s 共 {total}s")
    if fail():
        return False

    # B 段
    if not h.ecu_reset(it, "B/reset2(1101#2)"):
        return False
    h.wait_60(it, "B")
    h.file_check(it, "B/check2", DATA1.decode().split())
    h.session(it, "B/1003", b"\x10\x03", "进入扩展会话")
    if not h.unlock(it):
        return False
    if not (h.did_read(it, DATA1, "B/22") and h.did_write(it, DATA2, "B/2E")
            and h.did_read(it, DATA2, "B/22b")):
        return False
    if not h.ecu_reset(it, "B/reset3(1101#3)"):
        return False
    h.wait_60(it, "B2")
    h.file_check(it, "B2/check1", DATA2.decode().split())
    costs, total = h.ssh.rm_sync()
    h.log(f"[iter {it}] B2/rm+sync 完成 各命令 {costs}s 共 {total}s")
    if fail():
        return False

    # C 段：RED 点（rm+sync 完成后 ~1s 发 1101#4，与原测试一致）
    time.sleep(RESET_GAP_MS / 1000.0)
    if not h.ecu_reset(it, "C/reset4(1101#4)"):
        return False
    h.wait_60(it, "C")
    h.file_check(it, "C/check2", DATA2.decode().split())
    return not fail()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--iterations", type=int, default=1000)
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--ssh-host", default="172.16.0.14")
    ap.add_argument("--ssh-user", default="root")
    ap.add_argument("--ssh-password", default=os.environ.get("DUT_SSH_PASSWORD"))
    ap.add_argument("--observe-min", type=int, default=10,
                    help="RED 后存活观察时长（分钟），0 = 立即停止")
    args = ap.parse_args()

    if args.ssh_password is None:
        args.ssh_password = getpass.getpass(f"DUT SSH password ({args.ssh_user}@{args.ssh_host}): ")

    if len(DATA1) != 30 or len(DATA2) != 30:
        print("PKI 数据须 30B（与原测试 2E9A3E 长度一致）", file=sys.stderr)
        return 2

    cfg = load_config(args.config)
    run_dir = Path(__file__).parent / "logs" / f"repro_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True)
    print(f"运行目录：{run_dir}")
    print(f"iterations={args.iterations}  observe={args.observe_min}min  "
          f"config={args.config.name}  ssh={args.ssh_user}@{args.ssh_host}")

    ssh = Ssh(args.ssh_host, args.ssh_user, args.ssh_password)
    h = Harness(cfg, run_dir, ssh)
    red = False
    driver = make_driver(cfg)
    transport = None
    try:
        with Recorder(run_dir) as rec:
            transport = build_transport(cfg, driver, rec)
            h.uds = UdsClient(transport, p2_ms=cfg["timing"]["p2_ms"], p2star_ms=P2STAR_MS,
                              log=rec.event)
            h.driver = driver
            ka = h.start_keepalive()
            h.log(f"keepalive 启动：3E80 -> 0x{h.diag['functional_id']:X} 每 {KA_INTERVAL_MS}ms")

            for it in range(1, args.iterations + 1):
                t_it = time.monotonic()
                h.log(f"================= 第 {it} 次测试开始 =================")
                if not run_iteration(h, it):
                    red = True
                    break
                h.log(f"[iter {it}] 完成 ({time.monotonic() - t_it:.0f}s)，"
                      f"累计 RED: {len(h.red_events)}")

            if red and args.observe_min > 0:
                h.observe(args.observe_min)

            h.stop.set()
            ka.join(timeout=2)
    finally:
        if transport is not None:
            transport.stop()
        driver.close()

    h.dump_stats()
    print("\n========== 汇总 ==========")
    print(f"完成迭代: {h.stats[-1][0] if h.stats else 0}")
    print(f"RED 事件: {len(h.red_events)}  {h.red_events}")
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
