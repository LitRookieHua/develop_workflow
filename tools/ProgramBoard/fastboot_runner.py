"""经 Git Bash login shell 执行 fastboot 指令，输出实时转发控制台并落日志。"""
import os
import shlex
import shutil
import subprocess
import threading
import time

FASTBOOT_TIMEOUT_S = 60
CONNECT_RETRY_DELAY_S = 3


class FastbootError(Exception):
    pass


def find_bash() -> str:
    p = shutil.which("bash")
    if p and "system32" not in p.lower() and "windowsapps" not in p.lower():
        return p
    for cand in (r"D:\Program Files\Git\bin\bash.exe",
                 r"C:\Program Files\Git\bin\bash.exe",
                 r"C:\Program Files (x86)\Git\bin\bash.exe"):
        if os.path.isfile(cand):
            return cand
    raise FastbootError("找不到 Git Bash——请安装 Git for Windows 或将其加入 PATH")


def _posix_path_env(env):
    """python.exe 继承的是 Windows 格式 PATH（C:\\...;C:\\...），bash 无法解析其中的
    反斜杠条目导致 fastboot: command not found。转换为 /c/... : /d/... 格式。"""
    p = env.get("PATH", "")
    if ";" not in p:
        return
    out = []
    for part in p.split(";"):
        if not part:
            continue
        part = part.replace("\\", "/")
        if len(part) >= 2 and part[1] == ":":
            part = "/" + part[0].lower() + part[2:]
        out.append(part)
    env["PATH"] = ":".join(out)


def run_fastboot(args, target: str, log, timeout: float = FASTBOOT_TIMEOUT_S):
    """执行一条 fastboot 指令。target 形如 'udp:192.168.1.239'。
    成功返回 True，失败/超时抛 FastbootError。"""
    cmd_str = "fastboot " + " ".join(shlex.quote(a) for a in args)
    env = os.environ.copy()
    _posix_path_env(env)
    env["ANDROID_SERIAL"] = target
    log(f"$ {cmd_str}  (ANDROID_SERIAL={target})")

    proc = subprocess.Popen(
        [find_bash(), "-lc", cmd_str], env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    output = []

    def reader():
        for line in proc.stdout:
            log("  " + line.rstrip())
            output.append(line)

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise FastbootError(f"超时 ({timeout}s): {cmd_str}")
    t.join(timeout=2)

    text = "".join(output)
    if proc.returncode != 0 or "FAILED" in text:
        raise FastbootError(f"{cmd_str} 失败 (rc={proc.returncode})\n{text[-500:]}")


def run_fastboot_with_connect_retry(args, target: str, log,
                                    timeout: float = FASTBOOT_TIMEOUT_S):
    """首条指令专用：UDP fastboot 首连有发现延迟，失败先就地重试 1 次，
    不消耗主流程的断电重试次数。"""
    try:
        return run_fastboot(args, target, log, timeout)
    except FastbootError as e:
        log(f"首条指令失败，{CONNECT_RETRY_DELAY_S}s 后重试一次: {e}")
        time.sleep(CONNECT_RETRY_DELAY_S)
        return run_fastboot(args, target, log, timeout)
