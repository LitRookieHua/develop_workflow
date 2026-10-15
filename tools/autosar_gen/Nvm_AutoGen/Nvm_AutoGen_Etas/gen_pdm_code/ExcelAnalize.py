#! /usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'yian'

import pandas

''' ~~~~~ note ~~~~~~~~~~~~~~~~
a 'self' must be one of the argument somehow...
~~~~~~~~~~~~~~~~~~~~~~~~~~~ '''
class ExcelAnalize:

    def __init__(self):
        self.df = ''
        
    def read(self, exlSrc, Sheet):
        self.df = pandas.read_excel(exlSrc, sheet_name = Sheet, engine='openpyxl', keep_default_na = False)
        
    def get_col_name_by_idx(self, iCol1, iCol2 = 0):
        if iCol2 > iCol1:
            return self.df.columns[iCol1 : (iCol2 + 1)]
        else:
            return self.df.columns[iCol1]
    
    def get_row_name_by_idx(self, ColName):
        return self.df[ColName].tolist()
    
    def get_cell_by_idx(self, iRow, iCol):
        return self.df.iat[iRow, iCol]
        
    def get_count_by_col_name(self, ColName):
        return self.df[ColName].size
        
    def get_idx_at_col_val_by_col_name(self, ColName, strVal):
        d = self.df[ColName].to_dict()
        return list(d.keys())[list(d.values()).index(strVal)]
        
    def get_slice_by_col_idx(self, iCol1, iCol2 = 0):
        if iCol2 > iCol1:
            return self.df.iloc[:, iCol1 : (iCol2 + 1)]
        else:
            return self.df.iloc[:, iCol1]
            
    def get_line_by_col_idx(self, iRow, iCol1, iCol2 = 0):
        if iCol2 > iCol1:
            return self.df.iloc[iRow, iCol1 : (iCol2 + 1)]
        else:
            return self.df.iloc[iRow, iCol1]
    
    def get_dataframe(self):
        return self.df
        
    def print_dataframe(self):
        print(self.df)


# ~~~~~~~~~~~~~~~~~~~ test area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
r'''
import sys

__Reation_List_Path = r"C:\Users\ChenYC\Desktop\wtf\Geely_VF11_NET_E2EInValid_Concept_v1.3.xlsx"
__Reation_List_Sheet = r"0_DemEvent_for_Traditional"

if __name__ == '__main__':

    print('at least')
    E = ExcelAnalize()
    
    E.read(__Reation_List_Path, r'0_DemEvent_for_Traditional')
    print('read done')
    
    print(E.get_col_name_by_idx(6))
    
    print(E.get_col_name_by_idx(8, 22))
    
    print(E.get_cell_by_idx(1, 6))
    
    stay = input()

sys.exit(0)

'''

