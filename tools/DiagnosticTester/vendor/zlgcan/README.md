# zlgcan SDK（已内置）

ZLGCAN SDK（Windows x64）已随仓库内置，无需组装：`zlgcan.py`（python 绑定）、
`zlgcan.dll`（主 dll）、`kerneldlls/`（设备后端 dll）。来源：周立功官网
（https://manual.zlg.cn/web/#/55?page_id=2286），版本更新时按原目录结构替换。

注意：
- `zlgcan.py` 相对官方原版打了补丁：dll 改为按 `__file__` 所在目录加载
  （原版 `"./zlgcan.dll"` 依赖进程 CWD）。
- 设备后端 dll 由 zlgcan.dll 在运行时从自身目录旁的 `kerneldlls/` 加载。
