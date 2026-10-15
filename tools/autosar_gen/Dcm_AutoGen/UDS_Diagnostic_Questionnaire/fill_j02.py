# -*- coding: utf-8 -*-
"""根据客户问卷 FAWVW_UDS_Diagnostic_Questionnaire_MFK_DK3_J02_V001_260920.xlsx
填充 J02/UDS_Diagnostic_Questionnaire_J02.xlsx 的全部 sheet。

不改模板结构,只填数据。
映射约定:
- Service/DID/RID 会话列: Default=App 0x01/Boot 0x01, Programming=Boot 0x02, Extended=App 0x03/Boot 0x03
- 安全等级 (√N): √0 -> Locked/App/Boot 全 Y; √1 -> App Unlocked; √2 -> Boot Unlocked
- iMotion Unlocked: 客户未定义, 全 N
- 09C3 RID 客户标注"示例RID不需要实现", 不填入
"""
import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation, DataValidationList

FILE = 'J02/UDS_Diagnostic_Questionnaire_J02.xlsx'
wb = openpyxl.load_workbook(FILE)

# ============================== General ==============================
G = {
    'Communication Protocol': 'CANFD',
    'CAN Baudrate': '500000bps',
    'CP_CANFDBaudrate': '2000000bps',
    'CP_CANFDTxMaxDataLength': 'TX_DL = 64, CANFD',
    'CP_CANFDBitSamplePoint': '70%',
    'CP_CANFDSyncJumpWidth': '10%',
    'Physical Request CAN ID': '0x754',
    'Functional Request CAN ID': '0x7DF',
    'Physical Response CAN ID': '0x75C',
    'DoIP Edge Node Address': '0x0730',
    'Physical Request DoIP ID': '0x0754',
    'Functional Request DoIP ID': '0xE400',
    'Remote Tester Logical Address': '0x0E81',
    'IP': '192.168.0.5',
    'P2Server': '50ms', 'P2*Server': '5000ms', 'ΔP2': '150ms',
    'S3Server': '5000ms', 'P2Client': '200ms', 'P2*Client': '5150ms',
    'P3Client_Phys': '400ms', 'P3Client_Func': '400ms', 'S3Client': '2000ms',
    'PNRC0x21_Repetition_Time': '200ms',
    'PNRC0x21_CompletionTimeout': '60000ms',
    'PNRC0x78_CompletionTimeout': '100000ms',
    'P6Client': '2500ms', 'P6*Client': '7450ms', 'ΔP6': '2450ms',
    'N_Ar': '1000ms', 'N_As': '1000ms', 'N_Br': '60ms', 'N_Bs': '1000ms',
    'N_Cr': '1000ms', 'N_Cs': '60ms',
    'CP_StMin (Application software)': '10ms',
    'CP_StMin (Boot software)': '1ms',
    'CP_BlockSize': '0',
    'A_DoIP_Ctrl': '2s', 'A_DoIP_Announce_Wait': '0-500ms',
    'A_DoIP_Announce_Interval': '500ms', 'A_DoIP_Announce_Num': '3',
    'A_DoIP_Diagnostic_Message': '2000ms',
    'T_TCP_General_Inactivity': '5min', 'T_TCP_Initial_Inactivity': '2s',
    'T_TCP_Alive_Check': '500ms', 'A_Processing_Time': '2s',
    'A_Vehicle_Discovery_Timer': '5s',
}
ws = wb['General']
filled = 0
for r in range(3, ws.max_row + 1):
    item = ws.cell(row=r, column=3).value
    if item in G:
        ws.cell(row=r, column=4).value = G[item]
        filled += 1
missing = set(G) - {ws.cell(row=r, column=3).value for r in range(3, ws.max_row + 1)}
print(f'General: filled {filled}, unmatched items: {missing or "none"}')

# ============================== Service List ==============================
# (sid, name, sub, nrc, sprmib, addr, default, prog, ext, locked, app, boot)
S = [
    ('0x10', 'DiagnosticSessionControl', '0x01（Default Session）', '12>13>22>7E', 'Y', 'P/F', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y'),
    ('0x10', 'DiagnosticSessionControl', '0x02（Programming Session）', '12>13>22>7E', 'Y', 'P/F', 'N', 'Y', 'Y', 'Y', 'Y', 'Y'),
    ('0x10', 'DiagnosticSessionControl', '0x03（Extended Diagnostic Session）', '12>13>22>7E', 'Y', 'P/F', 'Y', 'N', 'Y', 'Y', 'Y', 'Y'),
    ('0x11', 'ECUReset', '0x01（ECU Hardware Reset）', '12>13>22', 'Y', 'P', 'N', 'Y', 'Y', 'N', 'Y', 'Y'),
    ('0x11', 'ECUReset', '0x02（ECU KL15 Reset）', '12>13>22', 'Y', 'P', 'N', 'Y', 'Y', 'N', 'Y', 'Y'),
    ('0x14', 'ClearDiagnosticInformation', '/', '13>22>31>72', 'N', 'P/F', 'Y', 'N', 'Y', 'Y', 'Y', 'Y'),
    ('0x19', 'ReadDTCInformation', '0x01（ReportNumberOfDTCByStatusMask）', '12>13>31', 'N', 'P', 'Y', 'N', 'Y', 'Y', 'Y', 'Y'),
    ('0x19', 'ReadDTCInformation', '0x02（ReportDTCByStatusMask）', '12>13>31', 'N', 'P', 'Y', 'N', 'Y', 'Y', 'Y', 'Y'),
    ('0x19', 'ReadDTCInformation', '0x04（ReportDTCSnapshotRecordByDTCNumber）', '12>13>31', 'N', 'P', 'Y', 'N', 'Y', 'Y', 'Y', 'Y'),
    ('0x19', 'ReadDTCInformation', '0x06（ReportDTCExtendedDataRecordByDTCNumber）', '12>13>31', 'N', 'P', 'Y', 'N', 'Y', 'Y', 'Y', 'Y'),
    ('0x19', 'ReadDTCInformation', '0x0A（ReportSupportedDTC）', '12>13>31', 'N', 'P', 'Y', 'N', 'Y', 'Y', 'Y', 'Y'),
    ('0x22', 'ReadDataByIdentifier', '/', '13>14>22>31>33', 'N', 'P', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y'),
    ('0x27', 'SecurityAccess', '0x03（Application）', '12>13>22>24>35>36>37', 'N', 'P', 'N', 'N', 'Y', 'N', 'Y', 'N'),
    ('0x27', 'SecurityAccess', '0x04（Application）', '12>13>22>24>35>36>37', 'N', 'P', 'N', 'N', 'Y', 'N', 'Y', 'N'),
    ('0x27', 'SecurityAccess', '0x11（Bootloader）', '12>13>22>24>35>36>37', 'N', 'P', 'N', 'Y', 'N', 'N', 'N', 'Y'),
    ('0x27', 'SecurityAccess', '0x12（Bootloader）', '12>13>22>24>35>36>37', 'N', 'P', 'N', 'Y', 'N', 'N', 'N', 'Y'),
    ('0x28', 'CommunicationControl', '0x00（EnableRxAndTx）', '12>13>22>31', 'Y', 'P/F', 'N', 'N', 'Y', 'Y', 'Y', 'Y'),
    ('0x28', 'CommunicationControl', '0x01（EnableRxAndDisableTx）', '12>13>22>31', 'Y', 'P/F', 'N', 'N', 'Y', 'Y', 'Y', 'Y'),
    ('0x28', 'CommunicationControl', '0x03（DisableRxAndTx）', '12>13>22>31', 'Y', 'P/F', 'N', 'N', 'Y', 'Y', 'Y', 'Y'),
    ('0x2E', 'WriteDataByIdentifier', '/', '13>22>31>33>72', 'N', 'P', 'N', 'Y', 'Y', 'N', 'Y', 'Y'),
    ('0x31', 'RoutineControl', '0x01（StartRoutine）', '12>13>22>24>31>33>72', 'N', 'P/F', 'N', 'Y', 'Y', 'N', 'Y', 'Y'),
    ('0x31', 'RoutineControl', '0x02（StopRoutine）', '12>13>22>24>31>33>72', 'N', 'P/F', 'N', 'N', 'Y', 'N', 'Y', 'N'),
    ('0x31', 'RoutineControl', '0x03（RequestRoutineResult）', '12>13>22>24>31>33>72', 'N', 'P/F', 'N', 'N', 'Y', 'N', 'Y', 'N'),
    ('0x36', 'TransferData', '/', '13>24>31>71>72>73', 'N', 'P', 'N', 'Y', 'N', 'N', 'N', 'Y'),
    ('0x37', 'RequestTransferExit', '/', '13>24>72', 'N', 'P', 'N', 'Y', 'N', 'N', 'N', 'Y'),
    ('0x38', 'RequestFileTransfer', '/', '13>22>31>33>70', 'N', 'P', 'N', 'Y', 'N', 'N', 'N', 'Y'),
    ('0x3E', 'TesterPresent', '0x00（TesterPresent）', '12>13', 'Y', 'P/F', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y'),
    ('0x85', 'ControlDTCSetting', '0x01（DTCLoggingOn）', '12>13>22>31', 'Y', 'P/F', 'N', 'N', 'Y', 'Y', 'Y', 'Y'),
    ('0x85', 'ControlDTCSetting', '0x02（DTCLoggingOff）', '12>13>22>31', 'Y', 'P/F', 'N', 'N', 'Y', 'Y', 'Y', 'Y'),
]
ws = wb['Service List']
for i, row in enumerate(S):
    r = 3 + i
    vals = list(row[:12]) + ['N', '', '']  # + iMotion, JIRA, Remark
    for cidx, v in enumerate(vals, 1):
        if v != '':
            ws.cell(row=r, column=cidx).value = v
print(f'Service List: {len(S)} rows')

# ============================== DID List ==============================
# (did, name, s22, s2e, dtype, dsource, dval, dlen, dsess, psess, esess, locked, app, boot, remark)
D = [
    ('0xF19E', 'ECU Variant ID', 'Yes', 'No', 'ASCII', 'VersionDid', 'EV_MFKIM', 26, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', 'ASAM ODX File Identifier <EV_>; 与问卷 ECU_Variant_ID 一致'),
    ('0xF1A2', 'ODX File Version', 'Yes', 'No', 'ASCII', 'VersionDid', '001', 3, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', '绑定诊断问卷版本号 V000-V999'),
    ('0xF187', 'VW Spare Part Number', 'Yes', 'No', 'ASCII', 'NvmDid', 'JP2980653  ', 11, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', 'VNR front number; 存储于Flash'),
    ('0xF15B', 'Fingerprint And Programming Date', 'Yes', 'No', 'BCD', 'NvmDid', '', 10, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', '数据来源于F15A'),
    ('0xF189', 'VW Application Software Version Number', 'Yes', 'No', 'ASCII', 'VersionDid', '', 4, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', '开发阶段DXXX/临时TXXX/量产阶段, 每次正式发版需变更'),
    ('0xF191', 'VW ECU Hardware Number', 'Yes', 'No', 'ASCII', 'VersionDid', 'JP2980653  ', 11, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', ''),
    ('0xF197', 'VW System Name', 'Yes', 'No', 'ASCII', 'VersionDid', 'MFK          ', 13, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', 'DK1/2/2F system 命名规则见客户问卷'),
    ('0xF1A3', 'VW ECU Hardware Version Number', 'Yes', 'No', 'ASCII', 'VersionDid', 'H01', 3, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', '随硬件版本变更'),
    ('0xF1D5', 'FDS_project_information', 'Yes', 'No', 'Hex', 'VersionDid', '', 5, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', 'bit7 密钥类型(0研发/1生产); byte2-5 FDS project ID 00 00 00 60'),
    ('0xF186', 'Active Diagnostic Session', 'Yes', 'No', 'Hex', 'DynamicDid', '', 1, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', '软件内部值; 0x01/0x02/0x03'),
    ('0xF190', 'VIN', 'Yes', 'Yes', 'ASCII', 'NvmDid', '-----------------', 17, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:Yes', 'Y', 'Y', 'Y', 'EEPROM; 默认17个0x2D; $2E仅扩展会话Level1'),
    ('0xF15A', 'Fingerprint', 'No', 'Yes', 'BCD', 'NvmDid', '', 9, '22:No 2E:No', '22:No 2E:Yes', '22:No 2E:No', 'N', 'N', 'Y', '编程时写入; Year/Month/Day+VW Device/Importer/Workshop Number'),
    ('0xF18C', 'ECU Serial Number', 'Yes', 'No', 'ASCII', 'NvmDid', '', 20, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', '结构: SupplierCode(3B)+PartCode(9B)+Batch(1B)+PartNo(4B)+Date(3B); 供应商代码待客户提供'),
    ('0x0249', 'Programming Hash', 'Yes', 'No', 'Hex', 'VersionDid', '', 32, '22:Yes 2E:No', '22:No 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', 'P-IVD; 软件内部值'),
    ('0x2EE2', 'Component_ZDC_ID', 'Yes', 'Yes', 'ASCII', 'NvmDid', '', 11, '22:Yes 2E:No', '22:No 2E:No', '22:Yes 2E:Yes', 'Y', 'Y', 'Y', '整车下线写入; $2E仅扩展会话Level1'),
    ('0xF192', 'System Supplier ECU Hardware Number', 'Yes', 'No', 'ASCII', 'VersionDid', 'IJH1', 4, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', ''),
    ('0xF193', 'System Supplier ECU Hardware Version Number', 'Yes', 'No', 'ASCII', 'VersionDid', 'H01 ', 4, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', ''),
    ('0xF194', 'System Supplier ECU Software Number', 'Yes', 'No', 'ASCII', 'VersionDid', 'IJS1', 4, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', ''),
    ('0xF195', 'System Supplier ECU Software Version Number', 'Yes', 'No', 'ASCII', 'VersionDid', '', 48, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', 'dataset内部版本号'),
    ('0xF180', 'VW BootSoftware Identification', 'Yes', 'No', 'ASCII', 'VersionDid', '0001', 4, '22:Yes 2E:No', '22:Yes 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', ''),
    ('0xF1DF', 'ECU Programming Information', 'Yes', 'No', 'Hex', 'DynamicDid', '', 1, '22:Yes 2E:No', '22:No 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', 'bit7-4 Reprogrammability; bit3-0 ProgramConsistency; 软件内部值'),
    ('0xF1E9', 'Type Certifacation Software Version', 'Yes', 'No', 'ASCII', 'VersionDid', '1000', 4, '22:Yes 2E:No', '22:No 2E:No', '22:Yes 2E:No', 'Y', 'Y', 'Y', ''),
]
ws = wb['DID List']
for i, row in enumerate(D):
    r = 3 + i
    vals = list(row[:14]) + ['N', '', row[14]]  # + iMotion, JIRA, remark
    for cidx, v in enumerate(vals, 1):
        if v != '':
            ws.cell(row=r, column=cidx).value = v
# 修正下拉范围: 会话组合 I-K, 安全等级 Y/N L-O
ws.data_validations = DataValidationList()
for formula, cells in [
    ('"Yes,No"', 'C3:D32'), ('"Hex,ASCII,BCD"', 'E3:E32'),
    ('"NvmDid,VersionDid,DynamicDid"', 'F3:F32'),
    ('"22:Yes 2E:No,22:Yes 2E:Yes,22:No 2E:No,22:No 2E:Yes"', 'I3:K32'),
    ('"Y,N"', 'L3:O32'),
]:
    dv = DataValidation(type='list', formula1=formula, allow_blank=True, errorStyle='warning')
    ws.add_data_validation(dv)
    dv.add(cells)
print(f'DID List: {len(D)} rows')

# ============================== RID List ==============================
# (rid, name, ctrl, req, resp, dsess, psess, esess, locked, app, boot, remark)
R = [
    ('0xFF01', 'Check Programming Dependencies', '0x01（StartRoutine）', '/', '1B: 0x00 correct / 0x01 incorrect / 0x02 SW-HW mismatch', 'N', 'Y', 'N', 'N', 'N', 'Y', ''),
    ('0x0203', 'Check Programming Preconditions', '0x01（StartRoutine）', '/', '1B bitmap: bit0 VehicleSpeed<3km/h, bit1 EngineSpeed=0, bit2 IgnitionOn, bit3 Voltage 9-16V, bit4 SelectorLever P, bit5 ElectricDrive, bit6-7 Reserved', 'N', 'N', 'Y', 'Y', 'Y', 'Y', ''),
    ('0x0202', 'Check Memory (checksum)', '0x01（StartRoutine）', '68B: Checksum and Signature', '1B: 0x00 correct / 0x01 incorrect / 0x02-0x7F Debug', 'N', 'Y', 'N', 'N', 'N', 'Y', ''),
    ('0xC010', 'Start Update', '0x01（StartRoutine）', '3B: MemoryAddress', 'RoutineResult(1B) + RoutineStatus(1B)', 'N', 'Y', 'N', 'N', 'N', 'Y', ''),
    ('0xC010', 'Start Update', '0x03（RequestRoutineResults）', '/', 'RoutineResult(1B) + RoutineStatus(1B) + Progress(1B: 0x00-0x64)', 'N', 'Y', 'N', 'N', 'N', 'Y', ''),
    ('0xC00E', 'Check Update', '0x01（StartRoutine）', '/', 'RoutineResult(1B) + RoutineStatus(1B)', 'N', 'N', 'Y', 'Y', 'Y', 'Y', ''),
    ('0x8510', 'EOL Calibration', '0x01（StartRoutine）', '1B: 0x00 120deg Calibration', 'routine status(1B) + calib start status(1B: bit0 SOC, bit1 内参, bit2 摄像头通信, bit3 摄像头连接, bit4 前舱盖, bit5 近光, bit6 远光, bit7 转向灯)', 'N', 'N', 'Y', 'N', 'Y', 'N', 'Pre-Condition检查项见Response; Limited Time 100ms'),
    ('0x8510', 'EOL Calibration', '0x03（RequestRoutineResults）', '/', 'routine status(1B) + calib result(1B) + calib progress(1B: 0-100%)', 'N', 'N', 'Y', 'N', 'Y', 'N', 'Limited Time 60s'),
    ('0x8511', 'Aftermarket Calibration', '0x01（StartRoutine）', '1B: 0x00 120deg Calibration', 'routine status(1B) + calib start status(1B: bit0 SOC, bit1 内参, bit2 摄像头通信, bit3 摄像头连接, bit4 前舱盖, bit5 近光, bit6 远光, bit7 转向灯)', 'N', 'N', 'Y', 'N', 'Y', 'N', ''),
    ('0x8511', 'Aftermarket Calibration', '0x03（RequestRoutineResults）', '/', 'routine status(1B) + calib result(1B) + calib progress(1B: 0-100%)', 'N', 'N', 'Y', 'N', 'Y', 'N', 'Limited Time 5min'),
]
ws = wb['RID List']
for i, row in enumerate(R):
    r = 3 + i
    vals = list(row[:11]) + ['N', '', row[11]]  # + iMotion, JIRA, remark
    for cidx, v in enumerate(vals, 1):
        if v != '':
            ws.cell(row=r, column=cidx).value = v
print(f'RID List: {len(R)} rows (09C3示例RID未填入)')

# ============================== NVM List ==============================
# (index, name, length, readall, writeall, priority, user, init, type, did, remark)
N = [
    (1, 'DidF190', 17, 'N', 'N', '', 'Dcm', '2D2D2D2D2D2D2D2D2D2D2D2D2D2D2D2D2D2D', '', '0xF190', 'VIN (EEPROM); 默认17个0x2D; 推导自客户问卷'),
    (2, 'DidF18C', 20, 'N', 'N', '', 'Dcm', '', '', '0xF18C', 'ECU Serial Number; 供应商代码待客户提供; 推导自客户问卷'),
    (3, 'DidF15A', 9, 'N', 'N', '', 'Dcm', '', '', '0xF15A', 'Fingerprint; 编程时写入; 推导自客户问卷'),
    (4, 'DidF15B', 10, 'N', 'N', '', 'Dcm', '', '', '0xF15B', 'Fingerprint And Programming Date; 数据来源于F15A; 推导自客户问卷'),
    (5, 'Did2EE2', 11, 'N', 'N', '', 'Dcm', '', '', '0x2EE2', 'Component ZDC ID; 整车下线写入; 推导自客户问卷'),
]
ws = wb['NVM List']
for i, row in enumerate(N):
    r = 3 + i
    for cidx, v in enumerate(row, 1):
        if v != '':
            ws.cell(row=r, column=cidx).value = v
print(f'NVM List: {len(N)} rows (推导自NvmDid类DID)')

# ============================== History ==============================
ws = wb['History']
ws['A3'] = 'V1.0'
ws['B3'] = '2026-09-23'
ws['C3'] = 'Hua Yao / 姚华'
ws['D3'] = ('Initialized from FAWVW_UDS_Diagnostic_Questionnaire_MFK_DK3_J02_V001_260920: '
            'General(48) + Service(14 svc/29 rows) + DID(22) + RID(7 RIDs/10 rows, 09C3示例未含) + NVM(5)')
print('History: V1.0 row added')

wb.save(FILE)
print('saved:', FILE)
