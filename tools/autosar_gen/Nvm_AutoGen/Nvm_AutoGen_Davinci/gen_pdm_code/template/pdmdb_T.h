/*################################################################################
# Automatically-generated file. Do not edit!
################################################################################*/
#ifndef _PDM_DB_H_INCLUDED_
#define _PDM_DB_H_INCLUDED_



#define PDM_DATA_ITEM_DESCRIPTOR(PdmId, RamLength, RamAddr)    {NvMConf_NvMBlockDescriptor_NvM_SWC_ ## PdmId, RamLength, (uint8 *)RamAddr},//PRQA S 1039

#define PDM_DATA_ITEM_COUNT         (sasaDataItemCountU)   //Define the Item count in PC Folder

//define pc data item //PRQA S 1039 
#define PDM_DATA_BASE                           \pdm_cfgTbl replace here
pdm_cfgTbl item start
    PDM_DATA_ITEM_DESCRIPTOR( sasaBLOCK_NAME, sasaNVM_BLOCK_LenthNum_DATA_LENGTH, sasaBlockName_Ram)\
pdm_cfgTbl item end    


#ifdef __cplusplus
extern "C"
{
#endif
//extern RAM block buffer
pdm_extern item start
extern unsigned char sasaRAMarrayName_Ram[sasalenth];
pdm_extern item end
pdm_extern replace here   


// extern ROM block buffer
/*ROM BLOCK Begin
extern "C" CONST UB ROMarrayName_Default;
ROM BLOCK End*/
#ifdef __cplusplus
}
#endif

#endif
