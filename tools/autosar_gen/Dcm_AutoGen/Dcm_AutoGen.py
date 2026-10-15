#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dcm_AutoGen - J6 ETAS Dcm 诊断生成统一入口 (一键流程).

流程 (按 configs/common.json 功能开关启停, 顺序即执行顺序):
  gen_dcm_arxml     问卷 Service List + DcmDspSession/DcmDspSecurity 表 ->
                    重建 J6B_Dcm_EcucValues.arxml 服务表及 DcmDsp 行容器
                    (Dcm_AutoGen_Etas/gen_dcm_arxml/Dcm_arxml_Script.py)
  gen_nrc_code      问卷 Service List -> 重建 ov_dia_notification.cpp NRC 检查
  gen_did_code      问卷 DID List -> DID 查找表/0x22/0x2E handler + version_did JSON
  gen_rid_code      问卷 RID List -> 0x31 处理器 (纯 NRC 骨架)
  etas_bsw_code_gen ETAS BSW 代码生成 (ISOLAR headless, 失败降级 Cobra.exe;
                    移植自 Dem_AutoGen_Etas/dem_autogen_etas.py)

用法:
  python Dcm_AutoGen.py --repo <mcu_app_j6路径> --config <变体名> [--excel <UDS问卷xlsx>]
                        [--json <version_did JSON>] [--dry-run]
  变体名如 j02; Excel 缺省在 UDS_Diagnostic_Questionnaire/<变体名>/(大小写不敏感) 下
  发现 UDS_Diagnostic_Questionnaire_<目录名>.xlsx; JSON 缺省在兄弟仓库
  version_did/modules/*/ 下发现 <变体名>_*.json.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

TOOL_ROOT = Path(__file__).resolve().parent

DCM_ARXML_SCRIPT = TOOL_ROOT / "Dcm_AutoGen_Etas" / "gen_dcm_arxml" / "Dcm_arxml_Script.py"
NRC_SCRIPT = TOOL_ROOT / "Dcm_AutoGen_User" / "gen_nrc_code.py"
DID_SCRIPT = TOOL_ROOT / "Dcm_AutoGen_User" / "gen_did_code.py"
RID_SCRIPT = TOOL_ROOT / "Dcm_AutoGen_User" / "gen_rid_code.py"
CONFIGS_DIR = TOOL_ROOT / "configs"
QUESTIONNAIRE_DIR = TOOL_ROOT / "UDS_Diagnostic_Questionnaire"

FEATURES = ("gen_dcm_arxml", "gen_nrc_code", "gen_did_code", "gen_rid_code",
            "etas_bsw_code_gen")

RTA_CAR_HOME_DEFAULT = Path(r"D:/ETAS/RTA-CAR_12.7.0")
BSW_TIMEOUT_S = 3600   # 全量 BSW 生成上限 60 分钟 (对齐 dem_autogen_etas)
BSW_POLL_S = 15
ERRORS_RE = re.compile(r"Errors:\s*(\d+)\s*,\s*Warnings:\s*(\d+)")
LICENSE_FAIL_RE = re.compile(
    r"Please set COBRA_LIC_PATH|No valid license", re.IGNORECASE)
# 输出中的显式失败标记 (对齐 bsw_gen.ps1 的错误行扫描)
OUTPUT_FAIL_RE = re.compile(r"\[ERROR\]|^\s*Error:|Execution failed", re.IGNORECASE)


def fail(msg):
    print("[Dcm_AutoGen] ERROR: %s" % msg)
    sys.exit(1)


# ---------------------------------------------------------------- 配置

def deep_merge(base: dict, override: dict) -> dict:
    """dict 递归合并, 标量直接覆盖 (override 优先)."""
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_feature_config(config: str):
    """读 configs/common.json + configs/<config>.json 深合并, 返回 (cfg, 来源名)."""
    common_path = CONFIGS_DIR / "common.json"
    if not common_path.is_file():
        fail("缺少 %s" % common_path)
    try:
        cfg = json.loads(common_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        fail("JSON 解析失败 %s: %s" % (common_path, e))
    if not isinstance(cfg, dict):
        fail("%s 内容必须是 JSON 对象" % common_path)
    source = "common"
    proj_path = CONFIGS_DIR / ("%s.json" % config)
    if proj_path.is_file():
        try:
            override = json.loads(proj_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            fail("JSON 解析失败 %s: %s" % (proj_path, e))
        if not isinstance(override, dict):
            fail("%s 内容必须是 JSON 对象" % proj_path)
        cfg = deep_merge(cfg, override)
        source = config
    missing = [k for k in FEATURES if k not in cfg]
    if missing:
        fail("%s 缺少功能键: %s" % (path, ", ".join(missing)))
    unknown = [k for k in cfg if k not in FEATURES]
    if unknown:
        fail("%s 含未知键: %s (允许: %s)"
             % (source, ", ".join(sorted(map(str, unknown))), ", ".join(FEATURES)))
    for k in FEATURES:
        if not isinstance(cfg[k], bool):
            fail("%s 的 %s 必须是布尔" % (source, k))
    return cfg, source


# ---------------------------------------------------------------- 路径发现

def resolve_repo_paths(repo: Path, config: str):
    """由 --repo + --config 推导目标路径 (glob, 无硬编码).

    兼容两种仓库布局:
      旧 (mcu_app_j6):   cpj_*/autosar/<变体>/BswRta, dia_cfg/var/src/vehicle/<变体>
      v2 (mcu_app_j6_v2): cpj_*/veh_<变体>/autosar/BswRta, veh_<变体>/dia_cfg/src
    """
    cfg = config.lower()
    hits = sorted(repo.glob("cpj_*/autosar/%s/BswRta" % config))
    vd_hits = sorted(repo.glob("cpj_*/dia_cfg/var/src/vehicle/%s" % config))
    v2_hits = [p for p in sorted(repo.glob("cpj_*/*/autosar/BswRta"))
               if p.parents[1].name.lower() in (cfg, "veh_" + cfg)]
    if v2_hits:
        hits += v2_hits
        vd_hits += [p.parents[1] / "dia_cfg" / "src" for p in v2_hits]
    hits = sorted(set(hits))
    vd_hits = sorted(set(vd_hits))
    if len(hits) != 1:
        fail("BswRta 匹配 %d 个 (需恰好 1): %s"
             % (len(hits), [str(h) for h in hits]))
    bswrta = hits[0].resolve()
    arxml_hits = [p for p in sorted(bswrta.glob("ecu_config/bsw/gen/*Dcm_EcucValues.arxml"))
                  if not p.name.startswith("RTA_BIP_")]
    if len(arxml_hits) != 1:
        fail("ecu_config/bsw/gen/*Dcm_EcucValues.arxml (排除 RTA_BIP_) 匹配 %d 个 (需恰好 1)"
             % len(arxml_hits))
    if len(vd_hits) != 1:
        fail("dia_cfg 车辆代码目录匹配 %d 个 (需恰好 1): %s"
             % (len(vd_hits), [str(h) for h in vd_hits]))
    vehicle_dir = vd_hits[0].resolve()
    return SimpleNamespace(
        repo=repo,
        bswrta=bswrta,
        arxml=arxml_hits[0].resolve(),
        vehicle_dir=vehicle_dir,
        nrc_cpp=vehicle_dir / "ov_dia_notification" / "ov_dia_notification.cpp",
        cobra=bswrta / "ecu_config" / "cobra" / "Cobra.exe",
        confgen_log=bswrta / "_log" / "BSW_ConfGen_ECUGeneration.txt",
        bsw_log=bswrta / "_log" / "rta-bsw.log",
    )


def discover_excel(config: str, excel_arg):
    """定位 UDS 问卷 Excel: --excel 优先, 否则 UDS_Diagnostic_Questionnaire/<变体>/
    (目录名大小写不敏感) 下找 UDS_Diagnostic_Questionnaire_<目录名>.xlsx."""
    if excel_arg:
        p = Path(excel_arg).resolve()
        if not p.is_file():
            fail("Excel 不存在: %s" % p)
        return p
    if not QUESTIONNAIRE_DIR.is_dir():
        fail("问卷目录不存在: %s (可用 --excel 手动指定)" % QUESTIONNAIRE_DIR)
    for d in sorted(QUESTIONNAIRE_DIR.iterdir()):
        if not d.is_dir() or d.name.lower() != config.lower():
            continue
        p = d / ("UDS_Diagnostic_Questionnaire_%s.xlsx" % d.name)
        if not p.is_file():
            fail("问卷目录 %s 下未找到 %s (可用 --excel 手动指定)" % (d, p.name))
        return p.resolve()
    fail("UDS_Diagnostic_Questionnaire/ 下无变体目录 %r (大小写不敏感; 可用 --excel 手动指定)"
         % config)


def discover_version_json(repo: Path, config: str, json_arg):
    """定位 version_did JSON: --json 优先, 否则兄弟仓库 version_did/modules/*/
    下按变体名前缀 (大小写不敏感) 发现唯一 <变体名>_*.json."""
    if json_arg:
        p = Path(json_arg).resolve()
        if not p.is_file():
            fail("JSON 不存在: %s" % p)
        return p
    vd_repo = repo.parent / "version_did"
    if not vd_repo.is_dir():
        fail("version_did 仓库不存在: %s (可用 --json 手动指定)" % vd_repo)
    hits = [p for p in sorted(vd_repo.glob("modules/*/*.json"))
            if p.stem.lower().startswith(config.lower() + "_")]
    if len(hits) != 1:
        fail("version_did/modules/*/ 下 %s_*.json 匹配 %d 个 (需恰好 1): %s (可用 --json 手动指定)"
             % (config, len(hits), [str(h) for h in hits]))
    return hits[0].resolve()


# ---------------------------------------------------------------- 子步骤执行

def run_step(title, cmd, cwd):
    """跑一个子步骤, 失败打印输出尾部并 exit 1."""
    print("[Dcm_AutoGen] ==> %s" % title)
    t0 = time.time()
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if proc.returncode != 0:
        print(proc.stdout[-3000:] if proc.stdout else "")
        print(proc.stderr[-3000:] if proc.stderr else "")
        print("[Dcm_AutoGen] FAILED (exit %d, %.0fs): %s"
              % (proc.returncode, time.time() - t0, title))
        sys.exit(1)
    print("[Dcm_AutoGen]     OK (%.0fs)" % (time.time() - t0))


# ---------------------------------------------------------------- ETAS BSW 代码生成
# (移植自 Dem_AutoGen_Etas/dem_autogen_etas.py: find_isolar_b / headless / Cobra)

def _has_isolar_launcher(d: Path) -> bool:
    """ISOLAR-AB.cmd 为当前启动器; 旧名 ISOLAR-B.cmd 已 deprecated, 仅兜底."""
    return (d / "ISOLAR-AB.cmd").is_file() or (d / "ISOLAR-B.cmd").is_file()


def find_isolar_b(root: Path):
    """在 RTA-CAR 安装目录下找 ISOLAR 启动器所在目录 (移植 bsw_gen.ps1 Find-IsolarB).

    root 可以是 RTA-CAR 根 / RTA-OS_* 目录 / ISOLAR-AB_* 目录本身.
    """
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
    # 兜底: 深度 <=3 递归扫描
    for depth in (1, 2, 3):
        hits = [p.parent for p in root.glob("*/" * depth + "ISOLAR-AB.cmd")]
        hits += [p.parent for p in root.glob("*/" * depth + "ISOLAR-B.cmd")]
        if hits:
            return sorted(hits, reverse=True)[0]
    return None


def isolar_cmd_path(isolar_dir: Path):
    """优先 ISOLAR-AB.cmd (ISOLAR-B.cmd 已 deprecated)."""
    ab = isolar_dir / "ISOLAR-AB.cmd"
    return ab if ab.is_file() else isolar_dir / "ISOLAR-B.cmd"


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
    """本次运行是否重写了日志 (防静默失败误判为成功)."""
    return log_path.is_file() and log_path.stat().st_mtime >= t0


def output_has_failure_marker(lines) -> bool:
    """扫描工具输出行, 是否含显式失败标记."""
    return any(OUTPUT_FAIL_RE.search(l) for l in lines)


def gen_bsw_headless(paths, isolar_cmd: Path):
    """ISOLAR-B headless: -generate -p=<BswRta> -t=BSW. 等进程自然退出, 超时杀进程树."""
    print("[Dcm_AutoGen] ==> 生成 BSW 代码 (ISOLAR headless, 属 etas_bsw_code_gen)")
    t0 = time.time()
    out_path = paths.bswrta / "_log" / "dcm_autogen.headless.out"
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
                print("[Dcm_AutoGen]     ... 仍在运行 (%.0fs)" % (time.time() - t0))
                last_beat = time.time()
        if proc.poll() is None:
            print("[Dcm_AutoGen]     超过 %ds 未完成, 终止 ISOLAR 进程树" % BSW_TIMEOUT_S)
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True)
            try:
                proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                pass
            return False
    # 子进程退出后文件系统落盘缓冲
    time.sleep(10)
    out_lines = out_path.read_text(encoding="utf-8", errors="replace").splitlines()
    failed_marker = output_has_failure_marker(out_lines)
    # headless 不产生 Cobra 专属的 BSW_ConfGen_ECUGeneration.txt,
    # 以 rta-bsw.log 新鲜度证明"BSW 生成确实跑了"
    bsw_fresh = confgen_log_fresh(paths.bsw_log, t0)
    print("[Dcm_AutoGen]     ISOLAR exit code: %s, rta-bsw.log fresh: %s (%.0fs)"
          % (proc.returncode, bsw_fresh, time.time() - t0))
    if failed_marker:
        for line in out_lines:
            if OUTPUT_FAIL_RE.search(line):
                print("    %s" % line)
        return False
    return proc.returncode == 0 and bsw_fresh


def gen_bsw_cobra(paths, isolar_dir: Path):
    """Cobra.exe 降级: 与 ISOLAR GUI 'Generate BSW Code' 1:1 (ConfGen+BSWGen+hooks)."""
    print("[Dcm_AutoGen] ==> 生成 BSW 代码 (Cobra.exe 降级, 属 etas_bsw_code_gen)")
    if not paths.cobra.is_file():
        print("[Dcm_AutoGen]     ERROR: Cobra.exe 不存在: %s" % paths.cobra)
        return False
    t0 = time.time()
    cmd = [str(paths.cobra), "--ProjectPath=.",
           "--isolarPath=%s" % isolar_dir, "--isolarARRoot=RTA_BIP"]
    try:
        proc = subprocess.run(cmd, cwd=str(paths.bswrta), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=BSW_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        print("[Dcm_AutoGen]     ERROR: Cobra 超过 %ds 未完成" % BSW_TIMEOUT_S)
        return False
    lines = [l for l in (proc.stdout or "").splitlines()
             + (proc.stderr or "").splitlines() if l.strip()]
    for line in lines[-12:]:
        print("    %s" % line)
    if any(LICENSE_FAIL_RE.search(l) for l in lines):
        print("[Dcm_AutoGen]     ERROR: Cobra license 检查失败")
        return False
    if 0 < len(lines) < 30:
        print("[Dcm_AutoGen]     ERROR: Cobra 输出仅 %d 行, 疑似静默失败" % len(lines))
        return False
    errs = parse_confgen_errors(paths.confgen_log)
    print("[Dcm_AutoGen]     Cobra exit code: %s, ConfGen: %s (%.0fs)"
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


def run_etas_bsw_code_gen(paths):
    rta_home = Path(os.environ.get("RTA_CAR_HOME", str(RTA_CAR_HOME_DEFAULT)))
    isolar_dir = find_isolar_b(rta_home)
    if isolar_dir is None:
        fail("ISOLAR-AB.cmd 未找到 (RTA_CAR_HOME=%s)" % rta_home)
    isolar_cmd = isolar_cmd_path(isolar_dir)
    print("[Dcm_AutoGen] ISOLAR    : %s" % isolar_cmd)
    ok = gen_bsw_headless(paths, isolar_cmd)
    if not ok:
        print("[Dcm_AutoGen] headless 失败, 降级 Cobra.exe ...")
        ok = gen_bsw_cobra(paths, isolar_dir)
    if not ok:
        fail("BSW 生成失败, 详见 %s 及 %s 目录下日志"
             % (paths.confgen_log, paths.bswrta / "_log"))


# ---------------------------------------------------------------- 主流程

def main():
    # 中文 Windows 下 stdout 重定向时默认 GBK; 行缓冲保证与子进程输出顺序一致
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    parser = argparse.ArgumentParser(description="J6 ETAS Dcm 诊断生成统一入口")
    parser.add_argument("--repo", required=True, help="mcu_app_j6 仓库根目录")
    parser.add_argument("--config", required=True,
                        help="变体名 (如 j02, 对应 cpj_*/autosar/<变体>/BswRta)")
    parser.add_argument("--excel", default=None,
                        help="UDS 问卷 xlsx (缺省在 UDS_Diagnostic_Questionnaire/<变体>/ 下发现)")
    parser.add_argument("--json", default=None,
                        help="version_did JSON (缺省在兄弟 version_did 仓库 modules/ 下发现)")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印将执行的命令, 不实际运行")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        fail("路径不存在或不是目录: %s" % repo)

    cfg, cfg_source = load_feature_config(args.config)
    enabled = [k for k in FEATURES if cfg[k]]
    if not enabled:
        fail("configs/common.json 未启用任何功能")

    scripts = {"gen_dcm_arxml": DCM_ARXML_SCRIPT, "gen_nrc_code": NRC_SCRIPT,
               "gen_did_code": DID_SCRIPT, "gen_rid_code": RID_SCRIPT}
    for feat in enabled:
        if feat in scripts and not scripts[feat].is_file():
            fail("脚本不存在 (%s): %s" % (feat, scripts[feat]))

    paths = resolve_repo_paths(repo, args.config)
    excel = discover_excel(args.config, args.excel)
    version_json = (discover_version_json(repo, args.config, args.json)
                    if cfg["gen_did_code"] else None)

    if cfg["gen_nrc_code"] and not paths.nrc_cpp.is_file():
        fail("NRC 目标文件不存在: %s" % paths.nrc_cpp)

    py = sys.executable
    steps = []
    if cfg["gen_dcm_arxml"]:
        steps.append(("gen_dcm_arxml",
                      [py, str(DCM_ARXML_SCRIPT), str(excel),
                       str(paths.arxml), str(paths.arxml)],
                      DCM_ARXML_SCRIPT.parent))
    if cfg["gen_nrc_code"]:
        steps.append(("gen_nrc_code",
                      [py, str(NRC_SCRIPT), str(excel), str(paths.nrc_cpp)],
                      NRC_SCRIPT.parent))
    if cfg["gen_did_code"]:
        steps.append(("gen_did_code",
                      [py, str(DID_SCRIPT), str(excel),
                       str(paths.vehicle_dir), str(version_json)],
                      DID_SCRIPT.parent))
    if cfg["gen_rid_code"]:
        steps.append(("gen_rid_code",
                      [py, str(RID_SCRIPT), str(excel), str(paths.vehicle_dir)],
                      RID_SCRIPT.parent))

    total = len(steps) + (1 if cfg["etas_bsw_code_gen"] else 0)

    print("[Dcm_AutoGen] Excel     : %s" % excel)
    print("[Dcm_AutoGen] MCU 仓库  : %s" % repo)
    print("[Dcm_AutoGen] 变体      : %s" % args.config)
    print("[Dcm_AutoGen] BswRta    : %s" % paths.bswrta)
    print("[Dcm_AutoGen] Dcm arxml : %s" % paths.arxml)
    if version_json:
        print("[Dcm_AutoGen] VD JSON   : %s" % version_json)
    print("[Dcm_AutoGen] 配置      : %s (%s)" % (CONFIGS_DIR / "common.json", cfg_source))
    print("[Dcm_AutoGen] 启用功能  : %s" % (" -> ".join(enabled)))

    if args.dry_run:
        print("[Dcm_AutoGen] --dry-run, 将依次执行:")
        for i, (name, cmd, _cwd) in enumerate(steps):
            print("  Step %d/%d %s: %s" % (i + 1, total, name, " ".join(cmd)))
        if cfg["etas_bsw_code_gen"]:
            rta_home = Path(os.environ.get("RTA_CAR_HOME", str(RTA_CAR_HOME_DEFAULT)))
            isolar_dir = find_isolar_b(rta_home)
            if isolar_dir is not None:
                print("  Step %d/%d etas_bsw_code_gen: %s -generate -p=%s -t=BSW"
                      " (失败降级 Cobra.exe)" % (total, total, isolar_cmd_path(isolar_dir),
                                                 paths.bswrta))
            else:
                print("  Step %d/%d etas_bsw_code_gen: ISOLAR-AB.cmd 未找到"
                      " (RTA_CAR_HOME=%s), 实际运行将报错" % (total, total, rta_home))
        return

    for i, (name, cmd, cwd) in enumerate(steps):
        run_step("Step %d/%d %s" % (i + 1, total, name), cmd, cwd)
    if cfg["etas_bsw_code_gen"]:
        print("[Dcm_AutoGen] ==> Step %d/%d etas_bsw_code_gen" % (total, total))
        run_etas_bsw_code_gen(paths)
    print("[Dcm_AutoGen] 全部完成")


if __name__ == "__main__":
    main()
