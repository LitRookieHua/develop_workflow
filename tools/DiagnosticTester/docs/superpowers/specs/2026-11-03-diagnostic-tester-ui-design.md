# DiagnosticTester 新增 PySide6 UI 界面

日期：2026-11-03
状态：已确认
修订：2026-11-03 增补六项——底部 Log 面板改为「日志/报文」双 Tab（原始 CAN 帧
视图，仅 diagnostic 三 ID）、例程运行期间挂起会话 transport（修复双 pump 抢帧
导致 UI 跑例程间歇超时的问题）、主窗口背景图与图标（`image/shenlilinghua.png`，
缺失自动降级）、中部 Tab 重组为「手动发送 / 固定例程 / 配置例程」三页（安全
解锁与读DTC 归入固定例程，新增会话切换）、布局改版（例程/日志占左半列，
右半列留空显示右上对齐的背景图；固定例程下拉框按内容自适应宽度）。
详见 §3/§4/§5 修订处。

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
- 任一任务（例程运行/单发/解锁/会话切换/读DTC）运行期间，其余任务入口控件
  禁用（避免与 run_flow 并发争用同一 transport）

## 3. 界面结构（布局方案 C 修订：工具条 + 左列[三 Tab 上2/5 + 日志/报文下3/5] + 右列背景留白）

```
┌────────────────────────────────────────────────────────┐
│ 工具条：配置下拉▾ | 连接/断开 | 状态● | 3E80开关 | 周期ms │
├──────────────────────────┬─────────────────────────────┤
│ Tab: [手动发送][固定例程][配置例程]                        │
│ （左半列 · 上 2/5）        │      背景图（右半列留空，      │
├──────────────────────────┤      右上对齐显示）           │
│ 【日志】｜【报文】双 Tab                                 │
│ （左半列 · 下 3/5）        │                             │
├──────────────────────────┴─────────────────────────────┤
│ 状态栏：状态 | 本次会话落盘目录                           │
└────────────────────────────────────────────────────────┘
```

- **工具条**：配置下拉扫 `configs/` 全部 yaml（含子目录，显示 `n60/n60_cx` 相对
  路径）；连接/断开按钮；连接状态（设备名+通道）；3E80 开关 + 周期 spinbox
  （500–50000，默认 2500）
- **手动发送 Tab**（修订：原「单发调试」，解锁控件移至固定例程）：TX hex 输入 +
  发送（Enter 触发）+ 收发历史表（时间/TX/RX/NRC/耗时，双击回填 TX）
- **固定例程 Tab**（修订新增）：内置固定动作三行——会话切换（下拉
  1001 默认 / 1003 扩展（默认选中）/ 1002 编程 + 「切换」按钮，正响应判定 0x50）；
  安全解锁（等级下拉（配置 security 节 + 内置 develop）+ 「解锁」按钮）；读DTC
  （「读取」按钮，序列同 §4 DTC 读取）。各动作结果回显本页状态行
- **配置例程 Tab**（修订：原「例程运行」，读DTC 移至固定例程）：例程树（根目录
  `<DiagnosticTester>/testcase/`，与 CLI 默认用法一致；工具条提供「浏览」可选
  任意目录或单个 yaml 文件兜底），按当前配置项目名过滤显示 `testcase/<项目>/` +
  刷新 + 运行 + 停止 + 结果汇总（PASS/FAIL/TIMEOUT、当前步骤、run_dir 路径）+
  「打开运行目录」（explorer）
- **日志 Tab**：QPlainTextEdit，行格式与 run.log 一致；自动滚动开关 / 清空按钮
- **报文 Tab**（修订新增）：**原始 CAN 帧逐行显示，不做 UDS 层转换**，且仅显示
  diagnostic 配置的 request/response/functional 三个 CAN ID（isotp tap 在 rx_id
  过滤前回调，UI 层负责按三 ID 过滤；总线其余流量仍照常落 trace.blf）。
  行格式 `[hh:mm:ss.mmm] TX|RX <ID> <SF|FF|CF|FC> <hex data>`；数据源为
  IsoTpTransport 的 tap 回调（pump/sender 线程 emit，主线程渲染），功能寻址
  直发帧与 3E80 保活帧同样进此页。自动滚动 / 清空独立于日志 Tab

## 4. 功能行为

### 连接会话

点连接 → `load_config` → `make_driver` → `build_transport` → `UdsClient` +
`Recorder`（落盘 `logs/<项目>_ui_<时间戳>/`，三路记录保证据链）；断开按
transport.stop → recorder.close → driver.close 逆序收尾。切换配置必须先断开。

### 例程运行（配置例程 Tab）

- worker 线程调 `run_flow`；run_dir 规则与 CLI `run` 一致：
  `<用例目录>/../logs/<用例名>/<时间戳>/`
- **运行前挂起会话 transport**（suspend_transport），结束后重建
  （resume_transport）：run_flow 会自建 pump 独占 driver RX，若不挂起则
  双 pump 在 driver.recv() 上抢帧导致响应间歇丢失（实测 t09 用例 UI 超时、
  CLI 全过的根因）
- 事件流经 log_hook 实时进 UI 日志 Tab（同时照常落盘）；原始帧经 frame_hook
  实时进报文 Tab（同时照常落 BLF）
- 停止按钮置位 threading.Event，`run_flow` 每步开始前检查，当前步完成后中止
  （不强杀线程）；已执行步骤计数照常汇总

### 报文页（修订新增）

- 数据源：IsoTpTransport tap（会话链路与 run_flow 自建链路都接
  frame_hook → Qt signal）、功能寻址直发帧、3E80 保活帧
- 只显示原始 CAN 帧行（`framefmt.format_frame_line`），不做 UDS 请求/响应
  解析转换；SF/FF/CF/FC 按首字节高半字节分类（FD 0x00 转义按 SF）
- 与 trace.blf 同源同时落盘（tap tee），证据链一致

### DTC 读取（修订新增）

- 固定例程 Tab「读DTC」按钮（修订：自配置例程 Tab 迁入）：worker 线程调
  `dem.run_dem(uds, maps, emit,
  unlock=develop)`，maps 从当前配置目录加载（dtc_map/event_map/fimfid_map/
  dem_dids.yaml）
- 序列：10 03 进扩展会话 → develop 解锁（失败记日志、不阻断后续读取）→
  19 02 0F + 3 个 event DID + fimfid 读取
- 运行期间手动发送/固定例程两页按钮与连接按钮禁用（防止断开拆掉 worker 脚下的
  链路）；结果回显固定例程状态行 + 状态栏
  汇总（0=全过，非 0=部分项失败）

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
- 每次发送落 BLF + 报文页一行 + 日志一行（三处同源）

## 5. 对现有代码的改动

全部为可选参数追加，缺省行为与现状完全一致，CLI 零影响：

- `flow.py` `run_flow`：`log_hook`（事件 tee）、`should_stop`（步间中止）、
  `frame_hook`（原始帧 tee，修订新增）
- `DiagnosticTester.py` `build_transport`：`frame_hook`（tap tee，修订新增）
- `dem.py` `run_dem`：`unlock=None` 可选参数（修订新增：给定 SecLevel 时在
  10 03 后、DTC 读取前执行 perform_unlock，失败不阻断）

其余模块（isotp/uds/security/can_driver/recorder）零改动。

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

- dem map 的编辑/维护 UI（DTC 读取本身已入 UI，map yaml 仍由 CLI/手工维护）
- 多 ECU 并行会话、GUI 里的用例编辑器
- 打包成 exe（直接 python 启动）
