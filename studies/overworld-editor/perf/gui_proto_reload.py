"""gui lane, prototype: reload only the blocks an Accept changed, instead of the whole map (WorldDoc._draft_changed).

    py studies/overworld-editor/perf/gui_proto_reload.py [runs]

After every Accept / undo / redo / Rescan the World tab calls _load_view3d -> WorldView3DPanel.load(site) -> the
worker's load_scene over ALL 480 cells (the view is replaced by "Loading the map..." meanwhile). Everything a cell
draws is a pure function of (a) the files named Block[wbx][by] * in that cell's row directory of every root of the
site's stack and (b) stock bytes, which never change in a process (render.cell_meshes / effective_prefab /
_stock_part). So a per-cell memo keyed by those files' (root, name, size, mtime_ns) returns the very same batches for
every cell an edit did not touch.

THE CHANGE IS REAL: a draft of FF9CustomMap-world under out/perf/gui/drafts_proto (ours alone), one real
`world-forest` (--game given) written into it at c1_lab's spot; the draft is drawn as the World tab draws it after an
Accept ("With the draft": the stack with the draft in place of FF9CustomMap-world). To repeat the measurement the
edited files are swapped between their before (the live folder's bytes, read only) and after bytes, so each timed
load follows a real change of exactly the cells the Accept wrote.

Variants on the SAME after-state, each compared byte-for-byte with V0's Packed (every part's float32 array, the draw
list) and textures:
  V0  the shipped load_scene (unpatched)
  V1  + a process-lifetime memo of render._stock_part (stock decode paid once per session; models a stock cache)
  V2  + the per-cell batch memo (fingerprinted) and a texture_rgba memo (by the tex_for array's identity)
Evidence: out/perf/gui/gui_proto_reload.json.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

DRAFTS = C.OUT / "drafts_proto"
SPOT, DONOR = (1400.0, -460.0), "13,15"


def same_packed(a, b) -> bool:
    return (a.tris == b.tris and a.draws == b.draws and list(a.arrays) == list(b.arrays)
            and all(a.arrays[p].dtype == b.arrays[p].dtype and a.arrays[p].tobytes() == b.arrays[p].tobytes()
                    for p in a.arrays))


def same_tex(a, b) -> bool:
    return list(a) == list(b) and all((a[p] is None and b[p] is None) or
                                      (a[p] is not None and b[p] is not None and a[p].tobytes() == b[p].tobytes())
                                      for p in a)


class Proto:
    """The two memos, installed by monkeypatch over render / worldview3d (nothing in the package changes)."""

    def __init__(self, R, V, *, roots_in_key=True):
        self.R, self.V = R, V
        self.roots_in_key = roots_in_key                              # False: the fingerprint alone (it names each
        #                                                               file's root): a draw-box switch keeps the cells
        #                                                               no switched root holds a file for
        self.orig_cell, self.orig_stock = R._cell_batches, R._stock_part
        self.orig_load, self.orig_rgba = R.load_batches, V.texture_rgba
        self.cells, self.stock, self.rgba = {}, {}, {}
        self.hits = self.misses = 0
        self._listing = None

    # V1: stock parts, decoded once per process (a stock BlockMesh is only read by _cell_batches: np.asarray copies)
    def stock_part(self, site, bx, by, part):
        key = (str(site.game), site.disc, bx, by, part)
        if key not in self.stock:
            self.stock[key] = self.orig_stock(site, bx, by, part)
        return self.stock[key]

    # V2: the per-cell memo
    def _dir(self, d: Path):
        got = self._listing.get(d)
        if got is None:
            try:
                got = {e.name: (e.stat().st_size, e.stat().st_mtime_ns) for e in os.scandir(d) if e.is_file()}
            except OSError:
                got = {}
            self._listing[d] = got
        return got

    def fingerprint(self, site, bx, by):
        from ff9mapkit.world import mesh as M
        wbx = M.wrap_block_col(bx)
        rel = Path("FF9_Data") / "WorldMap" / f"Disc{site.disc}" / "0_1" / f"r{by}"
        head = f"Block[{wbx}][{by}] "
        fp = []
        for i, root in enumerate(self.R.site_roots(site)):
            listing = self._dir(Path(root) / rel)
            fp += [(i, str(root), n, *st) for n, st in sorted(listing.items()) if n.startswith(head)]
        return tuple(fp)

    def load_batches(self, site, part_src=None, *, stock=False, bad=None):
        self._listing = {}
        self._site_key = ((tuple(str(r) for r in self.R.site_roots(site.resolved())) if self.roots_in_key else None),
                          site.disc, str(site.game), site.parts)
        try:
            return self.orig_load(site, part_src, stock=stock, bad=bad)
        finally:
            self._listing = None

    def cell_batches(self, site, bx, by, ox, oz, part_src, stock, bad):
        if part_src is not None or bad is not None:                   # (the view passes neither)
            return self.orig_cell(site, bx, by, ox, oz, part_src, stock, bad)
        key = (self._site_key, bx, by, stock)
        fp = self.fingerprint(site, bx, by)
        hit = self.cells.get(key)
        if hit is not None and hit[0] == fp:
            self.hits += 1
            return hit[1]
        self.misses += 1
        out = self.orig_cell(site, bx, by, ox, oz, part_src, stock, bad)
        self.cells[key] = (fp, out)
        return out

    def texture_rgba(self, tex):
        if tex is None:
            return None
        k = id(tex)
        if k not in self.rgba or self.rgba[k][0] is not tex:
            self.rgba[k] = (tex, self.orig_rgba(tex))
        return self.rgba[k][1]

    def install(self, level):
        R, V = self.R, self.V
        R._stock_part = self.stock_part if level >= 1 else self.orig_stock
        R._cell_batches = self.cell_batches if level >= 2 else self.orig_cell
        R.load_batches = self.load_batches if level >= 2 else self.orig_load
        V.texture_rgba = self.texture_rgba if level >= 2 else self.orig_rgba

    def uninstall(self):
        self.install(0)


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import draft as D
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import render as R
    if DRAFTS.exists():
        shutil.rmtree(DRAFTS)
    draft = D.ensure_draft(C.SOURCE, game=C.GAME, root=DRAFTS)
    env = dict(os.environ)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    env["PYTHONPYCACHEPREFIX"] = sys.pycache_prefix
    argv = [sys.executable, "-m", "ff9mapkit", "--game", str(C.GAME), "world-forest", "--mod-folder", str(draft),
            "--center", "{:g},{:g}".format(*SPOT), "--donor", DONOR]
    t = time.perf_counter()
    r = subprocess.run(argv, cwd=str(C.KIT), capture_output=True, text=True, timeout=900, env=env)
    out = {"forest_cli_s": round(time.perf_counter() - t, 2), "forest_argv": argv[3:], "rc": r.returncode}
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    edits = D.edits(draft)
    cells = sorted({tuple(int(v) for v in m.groups()) for m in
                    (__import__("re").search(r"Disc1/.*Block\[(\d+)\]\[(\d+)\]", e) for e in edits) if m})
    out["edited_files"], out["edited_disc1_cells"] = edits, cells
    after = {rel: (draft / rel).read_bytes() for rel in edits}
    before = {rel: ((C.SOURCE / rel).read_bytes() if (C.SOURCE / rel).is_file() else None) for rel in edits}
    print("forest", out["forest_cli_s"], "s; edited", len(edits), "files in cells", cells)

    def put(state):
        for rel, data in state.items():
            p = draft / rel
            if data is None:
                p.unlink(missing_ok=True)
            else:
                p.write_bytes(data)

    # the site the World tab draws after an Accept: the stack with the draft in place of its folder
    stack = R.game_stack(C.GAME)
    roots = tuple(draft if p.name == C.SOURCE.name else p for p in stack)
    allcells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
    site = R.RenderSite(cells=allcells, disc=1, game=C.GAME, stack=roots)
    proto = Proto(R, V)

    put(before)
    V.load_scene(site)                                                # warm the process (env, tex_for cache)
    put(after)
    ref_p, ref_t = V.load_scene(site)                                 # V0's answer for the after-state
    put(before)
    pa, _ = V.load_scene(site)
    out["change_visible"] = not same_packed(pa, ref_p)                # the edit shows: A != B

    res = {"V0": [], "V1": [], "V2": []}
    ident = {"V1": [], "V2": []}
    misses = []
    for i in range(runs):
        for level, name in ((0, "V0"), (1, "V1"), (2, "V2")):
            proto.install(level)
            put(before)
            if level == 2:
                V.load_scene(site)                                    # the user's current load (fills the memo)
            put(after)                                                # the Accept writes its cells
            h0, m0 = proto.hits, proto.misses
            t = time.perf_counter()
            p, tx = V.load_scene(site)
            res[name].append(time.perf_counter() - t)
            if level == 2:
                misses.append(proto.misses - m0)
            if level:
                ident[name].append(same_packed(p, ref_p) and same_tex(tx, ref_t))
            proto.uninstall()
        print(i, {k: round(v[-1], 3) for k, v in res.items()}, "V2 cells recomputed", misses[-1:], ident)
    # the undo: the after-state back to before (V2 from a memo that holds the after-state)
    proto.install(2)
    put(after)
    V.load_scene(site)
    put(before)
    t = time.perf_counter()
    pu, _ = V.load_scene(site)
    undo_v2 = time.perf_counter() - t
    proto.uninstall()
    put(before)
    pu0, _ = V.load_scene(site)
    out.update({k: C.stats(v) for k, v in res.items()})
    out["identical_to_V0"] = ident
    out["V2_cells_recomputed"] = misses
    out["undo_V2_s"] = round(undo_v2, 3)
    out["undo_V2_identical"] = same_packed(pu, pu0)
    out["note"] = ("V0/V1/V2 run on the same after-state; V2's memo was filled by a load of the before-state, as the "
                   "view has it when the Accept lands. Other lanes ran concurrently: min is the headline.")
    put(after)                                                        # leave the draft as the CLI wrote it
    C.dump("gui_proto_reload.json", out)


if __name__ == "__main__":
    main()
