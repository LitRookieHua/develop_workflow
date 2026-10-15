/**
 * @file SRU_crm_RteServices.h
 * @brief 
 * @version 1.0
 * @date 2026-10-13 11:40:24.474801
 * 
 * @author Xuanhe.Fang (Xuanhe.Fang@imotion.ai)
 * @copyright Copyright @2025 iMotion Automotive Technology (Suzhou) Co., Ltd.
 * 
 */
/*################################################################################
# Automatically-generated file. Do not edit!
################################################################################*/
#ifndef _SRU_CRM_RTESERVICES_H_
#define _SRU_CRM_RTESERVICES_H_

#ifdef __cplusplus
extern "C"
{
#endif

#ifdef __cplusplus
}
#endif
#include "sources/utility/typeLib/App_TypeDefine.h"
#include "sources/comps/SRU_CRM/pc/PDM/pdm_service.h"
#include "sources/comps/SRU_CRM/pc/time_service/time_service.h"
#include "sources\bsw\_oem_source_pc\BSW\_Common\Std_Types.h"

/////////////////////////////////////////////////////////////////////////////
//
//time_service
//

// NAME       : RTE_CALL_TIMESERVICE_GET_TIMESTAMP
// ARGUMENT   : pTimeStamp -- PTR_SYS_TIME_STAMP
// RETURN     : none
// REMARK     :
//extern VOID Rte_Call_TimeService_GetTimeStamp(SYS_TIME_STAMP * const pTimeStamp);
#define RTE_CALL_TIMESERVICE_GET_TIMESTAMP    sru_crm::Rte_Call_TimeService_GetTimeStamp

// NAME       : RTE_CALL_TIMESERVICE_START_TIMING
// ARGUMENT   : pTimeSpan -- PTR_SYS_TIME_SPAN
// RETURN     : none
// REMARK     :
//extern VOID Rte_Call_TimeService_StartTiming(SYS_TIME_SPAN * const pTimeSpan);
#define RET_CALL_TIMESERVICE_START_TIMING     sru_crm::Rte_Call_TimeService_StartTiming

// NAME       : RET_CALL_TIMESERVICE_GET_TIMESPAN
// ARGUMENT   : pTimeSpan -- PTR_SYS_TIME_SPAN
// RETURN     : none
// REMARK     :
//extern VOID Rte_Call_TimeService_GetTimeSpan(SYS_TIME_SPAN * const pTimeSpan);
#define RET_CALL_TIMESERVICE_GET_TIMESPAN     sru_crm::Rte_Call_TimeService_GetTimeSpan

// NAME       : RET_CALL_TIMESERVICE_GET_RANDOM
// ARGUMENT   : pRand -- UL *
// RETURN     : none
// REMARK     : pRand is the UL buffer for the random number
//extern VOID Rte_Call_TimeService_GetRandom(ULONG * const pRand);
#define RET_CALL_TIMESERVICE_GET_RANDOM     sru_crm::Rte_Call_TimeService_GetRandom
//
/////////////////////////////////////////////////////////////////////////////
//Pdm service

//platform data items:
//pc
//replace pc item data


#define PDM_Z001_FUNCTIONCONFIGURATION           ( 0U)
#define PDM_Z002_ECUSERIALNUMBER           ( 1U)
#define PDM_Z003_VIN           ( 2U)
#define PDM_Z004_FINGERPRINT           ( 3U)
#define PDM_Z005_INTERNALCODING           ( 4U)
#define PDM_Z006_TOUCHSIGNAL           ( 5U)
#define PDM_Z007_SECURELOG           ( 6U)
#define PDM_Z008_ECURESETNUMBER           ( 7U)
#define PDM_Z009_CALIBRATIONMODE           ( 8U)
#define PDM_Z010_UPDATETRIEDCOUNTER           ( 9U)
#define PDM_Z011_CHECKSUCCESSCOUNTER           ( 10U)
#define PDM_Z012_E2EENABLE           ( 11U)
#define PDM_Z013_DATETIMEBLOCK           ( 12U)
#define PDM_Z014_MTOC           ( 13U)
#define PDM_Z015_PROGRAMMINGDATE           ( 14U)
#define PDM_Z016_MANUFACTORYMODE           ( 15U)
#define PDM_Z017_VARIANTCODING           ( 16U)
#define PDM_Z018_VEHICLEPROJECTCODE           ( 17U)
#define PDM_Z019_DTCSETTINGCONTROLSTATE           ( 18U)
#define PDM_Z020_VEHICLEPOSITIONINFORMATION           ( 19U)
#define PDM_Z021_PKIINFORMATION           ( 20U)
#define PDM_Z022_CAMERACALIBRATIONSTATUS           ( 21U)
#define PDM_Z023_OFFLINECALIBRATION           ( 22U)
#define PDM_Z024_AFTERSALESYNAMICCALIBRATION           ( 23U)
#define PDM_Z025_DYNAMICSELFCALIBRATION           ( 24U)
#define PDM_Z026_AVMCALIBRATIONSTATUS           ( 25U)
#define PDM_Z027_AVMDYNAMICCALIBRATION           ( 26U)
#define PDM_Z028_AVMFRONTCAMERAOFFLINECALIBRATION           ( 27U)
#define PDM_Z029_AVMBACKCAMERAOFFLINECALIBRATION           ( 28U)
#define PDM_Z030_AVMLEFTCAMERAOFFLINECALIBRATION           ( 29U)
#define PDM_Z031_AVMRIGHTCAMERAOFFLINECALIBRATION           ( 30U)
#define PDM_Z032_AVMFRONT120CAMERAOFFLINECALIBRATION           ( 31U)
#define PDM_Z033_SWT           ( 32U)
#define PDM_Z034_DATETIMEBLOCK           ( 33U)
#define PDM_Z035_SSHENABLEDISABLE           ( 34U)
#define PDM_Z036_SECURITYFAILEDCOUNTERAPP           ( 35U)
#define PDM_Z037_SECURITYFAILEDCOUNTERBOOT           ( 36U)
#define PDM_Z038_FUSASWITCH           ( 37U)   


//cc
//replace cc item data

//data item length
//replace pc item length


#define PDM_Z001_FUNCTIONCONFIGURATION_LENGTH          20U
#define PDM_Z002_ECUSERIALNUMBER_LENGTH          45U
#define PDM_Z003_VIN_LENGTH          17U
#define PDM_Z004_FINGERPRINT_LENGTH          10U
#define PDM_Z005_INTERNALCODING_LENGTH          200U
#define PDM_Z006_TOUCHSIGNAL_LENGTH          4U
#define PDM_Z007_SECURELOG_LENGTH          160U
#define PDM_Z008_ECURESETNUMBER_LENGTH          1U
#define PDM_Z009_CALIBRATIONMODE_LENGTH          1U
#define PDM_Z010_UPDATETRIEDCOUNTER_LENGTH          2U
#define PDM_Z011_CHECKSUCCESSCOUNTER_LENGTH          2U
#define PDM_Z012_E2EENABLE_LENGTH          1U
#define PDM_Z013_DATETIMEBLOCK_LENGTH          8U
#define PDM_Z014_MTOC_LENGTH          17U
#define PDM_Z015_PROGRAMMINGDATE_LENGTH          4U
#define PDM_Z016_MANUFACTORYMODE_LENGTH          1U
#define PDM_Z017_VARIANTCODING_LENGTH          10U
#define PDM_Z018_VEHICLEPROJECTCODE_LENGTH          2U
#define PDM_Z019_DTCSETTINGCONTROLSTATE_LENGTH          40U
#define PDM_Z020_VEHICLEPOSITIONINFORMATION_LENGTH          1U
#define PDM_Z021_PKIINFORMATION_LENGTH          46U
#define PDM_Z022_CAMERACALIBRATIONSTATUS_LENGTH          32U
#define PDM_Z023_OFFLINECALIBRATION_LENGTH          70U
#define PDM_Z024_AFTERSALESYNAMICCALIBRATION_LENGTH          70U
#define PDM_Z025_DYNAMICSELFCALIBRATION_LENGTH          70U
#define PDM_Z026_AVMCALIBRATIONSTATUS_LENGTH          4U
#define PDM_Z027_AVMDYNAMICCALIBRATION_LENGTH          28U
#define PDM_Z028_AVMFRONTCAMERAOFFLINECALIBRATION_LENGTH          6U
#define PDM_Z029_AVMBACKCAMERAOFFLINECALIBRATION_LENGTH          6U
#define PDM_Z030_AVMLEFTCAMERAOFFLINECALIBRATION_LENGTH          6U
#define PDM_Z031_AVMRIGHTCAMERAOFFLINECALIBRATION_LENGTH          6U
#define PDM_Z032_AVMFRONT120CAMERAOFFLINECALIBRATION_LENGTH          6U
#define PDM_Z033_SWT_LENGTH          16U
#define PDM_Z034_DATETIMEBLOCK_LENGTH          8U
#define PDM_Z035_SSHENABLEDISABLE_LENGTH          1U
#define PDM_Z036_SECURITYFAILEDCOUNTERAPP_LENGTH          1U
#define PDM_Z037_SECURITYFAILEDCOUNTERBOOT_LENGTH          1U
#define PDM_Z038_FUSASWITCH_LENGTH          4U   

//cc
//replace cc item length


// NAME       : RTE_CALL_PDMSERVICE_READ
// ARGUMENT   : uwItemIndex -- UW, data item
//              pDest -- VOID *, destination buffer
//              uwReadBufferLen -- Item data length
//              pResult -- PDM_REQ_RESULT_TYPE *, result buffer
// RETURN     : Std_ReturnType
// REMARK     : synchronous result function, get the value of the data item from mirror RAM
//extern APP_RESULT Rte_Call_Pdm_Read(UW uwItemIndex, VOID * pDest, UW uwReadBufferLen, PDM_REQ_RESULT_TYPE * pResult);
#define RTE_CALL_PDMSERVICE_READ               sru_crm::Rte_Call_Pdm_Read

// NAME       : RTE_CALL_PDMSERVICE_RELOAD_READ
// ARGUMENT   : uwItemIndex -- UW, data item
//              pDest -- VOID *, destination buffer
//              uwReadBufferLen -- Item data length
//              pResult -- PDM_REQ_RESULT_TYPE *, result buffer
// RETURN     : Std_ReturnType
// REMARK     : synchronous result function, get the value of the data item from actual Nvm
//extern APP_RESULT Rte_Call_Pdm_ReloadRead(UW uwItemIndex, VOID * pDest, UW uwReadBufferLen, PDM_REQ_RESULT_TYPE * pResult);
#define RTE_CALL_PDMSERVICE_RELOAD_READ       sru_crm::Rte_Call_Pdm_ReloadRead

// NAME       : RTE_CALL_PDMSERVICE_WRITE
// ARGUMENT   : uwItemIndex -- UW, data item
//              pSrc -- VOID *, source buffer
//              uwWriteBufferLen -- Item data length
//              pResult -- PDM_REQ_RESULT_TYPE *, result buffer
// RETURN     : Std_ReturnType
// REMARK     : asynchronous result function, store the value to the data item in mirror RAM and actual Nvm
//extern APP_RESULT Rte_Call_Pdm_Write(UW uwItemIndex, VOID * pSrc, UW uwWriteBufferLen, PDM_REQ_RESULT_TYPE * pResult);
#define RTE_CALL_PDMSERVICE_WRITE            sru_crm::Rte_Call_Pdm_Write

// NAME       : RTE_CALL_PDMSERVICE_WRITEPOWEROFF
// ARGUMENT   : uwItemIndex -- UW, data item
//              pSrc -- VOID *, source buffer
//              uwWriteBufferLen -- Item data length
// RETURN     : Std_ReturnType
// REMARK     : asynchronous result function, store the value to the data item in mirror RAM,write to the nvm when power off
//extern APP_RESULT Rte_Call_Pdm_WritePowerOff(UW uwItemIndex, VOID * pSrc, UW uwWriteBufferLen, PDM_REQ_RESULT_TYPE * pResult);
#define RTE_CALL_PDMSERVICE_WRITEPOWEROFF    sru_crm::Rte_Call_Pdm_WritePowerOff

// NAME       : RTE_CALL_PDMSERVICE_IMMEDIATE_WRITE
// ARGUMENT   : uwItemIndex -- UW, data item
//              pSrc -- VOID *, source buffer
//              uwWriteBufferLen -- Item data length
//              pResult -- PDM_REQ_RESULT_TYPE *, result buffer
// RETURN     : Std_ReturnType
// REMARK     : synchronous result function, store the value to the data item in mirror RAM and actual Nvm
//extern APP_RESULT Rte_Call_Pdm_ImmediateWrite(UW uwItemIndex, VOID * pSrc, UW uwWriteBufferLen, PDM_REQ_RESULT_TYPE * pResult);
#define RTE_CALL_PDMSERVICE_IMMEDIATE_WRITE  sru_crm::Rte_Call_Pdm_ImmediateWrite

// NAME       : RTE_CALL_PDMSERVICE_ABCM_READ
// ARGUMENT   : uwItemIndex -- UW, data item
//              pDest -- VOID *, destination buffer
//              uwReadBufferLen -- Item data length
//              pResult -- PDM_REQ_RESULT_TYPE *, result buffer
// RETURN     : Std_ReturnType
// REMARK     : get value from dflash
extern Std_ReturnType Rte_Call_Pdm_ABCMRead(UW uwItemIndex, VOID * pDest, UW uwReadBufferLen, PDM_REQ_RESULT_TYPE * pResult);
#define RTE_CALL_PDMSERVICE_ABCM_READ    sru_crm::Rte_Call_Pdm_ABCMRead

// NAME       : RTE_CALL_PDMSERVICE_ABCM_WRITE
// ARGUMENT   : uwItemIndex -- UW, data item
//              pSrc -- VOID *, source buffer
//              uwWriteBufferLen -- Item data length
//              pResult -- PDM_REQ_RESULT_TYPE *, result buffer
// RETURN     : Std_ReturnType
// REMARK     : store the value to the dflash
extern Std_ReturnType Rte_Call_Pdm_ABCMWrite(UW uwItemIndex, VOID * pSrc, UW uwWriteBufferLen, PDM_REQ_RESULT_TYPE * pResult);
#define RTE_CALL_PDMSERVICE_ABCM_WRITE    sru_crm::Rte_Call_Pdm_ABCMWrite

/////////////////////////////////////////////////////////////////////////////

#endif
