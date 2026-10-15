//=============================================================================
//  P R O J E C T   I N F O R M A T I O N
//-----------------------------------------------------------------------------
//  Project Name: idc
//  Target system(s): tda4
//  Compiler(s):ARM
//=============================================================================

//---------------------------------------------------------------------------
/// @file evm_cfg_FidCfg.hpp
//---------------------------------------------------------------------------
/// @brief ref evm internal parameter used only by evm_cfg component
//---------------------------------------------------------------------------
#ifndef EVM_CFG_FIDCFG_HPP_INCLUDED
#define EVM_CFG_FIDCFG_HPP_INCLUDED

#include <basic_types/container/vector.hpp>

namespace evm
{
const zos::uint16_t EvmCfg_Max_Number_Event_cu16 = replace_Event_MAX_Number;

const zos::uint16_t EvmCfg_Max_Number_Event_AlignedBit_cu16 = replace_Event_AlignedBit;

const zos::uint16_t EvmCfg_Max_Number_EventToMixedFID_Group_cu16 = replace_EventToMixedFidGroupNumber;

const zos::uint16_t EvmCfg_Max_Number_FID_AlignedUint8_cu16 = replace_FIDNumberAlignUINT8;
} // end namespace evm

#endif // EVM_CFG_INTERFACES_HPP_INCLUDED
