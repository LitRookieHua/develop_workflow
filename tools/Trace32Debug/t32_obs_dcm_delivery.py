"""T32 观察 PduR_GF_TP_Dcm_Transmit_Func 交付时刻的长度错配（6762/6763 取证）。

断点停在函数入口，读 info 参数与 FIFO 会话状态，随后自动 Go 继续运行。
用于配合 DiagnosticTester 最小化用例，抓取推迟交付路径的实时证据。
"""
import sys
import time

PLUGIN_PY = r"C:\Users\YH\.claude\plugins\cache\imo-ai-agent-plugin-marketplace\imo-plugin-t32-toolkit\1.1.0\skills\t32-plugin\references\python"
sys.path.insert(0, PLUGIN_PY)

import t32_utils  # noqa: E402
import hang_common  # noqa: E402

FUNC_ADDR = 0x400975D0          # PduR_GF_TP_Dcm_Transmit_Func
FIFO_FIXED = 0x402A6B84         # PduR_gw_Tp_buf_PduRTxBuffer_FUNC_FUNC (const)

# PduR_TpSession_Dynamic 布局（PDUR_MULTICAST_FROM_TP=1, 无 S&F, MAX_QUEUEDEPTH=4）
# ⚠ PduLengthType=uint16（ComStack_Cfg.h），长度字段全部 u16：
#   0x00 bufferPtr | 0x04 readPtr | 0x08 writePtr | 0x0C metaDataPtr | 0x10 infoPtr
#   0x14 numRxLength_auo u16[4] | 0x1C numTxLength u16 | 0x1E SduLength_auo u16[4]
#   0x26 bufferLength u16 | 0x28 gwIdInstance | 0x2A Rx_Status | 0x2B Tx_Status
#   0x2C Tx_E_OK_Count | 0x2D Rx_FifoInstanceUsed | 0x2E Tx_FifoInstanceUsed
# PduInfoType: 0x00 SduDataPtr | 0x04 MetaDataPtr | 0x08 SduLength(u16)

MAX_HITS = 6
TIMEOUT_S = 90


def u32(dbg, addr):
    return hang_common.read32(dbg, addr)


def dump_session(dbg, sess):
    d = {}
    d["readPtr"] = u32(dbg, sess + 0x04)
    d["infoPtr"] = u32(dbg, sess + 0x10)
    w = u32(dbg, sess + 0x14)
    w2 = u32(dbg, sess + 0x18)
    d["numRx[0..3]"] = [w & 0xFFFF, w >> 16, w2 & 0xFFFF, w2 >> 16]
    w = u32(dbg, sess + 0x1C)
    w2 = u32(dbg, sess + 0x20)
    w3 = u32(dbg, sess + 0x24)
    d["numTxLength"] = w & 0xFFFF
    d["SduLen[0..3]"] = [w >> 16, w2 & 0xFFFF, w2 >> 16, w3 & 0xFFFF]
    d["bufferLength"] = w3 >> 16
    w = u32(dbg, sess + 0x28)
    d["Rx_Status"] = (w >> 16) & 0xFF
    d["Tx_Status"] = (w >> 24) & 0xFF
    w = u32(dbg, sess + 0x2C)
    d["Rx_Fifo"] = (w >> 8) & 0xFF
    d["Tx_Fifo"] = (w >> 16) & 0xFF
    rp = d["readPtr"]
    if rp:
        d["readPtr_data"] = f"{u32(dbg, rp):08X} {u32(dbg, rp + 4):08X}"
    return d


def main():
    node, port = t32_utils.resolve_node_port()
    t32rcl = t32_utils.require_rcl()
    with t32rcl.connect(node=node, port=port, packlen=1024) as dbg:
        dbg.cmd("Break.Delete")
        dbg.cmd(f"Break.Set 0x{FUNC_ADDR:08X} /Program")
        try:
            running = int(dbg.fnc("STATE.RUN()"))
        except Exception:
            running = 0
        if not running:
            dbg.cmd("Go")
        print("ARMED: breakpoint set, target running", flush=True)

        hits = 0
        t0 = time.time()
        while time.time() - t0 < TIMEOUT_S and hits < MAX_HITS:
            try:
                running = int(dbg.fnc("STATE.RUN()"))
            except Exception:
                time.sleep(0.05)
                continue
            if running:
                time.sleep(0.002)
                continue
            pc, _ = hang_common.read_reg(dbg, "pc")
            r0, _ = hang_common.read_reg(dbg, "r0")
            r1, _ = hang_common.read_reg(dbg, "r1")
            rec = {"hit": hits + 1, "pc": f"{pc:08X}" if pc else "?",
                   "id": r0, "info_ptr": r1}
            if r1:
                rec["info.SduDataPtr"] = u32(dbg, r1)
                rec["info.MetaDataPtr"] = u32(dbg, r1 + 4)
                rec["info.SduLength"] = u32(dbg, r1 + 8) & 0xFFFF
                dp = rec["info.SduDataPtr"]
                if dp:
                    rec["info.data[0..7]"] = f"{u32(dbg, dp):08X} {u32(dbg, dp + 4):08X}"
            conn = u32(dbg, FIFO_FIXED + 4)
            if conn:
                sess = u32(dbg, conn)
                if sess:
                    rec["session"] = dump_session(dbg, sess)
            print("HIT " + repr(rec), flush=True)
            hits += 1
            dbg.cmd("Go")
        dbg.cmd("Break.Delete")
        try:
            running = int(dbg.fnc("STATE.RUN()"))
        except Exception:
            running = 0
        if not running:
            dbg.cmd("Go")
        print(f"DONE hits={hits}", flush=True)


if __name__ == "__main__":
    main()
