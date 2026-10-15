#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dem_AutoGen - Vector(TDA4)/ETAS(J6) Dem 生成统一入口.

按 MCU 仓库目录结构自动判型, 参数转发给对应子工具执行, 子工具成功后
统一执行 gen_map_yaml 生成 map 表 (dtc_map/event_map, fimfid hpp 存在时
加 fimfid_map; 自带拷贝到 10_tools/diag/configs/<变体>/):
  ETAS (mcu_app_j6)    : 仓库下存在 cpj_*/autosar/<config>/BswRta
                         -> Dem_AutoGen_Etas/dem_autogen_etas.py
                         map 输出到 Excel 同目录 (cpj_*/tools/<config>/e2e_dem)
  Vector (mcu_app_tda4): 仓库下存在 */(<config>|veh_<config>)/microsar_cfg
                         -> Dem_AutoGen_Davinci/Dem_AutoGen.py
                         map 输出到 <变体>/tools/Evm_Script/Evm_Config_Excel_To_Csv

子工具的其余参数 (--excel/--variant/--customer/--sheet/--skip-gen 等)
原样转发; 两个子工具自身的功能开关仍由各自 configs/ 下的 yaml 控制.

用法:
  python Dem_AutoGen.py --repo <mcu仓库路径> --config <配置名> [子工具参数...]
  加 --dry-run: 只打印将执行的命令, 不实际运行
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

TOOL_ROOT = Path(__file__).resolve().parent

DAVINCI_MAIN = TOOL_ROOT / "Dem_AutoGen_Davinci" / "Dem_AutoGen.py"
ETAS_MAIN = TOOL_ROOT / "Dem_AutoGen_Etas" / "dem_autogen_etas.py"
GEN_MAP = TOOL_ROOT / "gen_map_yaml" / "gen_map_yaml.py"

FIMCFG_HPP = "zx_sys_evm_cfg_fimcfg.hpp"


def fail(msg):
    print("[Dem_AutoGen] ERROR: %s" % msg)
    sys.exit(1)


def extra_value(extra, flag):
    """从转发的参数表中取 flag 的值 (--flag value 或 --flag=value), 无则 None."""
    for i, a in enumerate(extra):
        if a == flag and i + 1 < len(extra):
            return extra[i + 1]
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return None


def davinci_microsar_hits(repo: Path, config: str, extra):
    """Davinci 变体定位: */(<variant>)/microsar_cfg, --variant/--customer 收窄."""
    variant = extra_value(extra, "--variant")
    customer = extra_value(extra, "--customer")
    cust_pat = customer if customer else "*"
    var_names = (variant,) if variant else (config, "veh_" + config)
    hits = []
    for v in var_names:
        hits += sorted(repo.glob("%s/%s/microsar_cfg" % (cust_pat, v)))
    return hits


def davinci_map_args(repo: Path, config: str, extra):
    """推导 Davinci 的 gen_map_yaml 参数 (project_dir, out_dir, fimcfg)."""
    variant = extra_value(extra, "--variant")
    customer = extra_value(extra, "--customer")
    cust_pat = customer if customer else "*"
    var_names = (variant,) if variant else (config, "veh_" + config)
    hits = []
    for v in var_names:
        hits += sorted(repo.glob("%s/%s/microsar_cfg/*/build/SipAddon"
                                 % (cust_pat, v)))
    if len(hits) != 1:
        fail("Davinci SipAddon 定位失败 (匹配 %d 个, 需恰好 1; 可用 "
             "--variant/--customer 收窄): %s"
             % (len(hits), [str(h) for h in hits]))
    sipaddon = hits[0].resolve()
    # repo/<customer>/<variant>/microsar_cfg/<cfg>/build/SipAddon -> 取变体目录
    variant_dir = sipaddon.parents[3]
    project_dir = sipaddon
    out_dir = variant_dir / "tools" / "Evm_Script" / "Evm_Config_Excel_To_Csv"
    fimcfg = variant_dir / "evm_cfg" / "inc" / "evm_cfg" / FIMCFG_HPP
    return project_dir, out_dir, fimcfg


def etas_map_args(repo: Path, config: str, extra):
    """推导 ETAS 的 gen_map_yaml 参数 (project_dir, out_dir, fimcfg)."""
    hits = sorted(repo.glob("cpj_*/autosar/%s/BswRta" % config))
    if len(hits) != 1:
        fail("ETAS BswRta 定位失败: cpj_*/autosar/%s/BswRta 匹配 %d 个 (需恰好 1)"
             % (config, len(hits)))
    bswrta = hits[0].resolve()
    excel_arg = extra_value(extra, "--excel")
    if excel_arg:
        out_dir = Path(excel_arg).resolve().parent
    else:
        xs = [p for p in sorted(
                  repo.glob("cpj_*/tools/%s/e2e_dem/IDC_EVM_Config*.xlsx"
                            % config))
              if not p.name.endswith("_merged.xlsx")]
        if len(xs) != 1:
            fail("ETAS map 输出目录定位失败: cpj_*/tools/%s/e2e_dem/"
                 "IDC_EVM_Config*.xlsx (排除 _merged) 匹配 %d 个 (需恰好 1; "
                 "可用 --excel 指定)" % (config, len(xs)))
        out_dir = xs[0].parent
    cpj = bswrta.parent.parent.parent   # cpj_x/autosar/<config>/BswRta -> cpj_x
    fimcfg = (cpj / "evm_cfg" / "var" / "inc" / "vehicle" / config
              / "evm_cfg" / FIMCFG_HPP)
    return bswrta, out_dir, fimcfg


def main():
    # 重定向到日志文件时保持行缓冲, 使本脚本与子进程输出顺序一致
    sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(
        description="Vector(TDA4)/ETAS(J6) Dem 生成统一入口")
    parser.add_argument("--repo", required=True,
                        help="MCU 仓库根目录 (mcu_app_tda4 或 mcu_app_j6)")
    parser.add_argument("--config", required=True,
                        help="配置/车型名 (如 v2xeu, rx, n60)")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印将执行的命令, 不实际运行")
    args, extra = parser.parse_known_args()

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        fail("路径不存在或不是目录: %s" % repo)

    etas = bool(list(repo.glob("cpj_*/autosar/%s/BswRta" % args.config)))
    davinci = bool(davinci_microsar_hits(repo, args.config, extra))
    if etas and davinci:
        fail("仓库同时匹配 ETAS 与 Davinci 结构, 无法判型: %s" % repo)
    if etas:
        platform, sub_main = "ETAS", ETAS_MAIN
    elif davinci:
        platform, sub_main = "Davinci", DAVINCI_MAIN
    else:
        fail("无法判型 (config=%s):\n"
             "  ETAS    需 cpj_*/autosar/%s/BswRta\n"
             "  Davinci 需 */(%s 或 veh_%s)/microsar_cfg"
             % (args.config, args.config, args.config, args.config))
    if not sub_main.is_file():
        fail("子工具不存在: %s" % sub_main)
    if not GEN_MAP.is_file():
        fail("脚本不存在: %s" % GEN_MAP)

    if platform == "ETAS":
        project_dir, out_dir, fimcfg = etas_map_args(repo, args.config, extra)
    else:
        project_dir, out_dir, fimcfg = davinci_map_args(repo, args.config, extra)
    sub_cmd = [sys.executable, str(sub_main),
               "--repo", str(repo), "--config", args.config] + extra
    map_cmd = [sys.executable, str(GEN_MAP), str(project_dir), str(out_dir)]
    if fimcfg.is_file():
        map_cmd.append(str(fimcfg))

    print("[Dem_AutoGen] 平台     : %s" % platform)
    print("[Dem_AutoGen] MCU 仓库 : %s" % repo)
    print("[Dem_AutoGen] 配置     : %s" % args.config)
    print("[Dem_AutoGen] 子工具   : %s" % sub_main)
    print("[Dem_AutoGen] map 工程 : %s" % project_dir)
    print("[Dem_AutoGen] map 输出 : %s" % out_dir)
    if len(map_cmd) > 4:
        print("[Dem_AutoGen] fimfid源 : %s" % fimcfg)

    if args.dry_run:
        print("[Dem_AutoGen] --dry-run, 将依次执行:")
        print("  %s" % " ".join(sub_cmd))
        print("  %s" % " ".join(map_cmd))
        return

    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    print("[Dem_AutoGen] ==> 运行子工具 %s" % sub_main.name)
    rc = subprocess.run(sub_cmd, env=env).returncode
    if rc != 0:
        print("[Dem_AutoGen] ERROR: 子工具失败 (exit %d), 跳过 map 生成" % rc)
        sys.exit(rc)

    print("[Dem_AutoGen] ==> 生成 map 表 (dtc/event%s.yaml)"
          % ("/fimfid" if len(map_cmd) > 4 else ""))
    rc = subprocess.run(map_cmd, env=env).returncode
    if rc != 0:
        print("[Dem_AutoGen] ERROR: gen_map_yaml 失败 (exit %d)" % rc)
        sys.exit(rc)
    print("[Dem_AutoGen] 全部完成")


if __name__ == "__main__":
    main()
