"""第二遍流式扫描：定位 8.5GB BLF 中的全部诊断流量。
- 所有 0x700-0x7FF 仲裁域 ID 的帧数统计
- 70E/78E/7DF 全部帧输出（时间线），若为空则说明诊断在别的通道
用法： python scan2_diag.py <blf路径>
"""
import sys
import collections
import can

path = sys.argv[1]
f = can.BLFReader(path)
t0 = None
hi_ids = collections.Counter()
diag = []
for m in f:
    aid = m.arbitration_id
    if aid >= 0x700:
        hi_ids[aid] += 1
        if aid in (0x70E, 0x78E, 0x7DF):
            if t0 is None:
                t0 = m.timestamp  # noqa
            diag.append((m.timestamp, aid, bytes(m.data), m.is_rx))
print("0x7xx ID stats:", {hex(k): v for k, v in sorted(hi_ids.items())})
print(f"diag frames 70E/78E/7DF: n={len(diag)}")
if diag:
    base = diag[0][0]
    print(f"diag span: rel {base - t0 if t0 else 0:.1f} ... absolute first={diag[0][0]:.3f} last={diag[-1][0]:.3f}")
    print(f"first diag abs-t0 = {diag[0][0]:.3f} (need t0_ref)")
# 直接给绝对时间戳序列（最后 200 帧 + 全部 70E TX 时刻）
with open(".tmp/diag_timeline.txt", "w", encoding="utf-8") as out:
    for ts, aid, data, is_rx in diag:
        out.write(f"{ts:.6f} {hex(aid)} {data.hex().upper()} {'rx' if is_rx else 'TX'}\n")
print("timeline written to .tmp/diag_timeline.txt")
