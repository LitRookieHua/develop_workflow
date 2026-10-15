#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import pandas
import process_arxml
import merge_excel
import modify_dtc_excel

DEM_REF_Merge_Excel_Path = r"Merger_Total_Event_Temporary.csv"
DEM_REF_Merge_Sheet = r"Total_Event"
DTC_Message_Csv_Path = r"DTC_Message.csv"
DTC_REF_Message_Sheet = r"DTC_Message"

DEM_REF_E2E_excel_name = r"EEZI_NET_E2E.xlsx"

class ARXML_Need_Data:
    def __init__(self):
        self.num = ''
        self.DTC_Number = ''
        self.DTC_Name = ''

def ReadDemExcel(input_file):

    df = pandas.read_csv(input_file)
    
    data = ARXML_Need_Data()
    data.start_offset = 0

    data.num = df['DTC Index'].size-data.start_offset
    data.DTC_Hex_Number = df['DTC(hex)'][data.start_offset:]
    data.DTC_Dec_Number = df['DTC(dec)'][data.start_offset:]
    data.DTC_Name = df['DTC Name'][data.start_offset:]

    return data

def is_exist(path):
    return os.path.isdir(path)

def ensure_exist(path):
    if not is_exist(path):
        os.makedirs(path)

def Gen_Dem_xml(ref_E2E_excel, arxml_path):

    merge_excel.Merge_Sheet(ref_E2E_excel, __FID_PCBA_Type_name, DEM_REF_Merge_Excel_Path)

    print(f'Merge "{DEM_REF_Merge_Excel_Path}" Successful!!!')

    modify_dtc_excel.GetDTCMessage(DEM_REF_Merge_Excel_Path, DTC_Message_Csv_Path)

    print(f'Get "{DTC_Message_Csv_Path}" Successful!!!')

    df = ReadDemExcel(DTC_Message_Csv_Path)

    process_arxml.ProcessArxml(arxml_path, df)

if __name__ == '__main__':
    argc = len(sys.argv)
    if argc < 3:
        print("Error found!!!!Please input correct parameters")
    else :
        DEM_REF_E2E_excel_name = sys.argv[1]
        __FID_PCBA_Type_name = sys.argv[2]
        DEM_ARXML_FILE_PATH = sys.argv[3]

        Gen_Dem_xml(DEM_REF_E2E_excel_name,DEM_ARXML_FILE_PATH)






















