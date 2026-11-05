# N60 0x27 Security Access Seed TRNG 化需求与设计说明

| 属性 | 值 |
| --- | --- |
| 工单 | IDC310BAIC-1429（来源需求 IDC310BAICREQ-6343「27 解锁seed要求」） |
| 项目/变体 | BAIC N60（cpj_baic，vehicle 变体 `n60`） |
| 修改分支 | develop + release/BAIC/N60_D109/B230（B230 cherry-pick 同步） |
| 仓库 | mcu_app_j6 |
| 日期 | 2026-11-05 |

## 一、 概述 (Overview)

### 1.1 功能背景与目标

来源需求 IDC310BAICREQ-6343（报告人 孙继烨，fixVersion B230）两条规则：

1. **种子记忆**：当前上电周期内，若 27 解锁未成功，持续发送 `27 01` 返回的 seed 一致；
2. **跨周期不重复**：至少保证连续五十个上电周期请求 `27 01`，seed 不重复。

现状（`cpj_baic/dia_cfg/var/src/vehicle/n60/0x27/ov_dia_0x27_security_access.cpp`）：

- seed 随机源是 `imo_GetRandom_u16()`——`GetCounterValue(Rte_TickCounter)` 喂 LCG（`RandomNo_u32 * 1103515245 + tick`），熵不足，上电周期起点一致时序列可重现（规则 2 不满足）；
- 周期内种子记忆由 Dcm 层安全访问管理既有机制承担（解锁未成功期间重复 `27 01` 复用 Dcm 内部 seed，不重新调用 GetSeed）——规则 1 现状即满足。

目标：seed 生成改调 `CryptoServ_TrngGenerate`（HSM TRNG 真随机数，共享组件 `components/bsw/Services/CryptoServ`），应用层不新增缓存（2026-11-05 用户确认）。

### 1.2 适用范围 (Scope)

- 仅 N60 变体：`cpj_baic/dia_cfg/var/src/vehicle/n60/0x27/ov_dia_0x27_security_access.cpp`（App/Boot/Develop 三个安全级共用该文件）；
- 不改 b81vs（已实现 TRNG，见 1.4 参考实现）、b70ks/n53（未在本需求范围）；
- 不改 Dcm 配置（arxml 的 DcmDspSecurityGetSeedFnc 回调名不变）、不改 CMake（`CryptoServ_Component` 已在 `cpj_baic/dia_cfg/CMakeLists.txt:53` 全项目链接）；
- 不改 Key/Seed 长度、KeyFactor、AES-CMAC 校验算法。

### 1.3 术语与缩略语

| 术语 | 含义 |
| --- | --- |
| TRNG | True Random Number Generator，HSM 硬件真随机数发生器 |
| LCG | Linear Congruential Generator，线性同余伪随机（现有回退路径） |
| 种子记忆 | 同一上电周期内解锁未成功时重复请求返回同一 seed |
| DF/Token | BAIC UDS Security Access Spec v2.0 的 AES-CMAC 认证数据（16B DF + 16B Token） |

### 1.4 参考文档

- 需求单：IDC310BAICREQ-6343（JIRA）
- 参考实现：b81vs 变体 `ov_dia_0x27_security_access.cpp`（IDC310BAIC-1385 b81-mcu-crypto-trng-interface，develop 已合入）——TRNG 直生 + LCG 回退模式
- `components/bsw/Services/CryptoServ/inc/CryptoServ_trng.h`：`Std_ReturnType CryptoServ_TrngGenerate(uint8 *RandomPtr, uint32 RandomLength)`
- BAIC UDS Security Access Spec v2.0（KeyFactor/AES-CMAC 定义）

### 1.5 设计约束与假设

- Dcm 回调签名固定（AUTOSAR Dcm 配置生成，不能改参数）；
- `CryptoServ_TrngGenerate` 同步接口，可在 Dcm 上下文直接调用（b81vs 已验证该模式）；
- TRNG 不可用时必须保底可用（诊断产线解锁不能因 HSM 异常而瘫痪）→ 保留 LCG 回退。

## 二、 架构设计与模块间交互 (Architecture & Interaction)

### 2.1 模块依赖关系与调用链

```
Tester          Dcm(生成代码, 不改)              ov_dia 0x27 (本次修改)                CryptoServ(共享组件, 不改)
27 01 ──────► DcmDspSecurityGetSeedFnc ──► AppSecurityGetSeed ────┬─► CryptoServ_TrngGenerate(seed, 16)
              (周期内 seed 由 Dcm               │      │ E_NOT_OK
               缓存复用, 不改)                  │      ▼
                                                  └─ imo_GetRandom_u16() LCG 回退(现状函数, 不改)
27 02 ──────► DcmDspSecurityCompareKeyFnc ► AppSecurityCompareKey(不改)
```

Boot（`BootSecurityGetSeed/CompareKey`）、Develop（`DevelopSecurityGetSeed/CompareKey`，带 16B magic number 校验）同理。

### 2.2 接口规范定义

对外接口（Dcm 配置回调，签名均不变）：

| 接口 | 签名 | 变化点 |
| --- | --- | --- |
| AppSecurityGetSeed | 既有 | 内部随机源改 TRNG（失败回退 LCG） |
| BootSecurityGetSeed | 既有 | 同上 |
| DevelopSecurityGetSeed | 既有 | 同上（magic number 校验保留） |
| App/Boot/DevelopSecurityCompareKey | 既有 | 无变化 |

### 2.3 并发与调度上下文

GetSeed/CompareKey 均在 Dcm 上下文（Dcm MainFunction 处理诊断请求）串行回调，单线程访问缓存，无需锁；TRNG 调用同步阻塞、长度 16B，b81vs 实测可行。

### 2.4 初始化时序

无应用侧初始化（不新增静态变量）。周期内 seed 生命周期由 Dcm 既有安全访问管理承担：解锁未成功期间重复 `27 01` 复用 Dcm 内部 seed，解锁成功/上电复位后重新调用 GetSeed。

## 三、 核心逻辑、状态机与参数规则 (Core Logic & Parameters)

### 3.1 核心状态机设计 (State Machine)

应用层无新增状态机，seed 生命周期完全由 Dcm 既有机制管理：

- 解锁未成功期间重复 `27 01` → Dcm 复用内部缓存的 seed（种子记忆，需求规则 1）；
- 解锁成功后再 `27 01` → Dcm 重新调用 GetSeed → TRNG 生成全新 seed；
- 上电复位 → Dcm 缓存清空 → 本周期首次 `27 01` 必经 GetSeed → TRNG 新 seed（跨周期不重复，需求规则 2 的起点）。

### 3.2 可配置参数表 (Configurable Parameters / Pre-Compile)

| 参数 | 值 | 说明 |
| --- | --- | --- |
| DCMAPPL_SECA_SEED_APP/BOOT/DEVELOP_LENGTH | 16u/16u/16u | 不变 |
| DCMAPPL_SECA_KEY_APP/BOOT/DEVELOP_LENGTH | 32u/32u/16u | 不变 |
| g_keyFactorUds_au8 / g_keyFactorBoot_au8 | 不变 | BAIC N53TB 规格定义 |

## 四、 模块详细设计 (Detailed Design)

### 4.1 模块划分与职责

仅改一个文件：`cpj_baic/dia_cfg/var/src/vehicle/n60/0x27/ov_dia_0x27_security_access.cpp`（+ `#include "CryptoServ_trng.h"` 于既有 extern "C" 块）。

### 4.2 函数级处理流程

**AppSecurityGetSeed / BootSecurityGetSeed**（两函数同构，缓冲区与长度不同）：

```
if CryptoServ_TrngGenerate(g_seedXxx_au8, 16) != E_OK:
    LogSync("TRNG generate failed, fallback to LCG")
    for i in 0..15: g_seedXxx_au8[i] = imo_GetRandom_u16()   // 现状 LCG, 原样保留
memcpy(Seed, g_seedXxx_au8, 16); *ErrorCode = E_POSITIVE_RESPONSE; LogSync(seed)
return E_OK
```

**DevelopSecurityGetSeed**：magic number 16B 校验保留；校验通过后走上述同构流程（回退路径沿用现状的 `+=` 累加形式）。

**App/Boot/DevelopSecurityCompareKey**：不改（g_seedXxx_au8 仍为 CompareKey 计算 Token 的依据，与最近一次 GetSeed 下发值一致）。

**imo_GetRandom_u16()**：现状函数（GetCounterValue 喂 LCG）原样保留，仅作为 TRNG 失败时的回退路径。

### 4.3 内部数据结构设计

不新增数据结构。g_seedApp/Boot/Develop_au8 既有模块级数组继续承载最近一次生成的 seed（CompareKey 用它计算 Token）。

## 五、 异常处理、容错与安全机制 (Error Handling & Safety)

| 异常 | 处理 |
| --- | --- |
| TRNG 生成失败（HSM 异常） | 回退现状 `imo_GetRandom_u16()` LCG，诊断解锁保底可用；LogSync 留痕 |
| 解锁成功后 seed 重放 | 解锁成功后 Dcm 重新调用 GetSeed，TRNG 生成全新 seed |
| 上电周期种子重复 | TRNG 硬件熵；回退态为现状 LCG（纯 tick），仅保底可用性，非本需求验收路径 |
| Develop 级非法请求 | magic number 不匹配维持 E_SUB_FUNCTION_NOT_SUPPORTED（不变） |

## 六、 验证、测试与集成要求 (Verification & Integration)

### 6.1 资源消耗与性能基线

每次 GetSeed 调用一次同步 TRNG（16B）。RAM 增量 0B（不新增静态变量，周期内重复请求由 Dcm 缓存吸收、不进 GetSeed）。

### 6.2 验收标准 (Acceptance Criteria)

工具：tools/DiagnosticTester，testcase `n60/security_access_seed/`（新建）：

1. 同上电周期连续多次 `27 01`（含发错 key 触发 NRC 35 后再请求）→ seed 逐次一致（Dcm 层种子记忆）；
2. 正确 key 解锁成功后再 `27 01` → seed 与此前不同（Dcm 重新取 seed，TRNG 生成）；
3. `cycle` 断电重启后再 `27 01` → seed 与上一周期不同（重复采样多周期；50 周期全量验证由测试侧台架断电循环执行，SIL 侧抽测 ≥2 周期）；
4. 回归：正确 DF+Token 解锁流程不受影响（27 01 → 27 02 成功解锁）。

## 附录A：需求追溯矩阵

| 需求条目 | 设计落实 | 验证 |
| --- | --- | --- |
| 种子记忆（周期内解锁未成功 seed 一致） | Dcm 层既有机制（本次不改动、不重复实现） | 验收 1 |
| 五十个上电周期 seed 不重复 | §4.2 GetSeed 主路径 TRNG；上电复位后每周期首次 GetSeed 必经 TRNG | 验收 3 |
| 调用 CryptoServ_TrngGenerate 替换 GetCounterValue | §4.2 GetSeed 主路径 TRNG；GetCounterValue 仅存于回退 LCG（现状函数不动，保底要求） | 验收 1/3/4 |

## 附录B：设计决策记录 (ADR 摘要)

- **ADR-1 不加应用层 seed 缓存**（2026-11-05 用户确认）：周期内种子记忆由 Dcm 层既有安全访问管理承担（解锁未成功期间重复 `27 01` 复用 Dcm 内部 seed），应用层只把随机源换成 TRNG，避免重复实现、diff 最小。
- **ADR-2 保留 LCG 回退而非 TRNG 失败直接报错**：产线/售后解锁可用性优先；回退即现状 `imo_GetRandom_u16()` 原样保留，不新增代码。
- **ADR-3 最小补丁、不同步 b81vs 风格**（2026-11-05 用户确认）：仅在 n60 现文件上做功能性修改（include + 3 个 GetSeed 随机源替换，最终 diff +19/-6），不引入 b81vs 变体的 PRQA 注释块、const 签名、`(void)` 转换等风格现代化，保持 diff 最小可评审。

## 附录C：开放问题 (Open Issues)

- 50 上电周期全量验证的执行归属（SIL 抽测 vs 测试台架断电循环）——随验收与报告人确认。
