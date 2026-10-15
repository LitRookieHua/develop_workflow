#! /usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'yian'

import sys


from ExcelAnalize import ExcelAnalize
import pandas
import ProcessArxml

''' ~~~~~ note ~~~~~~~~~~~~~~~~
a 'self' must be one of the argument somehow...
~~~~~~~~~~~~~~~~~~~~~~~~~~~ '''


# ~~~~~~~~~~~~~~~~~~~ config area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
__Platform_excel_name = r"..\CHERY_V2xSEA_NVM_List.xlsx"
__PDM_List_Sheet = r"01_NVM_List"
__PDM_ARXML_FILE_PATH = r"..\..\..\..\microsar_cfg\v2xsea_d300e\build\SipAddon\Config\Developer\ComponentTypes\NVM_SWC_1.arxml"
__PDM_DATA_TYPE_ARXML_FILE_PATH = r"..\..\..\..\microsar_cfg\v2xsea_d300e\build\SipAddon\Config\Developer\DataTypes.arxml"

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

class ARXML_Need_Data:
    def __init__(self):
        self.num = ''
        self.lenth = []
        self.Pdm_Name = []
        self.start_offset = ''

## brief read excel
#  @param input_file  excel path name 
#  @param sheetname      
def ReadDemExcel(input_file,sheetname):

    E = ExcelAnalize()

    # 读取表格文件
    E.read(input_file, sheetname)
    df = pandas.read_excel(input_file, engine ='openpyxl', sheet_name = sheetname)
    
    data = ARXML_Need_Data()
    data.start_offset = 0

    BlockCount = E.get_count_by_col_name(r'Name')
    BlockNameList = E.get_row_name_by_idx(r'Name')
    BlockLenthList = E.get_row_name_by_idx(r'Block Length')

    data.num = df['Index'].size-data.start_offset
    data.lenth = BlockLenthList[data.start_offset:BlockCount]
    data.Pdm_Name = BlockNameList[data.start_offset:BlockCount]

    return data

# ~~~~~~~~~~~~~~~~~~~ main area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _Gen_PDM_XML():

    df = ReadDemExcel(__Platform_excel_name,__PDM_List_Sheet)
    print('read excel success')
    
    __Block_Name_Col_Start = 2 #从PDM_DEM_ADMIN开始
    # for idx in BlockUserList:
        # if idx == 'DEM':
            # __Block_Name_Col_Start = __Block_Name_Col_Start +1
    
    ProcessArxml.ProcessArxml(__PDM_ARXML_FILE_PATH, __PDM_DATA_TYPE_ARXML_FILE_PATH, df)
   
    print('\nSuccess done\n')

if __name__ == '__main__':
    argc = len(sys.argv)
    if argc < 5:
        print("Error found!!!!Please input correct parameters")
    else :
        __Platform_excel_name = sys.argv[1]
        __PDM_List_Sheet = sys.argv[2]
        __PDM_ARXML_FILE_PATH = sys.argv[3]
        __PDM_DATA_TYPE_ARXML_FILE_PATH = sys.argv[4]
    _Gen_PDM_XML()


