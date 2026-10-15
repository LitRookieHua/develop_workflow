#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dem_autogen_etas - ETAS Dem 自动生成工具 (一键流程).

流程 (按 configs/*.yaml 深合并配置启停, 详见 specs/2026-09-19-dem-autogen-etas-feature-config-design.md):
  check_dtc_table  校验 DTC 表            (脚本尚未引入, 开启即报错)
  gen_dem_table    gen_dem_arxml + 紧接 BSW 代码生成 (ISOLAR headless, 失败降级 Cobra)
                  二级配置 jumpdown/jumpup 控制 DemDebounceCounterJumpDown/JumpUp
  gen_event_ctrl   生成 Dem_PrjSpecificControl.c
  gen_fim_code     生成 evm_cfg 3 个文件 (FidCfg.hpp / iSysFidCfg.cpp / zx fimcfg.hpp)

map 表生成 (gen_map_yaml) 已提取至上层 Dem_AutoGen/Dem_AutoGen.py 统一执行,
本脚本单独运行时不生成 map.

用法:
  python dem_autogen_etas.py --repo <mcu_app_j6路径> --config rx [--excel <IDC_EVM_Config*.xlsx>]
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

DEM_ARXML_SCRIPT = GEN_TOOLS / "gen_dem_arxml" / "Dem_arxml_Script.py"
EVENT_CTRL_SCRIPT = GEN_TOOLS / "gen_event_ctrl" / "Gen_EventAvailable_Control_Script.py"
FIMFID_SCRIPT = GEN_TOOLS / "gen_fim_code" / "gen_fim_code.py"
CONFIGS_DIR = GEN_TOOLS / "configs"

FEATURES = ("check_dtc_table", "gen_dem_table", "gen_event_ctrl",
            "gen_fim_code")

RTA_CAR_HOME_DEFAULT = Path(r"D:/ETAS/RTA-CAR_12.7.0")
BSW_TIMEOUT_S = 3600   # 全量 BSW 生成上限 60 分钟 (真机实测 20 分钟只跑到 Com 模块)
BSW_POLL_S = 15
ERRORS_RE = re.compile(r"Errors:\s*(\d+)\s*,\s*Warnings:\s*(\d+)")
LICENSE_FAIL_RE = re.compile(
    r"Please set COBRA_LIC_PATH|No valid license", re.IGNORECASE)
# 输出中的显式失败标记 (对齐 bsw_gen.ps1 的错误行扫描)
OUTPUT_FAIL_RE = re.compile(r"\[ERROR\]|^\s*Error:|Execution failed", re.IGNORECASE)


def fail(msg):
    print("[dem_autogen_etas] ERROR: %s" % msg)
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
        v = cfg[k]
        if k == "gen_dem_table":
            if not isinstance(v, dict):
                fail("gen_dem_table 必须是含 enabled 布尔键的映射")
            bad = [j for j in v if j not in ("enabled", "jumpdown", "jumpup")]
            if bad:
                fail("gen_dem_table 含未知二级键: %s (允许: enabled, jumpdown, jumpup)"
                     % ", ".join(sorted(map(str, bad))))
            if not isinstance(v.get("enabled"), bool):
                fail("gen_dem_table 必须是含 enabled 布尔键的映射")
            for j in ("jumpdown", "jumpup"):
                val = v.get(j, False)
                if not isinstance(val, bool):
                    fail("gen_dem_table.%s 必须是布尔" % j)
                v[j] = val
        elif not isinstance(v, bool):
            fail("%s 必须是布尔" % k)
    return cfg, source


def resolve_repo_paths(repo: Path, project: str):
    """由 --repo + --config 推导所有目标路径 (glob, 无硬编码; 31 车型实测同构)."""
    hits = sorted(repo.glob("cpj_*/autosar/%s/BswRta" % project))
    if len(hits) != 1:
        fail("cpj_*/autosar/%s/BswRta 匹配 %d 个 (需恰好 1): %s"
             % (project, len(hits), [str(h) for h in hits]))
    bswrta = hits[0].resolve()
    arxml_hits = [p for p in sorted(bswrta.glob("ecu_config/bsw/gen/*Dem_EcucValues.arxml"))
                  if not p.name.startswith("RTA_BIP_")]
    if len(arxml_hits) != 1:
        fail("ecu_config/bsw/gen/*Dem_EcucValues.arxml (排除 RTA_BIP_) 匹配 %d 个 (需恰好 1)"
             % len(arxml_hits))
    cpj = bswrta.parent.parent.parent  # cpj_x/autosar/<proj>/BswRta -> cpj_x
    return SimpleNamespace(
        repo=repo,
        bswrta=bswrta,
        arxml=arxml_hits[0],
        dem_ctrl_out=bswrta / "integration" / "src" / "bsw" / "Dem" / "user",
        fimfid_cpp_out=cpj / "evm_cfg" / "var" / "src" / "vehicle" / project / "_gen",
        fimfid_h_out=cpj / "evm_cfg" / "var" / "inc" / "vehicle" / project / "evm_cfg",
        cobra=bswrta / "ecu_config" / "cobra" / "Cobra.exe",
        confgen_log=bswrta / "_log" / "BSW_ConfGen_ECUGeneration.txt",
        bsw_log=bswrta / "_log" / "rta-bsw.log",
    )


def discover_excel(repo: Path, project: str, excel_arg):
    """定位输入 Excel: --excel 指定优先, 否则在 cpj_*/tools/<变体>/e2e_dem/ 下
    自动发现唯一 IDC_EVM_Config*.xlsx (排除 *_merged.xlsx 中间产物)."""
    if excel_arg:
        p = Path(excel_arg).resolve()
        if not p.is_file():
            fail("Excel 不存在: %s" % p)
        return p
    hits = [p for p in sorted(repo.glob("cpj_*/tools/%s/e2e_dem/IDC_EVM_Config*.xlsx" % project))
            if not p.name.endswith("_merged.xlsx")]
    if len(hits) != 1:
        fail("cpj_*/tools/%s/e2e_dem/ 下 IDC_EVM_Config*.xlsx (排除 _merged) 匹配 %d 个 (需恰好 1): %s%s"
             % (project, len(hits), [str(h) for h in hits],
                "" if hits else " (该变体目录不存在或无 Excel, 可用 --excel 手动指定)"))
    return hits[0].resolve()


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


def isolar_cmd_path(isolar_dir: Path) -> Path:
    """优先 ISOLAR-AB.cmd (ISOLAR-B.cmd 已 deprecated)."""
    ab = isolar_dir / "ISOLAR-AB.cmd"
    return ab if ab.is_file() else isolar_dir / "ISOLAR-B.cmd"


def run_step(title, cmd, cwd):
    """跑一个子步骤, 失败打印输出尾部并 exit 1."""
    print("[dem_autogen_etas] ==> %s" % title)
    t0 = time.time()
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if proc.returncode != 0:
        print(proc.stdout[-3000:] if proc.stdout else "")
        print(proc.stderr[-3000:] if proc.stderr else "")
        print("[dem_autogen_etas] FAILED (exit %d, %.0fs): %s"
              % (proc.returncode, time.time() - t0, title))
        sys.exit(1)
    print("[dem_autogen_etas]     OK (%.0fs)" % (time.time() - t0))


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
    print("[dem_autogen_etas] ==> 生成 BSW 代码 (ISOLAR headless, 属 gen_dem_table)")
    t0 = time.time()
    out_path = paths.bswrta / "_log" / "dem_autogen_etas.headless.out"
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
                print("[dem_autogen_etas]     ... 仍在运行 (%.0fs)"
                      % (time.time() - t0))
                last_beat = time.time()
        if proc.poll() is None:
            print("[dem_autogen_etas]     超过 %ds 未完成, 终止 ISOLAR 进程树" % BSW_TIMEOUT_S)
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
    # headless 不产生 Cobra 专属的 BSW_ConfGen_ECUGeneration.txt,
    # 以 rta-bsw.log 新鲜度证明"BSW 生成确实跑了"
    bsw_fresh = confgen_log_fresh(paths.bsw_log, t0)
    print("[dem_autogen_etas]     ISOLAR exit code: %s, rta-bsw.log fresh: %s (%.0fs)"
          % (proc.returncode, bsw_fresh, time.time() - t0))
    if failed_marker:
        for line in out_lines:
            if OUTPUT_FAIL_RE.search(line):
                print("    %s" % line)
        return False
    return proc.returncode == 0 and bsw_fresh


def gen_bsw_cobra(paths, isolar_dir: Path):
    """Cobra.exe 降级: 与 ISOLAR GUI 'Generate BSW Code' 1:1 (ConfGen+BSWGen+hooks)."""
    print("[dem_autogen_etas] ==> 生成 BSW 代码 (Cobra.exe 降级, 属 gen_dem_table)")
    if not paths.cobra.is_file():
        print("[dem_autogen_etas]     ERROR: Cobra.exe 不存在: %s" % paths.cobra)
        return False
    t0 = time.time()
    cmd = [str(paths.cobra), "--ProjectPath=.",
           "--isolarPath=%s" % isolar_dir, "--isolarARRoot=RTA_BIP"]
    try:
        proc = subprocess.run(cmd, cwd=str(paths.bswrta), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=BSW_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        print("[dem_autogen_etas]     ERROR: Cobra 超过 %ds 未完成" % BSW_TIMEOUT_S)
        return False
    lines = [l for l in (proc.stdout or "").splitlines()
             + (proc.stderr or "").splitlines() if l.strip()]
    for line in lines[-12:]:
        print("    %s" % line)
    if any(LICENSE_FAIL_RE.search(l) for l in lines):
        print("[dem_autogen_etas]     ERROR: Cobra license 检查失败")
        return False
    if 0 < len(lines) < 30:
        print("[dem_autogen_etas]     ERROR: Cobra 输出仅 %d 行, 疑似静默失败" % len(lines))
        return False
    errs = parse_confgen_errors(paths.confgen_log)
    print("[dem_autogen_etas]     Cobra exit code: %s, ConfGen: %s (%.0fs)"
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
    parser = argparse.ArgumentParser(description="ETAS Dem auto generation tool")
    parser.add_argument("--repo", required=True, help="mcu_app_j6 仓库根目录")
    parser.add_argument("--config", required=True,
                        help="变体名 (如 rx, 对应 configs/<变体名>.yaml 与 cpj_*/tools/<变体>/e2e_dem/)")
    parser.add_argument("--excel", default=None,
                        help="IDC_EVM_Config*.xlsx 路径 (缺省自动发现; 变体目录下有多个表时必须指定)")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()

    cfg, cfg_source = load_feature_config(args.config)

    feat_on = {
        "check_dtc_table": cfg["check_dtc_table"],
        "gen_dem_table": cfg["gen_dem_table"]["enabled"],
        "gen_event_ctrl": cfg["gen_event_ctrl"],
        "gen_fim_code": cfg["gen_fim_code"],
    }
    needed_scripts = {
        "gen_dem_table": DEM_ARXML_SCRIPT,
        "gen_event_ctrl": EVENT_CTRL_SCRIPT,
        "gen_fim_code": FIMFID_SCRIPT,
    }
    for feat, script in needed_scripts.items():
        if feat_on[feat] and not script.is_file():
            fail("脚本不存在: %s" % script)
    enabled = [k for k in FEATURES if feat_on[k]]
    total = len(enabled)
    step_titles = {name: "Step %d/%d %s" % (i + 1, total, name)
                   for i, name in enumerate(enabled)}

    paths = resolve_repo_paths(repo, args.config)
    excel = discover_excel(repo, args.config, args.excel)

    print("[dem_autogen_etas] Excel     : %s" % excel)
    print("[dem_autogen_etas] MCU 仓库  : %s" % repo)
    print("[dem_autogen_etas] 车型      : %s" % args.config)
    print("[dem_autogen_etas] BswRta    : %s" % paths.bswrta)
    print("[dem_autogen_etas] 目标 arxml: %s" % paths.arxml)
    print("[dem_autogen_etas] 配置      : %s (%s)" % (CONFIGS_DIR, cfg_source))
    print("[dem_autogen_etas] 启用功能  : %s"
          % (" -> ".join(enabled) if enabled else "无"))

    if cfg["check_dtc_table"]:
        fail("check_dtc_table 脚本尚未引入")

    if feat_on["gen_dem_table"]:
        gd = cfg["gen_dem_table"]
        step1_t0 = time.time()
        run_step("%s 生成 Dem ARXML (jumpdown=%s, jumpup=%s)"
                 % (step_titles["gen_dem_table"], gd["jumpdown"], gd["jumpup"]),
                 [sys.executable, str(DEM_ARXML_SCRIPT), str(excel), str(paths.arxml),
                  str(gd["jumpdown"]).lower(), str(gd["jumpup"]).lower()],
                 cwd=DEM_ARXML_SCRIPT.parent)
        # 子脚本 insert_* 失败时仅打印且 exit 0; 且 Delete_DemConfigSet 会先无条件重写
        # arxml, mtime 恒新, 故再以容器级 DEF 锚点做内容兜底 (插入失败 = 锚点缺失)
        if paths.arxml.stat().st_mtime < step1_t0 - 1:
            fail("gen_dem_table 声称成功但 arxml 未被重写: %s (子脚本静默失败?)" % paths.arxml)
        arxml_text = paths.arxml.read_text(encoding="utf-8", errors="replace")
        for anchor in ("Dem/DemConfigSet/DemEventParameter</DEFINITION-REF>",
                       "Dem/DemConfigSet/DemDTC</DEFINITION-REF>"):
            if arxml_text.count(anchor) < 1:
                fail("gen_dem_table 后 arxml 缺少 %s 容器 (子脚本 insert 静默失败?): %s"
                     % (anchor.split("/")[-1].split("<")[0], paths.arxml))

        rta_home = Path(os.environ.get("RTA_CAR_HOME", str(RTA_CAR_HOME_DEFAULT)))
        isolar_dir = find_isolar_b(rta_home)
        if isolar_dir is None:
            fail("ISOLAR-AB.cmd 未找到 (RTA_CAR_HOME=%s)" % rta_home)
        isolar_cmd = isolar_cmd_path(isolar_dir)
        print("[dem_autogen_etas] ISOLAR    : %s" % isolar_cmd)
        ok = gen_bsw_headless(paths, isolar_cmd)
        if not ok:
            print("[dem_autogen_etas] headless 失败, 降级 Cobra.exe ...")
            ok = gen_bsw_cobra(paths, isolar_dir)
        if not ok:
            fail("BSW 生成失败, 详见 %s 及 %s 目录下日志"
                 % (paths.confgen_log, paths.bswrta / "_log"))

    if feat_on["gen_event_ctrl"]:
        if not paths.dem_ctrl_out.is_dir():
            fail("Dem Ctrl 输出目录不存在: %s" % paths.dem_ctrl_out)
        run_step("%s 生成 Dem Ctrl C (Dem_PrjSpecificControl.c)"
                 % step_titles["gen_event_ctrl"],
                 [sys.executable, str(EVENT_CTRL_SCRIPT), str(excel), str(paths.dem_ctrl_out)],
                 cwd=EVENT_CTRL_SCRIPT.parent)

    if feat_on["gen_fim_code"]:
        paths.fimfid_cpp_out.mkdir(parents=True, exist_ok=True)
        paths.fimfid_h_out.mkdir(parents=True, exist_ok=True)
        run_step("%s 生成 EVM FiMFID (3 个文件)" % step_titles["gen_fim_code"],
                 [sys.executable, str(FIMFID_SCRIPT), str(excel),
                  str(paths.fimfid_cpp_out), str(paths.fimfid_h_out)],
                 cwd=FIMFID_SCRIPT.parent)

    print("[dem_autogen_etas] 全部完成")


if __name__ == "__main__":
    main()
