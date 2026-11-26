# J02 Change Diagnostic Function V2 需求与设计说明文档

| 项 | 内容 |
| --- | --- |
| 工单 | [C097FAWVW-38](https://jira.imotion.ai:7070/browse/C097FAWVW-38)（implemented 关联 7 张需求单：REQ-451/729/725/726/727/728/438） |
| 项目/变体 | FAWVW C097 / J02 |
| 日期 | 2026-11-26 |
| 分支 | develop + release/FAWVW/J02_C097/DV（mcu_app_j6_v2） |
| fixVersion | I210v1 |
| 状态 | 设计中 |

## 一、概述

### 1.1 功能背景与目标

J02 诊断功能 v2 批量改动（延续 [C097FAWVW-24](2026-11-12-C097FAWVW-24-j02-change-did-function-design.md) v1，问卷 V1.4 基础）：27 解锁延时 10s→10min、删除 0249 DID、新增 4635 E2EConfig 与 4 个 mode 类 DID（019C/2B37/2B38/2B39）、F193 硬件版本号由编译期常量改为动态获取。同步修改诊断问卷（develop 与 DV 两份副本）。

### 1.2 适用范围

- 仓库：`mcu_app_j6_v2`（问卷/DID handler/Dcm 生成配置）、`version_did`（4635 默认值）
- 不含：4635 E2EConfig 值的实际 E2E 通信校验开关接线（仅落 DID 接口，见开放问题 1）；REQ-451 的 Develop 等级失败计数补齐（用户确认本次只改延时值，见 ADR-2）

### 1.3 术语

| 术语 | 含义 |
| --- | --- |
| Level1 / Level2 | REQ 单口径：Level1=App 解锁（27 03/04，10 01/10 03 会话计时）；Level2=Boot 解锁（27 11/12，10 02 会话计时） |
| RAM 影子变量 | 4635 的运行时存储：初始化自 version did 编译期常量，2E 写 RAM，掉电恢复默认（NVM 不存储） |
| HW_Version 模块 | `components/bsw/Services/ObcServ/HW_Version`，HSI ADC 分压读硬件版本，`hw_read_version_enm()` 返回 HW_VERSION_1..N |

### 1.4 参考文档

- 需求单：REQ-451（延时）、REQ-729（4635）、REQ-725/726/727/728（mode DID）、REQ-438（F193 动态）
- 前序：C097FAWVW-24 v1 设计（问卷 V1.4、生成链、ADR-3 BSW 全量再生成回退策略、ADR-7 0249 桩）；C097FAWVW-25（DV 分支问卷分叉先例）

### 1.5 约束与假设

- Dcm 代码由问卷经 Dcm_AutoGen 生成，人工改动一律带 `<J02PATCH P{n}>` 标记防生成覆盖
- DV 与 develop 问卷有意分叉（C097FAWVW-25：DV 副本 0x11 放行行），本次两份都改且保留 DV 差异行
- ISOLAR BSW 全量再生成的回退策略沿用 v1 ADR-3（`git checkout HEAD` 恢复手工修正，仅保留本单驱动的生成物）

## 二、架构与生成链

沿用 v1 生成链（[v1 设计 §二](2026-11-12-C097FAWVW-24-j02-change-did-function-design.md)）：

```
UDS_Diagnostic_Questionnaire_J02.xlsx ──Dcm_AutoGen(--config j02)──▶ lookup table / 0x22/0x2E handler / Dcm EcucValues arxml
version_did: modules/FAWVW/J02_C097.json ──模板──▶ g_DidData_xxxx_au8
HW_Version 模块（HSI）──hw_read_version_enm()──▶ F193 0x22 handler 动态映射
```

- DcmDspSecurity 表（问卷 sheet）驱动 Dcm 安全访问配置（Dcm_Lcfg_DspUds），延时值改动经 Dcm_AutoGen 重生成落地
- 并发上下文：0x22/0x2E 均在 Dcm 任务上下文同步处理，mode 全局变量与 4635 影子变量仅在 Dcm 上下文读写，无跨上下文竞争

## 三、核心配置变更

### 3.1 问卷修改清单（V1.4 → V1.5，develop + DV 两份副本）

**DcmDspSecurity sheet（REQ-451，延时改 10min）：**

| 列 | 现值 → 新值 | 适用行 |
| --- | --- | --- |
| DcmDspSecurityDelayTime | 10 → 600 | Unlocked_Boot / Unlocked_App / Unlocked_Develop 三行 |
| DcmDspSecurityDelayTimeOnBoot | 10 → 600 | 同上 |

NumAttDelay=3、AttemptCounterEnabled、Get/SetAttempCount（Z036/Z037 NVM 持久化）维持现状。

**DID List sheet：**

| 动作 | DID | 行内容要点 |
| --- | --- | --- |
| 删除行 | 0x0249 Programming Hash | 32B VersionDid（v1 ADR-7 `<J02PATCH P2>` 全 0 读桩，整行删除） |
| 改行 | 0xF193 | Data Source: VersionDid → DynamicDid（其余列不变，默认 H01 作回退值） |
| 新增行 | 0x4635 E2EConfig | Unsigned / 2B / Data Source: VersionDid / Default `0x01 0x00`；22 Yes / 2E Yes；Default `22:Yes 2E:No`、Programming `22:No 2E:No`、Extended `22:Yes 2E:Yes`；Locked `22:Yes 2E:No`、Boot(Level2) `22:No 2E:No`、App(Level1) `22:Yes 2E:Yes`、iMotion `22:Yes 2E:Yes`；JIRA=REQ-729 |
| 新增行 | 0x019C Production mode | Hex / 1B / iMotionDid / 默认空（N.A）；22 Yes / 2E No；Default+Extended+Locked+App+iMotion `22:Yes 2E:No`、Programming+Boot(Level2) `22:No 2E:No`；JIRA=REQ-725 |
| 新增行 | 0x2B37 Transport mode | 同 019C 矩阵；JIRA=REQ-726 |
| 新增行 | 0x2B38 Showroom mode | 同 019C 矩阵；JIRA=REQ-727 |
| 新增行 | 0x2B39 Dynamometer mode | 同 019C 矩阵；JIRA=REQ-728 |

注：mode 类 DID 的 Boot Unlocked（Level2）列按需求单为 `22:No 2E:No`（Locked 可读而 Level2 不可读，需求单原文如此，原样落表）；0x2B39 需求单 Programming 列写 `22:Yes`（其余三个 mode 为 No），原样落表。

**History sheet**：新增 V1.5 行（2026-11-26，本单改动摘要）。

### 3.2 version_did 仓库修改

`modules/FAWVW/J02_C097.json` 新增 4635 默认值键（`ZX_DID_4635` = 0x01 0x00，E2E 关，pre-VFF 口径）。模板配套按 v1 F1D5 先例评估：若模板不支持非 ASCII 字节值数组，则以 0x22/0x2E handler 内 `<J02PATCH P3>` 直接初始化影子变量（实现阶段二选一，倾向 JSON 键——VFF 切换 bit=0 时只改 JSON 不改代码）。

### 3.3 mcu_app_j6_v2 修改（生成 + 手工）

| 修改点 | 方式 | 内容 |
| --- | --- | --- |
| 问卷入库 | 手工 | develop + DV 两份副本同步 V1.5（DV 保留 0x11 差异行）+ tools 同步副本 |
| Dcm/DID 生成物 | Dcm_AutoGen | lookup table（新 5 DID 行、删 0249 行）、0x22 handler（4635/019C/2B37/2B38/2B39 新增、0249/F193 改写）、Dcm arxml（延时 600 + 新 DID 容器） |
| mode 全局变量 | 手工 `<J02PATCH P3>` | 4 个 `zos::uint8_t` 全局（如 `g_Dia_ProductionMode_u8` 等），默认 0，归属 ov_dia 层 |
| 4635 RAM 影子 | 手工 `<J02PATCH P3>` | `g_Dia_E2EConfig_au8[2]` 初始化 {0x01, 0x00}（或自 version did 常量拷贝），2E 写 RAM |
| 0x22 handler | 生成 + patch | 4635 读影子；019C/2B37/2B38/2B39 读各全局；F193 动态读 `hw_read_version_enm()` 映射 `H%02d` 版本串（H01/H02/...），未用位补 0x20 满 4B；0249 handler 整体删除 |
| 0x2E handler | 生成 | 4635 写影子（长度校验 2B），会话/安全门控由 lookup table 生成列推导 |
| 0249 残留清理 | 手工 | DID_LENGTH_0x0249 宏、lookup 表项等引用随生成核对清除 |

### 3.4 F193 动态获取设计（REQ-438）

- 数据链：`hw_read_version_enm()`（HW_Version 模块，启动时 `HW_VersionCheck()` 采样 HSI ADC 分压）→ `HW_VERSION_n` 枚举 → `"H%02d"`（n=1→H01，n=2→H02 ...）→ 右补 0x20 至 4B
- 回退：`HW_NOKOWN`/`HW_VERSION_EXCEPTION`/越界 → 回退默认 `"H01"`（与问卷 Default Value 一致）
- 硬件版本与供应商版本号对应关系（H01/H02/H03...）按 REQ-438 note 由 HSI 分压档位天然承载，无需额外映射表

## 四、异常处理与容错

- 4635 2E 写长度 ≠ 2B → NRC 0x13（生成 handler 既有路径）
- mode DID 不支持 2E（生成列全 2E:No）→ NRC 0x31
- F193 硬件版本读取异常 → 回退 H01，不返回错误码（诊断读不因版本识别失败而失败）
- REQ-451 延时语义边界（会话切换不重置计时、锁止到期 KeyCtrs 清零、掉电锁止重新开始）由 Dcm 内建 delay 机制 + Z036/Z037 计数持久化 + DelayTimeOnBoot=600 承接，验证阶段逐条确认；发现差距另开问题单（开放问题 2）

## 五、验证方案

1. 编译通过（SSH 12.42，develop 与 DV 两分支分别编译）
2. 刷写（develop 固件）后 DiagnosticTester 用例：
   - 4635：22 读默认 `01 00`；2E 写 `00 00` 回读生效；断电重启恢复 `01 00`
   - 019C/2B37/2B38/2B39：22 读 `00`；Locked/Extended 默认可读、Programming 拒绝（NRC 0x7F/0x31 按生成表）
   - F193：22 读 `48 30 31 20`（"H01"+0x20，现板）
   - 0249：22 读 NRC 0x31（DID 已删）
   - 延时：3 次错误 key 后 27 立即 NRC 0x37（requiredTimeDelayNotExpired）；生成代码确认 `600` 落地（10min 全程等待不作为用例，以配置值 + 立即阻塞为准）
3. 用户台架手动验证（阶段 4 停下等确认）
4. 验收标准：问卷 V1.5 与 7 张需求单逐项一致；两分支编译零错误；上述用例全 PASS

## 附录A：需求追溯矩阵

| 需求单 | 内容 | 设计章节 | 验证 |
| --- | --- | --- | --- |
| REQ-451 | 延时 10min | §3.1 | 五-2 延时用例 |
| REQ-729 | 4635 E2EConfig | §3.1/§3.2/§3.3 | 五-2 4635 用例 |
| REQ-725/726/727/728 | 019C/2B37/2B38/2B39 | §3.1/§3.3 | 五-2 mode 用例 |
| REQ-438 | F193 动态 | §3.4 | 五-2 F193 用例 |
| （无单） | 删 0249 | §3.1/§3.3 | 五-2 0249 用例 |

## 附录B：ADR

- **ADR-1 mode DID 号以需求单为准**：用户消息写 2B50/2B51/2B52/2B53，需求单定义 019C/2B37/2B38/2B39，用户确认按需求单。
- **ADR-2 REQ-451 只改延时值**：现延时 10s/NumAttDelay=3，App/Boot 失败计数已有 Z036/Z037 NVM 持久化；本次仅 DelayTime/DelayTimeOnBoot 10→600（三行）。Develop 等级未使能失败计数——维持现状，不新增 Z 块（用户确认）。
- **ADR-3 4635 默认值放 version did + 2E 写 RAM**：NVM storage=No 但 2E Yes → RAM 影子变量（掉电恢复默认）；默认值进 version_did JSON（VFF 切换 bit=0 时只改 JSON）。E2E 实际校验开关接线不在本单。
- **ADR-4 F193 动态化走 HW_Version 模块**：现成 HSI ADC 分压方案（`hw_read_version_enm()`），不自建读版本逻辑；异常回退 H01。
- **ADR-5 两分支问卷同步**：develop 与 DV 副本都升 V1.5，DV 保留 0x11 放行差异行（C097FAWVW-25 分叉延续）；DV 分支编译验证后承载 cherry-pick。
- **ADR-6 0249 删除含 patch 桩清理**：v1 ADR-7 的 `<J02PATCH P2>` 读桩随行删除，宏与 lookup 引用一并清。

## 附录C：开放问题

1. 4635 的实际消费方（E2E 通信校验开关谁接线）——本单仅 DID 接口，待 E2E 通信需求单明确；影响：VFF 切 bit=0 前需接线方就位。
2. REQ-451 完整语义（KeyCtrs 到期清零、会话切换不重置计时）依赖 Dcm 内建行为，验证阶段逐条确认，有差距另开单。
