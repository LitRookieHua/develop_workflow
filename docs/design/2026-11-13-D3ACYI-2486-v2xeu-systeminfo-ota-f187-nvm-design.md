# v2xeu systeminfo/OTA F187 改读 NVM 需求与设计说明文档

| 项 | 内容 |
| --- | --- |
| 工单 | D3ACYI-2486（接口故障期间曾暂记 D3ACYI-2360，作废） |
| 项目/变体 | iCAR V2X EU（Chery D065，TDA4）/ V25/V27 海外 |
| 日期 | 2026-11-13 |
| 分支 | develop + release/Chery/V2XEU_D065/V460 |
| 状态 | PR 评审中（PR 660 develop / PR 661 V460） |

## 一、概述

### 1.1 功能背景与目标

v2xeu 的 F187（Vehicle Manufacturer Spare Part Number）在 0x22 诊断读（`gType_ov_dia_DID_ReadHandler_0xF187`）从 NVM 块 `NVM_PDM_VehicleManufacturerSparePartNumber` 读取（产线/诊断可写，真实值），但两条对 A 核的输出路径却用 version_did 生成的静态变体数组 `g_DidData_F187_au8_v2xeu`（硬编码），导致 A 核侧（OTA 升级包校验、系统信息展示）拿到的 F187 与诊断读值可能不一致。本次把两条输出路径统一改为参考 `gType_ov_dia_DID_ReadHandler_0xF187` 从 NVM 读：

1. `udsReadManufacturerSparePartNumber`（OTA 路径，download_manager_cfg，E_UDS_COMMAND_R_SERIAL_NUMBER 命令族）
2. `deliverMcuSystemInfo`（systeminfo IPC，CMCUSystemInfoOutput.m_vehicleManufacturerEcuPartNumber）

### 1.2 适用范围

- 仓库：仅 `mcu_app_tda4`（cpj_chery/veh_v2xeu）
- 分支：develop + `release/Chery/V2XEU_D065/V460`（V460 经 cherry-pick）
- 不含：0x22 读 handler 本身（已是 NVM 读法，作为参考实现不动）、version_did 仓库（静态数组仍保留，未消费后自然失效）

### 1.3 参考文档

| 编号 | 文档/单号 | 关联内容 |
| --- | --- | --- |
| R1 | [[T1LFL1 Change deliverMcuSystemInfo function]]（D1CYC-1561） | deliverMcuSystemInfo F187 数据流先例 |
| R2 | [[T1LFL1 add t1nfl3 vehicle]]（D1CYC-2381） | udsReadManufacturerSparePartNumber 变体索引先例 |
| R3 | 0x22 handler `gType_ov_dia_DID_ReadHandler_0xF187` | 本次统一的目标读法（参考实现） |

### 1.4 约束与假设

- NVM 块长度 16 字节（`NVM_CFG_NV_BLOCK_LENGTH_NVM_PDM_VehicleManufacturerSparePartNumber`），与 OTA 路径长度宏 `VEHICLE_MANUFACTURER_SPARE_PART_NUMBER_LENGTH (16u)` 一致；A 核字段 `m_vehicleManufacturerEcuPartNumber` 长度 `MCU_INFO_DID_LENGTH_0xF187`（默认填 0 值 DIA_DID_DEFLAUT_VALUE 后 memcpy）
- 假设 `idiaIdBasedReadWrite` 在两处调用上下文（ov_dia 周期任务 / uds 命令处理）均可安全调用——0x22 handler 与既有 F18B/F18C/F190 NVM 读法（同在 deliverMcuSystemInfo 内）已验证该模式

## 二、架构设计与数据流

```
NVM_PDM_VehicleManufacturerSparePartNumber (16B, NVM)
        │ idia::idiaIdBasedReadWrite(E_DIA_READ_REQUEST)
        ├─ gType_ov_dia_DID_ReadHandler_0xF187  （0x22 诊断读，现状不动，参考实现）
        ├─ udsReadManufacturerSparePartNumber   （OTA 路径，本次改：静态数组→NVM）
        │     └─ CReceiverManager.m_deliverData_au8 → IPC → OTA/下载管理
        └─ deliverMcuSystemInfo F187 段          （systeminfo，本次改：静态数组→NVM）
              └─ CMCUSystemInfoOutput.m_vehicleManufacturerEcuPartNumber → IPC → A 核
```

修改点（2 文件，均在 `cpj_chery/veh_v2xeu/dia_cfg/src/`）：

| 文件 | 函数 | 改动 |
| --- | --- | --- |
| `download_manager_cfg/uds_command_manager_cfg.cpp` | `udsReadManufacturerSparePartNumber()` | 删变体索引分支，改 `idiaIdBasedReadWrite(NvMConf_NvMBlockDescriptor_NVM_PDM_VehicleManufacturerSparePartNumber, ...)` 读 16B，读成功填 m_deliverData 返回 OK，失败返回 NOT_OK |
| `ov_diaRunnable.cpp` | `deliverMcuSystemInfo()` F187 段 | 删变体索引分支，改 NVM 读法（与同函数内 F18B/F18C/F190 段同模式），memcpy 到 `m_vehicleManufacturerEcuPartNumber` |

并发上下文：两处均在既有 ov_dia/uds 命令任务上下文同步执行，`idiaIdBasedReadWrite` 为该上下文安全接口（同函数既有 NVM 读法佐证），不引入新临界区。

## 三、异常处理与容错

- NVM 读失败（`idiaIdBasedReadWrite` 返回非 E_POSITIVE_RESPONSE）：OTA 路径返回 `RESPONSE_STATUS_NOT_OK`（原实现恒 OK）；systeminfo 路径保持 `m_vehicleManufacturerEcuPartNumber` 为 memset 默认值（0/DIA_DID_DEFLAUT_VALUE），不 publish 失败值
- 静态数组 `g_DidData_F187_au8_v2xeu` 保留（version_did 生成物），仅两处消费方不再引用；F189（同文件相邻段）不动

## 四、验证方案

1. 编译通过（SSH 12.42 TDA4 工作区，develop 与 V460 各一次）
2. 刷写后 DiagnosticTester：22 F187 读值 = NVM 值（写入 2E 后读回一致）；OTA/systeminfo 路径经台架联调确认（用户手动）
3. 验收标准：两路径 F187 输出与 NVM 块内容一致；0x22 读行为不变

## 附录A：需求追溯矩阵

| 需求 | 动作 |
| --- | --- |
| 用户需求：udsReadManufacturerSparePartNumber / deliverMcuSystemInfo 的 F187 参考gType_ov_dia_DID_ReadHandler_0xF187 | 两处改 NVM 读法，上传 develop + V460 |

## 附录B：ADR

- **ADR-1 读法统一到 NVM 而非反向（改 0x22 读静态数组）**：NVM 块是 F187 的权威存储（产线可写、2E 可写），0x22 读法为既有正确行为；两条 IPC 输出路径向它对齐单一数据源。代价：OTA/systeminfo 在 NVM 未初始化时输出默认值而非硬编码值；收益：诊断读/OTA/systeminfo 三路 F187 单一数据源，消除不一致。
- **ADR-2 不动 version_did**：静态数组由 version_did 生成，本单不删（避免跨仓库联动）；两处消费方改后数组成为无消费者冗余，后续清理另行立项。

## 附录C：开放问题

1. OTA 路径原实现读失败也返回 OK（恒 OK），本次改为失败返回 NOT_OK——若 OTA 下游对 NOT_OK 有重试/告警逻辑差异，评审时确认；保守方案是失败也返回 OK 但内容为默认值。
