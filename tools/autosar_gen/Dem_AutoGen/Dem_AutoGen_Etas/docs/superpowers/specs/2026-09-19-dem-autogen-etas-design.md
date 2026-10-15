# Dem_AutoGen_Etas 工具设计

- 日期: 2026-09-19
- 状态: 已确认
- 范围: `D:\Workspace\01_Projects\02_Src\10_tools\Dem_AutoGen_Etas`
- 来源: 拷贝 `mcu_app_j6/tools/e2e_dem_Script` 并重命名;架构对齐 `Dem_AutoGen_Davinci`(dem_autogen.py)

## 背景与目标

J6/ETAS 车型的 Dem/E2E 配置生成目前靠 `cpj_cmc/tools/rx/e2e_dem/gen_e2e_dem.bat` 手动四连跑,BSW 代码生成还要再手动开 ISOLAR。目标:做一个像 Vector 侧 `dem_autogen.py` 一样的一键工具——Excel 进,BSW arxml/Dem Ctrl C/evm_cfg 三处配置出,BSW 代码自动生成。

## 1. CLI

```
python dem_autogen_etas.py <IDC_EVM_Config*.xlsx> --repo <mcu_app_j6路径> --project rx [--skip-gen]
```

- Excel 显式传参(车型目录里混有其他车型的表,自动发现有误选风险)
- `--repo` 必填,指向 mcu_app_j6 仓库根
- `--project` 必填,车型短名(如 `rx`)
- `--skip-gen`:只跑三个生成脚本,不执行 BSW 代码生成

## 2. 目录结构与拷贝范围

```
Dem_AutoGen_Etas/
├── dem_autogen_etas.py        # 主编排(新建)
├── gen_dem_arxml/             # ← Gen_Dem_Arxml_Script(9 文件原样,零逻辑改动)
├── gen_event_ctrl/             # ← Gen_Event_Available_Control_Script(原样)
├── gen_evm_fimfid/             # ← Gen_Evm_FiMFID_Script(两脚本合一,详见 §4)
│   ├── gen_evm_fimfid.py       #   新建:合并后的主脚本
│   ├── Merge_ExcelSheets.py    #   原样保留
│   ├── TemplateFile.py         #   原样保留
│   ├── ReadMe.txt              #   原样保留(内容已过时,仅存档)
│   └── template/               #   3 个 .tpl 原样保留
└── docs/superpowers/specs|plans/
```

- 只重命名**目录**(snake_case,同 Davinci 风格);目录内**文件名不动**——import 都是目录内相对引用(`from Merge_ExcelSheets import ...`),目录改名零代码改动
- 不拷 `Export_Excel_To_Csv/`、`pick_latest_excel.py`(旧 bat 流程辅助件,新工具 Excel 显式传参用不到)
- 不拷 `Gen_Evm_FiMFID_Script/Gen_zx_fimcfg.py`、`Gen_Evm_FiMFID_Script.py`(被合并取代)

## 3. 路径推导(resolve_repo_paths)

`--repo + --project` 推导全部目标路径,无硬编码(实测 31/31 车型同构):

| 目标 | 推导规则 | 失败处理 |
|---|---|---|
| BswRta | `repo/cpj_*/autosar/<project>/BswRta` glob | 0 或多个命中 → exit 1 |
| Dem arxml | `BswRta/ecu_config/bsw/gen/*Dem_EcucValues.arxml`,排除 `RTA_BIP_` 前缀 | ≠1 个 → exit 1 |
| Dem Ctrl 输出 | `BswRta/integration/src/bsw/Dem/user/` | 不存在 → exit 1 |
| FiMFID cpp 输出 | `<cpj>/evm_cfg/var/src/vehicle/<project>/_gen/` | 不存在则创建 |
| FiMFID h 输出 | `<cpj>/evm_cfg/var/inc/vehicle/<project>/evm_cfg/`(zx fimcfg 同目录) | 不存在则创建 |
| ISOLAR-B | `RTA_CAR_HOME`(env,默认 `D:/ETAS/RTA-CAR_12.7.0`)下递归找 `ISOLAR-B.cmd` | 找不到 → exit 1 |

cpj 客户根 = BswRta 向上三级(`autosar/<project>` 的父级)。

## 4. 执行流程(4 步)

每步 subprocess 检查返回码,失败打印输出尾部并 exit 1。`_merged.xlsx` 中间产物仍写在 Excel 旁边(现状行为,不动)。

```
Step 1/4  gen_dem_arxml  : py Dem_arxml_Script.py <excel> <arxml>                    (cwd=脚本目录)
Step 2/4  gen_event_ctrl : py Gen_EventAvailable_Control_Script.py <excel> <dem_ctrl_out>
Step 3/4  gen_evm_fimfid : py gen_evm_fimfid.py <excel> <cpp_out> <h_out>
Step 4/4  BSW 生成      : headless 默认,Cobra.exe 降级;--skip-gen 跳过
```

## 5. gen_evm_fimfid.py(两脚本合一)

原 `Gen_Evm_FiMFID_Script.py` 与 `Gen_zx_fimcfg.py` 各自调 `merge_excel_sheets` 写**同一个** `_merged` 文件(参数实质相同),合并即"合并一次 + 两段生成":

1. `merge_excel_sheets(excel)` 跑一次
2. FiMFID 段(原 Gen_Evm_FiMFID_Script.py 主体):读 merged → FiMFID Y/N 二进制分组 → 生成 `evm_cfg_FidCfg.hpp` + `evm_cfg_iSysFidCfg.cpp`
3. zx 段(原 Gen_zx_fimcfg.py 的生成逻辑):提取 `FiMFID_` 列名 → 生成 `zx_sys_evm_cfg_fimcfg.hpp`;**丢弃**原 `filter_excel_columns()` 调用(返回值本就未用,死代码)
4. 版本号/时间戳统一推导一次

CLI:`python gen_evm_fimfid.py <excel> <cpp_out_dir> <h_out_dir>`(zx 输出到 h_out_dir)。

## 6. Step 4:BSW 生成(从 bsw_gen.ps1 移植成 python)

**默认 headless**(本机可用):

- `ISOLAR-B.cmd -generate -p=<BswRta> -t=BSW`,cwd=ISOLAR-B 所在目录
- 等进程自然退出(rx 实测 ~10.5 分钟);上限 20 分钟,超时 `taskkill /PID <pid> /T /F` 杀进程树,再等 10s 文件系统落盘
- 结果判定:解析 `<BswRta>/_log/BSW_ConfGen_ECUGeneration.txt` 的 `Errors: N, Warnings: M`;exit code 非 0 也算失败

**降级 Cobra.exe**(headless 失败时自动):

- `Cobra.exe --ProjectPath=. --isolarPath=<ISOLAR-AB目录> --isolarARRoot=RTA_BIP`,cwd=BswRta
- 判定:exit code + `_log/BSW_ConfGen_ECUGeneration.txt` 错误数 + license 静默失败检测(输出 `<30` 行或含 license 提示即失败)

两者都失败 → exit 1,提示查看 `_log/` 日志。license 为本机 license,无连接/断开步骤。

## 7. 验证方式

1. `py_compile` 全部脚本通过
2. `python dem_autogen_etas.py --help` 参数说明正确;缺 `--repo`/`--project` 报错退出
3. 真实 repo 路径推导检查(只读,不连工具、不写文件):BswRta/arxml/输出目录/ISOLAR-B 全部解析正确
4. `--skip-gen` 全流程 + 完整流程(含 BSW 生成)由用户实际运行验证

## 8. 不做的事

- 不改三个子目录里任何既有脚本逻辑(gen_evm_fimfid.py 合并除外)
- 不做 RTE/OS 生成(本工具只管 Dem 相关 BSW)
- 不做 Excel 自动发现(目录混表,显式传参最稳)
- 不加 license 连接(本机 license)
- 不做 Cobra.exe 优先模式(headless 是本机默认,按需再降级)
