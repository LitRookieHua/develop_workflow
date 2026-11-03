# DiagnosticTester 新增 PySide6 UI 界面

日期：2026-11-03
状态：已确认

## 背景与目标

DiagnosticTester 目前只有 CLI 入口（run/chat/probe/unlock/dem/dem-map）。日常调试
需要更顺手的工作台：免敲命令选配置、点按钮跑例程、单发调试、会话保持。目标：
新增 PySide6 GUI 入口，**完全复用现有底层模块**（flow/isotp/uds/security/can_driver/
recorder 零改动或近零改动），CLI 行为不变。

需求范围（用户确认）：

1. 兼容原始 python 脚本执行功能：CLI 保留，UI 与其共享同一份底层模块
2. 选择配置（设备+项目合一：选一个 config yaml）、选择例程（testcase yaml）、
   Log 界面、会话保持（功能寻址周期发 3E80）
3. 单发模式（TX/RX），含 0x27 安全解锁（类 chat）
4. 开发流程：tools/ 下新文件夹 + 新分支开发，完成后合并进 DiagnosticTester/

## 1. 总体架构与开发/合并流程

```
开发期（分支 feature/dt-ui）：
tools/dt_ui/                    # 临时开发目录
├── DiagnosticTesterUI.py       # UI 入口
├── ui/
│   ├── main_window.py          # 主窗口（工具条+Tab+日志面板）
│   ├── session.py              # 连接会话管理（driver→recorder→transport→uds）
│   └── workers.py              # QThread 会话 worker
└── tests/…                     # UI 新增测试
    # sys.path 注入 ../DiagnosticTester 复用底层模块

合并期（合入 master）：
tools/DiagnosticTester/
├── DiagnosticTester.py         # CLI 入口（不动）
├── DiagnosticTesterUI.py       # UI 入口（从 dt_ui 移入）
├── ui/…                        # 从 dt_ui 移入
└── requirements.txt            # 增加 PySide6
    # dt_ui/ 目录删除；README 增 UI 章节
```

- UI 技术栈：PySide6（LGPL，pip 安装）；Python 64 位（与 CX 卡绑定一致）
- 界面语言：中文

## 2. 线程模型

| 线程 | 职责 |
| --- | --- |
| Qt 主线程 | 界面事件、3E80 会话保持 QTimer |
| pump 接收线程（现有 IsoTpTransport） | 帧接收/重组/FC |
| 会话 worker（QThread，单个） | 串行执行例程运行/单发/解锁，同一时刻仅一个请求在途 |

- 3E80 由主线程 QTimer **直接 driver.send**（绕过 IsoTpTransport，不触碰其收发
  状态机——与 flow.py 功能寻址 no-expect 步骤同款路径）；驱动 `_tx_lock` 保证与
  pump 线程 FC 发送互斥
- worker 线程结果/日志经 Qt signal 回主线程，无跨线程直接操作控件
- 例程运行期间单发/解锁控件禁用（避免与 run_flow 并发争用同一 transport）

## 3. 界面结构（布局方案 C：顶部工具条 + 双 Tab + 底部共享日志）

```
┌────────────────────────────────────────────────────────┐
│ 工具条：配置下拉▾ | 连接/断开 | 状态● | 3E80开关 | 周期ms │
├────────────────────────────────────────────────────────┤
│ Tab: [例程运行] [单发调试]                                │
│ ┌──────────────────────────────────────────────────┐   │
│ │ （Tab 内容，独占中部空间）                          │   │
│ └──────────────────────────────────────────────────┘   │
├────────────────────────────────────────────────────────┤
│ Log 面板（两 Tab 共享，只读等宽，[时间戳] 前缀，自动滚动） │
├────────────────────────────────────────────────────────┤
│ 状态栏：状态 | 本次会话落盘目录                           │
└────────────────────────────────────────────────────────┘
```

- **工具条**：配置下拉扫 `configs/` 全部 yaml（含子目录，显示 `n60/n60_cx` 相对
  路径）；连接/断开按钮；连接状态（设备名+通道）；3E80 开关 + 周期 spinbox
  （500–50000，默认 2500）
- **例程运行 Tab**：例程树（根目录 `<DiagnosticTester>/testcase/`，与 CLI 默认
  用法一致；工具条提供「浏览」可选任意目录或单个 yaml 文件兜底），按当前配置
  项目名过滤显示 `testcase/<项目>/` + 刷新 +
  运行 + 停止 + 结果汇总（PASS/FAIL/TIMEOUT、当前步骤、run_dir 路径）+
  「打开运行目录」（explorer）
- **单发调试 Tab**：TX hex 输入 + 发送（Enter 触发）+ 解锁等级下拉（配置
  security 节 + 内置 develop）+ 解锁按钮 + 收发历史表（时间/TX/RX/NRC/耗时，
  双击回填 TX）
- **Log 面板**：QPlainTextEdit，行格式与 run.log 一致；暂停自动滚动 / 清空按钮

## 4. 功能行为

### 连接会话

点连接 → `load_config` → `make_driver` → `build_transport` → `UdsClient` +
`Recorder`（落盘 `logs/<项目>_ui_<时间戳>/`，三路记录保证据链）；断开按
transport.stop → recorder.close → driver.close 逆序收尾。切换配置必须先断开。

### 例程运行

- worker 线程调 `run_flow`；run_dir 规则与 CLI `run` 一致：
  `<用例目录>/../logs/<用例名>/<时间戳>/`
- 事件流经 log_hook 实时进 UI Log 面板（同时照常落盘）
- 停止按钮置位 threading.Event，`run_flow` 每步开始前检查，当前步完成后中止
  （不强杀线程）；已执行步骤计数照常汇总

### 单发

- `parse_hex_bytes` 校验（非法输入状态提示不清历史）
- worker 线程 `uds.request`；响应 hex/NRC/耗时进历史表 + 日志
- 请求异常（IsoTpError/TimeoutError 等）：日志 + 历史表标红，会话不断
- 解锁：`perform_unlock` 全序列，种子/密钥/结果进日志

### 会话保持（3E80）

- 帧：`encode(b"\x3e\x80", is_fd)` 的 SF 帧发 functional_id（0x80 抑制正响应，
  不等待）
- 周期可调默认 2500ms；仅连接后可开，断开自动停
- 配置无 `functional_id` 时开关禁用并提示
- 每次发送记一行日志

## 5. 对现有代码的改动

仅 `flow.py` 的 `run_flow` 新增两个可选参数（缺省行为与现状完全一致，CLI 零影响）：

- `log_hook=None`：每次事件（rec.event 时机）同步回调，供 UI tee 日志流
- `should_stop=None`：每步开始前调用，返回 True 则中止流程并照常汇总

其余模块（isotp/uds/security/dem/can_driver/recorder/DiagnosticTester.py）零改动。

## 6. 错误处理

| 场景 | 处理 |
| --- | --- |
| 配置加载/驱动打开失败 | 状态栏红字 + 弹窗，回退未连接态 |
| pump 线程异常（transport.pump_error） | 状态栏告警，程序不退出 |
| 单发/解锁失败 | 日志 + 历史表标红，会话保持 |
| 3E80 发送异常（驱动故障） | 日志告警，开关自动复位 |
| 关窗时例程在跑 | 先请求停止（2s 超时）再退出；Recorder with 语义保证已收记录落盘 |

## 7. 测试

- pytest（复用 mock_driver，不起 Qt 事件循环的纯逻辑单测）：
  - 配置扫描（configs/ 相对路径列表）
  - 3E80 帧构造（SF/补齐/FD 两种模式）
  - `run_flow` 新参数：log_hook 收到事件序列；should_stop 在步间中止
  - 例程树扫描
- UI 冒烟（手动验收清单）：`configs/example_mock.yaml` 走通
  连接 → 3E80 开启 → 例程运行 → 停止 → 单发 → 解锁 develop → 断开
- 现有 tests/ 全部保持绿

## 8. 非目标（本次不做）

- dem / dem-map 的 UI 化（CLI 保留可用）
- 多 ECU 并行会话、GUI 里的用例编辑器
- 打包成 exe（直接 python 启动）
