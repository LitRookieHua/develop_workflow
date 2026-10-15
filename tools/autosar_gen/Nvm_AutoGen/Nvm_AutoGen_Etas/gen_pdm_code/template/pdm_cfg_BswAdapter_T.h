/**
 * @file pdm_cfg_BswAdapter.h
 * @brief 
 * @version 1.0
 * @date replace_time
 * 
 * @author Xuanhe.Fang (Xuanhe.Fang@imotion.ai)
 * @copyright Copyright @2025 iMotion Automotive Technology (Suzhou) Co., Ltd.
 * 
 */
//=============================================================================
//  P R O J E C T   I N F O R M A T I O N
//-----------------------------------------------------------------------------
//  Project Name: idc
//  Target system(s): tda4
//  Compiler(s):ARM
//=============================================================================

//=============================================================================
/// @file ov_pdm_BswAdapter.h
/// @brief This file contains customer specific extension declaration or features of NVM BSW.
/// @details This file contains customer specific extension declaration or features of NVM BSW.
/// - Ram Block
//=============================================================================

#ifndef PDM_CFG_BSWADAPTER_H
#define PDM_CFG_BSWADAPTER_H

#include "Std_Types.h"
#include "NvM_Cfg.h"
#include "pdm_cfg.h"

/// @brief External declaration of customer specific Ram blocks and init callbacks


#ifdef __cplusplus
extern "C"
{
#endif
//extern RAM block buffer
pdm_extern item start
extern unsigned char sasaRAMarrayName_Ram[sasalenth];
pdm_extern item end
pdm_extern replace here   


//extern ROM block buffer
/*ROM BLOCK Begin
extern "C" CONST UB ROMarrayName_Default;
ROM BLOCK End*/
#ifdef __cplusplus
}
#endif

#endif
