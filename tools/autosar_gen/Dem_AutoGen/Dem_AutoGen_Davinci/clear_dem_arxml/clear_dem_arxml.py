#!/usr/bin/env python3
"""clear_dem_arxml - 清空 DemConfigSet 中的 DTC 和 Event, 只保留 DemEventParameter 模板容器.

处理逻辑:
  1. 备份目标 arxml 文件 (脚本目录下 backup/, 后缀 .bak_时间戳)
  2. 在 DemConfigSet 容器的 <SUB-CONTAINERS> 中找到 SHORT-NAME 为
     "DemEventParameter" 的模板容器, 将其 DemEventId 改为 1
  3. 删除 <SUB-CONTAINERS> 与 </SUB-CONTAINERS> 之间的所有内容
  4. 将模板容器放入 <SUB-CONTAINERS> 与 </SUB-CONTAINERS> 之间

用法:
  python clear_dem_arxml.py <ecuc_arxml_path>
"""

import re
import shutil
import sys
import time
from pathlib import Path

DEM_CONFIG_SET_REF = (
    '<DEFINITION-REF DEST="ECUC-PARAM-CONF-CONTAINER-DEF">'
    "/MICROSAR/Dem/DemConfigSet</DEFINITION-REF>"
)
TEMPLATE_SHORT_NAME = "<SHORT-NAME>DemEventParameter</SHORT-NAME>"
EVENT_ID_REF_END = "DemEventParameter/DemEventId</DEFINITION-REF>"

SUB_OPEN = "<SUB-CONTAINERS>"
SUB_CLOSE = "</SUB-CONTAINERS>"
CTR_OPEN = "<ECUC-CONTAINER-VALUE"
CTR_CLOSE = "</ECUC-CONTAINER-VALUE>"


def find_matching_close(text, open_pos, open_tag, close_tag):
    """从 open_pos 处的 open_tag 起, 深度计数返回匹配 close_tag 的起始位置."""
    depth = 0
    pos = open_pos
    while True:
        next_open = text.find(open_tag, pos)
        next_close = text.find(close_tag, pos)
        if next_close < 0:
            raise ValueError("未找到匹配的 %s" % close_tag)
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + len(open_tag)
        else:
            depth -= 1
            if depth == 0:
                return next_close
            pos = next_close + len(close_tag)


def iter_top_level_containers(inner):
    """遍历 SUB-CONTAINERS 内容中的一级 ECUC-CONTAINER-VALUE, 逐个返回 (start, end).

    start 含行首缩进, end 含 </ECUC-CONTAINER-VALUE> 闭合标签.
    """
    pos = 0
    while True:
        tag_start = inner.find(CTR_OPEN, pos)
        if tag_start < 0:
            return
        close_start = find_matching_close(inner, tag_start, CTR_OPEN, CTR_CLOSE)
        start = inner.rfind("\n", 0, tag_start) + 1
        end = close_start + len(CTR_CLOSE)
        yield start, end
        pos = end


def clear_dtc_events(target: Path):
    text = target.read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in text[:2000] else "\n"

    ref_pos = text.find(DEM_CONFIG_SET_REF)
    if ref_pos < 0:
        raise ValueError("未找到 DemConfigSet 的 DEFINITION-REF")

    sub_open = text.find(SUB_OPEN, ref_pos)
    if sub_open < 0:
        raise ValueError("DemConfigSet 后未找到 <SUB-CONTAINERS>")

    sub_close_start = find_matching_close(text, sub_open, SUB_OPEN, SUB_CLOSE)

    # 内容区: <SUB-CONTAINERS> 行尾换行之后 到 </SUB-CONTAINERS> 所在行行首之前
    inner_start = text.find("\n", sub_open) + 1
    close_line_start = text.rfind("\n", inner_start, sub_close_start) + 1
    inner = text[inner_start:close_line_start]

    # 找模板容器 (整个文件中 SHORT-NAME 精确为 DemEventParameter 的唯一容器)
    template = None
    n_containers = 0
    for start, end in iter_top_level_containers(inner):
        n_containers += 1
        block = inner[start:end]
        if TEMPLATE_SHORT_NAME in block:
            template = block

    if template is None:
        raise ValueError("未找到 SHORT-NAME 为 DemEventParameter 的模板容器")

    # DemEventId 改为 1
    id_pattern = re.compile(
        "(" + re.escape(EVENT_ID_REF_END) + r"\s*<VALUE>)\d+(</VALUE>)"
    )
    m = id_pattern.search(template)
    if m is None:
        raise ValueError("模板容器中未找到 DemEventId")
    old_id = template[m.start(1) + len(m.group(1)):m.start(2)]
    template = template[: m.start()] + m.group(1) + "1" + m.group(2) + template[m.end():]

    n_events = inner.count(">/MICROSAR/Dem/DemConfigSet/DemEventParameter</DEFINITION-REF>")
    n_dtcs = inner.count(">/MICROSAR/Dem/DemConfigSet/DemDTCClass</DEFINITION-REF>")

    new_text = text[:inner_start] + template + eol + text[close_line_start:]

    stamp = time.strftime("%Y%m%d_%H%M%S")
    # 备份不能放目标目录: DaVinci 保存工程时会清理 ECUC 目录下的非工程文件
    backup_dir = Path(__file__).resolve().parent / "backup"
    backup_dir.mkdir(exist_ok=True)
    backup = backup_dir / (target.name + ".bak_" + stamp)
    shutil.copy2(target, backup)
    target.write_bytes(new_text.encode("utf-8"))

    print("[clear_dem_arxml] 目标文件 : %s" % target)
    print("[clear_dem_arxml] 备份文件 : %s" % backup)
    print("[clear_dem_arxml] 清理统计 : 一级容器 %d 个 (DTC %d, Event %d)"
          % (n_containers, n_dtcs, n_events))
    print("[clear_dem_arxml] 保留模板 : DemEventParameter, DemEventId %s -> 1" % old_id)
    print("[clear_dem_arxml] 完成, 输出 %d 行" % new_text.count("\n"))


def main():
    if len(sys.argv) != 2:
        print("用法: python clear_dem_arxml.py <ecuc_arxml_path>", file=sys.stderr)
        sys.exit(1)
    target = Path(sys.argv[1])
    if not target.is_file():
        print("ERROR: 文件不存在: %s" % target, file=sys.stderr)
        sys.exit(1)
    clear_dtc_events(target)


if __name__ == "__main__":
    main()
