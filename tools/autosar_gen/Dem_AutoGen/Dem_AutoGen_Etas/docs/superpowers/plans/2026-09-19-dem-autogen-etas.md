# Dem_AutoGen_Etas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 一键工具 dem_autogen_etas:输入 IDC_EVM_Config Excel,生成 Dem arxml / Dem Ctrl C / evm_cfg 三处配置,并自动调 ISOLAR-B 生成 BSW 代码(headless 为主,Cobra.exe 降级)。

**Architecture:** 同 Dem_AutoGen_Davinci 的编排架构——一个主脚本 subprocess 调三个子目录脚本(从 mcu_app_j6/tools/e2e_dem_Script 拷贝改名,零逻辑改动),BSW 生成逻辑从 etas-integration skill 的 bsw_gen.ps1 移植成纯 python。路径全部由 `--repo + --project` glob 推导(实测 31/31 车型同构)。

**Tech Stack:** Python 3(依赖 pandas/openpyxl/lxml,运行环境已有)、subprocess、ISOLAR-B.cmd、Cobra.exe。

**Spec:** `docs/superpowers/specs/2026-09-19-dem-autogen-etas-design.md`

**工作目录:** `D:\Workspace\01_Projects\02_Src\10_tools\Dem_AutoGen_Etas`(git 仓库已初始化,master 分支)

**源目录:** `D:\Workspace\01_Projects\02_Src\02_Workspace_J6\src\mcu_app_j6\tools\e2e_dem_Script`(下文简称 `$SRC`,git-bash 路径 `/d/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/tools/e2e_dem_Script`)

---

### Task 1: 拷贝三个子目录并重命名

**Files:**
- Create: `gen_dem_arxml/`(9 个 .py,原样)
- Create: `gen_event_ctrl/`(2 个 .py + `template/Dem_PrjSpecificControl.tpl`,原样)
- Create: `gen_evm_fimfid/`(Merge_ExcelSheets.py、TemplateFile.py、ReadMe.txt、template/ 下 3 个 .tpl;排除 2 个被合并取代的 .py 和 4 个旧 .bat)

- [ ] **Step 1: 拷贝并清理**

```bash
cd /d/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Etas
SRC=/d/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/tools/e2e_dem_Script
cp -r "$SRC/Gen_Dem_Arxml_Script" gen_dem_arxml
cp -r "$SRC/Gen_Event_Available_Control_Script" gen_event_ctrl
cp -r "$SRC/Gen_Evm_FiMFID_Script" gen_evm_fimfid
rm gen_dem_arxml/Dem_arxml_Script.bat
rm gen_event_ctrl/Gen_EventAvailable_Control_Script.bat
rm gen_evm_fimfid/Gen_Evm_FiMFID_Script.py gen_evm_fimfid/Gen_Evm_FiMFID_Script.bat
rm gen_evm_fimfid/Gen_zx_fimcfg.py gen_evm_fimfid/Gen_zx_fimcfg.bat
find . -name __pycache__ -type d -not -path "./.git/*" -exec rm -rf {} +
```

排除理由:4 个旧 .bat 是被 dem_autogen_etas.py 取代的旧入口;`Gen_Evm_FiMFID_Script.py`/`Gen_zx_fimcfg.py` 被 Task 2 的合并脚本取代(spec §2)。

- [ ] **Step 2: 验证文件清单**

```bash
find . -type f -not -path "./.git/*" -not -path "./docs/*" | sort
```

Expected(14 个文件 + .gitignore):

```
./.gitignore
./gen_dem_arxml/Create_DemDebounceCounterBasedClass.py
./gen_dem_arxml/Create_DemDebounceTimeBaseClass.py
./gen_dem_arxml/Create_DemDTCAttributes.py
./gen_dem_arxml/Create_DemDTCs.py
./gen_dem_arxml/Create_DemEventParameter.py
./gen_dem_arxml/Delete_DemConfigSet.py
./gen_dem_arxml/Dem_arxml_Script.py
./gen_dem_arxml/Merge_ExcelSheets.py
./gen_dem_arxml/Parse_excel_list.py
./gen_event_ctrl/Excel_Event_Merge_Process.py
./gen_event_ctrl/Gen_EventAvailable_Control_Script.py
./gen_event_ctrl/template/Dem_PrjSpecificControl.tpl
./gen_evm_fimfid/Merge_ExcelSheets.py
./gen_evm_fimfid/ReadMe.txt
./gen_evm_fimfid/TemplateFile.py
./gen_evm_fimfid/template/evm_cfg_FidCfg.hpp.tpl
./gen_evm_fimfid/template/evm_cfg_iSysFidCfg.cpp.tpl
./gen_evm_fimfid/template/zx_sys_evm_cfg_fimcfg.hpp.tpl
```

- [ ] **Step 3: 编译检查(拷贝未改内容,应全部通过)**

```bash
py -3 -m py_compile gen_dem_arxml/*.py gen_event_ctrl/*.py gen_evm_fimfid/*.py
```

Expected: 无输出,exit 0。

- [ ] **Step 4: Commit**

```bash
git add gen_dem_arxml gen_event_ctrl gen_evm_fimfid
git commit -m "feat: copy e2e_dem_Script subdirs (renamed to snake_case)

Excludes old .bat entries and the two scripts merged into gen_evm_fimfid.py."
```

---

### Task 2: 写 gen_evm_fimfid.py(两脚本合一)

**Files:**
- Create: `gen_evm_fimfid/gen_evm_fimfid.py`

由 `Gen_Evm_FiMFID_Script.py`(FiMFID 段)与 `Gen_zx_fimcfg.py`(zx 段)合并:merge_excel_sheets 只跑一次,两个生成段共用 merged 文件;丢弃 `filter_excel_columns()` 死代码调用。类与函数体从两个原脚本逐字拷贝,仅作:统一 import、常量归并、`generate_zx_config` 从 Gen_zx_fimcfg.py 的 main 中抽出。

- [ ] **Step 1: 写入完整文件**

创建 `gen_evm_fimfid/gen_evm_fimfid.py`,内容如下(整文件):

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_evm_fimfid - EVM FiMFID 配置生成脚本(合并版)

由 Gen_Evm_FiMFID_Script.py 与 Gen_zx_fimcfg.py 合并而成:
  1. merge_excel_sheets 只跑一次(原两脚本各跑一遍,产物相同)
  2. FiMFID 段:读 merged Excel 的 FiMFID_* 列(Y/N),二进制去重分组,
     生成 evm_cfg_FidCfg.hpp + evm_cfg_iSysFidCfg.cpp
  3. zx 段:提取 FiMFID_ 列名,生成 zx_sys_evm_cfg_fimcfg.hpp

用法:
    python gen_evm_fimfid.py <excel_path> <cpp_out_dir> <h_out_dir>
示例:
    python gen_evm_fimfid.py IDC_EVM_Config_CMC_RX_V2.0_20260823.xlsx ./out_cpp ./out_h
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
```

- [ ] **Step 2: 编译检查**

```bash
cd /d/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Etas
py -3 -m py_compile gen_evm_fimfid/gen_evm_fimfid.py
```

Expected: 无输出,exit 0。

- [ ] **Step 3: 真实 Excel 冒烟(输出到临时目录,不动仓库)**

```bash
cd /d/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Etas/gen_evm_fimfid
py -3 gen_evm_fimfid.py \
  "/d/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/tools/rx/e2e_dem/IDC_EVM_Config_CMC_RX_V2.0_20260823.xlsx" \
  ./_smoke_cpp ./_smoke_h
```

Expected: 退出码 0;末尾打印 3 个输出文件;`_smoke_cpp/evm_cfg_iSysFidCfg.cpp`、`_smoke_h/evm_cfg_FidCfg.hpp`、`_smoke_h/zx_sys_evm_cfg_fimcfg.hpp` 三个文件存在。

注意:此运行会在 Excel 旁边重写 `IDC_EVM_Config_CMC_RX_V2.0_20260823_merged.xlsx`(与旧 bat 流程行为一致,内容为重新生成的等价文件)。

- [ ] **Step 4: 与仓库现有生成文件 diff(忽略时间戳行)**

```bash
REPO=/d/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc
cd /d/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Etas/gen_evm_fimfid
for pair in "_smoke_cpp/evm_cfg_iSysFidCfg.cpp:$REPO/evm_cfg/var/src/vehicle/rx/_gen/evm_cfg_iSysFidCfg.cpp" \
            "_smoke_h/evm_cfg_FidCfg.hpp:$REPO/evm_cfg/var/inc/vehicle/rx/evm_cfg/evm_cfg_FidCfg.hpp" \
            "_smoke_h/zx_sys_evm_cfg_fimcfg.hpp:$REPO/evm_cfg/var/inc/vehicle/rx/evm_cfg/zx_sys_evm_cfg_fimcfg.hpp"; do
  new="${pair%%:*}"; old="${pair#*:}"
  echo "=== diff $new vs $old ==="
  diff <(grep -v -E "20[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}" "$new") \
       <(grep -v -E "20[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}" "$old") && echo "(一致,仅时间戳不同)"
done
```

Expected: 每对输出 `(一致,仅时间戳不同)`。若有实质差异,停下排查(仓库文件可能对应旧版 Excel 或被手改过),不要继续。

- [ ] **Step 5: 清理冒烟产物并提交**

```bash
rm -rf _smoke_cpp _smoke_h
cd /d/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Etas
git add gen_evm_fimfid/gen_evm_fimfid.py
git commit -m "feat: add gen_evm_fimfid.py merging the two FiMFID scripts"
```

---

### Task 3: 写 dem_autogen_etas.py 主编排

**Files:**
- Create: `dem_autogen_etas.py`

编排 4 步;路径推导 glob 规则见 spec §3;BSW 生成 headless 默认 + Cobra.exe 降级(判定逻辑移植 bsw_gen.ps1)。

- [ ] **Step 1: 写入完整文件**

创建 `dem_autogen_etas.py`,内容如下(整文件):

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dem_autogen_etas - ETAS Dem 自动生成工具 (一键流程).

流程:
  Step 1/4  生成 Dem ARXML   (gen_dem_arxml/Dem_arxml_Script.py)
  Step 2/4  生成 Dem Ctrl C  (gen_event_ctrl/Gen_EventAvailable_Control_Script.py)
  Step 3/4  生成 EVM FiMFID  (gen_evm_fimfid/gen_evm_fimfid.py, 一次生成 3 个文件)
  Step 4/4  生成 BSW 代码    (ISOLAR-B headless 默认; 失败降级 Cobra.exe)

用法:
  python dem_autogen_etas.py <IDC_EVM_Config*.xlsx> --repo <mcu_app_j6路径> --project rx
  python dem_autogen_etas.py <excel> --repo <mcu_app_j6路径> --project rx --skip-gen
        # --skip-gen: 只跑三个生成脚本, 不执行 BSW 代码生成
"""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

GEN_TOOLS = Path(__file__).resolve().parent

DEM_ARXML_SCRIPT = GEN_TOOLS / "gen_dem_arxml" / "Dem_arxml_Script.py"
EVENT_CTRL_SCRIPT = GEN_TOOLS / "gen_event_ctrl" / "Gen_EventAvailable_Control_Script.py"
FIMFID_SCRIPT = GEN_TOOLS / "gen_evm_fimfid" / "gen_evm_fimfid.py"

RTA_CAR_HOME_DEFAULT = Path(r"D:/ETAS/RTA-CAR_12.7.0")
BSW_TIMEOUT_S = 1200   # headless 上限 20 分钟 (rx 实测 ~10.5 分钟)
BSW_POLL_S = 15
ERRORS_RE = re.compile(r"Errors:\s*(\d+)\s*,\s*Warnings:\s*(\d+)")
LICENSE_FAIL_RE = re.compile(
    r"Please set COBRA_LIC_PATH|license file|No valid license", re.IGNORECASE)


def fail(msg):
    print("[dem_autogen_etas] ERROR: %s" % msg)
    sys.exit(1)


def resolve_repo_paths(repo: Path, project: str):
    """由 --repo + --project 推导所有目标路径 (glob, 无硬编码; 31 车型实测同构)."""
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
    )


def find_isolar_b(root: Path):
    """在 RTA-CAR 安装目录下找 ISOLAR-B.cmd 所在目录 (移植 bsw_gen.ps1 Find-IsolarB).

    root 可以是 RTA-CAR 根 / RTA-OS_* 目录 / ISOLAR-AB_* 目录本身.
    """
    if not root.is_dir():
        return None
    if (root / "ISOLAR-B.cmd").is_file():
        return root
    cands = sorted((d for d in root.iterdir() if d.is_dir()
                    and (re.match(r"^ISOLAR-AB_\d", d.name) or re.match(r"^RTA-OS_", d.name))),
                   key=lambda d: d.name, reverse=True)
    for c in cands:
        if (c / "ISOLAR-B.cmd").is_file():
            return c
        for s in sorted((d for d in c.iterdir() if d.is_dir()
                        and re.match(r"^ISOLAR-AB_\d", d.name)),
                        key=lambda d: d.name, reverse=True):
            if (s / "ISOLAR-B.cmd").is_file():
                return s
    # 兜底: 深度 <=3 递归扫描
    for pat in ("*/ISOLAR-B.cmd", "*/*/ISOLAR-B.cmd", "*/*/*/ISOLAR-B.cmd"):
        hits = sorted(root.glob(pat), reverse=True)
        if hits:
            return hits[0].parent
    return None


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


def gen_bsw_headless(paths, isolar_cmd: Path):
    """ISOLAR-B headless: -generate -p=<BswRta> -t=BSW. 等进程自然退出, 超时杀进程树."""
    print("[dem_autogen_etas] ==> Step 4/4 生成 BSW 代码 (ISOLAR-B headless)")
    t0 = time.time()
    out_path = paths.bswrta / "_log" / "dem_autogen_etas.headless.out"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(isolar_cmd), "-generate", "-p=%s" % paths.bswrta, "-t=BSW"]
    with open(out_path, "w", encoding="utf-8", errors="replace") as out:
        proc = subprocess.Popen(cmd, cwd=str(isolar_cmd.parent),
                                 stdout=out, stderr=subprocess.STDOUT)
        deadline = time.time() + BSW_TIMEOUT_S
        while proc.poll() is None and time.time() < deadline:
            time.sleep(BSW_POLL_S)
        if proc.poll() is None:
            print("[dem_autogen_etas]     超过 %ds 未完成, 终止 ISOLAR 进程树" % BSW_TIMEOUT_S)
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True)
            proc.wait()
            return False
    # 子进程退出后文件系统落盘缓冲
    time.sleep(10)
    errs = parse_confgen_errors(paths.confgen_log)
    print("[dem_autogen_etas]     ISOLAR-B exit code: %s, ConfGen: %s (%.0fs)"
          % (proc.returncode, errs, time.time() - t0))
    return (proc.returncode == 0
            and confgen_log_fresh(paths.confgen_log, t0)
            and errs is not None and errs[0] == 0)


def gen_bsw_cobra(paths, isolar_dir: Path):
    """Cobra.exe 降级: 与 ISOLAR GUI 'Generate BSW Code' 1:1 (ConfGen+BSWGen+hooks)."""
    print("[dem_autogen_etas] ==> Step 4/4 生成 BSW 代码 (Cobra.exe 降级)")
    t0 = time.time()
    cmd = [str(paths.cobra), "--ProjectPath=.",
           "--isolarPath=%s" % isolar_dir, "--isolarARRoot=RTA_BIP"]
    proc = subprocess.run(cmd, cwd=str(paths.bswrta), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
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
    return (proc.returncode == 0
            and confgen_log_fresh(paths.confgen_log, t0)
            and errs is not None and errs[0] == 0)


def main():
    parser = argparse.ArgumentParser(description="ETAS Dem auto generation tool")
    parser.add_argument("excel", help="IDC_EVM_Config*.xlsx 路径")
    parser.add_argument("--repo", required=True, help="mcu_app_j6 仓库根目录")
    parser.add_argument("--project", required=True, help="车型短名 (如 rx)")
    parser.add_argument("--skip-gen", action="store_true",
                        help="只跑三个生成脚本, 不执行 BSW 代码生成")
    args = parser.parse_args()

    excel = Path(args.excel).resolve()
    repo = Path(args.repo).resolve()
    if not excel.is_file():
        fail("Excel 不存在: %s" % excel)
    for f in (DEM_ARXML_SCRIPT, EVENT_CTRL_SCRIPT, FIMFID_SCRIPT):
        if not f.is_file():
            fail("脚本不存在: %s" % f)

    paths = resolve_repo_paths(repo, args.project)
    if not paths.arxml.is_file():
        fail("Dem arxml 不存在: %s" % paths.arxml)
    if not paths.dem_ctrl_out.is_dir():
        fail("Dem Ctrl 输出目录不存在: %s" % paths.dem_ctrl_out)
    paths.fimfid_cpp_out.mkdir(parents=True, exist_ok=True)
    paths.fimfid_h_out.mkdir(parents=True, exist_ok=True)

    rta_home = Path(os.environ.get("RTA_CAR_HOME", str(RTA_CAR_HOME_DEFAULT)))
    isolar_dir = find_isolar_b(rta_home)
    if isolar_dir is None:
        fail("ISOLAR-B.cmd 未找到 (RTA_CAR_HOME=%s)" % rta_home)

    print("[dem_autogen_etas] Excel     : %s" % excel)
    print("[dem_autogen_etas] MCU 仓库  : %s" % repo)
    print("[dem_autogen_etas] 车型      : %s" % args.project)
    print("[dem_autogen_etas] BswRta    : %s" % paths.bswrta)
    print("[dem_autogen_etas] 目标 arxml: %s" % paths.arxml)
    print("[dem_autogen_etas] ISOLAR-B  : %s" % (isolar_dir / "ISOLAR-B.cmd"))

    run_step("Step 1/4 生成 Dem ARXML",
             [sys.executable, str(DEM_ARXML_SCRIPT), str(excel), str(paths.arxml)],
             cwd=DEM_ARXML_SCRIPT.parent)
    run_step("Step 2/4 生成 Dem Ctrl C (Dem_PrjSpecificControl.c)",
             [sys.executable, str(EVENT_CTRL_SCRIPT), str(excel), str(paths.dem_ctrl_out)],
             cwd=EVENT_CTRL_SCRIPT.parent)
    run_step("Step 3/4 生成 EVM FiMFID (3 个文件)",
             [sys.executable, str(FIMFID_SCRIPT), str(excel),
              str(paths.fimfid_cpp_out), str(paths.fimfid_h_out)],
             cwd=FIMFID_SCRIPT.parent)

    if args.skip_gen:
        print("[dem_autogen_etas] --skip-gen: 跳过 BSW 代码生成")
    else:
        ok = gen_bsw_headless(paths, isolar_dir / "ISOLAR-B.cmd")
        if not ok:
            print("[dem_autogen_etas] headless 失败, 降级 Cobra.exe ...")
            ok = gen_bsw_cobra(paths, isolar_dir)
        if not ok:
            fail("BSW 生成失败, 详见 %s 及 %s 目录下日志"
                 % (paths.confgen_log, paths.bswrta / "_log"))

    print("[dem_autogen_etas] 全部完成")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 编译检查**

```bash
cd /d/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Etas
py -3 -m py_compile dem_autogen_etas.py
```

Expected: 无输出,exit 0。

- [ ] **Step 3: --help 与缺参报错**

```bash
cd /d/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Etas
py -3 dem_autogen_etas.py --help
py -3 dem_autogen_etas.py foo.xlsx; echo "exit=$?"
```

Expected: `--help` 打印 usage(--repo/--project 必填);缺 `--repo`/`--project` 时 argparse 报 "the following arguments are required" 且 `exit=2`。

- [ ] **Step 4: 路径推导只读检查(不写任何文件)**

```bash
cd /d/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Etas
py -3 -c "
from pathlib import Path
import dem_autogen_etas as t
repo = Path(r'D:\Workspace\01_Projects\02_Src\02_Workspace_J6\src\mcu_app_j6')
p = t.resolve_repo_paths(repo, 'rx')
print('arxml :', p.arxml, p.arxml.is_file())
print('ctrl  :', p.dem_ctrl_out, p.dem_ctrl_out.is_dir())
print('cpp   :', p.fimfid_cpp_out, p.fimfid_cpp_out.is_dir())
print('h     :', p.fimfid_h_out, p.fimfid_h_out.is_dir())
print('cobra :', p.cobra, p.cobra.is_file())
print('isolar:', t.find_isolar_b(Path(r'D:\Etas\RTA-CAR_12.7.0')))
t.resolve_repo_paths(repo, 'no_such_project'); print('未报错=BUG')
"
```

Expected(注意大小写,find_isolar_b 用 `D:\Etas` 试真实盘符;若实际安装在别处,换成实际路径):

```
arxml : D:\...\cpj_cmc\autosar\rx\BswRta\ecu_config\bsw\gen\J6B_Dem_EcucValues.arxml True
ctrl  : D:\...\BswRta\integration\src\bsw\Dem\user True
cpp   : D:\...\cpj_cmc\evm_cfg\var\src\vehicle\rx\_gen True
h     : D:\...\cpj_cmc\evm_cfg\var\inc\vehicle\rx\evm_cfg True
cobra : D:\...\BswRta\ecu_config\cobra\Cobra.exe True
isolar: D:\ETAS\RTA-CAR_12.7.0\RTA-OS_12.7.0\ISOLAR-AB_12.7.0   (或 None)
[dem_autogen_etas] ERROR: cpj_*/autosar/no_such_project/BswRta 匹配 0 个 (需恰好 1): []
```

最后一行:未走到的 `print('未报错=BUG')` 不应出现(resolve_repo_paths 先 SystemExit)。若 `isolar` 为 None,先确认 RTA-CAR 真实安装路径再重试,不要跳过。

- [ ] **Step 5: Commit**

```bash
git add dem_autogen_etas.py
git commit -m "feat: add dem_autogen_etas orchestrator with headless/Cobra BSW generation"
```

---

### Task 4: 收尾检查

**Files:** 无新文件(只检查与清理)。

- [ ] **Step 1: 全量编译检查**

```bash
cd /d/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Etas
py -3 -m py_compile dem_autogen_etas.py gen_dem_arxml/*.py gen_event_ctrl/*.py gen_evm_fimfid/*.py
```

Expected: 无输出,exit 0。

- [ ] **Step 2: 工作区干净**

```bash
git status --short
```

Expected: 无未提交文件(冒烟产物已在 Task 2 Step 5 删除;若 `__pycache__` 出现在 status 里,确认 .gitignore 已覆盖)。

- [ ] **Step 3: 提交计划文档**

```bash
git add docs/superpowers/plans/2026-09-19-dem-autogen-etas.md
git commit -m "docs: add dem_autogen_etas implementation plan"
```

- [ ] **Step 4: 用户端到端验证(不自动执行)**

以下由用户在真实环境运行(spec §7 第 4 条),实现者不做:

```bash
# 半程验证(会写仓库文件: arxml/Dem Ctrl C/evm_cfg, 不跑 BSW 生成):
py -3 dem_autogen_etas.py \
  "D:\Workspace\01_Projects\02_Src\02_Workspace_J6\src\mcu_app_j6\cpj_cmc\tools\rx\e2e_dem\IDC_EVM_Config_CMC_RX_V2.0_20260823.xlsx" \
  --repo "D:\Workspace\01_Projects\02_Src\02_Workspace_J6\src\mcu_app_j6" --project rx --skip-gen

# 完整流程(含 BSW 生成, headless ~10 分钟):
py -3 dem_autogen_etas.py <excel> --repo <mcu_app_j6> --project rx
```

---

## Self-Review 结果

1. **Spec 覆盖**:§1 CLI(Task 3)、§2 目录拷贝与排除(Task 1/2)、§3 路径推导(Task 3 Step 1/4)、§4 四步流程(Task 3)、§5 FiMFID 合并(Task 2)、§6 BSW 生成与降级(Task 3)、§7 验证(Task 1-4 各步 + 用户端到端)、§8 不做的事(无对应任务,确认未越界)——全覆盖。
2. **占位符扫描**:无 TBD/TODO;所有代码步骤含完整代码。
3. **类型/命名一致性**:`gen_evm_fimfid.py` 的 CLI(3 参数)与 Task 3 调用一致;`resolve_repo_paths`/`find_isolar_b`/`parse_confgen_errors` 在 Task 3 Step 4 检查中引用的名字与定义一致。

---

## 执行后记(2026-09-19,Task 3 code review 修正)

计划中 Task 3 的代码块在 review 后有以下偏离(commit `fd9149f` + `12c0ca2`),以实际代码为准:

1. **BSW 成功判定反转默认值(关键)**:真实 ETAS ConfGen 日志不含 `Errors: N, Warnings: M` 汇总行(实测 16 份),原代码 `errs is not None and errs[0] == 0` 会把所有成功运行误判为失败。改为:exit code 0 + 日志新鲜时,汇总行缺失按 0 错误处理;另加 `OUTPUT_FAIL_RE`(`\[ERROR\]|^\s*Error:|Execution failed`)扫描工具输出,命中即失败。
2. **`--skip-gen` 不再解析 ISOLAR-B**:ISOLAR 解析与横幅打印移入非 skip-gen 分支,无 ISOLAR 的机器可正常跑半程。
3. **Step 1 mtime 兜底**:`Dem_arxml_Script.py` 的 `insert_*` 失败时静默 exit 0,编排器以 arxml mtime(留 1s 容差)检测"本次未写入"。
4. **健壮性**:Cobra.exe 缺失时干净报错返回 False(替代裸 FileNotFoundError);headless taskkill 后 `proc.wait(timeout=60)`;Cobra 降级加 `timeout=BSW_TIMEOUT_S`;license 正则裁剪为 `Please set COBRA_LIC_PATH|No valid license`。

以上为 commit `fd9149f` + `12c0ca2`。

最终整体 review 追加(commit `5cd1a18`):

5. **Step 1 内容兜底替代单纯 mtime**:`Delete_DemConfigSet.py` 在 insert 前无条件重写 arxml,mtime 恒新,原兜底检测不到 insert 静默失败。改为加内容检查——Step 1 后 arxml 必须含容器级 DEF 锚点 `Dem/DemConfigSet/DemEventParameter</DEFINITION-REF>` 与 `Dem/DemConfigSet/DemDTC</DEFINITION-REF>` 各 ≥1(rx 实测 603/75;锚点带闭标签,子参数路径更长不会误匹配)。
6. **stdout 编码兜底**:启动时 `sys.stdout.reconfigure(errors="replace")`,避免中文 Windows 下 stdout 重定向为 GBK 时子脚本 emoji 输出炸掉诊断信息。
7. **headless 心跳**:轮询循环每 60s 打印"仍在运行",替代 ~10 分钟静默等待。

真机完整流程验证后追加(commit `9fda68c`):

8. **headless 成功判定不能依赖 `BSW_ConfGen_ECUGeneration.txt`**:真机实测 headless 模式根本不产生该文件(Cobra 专属),原判定会把 headless 成功误判为失败并触发 Cobra 降级。改为以 `_log/rta-bsw.log` 新鲜度证明"BSW 生成确实跑了"。
9. **改用 `ISOLAR-AB.cmd`**:headless 输出首行提示 `ISOLAR-B.cmd` 已 deprecated,按提示切换(启动器解析同时兼容两个文件名)。
10. **超时 1200s → 3600s**:首次真机运行 20 分钟只推进到 Com 模块(99 个 action 用时 8.5 分钟,Com 单个 action 停滞 11.5 分钟被杀);放宽到 60 分钟后完整跑通仅需 ~12.4 分钟。

### 真机 E2E 结果(2026-09-19,rx,完整流程)

- 第 1 次:Step 1-3 通过(4s/1s/2s);headless 20 分钟超时被杀(卡在 Com);Cobra 降级因本机无 Cobra license 干净报错退出(exit 1)——错误路径行为符合预期
- 第 2 次(修复后):Step 1-3 通过;ISOLAR-AB.cmd headless 745s 完成,exit code 0,rta-bsw.log 全部 action Success,零失败标记;`全部完成`
- 产物核验:`Dem_Cfg_EventId.h` 603 个事件 define;`Dem_PrjSpecificControl.c` 生成(92KB);evm_cfg 三文件(FidCfg.hpp/iSysFidCfg.cpp/zx fimcfg.hpp)全部更新



