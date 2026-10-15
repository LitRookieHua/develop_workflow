import pandas as pd
import os
from typing import List
from shutil import copy2  # 用于备份原文件


def get_char_priority(char: str) -> tuple:
    """
    单个字符优先级计算（返回元组，值越小优先级越高）
    核心规则：
    1. 类型优先级：数字(0) > 大写字母(1) > 下划线(2) > 小写字母(3)
    2. 同类型细化：数字比数值（小者优先）、字母比ASCII码（小者优先）
    """
    if char.isdigit():
        return (0, int(char))
    elif char.isupper():
        return (1, ord(char))
    elif char == "_":
        return (2, 0)
    elif char.islower():
        return (3, ord(char))
    else:
        return (4, 99)


def generate_event_sort_key(event_name: str) -> tuple:
    """生成EventName的排序键（逐字符优先级元组）"""
    if pd.isna(event_name) or event_name.strip() == "":
        return ((99, 99),)
    return tuple([get_char_priority(c) for c in event_name.strip()])


def merge_excel_sheets(
        original_path: str,
        sheet_names: List[str] = ["PF_Event", "RCore_Event_d310", "CPJ_Event_Net"],
        add_source_column: bool = True,
        drop_duplicates: bool = False,
        new_suffix: str = "_merged",
        enable_event_sort: bool = True  # 按规则排序EventName（默认开启）
) -> str:
    """
    合并Excel工作表，清理空行，删除Event Name列N.A行，按规则排序EventName，并重编DEM Index。
    仅返回：保存后的Excel文件完整路径名

    参数：
        original_path: 原Excel文件路径
        sheet_names: 要合并的工作表名列表
        add_source_column: 是否添加来源工作表列
        drop_duplicates: 是否去重
        new_suffix: 新文件后缀
        enable_event_sort: 是否按字符规则排序EventName
    返回：
        str: 保存后的Excel文件完整路径名
    """
    if not os.path.exists(original_path):
        raise FileNotFoundError(f"原文件不存在：{original_path}")

    # 生成带路径的新文件名
    file_dir, file_name = os.path.split(original_path)
    file_name_no_ext, file_ext = os.path.splitext(file_name)
    new_file_name = f"{file_name_no_ext}{new_suffix}{file_ext}"
    new_full_path = os.path.join(file_dir, new_file_name)

    try:
        # 检查工作表是否存在
        all_sheets = pd.ExcelFile(original_path).sheet_names
        missing_sheets = [s for s in sheet_names if s not in all_sheets]
        if missing_sheets:
            raise ValueError(f"缺少工作表：{missing_sheets}")

        # 读取并清理每个工作表的空行 + 过滤N.A行
        df_list = []
        for sheet in sheet_names:
            df = pd.read_excel(original_path, sheet_name=sheet)
            # 检查DEM Index列
            if "DEM Index" not in df.columns:
                raise ValueError(f"工作表 {sheet} 中缺少‘DEM Index’列")
            # 检查EventName列（过滤/排序依赖）
            if "Event Name" not in df.columns:
                raise ValueError(f"工作表 {sheet} 中缺少‘Event Name’列（过滤/排序依赖）")
            
            # ===== 新增：清理空行 =====
            df_clean = df.dropna(how="all").copy()
            
            # ===== 核心修改1：删除Event Name列值为N.A的行 =====
            # 1. 将列转为字符串类型，避免非字符串值干扰
            df_clean["Event Name"] = df_clean["Event Name"].astype(str)
            # 2. 定义需要过滤的无效值（可按需添加/删除，比如"NA"/"na"/"n.a"）
            invalid_values = {"N.A", "NA", "na", "n.a", "N.a", "n.A"}
            # 3. 过滤：保留不在无效值列表中，且非空/非空格的行
            df_clean = df_clean[
                ~df_clean["Event Name"].str.strip().isin(invalid_values)
            ].copy()
            # 打印当前工作表过滤的行数
            filtered_count = len(df) - len(df_clean)
            if filtered_count > 0:
                print(f"工作表 {sheet}：删除Event Name列N.A行共 {filtered_count} 行")
            
            if add_source_column:
                df_clean["source_sheet"] = sheet
            df_list.append(df_clean)

        # 合并数据并二次清理空行
        merged_df = pd.concat(df_list, axis=0, ignore_index=True)
        before_final = len(merged_df)
        merged_df = merged_df.dropna(how="all")
        after_final = len(merged_df)
        if before_final > after_final:
            print(f"合并后额外清理全空行：{before_final - after_final} 行")

        # 去重（如果需要）
        if drop_duplicates:
            before_dup = len(merged_df)
            merged_df = merged_df.drop_duplicates()
            print(f"已去除重复行：{before_dup - len(merged_df)} 行")

        # 按规则排序EventName列
        if enable_event_sort and "Event Name" in merged_df.columns:
            print("开始按字符优先级规则排序EventName列...")
            merged_df["_sort_key"] = merged_df["Event Name"].apply(generate_event_sort_key)
            merged_df = merged_df.sort_values(by="_sort_key", ascending=True)
            merged_df = merged_df.drop(columns=["_sort_key"]).reset_index(drop=True)
            print("EventName列排序完成")

        # 重新编排DEM Index序号
        if merged_df.columns[0] != "DEM Index":
            raise ValueError(f"第一列名称不是‘DEM Index’，当前第一列是：{merged_df.columns[0]}")
        merged_df["DEM Index"] = range(1, len(merged_df) + 1)
        print(f"已完成‘DEM Index’重新编号，共 {len(merged_df)} 个有效行")

        # 保存结果
        merged_df.to_excel(new_full_path, index=False)
        print(f"合并完成，新文件路径：{new_full_path}")

        # 仅返回保存后的Excel完整路径名
        return new_full_path

    except Exception as e:
        raise IOError(f"处理失败：{str(e)}")


def filter_excel_columns(file_path: str, backup: bool = True, keep_backup: bool = False):
    """
    筛选Excel中列名是"Event Name"或前缀为"FiMFID_"的列，并覆盖保存原文件
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在：{file_path}")

    backup_path = f"{file_path}.bak"
    if backup:
        copy2(file_path, backup_path)

    try:
        df = pd.read_excel(file_path)
        columns = df.columns.tolist()

        # 筛选目标列
        filtered_columns = [
            col for col in columns
            if col == "Event Name" or str(col).startswith("FiMFID_")
        ]

        if not filtered_columns:
            raise ValueError("未找到符合条件的列（EventName或前缀为FiMFID_的列）")

        filtered_df = df[filtered_columns].copy()

        # ===== 核心修改2：二次校验（可选）- 防止漏过滤的N.A行 =====
        if "Event Name" in filtered_df.columns:
            filtered_df["Event Name"] = filtered_df["Event Name"].astype(str)
            invalid_values = {"N.A", "NA", "na", "n.a", "N.a", "n.A"}
            before_filter = len(filtered_df)
            filtered_df = filtered_df[
                ~filtered_df["Event Name"].str.strip().isin(invalid_values)
            ].copy()
            if before_filter - len(filtered_df) > 0:
                print(f"筛选列后额外删除N.A行：{before_filter - len(filtered_df)} 行")

        # 覆盖保存原文件
        with pd.ExcelWriter(file_path, engine="openpyxl", mode="w") as writer:
            filtered_df.to_excel(writer, index=False)

        # 删除备份（如果不需要保留）
        if backup and not keep_backup and os.path.exists(backup_path):
            os.remove(backup_path)

        print(f"筛选完成！保留列：{filtered_columns}，已覆盖保存至文件：{file_path}")
        return filtered_df

    except Exception as e:
        print(f"筛选失败：{str(e)}")
        if backup and os.path.exists(backup_path):
            print(f"备份文件已保留（可用于恢复）：{backup_path}")
        raise


if __name__ == '__main__':
    # 1. 替换为你的Excel文件实际路径
    excel_path = "GAC_AY7_PlatformPara_V0.8.xlsx"

    # 2. 合并工作表（仅返回新文件完整路径名）
    full_path_with_name = merge_excel_sheets(
        original_path=excel_path,
        add_source_column=True,
        drop_duplicates=False
    )
    print(f"合并后文件完整路径：{full_path_with_name}")

    # 3. 筛选列
    try:
        result_df = filter_excel_columns(full_path_with_name)
        print(f"筛选后数据行数：{len(result_df)}，保留列：{result_df.columns.tolist()}")
    except Exception as e:
        print(f"执行错误：{e}")