"""把 CanTp 表解析结果打补丁进 J6B_CanTp_EcucValues.arxml (只改 VALUE, 保留结构/S= 属性).

容器定位: 按 SHORT-NAME (CanTpGeneral / CanTpConfig / <NSdu 容器>)。
参数定位: 容器自身 PARAMETER-VALUES 下 DEFINITION-REF 后缀 = 参数名。
PaddingActivation 为全局开关: 写所有 CanTpRxNSdu 容器的 CanTpRxPaddingActivation
与所有 CanTpTxNSdu 容器的 CanTpTxPaddingActivation。
"""

import sys
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "gen_dcm_arxml"))
from arxml_pipeline import parse_arxml, write_arxml, ns_tag  # noqa: E402

from Parse_cantp_excel import (  # noqa: E402
    COL_BS, COL_STMIN, COL_NAR, COL_NBR, COL_NCR,
    COL_NAS, COL_NBS, COL_NCS,
)

GENERAL_CONTAINER = "CanTpGeneral"
CONFIG_CONTAINER = "CanTpConfig"

# NSdu 容器类型 -> {Excel 列名: (arxml 参数名, 值类型)}
RX_COL_MAP = {
    COL_BS: ("CanTpBs", "int"),
    COL_STMIN: ("CanTpSTmin", "float"),
    COL_NAR: ("CanTpNar", "float"),
    COL_NBR: ("CanTpNbr", "float"),
    COL_NCR: ("CanTpNcr", "float"),
}
TX_COL_MAP = {
    COL_NAS: ("CanTpNas", "float"),
    COL_NBS: ("CanTpNbs", "float"),
    COL_NCS: ("CanTpNcs", "float"),
}


def _fail(msg):
    raise ValueError("CanTp 打补丁错误: %s" % msg)


def _fmt(kind, v):
    if kind == "int":
        return str(int(v))
    if kind == "float":
        v = float(v)
        if v == int(v):
            return "%.1f" % v          # 1.0 / 5.0, 对齐基线 arxml 浮点渲染
        return repr(v)                 # 0.06 / 0.01 / 0.001
    return str(v)                      # 枚举原样


def _find_containers(root, short_name):
    hits = []
    for c in root.iter(ns_tag("ECUC-CONTAINER-VALUE")):
        sn = c.find(ns_tag("SHORT-NAME"))
        if sn is not None and sn.text == short_name:
            hits.append(c)
    return hits


def _single_container(root, short_name):
    hits = _find_containers(root, short_name)
    if len(hits) == 0:
        _fail("未找到容器 SHORT-NAME=%s" % short_name)
    if len(hits) > 1:
        _fail("容器 SHORT-NAME=%s 出现 %d 个 (需唯一)" % (short_name, len(hits)))
    return hits[0]


def _container_kind(c):
    """按 DEFINITION-REF 后缀判定 NSdu 容器类型: 'rx' / 'tx' / None."""
    d = c.find(ns_tag("DEFINITION-REF"))
    if d is None or not d.text:
        return None
    if d.text.rstrip("/").endswith("/CanTpRxNSdu"):
        return "rx"
    if d.text.rstrip("/").endswith("/CanTpTxNSdu"):
        return "tx"
    return None


def _param_element(container, param_name):
    """在容器自身 PARAMETER-VALUES 下找 DEFINITION-REF 后缀=param 的参数元素."""
    pv = container.find(ns_tag("PARAMETER-VALUES"))
    if pv is None:
        return None
    hits = []
    for el in pv:
        d = el.find(ns_tag("DEFINITION-REF"))
        if d is not None and d.text and d.text.rstrip("/").endswith("/" + param_name):
            hits.append(el)
    if len(hits) > 1:
        _fail("容器 %s 下参数 %s 出现 %d 个 (需唯一)"
              % (param_name, param_name, len(hits)))
    return hits[0] if hits else None


def _set_param(container, param_name, kind, value, changes):
    el = _param_element(container, param_name)
    if el is None:
        sn = container.find(ns_tag("SHORT-NAME"))
        _fail("容器 %s 下未找到参数 %s"
              % (sn.text if sn is not None else "?", param_name))
    v = el.find(ns_tag("VALUE"))
    if v is None:
        _fail("参数 %s 无可写 VALUE 元素" % param_name)
    text = _fmt(kind, value)
    v.text = text
    sn = container.find(ns_tag("SHORT-NAME"))
    changes.append((sn.text, param_name, text))


def patch_cantp_arxml(input_arxml, output_arxml, data):
    """将解析结果写入 arxml, 返回已写值列表 [(容器, 参数, 值字符串), ...]."""
    parsed = parse_arxml(input_arxml)
    if parsed is None:
        _fail("读取输入 arxml 失败: %s" % input_arxml)
    root, raw_content, xml_decl = parsed
    changes = []

    # 1. CanTpGeneral: PaddingByte + 全局 PaddingActivation
    if data.padding_byte is not None or data.padding_activation is not None:
        gen = _single_container(root, GENERAL_CONTAINER)
        if data.padding_byte is not None:
            _set_param(gen, "CanTpPaddingByte", "int", data.padding_byte, changes)
        if data.padding_activation is not None:
            rx = [c for c in root.iter(ns_tag("ECUC-CONTAINER-VALUE"))
                  if _container_kind(c) == "rx"]
            tx = [c for c in root.iter(ns_tag("ECUC-CONTAINER-VALUE"))
                  if _container_kind(c) == "tx"]
            if not rx:
                _fail("未找到任何 CanTpRxNSdu 容器, 无法写 PaddingActivation")
            if not tx:
                _fail("未找到任何 CanTpTxNSdu 容器, 无法写 PaddingActivation")
            for c in rx:
                _set_param(c, "CanTpRxPaddingActivation", "enum",
                           data.padding_activation, changes)
            for c in tx:
                _set_param(c, "CanTpTxPaddingActivation", "enum",
                           data.padding_activation, changes)

    # 2. CanTpConfig: MainFunctionPeriod
    if data.main_function_period is not None:
        cfg = _single_container(root, CONFIG_CONTAINER)
        _set_param(cfg, "CanTpMainFunctionPeriod", "float",
                   data.main_function_period, changes)

    # 3. NSdu 行: 按容器 SHORT-NAME
    for row in data.nsdu_rows:
        c = _single_container(root, row["name"])
        kind = _container_kind(c)
        if kind is None:
            _fail("容器 %s 不是 CanTpRxNSdu/CanTpTxNSdu 容器 (DEFINITION-REF 后缀不匹配)"
                  % row["name"])
        col_map = RX_COL_MAP if kind == "rx" else TX_COL_MAP
        for col, val in row["values"].items():
            if col not in col_map:
                _fail("容器 %s (%s) 不允许填 %s 列 (合法列: %s)"
                      % (row["name"], kind, col, ", ".join(sorted(col_map))))
            param, vkind = col_map[col]
            _set_param(c, param, vkind, val, changes)

    if not changes:
        _fail("没有任何参数被写入 (表可能全空或列名不匹配)")

    if not write_arxml(etree.ElementTree(root), output_arxml, raw_content, xml_decl):
        _fail("写回 arxml 失败: %s" % output_arxml)
    return changes


def _read_param(root, container_short_name, param_name):
    hits = _find_containers(root, container_short_name)
    if len(hits) != 1:
        return None
    el = _param_element(hits[0], param_name)
    if el is None:
        return None
    v = el.find(ns_tag("VALUE"))
    return v.text if v is not None else None


def verify_cantp_arxml(output_arxml, changes):
    """重开输出 arxml, 逐条断言已写值落位."""
    parsed = parse_arxml(output_arxml)
    if parsed is None:
        _fail("校验时读取输出 arxml 失败: %s" % output_arxml)
    root = parsed[0]
    bad = []
    for container, param, expected in changes:
        actual = _read_param(root, container, param)
        if actual != expected:
            bad.append("%s/%s 期望 %r 实际 %r" % (container, param, expected, actual))
    if bad:
        _fail("写回校验失败:\n  " + "\n  ".join(bad))
    return True
