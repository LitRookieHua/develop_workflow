# 开发工作流双链路重构设计（feature-development + problem-analysis）

> ⚠️ **历史文档**：本文中"Y: 直编"等编码方式已于 2026-10-19 废止（Y: 盘仅许刷写读镜像/读代码/写 .imobuilder，代码写与 git 操作一律 SSH），设计文档模板也已重构——现行规则以 `CLAUDE.md` 与 skill 为准，本文仅作历史记录。

- 日期：2026-10-16
- 状态：已确认
- 分支：refactor/workflow-structure
- 背景：将现有 dev-workflow（13 步）/ problem-analysis（6 步）两个 skill 重组为两条链路：**需求开发（Feature Development，5 阶段）**与**问题分析（Problem Analysis，4 阶段）**。结构对齐优先，缺失能力（x86 SIL、LDC/OOP 校验、PSA 回放、MCAP 解码、二分隔离/故障注入）作为「后续迭代」标注，不阻塞本次重构。

## 1. 目标与约束

### 目标

1. 新建 `feature-development` skill，替换并删除 `dev-workflow`：吸收其 13 步全部内容，重组为 5 阶段；story-creation 保持独立（阶段 1 复用）
2. 重写 `problem-analysis` skill 为 4 阶段：新增知识召回前置、V2 修复验证环节；分流保留
3. 两个 skill 均采用**骨架 + references** 组织：SKILL.md 只含阶段骨架 + 硬规则 + 日常命令，自包含细节块拆到 references，在关卡点强制阅读

### 已确认的关键决策

| 决策点 | 结论 |
| --- | --- |
| 重构首要目标 | 结构对齐优先，缺失能力标注后续迭代 |
| dev-workflow 去留 | 替换并删除（不留档备份，git 历史即存档） |
| 问题链路修复位置 | V2 工作区修复+编译+刷板+验证（不建分支不 commit）；正式提交转 feature-development 老工作区 |
| 阶段 1 设计文档 | **所有需求必写** docs/design/ 技术方案 |
| skill 文件组织 | 骨架 + references（方案 B） |

### 约束（红线，迁移中不得破坏）

- 规则内容**零丢失零删改**：dev-workflow 原文每条规则在新结构中均有落点
- git 写操作禁止 Windows 本地执行等 CLAUDE.md 硬规则原样保留
- V2 工作区仍不建分支、不 commit、不 push（修复属验证性 scratch 改动）
- 本次不实现任何新工具能力，不动 tools/、tests/、服务器状态

## 2. 目录结构

```
.claude/skills/
├── story-creation/          # 不动（仅改 2 处 dev-workflow 引用 → feature-development）
│   ├── SKILL.md
│   └── references/projects.md
├── feature-development/     # 新建，替换 dev-workflow
│   ├── SKILL.md             # 5 阶段骨架 + 硬规则 + 日常命令（~200 行）
│   └── references/
│       ├── workspace-setup.md       # .imobuilder 项目映射、J6 双仓库规则、依赖仓库核对
│       ├── build-troubleshooting.md # J6 clean 末步失败、固件排障 6.1、编译前分支核对
│       └── pr-merge.md              # reviewers 名单、飞书 open_id 表、PR 监控循环、CI 失败处置
└── problem-analysis/        # 重写为 4 阶段
    └── SKILL.md             # 复用 feature-development 的 references，不自建
```

### 三个 skill 职责边界

| skill | 职责 | 触发 |
| --- | --- | --- |
| story-creation | 立项（笔记 + JIRA Story） | 建笔记/建 Story/立项 |
| feature-development | 阶段 1~5 全程（吸收 dev-workflow 13 步） | 做需求/story 开发/走工作流 |
| problem-analysis | 问题单 4 阶段闭环（含 V2 修复验证） | 分析问题单/refuse |

### 数据流

```
问题单 ─→ problem-analysis（V2 分析 + 修复验证）
              ├─ 是问题 → story-creation 立项 → feature-development（老工作区开发，可对照 V2 已验证修复）
              └─ 不是问题 → refuse 关单
新需求 ─→ story-creation 立项 → feature-development
```

### 强制关卡规则（防 references 漏读）

- 主文件保留**全部日常命令与硬规则**（git SSH、编译命令、刷写命令、commit 格式），references 只放应急排障与名单映射
- feature-development：**开始第 2 阶段前必读 workspace-setup.md**（分支创建不可逆）；**创建 PR 前必读 pr-merge.md**（reviewers 漏加 PR 即废）；编译失败时读 build-troubleshooting.md
- problem-analysis：切环境前读 workspace-setup.md；编译失败读 build-troubleshooting.md

## 3. feature-development 内容映射

SKILL.md 主体 = 5 阶段骨架，每阶段标注来源步骤：

| 阶段 | 内容 | 来源 | 骨架中保留 | 拆到 references |
| --- | --- | --- | --- | --- |
| 1 需求解析与架构映射 | 调 story-creation 建笔记+Story；**新增**：docs/design/ 技术方案（所有需求必写，`YYYY-MM-DD-<工单号>-<主题>-design.md`：需求摘要、验收标准、BSW 模块影响分析（Dcm DID/RID / Dem Debouncing / PduR / Nvm）、修改点清单、验证方案）；Obsidian 笔记 Design 章节链接之 | step1-2 + 新增 | 全部 | — |
| 2 任务准备与环境隔离 | 确认项目/分支/仓库；SSH 切 develop 建分支（含 release 4.1 规则）；Y: 直编 | step3-4 | 命令骨架 | .imobuilder 映射、J6 双仓库、依赖仓库核对 → `workspace-setup.md`（关卡：建分支前必读） |
| 3 核心配置与编码 | Y: 直编、autosar 生成（5.1）、SSH 编译命令 | step5-6 | 全部日常命令 | J6 clean 末步失败、固件排障 6.1 → `build-troubleshooting.md`（编译失败时读） |
| 4 SIL 与台架验证 | 刷写（仅 J6）+ 手动验证停等 + DiagnosticTester | step7-8 | 全部 | — ；x86 SIL / LDC-OOP 校验器标注「后续迭代」 |
| 5 审查与合流 | commit/push、PR+飞书、PR 监控、笔记总结、自动关单、通知报告人 | step9-13 | 流程 + 命令 | reviewers 名单、open_id 表、监控循环细则、CI 失败处置 → `pr-merge.md`（关卡：创建 PR 前必读） |

其他要点：

- **frontmatter 触发词**：继承 dev-workflow 全部触发词（开发工作流/走工作流/做需求/story 开发/单步请求），实现无感替换
- **任务列表**：TaskCreate 每阶段 1 个任务（5 个），阶段内步骤在 skill 内列明；恢复粒度从 13 步变为 5 阶段
- **硬规则区**（git SSH / token / commit 格式）留在主文件尾部，problem-analysis 引用之
- 旧 step1（创建笔记）/step2（建 JIRA）细则留在 story-creation，feature-development 只写调用指引

## 4. problem-analysis 重写为 4 阶段

| 阶段 | 内容 | 来源 | 变化点 |
| --- | --- | --- | --- |
| 1 现场捕获与数据回放 | 拉问题单详情（复现步骤原样保存、附件下载留存）；现象固定——收集软硬件状态记录 | 旧 step1 | 增加「现象固定」提示；PSA 回放 / MCAP 解码标注「后续迭代」，当前手段为 description/附件/日志 |
| 2 知识召回与根因收敛 | ① 先检索 docs/analysis/ + Obsidian（ClaudeCodeNote）历史记录匹配同类问题；② 确认项目/分支/工作区（旧 step2）；③ V2 切环境 + 编译（旧 step3-4，命令细节复用 feature-development 及其 references）；④ 分析代码形成结论（旧 step5） | 旧 step2-5 | **知识召回前置且扩大到 Obsidian 笔记**；二分隔离/故障注入标注「后续迭代」 |
| 3 方案验证与精准修复 | **新增**：V2 工作区 Y: 直编修复 → 编译 → 刷板（仅 J6，tools/ProgramBoard，V2 路径；TDA4 无刷写工具，直接进入手动验证）→ 验证；最小化修改原则 | 新增（复用 feature-development 阶段 3-4 命令） | **突破旧规则「V2 不刷板不修复」**：仍不建分支、不 commit、不 push（改动留在 V2，git reset 可还原） |
| 4 经验沉淀与流程防腐 | ① 三处入库：docs/analysis/ + Obsidian 笔记 + JIRA 评论（旧 6.0）；② 分流：是问题 → 验证通过的修复转 feature-development 在老工作区正式建分支提交 PR（修复代码从 V2 拷贝或 cherry-pick）；不是问题 → refuse 关单（旧 6.2） | 旧 step6 | 分流目标改为 feature-development；是问题时多「V2 已验证修复」交接物 |

关键设计决策：

1. **V2 修复不提交**：阶段 3 的修复只是验证性修复（scratch 性质），正式代码必须走 feature-development 在老工作区重做提交——保持「V2 无污染、老工作区是唯一提交入口」红线
2. **交接物**：分流时明确告知 feature-development「V2 已验证的修复代码位置」，阶段 3 编码时对照 V2 改动移植
3. **编译排障引用**：主文件写「编译失败 → 读 feature-development/references/build-troubleshooting.md」，不再引用已删除的 dev-workflow 步骤号
4. **刷写命令**：V2 路径版本写进 problem-analysis 主文件（img-dir 指向 `Y:/01_Src/<workspace>_V2/src/...`）

## 5. 交叉引用清理清单

| 文件 | 改动 |
| --- | --- |
| `CLAUDE.md` | skill 入口表：dev-workflow 行 → feature-development（描述改 5 阶段）；problem-analysis 行描述改 4 阶段 |
| `story-creation/SKILL.md` | 2 处 dev-workflow 引用 → feature-development（文末边界章节 + frontmatter description） |
| `problem-analysis/SKILL.md` | 整体重写（含全部 9 处引用替换） |
| `docs/design/` 历史文档 | **不动**（存档性质） |
| `.claude/hooks/module_router.py` | 先查内容确认是否有 skill 名引用，有则同步改（预计无） |

## 6. 迁移顺序（单分支一次完成，每步可独立验证）

1. 新建 `feature-development/SKILL.md` + 3 个 references（内容从 dev-workflow 原文搬移重组，规则内容零删改）
2. 删除 `dev-workflow/` 目录
3. 重写 `problem-analysis/SKILL.md`
4. 改 `story-creation`（2 处）+ `CLAUDE.md`（2 行）+ 查 `module_router.py`
5. 全仓 grep 验证：dev-workflow 在 `.claude/`、`CLAUDE.md` 中清零（docs/ 存档除外）

## 7. 验证标准

- **内容零丢失**：dev-workflow 原文每条规则（13 步、4.1、5.1、6.1、10.1-10.3、12/13 步细则、事故经验）在新结构中均有落点——对照表逐项核对
- **引用闭环**：grep 确认所有 references 路径存在；feature-development 与 problem-analysis 交叉引用方向正确
- **触发词覆盖**：新 skill description 覆盖 dev-workflow 全部旧触发词，用户口语指令不受影响
- **frontmatter 合法**：name/description 格式与 story-creation 现有风格一致
- **新会话冒烟**：重开 Claude Code 会话确认 skills 列表出现 feature-development / problem-analysis（旧名消失）

## 8. 不做的事

- 不动 tools/、tests/harness/、hooks 逻辑（module_router 仅在查实有引用时改名字符串）
- 不删 docs/ 历史文档
- 不实现 x86 SIL、LDC/OOP 校验、PSA 回放、MCAP 解码、二分隔离/故障注入——各阶段标注「后续迭代」占位
- 不改 V2/老工作区的服务器端任何状态

## 9. 后续迭代项（本次不实现）

| 能力 | 落点 | 说明 |
| --- | --- | --- |
| x86 SIL 隔离验证 | feature-development 阶段 4 | 不依赖 ECU 硬件的黑白盒测试 |
| LDC/OOP 配置一致性校验 | feature-development 阶段 4 | 命令行校验器接入 |
| PSA 报文回放 / MCAP 解码 | problem-analysis 阶段 1 | 实车/台架通信时序脱机复现 |
| 二分法隔离 / 故障注入 | problem-analysis 阶段 2 | 可疑模块上下切断 + 伪造输入定位 |
