# T1JFL3 配置字映射国家解耦无效配置 DTC 设计文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | T1JFL3 配置字映射：国家不再关联配置字无效 DTC | **所属软件层级** | MCU 应用层（dia_cfg，手写代码） |
| **文档状态** | 🟡 待评审 | **安全与质量要求** | 零新增警告编译 |
| **模块负责人 / 作者** | Hua.Yao / Claude | **关联输入/输出** | 📋 [D100-1109](https://jira.imotion.ai:7070/browse/D100-1109) ｜ [D1CYC-2735](https://jira.imotion.ai:7070/browse/D1CYC-2735) ｜ 原实现 [D1CYC-773](https://jira.imotion.ai:7070/browse/D1CYC-773) |

> **📝 变更记录**
> * `2026-10-28`｜Hua.Yao｜V1.0｜初版：D100-1109 变更（国家不再关联配置字无效 DTC）

> 小改动（单分支单行级逻辑变更），按模板使用说明精简四、详细设计与附录A（追溯见 JIRA）。

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **背景**：D100-1109「客户配置字映射平台配置字」（原实现 D1CYC-773）2026-10-27 需求更新（Jason Yu 评论）：「国家不再关联配置字无效DTC」。现实现中整车配置字「销售区域（ICC）」（Coding DID 0x6757 Byte7）取预留值（0x2C~0xFF）时，除回退映射 China 外还置位配置无效标志，触发 DTC D30056（`DemEvent_CAN_Configuration_Invalid`）。
* **核心目标**：销售区域为预留值时仅回退映射 `EVehicleCountryEnum_China(0)`，不再触发 D30056；其余配置字的无效判定与 D30056 逻辑完全不变。

### 1.2 适用范围 (Scope)

* **适用控制器/平台**：JETOUR T1JFL3（TDA4 平台，`cpj_chery/veh_t1jfl3`）
* **范围边界**：仅改 salesRegion→country switch 的 default 分支行为；不涉及 Dem/Dcm/NvM 配置（零 arxml 变化），不涉及其他国家枚举值映射。

### 1.3 术语与缩略语

| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| Coding DID 0x6757 | Vehicle Config NvM 块 | 客户整车配置字 10 字节（NvM `NVM_PDM_VehicleConfig`） |
| salesRegion | 销售区域（ICC） | 0x6757 Byte7，映射内部配置字 `m_vehicleCountry` |
| D30056 | `DemDTC_U130056_Configuration_Invalid` | 配置字无效 DTC，事件 `DemEvent_CAN_Configuration_Invalid` |

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | : --- |
| R1 | [D100-1109 客户配置字映射平台配置字](https://jira.imotion.ai:7070/browse/D100-1109) | — | 需求来源（含 2026-10-27 变更评论） |
| R2 | [D1CYC-773 T1JFL3 Add configure bytes function](https://jira.imotion.ai:7070/browse/D1CYC-773) | — | 原实现 |
| R3 | [PDCU-34427 T1JFL3 change did and variant coding map](https://jira.imotion.ai:7070/browse/PDCU-34427) | — | 关联变更 |

### 1.5 设计约束与假设

* **技术约束**：代码写入一律 SSH 到服务器 10.0.12.42；双分支交付（develop + `Chery/T1JFL3_D100/T940`，develop 先做、T940 cherry-pick）。
* **外部假设**：需求方确认预留销售区域值不应视为配置错误（预留值合法存在，回退 China 即可）。
* **假设的验证方式**：台架写 0x6757 后 190A 读 DTC 验证（§6.2）。

---

## 二、 架构设计与模块间交互

数据流（无结构性变化，仅逻辑分支裁剪）：

```
Coding DID 0x6757 (NvM NVM_PDM_VehicleConfig, 10B)
  → Cov_diaRunnable::deliverVehicleConfig()            [dia_cfg/src/ov_diaRunnable.cpp:363]
      → salesRegion(Byte7) switch → m_vehicleCountry    [本次修改点 :602-658]
      → l_configInvalid_b 汇总 → Dem_ReportEventStatus  [:720-729]
  → CCodingVarDataOutput packData → System Manager 存文件
  → g_mcuVehicleCountry（供 idc2_dia_getVehicleCountry 查询）
```

**并发上下文**：`deliverVehicleConfig` 为诊断/初始化路径单线程调用（与原实现一致，无共享数据竞争变化）。

---

## 三、 核心逻辑变更

### 3.1 现状（变更前）

`ov_diaRunnable.cpp` salesRegion→country switch（:602-658）：

```
switch (l_salesRegion) {
  case 0x00..0x2B: 44 国逐一映射对应 EVehicleCountryEnum_xxx   // 不报 DTC
  default:          l_country = China; l_configInvalid_b = 1;  // 预留值 0x2C~0xFF → 报 D30056
}
```

`l_configInvalid_b` 同时由驱动形式/驱动类型/EPB/变速箱/悬架/座椅/备胎/2A1E 车型字等无效值置位，任一为 1 即 `Dem_ReportEventStatus(DemEvent_CAN_Configuration_Invalid, FAILED)`（:720-724）。

### 3.2 变更后

default 分支仅保留 `l_country = China` 回退，**删除 `l_configInvalid_b = 1;` 一行**。效果：销售区域预留值回退 China、不参与 D30056 判定；其余置位路径全部不变。

### 3.3 不变式

* 客户配置字未写入（0x6757 全 0，memcmp 判空 :410）时整段映射不执行，行为不变。
* 有效销售区域值（0x00~0x2B）映射关系不变，不报 D30056。
* 其余配置字无效 → D30056 的全部路径不变（回归面仅"销售区域预留值"这一输入组合）。

---

## 四、 详细设计（精简）

本需求仅涉及一处单行逻辑删除，无新增接口/状态机/数据模型，详见 §3。

### 修改点清单（文件级）

| # | 文件 | 修改方式 |
| :--- | :--- | : --- |
| 1 | `cpj_chery/veh_t1jfl3/dia_cfg/src/ov_diaRunnable.cpp`（salesRegion switch default 分支，约 :654） | 删除 `l_configInvalid_b = 1;` |

注：`dia_cfg/src/ov_diaRunnable.cpp` 为项目手写源码（非 `cpj_*/autosar/` 生成物），不适用 PATCH 标记规则。

### 分支与仓库

* 仓库：仅 `mcu_app_tda4`（TDA4 老工作区 `01_Workspace_TDA4`）
* 分支：`develop` + `Chery/T1JFL3_D100/T940`；feature 分支命名 `feature/D1CYC-2735-t1jfl3-country-no-invalid-dtc`（+ `-t940`）

---

## 五、 异常与容错

| 异常 / 边界场景 | 潜在风险 | 策略 |
| :--- | :--- | :--- |
| 销售区域预留值（0x2C~0xFF） | 误报 D30056（本需求消除） | 回退 China(0)，不置无效标志 |
| 其余配置字仍无效 | D30056 漏报 | 置位路径不动，保持原判定 |
| 0x6757 未写入（全 0） | 误映射/误报 | 判空短路不变（:410） |

---

## 六、 验证方案与验收标准

### 验收标准（从 D100-1109 变更评论提取）

- T1JFL3 配置字映射时，国家（销售区域）不再关联配置字无效 DTC（D30056）

### 验证手段（诊断台架，DiagnosticTester）

1. **A/B 对照**：写 0x6757 salesRegion=0xFF（预留）+ 其余字段全有效 → 基线（变更前）190A 可读出 D30056 / 修复后无 D30056
2. **回归**：salesRegion=有效值（如 0x00 China）→ 无 D30056、国家映射正确；其余字段置无效（如 seatCount=000）→ D30056 照常上报
3. **编译**：develop + T940 零新增警告

---

## 附录B：设计决策记录 (ADR 摘要)

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | 仅删 default 分支 `l_configInvalid_b = 1;` 一行 | 重构整个 switch（如函数表驱动） | 最小 diff，回归面收敛到单个输入组合；与原实现风格一致 |

## 附录C：开放问题

无。
