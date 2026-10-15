# gen_map_yaml 双模式扩展设计(Vector DaVinci + ETAS)

- 日期: 2026-09-19
- 状态: 已确认
- 范围: `D:\Workspace\01_Projects\02_Src\10_tools\Dem_AutoGen_Davinci`
- 前置: `2026-09-19-gen-map-yaml-design.md`(初版,仅 Vector)

## 背景与目标

gen_map_yaml 原先仅适配 Vector DaVinci(TDA4/MICROSAR)工程。扩展为同时适配 ETAS(J6/AUTOSAR_Dem)工程,使 J6 侧也能从 arxml 生成 dtc_map.yaml / event_map.yaml。

**不新增 CLI 开关**:不提供 `--vector`/`--etas` 参数,两种工程由目录结构自动判型(见下)。理由:两种工程的输入目录(SipAddon vs BswRta)结构差异显著,不存在歧义,显式开关是多余的状态。

## CLI

```
用法: python gen_map_yaml.py <project_dir> <output_dir>
```

- `project_dir`:Vector 传 **SipAddon** 文件夹;ETAS 传 **BswRta** 文件夹
- `output_dir`:不变,显式指定输出目录
- 原 `<ecuc_arxml>` 参数取消,改为工程目录

## 判型规则(自动,无开关)

按目录结构检测,两个条件互斥判定:

| 检测条件 | 判型 |
|---|---|
| `<dir>/Config/ECUC/StartApplication_Dem_Dem_ecuc.arxml` 是文件 | Vector |
| `<dir>/ecu_config/bsw/gen` 是目录 | ETAS |
| 两者都满足 / 都不满足 | 报错 exit 1(提示 Vector 需传 SipAddon、ETAS 需传 BswRta) |

## 文件定位

**Vector**(单一来源,DTC 和 Event 都在其中):
- `<dir>/Config/ECUC/StartApplication_Dem_Dem_ecuc.arxml`(固定文件名,判型时已确认存在)

**ETAS**(两个来源):
- DTC:`<dir>/ecu_config/bsw/gen/*Dem_EcucValues.arxml`,**排除** `RTA_BIP_` 前缀(RTA_BIP_Dem_EcucValues.arxml 是 BIP 默认值文件,仅 1KB,非工程实际配置);匹配数必须恰为 1,否则报错 exit 1
- Event:`<dir>/ecu_config/bsw/gen/_fwd/ecuc_configuration_values_fwd.arxml`(固定路径;此文件是 ETAS ID 生成器 `Dem_GenerateID.mwe#Dem_IdGenerator` 回填 DemEventId 的地方,603 个事件容器仅含 DemEventId 一个参数)

## 数据结构对比

两工程的 DemConfigSet SUB-CONTAINERS 一级容器结构相同(均为 ECUC-CONTAINER-VALUE),容器遍历逻辑(深度计数 + 一级迭代)共用,差异仅在判型锚串与参数定位:

| | Vector(MICROSAR) | ETAS(AUTOSAR_Dem) |
|---|---|---|
| DTC 容器锚串 | `>/MICROSAR/Dem/DemConfigSet/DemDTCClass</DEFINITION-REF>` | `>/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemDTC</DEFINITION-REF>` |
| DTC 值参数 | `DemDTCClass/DemUdsDTC</DEFINITION-REF>` 后的 `<VALUE>` | `DemDTC/DemDtcValue</DEFINITION-REF>` 后的 `<VALUE>` |
| Event 容器锚串 | `>/MICROSAR/Dem/DemConfigSet/DemEventParameter</DEFINITION-REF>` | `>/AUTOSAR_Dem/EcucModuleDefs/Dem/DemConfigSet/DemEventParameter</DEFINITION-REF>` |
| Event 来源文件 | 与 DTC 同一 arxml | `_fwd` 文件 |
| Event 值参数 | `DemEventParameter/DemEventId</DEFINITION-REF>` 后的 `<VALUE>` | 同左 |
| 模板排除 | 排除容器自身名为 `DemEventParameter` 的模板容器 | 不需要(_fwd 只含 ID 生成器回填的真实事件,无模板) |
| 实测规模 | DTC 250 / Event 1800 | DTC 75 / Event 603 |

## 输出格式

不变:根节点直接是映射,按 key 数值升序,UTF-8 无 BOM:
- `dtc_map.yaml`:`0x` + 大写十六进制(ETAS 示例:DemDtcValue 6653511 → `0x658647`)
- `event_map.yaml`:十进制

## 错误处理

沿用初版(重复 DTC 值/EventId 报具体冲突项、提取数为 0 报错,均 exit 1),新增:
- 目录不存在或无法判型 → 报错 exit 1,提示两种工程各需传什么目录
- ETAS `*Dem_EcucValues.arxml`(排除 RTA_BIP_ 后)匹配 0 个或多个 → 报错 exit 1
- `_fwd/ecuc_configuration_values_fwd.arxml` 不存在 → 报错 exit 1

## dem_autogen.py 集成改动

仅一处:Step 5/8d 调用的第一个参数由 `str(paths.ecuc)` 改为 `str(paths.sipaddon)`(resolve_repo_paths 已提供该变量),输出目录不变。docstring 与其余步骤不动。

## 验证方式

1. py_compile 通过
2. **Vector 回归**:对 TDA4 真实 SipAddon 目录跑,输出与现有 `Evm_Script/Evm_Config_Excel_To_Csv/` 两张 map 字节级一致
3. **ETAS 新路径**:对 J6 真实 BswRta 目录跑(输出到临时目录,只读安全),DTC 75 条、Event 603 条;抽查 DemDtcValue 6653511 ↔ 0x658647;与 `Dem_Cfg_EventId.h`(603 个 define)、`Dem_Cfg_DTC_DataStructures.c`(75 个 DTC 值)交叉核对
4. 错误路径:传无法判型的目录 → 报错 exit 1

## 不做的事

- 不加 `--vector`/`--etas` 开关(目录自动判型,规则如上)
- 不改输出格式,不改现有 Vector 行为(字节级兼容)
- 不做 J6 侧自动化流程集成(J6 单独手动跑)
- 不生成 dtc_map/event_map 之外的衍生表
