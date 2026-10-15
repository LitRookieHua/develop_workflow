from Merge_ExcelSheets import merge_excel_sheets
from Parse_excel_list import parse_dem_excel
from Clear_DemConfigSet import clear_demconfigset_subcontainers
from Create_DemEventParameter import insert_dem_event_to_arxml
from Create_DemDTCs import insert_dem_dtc_to_arxml
from Create_DemDTCAttributes import insert_dem_dtc_attributes_to_arxml
from Create_DemDebounceCounterBasedClass import insert_debounce_counter_based_to_arxml
from Create_DemDebounceTimeBaseClass import insert_debounce_time_based_to_arxml

import os
import sys

if __name__ == "__main__":
    # 命令行参数：<excel路径> <arxml路径> [jumpdown] [jumpup]（jump 缺省 true，兼容手工运行）
    if len(sys.argv) not in (3, 5):
        print("用法: python Dem_arxml_Script.py <excel_path> <arxml_path> [jumpdown] [jumpup]")
        print("示例: python Dem_arxml_Script.py IDC_EVM_Config_GAC_AY7_V1.4_20260622.xlsx J6B_Dem_EcucValues.arxml true true")
        sys.exit(1)
    jump_down = (sys.argv[3] if len(sys.argv) == 5 else "true").lower()
    jump_up = (sys.argv[4] if len(sys.argv) == 5 else "true").lower()
    for v in (jump_down, jump_up):
        if v not in ("true", "false"):
            print(f"错误: jumpdown/jumpup 只接受 true/false, 实际 {v!r}")
            sys.exit(1)

    # 1. Excel 文件路径（由调用方传入，不再硬编码车型文件名）
    excel_path = sys.argv[1]

    # 合并默认的3个工作表，添加来源标识，不去重
    merged_data, full_path_with_name, only_name = merge_excel_sheets(
        original_path=excel_path  # 原文件带路径
    )
    print(f"合并后数据行数：{len(merged_data)}")


    # ARXML 文件路径（由调用方传入）
    arxml_file_path = sys.argv[2]

    PARENT_CONTAINER_XPATH = ".//ar:ECUC-CONTAINER-VALUE[ar:SHORT-NAME='DemConfigSet']/ar:SUB-CONTAINERS"  # 父容器XPath

    try:
        # 方案1：自动匹配（适合列名仅大小写/空格差异）
        dem_data = parse_dem_excel(full_path_with_name)
        # 打印解析结果（验证是否成功）
        print(f"\n=== 解析成功！共 {dem_data.data_count} 条Event ===")

    except Exception as e:
        print(f"\n=== 解析提示：{str(e)}")

    # 检查文件是否存在
    if not os.path.exists(arxml_file_path):
        print(f"错误: 文件 '{arxml_file_path}' 不存在")
    else:
        clear_demconfigset_subcontainers(arxml_file_path)

    # 执行插入
    insert_dem_event_to_arxml(
        input_arxml=arxml_file_path,
        output_arxml=arxml_file_path,
        parent_xpath=PARENT_CONTAINER_XPATH,
        dem_data=dem_data
    )

    insert_dem_dtc_to_arxml(
        input_arxml=arxml_file_path,
        output_arxml=arxml_file_path,
        parent_xpath=PARENT_CONTAINER_XPATH,
        dem_data=dem_data
    )

    insert_dem_dtc_attributes_to_arxml(
        input_arxml=arxml_file_path,
        output_arxml=arxml_file_path,
        parent_xpath=PARENT_CONTAINER_XPATH,
        dem_data=dem_data
    )

    insert_debounce_counter_based_to_arxml(
        input_arxml=arxml_file_path,
        output_arxml=arxml_file_path,
        parent_xpath=PARENT_CONTAINER_XPATH,
        dem_data=dem_data,
        jump_down=jump_down,
        jump_up=jump_up
    )

    insert_debounce_time_based_to_arxml(
        input_arxml=arxml_file_path,
        output_arxml=arxml_file_path,
        parent_xpath=PARENT_CONTAINER_XPATH,
        dem_data=dem_data
    )