# Dem_AutoGen_Etas 功能配置化改造实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 工具拆成 5 个功能(check_dtc_table/gen_dem_table/gen_event_ctrl/gen_fim_code/gen_map_yaml)按 `configs/*.yaml` 深合并配置启停;BSW 生成归属 gen_dem_table;gen_evm_fimfid 改名 gen_fim_code;gen_map_yaml 从 Davinci 移植。

**Architecture:** 新增配置加载(深合并+校验)进主编排器;jumpdown/jumpup 经 argv 可选参数传入 gen_dem_arxml 链路替换硬编码 "true";其余功能为 subprocess 子步骤按配置顺序执行。spec 见 `docs/superpowers/specs/2026-09-19-dem-autogen-etas-feature-config-design.md`。

**Tech Stack:** Python 3.12 + PyYAML 6.0.3(本机已装)、subprocess、lxml(子脚本既有)。

**执行方式:** 直接在 master 上提交(该仓库独立、单人维护,与前次流程一致)。Task 1 与 Task 2 各自提交后工具保持可用。

---

### Task 1: jump 参数链 + configs/ + gen_map_yaml 拷贝

**Files:**
- Modify: `gen_dem_arxml/Create_DemDebounceCounterBasedClass.py`
- Modify: `gen_dem_arxml/Dem_arxml_Script.py`
- Create: `configs/common.yaml`, `configs/rx.yaml`
- Create: `gen_map_yaml/gen_map_yaml.py`(拷贝自 `D:\Workspace\01_Projects\02_Src\10_tools\Dem_AutoGen_Davinci\gen_map_yaml\gen_map_yaml.py`,原样零改动)

- [ ] **Step 1: Create_DemDebounceCounterBasedClass.py 加 jump 参数**

两处函数签名与值写入(argv 传 "true"/"false" 字符串,`str(x).lower()` 归一化,兼容 bool):

`create_debounce_counter_based_container`(现 66 行)签名追加两个关键字参数:

```python
def create_debounce_counter_based_container(parent_element, autosar_namespace: str, EventName, Debounce_Falied, Debounce_Pass, DecrementStepSize, lncrementStepSize, jump_down="true", jump_up="true"):
```

112 行 `num_param3_val.text = "true"` 改为:

```python
    num_param3_val.text = str(jump_down).lower()
```

121 行 `num_param4_val.text = "true"` 改为:

```python
    num_param4_val.text = str(jump_up).lower()
```

`insert_debounce_counter_based_to_arxml`(现 159 行)签名追加:

```python
def insert_debounce_counter_based_to_arxml(
        input_arxml: str,
        output_arxml: str,
        parent_xpath: str,
        dem_data,
        jump_down="true",
        jump_up="true"
) -> bool:
```

内部 `create_debounce_counter_based_container(...)` 调用(现 215 行附近)追加两个实参:

```python
                create_debounce_counter_based_container(
                    parent_element=parent_container,
                    autosar_namespace=autosar_ns,
                    EventName=dem_data.EventName[i],
                    Debounce_Falied=dem_data.Debounce_Falied[i],
                    Debounce_Pass=dem_data.Debounce_Pass[i],
                    DecrementStepSize=dem_data.DecrementStepSize[i],
                    lncrementStepSize=dem_data.lncrementStepSize[i],
                    jump_down=jump_down,
                    jump_up=jump_up
                )
```

- [ ] **Step 2: Dem_arxml_Script.py 加可选 argv**

13-18 行 argv 检查改为(3 或 5 个参数,4 个报错):

```python
if __name__ == "__main__":
    # 命令行参数：<excel路径> <arxml路径> [jumpdown] [jumpup]（jump 缺省 true，兼容手工运行）
    if len(sys.argv) not in (3, 5):
        print("用法: python Dem_arxml_Script.py <excel_path> <arxml_path> [jumpdown] [jumpup]")
        print("示例: python Dem_arxml_Script.py IDC_EVM_Config_GAC_AY7_V1.4_20260622.xlsx J6B_Dem_EcucValues.arxml true true")
        sys.exit(1)
    jump_down = sys.argv[3] if len(sys.argv) == 5 else "true"
    jump_up = sys.argv[4] if len(sys.argv) == 5 else "true"
```

72-77 行 `insert_debounce_counter_based_to_arxml(...)` 调用追加:

```python
    insert_debounce_counter_based_to_arxml(
        input_arxml=arxml_file_path,
        output_arxml=arxml_file_path,
        parent_xpath=PARENT_CONTAINER_XPATH,
        dem_data=dem_data,
        jump_down=jump_down,
        jump_up=jump_up
    )
```

- [ ] **Step 3: 建 configs/ 与拷贝 gen_map_yaml**

```bash
mkdir configs
cp "D:/Workspace/01_Projects/02_Src/10_tools/Dem_AutoGen_Davinci/gen_map_yaml/gen_map_yaml.py" gen_map_yaml/gen_map_yaml.py
```

`configs/common.yaml`(内容与 spec §3 完全一致):

```yaml
# 通用配置: 各车型共用基线, 项目 yaml 只写差异项深合并覆盖
check_dtc_table: false        # 脚本尚未引入, 占位
gen_dem_table:
  enabled: true
  jumpdown: false
  jumpup: false
gen_event_ctrl: false         # 大部分情况不需要
gen_fim_code: true
gen_map_yaml: true
```

`configs/rx.yaml`:

```yaml
# rx: jumpdown/jumpup 与众不同; 本次快速迭代只需要 fim + map
gen_dem_table:
  enabled: false
  jumpdown: true
  jumpup: true
```

- [ ] **Step 4: 验证 jump 参数生效(写临时副本, 不碰真实 arxml)**

```bash
cp "/d/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/autosar/rx/BswRta/ecu_config/bsw/gen/J6B_Dem_EcucValues.arxml" /tmp/J6B_test.arxml
py -3 gen_dem_arxml/Dem_arxml_Script.py "D:\Workspace\01_Projects\02_Src\02_Workspace_J6\src\mcu_app_j6\cpj_cmc\tools\rx\e2e_dem\IDC_EVM_Config_CMC_RX_V2.0_20260823.xlsx" "C:\tmp\J6B_test.arxml" false false 2>&1 | tail -3
grep -c "DemDebounceCounterJumpDown</DEFINITION-REF>" /tmp/J6B_test.arxml   # 与真实文件相同数量
grep -A1 "DemDebounceCounterJumpDown</DEFINITION-REF>" /tmp/J6B_test.arxml | grep -c "<VALUE>false</VALUE>"   # 全部为 false
```

(若 C:\tmp 不存在改用 %TEMP%;期望:JumpDown 锚点数量不变,值全部 false。注意 grep -A1 会带出紧跟的 `<VALUE>false</VALUE>`,计数 = 锚点数。)

再跑缺省参数(不传 jump)确认 true 路径不变:

```bash
py -3 gen_dem_arxml/Dem_arxml_Script.py <同上 excel> <临时 arxml> 2>&1 | tail -1
grep -A1 "DemDebounceCounterJumpDown</DEFINITION-REF>" /tmp/J6B_test.arxml | grep -c "<VALUE>true</VALUE>"
```

清理: `rm /tmp/J6B_test.arxml`

- [ ] **Step 5: py_compile + 提交**

```bash
py -3 -m py_compile gen_dem_arxml/Create_DemDebounceCounterBasedClass.py gen_dem_arxml/Dem_arxml_Script.py gen_map_yaml/gen_map_yaml.py
git add gen_dem_arxml/Create_DemDebounceCounterBasedClass.py gen_dem_arxml/Dem_arxml_Script.py configs/ gen_map_yaml/
git commit -m "feat: add jumpdown/jumpup params, configs, gen_map_yaml port"
```

---

### Task 2: gen_evm_fimfid 改名 + dem_autogen_etas.py 配置化改造

**Files:**
- Rename: `gen_evm_fimfid/` → `gen_fim_code/`;`gen_evm_fimfid.py` → `gen_fim_code.py`
- Modify: `gen_fim_code/gen_fim_code.py`(仅 docstring 用法行)
- Modify: `dem_autogen_etas.py`(docstring、常量、新增配置加载、main 重构)

- [ ] **Step 1: git mv 改名**

```bash
git mv gen_evm_fimfid gen_fim_code
git mv gen_fim_code/gen_evm_fimfid.py gen_fim_code/gen_fim_code.py
```

`gen_fim_code/gen_fim_code.py` docstring 中的用法行 `python gen_evm_fimfid.py ...` 改为 `python gen_fim_code.py ...`(其余不动;Merge_ExcelSheets.py/TemplateFile.py/template/ReadMe.txt 原样)。

- [ ] **Step 2: dem_autogen_etas.py — 常量与 docstring**

docstring 流程段改为:

```python
"""dem_autogen_etas - ETAS Dem 自动生成工具 (一键流程).

流程 (按 configs/*.yaml 深合并配置启停, 详见 specs/2026-09-19-dem-autogen-etas-feature-config-design.md):
  check_dtc_table  校验 DTC 表            (脚本尚未引入, 开启即报错)
  gen_dem_table    gen_dem_arxml + 紧接 BSW 代码生成 (ISOLAR headless, 失败降级 Cobra)
                  二级配置 jumpdown/jumpup 控制 DemDebounceCounterJumpDown/JumpUp
  gen_event_ctrl   生成 Dem_PrjSpecificControl.c
  gen_fim_code     生成 evm_cfg 3 个文件 (FidCfg.hpp / iSysFidCfg.cpp / zx fimcfg.hpp)
  gen_map_yaml     生成 dtc_map.yaml / event_map.yaml 到 Excel 同目录

用法:
  python dem_autogen_etas.py <IDC_EVM_Config*.xlsx> --repo <mcu_app_j6路径> --project rx
"""
```

import 增加 `import yaml`;常量区改为:

```python
DEM_ARXML_SCRIPT = GEN_TOOLS / "gen_dem_arxml" / "Dem_arxml_Script.py"
EVENT_CTRL_SCRIPT = GEN_TOOLS / "gen_event_ctrl" / "Gen_EventAvailable_Control_Script.py"
FIMFID_SCRIPT = GEN_TOOLS / "gen_fim_code" / "gen_fim_code.py"
MAP_YAML_SCRIPT = GEN_TOOLS / "gen_map_yaml" / "gen_map_yaml.py"
CONFIGS_DIR = GEN_TOOLS / "configs"

FEATURES = ("check_dtc_table", "gen_dem_table", "gen_event_ctrl",
            "gen_fim_code", "gen_map_yaml")
```

- [ ] **Step 3: dem_autogen_etas.py — 配置加载函数**

插在 `fail()` 之后:

```python
def deep_merge(base: dict, override: dict) -> dict:
    """dict 递归合并, 标量直接覆盖 (override 优先)."""
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_feature_config(project: str):
    """读 configs/common.yaml + configs/<project>.yaml 深合并, 返回 (cfg, 来源名)."""
    common_path = CONFIGS_DIR / "common.yaml"
    if not common_path.is_file():
        fail("缺少 %s" % common_path)
    cfg = yaml.safe_load(common_path.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict) or any(k not in cfg for k in FEATURES):
        fail("%s 必须包含全部功能键: %s" % (common_path, ", ".join(FEATURES)))
    source = "common"
    proj_path = CONFIGS_DIR / ("%s.yaml" % project)
    if proj_path.is_file():
        override = yaml.safe_load(proj_path.read_text(encoding="utf-8"))
        if not isinstance(override, dict):
            fail("%s 内容必须是映射" % proj_path)
        cfg = deep_merge(cfg, override)
        source = project
    unknown = [k for k in cfg if k not in FEATURES]
    if unknown:
        fail("配置含未知键: %s (允许: %s)"
             % (", ".join(sorted(unknown)), ", ".join(FEATURES)))
    for k in FEATURES:
        v = cfg[k]
        if k == "gen_dem_table":
            if not isinstance(v, dict) or not isinstance(v.get("enabled"), bool):
                fail("gen_dem_table 必须是含 enabled 布尔键的映射")
            for j in ("jumpdown", "jumpup"):
                val = v.get(j, False)
                if not isinstance(val, bool):
                    fail("gen_dem_table.%s 必须是布尔" % j)
                v[j] = val
        elif not isinstance(v, bool):
            fail("%s 必须是布尔" % k)
    return cfg, source
```

- [ ] **Step 4: dem_autogen_etas.py — main() 重构**

argparse 删除 `--skip-gen`;参数解析后加载配置:

```python
    cfg, cfg_source = load_feature_config(args.project)
```

存在性检查改为按启用功能(替换原"FIMFID_SCRIPT 等 3 个脚本"检查与 fimfid 目录 mkdir):

```python
    feat_on = {
        "gen_dem_table": cfg["gen_dem_table"]["enabled"],
        "gen_event_ctrl": cfg["gen_event_ctrl"],
        "gen_fim_code": cfg["gen_fim_code"],
        "gen_map_yaml": cfg["gen_map_yaml"],
    }
    needed_scripts = {
        "gen_dem_table": DEM_ARXML_SCRIPT,
        "gen_event_ctrl": EVENT_CTRL_SCRIPT,
        "gen_fim_code": FIMFID_SCRIPT,
        "gen_map_yaml": MAP_YAML_SCRIPT,
    }
    for feat, script in needed_scripts.items():
        if feat_on[feat] and not script.is_file():
            fail("脚本不存在: %s" % script)
    enabled = [k for k in FEATURES
               if (feat_on.get(k, False) if k != "check_dtc_table" else cfg[k])]
    total = len(enabled)
    step_titles = {name: "Step %d/%d %s" % (i + 1, total, name)
                   for i, name in enumerate(enabled)}
```

横幅(替换原 Excel/仓库/车型/BswRta/arxml 打印块,追加两行):

```python
    print("[dem_autogen_etas] 配置      : %s (%s)" % (CONFIGS_DIR, cfg_source))
    print("[dem_autogen_etas] 启用功能  : %s"
          % (" -> ".join(enabled) if enabled else "无"))
```

主流程(替换原 Step 1-4 全部,含 skip-gen 分支、尾部 BSW 块;Step 1 兜底逻辑原样保留;`dem_ctrl_out` 存在性检查移入 gen_event_ctrl 分支;fimfid 目录 mkdir 移入 gen_fim_code 分支):

```python
    if cfg["check_dtc_table"]:
        fail("check_dtc_table 脚本尚未引入")

    if feat_on["gen_dem_table"]:
        gd = cfg["gen_dem_table"]
        step1_t0 = time.time()
        run_step("%s 生成 Dem ARXML (jumpdown=%s, jumpup=%s)"
                 % (step_titles["gen_dem_table"], gd["jumpdown"], gd["jumpup"]),
                 [sys.executable, str(DEM_ARXML_SCRIPT), str(excel), str(paths.arxml),
                  str(gd["jumpdown"]).lower(), str(gd["jumpup"]).lower()],
                 cwd=DEM_ARXML_SCRIPT.parent)
        # 子脚本 insert_* 失败时仅打印且 exit 0; 且 Delete_DemConfigSet 会先无条件重写
        # arxml, mtime 恒新, 故再以容器级 DEF 锚点做内容兜底 (插入失败 = 锚点缺失)
        if paths.arxml.stat().st_mtime < step1_t0 - 1:
            fail("gen_dem_table 声称成功但 arxml 未被重写: %s (子脚本静默失败?)" % paths.arxml)
        arxml_text = paths.arxml.read_text(encoding="utf-8", errors="replace")
        for anchor in ("Dem/DemConfigSet/DemEventParameter</DEFINITION-REF>",
                       "Dem/DemConfigSet/DemDTC</DEFINITION-REF>"):
            if arxml_text.count(anchor) < 1:
                fail("gen_dem_table 后 arxml 缺少 %s 容器 (子脚本 insert 静默失败?): %s"
                     % (anchor.split("/")[-1].split("<")[0], paths.arxml))

        rta_home = Path(os.environ.get("RTA_CAR_HOME", str(RTA_CAR_HOME_DEFAULT)))
        isolar_dir = find_isolar_b(rta_home)
        if isolar_dir is None:
            fail("ISOLAR-AB.cmd 未找到 (RTA_CAR_HOME=%s)" % rta_home)
        isolar_cmd = isolar_cmd_path(isolar_dir)
        print("[dem_autogen_etas] ISOLAR    : %s" % isolar_cmd)
        ok = gen_bsw_headless(paths, isolar_cmd)
        if not ok:
            print("[dem_autogen_etas] headless 失败, 降级 Cobra.exe ...")
            ok = gen_bsw_cobra(paths, isolar_dir)
        if not ok:
            fail("BSW 生成失败, 详见 %s 及 %s 目录下日志"
                 % (paths.confgen_log, paths.bswrta / "_log"))

    if feat_on["gen_event_ctrl"]:
        if not paths.dem_ctrl_out.is_dir():
            fail("Dem Ctrl 输出目录不存在: %s" % paths.dem_ctrl_out)
        run_step("%s 生成 Dem Ctrl C (Dem_PrjSpecificControl.c)"
                 % step_titles["gen_event_ctrl"],
                 [sys.executable, str(EVENT_CTRL_SCRIPT), str(excel), str(paths.dem_ctrl_out)],
                 cwd=EVENT_CTRL_SCRIPT.parent)

    if feat_on["gen_fim_code"]:
        paths.fimfid_cpp_out.mkdir(parents=True, exist_ok=True)
        paths.fimfid_h_out.mkdir(parents=True, exist_ok=True)
        run_step("%s 生成 EVM FiMFID (3 个文件)" % step_titles["gen_fim_code"],
                 [sys.executable, str(FIMFID_SCRIPT), str(excel),
                  str(paths.fimfid_cpp_out), str(paths.fimfid_h_out)],
                 cwd=FIMFID_SCRIPT.parent)

    if feat_on["gen_map_yaml"]:
        run_step("%s 生成 map 表 (dtc_map/event_map.yaml)" % step_titles["gen_map_yaml"],
                 [sys.executable, str(MAP_YAML_SCRIPT), str(paths.bswrta), str(excel.parent)],
                 cwd=MAP_YAML_SCRIPT.parent)

    print("[dem_autogen_etas] 全部完成")
```

注:原 main() 里 `paths.arxml.is_file()` 检查删除(resolve_repo_paths 的 glob 本就要求恰好 1 个现存文件,冗余);`gen_bsw_headless`/`gen_bsw_cobra`/`run_step`/`find_isolar_b`/`isolar_cmd_path`/`resolve_repo_paths`/`parse_confgen_errors`/`confgen_log_fresh`/`output_has_failure_marker`/`fail` 全部不动。

- [ ] **Step 5: 验证(只读, 不跑生成)**

```bash
py -3 -m py_compile dem_autogen_etas.py gen_fim_code/gen_fim_code.py
py -3 dem_autogen_etas.py --help        # 无 --skip-gen, 各参数说明正确
py -3 dem_autogen_etas.py x.xlsx --repo r --project rx   # 路径推导报错先于一切(Excel 不存在)
py -3 - <<'EOF'
import importlib.util
spec = importlib.util.spec_from_file_location("m", "dem_autogen_etas.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
# rx.yaml 深合并: enabled false, jump true/true, 其余继承 common
cfg, src = m.load_feature_config("rx")
assert cfg["gen_dem_table"] == {"enabled": False, "jumpdown": True, "jumpup": True}
assert cfg["gen_fim_code"] is True and cfg["gen_map_yaml"] is True
assert cfg["gen_event_ctrl"] is False and cfg["check_dtc_table"] is False
assert src == "rx"
# 无项目 yaml -> 纯 common
cfg2, src2 = m.load_feature_config("t09")
assert src2 == "common" and cfg2["gen_dem_table"]["enabled"] is True
assert cfg2["gen_dem_table"]["jumpdown"] is False
# deep_merge 覆盖语义
assert m.deep_merge({"a": 1, "n": {"x": 1}}, {"n": {"y": 2}}) == {"a": 1, "n": {"x": 1, "y": 2}}
print("config checks OK")
EOF
```

错误路径(临时目录伪造 configs, monkeypatch CONFIGS_DIR)各跑一次确认 exit 1:未知键、common 缺键、gen_dem_table 非 dict、标量功能给了字符串。

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "feat: feature-config orchestrator, rename gen_evm_fimfid to gen_fim_code"
```

---

### Task 3: 收尾验证(含真机半程回归)

- [ ] **Step 1: 全量 py_compile + git status**

```bash
py -3 -m py_compile dem_autogen_etas.py gen_dem_arxml/*.py gen_event_ctrl/*.py gen_fim_code/*.py gen_map_yaml/*.py
git status --short   # 应干净
```

- [ ] **Step 2: 真机半程回归(rx 配置: 只跑 fim + map)**

```bash
py -3 dem_autogen_etas.py "D:\Workspace\01_Projects\02_Src\02_Workspace_J6\src\mcu_app_j6\cpj_cmc\tools\rx\e2e_dem\IDC_EVM_Config_CMC_RX_V2.0_20260823.xlsx" --repo "D:\Workspace\01_Projects\02_Src\02_Workspace_J6\src\mcu_app_j6" --project rx
```

期望:输出 `配置 (rx)`、`启用功能: gen_fim_code -> gen_map_yaml`、`Step 1/2 gen_fim_code OK`、`Step 2/2 gen_map_yaml OK`、`全部完成`,总耗时 <1 分钟(无 BSW 生成)。

产物核验:

```bash
E="/d/Workspace/01_Projects/02_Src/02_Workspace_J6/src/mcu_app_j6/cpj_cmc/tools/rx/e2e_dem"
ls -la "$E"/dtc_map.yaml "$E"/event_map.yaml
grep -c "0x" "$E/dtc_map.yaml"        # 75
grep -c "^[0-9]" "$E/event_map.yaml"  # 603
grep "0x658647" "$E/dtc_map.yaml"     # 存在 (DemDtcValue 6653511)
```

evm_cfg 三文件 mtime 为本次运行时间(内容此前已验证过与旧输出一致)。

- [ ] **Step 3: 提交计划文档 + 用户端验证**

```bash
git add docs/superpowers/plans/2026-09-19-dem-autogen-etas-feature-config.md
git commit -m "docs: add feature-config implementation plan"
```

完整流程(gen_dem_table enabled: true 的 jumpdown=false 路径 + BSW 生成)由用户决定何时真机验证——临时把 `configs/rx.yaml` 的 `gen_dem_table.enabled` 改 true 或删掉该键(继承 common)即可。

---

## Self-Review 结果

1. **Spec 覆盖**:§1 CLI 删 --skip-gen(Task 2 Step 4)、§2 五功能与顺序(Task 2 Step 4 主流程)、§3 配置深合并与校验(Task 1 Step 3 + Task 2 Step 3)、§4 jump 传递链(Task 1 Step 1/2)、§5 目录变更(Task 2 Step 1 + Task 1 Step 3)、§6 行为细节(Task 2 Step 4,check_dtc_table 占位报错/横幅/BSW 移位)、§7 验证(各 Task Step + Task 3)、§8 不做的事(无对应代码,确认未越界)——全覆盖。
2. **占位符扫描**:无 TBD/TODO;所有代码步骤含完整代码。
3. **类型/命名一致性**:`load_feature_config` 返回 `(cfg, source)` 与调用一致;`feat_on`/`step_titles`/`needed_scripts` 定义与使用一致;`FIMFID_SCRIPT` 新路径与 Task 2 Step 1 改名一致;`MAP_YAML_SCRIPT` 与 Task 1 Step 3 拷贝路径一致;`gen_fim_code.py` 内部 import(Merge_ExcelSheets 等)不受改名影响。
