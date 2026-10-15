# ==============================================================================
# Script Name: Excel_Event_Merge_Process.py
# Function Description: Merge multiple Excel worksheets, clean invalid data, filter specified columns, generate valid data file with change log
# Change Log (Chronological order from newest to oldest, latest changes at the top):
# ------------------------------------------------------------------------------
# Version: V1.3
# Modification Date: 2026-01-19
# Change Content:
# 1. New Feature: Retain only three columns - Event Name, DemUdsDTC, DTCEnableNo
# 2. New Feature: Delete rows where DemUdsDTC column is N.A (including spaces) or empty
# 3. Optimization: Add openpyxl engine for Excel read/write to improve .xlsx file compatibility
# ------------------------------------------------------------------------------
# Version: V1.2
# Modification Date: 2026-01-18
# Change Content:
# 1. New Feature: Function to delete invalid rows where Event Name is N.A
# 2. Optimization: Compatible with two column names - Event Name (with space) and EventName (without space)
# 3. Optimization: Improve type annotations, use precise Tuple instead of generic tuple
# ------------------------------------------------------------------------------
# Version: V1.1
# Modification Date: 2026-01-17
# Change Content:
# 1. Implementation: Multi-worksheet merge, full empty row cleaning, duplicate row deletion functions
# 2. Implementation: Custom character priority sorting for EventName column
# 3. Implementation: Reorganize DEM Index as continuous serial numbers
# ------------------------------------------------------------------------------
# Version: V1.0
# Modification Date: 2026-01-16
# Change Content: Initial version, implement basic Excel file reading and saving
# ==============================================================================

import pandas as pd
import os
from typing import List, Tuple
from datetime import datetime

def get_char_priority(char: str) -> Tuple[int, int]:
    """
    Single character priority calculation (return tuple, smaller value means higher priority)
    Rules:
    1. Type priority: Numeric(0) > Uppercase Letter(1) > Underscore(2) > Lowercase Letter(3)
    2. Same type refinement: Numeric by value (smaller first), Letter by ASCII code (smaller first)
    """
    if char.isdigit():
        # Numeric: Type 0 + value (smaller is higher priority)
        return (0, int(char))
    elif char.isupper():
        # Uppercase letter: Type 1 + ASCII code (smaller is higher priority)
        return (1, ord(char))
    elif char == "_":
        # Underscore: Type 2 + fixed 0
        return (2, 0)
    elif char.islower():
        # Lowercase letter: Type 3 + ASCII code (smaller is higher priority)
        return (3, ord(char))
    else:
        # Other characters: Lowest priority
        return (4, 99)

def generate_event_sort_key(event_name: str) -> Tuple[Tuple[int, int], ...]:
    """
    Generate sort key for EventName (tuple of character priority tuples)
    Logic: Compare characters from left to right one by one, continue comparing subsequent characters if prefixes are the same
    """
    if pd.isna(event_name) or event_name.strip() == "":
        # Return lowest priority tuple for empty values
        return ((99, 99),)
    # Generate priority tuple for each character to form sort key
    return tuple([get_char_priority(c) for c in event_name.strip()])

def merge_excel_sheets(
        original_path: str,
        sheet_names: List[str] = ["PF_Event", "RCore_Event_d310", "CPJ_Event_Net"],
        add_source_column: bool = True,
        drop_duplicates: bool = False,
        new_suffix: str = "_merged",
        enable_event_sort: bool = True,
        enable_delete_na_event: bool = True  # New: Whether to delete rows where Event Name is N.A
) -> Tuple[pd.DataFrame, str, str]:
    """
    Merge Excel worksheets, clean empty rows, renumber "DEM Index", and sort EventName column by rules.
    New Features:
    1. Delete rows where Event Name is N.A (execute before sorting)
    2. Retain only three columns - Event Name, DemUdsDTC, DTCEnableNo
    3. Remove rows where DemUdsDTC column is N.A (including spaces) or empty

    Core Function Execution Order:
    Merge → Clean empty rows → Remove duplicates → Delete N.A rows → Sort EventName → Filter specified three columns → Clean invalid DemUdsDTC rows → Renumber DEM Index → Save
    """
    if not os.path.exists(original_path):
        raise FileNotFoundError(f"Original file does not exist: {original_path}")

    # Generate new file name with path
    file_dir, file_name = os.path.split(original_path)
    file_name_no_ext, file_ext = os.path.splitext(file_name)
    new_file_name = f"{file_name_no_ext}{new_suffix}{file_ext}"
    new_full_path = os.path.join(file_dir, new_file_name)

    try:
        # Check if worksheets exist
        all_sheets = pd.ExcelFile(original_path).sheet_names
        missing_sheets = [s for s in sheet_names if s not in all_sheets]
        if missing_sheets:
            raise ValueError(f"Missing worksheets: {missing_sheets}")

        # Read and clean empty rows for each worksheet
        df_list = []
        for sheet in sheet_names:
            df = pd.read_excel(original_path, sheet_name=sheet, engine="openpyxl")
            # Check if current worksheet has "DEM Index" column
            if "DEM Index" not in df.columns:
                raise ValueError(f"Worksheet {sheet} missing 'DEM Index' column")
            # Check required columns (dependency for subsequent filtering)
            required_cols = ["DemUdsDTC", "DTCEnableNo"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Worksheet {sheet} missing required columns: {missing_cols}")
            # Check if EventName column exists (if sorting/deleting N.A rows is enabled)
            if (enable_event_sort or enable_delete_na_event):
                if "Event Name" not in df.columns and "EventName" not in df.columns:
                    raise ValueError(f"Worksheet {sheet} missing 'Event Name' or 'EventName' column (function dependency)")
            # Clean full empty rows of current worksheet
            df_clean = df.dropna(how="all").copy()
            if add_source_column:
                df_clean["source_sheet"] = sheet
            df_list.append(df_clean)

        # Step 1: Merge all data and clean empty rows again
        merged_df = pd.concat(df_list, axis=0, ignore_index=True)
        before_final = len(merged_df)
        merged_df = merged_df.dropna(how="all")
        after_final = len(merged_df)
        if before_final > after_final:
            print(f"Additional full empty rows cleaned after merging: {before_final - after_final} rows")

        # Step 2: Remove duplicates (if needed)
        if drop_duplicates:
            before_dup = len(merged_df)
            merged_df = merged_df.drop_duplicates()
            print(f"Duplicate rows removed: {before_dup - len(merged_df)} rows")

        # Step 3: Delete rows where Event Name is N.A (execute before sorting)
        if enable_delete_na_event:
            # Compatible with two column names: "Event Name" (with space), "EventName" (without space)
            event_col = "Event Name" if "Event Name" in merged_df.columns else "EventName"
            if event_col in merged_df.columns:
                # Count rows before deletion for calculating deleted quantity
                before_na_delete = len(merged_df)
                # Filter: Exclude rows where Event Name equals "N.A" (ignore leading/trailing spaces, exact match)
                merged_df = merged_df[merged_df[event_col].astype(str).str.strip() != "N.A"]
                # Reset index to avoid index fragmentation affecting subsequent operations
                merged_df = merged_df.reset_index(drop=True)
                # Count and print deletion result
                na_delete_count = before_na_delete - len(merged_df)
                print(f"✅ Rows with Event Name = N.A deleted, total deleted: {na_delete_count} rows")
            else:
                print("⚠️ 'Event Name'/EventName column not found, skip N.A row deletion")

        # Step 4: Sort EventName column by rules
        if enable_event_sort:
            event_col = "Event Name" if "Event Name" in merged_df.columns else "EventName"
            if event_col in merged_df.columns:
                print(f"Start sorting {event_col} column by character priority rules...")
                # Generate sort key and sort
                temp_sort_col = "_event_sort_key_temporary_column"
                merged_df[temp_sort_col] = merged_df[event_col].apply(generate_event_sort_key)
                merged_df = merged_df.sort_values(by=temp_sort_col, ascending=True)
                # Delete temporary sort key column
                merged_df = merged_df.drop(columns=[temp_sort_col])
                # Reset index (avoid index confusion after sorting)
                merged_df = merged_df.reset_index(drop=True)
                print(f"{event_col} column sorting completed")
            else:
                print("⚠️ 'Event Name'/EventName column not found, skip sorting operation")

        # Step 5: Core New Feature - Retain only specified three columns (Event Name, DemUdsDTC, DTCEnableNo)
        target_columns = ["Event Name", "DemUdsDTC", "DTCEnableNo"]
        # Compatible with EventName (without space) column name, replace with target column name
        if "EventName" in merged_df.columns and "Event Name" not in merged_df.columns:
            merged_df.rename(columns={"EventName": "Event Name"}, inplace=True)
        # Verify if target columns exist
        missing_target_cols = [col for col in target_columns if col not in merged_df.columns]
        if missing_target_cols:
            raise ValueError(f"Missing specified retained columns: {missing_target_cols}")
        # Filter to retain only specified three columns
        merged_df = merged_df[target_columns].copy()
        print(f"✅ Filtered to retain only specified columns: {target_columns}")

        # Step 6: Core New Feature - Remove rows where DemUdsDTC column is N.A (including spaces) or empty
        dem_col = "DemUdsDTC"
        if dem_col in merged_df.columns:
            before_dem_clean = len(merged_df)
            # Condition 1: Non-empty value (exclude NaN, None, empty string)
            cond1 = ~pd.isna(merged_df[dem_col])
            # Condition 2: After converting to string, remove leading/trailing spaces, not equal to "N.A"
            cond2 = merged_df[dem_col].astype(str).str.strip() != "N.A"
            # Condition 3: After converting to string, remove leading/trailing spaces, non-empty (exclude pure space rows)
            cond3 = merged_df[dem_col].astype(str).str.strip() != ""
            # Combine conditions, retain rows that meet requirements
            merged_df = merged_df[cond1 & cond2 & cond3].reset_index(drop=True)
            # Count deleted quantity
            dem_delete_count = before_dem_clean - len(merged_df)
            print(f"✅ Rows with DemUdsDTC = N.A or empty deleted, total deleted: {dem_delete_count} rows")
        else:
            print("⚠️ DemUdsDTC column not found, skip empty/N.A cleaning operation")

        # Step 7: Reorganize serial numbers of "DEM Index" (add column first, then number, since the column is missing after filtering)
        # Insert DEM Index as the first column (retain original logic)
        merged_df.insert(0, "DEM Index", range(1, len(merged_df) + 1))
        print(f"'DEM Index' renumbering completed, total {len(merged_df)} valid rows")

        # Step 8: Save results (specify engine to improve compatibility)
        merged_df.to_excel(new_full_path, index=False, engine="openpyxl")
        print(f"Merge completed, new file path: {new_full_path}")

        return merged_df, new_full_path, new_file_name

    except Exception as e:
        raise Exception(f"Processing failed: {str(e)}") from e

# -------------------------- Test Call Example --------------------------
if __name__ == "__main__":
    # Replace with your Excel file path
    EXCEL_PATH = r"IDC_EVM_Config_GAC_AY7_V1.4_20260622.xlsx"

    try:
        result_df, save_path, save_name = merge_excel_sheets(
            original_path=EXCEL_PATH,
            sheet_names=["PF_Event", "RCore_Event_d310", "CPJ_Event_Net"],
            add_source_column=True,
            drop_duplicates=True,
            enable_event_sort=True,
            enable_delete_na_event=True
        )
        # Preview first 10 rows of processed data (only show specified three columns + DEM Index)
        print("\nPreview of first 10 rows after processing:")
        print(result_df.head(10))
    except Exception as e:
        print(f"Execution error: {str(e)}")