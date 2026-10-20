# 验证方法（Validation Methods）

验证环节的统一入口。诊断类验证用 DiagnosticTester 自动跑用例；日志采集用 LogCollection；后续新增验证方法一律补充到本文档，其他地方只指向这里。

## 诊断功能验证 — DiagnosticTester

适用：UDS 诊断服务（0x10/0x27/0x2E/0x19/0x22 等会话、安全访问、DID/RID/DTC）的功能验证与问题复现。

**两步：编写 testcase → 运行验证。**

### 1. 编写 testcase

- 路径：`tools/DiagnosticTester/testcase/<项目>/<用例名>/<用例名>.yaml`
- 写法见 `tools/DiagnosticTester/README.md`（steps / on_fail / timing 三节）
- 用例设计要点：
  - 按**复现步骤原样翻译**成 yaml steps（ precondition 会话切换 → 目标操作 → 断言期望响应）
  - 时序要求写在 timing 节（如 0x37 延迟验证的等待 11s）
  - on_fail 记录失败时的取证动作（读 DID、抓响应原报文）
- 问题单验证建议同时在 `tests/harness/<模块>_<描述>/testcases/` 留一份（问题专属 harness，取证可追溯）

### 2. 运行验证

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/DiagnosticTester
python DiagnosticTester.py run testcase/<项目>/<用例>/<用例>.yaml --config configs/<项目>/<配置>.yaml
```

- **CAN 卡选择优先级：先用 CX（创芯 CX-USBCANFD，`_cx` 配置），CX 不可用时再用 ZLG（周立功，`_zlg` 配置）**；两种卡的 SDK/DLL 均已随仓库内置（`vendor/`）
- `--config` 切项目（CAN 通道、波特率、寻址方式、security 算法等项目参数在 config 里）
- 退出码：0 全 PASS / 1 有 FAIL/TIMEOUT / 2 配置错 / 3 运行期异常
- 也可经测试桩转发：`tests/harness/diag_test/run_case.py --testcase case_example.yaml --config ../../tools/DiagnosticTester/configs/<项目>/<配置>.yaml`

## MCU 日志采集 — LogCollection

适用：板子在跑时拉取 MCU 侧日志（/log/mcu），用于问题取证、插桩输出确认。

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/LogCollection
python collect_j6b.py --port <A核串口> --project <项目> [--host 192.168.1.239] [--dry-run]
```

- 前提：A 核串口 + 板子 SSH 可达；流程：串口登录执行 `pfctl -d` 使能 SSH → SFTP 拉 /log/mcu
- 落盘：`tools/LogCollection/logs/<项目>/mcu_<时间戳>/`，逐文件大小校验
- 实时调试串口采集（插桩日志）：`tests/harness/mcu_log/capture_com68.py [baud]`（R 核口按串口识别规则现查，见 [serial-port-identification.md](serial-port-identification.md)）
- 串口识别规则：[serial-port-identification.md](serial-port-identification.md)

## 电源操作（验证配套）

验证前后需要操作电源时（程控电源 KA3005P，COM 号漂移需现查）：

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/PowerControl
python power_control.py --port <COM> cycle   # 验证前重启电源
python power_control.py --port <COM> off     # 验证后关闭电源
```

## 后续验证方法（待补充）

新的验证方法（如 CAN 报文回放、MCAP 日志解码、HIL 自动化等）验证一项、补充一节到本文档，其他文档只加指向本文档的链接。
