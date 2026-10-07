"""STEP 11 -- THE EDITING GRAMMAR + per-site table, aggregated from census.json / anatomy.json.

Prints (and writes out/grammar_summary.json):
  * terrain (Form 1) tri bookkeeping over every changed block: kept-exact / re-heighted / cut / added, area shares
  * per-block changed-area fraction distribution (local touch-up vs whole-block rebuild)
  * entrance-tile (event bits) changes per block with landmark  -> the story-readable edits
  * the per-site table for NOTES.md
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/grammar_summary.py
"""
import json
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
rows = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
ana = json.loads((OUT / "anatomy.json").read_text(encoding="utf-8"))
res = {}

T = [r for r in rows if r["lod"] == "0_1" and r["part"] == "terrain" and r["cls"] not in ("IDENTICAL", "REORDERED")]
t1 = sum(r["t1"] for r in T); t4 = sum(r["t4"] for r in T)
sh = sum(r["tri_shared_exact"] for r in T); rh = sum(r["tri_reheighted"] for r in T)
o1 = sum(r["tri_only1"] for r in T); o4 = sum(r["tri_only4"] for r in T)
a1 = sum(r["area1"] for r in T); ao1 = sum(r["area_only1"] for r in T); arh = sum(r["area_reheighted"] for r in T)
print(f"TERRAIN, {len(T)} really-changed blocks: tris {t1} -> {t4} (net {t4-t1:+d})")
print(f"   kept exact {sh} ({100*sh/t1:.1f}%), re-heighted in place {rh} ({100*rh/t1:.1f}%), "
      f"cut {o1} ({100*o1/t1:.1f}%), added {o4}")
print(f"   XZ area: cut {100*ao1/a1:.1f}% + re-heighted {100*arh/a1:.1f}% of the changed blocks' area")
fr = sorted((r["area_only1"] + r["area_reheighted"]) / max(r["area1"], 1e-9) for r in T)
q = lambda p: round(fr[min(len(fr) - 1, int(p * len(fr)))], 3)
print(f"   per-block touched-area fraction: median {q(0.5)}, p75 {q(0.75)}, p90 {q(0.9)}, max {q(1.0)}; "
      f">50% touched: {sum(1 for f in fr if f > 0.5)} blocks")
big = sorted(T, key=lambda r: -(r["area_only1"] + r["area_reheighted"]) / max(r["area1"], 1e-9))[:8]
print("   most-touched blocks:", [((r["x"], r["y"]), round((r["area_only1"] + r["area_reheighted"]) / r["area1"], 2),
                                  r["t1"], r["t4"]) for r in big])
cls = Counter(r["cls"] for r in rows if r["lod"] == "0_1" and r["part"] == "terrain")
print("   terrain class counts:", dict(cls))
res["terrain"] = {"blocks": len(T), "t1": t1, "t4": t4, "kept": sh, "reheighted": rh, "cut": o1, "added": o4,
                  "area_cut_frac": ao1 / a1, "area_rh_frac": arh / a1,
                  "touched_frac_quantiles": {"p50": q(0.5), "p75": q(0.75), "p90": q(0.9), "max": q(1.0)},
                  "class_counts": dict(cls)}

# entrance changes per block
print("\nENTRANCE TILES (event bits) changed, per block (1u samples), from the engine-faithful ground query:")
ev = []
for k, r in ana["blocks"].items():
    if r["event_transitions"]:
        add = sum(v for a, b, v in r["event_transitions"] if a == 0 and b != 0)
        rem = sum(v for a, b, v in r["event_transitions"] if a != 0 and b == 0)
        swp = sum(v for a, b, v in r["event_transitions"] if a != 0 and b != 0)
        ev.append((k, r.get("landmark"), add, rem, swp, r["event_transitions"]))
for e in sorted(ev, key=lambda e: -(e[2] + e[3] + e[4])):
    print(f"   {e[0]:9s} ~{e[1]}: +{e[2]} new, -{e[3]} removed, {e[4]} re-id'd  {e[5]}")
res["entrances"] = ev

# per-site table (anatomy blocks with >= 150 changed samples)
print("\nSITES (blocks with >=150 changed 1u samples):")
site = []
for k, r in sorted(ana["blocks"].items(), key=lambda kv: -kv[1]["changed_samples"]):
    if r["changed_samples"] < 150:
        continue
    site.append({"block": k, "landmark": r.get("landmark"), "changed": r["changed_samples"],
                 "parts": r["parts_changed"], "dy": r.get("dy"), "mesh": r["mesh_transitions"][:3],
                 "topo": r["topo_transitions"][:3], "walk": r["walk_flips"], "bbox": r.get("changed_bbox_world")})
    print("  ", site[-1])
res["sites"] = site
(OUT / "grammar_summary.json").write_text(json.dumps(res, indent=0, default=str), encoding="utf-8")
print("->", OUT / "grammar_summary.json")
