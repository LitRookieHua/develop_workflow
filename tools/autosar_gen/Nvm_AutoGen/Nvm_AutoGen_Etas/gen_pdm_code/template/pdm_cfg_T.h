/**
 * @file pdm_cfg.h
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

#ifndef PDM_CFG_H
#define PDM_CFG_H

extern volatile unsigned char g_nvmCfgBlocks_u8;
/* number of iPdm data item(which are supported by iPdm interfaces per imo_com or API) */
extern volatile unsigned char g_ipdmTotalBlocksNumber_u8;

replace_DateTimeBlock_Alias


replace_NvMConf_NvMBlockDescriptor


// now configuring NVM length  
/// sizeof(Dem_Cfg_AdminDataType)  sizeof(Dem_Cfg_PrimaryEntryType) sizeof(Dem_Cfg_StatusDataType) sizeof(Dem_Cfg_AgingDataType)
replace_NVM_CFG_NV_BLOCK_LENGTH
/* Macro to enable/disable fallback feature */
#define ZXPDM_FALLBACK_MECHANISM_ENABLE_FOR_ALL_BLOCKS 1U /* fall back mechanism will be enabled for all */
                                                          /*zxPdm blocks */
#define ZXPDM_FALLBACK_MECHANISM_MIXED_CONFIGURATION 2U   /* fallback mechanism will be enabled/disabled per */
                                                          /* block through configuration in  */
                                                          /* zxPdm_CusBlockCfg_ast array with parameter */
                                                          /* m_fallback_enable_b */
#define ZXPDM_FALLBACK_MECHANISM ZXPDM_FALLBACK_MECHANISM_MIXED_CONFIGURATION

/* Macro to configure ECU power type */
#define ZXPDM_ECU_TERMINAL_TYPE_KL_15 1U /* ECU is ignition powered */
#define ZXPDM_ECU_TERMINAL_TYPE_KL_30 2U /* ECU is battery powered */
#define ZXPDM_ECU_TERMINAL_TYPE ZXPDM_ECU_TERMINAL_TYPE_KL_15

/* member variable for the maximal write retrigger times. It must be range in 0...250. Default value is 50. */
#define ZXPDM_CUS_MAX_WRITE_RETRY_COUNTER 50U

#define MAIN_DOMAIN_PDM_BLOCK_NUM 1u
#define MAIN_DOMAIN_PDM_LIST_SEPARATOR 0xAA
#define MAIN_DOMAIN_PDM_LIST_BUF_MAX_LEN 2012U


/** Acquire a global lock, including interrupts deactivated on the local core */
#define SchM_Enter_zxPdm()  SchMLockSuspend()

/** release a global lock*/
#define SchM_Exit_zxPdm()   SchMLockResume()

/** CoreId for pdm must be fixed w. core 1 */
#define zxPdmGetCoreID() 1

#endif /*PDM_CFG_H*/
