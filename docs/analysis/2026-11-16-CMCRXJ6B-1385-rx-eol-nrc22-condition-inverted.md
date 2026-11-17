# 🐞 RX EOL 标定 0x31 FE01 误报 NRC22（判据方向写反）问题分析报告

| 文档基础属性 | 内容说明 | 分析与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **问题单号** | 无（飞书 wiki「RX标定报NRC22问题」+ 实车 asc 报文，用户 2026-11-16 口头立项） | **分析结论** | 🟢 是问题（直接修复） |
| **问题主题** | RX (CMC_RX_J6B) EOL 标定 `31 01 FE 01` 在条件信号全 0 时误回 NRC22 | **缺陷类型** | 功能（需求判据实现方向写反） |
| **分析人 / 日期** | Hua.Yao / Claude / `2026-11-16` | **严重等级** | S3 一般（EOL 标定流程被拦截，产线标定无法执行） |
| **项目 / 变体** | CMC_RX_J6B 一体机（仓库 `mcu_app_j6` / `cpj_cmc`，M 核诊断） | **优先级** | P2 高（阻塞 EOL 标定） |
| **发现阶段** | 实车测试（2026-11-13 asc 报文） | **分析状态** | 🔵 已修复（develop 直接提交） |
| **根因分类** | 设计（设计文档误读需求截图）+ 编码（忠实实现错误设计） | **关联输出** | 🔗 [CMCRXJ6B-1385](https://jira.imotion.ai:7070/browse/CMCRXJ6B-1385) ｜ 📄 [设计文档 V1.1](../design/2026-11-09-CMCRXJ6B-1385-rx-eol-fe01-nrc22-can-signal-condition-design.md) |

> **📝 变更记录**
> * `2026-11-16`｜Hua.Yao / Claude｜V1.0｜初版：asc 取证 + 根因 + 判据反修复

---

## 一、 缺陷概述 (Defect Summary)

### 1.1 问题描述

> RX EOL 标定例程在整车条件信号（远/近光、机盖、车门）**全部为 0（应放行）** 时，`31 01 FE 01` 返回 NRC22 (ConditionsNotCorrect)——条件判据方向与需求相反。

### 1.2 现象与复现(原样摘录)

**来源**：飞书 wiki `RX标定报NRC22问题`（node `HKZnw0hlBihNxJkWVWBcEDKTnhh`）附实车 CAN 报文 `can_20261113111607-2.asc`（12MB，119051 行）。

**诊断会话重建**（712 请求 / 713 响应，仅 18 帧诊断流量）：

| 时间 | 请求 | 响应 | 说明 |
| --- | --- | --- | --- |
| 6.91s | `10 03` | `50 03` | 进扩展会话 |
| 7.08s | `27 01` | `67 01` | 请求 seed |
| 7.20s | `27 02`+key | `67 02` | 安全解锁成功 |
| 7.33/7.45/7.58s | `31 01 FE 01` | **`7F 31 22` ×3** | EOL 标定被拒（本缺陷现象） |
| 7.70s | `11 01` | `7F 11 78`→`51 01` | ECU reset 正常 |
| 22.74s | `14 FF FF FF` | `7F 14 78`→`54` | 清 DTC 正常 |

**期望行为**：CMCRXJ6B-1385 需求原文——`HIBEAM_ON == 1 or LOBEAM_ON == 1 or HOOD_AJAR == 1 or BCM_PSG_AJAR == 1 or BCM_DRV_AJAR_PR == 1` → NRC22；五信号全 0 应放行（正响应）。
**实际行为**：五信号全 0 仍回 NRC22 ×3。

### 1.3 环境矩阵

| 项 | 版本/值 | 来源 |
| :--- | :--- | :--- |
| 固件基线 | mcu_app_j6@develop（含 CMCRXJ6B-1385 已合并实现） | 实车 2026-11-13 |
| 硬件 | CMC_RX_J6B 一体机实车 | asc 报文 |
| 测试环境 | 实车，CAN 总线记录（Vector asc 格式） | 飞书 wiki 附件 |
| 软件依赖 | Acore 标定许可链路（m_calibPermetFlag，本次未涉及） | — |

### 1.4 分析输入与基线

| 输入 | 来源 | 说明 |
| :--- | :--- | :--- |
| 复现步骤/现象 | 飞书 wiki 文章 | §1.2 时间线 |
| 附件 | asc 报文（wiki drive token `Ip81bVW6aoxSEHxagxiccX21nLb`） | 已留存 `.tmp/can_20261113111607-2.asc` |
| 评论补充 | 用户 2026-11-16 口头确认 | 「图上是报NRC22的条件，即1是要报NRC22」 |
| 分析基线 | V2 工作区 `02_Workspace_J6_V2/src/mcu_app_j6@develop` | 修复前代码 |

---

## 二、 复现性与数据回放 (Reproducibility & Replay)

### 2.1 可复现性

| 复现率 | 条件 | 样本 |
| :--- | :--- | :--- |
| 每次必现（判据性缺陷） | 五信号任一为 0（本次实车全程全 0） | asc 内 3 次尝试 3 次复现 |

* **首次/末次出现**：CMCRXJ6B-1385 实现合入 develop 起即存在；实车 2026-11-13 首次暴露。

### 2.2 现象固定与回放

* **报文信号解码**（按 `J6B_Com_EcucValues.arxml` 位位置，25s 全程采样）：

| 信号 | 报文 | 位位置 | 全程值 | 需求判据 |
| --- | --- | --- | --- | --- |
| HIBEAM_ON | 0x424 | bit50 | 恒 0（byte6=0x00） | ==1 → NRC22 |
| LOBEAM_ON | 0x424 | bit49 | 恒 0 | 同上 |
| HOOD_AJAR | 0x425 | bit14 | 恒 0 | 同上 |
| BCM_PSG_AJAR | 0x425 | bit10 | 恒 0 | 同上 |
| BCM_DRV_AJAR_PR | 0x315 | bit23 | 恒 0 | 同上 |

* 关键帧：`0x424 @7.583s: 98 84 04 01 8d 2d 00 00`（byte0=0x98→IG1 on，byte6=0x00→灯全灭）；`0x425: 00 00 02 10 00 00 00 00`；`0x315: 28 00 00 fd 89 00 00 00`。
* 佐证：安全访问解锁/ECU reset/清 DTC 均正常——链路无故障，唯 0x31 FE01 被条件检查拦截。

---

## 三、 根因分析 (Root Cause Analysis)

### 3.1 知识召回(看代码之前先做)

| 检索源 | 关键词 | 结果 |
| :--- | :--- | :--- |
| `docs/design/` | RX EOL NRC22 | **命中** `2026-11-09-CMCRXJ6B-1385-rx-eol-fe01-nrc22-can-signal-condition-design.md`（即本缺陷的源头设计） |
| `docs/analysis/` | NRC22 / EOL 标定 | 无命中 |
| Obsidian Work Database | RX 标定 | 无命中 |

### 3.2 排查过程(假设-验证-排除链)

| # | 假设 | 验证手段 | 结果 |
| :--- | :--- | :--- | :--- |
| 1 | 安全访问/会话未满足 → NRC22 | asc 会话重建：10 03 / 27 02 均成功 | 排除（回的是 22 不是 33/31） |
| 2 | m_calibPermetFlag=0（A 核未许可）| 代码走读 `m_validateNRC_22`（ov_dia_0x31_routine_by_identifier_handler.cpp:593 附近）| 排除——permetFlag=0 时直接放行不检查条件，报 NRC22 必经条件检查路径 |
| 3 | 五信号条件检查不通过 | asc 解码五信号 + 代码走读 `EolCalibrationCheckCondition()`（:452）| **命中**——五信号全 0，而实现为「任一 !=1 → fail」 |
| 4 | 需求判据方向确认 | 用户口头确认 wiki 截图 + JIRA CMCRXJ6B-1385 需求原文拉取 | **确认**：`== 1 → NRC22`（任一信号为 1 拦截），实现写反 |

### 3.3 5 Whys 深挖

| 层级 | 提问 | 回答 |
| :--- | :--- | :--- |
| Why 1 | 为什么五信号全 0 还报 NRC22？ | `EolCalibrationCheckCondition()` 实现为「任一信号 != 1 → CALI_FAILED → NRC22」 |
| Why 2 | 为什么实现成 != 1？ | 设计文档 V1.0（2026-11-09）将需求截图判据误读为「五信号全部=1 才放行」 |
| Why 3 | 为什么设计阶段会误读？ | 需求以截图形式给出条件表，「1 报 NRC22」的列语义在无原文比对时被反向理解 |
| Why 4 | 为什么评审/验证没拦住？ | 实现阶段仅编译验证，未做五信号双态（全 0 / 置 1）台架用例；条件类逻辑缺「边界态」验证 |
| Why 5 | — | 条件判据类需求的验证用例应包含判据两态各至少 1 例，已落预防措施 |

### 3.4 根因与依据

* **根因**：`cpj_cmc/dia_cfg/var/src/vehicle/rx/0x31/ov_dia_0x31_routine_by_identifier_handler.cpp` `EolCalibrationCheckCondition()`（:452 起）三处判据 `!= 1u` 应为 `== 1u`——需求判据「任一信号==1 → NRC22」被实现为「任一信号!=1 → NRC22」，方向相反。
* **根因分类**：设计（需求截图误读）+ 编码（继承错误设计）。
* **代码依据**：`EolCalibrationCheckCondition()` 三处 if/else-if；设计文档 §2.2/§3.1（V1.0 误读表述）；JIRA CMCRXJ6B-1385 description 需求原文。
* **责任归属**：本模块缺陷（设计与实现同源）。

### 3.5 影响范围评估

* **仅 RX（cpj_cmc/vehicle/rx）**：`EolCalibrationCheckCondition` 为 rx 变体专属文件；其他变体无此函数实现。0xFE00 售后标定不经过该函数，不受影响。
* 附带影响：误实现下五信号非全 1 的场景会**误写 Z022 标定失败记录 NVM**——修复后仅在真实条件满足（任一==1）时写。

---

## 四、 分析结论与分流 (Conclusion & Triage)

**是问题**：条件判据方向写反（设计误读 + 编码继承），五信号全 0 的合法标定场景被 NRC22 拦截 → 直接在 V2 工作区 develop 分支修复并上传（用户指示：暂无问题单，不走立项流程）。

---

## 五、 修复方案(仅"是问题") (Fix Plan)

### 5.1 纠正措施(Corrective Action,治此件)

| # | 修改点 | 文件 | 改动说明 | 风险评估 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 三处判据 `!= 1u` → `== 1u`，注释同步 | `cpj_cmc/dia_cfg/var/src/vehicle/rx/0x31/ov_dia_0x31_routine_by_identifier_handler.cpp`（EolCalibrationCheckCondition） | 判据方向取反：任一信号==1 → CALI_FAILED；全 0 放行 | 仅影响 0x31 FE01 条件检查路径；Z022 写入/成功路径结构不变 |

* **交接物**：V2 工作区 `02_Workspace_J6_V2/src/mcu_app_j6`，commit `075cd4ed1`（`[F4CMC-98]`，立项 Story 后按单号 amend）；develop 直推被 pre-receive 拒绝（develop 分支仅允许 PR 修改），feature 分支 [F4CMC-98-rx-eol-nrc22-condition-inverted](https://bitbucket.imotion.ai:7990/projects/MCU/repos/mcu_app_j6/pull-requests/2073) → PR #2073。立项：Story [F4CMC-98](https://jira.imotion.ai:7070/browse/F4CMC-98) implemented 关联需求单 CMCRXJ6B-1385。
* **设计文档**：`docs/design/2026-11-09-CMCRXJ6B-1385-...-design.md` 升 V1.1（判据方向、伪代码、验证方案全部修正，变更记录说明误读来源）。

### 5.2 预防措施(Preventive Action,治同类)

| # | 预防动作 | 落点 | 状态 |
| :--- | :--- | :--- | :--- |
| 1 | 条件判据类需求：设计文档必须附 JIRA/需求**原文引用**（不只截图转述），判据方向用「==X → 结果」显式句式 | 设计文档模板使用习惯 | 已在本案 V1.1 落实 |
| 2 | 条件类逻辑验证用例必须覆盖判据两态（全 0 放行 / 置 1 拦截）各至少 1 例 | 验证方案编写习惯 | 已在 §六 验证方案落实 |

---

## 六、 验证结果(仅"是问题") (Verification)

* **验证性修复(V2 工作区)**：
  * 编译：`CMC/RX_C088/develop` preset（2026-11-16，见状态更新）
  * 刷写验证：待台架（五信号全 0 → `31 01 FE 01` 应正响应；任一置 1 → NRC22）
* **回归确认**：0xFE00 售后标定、安全访问/会话检查不经本次修改路径，无影响。

---

## 七、 关闭与生命周期 (Closure & Lifecycle)

### 7.1 可复用结论

* **快速排查路径**：`31 01 FE 01` + NRC22 → 先看五信号实际值（asc 按 arxml 位位置解码）→ 对照 `EolCalibrationCheckCondition()` 判据方向（== 1 拦截，非 != 1）→ `m_validateNRC_22` 的 permetFlag=0 时直接放行不报 22。
* **经验**：需求以截图给出判据表时，「值=1 报 NRC22」类语义易被反向转述；设计文档落笔前先拉 JIRA description 原文比对。

### 7.2 缺陷生命周期记录

| 状态 | 日期 | 操作人 | 备注 |
| :--- | :--- | :--- | :--- |
| 发现(报告) | 2026-11-13 | 实车测试 | asc 报文记录于实车 |
| 分析开始 | 2026-11-16 | Hua.Yao / Claude | 飞书 wiki 立项，asc 会话重建 |
| 根因确认 | 2026-11-16 | Hua.Yao / Claude | 用户确认判据方向（1 → NRC22） |
| 修复验证通过 | 2026-11-16 | 用户 | 台架两态验证 OK（全 0 正响应 / 置 1 NRC22） |
| 正式提交 | 2026-11-16 | Hua.Yao / Claude | commit `075cd4ed1`（[F4CMC-98]），PR #2073 合并 develop（Lucas.Han/Xibin.Feng/bot_ci 全批） |
| 关闭 | 2026-11-16 | — | F4CMC-98 已流转已解决（JIRA 评论+两步流转），无独立问题单 |

---

## 附录:原始证据

* asc 报文：飞书 wiki 附件 `can_20261113111607-2.asc`（12MB），本地留存 `.tmp/can_20261113111607-2.asc`（会话内临时，证据要点已摘录 §1.2/§2.2）
* 需求原文（JIRA CMCRXJ6B-1385 description）：
  > 31 01 FE 01的NRC22条件：CAN信号
  > HIBEAM_ON == 1 or LOBEAM_ON == 1 or HOOD_AJAR == 1 or BCM_PSG_AJAR == 1 or BCM_DRV_AJAR_PR == 1
  > Note:对应报文 ETACS_OUT1(0x424) / ETACS_OUT2(0x425) / ETACS_OUT3(0x315)
* 信号位位置来源：`cpj_cmc/autosar/rx/BswRta/ecu_config/bsw/gen/J6B_Com_EcucValues.arxml`（ComBitPosition/ComBitSize）
