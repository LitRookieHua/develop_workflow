# T09 G710 CanTp/Dcm 链路日志插桩

诊断请求黑洞（1101/2E 零响应）取证用：在 CanTp RX/TX 与 DCM DSL 关键路径加 14 个日志点，
经 `Log_FunSync`（= LogSyncAcoreOnly，`Log_Sync.h`）输出到 A 核 `/log/mcu/message`。

## 固件映射

| 项 | 值 |
| --- | --- |
| 问题固件基线 | package 19076 = `release/GAC/T09_Y1_D126/G710`（commit 68e497b4） |
| 插桩分支 | `feature/idc310gac-8553-1101-zero-response`（服务器 12.42 V2 工作区 mcu_app_j6） |
| 插桩 commit | 35b07f7ac（+148/-1，4 文件，全部带 `<T09PATCH P1>` patch 标记） |
| 编译 preset | `cpj_gac_t09_d310`（`.imobuilder` build_product = `Gac/T09Y1_D126/release/GAC_T09_Y1_D126_G710`） |

## 应用方法

- 服务器上直接 cherry-pick：`git cherry-pick 35b07f7ac`（依赖仓库同用 G710 分支，否则出现 usssensl 结构体成员编译错——该行与诊断链路无关，可屏蔽）
- 或对本目录 `0001-cantp-dcm-chain-debug-logging.patch` 执行 `git am` / `git apply`
- 基线不同时按 `<T09PATCH P1>` 标记定位人工移植；Log_FunSync 原型用 extern 声明就地引入，避免 BSW 头文件路径问题

## 日志点目录（grep 前缀）

| 前缀 | 位置 | 记录内容 |
| --- | --- | --- |
| `CTP RXI` | CanTp.c RxIndication 入口 | rxid/ch/sub(通道子状态)/fd/d0-d3/dl（3E80 过滤不记） |
| `CTP TXQ` | CanTp.c CanTp_Transmit 入口 | id/len/d0-d2/main |
| `CTP TXC` | CanTp.c TxConfirmation | id/res/main |
| `CTP SFREJ` | CanTp_Prv.c GetConnectionAcceptance SF 拒绝分支（**头号嫌疑**） | sub/act/tp 标记（3E80 被拒也记录，带 tp 标记） |
| `CTP FFREJ` | 同上 FF 路径 | 同上 |
| `CTP SOR` | SF PduR_CanTpStartOfReception 返回值 | ret（3E80 过滤） |
| `CTP FF SOR` | FF 路径 | ret |
| `DCM SOR` / `DCM SORRET` | Dcm_Dsl_StartOfReception 入口/出口 | reason/ret（3E80 过滤） |
| `DCM BUSY` | IsDslBusyWithRequest 分支 | DSL busy 门控命中 |
| `DCM TXR` | Dcm_Dsl_ResponseTransmission.c SendResponse 入口 | len/d0-d2 |
| `DCM TXRD` | PduR_DcmTransmit 返回值 | ret；`full=0` 变体 = deferral 分支 |

smprintf 仅支持 `%d/%02x/%s`（无长度修饰符）；日志走同步通道，量级为每诊断帧 1 行，3E80 已过滤防刷屏。

## 判别矩阵（黑洞命中后对时刻窗口 grep）

| 日志表现 | 结论 |
| --- | --- |
| 1001 时刻有 `CTP RXI` 无下文 + `CTP SFREJ sub=非IDLE` | CanTp RX 通道卡死（GetConnectionAcceptance 静默拒绝） |
| 1001 时刻 `CTP SOR ret≠OK` 且无 SFREJ | PduR/DCM 层拒绝 |
| `DCM BUSY` 命中 | DCM DSL busy 门控（StartOfReception→NOT_OK→CanTp 静默丢弃） |
| 3E80 同窗口出现 `CTP SFREJ ... tp` | 通道级问题波及功能寻址（0x70E 与 0x7DF 共用 channel 0） |
| pendings 全程 `DCM TXR/TXRD` 正常 | TX 链活着，楔死在 app/IPC 层（IpcDiagSvc GET_REQUEST_STATE 持续 BUSY） |
