# ⚙️ PduR 组播网关 DCM 交付长度修复（IDC310GAC-7835）需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | PduR TP 网关——向 DCM 的组播交付 | **所属软件层级** | BSW (Com Stack / PduR) |
| **文档状态** | 🟢 开发中 | **安全与质量要求** | 与既有 PduR 生成代码规范一致 |
| **模块负责人 / 作者** | @Hua.Yao | **关联输入/输出** | 🐞 分析报告 `docs/analysis/2026-10-20-IDC310GAC-6762-6763-pdur-tpdcmtx-stale-length.md` |

> **📝 变更记录**
> * `2026-10-20`｜@Hua.Yao｜V1.0｜基于 problem-analysis V2 已验证修复的正式交付设计

> **📋 精简说明**：本需求为单文件单行缺陷修复（9 个 GAC 项目同源文件同改动），按模板使用说明省略不涉及小节（状态机/可配置参数/内部数据结构/消息时序），追溯见 JIRA IDC310GAC-7835 与关联问题单。

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景与痛点**：IDC310GAC-6762/6763（T68 功能寻址脚本速度连发，隔帧 NRC13 或无响应）。根因已由 problem-analysis 定位并 V2 台架 A/B 验证：`PduR_Gateway_TpDcmTx.c` 向 `Dcm_StartOfReception` 申报的长度硬编码 `SduLength_auo[0]`（FIFO slot0 过期值），推迟交付帧长度与数据错配。
* **核心目标**：SoR 长度跟随调用者 `info->SduLength`（本槽真实长度），无 info 时退回 Rx 实例长度；develop 全部 GAC 项目 + 4 条 release 分支同步修复。
* **设计原则**：最小化修复——1 行改动，F4CMC-41 生产验证同款先例，不引入行为面变化。

### 1.2 适用范围 (Scope)

* **适用范围**：`mcu_app_j6` 仓库 `cpj_gac/autosar/` 下 9 个项目（ay7 / luna6 / s52 / s52-e046 / t09 / t51 / t68 / t75 / t88，均已 grep 确认存在缺陷行）+ release 分支 `release/GAC/T68Y_G460/0710`、`release/GAC/T09_Y1_D126/G710`、`release/GAC/T75_D084/G270`、`release/T51-D088/S.001`。
* **范围边界**：其余 cpj（baic/chery/cmc/dfpv/gwm/hyundai/pf/smartxtruck）不在本次范围（用户确认）；5ms 泛洪下的 4 槽 FIFO 容量问题（SWS_PduR_00807）不属本缺陷，不处理。

### 1.3 术语与缩略语

| 缩略语/术语 | 全称 | 本文中含义 |
| :--- | :--- | :--- |
| SoR | StartOfReception | DCM 接收启动接口，长度申报入口 |
| FIFO 实例 | PduR_TpSession_Dynamic 的槽 | MAX_QUEUEDEPTH=4，组播推迟交付按 Tx 实例轮转 |

### 1.4 参考文档

| 编号 | 文档名称/链接 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | 分析报告 `docs/analysis/2026-10-20-IDC310GAC-6762-6763-pdur-tpdcmtx-stale-length.md` | V1.0 | 根因/T32 取证/A/B 验证 |
| R2 | JIRA [IDC310GAC-7835](https://jira.imotion.ai:7070/browse/IDC310GAC-7835) | — | 本 Story |
| R3 | F4CMC-41 修复先例（Obsidian `Rx fix dcm not response problem`） | — | 同款修复生产验证 |

### 1.5 设计约束与假设

* **技术约束**：改动属 AUTOSAR 生成代码，必须加 `/* <{项目名}PATCH P1> */` 标记（CLAUDE.md 规则），防下次代码生成覆盖。
* **外部假设**：9 项目该文件同源同缺陷行（grep 已确认）；release 分支上下文一致（cherry-pick 时逐条核对，冲突手工解决）。
* **假设的验证方式**：编译（T68 preset）+ T68 台架两用例回归；其余项目/分支按用户确认无需再验证。

---

## 二、 架构设计与模块间交互 (Architecture & Interaction)

### 2.1 模块依赖关系与调用链

```
功能寻址 0x7DF → CanIf Rx → PduR_GwTp(×4, PduR_gw_Tp_buf_PduRTxBuffer_FUNC_FUNC)
  → PduR_GwMcTx_Transmit → loTransmitTable[2] = PduR_GF_TP_Dcm_Transmit_Func   ← 本修改点
      → Dcm_StartOfReception(id, info, TpSduLength, &bufferSizePtr)            ← 长度错配发生处
      → Dcm_CopyRxData → Dcm_TpRxIndication
```

* 立即路径 caller（`PduR_Gateway_TpRx.c`）与推迟路径 caller（`PduR_Gateway_TpTxConf.c`）的 `info` 均与本槽数据/长度自洽（分析报告 §3.4）。

### 2.2 修改点（接口行为变化）

| 接口 | 修改前 | 修改后 |
| :--- | :--- | :--- |
| `PduR_GF_TP_Dcm_Transmit_Func(id, info)` 内 `TpSduLength` | `SessionPtr->SduLength_auo[0]`（硬编码 slot0） | `(info != NULL_PTR) ? info->SduLength : SessionPtr->SduLength_auo[SessionPtr->Rx_FifoInstanceUsed_u8]` |

### 2.3 并发与调度上下文

* 不改变调用上下文与共享数据保护——仅修正传给 DCM 的标量长度取值来源。

---

## 四、 模块详细设计 (Detailed Design)

### 4.1 修改点清单

| # | 项目 | 文件 | 改动 |
| :--- | :--- | :--- | :--- |
| 1-9 | ay7/luna6/s52/s52-e046/t09/t51/t68/t75/t88 | `cpj_gac/autosar/<p>/BswRta/src/bsw/PduR/src/PduR_Gateway_TpDcmTx.c:71` | 同款 1 行 + `/* <{P}PATCH P1> */` 标记（P=AY7/LUNA6/S52/S52E046/T09/T51/T68/T75/T88） |
| R1-R4 | release 各分支对应项目 | 同上 | develop commit cherry-pick，冲突手工解决 |

（2.x 其余小节与三、五章不涉及：无状态机/参数/数据结构变化，异常路径不变——`info==NULL` 分支保留原语义退回 Rx 实例。）

---

## 六、 验证、测试与集成要求 (Verification & Integration)

### 6.1 验收标准

1. T68 preset 编译零错误。
2. 台架回归：`func_10_min_6762`（4/4 PASS）、`func_3e_no_response_stale_length`（7/7 PASS）——标准同 V2 验证（tools/DiagnosticTester，CX ch0 500K/2M）。
3. 其余 GAC 项目编译随 CI（PR 流水线）保障；用户确认无需逐项目台架验证。
4. 全部 PR（develop ×1 + release ×4）合并，两张问题单关单。

### 6.2 回归风险评估

* 立即路径：caller 恒带 info 且长度与原取值一致（slot0 即当前槽）——无行为变化。
* 推迟路径：info 长度 == 本槽真实长度（T32 HIT2 实测 2==`SduLen[1]`）——修复目标。
* v3 反证试验（强制 Rx 实例长度→7FFF21）已排除，方案唯一。
