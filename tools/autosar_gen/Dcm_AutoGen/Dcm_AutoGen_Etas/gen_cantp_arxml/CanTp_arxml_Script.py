"""CanTp arxml 生成入口: Excel CanTp 表 + 输入 arxml → 输出 arxml (原地).

流程:
  1. parse  解析问卷 CanTp 表 (CanTpGeneral/CanTpConfig/各 NSdu 容器行)
  2. patch  按容器 SHORT-NAME 把参数写进 arxml (只改 VALUE, 保留结构)
  3. verify 重开输出 arxml, 逐条断言已写值落位

用法:
  python CanTp_arxml_Script.py <excel_path> <input_arxml> <output_arxml>
"""

import sys

from Parse_cantp_excel import parse_cantp_excel
from Patch_CanTpParams import patch_cantp_arxml, verify_cantp_arxml


def main():
    if len(sys.argv) != 4:
        print("用法: python CanTp_arxml_Script.py <excel_path> <input_arxml> <output_arxml>")
        print("示例: python CanTp_arxml_Script.py UDS_Diagnostic_Questionnaire_J02.xlsx "
              "J6B_CanTp_EcucValues.arxml J6B_CanTp_EcucValues.arxml")
        sys.exit(1)
    excel_path, input_arxml, output_arxml = sys.argv[1:4]

    try:
        data = parse_cantp_excel(excel_path)
    except ValueError as e:
        print("错误：%s" % e)
        sys.exit(1)
    print("=== 解析成功！%d 个数据行, %d 个 NSdu 行, PaddingByte=%r, "
          "PaddingActivation=%r, MainFunctionPeriod=%r s ==="
          % (data.row_count, len(data.nsdu_rows), data.padding_byte,
             data.padding_activation, data.main_function_period))

    try:
        changes = patch_cantp_arxml(input_arxml, output_arxml, data)
        verify_cantp_arxml(output_arxml, changes)
    except ValueError as e:
        print("错误：%s" % e)
        sys.exit(1)

    print("已写入 %d 个参数:" % len(changes))
    for container, param, value in changes:
        print("  %-40s %-28s = %s" % (container, param, value))
    print("校验通过: %s" % output_arxml)


if __name__ == "__main__":
    main()
