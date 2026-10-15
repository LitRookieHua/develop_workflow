import pandas as pd
import os
import re
from typing import List, Dict
from Create_DemDTCs import uds_to_decimal
import sys

class DEM_Data:
    """完全对应需求表头的结构化数据类，属性与需求表头一一对应"""

    def __init__(self):
        self.DEM_Index: List[int] = []  # 需求表头：DEM Index
        self.Net_Node: List[str] = []  # 需求表头：Net Node
        self.EventName: List[str] = []  # 需求表头：EventName
        self.DTC_hex: List[str] = []  # 需求表头：DTC(hex)
        self.DemUdsDTC: List[str] = []  # 需求表头：DemUdsDTC
        self.EventKind: List[str] = []  # 需求表头：EventKind
        self.Recoverable: List[bool] = []  # 需求表头：Recoverable
        self.DTC_Priority: List[int] = []  # 需求表头：DTC Priority
        self.ImmediateNvStorage: List[bool] = []  # 需求表头：ImmediateNvStorage
        self.DebounceAlgorithm: List[str] = []  # 需求表头：DebounceAlgorithm
        self.Debounce_Falied: List[int] = []  # 需求表头：Debounce Falied
        self.Debounce_Pass: List[int] = []  # 需求表头：Debounce Pass
        self.DecrementStepSize: List[int] = []  # 需求表头：DecrementStepSize
        self.lncrementStepSize: List[int] = []  # 需求表头：lncrementStepSize
        self.SnapshotType: List[str] = []  # 需求表头：SnapshotType
        self.Aging: List[int] = []  # 需求表头：Aging
        self.ECG: List[str] = []  # 需求表头：ECG
        self.OprationCycle: List[str] = []  # 需求表头：OprationCycle
        self.data_count: int = 0  # 数据总条数


def check_for_duplicates(event_names: List[str]):
    """
    检查 EventName 列表中是否存在重复字符串（严格区分大小写和空格）。
    这是一个“只读”操作，不会以任何方式修改原始列表。
    如果发现重复，立即抛出 ValueError 异常并停止程序。
    """
    seen_names = set()

    for name in event_names:
        if name in seen_names:
            # 发现重复，立即报错并退出（错误信息包含重复项和位置，更友好）
            duplicate_index = event_names.index(name) + 1  # 转为人可读索引（从1开始）
            raise ValueError(
                f"❌ 发现重复的 EventName：\n"
                f"  重复项：'{name}'\n"
                f"  首次出现位置：第{duplicate_index}行\n"
                f"  程序已终止。"
            )
        seen_names.add(name)

    # 如果程序能运行到这里，说明没有发现重复
    print("✅ 检查完成：所有 EventName 均唯一，未发现重复。")


def validate_event_name_format(event_names: List[str]):
    """
    检查 EventName 是否符合规则：[a-zA-Z][a-zA-Z0-9_]*
    不符合则直接打印醒目错误信息并强制终止程序 (sys.exit)
    """
    pattern = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$')

    for name in event_names:
        if not name:
            continue

        if not pattern.match(name):
            print("\033[91m" + "=" * 80)
            print(f"❌  ERROR: Shortname invalid")
            print(f"    - Invalid name: {name}")
            print(f"    - Required pattern: [a-zA-Z][a-zA-Z0-9_]*")
            print("=" * 80 + "\033[0m")
            sys.exit(1)


def parse_dem_excel(
        input_file: str,
        column_mapping: Dict[str, str] = None  # 手动指定：Excel实际列名 → 需求表头名
) -> DEM_Data:
    """
    解析Excel的DEM数据，支持手动映射列名，解决列名不匹配问题
    :param input_file: Excel文件路径
    :param column_mapping: 列名映射字典（例：{"实际列名1":"需求表头名1", "实际列名2":"需求表头名2"}）
    :return: 结构化DEM_Data对象
    """
    # 1. 基础校验：文件是否存在
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"❌ Excel文件不存在：{input_file}")

    # 2. 读取Excel，先查看实际列名（方便调试）
    try:
        df = pd.read_excel(input_file)
        actual_columns = df.columns.tolist()
    except Exception as e:
        raise RuntimeError(f"❌ 读取Excel失败（格式错误或文件损坏）：{str(e)}")

    # 3. 定义「需求表头」（补充 DEM_Index 和 Net_Node，避免列缺失报错）
    required_headers = [
        "DEM Index", "Net Node",  # 补充必要列
        "Event Name", "DTC(hex)", "DemUdsDTC",
        "Event Kind", "Recoverable", "DTC Priority",
        "ImmediateNvStorage", "DebounceAlgorithm", "Debounce Falied",
        "Debounce Pass", "DecrementStepSize", "lncrementStepSize",
        "SnapshotType", "Aging", "ECG", "OprationCycle"
    ]

    # 3.1 若用户未指定映射，默认用「需求表头」模糊匹配（不区分大小写、忽略前后空格）
    if column_mapping is None:
        normalized_actual = {col.strip().lower(): col for col in actual_columns}
        column_mapping = {}

        for req_header in required_headers:
            normalized_req = req_header.strip().lower()
            if normalized_req in normalized_actual:
                column_mapping[normalized_actual[normalized_req]] = req_header
            else:
                raise ValueError(
                    f"❌ 未找到必需列：{req_header}\n"
                    f"请核对Excel实际列名（如下），并用 column_mapping 参数指定映射：\n"
                    f"实际列名列表：{actual_columns}\n"
                    f"示例：column_mapping = {{'Excel中的事件名': 'Event Name', 'Excel中的DTC': 'DTC(hex)'}}"
                )

    # 3.2 用映射字典重命名Excel列，统一为「需求表头」
    df_renamed = df.rename(columns=column_mapping)

    # 4. 初始化数据对象并赋值（严格保持原始数据，仅去除尾部空格的副本用于查重）
    dem_data = DEM_Data()
    dem_data.data_count = len(df_renamed)

    # 赋值逻辑（处理数据类型，兼容空值，**不修改原始列表**）
    dem_data.DEM_Index = df_renamed["DEM Index"].fillna(0).astype(int).tolist()
    dem_data.Net_Node = df_renamed["Net Node"].fillna("").astype(str).tolist()
    # 关键：保留原始 EventName（不做任何修改），创建副本用于去空格和查重
    dem_data.EventName = df_renamed["Event Name"].fillna("").astype(str).tolist()
    dem_data.DTC_hex = df_renamed["DTC(hex)"].fillna("").astype(str).tolist()
    dem_data.DemUdsDTC = df_renamed["DemUdsDTC"].fillna("").astype(str).tolist()
    dem_data.EventKind = df_renamed["Event Kind"].fillna("").astype(str).tolist()
    # Recoverable：兼容TRUE/FALSE、true/false、1/0等格式
    dem_data.Recoverable = df_renamed["Recoverable"].apply(
        lambda x: str(x).strip().upper() in ["TRUE", "1"] if not pd.isna(x) else False
    ).tolist()
    dem_data.DTC_Priority = df_renamed["DTC Priority"].fillna(0).astype(int).tolist()
    # ImmediateNvStorage：同Recoverable格式处理
    dem_data.ImmediateNvStorage = df_renamed["ImmediateNvStorage"].apply(
        lambda x: str(x).strip().upper() in ["TRUE", "1"] if not pd.isna(x) else False
    ).tolist()
    dem_data.DebounceAlgorithm = df_renamed["DebounceAlgorithm"].fillna("").astype(str).tolist()
    dem_data.Debounce_Falied = df_renamed["Debounce Falied"].fillna(0).astype(int).tolist()
    dem_data.Debounce_Pass = df_renamed["Debounce Pass"].fillna(0).astype(int).tolist()
    dem_data.DecrementStepSize = df_renamed["DecrementStepSize"].fillna(0).astype(int).tolist()
    dem_data.lncrementStepSize = df_renamed["lncrementStepSize"].fillna(0).astype(int).tolist()
    dem_data.SnapshotType = df_renamed["SnapshotType"].fillna("").astype(str).tolist()
    dem_data.Aging = df_renamed["Aging"].fillna(0).astype(int).tolist()
    dem_data.ECG = df_renamed["ECG"].fillna("").astype(str).tolist()
    dem_data.OprationCycle = df_renamed["OprationCycle"].fillna("").astype(str).tolist()

    # 5. DTC 转换校验（保持原有逻辑，不修改数据）
    for i in range(dem_data.data_count):
        try:
            current_uds = dem_data.DemUdsDTC[i]
            current_target_hex = dem_data.DTC_hex[i]

            # 检查是否为N.A，是则跳过
            if current_uds.upper() == "N.A" or current_target_hex.upper() == "N.A":
                continue

            # 正常转换和校验逻辑
            dec_val = uds_to_decimal(current_uds)
            converted_hex = hex(dec_val).upper()  # 转换后十六进制（大写）
            target_hex = current_target_hex.upper()  # 预期十六进制（统一大写）

            if converted_hex != target_hex:
                print(f"❌ 第{i + 1}组 DTC 校验失败：")
                print(f"  原始UDS字符串：{current_uds}")
                print(f"  转换后十六进制：{converted_hex}")
                print(f"  预期十六进制：{target_hex}")
                sys.exit(1)  # 不匹配则退出

        except Exception as e:
            print(f"❌ 第{i + 1}组 DTC 处理出错：{str(e)}")
            sys.exit(1)

    # 6. 检查 EventName 重复（关键：用去空格后的副本查重，不修改原始数据）
    # 创建去尾部空格的副本（避免因空格导致的“假重复”，同时保留原始数据）
    event_names_for_check = [name.rstrip() for name in dem_data.EventName]
    check_for_duplicates(event_names_for_check)

    validate_event_name_format(dem_data.EventName)

    return dem_data
