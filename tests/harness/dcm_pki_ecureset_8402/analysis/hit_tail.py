import sys, datetime
import can
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
src = "tests/harness/dcm_pki_ecureset_8402/logs/smoke_20261104_144814/trace.blf"
frames = []
for m in can.BLFReader(src):
    aid = m.arbitration_id
    if aid in (0x70E, 0x78E, 0x7DF):
        frames.append((m.timestamp, aid, bytes(m.data), m.is_rx, getattr(m, 'is_fd', False)))
print(f"diag frames: {len(frames)}  span: {datetime.datetime.fromtimestamp(frames[0][0]).strftime('%H:%M:%S.%f')[:-3]} .. {datetime.datetime.fromtimestamp(frames[-1][0]).strftime('%H:%M:%S.%f')[:-3]}")

def fmt(d, fd):
    if not d: return "EMPTY"
    pci = d[0] >> 4
    if pci == 0:
        n = d[0] & 0xf
        if fd and n == 0 and len(d) > 1:
            n2 = d[1]
            return f"SF(fd) dl={n2} {d[2:2+min(n2,12)].hex()}"
        return f"SF len={n} {d[1:1+n].hex()}"
    if pci == 1: return f"FF len={(d[0]&0xf)<<8|d[1]} {d[2:].hex()}"
    if pci == 2: return f"CF sn={d[0]&0xf} {d[1:].hex()}"
    if pci == 3: return f"FC fs={d[0]&0xf} bs={d[1] if len(d)>1 else '?'} stmin={d[2] if len(d)>2 else '?'}"
    return f"RAW {d.hex()}"

pend = [ts for ts, aid, d, rx, fd in frames if aid == 0x78E and len(d) >= 3 and d[1:3] == b'\x2e\x78' and (d[0] & 0xf) == 3]
print(f"pendings n={len(pend)} first={datetime.datetime.fromtimestamp(pend[0]).strftime('%H:%M:%S.%f')[:-3] if pend else '-'} last={datetime.datetime.fromtimestamp(pend[-1]).strftime('%H:%M:%S.%f')[:-3] if pend else '-'}")
nrc10 = [(ts, d) for ts, aid, d, rx, fd in frames if aid == 0x78E and len(d) >= 3 and d[0:1] == b'\x7f' and d[2:3] != b'\x78']
print(f"78E terminal NRCs (non-pending): {[(datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S.%f')[:-3], d.hex()) for ts, d in nrc10]}")

print("\n=== tail from 15:04:30 (all non-3e80 + 3e80 gaps>3s) ===")
cutoff = None
for i, (ts, aid, d, rx, fd) in enumerate(frames):
    if aid == 0x78E and len(d) >= 3 and d[1:3] == b'\x2e\x78' and (d[0] & 0xf) == 3:
        pass
prev3e = None
for ts, aid, d, rx, fd in frames:
    wc = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S.%f')[:-3]
    if aid == 0x7DF:
        if prev3e is not None and ts - prev3e > 3.0:
            print(f"{wc} RX 7DF {fmt(d, fd)}  <-- GAP {ts-prev3e:.1f}s")
        prev3e = ts
        continue
    if wc >= "15:04:30":
        print(f"{wc} {'RX' if aid != 0x78E else 'TX'} {aid:03X} {fmt(d, fd)}")

print("\n=== 1001 probes vs nearest 78E within 5s ===")
probes = [ts for ts, aid, d, rx, fd in frames if aid == 0x70E and len(d) >= 2 and d[1:2] == b'\x01']
for ts in probes:
    wc = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S.%f')[:-3]
    if wc < "15:01:00": continue
    near = [(datetime.datetime.fromtimestamp(t2).strftime('%H:%M:%S.%f')[:-3], d2.hex()) for t2, a2, d2, r2, f2 in frames if a2 == 0x78E and 0 <= t2 - ts <= 5.0]
    print(f"{wc} 1001 -> {near if near else 'NO RESPONSE'}")
