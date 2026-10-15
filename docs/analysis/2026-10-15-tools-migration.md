# 工具迁移记录：10_tools → develop_workflow/tools

- 日期：2026-10-15
- 性质：结构整合个案（非故障排障，留档备查）

## 结论

6 个工具（3 个 autosar_gen + DiagnosticTester/LogCollection/ProgramBoard）以复制副本方式迁入 `develop_workflow/tools/`。**tools/ 为运行时权威源，10_tools 冻结为迁移前备份**。副本 `.git` 已删除，工具随 develop_workflow 统一 git 仓库管理。

## 影响与注意事项

- skill（dev-workflow）中工具路径引用已同步改为 tools/ 绝对路径
- 旧 `.git` 历史需要回溯时去 10_tools 备份查（`git -C 10_tools/<工具> log`）
- 今后任何工具改动只改 tools/ 副本；10_tools 不再更新，避免双源分叉
