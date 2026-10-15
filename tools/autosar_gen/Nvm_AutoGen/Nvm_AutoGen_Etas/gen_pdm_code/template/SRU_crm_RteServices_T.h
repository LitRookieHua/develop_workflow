/**
 * @file SRU_crm_RteServices.h
 * @brief 
 * @version 1.0
 * @date replace_time
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
Pdm_RtePcTbl item start
#define sasaPdmNam           ( sasaidxU)
Pdm_RtePcTbl item end
Pdm_RtePcTbl replace here   


//cc
//replace cc item data

//data item length
//replace pc item length
Pdm_RteLenTbl item start
#define sasaPdmLenth          sasalenthU
Pdm_RteLenTbl item end
Pdm_RteLenTbl replace here   

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
