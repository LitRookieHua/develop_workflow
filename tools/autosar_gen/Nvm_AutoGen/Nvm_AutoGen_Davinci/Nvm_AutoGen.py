#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nvm_autogen - Vector NvM/PDM 自动生成工具 (一键流程).

流程分三个功能, 由 configs/ 下的 yaml 开关控制 (缺省 configs/common.yaml):
  check_nvm_table: 检查 NVM 表 (脚本尚未引入, 开启即报错中止)
  gen_nvm_arxml  : 1. 连接 license (USB over Network Client -> CodeMeter-Stick)
                   2. 更新 NVM arxml (gen_nvm_arxml/GenPdmARXML.py:
                      NVM_SWC_1.arxml + DataTypes.arxml)
                   3. DaVinci 自动 sync (DVCfgCmd --syncSystemDescription
                      --saveProject)
                   4. 生成 NvM 代码 (DVCfgCmd --generate
                      --modulesToGenerate /MICROSAR/NvM; --skip-gen 跳过)
                   5. 断开 license (无论中间步骤成败, 都会释放加密狗)
  gen_pdm_code   : 6. 生成 PDM 代码 (gen_pdm_code/CrmGen.py, 纯 Excel->代码,
                   无需 license; 读步骤 4 产物 microsar_cfg/<cfg>/src/GenData/
                   NvM_Cfg.h, 输出 <变体>/pdm_cfg 的 4 个文件)

用法:
  python Nvm_AutoGen.py --repo <mcu_app_tda4路径> --config v2xsea
        # 由配置名推导 variant (v2xsea -> veh_v2xsea), 按该配置的功能开关执行
  python Nvm_AutoGen.py --repo <mcu_app_tda4路径> --variant veh_v2xsea
        # 显式指定变体, 缺省 common.yaml 全流程
  加 --dry-run: 只打印推导路径与将执行的命令, 不实际运行
  加 --skip-gen: gen_nvm_arxml 中只更新 arxml, 不生成 NvM 代码

参数由 --variant 或配置名从目录结构自动推导:
  variant  = --variant, 或由配置名推导 (配置名 == 变体名或 veh_+配置名, 全仓库唯一)
  customer = 仓库根下唯一含 <variant>/microsar_cfg 的一级目录 (--customer 覆盖)
  cfg_dir  = <customer>/<variant>/microsar_cfg 的唯一子目录
  excel    = <customer>/<variant>/tools/Pdm_Script/ 下唯一 *NVM_List*.xlsx,
             回退 <变体>/tools/ 与仓库 tools/Gen_Pdm_Script/ (--excel 覆盖)
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import yaml

GEN_TOOLS = Path(__file__).resolve().parent

SHEET = "01_NVM_List"
EXCEL_GLOB = "*NVM_List*.xlsx"

GEN_NVM_SCRIPT = GEN_TOOLS / "gen_nvm_arxml" / "GenPdmARXML.py"
CRM_GEN_SCRIPT = GEN_TOOLS / "gen_pdm_code" / "CrmGen.py"

# license: USB over Network Client 连接服务器上的 WIBU CodeMeter-Stick
# (本机装在 D:, 生成服务器 13.10 装在 C:, 依次探测)
USBCLNCMD = next(p for p in (
    Path(r"D:\Program Files\USB over Network\usbclncmd.exe"),
    Path(r"C:\Program Files\USB over Network\usbclncmd.exe"),
) if p.is_file())
LICENSE_SRV_ID = "0"
LICENSE_VID_PID_REV = "064f:2af9:0100"
LICENSE_SERIAL = "000005243417"

DRY = False


def resolve_repo_paths(repo: Path, customer: str, variant: str, cfg_dir: str):
    """由 --repo/--variant 推导 MCU 仓库内的所有目标路径."""
    variant_dir = repo / customer / variant
    microsar = variant_dir / "microsar_cfg" / cfg_dir
    sipaddon = microsar / "build" / "SipAddon"
    pdm_inc = variant_dir / "pdm_cfg" / "inc" / "pdm_cfg"
    pdm_src = variant_dir / "pdm_cfg" / "src"
    return SimpleNamespace(
        repo=repo,
        customer=customer,
        variant=variant,
        cfg_dir=cfg_dir,
        variant_tools=variant_dir / "tools",
        nvm_swc=(sipaddon / "Config" / "Developer" / "ComponentTypes"
                 / "NVM_SWC_1.arxml"),
        datatype=sipaddon / "Config" / "Developer" / "DataTypes.arxml",
        nvm_cfg_h=microsar / "src" / "GenData" / "NvM_Cfg.h",
        pdm_cfg_h=pdm_inc / "pdm_cfg.h",
        pdmdb_h=pdm_inc / "pdmdb.h",
        pdmdb_cpp=pdm_src / "pdmdb.cpp",
        pdm_dataitem_cpp=pdm_src / "pdm_cfg_dataitem_config.cpp",
        sipaddon=sipaddon,
        dpa=sipaddon / "Demo.dpa",
        dvcfg_cmd=(repo / "microsar_tools_tda4" / "DaVinciConfigurator"
                   / "Core" / "DVCfgCmd.exe"),
    )


def discover_customer(repo: Path, variant: str):
    """customer = 仓库根下唯一含 <variant>/microsar_cfg 的一级目录."""
    matches = sorted(p for p in repo.iterdir()
                     if p.is_dir() and (p / variant / "microsar_cfg").is_dir())
    if len(matches) != 1:
        msg = ("%s 下含 %s/microsar_cfg 的一级目录应恰为 1 个, 实际 %d 个"
               " (可用 --customer 指定)" % (repo, variant, len(matches)))
        if matches:
            msg += ": " + ", ".join(p.name for p in matches)
        raise ValueError(msg)
    return matches[0].name


def discover_variant(repo: Path, config_stem: str, customer=None):
    """--variant 缺省时由配置名推导变体: 变体目录名 == 配置名或 veh_+配置名,
    全仓库 (或指定 customer 下) 唯一匹配, 返回 (customer, variant)."""
    wanted = (config_stem, "veh_" + config_stem)
    cust_dirs = ([repo / customer] if customer
                 else sorted(p for p in repo.iterdir() if p.is_dir()))
    matches = []
    for cust in cust_dirs:
        if not cust.is_dir():
            continue
        for var in sorted(cust.iterdir()):
            if (var.is_dir() and (var / "microsar_cfg").is_dir()
                    and var.name in wanted):
                matches.append((cust.name, var.name))
    if len(matches) != 1:
        msg = ("配置名 %s 未能唯一对应变体目录 (%s 或 veh_%s), 匹配 %d 个, "
               "请显式传入 --variant"
               % (config_stem, config_stem, config_stem, len(matches)))
        if matches:
            msg += ": " + ", ".join("%s/%s" % m for m in matches)
        raise ValueError(msg)
    return matches[0]


def discover_cfg_dir(repo: Path, customer: str, variant: str):
    """cfg_dir = <customer>/<variant>/microsar_cfg 的唯一子目录."""
    microsar = repo / customer / variant / "microsar_cfg"
    cfg_dirs = (sorted(p.name for p in microsar.iterdir() if p.is_dir())
                if microsar.is_dir() else [])
    if len(cfg_dirs) != 1:
        raise ValueError(
            "%s 下应恰有 1 个配置子目录 (cfg_dir), 实际 %d 个: %s"
            % (microsar, len(cfg_dirs), ", ".join(cfg_dirs)))
    return cfg_dirs[0]


def discover_excel(paths, excel_arg):
    """--excel 优先; 否则先在变体 tools/Pdm_Script/ 下找唯一 *NVM_List*.xlsx
    (排除 ~$ Office 锁文件), 回退变体 tools/ 与仓库 tools/Gen_Pdm_Script/."""
    if excel_arg:
        excel = Path(excel_arg).resolve()
        if not excel.is_file():
            raise ValueError("Excel 不存在: %s" % excel)
        return excel
    searched = []
    for base in (paths.variant_tools / "Pdm_Script", paths.variant_tools,
                 paths.repo / "tools" / "Gen_Pdm_Script"):
        searched.append(base)
        hits = [p for p in sorted(base.glob(EXCEL_GLOB)) if not p.name.startswith("~$")] \
            if base.is_dir() else []
        if len(hits) > 1:
            raise ValueError(
                "%s 下 %s 匹配 %d 个, 请 --excel 指定: %s"
                % (base, EXCEL_GLOB, len(hits), [p.name for p in hits]))
        if len(hits) == 1:
            return hits[0]
    raise ValueError(
        "未找到 %s (搜索: %s), 请 --excel 指定"
        % (EXCEL_GLOB, ", ".join(str(s) for s in searched)))


FEATURES = ("check_nvm_table", "gen_nvm_arxml", "gen_pdm_code")


def load_config(config_arg):
    """加载功能开关配置 (yaml), 返回 (配置文件路径, {feature: bool})."""
    if config_arg:
        candidates = [Path(config_arg), Path(config_arg + ".yaml"),
                      GEN_TOOLS / "configs" / config_arg,
                      GEN_TOOLS / "configs" / (config_arg + ".yaml")]
        path = next((p for p in candidates if p.is_file()), None)
        if path is None:
            path = GEN_TOOLS / "configs" / "common.yaml"
            available = ", ".join(
                p.stem for p in sorted((GEN_TOOLS / "configs").glob("*.yaml"))
            ) if (GEN_TOOLS / "configs").is_dir() else "无"
            print("[nvm_autogen] 未找到配置 %s, 回退 common.yaml "
                  "(configs/ 下可用: %s)" % (config_arg, available))
    else:
        path = GEN_TOOLS / "configs" / "common.yaml"
    if not path.is_file():
        raise ValueError("未找到默认配置 %s" % path)

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    unknown = sorted(set(data) - set(FEATURES))
    if unknown:
        raise ValueError("%s 含未知功能项: %s (可用: %s)"
                         % (path, ", ".join(unknown), ", ".join(FEATURES)))
    missing = sorted(set(FEATURES) - set(data))
    if missing:
        raise ValueError("%s 缺少功能项: %s" % (path, ", ".join(missing)))

    cfg = {}
    for key in FEATURES:
        val = data[key]
        if isinstance(val, bool):
            cfg[key] = val
        elif isinstance(val, str) and val.upper() in ("ON", "OFF"):
            cfg[key] = val.upper() == "ON"
        else:
            raise ValueError("%s 中 %s 的值应为 ON 或 OFF" % (path, key))
    return path, cfg


def run_step(title, cmd, cwd, tail_on_fail=25, check=True):
    print("[nvm_autogen] ==> %s" % title)
    if DRY:
        print("[nvm_autogen]     [dry-run] %s"
              % " ".join(str(c) for c in cmd))
        return None
    t0 = time.time()
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    dt = time.time() - t0
    if check and proc.returncode != 0:
        print(proc.stdout[-3000:] if proc.stdout else "")
        print(proc.stderr[-3000:] if proc.stderr else "")
        print("[nvm_autogen] FAILED (exit %d, %.0fs): %s"
              % (proc.returncode, dt, title))
        sys.exit(1)
    print("[nvm_autogen]     OK (%.0fs)" % dt)
    return proc


def davinci_sync(step_title, paths):
    """sync + save. 中间态可能有 reference 校验错误, 属预期, 不作为失败依据.

    判定失败: sync 未完成 / 工程被 UI 锁定 / save 未完成.
    注意: 结果信息只写进 DVCfgCmd.log (每次运行覆盖), stdout 不含关键行.
    """
    run_step(
        step_title + " (DaVinci sync)",
        [str(paths.dvcfg_cmd), "--project", str(paths.dpa),
         "--syncSystemDescription", "--saveProject", "--validate"],
        cwd=paths.sipaddon, check=False,
    )
    if DRY:
        return
    log = (paths.sipaddon / "DVCfgCmd.log").read_text(encoding="utf-8", errors="replace")
    if "could not be saved" in log:
        print("[nvm_autogen] ERROR: 工程被锁定, 请关闭 DaVinci Configurator UI 后重试")
        sys.exit(1)
    if "Action 'Synchronizing System Description...' successfully finished" not in log:
        print("[nvm_autogen] ERROR: System Description 同步未完成, 详见 %s"
              % (paths.sipaddon / "DVCfgCmd.log"))
        sys.exit(1)
    if "Project saved" not in log:
        print("[nvm_autogen] ERROR: 工程保存失败, 详见 %s"
              % (paths.sipaddon / "DVCfgCmd.log"))
        sys.exit(1)
    import re
    m = re.search(r"(Validation and Generation result summary:\s*[\r\n]+.*)", log)
    if m:
        print("[nvm_autogen]     %s" % " ".join(m.group(1).split()))


def license_connect(repo):
    run_step(
        "连接 license (CodeMeter-Stick %s)" % LICENSE_SERIAL,
        [str(USBCLNCMD), "connect", LICENSE_SRV_ID,
         "-a", LICENSE_VID_PID_REV, "-s", LICENSE_SERIAL],
        cwd=repo,
    )


def license_disconnect(repo):
    run_step(
        "断开 license",
        [str(USBCLNCMD), "disconnect", LICENSE_SRV_ID,
         "-a", LICENSE_VID_PID_REV, "-s", LICENSE_SERIAL],
        cwd=repo,
    )


def main():
    parser = argparse.ArgumentParser(description="Vector NvM/PDM auto generation tool")
    parser.add_argument("--repo", required=True,
                        help="mcu_app_tda4 仓库根目录 (绝对或相对路径)")
    parser.add_argument("--variant",
                        help="车型变体目录名 (如 veh_v2xsea; 缺省由配置名推导)")
    parser.add_argument("--customer",
                        help="客户一级目录名 (缺省自动发现唯一含 "
                             "<variant>/microsar_cfg 的目录)")
    parser.add_argument("--excel",
                        help="NVM 表 xlsx 路径 (缺省自动发现唯一的 %s)" % EXCEL_GLOB)
    parser.add_argument("--sheet",
                        help="Excel sheet 名 (缺省 %s)" % SHEET)
    parser.add_argument("--config",
                        help="功能开关配置 (configs/ 下的配置名或 yaml 路径, "
                             "缺省 common.yaml; 未找到时回退 common.yaml)")
    parser.add_argument("--skip-gen", action="store_true",
                        help="只更新 arxml, 不执行 NvM 代码生成")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印推导路径与将执行的命令, 不实际运行")
    args = parser.parse_args()
    global DRY
    DRY = args.dry_run

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print("[nvm_autogen] ERROR: 路径不存在或不是目录: %s" % repo)
        sys.exit(1)
    try:
        cfg_path, cfg = load_config(args.config)
        if args.variant:
            customer = args.customer or discover_customer(repo, args.variant)
            variant = args.variant
        else:
            stem = Path(args.config).stem if args.config else cfg_path.stem
            customer, variant = discover_variant(repo, stem, args.customer)
        cfg_dir = discover_cfg_dir(repo, customer, variant)
        paths = resolve_repo_paths(repo, customer, variant, cfg_dir)
        excel = discover_excel(paths, args.excel)
    except ValueError as e:
        print("[nvm_autogen] ERROR: %s" % e)
        sys.exit(1)
    sheet = args.sheet or SHEET

    needed = []
    if any(cfg[k] for k in FEATURES):
        needed.append(excel)
    if cfg["gen_nvm_arxml"]:
        needed += [paths.nvm_swc, paths.datatype, paths.dpa, paths.dvcfg_cmd,
                   USBCLNCMD, GEN_NVM_SCRIPT]
    if cfg["gen_pdm_code"]:
        needed += [CRM_GEN_SCRIPT] + [
            CRM_GEN_SCRIPT.parent / "template" / name for name in
            ("pdm_cfg_T.h", "pdm_cfg_dataitem_config_T.cpp",
             "pdmdb_T.cpp", "pdmdb_T.h")]
    for f in needed:
        if not f.exists():
            print("[nvm_autogen] ERROR: 文件不存在: %s" % f)
            sys.exit(1)

    print("[nvm_autogen] 变体      : %s/%s (cfg %s)"
          % (customer, variant, cfg_dir))
    print("[nvm_autogen] 配置      : %s" % cfg_path.name)
    print("[nvm_autogen] 功能开关  : %s" % ", ".join(
        "%s=%s" % (k, "ON" if cfg[k] else "OFF") for k in FEATURES))
    print("[nvm_autogen] NVM 表    : %s" % excel)
    print("[nvm_autogen] Sheet     : %s" % sheet)
    print("[nvm_autogen] MCU 仓库  : %s" % repo)
    print("[nvm_autogen] 目标 arxml: %s" % paths.nvm_swc)
    print("[nvm_autogen] DaVinci   : %s" % paths.dpa)
    if DRY:
        print("[nvm_autogen] *** DRY-RUN 模式, 只打印命令不执行 ***")

    # 功能 1: 检查 NVM 表 (脚本尚未引入)
    if cfg["check_nvm_table"]:
        print("[nvm_autogen] ERROR: check_nvm_table 脚本尚未引入, "
              "请将配置改为 OFF")
        sys.exit(1)

    # 功能 2: 更新 NVM arxml + NvM 代码生成 (license 全程持有)
    if cfg["gen_nvm_arxml"]:
        license_connect(repo)
        try:
            t0 = time.time()
            run_step("更新 NVM arxml (NVM_SWC_1 + DataTypes)",
                     [sys.executable, str(GEN_NVM_SCRIPT), str(excel), sheet,
                      str(paths.nvm_swc), str(paths.datatype)],
                     cwd=GEN_NVM_SCRIPT.parent)
            # 子脚本静默失败兜底: arxml 应被重写且仍含 RAM-BLOCK 容器
            if not DRY:
                if paths.nvm_swc.stat().st_mtime < t0 - 1:
                    print("[nvm_autogen] ERROR: 脚本声称成功但 arxml 未被重写: %s"
                          % paths.nvm_swc)
                    sys.exit(1)
                text = paths.nvm_swc.read_text(
                    encoding="utf-8", errors="replace")
                if "<RAM-BLOCK " not in text:
                    print("[nvm_autogen] ERROR: arxml 缺少 RAM-BLOCK 容器 "
                          "(子脚本静默失败?): %s" % paths.nvm_swc)
                    sys.exit(1)

            davinci_sync("同步 System Description", paths)

            if args.skip_gen:
                print("[nvm_autogen] --skip-gen: 跳过 NvM 代码生成")
            else:
                run_step("生成 NvM 代码",
                         [str(paths.dvcfg_cmd), "--project", str(paths.dpa),
                          "--generate", "--modulesToGenerate", "/MICROSAR/NvM"],
                         cwd=paths.sipaddon)
        finally:
            license_disconnect(repo)
    else:
        print("[nvm_autogen] 配置 OFF: 跳过 gen_nvm_arxml (不占用 license)")

    # 功能 3: 生成 PDM 代码 (纯 Excel -> 代码, 无需 license; cwd 用临时目录,
    #        使 CrmGen 产生的中间文件 Excel_To_Csv/ 随临时目录清除)
    if cfg["gen_pdm_code"]:
        pdm_tmp = Path(tempfile.mkdtemp(prefix="nvm_crm_"))
        try:
            if not DRY and not paths.nvm_cfg_h.is_file():
                print("[nvm_autogen] ERROR: NvM_Cfg.h 不存在: %s\n"
                      "  请先开启 gen_nvm_arxml 完整生成 (或历史产物未入库)"
                      % paths.nvm_cfg_h)
                sys.exit(1)
            for d in (paths.pdm_cfg_h.parent, paths.pdmdb_cpp.parent):
                d.mkdir(parents=True, exist_ok=True)
            pdm_t0 = time.time()
            run_step("生成 PDM 代码 (pdm_cfg.h/pdmdb.h/pdmdb.cpp/dataitem_config.cpp)",
                     [sys.executable, str(CRM_GEN_SCRIPT), str(excel), sheet,
                      str(paths.nvm_cfg_h), str(paths.pdm_cfg_h),
                      str(paths.pdmdb_h), str(paths.pdmdb_cpp),
                      str(paths.pdm_dataitem_cpp),
                      str(CRM_GEN_SCRIPT.parent / "template")],
                     cwd=pdm_tmp)
            # CrmGen 静默失败兜底 (参数错/默认值错时 exit 0 但不写文件):
            # 4 个输出文件都应被重写
            if not DRY:
                for out in (paths.pdm_cfg_h, paths.pdmdb_h,
                            paths.pdmdb_cpp, paths.pdm_dataitem_cpp):
                    if not out.is_file() or out.stat().st_mtime < pdm_t0 - 1:
                        print("[nvm_autogen] ERROR: CrmGen 声称成功但输出未更新: %s"
                              " (子脚本静默失败?)" % out)
                        sys.exit(1)
        finally:
            shutil.rmtree(pdm_tmp, ignore_errors=True)
    else:
        print("[nvm_autogen] 配置 OFF: 跳过 gen_pdm_code")

    print("[nvm_autogen] 全部完成")


if __name__ == "__main__":
    main()
