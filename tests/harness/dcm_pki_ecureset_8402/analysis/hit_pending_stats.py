import sys, datetime
import can
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
src = "tests/harness/dcm_pki_ecureset_8402/logs/smoke_20261104_144814/trace.blf"
pend = []
all78 = []
for m in can.BLFReader(src):
    aid = m.arbitration_id
    if aid == 0x78E:
        d = bytes(m.data)
        all78.append((m.timestamp, d))
        if len(d) >= 4 and d[0] & 0xf in (3, 8) and d[1] == 0x7f and d[2] == 0x2e:
            if d[3] == 0x78:
                pend.append(m.timestamp)
            else:
                print(f"2E terminal NRC: {datetime.datetime.fromtimestamp(m.timestamp).strftime('%H:%M:%S.%f')[:-3]} data={d.hex()}")
print(f"pendings n={len(pend)}")
print(f"first={datetime.datetime.fromtimestamp(pend[0]).strftime('%H:%M:%S.%f')[:-3]} last={datetime.datetime.fromtimestamp(pend[-1]).strftime('%H:%M:%S.%f')[:-3]}")
gaps = [b - a for a, b in zip(pend, pend[1:])]
print(f"cadence: min={min(gaps)*1000:.0f}ms max={max(gaps)*1000:.0f}ms mean={sum(gaps)/len(gaps)*1000:.0f}ms")
big = [(datetime.datetime.fromtimestamp(a).strftime('%H:%M:%S.%f')[:-3], (b-a)*1000) for (a, b) in zip(pend, pend[1:]) if b - a > 1.5]
print(f"gaps>1.5s: {big}")
# 78E 帧总数与 2E pending 外的 78E 帧（wedge 窗口内）
wedge = [(datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S.%f')[:-3], d.hex()) for ts, d in all78
         if d[1:3] != b'\x7f\x2e' and ts > pend[0] - 1 and ts < pend[-1] + 2]
print(f"78E non-2E frames inside wedge: {wedge}")
# 70E 请求帧全列（wedge 窗口）
reqs = []
for m in can.BLFReader(src):
    if m.arbitration_id == 0x70E:
        reqs.append((m.timestamp, bytes(m.data)))
inw = [(datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S.%f')[:-3], d.hex()) for ts, d in reqs if pend[0] < ts < pend[-1]]
print(f"70E requests inside wedge: n={len(inw)}")
for wc, h in inw: print(f"  {wc} {h}")
