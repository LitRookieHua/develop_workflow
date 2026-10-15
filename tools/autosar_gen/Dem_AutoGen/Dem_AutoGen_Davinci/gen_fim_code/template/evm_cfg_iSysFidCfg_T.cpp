/**
 * @file evm_cfg_iSysFidCfg.cpp
 * @brief
 * @version excel_version
 * @date Year-Mon-Day Hour:Minute:Second
 *
 * @author Xuanhe.Fang (Xuanhe.Fang@imotion.ai)
 * @copyright Copyright ©2013-2021 iMotion Automotive Technology (Suzhou) Co., Ltd.
 *
 */
//=============================================================================
//  C O P Y R I G H T
//-----------------------------------------------------------------------------
//  Copyright (c) by iMotion AI. All rights reserved.
//=============================================================================
#include "evm_cfg/evm_cfg_interfaces.hpp"

namespace evm
{
/// List of EventIds reported only by the CPF_cfg : CPF_cfg_runnable component.
const zos::uint16_t evmcfg_EventToMixedFidTable_tau16[EvmCfg_Max_Number_Event_cu16] = {
dsmcfg_EventToMixedFidTable item start
    EventToMixedFid_index_replace,    // replace_event_name
dsmcfg_EventToMixedFidTable item end
dsmcfg_EventToMixedFidTable replace here 

};

/// List of EventIds reported only by the CPF_param_cfg : CPF_param_cfg_runnable component.
const zos::uint8_t evm_cfg_EventToMixedFidGroup_taau8[EvmCfg_Max_Number_EventToMixedFID_Group_cu16][EvmCfg_Max_Number_FID_AlignedUint8_cu16] = {
EventToMixedFidGroup_index_replace
};

const zos::uint8_t evm_cfg_FimfidDefault_tau8[EvmPf_FidsSize_cu8] = {
FimfidDefault_replace
};

} // end namespace evm
