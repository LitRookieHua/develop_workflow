#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_fim_code - EVM FiMFID 配置生成脚本(合并版, 原名 gen_evm_fimfid)

由 Gen_Evm_FiMFID_Script.py 与 Gen_zx_fimcfg.py 合并而成:
  1. merge_excel_sheets 只跑一次(原两脚本各跑一遍,产物相同)
  2. FiMFID 段:读 merged Excel 的 FiMFID_* 列(Y/N),二进制去重分组,
     生成 evm_cfg_FidCfg.hpp + evm_cfg_iSysFidCfg.cpp
  3. zx 段:提取 FiMFID_ 列名,生成 zx_sys_evm_cfg_fimcfg.hpp

用法:
    python gen_fim_code.py <excel_path> <cpp_out_dir> <h_out_dir>
示例:
    python gen_fim_code.py IDC_EVM_Config_CMC_RX_V2.0_20260823.xlsx ./out_cpp ./out_h
输出:
    <cpp_out_dir>/evm_cfg_iSysFidCfg.cpp
    <h_out_dir>/evm_cfg_FidCfg.hpp
    <h_out_dir>/zx_sys_evm_cfg_fimcfg.hpp
"""

import sys
import os
import re
import datetime
import pandas as pd

from Merge_ExcelSheets import merge_excel_sheets
from TemplateFile import TemplateFile

# ---------------------- 1. 配置常量 ----------------------
MERGED_EXCEL_SUFFIX = "_merged"
TEMPLATE_DIR_NAME = "template"

# FiMFID 段(evm_cfg_FidCfg.hpp + evm_cfg_iSysFidCfg.cpp)
CPP_TPL_FILENAME = "evm_cfg_iSysFidCfg.cpp.tpl"
CPP_OUTPUT_FILENAME = "evm_cfg_iSysFidCfg.cpp"
H_TPL_FILENAME = "evm_cfg_FidCfg.hpp.tpl"
H_OUTPUT_FILENAME = "evm_cfg_FidCfg.hpp"

TARGET_SHEET_NAME = "Sheet1"          # merge_excel_sheets 输出的唯一 sheet
EVENT_NAME_COL_NAME = "Event Name"
EVENT_NAME_COL_INDEX = 1              # 事件名称列备选索引(B列)
DEM_INDEX_COL_NAME = "DEM Index"      # 用于计算 EvmCfg_Max_Number_Event_cu16

CPP_EVENT_ITEM_START = "dsmcfg_EventToMixedFidTable_item_start"
CPP_EVENT_ITEM_END = "dsmcfg_EventToMixedFidTable_item_end"
CPP_CORE_PLACEHOLDER = "EventToMixedFid_index_replace"
CPP_EVENT_TABLE_REPLACE = "dsmcfg_EventToMixedFidTable_replace_here"
CPP_GROUP_TABLE_REPLACE = "EventToMixedFidGroup_index_replace"

H_EVENT_MAX_NUM = "replace_Event_MAX_Number"
H_EVENT_ALIGNED_BIT = "replace_Event_AlignedBit"
H_GROUP_COUNT = "replace_EventToMixedFidGroupNumber"
H_FID_ALIGNED_UINT8 = "replace_FIDNumberAlignUINT8"

CPP_ARRAY_REGEX = re.compile(
    r"(const\s+zos::uint16_t\s+evmcfg_EventToMixedFidTable_tau16\s*\[\s*EvmCfg_Max_Number_Event_cu16\s*\]\s*=\s*\{)"
    r"(.*?)"
    r"(\};)",
    re.DOTALL | re.IGNORECASE
)

# zx 段(zx_sys_evm_cfg_fimcfg.hpp)
ZX_TPL_FILENAME = "zx_sys_evm_cfg_fimcfg.hpp.tpl"
ZX_OUTPUT_FILENAME = "zx_sys_evm_cfg_fimcfg.hpp"
FIDS_SIZE_PLACEHOLDER = "m_FidsSize_replace"
FIMFID_CONFIG_PLACEHOLDER = "m_FiMFID_replace"

# 两段共用
VERSION_PLACEHOLDER = "excel_version"
TIME_PLACEHOLDER = "Year-Mon-Day Hour:Minute:Second"


# ---------------------- 2. Excel 处理工具类 ----------------------
class ExcelHandler:
    def __init__(self):
        self.data: pd.DataFrame = pd.DataFrame()
        self.event_name_col_idx: int = -1
        self.fimfid_col_indices: list = []
        self.dem_index_col_idx: int = -1

    def load_excel(self, excel_path: str, sheet_name: str) -> None:
        """加载Excel并定位事件列、FiMFID列、DEM Index列"""
        try:
            self.data = pd.read_excel(
                excel_path,
                sheet_name=sheet_name,
                engine="openpyxl",
                keep_default_na=False
            )
            self._locate_event_col()
            self._locate_fimfid_cols()
            self._locate_dem_index_col()
            if self.event_name_col_idx == -1:
                raise ValueError("Excel中未找到事件名称列(EventName)")
            if not self.fimfid_col_indices:
                raise ValueError("Excel中未找到FiMFID_前缀列")
            if self.dem_index_col_idx == -1:
                raise ValueError(f"Excel中未找到{DEM_INDEX_COL_NAME}列")
            print(f"Excel加载成功：{len(self.data)}行事件，{len(self.fimfid_col_indices)}列FiMFID")
        except Exception as e:
            raise IOError(f"加载Excel失败：{str(e)}")

    def _locate_event_col(self):
        headers = self.data.columns.tolist()
        for idx, col in enumerate(headers):
            if str(col).strip().upper() == EVENT_NAME_COL_NAME.upper():
                self.event_name_col_idx = idx
                return
        if 0 <= EVENT_NAME_COL_INDEX < len(headers):
            self.event_name_col_idx = EVENT_NAME_COL_INDEX

    def _locate_fimfid_cols(self):
        headers = self.data.columns.tolist()
        self.fimfid_col_indices = [
            idx for idx, col in enumerate(headers)
            if str(col).strip().startswith("FiMFID_")
        ]

    def _locate_dem_index_col(self):
        headers = self.data.columns.tolist()
        for idx, col in enumerate(headers):
            if str(col).strip().upper() == DEM_INDEX_COL_NAME.upper():
                self.dem_index_col_idx = idx
                return

    def get_event_name(self, row_idx: int) -> str:
        if row_idx < 0 or row_idx >= len(self.data):
            return f"Unknown_Event_{row_idx + 1}"
        name = str(self.data.iloc[row_idx, self.event_name_col_idx]).strip()
        return name if name else f"Empty_Event_{row_idx + 1}"

    def get_fimfid_binary(self, row_idx: int) -> str:
        """FiMFID值→二进制串（Y=1，N=0，8位对齐）"""
        fimfid_vals = [
            str(self.data.iloc[row_idx, idx]).strip().upper()
            for idx in self.fimfid_col_indices
        ]
        binary_str = ''.join(['1' if val == 'Y' else '0' for val in fimfid_vals])
        align_len = ((len(binary_str) + 7) // 8) * 8
        return binary_str.ljust(align_len, '0')

    def get_row_count(self) -> int:
        return len(self.data) if not self.data.empty else 0

    def get_fimfid_col_count(self) -> int:
        return len(self.fimfid_col_indices)

    def get_max_dem_index(self) -> int:
        """获取DEM Index列的最大值（即最大事件编号）"""
        dem_index_values = self.data.iloc[:, self.dem_index_col_idx].apply(
            lambda x: int(str(x).strip()) if str(x).strip().isdigit() else 0
        )
        max_index = dem_index_values.max()
        print(f"DEM Index最大值：{max_index}（用于计算EvmCfg_Max_Number_Event_cu16）")
        return max_index


# ---------------------- 3. 模板处理工具类 ----------------------
class TemplateHandler:
    def __init__(self, tpl_type: str):
        self.content: str = ""
        self.tpl_type = tpl_type  # "C++" 或 "H"

    def load(self, tpl_path: str) -> None:
        if not os.path.exists(tpl_path):
            raise FileNotFoundError(f"模板文件不存在：{tpl_path}（检查路径和.tpl后缀）")
        try:
            with open(tpl_path, 'r', encoding="utf-8") as f:
                self.content = f.read()
            print(f"[{self.tpl_type}] 模板加载成功（{tpl_path}）")
        except Exception as e:
            raise IOError(f"加载{self.tpl_type}模板失败：{str(e)}")

    def replace_placeholder(self, placeholder: str, value: str) -> bool:
        if placeholder not in self.content:
            print(f"[{self.tpl_type}] 警告：未找到占位符「{placeholder}」")
            return False
        self.content = self.content.replace(placeholder, value)
        return True

    def extract_cpp_template(self, start_mark: str, end_mark: str) -> str:
        """提取C++模板中的事件项骨架（清除注释）"""
        array_match = CPP_ARRAY_REGEX.search(self.content)
        if not array_match:
            raise ValueError("C++模板中未找到事件映射数组声明")
        array_inner = array_match.group(2)

        start_pos = array_inner.find(start_mark)
        end_pos = array_inner.find(end_mark)
        if start_pos == -1 or end_pos == -1:
            raise ValueError(f"C++模板中未找到标记对：{start_mark} / {end_mark}")

        raw_content = array_inner[start_pos + len(start_mark):end_pos].strip()
        clean_content = re.sub(r"//.*?$", "", raw_content, flags=re.MULTILINE)
        clean_content = re.sub(r"\s+", " ", clean_content).strip()
        return clean_content

    def delete_cpp_marks(self, start_mark: str, end_mark: str) -> None:
        """删除C++模板中的事件项标记（仅在数组内部）"""
        array_match = CPP_ARRAY_REGEX.search(self.content)
        if not array_match:
            return
        array_prefix = array_match.group(1)
        array_inner = array_match.group(2)
        array_suffix = array_match.group(3)

        mark_pattern = re.compile(
            re.escape(start_mark) + r".*?" + re.escape(end_mark),
            re.DOTALL | re.IGNORECASE
        )
        new_inner = mark_pattern.sub("", array_inner)
        self.content = self.content.replace(
            array_prefix + array_inner + array_suffix,
            array_prefix + new_inner + array_suffix
        )
        print(f"[{self.tpl_type}] 模板标记删除成功：{start_mark} / {end_mark}")

    def save(self, output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        try:
            with open(output_path, 'w', encoding="utf-8") as f:
                f.write(self.content)
            print(f"[{self.tpl_type}] 输出文件保存成功：{output_path}")
        except Exception as e:
            raise IOError(f"保存{self.tpl_type}文件失败：{str(e)}")


# ---------------------- 4. 工具函数 ----------------------
def binary_to_hex(bin_str: str) -> list:
    """二进制字符串→十六进制列表（每8位对应一个UINT8）"""
    if len(bin_str) % 8 != 0:
        raise ValueError(f"二进制字符串长度必须是8的倍数（当前：{len(bin_str)}）")
    return [hex(int(bin_str[i:i+8], 2)) for i in range(0, len(bin_str), 8)]


def extract_fimfid_names_from_excel(excel_path: str) -> list:
    """从 merged Excel 中提取FiMFID列名（去除FiMFID_前缀）"""
    try:
        df = pd.read_excel(excel_path, engine="openpyxl")
        fimfid_names = []
        for col in df.columns:
            col_str = str(col).strip()
            if col_str.startswith("FiMFID_"):
                fid_name = col_str[len("FiMFID_"):].strip()
                if fid_name:
                    fimfid_names.append(fid_name)

        if not fimfid_names:
            raise ValueError("Excel中未找到FiMFID_前缀的列！")
        print(f"✅ 提取到FiMFID列名：共{len(fimfid_names)}个")
        return fimfid_names
    except Exception as e:
        raise RuntimeError(f"提取FiMFID列名失败：{str(e)}")


def generate_fimfid_members(fimfid_names: list) -> str:
    """生成结构体成员字符串：zos::uint8_t m_FiMFID_XXX;    /// 索引"""
    members = []
    for idx, fid_name in enumerate(fimfid_names):
        member_line = f"    zos::uint8_t m_FiMFID_{fid_name};    /// {idx}"
        members.append(member_line)
    return "\n".join(members)


def derive_excel_version(excel_path: str) -> str:
    """从 Excel 文件名推导版本号（匹配 V1.4 / V0.6 等），推导失败回退 'V1.0'"""
    base = os.path.basename(excel_path)
    m = re.search(r'(V\d+\.\d+(?:\.\d+)?)', base, re.IGNORECASE)
    return m.group(1) if m else "V1.0"


# ---------------------- 5. FiMFID 段 ----------------------
def generate_fimfid_config(
    excel_path: str,
    tpl_root: str,
    cpp_out_dir: str,
    h_out_dir: str,
    excel_version: str
) -> None:
    """生成H宏定义+C++数组（EvmCfg_Max_Number_Event_cu16基于DEM Index最大值）"""
    excel = ExcelHandler()
    excel.load_excel(excel_path, TARGET_SHEET_NAME)
    event_count = excel.get_row_count()
    fimfid_col_count = excel.get_fimfid_col_count()
    max_dem_index = excel.get_max_dem_index()

    event_bin_list = [excel.get_fimfid_binary(row) for row in range(event_count)]
    unique_bins = sorted(list(set(event_bin_list)))
    group_count = len(unique_bins)
    print(f"\n事件分组结果：{event_count}个事件 → {group_count}个唯一分组")

    print("\n" + "-"*50 + " 处理H模板 " + "-"*50)
    h_tpl = TemplateHandler("H")
    h_tpl.load(os.path.join(tpl_root, H_TPL_FILENAME))
    h_macros = {
        H_EVENT_MAX_NUM: str(max_dem_index),
        H_EVENT_ALIGNED_BIT: str((event_count + 7) // 8),
        H_GROUP_COUNT: str(group_count),
        H_FID_ALIGNED_UINT8: str((fimfid_col_count + 7) // 8)
    }
    for placeholder, value in h_macros.items():
        h_tpl.replace_placeholder(placeholder, value)
    h_tpl.save(os.path.join(h_out_dir, H_OUTPUT_FILENAME))

    print("\n" + "-"*50 + " 处理C++模板 " + "-"*50)
    cpp_tpl = TemplateHandler("C++")
    cpp_tpl.load(os.path.join(tpl_root, CPP_TPL_FILENAME))

    cpp_item_tpl = cpp_tpl.extract_cpp_template(CPP_EVENT_ITEM_START, CPP_EVENT_ITEM_END)
    if CPP_CORE_PLACEHOLDER not in cpp_item_tpl:
        raise ValueError(f"C++模板骨架中未找到核心占位符：{CPP_CORE_PLACEHOLDER}")
    print(f"[C++] 提取的模板骨架：{cpp_item_tpl}")

    event_array_items = []
    for row_idx in range(event_count):
        bin_str = event_bin_list[row_idx]
        group_idx = unique_bins.index(bin_str)
        event_item = cpp_item_tpl.replace(CPP_CORE_PLACEHOLDER, str(group_idx))
        event_name = excel.get_event_name(row_idx)
        if row_idx < event_count - 1:
            event_item = f"{event_item}  // {row_idx + 1}--{event_name}"
        else:
            event_item = f"{event_item.rstrip(',')}  // {row_idx + 1}--{event_name}"
        event_array_items.append(event_item)
    event_array_content = "\n        ".join(event_array_items)

    group_array_items = []
    total_groups = len(unique_bins)
    for group_idx, bin_str in enumerate(unique_bins):
        hex_list = binary_to_hex(bin_str)
        hex_str = ", ".join(hex_list)
        if group_idx < total_groups - 1:
            group_item = f"    /* Group{group_idx} */ {{ {hex_str} }},"
        else:
            group_item = f"    /* Group{group_idx} */ {{ {hex_str} }}"
        group_array_items.append(group_item)
    group_array_content = "\n        ".join(group_array_items)

    cpp_tpl.replace_placeholder(CPP_EVENT_TABLE_REPLACE, event_array_content)
    cpp_tpl.replace_placeholder(CPP_GROUP_TABLE_REPLACE, group_array_content)
    cpp_tpl.replace_placeholder(VERSION_PLACEHOLDER, excel_version)
    cpp_tpl.replace_placeholder(TIME_PLACEHOLDER, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    cpp_tpl.delete_cpp_marks(CPP_EVENT_ITEM_START, CPP_EVENT_ITEM_END)
    cpp_tpl.save(os.path.join(cpp_out_dir, CPP_OUTPUT_FILENAME))

    print(f"FiMFID段完成：事件{event_count}个，分组{group_count}个，最大DEM Index {max_dem_index}")


# ---------------------- 6. zx 段 ----------------------
def generate_zx_config(
    merged_excel: str,
    tpl_root: str,
    h_out_dir: str,
    excel_version: str
) -> None:
    """生成 zx_sys_evm_cfg_fimcfg.hpp（FIDs数量 + 结构体成员）"""
    fimfid_names = extract_fimfid_names_from_excel(merged_excel)
    fids_count = len(fimfid_names)
    print(f"✅ FiMFID总数：{fids_count}")

    fids_size_value = f"{fids_count}u"
    fimfid_members = generate_fimfid_members(fimfid_names)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    tpl_path = os.path.join(tpl_root, ZX_TPL_FILENAME)
    tpl_handler = TemplateFile()
    if not tpl_handler.read_text(tpl_path):
        raise RuntimeError(f"加载模板文件失败：{tpl_path}")
    tpl_handler.replace_all(FIDS_SIZE_PLACEHOLDER, fids_size_value)
    tpl_handler.replace_all(FIMFID_CONFIG_PLACEHOLDER, fimfid_members)
    tpl_handler.replace_all(VERSION_PLACEHOLDER, excel_version)
    tpl_handler.replace_all(TIME_PLACEHOLDER, current_time)

    output_path = os.path.join(h_out_dir, ZX_OUTPUT_FILENAME)
    if not tpl_handler.save_to_file(output_path):
        raise RuntimeError(f"保存输出文件失败：{output_path}")
    print(f"zx段完成：{output_path}（FiMFID总数={fids_count}）")


# ---------------------- 7. 入口 ----------------------
def main():
    if len(sys.argv) != 4:
        print(f"用法错误！正确格式：")
        print(f"python {sys.argv[0]} <excel_path> <cpp_out_dir> <h_out_dir>")
        print(f"示例：")
        print(f"python {sys.argv[0]} IDC_EVM_Config_CMC_RX_V2.0_20260823.xlsx ./out_cpp ./out_h")
        sys.exit(1)

    excel_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel 文件不存在: {excel_path}")
    cpp_out_dir = os.path.abspath(sys.argv[2])
    h_out_dir = os.path.abspath(sys.argv[3])
    excel_version = derive_excel_version(excel_path)

    script_root = os.path.dirname(os.path.abspath(__file__))
    tpl_root = os.path.join(script_root, TEMPLATE_DIR_NAME)
    if not os.path.exists(tpl_root):
        raise FileNotFoundError(
            f"模板文件夹不存在：{tpl_root}（需包含{CPP_TPL_FILENAME}、{H_TPL_FILENAME}和{ZX_TPL_FILENAME}）")

    try:
        print("=== 阶段1：合并 Excel（只跑一次） ===")
        merged_excel = merge_excel_sheets(excel_path)

        print("\n=== 阶段2：生成 FiMFID 配置（evm_cfg_FidCfg.hpp + evm_cfg_iSysFidCfg.cpp） ===")
        generate_fimfid_config(merged_excel, tpl_root, cpp_out_dir, h_out_dir, excel_version)

        print("\n=== 阶段3：生成 zx fimcfg（zx_sys_evm_cfg_fimcfg.hpp） ===")
        generate_zx_config(merged_excel, tpl_root, h_out_dir, excel_version)

        print("\n=== 所有流程执行成功！===")
        print(f"1. FiMFID cpp：{os.path.join(cpp_out_dir, CPP_OUTPUT_FILENAME)}")
        print(f"2. FiMFID h  ：{os.path.join(h_out_dir, H_OUTPUT_FILENAME)}")
        print(f"3. zx fim   ：{os.path.join(h_out_dir, ZX_OUTPUT_FILENAME)}")

    except Exception as e:
        print(f"\n=== 执行失败：{str(e)} ===")
        sys.exit(1)


if __name__ == "__main__":
    main()
