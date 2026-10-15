# Dem_AutoGen map 表生成功能设计

- 日期: 2026-09-19
- 状态: 已确认
- 范围: `D:\Workspace\01_Projects\02_Src\10_tools\Dem_AutoGen_Davinci`
- 注: CLI 已被 `2026-09-19-gen-map-yaml-etas-design.md` 取代 (改为工程目录输入, 双模式)

## 背景与目标

从生成的 `StartApplication_Dem_Dem_ecuc.arxml` 中提取 DTC 与 Event,生成两张映射表:

- `dtc_map.yaml`: DTC 值(十六进制)→ DTC 容器名
- `event_map.yaml`: EventId(十进制)→ Event 容器名

作为主流程 **Step 5/8d** 执行(5a Excel→CSV、5b DTC ARXML、5c Event ARXML 之后),每次运行都生成,无 CLI 开关。输出到 MCU 仓库的 Evm_Script/Evm_Config_Excel_To_Csv 目录。

## 数据源(arxml 实测结构)

DemConfigSet 的 SUB-CONTAINERS 一级容器中:

- **DTC**: `DEFINITION-REF = /MICROSAR/Dem/DemConfigSet/DemDTCClass`,SHORT-NAME 如 `DemDTC_C200016_KL30_TooLow`,参数 `DemUdsDTC` 为十进制整数(如 6291478 = 0x600016)。当前 v2xeu 表共 250 个。
- **Event**: `DEFINITION-REF = /MICROSAR/Dem/DemConfigSet/DemEventParameter`,SHORT-NAME 如 `DemEvent_IBS_FvCamEEPROM_OpDataCRCError`,参数 `DemEventId` 为十进制整数(如 1)。实测 1800 个。
- **模板容器**: SHORT-NAME 字面为 `DemEventParameter`(清理脚本保留的模板,实测 DemEventId=1801),**排除**。

## 输出格式

纯文本 YAML,根节点直接是映射,无外层包裹、无注释行(下面示例中的 `# 文件名` 行仅为文档标注,非文件内容),按 key 数值升序:

```yaml
# dtc_map.yaml
0x600016: DemDTC_C200016_KL30_TooLow
0x600017: DemDTC_C200017_KL30_TooHigh

# event_map.yaml
1: DemEvent_IBS_FvCamEEPROM_OpDataCRCError
2: DemEvent_IBS_RvCamEEPROM_OpDataCRCError
```

DTC key 格式: `0x` + 大写十六进制(`0x%X`)。UTF-8 无 BOM。

## 1. 新脚本 `gen_map_yaml/gen_map_yaml.py`

```
用法: python gen_map_yaml.py <ecuc_arxml> <output_dir>
```

- 提取方式: **容器级正则扫描**(方案 A)——复用 `clear_dem_arxml.py` 已验证的容器遍历模式(`find_matching_close` 深度计数 + 一级容器迭代),对每个容器先取 SHORT-NAME 与 DEFINITION-REF 判型,再在容器块内正则提取目标参数值。单遍流式,不建 DOM。
- 每个容器内参数定位: DEFINITION-REF 含 `/DemDTCClass/DemUdsDTC` 或 `/DemEventParameter/DemEventId` 时,取其后的第一个 `<VALUE>` 整数。
- 不用 minidom(23MB 建树慢且重,只为读约 3850 个值)。

## 2. dem_autogen.py 集成

- 新常量 `GEN_MAP = GEN_TOOLS / "gen_map_yaml" / "gen_map_yaml.py"`,加入启动文件存在性检查列表。
- Step 5/8c 之后新增:
  ```
  Step 5/8d 生成 map 表
  [sys.executable, str(GEN_MAP), str(paths.ecuc), str(paths.evm_script)]
  ```
  输出 `Evm_Script/Evm_Config_Excel_To_Csv/dtc_map.yaml` 与 `Evm_Script/Evm_Config_Excel_To_Csv/event_map.yaml`。失败则流程中止(finally 保障 license 释放)。
- docstring 流程说明补 5d,总步骤仍为 8 步。

## 3. 错误处理

- arxml 不存在或参数不对 → 用法报错,exit 1
- **重复 DTC 值或重复 EventId** → 报具体冲突项,exit 1(数据完整性必须暴露,不能静默覆盖)
- 提取数为 0(DTC 或 Event 任一为空)→ 报错 exit 1(防呆,流程中 5d 在 5b/5c 之后不可能为空)
- 输出前打印统计(DTC 数、Event 数、输出路径)

## 4. 验证方式

1. `py_compile` 通过
2. **standalone 跑真实 arxml**(只读安全): DTC 条数 = 250、Event 条数 = arxml 中 DemEvent_* 容器数;抽查条目与 grep 结果一致;文件为合法映射格式
3. 完整 8 步流程的 5d 随下次实际使用验证(不为验证单独重跑 26 分钟全流程)

## 5. 不做的事

- 不加 CLI 开关(--skip-map 等,用户确认每次都生成)
- 不引入 yaml 库(纯文本写入,格式即两列映射)
- 不改动 5a/b/c 及其余步骤的行为
- 不生成 dtc_map/event_map 之外的衍生表
