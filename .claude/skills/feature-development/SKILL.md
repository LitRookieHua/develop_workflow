---
name: feature-development
description: MCU 需求开发全流程工作流（5 阶段：需求解析与架构映射 → 任务准备与环境隔离 → 核心配置与编码 → SIL 与台架隔离验证 → 审查与合流；Obsidian 笔记 → JIRA story → 设计方案 → 建分支 → 改代码 → 编译 → 刷写 → 验证 → 上传 → Bitbucket PR → 关闭 JIRA/笔记 → 通知需求报告人）。Use this skill whenever the user mentions 开发工作流、走工作流、做需求、新需求、story 开发、开始开发, references a requirement or JIRA ticket (如 D3ACYI-xxxx) to develop in mcu_app_tda4 / mcu_app_j6 / mcu_app_j6_v2, or asks for any part of the flow — 切分支、编译代码、上传代码、提交 PR、总结笔记、关闭工单/JIRA — even if they only mention a single step.
---

# MCU 需求开发工作流（Feature Development，5 阶段）

5 阶段固定流程，适用于 TDA4 / J6 工作区的 mcu_app 需求开发。其中**阶段 4 的手动验证是用户手动操作**，执行到该处停下等用户确认。收尾（关 JIRA/笔记、通知报告人）在所有 PR 合并后**自动执行，无需用户确认**（见阶段 5）。

开始前用 TaskCreate 为本次需求创建任务列表（**每阶段一个任务，共 5 个**），逐步勾选，随时可从任务列表恢复进度。

## 路径角色与工作区

路径角色表见 CLAUDE.md「路径角色」（Y: 盘红线同 CLAUDE.md 安全红线）。本 skill 用 **V1 老工作区**（`01_Workspace_TDA4` / `02_Workspace_J6`）做需求开发；环境搭建（项目/分支确认、.imobuilder、建分支）见阶段 2。

---

## 开始前确认

从用户消息或笔记中确认以下信息，缺了就问：

1. **工作区**：TDA4（`Y:\01_Src\01_Workspace_TDA4`）还是 J6（`Y:\01_Src\02_Workspace_J6`）
2. **来源需求**：JIRA 单号/链接，或需求描述
3. **项目/变体**：如 V2XSEA、T1LFL1、T51、N60、J02
4. **待修改分支**：仅 develop，还是 develop + release（如 `release/Chery/V2XEU_D065/V460`）
5. **修改仓库**：mcu_app / zos_msg / version_did 中哪些仓库需要改动。J6 工作区的 mcu 仓库有 `mcu_app_j6` 和 `mcu_app_j6_v2` 两个，须按项目归属选定（判断规则见 [references/workspace-setup.md](../../references/workspace-setup.md)）

## 流程总览

| 阶段 | 内容 | 执行者 |
| --- | --- | --- |
| 1 | 需求解析与架构映射：story-creation 立项 + 知识召回 + docs/design 技术方案 | Claude |
| 2 | 任务准备与环境隔离：确认项目/分支/仓库，SSH 切 develop 建分支 | Claude（SSH） |
| 3 | 核心配置与编码：SSH 写代码（scp 推送）、autosar 生成、SSH 编译 | Claude（SSH） |
| 4 | SIL 与台架隔离验证：刷写（仅 J6）+ 手动验证 | 刷写 Claude / 验证**用户手动** |
| 5 | 审查与合流：commit/push、PR、监控合并、技术沉淀、关单、通知 | Claude |

---

## 阶段 1：需求解析与架构映射

1. **立项**：走 `story-creation` skill——创建 Obsidian 笔记（Work Database/ + Work Item Template，规则见 [references/obsidian-notes.md](../../references/obsidian-notes.md)）+ 创建 JIRA Story 并互相关联，细则全在该 skill
2. **知识召回——写方案之前先做**：检索 `docs/design/` 类似设计方案、`docs/analysis/` 相关个案、Obsidian `Work Database/` 笔记（检索规则见 [references/obsidian-notes.md](../../references/obsidian-notes.md) §7，关键词：需求功能名、模块名、项目变体）——命中同类方案 → 复用/更新历史结论加速编写；无命中 → 继续
3. **技术方案（所有需求必写）**：`docs/design/YYYY-MM-DD-<工单号>-<主题>-design.md`，**按仓库模板写**（MCU/AUTOSAR BSW 功能 → [autosar-general-feature-design-template.md](../../../docs/design/autosar-general-feature-design-template.md)；通用功能 → [general-functional-design-template.md](../../../docs/design/general-functional-design-template.md)；模板含属性表/术语/参考文档/约束假设/架构交互含并发上下文/详细设计/异常容错/验收标准/追溯矩阵/ADR/开放问题，小改动按模板内使用说明精简）。技术内容至少覆盖：
   - 需求摘要与验收标准（从 JIRA 需求单 description 提取，原样整理）
   - **BSW 模块影响分析**：明确影响的具体模块与参数（如 Dcm 的 DID/RID、Dem 的 Debouncing 策略、PduR 路由表、Nvm 块）
   - 修改点清单（文件/模块级别，作为附录）
   - 验证方案（用什么手段验证）
4. Obsidian 笔记 **Design 章节**一行指针链接该设计文档

> 后续迭代：AI/脚本自动从 JIRA 提取验收标准。

## 阶段 2：任务准备与环境隔离

⚠️ **关卡：动手前必读 [references/workspace-setup.md](../../references/workspace-setup.md)**（权威源：项目/分支/工作区确认、.imobuilder、J6 双仓库、SSH 切/建分支、依赖仓库同步、多分支与 release 规则）。

按手册在**老工作区**搭建开发环境：

1. 确认项目/分支/工作区（手册 §1；多分支/release 合入需求此时确认，规则见手册 §5）
2. 改 `.imobuilder` 的 `build_product`（手册 §2，`ls config/` 现查）
3. 对确认的修改仓库逐一建 feature 分支（手册 §4：reset 前残留改动备份、分支命名、推送），依赖仓库同步切分支（手册 §4）

## 阶段 3：核心配置与编码

**代码修改一律经 SSH 在服务器上写**（Y: 盘禁止写源码）。写入方式（scp 推送 / SSH heredoc / autosar 生成产物同步）见 [references/workspace-setup.md](../../references/workspace-setup.md) §6。

- develop 分支：如上修改
- release 分支（第二个分支）：可直接 cherry-pick develop 分支的 commit（SSH 执行 `git cherry-pick <commit-hash>`），冲突时手工解决（release 与 develop 代码有差异）

**编译**（SSH）：标准命令、关键规则（J6 `-x parking_dr uper_app` 必带、勿接 `| grep` 管道、编译前核对依赖仓库分支）一律查 **[references/build.md](../../references/build.md)**（权威源：命令 / 规则 / 排障 / 固件刷新）。编译失败先按报错判断是环境问题还是代码问题，排障对号入座；失败修复后重试，通过后进入阶段 4。

> 后续迭代：零警告（Zero-warning）与 MISRA 静态规范本地强制检查。

## 阶段 4：SIL 与台架隔离验证

**电源操作规则**：验证前 `cycle` 重启、验证后 `off` 关闭，无程控电源时提示用户手动断电/上电——命令与 COM 号见 [references/validation-methods.md](../../references/validation-methods.md)「电源操作」节；J6 刷写的断电冷启动已由工具内置（[flashing.md](../../references/flashing.md)），刷写前无需重复 `cycle`。

**刷写固件（仅 J6，Windows 本地执行）**：命令、示例、`--img-dir` 规则（必须显式传、指向 Y: 盘本工作区编译输出）、串口/电源 COM 识别、自动流程与失败排查一律查 **[references/flashing.md](../../references/flashing.md)**（权威源）。`--img-dir` 指向老工作区 `Y:/01_Src/02_Workspace_J6/src/<仓库>/build/<preset>/rpu_arm_gcc`。TDA4 工作区无自动刷写工具，跳过刷写直接进入手动验证。

**手动验证 —— 停下等待**：用户手动验证（台架/功能验证）。验证通过后用户会说继续。

**验证方法统一入口：[references/validation-methods.md](../../references/validation-methods.md)**——诊断相关验证用 `tools/DiagnosticTester` 自动执行（1. 编写 testcase → 2. 运行验证）；采集 log 用 `tools/LogCollection`；在线调试用 TRACE32（J6B `/t32-j6b-connect`、TDA4 `/t32-tda4-connect`，含任务调度/堆栈/Scom 分析指令）；电源操作配套见该文档。后续新增验证方法一律补充到该文档，其他地方只指向它。

```bash
python DiagnosticTester.py run testcase/<项目>/<用例>/<用例>.yaml --config configs/<项目>/<配置>.yaml
```

测试桩（转发器）见 `tests/harness/diag_test/`。

> 后续迭代：x86 SIL 无硬件隔离验证（黑白盒）、LDC/OOP 配置一致性校验器接入。

## 阶段 5：审查与合流

**交付收尾统一走 [references/delivery.md](../../references/delivery.md)**（权威源：commit/push → 创建 PR → 技术沉淀（docs + 笔记）→ PR 全部合并后关单 → 通知报告人；与 problem-analysis 共用）。本 skill 的差异点：

- **技术沉淀**：docs 沉淀在阶段 1 已完成（`docs/design/` 设计文档），本阶段按 delivery.md §3 核对完整性并做 Obsidian 笔记台账总结（status/Code Changes/Status Updates/Related Links）
- **通知报告人**：对象为**来源需求单**（parent requirement，如 `IDC310BAICREQ-4639`）的报告人
- **关联单关闭**：来源需求单 + 关联问题单都一并关闭

---

## ⚠️ 关键规则

- **Y: 盘只许刷写读镜像/读代码/写 `.imobuilder`，其余一律 SSH**——两重破坏性（CRLF 污染 3432 文件、mode 644→755 进 commit）与允许/禁止清单见 CLAUDE.md 安全红线（权威源）
- Token 存放位置、认证方式、踩坑规则一律见 [references/token-authentication.md](../../references/token-authentication.md)（权威源）；红线：token 绝不内联到任何会被提交的文件，`.imobuilder` 含 CI token 不要暴露
