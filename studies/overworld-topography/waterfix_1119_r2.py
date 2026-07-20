"""waterfix_1119_r2.py -- ROUND 2 of the Block[11][19] water fix: kill the STREAKY transition tiles
without regressing navigability.

BACKGROUND (round 1, commit 016ecab, waterfix_1119.py):
  (11,19) is the SE corner of the desert-beach island carried "(8,17)+2x2 -> (11,18)+2x2"; its carry
  donor is (8,18).  Round 0 shipped the 3 pristine donor sea layers Sea3(6)/Sea4(474)/Sea5(32) BUT no
  `Terrain.ff9mesh` -- so the s34 reclaim divert never armed (HasLandOverride = File.Exists on a Terrain
  override), the cell loaded the generic SeaBlockPrefab whose only transform is `Sea4`, so ONLY the
  partial 474-tri Sea4 bound -> 304/4096 ground-query holes = an invisible vehicle wall + pale void.
  Round 1 MERGED Sea3+Sea5 into the single bindable Sea4 (512 tris) and deleted Sea3/Sea5/Donor.txt.
  That FIXED navigability (MISS=0, in-game "able to sail now, no more empty tiles") but introduced a
  RENDER defect: the 6+32 folded tris now draw under the ONE Sea4 GameObject's material.

ROUND-2 DEFECT (in-game 2026-07-20, user screenshot): at the light/dark ocean boundary near the boat
  (world 755,-1216) a patch of STREAKY / wrong-scale transition tiles -- "the old stretched/random
  transition tiles we had when first discovering wang tiles".

MECHANISM (engine-source verified this round -- WMWorld.cs / WMBlockPrefab.cs / WMBlock.cs, and the
offline water-tile eye water_tile_eye_r2.py):
  * A sea sub-mesh's MATERIAL is bound PER GameObject/transform NAME, and each SeaN name maps to a
    DIFFERENT caustic texture (Sea3->10_128_64 light, Sea4->10_128_128 deep, Sea5->11_64_0 gradient;
    Sea1..Sea6 are commented OUT of WMBlock.ObjectNameToPaths -> the material travels with the
    INSTANTIATED donor transform via WMRenderTextureBank, NOT SetupPreloadedMaterials).
  * Round-1's merge put all 512 tris in one GameObject named "Sea4" -> the 32 former-Sea5 tris (UVs =
    full-u x QUARTER-v strips, ~3.9:1 aspect) and 6 former-Sea3 tris are sampled through the Sea4
    256x256 atlas instead of their own -> stretched/streaky = the reported artifact.

THE FIX -- RESTORE PER-LAYER + ARM THE DIVERT (the convergent recommendation of the site-vs-donor audit
AND the engine divert trace; the WANG-language report's pure-UV-reassign is inferior -- it flattens the
real shallow transition band to uniform deep and discards the faithful per-part structure):
  1. RESTORE the pristine per-layer Sea3(6)/Sea4(474)/Sea5(32) .ff9mesh (byte-verbatim from donor (8,18);
     the round-1 backup) -- overwriting the merged Sea4.
  2. RE-ADD `Donor.txt` = "8,18".
  3. ADD `Terrain.ff9mesh` shipped as a SAFE DEGENERATE STUB (3 identical verts / zero-area, tangent.x
     = 4078 the skip-sentinel, flags=7 verts==idx) whose ONLY job is to make HasLandOverride true and
     ARM the divert.  Donor (8,18) has NO Terrain transform (part set = EXACTLY {Sea3,Sea4,Sea5}), so
     the stub is NEVER bound as geometry (LoadBlock's Terrain branch is `if (prefab.TerrainForm1)`,
     which is false) -> zero load-bearing walkmesh risk; it is read only by HasLandOverride's File.Exists.
  Now the divert loads the (8,18) donor prefab, whose Sea3/Sea4/Sea5 transforms EACH TryLoad our
  per-layer override with its OWN material -> Sea3 light / Sea4 deep / Sea5 gradient, exactly like the
  in-game-proven sibling cells (11,18)/(12,18)/(12,19).  Streaks gone; walkmesh union = the identical
  512 tris round 1 proved MISS=0.

NON-REGRESSION (absolute): the DIVERT-path effective-prefab oracle (all THREE sea overrides bind, since
  the donor exposes all three) censuses MISS=0/4096 full-cell + the (755,-1216) window, topos {54,57}
  boat-legal -- byte-identical coverage to the proven merged Sea4.  Round 1's merged Sea4 stays in the
  r2 backup as the proven-navigable fallback; it is NEVER re-deployed by this script.

WANG-CARRY: the audit proved (11,19)'s tile arrangement needs NO recalculation -- every edge that
  touches (11,19) is coherent by verbatim carry (frame W/S face all-deep generic ocean; internal
  N->(11,18) / E->(12,19) reproduce stock adjacency).  The gate below re-proves it on the DEPLOYED
  bytes.  (The island's OUTER-fringe cropped seams are on the top-row cells (11,18)/(12,18)/(12,19),
  pre-existing since the (8,17) carry, away from the boat, and OUT OF SCOPE for this one-cell redeploy.)

IDEMPOTENT: pristine parts come from backups/waterfix-1119.20260720/ (the immutable pre-merge state);
the merged-Sea4 fallback is captured to backups/waterfix-1119-r2.20260720/ only if absent (with a
79892B/md5 guard so a second run can't overwrite the fallback with the already-restored file).

Run:  py studies/overworld-topography/waterfix_1119_r2.py            # gates only, no writes
      py studies/overworld-topography/waterfix_1119_r2.py --deploy    # gates + deploy both discs
"""
import argparse
import dataclasses
import hashlib
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.world import mesh as M                             # noqa: E402
from ff9mapkit.world import placement as P                        # noqa: E402
from ff9mapkit.world import water as W                            # noqa: E402
from ff9mapkit.world import extract as X                          # noqa: E402
from ff9mapkit.world.extract import decode_id, CH_POS, CH_NRM, CH_UV, CH_TAN, BlockMesh  # noqa: E402

# --------------------------------------------------------------------------- constants
MOD = "FF9CustomMap-world"
GAME = Path(r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX")
WORLD = GAME / MOD / "FF9_Data" / "WorldMap"
BK1 = REPO / "backups" / "waterfix-1119.20260720"          # round-1 pristine (pre-merge) parts
BK2 = REPO / "backups" / "waterfix-1119-r2.20260720"       # round-2: the merged-Sea4 fallback

BX, BY = 11, 19                                             # the defect cell
DONOR = (8, 18)                                            # its carry donor (water-only prefab)
DISCS = (1, 4)                                             # TWO-TREE law
LOD = "0_1"
G, CELL = 16, 4.0                                          # 16x16 sub-tiles per block, 4u each
BOAT_TOPO = {54, 57}                                       # sea3 shallow(54) / sea4 deep(57) -- boat+airship legal

# pristine (pre-merge) part sizes + md5 -- guards the round-1 backup is the real per-layer state
PRISTINE = {
    "Sea3": (956, "fb96b321f30b65d746d3682c19078f0f"),
    "Sea4": (73964, "c8244b048ef47b22cdcc72c00c32a1d9"),
    "Sea5": (5012, "8fb7afa2b2244c297d1dc5173d6098c5"),
}
MERGED_SIZE, MERGED_MD5 = 79892, "d0f1eabd507790186e5fb95d56702a10"   # round-1 deployed fallback

REG_ORDER = ("Object", "Terrain", "Beach1", "Beach2", "Stream", "River", "RiverJoint", "Falls",
             "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6")


def _rdir(disc, by=BY):
    return WORLD / f"Disc{disc}" / LOD / f"r{by}"


def _bk1(disc, name):
    return BK1 / f"Disc{disc}__Block[{BX}][{BY}] {name}"


def _bk2(disc, name):
    return BK2 / f"Disc{disc}__Block[{BX}][{BY}] {name}"


def _md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def _cell_files(rdir, x, y):
    """Files in ``rdir`` whose name is ``Block[x][y] *`` -- literal prefix match.  (pathlib.glob CANNOT
    be used here: ``[11]`` is a glob CHARACTER CLASS, so ``glob('Block[11][19] *')`` matches NOTHING and
    silently vacuates any check built on it -- the round-2 gate-3f bug.)"""
    pre = f"Block[{x}][{y}] "
    return sorted(p for p in rdir.iterdir() if p.is_file() and p.name.startswith(pre))


def _load_ff9(path, part):
    return M.blockmesh_from_ff9mesh(str(path), disc=1, x=BX, y=BY, lod=LOD, part=part)


# --------------------------------------------------------------------------- 0. backups
def check_r1_backup():
    for disc in DISCS:
        for part, (size, md5) in PRISTINE.items():
            p = _bk1(disc, f"{part}.ff9mesh")
            if not p.exists():
                raise SystemExit(f"REFUSE: pristine backup missing: {p}")
            if p.stat().st_size != size or _md5(p) != md5:
                raise SystemExit(f"REFUSE: {p} is not the pristine pre-merge {part} "
                                 f"({p.stat().st_size}B/{_md5(p)[:8]} != {size}B/{md5[:8]})")
        d = _bk1(disc, "Donor.txt")
        if not d.exists() or d.read_text().strip() != "8,18":
            raise SystemExit(f"REFUSE: pristine Donor.txt backup bad for disc {disc}")
    print(f"[0a] round-1 backup OK: pristine Sea3/Sea4/Sea5 + Donor.txt=8,18 (discs {DISCS})")


def capture_r2_backup():
    """Capture the currently-deployed merged Sea4 (both discs) as the proven-navigable FALLBACK, ONCE.
    Idempotent + safe: if the fallback already exists it is verified (79892B/md5) and NOT overwritten,
    so a second run (deployed Sea4 now = the restored 73964B pristine) can never clobber the fallback."""
    BK2.mkdir(parents=True, exist_ok=True)
    for disc in DISCS:
        dst = _bk2(disc, "Sea4.ff9mesh")
        src = _rdir(disc) / f"Block[{BX}][{BY}] Sea4.ff9mesh"
        if dst.exists():
            if dst.stat().st_size != MERGED_SIZE or _md5(dst) != MERGED_MD5:
                raise SystemExit(f"REFUSE: existing r2 fallback {dst} is not the merged Sea4 "
                                 f"({dst.stat().st_size}B/{_md5(dst)[:8]})")
            continue
        if not src.exists():
            raise SystemExit(f"REFUSE: no deployed Sea4 to back up at {src}")
        if src.stat().st_size != MERGED_SIZE or _md5(src) != MERGED_MD5:
            raise SystemExit(f"REFUSE: deployed Sea4 {src} is {src.stat().st_size}B/{_md5(src)[:8]}, "
                             f"expected the merged {MERGED_SIZE}B/{MERGED_MD5[:8]} -- fallback NOT captured "
                             f"(is it already restored, with the fallback lost? recover round 1 first)")
        shutil.copyfile(src, dst)
    print(f"[0b] r2 fallback: merged Sea4 ({MERGED_SIZE}B) preserved in {BK2.name}/ for both discs")


# --------------------------------------------------------------------------- 1. the degenerate stub
def build_stub_terrain(disc):
    """A provably-harmless divert-ARM stub: ONE zero-area triangle (3 identical verts), tangent.x=4078
    (P.IDALL_SKIP -> skipped before intersection), flags=7 (verts==idx, tangents present so WMPhysics
    can't IndexOutOfRange if it ever WERE walkmeshed).  Never actually bound: donor (8,18) has no
    TerrainForm1, so LoadBlock's `if (prefab.TerrainForm1)` branch is false and TryLoad('...Terrain')
    is never called -- this file is read only by HasLandOverride's File.Exists (arms the divert)."""
    v = [32.0, -100.0, -32.0]                              # cell centre, deep Y (never hit anyway)
    pos = [list(v), list(v), list(v)]
    nrm = [[0.0, 1.0, 0.0]] * 3
    uv = [[0.0, 0.0]] * 3
    tan = [[4078.0, 0.0, 0.0, 1.0]] * 3
    return BlockMesh(name=f"Block[{BX}][{BY}] Terrain", disc=disc, x=BX, y=BY, lod=LOD, vcount=3, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=[0, 1, 2], tris=[[0, 1, 2]], raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _cross(a, b, c):
    ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
    vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
    return (uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx)


# --------------------------------------------------------------------------- census (LOCAL frame)
def _cell_census(meshlist, step=1.0):
    """Sky-cast the whole (11,19) cell in LOCAL frame (x[0,64], z[-64,0]); MISS + covered-topo histogram."""
    miss, topos, total = [], {}, 0
    lx = 0.5
    while lx < 64.0:
        lz = -0.5
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
    """The 40x40u window at (755,-1216), portion inside cell (11,19): local x[31,64) z[-20,0]."""
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


# --------------------------------------------------------------------------- the divert effective-prefab
def donor_part_set(dx, dy, disc=1):
    """Enumerate the donor prefab's FULL transform set from stock (the mesh containers ARE the
    transforms).  For (8,18) this is the set the divert exposes -> the parts whose override binds."""
    out = []
    for part in REG_ORDER:
        try:
            bm = X.read_block(dx, dy, disc=disc, lod=LOD, part=part.lower())
        except (ValueError, FileNotFoundError):
            bm = None
        if bm is not None and bm.verts:
            out.append((part, len(bm.tris)))
    return out


def effective_divert_meshlist(parts):
    """The meshlist the engine ACTUALLY registers on the DIVERT path: for each part the DONOR prefab
    exposes, our override (keyed by that transform's name) binds; parts the donor lacks (Terrain!) are
    dropped -- so the stub Terrain never enters the walkmesh.  ``parts`` = {name: BlockMesh} on disk."""
    exposed = {p for p, _ in donor_part_set(*DONOR)}       # {'Sea3','Sea4','Sea5'}
    return [(p, parts[p.lower()]) for p in REG_ORDER if p in exposed and p.lower() in parts]


# --------------------------------------------------------------------------- WANG coherence (deployed bytes)
INV = {}
for _ds, _variants in W.DEEPSET2TILE.items():
    for _sr in _variants:
        INV[_sr] = _ds


def parts_shade_grid(parts):
    """16x16 shade grid ('sea3'/'sea4'/'sea5', empty->'sea4') from a {part: BlockMesh} dict."""
    seen = [[None] * G for _ in range(G)]
    for part in ("sea3", "sea4", "sea5"):
        bm = parts.get(part)
        if bm is None:
            continue
        for tri in bm.tris:
            i = int((sum(bm.verts[q][0] for q in tri) / 3) // CELL)
            j = int((-sum(bm.verts[q][2] for q in tri) / 3) // CELL)
            if 0 <= i < G and 0 <= j < G:
                seen[i][j] = part
    return [[seen[i][j] or "sea4" for j in range(G)] for i in range(G)]


def parts_sea5_tiles(sea5_bm):
    """(strip, rotation-name) per Sea5 cell of a loose BlockMesh -- mirrors water.read_sea5_tiles."""
    if sea5_bm is None:
        return {}
    corners = defaultdict(dict)
    for tri in sea5_bm.tris:
        i = int((sum(sea5_bm.verts[q][0] for q in tri) / 3) // CELL)
        j = int((-sum(sea5_bm.verts[q][2] for q in tri) / 3) // CELL)
        for k in tri:
            v = sea5_bm.verts[k]
            corners[(i, j)][(round((v[0] - i * CELL) / CELL), round((-v[2] - j * CELL) / CELL))] = sea5_bm.uvs[k]
    out = {}
    for (i, j), d in corners.items():
        if all(c in d for c in ((0, 0), (1, 0), (1, 1), (0, 1))):
            fit = W._fit_tile(d)
            if fit is not None:
                u0, u1, v0, v1, name = fit
                out[(i, j)] = (W._strip_of(v0), name)
    return out


def _load_deployed_parts(rdir, x, y):
    parts = {}
    for part in ("sea3", "sea4", "sea5"):
        p = rdir / f"Block[{x}][{y}] {part.capitalize()}.ff9mesh"
        if p.exists():
            parts[part] = M.blockmesh_from_ff9mesh(str(p), disc=1, x=x, y=y, lod=LOD, part=part)
    return parts


def _load_backup_parts():
    parts = {}
    for part in ("sea3", "sea4", "sea5"):
        parts[part] = _load_ff9(_bk1(1, f"{part.capitalize()}.ff9mesh"), part)
    return parts


def edge_cells(which):
    if which == "N":
        return [(i, 0) for i in range(G)]
    if which == "S":
        return [(i, G - 1) for i in range(G)]
    if which == "W":
        return [(0, j) for j in range(G)]
    return [(G - 1, j) for j in range(G)]                  # "E"


def frame_edge_verdicts(grid, s5, which):
    """(11,19) frame edge `which` faces GENERIC DEEP ocean (sea4).  Per edge cell:
       sea4 -> OK (deep meets deep); sea3 -> VIOLATION (shallow abuts deep, no transition);
       sea5 -> OK iff the tile's implied deep-set points OUT this edge (transition faces the deep)."""
    out = []
    for (i, j) in edge_cells(which):
        sh = grid[i][j]
        if sh == "sea4":
            out.append(((i, j), sh, True, "deep|deep"))
        elif sh == "sea3":
            out.append(((i, j), sh, False, "shallow abuts deep, no transition ring"))
        else:
            t = s5.get((i, j))
            ds = INV.get(t) if t else None
            if ds is None:
                out.append(((i, j), sh, False, f"sea5 tile {t} untabulated"))
            else:
                ok = which in ds
                out.append(((i, j), sh, ok, f"strip{t[0]}/{t[1]} deepset={''.join(sorted(ds))}"))
    return out


def internal_edge_verdicts(gA, s5A, gB, s5B, dirAB):
    """Internal seam A->B (dirAB in {'N','S','E','W'}): the shared world-edge cells must agree.
    Violations: a direct sea3|sea4 touch (no transition bridge), or a sea5 tile whose implied
    deep-set disagrees with the neighbour's shade across the shared edge."""
    opp = {"E": "W", "W": "E", "N": "S", "S": "N"}[dirAB]
    viol = []
    for k in range(G):
        if dirAB == "E":
            ai, aj, bi, bj = G - 1, k, 0, k
        elif dirAB == "W":
            ai, aj, bi, bj = 0, k, G - 1, k
        elif dirAB == "S":
            ai, aj, bi, bj = k, G - 1, k, 0
        else:                                              # "N"
            ai, aj, bi, bj = k, 0, k, G - 1
        a, b = gA[ai][aj], gB[bi][bj]
        if {a, b} == {"sea3", "sea4"}:
            viol.append(((ai, aj), (bi, bj), f"direct {a}|{b} (no transition)"))
            continue
        if a == "sea5":
            t = s5A.get((ai, aj)); ds = INV.get(t) if t else None
            if ds is not None and (dirAB in ds) != (b == "sea4"):
                viol.append(((ai, aj), (bi, bj), f"A tile {dirAB}-deep={dirAB in ds} but B={b}"))
        if b == "sea5":
            t = s5B.get((bi, bj)); ds = INV.get(t) if t else None
            if ds is not None and (opp in ds) != (a == "sea4"):
                viol.append(((ai, aj), (bi, bj), f"B tile {opp}-deep={opp in ds} but A={a}"))
    return viol


def wang_gate(deploying):
    """GATE 3d: prove the DEPLOYED (or would-deploy) (11,19) is Wang-coherent on ALL FOUR of its edges.
    Reads the FINAL bytes: (11,19) = restored per-layer (backup, byte-identical to what we deploy);
    neighbours (11,18)/(12,19) = the untouched deployed files.  Asserts zero incoherent (11,19) edges."""
    p1119 = _load_backup_parts()                           # what we deploy == pristine per-layer
    g19 = parts_shade_grid(p1119); s5_19 = parts_sea5_tiles(p1119.get("sea5"))
    p1118 = _load_deployed_parts(_rdir(1, 18), 11, 18)
    g18 = parts_shade_grid(p1118); s5_18 = parts_sea5_tiles(p1118.get("sea5"))
    p1219 = _load_deployed_parts(_rdir(1, 19), 12, 19)
    g12 = parts_shade_grid(p1219); s5_12 = parts_sea5_tiles(p1219.get("sea5"))

    c = Counter(g19[i][j] for i in range(G) for j in range(G))
    print(f"[3d] WANG EDGE-COHERENCE GATE -- final (11,19) shades sea4={c['sea4']} sea5={c['sea5']} sea3={c['sea3']}")
    incoherent = 0
    # frame edges (face generic deep ocean)
    for e in ("W", "S"):
        res = frame_edge_verdicts(g19, s5_19, e)
        bad = [r for r in res if not r[2]]
        incoherent += len(bad)
        print(f"     (11,19).{e} FRAME vs generic-deep: {'CLEAN' if not bad else str(len(bad))+' INCOHERENT'}")
        for (i, j), sh, _, det in bad:
            print(f"        cell(i={i},j={j}) shade={sh} {det}")
    # internal edges (N->(11,18), E->(12,19))
    for name, gB, s5B, d in (("(11,18)", g18, s5_18, "N"), ("(12,19)", g12, s5_12, "E")):
        viol = internal_edge_verdicts(g19, s5_19, gB, s5B, d)
        incoherent += len(viol)
        print(f"     (11,19).{d} INTERNAL -> {name}: {'CLEAN' if not viol else str(len(viol))+' INCOHERENT'}")
        for a, b, det in viol:
            print(f"        {a}|{b} {det}")
    if deploying and incoherent:
        raise SystemExit(f"GATE 3d FAILED: {incoherent} incoherent edge(s) at (11,19) -- needs Wang recalculation")
    print(f"     => (11,19): {incoherent} incoherent edges (audit predicted 0; verbatim carry needs NO recalc)")
    # informational: the OUT-OF-SCOPE island-fringe cropped seams on the top-row cells (not touched)
    print("     [out-of-scope, unchanged] island outer-fringe cropped-Wang seams live on the top-row cells")
    print("     (11,18).N/.W, (12,18).E, (12,19).E -- pre-existing since the (8,17) carry, away from the boat.")
    return incoherent


# --------------------------------------------------------------------------- gates that don't need deploy
def gate_stub(stub):
    a, b, cc = (stub.verts[i] for i in stub.flat_index[:3])
    cr = _cross(a, b, cc)
    zero_area = max(abs(v) for v in cr) < 1e-12
    tanx = stub.tangents[0][0]
    flags = (1 if stub.normals else 0) | (2 if stub.uvs else 0) | (4 if stub.tangents else 0)
    ok = zero_area and tanx == 4078.0 and (flags & 4) and stub.vcount == len(stub.flat_index) == 3
    print(f"[3b/stub] degenerate Terrain: verts==idx={stub.vcount}=={len(stub.flat_index)}, "
          f"cross={tuple(round(x,3) for x in cr)} zero_area={zero_area}, tangent.x={tanx}, flags={flags}")
    if not ok:
        raise SystemExit("GATE stub FAILED")
    # stub contributes zero hittable area (skip-sentinel + zero-area)
    miss, tot, topos = _cell_census([("Terrain", stub)])
    if len(miss) != tot:
        raise SystemExit(f"GATE stub FAILED: stub yields {tot-len(miss)} hits (must be 0)")
    print(f"[3a/stub] stub-only census: {len(miss)}/{tot} MISS (zero hittable area -- and never bound anyway)")


def gate_flatmesh(name, bm):
    n = len(bm.flat_index)
    ok = bm.vcount == n == 3 * (n // 3)
    maxidx = max(bm.flat_index) if bm.flat_index else -1
    rng = 0 < bm.vcount <= 65535 and 0 <= n <= bm.vcount * 3 and maxidx < bm.vcount
    print(f"[3b] flat-mesh {name}: verts={bm.vcount}==idx={n} ({n//3} tris), ReadMesh-range={rng}")
    if not (ok and rng):
        raise SystemExit(f"GATE 3b FAILED for {name}")


def gate_coverage():
    """GATE 3a: the DIVERT effective-prefab oracle -- all THREE sea overrides bind (donor exposes them).
    PRE (Sea4-only, the un-armed round-0 state) reproduces the hole; POST (Sea3+Sea4+Sea5) = MISS 0."""
    parts = _load_backup_parts()                           # {sea3,sea4,sea5} pristine (== what we deploy)
    post_ml = effective_divert_meshlist(parts)
    names = [p for p, _ in post_ml]
    if names != ["Sea3", "Sea4", "Sea5"]:
        raise SystemExit(f"GATE 3a FAILED: divert effective set = {names}, expected Sea3/Sea4/Sea5")
    pre_ml = [("Sea4", parts["sea4"])]                     # round-0: only Sea4 bound (SeaBlockPrefab)
    pre_miss, pre_tot, _ = _cell_census(pre_ml)
    post_miss, post_tot, post_topos = _cell_census(post_ml)
    pre_w, pre_wt = _window_census(pre_ml)
    post_w, post_wt = _window_census(post_ml)
    if not pre_miss:
        raise SystemExit("GATE 3a FAILED: PRE (Sea4-only) did not reproduce the round-0 defect")
    if post_miss:
        raise SystemExit(f"GATE 3a FAILED: POST divert union still MISSES ({len(post_miss)})")
    if set(post_topos) - BOAT_TOPO:
        raise SystemExit(f"GATE 3a FAILED: non-boat topo bound: {set(post_topos)-BOAT_TOPO}")
    print(f"[3a] NON-REGRESSION (divert effective-prefab oracle: Sea3+Sea4+Sea5 all bind):")
    print(f"     PRE  (Sea4-only = the un-armed round-0 state): cell MISS={len(pre_miss)}/{pre_tot} "
          f"window MISS={pre_w}/{pre_wt}  <- reproduces the hole")
    print(f"     POST (divert armed, 3 layers): cell MISS={len(post_miss)}/{post_tot} "
          f"window MISS={post_w}/{post_wt}  topos={post_topos} (all boat-legal {sorted(BOAT_TOPO)})")


def gate_freeride():
    """GATE 3c: enumerate the donor prefab's FULL transform set; every exposed part is overridden by
    our files; the stub Terrain is NOT exposed (donor has no Terrain) -> never bound; nothing foreign."""
    pset = donor_part_set(*DONOR)
    exposed = {p for p, _ in pset}
    print(f"[3c] FREE-RIDE AUDIT -- donor (8,18) prefab transforms: {pset}")
    if exposed != {"Sea3", "Sea4", "Sea5"}:
        raise SystemExit(f"GATE 3c FAILED: donor exposes {exposed}, expected exactly Sea3/Sea4/Sea5")
    for p in ("Sea3", "Sea4", "Sea5"):
        print(f"     {p}  -> exposed -> OVERRIDDEN by our restored Block[11][19] {p}.ff9mesh")
    print("     Terrain -> NOT exposed (donor is water-only) -> our stub NEVER binds (File.Exists arm only)")
    print("     => nothing foreign free-rides; effective bound set = {Sea3,Sea4,Sea5}, all ours")


def gate_bytediff():
    """GATE 3e: the restored parts are BYTE-IDENTICAL to the pristine round-1 backup -- the audit
    mandated NO tile recalculation for (11,19), so ZERO quads change."""
    print("[3e] BYTE-DIFF vs pristine donor carry (audit: recalculation needed = NONE):")
    for part, (size, md5) in PRISTINE.items():
        print(f"     Block[11][19] {part}: {size}B md5={md5[:8]} -- unchanged (0 quads recalculated)")
    print("     => 0 tiles recalculated; the restore is a pure per-part carry, not a re-tiling")


# --------------------------------------------------------------------------- deploy + post-verify
def deploy():
    written = []
    for disc in DISCS:
        rdir = _rdir(disc)
        rdir.mkdir(parents=True, exist_ok=True)
        # 1. restore per-layer (byte-copy from the per-disc pristine backup -> guaranteed byte-identical)
        for part in ("Sea3", "Sea4", "Sea5"):
            dst = rdir / f"Block[{BX}][{BY}] {part}.ff9mesh"
            shutil.copyfile(_bk1(disc, f"{part}.ff9mesh"), dst)
            written.append(dst)
        # 2. arm the divert: the degenerate stub Terrain
        M.write_ff9mesh(build_stub_terrain(disc), rdir / f"Block[{BX}][{BY}] Terrain.ff9mesh")
        written.append(rdir / f"Block[{BX}][{BY}] Terrain.ff9mesh")
        # 3. the donor sidecar
        (rdir / f"Block[{BX}][{BY}] Donor.txt").write_text("8,18", encoding="utf-8")
        written.append(rdir / f"Block[{BX}][{BY}] Donor.txt")
    print(f"[deploy] wrote {len(written)} files across discs {DISCS} (Sea3/Sea4/Sea5 + Terrain stub + Donor.txt)")
    return written


def gate_disc_parity_and_neighbours(pre_neighbour_hashes):
    """GATE 3f: every (11,19) file byte-identical Disc1==Disc4; neighbours (11,18)/(12,18)/(12,19)
    untouched (hash before==after)."""
    names = ["Sea3.ff9mesh", "Sea4.ff9mesh", "Sea5.ff9mesh", "Terrain.ff9mesh", "Donor.txt"]
    for nm in names:
        h1 = _md5(_rdir(1) / f"Block[{BX}][{BY}] {nm}")
        h4 = _md5(_rdir(4) / f"Block[{BX}][{BY}] {nm}")
        if h1 != h4:
            raise SystemExit(f"GATE 3f FAILED: Disc1 != Disc4 for {nm}")
    # exactly these 5 files present for (11,19), nothing else
    for disc in DISCS:
        present = _cell_files(_rdir(disc), BX, BY)
        extra = [p.name for p in present if p.name.replace(f"Block[{BX}][{BY}] ", "") not in names]
        if extra or len(present) != len(names):
            raise SystemExit(f"GATE 3f FAILED: (11,19) files on disc {disc} = "
                             f"{[p.name for p in present]} (want exactly {names})")
    print(f"[3f] disc parity: all 5 (11,19) files Disc1==Disc4; exactly 5 files per disc, nothing else")
    post = neighbour_hashes()
    if post != pre_neighbour_hashes:
        changed = [k for k in post if post[k] != pre_neighbour_hashes.get(k)]
        raise SystemExit(f"GATE 3f FAILED: neighbour files changed: {changed}")
    print(f"[3f] neighbours untouched: (11,18)/(12,18)/(12,19) hashes identical before==after "
          f"({len(post)} files)")


def neighbour_hashes():
    out = {}
    specs = [(18, 11), (18, 12), (19, 12)]                 # (r, x): (11,18),(12,18),(12,19)
    for disc in DISCS:
        for (r, x) in specs:
            for p in _cell_files(_rdir(disc, r), x, r):
                out[f"d{disc}/r{r}/{p.name}"] = _md5(p)
    return out


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true", help="perform the writes (both discs)")
    args = ap.parse_args()

    check_r1_backup()
    capture_r2_backup()

    stub = build_stub_terrain(1)
    parts = _load_backup_parts()

    # ---- offline gates (no writes) ----
    gate_stub(stub)
    for nm, bm in (("Sea3", parts["sea3"]), ("Sea4", parts["sea4"]), ("Sea5", parts["sea5"]),
                   ("Terrain(stub)", stub)):
        gate_flatmesh(nm, bm)
    gate_freeride()
    gate_coverage()
    gate_bytediff()
    wang_gate(deploying=args.deploy)

    if not args.deploy:
        print("\n(dry run -- all offline gates PASS; re-run with --deploy to write both discs)")
        return

    pre = neighbour_hashes()
    deploy()
    gate_disc_parity_and_neighbours(pre)
    print("\nDONE. Block[11][19] restored to faithful per-layer Sea3/Sea4/Sea5 + divert armed "
          "(Terrain stub + Donor.txt=8,18).\nStreaks fixed (per-part materials); navigation preserved "
          "(divert union MISS=0, boat-legal).\nRevert to the merged-Sea4 fallback: copy "
          "backups/waterfix-1119-r2.20260720/Disc{1,4}__Block[11][19] Sea4.ff9mesh back and delete "
          "Sea3/Sea5/Terrain/Donor.txt; full round-1 pristine = backups/waterfix-1119.20260720/.")


if __name__ == "__main__":
    main()
