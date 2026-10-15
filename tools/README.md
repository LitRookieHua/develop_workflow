# tools/ — 运行时权威源

本目录是 6 个开发辅助工具的**运行时权威源**，2026-10-15 从 `D:\Workspace\01_Projects\02_Src\10_tools` 复制迁入。

- `10_tools` 原处已**冻结**：仅作迁移前备份保留，不再更新
- 工具的后续迭代在**本目录**进行（随 develop_workflow 统一 git 仓库管理）
- 迁入时删除了各工具原 `.git` 历史（历史仍在 10_tools 备份中）及 `__pycache__`/`logs` 运行残留

## 工具清单

| 目录 | 用途 | 开发工作流中的角色 |
| --- | --- | --- |
| `autosar_gen/Dcm_AutoGen` | DCM 配置代码生成 | autosar 生成，目标为 D: 本地路径 |
| `autosar_gen/Dem_AutoGen` | DEM 配置代码生成 | 同上 |
| `autosar_gen/Nvm_AutoGen` | NVM 配置代码生成 | 同上 |
| `DiagnosticTester` | UDS 诊断测试（CAN/CANFD） | 第 8 步诊断功能验证（写 testcase 跑脚本） |
| `LogCollection` | MCU 日志采集（J6B/N60，串口+SFTP） | 问题分析日志采集 |
| `ProgramBoard` | 板子一键刷写（fastboot） | 第 7 步固件刷写（仅 J6） |
