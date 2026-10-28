# 🐞 [T1LFL1-0x22 功能寻址读 F190 复测报告] 问题分析报告

| 文档基础属性 | 内容说明 | 分析与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **问题单号** | 无问题单（口头复测报告；历史同源单 [D1CYC-1516](https://jira.imotion.ai:7070/browse/D1CYC-1516) 已关闭） | **分析结论** | 🔴 不是问题（暂定，遗留疑点见 §四） |
| **问题主题** | [Docan] 功能寻址读 F190 VIN 返回正响应，期望无响应 | **缺陷类型** | 环境（测试固件版本疑似不含修复） |
| **分析人 / 日期** | @Hua.Yao / `2026-10-28` | **严重等级** | S3（诊断协议合规性，量产测试项） |
| **项目 / 变体** | T1LFL1（Chery D073，TDA4，mcu_app_tda4） | **优先级** | P3 |
| **发现阶段** | 测试复测（口头报告，无单据） | **分析状态** | ⚪ 已关闭（暂定不是问题） |
| **根因分类** | 环境 | **关联输出** | 🔗 历史单 D1CYC-1516 ｜ 修复 Story [D1CYC-1615](https://jira.imotion.ai:7070/browse/D1CYC-1615) ｜ 📋 Obsidian 笔记《T1LFL1 Fix dem ec error and 22 function address bug》 |

> **📝 变更记录**
> * `2026-10-28`｜@Hua.Yao｜V1.0｜初版：源码层面回归核查，定性"不是问题（暂定）"

---

## 一、 缺陷概述 (Defect Summary)

### 1.1 问题描述

> T1LFL1 项目测试报告：[Docan] 功能寻址（0x7DF）读 F190 VIN 码时系统返回正响应，期望无响应。涉及 develop 分支和 T480 release 分支。无问题单，描述由用户口头传达——与 2026-09-22 已修复关闭的 D1CYC-1516 完全同源。

### 1.2 现象与复现（原样摘录）

**复现步骤**（原样，来自用户传达）：

> 问题描述： 在进行 [Docan] 功能寻址读取 F190VIN 码时，系统返回了正响应。
> 期望结果： 期望系统无响应。
> develop分支和T480 release分支

**期望行为**：0x22 服务寻址方式为 P（仅物理寻址），功能寻址请求应无响应（参考测试用例 Read VIN-TestCase4：send 22 F1 90 using CANID 7DF → 期望 NO Response）
**实际行为**：DUT 返回肯定响应 62 F1 90 ...（多帧传输）

### 1.3 环境矩阵

| 项 | 版本/值 | 来源 |
| :--- | :--- | :--- |
| 分析基线 develop | mcu_app_tda4@origin/develop@c255b911（2026-10-27） | git（SSH 10.0.12.42） |
| 分析基线 T480 | mcu_app_tda4@origin/release/Chery/T1LFL1_D073/T480@9e263465（2026-10-20） | git（SSH 10.0.12.42） |
| 失败测试固件 | **未知（无单据，未附构建包名/日期）** | 口头报告 |
| 历史失败包参照 | OTA-tda4_1100-...-T480-iDC_default_package-14053_**20260911**1058058.zip（D1CYC-1516，构建于修复合入前） | D1CYC-1516 附件 |
| 硬件/测试环境 | HIL（历史单同款测试） | 推断 |

### 1.4 分析输入与基线

| 输入 | 来源 | 说明 |
| :--- | :--- | :--- |
| 复现步骤/现象 | 用户口头传达 | §1.2 原样摘录 |
| 附件 | 无 | 无问题单 |
| 评论补充 | 无 | 无问题单 |
| 分析基线 | V1 工作区（01_Workspace_TDA4）+ origin 两分支 tip | 纯源码层面核查，未编译/未上台架 |

---

## 二、 复现性与数据回放 (Reproducibility & Replay)

### 2.1 可复现性

| 复现率 | 条件 | 样本 |
| :--- | :--- | :--- |
| 本次未复现（无环境/无固件信息） | — | 本次分析仅做源码层核查 |
| 历史同源问题：必现（HIL，2026-09-11 包） | 功能寻址 0x7DF 发 22 F1 90 | D1CYC-1516 |

* **首次/末次出现**：历史问题 2026-09-11 包必现 → 2026-09-22 修复后台架手动验证通过（功能寻址无响应 OK）→ 本次口头复测报告再现（固件版本未知）。

### 2.2 现象固定与回放

* 无本次失败的第一手证据（无单、无 BLF/trace、无包名）。历史 D1CYC-1516 证据（trace/log/规范表截图）存于 Obsidian assets 目录，见历史笔记。

---

## 三、 根因分析 (Root Cause Analysis)

### 3.1 知识召回（看代码之前先做）

| 检索源 | 关键词 | 结果 |
| :--- | :--- | :--- |
| Obsidian Work Database | T1LFL1 / F190 | **命中**：《T1LFL1 Fix dem ec error and 22 function address bug》（D1CYC-1615，2026-09-22 修复同源问题并验证通过） |
| `docs/analysis/` | F190 / T1LFL1 | 无直接命中（D1CYC-1615 当年未单独沉淀 analysis 报告，结论在笔记内） |
| `docs/design/` | T1LFL1 | 命中 D1CYC-2381（T1N FL3 车型新增，与本题无关） |

### 3.2 排查过程（假设-验证-排除链）

| # | 假设 | 验证手段 | 结果 |
| :--- | :--- | :--- | :--- |
| 1 | 修复被后续提交覆盖/回归 | `git log origin/develop / origin/T480 -- <ov_dia_notification.cpp>` 文件级历史：develop tip 为修复 commit ae1b9c64，T480 tip 为 d381d896，其后**无任何提交改动该文件**；`git show <tip>:<file>` 确认两分支 tip 文件内容均含功能寻址拒绝逻辑（147-151 行） | **排除** |
| 2 | Dcm 生成配置变更导致 callout 失联 | `git log --since=2026-09-23 -- cpj_chery/veh_t1lfl1/microsar_cfg/`：仅 DBC v4.3 导入与 CAN FIFO/滤波 3 笔，`GenData/Dcm_Lcfg.c` 自 initial commit 后零改动；`components/microsar/` 修复合入后零改动 | **排除** |
| 3 | `DCM_E_REQUEST_NOT_ACCEPTED` 机制本身无效（仍回正响应） | 走读 Vector Dcm：`Dcm_DiagExecIndicationFunc` 收到该返回值置 `DoSuppressResponse = TRUE`（Dcm.c:39046-39048），响应被抑制；callout 注册于 `Dcm_CfgDiagSysNotificationInfo[2]`（Dcm_Lcfg.c:637-641），服务分发前调用（Dcm.c:23674）；且 2026-09-22 用户台架手动验证通过 | **排除** |
| 4 | 失败测试固件不含修复（旧包/旧流水线基线） | 无单据无法直接证实；但历史失败包构建于 2026-09-11（修复合入 2026-09-23 前两天），源码三链路全部排除后仅剩此解释 | **最可能（未证实）** |

### 3.3 5 Whys 深挖

| 层级 | 提问 | 回答 |
| :--- | :--- | :--- |
| Why 1 | 为什么功能寻址 22 F1 90 收到正响应？ | 测试固件的运行行为与"含修复源码"不一致——含修复固件在机制上不可能回正响应（§3.2 #3） |
| Why 2 | 为什么不一致？ | 最可能：测试固件构建于 2026-09-23（PR #371/#372 合入）之前，或构建基线分支不含修复 |
| Why 3 | 为什么测试会用不含修复的固件？ | 复测报告无单据、未附构建包名/日期，无法核对固件版本 |
| Why 4 | 为什么版本核对环节缺失？ | 测试报告流转未强制携带固件版本信息（流程缺口，本次只能靠源码反证） |

### 3.4 根因与依据

* **根因**：环境类——失败测试所用固件疑似构建于修复合入（2026-09-23）之前；当前 develop/T480 源码中修复完整在位，非源码缺陷。
* **根因分类**：环境
* **代码依据**：`cpj_chery/veh_t1lfl1/dia_cfg/src/ov_dia_notification/ov_dia_notification.cpp:147-151`（0x22 功能寻址返回 `DCM_E_REQUEST_NOT_ACCEPTED`，两分支 tip 已验证）；`components/microsar/.../Dcm.c:39046-39048`（该返回值触发 `DoSuppressResponse=TRUE` 抑制响应）；`GenData/Dcm_Lcfg.c:637-641`（callout 注册）
* **责任归属**：非本模块缺陷；疑为测试固件版本管理/报告信息缺失问题

### 3.5 影响范围评估

* 仅涉及测试版本核对，无代码波及；T1LFL1 之外的变体（veh_t1jfl3 等）不涉及本现象。

---

## 四、 分析结论与分流 (Conclusion & Ttriage)

**不是问题（暂定）**：与 D1CYC-1516 同源的问题已于 D1CYC-1615 修复（PR #371→develop / #372→T480，2026-09-23 合并），当前两分支 tip 修复代码与 Dcm 抑制机制链路全部核查在位，无任何回归迹象。暂定结论：失败测试用的是不含修复的旧固件。

**遗留疑点**（结论为"暂定"的原因）：失败测试的构建包名/日期未知。**若测试方使用 2026-09-23 之后构建的包复测仍失败，此结论作废重开**——届时需拿到失败包名定位对应 commit 再进根因收敛。

---

## 五、 修复方案（仅"是问题"）

不适用（不是问题）。

## 六、 验证结果（仅"是问题"）

不适用（不是问题）。本次为源码层核查：origin/develop@c255b911 与 origin/release/Chery/T1LFL1_D073/T480@9e263465 两 tip 内容验证，未编译/未上台架。

---

## 七、 关闭与生命周期 (Closure & Lifecycle)

### 7.1 可复用结论

* 关键词检索路径：`F190 / 功能寻址 / 0x7DF / 22 F1 90 / T1LFL1` → 本篇 + Obsidian《T1LFL1 Fix dem ec error and 22 function address bug》。同现象再来：先核对测试固件构建日期是否 ≥ 2026-09-23，再查 `ov_dia_notification.cpp:147` 修复在位性。

### 7.2 缺陷生命周期记录

| 状态 | 日期 | 操作人 | 备注 |
| :--- | :--- | :--- | :--- |
| 发现（口头报告，无单） | 2026-10-27 | 测试方（未具名） | 描述与 D1CYC-1516 一致 |
| 分析开始 | 2026-10-28 | @Hua.Yao | 知识召回命中 D1CYC-1615 |
| 定性确认 | 2026-10-28 | @Hua.Yao | 用户确认"暂定不是问题" |
| 关闭 | 2026-10-28 | — | 无问题单，无 JIRA 流转；遗留疑点见 §四 |

---

## 附录：原始证据

* 源码核查证据（git 命令输出摘录）：
  * `git log origin/develop -- .../ov_dia_notification.cpp` → `ae1b9c64 feat(dia_cfg): [D1CYC-1615] ... 0x22 functional addressing`（该文件最后改动）
  * `git log origin/release/Chery/T1LFL1_D073/T480 -- .../ov_dia_notification.cpp` → `d381d896`（同上）
  * `git show origin/develop:<file>` / `git show origin/T480:<file>` → 147-151 行均含 `ReqType == DCM_FUNCTIONAL_REQUEST → DCM_E_REQUEST_NOT_ACCEPTED`
  * 修复合入时间：PR #371 merge bf696316（2026-09-23 10:30）、PR #372 merge f1960f92（2026-09-23 10:30）
* 历史证据（D1CYC-1516）：trace/log/规范表截图存 Obsidian `Work Database/assets/T1LFL1 Fix dem ec error and 22 function address bug/`
