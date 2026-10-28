# 📝 T1LFL1 Add T1NFL3 vehicle 详细设计

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | T1LFL1 平台新增 T1NFL3 车型（配置字 + versionDID） | **所属系统/服务** | mcu_app_tda4（TDA4 老工作区，Chery/T1LFL1_D073） |
| **文档状态** | 🟡 待评审 | **安全与质量要求** | 常规配置新增，无安全影响 |
| **负责人 / 作者** | Hua.Yao | **关联输入/输出** | 📋 [T1LFL1-477](https://jira.imotion.ai:7070/browse/T1LFL1-477) ｜ [D1CYC-2381](https://jira.imotion.ai:7070/browse/D1CYC-2381) |

> **📝 变更记录 (Revision History)**
> * `2026-10-22`｜Hua.Yao｜V1.0｜初始设计（复用 T1NFL5 先例 D1CYC-1260 模式）

> **📋 模板使用说明**：本需求为配置数据新增（3 仓库约 20 行），按模板精简规则省略四、详细设计中不涉及的小节与附录 A 追溯矩阵（需求仅涉及车型配置字新增，追溯见 JIRA T1LFL1-477）。

---

## 一、 概述 (Overview)

### 1.1 功能背景与业务/技术目标

* **背景**：T1LFL1 平台（D073）新增 T1N FL3 车型。来源需求 T1LFL1-477 于 2026-10-21 更新描述，新增 T1N FL3 段落：F187 零件号 704002931AA，F188 00.00.01，F191 0.0.1，车型配置字 0x0153。
* **核心目标**：
  1. zos_msg 车型枚举新增 `VEH_Chery_T1NFL3_FUEL_EX = 0x0153`
  2. versionDID 数据表新增 T1N FL3 的 F187/F188/F191 条目
  3. MCU 0x22 服务 F187/F188/F191 按 NVM 内部车型配置字返回 T1N FL3 对应数据；T1NFL3 **不 mapping 客户配置字**，内部配置字 0x0153 原样发给 System Manager
* **设计原则**：完全复用 T1NFL5（D1CYC-1260，0x0152）已验证模式，仅数据行新增，无逻辑变更。

### 1.2 适用范围 (Scope)

* **适用模块**：zos_msg（枚举 IDL）、version_did（DID 数据模板）、mcu_app_tda4 `cpj_chery/veh_t1lfl1`（0x22 handler + deliverVehicleConfig）
* **范围边界**：uss_app_tda4 的 T1NFL3 项目适配**不在本 Story 范围**（T1NFL5 先例为独立 Story D1CYC-1533）；不涉及任何客户配置字 D009 mapping 逻辑变更。

### 1.3 术语与缩略语

| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| F187/F188/F191 | DID 0xF187/0xF188/0xF191 | 零件号 / 软件版本号 / 硬件版本号 |
| 2A1E | 内部车型配置字 DID | NVM `NVM_PDM_InternalCoding`，确定内部车型（含 m_vehicleVariant） |
| D009 | 客户配置字 | 客户写入的整车配置字，优先级高于 2A1E（T1LFL1-475） |
| FUEL_EX | 燃油出口版 | T1N FL3/FL5 车型动力类型，不做客户配置字 mapping |

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | [T1LFL1-477](https://jira.imotion.ai:7070/browse/T1LFL1-477) | 2026-10-21 描述 | 需求来源（T1N FL3 段落） |
| R2 | [D1CYC-1260](https://jira.imotion.ai:7070/browse/D1CYC-1260)（T1NFL5 先例） | — | 实现模式来源：mcu `32d1f5ae`、version_did `55acc3a`、zos_msg `fedc6ee9` |
| R3 | [[T1LFL1 Change deliverMcuSystemInfo function]]（D1CYC-1561） | — | F187/F188/F191 变体索引数据流 |

### 1.5 设计约束与假设

* **技术约束**：分支 develop；三仓库均在 TDA4 老工作区；代码修改一律 SSH/scp，不动 Y: 盘。
* **外部假设**：System Manager / zos 平台侧对新增枚举值 0x0153 无需额外适配（枚举经 IDL 编译自动传播）；T1N FL3 零件号 704002931AA 为终值（需求单 2026-10-21 二次修正，勿用首版的 704002739AA——那是 FL5 的零件号）。

---

## 二、 架构设计与系统交互 (Architecture & Interaction)

### 2.1 数据流向

```text
[产线写 2A1E 内部车型配置字]
        │  NVM_PDM_InternalCoding（F187 零件号 704002931AA → T1N FL3）
        ▼
[ov_diaRunnable.cpp deliverVehicleConfig]  ── m_vehicleVariant=0x0153（不 mapping，switch 空 case 直通）
        │  codingmgr_var_output（IDL 枚举 VEH_Chery_T1NFL3_FUEL_EX）
        ▼
[System Manager] ── APP 启动车型识别

[诊断仪 0x22 读 F187/F188/F191]
        ▼
[ov_dia_0x22_read_data_by_identifier_handler.cpp]
   NVM variant → E_VARIANT_T1LFL1_ID_T1N_FL3 索引
        ▼
[g_DidData_F187/F188/F191_au8_t1lfl1[索引]]（version_did 模板生成，13/10/10 字节，0x20 填充）
```

### 2.2 修改点清单（文件级）

| 仓库 | 文件 | 改动 |
| :--- | :--- | :--- |
| zos_msg | `message/zos_msg/ccw/codingmgr_var_output.idl` | +1 行：`@value(0x0153) VEH_Chery_T1NFL3_FUEL_EX,`（接在 0x0152 之后） |
| version_did | `modules/CHERY/T1LFL1_D073.json` | +3 行：`ZX_DID_F187_T1N_FL3: 704002931AA`、`ZX_DID_F188_T1N_FL3: 00.00.01`、`ZX_DID_F191_T1N_FL3: 0.0.1` |
| version_did | `templates/version_did.cpp.in` | 3 处：`g_DidData_F187/F188/F191_au8_t1lfl1[]` 数组尾各加 `"@ZX_DID_F187/F188/F191_T1N_FL3@"`（含注释行） |
| version_did | `templates/version_did.hpp.in` | +1 行：enum `E_VARIANT_T1LFL1_ID` 中 `E_VARIANT_T1LFL1_ID_T1N_FL3`（T1L_FL2 之后、TOTAL 之前） |
| mcu_app_tda4 | `cpj_chery/veh_t1lfl1/dia_cfg/src/0x22/ov_dia_0x22_read_data_by_identifier_handler.cpp` | 3 处：0xF187/0xF188/0xF191 handler 的 variant switch 各加 case `VEH_Chery_T1NFL3_FUEL_EX → E_VARIANT_T1LFL1_ID_T1N_FL3` |
| mcu_app_tda4 | `cpj_chery/veh_t1lfl1/dia_cfg/src/ov_diaRunnable.cpp` | 1 处：`deliverVehicleConfig` variant switch 加空 case `VEH_Chery_T1NFL3_FUEL_EX: break;`（no D009 mapping，0x0153 原样下发） |

### 2.3 关键正确性约束

* **数组与枚举对齐**：`g_DidData_F187/F188/F191_au8_t1lfl1[]` 维度是 `E_VARIANT_T1LFL1_ID_TOTAL`，enum 新条目必须插在 `E_VARIANT_T1LFL1_ID_TOTAL` 之前且与三个数组尾部追加的条目顺序一致（同 T1NFL5 先例位置：T1L_FL2 之后）。
* **patch 标记不适用**：本改动全部落在人工维护源文件（非 `cpj_*/autosar/` 生成目录），无需 `<{项目名}PATCH P{id}>` 标记。
* **DID 长度**：F187 13 字节 / F188 10 字节 / F191 10 字节，0x20 右填充，由模板机制保证，无需干预。

---

## 五、 异常处理、安全性与高可用设计

| 异常 / 边界场景 | 潜在系统风险 | 策略 |
| :--- | :--- | :--- |
| NVM 未写 2A1E（空配置字） | F187 handler default 分支索引 0（返回首款车型数据） | 沿用既有 default 行为，与 T1NFL5 一致，不新增处理 |
| 客户误写 D009 | T1NFL3 期望不 mapping | switch 空 case 直通，客户配置字被忽略（需求明确"不 mapping 客户配置字"） |
| F187 零件号写错（704002739AA 是 FL5 号） | 台架识别成 FL5 | 需求单已二次修正；设计/编码/验证三处核对 704002931AA |

## 六、 交付验收与测试标准

- [ ] 三仓库 develop 分支编译通过（version_did / zos_msg 为数据仓库，mcu_app_tda4 全量编译验证）
- [ ] 台架（J6 不适用，TDA4 无自动刷写，按项目现有刷写流程）：写 2A1E 内部配置字为 T1N FL3（F187=704002931AA）后——
  - [ ] 0x22 读 F187 返回 `704002931AA`（0x20 填充至 13 字节）、F188 返回 `00.00.01`、F191 返回 `0.0.1`
  - [ ] System Manager 收到车型配置字 0x0153（不 mapping：写任意 D009 后下发值仍为 0x0153）
- [ ] 回归：默认/其他车型（如 T1L FL2 0x0150）F187/F188/F191 读值不变

## 附录B：设计决策记录 (ADR 摘要)

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | 完全复用 T1NFL5 模式（空 case 直通 + DID 索引表尾追加） | 新建独立映射逻辑 | T1NFL5（0x0152）已量产验证；T1N FL3 同为 FUEL_EX 不 mapping 车型，行为一致 |
| 2 | zos_msg 枚举并入本 Story（D1CYC-2381） | 像 T1NFL5 那样走独立需求单（T1LFL1-2801 由平台同事提交） | 用户明确本次范围含 zos_msg + MCU，单 Story 交付避免跨单依赖 |

## 附录C：开放问题 (Open Issues)

| # | 问题描述 | 影响 | 责任方 | 跟踪截止时间 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | uss_app_tda4 是否需要 T1NFL3 项目适配（T1NFL5 先例为独立 Story D1CYC-1533） | 若 T1N FL3 车型搭载 USS，需补适配 | 用户/USS 团队 | 待确认 |
