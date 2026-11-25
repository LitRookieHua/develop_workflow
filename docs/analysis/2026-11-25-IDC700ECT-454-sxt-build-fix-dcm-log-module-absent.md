# 🐞 [IDC700ECT-454-sxt 变体编译失败（DCM_RXPDUID_FIX 补丁引入 Log.h）] 问题分析报告

| 文档基础属性 | 内容说明 | 分析与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **问题单号** | IDC700ECT-454（Story，problem-analysis 流程直接立项，无独立 Problem 单） | **分析结论** | 🟢 是问题(编译失败，已修复) |
| **问题主题** | sxt/sxt_a/sxt_b 变体编译失败——9773 补丁引入 Log.h，smartxtruck 无 Log 模块 | **缺陷类型** | 集成（跨项目补丁同步引入不存在的模块依赖） |
| **分析人 / 日期** | @Hua.Yao / `2026-11-25` | **严重等级** | S2 严重（三变体全部无法出包） |
| **项目 / 变体** | smartxtruck（sxt / sxt_a / sxt_b），mcu_app_j6 | **优先级** | P3 中（JIRA Medium） |
| **发现阶段** | 编译（develop 分支集成） | **分析状态** | 🔵 已修复 |
| **根因分类** | 集成 | **关联输出** | 🔗 [IDC700ECT-454](https://jira.imotion.ai:7070/browse/IDC700ECT-454) ｜ 📋 Obsidian 分析笔记（SXT Build Fix Dcm Log Module Absent） |

> **📝 变更记录**
> * `2026-11-25`｜@Hua.Yao｜V1.0｜初版:现象固定与根因分析、修复与验证记录

---

## 一、 缺陷概述 (Defect Summary)

### 1.1 问题描述

2026-11-23 合入 mcu_app_j6 develop 的 IDC310GAC-9773（commit `0c53096d6`，DCM_RXPDUID_FIX 补丁）在 sxt/sxt_a/sxt_b 三个变体的 `Dcm_Prv_General.c` 引入了 `#include "Log.h"` 与 `LogSyncAcoreOnly` 日志调用；smartxtruck 工程没有 Log 模块，三个变体编译失败。

### 1.2 现象与复现(原样摘录)

**复现步骤**(原样)：

1. mcu_app_j6@develop（含 `0c53096d6`）编译 sxt 系变体
2. `Dcm_Prv_General.c:26` 的 `#include "Log.h"` 找不到头文件，编译失败

**期望行为**: IDC310GAC-9773 的钳位修复合入后，所有被打补丁的变体（含 sxt 系）编译通过
**实际行为**: sxt/sxt_a/sxt_b 三变体编译失败；其余 23 个变体中 GAC 系工程有 Log 模块、7 个老 Dcm 变体未打补丁，均不受影响

> 现象来源：2026-11-25 用户实测确认（三变体编译失败）；根因经代码走读确认（见 §3.2），无独立报错日志存档。

### 1.3 环境矩阵

| 项 | 版本/值 | 来源 |
| :--- | :--- | :--- |
| 固件版本 / commit | mcu_app_j6@develop@`0c53096d6`（IDC310GAC-9773 合入后） | 分析基线 |
| 编译环境 | 10.0.12.42（编译服务器），GHS/GCC 工具链 | 编译验证 |
| 涉及预设 | cpj_smartxtruck（sxt / sxt_a / sxt_b 三变体） | 仓库目录 |

### 1.4 分析输入与基线

| 输入 | 来源 | 说明 |
| :--- | :--- | :--- |
| 现象与验证结论 | 用户（2026-11-25） | 三变体编译失败；注释掉两行后编译通过 |
| 来源补丁 | commit `0c53096d6`（IDC310GAC-9773） | 补丁说明：Applied to 23 variants under cpj_*/autosar |
| 分析基线 | V1 工作区 mcu_app_j6@develop | 编译级问题，无需台架 |

---

## 二、 复现性与数据回放 (Reproducibility & Replay)

### 2.1 可复现性

| 复现率 | 条件 | 样本 |
| :--- | :--- | :--- |
| 每次必现 | develop 含 `0c53096d6`，编译任意 sxt 系变体 | 3/3 变体 |

* **首次/末次出现**: 首次出现 = `0c53096d6` 合入 develop（2026-11-23）；修复前持续存在

### 2.2 现象固定与回放

* **异常发生时的状态**: 确定性编译失败（非运行时问题），无需回放；代码走读即完整证据链（§3.4）

---

## 三、 根因分析 (Root Cause Analysis)

### 3.1 知识召回(看代码之前先做)

| 检索源 | 关键词 | 结果 |
| :--- | :--- | :--- |
| `docs/analysis/` 历史个案 | DCM_RXPDUID_FIX / Log.h / sxt 编译失败 | 无命中 |
| Obsidian Work Database 笔记 | IDC310GAC-9773 / sxt_a 编译 | 命中 sxt_a 链接阻塞笔记（IDC700ECT-16，运行时链接符号问题，与本编译问题无关，排除） |

### 3.2 排查过程(假设-验证-排除链)

| # | 假设 | 验证手段 | 结果 |
| :--- | :--- | :--- | :--- |
| 1 | sxt 工程缺 Log 模块，include 落地即失败 | `find cpj_smartxtruck -name 'Log.h'` → 无结果；Log.h 存在于 GAC 系工程 | 命中——见 §3.4 |
| 2 | 9773 补丁其他改动（钳位逻辑）也不兼容 sxt | 走读 `Dcm_Prv_GetMainConnection()` 钳位代码：仅用 Dcm 自身 API，无外部依赖 | 排除——钳位逻辑可在 sxt 编译通过（修复后验证确认） |

### 3.3 5 Whys 深挖

| 层级 | 提问 | 回答 |
| :--- | :--- | :--- |
| Why 1 | 为什么 sxt 变体编译失败？ | `Dcm_Prv_General.c:26` include 了不存在的 `Log.h` |
| Why 2 | 为什么会出现不存在的 include？ | IDC310GAC-9773 打补丁时给全部 23 个变体统一加了 Log 日志，Log 模块只在 GAC 等工程存在，smartxtruck 没有 |
| Why 3 | 为什么补丁没做工程差异适配？ | 补丁按"同源 BswRta 代码统一修改"批量同步，未校验各工程模块依赖差异 |
| Why 4 | 为什么批量同步没有拦住？ | 跨项目同步补丁无"目标工程模块存在性"校验步骤（流程缺口，防腐动作落点） |

### 3.4 根因与依据

* **根因**: `0c53096d6`（IDC310GAC-9773）跨项目批量同步 DCM_RXPDUID_FIX 补丁时，把 GAC 工程才有的 `Log.h`/`LogSyncAcoreOnly` 日志依赖带进了 smartxtruck 的三个变体（sxt/sxt_a/sxt_b），include 落地即编译失败
* **根因分类**: 集成
* **代码依据**: `cpj_smartxtruck/autosar/{sxt,sxt_a,sxt_b}/BswRta/src/bsw/Dcm/src/General/Dcm_Prv_General.c:26`（`#include "Log.h" /* DCM_RXPDUID_FIX */`）；`find cpj_smartxtruck -name 'Log.h'` 无结果
* **责任归属**: 上游补丁（IDC310GAC-9773）的跨项目同步范围问题；sxt 侧无责任

### 3.5 影响范围评估

* 仅 sxt/sxt_a/sxt_b 三变体（mcu_app_j6@develop）；9773 补丁的其余落点（GAC 系有 Log 模块、7 个 12.3-era 老变体未打）不受影响
* 钳位逻辑本体不受本次修复影响（仅去日志，行为不变）

---

## 四、 分析结论与分流 (Conclusion & Triage)

**是问题**：跨项目补丁同步引入不存在的模块依赖，属集成缺陷 → 立项 Story IDC700ECT-454，最小修复后走 PR 合 develop。

---

## 五、 修复方案(仅"是问题") (Fix Plan)

### 5.1 纠正措施(Corrective Action,治此件)

| # | 修改点 | 文件 | 改动说明 | 风险评估 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 注释掉 Log include | `cpj_smartxtruck/autosar/{sxt,sxt_a,sxt_b}/BswRta/src/bsw/Dcm/src/General/Dcm_Prv_General.c:26` | `// #include "Log.h" /* DCM_RXPDUID_FIX: ... */`（保留原注释，便于补丁重放时识别） | 无——去掉未编译过的日志调用 |
| 2 | 注释掉日志调用 | 同上 `:375`（`Dcm_Prv_GetMainConnection` 钳位分支内） | `// LogSyncAcoreOnly(...)` | 无——仅输出去除，钳位赋值逻辑保留 |

* **正式开发关联**: JIRA Story IDC700ECT-454；改动直接在 mcu_app_j6 feature 分支提交（两行注释级最小修复，不另写设计文档）

### 5.2 预防措施(Preventive Action,治同类)

| # | 预防动作 | 落点 | 状态 |
| :--- | :--- | :--- | :--- |
| 1 | 跨项目批量同步补丁时校验目标工程模块依赖（grep 目标工程再落 include） | 补丁同步操作惯例（autosar-code-generation.md patch 重放流程旁注候选） | 待办（记入本报告即可，不改流程文档） |

---

## 六、 验证结果(仅"是问题") (Verification)

* **编译验证**: sxt/sxt_a/sxt_b 三变体编译通过（2026-11-25 用户确认）
* **bench 复现说明（降级）**: 编译失败类问题，编译通过即修复验证，无运行时行为变化（仅去除日志输出），无需台架 A/B 复现
* **回归确认**: 钳位逻辑（IDC310GAC-9773 本体）保持不变，仅日志调用注释
* **正式提交后验证**: PR #2284 已合入 develop（2026-11-25），合入后 develop 三变体编译即恢复（修复即编译验证，无需额外复验）

---

## 七、 关闭与生命周期 (Closure & Lifecycle)

### 7.1 可复用结论

* 关键词：`sxt 编译失败` / `Log.h` / `DCM_RXPDUID_FIX` / `跨项目补丁同步` → 命中本篇
* 快速排查路径：变体编译失败先查失败行是否带外来工程模块依赖（include + `find <cpj> -name <Module>.h`），再查最近合入的跨项目补丁（`git log -p -- <file>`）

### 7.2 缺陷生命周期记录

| 状态 | 日期 | 操作人 | 备注 |
| :--- | :--- | :--- | :--- |
| 发现(报告) | 2026-11-25 | Hua.Yao | sxt 变体编译失败 |
| 根因确认 | 2026-11-25 | Hua.Yao | Log.h 缺失，9773 补丁引入 |
| 修复验证通过 | 2026-11-25 | Hua.Yao | 三变体编译通过 |
| 正式提交 | 2026-11-25 | Hua.Yao | commit `3f26939b7` @ feature/IDC700ECT-454-sxt-dcm-log-module-absent；PR [#2284](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/2284) |
| 关闭 | 2026-11-25 | — | PR #2284 已合并（bot_ci + Lucas.Han 批准）；Story 两步流转至已解决 |

---

## 附录:原始证据

* 来源补丁 commit（IDC310GAC-9773）信息与 23 变体落点说明：`git show 0c53096d6`（mcu_app_j6@develop）
* 当前修复 diff（三变体各 2 行，完全一致）：

```diff
-#include "Log.h" /* DCM_RXPDUID_FIX: LogSyncAcoreOnly for the diagnostic logs */
+// #include "Log.h" /* DCM_RXPDUID_FIX: LogSyncAcoreOnly for the diagnostic logs */
...
-        LogSyncAcoreOnly("[DCM] GetMainConnection invalid rxpduId=%d -> %d\r\n", (int)origRxPduId, (int)rxpduId);
+        // LogSyncAcoreOnly("[DCM] GetMainConnection invalid rxpduId=%d -> %d\r\n", (int)origRxPduId, (int)rxpduId);
```
