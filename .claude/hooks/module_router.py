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
    if re.search(r"\by:", c) and re.search(r"\bgit\b.*\b(reset|checkout|commit|clean|push|merge|rebase)\b", c):
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
    command = (data.get("tool_input") or {}).get("command", "")
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
    # win32: 管道下 Python stdout 默认 locale 编码（cp936），Claude Code 按 UTF-8 读 hook 输出会乱码
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
