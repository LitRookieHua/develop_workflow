# 🐞 CMC_RX_J6B 诊断五问题（编程会话停发/0x27 seed与计数/Dem 配置）分析报告

| 文档基础属性 | 内容说明 | 分析与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **问题单号** | [F4CMC-99](https://jira.imotion.ai:7070/browse/F4CMC-99) / [100](https://jira.imotion.ai:7070/browse/F4CMC-100) / [101](https://jira.imotion.ai:7070/browse/F4CMC-101) / [102](https://jira.imotion.ai:7070/browse/F4CMC-102) / [103](https://jira.imotion.ai:7070/browse/F4CMC-103)（五单合一修复 Story [F4CMC-105](https://jira.imotion.ai:7070/browse/F4CMC-105)） | **分析结论** | 🟢 五项均为问题（99/102/103 修复，100/101 Dem 配置层用户手动改） |
| **问题主题** | RX (CMC_RX_J6B) 实车暴露五项诊断问题 | **缺陷类型** | 99 配置缺接线（BswM 规则零引用）；102/103 App/配置层缺陷；100/101 DEXT 配置遗留 |
| **分析人 / 日期** | Hua.Yao / Claude / `2026-11-16 ~ 2026-11-17` | **严重等级** | 99/100/101 S3 一般；102/103 S2 较重（安全访问语义不符 ISO 14229） |
| **项目 / 变体** | CMC_RX_J6B 一体机（仓库 `mcu_app_j6` / `cpj_cmc`，M 核诊断） | **优先级** | P2 高（阻塞 Boot 刷写流程与安全访问） |
| **发现阶段** | 实车测试（版本包 ci.imotion.ai/package/21180，reporter Siyuan.Liu，5-5 必现） | **分析状态** | 🔵 99/102/103 已修复验证（PR #2096）；100/101 转其他 Story |
| **根因分类** | 设计/配置（BswM 未接线、Dcm 参数、Dem 遗留）+ 编码（seed 累加） | **关联输出** | 🔗 F4CMC-105 ｜ 📄 [设计文档](../design/2026-11-16-F4CMC-105-cmc-rx-diag-fixes-design.md) ｜ PR [#2096](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/2096) |

> **📝 变更记录**
> * `2026-11-16`｜Hua.Yao / Claude｜V1.0｜初版：五单定性 + 立项 F4CMC-105 + 三处修复方案
> * `2026-11-17`｜Hua.Yao / Claude｜V1.1｜修复验证全绿（102 20/20、103 17/17、99 总线取证 PASS）；补充 GAC 0x27 对比结论

---

## 一、 缺陷概述 (Defect Summary)

### 1.1 问题描述

实车测试（版本包 21180）暴露五项诊断问题，五单 5-5 必现：

| # | 现象 | 期望 |
| :--- | :--- | :--- |
| 99 | `10 02` 进编程会话后应用周期报文不停发 | Boot 模式停发应用报文（CMCRXJ6B-26） |
| 100 | DTC 快照 DID 为 GAC 遗留 0x0500/0x9A5D | 0x15A0/0x0601/0x15A2（CMCRXJ6B-42） |
| 101 | 扩展数据仅 2 记录 | 3 计数器（含 Aged counter，CMCRXJ6B-43） |
| 102 | 连续 `27 01` 请求 seed 每次不同 | 连续请求 seed 相同（CMCRXJ6B-28） |
| 103 | 3 败+延迟到期后错误计数被清零 | NRC37→NRC36→NRC37 序列（CMCRXJ6B-28） |

### 1.2 环境矩阵

| 项 | 版本/值 |
| :--- | :--- |
| 固件基线 | mcu_app_j6@develop（版本包 21180，2026-11-16） |
| 硬件 | CMC_RX_J6B 一体机（实车 / 台架 EVM） |
| 验证环境 | 台架：ProgramBoard 刷写 + DiagnosticTester（CX 712/713）+ CX 总线采样 |
| 分析基线 | V2 工作区 `02_Workspace_J6_V2/src/mcu_app_j6@develop` |

---

## 二、 复现性与数据回放 (Reproducibility & Replay)

* 五单均 5-5 必现（复现步骤见各问题单 customfield_12007 / Obsidian 笔记原样摘录）。
* 99 台架量化取证（修复后四阶段总线采样，`tests/harness/dcm_prog_session_comtx_rx/`）：默认/扩展会话 29 种应用报文 ID 在发 → 编程会话 **全部停发**（仅切换边界 1 帧）→ 回默认会话全部恢复。
* 102/103 复现 testcase 即回归用例（`tools/DiagnosticTester/testcase/rx/sec_access_fix/`），判别步与问题单基线行为一一对应（见 §六）。

---

## 三、 根因分析 (Root Cause Analysis)

### 3.1 知识召回

| 检索源 | 关键词 | 结果 |
| :--- | :--- | :--- |
| `docs/design/` | RX 0x27 / 编程会话 | 无同类命中（本次设计文档为首例） |
| `docs/analysis/` | 0x27 seed / NRC36/37 | 无命中 |
| Obsidian Work Database | RX 诊断 | 命中 [[Fix RX EOL calibration FE01 NRC22 condition logic]]（同批 RX 诊断问题，已闭环） |

### 3.2 排查过程（假设-验证-排除链）

| # | 问题 | 假设 | 验证 | 结果 |
| :--- | :--- | :--- | :--- | :--- |
| 99 | 不停发 | BswM 会话→Com 控制规则未接线 | 走读 `BswM_Cfg_Rule_cast[10]`：仅 10 条 ESH 上下电规则；DCM 会话 MRP 关联规则 0；会话条件/LE/动作列表全定义零引用 | **命中**（GAC 遗留孤儿积木，缺 DEXT 接线） |
| 102 | seed 变化 | `AppSecurityGetSeed()` 累加生成 | 走读 ov_dia_0x27：`g_seedApp_au8[i] += imo_GetRandom_u16()`，每次请求必变 | **命中** |
| 103 | 计数清零 | Dcm 配置延迟到期重置计数 | 走读 `Dcm_Dsp_Security[]`：两级 `ResetAttemptCounter_b = TRUE`；`DcmDspUds_Seca.c:117-125` 延迟到期即清零 | **命中** |
| 100/101 | Dem 配置差异 | DEXT Dem 环境数据未按 RX 需求更新 | `Dem_Cfg_EnvDid.h` 仅 0x0500/0x9A5D；`EnvExtendedDataRec.h` 仅 2 记录 | **命中**（GAC 遗留） |

### 3.3 5 Whys（以 99 为例）

| 层级 | 提问 | 回答 |
| :--- | :--- | :--- |
| Why 1 | 编程会话不停发？ | 会话切换回调未做 Com 控制，BswM 路线也未接线 |
| Why 2 | 为什么 BswM 未接线？ | RX 项目从 GAC 拷贝 BswM 配置，仅 ESH 上下电规则有效，DCM 会话规则零引用 |
| Why 3 | 为什么拷贝后未裁剪/补全？ | 变体移植 checklist 缺「模式管理规则按变体需求核对」项 |
| Why 4 | 为什么测试阶段才暴露？ | 编程会话停发仅 Boot 刷写场景可见，前期无刷写验证 |
| Why 5 | — | 编程会话行为需专项测试用例，已随本次 testcase 落库 |

### 3.4 根因与依据

* **99**：`BswM_Cfg_Rule_cast[10]` 零 DCM 会话规则（配置层缺陷）；修复走集成者回调 `DcmAppl_DcmSesCtrlChangeIndication`（重生成不覆盖，ADR #1）
* **102**：`ov_dia_0x27_security_access.cpp` seed 累加式生成（编码缺陷）
* **103**：`Dcm_Lcfg_DspUds.c` L1(:107)/L3(:135) `ResetAttemptCounter_b = TRUE`（生成代码配置与需求不符）
* **100/101**：Dem DEXT 配置 GAC 遗留，需 DEXT 改配置 + 10.0.13.10 重生成（用户手动改，转其他 Story）
* **GAC 0x27 对比结论**（2026-11-17 用户要求）：GAC 与 RX 算法层不兼容（GAC 4B seed + computeKey，RX 2B + mask 表），算法保持 RX；GAC seed 同为累加式；GAC 特有 Z016 manufactory 检查评估后不启用（用户指示 NVM 不添加）

---

## 四、 分析结论与分流 (Conclusion & Triage)

五项均为问题。99/102/103 由 F4CMC-105 修复（develop feature 分支 → PR）；100/101 为 Dem 配置层（DEXT+重生成），由需求创建人手动改并链接其他 Story 解决，F4CMC-105 仅跟踪。

---

## 五、 修复方案 (Fix Plan)

### 5.1 纠正措施

| # | 修改点 | 文件 | 说明 | 风险 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 编程会话停/恢复 Com TX | `DcmAppl_DcmSesCtrlChangeIndication.c`（集成模板，重写） | new==PROGRAMMING → `Com_IpduGroupStop(CAN0/CAN1_Tx)`；离开 → `Start(..., FALSE)`；RXPATCH P1 | 诊断流量不经 Com 组，零影响 |
| 2 | seed 稳定语义 | `ov_dia_0x27_security_access.cpp` | `s_app/bootSeedValid_b` 标志：一次解锁尝试内 seed 稳定，错 key 后重生成；已解锁（Dcm_GetSecurityLevel L1=0x01/L3=0x09）回 0 | 仅 0x27 路径；key 算法/长度未动，工具兼容 |
| 3 | 计数保持 | `Dcm_Lcfg_DspUds.c` L1/L3 | `ResetAttemptCounter_b` TRUE→FALSE，RXPATCH P1/P2，重生成后按标记重放 | NRC36 发射路径已就绪（NRC0x36MAXDELAYCOUNT=ON） |

### 5.2 预防措施

| # | 预防动作 | 落点 |
| :--- | :--- | :--- |
| 1 | 变体移植时核对 BswM 模式管理规则引用数（条件/LE/AL 零引用 = 孤儿配置） | RX/新变体移植 checklist |
| 2 | 0x27/0x10 类行为回归用例落库（seed_stability / attempt_counter_persist），判别步覆盖基线差异 | `tools/DiagnosticTester/testcase/rx/sec_access_fix/` |

---

## 六、 验证结果 (Verification)

| 用例 | 结果 | 判别步（基线红 → 修复绿） |
| :--- | :--- | :--- |
| `seed_stability`（102） | **20/20 PASS**（logs 20261117_110116） | 连续 3 次 2701 seed 相同（基线每次不同）；错 key 重生成；解锁后 67010000 |
| `attempt_counter_persist`（103） | **17/17 PASS**（logs 20261117_110047） | 35/35/36→37→保活等 11.5s→错 key **NRC36**（基线 NRC35）→2701 **NRC37**（基线正响应） |
| 99 总线四阶段取证 | **PASS**（harness logs probe_*.log） | 编程会话 28/29 应用 ID 停发，10 01 后全部恢复；编程会话内 2711 诊断流正常 |
| 编译 | `CMC/RX_C088/develop` preset 零错误，镜像生成（2026-11-17） | — |

注：基线红未在本板重跑（验证前固件已含修复），以问题单 5-5 必现记录 + 用例判别步与基线行为的明确差异作为改前证据（case b，降级原因：开发流程先修复后刷写）。

---

## 七、 关闭与生命周期 (Closure & Lifecycle)

| 状态 | 日期 | 操作人 | 备注 |
| :--- | :--- | :--- | :--- |
| 发现 | 2026-11-16 | Siyuan.Liu（实车测试） | 五单创建，版本包 21180 |
| 定性确认 | 2026-11-16 | Hua.Yao / 用户 | 五项均为问题；立项 F4CMC-105（五合一） |
| 修复完成 | 2026-11-17 | Hua.Yao / Claude | commit `947b5424f`，PR #2096 |
| 验证通过 | 2026-11-17 | Claude / 用户 | 102/103 用例全绿 + 99 总线取证 |
| 99/102/103 关单 | PR 合并后 | — | 路线一推进 IMPLEMENTED |
| 100/101 | 用户手动改 | 用户 | 链接其他 Story 解决，F4CMC-105 跟踪 |

---

## 附录:原始证据

* 问题单复现步骤：各单 customfield_12007 原样（Obsidian 笔记 Details 章节摘录）
* 用例日志：`tools/DiagnosticTester/testcase/rx/logs/{seed_stability,attempt_counter_persist}/20261117_*/`（run.log + trace.blf + result.csv）
* 99 取证：`tests/harness/dcm_prog_session_comtx_rx/logs/probe_20261117_*.log`
* 需求单：CMCRXJ6B-26/28/42/43
