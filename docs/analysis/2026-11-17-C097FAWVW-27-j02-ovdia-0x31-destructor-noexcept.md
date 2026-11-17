# 🐞 [C097FAWVW-27 - J02 编译失败：ov_dia 0x31 RID handler 析构异常规范不一致] 问题分析报告

| 文档基础属性 | 内容说明 | 分析与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **问题单号** | C097FAWVW-27 | **分析结论** | 🟢 是问题(转正式开发) |
| **问题主题** | J02 release 构建中断：veh_j02 诊断 RID handler 派生类虚析构缺 noexcept 触发 GHS #766-D | **缺陷类型** | 集成 |
| **分析人 / 日期** | @Hua.Yao / `2026-11-17` | **严重等级** | S3 一般(阻塞 CI 集成，不影响已发布功能) |
| **项目 / 变体** | J02 (C097FAWVW / FAWVW) | **优先级** | P3 中(与 JIRA severity B 对齐) |
| **发现阶段** | CI 集成构建(FAWVW/J02_C097/develop_qnx) | **分析状态** | 🔵 已修复(PR 待合并) |
| **根因分类** | 编码 | **关联输出** | 🔗 JIRA 问题单 C097FAWVW-27 ｜ 📄 修复 Story C097FAWVW-28 ｜ 📋 Obsidian 分析笔记 |

> **📝 变更记录**
> * `2026-11-17`｜@Hua.Yao｜V1.0｜初版：现象固定与根因分析
> * `2026-11-17`｜@Hua.Yao｜V1.1｜修复提交(PR #451)，验证改为 CI 编译路径

---

## 一、 缺陷概述 (Defect Summary)

### 1.1 问题描述

> J02（FAWVW C097）release 集成构建（GHS ghs-202414 工具链，warnings-as-errors）在编译 `cpj_fawvw/veh_j02/dia_cfg` 时失败：`ov_dia_0x31_routine_by_identifier_handler.hpp` 中 `CEOLCalibration`/`CAftermarketCalibration` 两个派生类虚析构未声明 `noexcept`，与基类析构链（全程 `noexcept`）异常规范不兼容，GHS 警告 #766-D 被升级为错误，构建中断（RETCODE 2）。

### 1.2 现象与复现(原样摘录)

**复现步骤**(原样，来自问题单 customfield_12007):

> Reproduce: trigger a CI build on J02_C097/develop_qnx (build task #1584595, https://ci.imotion.ai/task/1584595/detail) — mcu_app_j6_v2 fails with RETCODE 2.
>
> 1. Compiling veh_j02/dia_cfg emits warning #766-D at ov_dia_0x31_routine_by_identifier_handler.hpp:313-314: virtual destructor exception specification of CEOLCalibration / CAftermarketCalibration is incompatible with that of base classes (idia::ICRoutineandIOControl, idia::CRoutineControl, ov_dia::CCusRoutineControl).
> 2. The dia_cfg build treats warnings as errors, so the build aborts.
> 3. Introduced by commit 9817e98eaf which changed the inheritance of these derived classes.

**期望行为**：构建完成，无 #766-D 警告；派生类析构与基类析构异常规范一致。
**实际行为**：#766-D 升级为错误，mcu_app_j6_v2 构建失败（RETCODE 2）。

⚠️ 原单描述第 3 点归因不准确（见 §3.2 排查链 #1/#2）：9817e98eaf 未改动该 hpp。

### 1.3 环境矩阵

| 项 | 版本/值 | 来源 |
| :--- | :--- | :--- |
| 固件版本 / commit | mcu_app_j6_v2@develop@9817e98eafb6（CI 快照） | CI 任务 #1584595 detail |
| 构建配置 | FAWVW/J02_C097/develop_qnx，release | CI build_template 922 |
| 平台/工具链 | GAC/AY7_D066/armv8-r-generic/ghs202414-linux-20250922（docker ubuntu:22.04） | CI build_platform |
| 测试环境 | CI 构建机（非台架） | CI |
| 软件依赖 | zos_msg / version_did 等 @ develop | CI snapshot |

### 1.4 分析输入与基线

| 输入 | 来源 | 说明 |
| :--- | :--- | :--- |
| 复现步骤/现象 | 问题单 customfield_12007 | 原样摘录于 §1.2 |
| 附件 | 问题单 attachment | 无 |
| 评论补充 | 问题单 comment | 无（单据创建当日即分析） |
| 分析基线 | V2 工作区 | mcu_app_j6_v2@develop@85edafa53（缺陷在位）→ feature/C097FAWVW-28-j02-fix-ovdia-0x31-destructor-noexcept |

---

## 二、 复现性与数据回放 (Reproducibility & Replay)

### 2.1 可复现性

| 复现率 | 条件 | 样本 |
| :--- | :--- | :--- |
| 每次必现 | J02_C097 develop 分支 GHS 构建含该头文件即触发 | CI #1584595 一例；代码不一致静态可证 |

* **首次/末次出现**：2026-11-17 09:18 PR #448 合入后首个 J02 CI 构建暴露；develop HEAD（85edafa53）仍存在。

### 2.2 现象固定与回放

* **异常发生时的软硬件状态**：CI 构建编译 `veh_j02/dia_cfg` 时报 #766-D → warnings-as-errors 中断。GHS 编译器对虚函数覆盖的异常规范（exception specification）不一致发 #766-D 警告，工程把该警告升级为错误。
* **报文/时序回放**：不适用（编译期问题）。

---

## 三、 根因分析 (Root Cause Analysis)

### 3.1 知识召回(看代码之前先做)

| 检索源 | 关键词 | 结果 |
| :--- | :--- | :--- |
| `docs/analysis/` 历史个案 | 766 / noexcept | 无命中 |
| `docs/design/` 设计方案 | 766 / noexcept | 无命中 |
| Obsidian Work Database 笔记 | 766-D / noexcept | 无命中（仅本次新建笔记） |

### 3.2 排查过程(假设-验证-排除链)

| # | 假设 | 验证手段 | 结果 |
| :--- | :--- | :--- | :--- |
| 1 | 「9817e98eaf 新增继承/改动该 hpp 引入」（单据初判） | SSH `git show 9817e98eafb6 --stat`：该 merge 仅改 ads_ctrl 三文件；`git diff 5c445e352 9817e98eafb6 -- <hpp>` 为 0 行 | 排除——该 hpp 内容在 merge 前后完全一致 |
| 2 | 该 hpp 由更早 commit 引入即带缺陷 | `git log -- <hpp>`：引入于 d43d65273（IDC310GAC-7008，2026-09-30 诊断问卷导入），引入时析构即为 `~() {}` | 命中——缺陷出生点；9817e98eaf 只是触发首个覆盖该文件的 J02 CI 构建 |
| 3 | 基类侧 noexcept 来源 | `git log -S noexcept -- <idia 基类 hpp>`：9e741ef62（IDC510-6704 QAC 清理）给基类析构加 noexcept | 命中——两侧改动来自不同批次，汇合即冲突 |
| 4 | 析构链异常规范核实 | 在失败 commit 上逐级 `git show` + grep：`ICRoutineandIOControl() noexcept`(55) → `~CRoutineControl() noexcept override`(182) → `~CCusRoutineControl() noexcept override`(121)；派生类 276/314 行 `~() {}` | 命中——见 §3.4 |

### 3.3 5 Whys 深挖

| 层级 | 提问 | 回答 |
| :--- | :--- | :--- |
| Why 1 | 为什么编译失败？ | 派生类虚析构无 noexcept，覆盖 noexcept 基类析构，GHS #766-D + warnings-as-errors 中断 |
| Why 2 | 为什么派生类析构没有 noexcept？ | d43d65273 按问卷导入模板生成 RID 类时析构写成 `virtual ~XXX() {}`，未对齐基类风格 |
| Why 3 | 为什么基类有而派生类没有？ | 基类 noexcept 来自更早的 QAC 静态清理（IDC510-6704），两批改动出自不同项目/时间，无交叉检查 |
| Why 4 | 为什么评审/CI 没拦住？ | 该 hpp 合入（9-30）到首个 J02 GHS CI 构建覆盖（11-17）间隔近 7 周，缺陷潜伏到集成期才暴露 |
| Why 5 | 为什么潜伏这么久？ | J02 构建模板此前未覆盖 dia_cfg 新增目标，新文件合入后缺少即时构建反馈 |

### 3.4 根因与依据

* **根因**：`cpj_fawvw/veh_j02/dia_cfg/inc/ov_dia/0x31/ov_dia_0x31_routine_by_identifier_handler.hpp` 中 `CEOLCalibration`（276 行）与 `CAftermarketCalibration`（314 行）的虚析构声明为 `virtual ~XXX() {}`，未带 `noexcept`；其基类链 `idia::ICRoutineandIOControl → idia::CRoutineControl → ov_dia::CCusRoutineControl` 的析构全部为 `noexcept`。C++ 派生类虚函数覆盖的异常规范必须不宽于基类，GHS 检出不一致发 #766-D，工程 warnings-as-errors 使构建中断。
* **根因分类**：编码
* **代码依据**：失败 commit `9817e98eafb6` 上——派生类 `hpp:276,314`；基类 `components/idia/inc/idia/routine_io_control/idia_routine_io_control.hpp:55`、`components/idia/inc/idia/0x31/idia_0x31_routine_control_function.hpp:182`、同 hpp `:121`
* **责任归属**：本模块编码缺陷（问卷导入生成的 RID 类模板未对齐基类析构风格）

### 3.5 影响范围评估

* 同文件模式的其他变体副本（cpj_gac / cpj_gwm / cpj_honda 的同名 hpp）按最小补丁原则本次不同步；若其基类链同样带 noexcept 且走 GHS warnings-as-errors 构建，存在同型风险——待各自项目 CI 命中时按同方案处理。
* 编译期问题，无运行时功能影响，无实车风险。

---

## 四、 分析结论与分流 (Conclusion & Triage)

**是问题**：编码缺陷（派生类虚析构异常规范与基类不一致），阻塞 J02 develop 集成构建，需修复。已立项 Story C097FAWVW-28（is solved by C097FAWVW-27），在 V2 工作区 feature 分支完成修复交付。

---

## 五、 修复方案(仅"是问题") (Fix Plan)

### 5.1 纠正措施(Corrective Action,治此件)

| # | 修改点 | 文件 | 改动说明 | 风险评估 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `~CEOLCalibration` 加 `noexcept override` | `cpj_fawvw/veh_j02/dia_cfg/inc/ov_dia/0x31/ov_dia_0x31_routine_by_identifier_handler.hpp:276` | 与中间基类 `~CCusRoutineControl() noexcept override` 风格对齐 | 无行为变化（析构本就不可抛） |
| 2 | `~CAftermarketCalibration` 加 `noexcept override` | 同文件 `:314` | 同上 | 无行为变化 |

* **交接物**：V2 工作区 `mcu_app_j6_v2` 分支 `feature/C097FAWVW-28-j02-fix-ovdia-0x31-destructor-noexcept`，commit `40e8b56f1`
* **正式开发关联**：Story C097FAWVW-28 ｜ PR #451（bitbucket MCU/mcu_app_j6_v2）

### 5.2 预防措施(Preventive Action,治同类)

| # | 预防动作 | 落点 | 状态 |
| :--- | :--- | :--- | :--- |
| 1 | 诊断问卷导入生成的 RID 类析构模板对齐基类 `noexcept override` 风格 | 导入工具模板（zos 侧），后续导入需求时同步 | 待办（随下次导入需求处理） |
| 2 | 新增编译单元尽量随合入即时触发对应产品 CI 构建，缩短缺陷潜伏期 | 流程提醒，暂无强制手段 | 记录 |

---

## 六、 验证结果(仅"是问题") (Verification)

* **验证性修复(V2 工作区)**：
  * 编译：**验证路径调整**——本地不下载 GHS 交叉工具链（用户指定），A/B 对照改由 CI 承担：
    * 基线红：CI 任务 #1584595（同代码状态 9817e98eafb6、同 GHS 工具链）RETCODE 2——一手改前失败证据
    * 修复绿：PR #451 CI check 在 feature 分支（40e8b56f1）构建通过，bot_ci 审批通过（2026-11-17）——✅ 绿
  * 刷写：不适用（编译期问题，无固件行为变化）
  * 验证：通过标准 = feature 分支 CI 构建 RETCODE 0、无 #766-D
* **回归确认**：改动仅为异常规范声明，无运行时行为变化；CI 构建通过即覆盖编译回归
* **正式提交后验证**：PR 合并后 develop 构建（测试侧回归），待回填

---

## 七、 关闭与生命周期 (Closure & Lifecycle)

### 7.1 可复用结论

* GHS #766-D → 虚函数覆盖异常规范不一致：直接 diff 派生类与基类析构/虚函数声明的 `noexcept`；`git log -S noexcept` 可定位两侧引入批次
* CI 编译失败排障：先核 CI snapshot 的 commit 与失败文件 diff（`git diff <merge>^ <merge> -- <file>`），归因不能只看失败 merge 本身——本例失败 merge 并未改动失败文件

### 7.2 缺陷生命周期记录

| 状态 | 日期 | 操作人 | 备注 |
| :--- | :--- | :--- | :--- |
| 发现(报告) | 2026-11-17 | Hua.Yao | CI #1584595 排查后建 Problem C097FAWVW-27 |
| 分析开始 | 2026-11-17 | @Hua.Yao | V2 基线建立（develop@85edafa53） |
| 根因确认 | 2026-11-17 | @Hua.Yao | 用户确认定性：是问题 |
| 修复验证通过 | 2026-11-17 | @Hua.Yao | PR #451 CI 构建通过（bot_ci 审批），基线红/修复绿 A/B 成立 |
| 正式提交 | 2026-11-17 | @Hua.Yao | commit 40e8b56f1 / PR #451（当日合并） |
| 关闭 | 2026-11-17 | — | Problem 流转 Implemented（RCA+Bugfix 关联已填）；Story C097FAWVW-28 已解决 |

---

## 附录:原始证据

* CI 任务详情：https://ci.imotion.ai/task/1584595/detail（snapshot：mcu_app_j6_v2@9817e98eafb6）
* 失败 commit：`9817e98eafb69f4142c83ec25a43145023f5ebf5`（PR #448，仅改 ads_ctrl 三文件）
* 析构链 grep 输出（失败 commit）：`~CCusRoutineControl() noexcept override`:121、`~CEOLCalibration() {}`:276、`~CAftermarketCalibration() {}`:314；idia 基类 55/182 行 noexcept
* 修复 commit：`40e8b56f1`（feature/C097FAWVW-28-j02-fix-ovdia-0x31-destructor-noexcept，2 行 diff）
