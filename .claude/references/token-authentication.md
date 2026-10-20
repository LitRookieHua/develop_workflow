# CI / JIRA / Bitbucket 令牌认证规格

Token 存放位置、认证方式、踩坑规则（权威源）。安全底线：**绝不内联到任何会被提交的文件**（含命令日志回显注意脱敏）；`.imobuilder` 含 CI token，不要暴露其内容。

## JIRA（jira.imotion.ai:7070）

- **Token 存放**：`C:\Users\YH\.claude\jira_token.txt`（PAT；`C:\Users\YH\.claude\.mcp.json` 的 `mcpServers.atlassian.env.JIRA_API_TOKEN` 为同一 PAT）
- **认证方式**：`Authorization: Bearer <PAT>`——⚠️ **Basic auth 会 401**，只能 PAT Bearer
- **读取**：`TOKEN=$(cat ~/.claude/jira_token.txt | tr -d '\r\n')`（Windows 文件务必剥 `\r\n`，否则 401）
- **常用端点**：`GET/POST /rest/api/2/issue/{key}`、`.../transitions`、`/comment`、`GET /rest/api/2/project/<KEY>/versions`
- 状态流转规则见 [jira-workflow-transitions.md](jira-workflow-transitions.md)

## CI（ci.imotion.ai）

- **Token 存放**：`C:\Users\YH\.claude\tokens.md` 的 CI service token 段（CI 认证一律用此 token，不查 `.imobuilder`）
- **格式**：**整串已含 `Bearer ` 前缀**——使用时直接整串传，**勿再拼一次 Bearer**（二次拼接会 401）
- **用途**：
  - `imobuilder configure --ci_service_token`（传整串）
  - 构建轮询：`GET https://ci.imotion.ai/api/v1/build-tasks/<build_id>`，HTTP 头 `Authorization: <整串>`
- 轮询规则：remote_build 后轮询 3 次、每次隔 5 分钟，`state==7` 才继续下载，否则停下报告

## Bitbucket（bitbucket.imotion.ai:7990）

- **Token 存放**：`C:\Users\YH\.claude\mcp.json` 的 `mcpServers.bitbucket-mcu_app_tda4.env.BITBUCKET_API_TOKEN`（`BBDC-` 前缀）
- **认证方式**：`Authorization: Bearer <BBDC-...>`
- **常用端点**（REST 1.0）：`/rest/api/1.0/projects/<PROJ>/repos/<repo>/pull-requests`（POST 建 PR）、`.../pull-requests/<id>`（GET 状态 / POST merge）、`.../activities`（评审意见）

## 通用规则

1. Token 只从上述文件读取，用变量传递，不落盘到仓库、不写进会提交的脚本/文档
2. 输出/日志里出现 token 时只显示前 10 字符级脱敏
3. 401 排查顺序：先查前缀拼接（CI 双 Bearer / JIRA 缺 Bearer）→ 再查文件读取是否带 `\r\n` → 最后怀疑 token 过期
