#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from TemplateFile import TemplateFile
from ExcelAnalize import ExcelAnalize
import Merge_Excel
import glob
import datetime
from time import strftime

# ~~~~~~~~~~~~~~~~~~~ config area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
FIM_REF_Merge_Excel_Path = r"Merger_Total_FID.xlsx"
ScriptPath = r"./"

''' ~~~~~ note ~~~~~~~~~~~~~~~~
column starts from 0...
~~~~~~~~~~~~~~~~~~~~~~~~~~~ '''
__Event_Name_Col_Start = 2

# ~~~~~~~~~~~~~~~~~~~ declare area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def calc_bin_val_from_list(List):
    Binstring_str = ""
    for Val in List:
        if Val == 'Y':
            Binstring_str = Binstring_str + "1"
        else:
            Binstring_str = Binstring_str + "0"
    # 当Binstring_str长度不是8的倍数，需要后面补足
    for idx in range(8 - (len(Binstring_str) % 8)):
        Binstring_str = Binstring_str + "0"
    return Binstring_str

def calc_bin_val_from_str(str, CmpStr):
    BinVal = 0
    if str == CmpStr:
        BinVal = 1
    else:
        BinVal = 0
    return BinVal

def cfg_fimcfg_gen(m_FidsSize, m_FiMFID_tau8):
    struct_member = m_FiMFID_tau8.replace("zos::uint8_t", "uint8")
    
    with open(fimcfg_idl_path, 'w') as file:
        file.write("#ifndef ZX_SYS_EVM_CFG_FIM_CFG_HPP_INCLUDED\n")
        file.write("#define ZX_SYS_EVM_CFG_FIM_CFG_HPP_INCLUDED\n")
        file.write("#include <zos_msg/common/common.idl>" + '\n')
        file.write("module evm" + '\n')
        file.write("{" + '\n')
        
        file.write("/// @brief size of FIDs list" + '\n')
        file.write("const uint8 EvmPf_FidsSize_cu8 = " + str(m_FidsSize) + ";" + '\n')
        file.write("@topic\nstruct EvmPf_FuncPermission {"+ '\n')
        file.write("    " + struct_member)
        file.write("};" + '\n')
        file.write("};" + '\n')
        file.write("#endif // ZX_SYS_EVM_CFG_FIM_CFG_HPP_INCLUDED\n")
    
def evm_cfg_FidCfg_gen(replace_Event_MAX_Number,replace_Event_AlignedBit, replace_EventToMixedFidGroupNumber,  replace_FIDNumberAlignUINT8):
    
    with open(evm_cfg_FidCfg_path, 'w') as file:
        file.write("#ifndef EVM_CFG_FIDCFG_HPP_INCLUDED" + '\n')
        file.write("#define EVM_CFG_FIDCFG_HPP_INCLUDED" + '\n')
        file.write("#include <zos_msg/common/common.idl>" + '\n')
        file.write("module evm" + '\n')
        file.write("{" + '\n')
        
        file.write("const uint16 EvmCfg_Max_Number_Event_cu16 = " + replace_Event_MAX_Number + ";" + '\n')
        file.write("const uint16 EvmCfg_Max_Number_Event_AlignedBit_cu16 = " +replace_Event_AlignedBit+ ";" + '\n')

        file.write("const uint16 EvmCfg_Max_Number_EventToMixedFID_Group_cu16 = " +replace_EventToMixedFidGroupNumber+ ";" + '\n')

        file.write("const uint16 EvmCfg_Max_Number_FID_AlignedUint8_cu16 =" + replace_FIDNumberAlignUINT8+ ";" + '\n')
        
        file.write("};" + '\n')
        file.write("#endif // EVM_CFG_FIDCFG_HPP_INCLUDED" + '\n')
    

# ~~~~~~~~~~~~~~~~~~~ main area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def Fid_Gen():

    Merge_Excel.Merge_Sheet(__FID_excel_name, __FID_PCBA_Type_name, FIM_REF_Merge_Excel_Path)

    print(f'Merge "{FIM_REF_Merge_Excel_Path}" Successful!!!')

    Fdsm_fidcfg_cpp = TemplateFile()
    Fdsm_fidcfg_h = TemplateFile()
    Fdsm_evmfids_output_pf_hpp = TemplateFile()
    Event = ExcelAnalize()

    Fdsm_fidcfg_cpp.copy(__dsm_fidcfg_cpp_T_Path, __dsm_fidcfg_cpp_Path)
    Fdsm_fidcfg_h.copy(__dsm_fidcfg_h_T_Path, __dsm_fidcfg_h_Path)
    Fdsm_evmfids_output_pf_hpp.copy(__evmfids_output_pf_hpp_T_Path, __evmfids_output_pf_hpp_Path)

    Fdsm_fidcfg_cpp.read_text(__dsm_fidcfg_cpp_Path)
    Fdsm_fidcfg_h.read_text(__dsm_fidcfg_h_Path)
    Fdsm_evmfids_output_pf_hpp.read_text(__evmfids_output_pf_hpp_Path)

    excel_name_list = glob.glob(FIM_REF_Merge_Excel_Path)
    Event.read(excel_name_list[0], "total_event")

    # 获取 __FID_Name_Col_Start FIMFID起始列
    event_df = Event.get_specified_line(0)
    column_list = list(event_df)
    column_len = len(list(event_df))
    for header in range(0,column_len):
        name = column_list[header]
        if name.startswith('FiMFID_'):
            __FID_Name_Col_Start = header
            break

    # 获取 __FID_Name_Col_End FIMFID结束列
    for header in range(column_len-1, 0, -1):
        name = column_list[header]
        if name.startswith('FiMFID_'):
            __FID_Name_Col_End = header
            break

    FIDNum = __FID_Name_Col_End - __FID_Name_Col_Start + 1
    Fdsm_fidcfg_h.text_replace_to_all(r'replace_EVM_CFG_FIMFID_NUMBER', str(FIDNum))
    Fdsm_evmfids_output_pf_hpp.text_replace_to_all(r"m_FidsSize_replace",str(FIDNum)+"u")
    
    m_FidsSize = FIDNum


    if (FIDNum % 8 ) != 0:
        FIDNum_AlignUINT8 = (int)(FIDNum / 8) + 1
    else :
        FIDNum_AlignUINT8 = (int)(FIDNum / 8)

    Fdsm_fidcfg_h.text_replace_to_all(r'replace_FIDNumberAlignUINT8', str(FIDNum_AlignUINT8))
    replace_FIDNumberAlignUINT8 = str(FIDNum_AlignUINT8)
    EventCount = Event.get_count_by_col_name(r'Event Name')
    Fdsm_fidcfg_h.text_replace_to_all(r'replace_Event_MAX_Number', str(EventCount - 1)) # 1--避开E2E表中L2 N.A
    replace_Event_MAX_Number = str(EventCount - 1)
    Fdsm_fidcfg_h.text_replace_to_all(r'replace_Event_AlignedBit', str(int(EventCount/8)))
    replace_Event_AlignedBit = str(int(EventCount/8))
    
    # 获取FIMFID默认值
    FimfidDefault_tau8 = ""
    m_FiMFID_tau8 = ""
    idx = 0
    FimfidDefaultValue_List = Event.get_line_by_col_idx(0, __FID_Name_Col_Start, __FID_Name_Col_End)
    for FimfidDefaultValue in FimfidDefaultValue_List:
        if FimfidDefaultValue == "T":
            FimfidDefault_tau8 += "    0x01,   /// " + str(idx) + "--" + str(FimfidDefaultValue_List.index[idx] + "\n")
            m_FiMFID_tau8 += "    zos::uint8_t m_" + str(FimfidDefaultValue_List.index[idx]) + ";    /// " + str(idx) + "\n"
        else:
            FimfidDefault_tau8 += "    0x00,   /// " + str(idx) + "--" + str(FimfidDefaultValue_List.index[idx] + "\n")
            m_FiMFID_tau8 += "    zos::uint8_t m_" + str(FimfidDefaultValue_List.index[idx]) + ";    /// " + str(idx) + "\n"
        idx += 1
    Fdsm_fidcfg_cpp.text_replace_to_all(r"FimfidDefault_replace",FimfidDefault_tau8)
    Fdsm_evmfids_output_pf_hpp.text_replace_to_all(r"m_FiMFID_replace",m_FiMFID_tau8)
    
    cfg_fimcfg_gen(m_FidsSize, m_FiMFID_tau8)

    EventFIDBinValList = []
    for RIdx in range(1, EventCount): # 1--避开E2E表中L2 N.A
        FIDVarList = Event.get_line_by_col_idx(RIdx, __FID_Name_Col_Start, __FID_Name_Col_End)
        EventFIDBinValList.append(calc_bin_val_from_list(FIDVarList))
    BinValListCopy = EventFIDBinValList.copy()
    BinValListCopy.sort()

    FIDBinValList = []
    FIDBinValList.append(BinValListCopy[0])
    for Val in BinValListCopy:
        if Val != FIDBinValList[-1]:
            FIDBinValList.append(Val)

    Fdsm_fidcfg_h.text_replace_to_all(r'replace_EventToMixedFidGroupNumber', str(len(FIDBinValList)))
    replace_EventToMixedFidGroupNumber = str(len(FIDBinValList))
    PickUp = Fdsm_fidcfg_cpp.text_pick(r'dsmcfg_EventToMixedFidTable item start', r'dsmcfg_EventToMixedFidTable item end')
    ModifyText = ''
    
    evm_cfg_FidCfg_gen(replace_Event_MAX_Number,replace_Event_AlignedBit, replace_EventToMixedFidGroupNumber,  replace_FIDNumberAlignUINT8)

    idx = 1 # 1--避开E2E表中L2 N.A
    for EventCoordBinVal in EventFIDBinValList:
        ModifyText = Fdsm_fidcfg_cpp.text_append_line(ModifyText, PickUp)
        ModifyText = Fdsm_fidcfg_cpp.text_replace_to_text(r'EventToMixedFid_index_replace', str(FIDBinValList.index(EventCoordBinVal)), ModifyText)
        ModifyText = Fdsm_fidcfg_cpp.text_replace_to_text(r'replace_event_name', str(idx) + '--' + Event.get_cell_by_idx(idx, __Event_Name_Col_Start), ModifyText)
        idx = idx + 1

    Fdsm_fidcfg_cpp.text_replace_to_all(r'dsmcfg_EventToMixedFidTable replace here', ModifyText)
    Fdsm_fidcfg_cpp.text_delete(r'dsmcfg_EventToMixedFidTable item start', r'dsmcfg_EventToMixedFidTable item end')

    index = 0
    ModifyText = ''
    for val in FIDBinValList:
        num = 0
        tempstr = ""
        EventToMixedFidGroup = ""
        for i in range(FIDNum_AlignUINT8):
            EventToMixedFidGroup += hex(int(val[num : num + 8], 2)) + ","
            num += 8
        tempstr = "    /* %d */   { %s },   \n" % (index, EventToMixedFidGroup)
        index += 1
        ModifyText += tempstr

    time = datetime.datetime.now()
    Fdsm_fidcfg_cpp.text_replace_to_all(r'Year-Mon-Day Hour:Minute:Second', "%s-%s-%s %s:%s:%s"%(str(time.year), str(time.month),str(time.day),str(time.hour),str(time.minute),str(time.second)))
    Fdsm_fidcfg_cpp.text_replace_to_all(r'excel_version', "%s"%(os.path.basename(__FID_excel_name)))

    Fdsm_fidcfg_cpp.text_replace_to_all(r'EventToMixedFidGroup_index_replace', ModifyText)

    Fdsm_fidcfg_cpp.update_file(__dsm_fidcfg_cpp_Path)
    Fdsm_fidcfg_h.update_file(__dsm_fidcfg_h_Path)
    Fdsm_evmfids_output_pf_hpp.update_file(__evmfids_output_pf_hpp_Path)

    print("FIM Code Successful!!!")


if __name__ == '__main__':
    argc = len(sys.argv)
    if argc < 6:
       print("Error found!!!!Please input correct parameters")
    else :
        ScriptPath = sys.argv[1]
        __FID_excel_name =  sys.argv[2]
        __FID_PCBA_Type_name = sys.argv[3]
        __dsm_fidcfg_cpp_Path = sys.argv[4] + r"/evm_cfg_iSysFidCfg.cpp"
        __dsm_fidcfg_h_Path =  sys.argv[5] + r"/evm_cfg_FidCfg.hpp"
        __evmfids_output_pf_hpp_Path =  sys.argv[6] + r"/zx_sys_evm_cfg_fimcfg.hpp"
        fimcfg_idl_path = sys.argv[7] + r"/zx_sys_evm_cfg_fimcfg.idl"
        evm_cfg_FidCfg_path = sys.argv[7] + r"/evm_cfg_FidCfg.idl"

        __dsm_fidcfg_cpp_T_Path = ScriptPath + r"/template/evm_cfg_iSysFidCfg_T.cpp"
        __dsm_fidcfg_h_T_Path = ScriptPath + r"/template/evm_cfg_FidCfg_T.hpp"
        __evmfids_output_pf_hpp_T_Path = ScriptPath + r"/template/zx_sys_evm_cfg_fimcfg_T.hpp"

        Fid_Gen()


