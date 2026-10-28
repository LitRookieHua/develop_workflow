"""IDC310GAC-7994（9AD4 例程 PENDING 挂死/请求被吞）压测公共件。

判定口径（与 tools/UdsLogAnalyzer 一致）：
- swallow = 3101 发出后完全无响应（P2 超时且从未收到 7F3178）→ 缺陷复现
- hang    = 收到 7F3178 后 P2* 窗口内无最终响应 → 缺陷复现
- nrc22   = SoC 许可冷却窗口的设计内负响应，不算失败（testcase 预期）
- 3103 结果内容（标定成败）不影响判定——当前环境标定失败属预期
"""
import sys
import threading
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[3] / "tools" / "DiagnosticTester"
sys.path.insert(0, str(TOOLS))

from can_driver import CanFrame  # noqa: E402
from isotp import encode  # noqa: E402

REQ_3101 = b"\x31\x01\x9a\xd4"
REQ_3103 = b"\x31\x03\x9a\xd4"

REPRO_KINDS = ("swallow", "hang")


def fmt(r):
    if r.timeout:
        return f"TIMEOUT(pendings={r.pendings})"
    if r.response is None:
        return "EMPTY"
    txt = r.response.hex().upper()
    if r.nrc is not None:
        txt += f" (NRC 0x{r.nrc:02X})"
    return txt


def classify(r):
    """3101 响应定性 → (kind, text)。kind: accepted/nrc22/nrc24/nrcXX/swallow/hang。"""
    if r.timeout:
        return ("hang" if r.pendings >= 1 else "swallow"), fmt(r)
    if r.ok:
        return ("accepted" if r.response[:2] == b"\x71\x01" else "unexpected"), fmt(r)
    if r.nrc is None:
        return "unexpected", fmt(r)
    return (f"nrc{r.nrc:02x}", fmt(r))


def open_session(uds, level, log, boot_wait_s=60.0, allow_unlocked=False):
    """1003 + 0x27 解锁（1101 复位后 ECU 重启期间带重试）。

    allow_unlocked=True 用于每轮重认证场景：1003 重进后若安全未重锁
    （种子为零），视为已解锁继续，不判异常。
    """
    deadline = time.monotonic() + boot_wait_s
    while True:
        r = uds.request(b"\x10\x03")
        if r.ok:
            break
        if time.monotonic() > deadline:
            log(f"1003 失败（ECU 未就绪？）：{fmt(r)}")
            return False
        time.sleep(2.0)

    rs = uds.request(level.seed_request())
    if not rs.ok or len(rs.response) < 3:
        log(f"2701 取种子失败：{fmt(rs)}")
        return False
    seed = rs.response[2:]
    if set(seed) == {0}:
        if allow_unlocked:
            log("零种子（安全未重锁，视为已解锁）")
            return True
        log("!!! 零种子（已处于解锁态，异常）")
        return False
    rk = uds.request(bytes([0x27, level.key_sub]) + level.compute_key(seed))
    if not rk.ok:
        log(f"2702 发密钥失败：{fmt(rk)}")
        return False
    log("会话+安全解锁就绪")
    return True


class Keepalive:
    """3E80 功能寻址保活线程（S3=5s，默认 2s 周期）。"""

    def __init__(self, driver, rec, functional_id, fd, period_ms=2000):
        self._frames = [CanFrame(functional_id, f, is_fd=fd, bitrate_switch=fd)
                        for f in encode(b"\x3e\x80", fd)]
        self._driver = driver
        self._rec = rec
        self._period = period_ms / 1000.0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self._stop.is_set():
            for f in self._frames:
                try:
                    self._driver.send(f)
                    self._rec.frame(f, False)
                except Exception as exc:  # noqa: BLE001
                    self._rec.event(f"keepalive send error: {exc!r}")
            self._stop.wait(self._period)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=2)


def hold_for_t32(keepalive, log, minutes=10):
    """复现后保持现场供 TRACE32 附加（保活继续、不复位、不发新请求）。"""
    log("!!! 缺陷复现 —— 保持现场供 TRACE32 取证，勿断电/复位")
    log("    /t32-j6b-connect <feature 分支编译输出的 .elf>，重点变量：")
    log("    - 0x31 服务状态 m_serviceProcessingState_e（预期卡 E_DIA_SM_RUNNING）")
    log("    - 9AD4 例程 m_diaSMCurrentState_e / m_cyclicFeedbackRoutineState_e")
    log("    - DiaCalibrationManager m_calibStep / m_calibPermetFlag")
    log(f"    现场保持 {minutes} 分钟后退出……")
    time.sleep(minutes * 60)
