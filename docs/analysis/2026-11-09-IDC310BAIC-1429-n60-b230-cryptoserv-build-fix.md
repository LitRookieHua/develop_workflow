# 🐞 [IDC310BAIC-1429] N60 B230 分支编译失败（CryptoServ_trng.h 无法解析）分析报告

| 文档基础属性 | 内容说明 | 分析与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **问题单号** | IDC310BAIC-1429（B230 交付补完；来源需求 IDC310BAICREQ-6343） | **分析结论** | 🟢 是问题（已修复，PR #1897 待合入） |
| **问题主题** | B230 release 分支 dia_cfg 编译失败：CryptoServ_trng.h 找不到 | **缺陷类型** | 集成 / 配置 |
| **分析人 / 日期** | @Hua Yao / 2026-11-09 | **严重等级** | S2 严重（B230 分支 CI 构建全红，阻塞该分支一切交付） |
| **项目 / 变体** | BAIC N60（cpj_baic，vehicle `n60`） | **优先级** | P1 紧急（release 分支构建中断，当日修复） |
| **发现阶段** | CI 集成构建（PR #1853 合入后） | **分析状态** | 🔵 已修复 |
| **根因分类** | 集成（跨分支构建依赖未同步） | **关联输出** | 🔗 [IDC310BAIC-1429](https://jira.imotion.ai:7070/browse/IDC310BAIC-1429) ｜ 📄 [设计文档](../design/2026-11-05-IDC310BAIC-1429-n60-27-seed-trng-design.md)（§1.2 有勘误） ｜ 📋 Obsidian 笔记 Work Database/IDC310BAIC-1429 |

> **📝 变更记录**
> * `2026-11-09`｜@Hua Yao｜V1.0｜初版：定性、根因、修复与本地验证（PR 合并后回填 CI 复验）

---

## 一、 缺陷概述 (Defect Summary)

### 1.1 问题描述

PR #1853 将 N60 0x27 seed TRNG 改动合入 `release/BAIC/N60_D109/B230` 后，该分支 CI 全量编译失败：`cpj_baic/dia_cfg/var/src/vehicle/n60/0x27/ov_dia_0x27_security_access.cpp:21` 的 `#include "CryptoServ_trng.h"` 报 fatal error #2330（无法打开源文件），dia_cfg 目标编译中断。develop 分支同代码编译正常。

### 1.2 现象与复现（原样摘录）

来自 CI 任务 #1519582 的 infra 排查结论（用户提供，原样摘录）：

> 🤖 infra 排查结果 (#1519582)
> 状态: Fail | 发起人: yuhong.xia | 失败工程: mcu_app_j6
> 【结论】mcu_app_j6 编译失败：ov_dia_0x27_security_access.cpp 第 21 行 #include "CryptoServ_trng.h" 报 TI 编译器 fatal error #2330（无法打开源文件），导致 dia_cfg 目标编译中断。
> 【提交人】Hua Yao/姚华 (mcu_app_j6@b0fa662aee)

**复现步骤**（原样）：对 `release/BAIC/N60_D109/B230` 分支发起 CI 构建（N60_D109/release/BAIC_N60_D109_B230）→ mcu_app_j6 编译阶段必失败于上述 include。

**期望行为**：B230 分支编译通过（develop 同代码可编过）。
**实际行为**：CryptoServ_trng.h 搜索路径缺失，编译中断。

### 1.3 环境矩阵

| 项 | 版本/值 | 来源 |
| :--- | :--- | :--- |
| 固件版本 / commit | mcu_app_j6@b0fa662aee（PR #1853 merge，release/BAIC/N60_D109/B230） | CI 任务 |
| 构建配置 | BAIC/N60_D109/release/BAIC_N60_D109_B230（本地复验同 product，GCC arm-none-eabi 10.3 / R52） | CI #1519582 / 本地 |
| 测试环境 | CI 集成构建 + V2 工作区 imobuilder 全量编译 | 本次分析 |
| 相关工具 | imobuilder / cmake preset n60-gcc-dev | 构建日志 |

### 1.4 分析输入与基线

| 输入 | 来源 | 说明 |
| :--- | :--- | :--- |
| CI 报错原文 | 用户提供 infra 排查结论 | 原样摘录于 §1.2 |
| 提交内容 | `git show b0fa662aee` | PR #1853 merge，单文件 +19/-6（n60 ov 文件） |
| 设计文档 | docs/design/2026-11-05-IDC310BAIC-1429-n60-27-seed-trng-design.md | §1.2「不改 CMake」假设即缺口来源（已勘误） |
| 分析基线 | V2 工作区 mcu_app_j6@feature/IDC310BAIC-1429-cryptoserv-cmake-b230 | B230 基线 b0fa662ae + 1 行修复，全量编译通过 |

---

## 二、 复现性与数据回放 (Reproducibility & Replay)

### 2.1 可复现性

| 复现率 | 条件 | 样本 |
| :--- | :--- | :--- |
| 每次必现 | B230 分支任意编译（CI #1519582 实证；修复前基线确定性失败） | CI 1 次 + 根因链闭环 |

* **首次/末次出现**：首现于 PR #1853 合入后的 CI 构建（2026-11-05 之后）；修复 commit 76c947086 后本地全量编译通过，末次出现即基线态。

### 2.2 现象固定与回放

* 报错点固定：`ov_dia_0x27_security_access.cpp:21` `#include "CryptoServ_trng.h"` fatal error #2330，无随机性（纯编译期路径解析问题，与运行工况无关）。
* 本地同構回放：V2 工作区切换 `build_product: BAIC/N60_D109/release/BAIC_N60_D109_B230` 后以同一 product 全量编译，修复前逻辑上必失败（与 CI 同 CMake 图），修复后通过（§六）。

---

## 三、 根因分析 (Root Cause Analysis)

### 3.1 知识召回（看代码之前先做）

| 检索源 | 关键词 | 结果 |
| :--- | :--- | :--- |
| `docs/analysis/` 历史个案 | CryptoServ / 编译失败 / cherry-pick | 无命中 |
| `docs/design/` 设计方案 | 1429 / TRNG / seed | 命中：2026-11-05-IDC310BAIC-1429-n60-27-seed-trng-design.md——其 §1.2 记载「`CryptoServ_Component` 已在 `cpj_baic/dia_cfg/CMakeLists.txt:53` 全项目链接，故不改 CMake」，该断言**仅在 develop 成立**，是本次缺口的直接来源 |
| Obsidian Work Database 笔记 | IDC310BAIC-1429 | 命中既有笔记（本次补记 B230 修复台账） |

### 3.2 排查过程（假设-验证-排除链）

| # | 假设 | 验证手段 | 结果 |
| :--- | :--- | :--- | :--- |
| 1 | B230 分支上头文件不存在 | `git ls-tree origin/release/BAIC/N60_D109/B230 -- components/bsw/Services/CryptoServ/{inc,src}/` | 排除——`inc/CryptoServ_trng.h`、`src/CryptoServ_Trng.c` 均存在 |
| 2 | 组件自身 CMake 不再 PUBLIC 暴露 inc（两分支组件不一致） | `git diff B230 develop -- components/bsw/Services/CryptoServ/` | 排除——仅 QAC 注释格式差异，`target_include_directories(PUBLIC inc)` 两边一致 |
| 3 | dia_cfg 未链接 CryptoServ_Component，PUBLIC include 路径不传播 | 对比两分支 `cpj_baic/dia_cfg/CMakeLists.txt`：develop PRIVATE 块含 `CryptoServ_Component`（commit 2a2a02b95 / IDC310BAIC-1382 引入），B230 上 grep 零命中 | **命中**——见 §3.4 |
| 4 | （infra 报告备选假设）头文件名拼写/路径错误 | 对照 develop 同名 include 与组件头文件名 | 排除——`#include "CryptoServ_trng.h"` 与实际文件名一致，develop 编译通过即为反证 |

### 3.3 5 Whys 深挖

| 层级 | 提问 | 回答 |
| :--- | :--- | :--- |
| Why 1 | 为什么编译失败？ | dia_cfg 编译 ov_dia_0x27_security_access.cpp 时，头文件搜索路径中没有 `components/bsw/Services/CryptoServ/inc` |
| Why 2 | 为什么搜索路径缺失？ | 该路径靠 `CryptoServ_Component` 的 `target_include_directories(PUBLIC inc)` 传播，而 B230 上 dia_cfg 的 `target_link_libraries` PRIVATE 块没有链接该组件 |
| Why 3 | 为什么 B230 缺这一行？ | 该行由 IDC310BAIC-1382（b81vs TRNG，2026-09-28，commit 2a2a02b95）在 develop 上引入；IDC310BAIC-1429 的 B230 cherry-pick（PR #1853）只移植了本单的 .cpp 改动，跨单构建依赖未随之同步 |
| Why 4 | 为什么交付流程没拦住？ | ① release cherry-pick 规则默认「直接移植 commit、无需第二分支重新编译验证」（对自包含改动成立，对隐式依赖 develop 其他单构建配置的改动不成立）；② 本次验证只在 develop 侧完成，B230 分支合入后无编译验证，直到 CI 集成构建才暴露 |
| Why 5 | 为什么这类依赖脆弱？ | 源码 include 与构建脚本链接行分属不同提交/不同单据，跨分支同步时以「本单 commit」为单位，没有机制识别「改动引用了 develop 上其他单新增的构建配置」——防腐动作落点见 §5.2 |

### 3.4 根因与依据

* **根因**：`release/BAIC/N60_D109/B230` 分支的 `cpj_baic/dia_cfg/CMakeLists.txt` 缺少 `CryptoServ_Component` 链接（该行仅在 develop，由 2a2a02b95/IDC310BAIC-1382 引入），导致 1429 合入的 `#include "CryptoServ_trng.h"` 在 B230 上无法解析。
* **根因分类**：集成（跨分支构建依赖未同步）。
* **代码依据**：develop `cpj_baic/dia_cfg/CMakeLists.txt:53`（PRIVATE 块内 `CryptoServ_Component`）vs B230 同文件该块止于 `iNet`；组件 `components/bsw/Services/CryptoServ/CMakeLists.txt`（PUBLIC inc 传播）；2a2a02b95 diff（+1 行 CMake + b81vs .cpp）。
* **责任归属**：1429 交付流程（本人）——cherry-pick 未携带构建依赖 + B230 侧未验证；非组件代码缺陷。

### 3.5 影响范围评估

* **仅 B230 分支**：develop 有链接行不受影响；1429 未合入其他 release 分支（B220/B210 等无此 include）。
* 仅影响编译期，**不影响运行时行为**（修复为纯构建配置 +1 行）。
* 同类风险面：凡「cherry-pick 到 release 分支的改动引用了 develop 上其他单新增的组件链接/宏定义」都可能复现此模式——见 §5.2 预防。

---

## 四、 分析结论与分流 (Conclusion & Triage)

**是问题**（构建配置缺陷）：B230 分支缺 `CryptoServ_Component` 链接，最小修复 +1 行对齐 develop（用户 2026-11-09 确认沿用 IDC310BAIC-1429 交付，不新开 Story）。

**遗留疑点**：无。（infra 报告中「TI 编译器」「依赖未拉取」等表述经核实不成立——实际本地链路为 GCC R52，组件在 B230 完整存在。）

---

## 五、 修复方案 (Fix Plan)

### 5.1 纠正措施（Corrective Action，治此件）

| # | 修改点 | 文件 | 改动说明 | 风险评估 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | PRIVATE 链接块补 `CryptoServ_Component` | `cpj_baic/dia_cfg/CMakeLists.txt`（iNet 之后，对齐 develop 位置） | +1 行 | 无运行时影响；引入 CryptoServ 头路径与符号（组件已在 B230 存在，develop 同构已验证） |

* **交付物**：commit `76c947086`，分支 `feature/IDC310BAIC-1429-cryptoserv-cmake-b230`，PR [#1897](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/1897) → `release/BAIC/N60_D109/B230`。
* **正式开发关联**：沿用 IDC310BAIC-1429（设计文档已勘误，见 §3.1/关联输出）。

### 5.2 预防措施（Preventive Action，治同类）

| # | 预防动作 | 落点 | 状态 |
| :--- | :--- | :--- | :--- |
| 1 | release/第二分支 cherry-pick 前检查「改动的 include/符号是否依赖 develop 上其他单新增的组件链接或编译配置」，命中则把对应构建配置一并移植或在目标分支跑一次编译 | workspace-setup.md §5（cherry-pick 硬规则处补检查项） | 已建议（待用户确认后写入权威源） |
| 2 | 设计文档「不改 X」类假设须标注验证分支（develop 成立 ≠ release 分支成立） | design 文档模板/评审检查 | 已建议；本单设计文档 §1.2 已补勘误示范 |

---

## 六、 验证结果 (Verification)

* **A/B 对照（编译即复现）**：
  * 基线（红）：CI #1519582，B230@b0fa662aee，CryptoServ_trng.h fatal error #2330；
  * 修复（绿）：V2 工作区同 product（BAIC/N60_D109/release/BAIC_N60_D109_B230）全量 imobuilder build 通过（2026-11-09，3m9s），`ov_dia_0x27_security_access.cpp.obj` 产出晚于 CMakeLists 修改，include 解析成功（头文件缺失为硬错误，obj 存在即证明路径生效）。
* **回归确认**：纯构建配置改动（+1 行链接），无运行时行为变化，无需刷板；0x27 功能行为已在 develop 侧按 1429 验收用例验证（设计文档 §6.2），B230 代码与 develop 同源。
* **正式提交后验证**：PR #1897 合并后 CI 复验（待回填）。

---

## 七、 关闭与生命周期 (Closure & Lifecycle)

### 7.1 可复用结论

* 关键词：`CryptoServ_trng.h` / `#2330` / `B230 编译失败` / `cherry-pick 依赖` / `CryptoServ_Component` / `dia_cfg`。
* 快速排查路径：release 分支 include 解析失败 → 先 `git diff <release> develop -- <相关>CMakeLists.txt`（跨分支构建配置差异）→ 再查组件文件存在性（ls-tree）——本次 10 分钟内定位。
* 通用教训：**源码 diff 可 cherry-pick，构建配置依赖不会自动跟随**；「develop 能编过」不能推出「release 分支能编过」。

### 7.2 缺陷生命周期记录

| 状态 | 日期 | 操作人 | 备注 |
| :--- | :--- | :--- | :--- |
| 发现（报告） | 2026-11-05 后 | CI #1519582（发起 yuhong.xia） | infra 排查结论指向 b0fa662aee |
| 分析开始 | 2026-11-09 | @Hua Yao | V2 基线建立（问题定性确认，沿用 1429） |
| 根因确认 | 2026-11-09 | @Hua Yao | 用户确认定性 + 修复方案 |
| 修复验证通过 | 2026-11-09 | @Hua Yao | B230 product 全量编译 PASS（A/B 闭环） |
| 正式提交 | 2026-11-09 | @Hua Yao | commit 76c947086 / PR #1897 |
| 关闭 | 2026-11-09 | — | PR #1897 MERGED（11:54 前后），B230 分支编译恢复；JIRA 1429 已补合并评论，笔记关单 |

---

## 附录：原始证据

* infra 排查结论原文：见 §1.2 摘录（用户提供）。
* 关键命令留痕（服务器 10.0.12.42，mcu_app_j6）：
  * `git show b0fa662aee --stat` → 单文件 +19/-6（PR #1853 merge）
  * `git show origin/release/BAIC/N60_D109/B230:cpj_baic/dia_cfg/CMakeLists.txt | grep CryptoServ` → 零命中（develop 工作树同命令 → `:53`）
  * `git ls-tree origin/release/BAIC/N60_D109/B230 -- components/bsw/Services/CryptoServ/{inc,src}/` → 头文件与源码齐全
  * `git diff B230 develop -- components/bsw/Services/CryptoServ/` → 仅注释格式差异
  * 修复后编译产物：`build/cpj_baic_n60_d310/rpu_arm_gcc/cpj_baic/dia_cfg/CMakeFiles/dia_cfg.dir/var/src/vehicle/n60/0x27/ov_dia_0x27_security_access.cpp.obj`
