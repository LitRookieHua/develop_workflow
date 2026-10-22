# dtc-table-import：DTC 表导入规则（硬性）

EVM 诊断问卷（IDC_EVM_Config*.xlsx）导入 MCU 的流程规则，feature-development 的 DTC 表导入类需求一律遵守。表格校验规则（4 条 check + 跳过规则）见 `tools/autosar_gen/Dem_AutoGen/Dem_AutoGen_Davinci/check_dtc_table/check_dtc_table.py` 模块 docstring。

## 硬规则

1. **修改表格必须通知需求创建人**：导入过程中修正过表格（如空 DTC 列补 `N.A`、事件名手误改名），必须把修正版表格 + 改动说明发给问卷需求创建人（来源释放单 reporter，如 D100-1071 的 Jason.Yu），由其在后续释放版本中更新——不通知则下轮导入重复触发同样问题。
2. **表格必须上传 zos_msg**：每次问卷导入，xlsx 必须上传到 zos_msg 仓库 `Gen_evm_dem_Script/`（删旧版本、加新版本，命名带日期后缀如 `IDC_EVM_Config_Chery_D100_T1JFL3_V0.8_20261021.xlsx`），与 mcu 仓库导入配套建 PR（zos_msg reviewers 见 pr-merge.md）。即使本次改动看似只影响 mcu 侧生成物、即使历史先例没传，也要传——zos_msg 的 EVM 接口生成按 `EVM_CFG_FILE_NAME` 前缀从自己仓库找 xlsx，不传则 zos 侧生成输入与 mcu 侧脱节。
3. **校验失败修表不修工具**：`check_dtc_table.py` 校验 FAIL 时修正表格本身（对齐邻行约定），不放宽校验工具。
4. **生成产物手误的最小修复**：表格事件名手误（历史遗留）在全量重导入后暴露导致编译失败时，只手改编译受阻的宏定义（如 Dem_Lcfg.h），不重新导入；注释/arxml/缓存里的残留 typo 无害，下轮导入自愈。

## 流程位置

完整开发流程（立项→分支→导入生成→编译→验证→PR）走 feature-development skill；表格导入子工具为 `tools/autosar_gen/Dem_AutoGen`（TDA4 Davinci 变体）。
