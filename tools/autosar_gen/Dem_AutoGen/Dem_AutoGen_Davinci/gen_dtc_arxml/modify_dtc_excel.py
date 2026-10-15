#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import xlrd
import pandas
from pandas import DataFrame

def GetDTCMessage(DEM_REF_Merge_Excel_Path, DTC_Message_Csv_Path):
    df = pandas.read_csv(DEM_REF_Merge_Excel_Path)
    df = df.loc[:, ['DTC(hex)', 'DTC Name']]
    df = df.drop_duplicates()
    df = df[df["DTC(hex)"] != "N.A"]
    df = df.dropna(subset=["DTC(hex)"])
    df["DTC(dec)"] = df["DTC(hex)"].apply(lambda x: int(str(x), 16))
    df = df.sort_values(by='DTC Name').reset_index(drop=True)
    df.index.name = 'DTC Index'
    df.to_csv(DTC_Message_Csv_Path)


