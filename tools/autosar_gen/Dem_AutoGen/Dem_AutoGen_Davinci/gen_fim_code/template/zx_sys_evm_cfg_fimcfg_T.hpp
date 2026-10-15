/*

 * @Date: 2023-05-31 17:43:57
 * @LastEditors: ZX\Xuanhe.Fang Xuanhe.Fang@imotion.ai
 * @LastEditTime: 2023-06-01 09:59:17
 * @FilePath: \idc_mcu_app\tools\Gen_evm_FiMFID_Script\template\evmfids_output_pf_T.hpp
 * @Description:
 */
//=============================================================================
//  C O P Y R I G H T
//-----------------------------------------------------------------------------
//  Copyright (c) by iMotion AI. All rights reserved.
//=============================================================================
//  D E S C R I P T I O N
//-----------------------------------------------------------------------------
//  Project Name: IDC2
//  Target System(s):
//  Compiler(s):
//=============================================================================
//  I N I T I A L   A U T H O R   I D E N T I T Y
//-----------------------------------------------------------------------------
//  Name:
//=============================================================================

#ifndef ZX_SYS_EVM_CFG_FIM_CFG_HPP_INCLUDED
#define ZX_SYS_EVM_CFG_FIM_CFG_HPP_INCLUDED

#include <basic_types/container/vector.hpp>
#include <basic_types/container/array.hpp>
#include <basic_types/types.hpp>
#include <basic_types/serialization/serialization.hpp>

namespace evm
{

/// @brief size of FIDs list
const zos::uint8_t EvmPf_FidsSize_cu8 = m_FidsSize_replace;

/// @brief Function permission needed in the software components
/// Valid states: true (1):  permission granted to run the function,
///               false (0) : permission not granted to run the function
struct EvmPf_FuncPermission
{
m_FiMFID_replace
};

} // namespace evm
#endif
