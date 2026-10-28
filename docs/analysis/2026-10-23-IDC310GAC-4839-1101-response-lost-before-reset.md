# 🐞 IDC310GAC-4839 0x11 ECUReset 1101 最终正响应 5101 在复位前丢失 问题分析报告

| 文档基础属性 | 内容说明 | 分析与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **问题单号** | IDC310GAC-4839（机理①，修复 Story：IDC310GAC-8028） | **分析结论** | 🟢 是问题（转正式开发） |
| **问题主题** | 压测中 1101 只回 7F1178 后 ECU 直接复位，5101 未发出 | **缺陷类型** | 功能（时序竞态） |
| **分析人 / 日期** | @Hua.Yao / `2026-10-23` | **严重等级** | S3 一般（诊断 0x11 服务偶发丢最终正响应，1/1001） |
| **项目 / 变体** | GAC J6 全变体（develop 8 变体：ay7/s52/s52-e046/t09/t51/t68/t75/t88） | **优先级** | P2 高 |
| **发现阶段** | 台架集成测试（诊断压测） | **分析状态** | 🔵 已修复 |
| **根因分类** | 编码（跨任务竞态防御不足） | **关联输出** | 🔗 [IDC310GAC-4839](https://jira.imotion.ai:7070/browse/IDC310GAC-4839) ｜ 📋 Obsidian 笔记《GAC fix 1101 positive response lost before reset》 |

> **📝 变更记录**
> * `2026-10-23`｜@Hua.Yao｜V1.0｜初版：现象固定、根因分析、修复验证（V2 工作区）

---

## 一、 缺陷概述 (Defect Summary)

### 1.1 问题描述

> 0x11 ECUReset（hardReset 1101）pending 过程中，R 核 `l_ECUReset_cyclic` 完成 NvM WriteAll 后仅等待 10 个 10ms 周期（~100ms）就执行 `hal_mcu_reset()`，而最终正响应 5101 由另一 10ms 任务（DCM pending 轮询）在状态 OK 后的下个周期才发出——负载抖动下复位抢在 5101 发送之前执行，最终正响应丢失，tester 侧表现为 1101 只收到 7F1178 后 ECU 直接复位。

### 1.2 现象与复现（原样摘录）

来源：IDC310GAC-4839 Problem Description（customfield_12007）+ 报告人 2026-09-04 评论。

> *Precondition:* 正常上电
>
> 1、版本：https://ci.imotion.ai/package/8513/detail
>
> 2、全部外设
>
> *Reproduce Steps:*
>
> 1、诊断压测
>
> *Expected result:*
>
> 1、无异常
>
> *Actual result:*
>
> 1、压测到27服务时偶现诊断不回复
>
> {*}Probability of reproduce:{*}1-300

> 报告人评论（换包 13046 复测）：压测中仍然会有不回复现象，200 次出现 2 次，一次是 1101 不回复，一次是 1003 不回复，log 见 20260904.7z。

**期望行为**：1101 → NRC78（pending）→ 最终 5101 正响应 → ECU 复位（响应先于复位）。
**实际行为**（TC5 失败周期，1/1001）：`1101 → 7F1178(23ms) → 7F1178(1.04s) → 5101 始终未发出 → ECU 复位执行`；应用报文复位前连续、重启间隙 0.51s（与正常 1101 周期一致）、恢复后稳定——ECU 未挂，是 DCM pending 过程中复位抢跑了 5101 发送。

### 1.3 环境矩阵

| 项 | 版本/值 | 来源 |
| :--- | :--- | :--- |
| 固件版本 / commit | 测试包 13046（2026-09-03，含 7306）；分析基线 mcu_app_j6@develop@f2dca8b81 | 问题单 / V2 工作区 |
| 硬件版本 / 板卡 | J6B MCU EVM 两盒_plus（台架） | 分析复现环境 |
| 测试环境 | 台架，程控电源 KA3005P（COM44），CX-USBCANFD（FD 500k/2M） | 本次分析 |
| 相关工具/诊断仪 | DiagnosticTester（自制压测工具，testcase 循环 1003→1101） | 本次分析 |
| 复现变体 | 报告环境 AY7 D066 台架（SystemTester_GAC_AY7）；本次验证用 T51（develop 同源生成代码） | 问题单 / 分析 |

### 1.4 分析输入与基线

| 输入 | 来源 | 说明 |
| :--- | :--- | :--- |
| 复现步骤/现象 | 问题单 customfield_12007 | 原样摘录于 §1.2 |
| 附件（日志/报文） | 问题单附件 20260904.7z | TC5/TC9/TC10 BLF 解析留存 `.tmp/20260904/` |
| 评论补充 | 报告人 2026-09-04 | 13046 复测仍复现（1101 与 1003 各一次） |
| 分析基线 | V2 工作区 `02_Workspace_J6_V2/src/mcu_app_j6` | develop@f2dca8b81（可编译通过），feature 分支 `feature/IDC310GAC-8028-1101-response-lost-before-reset` |

---

## 二、 复现性与数据回放 (Reproducibility & Replay)

### 2.1 可复现性

| 复现率 | 条件 | 样本 |
| :--- | :--- | :--- |
| 概率性 ~1/1001 | 诊断压测、DCM 侧负载抖动 >63ms | 问题单 TC5（20260904.7z，1001 循环 1 次） |
| 台架未复现 | 安静台架（无负载注入）压测 | 本次 run1/run2 各 1000 循环，机理① 0 次 |

* **首次/末次出现**：首次 2026-08 版本 8513；13046（含 7306）复测仍存在；与 0x27 修复链（7306/6205/7888）无关（13046 早于 7888）。
* 台架无法注入 DCM 侧负载抖动，机理①按 case (b) 降级：以问题单 TC5 BLF 为改前证据 + 余量实测佐证（见 §2.2、§6）。

### 2.2 现象固定与回放

* **问题单 TC5 BLF（改前证据）**：`1003→5003` 正常(20ms)；`1101→7F1178(23ms)→7F1178(1.04s)→5101 未发出→复位`；应用报文重启间隙 0.51s 与正常复位一致。
* **余量实测（本次分析，T51 台架 44 个正常循环）**：5101 发出 → 复位执行的间隔 **63-114ms**（`RESET_DEBOUNCE_MAX_BEFORE_RESET=10` → ~100ms 理论值）。任何 DCM 侧 >63ms 的调度抖动即让复位获胜——这就是 1/1001 偶现的窗口。

---

## 三、 根因分析 (Root Cause Analysis)

### 3.1 知识召回（看代码之前先做）

| 检索源 | 关键词 | 结果 |
| :--- | :--- | :--- |
| `docs/analysis/` 历史个案 | 4839/1101/诊断不回复 | 命中：`2026-10-21-IDC310GAC-3990-diagnostic-first-frame-response-over-50ms.md`（同压测家族 TC10 机理，7888 已修复，非本机理）；IDC310GAC-5759（1101 后 ECU 整机离线，非软件缺陷，已转单） |
| `docs/design/` 设计方案 | ecureset/dcm | 无命中 |
| Obsidian Work Database 笔记 | 4839/1101 | 命中：《GAC dcm response NRC7F and fix dcm bug》7306/6205 修复链台账（与本机理无关，佐证排除链） |
| JIRA 历史单 | 1101 reset delay | 命中：IDC310-7101（fx12 modify 1101 reset delay，已解决）——对应代码中 B06_5/FX12FL/T1MA/B81VS 的 100 周期先例分支 |

### 3.2 排查过程（假设-验证-排除链）

| # | 假设 | 验证手段 | 结果 |
| :--- | :--- | :--- | :--- |
| 1 | ECU 整机挂死/异常复位 | TC5 BLF 应用报文分析 | 排除——复位前应用报文连续、重启间隙 0.51s 与正常 1101 一致、恢复后稳定 |
| 2 | 与 0x27 修复链（7306/6205）相关 | 版本时间线比对 | 排除——13046 已含 7306 仍复现，且现象在 0x11 服务 |
| 3 | 7888 首帧 P2max 超时同款 | BLF 逐帧对照 | 排除——7888 是多帧首帧 51.5ms 超 P2max（TC10）；本现象是单帧 5101 整体未发出（TC5） |
| 4 | 复位执行抢在 5101 发送之前（响应/复位竞态） | 代码走读 + 台架余量实测（63-114ms） | **命中**——见 §3.4 |
| 5 | （台架复现中发现的新机理④）NvM WriteAll 卡死导致诊断永久无响应 | run1 BLF：7F1178 1Hz 持续 4min+ 无复位，应用报文连续 | 命中但**不在本单范围**——IDC310GAC-7775 已修复（`E_WRITE_RETRIGGER_ONGOING` 分支每周期覆盖 step/清计数使 180s 超时失效），本 PR 不携带该修复 |

### 3.3 5 Whys 深挖

| 层级 | 提问 | 回答 |
| :--- | :--- | :--- |
| Why 1 | 为什么 5101 丢失？ | 复位在 5101 发出前执行了（余量仅 63-114ms，抖动即翻转） |
| Why 2 | 为什么余量这么小？ | `RESET_DEBOUNCE_MAX_BEFORE_RESET` 对 GAC 变体=10 周期（~100ms），而 5101 由另一 10ms 任务在状态 OK 后下个周期才发 |
| Why 3 | 为什么 GAC 只配 10 周期？ | 该防抖量当初只按 IPC 场景（B06_5/FX12FL/T1MA/B81VS）识别为需要 100 周期，GAC J6 的 R 核 DCM 自发 5101 场景未纳入 |
| Why 4 | 为什么评审没拦住？ | 跨任务时序余量没有量化验收（无"响应发出→复位执行"最小余量指标） |
| Why 5 | 为什么没有该指标？ | 响应/复位竞态属隐式跨任务依赖，规格未显式定义复位等待与响应发送的先后约束 |

### 3.4 根因与依据

* **根因**：`components/idia/src/0x11/idia_0x11_ecu_reset.cpp:77` 的变体宏分支使 GAC J6 落入 `RESET_DEBOUNCE_MAX_BEFORE_RESET 10u`——`l_ECUReset_cyclic`（`RE_HRTgt_10ms` 10ms 任务，经 `idc_dia_run()`）置状态 OK 后仅 ~100ms 即 `hal_mcu_reset()`，而 DCM pending 轮询（`Core0_OsTask_BSW_10ms` → `Dcm_MainFunction()`）返回 DCM_E_OK 后才发 5101，两任务间无显式先后约束，负载抖动下复位获胜。
* **根因分类**：编码（跨任务竞态防御不足）。
* **代码依据**：`idia_0x11_ecu_reset.cpp:77`（宏分支）；`l_ECUReset_srvcExecute:119-158`（DCM 轮询侧 :134-141 status OK→DCM_E_OK）；`l_ECUReset_cyclic:177-296`（:245-249 NvM 完成→status OK；:263-275 防抖计数；:283 `hal_mcu_reset()`）。
* **责任归属**：本模块（idia 0x11）缺陷。
* **先例**：IDC310-7101（fx12）已为 IPC 场景引入 100 周期分支，注释明言"A-core needs time to consume the 0x51 positive response sent via IPC"——同为响应先于复位的竞态，GAC J6 场景等价。

### 3.5 影响范围评估

* 该宏为公共代码：修复前 `#else` 分支（10u）覆盖**所有未列出的项目/变体**，同款竞态理论上存在于全部 10u 项目；已在修复中统一为 100u（公共问题，不按项目区分）。
* 同单其余机理不在本修复范围：TC10 首帧超时（7888 已修复）；TC9 复位后自发二次重启（ECU 级，待单独分析）；机理④ NvM 卡死（7775 修复中）。

---

## 四、 分析结论与分流 (Conclusion & Triage)

**是问题**：0x11 EcuReset 最终正响应与复位执行存在跨任务竞态，GAC J6（及全部 10u 项目）防抖余量不足（实测 63-114ms），偶发（1/1001）复位抢跑丢失 5101。→ 转正式修复（Story [IDC310GAC-8028](https://jira.imotion.ai:7070/browse/IDC310GAC-8028)，V2 工作区全流程交付）。

**遗留疑点**：无（机理④、TC9 已分流至对应单据）。

---

## 五、 修复方案（仅"是问题"） (Fix Plan)

### 5.1 纠正措施（Corrective Action，治此件）

| # | 修改点 | 文件 | 改动说明 | 风险评估 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 删除变体宏分支，`RESET_DEBOUNCE_MAX_BEFORE_RESET` 全项目无条件 `100u`（10ms 周期 → ~1000ms） | `components/idia/src/0x11/idia_0x11_ecu_reset.cpp:77` | 原 100u 先例项目（B06_5/FX12FL/T1MA/B81VS）行为不变；原 10u 项目（含 GAC J6 8 变体）复位延后 ~900ms | 0x11 复位总时长增加 ~0.9s，仍在 NRC78 pending 语义内（P2max×pending 模式），无功能影响 |

* **验证性修复（V2 工作区，已直接作为正式交付）**：分支 `feature/IDC310GAC-8028-1101-response-lost-before-reset`，单文件 4 行净改动。
* **不携带**：IDC310GAC-7775（NvM 卡死解堵）cherry-pick 不进本 PR——原作者已在 `bugfix/IDC310GAC-7775-pdm-develop` 修复待 merge，本 PR 避免重复携带。

### 5.2 预防措施（Preventive Action，治同类）

| # | 预防动作 | 落点 | 状态 |
| :--- | :--- | :--- | :--- |
| 1 | 跨任务"事件→动作"链路引入最小余量检查（响应发出→复位/关断执行） | 后续设计评审 checklist | 待办 |
| 2 | 本报告沉淀可复用结论（§7.1），同类"复位/关断抢跑响应"现象可直接命中 | docs/analysis | 已完成 |

---

## 六、 验证结果（仅"是问题"） (Verification)

* **验证性修复（V2 工作区，T51 台架）**：
  * 编译：`cpj_gac_t51_d310` preset，通过（2026-10-23 17:04）
  * 刷写：ProgramBoard_j6b（t51_mcu.json，MCU_a/MCU_b，2026-10-23）
  * **A/B 余量对照**：改前 63-114ms（44 循环）→ 改后 **957-1017ms**（smoke 5 循环 + 100 循环回归 99 次复位，全部 ≥957ms）——防抖精确生效，每次复位都在 5101 之后 ≥957ms
  * smoke：10/10 PASS
* **回归确认**：100 循环回归 `repro_1101_loop_t51_100.yaml`：195/200 PASS / 0 FAIL / 5 TIMEOUT——5 个 TIMEOUT 逐条 BLF 核查全部排除机理①：步骤 1-2 撞 run 启动残留 pending 窗口；步骤 4 的 1101 落在前一循环 5101 后的 1s 复位等待窗内（修复引入的窗口，测试时序伪超时）；步骤 41/138 为单次慢 pending（>10s p2star 窗口）下一步即恢复。**机理①特征（5101 发出后复位抢跑）零出现**。
* **机理④台架佐证（7775 修复，非本 PR 范围）**：run2 1000 循环含 7775 cherry-pick 固件，NvM 卡死发作 7 次（约 1/140），全部 180s 超时强制复位自愈，无一超过 10 分钟——7775 修复行为与 commit 描述一致；卡死根因待 7775 侧闭环。
* **正式提交后验证**：PR 合并后版本复验待回填。

---

## 七、 关闭与生命周期 (Closure & Lifecycle)

### 7.1 可复用结论

* 现象关键词：`1101 不回复` / `5101 丢失` / `7F1178 后无正响应` / `复位抢跑`——先查"最终响应发出→复位/关断执行"余量（本篇：`idia_0x11_ecu_reset.cpp` 防抖宏），再查 NvM 卡死（7775 链）。
* 台架安静环境无法复现负载竞态时，用"余量实测"替代复现：量化正常路径的最坏余量，与注入抖动量级比对即可定性。

### 7.2 缺陷生命周期记录

| 状态 | 日期 | 操作人 | 备注 |
| :--- | :--- | :--- | :--- |
| 发现（报告） | 2026-08 | 报告人 | 问题单 4839 创建（压测偶现诊断不回复） |
| 分析开始 | 2026-10-23 | @Hua.Yao | V2 基线建立，BLF 逐帧定性 |
| 根因确认 | 2026-10-23 | @Hua.Yao | 机理①竞态确认（用户确认，聚焦本机理立项 8028） |
| 修复验证通过 | 2026-10-23 | @Hua.Yao | A/B 余量 63-114ms→957-1017ms，100 循环回归机理①零复发 |
| 正式提交 | 2026-10-23 | @Hua.Yao | commit `d01e59326`｜[PR #1682](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/1682)（develop） |
| 关闭 | — | — | 待 PR 合并后回填 |

---

## 附录：原始证据

* 问题单附件 20260904.7z 解析（TC5/TC9/TC10 BLF）：`.tmp/20260904/`（会话临时，结论已沉淀本报告）
* 台架压测产物（DiagnosticTester run 目录，含 result.csv / trace.blf / run.log）：
  * run1 基线（机理④卡死取证）：`tests/harness/dcm_ecureset_1101_lost/testcases/20261023_114503/`
  * run2 含 7775（机理④自愈佐证，1000 循环）：`tests/harness/dcm_ecureset_1101_lost/testcases/20261023_145323/`
  * 修复后 smoke：`tests/harness/dcm_ecureset_1101_lost/testcases/20261023_170315/`
  * 修复后 100 循环回归：`tests/harness/dcm_ecureset_1101_lost/testcases/20261023_171252/`
* 复现/回归用例：`tests/harness/dcm_ecureset_1101_lost/testcases/repro_1101_loop_t51_{smoke,100,1000}.yaml`
