"""统计 diag_timeline.txt 中 1101 请求的完整结局分布。
每行格式: abs_ts id datahex rx
t0 = 1793631356.2676
"""
import collections

T0 = 1793631356.2676

req1101 = []      # (rel, data 前 8 hex)
resp_after = []   # 每个请求的结局
pend78 = 0
n5101 = 0
n7f11 = 0

lines = open(".tmp/diag_timeline.txt", encoding="utf-8").read().splitlines()
print(f"total lines: {len(lines)}")

# 先收集全部 70E 上的 1101 请求（SF: 02 11 01）
events = []  # (rel, id, data16, kind)
for ln in lines:
    parts = ln.split()
    if len(parts) < 4:
        continue
    ts, aid, data = float(parts[0]), parts[1], parts[2]
    rel = ts - T0
    if aid == "0x70e" and data[:6] == "021101":
        events.append((rel, "REQ1101", data))
    elif aid == "0x78e" and data[:6] == "025101":
        events.append((rel, "5101", data))
    elif aid == "0x78e" and data[:8] == "037F1178":
        events.append((rel, "PEND78", data))
    elif aid == "0x78e" and data[:4] == "037F" and data[4:8] == "1111":
        events.append((rel, "NRC7F11", data))

# 按 1101 请求分组结局
groups = []
cur = None
for rel, kind, data in events:
    if kind == "REQ1101":
        if cur:
            groups.append(cur)
        cur = {"req": rel, "pend": 0, "ok": None, "nrc": None}
    elif cur is not None:
        if kind == "PEND78":
            cur["pend"] += 1
        elif kind == "5101":
            cur["ok"] = rel
        elif kind == "NRC7F11":
            cur["nrc"] = rel
if cur:
    groups.append(cur)

print(f"\ntotal 1101 requests: {len(groups)}")
outcome = collections.Counter()
for g in groups:
    if g["ok"] is not None:
        outcome["5101 OK"] += 1
    elif g["nrc"] is not None:
        outcome["NRC 7F11"] += 1
    elif g["pend"] > 0:
        outcome[f"pending-only"] += 1
    else:
        outcome["ZERO response"] += 1
print("outcomes:", dict(outcome))

# 请求间隔直方图（看 60s 节奏）
ivals = [round(groups[i + 1]["req"] - groups[i]["req"]) for i in range(len(groups) - 1)]
ih = collections.Counter(ivals)
print("interval histogram (top):", dict(sorted(ih.items(), key=lambda x: -x[1])[:10]))

# 失败组（零响应 / pending-only）详情
print("\nfailed/pending-only groups:")
for i, g in enumerate(groups):
    if g["ok"] is None and g["nrc"] is None:
        print(f"  #{i + 1} req_rel={g['req']:.3f} pend={g['pend']}")

# 最后 5 组时间线
print("\nlast 5 groups:")
for g in groups[-5:]:
    print(f"  req={g['req']:.3f} pend={g['pend']} ok={'%.3f' % g['ok'] if g['ok'] else None} nrc={g['nrc']}")

# 最后一次 1101 之后 78E 上有任何帧吗
last_req = groups[-1]["req"]
after = [(float(p[0]) - T0, p[1], p[2]) for p in (ln.split() for ln in lines)
         if len(p) >= 4 and float(p.split()[0] if False else 0) == 0 or True]
# 简化：直接过滤
after = []
for ln in lines:
    parts = ln.split()
    if len(parts) < 4:
        continue
    rel = float(parts[0]) - T0
    if rel > last_req and parts[1] == "0x78e":
        after.append((rel, parts[2]))
print(f"\nframes on 78E after last 1101 (rel {last_req:.3f}): n={len(after)}")
for rel, d in after[:10]:
    print(f"  {rel:.3f} {d}")

# 最后 3 分钟 70E/78E/7DF 帧数（看脚本是否还在发请求）
tail_lines = [ln.split() for ln in lines if len(ln.split()) >= 4]
t_end = float(tail_lines[-1][0]) - T0
print(f"\ntimeline end rel={t_end:.1f}, last 1101 at {last_req:.1f}, silence={t_end - last_req:.1f}s")
