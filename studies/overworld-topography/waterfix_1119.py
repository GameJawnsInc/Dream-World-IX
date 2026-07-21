"""waterfix_1119.py -- fix the PALE / genuinely-UNNAVIGABLE water at world (755,-1216) = Block[11][19].

THE DEFECT (in-game 2026-07-20): near world (755,-1216) tiles render pale/flat and BOTH boat and
airship are blocked. The cell is the (11,19) corner of the desert-beach island carried
"(8,17)+2x2 -> (11,18)+2x2".  This was the first defect of the whole arc where the offline census
oracle (fed all three deployed .ff9mesh files) reported ZERO misses while the live engine blocked it.

ROOT CAUSE -- s34 source-confirmed (memoria-patches/s34-worldmap-mesh-override.patch, WMWorld.cs):
  * A sea cell only diverts to a reclaim DONOR prefab when `HasLandOverride(disc,x,y)` is true, and
    that predicate is TRUE iff a `Block[x][y] Terrain.ff9mesh` override FILE exists (patch :286-289).
  * Block[11][19] carries NO Terrain override (donor (8,18) is water-only) -> HasLandOverride=FALSE ->
    the divert never fires -> the cell loads the generic `SeaBlockPrefab`, whose ONLY child transform
    is `Sea4`.  `LoadBlock`/`RegisterBlockComponent` look up an override PER prefab-transform NAME
    (`TryLoad("...Block[11][19] " + transform.name)`), so ONLY `Block[11][19] Sea4.ff9mesh` binds.
  * The deployed `Sea3.ff9mesh` / `Sea5.ff9mesh` have no matching transform on SeaBlockPrefab and are
    silently skipped -- and the `Donor.txt="8,18"` sidecar is DEAD (only read inside the un-armed
    divert).  Confirmed by GAME/Memoria.log line 55: only "Block[11][19] Sea4" loaded, while every
    sibling island cell (11,18)/(12,18)/(12,19) -- all of which DO ship a Terrain override -> divert ->
    a rich donor -- loaded all their parts.
  * The carried donor (8,18) Sea4 mesh is a PARTIAL 474-tri interior band; at the donor's home its
    holes were covered by the Sea3/Sea5 layers.  Carried here with only Sea4 binding, those holes are
    real ground-query holes -> `place()` MISS -> defaultHeight=0, which is simultaneously an invisible
    VEHICLE WALL (boat+airship blocked) AND a void/pale render (placement rule 2).  This script's
    ORACLE GATE reproduces it: pristine Sea4 alone = 304/4096 cell misses; the merge = 0.

THE FIX (Route 2 / option c -- the convergent recommendation of the engine-source + oracle-gap
forensics; the safest on engine-semantics grounds because it stays on the exact SeaBlockPrefab path
every open-ocean cell already uses and invokes NO new engine behavior):
  MERGE the Sea3 + Sea5 triangles into the single bindable `Sea4` part (topograph tangent.x carried
  verbatim -> boat-legality byte-preserved), then DELETE the now-inert Sea3/Sea5 + the dead Donor.txt
  so the on-disk state equals what the engine loads (a Terrain-less water cell = exactly ONE file, the
  complete Sea4).  Mirrored to Disc4 by explicit byte-copy -- NOT discmirror.auto_mirror, whose
  FREE-RIDE PIN (discmirror.py:241-265) would read the inert Donor.txt and RESURRECT donor (8,18)'s
  Sea3/Sea5 onto Disc4, re-creating the orphans and a Disc1/Disc4 asymmetry.

IDEMPOTENT: reads the PRE-FIX pristine parts from backups/waterfix-1119.20260720/ (captured before the
first edit), recomputes the merge deterministically (byte-identical every run), rewrites, re-deletes.

Run:  py studies/overworld-topography/waterfix_1119.py
"""
import dataclasses
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.world import mesh as M                            # noqa: E402
from ff9mapkit.world import placement as P                       # noqa: E402
from ff9mapkit.world.extract import decode_id                    # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "beach_island_sea_patch", Path(__file__).with_name("beach_island_sea_patch.py"))
bsp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bsp)                                    # reuse merge_local_mesh (FLAT-MESH flatten)

# --------------------------------------------------------------------------- constants
MOD = "FF9CustomMap-world"
GAME = Path(r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX")
WORLD = GAME / MOD / "FF9_Data" / "WorldMap"
BK = REPO / "backups" / "waterfix-1119.20260720"
BX, BY = 11, 19                                                  # the defect cell
DONOR = (8, 18)                                                  # its (inert) carry donor
DISCS = (1, 4)                                                   # TWO-TREE law
LOD = "0_1"
BOAT_TOPO = {54, 57}                                            # sea3 shallow / sea4 deep -- boat+airship legal
DEFECT_WORLD = (755.0, -1216.0)                                 # user report; local (51, 0) in cell (11,19)

# pristine (pre-fix) part sizes -- a guard that the backup is the real pre-merge state
PRISTINE = {"Sea4": 73964, "Sea3": 956, "Sea5": 5012}          # 474 / 6 / 32 tris


def _rdir(disc):
    return WORLD / f"Disc{disc}" / LOD / f"r{BY}"


def _bk(disc, name):
    return BK / f"Disc{disc}__Block[{BX}][{BY}] {name}"


def _load(path, part):
    return M.blockmesh_from_ff9mesh(str(path), disc=1, x=BX, y=BY, lod=LOD, part=part)


# --------------------------------------------------------------------------- 0. backup guard
def check_backup():
    for disc in DISCS:
        for part, size in PRISTINE.items():
            p = _bk(disc, f"{part}.ff9mesh")
            if not p.exists():
                raise SystemExit(f"REFUSE: pristine backup missing: {p}")
            if p.stat().st_size != size:
                raise SystemExit(f"REFUSE: {p} is {p.stat().st_size}B, expected pristine {size}B "
                                 f"(the backup is NOT the pre-merge state -- do not proceed)")
        if not _bk(disc, "Donor.txt").exists():
            raise SystemExit(f"REFUSE: Donor.txt backup missing for disc {disc}")
    print(f"[0] backup OK: pristine Sea4/Sea3/Sea5 + Donor.txt for discs {DISCS} in {BK.name}/")


# --------------------------------------------------------------------------- the effective-prefab ORACLE GATE
def effective_parts(rdir, bx, by):
    """Model the s34 EFFECTIVE prefab -- the oracle-gap fix.  The engine binds overrides ONLY for
    the transforms the effective prefab exposes:
      * a `Terrain.ff9mesh` override present  -> HasLandOverride true -> the reclaim DIVERT fires ->
        the effective prefab is the Donor.txt donor prefab (its full part set; un-overridden parts
        free-ride from the donor).  [modeled for completeness; NOT the (11,19) path]
      * NO Terrain override                   -> HasLandOverride false -> `SeaBlockPrefab`, which
        exposes exactly {"Sea4"}.  Any Sea3/Sea5/... override on disk is DROPPED (never bound).
    Returns the set of part names whose override will actually load."""
    if (rdir / f"Block[{bx}][{by}] Terrain.ff9mesh").exists():
        return None                                             # land/divert path -- resolve via Donor.txt donor
    return {"Sea4"}                                            # SeaBlockPrefab (log-derived; the only sea transform)


def effective_meshlist(rdir, bx, by, overrides):
    """Build the meshlist the engine ACTUALLY registers for the cell, given a dict {part: BlockMesh}
    of the overrides sitting on disk.  Keeps only the parts the effective prefab exposes -- so a
    Sea3/Sea5 file that will never bind is DROPPED (the exact gap the prior census missed)."""
    parts = effective_parts(rdir, bx, by)
    if parts is None:
        raise SystemExit("land-divert path not modeled for this cell (it has no Terrain override)")
    return [(p, overrides[p]) for p in ("Object", "Terrain", "Beach1", "Beach2", "Sea1", "Sea2",
                                        "Sea3", "Sea4", "Sea5", "Sea6") if p in parts and p in overrides]


def _cell_census(meshlist, step=1.0):
    """Sky-cast the whole (11,19) cell in LOCAL frame (x[0,64], z[-64,0]); MISS + covered-topo histogram."""
    miss, topos, total = [], {}, 0
    lx = 0.25
    while lx < 64.0:
        lz = -0.25
        while lz > -64.0:
            total += 1
            _, nm, _, tp = P.place(meshlist, lx, lz, y=0.0, sky=True)
            if nm == "MISS":
                miss.append((round(lx, 2), round(lz, 2)))
            else:
                topos[tp] = topos.get(tp, 0) + 1
            lz -= step
        lx += step
    return miss, total, topos


def _window_census(meshlist, step=0.5):
    """The 40x40u window at (755,-1216), portion inside cell (11,19): local x[31,64) z[-20,0]
    (world z>-1216 is neighbour (11,18), covered by its own full override set per Memoria.log:35-38)."""
    miss = tot = 0
    lx = 31.0
    while lx < 64.0:
        lz = 0.0
        while lz >= -20.0:
            tot += 1
            _, nm, _, _ = P.place(meshlist, lx, lz, y=0.0, sky=True)
            miss += (nm == "MISS")
            lz -= step
        lx += step
    return miss, tot


# --------------------------------------------------------------------------- main
def main():
    check_backup()

    # --- 1. load pristine parts + build the merged Sea4 -------------------------------------------
    s4 = _load(_bk(1, "Sea4.ff9mesh"), "Sea4")
    s3 = _load(_bk(1, "Sea3.ff9mesh"), "Sea3")
    s5 = _load(_bk(1, "Sea5.ff9mesh"), "Sea5")
    n4, n3, n5 = len(s4.flat_index) // 3, len(s3.flat_index) // 3, len(s5.flat_index) // 3
    print(f"[1] pristine parts: Sea4={n4} tris, Sea3={n3}, Sea5={n5} (all in LOCAL frame, Y=0)")
    merged = bsp.merge_local_mesh(bsp.merge_local_mesh(s4, s3), s5)
    merged = dataclasses.replace(merged, name=f"Block[{BX}][{BY}] Sea4")
    nm = len(merged.flat_index) // 3

    # --- gate (a) BYTE-DIFF: the merge only APPENDS Sea3+Sea5; the pristine Sea4 base is preserved --
    assert nm == n4 + n3 + n5 == 512, f"tri count {nm} != {n4}+{n3}+{n5}"
    base_pos = merged.chan_arrays[list(merged.channels)[0]][:s4.vcount]
    assert base_pos == s4.chan_arrays[list(s4.channels)[0]], "merge altered the Sea4 base verts"
    print(f"[a] byte-diff: merged Sea4 = {n4}+{n3}+{n5} = {nm} tris; first {n4} tris = pristine Sea4 verbatim, "
          f"Sea3+Sea5 appended, nothing else changed")

    # --- gate (b) FLAT-MESH INVARIANT (verts == idx) ---------------------------------------------
    assert merged.vcount == len(merged.flat_index) == 3 * nm, "FLAT-MESH INVARIANT violated"
    topos = {}
    for t in range(nm):
        tp = decode_id(int(round(merged.tangents[merged.flat_index[3 * t]][0])))["topograph"]
        topos[tp] = topos.get(tp, 0) + 1
    assert set(topos) <= BOAT_TOPO, f"non-boat topo carried in: {set(topos) - BOAT_TOPO}"
    print(f"[b] flat-mesh: vcount={merged.vcount} == idx={len(merged.flat_index)}; topos={topos} "
          f"(all in BOAT_TOPO {sorted(BOAT_TOPO)})")

    # --- gate (c) FREE-RIDE AUDIT ----------------------------------------------------------------
    print("[c] free-ride audit -- effective prefab = SeaBlockPrefab (no Terrain override -> no divert):")
    print(f"      exposed transforms = {{Sea4}}  (SeaBlockPrefab is generic deep ocean)")
    print(f"      Sea4     -> OVERRIDDEN by our merged {nm}-tri file (complete, MISS=0 below)")
    print(f"      Sea3/Sea5-> NOT exposed by SeaBlockPrefab -> never bound -> DELETED (folded into Sea4)")
    print(f"      Donor.txt='{DONOR[0]},{DONOR[1]}' -> INERT (read only inside the un-armed divert) -> DELETED")
    print(f"      => nothing foreign free-rides into the water; the cell binds exactly ONE part, Sea4")

    # --- gate (d) THE MONEY GATE: oracle with the effective-prefab gate ---------------------------
    #   PRE  = the pristine files as they sat on disk (Sea3/Sea4/Sea5 + Donor.txt, no Terrain).
    #          effective_meshlist DROPS Sea3/Sea5 -> Sea4-only -> must reproduce the live MISS.
    #   POST = the merged Sea4 alone -> must be MISS=0, boat-legal.
    pre_overrides = {"Sea3": s3, "Sea4": s4, "Sea5": s5}
    pre_ml = effective_meshlist(_rdir(1), BX, BY, pre_overrides)
    post_ml = effective_meshlist(_rdir(1), BX, BY, {"Sea4": merged})
    assert [p for p, _ in pre_ml] == ["Sea4"], "effective gate should drop Sea3/Sea5"
    pre_miss, pre_tot, _ = _cell_census(pre_ml)
    post_miss, post_tot, post_topos = _cell_census(post_ml)
    pre_w, pre_wt = _window_census(pre_ml)
    post_w, post_wt = _window_census(post_ml)
    if not pre_miss:
        raise SystemExit("GATE d FAILED: the PRE config did not reproduce the defect offline")
    if post_miss:
        raise SystemExit(f"GATE d FAILED: the POST merged Sea4 still MISSES ({len(post_miss)}) -- "
                         f"needs mesh.fill_missing_grid_quads")
    xs = [m[0] for m in pre_miss]
    zs = [m[1] for m in pre_miss]
    print(f"[d] MONEY GATE -- effective-prefab oracle (only Sea4 binds for this Terrain-less cell):")
    print(f"      PRE  (pristine Sea4 only, = what the live engine loaded):")
    print(f"           cell   MISS={len(pre_miss)}/{pre_tot}  hole bbox local x[{min(xs)},{max(xs)}] "
          f"z[{min(zs)},{max(zs)}] = world x[{704+min(xs):.0f},{704+max(xs):.0f}] "
          f"z[{-1216+min(zs):.0f},{-1216+max(zs):.0f}]  (contains the reported {DEFECT_WORLD})")
    print(f"           window MISS={pre_w}/{pre_wt}  <-- reproduces the live defect offline")
    print(f"      POST (merged Sea4):  cell MISS={len(post_miss)}/{post_tot}  window MISS={post_w}/{post_wt}  "
          f"covered topos={post_topos} (all boat-legal)")

    # --- 2. DEPLOY (both discs, explicit) --------------------------------------------------------
    written = []
    for disc in DISCS:
        rdir = _rdir(disc)
        rdir.mkdir(parents=True, exist_ok=True)
        p = M.write_ff9mesh(dataclasses.replace(merged, disc=disc),
                            rdir / f"Block[{BX}][{BY}] Sea4.ff9mesh")
        written.append(p)
        for dead in ("Sea3.ff9mesh", "Sea5.ff9mesh", "Donor.txt"):
            f = rdir / f"Block[{BX}][{BY}] {dead}"
            if f.exists():
                f.unlink()
    print(f"[2] deployed merged Sea4 + removed Sea3/Sea5/Donor.txt on discs {DISCS}")

    # --- gate (e) TWO-TREE mirror verify ---------------------------------------------------------
    b1 = (_rdir(1) / f"Block[{BX}][{BY}] Sea4.ff9mesh").read_bytes()
    b4 = (_rdir(4) / f"Block[{BX}][{BY}] Sea4.ff9mesh").read_bytes()
    assert b1 == b4, "Disc1 and Disc4 Sea4 differ"
    leftovers = [f.name for disc in DISCS for f in _rdir(disc).glob(f"Block[{BX}][{BY}] *")
                 if not f.name.endswith("Sea4.ff9mesh")]
    assert not leftovers, f"unexpected leftover (11,19) files: {leftovers}"
    print(f"[e] two-tree: Disc1 Sea4 == Disc4 Sea4 ({len(b1)}B, byte-identical); "
          f"(11,19) now has exactly ONE file per disc (Sea4)")

    print("\nDONE. Block[11][19] is a clean single-part (Sea4) override; the merged mesh covers the whole "
          "cell MISS=0, boat/airship-legal.\nRevert = copy the 8 files in backups/waterfix-1119.20260720/ "
          "back into the two r19 dirs (restores pristine Sea4 + Sea3/Sea5 + Donor.txt).")


if __name__ == "__main__":
    main()
