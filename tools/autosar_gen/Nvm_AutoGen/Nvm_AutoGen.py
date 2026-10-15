#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nvm_AutoGen - Vector(TDA4)/ETAS(J6) NvM/PDM 生成统一入口.

按 MCU 仓库目录结构自动判型, 参数转发给对应子工具执行:
  ETAS (mcu_app_j6)    : 仓库下存在 cpj_*/autosar/<config>/BswRta
                         -> Nvm_AutoGen_Etas/nvm_autogen_etas.py
  Vector (mcu_app_tda4): 仓库下存在 */(<config>|veh_<config>)/microsar_cfg
                         -> Nvm_AutoGen_Davinci/Nvm_AutoGen.py

子工具的其余参数 (--excel 等通用参数, 以及 --variant/--customer/--sheet/
--skip-gen 等 Davinci 专属参数) 原样转发; 两个子工具自身的功能开关仍由
各自 configs/ 下的 yaml 控制.

用法:
  python Nvm_AutoGen.py --repo <mcu仓库路径> --config <配置名> [子工具参数...]
  加 --dry-run: 转发给子工具并运行其 dry-run (子工具只打印命令, 不实际生成)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

TOOL_ROOT = Path(__file__).resolve().parent

DAVINCI_MAIN = TOOL_ROOT / "Nvm_AutoGen_Davinci" / "Nvm_AutoGen.py"
ETAS_MAIN = TOOL_ROOT / "Nvm_AutoGen_Etas" / "nvm_autogen_etas.py"


def fail(msg):
    print("[Nvm_AutoGen] ERROR: %s" % msg)
    sys.exit(1)


def extra_value(extra, flag):
    """从转发的参数表取 flag 的值 (--flag value 或 --flag=value), 无则 None."""
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


def etas_bswrta_hits(repo: Path, config: str):
    """ETAS 变体定位, 与 nvm_autogen_etas.resolve_repo_paths 两种布局一致:
    v1 (mcu_app_j6):    cpj_*/autosar/<config>/BswRta
    v2 (mcu_app_j6_v2): cpj_*/<veh_xx>/autosar/BswRta (config 须是 <veh_xx> 子串)"""
    hits = sorted(repo.glob("cpj_*/autosar/%s/BswRta" % config))
    hits += sorted(p for p in repo.glob("cpj_*/*/autosar/BswRta")
                   if config.lower() in p.parent.parent.name.lower())
    return hits


def main():
    # 重定向到日志文件时保持行缓冲并统一 UTF-8 输出, 与子工具日志编码一致
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    parser = argparse.ArgumentParser(
        description="Vector(TDA4)/ETAS(J6) NvM/PDM 生成统一入口")
    parser.add_argument("--repo", required=True,
                        help="MCU 仓库根目录 (mcu_app_tda4 或 mcu_app_j6)")
    parser.add_argument("--config", required=True,
                        help="配置/车型名 (如 v2xsea, rx)")
    parser.add_argument("--dry-run", action="store_true",
                        help="转发给子工具执行其 dry-run (只打印命令, 不实际生成)")
    args, extra = parser.parse_known_args()

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        fail("路径不存在或不是目录: %s" % repo)

    etas = bool(etas_bswrta_hits(repo, args.config))
    davinci = bool(davinci_microsar_hits(repo, args.config, extra))
    if etas and davinci:
        fail("仓库同时匹配 ETAS 与 Davinci 结构, 无法判型: %s" % repo)
    if etas:
        platform, sub_main = "ETAS", ETAS_MAIN
    elif davinci:
        platform, sub_main = "Davinci", DAVINCI_MAIN
    else:
        fail("无法判型 (config=%s):\n"
             "  ETAS    需 cpj_*/autosar/%s/BswRta 或 cpj_*/<含%s>/autosar/BswRta\n"
             "  Davinci 需 */(%s 或 veh_%s)/microsar_cfg"
             % (args.config, args.config, args.config, args.config, args.config))
    if not sub_main.is_file():
        fail("子工具不存在: %s" % sub_main)

    sub_cmd = [sys.executable, str(sub_main),
               "--repo", str(repo), "--config", args.config] + extra
    if args.dry_run:
        sub_cmd.append("--dry-run")

    print("[Nvm_AutoGen] 平台     : %s" % platform)
    print("[Nvm_AutoGen] MCU 仓库 : %s" % repo)
    print("[Nvm_AutoGen] 配置     : %s" % args.config)
    print("[Nvm_AutoGen] 子工具   : %s" % sub_main)

    if args.dry_run:
        print("[Nvm_AutoGen] --dry-run, 将执行:")
        print("  %s" % " ".join(sub_cmd))

    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    print("[Nvm_AutoGen] ==> 运行子工具 %s" % sub_main.name)
    rc = subprocess.run(sub_cmd, env=env).returncode
    if rc != 0:
        print("[Nvm_AutoGen] ERROR: 子工具失败 (exit %d)" % rc)
        sys.exit(rc)
    print("[Nvm_AutoGen] 全部完成")


if __name__ == "__main__":
    main()
