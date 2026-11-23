# DemGeneral 配置表编辑规则（AI 改表权威源）

`IDC_DemGeneral_Config*.xlsx`（gen_dem_general 的输入表）不是人工填写的业务表格，而是 **AI 维护的机器可读配置**。本文档是 AI 修改该表的权威规则源；生成器 `tools/autosar_gen/Dem_AutoGen/Dem_AutoGen_Etas/gen_dem_general/gen_dem_general.py` 是硬校验兜底，但 AI 改表时应一次改对，不要靠生成器报错试错。设计背景见 [2026-11-20-dem-autogen-etas-gen-dem-general-design.md](../../docs/design/2026-11-20-dem-autogen-etas-gen-dem-general-design.md)。

## 1. 文件管理规则

- 表放在 `cpj_cmc/tools/<变体>/e2e_dem/`，命名 `IDC_DemGeneral_Config_<项目>_<版本>_<日期>.xlsx`（如 `IDC_DemGeneral_Config_CMC_RX_V3.0_20261120.xlsx`），**与 DTC 的 EVM 表（IDC_EVM_Config*）分开**，表内只含本文档的两个 sheet
- **新变体从工具内模板起步**：复制 `tools/autosar_gen/Dem_AutoGen/Dem_AutoGen_Etas/gen_dem_general/template/IDC_DemGeneral_Config_template.xlsx`（仅含两个 sheet 的表头结构，列名/顺序不可改），按 §2/§3 填行；表头勿手敲，以防列名偏差
- 编辑用 openpyxl（python 脚本放 `.tmp/`，改前先备份原文件到 `.tmp/`）；不要用会破坏其他 sheet 的整表重写方式
- 表在 mcu_app_j6 仓库内，属代码资产，commit 随需求走（格式同 MCU 仓库规则）

## 2. Sheet schema（列名逐字符一致，生成器强校验）

**`enable_condition_group`**：`No. | ItemKind | Name | Description | Status | Members`

- ItemKind 语义：**EC** = DemEnableCondition（单个使能条件，运行时 SWC 经 `Dem_SetEnableCondition` 置位）；**ECG** = DemEnableConditionGroup（使能条件组，组内 EC 全部为 true 事件才可用，事件参数经 `DemEnableConditionGroupRef` 引用组）
- **Description 仅文档用途，不进 arxml**，写人话即可；其余列全部有语义

**`extended_freeze_data`**：`No. | ItemKind | Name | DataType | Source | InternalElement | DidHex | Number | Update | Trigger | Members`

| ItemKind | 对应容器类 | 专用列 |
| --- | --- | --- |
| DATA-ELEMENT | DemDataElementClass（choice） | Source=External 用 DataType；Source=Internal 用 InternalElement |
| DID-CLASS | DemDidClass | DidHex + Members |
| FREEZE-FRAME-CLASS | DemFreezeFrameClass | Members=DidClass 名 |
| SNAPSHOT-RECORD | DemFreezeFrameRecordClass | Number/Update/Trigger，**无 Members** |
| EXTENDED-RECORD | DemExtendedDataRecordClass | Number/Update/Trigger + Members=SR 名 |
| EXTENDED-DATA-CLASS | DemExtendedDataClass | Members=EXTENDED-RECORD 名 |
| FF-RECNUM-CLASS | DemFreezeFrameRecNumClass | Members=SNAPSHOT-RECORD 名 |

- 空单元格一律留**空**，不写 "N/A"、"-"、"无" 等占位串

## 3. 取值规则（AI 填值时逐条核对）

### 3.1 通用

1. **Name 全表唯一且非空**（两个 sheet 各自内部唯一；建议同时避免与 DemGeneral 既有手工容器重名）
2. Name 即容器 SHORT-NAME，用合法 C 标识符风格（字母/数字/下划线，字母开头），与引用处逐字符一致
3. Members 为空格分隔的名字列表，**重复名字禁止**
4. 行序建议按依赖序排（被引用者在前）：DATA-ELEMENT → DID-CLASS → FREEZE-FRAME-CLASS → SNAPSHOT-RECORD → EXTENDED-RECORD → EXTENDED-DATA-CLASS → FF-RECNUM-CLASS（生成器允许乱序——先全量校验后构建，但乱序伤可读性）

### 3.2 enable_condition_group

5. EC 行 **Status 填 arxml 实值**（不是想当然的 false）——教训：EC_ACANBusNormal/EC_FRCANBusNormal 实际为 `true`，初版误填 false 造成黄金对照 diff。新增 EC 时先查现网 arxml 或与需求方确认初值
6. EC 行 Members 必须为空；ECG 行 Members 必填
7. ECG 的 Members 只能是：本 sheet 内的 EC 名，或 DemGeneral 下已存在的使能条件容器名；**引用不存在名字会在生成时 fail**（删行前先确认没有 ECG 引用它）

### 3.3 extended_freeze_data

8. DATA-ELEMENT：Source 只许 `External`/`Internal`（大小写不敏感）
   - External → DataType 只许 `UINT8`/`UINT16`/`UINT32`（外部 SR 走 OPAQUE 回调）
   - Internal → InternalElement 填 Dem 内部数据枚举（如 `DEM_OCCCTR`、`DEM_AGINGCTR_UPCNT`），DataType/InternalElement 另一列留空；此时 Members/DidHex 等列全部留空
9. DID-CLASS：DidHex 必须 `0x` 开头十六进制（如 `0x0601`）；Members 是本表 DATA-ELEMENT 名
10. SNAPSHOT-RECORD / EXTENDED-RECORD：Number 为十进制整数字符串（快照/扩展记录号，通常 `1`）；Update/Trigger 填 Dem 枚举全名（现网取值：`DEM_UPDATE_RECORD_YES`、`DEM_TRIGGER_ON_CONFIRMED`），不要缩写
11. 依赖方向硬约束（成员类型不符生成时 fail）：
    - DID-CLASS ← DATA-ELEMENT
    - FREEZE-FRAME-CLASS ← DID-CLASS
    - EXTENDED-RECORD ← DATA-ELEMENT
    - EXTENDED-DATA-CLASS ← EXTENDED-RECORD
    - FF-RECNUM-CLASS ← SNAPSHOT-RECORD
12. **手工维护容器不进表**：带额外配置的容器（如 `SR_Vehicle_Speed` 带 DemDiagnosisScaling）不在生成器管辖内，不要为"补全"而加进 sheet——加了反而会被幂等删除逻辑重建掉额外配置

## 4. 修改场景操作序列

- **新增 DID**：加 DATA-ELEMENT 行（每个数据元素一行）→ 加 DID-CLASS 行（DidHex + Members）→ 若要进快照，把 DID-CLASS 名追加到对应 FREEZE-FRAME-CLASS 行的 Members
- **新增扩展数据字段**：加 DATA-ELEMENT 行 → 把名字追加到对应 EXTENDED-RECORD 行 Members
- **新增使能条件**：加 EC 行（确认 Status 实值）→ 需要成组时加/改 ECG 行 Members
- **删除/改名容器**：先全局确认无引用（本表 Members 列 + arxml 里 `DemGeneral/<名字>` 的 VALUE-REF + gen_dem_table 子脚本的**固定名引用**：`Create_DemDTCAttributes.py` 引用 `ExtendedDataClass_DTC_Properties` / `FreezeFrame_DTC_DidSet_TypeA|B` / `DTC_Properties_FFRecNumClass`，`Create_DemEventParameter.py` 按 ECG 列引用组名）——这些固定名是隐式契约，改名等于断链
- 从 sheet 删掉的行，重跑生成器会同步删除 arxml 中对应容器（含上次生成残留的 USER_GENERATED 容器）

## 5. 改表后必做验证

1. 单跑生成器两遍：`python gen_dem_general.py <表> <arxml> true true`——第一遍 OK 后，第二遍应报删 0 建 0（或等价幂等），并对 arxml 做 diff 确认第二遍零变化
2. 容器级 diff：与改前 arxml 比对，确认变化只落在预期容器（对照脚本思路见设计文档 §3：剔除 S 属性、子容器稳定排序后逐容器比较）
3. 改了被 gen_dem_table 固定名引用的容器名时，必须跑全流程 `python dem_autogen_etas.py --repo <mcu_app_j6> --config <变体>` 验证 ISOLAR 重生成后引用不断链
4. 报告改动时列出：新增/删除/修改的行名清单，便于评审

## 6. 红线

- 不为图省事直接手改 arxml 里的受管容器——sheet 是唯一真源，手改会在下次生成时被覆盖
- 不在 EVM 表（IDC_EVM_Config*）里加这两个 sheet（历史遗留的混放已拆分，别再合回去）
- 不改 gen_dem_general.py 的校验逻辑来迁就错误表格数据——修表不修工具（与 DTC 表导入规则同理，见 [dtc-table-import.md](dtc-table-import.md)）
