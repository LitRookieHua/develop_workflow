//=============================================================================
//  P R O J E C T   I N F O R M A T I O N
//-----------------------------------------------------------------------------
//  Project Name: idc
//  Target system(s): tda4
//  Compiler(s):ARM
//=============================================================================

#ifndef PDM_CFG_H
#define PDM_CFG_H

#include "pdm_cfg/pdm_cfg_dataitem_config.h"

#define NVM_CFG_NR_BLOCKS (replace_NVM_CFG_NR_BLOCKS)

replace_NvMConf_NvMBlockDescriptor

    // now configuring NVM length
    /// sizeof(Dem_Cfg_AdminDataType)  sizeof(Dem_Cfg_PrimaryEntryType) sizeof(Dem_Cfg_StatusDataType)
    /// sizeof(Dem_Cfg_AgingDataType)
    replace_NVM_CFG_NV_BLOCK_LENGTH

/** Acquire a global lock, including interrupts deactivated on the local core */
#define SchM_Enter_zxPdm() SchMLockSuspend()

/** release a global lock*/
#define SchM_Exit_zxPdm() SchMLockResume()

/** CoreId for pdm must be fixed w. core 1 */
#define zxPdmGetCoreID() 1

#endif /*PDM_CFG_H*/
