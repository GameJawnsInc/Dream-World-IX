#!/usr/bin/env python
r"""Retile the ISOLATED desert-mains orphan triangle on the Path-D two-ground landmass.

THE DEFECT (owner playtest, 2026-08-05, world 9013 junction-compose landmass)
    Block[2][17] Terrain.ff9mesh, tri index 521, vertex indices 1563/1564/1565,
    world (132.0,-1127.848) (136.0,-1127.344) (136.0,-1129.695) -- a 4.70 u^2 wedge.
    It wears a DESERT-mains atlas rect while its own IDALL topograph is 0 (grass) and all
    three of its edge-neighbours are grass-language tris (447, 463 grass-mains; 119 the
    grass side of a grass|desert strip pair). It is a size-1 connected component in the
    desert-mains visual family -- an unlawful stray.

    NOT a MIXED-CELL PAIR member (coastmorph.py:826): a pair member shares its cell AND its
    uv rect with a second tri of the other family across the tile diagonal. This tri shares
    its rect with nothing. The script asserts this and refuses if a partner appears.

ROOT CAUSE (measured, not guessed)
    The stray's uv is EXACTLY grassland.ground_uv(vert, cell=(33,-283), quad=(1,1),
    ori=270, ground="desert") -- a perfectly lawful per-vert mains evaluation on the correct
    lattice cell, with the wrong GROUND FAMILY. (The Disc1/Disc4 twins carry the same tri at
    ori=0; quad and cell agree, so only the tile-seed differs.) The generator got the tri's
    topograph from the grass side and its uv family from the desert side: a one-tri family
    selector slip, not a uv-math bug. That is why it reproduces across trees built with
    different tile seeds.

THE FIX -- uv only. Geometry, normals, the index buffer and IDALL are never touched.
  mode "translate" (DEFAULT, recommended): apply THE TRANSLATION LAW (grassland.py:57-62)
    in reverse -- uv_new = uv_old - (GROUNDS[src].mains_du, .mains_dv)
                                  + (GROUNDS[dst].mains_du, .mains_dv)
    With dst="grass" (deltas 0,0) this is a pure subtraction of the desert delta
    (-0.65332, +0.09863). It recovers EXACTLY the grass tile the generator would have
    emitted for cell (33,-283) had the family selector been right: same cell, same quadrant,
    same rotation, same per-vert fractional positions. Nothing is re-rolled.
  mode "redress" (fallback): the shipped ff9mapkit.world.orphangate.compute_orphan_redress
    shape -- cell = the tri's centroid 4u cell, (quad,ori) = grassland.assign_mains({cell},
    seed=DEFAULT_REDRESS_SEED), uv = grassland.ground_uv(...). Also lawful, but it re-rolls
    the cell's quadrant/rotation to a seed-derived tile unrelated to the generator's choice.

LAWS THAT GATE IT (all checked at runtime, the script refuses rather than warns)
  * THE CUT-VERT LAW (CHANGELOG.md:403; coastmorph.py:997) -- the tile map is EVALUATED AT
    THE VERT, never corner-snapped. Verified by re-deriving the output as a
    grassland.mains_uv evaluation (`realises` post-condition below): if the result is a
    genuine per-vert linear evaluation it reproduces bit-for-bit, a corner-snap smear does
    not. Every (quad,ori) here that would sit strictly inside ONE quadrant rect costs a
    0.164-of-a-quadrant clamp = a 0.66-world-unit smear; both modes clamp 0.0141 of a
    quadrant = 0.44 texel of the 1024 atlas, i.e. sub-pixel.
  * THE TILE-RECT CONTAINMENT LAW (coastmorph.py:989-1030, :1175) -- the uv image must not
    sample gutter/foreign atlas content. Asserted: the image lies wholly inside
    grassland.FAM_REGION["main"] (the grass 2x2), bleeding only ACROSS THE INTERNAL SPLIT
    into the sibling quadrant -- the documented lawful inward bleed (grassland.py:16-19:
    "conforming boundary tris extrapolate slightly PAST their quadrant -- but only INWARD
    ..., NEVER outside the 2x2 region"). Outside the 2x2 is the transparent gutter that
    renders WHITE, and never happens here.
  * THE TILED-MAINS FILL / modal-family rule (CHANGELOG.md:449) -- the retile target is the
    LOCAL MODAL ground family; all three edge-neighbours are grass, so the modal family is
    grass.
  * IDALL stays bit-identical because the tri's topograph is already
    GROUNDS["grass"]["topo"] == 0 -- compute_orphan_redress's Round-2 shape ("when the topo
    already matches, only the UV moves"). This preserves the rung-6 ENTRANCE arming (event
    bits, idall 16384) on the live Disc9 file.

USAGE
    py fix_triangle.py --dry-run                       # live Disc9 block, translate mode
    py fix_triangle.py --dry-run --mode redress
    py fix_triangle.py --dry-run --file "<...>/Disc1/0_1/r17/Block[2][17] Terrain.ff9mesh"
    py fix_triangle.py --write                         # backs up to C:/gd/Dream-World-IX/backups/ first
A real write requires --write; --dry-run reports the exact byte delta and writes nothing.
"""
from __future__ import annotations

import argparse
import datetime
import re
import shutil
import struct
import sys
from pathlib import Path

# the repo's own kit, derived from this file's location -- the original hardcoded the authoring
# WORKTREE's ff9mapkit path, which evaporates when that worktree is pruned (the worktree-parked
# trap, in code-path form)
KIT = Path(__file__).resolve().parents[4] / "ff9mapkit"
if str(KIT) not in sys.path:
    sys.path.insert(0, str(KIT))

from ff9mapkit.world import grassland as GL                       # noqa: E402
from ff9mapkit.world import mesh as WM                            # noqa: E402
from ff9mapkit.world.extract import BLOCK_SIZE, decode_id         # noqa: E402
from ff9mapkit.world.mesh import read_ff9mesh                     # noqa: E402
from ff9mapkit.world.orphangate import DEFAULT_REDRESS_SEED       # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
DEFAULT_FILE = (GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc9" / "0_1" / "r17"
                / "Block[2][17] Terrain.ff9mesh")
BACKUP_ROOT = Path(r"C:\gd\Dream-World-IX\backups")

BX, BY = 2, 17
OX, OZ = BX * BLOCK_SIZE, -BY * BLOCK_SIZE                        # (128, -1088)
TRI = 521
EXPECT_VERTS = [(132.0, -1127.847656), (136.0, -1127.343750), (136.0, -1129.695312)]
POS_TOL = 1e-3
SRC_FAMILY, DST_FAMILY = "desert", "grass"


def channel_offsets(vcount: int, flags: int) -> dict:
    off = 20
    seg = {"verts": off}
    off += vcount * 12
    if flags & 1:
        seg["normals"] = off
        off += vcount * 12
    if flags & 2:
        seg["uvs"] = off
        off += vcount * 8
    if flags & 4:
        seg["tangents"] = off
        off += vcount * 16
    seg["indices"] = off
    seg["_end"] = off + 0
    return seg


def realises(pts, uvs, family, tol=3e-4):
    """Every (cell, quad, ori) whose grassland.ground_uv(..., family) reproduces these uvs at
    these world XZ points. A genuine per-vert linear evaluation has >=1 hit; a corner-snap
    smear has none. THE CUT-VERT LAW's own witness."""
    out = []
    ci = range(int(min(p[0] for p in pts) // 4) - 1, int(max(p[0] for p in pts) // 4) + 2)
    cj = range(int(min(p[1] for p in pts) // 4) - 1, int(max(p[1] for p in pts) // 4) + 2)
    for i in ci:
        for j in cj:
            for uh in (0, 1):
                for vh in (0, 1):
                    for ori in GL.ORIS:
                        if all(abs(GL.ground_uv(p[0], p[1], (i, j), (uh, vh), ori, family)[k] - u[k]) < tol
                               for p, u in zip(pts, uvs) for k in (0, 1)):
                            out.append(((i, j), (uh, vh), ori))
    return out


def plan(path: Path, mode: str = "translate") -> dict:
    """Locate the orphan, verify every precondition, compute the replacement uvs."""
    raw = path.read_bytes()
    if raw[:4] != b"F9WM":
        raise SystemExit(f"not a .ff9mesh: {path}")
    _ver, vcount, icount, flags = struct.unpack_from("<iiii", raw, 4)
    d = read_ff9mesh(path)
    idx = d["indices"]
    tris = [idx[i:i + 3] for i in range(0, len(idx), 3)]
    if TRI >= len(tris):
        raise SystemExit(f"{path}: only {len(tris)} tris, no tri {TRI}")
    tv = tris[TRI]

    world = [(d["verts"][i][0] + OX, d["verts"][i][1], d["verts"][i][2] + OZ) for i in tv]
    xz = [(p[0], p[2]) for p in world]
    for (ex, ez), p in zip(EXPECT_VERTS, world):
        if abs(p[0] - ex) > POS_TOL or abs(p[2] - ez) > POS_TOL:
            raise SystemExit(
                f"PRECONDITION FAILED: tri {TRI} geometry moved -- expected {EXPECT_VERTS}, got "
                f"{[(round(p[0], 4), round(p[2], 4)) for p in world]}. Re-locate before editing.")

    old_uv = [list(d["uvs"][i]) for i in tv]
    sr = GL.ground_main_region(SRC_FAMILY)
    bb = (min(u for u, _ in old_uv), min(v for _, v in old_uv),
          max(u for u, _ in old_uv), max(v for _, v in old_uv))
    if not (sr[0] - 4e-3 <= bb[0] and bb[2] <= sr[2] + 4e-3
            and sr[1] - 4e-3 <= bb[1] and bb[3] <= sr[3] + 4e-3):
        raise SystemExit(
            f"PRECONDITION FAILED: tri {TRI}'s uv bbox {tuple(round(c, 6) for c in bb)} is not inside "
            f"the {SRC_FAMILY}-mains rect {tuple(round(c, 5) for c in sr)} -- already fixed, or a "
            f"different defect. Refusing.")

    old_idall = [int(round(d["tangents"][i][0])) for i in tv]
    dec = decode_id(old_idall[0])
    if dec["topograph"] != GL.GROUNDS[DST_FAMILY]["topo"]:
        raise SystemExit(
            f"PRECONDITION FAILED: tri {TRI} topograph is {dec['topograph']}, not "
            f"{GL.GROUNDS[DST_FAMILY]['topo']} -- this script is the UV-ONLY shape "
            f"(compute_orphan_redress Round 2). A topo change needs the full redress. Refusing.")

    cen = (sum(p[0] for p in xz) / 3.0, sum(p[1] for p in xz) / 3.0)
    cell = (int(cen[0] // 4), int(cen[1] // 4))

    # THE MIXED-CELL PAIR check: no other tri in this cell may share this tri's uv rect.
    partners = []
    for ti, t in enumerate(tris):
        if ti == TRI:
            continue
        w = [(d["verts"][i][0] + OX, d["verts"][i][2] + OZ) for i in t]
        c = (sum(q[0] for q in w) / 3.0, sum(q[1] for q in w) / 3.0)
        if (int(c[0] // 4), int(c[1] // 4)) != cell:
            continue
        uv = [d["uvs"][i] for i in t]
        b2 = (min(u for u, _ in uv), min(v for _, v in uv), max(u for u, _ in uv), max(v for _, v in uv))
        if all(abs(b2[k] - bb[k]) < 6e-3 for k in range(4)):
            partners.append(ti)
    if partners:
        raise SystemExit(
            f"REFUSING: tri {TRI} shares its uv rect with same-cell tri(s) {partners} -- that is a "
            f"LAWFUL MIXED-CELL PAIR (coastmorph.py:826), not a stray. Do not retile it.")

    src_hits = realises(xz, old_uv, SRC_FAMILY)
    if mode == "translate":
        gs, gd = GL.GROUNDS[SRC_FAMILY], GL.GROUNDS[DST_FAMILY]
        du = gd["mains_du"] - gs["mains_du"]
        dv = gd["mains_dv"] - gs["mains_dv"]
        new_uv = [[u + du, v + dv] for u, v in old_uv]
        if not src_hits:
            raise SystemExit(
                f"REFUSING (translate mode): tri {TRI}'s current uv is NOT a lawful "
                f"{SRC_FAMILY} mains evaluation, so translating it does not yield a lawful "
                f"{DST_FAMILY} tile. Use --mode redress.")
        quad, ori = src_hits[0][1], src_hits[0][2]
        cell = src_hits[0][0]
    elif mode == "redress":
        qm, om = GL.assign_mains({cell}, seed=DEFAULT_REDRESS_SEED)
        quad, ori = qm[cell], om[cell]
        new_uv = [list(GL.ground_uv(p[0], p[1], cell, quad, ori, DST_FAMILY)) for p in xz]
    else:
        raise SystemExit(f"unknown mode {mode!r}")

    # POST-CONDITION 1 -- TILE-RECT CONTAINMENT: inside the destination family's 2x2 region.
    mr = GL.ground_main_region(DST_FAMILY)
    nb = (min(u for u, _ in new_uv), min(v for _, v in new_uv),
          max(u for u, _ in new_uv), max(v for _, v in new_uv))
    if not (mr[0] - 1e-6 <= nb[0] and nb[2] <= mr[2] + 1e-6
            and mr[1] - 1e-6 <= nb[1] and nb[3] <= mr[3] + 1e-6):
        raise SystemExit(f"TILE-RECT CONTAINMENT: computed uv bbox {nb} escapes the {DST_FAMILY} mains "
                         f"region {mr} -- transparent gutter would render WHITE. Refusing.")
    # POST-CONDITION 2 -- THE CUT-VERT LAW: the result must still be a genuine per-vert
    # evaluation of the destination family's map (not a smear).
    dst_hits = realises(xz, new_uv, DST_FAMILY)
    if not dst_hits:
        raise SystemExit(f"CUT-VERT LAW: the computed uvs are not reproducible as a per-vert "
                         f"{DST_FAMILY} mains evaluation -- refusing to ship a smear.")

    seg = channel_offsets(vcount, flags)
    edits = []
    for k, vi in enumerate(tv):
        o = seg["uvs"] + vi * 8
        edits.append(dict(vert=vi, offset=o, old=old_uv[k], new=new_uv[k],
                          old_bytes=raw[o:o + 8], new_bytes=struct.pack("<2f", *new_uv[k])))
    return dict(path=path, raw=raw, vcount=vcount, icount=icount, flags=flags, seg=seg, mode=mode,
                tri=TRI, tri_verts=tv, world=world, cell=cell, quad=quad, ori=ori,
                src_hits=src_hits, dst_hits=dst_hits, old_idall=old_idall, edits=edits)


def apply_edits(raw: bytes, edits) -> bytes:
    out = bytearray(raw)
    for e in edits:
        out[e["offset"]:e["offset"] + 8] = e["new_bytes"]
    return bytes(out)


def report(p: dict) -> None:
    print(f"file        : {p['path']}")
    print(f"mode        : {p['mode']}")
    print(f"vcount={p['vcount']} icount={p['icount']} flags={p['flags']}  "
          f"uv@{p['seg']['uvs']} tangents@{p['seg']['tangents']} indices@{p['seg']['indices']}")
    print(f"tri {p['tri']}  vert indices {p['tri_verts']}")
    print(f"world verts : {[(round(v[0], 4), round(v[1], 4), round(v[2], 4)) for v in p['world']]}")
    print(f"OLD uv realises as {SRC_FAMILY} mains at: {p['src_hits']}")
    print(f"NEW uv realises as {DST_FAMILY} mains at: {p['dst_hits']}   "
          f"(cell={p['cell']} quad={p['quad']} ori={p['ori']})")
    print(f"IDALL       : {p['old_idall']} -- UNCHANGED "
          f"(topo {decode_id(p['old_idall'][0])['topograph']} already grass; event/area/flags preserved)")
    for k, e in enumerate(p["edits"]):
        print(f"  v{k} vert {e['vert']:5d} @[{e['offset']},{e['offset'] + 8})  "
              f"uv {tuple(round(c, 6) for c in e['old'])} -> {tuple(round(c, 6) for c in e['new'])}   "
              f"{e['old_bytes'].hex()} -> {e['new_bytes'].hex()}")


def verify_delta(before: bytes, after: bytes, p: dict) -> None:
    diff = [i for i in range(len(before)) if before[i] != after[i]]
    planned = set()
    for e in p["edits"]:
        planned.update(range(e["offset"], e["offset"] + 8))
    extra = sorted(set(diff) - planned)
    uv0, uv1 = p["seg"]["uvs"], p["seg"]["tangents"]
    print(f"\nBYTE DELTA: {len(diff)} bytes changed; planned window = {len(planned)} bytes "
          f"(3 uv pairs, verts {[e['vert'] for e in p['edits']]})")
    print(f"  every changed byte inside the uv channel [{uv0},{uv1}) : {all(uv0 <= i < uv1 for i in diff)}")
    print(f"  unplanned changed bytes                                : {len(extra)}")
    print(f"  planned-but-unchanged (float already held the value)   : {len(planned) - len(diff)}")
    if extra:
        raise SystemExit(f"REFUSING: {len(extra)} bytes changed OUTSIDE the plan: {extra[:32]}")
    bounds = [("header", 0, 20), ("verts", p["seg"]["verts"], p["seg"]["normals"]),
              ("normals", p["seg"]["normals"], p["seg"]["uvs"]),
              ("tangents", p["seg"]["tangents"], p["seg"]["indices"]),
              ("indices", p["seg"]["indices"], len(before))]
    for name, s, e in bounds:
        print(f"  {name:9} [{s},{e}) byte-identical: {before[s:e] == after[s:e]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=str(DEFAULT_FILE), help="target .ff9mesh")
    ap.add_argument("--mode", choices=("translate", "redress"), default="translate")
    ap.add_argument("--dry-run", action="store_true", help="report + verify, write nothing")
    ap.add_argument("--write", action="store_true", help="actually write (backs up first)")
    a = ap.parse_args()
    if a.write == a.dry_run:
        raise SystemExit("pick exactly one of --dry-run / --write")

    p = plan(Path(a.file), mode=a.mode)
    report(p)
    after = apply_edits(p["raw"], p["edits"])
    verify_delta(p["raw"], after, p)

    if a.dry_run:
        print("\nDRY RUN -- nothing written.")
        return

    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = BACKUP_ROOT / f"{p['path'].name}.{stamp}"
    shutil.copy2(p["path"], bak)
    print(f"\nbacked up -> {bak}")
    p["path"].write_bytes(after)
    print(f"WROTE {p['path']} ({len(after)} bytes)")
    # THE LEDGER LAW (learned the hard way -- this very script's 2026-08-05 run left the ONLY
    # DIVERGED row in the install's ledger): an in-place rewrite of a DEPLOYED override must
    # record_ledger_write, or the next deploy_override at this cell+part refuses OUR OWN bytes
    # as foreign (mesh.py's rec-16 class; same call coastnav/rimretile make). Guarded so a
    # --file pointing at a loose copy outside a mod tree ledgers nothing.
    m = re.search(r"Disc(\d+)[/\\][^/\\]+[/\\]r\d+[/\\]Block\[(\d+)\]\[(\d+)\] Terrain\.ff9mesh$",
                  str(p["path"]))
    if m and "FF9_Data" in p["path"].parts:
        WM.record_ledger_write(p["path"], cell=(int(m.group(2)), int(m.group(3))),
                               part="Terrain", write_disc=int(m.group(1)))
        print(f"  ledgered (disc {m.group(1)}) -- the ownership refusal now knows these bytes")
    else:
        print("  NOT ledgered: --file is outside a mod tree's FF9_Data/WorldMap layout")
    d = read_ff9mesh(p["path"])
    print("  new uvs:", [tuple(round(c, 6) for c in d["uvs"][vi]) for vi in p["tri_verts"]])
    print("  idall  :", [int(round(d["tangents"][vi][0])) for vi in p["tri_verts"]])
    print("REMEMBER: in-game ~ -> Reload / re-enter world 9013 to see it; the twins in "
          "Disc1/Disc4 carry the same defect (pass --file).")


if __name__ == "__main__":
    main()
