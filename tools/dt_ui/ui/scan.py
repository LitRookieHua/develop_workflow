"""纯逻辑扫描：configs 配置列表与 testcase 例程树（无 Qt 依赖，可单测）。"""
from __future__ import annotations

from pathlib import Path

# dem 子命令的 map 文件不是项目配置，扫描时排除
MAP_FILES = {"dtc_map.yaml", "event_map.yaml", "fimfid_map.yaml", "dem_dids.yaml"}


def scan_configs(configs_dir) -> list[tuple[str, Path]]:
    """扫 configs/ 全部配置 yaml（含子目录），返回 (显示名, 路径) 列表。

    显示名 = 相对 configs 的路径去 .yaml（正斜杠，如 n60/n60_cx、example_mock），
    map 文件排除，按显示名排序。
    """
    root = Path(configs_dir)
    out: list[tuple[str, Path]] = []
    if not root.is_dir():
        return out
    for p in root.rglob("*.yaml"):
        if p.name in MAP_FILES:
            continue
        rel = p.relative_to(root).with_suffix("")
        out.append((rel.as_posix(), p))
    return sorted(out)


def scan_routines(testcase_root, project: str) -> list[tuple[str, Path]]:
    """扫 testcase/<项目>/ 下全部用例 yaml（含子目录），返回 (显示名, 路径) 列表。

    显示名 = 相对 testcase_root/<项目> 的路径去 .yaml；项目目录不存在返回 []。
    """
    root = Path(testcase_root)
    base = root / project
    if not base.is_dir():
        return []
    out = []
    for p in base.rglob("*.yaml"):
        rel = p.relative_to(base).with_suffix("")
        out.append((rel.as_posix(), p))
    return sorted(out)
