#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
uds_log_analyzer.py — 离线解析 CAN 报文日志（BLF/ASC/PCAP 等），检测 UDS 异常事件

检测类别:
  1. 请求无响应          — 请求在超时时间内无任何正/负响应（按 SID 队列配对, 允许乱序）
  2. NRC78 PENDING 挂死  — 收到 7F <sid> 78 后, 规定时间内无最终响应
  3. NRC 负响应          — 按 (服务, NRC) 聚合为事件（连续相同 NRC 合并成一个事件）
  4. 多帧传输未完成      — ISO-TP FF/CF 序列被中断
  5. S3 会话超时         — 诊断通道静默超过 S3 且处于非默认会话 → 会话回落默认会话
                          （已考虑 0x7DF 功能寻址 3E80 保活; 静默期间有保活则不报）
  6. 响应延迟异常        — 无 NRC78 前导的慢响应（P2 首帧时序问题）, 附全量延迟统计

用法:
  python uds_log_analyzer.py trace.blf
  python uds_log_analyzer.py trace.blf --ignore-nrc 22 --out report.txt
  python uds_log_analyzer.py trace.blf --req-id 0x70E --res-id 0x78E

参数:
  --req-id HEX          请求 CAN ID（不指定则自动识别: XOR 0x80 配对 + UDS 内容校验）
  --res-id HEX          响应 CAN ID（不指定则自动识别）
  --ignore-nrc 22,7F    忽略指定 NRC（testcase 期望结果, 非异常）
  --timeout 5.0         请求响应超时（无响应判定）
  --pending-timeout 5.0 NRC78 后等待最终响应的时间
  --s3 5.0              S3 会话超时秒数
  --slow-threshold 0.05 响应延迟异常阈值秒数（0 关闭; 默认 50ms = P2ServerMax）
  --storm-gap 1.0       连续同类事件聚合窗口（间隔超过该值则拆分为两个事件）
  --out FILE            报告同时写入文件
"""

import argparse
import datetime
import sys
from bisect import bisect_left
from collections import deque

try:
    import can
except ImportError:
    print("需要 python-can: pip install python-can", file=sys.stderr)
    sys.exit(2)

SID_TABLE = {
    0x10: "DiagnosticSessionControl", 0x11: "ECUReset",
    0x14: "ClearDiagnosticInformation", 0x19: "ReadDTCInformation",
    0x22: "ReadDataByIdentifier", 0x23: "ReadMemoryByAddress",
    0x27: "SecurityAccess", 0x28: "CommunicationControl",
    0x2A: "ReadDataByPeriodicIdentifier", 0x2E: "WriteDataByIdentifier",
    0x2F: "InputOutputControlByIdentifier", 0x31: "RoutineControl",
    0x34: "RequestDownload", 0x35: "RequestUpload",
    0x36: "TransferData", 0x37: "RequestTransferExit",
    0x38: "RequestFileTransfer", 0x3D: "WriteMemoryByAddress",
    0x3E: "TesterPresent", 0x85: "ControlDTCSetting",
    0x86: "ResponseOnEvent", 0x87: "LinkControl",
}

RES_SIDS = {0x7F} | {sid | 0x40 for sid in SID_TABLE}

ROUTINE_SUB = {0x01: "start", 0x02: "stop", 0x03: "request-results"}

SESSION_NAMES = {0x01: "default", 0x02: "programming", 0x03: "extended"}

FUNCTIONAL_ID = 0x7DF

NRC_TABLE = {
    0x10: ("generalReject", "通用拒绝"),
    0x11: ("serviceNotSupported", "服务不支持"),
    0x12: ("subFunctionNotSupported", "子功能不支持"),
    0x13: ("incorrectMessageLengthOrInvalidFormat", "报文长度/格式错误"),
    0x14: ("responseTooLong", "响应超长"),
    0x21: ("busyRepeatRequest", "忙, 请重试"),
    0x22: ("conditionsNotCorrect", "条件不满足"),
    0x24: ("requestSequenceError", "请求序列错误"),
    0x25: ("noResponseAvailable", "无可用响应"),
    0x26: ("failurePreventsExecutionOfRequestedAction", "故障阻止执行请求动作"),
    0x31: ("requestOutOfRange", "请求超范围"),
    0x33: ("securityAccessDenied", "安全访问被拒(未解锁或解锁失败)"),
    0x34: ("authenticationRequired", "需要认证"),
    0x35: ("exceededNumberOfAttempts", "超过尝试次数"),
    0x36: ("requiredTimeDelayNotExpired", "延时未到(防暴力解锁)"),
    0x70: ("uploadDownloadNotAccepted", "不允许上传下载"),
    0x71: ("transferDataSuspended", "数据传输被挂起"),
    0x72: ("generalProgrammingFailure", "通用编程失败"),
    0x73: ("wrongBlockSequenceCounter", "块序列计数器错误"),
    0x78: ("requestCorrectlyReceivedResponsePending", "响应未就绪(PENDING)"),
    0x7E: ("subFunctionNotSupportedInActiveSession", "当前会话不支持该子功能"),
    0x7F: ("serviceNotSupportedInActiveSession", "当前会话不支持该服务"),
}

NRC_HINTS = {
    0x7F: "常见原因: S3 超时后会话已回落默认会话, 或会话切换丢失",
    0x7E: "常见原因: S3 超时后会话已回落默认会话",
    0x22: "ECU 内部条件不满足(应用层状态机限制), 若对外状态已空闲则属状态失配",
    0x33: "请求前未完成 SecurityAccess 解锁, 或解锁计数/延时限制",
    0x24: "服务执行顺序错误(如未 start 就 request-results)",
    0x78: "PENDING 为协议正常行为, 仅在无最终响应时才构成异常",
}

NO_RESP_MERGE_GAP = 30.0  # 相同请求的连续无响应合并窗口


def parse_hex(s):
    return int(s, 16)


def fmt_hex(data):
    return " ".join("%02x" % b for b in data)


def fmt_time(t, base):
    dt = datetime.datetime.fromtimestamp(t)
    return "%s (rel %.3fs)" % (dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], t - base)


def fmt_sid(data, is_req):
    """请求/响应报文的可读描述"""
    if not data:
        return "(空)"
    sid = data[0]
    if sid == 0x7F and len(data) >= 3:
        name = SID_TABLE.get(data[1], "?")
        return "负响应 service 0x%02X(%s) NRC 0x%02X" % (data[1], name, data[2])
    name = SID_TABLE.get(sid if is_req else sid & ~0x40, "?")
    if not is_req:
        sid &= ~0x40
    desc = "0x%02X(%s)" % (sid, name)
    if sid == 0x31 and len(data) >= 4:
        desc += " sub=%s routine=0x%02X%02X" % (
            ROUTINE_SUB.get(data[1], hex(data[1])), data[2], data[3])
    elif sid == 0x10 and len(data) >= 2:
        desc += " session=%s" % SESSION_NAMES.get(data[1], hex(data[1]))
    return ("请求 " if is_req else "响应 ") + desc


class IsoTpReassembler:
    """单方向 ISO-TP 重组: SF/FF/CF -> 完整 UDS 报文, FC 跳过"""

    def __init__(self):
        self.buf = None  # [t_start, total_len, bytearray]
        self.incomplete = []  # [(t_start, got, total)]

    def feed(self, t, data):
        """返回 (t_start, uds_bytes) 或 None"""
        if not data:
            return None
        pci = data[0] >> 4
        if pci == 0x0:  # SingleFrame（含 CAN FD SF escape: 00 <len> <payload>）
            if self.buf is not None:
                self.incomplete.append((self.buf[0], len(self.buf[2]), self.buf[1]))
                self.buf = None
            if data[0] == 0x00:
                if len(data) < 2:
                    return None
                ln = data[1]
                payload = data[2:2 + ln]
            else:
                ln = data[0] & 0x0F
                payload = data[1:1 + ln]
            return (t, bytes(payload)) if ln > 0 else None
        if pci == 0x1:  # FirstFrame
            if self.buf is not None:
                self.incomplete.append((self.buf[0], len(self.buf[2]), self.buf[1]))
            total = ((data[0] & 0x0F) << 8) | data[1]
            self.buf = [t, total, bytearray(data[2:])]
            return None
        if pci == 0x2:  # ConsecutiveFrame (data[0]&0x0F 是序列号, 载荷为其后全部字节)
            if self.buf is None:
                return None
            self.buf[2].extend(data[1:])
            if len(self.buf[2]) >= self.buf[1]:
                out = (self.buf[0], bytes(self.buf[2][:self.buf[1]]))
                self.buf = None
                return out
            return None
        return None  # FlowControl 等

    def finish(self):
        if self.buf is not None:
            self.incomplete.append((self.buf[0], len(self.buf[2]), self.buf[1]))
            self.buf = None


def _sf_sid(data):
    """单帧则返回 UDS 首字节(SID), 否则 None"""
    if not data or (data[0] >> 4) != 0:
        return None
    ln = data[0] & 0x0F
    if ln == 0 or 1 + ln > len(data):
        return None
    return data[1]


def detect_ids(path):
    """自动识别诊断请求/响应 ID 对（res = req ^ 0x80, 且内容须像 UDS）

    仅凭 XOR 0x80 配对会撞上普通周期报文, 因此按单帧首字节校验:
    请求通道 SID 在已知服务表内, 响应通道为 0x7F 或 SID+0x40。
    """
    hist = {}      # id -> 帧数
    req_like = {}  # id -> 单帧 SID 像请求的帧数
    res_like = {}  # id -> 单帧 SID 像响应的帧数
    n = 0
    for msg in can.LogReader(path):
        n += 1
        aid = msg.arbitration_id
        hist[aid] = hist.get(aid, 0) + 1
        sid = _sf_sid(bytes(msg.data))
        if sid is None:
            continue
        if sid in SID_TABLE:
            req_like[aid] = req_like.get(aid, 0) + 1
        if sid in RES_SIDS:
            res_like[aid] = res_like.get(aid, 0) + 1

    candidates = []
    for req, cnt in req_like.items():
        res = req ^ 0x80
        if res not in res_like:
            continue
        score = cnt + res_like[res]
        # 0x700-0x7EF 为标准诊断 ID 范围（排除功能寻址 0x7DF）
        in_diag_range = 0x700 <= req <= 0x7EF and req != FUNCTIONAL_ID
        candidates.append((in_diag_range, score, req, res))

    diag = [c for c in candidates if c[0]]
    if diag:
        # 诊断范围内的配对: 稀疏日志（如只录了故障轮次）也算, 低阈值即可
        best = max(diag, key=lambda c: c[1])
    else:
        generic = [c for c in candidates if c[1] >= 10]
        best = max(generic, key=lambda c: c[1]) if generic else None
    if best is None:
        return None, hist, n
    return (best[2], best[3]), hist, n


def load_uds_messages(path, req_id, res_id):
    """返回 (messages, meta); messages: (t, dir, data) dir='req'/'res'"""
    tx = IsoTpReassembler()
    rx = IsoTpReassembler()
    messages = []
    other_ids = {}
    functional_ts = []  # 0x7DF 帧时间戳（S3 保活判断用）
    first_frame_t = None
    for msg in can.LogReader(path):
        aid = msg.arbitration_id
        if first_frame_t is None:
            first_frame_t = msg.timestamp
        if aid == req_id:
            out = tx.feed(msg.timestamp, bytes(msg.data))
            if out:
                messages.append((out[0], "req", out[1]))
        elif aid == res_id:
            out = rx.feed(msg.timestamp, bytes(msg.data))
            if out:
                messages.append((out[0], "res", out[1]))
        elif aid == FUNCTIONAL_ID:
            functional_ts.append(msg.timestamp)
        else:
            other_ids[aid] = other_ids.get(aid, 0) + 1
    tx.finish()
    rx.finish()
    messages.sort(key=lambda m: m[0])
    functional_ts.sort()
    meta = {
        "first_frame_t": first_frame_t,
        "other_ids": other_ids,
        "functional_ts": functional_ts,
        "tx_incomplete": tx.incomplete,
        "rx_incomplete": rx.incomplete,
    }
    return messages, meta


def _functional_in_window(functional_ts, t_lo, t_hi):
    """窗口内是否有 0x7DF 帧（任何功能寻址请求都会刷新 S3）"""
    i = bisect_left(functional_ts, t_lo)
    return i < len(functional_ts) and functional_ts[i] <= t_hi


def _identifier(sid, data):
    """提取用于请求-响应配对的标识字节（正响应会回显请求标识）

    0x22/0x2E 按 DID, 0x31/0x2F 按 sub+DID, 0x27 等按子功能, 其余取前两字节。
    """
    if sid in (0x22, 0x2E):
        return bytes(data[1:3])
    if sid in (0x2F, 0x31):
        return bytes(data[1:4])
    if sid in (0x27, 0x28, 0x3E, 0x85, 0x11, 0x10, 0x87, 0x36, 0x37):
        return bytes(data[1:2])
    if sid == 0x14:
        return bytes(data[1:4])
    if sid == 0x19:
        return bytes(data[1:3])
    return bytes(data[1:3])


def analyze(messages, meta, timeout, pending_timeout, s3, slow_threshold,
            storm_gap, ignore_nrcs):
    events = []          # dict: kind,title,time,detail,msgs,reason
    queues = {}          # sid -> deque[(t, data)] 已发未答请求（按 SID 配对, 允许乱序到达）
    noresp_group = None  # 正在累积的无响应组
    pending78 = {}       # sid -> [t_last78, t_first78, req_data]
    nrc_runs = {}        # (sid,nrc) -> run dict
    slow_runs = {}       # sid -> run dict
    nrc_counts = {}      # (sid,nrc) -> 总数(含被过滤)
    latencies = []       # (latency, ) 已配对请求-响应延迟
    orphan_res = 0
    session = 0x01       # 当前会话（默认会话; 由 50 xx 正响应更新）
    prev_msg = None      # (t, dir, data) 上一条 UDS 报文（S3 静默检测用）
    base = messages[0][0] if messages else (meta["first_frame_t"] or 0)
    functional_ts = meta["functional_ts"]

    def close_noresp_group():
        nonlocal noresp_group
        if noresp_group:
            g = noresp_group
            dur = g["t_last_req"] - g["t_first"]
            if g["t_next"] is not None:
                reason = ("请求发出后 ECU 无任何响应（正/负响应均无）。%.1fs 后才出现下一条报文。"
                          "可能原因: 服务 handler PENDING 挂死、响应报文丢失、或 ECU 未收到请求。"
                          % (g["t_next"] - g["t_last_req"]))
            else:
                reason = ("请求发出后直到日志结束 ECU 无任何响应。"
                          "可能原因: PENDING 挂死或报文丢失。")
            events.append({
                "kind": "no_response",
                "_t": g["t_first"],
                "title": "请求无响应 ×%d" % len(g["reqs"]),
                "time": fmt_time(g["t_first"], base),
                "detail": "首次 %s, 最后一次 %s, 持续 %.1fs" % (
                    fmt_time(g["t_first"], base), fmt_time(g["t_last_req"], base), dur),
                "msgs": [("请求", fmt_hex(g["first_req"]),
                          fmt_sid(g["first_req"], True))],
                "reason": reason,
            })
            noresp_group = None

    def add_no_response(t_req, req_data, now_t):
        """超时未答的请求计入无响应组"""
        nonlocal noresp_group
        if noresp_group and noresp_group["last_data"] == req_data \
                and (t_req - noresp_group["t_last_req"]) <= NO_RESP_MERGE_GAP:
            noresp_group["reqs"].append(t_req)
            noresp_group["t_last_req"] = t_req
            noresp_group["t_next"] = now_t
        else:
            close_noresp_group()
            noresp_group = {
                "t_first": t_req, "t_last_req": t_req, "t_next": now_t,
                "first_req": req_data, "last_data": req_data, "reqs": [t_req],
            }

    def purge_expired(now_t):
        """把等待超过 timeout 的请求判为无响应"""
        for sid in list(queues):
            q = queues[sid]
            while q and now_t - q[0][0] > timeout:
                t_req, req_data = q.popleft()
                add_no_response(t_req, req_data, now_t)
            if not q:
                del queues[sid]

    def pop_request(sid, ident=None):
        """取走该服务的未答请求: 正响应按标识内容匹配, 负响应(无标识回显)按最旧。无则 None"""
        q = queues.get(sid)
        if not q:
            return None
        if ident is not None:
            for i, entry in enumerate(q):
                if _identifier(sid, entry[1]) == ident:
                    item = q[i]
                    del q[i]
                    if not q:
                        del queues[sid]
                    return item
            return None
        item = q.popleft()
        if not q:
            del queues[sid]
        return item

    def check_pending78_expiry(now_t):
        for sid in list(pending78):
            t_last, t_first, req_data = pending78[sid]
            if now_t - t_last > pending_timeout:
                events.append({
                    "kind": "nrc78_hang",
                    "_t": t_first,
                    "title": "NRC78 后无最终响应 (PENDING 挂死, service 0x%02X)" % sid,
                    "time": fmt_time(t_first, base),
                    "detail": "NRC78 首次 %s, 最后一次 %s, %.1fs 无最终响应" % (
                        fmt_time(t_first, base), fmt_time(t_last, base),
                        now_t - t_last),
                    "msgs": [
                        ("请求", fmt_hex(req_data), fmt_sid(req_data, True)),
                        ("响应", "7f %02x 78" % sid,
                         "负响应 service 0x%02X(%s) NRC 0x78(PENDING)" % (
                             sid, SID_TABLE.get(sid, "?")))],
                    "reason": "收到 NRC78 (requestCorrectlyReceivedResponsePending) 后 %.1fs 内"
                              "无最终响应 — 服务 PENDING 生命周期挂死。" % pending_timeout,
                })
                del pending78[sid]

    def close_nrc_run(key, run):
        sid, nrc = key
        name, zh = NRC_TABLE.get(nrc, ("unknown", "未知 NRC"))
        hint = NRC_HINTS.get(nrc, "")
        events.append({
            "kind": "nrc",
            "_t": run["t_first"],
            "title": "NRC 0x%02X %s (%s, service 0x%02X %s) ×%d" % (
                nrc, name, zh, sid, SID_TABLE.get(sid, "?"), run["count"]),
            "time": fmt_time(run["t_first"], base),
            "detail": "%s ~ %s, 持续 %.1fs" % (
                fmt_time(run["t_first"], base), fmt_time(run["t_last"], base),
                run["t_last"] - run["t_first"]),
            "msgs": [
                ("请求", fmt_hex(run["req_data"]) if run["req_data"] else "?",
                 fmt_sid(run["req_data"], True) if run["req_data"] else ""),
                ("响应", "7f %02x %02x" % (sid, nrc),
                 "负响应 service 0x%02X(%s) NRC 0x%02X(%s)" % (
                     sid, SID_TABLE.get(sid, "?"), nrc, name))],
            "reason": ("NRC 含义: %s。%s" % (zh, hint)) if hint else "NRC 含义: %s。" % zh,
        })

    def add_slow(sid, lat, t, req_data, res_data):
        """无 NRC78 前导的慢响应聚合"""
        run = slow_runs.get(sid)
        if run and (t - run["t_last"]) <= storm_gap:
            run["count"] += 1
            run["t_last"] = t
            run["max_lat"] = max(run["max_lat"], lat)
        else:
            if run:
                close_slow_run(sid, run)
            slow_runs[sid] = {
                "count": 1, "t_first": t, "t_last": t, "max_lat": lat,
                "req_data": req_data, "res_data": res_data,
            }

    def close_slow_run(sid, run):
        events.append({
            "kind": "slow_response",
            "_t": run["t_first"],
            "title": "响应延迟异常 (无 NRC78 前导, service 0x%02X %s) ×%d" % (
                sid, SID_TABLE.get(sid, "?"), run["count"]),
            "time": fmt_time(run["t_first"], base),
            "detail": "%s ~ %s, 最长延迟 %.0fms" % (
                fmt_time(run["t_first"], base), fmt_time(run["t_last"], base),
                run["max_lat"] * 1000),
            "msgs": [
                ("请求", fmt_hex(run["req_data"]) if run["req_data"] else "?",
                 fmt_sid(run["req_data"], True) if run["req_data"] else ""),
                ("响应", fmt_hex(run["res_data"]) if run["res_data"] else "?",
                 fmt_sid(run["res_data"], False) if run["res_data"] else "")],
            "reason": "响应耗时超过阈值且此前无 NRC78 (RCRRP) — 违反 P2ServerMax 时序。"
                      "典型根因: 服务首周期 PENDING 未按协议转成 NRC78（首帧响应延迟）。",
        })

    def check_s3_silence(t, cur):
        """诊断通道静默超过 S3 且非默认会话 → 会话回落事件"""
        nonlocal session, prev_msg
        if prev_msg is None:
            return
        gap = t - prev_msg[0]
        if gap <= s3 or session == 0x01:
            return
        if _functional_in_window(functional_ts, prev_msg[0], t):
            return  # 功能寻址保活在刷新 S3
        tp, dprev, dcur = prev_msg[0], prev_msg[2], cur[2]
        events.append({
            "kind": "s3_timeout",
            "_t": tp,
            "title": "诊断通道静默 %.1fs ≥ S3(%.1fs) — %s会话超时回落默认会话" % (
                gap, s3, SESSION_NAMES.get(session, hex(session))),
            "time": fmt_time(tp, base),
            "detail": "%s ~ %s, 静默 %.1fs" % (
                fmt_time(tp, base), fmt_time(t, base), gap),
            "msgs": [
                ("静默前", fmt_hex(dprev) if dprev else "?",
                 fmt_sid(dprev, prev_msg[1] == "req") if dprev else ""),
                ("静默后", fmt_hex(dcur) if dcur else "?",
                 fmt_sid(dcur, cur[1] == "req") if dcur else "")],
            "reason": "扩展/编程会话下诊断通道无任何请求/响应超过 S3 定时器, ECU 会话已回落"
                      "默认会话 — 后续受会话限制的服务将回 NRC 0x7F/0x7E, 安全访问状态同时丢失。"
                      "静默期间无 0x7DF 功能寻址保活。",
        })
        session = 0x01  # S3 已到期, 后续按默认会话看待

    for msg in messages:
        t, direction, data = msg
        check_pending78_expiry(t)
        purge_expired(t)
        check_s3_silence(t, msg)
        if direction == "req":
            sid = data[0] if data else None
            if sid is None:
                continue
            queues.setdefault(sid, deque()).append((t, data))
            prev_msg = msg
            continue

        # 响应: 与同 SID 最早未答请求配对
        if not data:
            prev_msg = msg
            continue
        if data[0] == 0x7F and len(data) >= 3:
            sid, nrc = data[1], data[2]
            key = (sid, nrc)
            nrc_counts[key] = nrc_counts.get(key, 0) + 1
            item = pop_request(sid)
            req_data = item[1] if item else None
            had78 = sid in pending78
            if item is None and not had78:
                orphan_res += 1
            if nrc == 0x78:
                # 78 是中间响应, 不计延迟; 最终响应到来时才配对完成
                if sid in pending78 and t - pending78[sid][0] <= storm_gap:
                    pending78[sid][0] = t
                else:
                    pending78[sid] = [t, t, req_data]
                prev_msg = msg
                continue
            if item is not None:
                latencies.append(t - item[0])
            if nrc not in ignore_nrcs:
                run = nrc_runs.get(key)
                if run and (t - run["t_last"]) <= storm_gap:
                    run["count"] += 1
                    run["t_last"] = t
                else:
                    if run:
                        close_nrc_run(key, run)
                    nrc_runs[key] = {
                        "count": 1, "t_first": t, "t_last": t,
                        "req_data": req_data,
                    }
            # 非78负响应 = 该服务的最终响应
            pending78.pop(sid, None)
            if slow_threshold and item is not None and not had78 \
                    and (t - item[0]) > slow_threshold:
                add_slow(sid, t - item[0], t, req_data, data)
        else:
            # 正响应: 按回显标识与请求配对
            sid = data[0] & ~0x40
            item = pop_request(sid, _identifier(sid, data))
            had78 = sid in pending78
            if item is None and not had78:
                orphan_res += 1
            elif item is not None:
                latencies.append(t - item[0])
            pending78.pop(sid, None)
            if slow_threshold and item is not None and not had78 \
                    and (t - item[0]) > slow_threshold:
                add_slow(sid, t - item[0], t, item[1], data)
            if data[0] == 0x50 and len(data) >= 2:
                session = data[1]
        prev_msg = msg

    # 收尾
    if messages:
        eof_t = messages[-1][0]
        check_pending78_expiry(eof_t + pending_timeout + 1)
        purge_expired(eof_t + timeout + 1)
        close_noresp_group()
    for key, run in list(nrc_runs.items()):
        close_nrc_run(key, run)
        del nrc_runs[key]
    for sid, run in list(slow_runs.items()):
        close_slow_run(sid, run)
        del slow_runs[sid]
    events.sort(key=lambda e: e["_t"])
    return events, nrc_counts, orphan_res, base, latencies


def render_report(path, events, nrc_counts, orphan_res, base, meta,
                  req_id, res_id, messages, auto_ids, ignore_nrcs,
                  latencies, slow_threshold):
    lines = []
    ap = lines.append
    ap("=" * 78)
    ap("UDS 日志分析报告: %s" % path)
    ap("=" * 78)
    if meta["first_frame_t"] is not None:
        t0 = datetime.datetime.fromtimestamp(meta["first_frame_t"])
        ap("文件首帧: %s" % t0.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
    if messages:
        ap("UDS 首报文: %s (文件首帧后 %.3fs)" % (
            fmt_time(messages[0][0], base)[:23],
            messages[0][0] - meta["first_frame_t"]))
    ap("诊断通道: req=0x%03X, res=0x%03X%s" % (
        req_id, res_id, " (自动识别)" if auto_ids else ""))
    n_req = sum(1 for m in messages if m[1] == "req")
    n_res = len(messages) - n_req
    ap("UDS 报文: %d (请求 %d / 响应 %d), 孤儿响应 %d" % (
        len(messages), n_req, n_res, orphan_res))
    if meta["functional_ts"]:
        ap("功能寻址 0x7DF 帧 %d (S3 保活判断用)" % len(meta["functional_ts"]))
    if latencies:
        ls = sorted(latencies)
        p95 = ls[min(len(ls) - 1, int(len(ls) * 0.95))]
        ap("响应延迟: %d 对配对, min %.0fms / avg %.0fms / P95 %.0fms / max %.0fms"
           % (len(ls), ls[0] * 1000, sum(ls) / len(ls) * 1000,
              p95 * 1000, ls[-1] * 1000))

    # NRC 总览（含被过滤的）
    if nrc_counts:
        ap("-" * 78)
        ap("NRC 总览 (按 服务/NRC 计数, 含被过滤项):")
        for (sid, nrc), cnt in sorted(nrc_counts.items(),
                                      key=lambda kv: -kv[1]):
            name, zh = NRC_TABLE.get(nrc, ("unknown", "未知 NRC"))
            mark = "  [已过滤 --ignore-nrc]" if nrc in ignore_nrcs else ""
            ap("  service 0x%02X NRC 0x%02X %-45s ×%d%s" % (
                sid, nrc, "%s (%s)" % (name, zh), cnt, mark))

    # 事件
    ap("-" * 78)
    if not events:
        ap("未检测到异常事件。")
    for i, ev in enumerate(events, 1):
        ap("")
        ap("[异常 %d] %s" % (i, ev["title"]))
        ap("  时间: %s" % ev["time"])
        ap("  %s" % ev["detail"])
        for role, hexs, desc in ev["msgs"]:
            if desc:
                ap("  %s: %s  (%s)" % (role, hexs, desc))
            else:
                ap("  %s: %s" % (role, hexs))
        ap("  原因: %s" % ev["reason"])

    # 多帧未完成
    inc = [("请求方向", x) for x in meta["tx_incomplete"]] + \
          [("响应方向", x) for x in meta["rx_incomplete"]]
    if inc:
        ap("-" * 78)
        ap("多帧传输未完成 ×%d:" % len(inc))
        for role, (t, got, total) in inc[:50]:
            ap("  [%s] %s: 收到 %d/%d 字节后中断" % (role, fmt_time(t, base), got, total))
        if len(inc) > 50:
            ap("  ... 其余 %d 项省略" % (len(inc) - 50))

    ap("")
    ap("=" * 78)
    ap("事件统计: %d 个" % len(events))
    for kind, label in [("no_response", "请求无响应"), ("nrc78_hang", "NRC78 挂死"),
                        ("nrc", "NRC 负响应"), ("s3_timeout", "S3 会话超时"),
                        ("slow_response", "响应延迟异常")]:
        n = sum(1 for e in events if e["kind"] == kind)
        if n:
            ap("  %s: %d" % (label, n))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="解析 CAN 报文日志, 检测 UDS 异常 (无响应/NRC/PENDING 挂死/S3 超时/响应延迟)")
    ap.add_argument("logfile", help="CAN 日志文件 (BLF/ASC/PCAP 等, python-can 支持的格式)")
    ap.add_argument("--req-id", type=parse_hex, default=None,
                    help="请求 CAN ID (hex, 如 0x70E; 缺省自动识别)")
    ap.add_argument("--res-id", type=parse_hex, default=None,
                    help="响应 CAN ID (hex, 如 0x78E; 缺省自动识别)")
    ap.add_argument("--ignore-nrc", default="",
                    help="忽略的 NRC 列表 (逗号分隔, hex, 如 22,7F)")
    ap.add_argument("--timeout", type=float, default=5.0,
                    help="请求响应超时秒数 (默认 5.0)")
    ap.add_argument("--pending-timeout", type=float, default=5.0,
                    help="NRC78 后等待最终响应秒数 (默认 5.0)")
    ap.add_argument("--s3", type=float, default=5.0,
                    help="S3 会话超时秒数 (默认 5.0)")
    ap.add_argument("--slow-threshold", type=float, default=0.05,
                    help="响应延迟异常阈值秒数, 0 关闭 (默认 0.05 = P2ServerMax 50ms)")
    ap.add_argument("--storm-gap", type=float, default=1.0,
                    help="连续同类事件聚合窗口秒数 (默认 1.0)")
    ap.add_argument("--out", default=None, help="报告输出文件")
    args = ap.parse_args()

    ignore_nrcs = set()
    if args.ignore_nrc:
        try:
            ignore_nrcs = {int(x.strip(), 16) for x in args.ignore_nrc.split(",")
                           if x.strip()}
        except ValueError:
            print("无效的 NRC 值: %s (应为 hex, 如 22,7F)" % args.ignore_nrc,
                  file=sys.stderr)
            sys.exit(2)

    auto_ids = False
    req_id, res_id = args.req_id, args.res_id
    if req_id is None and res_id is None:
        pair, _, _ = detect_ids(args.logfile)
        if pair is None:
            print("无法自动识别诊断 ID 对 (req^0x80=res 且内容像 UDS), "
                  "请用 --req-id/--res-id 指定", file=sys.stderr)
            sys.exit(2)
        req_id, res_id = pair
        auto_ids = True
    elif req_id is None:
        req_id = res_id ^ 0x80
    elif res_id is None:
        res_id = req_id ^ 0x80

    messages, meta = load_uds_messages(args.logfile, req_id, res_id)
    if not messages:
        print("该 ID 对上无 UDS 报文", file=sys.stderr)
        sys.exit(2)

    events, nrc_counts, orphan_res, base, latencies = analyze(
        messages, meta, args.timeout, args.pending_timeout, args.s3,
        args.slow_threshold, args.storm_gap, ignore_nrcs)
    report = render_report(
        args.logfile, events, nrc_counts, orphan_res, base, meta,
        req_id, res_id, messages, auto_ids, ignore_nrcs,
        latencies, args.slow_threshold)
    print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fp:
            fp.write(report + "\n")
        print("\n报告已写入 %s" % args.out, file=sys.stderr)


if __name__ == "__main__":
    main()
