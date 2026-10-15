#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nvm_autogen_etas - ETAS NvM/PDM 自动生成工具 (一键流程).

流程 (按 configs/*.yaml 深合并配置启停):
  check_nvm_table  校验 NVM 表            (脚本尚未引入, 开启即报错)
  gen_nvm_arxml    更新 J6B_NvM_EcucValues.arxml (gen_nvm_arxml/GenPdmARXML.py
                   原地更新) + 紧接 BSW 代码生成 (ISOLAR headless, 失败降级 Cobra)
  gen_pdm_code     生成 PDM 代码 (gen_pdm_code/CrmGen.py, 纯 Excel->代码,
                   读 BswRta/src/bsw/NvM/NvM_Cfg.h, 输出 cpj_*/pdm_cfg/<变体>
                   的 4 个文件 + 脚本目录 SRU_crm_RteServices.h)

用法:
  python nvm_autogen_etas.py --repo <mcu_app_j6或mcu_app_j6_v2路径> --config rx [--excel <表>] [--dry-run]

支持两种仓库布局 (按 --config 变体名自动识别):
  v1 (mcu_app_j6):    cpj_*/autosar/<变体>/BswRta + cpj_*/pdm_cfg/<变体>/
  v2 (mcu_app_j6_v2): cpj_*/<veh_xx>/autosar/BswRta + cpj_*/<veh_xx>/pdm_cfg/
                      (变体名须是 <veh_xx> 目录名子串, 如 j02 匹配 veh_j02)
"""

import argparse
import os
import re
import subprocess
import sys
import time
import yaml
from pathlib import Path
from types import SimpleNamespace

GEN_TOOLS = Path(__file__).resolve().parent

GEN_NVM_SCRIPT = GEN_TOOLS / "gen_nvm_arxml" / "GenPdmARXML.py"
CRM_GEN_SCRIPT = GEN_TOOLS / "gen_pdm_code" / "CrmGen.py"
CONFIGS_DIR = GEN_TOOLS / "configs"

SHEET = "01_NVM_List"
EXCEL_GLOB = "*_NVM_List*.xlsx"

FEATURES = ("check_nvm_table", "gen_nvm_arxml", "gen_pdm_code")

RTA_CAR_HOME_DEFAULT = Path(r"D:/ETAS/RTA-CAR_12.7.0")
BSW_TIMEOUT_S = 3600   # 全量 BSW 生成上限 60 分钟
BSW_POLL_S = 15
ERRORS_RE = re.compile(r"Errors:\s*(\d+)\s*,\s*Warnings:\s*(\d+)")
LICENSE_FAIL_RE = re.compile(
    r"Please set COBRA_LIC_PATH|No valid license", re.IGNORECASE)
OUTPUT_FAIL_RE = re.compile(r"\[ERROR\]|^\s*Error:|Execution failed", re.IGNORECASE)

# arxml 内容兜底锚点: NvMBlockDescriptor 参数容器 (静默失败 = 锚点缺失)
ARXML_ANCHOR = ("NvM/EcucModuleDefs/NvM/NvMBlockDescriptor/"
                "NvMBlockManagementType</DEFINITION-REF>")

DRY = False


def fail(msg):
    print("[nvm_autogen_etas] ERROR: %s" % msg)
    sys.exit(1)


def deep_merge(base: dict, override: dict) -> dict:
    """dict 递归合并, 标量直接覆盖 (override 优先)."""
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_feature_config(project: str):
    """读 configs/common.yaml + configs/<project>.yaml 深合并, 返回 (cfg, 来源名)."""
    common_path = CONFIGS_DIR / "common.yaml"
    if not common_path.is_file():
        fail("缺少 %s" % common_path)
    try:
        cfg = yaml.safe_load(common_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        fail("YAML 解析失败 %s: %s" % (common_path, e))
    if not isinstance(cfg, dict) or any(k not in cfg for k in FEATURES):
        fail("%s 必须包含全部功能键: %s" % (common_path, ", ".join(FEATURES)))
    source = "common"
    proj_path = CONFIGS_DIR / ("%s.yaml" % project)
    if proj_path.is_file():
        try:
            override = yaml.safe_load(proj_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            fail("YAML 解析失败 %s: %s" % (proj_path, e))
        if not isinstance(override, dict):
            fail("%s 内容必须是映射" % proj_path)
        cfg = deep_merge(cfg, override)
        source = project
    unknown = [k for k in cfg if k not in FEATURES]
    if unknown:
        fail("配置含未知键: %s (允许: %s)"
             % (", ".join(sorted(map(str, unknown))), ", ".join(FEATURES)))
    for k in FEATURES:
        if not isinstance(cfg[k], bool):
            fail("%s 必须是布尔" % k)
    return cfg, source


def resolve_repo_paths(repo: Path, project: str):
    """由 --repo + --config 推导所有目标路径 (glob, 无硬编码).

    v1 (mcu_app_j6):    cpj_*/autosar/<变体>/BswRta,      pdm_cfg 在 cpj_*/pdm_cfg/<变体>/
    v2 (mcu_app_j6_v2): cpj_*/<veh_xx>/autosar/BswRta,    pdm_cfg 在 cpj_*/<veh_xx>/pdm_cfg/
    """
    hits = sorted(repo.glob("cpj_*/autosar/%s/BswRta" % project))
    if hits:
        pdm_base = hits[0].parent.parent.parent / "pdm_cfg" / project
    else:
        hits = sorted(p for p in repo.glob("cpj_*/*/autosar/BswRta")
                      if project.lower() in p.parent.parent.name.lower())
        if not hits:
            fail("未找到 %s 的 BswRta (尝试了 cpj_*/autosar/%s/BswRta 与 "
                 "cpj_*/*%s*/autosar/BswRta 两种布局)" % (project, project, project))
        pdm_base = hits[0].parent.parent / "pdm_cfg"
    if len(hits) != 1:
        fail("BswRta 匹配 %d 个 (需恰好 1): %s"
             % (len(hits), [str(h) for h in hits]))
    bswrta = hits[0].resolve()
    arxml_hits = [p for p in sorted(bswrta.glob("ecu_config/bsw/gen/*NvM_EcucValues.arxml"))
                  if not p.name.startswith("RTA_BIP_")]
    if len(arxml_hits) != 1:
        fail("ecu_config/bsw/gen/*NvM_EcucValues.arxml (排除 RTA_BIP_) 匹配 %d 个 (需恰好 1)"
             % len(arxml_hits))
    pdm_inc = pdm_base / "inc" / "pdm_cfg"
    pdm_src = pdm_base / "src"
    return SimpleNamespace(
        repo=repo,
        bswrta=bswrta,
        arxml=arxml_hits[0],
        pdm_base=pdm_base,
        nvm_cfg_h=bswrta / "src" / "bsw" / "NvM" / "NvM_Cfg.h",
        bsw_adapter_h=pdm_inc / "pdm_cfg_BswAdapter.h",
        bsw_adapter_c=pdm_src / "pdm_cfg_BswAdapter.c",
        dataitem_cpp=pdm_src / "pdm_cfg_dataitem_config.cpp",
        pdm_cfg_h=pdm_inc / "pdm_cfg.h",
        rte_h=CRM_GEN_SCRIPT.parent / "SRU_crm_RteServices.h",
        cobra=bswrta / "ecu_config" / "cobra" / "Cobra.exe",
        confgen_log=bswrta / "_log" / "BSW_ConfGen_ECUGeneration.txt",
        bsw_log=bswrta / "_log" / "rta-bsw.log",
    )


def discover_excel(paths, project: str, excel_arg):
    """定位输入 Excel: --excel 指定优先, 否则在 <pdm_base>/Pdm_Script/ 下自动发现
    唯一 *_NVM_List*.xlsx (排除 *_merged.xlsx 中间产物与 ~$ Office 锁文件);
    多个命中时优先文件名以变体名开头的表 (如 j02 -> J02_NVM_List.xlsx)."""
    if excel_arg:
        p = Path(excel_arg).resolve()
        if not p.is_file():
            fail("Excel 不存在: %s" % p)
        return p
    script_dir = paths.pdm_base / "Pdm_Script"
    hits = [p for p in sorted(script_dir.glob(EXCEL_GLOB))
            if not p.name.endswith("_merged.xlsx") and not p.name.startswith("~$")]
    if len(hits) > 1:
        pref = [p for p in hits if p.stem.lower().startswith(project.lower())]
        if len(pref) == 1:
            return pref[0].resolve()
    if len(hits) != 1:
        fail("%s 下 %s (排除 _merged/~$) 匹配 %d 个 (需恰好 1): %s%s"
             % (script_dir, EXCEL_GLOB, len(hits), [str(h) for h in hits],
                "" if hits else " (该变体目录不存在或无 Excel, 可用 --excel 手动指定)"))
    return hits[0].resolve()


def _has_isolar_launcher(d: Path) -> bool:
    """ISOLAR-AB.cmd 为当前启动器; 旧名 ISOLAR-B.cmd 已 deprecated, 仅兜底."""
    return (d / "ISOLAR-AB.cmd").is_file() or (d / "ISOLAR-B.cmd").is_file()


def find_isolar_b(root: Path):
    """在 RTA-CAR 安装目录下找 ISOLAR 启动器所在目录 (移植 bsw_gen.ps1 Find-IsolarB)."""
    if not root.is_dir():
        return None
    if _has_isolar_launcher(root):
        return root
    cands = sorted((d for d in root.iterdir() if d.is_dir()
                    and (re.match(r"^ISOLAR-AB_\d", d.name) or re.match(r"^RTA-OS_", d.name))),
                   key=lambda d: d.name, reverse=True)
    for c in cands:
        if _has_isolar_launcher(c):
            return c
        for s in sorted((d for d in c.iterdir() if d.is_dir()
                        and re.match(r"^ISOLAR-AB_\d", d.name)),
                        key=lambda d: d.name, reverse=True):
            if _has_isolar_launcher(s):
                return s
    for depth in (1, 2, 3):
        hits = [p.parent for p in root.glob("*/" * depth + "ISOLAR-AB.cmd")]
        hits += [p.parent for p in root.glob("*/" * depth + "ISOLAR-B.cmd")]
        if hits:
            return sorted(hits, reverse=True)[0]
    return None


def isolar_cmd_path(isolar_dir: Path) -> Path:
    """优先 ISOLAR-AB.cmd (ISOLAR-B.cmd 已 deprecated)."""
    ab = isolar_dir / "ISOLAR-AB.cmd"
    return ab if ab.is_file() else isolar_dir / "ISOLAR-B.cmd"


def run_step(title, cmd, cwd):
    """跑一个子步骤, 失败打印输出尾部并 exit 1."""
    print("[nvm_autogen_etas] ==> %s" % title)
    if DRY:
        print("[nvm_autogen_etas]     [dry-run] %s"
              % " ".join(str(c) for c in cmd))
        return
    t0 = time.time()
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if proc.returncode != 0:
        print(proc.stdout[-3000:] if proc.stdout else "")
        print(proc.stderr[-3000:] if proc.stderr else "")
        print("[nvm_autogen_etas] FAILED (exit %d, %.0fs): %s"
              % (proc.returncode, time.time() - t0, title))
        sys.exit(1)
    print("[nvm_autogen_etas]     OK (%.0fs)" % (time.time() - t0))


def parse_confgen_errors(log_path: Path):
    """解析 BSW_ConfGen_ECUGeneration.txt 里的 'Errors: N, Warnings: M' (取最后一次出现)."""
    if not log_path.is_file():
        return None
    last = None
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = ERRORS_RE.search(line)
        if m:
            last = (int(m.group(1)), int(m.group(2)))
    return last


def confgen_log_fresh(log_path: Path, t0: float):
    """本次运行是否重写了 ConfGen 日志 (防静默失败误判为成功)."""
    return log_path.is_file() and log_path.stat().st_mtime >= t0


def output_has_failure_marker(lines) -> bool:
    """扫描工具输出行, 是否含显式失败标记."""
    return any(OUTPUT_FAIL_RE.search(l) for l in lines)


def gen_bsw_headless(paths, isolar_cmd: Path):
    """ISOLAR-B headless: -generate -p=<BswRta> -t=BSW. 等进程自然退出, 超时杀进程树."""
    print("[nvm_autogen_etas] ==> 生成 BSW 代码 (ISOLAR headless, 属 gen_nvm_arxml)")
    # stale NvM 日志存在时 ISOLAR 会跳过 NvM 模块并仍报成功 (静默失败), 必须先删
    for name in ("NvM_ArxmlGen_LogFile.txt", "NvM_CodeGen_LogFile.txt"):
        stale = paths.bswrta / "_log" / name
        if stale.is_file():
            stale.unlink()
            print("[nvm_autogen_etas]     已删除 stale 日志: %s" % stale)
    t0 = time.time()
    out_path = paths.bswrta / "_log" / "nvm_autogen_etas.headless.out"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(isolar_cmd), "-generate", "-p=%s" % paths.bswrta, "-t=BSW"]
    with open(out_path, "w", encoding="utf-8", errors="replace") as out:
        proc = subprocess.Popen(cmd, cwd=str(isolar_cmd.parent),
                                 stdout=out, stderr=subprocess.STDOUT)
        deadline = time.time() + BSW_TIMEOUT_S
        last_beat = time.time()
        while proc.poll() is None and time.time() < deadline:
            time.sleep(BSW_POLL_S)
            if time.time() - last_beat >= 60:
                print("[nvm_autogen_etas]     ... 仍在运行 (%.0fs)"
                      % (time.time() - t0))
                last_beat = time.time()
        if proc.poll() is None:
            print("[nvm_autogen_etas]     超过 %ds 未完成, 终止 ISOLAR 进程树" % BSW_TIMEOUT_S)
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True)
            try:
                proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                pass
            return False
    # 子进程退出后文件系统落盘缓冲
    time.sleep(10)
    out_lines = out_path.read_text(
        encoding="utf-8", errors="replace").splitlines()
    failed_marker = output_has_failure_marker(out_lines)
    bsw_fresh = confgen_log_fresh(paths.bsw_log, t0)
    print("[nvm_autogen_etas]     ISOLAR exit code: %s, rta-bsw.log fresh: %s (%.0fs)"
          % (proc.returncode, bsw_fresh, time.time() - t0))
    if failed_marker:
        for line in out_lines:
            if OUTPUT_FAIL_RE.search(line):
                print("    %s" % line)
        return False
    return proc.returncode == 0 and bsw_fresh


def gen_bsw_cobra(paths, isolar_dir: Path):
    """Cobra.exe 降级: 与 ISOLAR GUI 'Generate BSW Code' 1:1 (ConfGen+BSWGen+hooks)."""
    print("[nvm_autogen_etas] ==> 生成 BSW 代码 (Cobra.exe 降级, 属 gen_nvm_arxml)")
    if not paths.cobra.is_file():
        print("[nvm_autogen_etas]     ERROR: Cobra.exe 不存在: %s" % paths.cobra)
        return False
    t0 = time.time()
    cmd = [str(paths.cobra), "--ProjectPath=.",
           "--isolarPath=%s" % isolar_dir, "--isolarARRoot=RTA_BIP"]
    try:
        proc = subprocess.run(cmd, cwd=str(paths.bswrta), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=BSW_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        print("[nvm_autogen_etas]     ERROR: Cobra 超过 %ds 未完成" % BSW_TIMEOUT_S)
        return False
    lines = [l for l in (proc.stdout or "").splitlines()
             + (proc.stderr or "").splitlines() if l.strip()]
    for line in lines[-12:]:
        print("    %s" % line)
    if any(LICENSE_FAIL_RE.search(l) for l in lines):
        print("[nvm_autogen_etas]     ERROR: Cobra license 检查失败")
        return False
    if 0 < len(lines) < 30:
        print("[nvm_autogen_etas]     ERROR: Cobra 输出仅 %d 行, 疑似静默失败" % len(lines))
        return False
    errs = parse_confgen_errors(paths.confgen_log)
    print("[nvm_autogen_etas]     Cobra exit code: %s, ConfGen: %s (%.0fs)"
          % (proc.returncode, errs, time.time() - t0))
    if output_has_failure_marker(lines):
        for line in lines:
            if OUTPUT_FAIL_RE.search(line):
                print("    %s" % line)
        return False
    # ConfGen 日志无 'Errors: N' 汇总行时按 0 错误处理 (对齐 bsw_gen.ps1 默认)
    return (proc.returncode == 0
            and confgen_log_fresh(paths.confgen_log, t0)
            and (errs is None or errs[0] == 0))


def main():
    # 中文 Windows 下 stdout 重定向时默认 GBK, 子脚本输出含 emoji 会炸掉诊断信息
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="ETAS NvM/PDM auto generation tool")
    parser.add_argument("--repo", required=True,
                        help="mcu_app_j6 / mcu_app_j6_v2 仓库根目录")
    parser.add_argument("--config", required=True,
                        help="变体名 (如 rx, 对应 configs/<变体名>.yaml 与 cpj_*/pdm_cfg/<变体>/)")
    parser.add_argument("--excel", default=None,
                        help="*_NVM_List.xlsx 路径 (缺省自动发现; 变体目录下有多个表时必须指定)")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印推导路径与将执行的命令, 不实际运行")
    args = parser.parse_args()
    global DRY
    DRY = args.dry_run

    repo = Path(args.repo).resolve()

    cfg, cfg_source = load_feature_config(args.config)

    needed_scripts = {
        "gen_nvm_arxml": GEN_NVM_SCRIPT,
        "gen_pdm_code": CRM_GEN_SCRIPT,
    }
    for feat, script in needed_scripts.items():
        if cfg[feat] and not script.is_file():
            fail("脚本不存在: %s" % script)
    # 模板文件逐一检查 (防模板缺失静默暴露)
    TEMPLATE_FILES = ("SRU_crm_RteServices_T.h", "pdm_cfg_BswAdapter_T.c",
                      "pdm_cfg_BswAdapter_T.h", "pdm_cfg_T.h",
                      "pdm_cfg_dataitem_config_T.cpp")
    if cfg["gen_pdm_code"]:
        for name in TEMPLATE_FILES:
            f = CRM_GEN_SCRIPT.parent / "template" / name
            if not f.is_file():
                fail("模板文件不存在: %s" % f)

    paths = resolve_repo_paths(repo, args.config)
    excel = discover_excel(paths, args.config, args.excel)

    print("[nvm_autogen_etas] Excel     : %s" % excel)
    print("[nvm_autogen_etas] MCU 仓库  : %s" % repo)
    print("[nvm_autogen_etas] 车型      : %s" % args.config)
    print("[nvm_autogen_etas] BswRta    : %s" % paths.bswrta)
    print("[nvm_autogen_etas] PDM 目录  : %s" % paths.pdm_base)
    print("[nvm_autogen_etas] 目标 arxml: %s" % paths.arxml)
    print("[nvm_autogen_etas] 配置      : %s (%s)" % (CONFIGS_DIR, cfg_source))
    print("[nvm_autogen_etas] 启用功能  : %s"
          % " -> ".join(k for k in FEATURES if cfg[k]))
    if DRY:
        print("[nvm_autogen_etas] *** DRY-RUN 模式, 只打印命令不执行 ***")

    if cfg["check_nvm_table"]:
        fail("check_nvm_table 脚本尚未引入")

    if cfg["gen_nvm_arxml"]:
        t0 = time.time()
        run_step("更新 NvM arxml (原地)",
                 [sys.executable, str(GEN_NVM_SCRIPT), "-i", str(paths.arxml),
                  "-e", str(excel), "-o", str(paths.arxml)],
                 cwd=GEN_NVM_SCRIPT.parent)
        # 子脚本静默失败兜底: arxml 应被重写且仍含 NvMBlockDescriptor 容器
        if not DRY:
            if paths.arxml.stat().st_mtime < t0 - 1:
                fail("gen_nvm_arxml 声称成功但 arxml 未被重写: %s (子脚本静默失败?)"
                     % paths.arxml)
            text = paths.arxml.read_text(encoding="utf-8", errors="replace")
            if ARXML_ANCHOR not in text:
                fail("gen_nvm_arxml 后 arxml 缺少 NvMBlockDescriptor 容器 "
                     "(子脚本静默失败?): %s" % paths.arxml)

        rta_home = Path(os.environ.get("RTA_CAR_HOME", str(RTA_CAR_HOME_DEFAULT)))
        isolar_dir = find_isolar_b(rta_home)
        if isolar_dir is None:
            fail("ISOLAR-AB.cmd 未找到 (RTA_CAR_HOME=%s)" % rta_home)
        isolar_cmd = isolar_cmd_path(isolar_dir)
        print("[nvm_autogen_etas] ISOLAR    : %s" % isolar_cmd)
        if DRY:
            print("[nvm_autogen_etas]     [dry-run] %s -generate -p=%s -t=BSW"
                  % (isolar_cmd, paths.bswrta))
            print("[nvm_autogen_etas]     [dry-run] 失败时降级: %s --ProjectPath=. "
                  "--isolarPath=%s --isolarARRoot=RTA_BIP" % (paths.cobra, isolar_dir))
        else:
            ok = gen_bsw_headless(paths, isolar_cmd)
            if not ok:
                print("[nvm_autogen_etas] headless 失败, 降级 Cobra.exe ...")
                ok = gen_bsw_cobra(paths, isolar_dir)
            if not ok:
                fail("BSW 生成失败, 详见 %s 及 %s 目录下日志"
                     % (paths.confgen_log, paths.bswrta / "_log"))

    if cfg["gen_pdm_code"]:
        # nvm_cfg_h 检查在执行时做 (gen_nvm_arxml=ON 时本流程会产出,
        # 全新 checkout 启动时不误杀)
        if not DRY and not paths.nvm_cfg_h.is_file():
            fail("NvM_Cfg.h 不存在: %s\n  请先开启 gen_nvm_arxml 完整生成 "
                 "(或历史产物未入库)" % paths.nvm_cfg_h)
        pdm_t0 = time.time()
        run_step("生成 PDM 代码 (BswAdapter.h/.c + dataitem_config.cpp + pdm_cfg.h + RteServices.h)",
                 [sys.executable, str(CRM_GEN_SCRIPT), str(excel), SHEET,
                  str(paths.nvm_cfg_h), str(paths.bsw_adapter_h),
                  str(paths.bsw_adapter_c), str(paths.dataitem_cpp),
                  str(paths.rte_h), str(paths.pdm_cfg_h)],
                 cwd=CRM_GEN_SCRIPT.parent)
        # CrmGen 静默失败兜底 (默认值错时提前 return 且 exit 0):
        # 5 个输出文件都应被重写
        if not DRY:
            for out in (paths.bsw_adapter_h, paths.bsw_adapter_c,
                        paths.dataitem_cpp, paths.rte_h, paths.pdm_cfg_h):
                if not out.is_file() or out.stat().st_mtime < pdm_t0 - 1:
                    fail("CrmGen 声称成功但输出未更新: %s (子脚本静默失败?)" % out)

    print("[nvm_autogen_etas] 全部完成")


if __name__ == "__main__":
    main()
