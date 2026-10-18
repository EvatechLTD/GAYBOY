"""Project-only SameBoy controls. The keyboard filter applies only to its window."""
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import struct
import subprocess
import sys
import time
from sameboy_cursor import keep_cursor_visible
from sameboy_palette import configure_desktop_palette

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / 'tools/sameboy/sameboy.exe'
ALLOWED = {0x25, 0x26, 0x27, 0x28, 0x58, 0x5A, 0x20, 0xA0}


def configure():
    keep_cursor_visible(EXE)
    prefs = EXE.with_name('prefs.bin')
    data = bytearray(prefs.read_bytes())
    # SameBoy 1.0.4 configuration_t: SDL scancodes, followed by keys_2 at 96.
    if len(data) != 4460:
        raise RuntimeError('Unexpected SameBoy preference version')
    struct.pack_into('<9I', data, 0, 79, 80, 82, 81, 27, 29, 44, 225, 0)
    struct.pack_into('<32I', data, 96, *([0] * 32))
    struct.pack_into('<I', data, 40, 1)  # Fill available space, preserve aspect ratio.
    # Match tools/browser_sameboy.c: accurate DMG high-pass, no added SoC noise.
    struct.pack_into('<I', data, 48, 1)  # GB_HIGHPASS_ACCURATE
    data[4385] = 0  # configuration_t.interference_volume
    configure_desktop_palette(data)
    prefs.write_bytes(data)


def run(rom):
    user = C.WinDLL('user32', use_last_error=True)
    user.SetProcessDPIAware()
    kernel = C.WinDLL('kernel32', use_last_error=True)
    result_type = C.c_ssize_t
    callback_type = C.WINFUNCTYPE(result_type, C.c_int, W.WPARAM, W.LPARAM)

    class Key(C.Structure):
        _fields_ = [('vk', W.DWORD), ('scan', W.DWORD), ('flags', W.DWORD),
                    ('time', W.DWORD), ('extra', C.c_size_t)]

    user.SetWindowsHookExW.argtypes = [C.c_int, callback_type, W.HINSTANCE, W.DWORD]
    user.SetWindowsHookExW.restype = W.HANDLE
    user.CallNextHookEx.argtypes = [W.HANDLE, C.c_int, W.WPARAM, W.LPARAM]
    user.CallNextHookEx.restype = result_type
    user.UnhookWindowsHookEx.argtypes = [W.HANDLE]
    user.GetForegroundWindow.restype = W.HWND
    user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    user.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    user.ShowWindowAsync.argtypes = [W.HWND, C.c_int]
    user.IsZoomed.argtypes = [W.HWND]
    user.IsWindowVisible.argtypes = [W.HWND]
    user.GetWindowTextLengthW.argtypes = [W.HWND]
    user.GetWindowRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
    user.SetWindowPos.argtypes = [W.HWND, W.HWND, C.c_int, C.c_int,
                                 C.c_int, C.c_int, W.UINT]
    user.SetForegroundWindow.argtypes = [W.HWND]
    user.MonitorFromWindow.argtypes = [W.HWND, W.DWORD]
    user.MonitorFromWindow.restype = W.HANDLE

    class Monitor(C.Structure):
        _fields_ = [('size', W.DWORD), ('screen', W.RECT), ('work', W.RECT),
                    ('flags', W.DWORD)]

    user.GetMonitorInfoW.argtypes = [W.HANDLE, C.POINTER(Monitor)]
    enum_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    user.EnumWindows.argtypes = [enum_type, W.LPARAM]
    kernel.GetModuleHandleW.argtypes = [W.LPCWSTR]
    kernel.GetModuleHandleW.restype = W.HMODULE
    process = None
    restart = False
    f5_down = False

    @enum_type
    def size_window(window, _):
        owner = W.DWORD()
        user.GetWindowThreadProcessId(window, C.byref(owner))
        if (owner.value == process.pid and user.IsWindowVisible(window)
                and user.GetWindowTextLengthW(window)):
            monitor = Monitor()
            monitor.size = C.sizeof(monitor)
            user.GetMonitorInfoW(user.MonitorFromWindow(window, 2), C.byref(monitor))
            area = monitor.work
            rect = W.RECT()
            user.GetWindowRect(window, C.byref(rect))
            width, height = 640, 480
            left = area.left + max(0, (area.right-area.left-width)//2)
            top = area.top + max(0, (area.bottom-area.top-height)//2)
            if (user.IsZoomed(window) or rect.right-rect.left != width
                    or rect.bottom-rect.top != height):
                user.ShowWindowAsync(window, 9)
                user.SetWindowPos(window, W.HWND(-1), left, top,
                                  width, height, 0x0040)
                user.SetForegroundWindow(window)
            else:
                user.SetWindowPos(window, W.HWND(-1), 0, 0, 0, 0, 0x0013)
            return False
        return True

    @callback_type
    def filter_key(code, message, pointer):
        nonlocal restart, f5_down
        if code >= 0 and process is not None:
            owner = W.DWORD()
            window = user.GetForegroundWindow()
            user.GetWindowThreadProcessId(window, C.byref(owner))
            if owner.value == process.pid:
                key = C.cast(pointer, C.POINTER(Key)).contents
                down = message in (0x100, 0x104)
                if key.vk == 0x74:  # F5: save battery and restart the ROM.
                    if down and not f5_down:
                        restart = True
                        user.PostMessageW(window, 0x10, 0, 0)
                    f5_down = down
                    return 1
                if key.vk == 0xA1:  # Right Shift acts exactly like Left Shift.
                    user.keybd_event(0xA0, 0x2A, 0 if down else 2, 0)
                    return 1
                if key.vk not in ALLOWED:
                    return 1
        return user.CallNextHookEx(None, code, message, pointer)

    hook = user.SetWindowsHookExW(13, filter_key, kernel.GetModuleHandleW(None), 0)
    if not hook:
        raise C.WinError(C.get_last_error())
    try:
        while True:
            configure()
            startup = subprocess.STARTUPINFO()
            startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 1  # Normal window, including F5 restarts.
            process = subprocess.Popen([str(EXE), '--model', 'dmg', str(rom)],
                                       cwd=EXE.parent, startupinfo=startup)
            (ROOT / 'build/emulator.pid').write_text(str(process.pid))
            restart = f5_down = False
            size_until = time.monotonic() + 8
            message = W.MSG()
            while process.poll() is None:
                # SDL resizes again after loading the ROM/boot display. Check
                # through startup rather than trusting a queued ShowWindow call.
                if time.monotonic() < size_until:
                    user.EnumWindows(size_window, 0)
                while user.PeekMessageW(C.byref(message), None, 0, 0, 1):
                    user.TranslateMessage(C.byref(message))
                    user.DispatchMessageW(C.byref(message))
                time.sleep(.005)
            if not restart:
                break
    finally:
        user.UnhookWindowsHookEx(hook)


if __name__ == '__main__':
    run(Path(sys.argv[1]).resolve())
