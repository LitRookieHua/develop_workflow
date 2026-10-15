#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import glob
import pandas

EXCEL_TABLE_DIR = r"Excel_Table"
REQUIRED_SHEET_SUBSTRINGS = ["PF_Event", "RCore_Event_", "CPJ_Event_Net"]
CHECK_COLUMNS = ["Event Name", "DTC(hex)", "DTC Name"]


def find_excel_files(directory):
    """Find all .xlsx files in the given directory."""
    pattern = os.path.join(directory, "*.xlsx")
    files = glob.glob(pattern)
    return sorted(files)


def match_sheets(sheet_names):
    """Match sheet names by required substrings. Returns dict: substring -> sheet_name or None."""
    result = {}
    for substr in REQUIRED_SHEET_SUBSTRINGS:
        matched = None
        for name in sheet_names:
            if substr in name:
                matched = name
                break
        result[substr] = matched
    return result


def filter_rows(df):
    """Filter out N.A placeholder rows. Returns filtered DataFrame and skip count."""
    skip_count = 0
    filtered = df.copy()
    # Skip first row only if it is an N.A placeholder
    if len(filtered) > 0:
        first_dtc = str(filtered.iloc[0]["DTC(hex)"]).strip()
        if first_dtc == "N.A":
            filtered = filtered.iloc[1:]
            skip_count += 1
    # Skip rows where DTC(hex) == "N.A"
    na_mask = filtered["DTC(hex)"].astype(str).str.strip() == "N.A"
    skip_count += int(na_mask.sum())
    filtered = filtered[~na_mask].copy()
    return filtered, skip_count


def check_no_spaces(sheet_name, df):
    """Rule 2: Check for space characters in CHECK_COLUMNS. Returns list of errors."""
    errors = []
    for idx, row in df.iterrows():
        excel_row = idx + 2  # +1 for 0-based to 1-based, +1 for header row
        for col in CHECK_COLUMNS:
            val = row.get(col)
            if pandas.isna(val):
                continue  # handled by rule 3
            val_str = str(val)
            if val_str != val_str.strip():
                msg = f'[FAIL] [{sheet_name}] Row {excel_row}: "{col}" contains space characters: "{val_str}"'
                print(msg)
                errors.append(msg)
    return errors


def check_not_empty(sheet_name, df):
    """Rule 3: Check for empty/blank values in CHECK_COLUMNS. Returns list of errors."""
    errors = []
    for idx, row in df.iterrows():
        excel_row = idx + 2  # +1 for 0-based to 1-based, +1 for header row
        for col in CHECK_COLUMNS:
            val = row.get(col)
            if pandas.isna(val):
                msg = f'[FAIL] [{sheet_name}] Row {excel_row}: "{col}" is empty'
                print(msg)
                errors.append(msg)
            elif isinstance(val, str) and val.strip() == "":
                msg = f'[FAIL] [{sheet_name}] Row {excel_row}: "{col}" is empty'
                print(msg)
                errors.append(msg)
    return errors


def check_dtc_prority_consistency(sheet_name, df):
    """Rule 4: Same DTC(hex) must have same Prority. Returns list of errors."""
    errors = []
    if "Prority" not in df.columns:
        return errors
    dtc_groups = df.groupby("DTC(hex)")
    for dtc_hex, group in dtc_groups:
        valid_mask = group["Prority"].notna() & (group["Prority"].astype(str).str.strip() != "N.A")
        prority_values = group.loc[valid_mask, "Prority"].unique()
        if len(prority_values) > 1:
            first_val = prority_values[0]
            conflicting = group[valid_mask & (group["Prority"] != first_val)]
            first_row = group[valid_mask & (group["Prority"] == first_val)].index[0] + 2
            for conflict_idx in conflicting.index:
                conflict_row = conflict_idx + 2
                conflict_val = group.loc[conflict_idx, "Prority"]
                msg = f'[FAIL] [{sheet_name}] DTC {dtc_hex} has conflicting Prority: row {first_row}={first_val}, row {conflict_row}={conflict_val}'
                print(msg)
                errors.append(msg)
    return errors


def check_excel(filepath):
    """Run all checks on a single Excel file. Returns error count."""
    filename = os.path.basename(filepath)

    print(f"\n=== Checking: {filename} ===")

    try:
        xl = pandas.ExcelFile(filepath, engine="openpyxl")
    except Exception as e:
        msg = f"[FAIL] Cannot read file: {e}"
        print(msg)
        return 1

    sheet_matches = match_sheets(xl.sheet_names)

    # Rule 1: Sheet name validation
    errors = 0
    for substr, matched in sheet_matches.items():
        if matched is None:
            msg = f'[FAIL] No sheet found with "{substr}" in its name'
            print(msg)
            errors += 1

    # Collect matched sheet names for rules 2-4
    matched_sheets = [name for name in sheet_matches.values() if name is not None]

    # Read all matched sheets before closing
    sheet_data = {}
    for sheet_name in matched_sheets:
        sheet_data[sheet_name] = pandas.read_excel(xl, sheet_name=sheet_name)
    xl.close()

    # Run rules 2-4 on each matched sheet
    for sheet_name in matched_sheets:
        print(f"\n--- Sheet: {sheet_name} ---")
        df = sheet_data[sheet_name]
        filtered, skip_count = filter_rows(df)

        sheet_errors = 0
        sheet_errors += len(check_not_empty(sheet_name, filtered))
        sheet_errors += len(check_no_spaces(sheet_name, filtered))
        sheet_errors += len(check_dtc_prority_consistency(sheet_name, filtered))

        if sheet_errors == 0:
            print("All checks passed.")
        if skip_count > 0:
            print(f"[INFO] {skip_count} rows skipped (DTC=N.A)")

        errors += sheet_errors

    return errors


if __name__ == "__main__":
    excel_dir = sys.argv[1] if len(sys.argv) > 1 else EXCEL_TABLE_DIR
    excel_files = find_excel_files(excel_dir)

    if not excel_files:
        print(f"No .xlsx files found in {excel_dir}")
        sys.exit(1)

    total_errors = 0
    summary_lines = []

    for filepath in excel_files:
        filename = os.path.basename(filepath)
        error_count = check_excel(filepath)
        total_errors += error_count
        summary_lines.append(f"{filename}: {error_count} error(s)")

    print("\n=== Summary ===")
    for line in summary_lines:
        print(line)

    if total_errors > 0:
        print(f"\nTotal: {total_errors} error(s) - CHECK FAILED")
        sys.exit(1)
    else:
        print("\nAll checks passed.")
        sys.exit(0)
