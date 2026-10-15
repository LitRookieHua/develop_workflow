#! /usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'yian'

import os
import re

from shutil import copyfile

''' ~~~~~ note ~~~~~~~~~~~~~~~~
a 'self' must be one of the argument somehow...
~~~~~~~~~~~~~~~~~~~~~~~~~~~ '''
class TemplateFile:

    def __init__(self):
        self.File = ''
        self.AllText = ''
        
    def copy(self, fSrc, fDest):
        copyfile(fSrc, fDest)
    
    def read_text(self, fName):
        self.File = open(fName, 'r')
        self.AllText = self.File.read()
        self.File.close()
    
    def text_replace_to_all(self, strOld, strNew):
        self.AllText = self.AllText.replace(strOld, strNew)
        
    def text_replace_to_text(self, strOld, strNew, strText):
        return strText.replace(strOld, strNew)
        
    def text_pick(self, StartExpress, EndExpress):      
        s = re.search(StartExpress + '\n' + r'([\s\S\n\r\t\v\f]+)' + '\n' + EndExpress, self.AllText)
        if s:
            return s.group(1)
        else:
            return ''

    def text_delete(self, StartExpress, EndExpress):      
        self.AllText = re.sub(StartExpress + r'[\s\S\n\r\t\v\f]+' + EndExpress, '', self.AllText)
        
    def text_append_line(self, strText, strAppend):
        strRet = strText + '\n' + strAppend
        return strRet
    
    def text_nest(self, strText):
        strRet =  '\t' + strText
        return strRet
        
    def text_pick_replace_complex(self, StartExpress, EndExpress, strOld, strNewList, strReplaceHere):
        strPickup = self.text_pick(StartExpress, EndExpress)
        strModifyText = ''
        for strNew in strNewList:
            strModifyText = self.text_append_line(strModifyText, strPickup)
            strModifyText = self.text_replace_to_text(strOld, strNew, strModifyText)
        self.text_replace_to_all(strReplaceHere, strModifyText)
        self.text_delete(StartExpress, EndExpress)
    
    def update_file(self, fName):
        self.File = open(fName, 'w')
        self.File.write(self.AllText)
        self.File.close()
        
    def tohex(self, iCol1,iCol2):
        strdefval = ''
        idx = 1
        limit_num = 8
                
        if iCol1 == 'DEFAULT-00' :     #将默认值为‘DEFAULT’写入为0x00
            for num in range(iCol2):
                strdefval = strdefval + '0x00u' + ','
                if idx%limit_num == 0  and idx >= limit_num:
                    strdefval = strdefval + '\n\t'
                idx = idx + 1
        elif iCol1 == 'DEFAULT-FF' :     #将默认值为‘DEFAULT’写入为0xFF
            for num in range(iCol2):
                strdefval = strdefval + '0xFFu' + ','
                if idx%limit_num == 0  and idx >= limit_num:
                    strdefval = strdefval + '\n\t'
                idx = idx + 1
        elif iCol1 == 'DEFAULT-46' :     #将默认值为‘DEFAULT’写入为0x46
            for num in range(iCol2):
                strdefval = strdefval + '0x46u' + ','
                if idx%limit_num == 0  and idx >= limit_num:
                    strdefval = strdefval + '\n\t'
                idx = idx + 1
        elif iCol1 == 'DEFAULT-20' :     #将默认值为‘DEFAULT’写入为0x20
            for num in range(iCol2):
                strdefval = strdefval + '0x20u' + ','
                if idx%limit_num == 0  and idx >= limit_num:
                    strdefval = strdefval + '\n\t'
                idx = idx + 1        
        else:                       #将非默认值为‘DEFAULT’写入
            if type(iCol1) == int and iCol2 > 0:
                if iCol1 < 0xFF :
                    return ('0x' + str(iCol1) + 'u')
                else:
                    return -1
            if len(iCol1.split(' ')) != iCol2:
                return -1
            for num in iCol1.split(' ') :
                strdefval = strdefval + '0x' + num + 'u,'
                if idx%limit_num == 0  and idx >= limit_num:
                    strdefval = strdefval + '\n\t'
                idx = idx + 1
                
        if (idx-1)%limit_num == 0:          #删除多余换行符
            strdefval = strdefval.rstrip('/\n/\t')
        strdefval = strdefval.rstrip(',')  #删除最后的','
        return strdefval
        


# ~~~~~~~~~~~~~~~~~~~ test area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
r'''
#import sys

__MapPbCfg_T_Path = r"C:\Users\ChenYC\Desktop\wtf\DemEvent_Map_PBcfg_T.h"
__MapPbCfg_Path = r"C:\Users\ChenYC\Desktop\wtf\test\DemEvent_Map_PBcfg.h"
__PickUp = ''
__ModifyText = ''

if __name__ == '__main__':

    print('at least')
    F = TemplateFile()
    
    F.copy(__MapPbCfg_T_Path, __MapPbCfg_Path)
    print('copy done')
    
    F.read_text(__MapPbCfg_Path)
    print('open done')
    
    F.text_replace_to_all(r'sasaAfidShutAllFuncIdx', r'0U')
    print('replace all done')
    
    __PickUp = F.text_pick(r'variant_ref_bit_pos item start', r'variant_ref_bit_pos item end')
    print('pick done')
    
    __ModifyText = F.text_replace_to_text(r'sasaFunc', r'AEB', __PickUp)
    print('replace pick done')
    
    __ModifyText = F.text_append_line(__ModifyText, __PickUp)
    print('append done')
    
    __ModifyText = F.text_replace_to_text(r'sasaFunc', r'ELK', __ModifyText)
    print('replace pick done')
    
    __ModifyText = F.text_nest( __ModifyText)
    print('nest done')
    
    F.text_replace_to_all(r'variant_ref_bit_pos replace here', __ModifyText)
    print('replace here done')
    
    F.text_delete(r'variant_ref_bit_pos item start', r'variant_ref_bit_pos item end')
    print('delete done')
    
    # print(F.AllText)
    
    F.update_file(__MapPbCfg_Path)
    print('close done')
    
    stay = input()

sys.exit(0)
'''


