# 🐞 IDC310GAC-6762/6763 功能寻址组播网关交付长度错配 问题分析报告

| 文档基础属性 | 内容说明 | 分析与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **问题单号** | IDC310GAC-6762 / IDC310GAC-6763 | **分析结论** | 🟢 是问题(转正式开发) |
| **问题主题** | 功能寻址脚本速度连发时 1003 回 NRC13 / 后续请求不响应 | **缺陷类型** | 功能(编码缺陷) |
| **分析人 / 日期** | @Hua.Yao / `2026-10-20` | **严重等级** | S3 一般(诊断功能特定时序下失效) |
| **项目 / 变体** | GAC T68 | **优先级** | Medium(与 JIRA 保持一致) |
| **发现阶段** | 台架集成测试 | **分析状态** | 🔵 已修复(V2 验证性修复通过,待正式提交) |
| **根因分类** | 编码 | **关联输出** | 🔗 JIRA 6762/6763 ｜ 📋 Obsidian 分析笔记 |

> **📝 变更记录**
> * `2026-10-20`｜@Hua.Yao｜V1.0｜初版:根因分析 + T32 实时取证 + V2 修复 A/B 验证

---

## 一、 缺陷概述 (Defect Summary)

### 1.1 问题描述

> 功能寻址(0x7DF)请求走 PduR TP 网关"组播本地 DCM + 转发 CANFR"共享 FIFO 路径,当转发通道忙导致向 DCM 的交付被推迟到下一 FIFO 槽时,`PduR_GF_TP_Dcm_Transmit_Func` 向 `Dcm_StartOfReception` 申报的长度硬编码取 `SduLength_auo[0]`(slot0 的过期长度)而非本次交付槽的真实长度,导致 DCM 按"上一请求的长度"解析"本请求的数据":过长→NRC13(6762),过短→CopyRxData 校验失败→静默丢弃(6763)。

### 1.2 现象与复现(原样摘录)

**IDC310GAC-6762**:

**复现步骤**(原样,customfield_12007):

```
*Precondition:* 正常上电
1、版本：[https://ci.imotion.ai/package/13946/detail]
2、全部外设
*Reproduce Steps:*
1、功能寻址发送10010100
2、功能寻址1003
*Expected result:* 2、5003003200c8
*Actual result:* 2、7f1013
*Probability of reproduce:* 5-5
```

**IDC310GAC-6763**:

**复现步骤**(原样,customfield_12007):

```
*Precondition:* 正常上电
1、版本：https://ci.imotion.ai/package/13946/detail
2、全部外设
*Reproduce Steps:*
1、功能寻址发送较短长度的请求如10、3e、19、1904
2、功能寻址再次发送请求
*Expected result:* 2、正常响应
*Actual result:* 2、不响应
*Probability of reproduce:* 5-5
```

**期望行为**:功能寻址每条请求均按自身长度解析并正常应答(UDS 按请求实际长度校验)。
**实际行为**:连发场景下隔帧出现 NRC13(长度错配过长)或无响应(长度错配过短),单发/慢速场景正常。

### 1.3 环境矩阵

| 项 | 版本/值 | 来源 |
| :--- | :--- | :--- |
| 固件版本 | ci package 13946(v0 基线);分析基线 mcu_app_j6@develop(V2 工作区) | 问题单/分析 |
| 硬件 | T68 板(J6B EVM,与 T09 同板同接线) | 台架 |
| 测试环境 | 台架,程控电源 KA3005P(COM44),CAN 卡 CX-USBCANFD ch0 500K/2M | 台架 |
| 测试工具 | DiagnosticTester(本仓库 tools/)+ TRACE32(R52 Attach) | 分析 |
| 刷写 | ProgramBoard_j6b.py,A核串口 COM65,fastboot UDP 192.168.1.239 | 分析 |

### 1.4 分析输入与基线

| 输入 | 来源 | 说明 |
| :--- | :--- | :--- |
| 复现步骤/现象 | 问题单 customfield_12007 | 原样摘录于 §1.2(description 为空) |
| 附件 | 问题单 attachment | 无 |
| 评论补充 | 问题单 comment | 无额外关键信息 |
| 分析基线 | V2 工作区 `02_Workspace_J6_V2` | mcu_app_j6@develop,T68 产品配置编译通过(build_config 因 glibc 不兼容临时切回可编译 commit,由用户操作) |

---

## 二、 复现性与数据回放 (Reproducibility & Replay)

### 2.1 可复现性

| 复现率 | 条件 | 样本 |
| :--- | :--- | :--- |
| 每次必现(5-5) | 功能寻址、脚本速度(~5ms 间隔)连发且前一请求长度≠后一请求长度、转发通道忙触发 FIFO 推迟交付 | 最小化用例 4/4 步稳定复现 v0 红/v2 绿 |

* **首次/末次出现**:首现于 package 13946;v0 基线(2026-10-20 台架)仍存在,v2 修复后消失。

### 2.2 现象固定与回放

* **6762 最小化复现**(空队列起步,`tools/DiagnosticTester/testcase/t68/func_10_min_6762/`):物理 `1003` 清队列 → 功能 `10010100`(slot0,4B,NRC13 合理)→ **5ms 后功能 `1003`(slot1,2B,转发忙→组播推迟交付→回 `7F1013`)** → 功能 `1001`(slot2,恢复 PASS)。v0 干净跑(20261020_151747):step3 FAIL,其余 PASS——失败点隔离在"slot1 推迟交付"单帧。
* **6763 精确复现**(`func_3e_no_response_stale_length/`):功能 `3E`(1B)后发 `3E0000`(3B)→ **TIMEOUT 静默丢弃**(20261020_142930,step3);后续帧恢复。过期长度 1 < 实际 3 → DCM CopyRxData 长度校验 E_NOT_OK → 无任何应答。
* **共同机制**:两条单是同一缺陷的两个表现——过期长度>实际→NRC13;过期长度<实际→静默丢。"隔帧失败"来自 4 槽 FIFO 实例轮转(PDUR_MAX_QUEUEDEPTH=4)。

---

## 三、 根因分析 (Root Cause Analysis)

### 3.1 知识召回(看代码之前先做)

| 检索源 | 关键词 | 结果 |
| :--- | :--- | :--- |
| Obsidian Work Database | Dcm not response / PduR | **命中**:`Rx fix dcm not response problem.md`(F4CMC-41,同款缺陷已修先例,v2 写法来源) |
| `docs/analysis/` | PduR/NRC13/不响应 | 无命中(有 7100 NRC37 延迟恢复,不同缺陷) |
| `docs/design/` | PduR | 无命中 |

### 3.2 排查过程(假设-验证-排除链)

| # | 假设 | 验证手段 | 结果 |
| :--- | :--- | :--- | :--- |
| 1 | DCM 请求长度校验逻辑误判 | 走读 Dcm 侧解析 | 排除——DCM 按收到的 SduLength 正确解析,错在传入长度 |
| 2 | PduR 两条交付路径的 readerPduInfo 数据/长度错配 | 走读 `PduR_Gateway_TpRx.c:519-527/637-645`(立即路径)与 `PduR_Gateway_TpTxConf.c:183-300`(推迟路径) | 排除——两条路径各自自洽(readPtr 与 SduLength_auo[实例号] 配套) |
| 3 | SoR(StartOfReception)长度取值错误 | `PduR_Gateway_TpDcmTx.c:71` 走读 + T32 断点实时取证 | **命中——见 §3.4** |
| 4 | (反证试验)推迟路径强制用 Rx 实例长度 | v3 试验补丁刷板 | 排除且反证——Tx 槽数据指针配 Rx 实例长度→数据/长度错配→NRC 0x21(7FFF21,20261020_145444),证明 caller info 才是正确长度源,v3 已还原 |
| 5 | 5ms 泛洪全帧失败? | 6 步 5ms 间隔用例 vs 最小化 4 步用例对照 | 区分——全帧失败是 4 槽 FIFO 过载(SWS_PduR_00807 设计容量,非本缺陷);本缺陷单帧即现(最小化用例) |

### 3.3 5 Whys 深挖

| 层级 | 提问 | 回答 |
| :--- | :--- | :--- |
| Why 1 | 为什么功能寻址连发时隔帧 NRC13/不响应? | 推迟交付帧向 DCM 申报的 SoR 长度是 slot0 的过期长度,与本次数据不符 |
| Why 2 | 为什么长度取错? | `PduR_Gateway_TpDcmTx.c:71` 硬编码 `SduLength_auo[0]`,未跟随调用者 info 或本次 FIFO 实例 |
| Why 3 | 为什么代码如此? | 该函数早期仅支持单实例立即交付(下标 0 恒对);引入组播 FIFO 多实例(PDUR_MULTICAST_FROM_TP)后未同步适配 |
| Why 4 | 为什么评审没拦住? | F4CMC-41 已在先例项目修过同款,但修复未同步回基础库/全部项目,同源代码在新项目复现(见 §3.5) |
| Why 5 | 为什么先例修复未回流? | 供应商/生成代码的缺陷修复缺乏跨项目回流机制——预防动作落点(§5.2) |

### 3.4 根因与依据

* **根因**:`PduR_Gateway_TpDcmTx.c:71` 的 `TpSduLength = SessionPtr->SduLength_auo[0];` 硬编码 FIFO 下标 0——功能寻址组播交付推迟时,本次数据在槽 N 而 SoR 长度取槽 0,DCM 按过期长度解析新数据。
* **根因分类**:编码。
* **代码依据**:
  - 路由链:0x7DF → `PduR_GwTp[]` 4 个 gt 挂 `PduR_GwMcTx_Transmit` → loTransmitTable[2]=`PduR_GF_TP_Dcm_Transmit_Func`(`PduR_PBcfg.c:1954/2273`),FIFO=`PduR_gw_Tp_buf_PduRTxBuffer_FUNC_FUNC`
  - 推迟路径 caller 自洽性:`PduR_Gateway_TpTxConf.c:183-300`(readPtr=begin+Tx实例×bufferLength、readerPduInfo 用 `SduLength_auo[Tx_FifoInstanceUsed]`)
  - **T32 实时取证**(2026-10-20,v0 固件,断点 `PduR_GF_TP_Dcm_Transmit_Func` 0x400975D0):HIT2=`1003` slot1 推迟交付时刻 `info.SduLength=2`(正确)、`SduLength_auo=[4,2,2,0]`(v0 取 [0]=4 为 slot0 过期值)——错配直接抓现行,证据存 `testcase/t68/func_10_min_6762/t32_evidence_20261020.txt`
  - 结构依据:`PduR_Types.h` PduR_TpSession_Dynamic(PduLengthType=uint16);`PduR_Cfg_Internal.h:73` PDUR_MULTICAST_FROM_TP_SUPPORT=1
* **责任归属**:本模块(PduR 生成/供应商代码)缺陷。

### 3.5 影响范围评估

* 同源 `PduR_Gateway_TpDcmTx.c` 存在于所有使用该 PduR 版本、配置功能寻址 TP 组播网关的项目——**修复需同步**:develop 全部 GAC 项目 + release 分支 `release/GAC/T68Y_G460/0710`、`release/GAC/T09_Y1_D126/G710`、`release/GAC/T75_D084/G270`、`release/T51-D088/S.001`(用户确认范围,其余分支无需处理)。
* 先例:F4CMC-41(TDA4 侧)已用同款修复验证过生产环境。

---

## 四、 分析结论与分流 (Conclusion & Triage)

**是问题**:PduR 组播网关向 DCM 推迟交付时 SoR 长度硬编码 FIFO 下标 0,属编码缺陷,两表现(NRC13/静默丢)同根。→ 转正式开发(范围见 §3.5)。

---

## 五、 修复方案(仅"是问题") (Fix Plan)

### 5.1 纠正措施(Corrective Action,治此件)

| # | 修改点 | 文件 | 改动说明 | 风险评估 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | SoR 长度跟随调用者 info,无 info 时退回 Rx 实例长度 | `cpj_gac/autosar/<项目>/BswRta/src/bsw/PduR/src/PduR_Gateway_TpDcmTx.c:71` | `TpSduLength = (info != NULL_PTR) ? info->SduLength : SessionPtr->SduLength_auo[SessionPtr->Rx_FifoInstanceUsed_u8];`(F4CMC-41 同款);**改动按 AUTOSAR patch 规则加 `<{项目名}PATCH P1>` 标记**(防下次代码生成覆盖,见 CLAUDE.md) | 立即路径 caller 恒带 info、长度不变;推迟路径 info 长度==本槽真实长度(T32 已证),无行为回归面;注释标记不影响已验证二进制 |

* **交接物**(给 feature-development):V2 工作区 `02_Workspace_J6_V2/src/mcu_app_j6@develop` 的 `cpj_gac/autosar/t68/BswRta/src/bsw/PduR/src/PduR_Gateway_TpDcmTx.c`(1 行 diff);正式提交范围=develop 全 GAC 项目(逐项目同文件同改动)+ 4 条 release 分支(cherry-pick/同款重打),其他分支无需再验证(用户确认)。
* **正式开发关联**:JIRA Story(转 story 后回填单号)。

### 5.2 预防措施(Preventive Action,治同类)

| # | 预防动作 | 落点 | 状态 |
| :--- | :--- | :--- | :--- |
| 1 | 供应商/生成代码缺陷修复完成后,排查同源代码在其他项目/分支的存在并建立同步清单(本次靠人工召回 F4CMC-41 才命中) | problem-analysis 阶段 2 知识召回环节已实践;流程化待与团队确认 | 待办 |

---

## 六、 验证结果(仅"是问题") (Verification)

* **验证性修复(V2 工作区,mcu_app_j6@develop,T68 产品配置)**:
  * 编译:`imobuilder build mcu_app_j6 -r -x parking_dr uper_app` 通过(2026-10-20)
  * 刷写:ProgramBoard_j6b.py t68_mcu.json,2026-10-20
  * A/B 验证(DiagnosticTester,CX ch0 500K/2M):

| 用例 | v0 基线 | v2 修复 |
| :--- | :--- | :--- |
| func_10_min_6762(4 步,6762 最小化) | step3 `1003`→`7F1013` FAIL(20261020_151747) | **4/4 PASS**(20261020_160247) |
| func_3e_no_response_stale_length(7 步,6763) | step3 `3E0000` TIMEOUT 静默丢(20261020_142930) | **7/7 PASS**(20261020_144006 / 20261020_160311 两次) |

* **回归确认**:两用例全步骤(含 NRC13 合理场景、正常会话切换)全绿;v3 错误方案(7FFF21)已排除并还原。
* **正式提交后验证**:待 PR 合并后回填。

---

## 七、 关闭与生命周期记录 (Closure & Lifecycle)

### 7.1 可复用结论

* 关键词:功能寻址 NRC13 / 隔帧不响应 / SduLength_auo / PduR_GF_TP_Dcm_Transmit_Func / 组播推迟交付 → 命中本篇。快速判定:连发时"过期长度>实际→NRC13、<实际→静默丢"即此缺陷;修复模板=F4CMC-41 v2 写法。

### 7.2 缺陷生命周期记录

| 状态 | 日期 | 操作人 | 备注 |
| :--- | :--- | :--- | :--- |
| 发现(报告) | 2026-10(问题单创建) | Siyuan Liu | 6762/6763 两单 |
| 分析开始 | 2026-10-20 | @Hua.Yao | V2 基线建立 |
| 根因确认 | 2026-10-20 | @Hua.Yao | 代码走读 + T32 实时取证 |
| 修复验证通过 | 2026-10-20 | @Hua.Yao | V2 A/B 验证全绿 |
| 正式提交 | 待回填 | @Hua.Yao | develop GAC 全项目 + 4 release 分支 |
| 关闭 | 待回填 | — | 待 JIRA 流转 |

---

## 附录:原始证据

* T32 实时取证(断点停机内存快照+结构偏移说明):`tools/DiagnosticTester/testcase/t68/func_10_min_6762/t32_evidence_20261020.txt`
* 测试运行目录(`result.csv`/`run.log`/`trace.blf`):
  - v0 红:`func_10_min_6762/20261020_151747`(6762)、`func_3e_no_response_stale_length/20261020_142930`(6763)
  - v0+T32(时序扰动,仅取 HIT 快照):`20261020_154604`/`20261020_155543`
  - v3 错误方案证据(7FFF21):`func_3e_no_response_stale_length/20261020_145444`
  - v2 绿:`func_10_min_6762/20261020_160247`、`func_3e_no_response_stale_length/20261020_144006`/`20261020_160311`
* 用例定义:`tools/DiagnosticTester/testcase/t68/func_10_min_6762/func_10_min_6762.yaml`、`func_3e_no_response_stale_length/func_3e_no_response_stale_length.yaml`、`func_10_nrc13_stale_length/func_10_nrc13_stale_length.yaml`(6 步泛洪版,含 FIFO 容量混淆因素说明)
* T32 观察脚本:`tools/Trace32Debug/t32_obs_dcm_delivery.py`(脚本原位于 tools/DiagnosticTester/,2026-10-21 迁入 Trace32Debug;testcase 下的 t32_evidence 取证文件随用例留在 DiagnosticTester)
