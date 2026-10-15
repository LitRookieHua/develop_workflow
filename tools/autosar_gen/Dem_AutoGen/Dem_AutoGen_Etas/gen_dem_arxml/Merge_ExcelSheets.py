import pandas as pd
import os
from typing import List, Tuple


def get_char_priority(char: str) -> Tuple[int, int]:
    """
    单个字符优先级计算（返回元组，值越小优先级越高）
    规则：
    1. 类型优先级：数字(0) > 大写字母(1) > 下划线(2) > 小写字母(3)
    2. 同类型细化：数字比数值（小者优先）、字母比ASCII码（小者优先）
    """
    if char.isdigit():
        # 数字：类型0 + 数值（越小越优先）
        return (0, int(char))
    elif char.isupper():
        # 大写字母：类型1 + ASCII码（越小越优先）
        return (1, ord(char))
    elif char == "_":
        # 下划线：类型2 + 固定0
        return (2, 0)
    elif char.islower():
        # 小写字母：类型3 + ASCII码（越小越优先）
        return (3, ord(char))
    else:
        # 其他字符：最低优先级
        return (4, 99)


def generate_event_sort_key(event_name: str) -> Tuple[Tuple[int, int], ...]:
    """
    生成EventName的排序键（逐字符优先级元组）
    逻辑：逐字符从左到右比对，前缀相同则继续比对后续字符
    """
    if pd.isna(event_name) or event_name.strip() == "":
        # 空值返回最低优先级元组
        return ((99, 99),)
    # 逐字符生成优先级元组，组成排序键
    return tuple([get_char_priority(c) for c in event_name.strip()])


def merge_excel_sheets(
        original_path: str,
        sheet_names: List[str] = ["PF_Event", "RCore_Event_d310", "CPJ_Event_Net"],
        add_source_column: bool = True,
        drop_duplicates: bool = False,
        new_suffix: str = "_merged",
        enable_event_sort: bool = True,
        enable_delete_na_event: bool = True  # 新增：是否删除Event Name为N.A的行
) -> Tuple[pd.DataFrame, str, str]:
    """
    合并Excel工作表，清理空行，对“DEM Index”重新编号，并按规则排序EventName列。
    新增功能：删除Event Name为N.A的行（排序前执行）

    核心功能执行顺序：
    合并→清理空行→去重→【删除N.A行】→ 排序EventName → DEM Index重编号 → 保存
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

        # 读取并清理每个工作表的空行
        df_list = []
        for sheet in sheet_names:
            df = pd.read_excel(original_path, sheet_name=sheet)
            # 检查当前工作表是否有“DEM Index”列
            if "DEM Index" not in df.columns:
                raise ValueError(f"工作表 {sheet} 中缺少‘DEM Index’列")
            # 检查是否有EventName列（若启用排序/删除N.A行）
            if (enable_event_sort or enable_delete_na_event):
                if "Event Name" not in df.columns and "EventName" not in df.columns:
                    raise ValueError(f"工作表 {sheet} 中缺少‘Event Name’或‘EventName’列（功能依赖）")
            # 清理当前工作表的全空行
            df_clean = df.dropna(how="all").copy()
            if add_source_column:
                df_clean["source_sheet"] = sheet
            df_list.append(df_clean)

        # 步骤1：合并所有数据并二次清理空行
        merged_df = pd.concat(df_list, axis=0, ignore_index=True)
        before_final = len(merged_df)
        merged_df = merged_df.dropna(how="all")
        after_final = len(merged_df)
        if before_final > after_final:
            print(f"合并后额外清理全空行：{before_final - after_final} 行")

        # 步骤2：去重（如果需要）
        if drop_duplicates:
            before_dup = len(merged_df)
            merged_df = merged_df.drop_duplicates()
            print(f"已去除重复行：{before_dup - len(merged_df)} 行")

        # 步骤3：新增核心功能 - 删除Event Name为N.A的行（排序前执行）
        if enable_delete_na_event:
            # 兼容两种列名："Event Name"（带空格）、"EventName"（无空格）
            event_col = "Event Name" if "Event Name" in merged_df.columns else "EventName"
            if event_col in merged_df.columns:
                # 统计删除前行数，方便计算删除数量
                before_na_delete = len(merged_df)
                # 筛选：排除Event Name等于"N.A"的行（忽略前后空格，精准匹配）
                merged_df = merged_df[merged_df[event_col].astype(str).str.strip() != "N.A"]
                # 重置索引，避免索引断层影响后续操作
                merged_df = merged_df.reset_index(drop=True)
                # 统计并打印删除结果
                na_delete_count = before_na_delete - len(merged_df)
                print(f"✅ 已删除Event Name为N.A的行，共删除 {na_delete_count} 行")
            else:
                print("⚠️ 未找到Event Name/EventName列，跳过删除N.A行操作")

        # 步骤4：按规则排序EventName列
        if enable_event_sort:
            event_col = "Event Name" if "Event Name" in merged_df.columns else "EventName"
            if event_col in merged_df.columns:
                print(f"开始按字符优先级规则排序{event_col}列...")
                # 生成排序键并排序
                merged_df["_sort_key"] = merged_df[event_col].apply(generate_event_sort_key)
                merged_df = merged_df.sort_values(by="_sort_key", ascending=True)
                # 删除临时排序键列
                merged_df = merged_df.drop(columns=["_sort_key"])
                # 重置索引（避免排序后索引混乱）
                merged_df = merged_df.reset_index(drop=True)
                print(f"{event_col}列排序完成")
            else:
                print("⚠️ 未找到Event Name/EventName列，跳过排序操作")

        # 步骤5：重新编排“DEM Index”的序号（从1开始连续编号）
        if merged_df.columns[0] != "DEM Index":
            raise ValueError(f"第一列名称不是‘DEM Index’，当前第一列是：{merged_df.columns[0]}")
        # 生成新序号并覆盖（清理后重新连续编号）
        merged_df["DEM Index"] = range(1, len(merged_df) + 1)
        print(f"已完成‘DEM Index’重新编号，共 {len(merged_df)} 个有效行")

        # 步骤6：保存结果
        merged_df.to_excel(new_full_path, index=False)
        print(f"合并完成，新文件路径：{new_full_path}")

        return merged_df, new_full_path, new_file_name

    except Exception as e:
        raise IOError(f"处理失败：{str(e)}")


# -------------------------- 测试调用示例 --------------------------
if __name__ == "__main__":
    # 替换为你的Excel文件路径
    EXCEL_PATH = r"IDC_EVM_Config_GAC_AY7_V0.8_20260112.xlsx"

    try:
        result_df, save_path, save_name = merge_excel_sheets(
            original_path=EXCEL_PATH,
            sheet_names=["PF_Event", "RCore_Event_d310", "CPJ_Event_Net"],
            add_source_column=True,
            drop_duplicates=True,
            enable_event_sort=True,
            enable_delete_na_event=True  # 启用删除N.A行功能
        )
        # 预览处理后的前10行数据
        print("\n处理后前10行数据预览：")
        print(result_df[["DEM Index", "Event Name"]].head(10) if "Event Name" in result_df.columns else result_df[["DEM Index"]].head(10))
    except Exception as e:
        print(f"执行错误：{str(e)}")