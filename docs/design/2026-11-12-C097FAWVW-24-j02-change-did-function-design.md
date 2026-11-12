# J02 Change DID Function 需求与设计说明文档

| 项 | 内容 |
| --- | --- |
| 工单 | [C097FAWVW-24](https://jira.imotion.ai:7070/browse/C097FAWVW-24)（关联 32 条 C097FAWVWREQ 需求单，implemented） |
| 项目/变体 | FAWVW C097 / J02 |
| 日期 | 2026-11-12 |
| 分支 | develop（mcu_app_j6_v2 / version_did） |
| fixVersion | I210v1 |
| 状态 | 设计评审中 |

## 一、概述

### 1.1 功能背景与目标

客户（一汽 FAWVW）2026-11-04~11 在 JIRA 需求树新下发 32 条 DID 需求（04_UDS Data_Customer/DID folder 38683 + 05_UDS Data_iMotion Platform folder 35521）。J02 现有 UDS 诊断问卷（V1.3，2026-09）与该需求树存在 2 处缺失、9 处属性差异。本需求将问卷、NVM 存储配置、version_did 值与 mcu_app_j6_v2 DID 实现全部对齐到需求树。

### 1.2 适用范围

- 仓库：`mcu_app_j6_v2`（问卷/NVM 配置/生成代码）、`version_did`（DID 值）
- 不含：C097FAWVWREQ-401 ImotionUnlocked（27 服务 0x61/0x62 解锁算法，AES-128-CMAC）——属安全访问范畴，J02 已有 0x27 AES128-CBC 实现，是否切换算法另行确认（见开放问题）
- 不含：需求树中 Configuration DID（38690）/ EOL DID（38691）两个空文件夹（当前无需求单）

### 1.3 术语

| 术语 | 含义 |
| --- | --- |
| Data Source | 问卷 DID List 列，取值 VersionDid（编译期常量，version_did 生成）/ NvmDid（NVM 块读写）/ iMotionDid（内部信号）/ DynamicDid（运行时计算） |
| 左对齐填充 | REQ-450：VersionDID ASCII 数据右侧补 0x20 至满长度 |
| 工厂后门 | REQ-447：F1A3 客户侧只读，仅 iMotion 解锁（知行工厂）允许 2E 写 |

### 1.4 参考文档

- 需求树：C097FAWVWREQ folder 38683（VersionDID 18 / DynamicData 2 / OTA 4）、folder 35521（iMotion Platform 8）、REQ-450 左对齐规则、REQ-401 ImotionUnlocked
- 前序：IDC310GAC-7008（J02 UDS 服务与问卷 V1.0~V1.3 基础，PR mcu_app_j6_v2#57 已合并）
- 先例：RX change did function（F4CMC-59，版本 DID 填充方向处理）

### 1.5 约束与假设

- Dcm/NvM 代码由问卷/NVM 表经 Dcm_AutoGen / Nvm_AutoGen 生成，人工不直接改生成区
- version_did 的 IDC310GAC-7008 遗留未提交改动（J02_C097.json DID 值）不单独提交，并入本单
- version_did JSON 值格式：左对齐、右补空格（0x20）至标称长度（如 F187 `"JP2980653  "` 11B）

## 二、架构设计与生成链

```
UDS_Diagnostic_Questionnaire_J02.xlsx ──Dcm_AutoGen(--config j02)──▶ dia_cfg（lookup table / 0x22 / 0x2E handler、Dcm EcucValues arxml）
        │                                    │
        │                                    ├─ VersionDid ──▶ version_did JSON 回填 + g_DidData_Fxxx 数组
        │                                    └─ NvmDid ──▶ NVM_BLOCK_MAP(DID→Pdm_Z0xx) + idiaIdBasedReadWrite
J02_NVM_List.xlsx ──Nvm_AutoGen(--config j02)──▶ pdm_cfg（pdm_cfg.h/.cpp、NvM EcucValues arxml）
modules/FAWVW/J02_C097.json ──CMake parse_json.py + configure_file──▶ version_did.cpp/hpp（g_DidData_Fxxx_au8）
```

- 问卷权威存放位置（本单起）：`mcu_app_j6_v2/cpj_fawvw/veh_j02/dia_cfg/doc/UDS_Diagnostic_Questionnaire_J02.xlsx`；`tools/autosar_gen/Dcm_AutoGen/UDS_Diagnostic_Questionnaire/J02/` 保留同步副本供自动发现，生成时用 `--excel` 指向 dia_cfg/doc 副本
- Dcm_AutoGen 入口：`python tools/autosar_gen/Dcm_AutoGen/Dcm_AutoGen.py --repo <mcu_app_j6_v2> --config j02 --excel <问卷路径>`
- Nvm_AutoGen 入口：`python tools/autosar_gen/Nvm_AutoGen/Nvm_AutoGen.py --repo <mcu_app_j6_v2> --config j02`
- 并发上下文：0x22/0x2E 均在 Dcm 任务上下文同步处理；NVM 读写走 idiaIdBasedReadWrite + pending 轮询，本单不改变该机制

## 三、核心配置变更

### 3.1 问卷 DID List 修改清单（V1.3 → V1.4）

**新增 2 个 DID：**

| DID | Name | Type | Len | Default | Source | 22/2E | 会话/安全要点 | NVM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1E8 | Anonymization Algorithm Software Version | ASCII | 4 | 1000 | VersionDid | 22 Yes / 2E No | Def+Ext 22:Yes，Prog 22:No；Locked/L1/iM 22:Yes，L2 22:No | No |
| 2A18 | IMotion PCBA SN | ASCII | 12 | 全0x00 | NvmDid | 22 Yes / 2E Yes | 2E 仅 Ext + iM；L1/L2/iM 均 22:Yes | Yes（12B） |

**属性修改 9 个 DID：**

| DID | 修改项 | 现值 → 新值 | 需求单 |
| --- | --- | --- | --- |
| F195 | Default | V0.0.1 → I210v1 | REQ-440 |
| F195 | Programming 会话 | 22:Yes → 22:No | REQ-440 |
| F197 | Programming 会话 | 22:Yes → 22:No | REQ-434 |
| F192 | Programming 会话 | 22:Yes → 22:No | REQ-436 |
| F193 | Programming 会话 | 22:Yes → 22:No | REQ-438 |
| F194 | Programming 会话 | 22:Yes → 22:No | REQ-439 |
| F190 | iMotion Unlocked | 2E:No → 2E:Yes | REQ-446 |
| F1A3 | Support $2E | No → Yes（仅 iM 解锁 2E:Yes） | REQ-447 |
| F1A3 | Data Source | VersionDid → NvmDid（NVM 存储默认 H01） | REQ-447 |
| F18C | Extended 会话 | 2E:Yes → 2E:No（2E 仅 iM 解锁） | REQ-448 |

**验证阶段修正（2026-11-12 实测驱动）**：F1A3/F18C 的 **Extended 会话列由 2E:No 改回 2E:Yes**（见 ADR-6）。生成器 Parse_did_excel.py 只从三个会话列推导 write_sessions，会话列置 2E:No 会让 lookup table 写会话为 NULL，解锁后仍 NRC 0x31；解锁门控由 iMotion 安全列（E_DIA_SECLEVEL_DEVELOPMENT_UNLOCK）承担，与 2A18/F190/2EE2 行模式一致。修改 13.10 生成机问卷 K18/K23 单元格后重生成 lookup table。
| 2EE2 | iMotion Unlocked | 2E:No → 2E:Yes | REQ-449 |
| F1DF | Programming 会话 | 22:No → 22:Yes | REQ-456 |
| F289 | Data Type | Hex → ASCII（Supplier Inner SW Version） | REQ-414 |
| F289 | Programming 会话 | 22:No → 22:Yes | REQ-414 |

注：F190 默认值 17×0x2D 与现问卷 `-----------------` 等价（0x2D = '-'）；F1E9/F1D5/F186/F15A/F15B/0249/F180/F18C 等其余字段比对一致；2A1D FimFid 问卷有而需求树无，保留并标记（开放问题 3）。

### 3.2 NVM 存储（任务 2 评估结论）

需**新增 2 个 NVM 块**（`J02_NVM_List.xlsx` → Pdm_Z013 / Pdm_Z014，iPdm_ReadWriteImmediately，User=DID）：

| Index | Name | Len | Init | DID | 依据 |
| --- | --- | --- | --- | --- | --- |
| 13 | Pdm_Z013_EcuHwVersionNumber | 3 | H01（0x48 0x30 0x31） | 0xF1A3 | REQ-447：NVM storage Yes，默认 H01，工厂后门写入 |
| 14 | Pdm_Z014_PcbaSN | 12 | ALL-00 | 0x2A18 | REQ-413：NVM storage Yes，默认全0x00，下线写入 |

既有块已覆盖：F190→Z007、F18C→Z006、F15A→Z008、2EE2→Z012；F15B 读值由 F15A 派生无需独立块。其余全部 VersionDid=No NVM，无需存储。

### 3.3 version_did 仓库修改（任务 4）

`modules/FAWVW/J02_C097.json`（在 IDC310GAC-7008 未提交改动之上继续）：

- `ZX_DID_F195`: `"V0.0.1"` → `"I210v1"`（左对齐右补 0x20 至 48B 由生成/模板处理）
- 新增 `ZX_DID_F1E8`: `"1000"`
- F1A3 改 NVM 存储后不再走 version_did 常量（保留键清空或删除，随生成核对）

模板配套（version_did 仓库）：

- `templates/version_did.cpp.in`：新增 `g_DidData_F1E8_au8` 数组与 `@ZX_DID_F1E8@` 占位
- `templates/version_did.hpp.in`：新增 extern 声明
- `Dcm_AutoGen/User/gen_did_code.py` VERSION_DID_LANDING（tools 仓库）覆盖 F1E8 landing（`--vd-template` 可重提取）

### 3.4 mcu_app_j6_v2 修改（任务 5，生成 + 手工）

| 修改点 | 方式 | 内容 |
| --- | --- | --- |
| 问卷入库 | 手工 | `dia_cfg/doc/UDS_Diagnostic_Questionnaire_J02.xlsx`（V1.4）+ tools 副本同步 |
| NVM 表 | 手工 | `pdm_cfg/Pdm_Script/J02_NVM_List.xlsx` 加 Z013/Z014 + History V1.9 |
| pdm_cfg 生成物 | Nvm_AutoGen | pdm_cfg.h/.cpp、NvM EcucValues arxml |
| dia_cfg 生成物 | Dcm_AutoGen | lookup table、0x22/0x2E handler（F1E8/F1A3/2A18 新增，F18C/2EE2 写 handler 由骨架转实作）、Dcm arxml |
| NVM_BLOCK_MAP | tools 手工 | gen_did_code.py 增加 F1A3→Z013、2A18→Z014 映射 |
| 编译 | SSH | 按 build.md 流程编译 mcu_app_j6_v2（J6 `-x parking_droid_app` 类参数按权威源核对） |

2E 写安全门控由 lookup table 会话/安全列生成：F190/F1A3/2EE2/2A18 的 iMotion Unlocked 2E:Yes、F18C 的 Ext 2E:No 修改均落入生成表，无手写门控代码。2EE2 的 2E 权限（Level1+iMotion）推导出 `E_DIA_SECLEVEL_NORMAL_DEVELOPMENT_UNLOCK` 组合，为 lookup table hpp 安全枚举新增该位组合（枚举区在 AUTO-GENERATED 替换区之外，重生成保留），gen_did_code.py VALID_SEC 同步。

## 四、异常处理与容错

- 2E 写 NVM 沿用 `gType_ov_dia_DID_WriteHandler`（idiaIdBasedReadWrite + pending 轮询），写失败返回 NRC 既有路径
- F1A3 客户侧（Locked/L1/L2）2E 一律拒绝（NRC 0x31/0x33 按生成表），仅 iMotion 解锁放行——工厂后门语义
- 长度不匹配骨架（如历史 F18C 骨架）在重新生成后必须消除，编译期由 pdm_cfg.h 宏校验兜底

## 五、验证方案

1. 编译通过（SSH，develop）
2. 刷写后 DiagnosticTester 用例：新增 F1E8/2A18 读、F195 值、F190/F1A3/2EE2 在 iMotion 解锁下 2E 写、F18C Ext 2E 拒绝、F197/F192~F195 Prog 会话 22 拒绝（NRC 0x7F）
3. 用户台架手动验证（阶段 4 停下等确认）
4. 验收标准：问卷 V1.4 与需求树 32 条逐项一致（比对脚本复跑零差异）；NVM 表评审通过；生成代码编译零错误

## 附录A：需求追溯矩阵（摘要）

| 需求单 | DID | 动作 |
| --- | --- | --- |
| REQ-429~443,446~449,452~456,410~416 | 见 §3.1 | 新增/修改/确认一致 |
| REQ-450 | 全部 VersionDID | 左对齐右补 0x20（JSON 现值已符合，生成层保持） |
| REQ-401 | —（27 算法） | 本单不含，开放问题 1 |
| REQ-445,454 | F186/F1D5 | 已一致，无改动 |

完整 32 条逐项比对记录：`.tmp/did_diff_report2.txt`（结论已收录 §3.1，临时文件不进 git）

## 附录B：ADR

- **ADR-1 问卷权威位置迁移**：问卷从 tools 仓库自动发现路径迁至 mcu_app_j6_v2 `dia_cfg/doc/`（与诊断配置同仓库演进），tools 留同步副本 + `--excel` 显式指向。代价：两处副本需同步；收益：问卷随项目代码版本化、评审入口统一。
- **ADR-2 F1A3 走 NvmDid 而非 VersionDid**：需求明确 NVM storage + 工厂后门写入，编译期常量无法满足写入语义。
- **ADR-3 BSW 全量再生成的回退策略**：Nvm/Dcm_AutoGen 触发的 ISOLAR BSW 生成会重写约 70 个 J02 BSW 文件，其中 57 个为手工改动被覆盖（Com DLC 处理、CanNm NetM 门控、ComM 保活、EcuM/WdgIf `//zjz` 基线修正、StbM RTC 等，参照 IDC310HONDA-4 先例 6f9448c9b）或生成器「整文件追加」式损坏产物（CanTSyn 4 个、rba_MemLib 3 个），一律 `git checkout HEAD` 恢复；仅保留本单配置真正驱动的 15 个（NvM_Cfg、Fee 块映射、NvM/NvM BSWMD/_fwd arxml、CodeGen_Version.h）。J02 尚无 restore_handedit 白名单（GWM 各变体已有），后续可参照补建。
- **ADR-4 NvM_Cfg.h 常量限定开关的手工修正**：重生成将 `NVM_RB_EXPLICIT_SYNC_READ_WITH_CONST` 回退为 STD_OFF，而 Dem 事件存储回调签名为 `(const void*)`，HEAD 的 STD_ON 为配合该签名的手工修正（无 patch 标记）——本单恢复 STD_ON 并在两台生成/编译机同步。该开关属「无标记手工修正被生成覆盖」家族，是 J02 补建 restore_handedit 白名单时应收录的第一批条目。
- **ADR-5 依赖仓库滞后导致的两类编译失败（存量问题，非本单引入）**：本机 hobot_j6b_v1_0_0_mcu 检出版本落后 origin/develop 近两个月（2e32fd7 @09-24 vs 677be05），引发：① scons yaml 缺 T1 include 路径（`os/gcc_gen/Trace_*.c` 找不到 `T1_RTAExt.h`）——上游 develop 已含修复（同款三条路径：`cpj_fawvw/veh_j02/t1_cfg/gen`、`tools/T1/src`、`tools/T1/interface`）；② C097FAWVW-6/15 的 buffer log/HSI 对齐依赖 `Service/Log/Common/inc/Log_AcoreBuffer.h` 等新文件缺失。处理：hobot 仓库 fast-forward 至 origin/develop（677be05），本地临时 yaml 改动丢弃。教训：J02 全量 clean 编译前必须先同步依赖仓库（workspace-setup §4），否则会误判为本次改动引入的问题。
- **ADR-6 F1A3/F18C 扩展会话 2E 放开（问卷会话列语义修正）**：设计期按 REQ-447/448 将 F18C Ext 列写为 2E:No（意为"仅 iM 解锁可写"），实测 2E 写 NRC 0x31——生成器的会话列语义是**会话准入**（write_sessions 直接来自三列），安全列才是**解锁门控**；两列语义不同，不能借会话列表达安全约束。修正：F1A3/F18C Ext 会话列恢复 2E:Yes，iMotion 安全列保持 DEVELOPMENT_UNLOCK，最终行为与需求一致（未解锁 NRC 0x33、解锁后可写）。教训：问卷会话列只表达"该会话是否支持该服务"，安全约束一律放安全列。
- **ADR-7 三个遗留 TODO 读桩的默认值落定**：0249（Programming Hash 32B）、F1D5（FDS_project_information 5B）、F1DF（ECU Programming Information 1B）为生成器历史遗留桩（version_did 模板无对应数组 / DynamicDid 需手动实现），读回 NRC 0x22。按用户给定默认值以 `<J02PATCH P2>` 实现：0249 全 0、F1D5 = 00 00 00 00 60（与问卷 c7 一致）、F1DF = 0x40。用户确认不单独刷板验证，随下次编译/刷写生效。

## 附录C：开放问题

1. ~~REQ-401 ImotionUnlocked 算法（AES-128-CMAC vs 现 AES128-CBC）~~：**已确认（2026-11-12 用户评审）不在本单范围**
2. ~~F289 取值源~~：**已确认（2026-11-12 用户评审）维持编译期构建时间宏 `DIA_ZX_VERSION_BUILD_DATE_UTC8`**
3. ~~2A1D FimFid~~：**已确认（2026-11-12 用户评审）保留**，评审时向客户/需求创建人确认
4. ~~F1D5/0249 当前 version_did JSON 无对应键且取值非 ASCII 字符串（F1D5 hex 字节、0249 N.A），无法套用字符串模板——保留现有骨架实现，本单不改；F1E9 已补 JSON 键 + 模板落点（值 "1000"）~~：**已按用户给定默认值在 0x22 读 handler 以 `<J02PATCH P2>` 落定**（0249 全 0、F1D5 = 00 00 00 00 60、F1DF = 0x40，见 ADR-7）

## 附录D：验证记录（2026-11-12，DiagnosticTester 实测）

| 用例 | 结果 | 日志 |
| --- | --- | --- |
| did_verify（24 步：门控拒绝 + 解锁 2E 写回读恢复 + Prog 会话 22 拒绝） | 24/24 PASS | `testcase/j02/did_verify/logs/did_verify/20261112_173644` |
| did_readall（31 个 DID 全量读默认值） | 28/31 PASS（3 失败为遗留 TODO 桩，ADR-7 已修码） | `testcase/j02/did_readall/logs/did_readall/20261112_173842` |
| security_access（App 03/04、Develop 61/62 扩展会话；Boot 11/12 编程会话） | 5/5 PASS | `testcase/j02/security_access/logs/security_access/20261112_174846` |
| 用户台架手动验证 | 通过 | — |

工具侧配套：security.py 新增 `j02_oem_cbc` 算法（OEM 规范 v2.0：`AES128(Seed12B‖Mask4B ⊕ IV)` 按固定下标提取 12B，对照 `ov_dia_0x27_security_access.cpp` secCalculateKey）；configs/j02/j02_cx.yaml 配置 app/boot 两等级（Mask 暂用规范 4.2 示例值，与 ECU 侧同源 TODO）。Boot 27 11 在扩展会话拒 NRC 0x7E，属 DCM 会话门控预期。
