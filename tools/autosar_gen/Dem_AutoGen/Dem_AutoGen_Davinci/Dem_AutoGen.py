#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dem_autogen - Vector Dem 自动生成工具 (一键流程).

流程分三个功能, 由 configs/ 下的 yaml 开关控制 (缺省 configs/common.yaml 全 ON):
  check_dtc_table: 步骤 1  检查 DTC 表 (check_dtc_table/check_dtc_table.py,
                   失败则中止, 不占用 license)
  gen_dem_table  : 步骤 2-8 Dem 生成
                   2. 连接 license (USB over Network Client -> CodeMeter-Stick)
                   3. 清除 DTC/Event : 调用 clear_dem_arxml/clear_dem_arxml.py
                   4. DaVinci 自动 sync (DVCfgCmd --syncSystemDescription --saveProject)
                   5. 依次执行 excel_to_csv -> gen_dtc_arxml -> gen_event_arxml
                   6. DaVinci 自动 sync
                   7. 生成 Dem 代码 (DVCfgCmd --generate --modulesToGenerate /MICROSAR/Dem)
                   8. 断开 license (无论中间步骤成败, 都会释放加密狗)
  gen_fim_code   : 步骤 9  生成 FiM 代码 (gen_fim_code/dsmFidGen.py, 纯
                   Excel->代码, 无需 license; 输出 <variant>/evm_cfg 的
                   src/_gen 与 inc/evm_cfg, .idl 产物为临时文件不保留)

map 表生成 (gen_map_yaml) 已提取至上层 Dem_AutoGen/Dem_AutoGen.py 统一执行,
本脚本单独运行时不生成 map.

用法:
  python dem_autogen.py --repo <mcu_app_tda4路径> --config v2xeu
        # 由配置名推导 variant (v2xeu -> veh_v2xeu), 按该配置的功能开关执行
  python dem_autogen.py --repo <mcu_app_tda4路径> --variant veh_v2xeu
        # 显式指定变体, 缺省 common.yaml 全流程
  python dem_autogen.py --repo <mcu_app_tda4路径> --config t1jfl3
        # 无 configs/t1jfl3.yaml 时回退 common.yaml (全 ON), 变体仍按 t1jfl3 推导
  加 --skip-gen: gen_dem_table 中只更新 arxml, 不生成 Dem 代码

参数由 --variant 或配置名从目录结构自动推导:
  variant  = --variant, 或由配置名推导 (配置名 == 变体名或 veh_+配置名, 全仓库唯一)
  customer = 仓库根下唯一含 <variant>/microsar_cfg 的一级目录 (--customer 覆盖)
  cfg_dir  = <customer>/<variant>/microsar_cfg 的唯一子目录
  sheet    = RCore_Event_<cfg_dir> (--sheet 覆盖)
  excel    = <customer>/<variant>/tools/Evm_Script 下唯一的 IDC_EVM_Config*.xlsx
             (--excel 覆盖, 须位于该 Evm_Script 下)
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

SHEET_PREFIX = "RCore_Event_"
EXCEL_GLOB = "IDC_EVM_Config*.xlsx"

CLEAR_SCRIPT = GEN_TOOLS / "clear_dem_arxml" / "clear_dem_arxml.py"
EXCEL_TO_CSV = GEN_TOOLS / "excel_to_csv" / "excel_to_csv.py"
GEN_DTC = GEN_TOOLS / "gen_dtc_arxml" / "gen_dtc_arxml.py"
GEN_EVENT = GEN_TOOLS / "gen_event_arxml" / "gen_event_arxml.py"
CHECK_EXCEL = GEN_TOOLS / "check_dtc_table" / "check_dtc_table.py"
FIM_GEN = GEN_TOOLS / "gen_fim_code" / "dsmFidGen.py"

# license: USB over Network Client 连接服务器上的 WIBU CodeMeter-Stick
# (本机装在 D:, DaVinci 生成服务器装在 C:, 依次探测)
USBCLNCMD = next(p for p in (
    Path(r"D:\Program Files\USB over Network\usbclncmd.exe"),
    Path(r"C:\Program Files\USB over Network\usbclncmd.exe"),
) if p.is_file())
LICENSE_SRV_ID = "0"
LICENSE_VID_PID_REV = "064f:2af9:0100"
LICENSE_SERIAL = "000005243417"

TEMP_CSVS = ["Merger_Total_Event_Temporary.csv", "DTC_Message.csv"]


def resolve_repo_paths(repo: Path, customer: str, variant: str, cfg_dir: str):
    """由 --repo/--variant 推导 MCU 仓库内的所有目标路径."""
    evm_script = repo / customer / variant / "tools" / "Evm_Script"
    sipaddon = (
        repo / customer / variant / "microsar_cfg" / cfg_dir
        / "build" / "SipAddon"
    )
    return SimpleNamespace(
        repo=repo,
        customer=customer,
        variant=variant,
        cfg_dir=cfg_dir,
        evm_script=evm_script,
        sipaddon=sipaddon,
        ecuc=sipaddon / "Config" / "ECUC" / "StartApplication_Dem_Dem_ecuc.arxml",
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


def discover_excel(evm_script: Path, excel_arg):
    """--excel 优先 (须位于 Evm_Script 下); 否则取唯一的 IDC_EVM_Config*.xlsx."""
    if excel_arg:
        excel = Path(excel_arg).resolve()
        if excel.parent != evm_script:
            raise ValueError(
                "--excel 必须位于 %s 下 (后续子脚本按文件名调用)" % evm_script)
        return excel
    xlsx = sorted(evm_script.glob(EXCEL_GLOB))
    if len(xlsx) != 1:
        msg = ("%s 下 %s 匹配到 %d 个, 应恰为 1 个, 可用 --excel 手动指定"
               % (evm_script, EXCEL_GLOB, len(xlsx)))
        if xlsx:
            msg += ": " + ", ".join(p.name for p in xlsx)
        raise ValueError(msg)
    return xlsx[0]


FEATURES = ("check_dtc_table", "gen_dem_table", "gen_fim_code")


def load_config(config_arg):
    """加载功能开关配置 (yaml), 返回 (配置文件路径, {feature: bool}).

    config_arg 为空时用 configs/common.yaml; 非空时按 原路径 / 加 .yaml /
    configs/<名> / configs/<名>.yaml 依次探测, 均不存在时回退 common.yaml
    并打印提示 (配置名仍可用于推导 variant).
    """
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
            print("[dem_autogen] 未找到配置 %s, 回退 common.yaml "
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
    print("[dem_autogen] ==> %s" % title)
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
        print("[dem_autogen] FAILED (exit %d, %.0fs): %s"
              % (proc.returncode, dt, title))
        sys.exit(1)
    print("[dem_autogen]     OK (%.0fs)" % dt)
    return proc


def check_dtc_table(excel):
    """调用 check_dtc_table.py 校验 DTC 表, 失败则中止."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_dtc_table", CHECK_EXCEL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print("[dem_autogen] ==> Step 1/9 检查 DTC 表 (%s)" % excel.name)
    error_count = mod.check_excel(str(excel))
    if error_count:
        print("[dem_autogen] ERROR: DTC 表校验失败, 共 %d 个错误, 已中止 (未连接 license)"
              % error_count)
        sys.exit(1)
    print("[dem_autogen]     OK, DTC 表校验通过")


def davinci_sync(step_title, paths):
    """sync + save. clear 后的中间态会有大量 reference 校验错误, 属预期, 不作为失败依据.

    判定失败: sync 未完成 / 工程被 UI 锁定 / save 未完成.
    注意: 结果信息只写进 DVCfgCmd.log (每次运行覆盖), stdout 不含关键行.
    """
    run_step(
        step_title + " (DaVinci sync)",
        [str(paths.dvcfg_cmd), "--project", str(paths.dpa),
         "--syncSystemDescription", "--saveProject", "--validate"],
        cwd=paths.sipaddon, check=False,
    )
    log = (paths.sipaddon / "DVCfgCmd.log").read_text(encoding="utf-8", errors="replace")
    if "could not be saved" in log:
        print("[dem_autogen] ERROR: 工程被锁定, 请关闭 DaVinci Configurator UI 后重试")
        sys.exit(1)
    if "Action 'Synchronizing System Description...' successfully finished" not in log:
        print("[dem_autogen] ERROR: System Description 同步未完成, 详见 %s"
              % (paths.sipaddon / "DVCfgCmd.log"))
        sys.exit(1)
    if "Project saved" not in log:
        print("[dem_autogen] ERROR: 工程保存失败, 详见 %s"
              % (paths.sipaddon / "DVCfgCmd.log"))
        sys.exit(1)
    import re
    m = re.search(r"(Validation and Generation result summary:\s*[\r\n]+.*)", log)
    if m:
        print("[dem_autogen]     %s" % " ".join(m.group(1).split()))


def license_connect(repo):
    run_step(
        "Step 2/9 连接 license (CodeMeter-Stick %s)" % LICENSE_SERIAL,
        [str(USBCLNCMD), "connect", LICENSE_SRV_ID,
         "-a", LICENSE_VID_PID_REV, "-s", LICENSE_SERIAL],
        cwd=repo,
    )


def license_disconnect(repo):
    run_step(
        "Step 8/9 断开 license",
        [str(USBCLNCMD), "disconnect", LICENSE_SRV_ID,
         "-a", LICENSE_VID_PID_REV, "-s", LICENSE_SERIAL],
        cwd=repo,
    )


def main():
    parser = argparse.ArgumentParser(description="Vector Dem auto generation tool")
    parser.add_argument("--repo", required=True,
                        help="mcu_app_tda4 仓库根目录 (绝对或相对路径)")
    parser.add_argument("--variant",
                        help="车型变体目录名 (如 veh_v2xeu; 缺省由配置名推导, "
                             "如 v2xeu -> veh_v2xeu)")
    parser.add_argument("--customer",
                        help="客户一级目录名 (缺省自动发现唯一含 "
                             "<variant>/microsar_cfg 的目录)")
    parser.add_argument("--excel",
                        help="DTC 表 xlsx 路径 (须位于该变体 Evm_Script 下; "
                             "缺省自动发现唯一的 %s)" % EXCEL_GLOB)
    parser.add_argument("--sheet",
                        help="Excel sheet 名 (缺省 %s<cfg_dir>)" % SHEET_PREFIX)
    parser.add_argument("--config",
                        help="功能开关配置 (configs/ 下的配置名或 yaml 路径, "
                             "缺省 common.yaml; 未找到时回退 common.yaml)")
    parser.add_argument("--skip-gen", action="store_true",
                        help="只更新 arxml, 不执行 Dem 代码生成")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print("[dem_autogen] ERROR: 路径不存在或不是目录: %s" % repo)
        sys.exit(1)
    try:
        cfg_path, cfg = load_config(args.config)
        if args.variant:
            customer = args.customer or discover_customer(repo, args.variant)
            variant = args.variant
        else:
            # 用请求的配置名 (而非回退后的 common.yaml) 推导 variant
            stem = Path(args.config).stem if args.config else cfg_path.stem
            customer, variant = discover_variant(repo, stem, args.customer)
        cfg_dir = discover_cfg_dir(repo, customer, variant)
        paths = resolve_repo_paths(repo, customer, variant, cfg_dir)
        excel = discover_excel(paths.evm_script, args.excel)
    except ValueError as e:
        print("[dem_autogen] ERROR: %s" % e)
        sys.exit(1)
    sheet = args.sheet or (SHEET_PREFIX + cfg_dir)

    needed = []
    if any(cfg[k] for k in ("check_dtc_table", "gen_dem_table", "gen_fim_code")):
        needed.append(excel)
    if cfg["gen_dem_table"]:
        needed += [paths.ecuc, paths.dpa, paths.dvcfg_cmd, USBCLNCMD,
                   CLEAR_SCRIPT, EXCEL_TO_CSV, GEN_DTC, GEN_EVENT]
    if cfg["gen_fim_code"]:
        needed.append(FIM_GEN)
    for f in needed:
        if not f.is_file():
            print("[dem_autogen] ERROR: 文件不存在: %s" % f)
            sys.exit(1)

    print("[dem_autogen] 变体      : %s/%s (cfg %s)"
          % (customer, variant, cfg_dir))
    print("[dem_autogen] 配置      : %s" % cfg_path.name)
    print("[dem_autogen] 功能开关  : %s" % ", ".join(
        "%s=%s" % (k, "ON" if cfg[k] else "OFF") for k in FEATURES))
    print("[dem_autogen] DTC 表    : %s" % excel.name)
    print("[dem_autogen] Sheet     : %s" % sheet)
    print("[dem_autogen] MCU 仓库  : %s" % repo)
    print("[dem_autogen] 目标 arxml: %s" % paths.ecuc)
    print("[dem_autogen] DaVinci   : %s" % paths.dpa)

    # 功能 1: 检查 DTC 表
    if cfg["check_dtc_table"]:
        check_dtc_table(excel)
    else:
        print("[dem_autogen] 配置 OFF: 跳过 check_dtc_table (Step 1)")

    # 功能 2: Dem 生成 (license + 清除 + sync + arxml + Dem 代码)
    if cfg["gen_dem_table"]:
        license_connect(repo)
        try:
            # 3. 清除 DTC 和 Event
            run_step("Step 3/9 清除 DTC/Event",
                     [sys.executable, str(CLEAR_SCRIPT), str(paths.ecuc)], cwd=repo)

            # 4. DaVinci 自动 sync
            davinci_sync("Step 4/9", paths)

            # 5. 执行 dem arxml 生成脚本
            run_step("Step 5/9a Excel 转 CSV",
                     [sys.executable, str(EXCEL_TO_CSV), excel.name, "Evm_Config_Excel_To_Csv"],
                     cwd=paths.evm_script)
            run_step("Step 5/9b 生成 DTC ARXML",
                     [sys.executable, str(GEN_DTC), excel.name, sheet, str(paths.ecuc)],
                     cwd=paths.evm_script)
            for csv in TEMP_CSVS:
                (paths.evm_script / csv).unlink(missing_ok=True)
            run_step("Step 5/9c 生成 Event ARXML",
                     [sys.executable, str(GEN_EVENT), excel.name, sheet, str(paths.ecuc)],
                     cwd=paths.evm_script)
            for csv in TEMP_CSVS:
                (paths.evm_script / csv).unlink(missing_ok=True)

            # 6. DaVinci 自动 sync
            davinci_sync("Step 6/9", paths)

            # 7. 生成 Dem 代码
            if args.skip_gen:
                print("[dem_autogen] --skip-gen: 跳过 Dem 代码生成")
            else:
                run_step("Step 7/9 生成 Dem 代码",
                         [str(paths.dvcfg_cmd), "--project", str(paths.dpa),
                          "--generate", "--modulesToGenerate", "/MICROSAR/Dem"],
                         cwd=paths.sipaddon)
        finally:
            license_disconnect(repo)
    else:
        print("[dem_autogen] 配置 OFF: 跳过 gen_dem_table (Step 2-8, 不占用 license)")

    # 功能 3: 生成 FiM 代码 (纯 Excel -> 代码, 无需 license; cwd 用临时目录,
    #        使 dsmFidGen 产生的中间文件 Merger_Total_FID.xlsx 随临时目录清除)
    fim_hpp = (repo / customer / variant / "evm_cfg" / "inc" / "evm_cfg"
               / "zx_sys_evm_cfg_fimcfg.hpp")
    if cfg["gen_fim_code"]:
        fim_gen_dir = fim_hpp.parent.parent.parent / "src" / "_gen"
        for d in (fim_gen_dir, fim_hpp.parent):
            d.mkdir(parents=True, exist_ok=True)
        idl_tmp = Path(tempfile.mkdtemp(prefix="dem_fim_idl_"))
        try:
            run_step("Step 9/9 生成 FiM 代码",
                     [sys.executable, str(FIM_GEN), str(FIM_GEN.parent),
                      str(excel), sheet, str(fim_gen_dir), str(fim_hpp.parent),
                      str(fim_hpp.parent), str(idl_tmp)],
                     cwd=idl_tmp)
        finally:
            shutil.rmtree(idl_tmp, ignore_errors=True)
    else:
        print("[dem_autogen] 配置 OFF: 跳过 gen_fim_code (Step 9)")

    print("[dem_autogen] 全部完成")


if __name__ == "__main__":
    main()
