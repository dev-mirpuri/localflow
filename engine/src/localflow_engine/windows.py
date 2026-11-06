"""Windows input and output: the keyboard hook, and paste through the clipboard (ADR-0002)."""

import ctypes
import threading
import time
from collections.abc import Callable
from pathlib import PureWindowsPath

import keyboard

INJECTED_S = 0.03
RESTORE_S = 0.2
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

user32, kernel32 = ctypes.WinDLL("user32"), ctypes.WinDLL("kernel32")
user32.OpenClipboard.argtypes = (ctypes.c_void_p,)
user32.GetClipboardData.restype = ctypes.c_void_p
user32.GetClipboardData.argtypes = (ctypes.c_uint,)
user32.SetClipboardData.restype = ctypes.c_void_p
user32.SetClipboardData.argtypes = (ctypes.c_uint, ctypes.c_void_p)
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalAlloc.argtypes = (ctypes.c_uint, ctypes.c_size_t)
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = (ctypes.c_void_p,)
kernel32.GlobalUnlock.argtypes = (ctypes.c_void_p,)
kernel32.GlobalFree.argtypes = (ctypes.c_void_p,)
user32.GetForegroundWindow.restype = ctypes.c_void_p
user32.GetWindowThreadProcessId.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))
kernel32.OpenProcess.restype = ctypes.c_void_p
kernel32.OpenProcess.argtypes = (ctypes.c_uint, ctypes.c_int, ctypes.c_uint)
kernel32.QueryFullProcessImageNameW.argtypes = (
    ctypes.c_void_p,
    ctypes.c_uint,
    ctypes.c_wchar_p,
    ctypes.POINTER(ctypes.c_ulong),
)
kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)

# The hook sees our own Ctrl+V as ordinary keys, and keyboard's events can't say otherwise.
injecting = threading.Event()


def hook(on_key: Callable[[str, int, bool, bool], bool]) -> None:
    """Calls on_key(name, scan_code, down, injected) on the hook thread; True swallows the key."""

    def callback(event: keyboard.KeyboardEvent) -> bool:
        if event.name is None:
            return True
        return not on_key(
            event.name, event.scan_code, event.event_type == "down", injecting.is_set()
        )

    keyboard.hook(callback, suppress=True)


def unhook() -> None:
    keyboard.unhook_all()


def paste(text: str) -> None:
    """Pastes text at the cursor with Ctrl+V, then puts the clipboard's text back."""
    saved = get_text()
    set_text(text)
    injecting.set()
    try:
        keyboard.send("ctrl+v")
        time.sleep(INJECTED_S)
    finally:
        injecting.clear()
    time.sleep(RESTORE_S - INJECTED_S)
    set_text(saved)


def target_app() -> str:
    """The foreground window's process name, like notepad.exe, or "" if Windows won't say."""
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
    process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not process:
        return ""
    try:
        size = ctypes.c_ulong(32768)
        path = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size)):
            return ""
        return PureWindowsPath(path.value).name
    finally:
        kernel32.CloseHandle(process)


def open_clipboard() -> None:
    for _ in range(100):
        if user32.OpenClipboard(None):
            return
        time.sleep(0.01)
    raise OSError("clipboard stayed busy for 1 s")


def get_text() -> str | None:
    open_clipboard()
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        pointer = kernel32.GlobalLock(handle) if handle else None
        if not pointer:
            return None
        try:
            return ctypes.wstring_at(pointer)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def set_text(text: str | None) -> None:
    """Replaces the clipboard with text, or leaves it empty for None."""
    open_clipboard()
    try:
        user32.EmptyClipboard()
        if text is None:
            return
        data = ctypes.create_unicode_buffer(text)
        memory = kernel32.GlobalAlloc(GMEM_MOVEABLE, ctypes.sizeof(data))
        ctypes.memmove(kernel32.GlobalLock(memory), data, ctypes.sizeof(data))
        kernel32.GlobalUnlock(memory)
        if not user32.SetClipboardData(CF_UNICODETEXT, memory):
            kernel32.GlobalFree(memory)
            raise ctypes.WinError()
    finally:
        user32.CloseClipboard()
