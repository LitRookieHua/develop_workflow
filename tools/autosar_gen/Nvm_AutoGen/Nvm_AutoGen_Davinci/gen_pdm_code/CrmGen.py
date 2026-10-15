#! /usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'yian'

import sys
import os
import datetime

from TemplateFile import TemplateFile
from ExcelAnalize import ExcelAnalize
import Merge_Excel
import pandas as pd

''' ~~~~~ note ~~~~~~~~~~~~~~~~
a 'self' must be one of the argument somehow...
~~~~~~~~~~~~~~~~~~~~~~~~~~~ '''


# ~~~~~~~~~~~~~~~~~~~ config area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
__pdmdbH_T_Path = r"..\PDM_Gen_Crm_Script\template\pdmdb_T.h"
__pdmdbH_Path = r"..\..\..\..\pdm_cfg\v2xsea\inc\pdm_cfg\pdmdb.h"

__pdmdbC_T_Path = r"..\PDM_Gen_Crm_Script\template\pdmdb_T.cpp"
__pdmdbC_Path = r"..\..\..\..\pdm_cfg\v2xsea\src\pdmdb.cpp"

__ov_pdm_dataitem_config_T_Path = r"..\PDM_Gen_Crm_Script\template\pdm_cfg_dataitem_config_T.cpp"
__ov_pdm_dataitem_config_Path = r"..\..\..\..\pdm_cfg\v2xsea\src\pdm_cfg_dataitem_config.cpp"


__pdm_cfg_T_Path = r"..\PDM_Gen_Crm_Script\template\pdm_cfg_T.h"
__pdm_cfg_Path = r"..\..\..\..\pdm_cfg\v2xsea\inc\pdm_cfg\pdm_cfg.h"

__Platform_csv_name = r"..\CHERY_V2xSEA_NVM_List.csv"
__Platform_excel_name = r"..\CHERY_V2xSEA_NVM_List.xlsx"
__PDM_List_Sheet = r"01_NVM_List"

__NvM_Cfg_h_Path = r"..\..\..\..\microsar_cfg\v2xsea_d300e\src\GenData\NvM_Cfg.h"

''' ~~~~~ note ~~~~~~~~~~~~~~~~
column starts from 0...
~~~~~~~~~~~~~~~~~~~~~~~~~~~ '''



# ~~~~~~~~~~~~~~~~~~~ declare area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def calc_bin_val_from_list(List):
    BinVal = 0
    WeiVal = 1
    for Val in List:
        if Val == 'Y':
                BinVal = BinVal + WeiVal
        WeiVal = WeiVal * 2
    return BinVal
    
def calc_bin_val_from_str(str, CmpStr):
    BinVal = 0
    if str == CmpStr:
        BinVal = 1
    else:
        BinVal = 0
    return BinVal

def map_read_write_type(excel_value):
    """将Excel中的iPdm_ReadWriteType值映射到C++枚举值"""
    if not excel_value or excel_value == '':
        return 'iPdm_ReadWriteNormal'  # 默认值
    
    excel_value_str = str(excel_value).strip()
    
    # 支持多种可能的输入值
    if excel_value_str in ['NORMAL', 'READWRITENORMAL', '0', '0x00', 'iPdm_ReadWriteNormal']:
        return 'iPdm_ReadWriteNormal'
    elif excel_value_str in ['IMMEDIATELY', 'READWRITEIMMEDIATELY', 'WRITEIMMEDIATELY', '1', '0x01','iPdm_ReadWriteImmediately']:
        return 'iPdm_ReadWriteImmediately'
    else:
        # 默认返回Normal，并输出警告
        print('WARNING: Unknown iPdm_ReadWriteType value "' + excel_value_str + '", using default: iPdm_ReadWriteNormal')
        return 'iPdm_ReadWriteNormal'

# ~~~~~~~~~~~~~~~~~~~ main area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def CRM_Gen():

    FPdmH = TemplateFile()
    FRteH = TemplateFile()
    FPdmC = TemplateFile()
    Fov_pdm_dataitem_configC = TemplateFile()
    FPdm_CfgH = TemplateFile()
    E = ExcelAnalize()
    
    #导入模板
    abs_file_path = os.path.abspath(__pdmdbH_T_Path)
    print("待解析文件绝对路径：", abs_file_path)

    FPdmH.copy(__pdmdbH_T_Path, __pdmdbH_Path)
    print('copy pdmdb_T.h done')
    
    
    FPdmC.copy(__pdmdbC_T_Path, __pdmdbC_Path)
    print('copy pdmdb_T.cpp done')

    Fov_pdm_dataitem_configC.copy(__ov_pdm_dataitem_config_T_Path, __ov_pdm_dataitem_config_Path)
    print('copy ov_pdm_dataitem_config_T.cpp done')

    FPdm_CfgH.copy(__pdm_cfg_T_Path, __pdm_cfg_Path)
    print('copy pdm_cfg_T.h done')
    
    
    #读取文件
    FPdmH.read_text(__pdmdbH_Path)
    print('open pdmdb.h done')
    
    
    FPdmC.read_text(__pdmdbC_Path)
    print('open pdmdb.cpp done')

    Fov_pdm_dataitem_configC.read_text(__ov_pdm_dataitem_config_Path)
    print('open ov_pdm_dataitem_config.cpp done')

    FPdm_CfgH.read_text(__pdm_cfg_Path)
    print('open pdm_cfg.h done')

    FNvM_CfgH = open(__NvM_Cfg_h_Path)
    print('open NvM_Cfg.h done')

    # 将NvM_Cfg.h中的 NvMConf_NvMBlockDescriptor_NVM_SWC_PDM* 复制到pdm_cfg.h
    replace_NvMConfID = ""
    blocks_count = 2
    for (num,value) in enumerate(FNvM_CfgH):
        if "NvMConf_NvMBlockDescriptor_NVM_SWC" in value:
            blocks_count += 1
            value1 = value.replace("NvMConf_NvMBlockDescriptor_NVM_SWC","NvMConf_NvMBlockDescriptor_NVM")
            replace_NvMConfID += value1
            #print("line num is: ", blocks_count, "content:", replace_NvMConf)

    FPdm_CfgH.AllText = FPdm_CfgH.AllText.replace("replace_NVM_CFG_NR_BLOCKS",str(blocks_count) + "u")
    FPdm_CfgH.AllText = FPdm_CfgH.AllText.replace("replace_NvMConf_NvMBlockDescriptor", replace_NvMConfID)

    #读取表格文件
    E.read(__Platform_excel_name, __PDM_List_Sheet)
    print('read excel done')
    
    #获取表格中的name等信息
    BlockNameList = E.get_row_name_by_idx(r'Name')
    BlockUserList = E.get_row_name_by_idx(r'User')
    BlockLenthList = E.get_row_name_by_idx(r'Block Length')
    BlockDefaultValList = E.get_row_name_by_idx(r'Init  Value(Hex)')
    BlockReadWriteTypeList = E.get_row_name_by_idx(r'iPdm_ReadWriteType')
    print('read name and lenth and default val and ReadWriteType from excel done')

    PickUp_iPdm_CusBlockCfg_Did = Fov_pdm_dataitem_configC.text_pick(r'replace Did start', r'replace Did end')
    ModifyText_iPdm_CusBlockCfg_Did = ''
    print('6 pick iPdm_CusBlockCfg_Did done ')

    PickUp_iPdm_CusBlockCfg_Dem = Fov_pdm_dataitem_configC.text_pick(r'replace Dem start', r'replace Dem end')
    ModifyText_iPdm_CusBlockCfg_Dem = ''
    print('7 pick iPdm_CusBlockCfg_Dem done ')


    id_count = 0
    replace_NvMConfLen = ""
    for EventFuncBinVal in BlockNameList:
        replace_NvMConfLen = replace_NvMConfLen + "#define NVM_CFG_NV_BLOCK_LENGTH_NVM_" + EventFuncBinVal.replace("Pdm","PDM") + "    (" + str(BlockLenthList[id_count]) + "u)\n"
        
        #配置ov_pdm_dataitem_config.cpp
        # 获取当前项的ReadWriteType并映射到C++枚举值
        current_read_write_type = map_read_write_type(BlockReadWriteTypeList[id_count])
        
        if "DEM" == BlockUserList[id_count]:
            ModifyText_iPdm_CusBlockCfg_Dem = Fov_pdm_dataitem_configC.text_append_line(ModifyText_iPdm_CusBlockCfg_Dem, PickUp_iPdm_CusBlockCfg_Dem)
            ModifyText_iPdm_CusBlockCfg_Dem = Fov_pdm_dataitem_configC.text_replace_to_text(r'replace_Dem_BlockID', 'NvMConf_NvMBlockDescriptor_NVM_PDM_DEM' + EventFuncBinVal.replace("Pdm_DEM",""), ModifyText_iPdm_CusBlockCfg_Dem)
            ModifyText_iPdm_CusBlockCfg_Dem = Fov_pdm_dataitem_configC.text_replace_to_text(r'RamReplace_Dem_BlockID', '(uint8 *)&Dem_Cfg' + EventFuncBinVal.replace("Pdm_DEM",""), ModifyText_iPdm_CusBlockCfg_Dem)
            ModifyText_iPdm_CusBlockCfg_Dem = Fov_pdm_dataitem_configC.text_replace_to_text(r'LengthReplace_Dem_BlockID', 'NVM_CFG_NV_BLOCK_LENGTH_NVM_' + EventFuncBinVal.replace("Pdm","PDM"), ModifyText_iPdm_CusBlockCfg_Dem)
            # 替换ReadWriteType
            ModifyText_iPdm_CusBlockCfg_Dem = Fov_pdm_dataitem_configC.text_replace_to_text(r'iPdm_ReadWriteType_replace', current_read_write_type, ModifyText_iPdm_CusBlockCfg_Dem)
        else:
            ModifyText_iPdm_CusBlockCfg_Did = Fov_pdm_dataitem_configC.text_append_line(ModifyText_iPdm_CusBlockCfg_Did, PickUp_iPdm_CusBlockCfg_Did)
            ModifyText_iPdm_CusBlockCfg_Did = Fov_pdm_dataitem_configC.text_replace_to_text(r'replace_Did_BlockID', 'NvMConf_NvMBlockDescriptor_NVM_' + EventFuncBinVal.replace("Pdm","PDM"), ModifyText_iPdm_CusBlockCfg_Did)
            ModifyText_iPdm_CusBlockCfg_Did = Fov_pdm_dataitem_configC.text_replace_to_text(r'RamReplace_Did_BlockID', 'Pdm'+EventFuncBinVal.lstrip('Pdm')+'_Ram', ModifyText_iPdm_CusBlockCfg_Did)
            ModifyText_iPdm_CusBlockCfg_Did = Fov_pdm_dataitem_configC.text_replace_to_text(r'LengthReplace_Did_BlockID', 'NVM_CFG_NV_BLOCK_LENGTH_NVM_' + EventFuncBinVal.replace("Pdm","PDM"), ModifyText_iPdm_CusBlockCfg_Did)
            # 替换ReadWriteType
            ModifyText_iPdm_CusBlockCfg_Did = Fov_pdm_dataitem_configC.text_replace_to_text(r'iPdm_ReadWriteType_replace', current_read_write_type, ModifyText_iPdm_CusBlockCfg_Did)

        id_count = id_count + 1
        
    FPdmC.AllText = FPdmC.AllText.replace("replace_IPDM_CUS_TOTAL_NUMBER_OF_DATA_BLOCKS", str(id_count) + "u")
    FPdm_CfgH.AllText = FPdm_CfgH.AllText.replace("replace_NVM_CFG_NV_BLOCK_LENGTH", replace_NvMConfLen)

    __Block_Name_Col_Start = 0
    for idx in BlockUserList:
        if idx == 'DEM':
            __Block_Name_Col_Start = __Block_Name_Col_Start +1

    #计算PDM Block个数,去除默认存在Blcok.
    BlockCount = E.get_count_by_col_name(r'Name')
    BlockNameList = BlockNameList[__Block_Name_Col_Start:BlockCount]
    BlockLenthList = BlockLenthList[__Block_Name_Col_Start:BlockCount]
    BlockDefaultValList = BlockDefaultValList[__Block_Name_Col_Start:BlockCount]
    BlockReadWriteTypeList = BlockReadWriteTypeList[__Block_Name_Col_Start:BlockCount]
    BlockCount = BlockCount-__Block_Name_Col_Start
    

    #往db.h写入计算个数
    FPdmH.text_replace_to_all(r'sasaDataItemCount', str(BlockCount))
    
    #依靠定位获取模板中的对应生成标准模板
    PickUp_Def = FPdmH.text_pick(r'pdm_cfgTbl item start', r'pdm_cfgTbl item end')
    ModifyText_Def = ''
    print('1 pick  define done ')
    
    PickUp_Exturn = FPdmH.text_pick(r'pdm_extern item start', r'pdm_extern item end')
    ModifyText_Exturn = ''
    print('2 pick exturn done ')
    
    PickUp_Ram = FPdmC.text_pick(r'pdm_Ram item start', r'pdm_Ram item end')
    ModifyText_Ram = ''
    print('3 pick Ram done ')
    
    PickUp_Rte = FRteH.text_pick(r'Pdm_RtePcTbl item start', r'Pdm_RtePcTbl item end')
    ModifyText_Rte = ''
    print('4 pick Rte pc table done ')
    
    PickUp_Rte_Len = FRteH.text_pick(r'Pdm_RteLenTbl item start', r'Pdm_RteLenTbl item end')
    ModifyText_Rte_Len = ''
    print('5 pick Rte Lenth done ')
    
    idx = 0
    for EventFuncBinVal in BlockNameList:

        if idx == (BlockCount -1):        #末尾删除字符 '\'
            PickUp_Def = PickUp_Def.rstrip('\\')  
        
        ModifyText_Def = FPdmH.text_append_line(ModifyText_Def, PickUp_Def)
        ModifyText_Def = FPdmH.text_replace_to_text(r'sasaBLOCK_NAME', EventFuncBinVal, ModifyText_Def)
        ModifyText_Def = FPdmH.text_replace_to_text(r'sasaBlockName_Ram', 'Pdm'+EventFuncBinVal.lstrip('Pdm')+'_Ram', ModifyText_Def)
        ModifyText_Def = FPdmH.text_replace_to_text(r'sasaNVM_BLOCK_LenthNum_DATA_LENGTH', str(BlockLenthList[idx]), ModifyText_Def)
        
        ModifyText_Exturn = FPdmH.text_append_line(ModifyText_Exturn, PickUp_Exturn)
        ModifyText_Exturn = FPdmH.text_replace_to_text(r'sasaRAMarrayName_Ram', 'Pdm'+EventFuncBinVal.lstrip('Pdm')+'_Ram', ModifyText_Exturn)
        ModifyText_Exturn = FPdmH.text_replace_to_text(r'sasalenth', str(BlockLenthList[idx]), ModifyText_Exturn)
        
        ModifyText_Ram = FPdmC.text_append_line(ModifyText_Ram, PickUp_Ram)
        temp1 = FPdmC.tohex(BlockDefaultValList[idx],BlockLenthList[idx])
        if temp1 == -1 :
            print('ERROE ' ,EventFuncBinVal ,' default val is wrong')
            return 
        ModifyText_Ram = FPdmC.text_replace_to_text(r'sasaRAMblockname_Ram', 'Pdm'+EventFuncBinVal.lstrip('Pdm')+'_Ram', ModifyText_Ram)
        ModifyText_Ram = FPdmC.text_replace_to_text(r'sasasalenth', str(BlockLenthList[idx]), ModifyText_Ram)
        ModifyText_Ram = FPdmC.text_replace_to_text(r'sasavalue', str(temp1), ModifyText_Ram)
        
        ModifyText_Rte = FRteH.text_append_line(ModifyText_Rte, PickUp_Rte)
        ModifyText_Rte = FRteH.text_replace_to_text(r'sasaPdmNam', EventFuncBinVal.upper(), ModifyText_Rte)
        ModifyText_Rte = FRteH.text_replace_to_text(r'sasaidx', str(idx), ModifyText_Rte)
        
        ModifyText_Rte_Len = FRteH.text_append_line(ModifyText_Rte_Len, PickUp_Rte_Len)
        ModifyText_Rte_Len = FRteH.text_replace_to_text(r'sasaPdmLenth', EventFuncBinVal.upper() + '_LENGTH', ModifyText_Rte_Len)
        ModifyText_Rte_Len = FRteH.text_replace_to_text(r'sasalenth', str(BlockLenthList[idx]), ModifyText_Rte_Len)
        
        idx = idx + 1
        #print(idx)
    print('pick modify done')
    
    FPdmH.text_replace_to_all(r'pdm_cfgTbl replace here', ModifyText_Def)
    FPdmH.text_replace_to_all(r'pdm_extern replace here', ModifyText_Exturn)
    FPdmC.text_replace_to_all(r'pdm_Ram replace here', ModifyText_Ram)
    FRteH.text_replace_to_all(r'Pdm_RtePcTbl replace here', ModifyText_Rte)
    FRteH.text_replace_to_all(r'Pdm_RteLenTbl replace here', ModifyText_Rte_Len)
    Fov_pdm_dataitem_configC.text_replace_to_all(r'replace Did here', ModifyText_iPdm_CusBlockCfg_Did)
    Fov_pdm_dataitem_configC.text_replace_to_all(r'replace Dem here', ModifyText_iPdm_CusBlockCfg_Dem)
    
    # 获取当前日期和时间
    current_datetime = datetime.datetime.now()
    FPdmH.text_replace_to_all(r'replace_time', str(current_datetime))
    Fov_pdm_dataitem_configC.text_replace_to_all(r'replace_time', str(current_datetime))
    FPdm_CfgH.text_replace_to_all(r'replace_time', str(current_datetime))
    print('replace here done')
    
    FPdmH.text_delete(r'pdm_cfgTbl item start', r'pdm_cfgTbl item end')
    FPdmH.text_delete(r'pdm_extern item start', r'pdm_extern item end')
    FPdmC.text_delete(r'pdm_Ram item start', r'pdm_Ram item end')
    FRteH.text_delete(r'Pdm_RtePcTbl item start', r'Pdm_RtePcTbl item end')
    FRteH.text_delete(r'Pdm_RteLenTbl item start', r'Pdm_RteLenTbl item end')
    Fov_pdm_dataitem_configC.text_delete(r'replace Did start', r'replace Did end')
    Fov_pdm_dataitem_configC.text_delete(r'replace Dem start', r'replace Dem end')
    print('delete done')
    
    #更新文件
    FPdmH.update_file(__pdmdbH_Path)  
    FPdmC.update_file(__pdmdbC_Path)
    Fov_pdm_dataitem_configC.update_file(__ov_pdm_dataitem_config_Path)
    FPdm_CfgH.update_file(__pdm_cfg_Path)

    # 读取Excel文件中所有子表的名称
    t_excelFile = pd.ExcelFile(__Platform_excel_name)
    # 创建Excel_To_Csv文件夹
    os.makedirs("Excel_To_Csv", exist_ok=True)
    # 遍历所有工作表
    for t_sheet_name in t_excelFile.sheet_names:
        # 读取工作表
        t_df = pd.read_excel(t_excelFile, sheet_name=t_sheet_name)
        # 导出为CSV文件，文件名与工作表名相同
        csv_file_path = f"Excel_To_Csv\{t_sheet_name}.csv"
        t_df.to_csv(csv_file_path, encoding='utf-8-sig')
        print(f"sheet <{t_sheet_name}.csv> export OK!")

    print('Success done\n')

if __name__ == '__main__':
    argc = len(sys.argv)
    if argc != 9:
        print("Error found!!!!Please input correct parameters",argc)
        sys.exit(0)
    else:
        __Platform_excel_name = sys.argv[1]
        __PDM_List_Sheet = sys.argv[2]
        __NvM_Cfg_h_Path = sys.argv[3]
        __pdm_cfg_Path = sys.argv[4]
        __pdmdbH_Path = sys.argv[5]
        __pdmdbC_Path = sys.argv[6]
        __ov_pdm_dataitem_config_Path = sys.argv[7]
        t_templatePath = sys.argv[8]
        __pdm_cfg_T_Path = t_templatePath + r"\pdm_cfg_T.h"
        __pdmdbH_T_Path = t_templatePath + r"\pdmdb_T.h"
        __pdmdbC_T_Path = t_templatePath + r"\pdmdb_T.cpp"
        __ov_pdm_dataitem_config_T_Path = t_templatePath + r"\pdm_cfg_dataitem_config_T.cpp"
        print('__Platform_excel_name:',__Platform_excel_name)
    
    CRM_Gen()


