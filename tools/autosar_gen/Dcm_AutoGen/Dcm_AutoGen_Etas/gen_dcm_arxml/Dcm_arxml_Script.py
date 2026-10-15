"""Dcm arxml 生成入口: Excel + 输入 arxml → 输出 arxml.

流程 (参考 Dem_AutoGen_Etas/gen_dem_arxml/Dem_arxml_Script.py):
  1. parse  解析 UDS 诊断问卷 Service List + DcmDspSession/DcmDspSecurity 表
  2. clear  清空 ETAS_ServiceTable_DoCAN 的 SUB-CONTAINERS
  3. insert 重建 DcmDsdService / DcmDsdSubService
  4. rebuild 清空并重建 DcmDspSession / DcmDspSecurity 的 SUB-CONTAINERS

用法:
  python Dcm_arxml_Script.py <excel_path> <input_arxml> <output_arxml>
"""

import sys

from Parse_dcm_excel import parse_dcm_excel
from Parse_dcm_dsp_excel import parse_dcm_dsp_excel
from Clear_DcmServiceTable import clear_service_table_subcontainers
from Create_DcmDsdServices import insert_dcm_services_to_arxml
from Rebuild_DcmDsp import rebuild_dcm_dsp_containers


def main():
    if len(sys.argv) != 4:
        print("用法: python Dcm_arxml_Script.py <excel_path> <input_arxml> <output_arxml>")
        print("示例: python Dcm_arxml_Script.py UDS_Diagnostic_Questionnaire_J02.xlsx "
              "J6B_Dcm_EcucValues.arxml J6B_Dcm_EcucValues.arxml")
        sys.exit(1)
    excel_path, input_arxml, output_arxml = sys.argv[1:4]

    # 1. 解析 Excel (先全部解析, 失败即退出, 不改动文件)
    try:
        dcm_data = parse_dcm_excel(excel_path)
        dsp_data = parse_dcm_dsp_excel(excel_path)
    except ValueError as e:
        print("错误：%s" % e)
        sys.exit(1)
    print("=== 解析成功！共 %d 个服务, %d 个 Session 行, %d 个 Security 行 ==="
          % (dcm_data.service_count, dsp_data.session_count, dsp_data.security_count))
    expected_subs = sum(len(s["subs"]) for s in dcm_data.services)

    # 2. 清空服务表
    if not clear_service_table_subcontainers(input_arxml, output_arxml):
        sys.exit(1)

    # 3. 重建服务容器
    if not insert_dcm_services_to_arxml(output_arxml, output_arxml, dcm_data):
        sys.exit(1)

    # 4. 重建 DcmDspSession / DcmDspSecurity
    if not rebuild_dcm_dsp_containers(output_arxml, output_arxml, dsp_data):
        sys.exit(1)

    # 5. 内容锚点兜底 (子脚本静默失败 = 锚点缺失)
    with open(output_arxml, encoding="utf-8", errors="replace") as f:
        text = f.read()
    checks = [
        ("DcmDsdService</DEFINITION-REF>", dcm_data.service_count),
        ("DcmDsdSubService</DEFINITION-REF>", expected_subs),
        ("Dcm/DcmConfigSet/DcmDsp/DcmDspSession/DcmDspSessionRow</DEFINITION-REF>",
         dsp_data.session_count),
        ("Dcm/DcmConfigSet/DcmDsp/DcmDspSecurity/DcmDspSecurityRow</DEFINITION-REF>",
         dsp_data.security_count),
    ]
    for anchor, expected in checks:
        actual = text.count(anchor)
        if actual != expected:
            print("错误：锚点 %s 计数 %d != 预期 %d (子脚本 insert 静默失败?): %s"
                  % (anchor, actual, expected, output_arxml))
            sys.exit(1)
    print("锚点校验通过: DcmDsdService=%d, DcmDsdSubService=%d, "
          "DcmDspSessionRow=%d, DcmDspSecurityRow=%d"
          % (dcm_data.service_count, expected_subs,
             dsp_data.session_count, dsp_data.security_count))


if __name__ == "__main__":
    main()
