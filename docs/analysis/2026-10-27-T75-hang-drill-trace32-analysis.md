# T75 挂死问题分析演练报告（CPU abort / 任务死循环 / 栈溢出三场景）

| 文档基础属性 | 内容说明 | 分析与合规属性 | 内容说明 |
| :--- | :--- | :--- | :--- |
| **问题单号** | DRILL-T75-HANG（技术演练，无 JIRA 单） | **分析结论** | 🟢 演练完成（三场景证据链闭环） |
| **问题主题** | 挂死问题 TRACE32 排查方法论演练 | **缺陷类型** | 其他（fault injection 演练） |
| **分析人 / 日期** | @Hua.Yao / `2026-10-27` | **严重等级** | 不适用 |
| **项目 / 变体** | T75（GAC，D084） | **优先级** | 不适用 |
| **发现阶段** | 台架演练 | **分析状态** | ⚪ 已关闭（演练性质） |
| **根因分类** | 不适用（注入式演练） | **关联输出** | 本地分支 `debug/t75-hang-drill`（未 push，场景 4-6 复用） |

> **📝 变更记录**
> * `2026-10-27`｜@Hua.Yao｜V1.0｜初版：三场景注入、TRACE32 取证、判据表

---

## 一、 演练概述

### 1.1 目的

以 T75 项目为载体，通过**故障注入 + 编译刷板 + TRACE32 实测**，演练三类高频挂死形态（CPU abort / 任务死循环 / 栈溢出）的完整排查链路，沉淀判据表与实战流程，供真实问题单排查时快速召回。

### 1.2 注入与触发机制

| 项 | 值 |
| :--- | :--- |
| 注入点 | `cpj_gac/os_cfg/t75/src/os_cfg_core0.c` `TASK(Core0_OsTask_BSW_1000ms)` 任务体首行调 `hang_drill_hook()` |
| 注入代码 | `cpj_gac/os_cfg/t75/src/hang_drill.c` + `inc/hang_drill.h`（本地 debug 分支 commit `961faf0b7`） |
| 选择器 | `g_hang_drill_fault`（BSS @ `0x3FF283A4`），TRACE32 运行时 `Data.SET` 切换 |
| 故障类型 | 0=正常（默认）；1=数据 abort（写未对齐地址 0x3）；2=任务死循环（volatile while）；3=栈溢出（无界递归）；**4=只关看门狗不注故障**（现场保活用） |
| 看门狗保活 | selector≠0 时 hook 内调 `Pmic_Lld_SetWdgConfig(0, cfg{ConfMode=0})` 门控关 PMIC wdt——**否则停机/关机后 1s 内整板复位，现场被洗掉** |
| 递归防优化 | 递归函数返回值引用局部 `pad[0]`（递归后引用）——**尾递归会被 GCC 优化成循环，栈不涨，注入失败**（实测踩坑） |

### 1.3 环境矩阵

| 项 | 版本/值 |
| :--- | :--- |
| 固件基线 | `mcu_app_j6@develop@41a69fde3`（V2 工作区，本地 debug 分支叠加注入） |
| build_product / preset | `Gac/T75_D084/develop` / `t75-gcc-dev` → `build/cpj_gac_t75_d310/rpu_arm_gcc` |
| 硬件 | J6B MCU EVM PLUS（A核串口 COM33=SERIAL-C，R核 COM32，电源 KA3005P COM44） |
| 工具 | TRACE32 attach（RCL 23456，ELF 一致性校验通过）；DiagnosticTester（CX 卡，t75_cx.yaml）；ProgramBoard（t75_mcu.json） |
| 黑盒用例 | `testcase/t75/probe_0100_0104`（读 F195/0100/0104 三 DID） |

---

## 二、 三场景实测记录

### 2.1 场景 1：CPU abort（写未对齐地址 0x3）

**触发**：`Data.SET D:0x3FF283A4 %Word 1` → 1s 内 1000ms 任务撞 `STR R3,[R2,#3]`。

**排查链（hang_diag → hang_scene → hang_pin）实测输出要点**：

| 步骤 | 实测结果 | 推论 |
| :--- | :--- | :--- |
| hang_diag（逐核 PC/CPSR） | 核0 SYS 模式，**SPSR_ABT=0x6000011F≠0**；核1 干净 | 出过 abort（OS 善后已切回 SYS，CPSR 看不出）；问题隔离在核0；出事前模式 SYS=任务上下文 |
| hang_scene（定性） | PC 卡 `Os_ShutdownOS` 自旋（`B .` 0xEAFFFFFD）；R14_ABT=0x4014A7D0 | OS 主动保护关机，非 CPU 当场卡死 |
| hang_pin（定位） | 出错指令 0x4014A7C8 = `STR R3,[R2,#3]` @ **hang_drill.c:52**；前序 `MOV R2,#0`+`MOVW R3,#0xDEAD` | 坏地址=0+3=3；未对齐写 → DFSC 0x21 |
| 断 ProtectionHook（可复现增强） | 命中后 **R0=14** | 查 Os.h：`E_OS_PROTECTION_MEMORY`=14，MPU 内存保护违例 |
| 黑盒探针 | **3/3 TIMEOUT** | 整机离线，OS 关机自旋 |

**完整因果链**：

```
写 0x3（未对齐+无 MPU region）→ Data Abort（DFSC 0x21，WnR=1）
  → RTA-OS 异常接管，核切回 SYS → ProtectionHook(R0=14)
  → Os_ShutdownOS 自旋 → 50ms 喂狗闹钟停 → PMIC wdt 1s 复位（"挂了又活"）
```

**看门狗级联教训（第一轮实测踩坑）**：未关 wdt 时，注入后探针 3/3 PASS——板子已被 wdt 复位重启、现场全丢，TRACE32 报 `target system down`。**abort 类挂死的窗口期 = wdt 超时前**，必须在复位前抢抓，或预先门控关狗。

### 2.2 场景 2：任务死循环（1000ms 任务内 while(1)）

**触发**：selector=2。

| 步骤 | 实测结果 | 推论 |
| :--- | :--- | :--- |
| hang_diag | SYS 模式、**SPSR_ABT=0（未出 abort）** | **与场景 1 的一票鉴别点**：纯软件死循环 |
| PC 定位 | PC @ hang_drill.c:58 while 循环 | 用户代码内死循环，非 OS/异常 |
| 活任务地图（Task_Counter_au32 对照 5s） | **仅 BSW_1000ms 计数 FROZEN**；1ms +4983 / 5ms +997 / 50ms +100 照跑 | 秒级锁定挂死任务；调度器仍活着 |
| 黑盒探针 | **3/3 PASS** | **"部分挂死"**：诊断通道（Dcm/CanTp/CanIf）活着，仅该任务周期功能全停。**ECU 能应答诊断 ≠ 没挂死** |
| 在线救活 | TRACE32 清 selector→0，循环退出，任务恢复（计数 183→187） | 无需复位即可恢复，取证后可在线修复验证 |

### 2.3 场景 3：栈溢出（无界递归）

**触发**：selector=3（第二版注入，防尾调用优化）。

| 步骤 | 实测结果 | 推论 |
| :--- | :--- | :--- |
| 第一版注入失败 | PC @ hang_drill.c:33，SP 不动 | **尾递归被 GCC 优化成循环，栈没涨**——注入栈溢出必须防尾调用消除 |
| hang_diag | SYS + SPSR_ABT≠0；**PC 与 R14_ABT 都在 `Os_ProtectionLog`** | 不是任务栈现场的直接 abort，是 OS 善后路径里的嵌套 abort |
| hang_pin | 出错指令 = `PUSH {r4-r8,lr}`（ProtectionSupport.c:1534 函数序言，机器码 0xE92D41F0）；SP=0x3FEABD90 **低于 abort 栈基 0x3FEAC100** | **abort 栈自己被打穿**：递归先穿任务栈 → abort → OS 异常处理在小 abort 栈上跑 → 又穿 → 嵌套 abort 故障循环 |
| ProtectionHook 断点 | **15s 不命中** | 嵌套 abort 循环里 ProtectionHook 永远到不了——**断点不命中 ≠ 没有保护违例** |
| OS 栈水位（TASK.DTASK） | BSW_1000ms RUNNING，峰值 904B（基线 576B）；实际递归深度 SP 推算 ~15KB | **水位只在调度点采样，任务 fault 在周期内则远低于真实深度**——水位正常 ≠ 没溢出 |
| 黑盒探针 | 3/3 TIMEOUT | 整机离线（故障循环） |

---

## 三、 三场景判据速查表（核心沉淀）

| 判据 | CPU abort | 任务死循环 | 栈溢出（级联） |
| :--- | :--- | :--- | :--- |
| SPSR_ABT | ≠0 | **=0** | ≠0 |
| PC 位置 | `Os_ShutdownOS` 自旋 | 用户代码循环 | `Os_ProtectionLog`（嵌套 abort 循环） |
| R14_ABT 指向 | 出错指令（用户代码） | — | OS 善后代码（PUSH 序言） |
| ProtectionHook R0 | 14 = E_OS_PROTECTION_MEMORY | 不到（没违例） | **到不了**（abort 栈先穿） |
| 任务计数 | 全停（OS 关机） | **仅挂死任务冻结** | 全停（故障循环） |
| 诊断应答 | 无 | **可能正常** | 无 |
| 现场保活 | 需关 wdt（1s 复位） | 天然稳定 | 需关 wdt |

## 四、 排查方法论（流程沉淀）

**标准顺序**（对应脚本链）：

1. **保现场**：TRACE32 attach（不 reset 不 break）；确认 `ELF 与固件一致`（不一致则符号/栈全不可信）
2. **黑盒分型**：诊断探针 → 全超时 = CPU/OS 级；应答正常但功能停 = 任务级（部分挂死）
3. **逐核 PC/CPSR**（hang_diag.py）：SPSR_ABT≠0 = 出过 abort（第一判据）；SPSR_ABT=0 且 PC 在用户代码 = 死循环方向
4. **定性**（hang_scene.py）：PC 在 `Os_ShutdownOS` = OS 保护关机；栈回溯见 `Os_ProtectionLog←Os_ShutdownOS` 链同
5. **定位**（hang_pin.py）：出错指令 = R14_ABT−8（数据）/−4（取指）；反汇编 + 前序指令还原坏指针；`sYmbol.SOURCEFILE/LINE` 到源码行
6. **定性增强**（可复现时）：断 `ProtectionHook` 读 R0（违例 StatusType：13=STACKFAULT / 14=MEMORY / 18=EXCEPTION）

**寄存器分工**（排查时各回答一个问题）：

| 寄存器 | 回答 |
| :--- | :--- |
| CPSR | 现在什么模式（注意 SYS 是 OS 善后常态，不能排除 abort） |
| SPSR_ABT | 出过 abort 吗；出事前什么模式（M[4:0]） |
| R14_ABT | 哪条指令出的事（−8/−4 算术） |
| DFSR/DFAR | 什么类型故障（DFSC 码）+ 挂在哪个地址（粘滞，事后可读） |
| ProtectionHook R0 | OS 认定什么违例 |

**DFSC 速查**：0x21 对齐错（指针算错）；0x0D/0x05 MPU 越权/背景区（常见栈溢出踩保护区）；0x10/0x08 总线超时/从设备挂死；0x18 ECC/RAM 损坏；bit11 WnR=1 为写。

**易错点清单**（实测全部踩过或验证过）：

- **看门狗洗现场**：关机自旋/断点停机 → 喂狗停 → PMIC wdt 复位。现场要在复位前抢抓；演练固件 selector=4 可只关狗不注故障（健康板手动 Break 前必用）
- **abort 栈不可信**：R13_ABT 指向区域多为链接器 FILL（0x4C4C4946）空栈，OS 保存的上下文不在那
- **RCL 读 DFSR/DFAR 可能读空**：SYS 模式下常态，用 GUI `PER.view , "Fault"` 或直接走 R14_ABT 反汇编
- **UI 里 banked 寄存器**：不在 PER.view 分组（那是 CP15）；用 `Register` 窗口切 Mode 到 Abort，或直接跑 hang_scene.py（RCL 多名回退）
- **编译器陷阱指令**：`MOV Rn,#0`+`STR Rn,[Rn]`=空指针写、`0xE7F000F0`=UDF 断言——确定性崩溃，别当野指针偶发查；出错指令前 `CMP #N` 的 N 常是业务阈值
- **OS 栈水位边界**：调度点采样，任务死在周期内则不更新（场景 3：904B vs 实际 15KB）

## 五、 演练产出与状态

| 项 | 状态 |
| :--- | :--- |
| 注入代码 | 本地 `debug/t75-hang-drill` 分支 commit `961faf0b7`（未 push；selector=0 时行为与基线一致） |
| `.imobuilder` | 已恢复 `Gac/T51_D088/develop` |
| 板子 | 在跑 drill 固件（selector=0，正常行为） |
| 场景 4-6（中断异常/通信栈挂死/看门狗复位） | 待做：同一 selector 机制加 case 4-6，注入点需现场探查（ISR 回调 / CanSM-ComM main function / WdgM 喂狗链） |
| 栈水位原始数据 | `.tmp/stack_baseline.txt`、`.tmp/stack_overflow.txt`（基线 vs 溢出对照） |

## 附录：可复用结论（下次检索入口）

* 检索关键词：`挂死` / `abort` / `SPSR_ABT` / `死循环` / `栈溢出` / `ShutdownOS` / `E_OS_PROTECTION_MEMORY` / `看门狗复位 现场丢失` / `hang_diag`
* 同类真实问题单排查：命中本篇 → 直接走 §四 排查顺序 + §三 判据表；abort 类优先抢 wdt 复位前的窗口
* TRACE32 脚本链：`hang_common.py`（寄存器多名回退/CPSR 解码）→ `hang_diag.py` → `hang_scene.py` → `hang_pin.py`（插件 `t32-plugin/references/python/`，连接信息复用 `.t32/connection.json`）
* KB 权威源：`kb/20-专题/Cortex-R52 死机与异常诊断.md`
