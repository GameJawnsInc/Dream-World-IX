"""Bring the running FF9 window to the front after a deploy (ask-user #16 -- opt-in, default OFF).

RAISE/FLASH ONLY -- no synthetic input. The chair's ruling killed the stretch "tap ~ for them" idea
(a synthetic keystroke can land mid-load), so it is deliberately not built here. Discovery mirrors
``tools/game_snap.ps1``: the game is the process named ``FF9`` owning a top-level window -- the title
is not matched (it varies by localization; the process name doesn't). Everything is FAIL-SOFT: a
missing game, a non-Windows platform, or any Win32 refusal degrades to a silent no-op, because a
convenience must never break the deploy verdict it decorates.

Windows refuses ``SetForegroundWindow`` from a background process -- but this is called while the
Workspace IS the foreground process (the user just pressed F9), which is exactly the case the OS
allows. If it still refuses (a race, a fullscreen exclusive), ``FlashWindowEx`` marks the taskbar
button instead, which is the polite half the OS never refuses.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as _wt
import sys

GAME_PROCESS = "FF9.exe"                           # the Steam FF9 launcher process (game_snap.ps1 parity)


def _game_pids() -> set[int]:
    """PIDs of every running ``FF9.exe`` via a Toolhelp32 snapshot (no psutil dependency)."""
    k32 = ctypes.windll.kernel32
    TH32CS_SNAPPROCESS = 0x2

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", _wt.DWORD), ("cntUsage", _wt.DWORD), ("th32ProcessID", _wt.DWORD),
                    ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)), ("th32ModuleID", _wt.DWORD),
                    ("cntThreads", _wt.DWORD), ("th32ParentProcessID", _wt.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", _wt.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]

    pids: set[int] = set()
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == ctypes.c_void_p(-1).value:
        return pids
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            if entry.szExeFile.lower() == GAME_PROCESS.lower():
                pids.add(int(entry.th32ProcessID))
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        k32.CloseHandle(snap)
    return pids


def _main_window(pids: set[int]):
    """The game's top-level window: visible, unowned, and belonging to one of ``pids`` (the same shape
    .NET's MainWindowHandle resolves for game_snap). None when the game has no window yet."""
    u32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(_wt.BOOL, _wt.HWND, _wt.LPARAM)
    def _enum(hwnd, _lp):
        if not u32.IsWindowVisible(hwnd) or u32.GetWindow(hwnd, 4):    # 4 = GW_OWNER: owned popups lose
            return True
        pid = _wt.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if int(pid.value) in pids:
            found.append(hwnd)
            return False                            # first match wins -- stop enumerating
        return True

    u32.EnumWindows(_enum, 0)
    return found[0] if found else None


def raise_game() -> bool:
    """Raise the running FF9 window (restore if minimized, foreground if the OS allows, flash if it
    refuses). True when a game window was found -- the caller may use that for a quiet status note.
    Never raises; never touches input."""
    if sys.platform != "win32":
        return False
    try:
        pids = _game_pids()
        if not pids:
            return False
        hwnd = _main_window(pids)
        if hwnd is None:
            return False
        u32 = ctypes.windll.user32
        if u32.IsIconic(hwnd):
            u32.ShowWindow(hwnd, 9)                 # SW_RESTORE -- a minimized window can't be foregrounded
        if not u32.SetForegroundWindow(hwnd):
            # the OS refused the raise -> flash the taskbar button instead (FLASHW_TRAY | FLASHW_TIMERNOFG)
            class FLASHWINFO(ctypes.Structure):
                _fields_ = [("cbSize", _wt.UINT), ("hwnd", _wt.HWND), ("dwFlags", _wt.DWORD),
                            ("uCount", _wt.UINT), ("dwTimeout", _wt.DWORD)]
            info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, 0x2 | 0xC, 3, 0)
            u32.FlashWindowEx(ctypes.byref(info))
        return True
    except Exception:                               # noqa: BLE001 -- fail-soft by contract (see module doc)
        return False
