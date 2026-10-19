# develop_workflow 项目结构整合实施计划

> ⚠️ **历史文档**：本文中"Y: 直编"等编码方式已于 2026-10-19 废止（Y: 盘仅许刷写读镜像/读代码/写 .imobuilder，代码写与 git 操作一律 SSH），设计文档模板也已重构——现行规则以 `CLAUDE.md` 与 skill 为准，本文仅作历史记录。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 dev-workflow / story-creation 两个 skill 与 10_tools 下 6 个工具整合为标准化的 develop_workflow 项目结构（依据 `docs/design/2026-10-15-develop-workflow-restructure-design.md`）。

**Architecture:** 目录骨架 + 工具副本（删 .git，tools/ 成为运行时权威源）+ skill 原样搬入并修订 4 处引用 + 顶层 CLAUDE.md 硬规则 + PreToolUse hook 模块分流提醒（TDD：selftest 先行）+ tests/harness 两个测试桩 + git init 统一仓库。

**Tech Stack:** Windows git bash、Python 3（hooks 与 harness 桩）、Claude Code hooks（PreToolUse JSON 协议）、git。

**工作目录：** `D:\Workspace\01_Projects\02_Src\11_AI\develop_workflow`（下文所有相对路径基于此）

**约定：** 本工程自身的 commit 无 JIRA 工单号，消息格式用 `feat(workflow): <描述>`（全局 [工单号] 格式适用于 MCU 仓库，此处从简）。

---

### Task 1: 目录骨架 + 工具复制与清理

**Files:**
- Create: 目录 `tools/autosar_gen/`、`tools/`、`docs/analysis/`、`tests/harness/`、`.claude/skills/`、`.claude/hooks/`
- Create（复制副本）: `tools/autosar_gen/{Dcm,Dem,Nvm}_AutoGen/`、`tools/{DiagnosticTester,LogCollection,ProgramBoard}/`

- [ ] **Step 1: 建目录骨架**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow" && mkdir -p tools/autosar_gen docs/analysis tests/harness .claude/skills .claude/hooks
```

期望：无报错。

- [ ] **Step 2: 复制 6 个工具（含全部内容）**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow" && \
cp -r "D:/Workspace/01_Projects/02_Src/10_tools/Dcm_AutoGen" tools/autosar_gen/ && \
cp -r "D:/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen" tools/autosar_gen/ && \
cp -r "D:/Workspace/01_Projects/02_Src/10_tools/Nvm_AutoGen" tools/autosar_gen/ && \
cp -r "D:/Workspace/01_Projects/02_Src/10_tools/DiagnosticTester" tools/ && \
cp -r "D:/Workspace/01_Projects/02_Src/10_tools/LogCollection" tools/ && \
cp -r "D:/Workspace/01_Projects/02_Src/10_tools/ProgramBoard" tools/
```

注意：文件量大（含 vendor DLL、镜像目录），可能耗时数分钟。期望：退出码 0，10_tools 原处不动。

- [ ] **Step 3: 删除副本中的 .git / __pycache__ / logs 运行残留**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow" && \
find tools -name .git -type d -exec rm -rf {} + ; \
find tools -name __pycache__ -type d -exec rm -rf {} + ; \
find tools -name .pytest_cache -type d -exec rm -rf {} + ; \
rm -rf tools/DiagnosticTester/logs tools/LogCollection/logs tools/ProgramBoard/logs ; true
```

- [ ] **Step 4: 验证复制结果**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow" && \
ls tools/autosar_gen tools/ && \
find tools -name .git | wc -l && find tools -name __pycache__ | wc -l
```

期望：`tools/autosar_gen` 下有 Dcm_AutoGen/Dem_AutoGen/Nvm_AutoGen；`tools/` 下有 DiagnosticTester/LogCollection/ProgramBoard/autosar_gen；两个 `wc -l` 均输出 `0`；`tools/DiagnosticTester/testcase/` 下 n60/rx/t1lfl1/t75 用例资产仍在。

### Task 2: tools/README.md + 迁移说明文档

**Files:**
- Create: `tools/README.md`
- Create: `docs/analysis/2026-10-15-tools-migration.md`

- [ ] **Step 1: 写 tools/README.md**

```markdown
# tools/ — 运行时权威源

本目录是 6 个开发辅助工具的**运行时权威源**，2026-10-15 从 `D:\Workspace\01_Projects\02_Src\10_tools` 复制迁入。

- `10_tools` 原处已**冻结**：仅作迁移前备份保留，不再更新
- 工具的后续迭代在**本目录**进行（随 develop_workflow 统一 git 仓库管理）
- 迁入时删除了各工具原 `.git` 历史（历史仍在 10_tools 备份中）及 `__pycache__`/`logs` 运行残留

## 工具清单

| 目录 | 用途 | 开发工作流中的角色 |
| --- | --- | --- |
| `autosar_gen/Dcm_AutoGen` | DCM 配置代码生成 | autosar 生成，目标为 D: 本地路径 |
| `autosar_gen/Dem_AutoGen` | DEM 配置代码生成 | 同上 |
| `autosar_gen/Nvm_AutoGen` | NVM 配置代码生成 | 同上 |
| `DiagnosticTester` | UDS 诊断测试（CAN/CANFD） | 第 8 步诊断功能验证（写 testcase 跑脚本） |
| `LogCollection` | MCU 日志采集（J6B/N60，串口+SFTP） | 问题分析日志采集 |
| `ProgramBoard` | 板子一键刷写（fastboot） | 第 7 步固件刷写（仅 J6） |
```

- [ ] **Step 2: 写 docs/analysis/2026-10-15-tools-migration.md**

```markdown
# 工具迁移记录：10_tools → develop_workflow/tools

- 日期：2026-10-15
- 性质：结构整合个案（非故障排障，留档备查）

## 结论

6 个工具（3 个 autosar_gen + DiagnosticTester/LogCollection/ProgramBoard）以复制副本方式迁入 `develop_workflow/tools/`。**tools/ 为运行时权威源，10_tools 冻结为迁移前备份**。副本 `.git` 已删除，工具随 develop_workflow 统一 git 仓库管理。

## 影响与注意事项

- skill（dev-workflow）中工具路径引用已同步改为 tools/ 绝对路径
- 旧 `.git` 历史需要回溯时去 10_tools 备份查（`git -C 10_tools/<工具> log`）
- 今后任何工具改动只改 tools/ 副本；10_tools 不再更新，避免双源分叉
```

- [ ] **Step 3: Commit（与 Task 3、4 合并提交也可，此处先不提交，统一在 Task 8 首提交）**

本任务无独立 commit（工程尚未 git init，首提交在 Task 8）。

### Task 3: story-creation skill 搬入（原样，零修订）

**Files:**
- Create: `.claude/skills/story-creation/SKILL.md`（复制自 `C:\Users\YH\.claude\skills\story-creation\SKILL.md`）
- Create: `.claude/skills/story-creation/references/projects.md`（复制）

- [ ] **Step 1: 复制 skill 文件**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow" && \
cp -r "C:/Users/YH/.claude/skills/story-creation" .claude/skills/
```

- [ ] **Step 2: 验证**

```bash
diff -r "C:/Users/YH/.claude/skills/story-creation" .claude/skills/story-creation
```

期望：无输出（完全一致）。C 盘原 skill 保留不动（用户指示暂不删除）。

### Task 4: dev-workflow skill 搬入 + 4 处修订

**Files:**
- Create: `.claude/skills/dev-workflow/SKILL.md`（复制后修订）
- Modify: `.claude/skills/dev-workflow/SKILL.md`（4 处，见下）

- [ ] **Step 1: 复制 skill 文件**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow" && \
cp -r "C:/Users/YH/.claude/skills/dev-workflow" .claude/skills/
```

- [ ] **Step 2: 修订 ① — 「开始前确认」之前插入路径角色表**

在 `.claude/skills/dev-workflow/SKILL.md` 中，`## 开始前确认` 行之前插入：

```markdown
## 路径角色

| 路径 | 角色 |
| --- | --- |
| `D:\Workspace\01_Projects\02_Src` | 本地代码，**autosar 代码生成专用**（develop_workflow/tools/autosar_gen 生成目标） |
| `10.0.12.42:/comp/user_data/yaohua/01_Src` | 服务器，**编译/代码分析/代码修复** |
| `Y:\01_Src`（服务器映射，同一文件系统） | 服务器代码在 Windows 侧的编辑入口（改代码走 Y: 直编） |

---
```

- [ ] **Step 3: 修订 ② — 第 5 步末尾补 autosar 生成场景**

在第 5 步「- release 分支（第二个分支）：可直接 cherry-pick …」条目之后、「## 第 6 步」之前插入：

```markdown
### 5.1 autosar 生成代码场景

Dcm/Dem/Nvm 配置类需求使用 `D:\Workspace\01_Projects\02_Src\11_AI\develop_workflow\tools\autosar_gen\` 下工具生成代码：

- 生成目标为 D: 本地路径（`D:\Workspace\01_Projects\02_Src`，autosar 专用）
- 产物需进入服务器仓库时，从 D: 拷贝同步到 Y: 对应仓库路径，再走第 9 步 SSH 提交
```

- [ ] **Step 4: 修订 ③ — 第 7 步工具路径改指 tools/**

`.claude/skills/dev-workflow/SKILL.md` 中 3 处替换（replace_all 处理第 7 步内两处 10_tools 路径）：

1. old: `D:\Workspace\01_Projects\02_Src\10_tools\ProgramBoard\` → new: `D:\Workspace\01_Projects\02_Src\11_AI\develop_workflow\tools\ProgramBoard\`
2. old: `cd D:/Workspace/01_Projects/02_Src/10_tools/ProgramBoard` → new: `cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/ProgramBoard`

- [ ] **Step 5: 修订 ④ — 第 8 步补诊断验证方式**

将「## 第 8 步：手动验证 —— 停下等待」一节整体替换为：

```markdown
## 第 8 步：手动验证 —— 停下等待

用户手动验证（台架/功能验证）。验证通过后用户会说继续。

诊断功能验证用 `D:\Workspace\01_Projects\02_Src\11_AI\develop_workflow\tools\DiagnosticTester`：自己写 testcase（`testcase/<项目>/<用例>/<用例>.yaml`，写法见该目录 README.md），然后跑脚本验证：

```bash
python DiagnosticTester.py run testcase/<项目>/<用例>/<用例>.yaml --config configs/<项目>/<配置>.yaml
```

测试桩（转发器）见 `develop_workflow/tests/harness/diag_test/`。
```

- [ ] **Step 6: 验证修订结果**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow" && \
grep -c "10_tools" .claude/skills/dev-workflow/SKILL.md ; \
grep -n "路径角色\|5.1 autosar\|DiagnosticTester\|11_AI/develop_workflow/tools" .claude/skills/dev-workflow/SKILL.md | head
```

期望：`10_tools` 计数为 `0`；四项修订关键词均能 grep 到。

### Task 5: 顶层 CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: 写 CLAUDE.md**

```markdown
# develop_workflow 硬规则

## 安全红线

- **git 写操作禁止 Windows 本地执行**：`Y:\01_Src` 是服务器 10.0.12.42（`/comp/user_data/yaohua/01_Src`）的网络映射，本地 git `core.autocrlf=true` 会把工作区文件改写成 CRLF 污染服务器仓库（曾实际污染 3432 个文件）。reset/clean/checkout/commit/push 一律 `ssh yaohua@10.0.12.42` 执行
- 本地 Y: 盘 git 命令仅限只读，且必须加 `-c core.filemode=false`
- **Token 安全**：JIRA/Bitbucket token 从 `C:\Users\YH\.claude\` 下配置读取，绝不内联进任何会被提交的文件；`.imobuilder` 含 CI token，不要暴露其内容
- **commit 格式**（MCU 仓库，全局规则）：`feat(模块名): [工单号] 项目名 + 描述`

## 路径角色

| 路径 | 角色 |
| --- | --- |
| `D:\Workspace\01_Projects\02_Src` | 本地代码，**autosar 代码生成专用**（tools/autosar_gen 生成目标） |
| `10.0.12.42:/comp/user_data/yaohua/01_Src` | 服务器：**编译/代码分析/代码修复** |
| `Y:\01_Src`（服务器映射，同一文件系统） | 服务器代码在 Windows 侧的编辑入口 |

## 先检索再动手

分析问题时先查 `docs/analysis/` 是否有同类问题、`docs/design/` 是否有类似设计方案——有则复用/更新，无则新建沉淀（排障个案写进 analysis/，较大改动方案写进 design/）。

## 目录约定

- `docs/analysis/` 具体问题个案报告；`docs/design/` 设计方案
- `tests/harness/` 测试桩：DiagnosticTester 跑测试用例、LogCollection 采集 MCU 日志分析
- `tools/` 工具**运行时权威源**（10_tools 已冻结不再更新，工具迭代在这里做）

## skill 入口

- 立项（建 Obsidian 笔记 / 建 JIRA Story）→ `story-creation`
- 开发全流程（分支/编译/刷写/验证/PR/收尾）→ `dev-workflow`
```

- [ ] **Step 2: 验证**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow" && wc -l CLAUDE.md
```

期望：约 35-45 行。

### Task 6: hooks 模块分流提醒（TDD）

**Files:**
- Create: `.claude/hooks/selftest.py`（测试先行）
- Create: `.claude/hooks/module_router.py`（实现）
- Create: `.claude/settings.json`（hook 注册）

- [ ] **Step 1: 写自测脚本（失败测试）**

`.claude/hooks/selftest.py`：

```python
"""module_router 自测：正/负样例，可独立重跑。用法：python selftest.py"""
import module_router

CASES = [
    # (输入命令片段, 期望提醒包含的关键词 or None=不应触发)
    ("确认 c06g 项目的分支归属", "GWM 项目分流"),
    ("de09g 需求要改 mcu 仓库", "GWM 项目分流"),
    ('ssh yaohua@10.0.12.42 "cd /comp/user_data/yaohua/01_Src/02_Workspace_J6 && imobuilder build mcu_app_j6 -r -x parking_dr uper_app"', "依赖仓库分支"),
    ("python tools/autosar_gen/Dcm_AutoGen/Dcm_AutoGen.py --input x.xlsx", "autosar 生成目标"),
    ("python tools/autosar_gen/Nvm_AutoGen/Nvm_AutoGen.py", "autosar 生成目标"),
    ("git -C Y:/01_Src/02_Workspace_J6/src/mcu_app_j6 checkout develop", "硬规则"),
    ("cd tools/ProgramBoard && python ProgramBoard_j6b.py --help", None),
    ("ls D:/Workspace/01_Projects/02_Src", None),
    ('ssh yaohua@10.0.12.42 "cd mcu_app_j6 && git status"', None),
    ("git -c core.filemode=false -C Y:/01_Src/01_Workspace_TDA4 log --oneline", None),
]

for cmd, expect in CASES:
    notes = module_router.check(cmd)
    text = "；".join(notes)
    if expect is None:
        assert not notes, f"不应触发却触发: {cmd!r} -> {text!r}"
    else:
        assert expect in text, f"应含『{expect}』: {cmd!r} -> {text!r}"

print(f"selftest OK: {len(CASES)} cases passed")
```

- [ ] **Step 2: 运行确认失败**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/.claude/hooks" && python selftest.py
```

期望：FAIL，`ModuleNotFoundError: No module named 'module_router'`。

- [ ] **Step 3: 实现 module_router.py**

```python
"""模块分流提醒 hook（PreToolUse / Bash）：关键词检测，只提醒不拦截。

stdin 收 Claude Code hooks JSON；无匹配静默 exit 0；有匹配输出
permissionDecision=allow + 提醒文本（permissionDecisionReason 会注入模型上下文）。
自测：python selftest.py
"""
import json
import re
import sys


def check(command: str) -> list:
    notes = []
    c = command.lower()
    if re.search(r"gwm|c06g|de09g", c):
        notes.append(
            "GWM 项目分流：按具体车型 cpj 目录实际所在仓库确认归属——mcu_app_j6_v2 是新仓库，"
            "v2 已有的项目不再用 mcu_app_j6；两仓库都有 cpj_gwm 目录，不能只按 OEM 判断，拿不准问用户"
        )
    if "imobuilder" in c and ("02_workspace_j6" in c or "mcu_app_j6" in c):
        notes.append(
            "J6 编译前核对 workspace 依赖仓库分支：mcu 与 zos_msg 等依赖仓库必须同分支，"
            "否则出现接口不匹配类编译错误（如 ipc_cfg_message.hpp: expected class name）"
        )
    if re.search(r"y:", c) and re.search(r"\bgit\b.*\b(reset|checkout|commit|clean|push|merge|rebase)\b", c):
        notes.append(
            "硬规则：Y: 盘 git 写操作禁止本地执行（CRLF 污染服务器仓库），一律 ssh yaohua@10.0.12.42；"
            "本地仅只读且必须加 -c core.filemode=false"
        )
    if re.search(r"dcm_autogen|dem_autogen|nvm_autogen", c):
        notes.append(
            "autosar 生成目标为 D: 本地路径（D:\\Workspace\\01_Projects\\02_Src，autosar 专用）；"
            "产物进服务器仓库需经 Y: 拷贝同步"
        )
    return notes


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    if data.get("tool_name") != "Bash":
        sys.exit(0)
    command = data.get("tool_input", {}).get("command", "")
    notes = check(command)
    if not notes:
        sys.exit(0)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "；".join(notes),
        }
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑自测确认通过**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/.claude/hooks" && python selftest.py
```

期望：`selftest OK: 10 cases passed`。

注意：case 10（`git -c core.filemode=false -C Y:/... log`）是只读命令不应触发——规则用 git 后接写子动词（reset/checkout/commit/clean/push/merge/rebase）才命中，`log` 不在列表，通过。若 case 9 因 `mcu_app_j6` + 无 imobuilder 判定正确不触发，则规则边界正确。

- [ ] **Step 5: 端到端管道验证 hook 协议**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow" && \
echo '{"tool_name":"Bash","tool_input":{"command":"git -C Y:/01_Src/x checkout develop"}}' | python .claude/hooks/module_router.py
```

期望：stdout 输出 JSON，含 `"permissionDecision": "allow"` 与「硬规则」提醒文本。

再验证无匹配静默：

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"ls D:/x"}}' | python .claude/hooks/module_router.py ; echo "exit=$?"
```

期望：无 stdout 输出，`exit=0`。

- [ ] **Step 6: 注册到 settings.json**

`.claude/settings.json`：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/module_router.py\""
          }
        ]
      }
    ]
  }
}
```

### Task 7: tests/harness 测试桩

**Files:**
- Create: `tests/harness/README.md`
- Create: `tests/harness/diag_test/run_case.py`
- Create: `tests/harness/diag_test/case_example.yaml`
- Create: `tests/harness/mcu_log/collect_mcu_log.py`

- [ ] **Step 1: 写 diag_test/run_case.py（DiagnosticTester 跑用例桩）**

```python
"""诊断测试桩：转发 tools/DiagnosticTester 跑指定测试用例（第 8 步诊断功能验证用）。

用法（真板在线）：
  python run_case.py --testcase case_example.yaml --config <DT目录>/configs/rx/rx_cx.yaml
  python run_case.py --testcase <用例.yaml> --config <配置.yaml> [DiagnosticTester 额外参数透传]

退出码透传 DiagnosticTester（0 全 PASS / 1 有 FAIL / 2 配置错 / 3 运行期异常）。
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DT = ROOT / "tools" / "DiagnosticTester" / "DiagnosticTester.py"


def main():
    ap = argparse.ArgumentParser(description="DiagnosticTester 用例转发桩")
    ap.add_argument("--testcase", required=True, help="测试用例 yaml 路径")
    ap.add_argument("--config", required=True, help="项目配置 yaml 路径")
    args, extra = ap.parse_known_args()
    cmd = [sys.executable, str(DT), "run", args.testcase, "--config", args.config, *extra]
    print(f"[diag_test] {' '.join(str(c) for c in cmd)}")
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 写 diag_test/case_example.yaml（示例用例）**

```yaml
steps:
  - name: 进扩展会话
    request: "1003"
    expect: "5003"
  - name: 读软件版本 DID F195
    request: "22F195"
    expect: "62F195"
on_fail: abort
```

- [ ] **Step 3: 写 mcu_log/collect_mcu_log.py（LogCollection 采集桩）**

```python
"""MCU 日志采集桩：转发 tools/LogCollection/collect_j6b.py（需板子 A 核串口 + 板子在线）。

用法：
  python collect_mcu_log.py --port COM30 --project Rx            # 采集 /log/mcu
  python collect_mcu_log.py --port COM30 --project Rx --dry-run  # 仅列文件清单不下载

日志落盘：tools/LogCollection/logs/<项目>/mcu_<时间戳>/。
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LC = ROOT / "tools" / "LogCollection" / "collect_j6b.py"


def main():
    ap = argparse.ArgumentParser(description="LogCollection 采集转发桩")
    ap.add_argument("--port", required=True, help="板子 A 核串口 COM 号")
    ap.add_argument("--project", required=True, help="项目名（日志保存到 logs/<项目>/）")
    ap.add_argument("--dry-run", action="store_true", help="仅列文件清单")
    args, extra = ap.parse_known_args()
    cmd = [sys.executable, str(LC), "--port", args.port, "--project", args.project]
    if args.dry_run:
        cmd.append("--dry-run")
    cmd += extra
    print(f"[mcu_log] {' '.join(str(c) for c in cmd)}")
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 写 tests/harness/README.md**

```markdown
# tests/harness — 测试桩

针对具体问题和工具功能的测试隔离桩：高度解耦、可独立重跑。

## diag_test/ — DiagnosticTester 跑测试用例（第 8 步诊断功能验证）

```bash
cd tests/harness/diag_test
python run_case.py --testcase case_example.yaml --config ../../tools/DiagnosticTester/configs/<项目>/<配置>.yaml
```

- 用例写法见 `tools/DiagnosticTester/README.md`（steps/on_fail/timing 三节）
- 新需求验证：在 diag_test/ 或工具 `testcase/<项目>/` 下写用例 yaml，换 `--config` 切项目
- 退出码：0 全 PASS / 1 有 FAIL/TIMEOUT / 2 配置错 / 3 运行期异常

## mcu_log/ — LogCollection 采集 MCU 日志分析

```bash
cd tests/harness/mcu_log
python collect_mcu_log.py --port <A核串口COM号> --project <项目> [--dry-run]
```

- 需板子在线（A 核串口 + 板子 SSH 可达）；流程：串口 pfctl -d 使能 SSH → SFTP 拉 /log/mcu
- 日志落盘 `tools/LogCollection/logs/<项目>/mcu_<时间戳>/`
```

- [ ] **Step 5: 冒烟验证三个工具副本可运行**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow" && \
python tools/ProgramBoard/ProgramBoard_j6b.py --help > /dev/null && echo "ProgramBoard OK" ; \
python tools/LogCollection/collect_j6b.py --help > /dev/null && echo "LogCollection OK" ; \
python tools/DiagnosticTester/DiagnosticTester.py --help > /dev/null && echo "DiagnosticTester OK"
```

期望：三行 OK（DiagnosticTester.py 顶层无 --help 子命令时验证 `run --help`；若 import 失败会抛 ModuleNotFoundError）。

- [ ] **Step 6: 跑 DiagnosticTester 自带测试套件（副本完整性验证）**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/DiagnosticTester" && python -m pytest tests/ -v 2>&1 | tail -5
```

期望：全部 PASS（如缺 pytest 则 `python -m pip install pytest` 后重跑）。若因复制丢文件失败，对照 10_tools 原目录补齐。

### Task 8: git init + .gitignore + 首提交

**Files:**
- Create: `.gitignore`
- Create: git 仓库（`git init`）

- [ ] **Step 1: git init + 写 .gitignore**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow" && git init
```

`.gitignore`：

```gitignore
__pycache__/
*.pyc
.pytest_cache/
logs/
*.log
```

- [ ] **Step 2: 核对暂存内容（防止运行残留入库）**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow" && \
git add -A . && git status --short | head -30 && git status --short | wc -l
```

期望：无 `__pycache__`、`logs/`、`.log` 条目；有 CLAUDE.md、.claude/、docs/、tests/、tools/（含 testcase 用例资产）。若 testcase 下出现时间戳运行目录（形如 `20261015_143025/`），用 `git rm -r --cached` 排除。

- [ ] **Step 3: 首提交**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow" && \
git commit -m "feat(workflow): initialize develop_workflow project structure

整合 dev-workflow/story-creation skills 与 10_tools 六工具为统一结构：
CLAUDE.md 硬规则 + .claude/{skills,hooks} + docs/{analysis,design} + tests/harness + tools（运行时权威源）
"
```

期望：提交成功。远端上传由用户后续决定，本任务不 push。

### Task 9: 终验（对照设计 §7 验证标准）

- [ ] **Step 1: 结构对照**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow" && \
find . -path ./.git -prune -o -type d -print | grep -v "tools/" | sort
```

期望：与设计 §2 目录树一致（.claude/hooks、.claude/skills/{dev-workflow,story-creation}、docs/analysis、docs/design、tests/harness/{diag_test,mcu_log}）。

- [ ] **Step 2: hook selftest 复跑 + skill 引用核对**

```bash
cd "D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow" && \
python .claude/hooks/selftest.py && \
grep -rc "10_tools" .claude/skills/ CLAUDE.md | grep -v ":0" ; echo "ref-check exit=$?"
```

期望：`selftest OK: 10 cases passed`；`10_tools` 引用清零（grep -v ":0" 无输出，`ref-check exit=1` 属预期——grep 无匹配）。

注意：`.claude/skills/story-creation/SKILL.md` 含「10_tools」吗——不含（该 skill 无工具路径引用）；若 grep 发现残留，逐条改为 tools/ 新路径。

- [ ] **Step 3: 会话级验证（人工）**

在 develop_workflow 目录重开 Claude Code 会话，确认：skills 列表出现本项目的 `dev-workflow`、`story-creation`；执行任一 Bash 命令（含 GWM 或 autosar 关键词）可见 hook 提醒注入。此步需人工确认后勾选。

---

## Self-Review 结论

- **Spec 覆盖**：设计 §2（Task 1/3/4/5/6/7）、§3（Task 5）、§4（Task 6 TDD）、§5（Task 1-4 + Task 2 迁移说明）、§6（Task 7）、§7（Task 6/7/9）、§8（Task 8）——全覆盖
- **占位符**：无 TBD/TODO；所有代码步骤含完整代码
- **类型/路径一致性**：`module_router.check()` 在 selftest 与实现中签名一致；harness 桩 `parents[3]` 相对层级（diag_test/mcu_log → harness → tests → root）两处一致；工具路径统一用 `D:\Workspace\01_Projects\02_Src\11_AI\develop_workflow\tools\...`
