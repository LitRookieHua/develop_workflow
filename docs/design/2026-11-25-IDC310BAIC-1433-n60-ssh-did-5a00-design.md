# ⚙️ N60 SSH 开关 DID 变更（0x9D01 → 0x5A00）需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | 诊断 DID 配置（ov_dia，Dcm 0x22/0x2E 自定义 DID） | **所属软件层级** | BSW (Diag Stack) + CDD `ov_dia` |
| **文档状态** | 🟢 开发中 | **安全与质量要求** | MISRA C:2012 ｜ 编译器零警告 ｜ 不新增 NVM 块 |
| **模块负责人 / 作者** | @Hua.Yao | **关联输入/输出** | 📑 `IDC310BAICREQ-6700` ｜ 📊 `IDC310BAIC-1433` |

> **📝 变更记录**
> * `2026-11-25`｜@Hua.Yao｜V1.0｜N60 SSH 开关 DID 由 0x9D01 改为 0x5A00（A 核 IPC 交互保持不变）

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标
* **业务背景与痛点**：客户要求 N60 的 SSH 使能开关 DID 由 `0x9D01` 改为 `0x5A00`（需求单 `IDC310BAICREQ-6700` 替换原 `IDC310BAICREQ-1158`，Story `IDC310BAIC-1433`）。原实现见 [[N60 Change ssh function - NVM storage and power-on sync]]（`IDC310BAIC-1363`）。
* **核心目标**：诊断仪侧 `22 5A00` / `2E 5A00` 与非默认/扩展会话、安全等级（2701）门控行为与现 `0x9D01` 完全一致；NVM 块 `Z020_SSHEnableDisable` 与 A 核 IPC（subfunction `0x2E0A`）载荷**均不改变**。
* **设计原则**：
  1. **最小变更**：仅改 DID 号与查找表位置，读写逻辑、NVM、IPC 协议零改动。
  2. **A 核解耦**：A 核交互按需求原文"原有 A 核交互不变"处理——IPC 透传报文仍为 `2E 9D 01 XX`，正响应校验仍为 `6E 9D 01 00`。

### 1.2 适用范围 (Scope)
* **适用控制器/平台**：J6（N60，`cpj_baic`，构建 `BAIC/N60_D109`）。
* **核心职责**：`ov_dia` DID 读写 handler + `g_dia_did_lookup_table_ast` 查找表登记。
* **范围边界**：不改 A 核代码；不改 NVM 布局（`Z020` 块 ID 57、1 字节）；不改上电同步时序（20s 首发送、每 2s 重试、上限 15 次）；其他 BAIC 变体（b81vs/b70ks/n53）不在本需求范围。

### 1.3 术语与缩略语
| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| DID | Data Identifier | UDS 数据标识符，`0x22` 读 / `0x2E` 写 |
| IPC | Inter-Processor Communication | R 核（MCU）↔ A 核跨核消息，本需求用 subfunction `0x2E0A` |
| PDM | Persistent Data Management | 项目侧 NVM 数据管理封装 |

### 1.4 参考文档
| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | JIRA `IDC310BAIC-1433` | — | 本 Story（需求实现单） |
| R2 | JIRA `IDC310BAICREQ-6700` | — | 需求来源（替换 `IDC310BAICREQ-1158`） |
| R3 | JIRA `IDC310BAIC-1363` / `IDC310BAIC-1353` | — | 历史实现（NVM 存储 + 上电同步 / IPC 透传） |
| R4 | ISO 14229-1 (UDS) | 2020 | 0x22/0x2E 会话与安全访问语义 |

### 1.5 设计约束与假设
* **技术约束**：查找表用二分查找（`g_Diag_Search_DID_mid`），条目必须严格按 DID 升序排列。
* **外部假设**：A 核的 SSH 使能 UDS 服务 DID 仍为 `0x9D01`（按 Story 描述"原有 A 核交互不变"）。
* **假设的验证方式**：台架 `2E 5A00 01` 后观察 A 核正响应 `6E 9D 01 00` → MCU 回 `6E 5A00`；若 A 核侧实际已同步改为 0x5A00，则需回改 IPC 载荷（见附录 C）。

---

## 二、 架构设计与模块间交互 (Architecture & Interaction)

### 2.1 模块依赖关系与调用链
* **上游调用者**：Dcm（`0x22`/`0x2E` 服务分发）→ `g_dia_did_lookup_table_ast` 查表 → `ov_dia` handler。
* **下游被调**：PDM/NvM（`Z020_SSHEnableDisable`）、`hct_ipc_diag::HctUdsIpcHandler`（`IPCADPR_HCT_SSH_SWITCH = 0x2E0A`）。
* **核心交互时序**：
  `诊断仪 22/2E 5A00` ➡️ `Dcm` ➡️ `ov_dia handler` ➡️ `NVM Z020 读/写` + `IPC 2E 9D 01 XX → A 核` ➡️ `正响应 62/6E 5A00`

### 2.2 接口规范定义 (APIs & Callouts)
| 接口类型 | 函数原型 / 接口名称 | 输入/输出参数说明 | 核心职责与调用时机 |
| :--- | :--- | :--- | :--- |
| **0x22 handler** | `gType_ov_dia_DID_ReadHandler_0x5A00(uint16 f_index_u16, uint8 *buf)` | OUT: 1 字节 SSH 状态 | 读本地 NVM `Z020`，回 `62 5A00 XX` |
| **0x2E handler** | `gType_ov_dia_DID_WriteHandler_0x5A00(uint16 f_index_u16, const uint8 *buf)` | IN: 1 字节（0x00/0x01） | 写 NVM `Z020` → IPC 透传 A 核 → 校验 `6E 9D 01 00` → 回 `6E 5A00` |
| **IPC** | `HctUdsIpcHandler::process(payload, len, 0x2E0A, HctIpcFeature::SSH)` | payload `2E 9D 01 XX`（**不变**） | 跨核透传 SSH 使能 |

### 2.3 并发与调度上下文
| 接口 / 共享资源 | 执行上下文 | 临界区保护方式 | 备注 |
| :--- | :--- | :--- | :--- |
| 0x22/0x2E handler | Dcm 任务上下文（`ov_dia` runnable） | 沿用现有框架的 BUSY/重入状态机（`static` 状态，无并发写） | 本次不改 |
| 上电同步 `HctIpcDiagSsh_MainFunction` | 周期任务 10ms | 单任务，无锁 | 本次不改 |

### 2.4 初始化时序
* 不改初始化顺序；`Pdm_Z020_SSHEnableDisable_Ram[0]` 由 NvM ReadAll 恢复后，上电 20s 起由 `HctIpcDiagSsh_MainFunction` 推送 A 核。

---

## 三、 核心逻辑、状态机与参数规则 (Core Logic & Parameters)

### 3.1 核心状态机设计 (State Machine)
`2E 5A00` 写状态机保持 `IDC310BAIC-1363` 现状，仅 DID 名变化：

| 当前状态 | 目标状态 | 触发条件 | 动作 |
| :--- | :--- | :--- | :--- |
| `WRITE_NVM` | `IPC_POLL` | NVM 写返回 `E_DID_OK` | 同一次调用内发 IPC `2E 9D 01 XX` |
| `WRITE_NVM` | `NVM_POLL` | NVM 写返回 `E_DID_BUSY` | 等框架重入 |
| `NVM_POLL` | `WRITE_NVM` | NVM 写失败 | 复位重来 |
| `IPC_POLL` | `WRITE_NVM` | IPC 完成（任意结果） | 校验 `6E 9D 01 00` → `E_DID_OK`，否则 `E_DID_ERROR` |

### 3.2 可配置参数表 (Configurable Parameters / Pre-Compile)
| 参数分类 | 参数名称 | 可配置范围 | 默认推荐值 | 参数作用 |
| :--- | :--- | :--- | :---: | :--- |
| DID 编号 | 查找表条目 `0x9D01` → `0x5A00` | 固定 | `0x5A00` | 诊断仪侧 DID |
| 数据长度 | `DID_LENGTH_0x5A00` | 固定 | `1u` | 单字节状态 |
| NVM 块 | `Z020_SSHEnableDisable`（ID 57） | 固定 | 不变 | 掉电保存 |
| IPC DID | payload 内 `0x9D, 0x01` | 固定 | **不变** | A 核交互契约 |

---

## 四、 模块详细设计 (Detailed Design)

### 4.1 模块划分与职责
| 子模块/源文件 | 职责 | 对外接口 | 内部依赖 |
| :--- | :--- | :--- | :--- |
| `dia_cfg/var/src/vehicle/n60/did_lookup_table/ov_dia_did_lookup_table.cpp` | DID → handler 映射（二分查找有序表） | 表项 | — |
| `dia_cfg/var/src/vehicle/n60/0x22/...handler.cpp/.hpp` | 0x22 读 handler + 长度宏/声明 | `gType_ov_dia_DID_ReadHandler_0x5A00` | PDM `Z020` |
| `dia_cfg/var/src/vehicle/n60/0x2e/...handler.cpp/.hpp` | 0x2E 写 handler + 声明 | `gType_ov_dia_DID_WriteHandler_0x5A00` | PDM `Z020`、IPC `0x2E0A` |
| `dia_cfg/var/src/vehicle/n60/0x31/...handler.cpp` | FF04 例行服务（已改为 no-op） | — | 仅注释更新 |
| `dia_cfg/var/src/vehicle/n60/hct_ipc_diag/hct_ipc_diag_ssh.cpp` | 上电 NVM → A 核同步 | `HctIpcDiagSsh_MainFunction` | **不改**（payload 保持 `2E 9D 01 XX`） |

### 4.2 函数级处理流程
```text
DID 查找表（严格升序）
... 0x4103 → 0x5A00（新增位置） → 0x9B10 → 0x9B11 → ...

0x22 读 5A00:
  1. gType_ov_dia_DID_ReadPayloadFromNvM<Z020长度, DID_LENGTH_0x5A00>(Z020 blockId, buf)
  2. 返回 E_DID_OK → Dcm 回 62 5A00 XX

0x2E 写 5A00: 同 IDC310BAIC-1363 状态机
  WRITE_NVM → NVM_POLL ↔
  IPC payload 固定 {0x2E,0x9D,0x01, value}，响应校验 {0x6E,0x9D,0x01,0x00}
```

### 4.3 内部数据结构设计
无新增数据结构；`static` 状态机变量沿用（仅函数名变化）。

### 4.4 消息级时序
```text
诊断仪        Dcm/ov_dia            PDM/NvM            A核(IPC 0x2E0A)
  |--22 5A00---->|                     |                     |
  |              |--读 Z020----------->|                     |
  |<--62 5A00 XX-|                     |                     |
  |--2E 5A00 01->|                     |                     |
  |              |--写 Z020----------->|                     |
  |              |--2E 9D 01 01--------------------------->|
  |              |<--6E 9D 01 00--------------------------|
  |<--6E 5A00----|                     |                     |
```

---

## 五、 异常处理、容错与安全机制 (Error Handling & Safety)

| 异常/边界场景 | 潜在风险 | 防御与降级策略 |
| :--- | :--- | :--- |
| 非法值（非 0x00/0x01） | 写入非法状态 | `gType_ov_dia_CheckRange_BooleanByte` 拒绝，回 NRC（沿用现状） |
| NVM 写失败 | 状态未持久化 | 状态机复位重来（沿用现状） |
| A 核 IPC 超时/负响应 | 诊断仪长时间挂起 | 沿用重试/超时，最终回负响应（沿用现状） |
| 查找表乱序 | 二分查找失败，DID 不可达 | 0x5A00 插入 0x4103 与 0x9B10 之间，保持严格升序 |

---

## 六、 验证、测试与集成要求 (Verification & Integration)

### 6.1 资源消耗与性能基线
| 指标 | 预算/基线 | 测量方法 |
| :--- | :--- | :--- |
| ROM/RAM 变化 | 表项常量替换，0 增量 | map 文件对比（可选） |
| 响应时延 | 不劣于 0x9D01 现状 | 诊断台架实测 |

### 6.2 验收标准 (Acceptance Criteria)
- [ ] `22 5A00` 默认/扩展会话返回 `62 5A00 XX`（NVM 值）
- [ ] `2E 5A00` 非默认会话 → `7F 2E 31`；扩展会话未解锁 → `7F 2E 33`；2701 解锁后可写
- [ ] `2E 5A00 01` → NVM 落库 + A 核正响应 → 回 `6E 5A00`；A 核拒绝时回 `7F 2E 22`
- [ ] 掉电重启后 `22 5A00` 保持写入值
- [ ] 上电 20s 起 A 核收到 `2E 9D 01 XX`（IPC 日志确认）
- [ ] `22 9D01` / `2E 9D01` 不再响应（已从查找表移除）
- [ ] 编译通过（零新增警告），J6 `-x parking_dr uper_app` 标准命令

---

## 附录A：需求追溯矩阵
| 需求编号 | 需求摘要 | 设计章节 | 验证章节/用例 |
| :--- | :--- | :--- | :--- |
| IDC310BAICREQ-6700 | SSH 开关 DID 0x9D01 → 0x5A00，A 核交互不变 | §3.2 / §4.2 | §6.2；`tools/DiagnosticTester/testcase/n60/did_5a00_read_write/` |

## 附录B：设计决策记录 (ADR 摘要)
| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | IPC 载荷保持 `2E 9D 01 XX`、正响应校验 `6E 9D 01 00` | 同步改为 `2E 5A 00 XX` | 需求原文"原有 A 核交互不变"，A 核团队不改；改则跨团队契约破坏 |
| 2 | 新增 0x5A00 条目、删除 0x9D01 条目（而非别名共存） | 保留 0x9D01 兼容 | 客户要求 DID 变更，双 DID 会让旧 DID 继续生效，偏离需求 |
| 3 | handler 重命名为 `..._0x5A00` | 保留旧名 | 名称与 DID 一致，避免后续维护误读；仅 n60 变体受影响 |

## 附录C：开放问题 (Open Issues)
| # | 问题描述 | 影响 | 责任方 | 跟踪截止时间 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | A 核 SSH 服务 DID 是否也已改为 0x5A00（若已改，IPC 载荷需同步） | 2E 写成功与否 | 需求方 / A 核团队 | 台架验证时确认（2026-11-27 前） |
