"""从 bench BLF（单节点，DUT 自发=全部非诊断 ID）提取 DUT 周期报文 ID 集。
阈值：45min 内 >=200 帧（≈>=0.1Hz）视为周期报文。
输出 .tmp/dut_ids.txt（每行一个 hex id）
"""
import collections
import can

f = can.BLFReader("tests/harness/dcm_pki_ecureset_8402/logs/smoke_20261102_174328/trace.blf")
cnt = collections.Counter()
for m in f:
    aid = m.arbitration_id
    if aid in (0x70E, 0x78E, 0x7DF):
        continue
    cnt[aid] += 1

periodic = sorted(a for a, c in cnt.items() if c >= 200)
print(f"bench IDs total={len(cnt)} periodic(>=200 in 45min)={len(periodic)}")
print("top 40:", [(hex(a), cnt[a]) for a in sorted(cnt, key=lambda x: -cnt[x])[:40]])
with open(".tmp/dut_ids.txt", "w") as out:
    for a in periodic:
        out.write(f"{a:x}\n")
print("written .tmp/dut_ids.txt")
