#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import xlrd
import pandas
from pandas import DataFrame

Platform_Event_group_name = r"PF_Event"
E2E_Event_group_name = r"CPJ_Event_Net"

def Merge_Sheet(in_e2e_excel,pcba_type_name,out_merger_excel_name):
    #读取数据
    E2e_excel = pandas.read_excel(in_e2e_excel, None)  # 读入数据文件

    Sheet_keys = [Platform_Event_group_name,pcba_type_name,E2E_Event_group_name]
    #第三步：数据合并
    iris_concat = pandas.DataFrame()
    for i in Sheet_keys:
        iris1 = E2e_excel[i]
        iris_concat = pandas.concat([iris_concat,iris1],ignore_index=True)

    iris_concat = iris_concat.loc[:, ['DEM Index', 'Event Name','DTC(hex)', 'DTC Name','Prority', 'Debounce Algorithm','Debounce Falied', 'Debounce Pass','Aging', 'Enable Condition Group(ECG)']]
    iris_concat = iris_concat.drop([0])
    iris_concat.to_csv(out_merger_excel_name)#数据保存路径


def Delete_Excel(excel):
    if os.path.exists(excel):  # 如果文件存在
        # 删除文件，可使用以下两种方法。
        os.remove(excel)
        # os.unlink(path)
    else:
        print('no such file:%s' % excel)  # 则返回文件不存在