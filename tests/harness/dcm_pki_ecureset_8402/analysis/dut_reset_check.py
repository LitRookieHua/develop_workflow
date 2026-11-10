"""检查测试 BLF 中 DUT 的 22 个周期 ID：
1) 阳性对照：成功 1101（rel 61017.354→5101@61018.230，ECU 真复位）后 DUT ID 同步缺口
2) 失败 1101（rel 61084.884 零响应）后同样窗口有无缺口 → 判断复位是否执行
3) DUT ID 是否持续到 capture 结束（app 存活）
"""
import collections
import can

T0 = 1793631356.2676
GOOD_RESET = 61018.230   # 成功轮 5101 时刻（复位执行点）
FAIL_1101 = 61084.884     # 失败 1101 TX 时刻
START = 60300.0           # 开始记录的相对时刻（含成功轮作对照）

dut = {int(x, 16) for x in open(".tmp/dut_ids.txt").read().split()}
print(f"DUT ids: n={len(dut)}")

per_id = collections.defaultdict(list)  # aid -> [rel,...]
t_end = None
n_match = 0

f = can.BLFReader("tests/harness/dcm_pki_ecureset_8402/1101没有回复.blf")
for m in f:
    aid = m.arbitration_id
    if aid in dut:
        rel = m.timestamp - T0
        t_end = rel
        if rel >= START:
            per_id[aid].append(rel)
            n_match += 1

print(f"recorded frames rel>={START}: {n_match}, capture_end_rel={t_end:.1f}" if t_end else "no frames")

def gaps_in(id_rels, lo, hi):
    """返回 [(gap_start, dur)] 完全落在 [lo,hi] 内的相邻帧缺口（>0.2s）"""
    out = []
    for a, b in zip(id_rels, id_rels[1:]):
        if lo <= a and b <= hi + 5 and b - a > 0.2:
            out.append((a, b - a))
    return out

print(f"\n=== 阳性对照：成功复位 @ {GOOD_RESET}（窗口 [{GOOD_RESET-2}, {GOOD_RESET+30}]）===")
agg = collections.Counter()
for aid, rels in sorted(per_id.items()):
    g = gaps_in(rels, GOOD_RESET - 2, GOOD_RESET + 30)
    if g:
        biggest = max(g, key=lambda x: x[1])
        agg[round(biggest[0] - GOOD_RESET, 1)] += 1
        print(f"  {hex(aid)}: max gap start={biggest[0]:.3f} (rel+{biggest[0]-GOOD_RESET:.3f}) dur={biggest[1]:.3f}")
    else:
        print(f"  {hex(aid)}: no gap>0.2s")
print("gap-start offsets histogram:", dict(sorted(agg.items())))

print(f"\n=== 失败 1101 @ {FAIL_1101}（窗口 [{FAIL_1101-2}, {FAIL_1101+60}]）===")
agg2 = collections.Counter()
for aid, rels in sorted(per_id.items()):
    g = gaps_in(rels, FAIL_1101 - 2, FAIL_1101 + 60)
    if g:
        biggest = max(g, key=lambda x: x[1])
        agg2[round(biggest[0] - FAIL_1101, 1)] += 1
        print(f"  {hex(aid)}: max gap start={biggest[0]:.3f} (rel+{biggest[0]-FAIL_1101:.3f}) dur={biggest[1]:.3f}")
    else:
        print(f"  {hex(aid)}: no gap>0.2s")
print("gap-start offsets histogram:", dict(sorted(agg2.items())))

print("\n=== DUT 存活性：各 ID 最后一帧相对时刻（capture_end 以上=活着）===")
for aid, rels in sorted(per_id.items()):
    print(f"  {hex(aid)}: last={rels[-1]:.1f} n={len(rels)}")
