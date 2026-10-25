"""verify (gui skeptic): C1 WITHOUT the unbounded stock memo. The lane's in-tab P1 (Proto level 2) also installs V1, a
process-lifetime memo of EVERY stock BlockMesh the map reads (946+ masters, Python lists, never evicted); C1 as
written does not need it (a cell hit never reads stock). This times the reload after the REAL 2-cell forest edit the
lane's gui_proto_reload made (re-made here, in verify/drafts_proto by verify_gui_run.py gui_proto_reload), for:
  V0   shipped
  V2   the lane's level 2 (cell memo + texture memo + V1 stock memo)
  V2n  cell memo + texture memo, stock reads as shipped (extract's 512-entry LRU)
each compared byte-for-byte with V0; and a draw-box switch (the stack -> with the draft) for V2 / V2n, the first
Accept's case (every cell with a file in the switched root misses).

    py studies/overworld-editor/perf/verify_gui_c1_nov1.py [runs]
Evidence: out/perf/gui/verify/verify_gui_c1_nov1.json
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

C.OUT = C.OUT / "verify"
DRAFTS = C.OUT / "drafts_proto"


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import draft as D
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import render as R
    from gui_proto_reload import Proto, same_packed, same_tex
    draft = D.draft_path(C.SOURCE, root=DRAFTS)
    assert D.read_meta(draft) is not None, "run verify_gui_run.py gui_proto_reload first"
    edits = D.edits(draft)
    after = {rel: (draft / rel).read_bytes() for rel in edits}
    before = {rel: ((C.SOURCE / rel).read_bytes() if (C.SOURCE / rel).is_file() else None) for rel in edits}

    def put(state):
        for rel, data in state.items():
            p = draft / rel
            if data is None:
                p.unlink(missing_ok=True)
            else:
                p.write_bytes(data)
    stack = R.game_stack(C.GAME)
    roots = tuple(draft if p.name == C.SOURCE.name else p for p in stack)
    allcells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
    site = R.RenderSite(cells=allcells, disc=1, game=C.GAME, stack=roots)
    site_stack = R.RenderSite(cells=allcells, disc=1, game=C.GAME, stack=stack)
    put(after)
    ref, ref_t = V.load_scene(site)
    res = {"V0": [], "V2": [], "V2n": []}
    ident = {"V2": [], "V2n": []}
    sw = {"V2": [], "V2n": []}
    sw_ident = {"V2": [], "V2n": []}
    sw_miss = {"V2": [], "V2n": []}
    for i in range(runs):
        for name in ("V0", "V2", "V2n"):
            proto = Proto(R, V, roots_in_key=False)
            if name != "V0":
                proto.install(2)
                if name == "V2n":
                    R._stock_part = proto.orig_stock                  # no stock memo: as shipped
            put(before)
            if name != "V0":
                V.load_scene(site)                                    # the view's current load fills the memo
            put(after)
            t = time.perf_counter()
            p, tx = V.load_scene(site)
            res[name].append(time.perf_counter() - t)
            if name != "V0":
                ident[name].append(same_packed(p, ref) and same_tex(tx, ref_t))
                # the first Accept: the view drew the game's stack; now it draws the draft in its folder's place
                proto.cells.clear()
                V.load_scene(site_stack)
                m0 = proto.misses
                t = time.perf_counter()
                p2, tx2 = V.load_scene(site)
                sw[name].append(time.perf_counter() - t)
                sw_miss[name].append(proto.misses - m0)
                sw_ident[name].append(same_packed(p2, ref) and same_tex(tx2, ref_t))
            proto.uninstall()
        print(i, {k: round(v[-1], 3) for k, v in res.items()}, "switch", {k: round(v[-1], 3) for k, v in sw.items()},
              sw_miss, ident, sw_ident, flush=True)
    put(after)
    out = {**{k: C.stats(v) for k, v in res.items()}, "identical_to_V0": ident,
           "switch_stack_to_draft": {k: C.stats(v) for k, v in sw.items()}, "switch_misses": sw_miss,
           "switch_identical": sw_ident,
           "note": "V2n = C1 without the V1 stock memo; interleaved V0/V2/V2n per run; other lanes ran concurrently"}
    C.dump("verify_gui_c1_nov1.json", out)


if __name__ == "__main__":
    main()
