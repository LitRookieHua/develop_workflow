"""module_router 自测：正/负样例，可独立重跑。用法：python selftest.py"""
import module_router

CASES = [
    # (输入命令片段, 期望提醒包含的关键词 or None=不应触发)
    ('ssh yaohua@10.0.12.42 "cd /comp/user_data/yaohua/01_Src/02_Workspace_J6 && imobuilder build mcu_app_j6 -r -x parking_dr uper_app"', "依赖仓库分支"),
    ("python tools/autosar_gen/Dcm_AutoGen/Dcm_AutoGen.py --input x.xlsx", "autosar 生成目标"),
    ("python tools/autosar_gen/Nvm_AutoGen/Nvm_AutoGen.py", "autosar 生成目标"),
    ("git -C Y:/01_Src/02_Workspace_J6/src/mcu_app_j6 checkout develop", "硬规则"),
    ("cd tools/ProgramBoard && python ProgramBoard_j6b.py --help", None),
    ("ls D:/Workspace/01_Projects/02_Src", None),
    ('ssh yaohua@10.0.12.42 "cd mcu_app_j6 && git status"', None),
    ("git -c core.filemode=false -C Y:/01_Src/01_Workspace_TDA4 log --oneline", None),
    ("git add -A && git commit -m \"fix proxy: timeout\"", None),
]

for cmd, expect in CASES:
    notes = module_router.check(cmd)
    text = "；".join(notes)
    if expect is None:
        assert not notes, f"不应触发却触发: {cmd!r} -> {text!r}"
    else:
        assert expect in text, f"应含『{expect}』: {cmd!r} -> {text!r}"

print(f"selftest OK: {len(CASES)} cases passed")
