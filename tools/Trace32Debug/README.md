# Trace32Debug

T32（TRACE32）实时调试/取证脚本的存放目录。用断点停机读内存的方式抓取运行时证据，配合 `tools/DiagnosticTester` 的用例执行使用（DiagnosticTester 发报文，本目录脚本观察目标机内部状态）。

## 使用前提

1. TRACE32 已启动，`config.t32` 配了 `RCL=NETTCP` + `PORT=23456`
2. 先用 `/t32-j6b-connect` skill 完成连接 + ELF 加载（生成 `.t32/connection.json` 缓存）

## ⚠️ 必须在本目录下运行脚本

插件的 `.t32/` 连接缓存按 `IMO_T32_CWD` 环境变量（未设则 CWD）解析——**在本目录下执行脚本**，缓存才会落到 `Trace32Debug/.t32/`：

```bash
cd tools/Trace32Debug
python t32_obs_dcm_delivery.py
```

或在任意位置前置环境变量：`export IMO_T32_CWD=<本目录绝对路径>`。

## 脚本清单

| 脚本 | 用途 |
| --- | --- |
| `t32_obs_dcm_delivery.py` | 断点 `PduR_GF_TP_Dcm_Transmit_Func` 入口，读 info 参数与 FIFO 会话状态后自动 Go——抓 PduR 组播推迟交付的长度错配（IDC310GAC-6762/6763 取证，2026-10-20） |

新增 T32 调试脚本一律放本目录，并在上表登记。脚本内的结构体偏移注释是取证时实算的现场知识，复用前按目标项目重新核对。

## 目录内容

- `t32_obs_dcm_delivery.py` 等调试脚本（入库）
- `.t32/` 连接缓存（本机状态：node/port/code_path/elf，含本机绝对路径）——已 gitignore，不入库
