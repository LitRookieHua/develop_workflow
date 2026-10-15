#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import pandas
import process_arxml
import merge_excel

DEM_REF_Merge_Excel_Path = r"Merger_Total_Event_Temporary.csv"
DEM_REF_Merge_Sheet = r"Total_Event"

DEM_REF_E2E_excel_name = r"..\IDC_E2EInValid_V1.0.xlsx"

class ARXML_Need_Data:
    def __init__(self):
        self.num = ''
        self.DTC = ''
        self.Event_Name = ''
        self.Priority = ''
        self.Debounce_Algorithm = ''
        self.Debounce_Pass = ''
        self.Debounce_Failed = ''
        self.Aging = ''
        self.EnableCondition = ''
        self.start_offset = ''

def ReadDemExcel(input_file):

    df = pandas.read_csv(input_file)
    
    data = ARXML_Need_Data()
    data.start_offset = 0


    data.num = df['DEM Index'].size-data.start_offset
    data.DTC = df['DTC Name'][data.start_offset:]
    data.Event_Name = df['Event Name'][data.start_offset:]
    data.Priority = df['Prority'][data.start_offset:]
    data.Debounce_Algorithm = df['Debounce Algorithm'][data.start_offset:]
    data.Debounce_Pass = df['Debounce Pass'][data.start_offset:]
    data.Debounce_Failed = df['Debounce Falied'][data.start_offset:]
    data.Aging = df['Aging'][data.start_offset:]
    data.EnableCondition = df['Enable Condition Group(ECG)'][data.start_offset:]
    return data

def is_exist(path):
    return os.path.isdir(path)

def ensure_exist(path):
    if not is_exist(path):
        os.makedirs(path)

def Gen_Dem_xml(ref_E2E_excel, arxml_path):

    merge_excel.Merge_Sheet(ref_E2E_excel, __FID_PCBA_Type_name,DEM_REF_Merge_Excel_Path)

    print(f'Merge "{DEM_REF_Merge_Excel_Path}" Successful!!!')

    df = ReadDemExcel(DEM_REF_Merge_Excel_Path)

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






















