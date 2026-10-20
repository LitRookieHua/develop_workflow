"""MCU 日志采集工具（J6B / N60 板子通用，QNX 系统，串口使能 SSH 后 SFTP 拉取 /log/mcu）。

用法:
  python collect_j6b.py --port COM33 --project Rx [--host 192.168.1.239]
                        [--retries 3] [--dry-run]
  (--port 为 A 核串口，COM 号会漂移，识别规则见
   .claude/references/serial-port-identification.md)

流程:
  1. 串口使能 SSH：每次上电/重启后 pf 会拦截 SSH，需通过 A 核串口登录
     执行 pfctl -d 并等待 "pf disabled"
  2. SFTP 递归下载 /log/mcu → logs/<项目>/mcu_<yyyymmdd_HHMMSS>/，
     逐文件对比远端/本地大小校验，不删除板上文件
"""
import argparse
import logging
import stat as stat_mod
import sys
import time
from pathlib import Path

import paramiko
import serial

BOARD_USER = "root"
BOARD_PASSWORD = "hct@Shanghai0427"
SSH_PORT = 22
ACORE_BAUDRATE = 921600         # A 核串口波特率
ENABLE_SSH_TIMEOUT = 180        # 上电/重启后等串口出现 login 提示（QNX 启动）
PFCTL_WAIT = 15                 # pfctl -d 等 "pf disabled"
SSH_READY_TIMEOUT = 300         # 等 SSH 就绪（QNX 完整启动）
REMOTE_LOG_DIR = "/log/mcu"


class CollectError(Exception):
    pass


def parse_args():
    ap = argparse.ArgumentParser(description="J6B MCU 日志采集工具")
    ap.add_argument("--port", required=True,
                    help="板子 A 核串口 COM 号（登录执行 pfctl -d 使能 SSH）")
    ap.add_argument("--project", required=True,
                    help="项目名，日志保存到 logs/<项目>/ 下")
    ap.add_argument("--host", default="192.168.1.239", help="板子 IP")
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true",
                    help="只列出 /log/mcu 文件清单，不下载")
    return ap.parse_args()


def setup_logging(here: Path):
    log_dir = here / "logs"
    log_dir.mkdir(exist_ok=True)
    logfile = log_dir / time.strftime("collect_%Y%m%d_%H%M%S.log")

    logger = logging.getLogger("collect")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(ch)
    logger.addHandler(fh)

    def log(msg: str):
        logger.info(msg)

    return log, logfile


def enable_ssh_via_serial(port: str, log):
    """上电/重启后 QNX 的 pf 会拦截 SSH，必须通过 A 核串口登录执行
    pfctl -d 并等待 "pf disabled"。

    串口登录交互必须用 \r 行结尾（\n 会导致登录流程卡住）。"""
    try:
        ser = serial.Serial(port, ACORE_BAUDRATE, timeout=0.2)
    except serial.SerialException as e:
        raise CollectError(f"无法打开 A 核串口 {port}: {e}") from e
    try:
        deadline = time.monotonic() + ENABLE_SSH_TIMEOUT

        def drain(sec: float) -> bytes:
            """读 sec 秒串口，返回期间收到的原始数据。"""
            out = b""
            end = time.monotonic() + sec
            while time.monotonic() < end:
                n = ser.in_waiting
                if n:
                    out += ser.read(n)
                else:
                    time.sleep(0.05)
            return out

        buf = b""
        logged_in = False
        while time.monotonic() < deadline:
            ser.write(b"\r")
            buf += drain(1.5)
            if b"login:" in buf:
                ser.write(b"root\r")
                buf += drain(1.0)
                ser.write(BOARD_PASSWORD.encode() + b"\r")
                buf += drain(2.0)
            if b"root@hobot" in buf:
                logged_in = True
                break
            buf = b""
            time.sleep(2)
        if not logged_in:
            raise CollectError(f"串口 {port} 登录超时（{ENABLE_SSH_TIMEOUT:.0f}s），"
                               f"最后输出: {buf[-200:]!r}")

        ser.write(b"pfctl -d\r")
        out = drain(PFCTL_WAIT)
        # pf 已关闭时 pfctl -d 会打印 "pf not enabled"，同样代表 SSH 可连
        if b"pf disabled" not in out and b"pf not enabled" not in out:
            raise CollectError(f"pfctl -d 后未见 pf disabled，输出: {out!r}")
        log(f"串口 {port} 已执行 pfctl -d（pf disabled），SSH 已使能")
    finally:
        ser.close()


def connect_ssh(host: str, timeout: float, log):
    """循环尝试连接直到 SSH 就绪（上电/重启后 QNX 启动需要时间）。"""
    deadline = time.monotonic() + timeout
    while True:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(host, port=SSH_PORT, username=BOARD_USER,
                           password=BOARD_PASSWORD, timeout=10,
                           allow_agent=False, look_for_keys=False)
            log(f"SSH 已连接: {BOARD_USER}@{host}")
            return client
        except Exception as e:
            client.close()
            if time.monotonic() >= deadline:
                raise CollectError(f"SSH 连接 {host} 超时（{timeout:.0f}s）: {e}") from e
            time.sleep(3)


def walk_remote(sftp: paramiko.SFTPClient, remote_dir: str, prefix: str = ""):
    """递归遍历远端目录，返回 [(相对路径, 大小)]。"""
    entries = []
    for attr in sftp.listdir_attr(remote_dir):
        if attr.filename in (".", ".."):
            continue
        rel = f"{prefix}{attr.filename}"
        if stat_mod.S_ISDIR(attr.st_mode):
            entries.extend(walk_remote(sftp, f"{remote_dir}/{attr.filename}",
                                       f"{rel}/"))
        else:
            entries.append((rel, attr.st_size))
    return entries


def download_dir(sftp: paramiko.SFTPClient, remote_dir: str, dest: Path,
                 entries, log):
    dest.mkdir(parents=True, exist_ok=True)
    for rel, size in entries:
        local = dest / rel
        local.parent.mkdir(parents=True, exist_ok=True)
        log(f"下载 {rel}（{size/1e6:.2f} MB）")
        state = {"t": time.monotonic()}

        def cb(done: int, total: int):
            now = time.monotonic()
            if now - state["t"] >= 5.0:
                log(f"  {done/1e6:8.2f}/{total/1e6:.2f} MB")
                state["t"] = now

        sftp.get(f"{remote_dir}/{rel}", str(local), callback=cb)
        got = local.stat().st_size
        if got == size:
            log(f"  {rel} 完成（{got/1e6:.2f} MB）")
        else:
            log(f"  {rel} 完成（{got/1e6:.2f} MB，板上仍在写入）")
    log(f"共下载 {len(entries)} 个文件 → {dest}")


def verify_downloaded(dest: Path, entries, log):
    """逐文件检查本地存在且大小不小于扫描时大小（板上日志持续写入，
    下载后文件只会更大或相等）。返回 None 表示通过，否则为错误描述。"""
    errors = []
    for rel, size in entries:
        local = dest / rel
        if not local.is_file():
            errors.append(f"{rel}: 本地缺失")
        elif local.stat().st_size < size:
            errors.append(f"{rel}: 大小不足 本地 {local.stat().st_size} / 扫描时 {size}")
    if errors:
        return "; ".join(errors)
    total = sum(size for _, size in entries)
    log(f"校验通过: {len(entries)} 个文件, 共 {total/1e6:.2f} MB")
    return None


def collect_once(args, log) -> Path | None:
    enable_ssh_via_serial(args.port, log)
    client = connect_ssh(args.host, SSH_READY_TIMEOUT, log)
    try:
        sftp = client.open_sftp()
        try:
            log(f"扫描 {REMOTE_LOG_DIR} ...")
            try:
                entries = walk_remote(sftp, REMOTE_LOG_DIR)
            except FileNotFoundError as e:
                raise CollectError(f"板上 {REMOTE_LOG_DIR} 不存在或不可访问: {e}") from e
            if not entries:
                raise CollectError(f"{REMOTE_LOG_DIR} 下没有文件")
            total = sum(size for _, size in entries)
            log(f"板上 {REMOTE_LOG_DIR}: {len(entries)} 个文件, 共 {total/1e6:.2f} MB")
            for rel, size in sorted(entries):
                log(f"  {rel}  ({size/1e6:.2f} MB)")

            if args.dry_run:
                log("[dry-run] 跳过下载")
                return None

            dest = (Path(__file__).resolve().parent / "logs" / args.project /
                    time.strftime("mcu_%Y%m%d_%H%M%S"))
            download_dir(sftp, REMOTE_LOG_DIR, dest, entries, log)
            err = verify_downloaded(dest, entries, log)
            if err is not None:
                raise CollectError(f"下载校验失败: {err}")
            return dest
        finally:
            sftp.close()
    finally:
        client.close()


def main() -> int:
    args = parse_args()
    log, logfile = setup_logging(Path(__file__).resolve().parent)
    log(f"采集 {REMOTE_LOG_DIR} | 项目: {args.project} | 目标: {args.host} | 日志: {logfile}")

    for attempt in range(1, args.retries + 1):
        log(f"=== 第 {attempt}/{args.retries} 次尝试 ===")
        try:
            dest = collect_once(args, log)
            if dest is not None:
                log(f"✅ 采集完成: {dest}")
            return 0
        except (CollectError, paramiko.SSHException, OSError) as e:
            log(f"❌ 第 {attempt} 次失败: {e}")
        time.sleep(1)

    log(f"❌ {args.retries} 次尝试均失败，详见日志 {logfile}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
