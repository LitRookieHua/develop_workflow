# UdsLogAnalyzer — UDS 报文日志离线分析

离线解析 CAN 报文日志（BLF/ASC/PCAP 等，python-can 支持的格式），自动检测 UDS 异常事件。
来源于 IDC310GAC-4796/5999/6659/6398（EOL 标定 9AD4 压测）问题分析，把 BLF 逐帧人肉分析固化为工具。

## 检测类别

| # | 类别 | 说明 |
| --- | --- | --- |
| 1 | 请求无响应 | 请求在超时内无任何正/负响应（按 SID 队列配对，正响应按 DID/子功能内容匹配，允许乱序到达） |
| 2 | NRC78 PENDING 挂死 | 收到 `7F <sid> 78` 后规定时间内无最终响应 |
| 3 | NRC 负响应 | 按（服务, NRC）聚合，连续相同 NRC 合并为一个事件（风暴不刷屏） |
| 4 | 多帧传输未完成 | ISO-TP FF/CF 序列被中断 |
| 5 | S3 会话超时 | 诊断通道静默超过 S3 且处于非默认会话 → 会话回落（静默期间有 0x7DF 保活则不报） |
| 6 | 响应延迟异常 | 无 NRC78 前导的慢响应（P2 首帧时序问题），附全量延迟统计 |

输出：报错标题 / 报错时间 + 完整 UDS 报文（hex + 服务解析）/ 报错原因。

## 用法

    python uds_log_analyzer.py trace.blf
    python uds_log_analyzer.py trace.blf --ignore-nrc 22 --out report.txt
    python uds_log_analyzer.py trace.blf --req-id 0x70E --res-id 0x78E

常用参数：

- `--ignore-nrc 22,7F`：忽略指定 NRC（testcase 期望结果而非异常，如 NRC22 风暴是压测用例的预期负响应）
- `--req-id/--res-id`：缺省自动识别（XOR 0x80 配对 + SF 首字节 UDS 特征校验 + 优先 0x700-0x7EF 诊断 ID 范围）
- `--timeout 5.0`：无响应判定超时
- `--pending-timeout 5.0`：NRC78 后等待最终响应时间
- `--s3 5.0`：S3 会话超时
- `--slow-threshold 0.05`：响应延迟异常阈值（默认 50ms = P2ServerMax，0 关闭）
- `--storm-gap 1.0`：连续同类事件聚合窗口
- `--out FILE`：报告写入文件

依赖：`pip install python-can`（BLF 解析用，验证版本 4.6.1）。

## 解析能力

- ISO-TP 重组：经典单帧/首帧/连续帧，**CAN FD SF escape**（`00 <len> <payload>`，DLC 12/48/64 等非 8 帧），流控帧跳过
- 同一日志混跑经典 CAN 与 CAN FD 帧均可处理
- 时间输出为绝对墙钟 + 相对 UDS 首报文（rel）双基

## 实测验证

- `J6BREQ-11473_EOL标定9AD4.blf`（IDC310GAC-6659，87MB/268 万帧）：`--ignore-nrc 22` 后检出——请求无响应 ×1（被吞的 31019ad4，5.1s 静默）、S3 会话超时 ×2（5.1s 静默→会话回落）、NRC 0x7F 风暴 ×2046+×2886（自动揭示 tester 中途从 3101 切换 3103 重试）、NRC31（0x22）×6/轮
- `J6BREQ-10553_进标定压测9AD4_83.blf`（IDC310GAC-6398）：检出 NRC78 挂死 ×1（31019ad4 → 7F3178 → 11s 无最终响应）；407 帧 3E80 保活正确排除，无误报 S3 超时
