# Dem_AutoGen_Etas gen_dem_general 功能设计（DemGeneral 侧容器自动化生成）

- 日期：2026-11-20
- 关联：CMCRXJ6B-42/43（RX Dem 快照 DID 集 + 扩展数据单记录）、IDC310GAC-7747（工具沉淀线）
- 状态：已实现并验证（黄金对照收敛 + 全流程实跑 + 幂等回归）
- 代码：`tools/autosar_gen/Dem_AutoGen/Dem_AutoGen_Etas/gen_dem_general/gen_dem_general.py` + `dem_autogen_etas.py` 接线

## 1. 背景与动机

CMCRXJ6B-42/43 案例交付时，快照/扩展数据涉及的 **DemGeneral 侧容器**（30 个 SR 数据元素、3 个 DidClass、FreezeFrame TypeA/B、快照/扩展记录、ExtendedDataClass、FFRecNumClass、6 组使能条件/组）全部靠**手工编辑 arxml**。而现有 gen_dem_table 只生成 DemConfigSet 侧（事件/DTC/属性），其子脚本按固定名引用这些 DemGeneral 容器：

- `Create_DemDTCAttributes.py:160-180`：引用 `ExtendedDataClass_DTC_Properties`、`FreezeFrame_DTC_DidSet_TypeA|TypeB`、`DTC_Properties_FFRecNumClass`
- `Create_DemEventParameter.py:220`：按 ECG 列引用 `<ECG 组名>` 的 `DemEnableConditionGroupRef`

换项目/换需求时这套手工容器要重做一遍。本功能从输入 Excel 的两个专用 sheet 读参数自动生成，sheet 即唯一真源。

## 2. 方案总览

### 2.1 功能开关（configs）

`configs/common.yaml` 新增（项目 yaml 按需覆盖）：

```yaml
gen_dem_general:
  enabled: true
  enable_condition_group: true   # 使能条件/组子开关
  extended_freeze_data: true     # 快照/扩展数据栈子开关
```

`dem_autogen_etas.py` 的 `FEATURES` 在 `gen_dem_table` 之前插入 `gen_dem_general`（arxml 先改好再进 ISOLAR 重生成）。

### 2.2 输入 Excel（独立 DemGeneral 配置表）

两个 sheet 放在**独立的配置表**（不与 DTC 的 EVM 表混放），与 EVM 表同目录：
`cpj_cmc/tools/<变体>/e2e_dem/IDC_DemGeneral_Config_<项目>_<版本>_<日期>.xlsx`（RX 实例：`IDC_DemGeneral_Config_CMC_RX_V3.0_20261120.xlsx`），只含以下两个 sheet，列名必须一致：

主脚本定位规则：`--excel-general` 指定优先，否则在 `cpj_*/tools/<变体>/e2e_dem/` 下自动发现唯一 `IDC_DemGeneral_Config*.xlsx`（排除 `_merged`）。空表模板随工具存放：`gen_dem_general/template/IDC_DemGeneral_Config_template.xlsx`（仅表头结构，新变体复制起步）。

> 表为 AI 维护（非人工填写），编辑规则权威源：[.claude/references/dem-general-config-table.md](../../.claude/references/dem-general-config-table.md)（sheet schema、取值规则、依赖方向、修改场景操作序列、改表后验证）。

**`enable_condition_group`**（6 列）：

| 列 | 语义 |
| --- | --- |
| No. | 序号 |
| ItemKind | `EC` = DemEnableCondition（单个使能条件，运行时 SWC 经 Dem_SetEnableCondition 置位）；`ECG` = DemEnableConditionGroup（使能条件组，组内 EC 全 true 事件才可用） |
| Name | 容器 SHORT-NAME |
| Description | 语义说明（仅文档用途，不进 arxml） |
| Status | DemEnableConditionStatus（布尔） |
| Members | ECG 行：空格分隔的 EC 名（sheet 内优先，否则须为 DemGeneral 存活容器）；EC 行必须为空 |

**`extended_freeze_data`**（11 列）：`No. | ItemKind | Name | DataType | Source | InternalElement | DidHex | Number | Update | Trigger | Members`

| ItemKind | 对应容器类 | 关键列 |
| --- | --- | --- |
| DATA-ELEMENT | DemDataElementClass（choice） | Source=External → DataType UINT8/16/32；Source=Internal → InternalElement 枚举（如 DEM_OCCCTR） |
| DID-CLASS | DemDidClass | DidHex（0x 十六进制）+ Members=SR 名 |
| FREEZE-FRAME-CLASS | DemFreezeFrameClass | Members=DidClass 名 |
| SNAPSHOT-RECORD | DemFreezeFrameRecordClass | Number/Update/Trigger（无 Members） |
| EXTENDED-RECORD | DemExtendedDataRecordClass | Number/Update/Trigger + Members=SR 名 |
| EXTENDED-DATA-CLASS | DemExtendedDataClass | Members=EXTENDED-RECORD 名 |
| FF-RECNUM-CLASS | DemFreezeFrameRecNumClass | Members=SNAPSHOT-RECORD 名 |

### 2.3 生成规则

- CLI：`python gen_dem_general.py <DemGeneral配置表xlsx> <arxml> <ecg:true|false> <efd:true|false>`
- 插入位置：`.//ar:ECUC-CONTAINER-VALUE[ar:SHORT-NAME='DemGeneral']/ar:SUB-CONTAINERS` 尾部（定位必须恰好 1 个）
- DEFINITION-REF 指向 `/AUTOSAR_Dem/EcucModuleDefs/Dem/DemGeneral/<类>`；引用 VALUE-REF 前缀 `/RTA_BIP/EcucModuleConfigurationValuess/Dem/DemGeneral/`（"Valuess" 拼写为既有约定，保留）
- 全部生成容器带 `S="USER_GENERATED"` 标记（与案例手工容器一致，ETAS 生成标记）
- 空参数/空引用不落空包装元素（`PARAMETER-VALUES`/`REFERENCE-VALUES` 懒创建，与手工容器形态一致）
- 序列化复用 `gen_dem_arxml/Create_DemDTCs.py` 管线（xml declaration 保留 + lxml + `preprocess_xml_tags`/`format_xml_indent` + CRLF 写回 + DOCTYPE 保留），与既有 Create_* 同先例
- 校验失败显式 exit 1：缺 sheet/缺列、Name 重复/为空、ItemKind 非法、EC 带 Members、ECG/成员类 Members 为空、DataType/Source 非法、DidHex 非 0x、记录行缺 Number/Update/Trigger、成员引用既不在 sheet 也不在存活容器、成员类型与依赖方向不符（DID-CLASS←DATA-ELEMENT、FREEZE-FRAME-CLASS←DID-CLASS、EXTENDED-RECORD←DATA-ELEMENT、EXTENDED-DATA-CLASS←EXTENDED-RECORD、FF-RECNUM-CLASS←SNAPSHOT-RECORD）

### 2.4 幂等替换策略

先删后建，sheet 为唯一真源。删除条件（满足其一）：

1. SHORT-NAME 在当前 sheet 中；
2. 属受管定义类型（ECG 开关管 `DemEnableCondition`/`DemEnableConditionGroup`；EFD 开关管 `DemDataElementClass`/`DemDidClass`/`DemFreezeFrameClass`/`DemFreezeFrameRecordClass`/`DemExtendedDataRecordClass`/`DemExtendedDataClass`/`DemFreezeFrameRecNumClass`）且 `S="USER_GENERATED"`。

不在 sheet 中的手工容器（如带 DemDiagnosisScaling 的 `SR_Vehicle_Speed`）不受影响。成员引用解析以**删除后**存活集合为准，防「sheet 删了被引用容器」产生悬空引用。

## 3. 验证结论（本机 D:，RTA-CAR 12.7.0）

1. **黄金对照**：以 CMCRXJ6B-42/43 案例手工容器为基准（golden 备份 48 个 DemGeneral 子容器），单跑生成器后逐容器规范化比较（剔除 S 属性、属性序归一、子容器稳定排序）：48/48 命中，唯一残留差异为 `SR_ExtendedDataRecord_Ageing_Counter` 内层 choice 容器 SHORT-NAME（手工命名 `DemInternalDataElementClass_0` vs 生成统一 `DemInternalDataElementClass`）——语义无关（引用只指向外层容器），接受；DemGeneral 段外整文件字节级一致（diff 行范围 175–1059 全落在 DemGeneral 段内）。
2. **幂等回归**：连续跑两次生成器，第二次输出与第一次**字节级一致**（cmp 零差异）。
3. **全流程**：`python dem_autogen_etas.py --repo <mcu_app_j6> --config rx` 全步骤 OK（gen_dem_general → gen_dem_arxml → ISOLAR headless BSW 重生成 → gen_event_ctrl → gen_fim_code）；重生成后 DemGeneral 容器仍在。
4. 期间修正 sheet 两处：EC_ACANBusNormal/EC_FRCANBusNormal 的 Status 按 arxml 实值应为 `true`（初始误填 false）。

## 4. 已知边界 / 不做

- 不动 gen_dem_table/gen_event_ctrl/gen_fim_code 既有行为；不动 DemConfigSet 侧生成逻辑（引用侧已按固定名写好）。
- 不生成 OperationCycle/StorageCondition/DemClient/DemRbGeneral 等非本次范围容器。
- ItemKind 固定七类，不做通用 schema 演进（够覆盖快照+扩展数据模式）。
- 内层 choice 容器 SHORT-NAME 采用统一命名，不复制手工命名痕迹（`_0` 等后缀）。
