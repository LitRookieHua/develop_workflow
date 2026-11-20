# ⚙️ RX EOL 标定 0x31 FE01 NRC22 条件（CAN 信号）需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | Dcm 0x31 RoutineControl FE01 EOL 标定 NRC22 前置条件 | **所属软件层级** | 诊断应用层（ov_dia / dia_cfg） |
| **文档状态** | 🟡 待评审 | **安全与质量要求** | MISRA C:2012 ｜ 零警告 |
| **模块负责人 / 作者** | Hua.Yao / Claude | **关联输入/输出** | 📑 [CMCRXJ6B-1385](https://jira.imotion.ai:7070/browse/CMCRXJ6B-1385) |

> **📝 变更记录**
> * `2026-11-09`｜Hua.Yao / Claude｜V1.0｜初版：NRC22 条件改为 CAN 信号判据
> * `2026-11-16`｜Hua.Yao / Claude｜V1.1｜**修正判据方向**：V1.0 将需求截图误读为「五信号全部=1 才放行」，实为「任一信号==1 → NRC22，全部==0 才放行」（JIRA 需求原文确认）；实车 asc 报文复现该误实现（五信号全 0 仍回 NRC22），develop 修复
> * `2026-11-18`｜Hua.Yao / Claude｜V1.2｜**需求变更收敛**（JIRA 评论 2026-11-17 Jason.Yu）：删除车门两信号条件——`ETACS_OUT3(0x315) BCM_DRV_AJAR_PR`、`ETACS_OUT2(0x425) BCM_PSG_AJAR`；NRC22 判据由五信号收敛为三信号（HIBEAM_ON / LOBEAM_ON / HOOD_AJAR），判据方向（==1 → NRC22）不变

> 本需求为单文件小改动（条件判断逻辑填充），按模板精简规则省略部分详细设计小节，追溯见 JIRA。

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景**：RX (CMC_RX_J6B) 项目 EOL 标定例程（0x31 RID 0xFE01）启动前需校验整车状态。当前 `EolCalibrationCheckCondition()` 中所有条件检查均被注释（历史移植自其他项目的车门/灯光/挡位检查，信号结构不适配 RX），条件检查形同虚设——任何状态下 `31 01 FE 01` 都不会因条件不满足返回 NRC22。
* **核心目标**：按需求单 CMCRXJ6B-1385（2026-11-17 变更后），NRC22 条件基于本车实际 CAN 信号判定：任一条件信号为 1 即 `31 01 FE 01` 返回 NRC22 (ConditionsNotCorrect)；三信号（HIBEAM_ON / LOBEAM_ON / HOOD_AJAR）全部为 0 才放行标定，车门信号不参与判据。
* **设计原则**：只填充现有检查函数的条件体，复用既有 valin_cfg 信号结构（`g_CAN0_ETACS_OUT*_st`），不新增模块、不改 Dcm 配置。

### 1.2 适用范围 (Scope)

* **适用控制器/平台**：CMC_RX_J6B 一体机（J6 平台，仓库 `mcu_app_j6` / `cpj_cmc`，M 核诊断）
* **范围边界**：仅改 `dia_cfg/var/src/vehicle/rx/0x31/ov_dia_0x31_routine_by_identifier_handler.cpp` 的 `EolCalibrationCheckCondition()`（及必要的 include）；不涉及 0xFE00 售后标定、Dcm BSW 配置、NVM、autosar 重生成。

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | [CMCRXJ6B-1385 EOL标定NRC22条件](https://jira.imotion.ai:7070/browse/CMCRXJ6B-1385) | — | 需求来源（信号与报文映射） |
| R2 | ISO 14229-1 (UDS) | 2020 | NRC 0x22 ConditionsNotCorrect 语义 |

### 1.5 设计约束与假设

* **技术约束**：代码修改一律 SSH 在 10.0.12.42 服务器执行（scp 推送），Y: 盘禁止写源码；MISRA / 零警告。
* **外部假设**：三条 ETACS 报文（0x424/0x425/0x315）在 EOL 场景由台架/BCM 正常发出，信号已由 Com → NetCom 链路写入 `g_CAN0_ETACS_OUT*_st`（`NetCom_Notification_Can.cpp` 既有序列）。

---

## 二、 架构设计与模块间交互 (Architecture & Interaction)

### 2.1 调用链（条件检查位置）

```text
Tester: 31 01 FE 01 (EOL 标定启动)
  → Dcm 0x31 dispatcher → CEOLCalibration::m_validateNRC_22()
      → m_calibPermetFlag == 1 (A 核标定许可, 既有逻辑保留)
      → EolCalibrationCheckCondition()   ← 本次唯一修改点
          → 读 g_CAN0_ETACS_OUT1/2/3_st 信号
          → 任一条件不满足 → NRC22 (E_CONDITIONS_NOT_CORRECT)
  → 通过后 m_excuteStartCustomer → DiaCalibrationManager IPC → A 核标定
```

### 2.2 需求信号映射（R1 原文整理，V1.2 变更后）

| 条件信号 | 所属报文 | 全局结构（valin_cfg） | 判据 | V1.2 状态 |
| :--- | :--- | :--- | :--- | :--- |
| `HIBEAM_ON` | ETACS_OUT1 (0x424) | `g_CAN0_ETACS_OUT1_st.HIBEAM_ON_u8` | == 1 → fail | 保留 |
| `LOBEAM_ON` | ETACS_OUT1 (0x424) | `g_CAN0_ETACS_OUT1_st.LOBEAM_ON_u8` | == 1 → fail | 保留 |
| `HOOD_AJAR` | ETACS_OUT2 (0x425) | `g_CAN0_ETACS_OUT2_st.HOOD_AJAR_u8` | == 1 → fail | 保留 |
| `BCM_PSG_AJAR` | ETACS_OUT2 (0x425) | `g_CAN0_ETACS_OUT2_st.BCM_PSG_AJAR_u8` | ~~== 1 → fail~~ | **删除（V1.2）** |
| `BCM_DRV_AJAR_PR` | ETACS_OUT3 (0x315) | `g_CAN0_ETACS_OUT3_st.BCM_DRV_AJAR_PR_u8` | ~~== 1 → fail~~ | **删除（V1.2）** |

需求语义（JIRA CMCRXJ6B-1385 需求原文，2026-11-17 变更后）：`HIBEAM_ON == 1 or LOBEAM_ON == 1 or HOOD_AJAR == 1` → NRC22；即三信号任一为 1（远/近光开启、机盖开）拦截标定，全部为 0 才放行。

> 变更依据：JIRA CMCRXJ6B-1385 评论（2026-11-17，Jason.Yu）：「需求变更删除 ETACS_OUT3(0x315) BCM_DRV_AJAR_PR == 1 和 ETACS_OUT2(0x425) BCM_PSG_AJAR == 1 的条件检查」。变更后需求单 Note 只列 0x424（HIBEAM_ON/LOBEAM_ON）与 0x425（HOOD_AJAR）——车门信号完全退出判据，0x315 报文不再参与。历史（V1.0 误读为 AND 放行 → V1.1 修正 OR 拦截）见变更记录。

### 2.3 并发与调度上下文

`m_validateNRC_22` 在 Dcm 诊断请求处理上下文执行（与 `NetCom_Notification_Can.cpp` 的 Com 通知上下文不同）。单字节读取无撕裂风险，与库内既有用法（`ov_diaRunnable.cpp` 直接读 `g_CAN0_BS_328h_st`）一致，无需临界区。

---

## 三、 核心逻辑设计

### 3.1 条件判断伪代码

```text
EolCalibrationCheckCondition():   # V1.2：三信号判据
  if HIBEAM_ON == 1 or LOBEAM_ON == 1        → l_failedReason = CALI_FAILED
  else if HOOD_AJAR == 1                     → l_failedReason = CALI_FAILED

  if l_failedReason != 0:
      沿既有失败路径写 Z022 (CALI_FAILED_REASON) → return Failure
  return Success
```

* 失败原因码：三项条件共用 `CALI_FAILED (0x03)`（需求未定义细分原因码；沿用函数既有失败路径与 Z022 写入行为）。
* V1.2 变更实现方式：在现网 `== 1u` 判据基础上删除 `BCM_PSG_AJAR`、`BCM_DRV_AJAR_PR` 两处检查分支（含 0x315 头文件引用若因此不再使用则一并清理）；判据方向与失败路径结构不变。
* 保留既有 `m_calibPermetFlag == 1` 前置检查（A 核标定许可）不变。

### 3.2 修改点清单（附录）

| # | 文件 | 修改 |
| :--- | :--- | :--- |
| 1 | `cpj_cmc/dia_cfg/var/src/vehicle/rx/0x31/ov_dia_0x31_routine_by_identifier_handler.cpp` | `EolCalibrationCheckCondition()` 删除 `BCM_PSG_AJAR`、`BCM_DRV_AJAR_PR` 条件分支（V1.2 需求变更收敛为三信号） |

---

## 六、 验证方案

* 诊断仪（DiagnosticTester）或台架 EOL 流程验证（V1.2 三信号判据）：
  1. 三信号全部为 0（车门开/关任意状态，车门已不参与判据）→ `31 01 FE 01` 正响应（0x71 01 FE 01）
  2. 逐项置 1（如开启近光/打开机盖）→ NRC22
  3. **车门信号回归**：`BCM_PSG_AJAR` / `BCM_DRV_AJAR_PR` 置 1（其余三信号全 0）→ 仍应正响应（确认车门条件已彻底退出）
  4. 回归：安全访问/会话（NRC31/33）、售后标定 0xFE00 不受影响
* J6 刷写后用户手动台架验证（阶段 4）。

## 附录B：ADR 摘要

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | 直接读 `g_CAN0_ETACS_OUT*_st` 全局结构 | Com_ReceiveSignal(ComConf_ComSignal...) | dia_cfg 内既有先例（ov_diaRunnable.cpp GetVehicleSpeed）即直接读全局结构；valin_cfg_net_cbk.hpp 已被本文件 include |
| 2 | 条件共用 CALI_FAILED 0x03（V1.2 起为三信号） | 每条件独立原因码 | 需求单只要求 NRC22 拒绝，未定义细分原因码；失败路径沿用函数既有 Z022 写序列 |
| 3 | 不改 m_validateNRC_22 的 permetFlag 结构 | 重构前置检查 | 最小改动原则——只填充空的条件检查函数 |
