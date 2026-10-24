import win32gui
import win32process
import psutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get_windows_info():
    results = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True

        title = win32gui.GetWindowText(hwnd).strip()

        if not title:
            return True

        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            proc = psutil.Process(pid)

            exe = proc.name()
            exe_path = proc.exe()

            try:
                cmdline = " ".join(proc.cmdline())
            except Exception:
                cmdline = ""

            results.append({
                "hwnd": hwnd,
                "title": title,
                "pid": pid,
                "exe": exe,
                "exe_path": exe_path,
                "cmdline": cmdline,
            })

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        return True

    win32gui.EnumWindows(callback, None)

    return results


if __name__ == "__main__":
    windows = get_windows_info()

    for w in windows:
        print("=" * 80)
        print(f"Cửa sổ : {w['title']}")
        print(f"PID    : {w['pid']}")
        print(f"EXE    : {w['exe']}")
        print(f"Đường dẫn: {w['exe_path']}")
        print(f"Command: {w['cmdline']}")