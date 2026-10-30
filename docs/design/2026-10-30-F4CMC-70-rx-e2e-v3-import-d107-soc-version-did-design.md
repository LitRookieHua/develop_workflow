# ⚙️ RX E2E V3.0 导入 + D107 SOC 版本 DID 需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | Dem E2E 事件配置 / Dcm DID 读取 | **所属软件层级** | BSW (Dem / Dcm / 诊断应用层) |
| **文档状态** | 🟡 待评审 | **安全与质量要求** | MISRA C:2012 ｜ 零警告 |
| **模块负责人 / 作者** | Hua.Yao / Claude | **关联输入/输出** | 📊 `IDC_EVM_Config_CMC_RX_V3.0_20261029.xlsx` ｜ 📑 [CMCRXJ6B-147](https://jira.imotion.ai:7070/browse/CMCRXJ6B-147) / [CMCRXJ6B-818](https://jira.imotion.ai:7070/browse/CMCRXJ6B-818) / [F4CMC-70](https://jira.imotion.ai:7070/browse/F4CMC-70) |

> **📝 变更记录**
> * `2026-10-30`｜Hua.Yao / Claude｜V1.0｜初版：V3.0 差异分析 + D107 实现设计

> 本需求为配置导入 + 小型 DID 变更，按模板精简规则省略部分详细设计小节，追溯见 JIRA。

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景**：客户侧（CMCRXJ6B-146，Jason Yu）于 2026-10-29 释放 RX 项目 E2E 诊断问卷 V3.0（历次：V1.0 2026-04-15 → V2.0 2026-08-21，上轮导入见 `docs/design/` 无、Obsidian「Rx update dtc table v2.0」）。同时需求 CMCRXJ6B-818 要求实现 D107（SOC 软件版本内部使用）。
* **核心目标**：
  1. 导入 V3.0 问卷（Event 定义、Event↔DTC mapping、ECG），生成物覆盖 `cpj_cmc` 对应文件
  2. D107 按需求矩阵实现：ASCII 8 字节、仅 $22、默认值 `V1.0.0`、未使用位 0x20 填充右对齐、无 NVM
* **设计原则**：完全复用既有生成链（`gen_e2e_dem.bat` 4 脚本）与 versionDid 机制（D19A 同型先例），不新增任何手写框架代码。

### 1.2 适用范围 (Scope)

* **适用控制器/平台**：CMC_RX_J6B 一体机（J6 平台，仓库 `mcu_app_j6` / `cpj_cmc`）
* **范围边界**：PF_Event 无变化；不涉及 A 核 IPC 改动；不涉及 NVM 新块。

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | [CMCRXJ6B-147 E2E导入](https://jira.imotion.ai:7070/browse/CMCRXJ6B-147) | — | 需求来源 |
| R2 | [CMCRXJ6B-818 SOC软件版本内部使用(D107)](https://jira.imotion.ai:7070/browse/CMCRXJ6B-818) | — | DID 属性矩阵 |
| R3 | [CMCRXJ6B-146 E2E版本释放](https://jira.imotion.ai:7070/browse/CMCRXJ6B-146) | V3.0 | 问卷 xlsx 附件 |
| R4 | [dtc-table-import.md](../../.claude/references/dtc-table-import.md) | — | 导入硬规则 |
| R5 | [autosar-code-generation.md](../../.claude/references/autosar-code-generation.md) | — | 生成路径与流程 |

### 1.5 设计约束与假设

* **技术约束**：autosar 生成一律在 10.0.13.10服务器执行（`ssh cp@10.0.13.10`），产物 scp 至 12.42 编译；Y: 盘禁止写源码。
* **外部假设**：V3.0 问卷已释放评审（R3）；表格无需修正（导入时如触发校验修正，按 R4 硬规则通知 Jason Yu）。

---

## 二、 架构设计与模块间交互 (Architecture & Interaction)

### 2.1 E2E 导入链（147）

```
V3.0 xlsx（cpj_cmc/tools/rx/e2e_dem/，删 V2.0 xlsx）
  → 10.0.13.10服务器 gen_e2e_dem.bat（4 脚本：Gen_Dem_Arxml / Gen_EventAvailable / Gen_Evm_FiMFID / Gen_zx_fimcfg）
  → J6B_Dem_EcucValues.arxml + Dem_PrjSpecificControl.c + evm_cfg_iSysFidCfg.cpp + evm_cfg_FidCfg.hpp + zx_sys_evm_cfg_fimcfg.hpp
  → scp → 12.42 编译
```

### 2.2 D107 数据链（818，D19A 同型）

```
version_did 仓库 modules/CMC/RX_C088.json（ZX_DID_D107: "V1.0.0"）
  → 模板渲染 templates/version_did.cpp.in / .hpp.in → g_DidData_D107_au8
  → mcu 0x22 handler 读 g_DidData_D107_au8，0x20 右对齐填充 8 字节
```

---

## 三、 核心逻辑与参数规则

### 3.1 V3.0 与 V2.0 差异（实测 diff，按事件名对齐）

| Sheet | 变化 | 明细 |
| :--- | :--- | :--- |
| CPJ_Event_Net | **净增 1 事件** | `DemEvent_EV_CANA_SZS_INVALID1`（SZS==0x0 连续 10 次；DTC 0x579609 `DemDTC_C179609_SZS_Fault`；CounterBase 10/1/40；ECG_NET_ACAN；PowerCycle）——其余 120 行仅序号列重排，无实质变化 |
| RCore_Event_d310 | **139 事件去 DTC 映射** | `0x658548 DemDTC_C258548_SafetyLibError` → `N.A`（ModuleMain_Mapped_* 系列事件，同 GWM w11w12「屏蔽 Safetylib DTC mapping」先例） |
| PF_Event | 无变化 | — |
| 04_ECG / 05_Abbr / 06_FiMFID | 无变化 | — |

### 3.2 D107 属性矩阵（R2 原样）

| 属性 | 值 |
| :--- | :--- |
| DID / Name | 0xD107 / SOC软件版本内部使用 |
| $22 / $2E | Yes / No |
| Data Type / Length | ASCII / 8 字节 |
| 会话 | Default: Yes / Programming: No / Extended: Yes |
| 安全 | Locked: Yes / Level3 FBL: No / Level1 OEM: Yes / iMotion: Yes |
| Default Value | `V1.0.0` |
| NVM | No |
| 填充 | 未使用位 0x20，右对齐（`"  V1.0.0"`） |

### 3.3 现状与差距

D107 已有**空壳实现**：handler 直接返回 OK 不填数据，lookup 表长度 32。本次将其落地为 D19A 同型（会话/安全枚举与 D19A 条目一致，无需改权限位）。

---

## 四、 异常与容错

* D107 handler 防御：字符串长度 > 8 时截断（strlen 上限保护，同 F195 写法）
* 139 个去 DTC 映射事件：Dem 侧生成无 DTC 事件属既有模式（GWM 先例），编译期验证

---

## 五、 修改点清单（附录）

| # | 仓库 | 文件 | 改动 |
| :--- | :--- | :--- | :--- |
| 1 | mcu_app_j6 | `cpj_cmc/tools/rx/e2e_dem/` | 新增 V3.0 xlsx，删 V2.0 两 xlsx |
| 2 | mcu_app_j6 | `cpj_cmc/autosar/rx/BswRta/ecu_config/bsw/gen/J6B_Dem_EcucValues.arxml` | 生成 |
| 3 | mcu_app_j6 | `cpj_cmc/autosar/rx/BswRta/integration/src/bsw/Dem/user/Dem_PrjSpecificControl.c` | 生成 |
| 4 | mcu_app_j6 | `cpj_cmc/evm_cfg/var/src/vehicle/rx/_gen/evm_cfg_iSysFidCfg.cpp` | 生成 |
| 5 | mcu_app_j6 | `cpj_cmc/evm_cfg/var/inc/vehicle/rx/evm_cfg/evm_cfg_FidCfg.hpp` + `zx_sys_evm_cfg_fimcfg.hpp` | 生成 |
| 6 | mcu_app_j6 | `cpj_cmc/dia_cfg/var/inc/vehicle/rx/ov_dia/0x22/ov_dia_0x22_read_data_by_identifier_handler.hpp` | `DID_LENGTH_0xD107 32u→8u` |
| 7 | mcu_app_j6 | `cpj_cmc/dia_cfg/var/src/vehicle/rx/0x22/ov_dia_0x22_read_data_by_identifier_handler.cpp` | D107 handler 实现（0x20 右对齐 + `g_DidData_D107_au8`） |
| 8 | mcu_app_j6 | `cpj_cmc/dia_cfg/var/src/vehicle/rx/did_lookup_table/ov_dia_did_lookup_table.cpp` | D107 条目长度 32→8 |
| 9 | version_did | `modules/CMC/RX_C088.json` | 加 `"ZX_DID_D107": "V1.0.0"` |
| 10 | version_did | `templates/version_did.cpp.in` / `version_did.hpp.in` | 加 `g_DidData_D107_au8` 定义/声明 |
| 11 | zos_msg | `Gen_evm_dem_Script/` | 上传 V3.0 xlsx、删旧版本（R4 硬规则 2） |

## 六、 验收标准

- R1/147：导入 T1JFL3…即 RX E2E V3.0 版本（详见 CMCRXJ6B-146），内容包含 Event 定义、Event 和 DTC 的 mapping、ECG 等
- R2/818：$22 读 D107 返回 8 字节 `"  V1.0.0"`（0x20 右对齐）；默认会话可读、扩展会话可读、编程会话不可读；Locked/Level1/iMotion 可读、Level3 FBL 不可读
- 编译零警告通过；SIL 验证（DiagnosticTester $22 用例）

## 七、 交付记录（2026-10-30）

- 生成：10.0.13.10 上 `Dem_AutoGen.py --config rx` 主入口全量重生成（ISOLAR headless ~250s + gen_map_yaml 三个 map 表）
- 同步范围（13.10 → 12.42，18 文件 + 3 map yaml）：4 Dem arxml + 9 Dem_Cfg_* + 2 FiM_PC + 3 evm_cfg；**相比 V2.0 先例新增 FiM**（`FIM_CFG_NUMBEROFDEMEVENTIDS` 897→604 对齐 Dem 事件数，V2.0 遗留不一致顺带修正）；**新增 3 个 map yaml 合入**（用户指示，先例不同步 map）
- **PduR_Gateway_TpDcmTx.c 排除同步**：ISOLAR 重生成会覆盖回退 F4CMC-41 的功能寻址修复，已补 `RXPATCH P1` 标记（防下次生成丢失，重放规则见 autosar-code-generation.md §1）
- 非 Dem 模块重生成 diff（Com/CanSM/BswM/StbM/WdgM 等 ~27 文件）未同步，与本单无关
- 验证：用户上板验证通过；三仓 commit（mcu c7f221e34 / version_did 5e534d7 / zos_msg 5adc7e1f），PR 顺序按 pr-merge.md §0（zos/version_did 先行）
