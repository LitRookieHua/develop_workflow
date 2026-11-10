"""分析失败窗口 BLF：还原失败 1101 前后的完整诊断交互时间线。
重点：0x70E/0x78E/0x7DF 全部帧 + 0x50e 出现时段 + 成功轮 vs 失败轮结构差异。
"""
import sys
import can

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

T0 = 1793631356.2676
src = "tests/harness/dcm_pki_ecureset_8402/1101没有回复_failwin_pm120s.blf"

diag = []
p50e = []
for m in can.BLFReader(src):
    aid = m.arbitration_id
    rel = m.timestamp - T0
    if aid in (0x70E, 0x78E, 0x7DF):
        d = m.data
        # PCI 解析（标准 CAN 帧假设，SF/FF/CF 或裸报文）
        diag.append((rel, aid, bytes(d)))
    elif aid == 0x50e:
        p50e.append((rel, bytes(m.data)))

print(f"diag frames: {len(diag)}, 0x50e frames: {len(p50e)}")
if p50e:
    print(f"0x50e span: [{p50e[0][0]:.3f}, {p50e[-1][0]:.3f}] n={len(p50e)}")
    gaps = [(a, b - a) for (a, _), (b, _) in zip(p50e, p50e[1:]) if b - a > 1.0]
    print(f"0x50e >1s gaps: {gaps[:10]}")
    print(f"0x50e first data: {p50e[0][1].hex()}  last data: {p50e[-1][1].hex()}")

def fmt_pci(d):
    if not d:
        return "?"
    pci = d[0] >> 4
    if pci == 0:
        return f"SF len={d[0] & 0xf} {d[1:1+(d[0]&0xf)].hex()}"
    if pci == 1:
        return f"FF len={(d[0]&0xf)<<8|d[1]} {d[2:].hex()}"
    if pci == 2:
        return f"CF sn={d[0]&0xf} {d[1:].hex()}"
    if pci == 3:
        return f"FC fs={d[0]&0xf} bs={d[1] if len(d)>1 else '?'} stmin={d[2] if len(d)>2 else '?'}"
    return f"RAW {d.hex()}"

print("\n=== 诊断时间线（rel / dir / ID / PCI）===")
for rel, aid, d in diag:
    direction = "RX" if aid in (0x70E, 0x7DF) else "TX"
    print(f"{rel:10.3f} {direction} {aid:03X} {fmt_pci(d)}")
