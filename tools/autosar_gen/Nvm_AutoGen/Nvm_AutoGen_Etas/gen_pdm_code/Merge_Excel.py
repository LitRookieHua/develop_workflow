#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import xlrd
import pandas
from pandas import DataFrame


merger_excel_name = r"Merger_Total_Event_Temporary.xlsx"

Platform_Event_group_name = r"01_Platform_Event"
SCFM_Event_group_name = r"02_SCFM_Event"
Failsafe_Event_group_name = r"03_Failsafe_Event"
E2E_Event_group_name = r"02_Dataset_E2E"

def Merge_Sheet(plateform_excel,e2e_excel):
    #读取数据
    Platform_excel = pandas.read_excel(plateform_excel,None)#读入数据文件
    E2e_excel = pandas.read_excel(e2e_excel, None)  # 读入数据文件

    Sheet_keys = [Platform_Event_group_name,SCFM_Event_group_name,Failsafe_Event_group_name]
    #第三步：数据合并
    iris_concat = pandas.DataFrame()
    for i in Sheet_keys:
        iris1 = Platform_excel[i]
        iris_concat = pandas.concat([iris_concat,iris1])

    iris1 = E2e_excel[E2E_Event_group_name]
    iris_concat = pandas.concat([iris_concat, iris1])

    iris_concat.to_excel(merger_excel_name,sheet_name='Total_Event')#数据保存路径


def Delete_Excel(excel):
    if os.path.exists(excel):  # 如果文件存在
        # 删除文件，可使用以下两种方法。
        os.remove(excel)
        # os.unlink(path)
    else:
        print('no such file:%s' % excel)  # 则返回文件不存在