"""PROBE: which `--ground` families does `world-island` (island.build_landmass) actually MINT vs REFUSE?

The CLI help for `world-island --ground` says: 'grass (default), desert, snow, canyon are island-complete fills;
scrub/brush/dunes ... mintable, but a whole island of them reads off-language'.  CLAUDE.md section 8 + the code
(island.py:254-273 THE WALL-CONTEXT LAW, fail-closed since 2026-07-19) say canyon is refused outright, and
scrub/brush/dunes (wall_coastal unset/False) are refused too.  The help text and the code cannot both be right.

INSTRUMENT: build_landmass is hermetic when stamps=None, n_patches=0 (no install read), so it can be called
for every ground at a tiny radius.  CALIBRATION: the positive control 'grass' MUST build (otherwise a refusal on
the others could be a generic breakage rather than the wall-context gate); the verdict reads the refusal TEXT,
not merely 'an exception happened'.

Rerun:  py studies/terrain-malleability/operators/probe_island_ground_refusal.py
"""
import sys
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import island as I, grassland as G

rows = []
for g in G.GROUNDS:
    try:
        r = I.build_landmass(center=(300.0, -300.0), base_radius=14.0, seed=5.0, n_patches=0, stamps=None,
                             ground=g, relief_amp=0.0)
        rows.append((g, "BUILT", f"{len(r['blocks'])} block(s)"))
    except ValueError as e:
        msg = str(e)
        kind = "REFUSED:WALL-CONTEXT" if "WALL-CONTEXT" in msg else "OTHER-ValueError"
        rows.append((g, kind, msg[:110].replace("\n", " ")))
    except Exception as e:                                           # noqa: BLE001
        rows.append((g, "OTHER-" + type(e).__name__, str(e)[:110]))

print(f"{'ground':8s} {'wall_coastal':12s} outcome")
for g, k, m in rows:
    print(f"{g:8s} {str(G.GROUNDS[g].get('wall_coastal')):12s} {k:22s} {m}")
ctrl = dict((g, k) for g, k, _ in rows)
ok = ctrl.get("grass") == "BUILT"
print("\npositive control (grass builds):", "PASS" if ok else "FAIL -- probe void")
print("mintable:", sorted(g for g, k, _ in rows if k == "BUILT"))
print("refused by the wall-context gate:", sorted(g for g, k, _ in rows if k == "REFUSED:WALL-CONTEXT"))
sys.exit(0 if ok else 3)
