# Dem_AutoGen_Etas 功能配置化改造设计

- 日期: 2026-09-19
- 状态: 已确认
- 范围: `D:\Workspace\01_Projects\02_Src\10_tools\Dem_AutoGen_Etas`
- 前置: `2026-09-19-dem-autogen-etas-design.md`(初版,固定 4 步流程)

## 背景与目标

初版工具固定 4 步流程(arxml → event ctrl → fim → BSW 生成)。实际使用中:

1. 不同车型/不同迭代只需要部分步骤(如 rx 本次快速迭代只要 fim + map,arxml 没动不需要 12 分钟 BSW 生成)
2. `DemDebounceCounterJumpDown/JumpUp` 在 `Create_DemDebounceCounterBasedClass.py:112,121` 硬编码 `"true"`,rx 项目两个均为 true,其余项目均为 false,需按项目区分

目标:拆成 5 个功能按 yaml 配置启停;BSW 生成归属 gen_dem_table(gen_dem_arxml 之后立即执行);目录命名对齐功能名。

## 1. CLI

```
python dem_autogen_etas.py <IDC_EVM_Config*.xlsx> --repo <mcu_app_j6路径> --project rx
```

- **删除 `--skip-gen`**
- `--project` 兼任配置文件选择:`configs/<project>.yaml`,不存在则纯用 `common.yaml`
- 路径推导规则不变(BswRta/arxml/输出目录/cpj)

## 2. 五个功能与执行顺序

| # | 配置键 | 实现 | 默认(common) |
|---|---|---|---|
| 1 | `check_dtc_table` | 占位,脚本尚未引入;ON 时报错退出 | false |
| 2 | `gen_dem_table` | `gen_dem_arxml` + **紧接 BSW 生成**(headless,失败降级 Cobra) | enabled: true, jumpdown/jumpup: false |
| 3 | `gen_event_ctrl` | `Gen_EventAvailable_Control_Script.py` → Dem_PrjSpecificControl.c | false |
| 4 | `gen_fim_code` | gen_evm_fimfid 改名,一次生成 3 个文件 | true |
| 5 | `gen_map_yaml` | 拷贝自 `Dem_AutoGen_Davinci/gen_map_yaml`,输出 Excel 同目录 | true |

执行顺序固定如上表,按启用项动态编号(`Step i/N`,N = 启用功能数)。

**gen_map_yaml 必须在 BSW 生成之后**:ETAS 的 DemEventId 由 ID 生成器在 BSW 生成期间回填到 `_fwd/ecuc_configuration_values_fwd.arxml`,此顺序保证 map 数据新鲜(gen_dem_table OFF 时 _fwd 为上次 BSW 生成结果,arxml 未变则数据依然正确)。

## 3. 配置文件 `configs/`

```yaml
# configs/common.yaml
check_dtc_table: false        # 脚本尚未引入, 占位
gen_dem_table:
  enabled: true
  jumpdown: false
  jumpup: false
gen_event_ctrl: false         # 大部分情况不需要
gen_fim_code: true
gen_map_yaml: true
```

```yaml
# configs/rx.yaml(项目文件只写差异项)
gen_dem_table:
  enabled: false              # rx 本次只需要 fim + map
  jumpdown: true
  jumpup: true
```

**合并语义**:深合并——dict 递归合并,标量直接覆盖;项目 yaml 不存在则纯 common。

**校验(exit 1)**:

- common.yaml 必须含全部 5 个功能键(它是合并基)
- 合并后出现未知键(防拼写错误静默失效)
- 各功能值必须是 bool;`gen_dem_table` 合并后必须是 dict 且含 `enabled`
- `jumpdown`/`jumpup` 缺省视为 false

yaml 布尔即口语的 ON/OFF(true/false)。

## 4. jump 参数传递链

```
dem_autogen_etas.py(读合并后配置)
  → Dem_arxml_Script.py <excel> <arxml> [jumpdown] [jumpup]   # 可选 argv, 缺省 true(手工运行行为不变)
    → insert_debounce_counter_based_to_arxml(..., jump_down, jump_up)
      → create_debounce_counter_based_container(..., jump_down, jump_up)
        → num_param3_val.text = str(jump_down).lower()         # "true"/"false"
```

仅 `Dem_arxml_Script.py` 与 `Create_DemDebounceCounterBasedClass.py` 两处改动(初版"子目录零改动"约定的唯一例外);`Create_DemDebounceTimeBaseClass.py` 无 jump 参数,不动。

## 5. 目录与文件变更

| 变更 | 内容 |
|---|---|
| 改名 | `gen_evm_fimfid/` → `gen_fim_code/`,主脚本 `gen_evm_fimfid.py` → `gen_fim_code.py`(内部 Merge_ExcelSheets.py、TemplateFile.py、template/、ReadMe.txt 原样) |
| 新增 | `gen_map_yaml/`(从 `Dem_AutoGen_Davinci/gen_map_yaml` 原样拷贝,单文件自包含) |
| 新增 | `configs/common.yaml` + `configs/rx.yaml` |
| 不动 | `gen_dem_arxml/`、`gen_event_ctrl/` 目录名与内容(§4 两文件除外) |

## 6. 行为细节

- `gen_bsw_headless`/`gen_bsw_cobra`/Step 1 内容兜底(mtime + 容器锚点)逻辑不变,调用点整体移入 gen_dem_table 流程,紧跟 gen_dem_arxml
- `check_dtc_table` ON → `fail("check_dtc_table 脚本尚未引入")`
- `gen_map_yaml` 调用:`python gen_map_yaml.py <BswRta> <excel父目录>`,cwd = 脚本目录
- 启动横幅打印配置来源(项目 yaml / 纯 common)与合并后各功能开关
- BSW 生成依旧仅在 gen_dem_table enabled 时执行

## 7. 验证方式

1. `py_compile` 全部脚本通过
2. `--help` 不再出现 `--skip-gen`
3. 配置加载检查(只读):rx.yaml 合并结果(jumpdown/jumpup true、enabled false)、无项目 yaml 时纯 common、未知键/类型错误/缺键均报错退出
4. 真机半程回归:rx 配置只跑 fim + map,产物与旧输出一致 + dtc_map.yaml/event_map.yaml 生成于 Excel 同目录
5. gen_dem_table ON 的完整流程(arxml jumpdown=false 路径 + BSW 生成)由用户真机验证

## 8. 不做的事

- 不实现 check_dtc_table 脚本本体(仅配置占位)
- gen_map_yaml 不传第 3 参数 fimcfg hpp(暂不生成 fimfid_map.yaml,Davinci 流程同样未传)
- 不改 BSW 生成判定逻辑与路径推导规则
- 不改 DemDebounceCounterJumpDown/JumpUp 之外的任何 arxml 参数
