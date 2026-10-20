# J6B 固件刷写工具

一键刷写 J6B MCU 固件：自动打断 uboot → `fastboot udp` → 刷分区 → 重启，失败自动断电重试，全程无人值守（约 35 秒/次）。

一键刷写 J6B OTA 整包：`ota_j6b.py`（见下文「OTA 整包刷写」）。

## 硬件要求

| 设备 | 连接 | 说明 |
|---|---|---|
| 刷写板 | A 核串口 → PC（识别规则见下节链接） | 波特率 J6 921600 / TDA4 115200 |
| 刷写板 | 网线 → PC 同网段 | fastboot 走 UDP |
| KORAD KA3005P | USB → PC（当前为 **COM44**，`power_control.py --port <COM> id` 能应答即确认） | 可选；不接则失败时提示人工断电 |
| 刷写板 | 供电接 KA3005P 输出（12V） | 自动断电重试依赖此项 |

软件：Python 3.12+、pyserial、Git Bash（fastboot 在其 PATH 中，当前为 `hobot_tools/platform-tools_r30.0.5-windows`）。

## A 核 / R 核串口识别

**识别规则的唯一权威源：[`.claude/skills/feature-development/references/serial-port-identification.md`](../../.claude/skills/feature-development/references/serial-port-identification.md)**——J6（全 921600）：CH9114 四口 SERIAL-C=A 核 / SERIAL-D=R 核，普通 USB Serial Port 按 COM 号升序第 3/4 个；TDA4（全 115200）：两组各 4 个连续串口，A 核组第 1 个、R 核组第 2 个。COM 号随 USB 重枚举漂移，换板后按规则重新判定，本 README 不重复维护规则内容。

## 使用

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/ProgramBoard

# 日常刷写（接电源；--port 为 A 核串口，按识别规则现查，示例 COM33 = J6 EVM SERIAL-C）
python ProgramBoard_j6b.py --port COM33 --psu-com COM44

# 不接电源（失败时提示人工断电，回车继续）
python ProgramBoard_j6b.py --port COM33
```

流程：断电冷启动(3s) → 20ms 周期发空格打断 uboot → `fastboot udp` → 解析板子 IP → `oem interface:mtd` → `flash MCU_a` → `flash MCU_b` → `fastboot reboot`。任一步失败自动断电重来，默认重试 3 次。退出码：0 成功 / 1 失败。

## 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--port` | （必填） | 板子 A 核串口 COM 号 |
| `--psu-com` | 无 | 电源串口 COM 号（不填走人工断电模式；电源工具见 `../PowerControl/`） |
| `--psu-type` | `korad` | 电源类型（见 `../PowerControl/`） |
| `--config` | `configs/n60_mcu.json` | 刷写配置（分区、镜像、匹配关键字） |
| `--img-dir` | N60 的 `rpu_arm_gcc` 目录 | 镜像相对路径的基目录 |
| `--retries` | 3 | 失败重试次数 |
| `--dry-run` | 关 | 只打断/进 fastboot/解析 IP，不刷写不动电源 |

## 刷其他项目 / 分区

复制 `configs/n60_mcu.json` 改 `commands` 即可，例如刷整包 bin：

```json
{
  "uboot_baudrate": 921600,
  "interrupt_keyword": "Hit any key to stop autoboot",
  "prompt_pattern": "Hobot[$#]",
  "fastboot_ready_pattern": "Listening for fastboot command",
  "commands": [
    {"type": "fastboot", "args": ["oem", "interface:mtd"]},
    {"type": "fastboot", "args": ["flash", "MCU_a", "xxx.img"]},
    {"type": "fastboot", "args": ["flash", "MCU_b", "xxx.img"]}
  ]
}
```

运行时 `--config` 指向新文件，img 相对路径基于 `--img-dir` 解析。

## 换新板校准

新板子/新 uboot 版本先跑 `--dry-run`，对照 `logs/flash_*.log` 里的 `[SER]` 原始打印，确认配置中三个关键字是否匹配：

1. `prompt_pattern` — uboot 提示符（J6B 为 `Hobot$`）
2. `fastboot_ready_pattern` — fastboot 就绪打印（J6B 为 `Listening for fastboot command`）
3. IP 解析 — 从就绪打印中提取 IPv4（取最后一个候选）

## 日志

`logs/flash_YYYYMMDD_HHMMSS.log`，每次运行一个文件：控制台只打关键进度，日志含全部串口原始数据（`[SER]` 前缀）和 fastboot 完整输出。排障先看这里。

## OTA 整包刷写

板子正常启动到 QNX 后，走 SSH 刷 OTA 整包（不动 uboot/fastboot）：

```bash
cd D:/Workspace/01_Projects/02_Src/11_AI/develop_workflow/tools/ProgramBoard

# 日常（板子已上电在线）
# 日常（板子已上电在线；--port 为 A 核串口，按识别规则现查）
python ota_j6b.py --port COM33

# 冷启动后完整流程（接电源）
python ota_j6b.py --port COM33 --psu-com COM44

# 指定包路径（缺省取 ota_package/ 下最新 zip）
python ota_j6b.py --port COM33 --ota path/to/xxx.zip
```

流程：断电冷启动(3s) → **串口使能 SSH**（见下）→ 删除 `/ota` 旧包 → SFTP 原名上传整包（**不重命名**）→ **大小+MD5 校验** → `ota_tool -g` 记录当前槽位 → `. /etc/profile && cd /ota && ota_tool -p` 原名安装，等待 `[OTA SUCCESSFULL]` → 板子自动重启 → 等 60s → **串口使能 SSH** → `ota_tool -g` 确认槽位翻转（A→B / B→A）才算成功。任一步失败自动重来，默认重试 3 次。

依赖：`pip install paramiko pyserial`（paramiko 5.0+）。

| 参数 | 默认 | 说明 |
|---|---|---|
| `--port` | （必填） | A 核串口 COM 号（识别规则见上文「A 核 / R 核串口识别」），上电/重启后串口登录执行 `pfctl -d` 使能 SSH |
| `--ota` | ota_package/ 最新 zip | OTA 整包本地路径 |
| `--psu-com` | 无 | 电源串口 COM 号（不填则假定板子已上电启动） |
| `--psu-type` | `korad` | 电源类型（见 `../PowerControl/`） |
| `--host` | 192.168.1.239 | 板子 IP |
| `--retries` | 3 | 失败重试次数 |
| `--dry-run` | 关 | 只连接/删旧包/查空间，不上传不安装 |

日志：`logs/ota_YYYYMMDD_HHMMSS.log`。

### 板子已知坑（2026-09 实测）

- **升级成功判定**：`ota_tool -p` 输出出现 `[OTA SUCCESSFULL]` 表示安装完成，随后板子自动重启；重启后 `ota_tool -g` 槽位翻转（A→B / B→A）才代表升级生效
- **每次上电/重启后 pf 会拦截 SSH**：必须通过 A 核串口登录（921600，root / hct@Shanghai0427，行结尾必须 `\r`）执行 `pfctl -d`，等到 `pf disabled` 后 SSH 才可连
- **QNX sftp-server 流水线写丢数据**：paramiko `sftp.put()` 默认 pipelined，实测 554MB 只落盘 245MB 且不报错。必须逐块同步写（`rf.write()` 非流水线模式）并做大小+MD5 校验，不一致自动重传（3 次）
- **ota_tool 安装必须带登录 shell 环境**：SSH `exec_command` 的非登录 shell 缺 `LD_LIBRARY_PATH` 等 `/etc/profile` 定义的变量，ota_tool 在启动 `ota_process` 子进程处直接段错误（exit=139；实测 PTY / cd /ota / 相对路径均非根因）。脚本用 `. /etc/profile && cd /ota && ota_tool -p <原名>` + PTY 复刻交互式调用

## 已知板子特性（2026-09 实测，N60 EVM）

- **bootdelay=0**：看到 `Hit any key to stop autoboot: 0` 再发键来不及，必须从启动打印出现起以 20ms 周期持续发空格（100ms 不够）
- **fastboot 模式下串口 `reset` 无效**，必须用 `fastboot reboot`（UDP 通道）
- 板子 IP（192.168.1.239）来自 uboot-env 静态配置，不依赖 DHCP
- gmac0 无 PHY 会打印 `phy_connect() failed`，实际走 gmac1，属正常

## 模块结构

```
ProgramBoard_j6b.py  CLI 入口 + 主流程编排（打断/刷写/重试）
ota_j6b.py         OTA 整包刷写（SSH/SFTP + 校验 + ota_tool）
uboot_console.py   串口监听、正则匹配、发送命令
fastboot_runner.py 经 Git Bash 调 fastboot
configs/           刷写配置
ota_package/       OTA 整包存放目录（缺省取最新 zip）
logs/              运行日志
```
