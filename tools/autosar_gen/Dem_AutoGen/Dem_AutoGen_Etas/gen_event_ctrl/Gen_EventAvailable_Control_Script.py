# ==============================================================================
# Change Log
# ------------------------------------------------------------------------------
# Version  Date        Author    Change Log
# ------------------------------------------------------------------------------
# v1.0     2026-01-21  Developer Initial version release
#                              - Implement merge and clean for multiple Excel worksheets
#                              - Achieve data format conversion (macro name + U suffix)
#                              - Realize template placeholder replacement to generate compilable C files
#                              - Remove all processing logic for Dem_EventAvailable_Control_Init function
# v1.1     2026-01-21  Developer Optimize format adaptation and error handling
#                              - Increase macro name alignment width for ultra-long macro name scenarios
#                              - Optimize DTCEnableNo format processing to fix all-0 output issue
#                              - Improve exception handling and log prompts, add file backup mechanism
# ==============================================================================

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dem Configuration File Auto-Generation Script (Integrated Version)
Process: Excel multi-worksheet merge & clean → Data format conversion (macro name + U suffix) → Template placeholder replacement → Generate compilable C file
Dependency: Excel_Event_Merge_Process.py (must be in the same directory as the current script)
Note: All processing logic for Dem_EventAvailable_Control_Init function has been removed, the original content of the function in the template is retained
"""

import sys
import os
import re
import datetime
import pandas as pd
from typing import List, Tuple

# Import Excel processing module (consistent with the actual file name Excel_Event_Merge_Process.py)
try:
    from Excel_Event_Merge_Process import merge_excel_sheets
except ImportError as e:
    raise ImportError(f"Missing Excel processing module: {str(e)}\nPlease ensure Excel_Event_Merge_Process.py is in the same directory as the current script")

# ---------------------- 1. Global Configuration Constants ----------------------
# Excel Configuration
EXCEL_ORIGINAL_PATH = ""  # 由命令行参数传入，不再硬编码车型文件名
EXCEL_SHEET_NAMES = ["PF_Event", "RCore_Event_d310", "CPJ_Event_Net"]  # Worksheets to be merged
EXCEL_MERGED_SUFFIX = "_merged"  # Suffix of merged Excel file

# Template Configuration
TEMPLATE_DIR_NAME = "template"  # Template folder name
TPL_FILENAME = "Dem_PrjSpecificControl.tpl"  # Template file name
OUTPUT_FILENAME = "Dem_PrjSpecificControl.c"  # Output file name

# Placeholder Configuration
TPL_VERSION_PLACEHOLDER = "excel_version"
TPL_TIME_PLACEHOLDER = "Year-Mon-Day Hour:Minute:Second"
TPL_DEM_TABLE_REPLACE = "Dem_EventControlMappingTable_replace"

# C Array Macro Prefix Configuration (Fixed: No duplicate prefixes)
EVENT_MACRO_PREFIX = "DemConf_DemEventParameter_"  # Event macro prefix
DTC_MACRO_PREFIX = "DemConf_DemDTCClass_"  # DTC macro prefix

# Array Alignment Configuration (Ultra-long macro name adaptation + Enable No right alignment)
EVENT_MACRO_ALIGN_WIDTH = 85  # Increase event macro alignment width for ultra-long macro names
DTC_MACRO_ALIGN_WIDTH = 75    # Increase DTC macro alignment width for ultra-long macro names
ENABLE_NO_ALIGN_WIDTH = 5     # Enable No right alignment width (Ensure neat numbers)


# ---------------------- 2. Excel Data Processing & Format Conversion Tool Class ----------------------
class ExcelDataConverter:
    def __init__(self, excel_original_path: str, sheet_names: List[str]):
        self.excel_original_path = excel_original_path
        self.sheet_names = sheet_names
        self.merged_df: pd.DataFrame = pd.DataFrame()
        self.merged_excel_path: str = ""
        self.valid_data_list: List[Tuple[str, str, str]] = []

    def process_excel(self) -> None:
        """Execute Excel merge, cleaning and filtering (call external module)"""
        print("=== Phase 1: Merge and Clean Multiple Excel Worksheets ===")
        try:
            self.merged_df, self.merged_excel_path, _ = merge_excel_sheets(
                original_path=self.excel_original_path,
                sheet_names=self.sheet_names,
                add_source_column=True,
                drop_duplicates=True,
                new_suffix=EXCEL_MERGED_SUFFIX,
                enable_event_sort=True,
                enable_delete_na_event=True
            )
            print(f"✅ Excel processing completed, merged file: {self.merged_excel_path}")
            print(f"✅ Number of valid data rows: {len(self.merged_df)}")
        except Exception as e:
            raise Exception(f"Excel processing failed: {str(e)}")

    def convert_to_macro_format(self) -> None:
        """Convert Excel data to C macro format (add prefix, append U suffix, format fault tolerance)"""
        print("\n=== Phase 2: Convert Excel Data to C Macro Array Format ===")
        if self.merged_df.empty:
            raise ValueError("No valid Excel data, cannot convert to macro format")

        # Extract core three columns (Ensure column name compatibility)
        required_cols = ["Event Name", "DemUdsDTC", "DTCEnableNo"]
        for col in required_cols:
            if col not in self.merged_df.columns:
                raise ValueError(f"Excel missing required column: {col}")

        # Convert row by row
        for idx, row in self.merged_df.iterrows():
            # 1. Event Name → Add only the required prefix
            event_name = str(row["Event Name"]).strip()
            event_macro = self._format_event_name(event_name)
            event_macro_full = f"{EVENT_MACRO_PREFIX}{event_macro}"

            # 2. DemUdsDTC → Add macro prefix (No duplicates)
            dtc_id = str(row["DemUdsDTC"]).strip()
            dtc_macro = self._format_dtc_id(dtc_id)
            dtc_macro_full = f"{DTC_MACRO_PREFIX}{dtc_macro}"

            # 3. DTCEnableNo → Convert to number + U suffix
            enable_no_raw = str(row["DTCEnableNo"]).strip()
            enable_no_u = self._format_dtc_enable_no(enable_no_raw)

            # Save to valid data list
            self.valid_data_list.append((event_macro_full, dtc_macro_full, enable_no_u))

        print(f"✅ Data format conversion completed, generated {len(self.valid_data_list)} macro array items")

    def _format_event_name(self, event_name: str) -> str:
        """Format event name (add DemEvent_ prefix, retain original naming format)"""
        if not event_name:
            return "DemEvent_Unknown_Event"

        # Replace special characters with underscores, remove illegal characters
        formatted = event_name.replace(" ", "_").replace("-", "_").replace(".", "_").replace("/", "_")
        formatted = "".join([c for c in formatted if c.isalnum() or c == "_"])

        # Add DemEvent_ prefix (Do not add repeatedly)
        if not formatted.startswith("DemEvent_"):
            formatted = f"DemEvent_{formatted}"

        return formatted if formatted else "DemEvent_Unknown_Event"

    def _format_dtc_id(self, dtc_id: str) -> str:
        """Format DTC ID (add DemDTC_ prefix, no duplicates)"""
        if not dtc_id:
            return "Unknown_DTC"

        # Replace special characters with underscores, remove illegal characters
        formatted = dtc_id.replace(" ", "_")
        formatted = "".join([c for c in formatted if c.isalnum() or c in ["_", "U"]])

        # Add DemDTC_ prefix (Do not add repeatedly)
        if not formatted.startswith("DemDTC_") and formatted != "Unknown_DTC":
            formatted = f"DemDTC_{formatted}"

        return formatted if formatted else "Unknown_DTC"

    def _format_dtc_enable_no(self, enable_no_raw: str) -> str:
        """Compatible with multiple data formats, fix all-0 output issue"""
        if not enable_no_raw:
            return "0U"

        # Extract pure numbers
        num_match = re.search(r'\d+', enable_no_raw)
        if not num_match:
            return "0U"
        pure_num = num_match.group()

        # Convert to integer and append U suffix
        try:
            enable_no_int = int(pure_num)
            return f"{enable_no_int}U"
        except ValueError:
            return "0U"

    def get_aligned_c_array_content(self) -> str:
        """Generate neatly aligned C array content (only process array items, no involvement with other functions)"""
        if not self.valid_data_list:
            return "    /* No valid event data */"

        c_array_items = []
        total_items = len(self.valid_data_list)

        for idx, (event_macro, dtc_macro, enable_no_u) in enumerate(self.valid_data_list):
            # Left alignment padding to keep format neat
            event_macro_aligned = event_macro.ljust(EVENT_MACRO_ALIGN_WIDTH)
            dtc_macro_aligned = dtc_macro.ljust(DTC_MACRO_ALIGN_WIDTH)

            # Enable No right alignment
            enable_no_num = enable_no_u[:-1]
            enable_no_aligned = enable_no_num.rjust(ENABLE_NO_ALIGN_WIDTH) + "U"

            # Splice array items (remove comma for the last item)
            if idx == total_items - 1:
                c_item = f"{{{event_macro_aligned}, {dtc_macro_aligned}, {enable_no_aligned}}}"
            else:
                c_item = f"{{{event_macro_aligned}, {dtc_macro_aligned}, {enable_no_aligned}}},"

            # Add unified indentation
            c_array_items.append(f"    {c_item}")

        return "\n".join(c_array_items)


# ---------------------- 3. Template Processing Tool Class (Core Modification: Remove all processing for Dem_EventAvailable_Control_Init function) ----------------------
class TemplateHandler:
    def __init__(self):
        self.content: str = ""

    def load_template(self, tpl_path: str) -> None:
        """Load template (only add array semicolon, no processing for any functions)"""
        if not os.path.exists(tpl_path):
            raise FileNotFoundError(f"Template file does not exist: {tpl_path} (Please put it in the template folder)")
        try:
            with open(tpl_path, 'r', encoding="utf-8") as f:
                self.content = f.read()
            # Only retain the fix of "adding semicolon at the end of array" (irrelevant to functions, required by array syntax)
            self._fix_only_array_semicolon()
            print(f"\n✅ Template loaded successfully (only fix array semicolon, no processing for other content): {tpl_path}")
        except Exception as e:
            raise IOError(f"Template loading failed: {str(e)}")

    def _fix_only_array_semicolon(self) -> None:
        """Only fix the semicolon at the end of Dem_EventControlMappingTable array, no processing for any functions"""
        self.content = self.content.replace(
            "    Dem_EventControlMappingTable_replace\n\t\n}",
            "    Dem_EventControlMappingTable_replace\n\t\n};"
        )

    def replace_placeholders(self, c_array_content: str, excel_version: str) -> None:
        """Only replace 3 core placeholders, no modification to any function content"""
        print("\n=== Phase 3: Replace Template Placeholders (No Modification to Functions) ===")
        # 1. Replace Dem table array placeholder
        self.content = self.content.replace(TPL_DEM_TABLE_REPLACE, c_array_content)
        # 2. Replace version number placeholder
        self.content = self.content.replace(TPL_VERSION_PLACEHOLDER, excel_version)
        # 3. Replace time placeholder
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.content = self.content.replace(TPL_TIME_PLACEHOLDER, current_time)
        print("✅ Placeholder replacement completed (no changes to any functions)")

    def save_output(self, output_path: str) -> None:
        """Save output file"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        # Write to new file (retain original content of template functions)
        try:
            with open(output_path, 'w', encoding="utf-8") as f:
                f.write(self.content)
            print(f"\n✅ Output file saved successfully: {output_path}")
        except Exception as e:
            raise IOError(f"Output file saving failed: {str(e)}")


# ---------------------- 4. Core Generation Process ----------------------
def generate_dem_config(excel_version: str, script_root: str, output_dir: str) -> None:
    """End-to-end generate Dem configuration file (no processing for Dem_EventAvailable_Control_Init function)"""
    # Step 1: Excel data processing and format conversion
    excel_converter = ExcelDataConverter(
        excel_original_path=EXCEL_ORIGINAL_PATH,
        sheet_names=EXCEL_SHEET_NAMES
    )
    excel_converter.process_excel()
    excel_converter.convert_to_macro_format()
    c_array_content = excel_converter.get_aligned_c_array_content()

    # Step 2: Template processing and placeholder replacement (no modification to functions)
    tpl_handler = TemplateHandler()
    tpl_path = os.path.join(script_root, TEMPLATE_DIR_NAME, TPL_FILENAME)
    output_path = os.path.join(output_dir, OUTPUT_FILENAME)

    tpl_handler.load_template(tpl_path)
    tpl_handler.replace_placeholders(c_array_content, excel_version)
    tpl_handler.save_output(output_path)

    # Step 3: Generation completion prompt
    print("\n" + "=" * 60)
    print("Dem Configuration File Generation Completed!")
    print(f"1. Output File: {output_path}")
    print(f"2. Generation Info: Excel Version {excel_version}, {len(excel_converter.valid_data_list)} macro array items in total")
    print(f"3. Note: Dem_EventAvailable_Control_Init function retains the original template content, no processing is done")
    print("=" * 60)


# ---------------------- 5. Entry Function ----------------------
def derive_excel_version(excel_path: str) -> str:
    """从 Excel 文件名推导版本号（匹配 V1.4 / V0.6 等），推导失败回退 'V1.0'"""
    base = os.path.basename(excel_path)
    m = re.search(r'(V\d+\.\d+(?:\.\d+)?)', base, re.IGNORECASE)
    return m.group(1) if m else "V1.0"


def main():
    # 校验命令行参数：<excel路径> <输出目录>（输出目录默认为 Excel 所在目录）
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(f"Usage Error! Correct format:")
        print(f"python {sys.argv[0]} <excel_path> [output_dir]")
        print(f"Example: python {sys.argv[0]} IDC_EVM_Config_GAC_AY7_V1.4_20260622.xlsx ./output")
        sys.exit(1)

    excel_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel 文件不存在: {excel_path}")

    # 版本号从文件名自动推导，无需手动传入
    excel_version = derive_excel_version(excel_path)

    # 输出目录：未传入则与 Excel 同目录；传入则使用传入路径
    if len(sys.argv) == 3:
        output_dir = os.path.abspath(sys.argv[2])
    else:
        output_dir = os.path.dirname(excel_path)

    # 脚本根目录（模板与依赖文件所在），即本脚本所在目录
    script_root = os.path.dirname(os.path.abspath(__file__))

    # 将命令行传入的 Excel 路径写入全局配置，供 ExcelDataConverter 使用
    global EXCEL_ORIGINAL_PATH
    EXCEL_ORIGINAL_PATH = excel_path

    # 若输出文件已存在，不再生成 .bak（按需求禁用备份）
    output_path = os.path.join(output_dir, OUTPUT_FILENAME)

    # Verify parameter validity
    if not os.path.exists(script_root):
        raise FileNotFoundError(f"Script root directory does not exist: {script_root}")
    if not excel_version:
        raise ValueError("Excel version cannot be empty (e.g. V1.3)")
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        raise OSError(f"Failed to create output directory: {output_dir}, Error: {str(e)}")

    # Execute generation process
    try:
        generate_dem_config(excel_version, script_root, output_dir)
        print("\n=== All Processes Executed Successfully! ===")
    except Exception as e:
        print(f"\n=== Execution Failed: {str(e)} ===")
        sys.exit(1)


if __name__ == "__main__":
    main()