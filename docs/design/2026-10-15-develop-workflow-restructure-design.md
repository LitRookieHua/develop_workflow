# develop_workflow 工作流项目结构整合设计

- 日期：2026-10-15
- 状态：已确认
- 背景：将 `C:\Users\YH\.claude\skills\` 下的 dev-workflow、story-creation 两个 skill 与 `D:\Workspace\01_Projects\02_Src\10_tools` 下的 6 个工具，整合为标准化的 `develop_workflow` 项目结构，用于优化结构、沉淀积累。

## 1. 目标与约束

- 日常 Claude 会话在 `D:\Workspace\01_Projects\02_Src\11_AI\develop_workflow` 目录启动，项目级 skill 就地生效
- skill 内容原样搬入（不拆分 references），仅修订工具路径等少量引用
- 工具以**复制副本**方式进入 `tools/`，副本的 `.git` 删除，整个工程后续作为一个独立 git 仓库统一管理
- `10_tools` 原处保留不动（迁移前备份），今后不再更新，工具迭代在 `tools/` 副本上做（**运行时权威源**）
- C 盘 skill 路径暂不删除

## 2. 目录结构

```
develop_workflow/
├── CLAUDE.md                  # 顶层硬规则（见 §3）
├── .claude/
│   ├── settings.json          # 注册模块分流提醒 hook
│   ├── skills/
│   │   ├── dev-workflow/      # 原样搬入 + §5 修订
│   │   └── story-creation/    # 原样搬入（SKILL.md + references/）
│   └── hooks/
│       ├── module_router.py   # 模块分流提醒脚本
│       └── selftest.py        # hook 自测（样例输入/期望输出对）
├── docs/
│   ├── analysis/              # 具体问题（个案排障报告）
│   └── design/                # 设计方案
├── tests/
│   └── harness/               # 测试桩（见 §6）
└── tools/                     # 运行时权威源（副本，无 .git）
    ├── autosar_gen/
    │   ├── Dcm_AutoGen/
    │   ├── Dem_AutoGen/
    │   └── Nvm_AutoGen/
    ├── DiagnosticTester/
    ├── LogCollection/
    ├── ProgramBoard/
    └── README.md              # 说明权威源地位与 10_tools 冻结状态
```

数据流：会话在本目录启动 → CLAUDE.md 硬规则自动加载 → 用户触发 `.claude/skills/dev-workflow` → 第 7 步刷写调用 `tools/ProgramBoard`，第 8 步诊断验证调用 `tools/DiagnosticTester`。

## 3. 顶层 CLAUDE.md 内容

### 3.1 硬规则

- git 写操作（reset/clean/checkout/commit/push）禁止 Windows 本地执行，一律 SSH `yaohua@10.0.12.42`
- 本地 Y: 盘 git 命令仅只读，且必须 `-c core.filemode=false`（CRLF/mode 位污染教训）
- commit 格式：`feat(模块名): [工单号] 项目名 + 描述`
- Token 安全：JIRA/Bitbucket token 从 `C:\Users\YH\.claude\` 配置读取，绝不内联进任何会被提交的文件
- **先检索再动手**：分析问题时先查 `docs/analysis/` 是否有同类问题、`docs/design/` 是否有类似设计方案，有则复用/更新，无则新建

### 3.2 路径角色表

| 路径 | 角色 |
| --- | --- |
| `D:\Workspace\01_Projects\02_Src` | 本地代码，**autosar 代码生成专用**（tools/autosar_gen 生成目标） |
| `10.0.12.42:/comp/user_data/yaohua/01_Src` | 服务器，**编译/代码分析/代码修复** |
| `Y:\01_Src`（服务器映射，同一文件系统） | 服务器代码在 Windows 侧的编辑入口（改代码走 Y: 直编） |

### 3.3 目录结构约定

- `docs/analysis/` 具体问题个案；`docs/design/` 设计方案
- `tests/harness/` 测试桩（DiagnosticTester 跑用例、LogCollection 采日志）
- `tools/` 运行时权威源；10_tools 已冻结，工具迭代在 tools/ 做

### 3.4 skill 入口指引

- 立项（建笔记/建 Story）→ `story-creation`
- 开发全流程（分支/编译/刷写/验证/PR/收尾）→ `dev-workflow`

CLAUDE.md 保持精炼（~40 行级），细节留在 skill，不重复。

## 4. hooks 模块分流提醒

PreToolUse 针对 Bash 命令关键词检测，**只提醒不拦截**：

| 检测信号 | 提醒内容 |
| --- | --- |
| GWM 车型关键词（c06g/de09g 等） | 按车型 cpj 目录实际所在仓库确认归属（v2 是新仓库，v2 有的项目不再用 mcu_app_j6；两仓库都有 `cpj_gwm`，不能只按 OEM 判断） |
| J6 编译命令（`imobuilder` + J6 路径） | 核对 workspace 依赖仓库（zos_msg 等）分支与 mcu 一致，防接口不匹配 |
| Y: 盘本地 git 写命令 | 硬规则提醒：git 写操作走 SSH，本地仅只读加 filemode |
| autosar 生成调用（Dcm/Dem/Nvm_AutoGen） | 生成目标是 D: 本地路径（autosar 专用），产物进服务器需经 Y: 拷贝同步 |

实现：`module_router.py` 单文件（规则表 + 命令解析），`settings.json` 注册，`selftest.py` 内置正/负样例可独立重跑。

不做：流程顺序追踪（skill 内 TaskCreate 已覆盖）、定时催审。

## 5. 迁移与修订清单

### 5.1 工具复制

- `10_tools/{Dcm,Dem,Nvm}_AutoGen` → `tools/autosar_gen/`；`10_tools/{DiagnosticTester,LogCollection,ProgramBoard}` → `tools/`
- 复制后删除各副本的 `.git`、`__pycache__`、`logs/` 运行残留
- 10_tools 原处不动

### 5.2 dev-workflow SKILL.md 修订（仅以下几处，其余原样）

1. 路径角色表加入「开始前确认」之前
2. 第 5 步：补充 autosar 生成场景（生成目标 D: 本地路径，产物经 Y: 同步进服务器仓库）
3. 第 7 步：`10_tools/ProgramBoard` 路径 → `tools/ProgramBoard`
4. 第 8 步：手动验证补充「诊断功能验证用 tools/DiagnosticTester，自己写 testcase 跑脚本验证」

### 5.3 story-creation

原样搬入（SKILL.md + references/projects.md），零内容修订。

### 5.4 其他

- CLAUDE.md 新建（§3 内容）
- hooks + settings.json（§4）
- `docs/analysis/` 放本次迁移说明一份

## 6. tests/harness 测试桩

存放针对具体问题和工具功能的测试隔离桩，初始两个：

1. **DiagnosticTester 跑测试用例**：诊断功能验证桩（第 8 步验证用）
2. **LogCollection 采集 MCU 日志分析**：日志采集分析桩

要求：高度解耦、可独立重跑。

## 7. 验证标准

- hook selftest 跑通：4 类检测信号各有正/负样例
- skill 引用核对：SKILL.md 中 `10_tools` 字样清零，tools/ 下 6 个工具可寻址
- 工具冒烟：DiagnosticTester / LogCollection / ProgramBoard 副本可运行（`python -c import` 或 `--help`）
- CLAUDE.md / 目录结构与本设计一致

## 8. Git 策略

- develop_workflow 本身 `git init`，工具副本 `.git` 已删除，作为普通目录纳入统一仓库
- 首 commit 纳入 CLAUDE.md / .claude / docs / tests / tools（README）
- 上传远端时机由用户后续决定
