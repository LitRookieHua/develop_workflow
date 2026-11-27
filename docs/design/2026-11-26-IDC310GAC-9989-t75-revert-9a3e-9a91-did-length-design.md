# T75 回退 9A3E/9A91 DID 长度改动与 9A6E rename 需求与设计说明文档

| 文档基础属性 | 内容说明 | 架构与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **功能模块名称** | T75 PKI DID 回退（dia_cfg / pdm_cfg / NvM 配置） | **所属软件层级** | BSW (Diag / Memory Stack) |
| **文档状态** | 🟢 开发中 | **安全与质量要求** | 零警告编译（CI 门禁） |
| **模块负责人 / 作者** | Hua.Yao | **关联输入/输出** | 📑 IDC310GAC-9989 ｜ 📊 [2026-10-22 前置设计](2026-10-22-IDC310GAC-7988-7989-pki-9a3e-9a95-ar-ipc-design.md) |

> **📝 变更记录**
> * `2026-11-26`｜Hua.Yao｜V1.0｜纯回退设计：revert 7368 + 7483 两笔提交

> 本需求仅涉及两笔既有提交的 revert，追溯见 JIRA（IDC310GAC-9989）；按模板使用说明精简，省略详细设计中不涉及的小节。

---

## 一、 概述 (Overview)

### 1.1 功能背景与目标

* **业务背景**：需求变更——T75-G1 PKI DID 长度确认不需要 46，改回 30。release/GAC/T75_D084/G280 上的两笔提交需整体回退：
  * `254914b` feat(dia_cfg): [IDC310GAC-7368] T75 change 9A3E and 9A91 DID length from 30 to 46
  * `55090b2` feat(dia_cfg): [IDC310GAC-7483] T75 rename PKI DID 9A3E to 9A6E, AR IPC keeps 9A3E
* **核心目标**：G280 分支恢复 DID 9A3E（长度 30）、去掉 9A6E、9A91 长度回 30、Z021 PkiInformation NVM block 长度回 30、9A3E write IPC frame 回 33。
* **范围边界**：仅 release/GAC/T75_D084/G280 分支；develop 等其他分支不在本次范围。

### 1.2 参考文档

| 编号 | 文档名称 | 版本 | 关联内容 |
| :--- | :--- | :--- | :--- |
| R1 | IDC310GAC-9989 | — | 本 Story |
| R2 | IDC310GAC-7368 / 7483 | — | 被回退的两笔原始实现 |
| R3 | 2026-10-22-IDC310GAC-7988-7989-pki-9a3e-9a95-ar-ipc-design.md | V1.0 | 前置实现（引用 7368/7483 为前置依赖） |

---

## 二、 回退方案与影响分析

### 2.1 回退顺序（关键）

**先 revert 7483（rename 9A6E→9A3E），再 revert 7368（长度 46→30）**。反序会对 0x22 hpp / DID 表产生内容冲突（本地演练实测：正确顺序两笔 revert 全部干净应用，反序冲突 2 个文件）。

### 2.2 对 7988/7989（9A95 转发）的影响分析——回退安全性结论

* `IpcDiagSvc_ResponsePkiUrlPort`（0x2238 自动应答）使用变体自适应宏 `NVM_CFG_NV_BLOCK_LENGTH_NVM_PDM_Z021_PkiInformation`，Z021 回 30 后应答长度自动变 33，**不写死 46，无需改动**；
* AR IPC 契约本就保持 9A3E（7483 只改了诊断侧 DID 名），回退 rename 不影响 A 核交互；
* 9A95 证书状态查询转发（t75 0x22 handler + DID 表 9A95 条目）与 9A3E/9A6E 不重叠，回退演练确认完整保留；
* `dia_cfg/var/src/vehicle/t75/0x22` cpp 在 7483 后另有 7988/7989 改动（9A95 handler），演练确认 revert 7483 自动合并无冲突、9A95 handler 完好。

### 2.3 修改点清单（14 文件，全部由两笔 revert 自动覆盖）

| 区域 | 文件 | 回退内容 |
| :--- | :--- | :--- |
| NvM/Fee/Ecuc 生成物 | `cpj_gac/autosar/t75/BswRta/`（J6B_NvM_EcucValues.arxml、Fee ×2、NvM ×2） | Z021 block 长度 46→30 |
| dia_cfg 0x22/0x2e | `cpj_gac/dia_cfg/var/.../t75/`（0x22 hpp/cpp、0x2e hpp(公共)/cpp、DID 表）+ 公共 0x2e hpp | 9A6E→9A3E、长度 46→30、write frame 49→33 |
| pdm_cfg | `AY7_NVM_List.xlsx`、`pdm_cfg.h`、`pdm_cfg_BswAdapter.h/.c` | Z021 NVM 列表与块长 46→30 |

### 2.4 验证方案

* 本地（D: 镜像）已做 revert 演练：正确顺序零冲突，回退后状态逐项核对通过（DID_LENGTH_0x9A3E/0x9A91=30u、9A6E 消失、9A95 保留、Z021=30）；
* 按用户指令跳过本地编译与台架验证，编译正确性由 PR 合并前 CI 构建门禁覆盖；
* 回退后状态 = `254914b` 父提交状态 + 7988/7989 的 9A95 增量。
