# ⚙️ J02 DID 0x2A0C Internal Temperature Cluster（CAM 温度 A核→R核 传递与转换）需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | DID 2A0C Internal Temperature Cluster | **所属软件层级** | BSW (Diag / dia_cfg + ipc_cfg) |
| **文档状态** | 🟡 待评审 | **安全与质量要求** | QM ｜ MISRA C:2012 ｜ 编译零新增警告 |
| **模块负责人 / 作者** | @Hua.Yao | **关联输入/输出** | 📑 C097FAWVWREQ-416 ｜ 📊 UDS_Diagnostic_Questionnaire_J02.xlsx |

> **📝 变更记录**
> * `2026-11-18`｜@Hua.Yao｜V1.0｜完成需求解析、现状侦察与转换设计

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景**：J02（一汽捷达 C097FAWVW）诊断问卷新增 DID `0x2A0C Internal Temperature Cluster`（30 字节，$22 只读），汇总 ECU 内部温度：NTC/J6B 板温（MCU 接口直取）+ 摄像头温度（A核 经 IPC 传给 R核）。
* **核心目标**：$22 读 2A0C 时各字段按问卷定义返回——分辨率 0.01℃、补码 WORD；其中 CAM Temp Sensor Average 由 R核 完成对 A核 raw 数据的转换（raw 含义：byte1-50=整数℃、byte2/256=小数℃）。
* **设计原则**：
  1. **沿用 RX 既有链路**：IPC 接收与 2A0C handler 骨架已从 CMC RX 基线迁移（commit d43d65273），本次只补齐 J02 问卷要求的转换差异点。
  2. **转换收敛在诊断读取侧**：IPC 原始数据保持 raw 语义不动，转换发生在 2A0C handler 内。

### 1.2 适用范围 (Scope)

* **适用控制器**：J02（mcu_app_j6_v2 / cpj_fawvw / veh_j02），分支 develop。
* **核心职责**：DID 2A0C 读处理中 CAM 温度三路（Average / Sensor0 / Sensor1）raw→0.01℃ 补码编码转换。
* **范围边界**：不改 IPC 接收层（`IpcAdpr_Parse_CameraTemp` 仍存 raw）；不做 NTC/J6B 字段改动（`Diag_Get_Temperature()` 已返回 0.01℃ 补码 WORD）；不做 RX 的 D101/D102/D199 派生 DID（J02 问卷无此需求）。

### 1.3 术语与缩略语

| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| CAM Temp | Camera Temperature | 摄像头模组温度，A核 侧 `i2ctransfer -f -y 0 w2@0x36 0x4d 0x50 r2` 读取 |
| IPC | Inter-Processor Communication | A核（SOC）与 R核（MCU）核间通信 |
| raw 编码 | — | A核自定义编码：`byte1-50` = 整数℃，`byte2/256` = 小数℃ |

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | [C097FAWVWREQ-416](https://jira.imotion.ai:7070/browse/C097FAWVWREQ-416) | — | 需求来源，字段表 + 转换要求 |
| R2 | A_R核IPC交互规范（飞书云文档，见需求单附件链接） | V0.0.1_20260421 | IPC 通道与 Payload 定义 |
| R3 | [C097FAWVW-29](https://jira.imotion.ai:7070/browse/C097FAWVW-29) | — | 实现 Story |
| R4 | `cpj_cmc` RX 同名实现（IDC310-5923 / F4CMC-56 先例） | — | IPC 链路与 DID handler 参考 |

### 1.5 设计约束与假设

* **技术约束**：GHS 编译（J02 GCC 迁移后 CI 编译）；`ov_dia`/`idia` 诊断框架既有 handler 签名不变；不新增动态内存。
* **外部假设**：A核 按 A_R核IPC交互规范 在 IPC instance channel2（代码映射 `IPCTP_INSTANCE_ID_7, IPCTP_CHANNEL_ID_2`）周期发送 ≥26 字节 payload，Byte20-25 为三路 CAM 温度 raw 值。
* **假设的验证方式**：阶段 4 台架实测——A核 读 i2c raw 值与 $22 2A0C 返回值按公式对账。

---

## 二、 架构设计与模块间交互 (Architecture & Interaction)

### 2.1 模块依赖关系与调用链

```text
A核(SOC)
  ├─ i2c 读摄像头 (0x36 0x4d 0x50, 2B raw)          [A核 侧, 本设计不改]
  └─ IPC 发送 (instance ch2, payload Byte20-25=3路raw)
        ➡️ MCAL Ipc RX
        ➡️ IpcAdpr_Parse_CameraTemp()               [ipc_cfg, 已存在, 存 raw 至 g_CameraTemp_Data[6]]
        ➡️ gType_ov_dia_DID_ReadHandler_0x2A0C()    [dia_cfg, 本次修改点: raw→0.01℃ 转换]
              ├─ Byte0-7   ← Diag_Get_Temperature() [DiagM 组件, 已存在]
              └─ Byte8-13  ← g_CameraTemp_Data 转换 [本次新增转换]
        ➡️ DCM $22 响应
```

### 2.2 接口规范定义

| 接口类型 | 函数原型 | 输入/输出 | 职责与时机 |
| :--- | :--- | :--- | :--- |
| IPC Callback | `IpcAdpr_Parse_CameraTemp(void* buf, uint32 size)` | IN: payload(≥26B)；写 `g_CameraTemp_Data[6]` | 接收 IPC 即存 raw，已存在不改 |
| DID Read Handler | `gType_ov_dia_DID_ReadHandler_0x2A0C(uint16 idx, uint8* buf)` | OUT: 30B | $22 读 2A0C，本次在 Byte8-13 处加转换 |
| 新增静态函数 | `OvDia_ConvCamTempRawTo01C(uint8 raw_int, uint8 raw_frac)` → `int16` | raw 两字节 → 0.01℃ 补码 | handler 内复用，三路同用 |

### 2.3 并发与调度上下文

| 接口 / 共享资源 | 执行上下文 | 临界区保护 | 备注 |
| :--- | :--- | :--- | :--- |
| `g_CameraTemp_Data` 写 | IPC 接收回调 | 单写者（IPC 回调） | 沿用 RX 既有无锁设计 |
| `g_CameraTemp_Data` 读 | Dcm 诊断任务（$22 处理） | 无锁读，最坏读到半新半旧一帧 | 6 字节温度值非一致性关键数据；RX 同策略已验证 |

---

## 三、 核心逻辑与转换规则 (Core Logic)

### 3.1 数据格式与转换公式

**raw 编码**（A核 → R核，IPC Payload 每路 2 字节）：

```text
物理温度(℃) = (byte1 - 50) + byte2 / 256
例：byte1=70, byte2=0   → 20.00℃
    byte1=69, byte2=128 → 19.50℃
```

**DID 编码**（问卷定义：分辨率 0.01，补码 WORD，大端）：

```text
did_value = round( 物理温度 × 100 )
          = (byte1 - 50) × 100 + (byte2 × 100 + 128) / 256   [整数运算, 四舍五入]
```

验证：byte1=70,byte2=0 → 2000（20.00℃）；byte1=69,byte2=128 → 1900+50=1950（19.50℃）；byte1=45（-5℃）→ -500。

### 3.2 2A0C 返回布局（30 字节）

| Byte | 字段 | 来源 | 本次改动 |
| --- | --- | --- | --- |
| 0-1 | NTC_TEMP_AD | `Diag_Get_Temperature()[0..1]` | 无 |
| 2-3 | J6B_CMN_TS1 | `Diag_Get_Temperature()[2..3]` | 无 |
| 4-5 | J6B_MCU_TS1 | `Diag_Get_Temperature()[4..5]` | 无 |
| 6-7 | J6B_MCU_TS2 | `Diag_Get_Temperature()[6..7]` | 无 |
| 8-9 | CAM Temp Sensor Average | `g_CameraTemp_Data[0..1]` **转换后** | ✅ 本次 |
| 10-11 | CAM Temp Sensor0（预留） | `g_CameraTemp_Data[2..3]` **转换后** | ✅ 本次（同公式） |
| 12-13 | CAM Temp Sensor1（预留） | `g_CameraTemp_Data[4..5]` **转换后** | ✅ 本次（同公式） |
| 14-29 | 保留 | 0 | 无（memset 清零） |

---

## 四、 模块详细设计 (Detailed Design)

### 4.1 模块划分与职责

| 子模块/源文件 | 职责 | 改动 |
| :--- | :--- | :--- |
| `cpj_fawvw/veh_j02/dia_cfg/src/0x22/ov_dia_0x22_read_data_by_identifier_handler.cpp` | 2A0C handler 内 Byte8-13 raw→0.01℃ 转换 | ✅ 唯一修改点 |

### 4.2 函数级处理流程

```text
gType_ov_dia_DID_ReadHandler_0x2A0C(idx, buf):
1. memset(buf, 0, 30)
2. memcpy(buf[0], Diag_Get_Temperature(), 8)          /* NTC/J6B, 0.01℃ 补码 WORD 原样 */
3. for i in 0..2:                                     /* 3 路 CAM 温度 */
   3.1 v = (int16)( (g_CameraTemp_Data[i*2] - 50) * 100
                    + (g_CameraTemp_Data[i*2+1] * 100 + 128) / 256 )
   3.2 buf[8+i*2]   = v >> 8;  buf[9+i*2] = v & 0xFF  /* 大端补码 */
4. return E_DID_OK
```

运算全部为无符号/有符号 16/32 位整数运算，无浮点；溢出评估：byte1∈[0,255] → 中间值最大 255×100=25500 < 32767，`int16` 不溢出（负向 -5000 同安全）。

---

## 五、 异常处理与容错 (Error Handling)

| 异常/边界场景 | 潜在风险 | 防御策略 |
| :--- | :--- | :--- |
| IPC 未收到帧（A核 未上电/异常） | 温度为 0 → 转换后 -50.00℃ 失真 | 沿用现状（`g_CameraTemp_Data` 初值 0）；raw=0 为合法编码下限（-50℃），与 A核 数据下限一致，不做特殊值注入 |
| IPC payload < 26 字节 | 越界拷贝 | `IpcAdpr_Parse_CameraTemp` 已有 `size >= 26u` 防御，不改 |
| A核 raw 超范围（byte1 < 50） | 负温，属合法物理值 | 直接按有符号公式转换，不截断 |

---

## 六、 验证与验收 (Verification)

### 6.1 验收标准

- [ ] 编译通过（SSH 编译 + CI），无新增警告
- [ ] 台架 $22 读 2A0C（默认会话，任意安全态）：返回 30 字节，Byte14-29 全 0
- [ ] **转换对账**：A核 读 `i2ctransfer -f -y 0 w2@0x36 0x4d 0x50 r2` 得 raw (b1,b2)，DID Byte8-9 大端值 = (b1-50)×100 + round(b2×100/256)
- [ ] NTC/J6B 四路（Byte0-7）与既有行为一致（回归）
- [ ] Programming 会话下 2A0C 不响应（NRC 7F 22 31/7F）；会话/安全矩阵与问卷一致（回归）

### 6.2 验证手段

`tools/DiagnosticTester` 新增 J02 2A0C 用例（22 读 + 长度/格式断言），转换对账由用户台架实测（A核 i2c 值 vs DID 返回值）。

---

## 附录A：需求追溯矩阵

| 需求编号 | 需求摘要 | 设计章节 | 验证章节/用例 |
| :--- | :--- | :--- | :--- |
| REQ-416 字段表 Byte0-7 | NTC/J6B 温度 MCU 直取 | §3.2（已有实现回归） | §6.1 回归项 |
| REQ-416 字段表 Byte8-9 | CAM Average IPC Byte20/21 + 转换 | §3.1 / §4.2 | §6.1 对账项 |
| REQ-416 字段表 Byte10-13 | CAM Sensor0/1 预留 | §3.2（同公式转换） | §6.1 格式项 |
| REQ-416 会话/安全矩阵 | $22 全会话全安全态可读 | 既有 lookup 表条目（与 RX 一致，已符合） | §6.1 回归项 |
| 用户补充转换定义 | byte1-50 整数 / byte2÷256 小数 | §3.1 公式 | §6.1 对账项 |

## 附录B：设计决策记录 (ADR)

| # | 决策 | 备选方案 | 选择理由 |
| :--- | :--- | :--- | :--- |
| 1 | 转换放在 2A0C handler（读时转换），`g_CameraTemp_Data` 保持 raw | 在 `IpcAdpr_Parse_CameraTemp` 收包即转成物理值 | IPC 层保持与 A核 交互规范 raw 契约一致、与 RX 代码同构；J02 中该缓冲唯一消费者就是 2A0C，转换局部化便于对账 |
| 2 | Sensor0/1（预留）同样转换 | 保持 raw 透传 | 问卷三路字段格式声明一致（0.01 补码 WORD）；预留≠不转换，避免后续启用时再改 |
| 3 | J02 不引入 RX 的 D101/D102/D199 | 移植 RX 派生 DID | J02 问卷无此需求（RX EOL 专属），范围边界外 |

## 附录C：开放问题 (Open Issues)

| # | 问题描述 | 影响 | 责任方 | 跟踪截止时间 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 需求单写「IpcInstance_6 channel2」，代码映射为 `IPCTP_INSTANCE_ID_7, IPCTP_CHANNEL_ID_2`（沿用 RX） | 若 A核 实际发送 instance 与代码不符则收不到帧 | 联调对账（阶段 4 实测覆盖） | 2026-11-25 |
| 2 | 分辨率取整规则问卷未明确（round vs 截断） | Byte8-13 尾数 ±0.01℃ 差异 | 按 RX 先例取 round(+128)，如需求方有异议按其定义调整 | 2026-11-25 |
