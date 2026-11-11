# ⚙️ T1LFL1 D009 默认值全 FF 需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | T1LFL1 D009（APA Diagnostic Configuration）默认值与配置字判断修改 | **所属软件层级** | BSW (Dcm / NvM / PDM) |
| **文档状态** | 🟢 已实现 | **安全与质量要求** | 零警告编译 |
| **模块负责人 / 作者** | Hua.Yao / Claude | **关联输入/输出** | 📋 [T1LFL1-356](https://jira.imotion.ai:7070/browse/T1LFL1-356) / [D1CYC-3389](https://jira.imotion.ai:7070/browse/D1CYC-3389) |

> **📝 变更记录**
> * `2026-11-11`｜Hua.Yao｜V1.0｜D009 默认值改全 FF + 配置字存在性判断基准同步（全 0 → 全 FF）

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景**：需求单 [T1LFL1-356](https://jira.imotion.ai:7070/browse/T1LFL1-356)（APA Diagnostic Configuration，Reviewed，报告人 Jason Yu/郁捷杰）定义 DID D009 为 3 字节 Bitmap，Default Value = 全 F；现网代码默认值为全 0。
* **核心目标**：D009 默认值改为全 FF（FF FF FF）；「有没有配置字」的判断逻辑比较基准由全 0 改为全 FF，保证未写配置/清除配置后的状态与默认态一致。

### 1.2 适用范围 (Scope)

* **适用控制器/平台**：奇瑞 T1L FL1（D073，TDA4 平台，`cpj_chery/veh_t1lfl1`）
* **核心职责**：D009（NVM 块 `NVM_PDM_VehicleConfig`，3 字节）默认值 + 配置字存在性判断 + 清除例程恢复值
* **范围边界**：D009 读/写处理器的会话与安全等级矩阵不变（Default 22:Yes/2E:No、Extended 22/2E:Yes）；写侧打点范围校验（不一致回 NRC）不变；`Pdm_VehicleConfigStatus` 状态字节不变

### 1.3 术语与缩略语

| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| D009 | APA Diagnostic Configuration | 3 字节 Bitmap 诊断 DID，映射 NVM 块 VehicleConfig |
| 配置字 | Vehicle Config Word | D009 的 NVM 存储，含变速箱/车型/TRM/动力/驱动/轮胎/小书包/左右舵位域 |
| PDM | Persistent Data Manager | NVM 数据管理，RAM 镜像初值即默认值 |

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | [T1LFL1-356](https://jira.imotion.ai:7070/browse/T1LFL1-356) | — | 需求来源（D009 定义、会话矩阵、默认值全 F、NRC22 规则） |
| R2 | [[T1JFL1 fix clear configure bytes bug]]（D1CYC-1480） | — | 同域先例：清除配置字例程与 2A1E 默认值恢复模式 |
| R3 | [[T1JFL3 Add configure bytes function]]（D1CYC-773） | — | 配置字功能原始实现 |

### 1.5 设计约束与假设

* **技术约束**：代码修改经 SSH（12.42），编译 `imobuilder build mcu_app_tda4 -r`
* **外部假设**：默认值仅由 `pdmdb.cpp` RAM 初值决定（NvM 块无 ROM 默认值，已核实 microsar_cfg 无该块默认值定义）
* **假设的验证方式**：编译 + 台架（读 D009 默认值全 FF、写脏后清除恢复全 FF、未配置事件触发正确）

---

## 二、 架构设计与模块间交互

**数据流**：上电 PDM 初始化 `Pdm_VehicleConfig_Ram`（默认值）→ NVM 读写；`22 D009` 读 NVM 块返回；`2E D009` 位域校验后写 NVM；周期 runnable 读块做「有无配置字」判断（配置事件 CAN_Configuration_NotConfigured PASSED/FAILED）并向 coding mgr 投递映射；`31 01 2C F5` 清除例程恢复默认。

**并发上下文**：D009 读写在 Dcm 任务上下文，`checkFunctionConfigStatus`/`deliverVehicleConfig` 在 dia runnable 周期上下文，均经 `idiaIdBasedReadWrite` 同步访问 NVM 块，与现有机制一致，无新增并发路径。

---

## 三、 BSW 模块影响分析与修改点清单

### 3.1 BSW 模块影响

| 模块 | 影响 | 说明 |
| :--- | :--- | :--- |
| **PDM** | 默认值变更 | `Pdm_VehicleConfig_Ram` RAM 初值全 0 → 全 FF |
| **Dcm（dia_cfg）** | 判断基准变更 | 2 处「有无配置字」判断的比较缓冲区全 0 → 全 FF |
| **Dcm（0x31 例程）** | 恢复值变更 | 清除例程写 0 → 写 FF（与新默认一致） |
| NvM / Dem | 无 | 块长度/BlockID 不变；事件与判断结果语义不变（未配置=默认态=全 FF） |

### 3.2 修改点清单（文件级）

| # | 文件 | 修改方式 |
| :--- | :--- | :--- |
| 1 | `pdm_cfg/src/pdmdb.cpp:32` `Pdm_VehicleConfig_Ram[3]` | 手工：`{0x00u,0x00u,0x00u}` → `{0xFFu,0xFFu,0xFFu}` |
| 2 | `dia_cfg/src/ov_diaRunnable.cpp` `checkFunctionConfigStatus()` | 手工：`memset(...,0x00,...)` → `0xFF` |
| 3 | `dia_cfg/src/ov_diaRunnable.cpp` `deliverVehicleConfig()` | 手工：`memset(...,0x00,...)` → `0xFF` |
| 4 | `dia_cfg/src/0x31/ov_dia_0x31_routine_by_identifier_handler.cpp` `CClearInternalConfig::m_excuteStartCustomer()` | 手工：`memset(...,0,...)` → `0xFF` |

> 语义说明：判断逻辑语义不变（「非默认态 = 已配置」），仅默认态的物理值由全 0 变为全 FF；`deliverVehicleConfig` 未配置时跳过投递的行为与原先（全 0 跳过）保持一致。

### 3.3 分支与仓库

* 仓库：`mcu_app_tda4`（仅此一仓库）
* 分支：`develop` + `release/Chery/T1LFL1_D073/T480`；develop 先做，T480 cherry-pick（冲突取 develop 侧；develop 含 6 变体、T480 仅 t1lfl1 变体的差异与 D1CYC-1480 先例相同——本次只改 veh_t1lfl1 目录，两分支 diff 同构）
* feature 分支命名：`feature/D1CYC-3389-t1lfl1-d009-default-all-ff`（+`-t480`）

---

## 四、 验证方案

1. **编译**：SSH imobuilder 编译通过（develop 与 T480 各一次，零新增警告）
2. **台架手动验证**（验证点）：
   - 全新/清除状态读 `22 D009` 返回 `FF FF FF`
   - `2E D009` 写合法值后读回一致；写越界值（如 transType≥0x04）回 NRC
   - `31 01 2C F5` 清除后读 `22 D009` = `FF FF FF`
   - 未配置状态下 `CAN_Configuration_NotConfigured` 事件 FAILED；写入配置后 PASSED

### 验收标准（从 T1LFL1-356 提取）

- D009 默认值全 F；会话矩阵不变；值与 T1L 打点范围不一致时回 NRC22
- 上传 develop 和 release/Chery/T1LFL1_D073/T480 分支

---

## 附录B：设计决策记录 (ADR 摘要)

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | 清除例程写 FF 而非保持写 0 | 仅改默认值与判断 | 清除的目的即恢复出厂默认；默认改 FF 后写 0 会造成「清除后 ≠ 默认态」且被判断逻辑误判为已配置 |
| 2 | 默认值只改 pdmdb.cpp RAM 初值 | 同时改 NvM 配置 arxml | 已核实 microsar_cfg 无该块 ROM 默认值定义，PDM RAM 初值是唯一默认值来源（最小修改） |

## 附录C：开放问题

无。
