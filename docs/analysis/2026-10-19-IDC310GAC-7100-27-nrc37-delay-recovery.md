# 🐞 IDC310GAC-7100 0x27服务NRC37延迟过期后种子重放导致解锁被拒 问题分析报告

| 文档基础属性 | 内容说明 | 分析与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **问题单号** | IDC310GAC-7100 | **分析结论** | 🟡 是问题但 develop 已修复(测试包为修复前基线,换版本回归即可,无需新代码) |
| **问题主题** | 0x27 秘钥计数器到 2 等待 11s 后,2701 种子重放再触发 NRC37,APP 解锁被拒 | **缺陷类型** | 功能(安全访问 0x27 服务) |
| **分析人 / 日期** | @Hua Yao / `2026-10-19` | **严重等级** | S3 一般(安全解锁功能受阻,10s+重试序列下才触发,非攻击面) |
| **项目 / 变体** | T75-G(GAC T75-G1,mcu_app_j6/cpj_gac/autosar/t75) | **优先级** | P3 中 |
| **发现阶段** | 台架功能测试 | **分析状态** | 🔵 已修复(develop 分支,7162+6205) |
| **根因分类** | 编码(DCM SECA 延迟过期后状态清理不完整) | **关联输出** | 🔗 [JIRA IDC310GAC-7100](https://jira.imotion.ai:7070/browse/IDC310GAC-7100) ｜ 📄 无需新设计文档 ｜ 📋 Obsidian《T75 Fix 27 NRC37 delay recovery》 |

> **📝 变更记录**
> * `2026-10-19`｜@Hua Yao｜V1.0｜初版:现象固定、根因分析、develop 基线自动验证通过

---

## 一、 缺陷概述 (Defect Summary)

### 1.1 问题描述

0x27 安全访问服务中,失败计数器达到 NumAttDelay(2)武装 10s 延迟并等延迟过期后,DCM 未清除存储的种子(SeedBuff)与 IsGetSeed 标志;后续 2701 命中"存储种子重放"分支重新累计计数器,再次武装延迟,导致解锁请求被 NRC 0x37 拒绝。

### 1.2 现象与复现(原样摘录)

**复现步骤**(原样,来自问题单 Problem Description 字段):

> *Precondition:* 正常上电
> 1、版本:[https://ci.imotion.ai/package/9494/detail](https://ci.imotion.ai/package/9494/detail)
> 2、全部外设
>
> *Reproduce Steps:*
> 1、1003
> 2、连续请求4次2701,使秘钥计数器达到2
> 3、等待11s
> 4、发送2次2701
> 5、APP解锁
>
> *Expected result:*
> 4、肯定响应
> 5、解锁成功
>
> *Actual result:*
> 5、NRC37
> {*}Probability of reproduce:{*}5-5

**期望行为**:步骤 4 两次 2701 回肯定响应(种子),步骤 5 解锁成功(6702)。
**实际行为**:步骤 5 回 NRC 0x37(requiredTimeDelayNotExpired),解锁失败。

### 1.3 环境矩阵

| 项 | 版本/值 | 来源 |
| :--- | :--- | :--- |
| 固件版本 / commit | CI 包 9494(2026-09-29 构建,修复前基线) | 问题单 |
| 分析/验证基线 | mcu_app_j6@develop@98eaa4d03(含 7162+6205 修复) | V2 工作区编译刷写 |
| 硬件版本 / 板卡 | J6B EVM(CH9114 串口,A核=SERIAL-C/COM33) | 本地台架 |
| 测试环境 | 台架,程控电源 KA3005P(COM44),CAN 卡创芯 CX-USBCANFD | 本地台架 |
| 相关工具/诊断仪 | DiagnosticTester(testcase/t75/sec_27_nrc37_delay_recovery) | 本验证 |

### 1.4 分析输入与基线

| 输入 | 来源 | 说明 |
| :--- | :--- | :--- |
| 复现步骤/现象 | 问题单 Problem Description(customfield_12007) | 原样摘录于 §1.2;标准 description/评论均为空 |
| 附件 | 问题单 attachment | 无 |
| 评论补充 | 问题单 comment | 无 |
| 分析基线 | 02_Workspace_J6_V2/src/mcu_app_j6@develop@98eaa4d03 | 编译通过(T75G_D134 preset) |

---

## 二、 复现性与数据回放 (Reproducibility & Replay)

### 2.1 可复现性

| 复现率 | 条件 | 样本 |
| :--- | :--- | :--- |
| 5-5 每次必现(修复前基线) | 计数器达 2 → 等 11s → 2×2701 → 解锁 | 问题单 reporter 实测 |
| 0(修复后 develop 基线) | 同序列 | 本次自动验证 13/13 PASS |

* **首次/末次出现**:首次发现于 CI 包 9494(2026-09-29);develop 分支 2026-09-30 后(含 1c1f24294)不复现。

### 2.2 现象固定与回放

* **关键状态链**(T75G 配置,`Dcm_Lcfg_DspUds.c` / `Dcm_Cfg_DspUds.h`):
  * NumAttDelay=2、DelayTime=1000×10ms=**10s**、NumAttLock=0、DCM_CFG_DSP_DELAYTIMERMONITORING=**DCM_PRV_REQUEST_SEED**(延迟监控在种子请求侧)、ResetAttemptCounter=TRUE、STORESEED=ON
* **报文回放**(2026-10-19 自动验证前半段,修复前行为同构):
  * 4×2701 → 前 3 次 `6701 1E3BEB51`(重放同一种子,计数器 0→2),第 4 次 `7F 27 37`(延迟武装)
  * 等 11s 后 2×2701 → 修复前:重放分支计数器再累计到 2、再次武装延迟 → 解锁 2701 被 `7F 27 37` 拒(问题单现象)

---

## 三、 根因分析 (Root Cause Analysis)

### 3.1 知识召回(看代码之前先做)

| 检索源 | 关键词 | 结果 |
| :--- | :--- | :--- |
| `docs/analysis/` 历史个案 | NRC37 / 0x27 / 秘钥 | 无直接命中 |
| `docs/design/` 设计方案 | 27 / security | 无直接命中 |
| Obsidian Work Database 笔记 | NRC37 / 2701 / 秘钥 | **命中**《UDS_SecurityAccess_NRC37_Fix_Note》(IDC310-821,AY7):同类机制——IsGetSeed_u8 标志与失败计数器的引入背景,加速本单收敛 |
| git 历史(DcmDspUds_Seca.c) | 7822 / 7162 / 6205 | **命中**修复链:081bef2fb(IDC310-7822)→ 1c1f24294(IDC310GAC-7162)→ f37daa9f6(IDC310GAC-6205) |

### 3.2 排查过程(假设-验证-排除链)

| # | 假设 | 验证手段 | 结果 |
| :--- | :--- | :--- | :--- |
| 1 | 测试方法问题(等待期 S3 超时回默认会话,0x27 被拒) | 走读 DSL S3 逻辑 + 首版自动验证(等待期未保活,2701 回 `7F 27 7F`) | **排除**——NRC 0x7F≠0x37,与问题单现象不符;问题单测试仪保活了会话 |
| 2 | 延迟时间未真正过期(DelayTime 计算/单位错) | 核对配置:1000×10ms=10s,等待 11s>10s | **排除**——时间足够 |
| 3 | 延迟过期后失败计数器/种子状态未清理,种子重放分支二次累计并再武装延迟 | 走读 `Dcm_Prv_CheckNRCForSeedRequest` / `Dcm_Prv_ProcessSeedRequest` + 对照 git 历史 1c1f24294 diff | **命中**——见 §3.3/§3.4 |

### 3.3 5 Whys 深挖

| 层级 | 提问 | 回答 |
| :--- | :--- | :--- |
| Why 1 | 为什么等 11s 后解锁仍被 NRC37 拒? | 延迟过期后的 2×2701 走"存储种子重放"分支,计数器从残留状态再次累计到 NumAttDelay=2,重新武装 10s 延迟,解锁请求落在新的延迟窗口内 |
| Why 2 | 为什么延迟过期后状态没清干净? | 修复前代码在延迟过期路径只按 ResetAttemptCounter_b 清了 FailedAtm_cnt,**SeedBuff 与 IsGetSeed_u8 残留**——IsGetSeed=1 使重放分支的计数递增条件成立,旧种子使 Dcm_Prv_IsSeedAlreadyStored 判真 |
| Why 3 | 为什么这段代码如此? | IDC310-821(AY7)引入 IsGetSeed 连续种子请求计数机制时,只覆盖"计数递增",未覆盖"延迟过期后的状态复位"——两条生命周期(计数器 vs 种子)不同步 |
| Why 4 | 为什么 7822/7162 的修复没拦住本单? | 本单测试包 9494 构建于 2026-09-29,而 7162 落地于 2026-09-30——测试版本与修复版本恰好擦肩;且 7822 修的是"永不触发 0x37"的反向死锁,7162 才补上"超时后清种子"这一半 |
| Why 5 | 为什么测试基线与修复基线的时序差没有预警? | 逐单人工核对 CI 包构建日期与相关模块修复提交日期,无工具化手段——流程缺口,见 §5.2 预防 |

### 3.4 根因与依据

* **根因**:DCM SECA 延迟过期路径未同步清除 SeedBuff 与 IsGetSeed_u8(`DcmDspUds_Seca.c` 的 `Dcm_Prv_CheckNRCForSeedRequest` 延迟过期块,修复前版本),导致种子重放分支二次累计计数器并再武装延迟,解锁请求被 NRC 0x37 拒绝。
* **根因分类**:编码(状态生命周期管理不完整)。
* **代码依据**:
  * 修复 commit `1c1f24294`(IDC310GAC-7162,2026-09-30):延迟过期块新增 SeedBuff 清零 + IsGetSeed_u8=0,并引入 s_keyReqSinceSeed_u8 防错密钥双重计数
  * 修复 commit `f37daa9f6`(IDC310GAC-6205,2026-10-08):ResetAttemptCounter_b 块补清 IsGetSeed_u8(含 t75)
  * 规格:ISO 14229-1 SecurityAccess——延迟过期后 ECU 应恢复正常种子/密钥流程
* **责任归属**:本模块(DCM)缺陷,已在 develop 修复;测试包版本早于修复,无需新代码。

### 3.5 影响范围评估

* 修复前基线同样影响 7162 所列全部 10 个 GAC 变体(ay7/s52/s52-e046/t09/t51/t68/t75/t88/t996d/v20)——但 7162/6205 已一并修复,**develop 分支全部闭环**;仅各变体修复前的存量测试版本受影响,换版本即可。

---

## 四、 分析结论与分流 (Conclusion & Triage)

**是问题,但 develop 分支已修复**——CI 包 9494(2026-09-29)是修复(2026-09-30 `1c1f24294`)前的基线,现象与修复前代码推演逐字吻合;当前 develop(98eaa4d03)编译刷板自动验证 13/13 PASS。**无需新代码,建议测试换 develop 最新版本回归后关单。**

---

## 五、 修复方案(仅"是问题") (Fix Plan)

### 5.1 纠正措施(Corrective Action,治此件)

不适用——修复已存在于 develop(`1c1f24294` IDC310GAC-7162 + `f37daa9f6` IDC310GAC-6205),本单无需 V2 验证性修复,无交接物。

### 5.2 预防措施(Preventive Action,治同类)

| # | 预防动作 | 落点 | 状态 |
| :--- | :--- | :--- | :--- |
| 1 | 问题单分析时先查 git log 该模块修复链与测试包构建日期的时序差(测试包早于修复 → 先换版本回归) | problem-analysis skill 阶段 2 知识召回已含 git 历史检索实践 | 已落实(本单实践) |
| 2 | 0x27 延迟恢复类用例沉淀为可复跑 testcase | `tools/DiagnosticTester/testcase/t75/sec_27_nrc37_delay_recovery/` | 已落地 |

---

## 六、 验证结果(仅"是问题") (Verification)

* **验证方式**:develop 基线(98eaa4d03)编译 → ProgramBoard 刷写(t75_mcu.json,MCU_a/MCU_b) → **DiagnosticTester 自动验证**(非手动):
  * 用例:`testcase/t75/sec_27_nrc37_delay_recovery/sec_27_nrc37_delay_recovery.yaml`,CX-USBCANFD
  * **结果:13/13 PASS**(2026-10-19 17:53,run.log/result.csv/trace.blf 落盘在用例目录 `20261019_175303/`)
  * 关键证据:第 4 次 2701 `7F 27 37`(延迟武装,与问题单同构)→ 3E00 保活等 11s → 2701 回**全新种子** `6701 F2E110EE`(≠旧种子 `1E3BEB51`,证明 SeedBuff 已清)→ 第 2 次 2701 正常回种子 → **解锁 `6702` 成功**
  * ⚠️ 用例设计要点:等待期必须 3E00 保活防 S3 超时回默认会话(首版未保活,2701 回 `7F 27 7F`,是测试方法问题非固件问题)
* **回归确认**:正常种子-密钥流程(security_access 自动序列)通过;重放计数、延迟武装行为与设计一致
* **正式提交后验证**:不适用(无新提交,复用既有 develop 修复)

---

## 七、 关闭与生命周期 (Closure & Lifecycle)

### 7.0.1 同源问题单 release 分支同步（2026-10-19 追加）

同源缺陷影响 5 个 GAC 变体的 release 分支（均停留于修复前基线，已逐一核实不含 7162）。按用户指示全链同步 7822→7162→6205（cherry-pick 自 develop），各分支 own-variant Seca.c 已 diff 确认与 develop 完全一致；release 分支上不存在的变体文件（t88/t996d/v20）在冲突中保持删除。分支与 PR：

| 变体 | release 分支 | 问题单 | cherry-pick | PR |
| :--- | :--- | :--- | :--- | :--- |
| T75 | release/GAC/T75_D084/G270 | 7100 | 7822+7162+6205 | [#1578](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/1578/overview) |
| T09-Y | release/GAC/T09_Y1_D126/G710 | 6886 | 7822+7162+6205 | [#1579](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/1579/overview) |
| T68 | release/GAC/T68Y_G460/0710 | 6301 | 7822+7162+6205 | [#1580](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/1580/overview) |
| T51 | release/T51-D088/S.001 | 无单（预防性） | 7822+7162+6205 | [#1581](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/1581/overview) |
| S52 | release/GAC/S52_D110/G540 | 5697/6324 | 7162+6205（7822 已含） | [#1582](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/1582/overview) |

**6886（T09-Y，7822 类症状：0x37 永不触发）复现场景验证**：两轮 4×2701 + 等 11s（3E00 保活），断言两轮第 4 次均回 NRC37——**T09-Y 实板**（develop 基线 T09 固件 Gac/T09Y1_D126，ECU 版本 G710v6）DiagnosticTester 14/14 PASS（`testcase/t09/sec_27_nrc37_retrigger/20261020_091507/`）：第一轮第 4 次 `7F 27 37`（延迟武装）→ 第二轮回全新种子 `B6B8F48A`（≠第一轮 `0480B8A7`）且第 4 次再次 `7F 27 37`（延迟重新武装，修复前此处永不回 NRC37）。台架经验：T09 诊断挂 CANFD1（500k/2M），CX 卡 ch0；换板后 USB Serial Port 升序第 3 个（COM65）= A 核。

### 7.1 可复用结论

* 0x27 NRC37 相关异常先查 git log `DcmDspUds_Seca.c` 修复链(821→7822→7162→6205)与测试包构建日期的先后;测试包早于 2026-09-30 的 GAC 变体均可能携带本缺陷
* DiagnosticTester 验证 0x27 延迟类场景:等待段用 3E00 保活(`delay_after_ms` 分段累计),否则 S3 超时会以 `7F 27 7F` 假失败
* 变体 CAN 配置差异排查顺序:FD 数据段波特率(T09=2M,T75=5M)→ 诊断 CAN ID 所挂控制器(T09=CANFD1,T75=CANFD11)→ 台架接线;`CanIf_PBcfg.c` 搜 `0x70E` 可直接定位控制器名

### 7.2 缺陷生命周期记录

| 状态 | 日期 | 操作人 | 备注 |
| :--- | :--- | :--- | :--- |
| 发现(报告) | 2026-09-29 | Siyuan Liu | 问题单创建(CI 包 9494) |
| 修复(develop) | 2026-09-30 | Xuanhe Fang | `1c1f24294` IDC310GAC-7162,经 [PR #1346](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/1346/overview) 合入(先于本单分析) |
| 修复补充 | 2026-10-08 | Hua Yao | `f37daa9f6` IDC310GAC-6205 |
| 分析开始 | 2026-10-19 | @Hua Yao | V2 基线建立(T75G_D134) |
| 根因确认 | 2026-10-19 | @Hua Yao | 修复前代码推演与现象逐字吻合 |
| 验证通过 | 2026-10-19 | @Hua Yao | develop 刷板 + DiagnosticTester 13/13 PASS |
| 同源单分支同步 | 2026-10-19 | @Hua Yao | 5 个 release 分支 cherry-pick 修复链并建 PR(#1578-#1582);6886 场景 14/14 PASS |
| 关闭 | 待办 | — | 建议:换 develop 版本回归后以"已修复/duplicate of 7162"关单(待用户确认分流) |

---

## 附录:原始证据

* 自动验证日志:`tools/DiagnosticTester/testcase/t75/sec_27_nrc37_delay_recovery/20261019_175303/`(run.log / result.csv / trace.blf)
* 首版假失败日志(未保活,S3 超时):同目录 `20261019_174901/`
* 修复 diff:`git show 1c1f24294 -- cpj_gac/autosar/t75/.../DcmDspUds_Seca.c`(服务器 mcu_app_j6)
