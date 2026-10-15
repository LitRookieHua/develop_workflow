import sys
import pandas
import os


Excel_Path = r"IDC_EVM_Config_Chery_E01E02_V1.2_20251223.xlsx"
Csv_Path = r"Evm_Config_Excel_To_Csv"

def excel_to_csv():
    # 读取Excel文件
    t_xls = pandas.ExcelFile(Excel_Path)
    # 创建Excel_To_Csv文件夹
    os.makedirs(Csv_Path, exist_ok=True)
    
    # 遍历所有工作表
    for t_sheet_name in t_xls.sheet_names:
        # 读取工作表
        t_df = pandas.read_excel(t_xls, sheet_name=t_sheet_name)
        
        # 导出为CSV文件，文件名与工作表名相同
        csv_file_path = f"{Csv_Path}/{t_sheet_name}.csv"
        t_df.to_csv(csv_file_path, encoding='utf-8-sig')
        print(f"sheet <{t_sheet_name}.csv> export OK!")


if __name__ == '__main__':
    argc = len(sys.argv)
    if argc != 3:
        print("Error found!!!!Please input correct parameters")
        sys.exit(0)
    else:
        Excel_Path = sys.argv[1]
        Csv_Path   = sys.argv[2]
        
    excel_to_csv()
    
