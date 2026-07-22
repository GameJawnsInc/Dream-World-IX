"""THE LAST-UNSTUDIED-MESH-PARTS CENSUS -- Beach2, Sea6, the sole Sea4f, and block 219.

Roadmap 5.25 (`AUDIT-AND-ROADMAP-2026-07-18.md`). The coast/interior arc decoded Beach1
(the foam swash ribbon) and the Sea1-5 shade ladder; four worldmap sub-mesh forms were never
measured. This closes them with numbers and states, for EACH, the kit-impact verdict.

METHOD (all offline, reads your own install; ~1 min):
  1. PART UNIVERSE  -- every worldmap sub-mesh part name + which blocks bear beach2/sea6/sea4f,
                       both discs (the bundle container keys are the ground truth).
  2. BEACH2         -- geometry + UV atlas band + underlying terrain topo, vs Beach1; is it a
                       second beach ON a block, or a distinct regional shore?
  3. SEA6           -- geometry + atlas band vs the Sea1-5 ladder; a depth rung or an orthogonal
                       special tile?
  4. SEA4f          -- what the "f" is (the generic seamless-ocean fill mesh) and why exactly one.
  5. BLOCK 219      -- grid identity + the early-return scan order's override reachability.
  6. KIT IMPACT     -- programmatically confirm which kit carry/gate lists OMIT beach2/sea6, so a
                       donor bearing them slips the blind spot; confirm the disc-4 mirror is
                       part-agnostic (unaffected).

ENGINE PROVENANCE (file:line, C:/gd/FFIX/Memoria):
  * WMBlockPrefab.cs:14-36  -- the prefab slots: Beach1/Beach2, Sea1..Sea6, Sea3_2/4_2/5_2.
  * WMWorldPrefabMaker.cs:38-167 -- how each named sub-mesh binds a slot; the empty-block sea
    fallback borrows Block[12][0] Terrain+Sea4+Sea6 (152-156); the (j==3,i==9) form-2 special (159-166).
  * WMWorld.cs:569-604      -- block 219's early-return: Object/Terrain(f1+f2) + WaterShrine effect
    + Sea3/4/5(f1) + Sea3_2/4_2/5_2(f2), then `return` -- ALL other parts skipped.
  * WMWorld.cs:711-720      -- Beach1 then Beach2 registered form1+form2 (HasBeach2).
  * WMWorld.cs:766-770      -- Sea6 registered LAST, form1+form2 (HasSea).
  * WMWorld.cs:1161-1163    -- the runtime SeaBlockPrefab = the baked prefab `Block[12][0]f`.
  * WMRenderTextureBank.cs:34-63 -- the atlas texture bands (below), all animated.

ATLAS BANDS (WMRenderTextureBank.cs, "row_uoff_voff", frame count):
  Beach1 11_0_128 (4f) | Beach2 11_128_128 (4f -- own material, own art)
  Sea1 10_64_0 | Sea2 10_128_0 | Sea3 10_128_64 | Sea4 10_128_128 | Sea5 11_64_0 (all 6f)
  Sea6 11_192_64 (4f -- own material, distinct band, NOT a ladder rung)

RESULT (disc 1+4, 2026-07-22): see the printed verdicts. Headline: Beach2 = a DISTINCT regional
shore (4 blocks, own atlas, its blocks have NO Beach1 -- an alternative, not a second beach);
Sea6 = a single 4x4 2-tri decorative open-ocean tile (own 4-frame atlas, orthogonal to the ladder);
Sea4f = the 512-tri full-cell seamless ocean fill the generic SeaBlockPrefab renders; block 219 =
grid (3,9), the Water Shrine, the ONLY block with the Sea*_2 water-level form-switch. KIT IMPACT:
`transplant.PARTS` and `GroundRetile.for_donor` omit BOTH beach2 and sea6 -> a ROTATED/SHIFTED
`world-transplant` of one of the 8 bearing blocks leaves that part free-riding UNROTATED underneath
(beach2 = a visible floating shore; sea6 = a negligible fleck). Low reach (none are qualified
donors; the default beach_only donor scan excludes the beach2 blocks -- they have no beach1), but a
real latent blind spot worth a one-line fix. Sea4f + block 219 = decode-only; the disc-4 mirror is
part-agnostic (unaffected).

Run from the repo root:  py studies/overworld-topography/mesh_parts_census.py
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X          # noqa: E402
from ff9mapkit.world import transplant as TP      # noqa: E402


def _part_blocks(disc, lod="0_1"):
    """{(part): sorted [(x,y)]} for every worldmap block sub-mesh on `disc` at `lod`."""
    env = X._worldmap_env(disc)
    pat = re.compile(rf"worldmap/disc{disc}/{lod}/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9]+)(?:\.asset)?$")
    per = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            per[m.group(3)].add((int(m.group(1)), int(m.group(2))))
    return {p: sorted(bs) for p, bs in per.items()}


def _stats(bx, by, part, disc=1):
    try:
        bm = X.read_block(bx, by, disc=disc, part=part)
    except Exception:
        return None
    V, U = bm.verts, bm.uvs
    ys = [v[1] for v in V]
    us = [u[0] for u in U] if U else [0.0]
    vs = [u[1] for u in U] if U else [0.0]
    return dict(v=bm.vcount, tri=len(bm.tris), ymin=min(ys), ymax=max(ys),
                umin=min(us), umax=max(us), vmin=min(vs), vmax=max(vs))


def _fmt(s):
    return (f"v={s['v']:>4} tri={s['tri']:>4} y[{s['ymin']:+.2f},{s['ymax']:+.2f}] "
            f"u[{s['umin']:.4f},{s['umax']:.4f}] v[{s['vmin']:.4f},{s['vmax']:.4f}]") if s else "ABSENT"


# ---- 1. PART UNIVERSE ----------------------------------------------------------------------------
print("1. PART UNIVERSE (distinct worldmap sub-mesh names per disc, 0_1 LOD):")
D1 = _part_blocks(1)
D4 = _part_blocks(4)
for disc, per in ((1, D1), (4, D4)):
    counts = {p: len(b) for p, b in sorted(per.items(), key=lambda kv: -len(kv[1]))}
    print(f"   disc{disc}: {counts}")
BEACH2 = D1["beach2"]
SEA6 = D1["sea6"]
SEA4F = D1["sea4f"]
print(f"\n   beach2 blocks: {BEACH2}")
print(f"   sea6   blocks: {SEA6}")
print(f"   sea4f  blocks: {SEA4F}   (the sole one)")
assert D1["beach2"] == D4["beach2"] and D1["sea6"] == D4["sea6"] and D1["sea4f"] == D4["sea4f"], \
    "disc1/disc4 part maps diverge for the studied forms"
print("   -> disc1 == disc4 for all three forms (identical asset trees).")

# ---- 2. BEACH2 -----------------------------------------------------------------------------------
print("\n2. BEACH2 (atlas 11_128_128, own Beach2Material -- WMRenderTextureBank.cs:37-39):")
print(f"   reference Beach1 (18,15): {_fmt(_stats(18, 15, 'beach1'))}   uv-band v~[0.02,0.47] (atlas row 11 u0)")
for (bx, by) in BEACH2:
    b1 = _stats(bx, by, "beach1")
    b2 = _stats(bx, by, "beach2")
    bm = X.read_block(bx, by, disc=1, part="terrain")
    topo = Counter(X.decode_id(i)["topograph"] for i in X.block_mapids(bm))
    print(f"   ({bx},{by}): beach1={_fmt(b1):<8}  beach2={_fmt(b2)}")
    print(f"            terrain topos={dict(sorted(topo.items()))}")
no_beach1 = [b for b in BEACH2 if _stats(*b, "beach1") is None]
print(f"   => Beach2's UV band is u[0,0.5],v[0,0.97] -- the 11_128_128 atlas half, DISTINCT from "
      f"Beach1's v[~0.02,0.47].\n   => {len(no_beach1)}/4 beach2 blocks have NO beach1 {no_beach1} "
      f"=> Beach2 is an ALTERNATIVE regional shore, not a 2nd beach on a block.")

# ---- 3. SEA6 -------------------------------------------------------------------------------------
print("\n3. SEA6 (atlas 11_192_64, own Sea6Material, 4-frame -- WMRenderTextureBank.cs:61-63):")
for (bx, by) in SEA6:
    bm = X.read_block(bx, by, disc=1, part="sea6")
    V = bm.verts
    xr = (min(v[0] for v in V), max(v[0] for v in V))
    zr = (min(v[2] for v in V), max(v[2] for v in V))
    ladder = [p for p in ("sea1", "sea2", "sea3", "sea4", "sea5") if _stats(bx, by, p)]
    print(f"   ({bx},{by}): {_fmt(_stats(bx, by, 'sea6'))}  span x{xr} z{zr}  "
          f"(~{xr[1]-xr[0]:.0f}x{zr[1]-zr[0]:.0f}u)  ladder-here={ladder}")
sizes = {(_stats(*b, 'sea6')['tri']) for b in SEA6}
print(f"   => every sea6 instance = {sizes} tri (a single ~4x4u quad), always interior open ocean;\n"
      f"   => u-max 0.9841 matches Sea5's atlas scale, NOT sea1-4's 0.9921 -- Sea6 is an ORTHOGONAL\n"
      f"      special open-ocean decoration tile, NOT a rung of the shallow<->deep ladder.")

# ---- 4. SEA4f ------------------------------------------------------------------------------------
print("\n4. SEA4f -- the generic-ocean FILL mesh (runtime SeaBlockPrefab = baked `Block[12][0]f`, "
      "WMWorld.cs:1161):")
s4 = _stats(12, 0, "sea4")
s4f = _stats(12, 0, "sea4f")
print(f"   (12,0) sea4  = {_fmt(s4)}")
print(f"   (12,0) sea4f = {_fmt(s4f)}")
print(f"   => sea4f is {s4f['tri']} tri = 256 quads = a PERFECT 16x16 full-cell grid (seamless tiling "
      f"ocean);\n      the real sea4 is {s4['tri']} tri ({s4['tri']-s4f['tri']:+d}). Exactly ONE exists "
      f"because there is exactly ONE\n      generic ocean prefab; (12,0) is its arbitrary plain-open-ocean home.")

# ---- 5. BLOCK 219 --------------------------------------------------------------------------------
print("\n5. BLOCK 219 (Water Shrine) -- Number = row i*24 + col j:")
i219, j219 = divmod(219, 24)
print(f"   Number 219 => grid (x={j219}, y={i219})  [matches WMWorldPrefabMaker.cs:159 `j==3 && i==9`]")
terr = _stats(j219, i219, "terrain")
print(f"   ({j219},{i219}) terrain={_fmt(terr)} (a small landmass, y up to {terr['ymax']:.1f}); "
      f"object present={_stats(j219,i219,'object') is not None}")
present = [p for p in ("sea1", "sea2", "sea3", "sea4", "sea5", "sea6", "beach1", "beach2")
           if _stats(j219, i219, p)]
print(f"   water parts present in stock: {present}")
# the switchable form-2 water lives in the 0_2 LOD (WMWorldPrefabMaker.cs:161-166)
d1_02 = _part_blocks(1, "0_2")
form2_here = sorted(p for p, bs in d1_02.items() if (j219, i219) in bs)
print(f"   0_2-LOD parts at (3,9) = {form2_here}  (the Sea3_2/4_2/5_2 water-LEVEL form-switch)")
print("   => the WMWorld.cs:569-604 early return registers ONLY Object/Terrain(f1+f2) + WaterShrine\n"
      "      effect + Sea3/4/5(f1) + Sea3_2/4_2/5_2(f2), then RETURNS. So an s34 override on (3,9) can\n"
      "      reach Terrain/Object/Sea3/Sea4/Sea5 ONLY; Beach1/2, Sea1/2/6, Stream/River/Falls, Volcano\n"
      "      overrides are SKIPPED (never instantiated). Reclaim (Path D) never applies -- (3,9) is not IsSea.")

# ---- 6. KIT IMPACT -------------------------------------------------------------------------------
print("\n6. KIT IMPACT (which carry/gate part lists OMIT the studied forms):")
print(f"   transplant.PARTS         = {TP.PARTS}")
print(f"     beach2 in PARTS? {'beach2' in TP.PARTS}    sea6 in PARTS? {'sea6' in TP.PARTS}")
print(f"   OPEN_WATER_PARTS         = {sorted(TP.OPEN_WATER_PARTS)}   (fills; sea6 absent)")
adj_parts = sorted({p for pr in TP.SEA_ADJ_LAWFUL for p in pr})
print(f"   SEA_ADJ_LAWFUL parts     = {adj_parts}   (sea6 absent -> wang gate never reasons about it)")
# effective_prefab_arm assumes the generic SeaBlockPrefab binds only Sea4:
armstub, gate = TP.effective_prefab_arm([("Sea6", None)], cell=(9, 9), sidecar_parts=None)
print(f"   effective_prefab_arm on a lone Sea6 emit (no Terrain): bound={gate['bound']} "
      f"armed={gate['armed']}  -> a Sea6 would be treated as non-Sea4 (armed);")
print(f"      but the kit NEVER emits sea6/beach2 (absent from every emitter), so no gate MIS-fires.")
print("   THE DROP PATH (transplant.py:2656-2664): the deploy loop iterates ONLY `parts` (=PARTS);")
print("      a donor part outside it is neither re-emitted (rotated/shifted) NOR blanked -> under a")
print("      ROTATED/SHIFTED carry the donor prefab's ORIGINAL beach2/sea6 free-rides UNROTATED.")
qualified = {(0, 0), (10, 5), (10, 6), (5, 15), (5, 16), (6, 15), (6, 16), (12, 16), (12, 17)}
reach_b = sorted(set(BEACH2) & qualified)
reach_s = sorted(set(SEA6) & qualified)
print(f"   REACH: qualified --donor blocks intersect beach2={reach_b} sea6={reach_s} (none). The")
print(f"      default beach_only donor scan EXCLUDES the beach2 blocks (they have no beach1).")
print("   THE DISC-4 MIRROR (discmirror.py) is part-AGNOSTIC (regex `[a-z0-9]+`, whole-donor free-ride")
print("      pin) -> it would carry beach2/sea6 faithfully; the mirror is NOT a gap.")

print("\n=> VERDICT:\n"
      "   Beach2 -- REAL latent gap (low reach): add 'beach2' to transplant.PARTS +\n"
      "     GroundRetile.for_donor's gather (+ its Beach2Material foam relabel) so a rotated/shifted\n"
      "     carry of (6,3)/(7,3)/(8,2)/(8,3) doesn't leave a floating unrotated shore. Not urgent.\n"
      "   Sea6  -- real-but-NEGLIGIBLE (a single 4x4 fleck); same PARTS omission, cosmetically invisible.\n"
      "     Adding 'sea6' to PARTS makes a verbatim carry byte-complete; no gate mis-fires today.\n"
      "   Sea4f -- DECODE-ONLY: the seamless full-cell ocean fill; no kit path reads/targets it.\n"
      "   Block 219 = (3,9) -- DECODE-ONLY: only Terrain/Object/Sea3/4/5 are override-reachable there;\n"
      "     the WaterShrine + form-switch are hardcoded to Number==219 (uncarriable). No kit path targets it.")
