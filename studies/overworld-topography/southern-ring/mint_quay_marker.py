"""THE LANTERN QUAY MARKER -- author the marker OBJ (and optionally build/deploy it).

WHAT THIS MAKES
    A verbatim copy of stock FF9's own HARBOUR GATE, seated beside the Lantern Quay's world-map
    trigger on the junction island's west shore, so the case-53 entrance is VISIBLE instead of an
    invisible 6-tile trigger cluster on featureless grass.

THE LANE (decided, not re-litigated)
    A baked per-block **Object** mesh -- the stock landmark substrate -- loaded through the s34
    `transform.name`-GENERIC override seam the Southern Ring already requires. NOT the scripted
    3DModel/`.eb` lane; NOT SPS.

THE DONOR -- Alexandria Harbour, `Block[21][10] Object` (disc 1, lod 0_1)
    FF9's literal harbour/quay gate, and the cleanest carry in the 63-block stock Object census:
    the block's ENTIRE Object part IS the one structure, so this exports whole -- no trimming, no
    index slicing.

      104 tris / 312 verts, one submesh (0, 312); every vertex referenced exactly once
      ONE uniform IDALL 6382 (0x18EE = event 0, area 24, topograph 59, flags 2)
      single connected component over 66 shared positions
      LOCAL bbox x[0.000, 6.277] y[0.000, 5.531] z[-43.441, -35.055]  (base at local y 0 = sea level)
      footprint 6.277 x 8.387 u, height 5.531 u
      UV span u[0.00391, 0.12793] v[0.12305, 0.18457], zero degenerate UVs

    Carried VERBATIM: positions + UVs + normals ride through the OBJ, so the copy samples the same
    shared `res(1_24)_objects` atlas. A carry that drops UVs renders flat WHITE off the atlas's
    alpha-0 corner -- that is the failure mode this script's UV gate exists to catch.

    (An earlier pass used `Block[18][13]`'s 9-tri post on a `world/locate.py` area->place join that
    is now PROVEN BROKEN -- the engine packs CELL coords into the world dispatch key, not the IDALL
    (ff9.cs:2233 + w_worldPos2Cell at :5299-5303). Those 9 tris are a FRAGMENT of the South Gate
    complex, which spans (18,13)+(18,14) at 140 tris, so the carry risked reading as a cut fragment.)

PLACEMENT -- ONE instance
    `--at (48, -1157)`, which anchors the mesh's XZ BOUNDING-BOX centre (blendio.py:198-203 -- the
    bbox centre, NOT the vertex centroid) and shifts XZ only (dy = 0). Base pre-translated to world
    y = 3.00, Block[0][18]'s measured plateau. Resulting world span:

      x[44.861, 51.139]  z[-1161.193, -1152.807]  y[3.000, 8.531]

    -1157 is the exact centre of the lawful window: the gate sits fully NORTH of the trigger
    exclusion (z > -1162) with 0.807 u to spare on each side of a 10 u window for an 8.387 u gate,
    2.807 u clear of the nearest real trigger tile (z <= -1164), and 11.174 u from the arrive point.

THE IDALL
    Every triangle is stamped **4078** (0x0FEE = area 15, topograph 59, flags 2) via the `--idall`
    lever, replacing the donor's own 6382. Note both are `flags == 2` and `topograph == 59`, so the
    restamp only moves the area field -- it keeps the donor's structural invariants.

    Why it is load-bearing here, not cosmetic: `WMWorld.LoadBlock` registers `prefab.ObjectForm1`
    BEFORE `prefab.TerrainForm1`, and `RegisterBlockComponent(..., form1: true, ...)` feeds the loose
    Object override to `block.AddWalkMeshForm1` (WMWorld.cs:775-814). Block (0,18) is a reclaimed cell
    whose `Donor.txt` names donor (0,0), and (0,0) HAS a stock Object component -- so this override
    enters the walkmesh AHEAD of Terrain. The ground query is first-mesh/first-tri-wins, so an
    ordinary `--topograph 59` stamp would make the gate SHADOW the quay trigger and the entrance
    would stop firing.

    `WMPhysics.Raycast` (WMPhysics.cs:15-20) skips 4078/4088/2040 outright -> the on-foot walk query
    never sees the gate: walk-through, no shadow. `ff9.w_movementUpdate` (ff9.cs:5160-5164) also keeps
    a NON-controlled actor's own Y on a 4078 hit (remapping the id to 0xFD2) instead of snapping it to
    the gate top, so followers do not climb it.

    Stock precedent (measured, disc 1): Chocobo's Forest ships 100 Object tris of 4078 across
    (16,14)=59, (17,14)=35, (16,15)=3, (17,15)=3. 4078 is the shipping render-only idiom.

    4078 is NOT a blanket exemption. Every sky-cast placement path (`ff9.w_nwpHitBool` callers, e.g.
    ff9.cs:4750, 4849) sets `WMPhysics.IgnoreExceptions = true`, which DEFEATS the skip -- so marker
    geometry under a spawn or an arrive point would still be hit. Hence the hard exclusion: nothing
    within 6 u of the arrive point (60, -1168).

WHY NO `--seat`, NO `--keep-block`, NO `--floor` TRIM
    * `--seat` samples PRISTINE terrain at the target; block (0,18) is a RECLAIMED ocean cell
      (`Donor.txt` = "0,0") with no pristine parts, so it raises. The base is pre-translated to
      y 3.00 instead, and `--at` shifts XZ only.
    * `--keep-block` is a no-op here: the block's live Object file is a 176-byte blanking stub (a
      down-facing tri at y -80 suppressing reclaim-donor (0,0)'s 5 object tris). This build REPLACES
      it, which is correct -- the donor's tris stay overridden either way.
    * `world-mesh-trim --floor` drops LOW UP-FACING faces (a building's dirt apron). This gate is
      only 5.531 u tall, so at the default `base_height=6.0` the trim would drop EVERY one of its 34
      up-facing faces -- it would gut the structure. Skipped.

STANDING TRAP
    `world/island.py` (`HIDDEN_PARTS` at :53, deployed at :955-957 and :966-969) unconditionally
    re-deploys that 176-byte Object blanking stub. Any future re-run of the island mint over block
    (0,18) WIPES this marker -- re-run this script afterwards.

USAGE
    py studies/overworld-topography/southern-ring/mint_quay_marker.py            # write the OBJ + run the gates
    py studies/overworld-topography/southern-ring/mint_quay_marker.py --build    # ... then build + deploy

    The build is equivalent to:
      py -m ff9mapkit world-mesh-build <quay_marker.obj> --into-block 0 18 --part object \
         --idall 4078 --at 48 -1157 --mod-folder FF9CustomMap-world
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.world import extract as W                      # noqa: E402
from ff9mapkit.world import blendio as BIO                    # noqa: E402

# ---- the decided design, as constants -------------------------------------------------------------
DONOR_BLOCK = (21, 10)          # Alexandria Harbour -- FF9's own harbour/quay gate
DONOR_TRIS, DONOR_VERTS = 104, 312
TARGET_BLOCK = (0, 18)          # the Lantern Quay's cell (reclaimed, Donor.txt "0,0")
ANCHOR = (48.0, -1157.0)        # --at: the XZ BBOX CENTRE lands here; centre of the lawful window
BASE_Y = 3.00                   # Block[0][18]'s measured plateau
MARKER_IDALL = 4078             # 0x0FEE -- the engine's render-only skip id

TRIGGER_BBOX = (44.0, 52.0, -1172.0, -1164.0)     # x0,x1,z0,z1 of the 6 idall-16384 tris
EXCLUSION = (42.0, 54.0, -1174.0, -1162.0)        # the trigger bbox + a 2u keep-out margin
ARRIVE_POINT = (60.0, -1168.0)                    # the berth-exit arrive point (a sky-cast IGNORES 4078)
ARRIVE_CLEARANCE = 6.0

OBJ_OUT = HERE / "quay_marker.obj"


def build_marker_obj() -> dict:
    """Read the donor gate and return a parsed-OBJ dict placed at its final WORLD coords."""
    bm = W.read_block(*DONOR_BLOCK, disc=1, lod="0_1", part="object")
    ox, oz = W.block_world_origin(*DONOR_BLOCK)
    verts = [(v[0] + ox, v[1], v[2] + oz) for v in bm.verts]          # donor block-LOCAL -> WORLD
    xs = [v[0] for v in verts]
    zs = [v[2] for v in verts]
    cx, cz = (min(xs) + max(xs)) / 2.0, (min(zs) + max(zs)) / 2.0     # bbox centre == what --at anchors
    dx, dz = ANCHOR[0] - cx, ANCHOR[1] - cz
    dy = BASE_Y - min(v[1] for v in verts)                            # lowest point -> the plateau

    V = [(v[0] + dx, v[1] + dy, v[2] + dz) for v in verts]
    VT = [tuple(u) for u in bm.uvs]
    VN = [tuple(n) for n in bm.normals]
    # bm.tris index the vertex pool directly (== bm.flat_index triples), and the index buffer is
    # REORDERED for draw order -- carry it verbatim rather than re-sorting.
    faces = [tuple((i + 1, i + 1, i + 1) for i in tri) for tri in bm.tris]
    return {"V": V, "VT": VT, "VN": VN, "faces": faces, "donor": bm}


def _face_nys(V, faces):
    return sorted(round(BIO._face_normal_y_and_cy(V, f)[0], 4) for f in faces)


def gates(obj: dict) -> int:
    """Offline gates. Returns the number of FAILURES (0 = clear)."""
    V, VT, faces, d = obj["V"], obj["VT"], obj["faces"], obj["donor"]
    bad = 0

    def check(ok: bool, label: str, detail: str = "") -> None:
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}{('  -- ' + detail) if detail else ''}")

    print("\n=== GATES ===")
    xs = [v[0] for v in V]; ys = [v[1] for v in V]; zs = [v[2] for v in V]
    print(f"  world span: x[{min(xs):.3f},{max(xs):.3f}] y[{min(ys):.3f},{max(ys):.3f}] "
          f"z[{min(zs):.3f},{max(zs):.3f}]   verts={len(V)} tris={len(faces)}")

    check(len(faces) == DONOR_TRIS and len(V) == DONOR_VERTS,
          f"the WHOLE donor part carried ({DONOR_TRIS} tris / {DONOR_VERTS} verts)",
          f"got {len(faces)} / {len(V)}")
    check(abs((min(xs) + max(xs)) / 2.0 - ANCHOR[0]) < 1e-6 and abs((min(zs) + max(zs)) / 2.0 - ANCHOR[1]) < 1e-6,
          f"XZ bbox centre == the anchor {ANCHOR} (so `--at` is an identity shift)")
    check(abs(min(ys) - BASE_Y) < 1e-6, f"base sits at y {BASE_Y}", f"got {min(ys):.4f}")

    # in-block: block-local verts must stay inside the 64x64 footprint
    tox, toz = W.block_world_origin(*TARGET_BLOCK)
    inblock = tox <= min(xs) and max(xs) <= tox + 64 and toz - 64 <= min(zs) and max(zs) <= toz
    check(inblock, f"whole mesh inside block{list(TARGET_BLOCK)}'s footprint x[{tox},{tox + 64}] z[{toz - 64},{toz}]",
          f"edge margins  N {toz - max(zs):.3f}u  S {min(zs) - (toz - 64):.3f}u  "
          f"W {min(xs) - tox:.3f}u  E {tox + 64 - max(xs):.3f}u")

    # UV carry -- the failure mode that renders flat white
    check(len(VT) == len(V), "one UV per vertex")
    check(all(any(abs(c) > 1e-6 for c in u) for u in VT), "no degenerate [0,0] UV (would render white)")
    check(sorted({round(u[0], 6) for u in VT}) == sorted({round(u[0], 6) for u in d.uvs})
          and sorted({round(u[1], 6) for u in VT}) == sorted({round(u[1], 6) for u in d.uvs}),
          "U and V sets match the donor's exactly (verbatim carry)")
    us = [u[0] for u in VT]; vs = [u[1] for u in VT]
    print(f"         UV range u[{min(us):.5f},{max(us):.5f}] v[{min(vs):.5f},{max(vs):.5f}]")

    # geometry fidelity: the per-face normal-Y distribution must be the donor's (a pure translation)
    dny = _face_nys([tuple(v) for v in d.verts], [tuple((i + 1, i + 1, i + 1) for i in t) for t in d.tris])
    check(_face_nys(V, faces) == dny, "per-face normal-Y distribution == the donor's (pure translation)",
          f"up={sum(1 for n in dny if n > 0.5)} vertical={sum(1 for n in dny if abs(n) <= 0.5)} "
          f"down={sum(1 for n in dny if n < -0.5)}")

    # exclusion 1 (HARD): the arrive point -- a sky-cast ignores the 4078 skip
    dmin = min(math.dist((v[0], v[2]), ARRIVE_POINT) for v in V)
    check(dmin >= ARRIVE_CLEARANCE,
          f"EXCLUSION 1: every vertex >= {ARRIVE_CLEARANCE}u from the arrive point {ARRIVE_POINT}",
          f"nearest {dmin:.3f}u")

    # exclusion 2: the trigger bbox + 2u margin
    x0, x1, z0, z1 = EXCLUSION
    inside = [v for v in V if x0 <= v[0] <= x1 and z0 <= v[2] <= z1]
    check(not inside, f"EXCLUSION 2: no vertex inside the keep-out rect x[{x0},{x1}] z[{z0},{z1}]",
          f"{len(inside)} inside" if inside else
          f"nearest real trigger tile is {min(zs) - TRIGGER_BBOX[3]:.3f}u away")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true", help="also build + deploy the override (writes the install)")
    ap.add_argument("--mod-folder", default="FF9CustomMap-world")
    args = ap.parse_args()

    obj = build_marker_obj()
    d = obj["donor"]
    print(f"donor Block{list(DONOR_BLOCK)} Object: {d.vcount} verts, {len(d.tris)} tris, submeshes={d.submeshes}, "
          f"idall={sorted({int(round(d.tangents[d.flat_index[3 * t]][0])) for t in range(len(d.tris))})}")
    if gates(obj):
        print("\nGATES FAILED -- nothing written.", file=sys.stderr)
        return 1
    BIO.write_obj(obj, OBJ_OUT)
    print(f"\nwrote {OBJ_OUT}")

    if not args.build:
        print("\nnot built (pass --build). The equivalent CLI:\n"
              f"  py -m ff9mapkit world-mesh-build {OBJ_OUT.name} --into-block {TARGET_BLOCK[0]} {TARGET_BLOCK[1]} "
              f"--part object --idall {MARKER_IDALL} --at {ANCHOR[0]:.0f} {ANCHOR[1]:.0f} "
              f"--mod-folder {args.mod_folder}")
        return 0

    info = BIO.build_from_obj(str(OBJ_OUT), into_block=TARGET_BLOCK, mod_folder=args.mod_folder, part="object",
                              idall=MARKER_IDALL, at=ANCHOR)
    print(f"\ndeployed -> {info['dest']}")
    print(f"  {info['verts']} verts, {info['tris']} tris, idall {info['idall']} (0x{info['idall']:04X}); "
          f"replaced {info['replaced_stock_tris']} stub tri(s); Disc4 auto-mirrored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
