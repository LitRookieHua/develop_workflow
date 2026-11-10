"""截取测试 BLF 失败窗口报文另存：
失败 1101 TX rel=61084.884（abs t0=1793631356.2676）
窗口 [rel-120, rel+120]，全部 ID 全部帧，原样写 BLF。
"""
import can

T0 = 1793631356.2676
FAIL = 61084.884
LO, HI = FAIL - 120.0, FAIL + 120.0

src = "tests/harness/dcm_pki_ecureset_8402/1101没有回复.blf"
dst = "tests/harness/dcm_pki_ecureset_8402/1101没有回复_failwin_pm120s.blf"

n = 0
with can.BLFWriter(dst) as w:
    for m in can.BLFReader(src):
        rel = m.timestamp - T0
        if rel < LO:
            continue
        if rel > HI:
            break
        w.on_message_received(m)
        n += 1
print(f"written {n} frames -> {dst}, window rel [{LO:.3f}, {HI:.3f}]")
