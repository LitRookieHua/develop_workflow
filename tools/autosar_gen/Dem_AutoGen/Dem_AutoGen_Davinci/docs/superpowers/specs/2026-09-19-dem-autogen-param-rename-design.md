# Dem_AutoGen_Davinci 参数化与重命名设计

- 日期: 2026-09-19
- 状态: 已确认
- 范围: `D:\Workspace\01_Projects\02_Src\10_tools\Dem_AutoGen_Davinci`

## 背景与目标

1. 工具当前把 MCU 仓库路径硬编码在脚本常量里(`REPO` / `DEFAULT_TARGET`),工作区结构调整就要改代码。目标:仓库路径改为必填命令行参数 `--repo`,工具与工作区路径彻底解耦。
2. 脚本与目录命名混杂(`Gen_DTC_ARXML_Script/Gen_DTC_ARXML.py` 等),目标:统一 snake_case 并使命名更达意。

## 1. CLI 参数化(`Dem_AutoGen.py` → `dem_autogen.py`)

```
python dem_autogen.py <DTC表.xlsx> --repo <mcu_app_tda4路径> [--sheet xxx] [--skip-gen]
```

- `--repo` 必填,无默认值;`--sheet`、`--skip-gen` 保持原有语义。
- 删除模块级 `REPO` 常量;`ECUC`/`DPA`/`SIPADDON`/`EVM_SCRIPT`/`DVCFG_CMD` 改为在 `main()` 内由 `args.repo` 构建,作为参数传入各步骤函数。
- 工具自身路径(`GEN_TOOLS`,基于 `__file__`)不受影响;子脚本路径常量(`CLEAR_SCRIPT` 等)随重命名同步更新。
- `--repo` 传错由启动时的文件存在性检查截获(现有机制不变)。
- license 相关常量(`USBCLNCMD` 等)与流程逻辑(8 步)不动。

## 2. 命名映射(9 文件 + 5 目录)

| 旧 | 新 |
|---|---|
| `Dem_AutoGen.py` | `dem_autogen.py` |
| `Check_Excel_Script/Check_Excel.py` | `check_dtc_table/check_dtc_table.py` |
| `Gen_Clear_ARXML_Script/Dem_ClearDtcEvent.py` | `clear_dem_arxml/clear_dem_arxml.py` |
| `Gen_DTC_ARXML_Script/Gen_DTC_ARXML.py` | `gen_dtc_arxml/gen_dtc_arxml.py` |
| `Gen_DTC_ARXML_Script/Merge_Excel.py` | `gen_dtc_arxml/merge_excel.py` |
| `Gen_DTC_ARXML_Script/ModifyDtcExcel.py` | `gen_dtc_arxml/modify_dtc_excel.py` |
| `Gen_DTC_ARXML_Script/ProcessArxml.py` | `gen_dtc_arxml/process_arxml.py` |
| `Gen_Event_ARXML_Script/Gen_Event_ARXML.py` | `gen_event_arxml/gen_event_arxml.py` |
| `Gen_Event_ARXML_Script/Merge_Excel.py` | `gen_event_arxml/merge_excel.py` |
| `Gen_Event_ARXML_Script/ProcessArxml.py` | `gen_event_arxml/process_arxml.py` |
| `Gen_Excel_To_Csv_Script/Excel_To_Csv.py` | `excel_to_csv/excel_to_csv.py` |

说明:
- 两份 `ProcessArxml.py` 内容有差异,各自保留在对应目录,不改内容;`Merge_Excel.py` 两份完全相同,按方案 A 也保留重复(去重属扁平化方案 B,不做)。
- `Excel_Table/`(Excel 配置表)、`backup/`、`.gitignore` 不动。

## 3. 接口与连带修改

- `clear_dem_arxml.py`:删除 `DEFAULT_TARGET`(硬编码仓库路径,已无意义),ecuc 路径改为必填位置参数;主流程显式传参,行为不变。
- 子脚本内部 `import` 同步改名(`import ProcessArxml` → `import process_arxml` 等)。
- 删除死代码:`gen_dtc_arxml.py` / `gen_event_arxml.py` 中被 `argv[3]` 覆盖的 `DEM_ARXML_FILE_PATH` 常量(内含旧仓库相对路径)。
- 日志前缀一致化:`[Dem_AutoGen]` → `[dem_autogen]`,`[Dem_ClearDtcEvent]` → `[clear_dem_arxml]`;其余子脚本输出不动。
- 各脚本 docstring 中的用法说明同步更新为新文件名与新参数。
- 清理旧 `__pycache__` 目录。

## 4. 验证方式

1. `py_compile` 全部脚本通过。
2. `python dem_autogen.py --help` 参数说明正确;缺 `--repo` 时报错退出。
3. 用真实 repo 路径做路径推导检查:加载模块/构造参数后验证 ECUC、DPA、DVCFG_CMD、EVM_SCRIPT、各子脚本等路径存在(不连 license、不写文件)。
4. 完整流程(含 license、DaVinci)由用户实际运行验证。

## 5. 不做的事

- 不扁平化目录、不去重 `Merge_Excel.py` / `ProcessArxml.py`。
- 不改各子脚本的核心处理逻辑(除上述 import/常量/前缀连带项)。
- 不改 license 连接方式与 8 步流程结构。
