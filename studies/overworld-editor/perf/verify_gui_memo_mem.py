"""verify (gui skeptic): what C1's per-cell memo and P4's ground grid HOLD (the lane did not measure memory), on the
game's stack (read only). Bytes of numpy buffers only (a lower bound: dict/list/tuple overheads excluded, except the
grid's per-cell array objects, counted by sys.getsizeof).

    py studies/overworld-editor/perf/verify_gui_memo_mem.py
Evidence: out/perf/gui/verify/verify_gui_memo_mem.json
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

C.OUT = C.OUT / "verify"
C.OUT.mkdir(parents=True, exist_ok=True)


def private_mb():
    """This process's private bytes (Windows PROCESS_MEMORY_COUNTERS_EX.PrivateUsage), MB."""
    import ctypes
    from ctypes import wintypes

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (n, ctypes.c_size_t) for n in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                                           "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                                           "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage",
                                           "PrivateUsage")]
    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    k32 = ctypes.WinDLL("kernel32")
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi")
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    assert psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
    return pmc.PrivateUsage / 1e6


def main():
    import gc
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import render as R
    from gui_proto_reload import Proto
    import gui_proto_preview as PP
    cells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
    site = R.RenderSite(cells=cells, disc=1, game=C.GAME, stack=R.game_stack(C.GAME))
    V.load_scene(site)                                                # warm: env, tex cache, extract's own LRU
    gc.collect()
    base_mb = private_mb()
    proto = Proto(R, V, roots_in_key=False)
    proto.install(2)
    t = time.perf_counter()
    packed, tex = V.load_scene(site)
    fill = time.perf_counter() - t
    proto.uninstall()
    gc.collect()
    with_both_mb = private_mb()
    proto.stock.clear()
    gc.collect()
    without_stock_mb = private_mb()
    memo_bytes = sum(w.nbytes + uv.nbytes + tr.nbytes for _fp, out in proto.cells.values() for _p, w, uv, tr in out)
    stock_memo = len(proto.stock)
    packed_bytes = sum(a.nbytes for a in packed.arrays.values())
    rgba_bytes = sum(v[1].nbytes for v in proto.rgba.values() if v[1] is not None)
    t = time.perf_counter()
    gg = PP.GroundGrid(packed)
    build = time.perf_counter() - t
    pick_bytes = sum(sum(a.nbytes for a in packed.pick_arrays(p)) for p in packed.arrays)
    grid_bytes = sum(a.nbytes + sys.getsizeof(a) for g in gg.grid.values() for a in g.values())
    ncell = sum(len(g) for g in gg.grid.values())
    # the stock memo (V1) holds BlockMesh masters: python lists of floats -- estimate from one part's lists
    import random
    sample = []
    def bm_size(bm):
        if bm is None:
            return 0
        n = 0
        for ch in bm.chan_arrays.values():
            n += sys.getsizeof(ch) + sum(sys.getsizeof(r) + 24 * len(r) for r in ch)
        n += sys.getsizeof(bm.tris) + sum(sys.getsizeof(r) for r in bm.tris) + sys.getsizeof(bm.flat_index)
        n += len(bm.raw_vbuf) + len(bm.raw_ibuf)
        return n
    avg = 0.0
    out = {"load_with_memo_fill_s": round(fill, 3), "cells_memoized": len(proto.cells),
           "C1_cell_memo_numpy_MB": round(memo_bytes / 1e6, 1), "packed_MB": round(packed_bytes / 1e6, 1),
           "texture_rgba_memo_MB": round(rgba_bytes / 1e6, 1),
           "V1_stock_memo_entries": stock_memo,
           "private_MB_warm_no_memo": round(base_mb, 1), "private_MB_with_C1_and_V1_memos_and_a_packed":
           round(with_both_mb, 1), "private_MB_after_dropping_V1_stock_memo": round(without_stock_mb, 1),
           "P4_pick_arrays_MB": round(pick_bytes / 1e6, 1), "P4_grid_MB": round(grid_bytes / 1e6, 1),
           "P4_grid_cells": ncell, "P4_grid_build_s": round(build, 3)}
    print(out)
    C.dump("verify_gui_memo_mem.json", out)


if __name__ == "__main__":
    main()
