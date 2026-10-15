/**
 * @file pdm_cfg_BswAdapter.c
 * @brief 
 * @version 1.0
 * @date replace_time
 * 
 * @author Xuanhe.Fang (Xuanhe.Fang@imotion.ai)
 * @copyright Copyright @2025 iMotion Automotive Technology (Suzhou) Co., Ltd.
 * 
 */
//=============================================================================
//  C O P Y R I G H T
//-----------------------------------------------------------------------------
/// @copyright (c) 2023 iMotion AI. All rights reserved.
//
//  The reproduction, distribution and utilization of this file as
//  well as the communication of its contents to others without express
//  authorization is prohibited. Offenders will be held liable for the
//  payment of damages. All rights reserved in the event of the grant
//  of a patent, utility model or design.
//=============================================================================
//  P R O J E C T   I N F O R M A T I O N
//-----------------------------------------------------------------------------
//     Projectname: iMotion Driving Computer
//  Target systems: X86_64, ARM, IMP-X7+
//       Compilers: ISO C++11 compliant
//=============================================================================
//  I N I T I A L   A U T H O R   I D E N T I T Y
//-----------------------------------------------------------------------------
//  Name: ZX
//  Department: EA2
//=============================================================================

#include "pdm_cfg/pdm_cfg_BswAdapter.h"
#include "pdm_cfg/pdm_cfg.h"

///    PRQA S 2410 : This object is array type
///    This warning cannot be fixed since this size is generated from BCT and we cannot use cpp alternatives as this is c file

/// @brief Definition of customer specific Ram blocks

volatile unsigned char g_nvmCfgBlocks_u8 = replace_NVM_CFG_NR_BLOCKS;  
/* number of iPdm data item(which are supported by iPdm interfaces per imo_com or API) */
volatile unsigned char g_ipdmTotalBlocksNumber_u8 = replace_IPDM_CUS_TOTAL_NUMBER_OF_DATA_BLOCKS;


pdm_Ram item start
unsigned char sasaRAMblockname_Ram[sasasalenth] = 
{
    sasavalue
};
pdm_Ram item end
pdm_Ram replace here 

//NvM ROM Block default value
/*NvM ROM block Begin
CONST UB ROMblockname_Default = 
{
    value
};
NvM ROM Block End*/
