/**
 * @file pdm_cfg_dataitem_config.cpp
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
/// @file pdm_cfg_dataitem_config.cpp
/// @brief pdm_cfg_dataitem_handling
/// @details This file is intended to define define array to hold the customer 
///          configuration of data items.
//----------------------------------------------------------------------------

#ifdef __cplusplus
extern "C"
{
#endif

#ifdef __cplusplus
}
#endif

#include "iPdm/iPdm_CoreNvmBswAdapter.hpp"
#include "pdm_cfg/pdm_cfg_BswAdapter.h"
#include "pdm_cfg/pdm_cfg.h"
// PRQA S 2642, 4649 EOF
namespace iPdm
{
    /// struct array to hold the customer specific configuration of iPdm data items
    /// g_ipdmTotalBlocksNumber_u8
    IPDM_CUSBLOCKCFG_ST const iPdm_CusBlockCfg_ast[] =
    {   
replace Did start
        {
            replace_Did_BlockID, //BlockID  
            RamReplace_Did_BlockID, //address of ram block
            iPdm_ReadWriteType_replace,
            LengthReplace_Did_BlockID, // length of ram block bytes 
        },
replace Did end
        replace Did here
replace Dem start
        {
            replace_Dem_BlockID, //BlockID  
            RamReplace_Dem_BlockID, //address of ram block
            iPdm_ReadWriteType_replace,
            LengthReplace_Dem_BlockID, // length of ram block bytes
        },
replace Dem end
        replace Dem here
    };

}


void SchMLockResume(void)
{

}


void SchMLockSuspend(void)
{
        
}