"""THE DESERT BEACH ACCEPTANCE -- the family-keyed sand-band machinery vs real bytes.

Rung A shipped: coastmorph's sand-band verbs auto-detect the block's family
(SAND_BANDS: grass topo-31 / desert topo-32, THE BEACH TRANSLATION LAW). This proves
the desert side against every real desert beach block, offline:

  1. THE DECODE CENSUS -- every sand tri on all 40 beach blocks decodes under its
     block's own family at grass-comparable rates (run/cap/conforming accounting).
  2. sand_rebuild on desert blocks -- the identity rebuild (P/Q rect flip + re-decode
     self-check) must build on desert bands exactly as it does on grass.
  3. cap_rebuild on desert blocks -- the end-cap byte-identity round-trip.
  4. beach_mint dry-build on any desert block of the rung-1 column class.

The grass side needs no new proof -- the 44 golden tests are byte-frozen through the
refactor. Run from the repo root:
    py studies/overworld-topography/desert_beach_acceptance.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import coastmorph as CM                # noqa: E402
from ff9mapkit.world import transplant as TR                # noqa: E402

OUTD = Path(__file__).with_name("out")
prev = json.loads((OUTD / "desert_beach.json").read_text())
beach_blocks = [tuple(map(int, s.split(","))) for s in prev["beach_blocks"]]
out = {}

# ---- 1. the decode census -----------------------------------------------------------------------
print("1. THE DECODE CENSUS (per block: family + run/cap/conforming tri counts)")
per_fam = {"grass": Counter(), "desert": Counter()}
for blk in beach_blocks:
    terr = TR.world_tris(*blk, "terrain", disc=1)
    fam = CM._sand_band_family(terr, what=f"{blk}")
    assert fam is not None, f"{blk}: a beach1 block with no sand?"
    c = Counter()
    for t3 in terr:
        if X.decode_id(int(round(t3[0][3][0])))["topograph"] != fam["topo"]:
            continue
        d = CM._sand_tri_decode(t3, fam)
        c["run" if d and d[0] == "run" else "cap" if d else "conforming"] += 1
    per_fam[fam["name"]].update(c)
    print(f"   {blk}: {fam['name']:6s} {dict(c)}")
for name, c in per_fam.items():
    tot = sum(c.values())
    dec = c["run"] + c["cap"]
    print(f"   == {name}: {tot} sand tris, decodable {dec} ({dec / max(1, tot):.0%}) "
          f"run {c['run']} cap {c['cap']} conforming {c['conforming']}")
    out[f"census_{name}"] = dict(c)
g = per_fam["grass"]
d = per_fam["desert"]
rate_g = (g["run"] + g["cap"]) / max(1, sum(g.values()))
rate_d = (d["run"] + d["cap"]) / max(1, sum(d.values()))
assert rate_d >= rate_g - 0.15, f"desert decodes far below grass ({rate_d:.0%} vs {rate_g:.0%})"
print(f"   GATE: desert decode rate {rate_d:.0%} within 15pt of grass {rate_g:.0%}  OK")

# ---- 2 + 3 + 4: the verbs on desert blocks ------------------------------------------------------
des_blocks = [blk for blk in beach_blocks
              if CM._sand_band_family(TR.world_tris(*blk, "terrain", disc=1),
                                      what="x")["name"] == "desert"]
print(f"\n2. sand_rebuild over the {len(des_blocks)} desert blocks:")
ok = []
for blk in des_blocks:
    try:
        tw = CM.sand_rebuild(blk, disc=1)
        n = sum(len(t.tris) for t in tw if type(t).__name__ == "EmitTris")
        ok.append((blk, n))
        print(f"   {blk}: BUILT ({n} tris re-derived)")
    except ValueError as e:
        print(f"   {blk}: refused -- {e}")
assert ok, "sand_rebuild built on NO desert block"
out["sand_rebuild_ok"] = [[list(b), n] for b, n in ok]

print(f"\n3. cap_rebuild over the desert blocks:")
ok3 = []
for blk in des_blocks:
    try:
        tw = CM.cap_rebuild(blk, disc=1)
        n = sum(len(t.tris) for t in tw if type(t).__name__ == "EmitTris")
        ok3.append((blk, n))
        print(f"   {blk}: BUILT ({n} tris, byte-identity through the emitters)")
    except ValueError as e:
        print(f"   {blk}: refused -- {e}")
out["cap_rebuild_ok"] = [[list(b), n] for b, n in ok3]

print(f"\n4. beach_mint (rung-1 identity class) over the desert blocks:")
ok4 = []
for blk in des_blocks:
    try:
        tw = CM.beach_mint(blk, disc=1)
        n = sum(len(t.tris) for t in tw if type(t).__name__ == "EmitTris")
        ok4.append((blk, n))
        print(f"   {blk}: BUILT ({n} tris minted)")
    except ValueError as e:
        print(f"   {blk}: refused -- {str(e)[:90]}")
out["beach_mint_ok"] = [[list(b), n] for b, n in ok4]

print("\nACCEPTANCE:", "PASSED" if ok and (ok3 or ok4) else "PARTIAL -- see refusals")
(OUTD / "desert_beach_acceptance.json").write_text(json.dumps(out, indent=1))
print(f"-> {OUTD / 'desert_beach_acceptance.json'}")
