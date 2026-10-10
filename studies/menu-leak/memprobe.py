"""FF9.exe memory probe for the menu-leak soaks: PrivateUsage straight from Win32 (no PowerShell spin-up)."""
from __future__ import annotations

import ctypes
from ctypes import wintypes


class _PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t)]


_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.OpenProcess.restype = wintypes.HANDLE
_k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PMC), wintypes.DWORD]


def private_mb(pid: int) -> tuple[float, float]:
    """(private MB, working-set MB) of ``pid``."""
    h = _k32.OpenProcess(0x1000 | 0x0010, False, pid)     # QUERY_LIMITED_INFORMATION | VM_READ
    if not h:
        raise OSError(f"OpenProcess({pid}) failed: {ctypes.get_last_error()}")
    try:
        pmc = _PMC()
        pmc.cb = ctypes.sizeof(_PMC)
        if not _k32.K32GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
            raise OSError(f"GetProcessMemoryInfo failed: {ctypes.get_last_error()}")
        return pmc.PrivateUsage / 2**20, pmc.WorkingSetSize / 2**20
    finally:
        _k32.CloseHandle(h)


def _slope(rows: list[dict]) -> float | None:
    """Least-squares MB per menu over an arm's samples."""
    pts = [(r["n"], r["private_mb"]) for r in rows]
    if len(pts) < 2:
        return None
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    den = sum((p[0] - mx) ** 2 for p in pts)
    return None if den == 0 else sum((p[0] - mx) * (p[1] - my) for p in pts) / den
