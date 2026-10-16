# build-troubleshooting：编译排障手册

编译失败先读本手册再动手。按现象对号入座，全部为实际发生过的案例。

## 1. J6 clean 末步 `-clean_binary` 必定失败（属正常，勿重复 clean）

（2026-09-11 实际发生，与 `-x` 无关）imobuilder 把 `--build --preset pf-gcc-clean` 参数拼到仓库的 clean 命令（`rm -rf .../output`）末尾，rm 报 `unrecognized option '--build'`，clean 以 exit 4 结束。但此时 clean 的其余部分（workspace build 树、各依赖包目录、`src/<仓库>/build`）已删完，实际效果等于 clean 完成，只需手动补删残留目录再直接 build：

```bash
ssh yaohua@10.0.12.42 "rm -rf /comp/user_data/yaohua/01_Src/02_Workspace_J6/src/<仓库>/output"
ssh yaohua@10.0.12.42 "cd /comp/user_data/yaohua/01_Src/02_Workspace_J6/ && imobuilder build <mcu_app_j6|mcu_app_j6_v2> -r -x parking_dr uper_app"
```

## 2. 后台编译不要接 `| grep` 管道

会把真实退出码掩盖成 grep 的退出码（2026-09-11 实际发生：clean 致命失败却报 exit 0）。SSH 警告信息留在输出文件里即可。

## 3. 编译前核对依赖仓库分支

（2026-10-15 实际发生）mcu 产品的构建会组合 workspace 里当前 checkout 的 zos_msg 等依赖仓库代码。develop/V460 两条分支交替开发时，切换 mcu 仓库后**必须把 zos_msg 等依赖仓库也切到对应分支**，否则出现接口不匹配类编译错误（如 `ipc_cfg_message.hpp: error: expected class name`，基类 `zos::park_dr::COdoAbstOutput` 找不到——develop mcu 配了 v460 的 zos_msg）。

编译报「找不到类/接口不匹配」先查：

```bash
ssh yaohua@10.0.12.42 "cd <workspace>/src/<依赖仓库> && git branch --show-current"
```

## 4. 固件问题排障（parking_dr / uper_app / MCU21，2026-10-14 用户指示）

编译阶段遇到以下问题按对应方案处理：

- **遇到 parking_dr / uper_app 的问题 → 更新 parking_dr 和 uper_app 固件**（这两个包是远端预编译产物，本地缓存的旧固件会导致链接结果异常，如 final bin 超大小限制）：
  1. 清空 download 目录内容：TDA4 为 workspace 下 `output/armv7-r-generic-tda4-r5f-llvm/release/download`；J6 为 `output/armv8-r-generic-gcc-r52/release/download`
  2. `imobuilder configure --ci_service_token 'Bearer <jwt>'`（⚠️ Bearer 和 token 之间必须有空格，拼成 `BearereyJ...` 或裸 JWT 都会 401；jwt 取自 `.imobuilder` 里的 CI token，不要暴露）
  3. `imobuilder remote_build parking_dr` 和 `imobuilder remote_build uper_app`，各返回一个 build_id
  4. 等构建完成（约 10 分钟）后 `imobuilder download target-<build_id> --build_id <build_id>` 下载两个固件
- **遇到 MCU21 固件的问题 → 重新编译 MCU21 固件**（uss_app_tda4 仓库，⚠️ 先确认该仓库在正确分支，残留旧分支会 API 不匹配编不过）：

```bash
imobuilder clean uss_app_tda4 -r -x parking_dr uper_app
imobuilder build uss_app_tda4 -r -x parking_dr uper_app
```

修完后重新 build mcu 仓库。2026-10-14 实际案例：v2xeu develop 基线 final bin 超 3456KB 限制，根因是 parking_dr/uper_app 为 9月4 旧固件 + uss_app_tda4 在错误分支，按上述流程刷新后 3329040 字节通过。
