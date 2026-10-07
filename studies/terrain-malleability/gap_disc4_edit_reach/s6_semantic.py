"""STEP 6 -- SEMANTIC TRAPS: where a geometrically correct disc-4 transfer is still wrong, + the pin-path bug.

  A  PER-PART refusal: of the 189 gate-refused land cells, how many refuse ONLY because a non-Terrain part
     differs (Terrain identical or an exact permutation) -- what a per-part gate would recover for the
     Terrain-only verbs (world-terrain / -retarget / -deploy).
  B  OVERLAY geometry: disc-4-only Terrain tris that share NO corner position with any disc-4 tri that has a
     disc-1 counterpart (geometry laid over / inset in the ground with its own vertices). Vertex-sharing closure
     cannot see them (s4 K5 found one at (19,11)); topograph histogram + overlap with the RIDGE layer.
  C  DISPATCH of the entrance cells disc 4 closed or opened: per cell, the disc-1 vs disc-4 event-tile cells, and
     whether the disc-4 free-roam dispatcher EVT_WORLD_WORLD08 (wldMapNo 9008, the SC>=11090 state; memory
     project-ff9-overworld-worlds) and the default WORLD09 still carry an object-0 cell-tag trigger for them
     (ff9.WorldEvent packs the walked CELL: ff9.cs w_worldPos2Cell :9106 + WorldEvent call :5197 at the stock
     base) -> whether re-stamping a disc-1 entrance tile onto disc 4 RE-OPENS a place.
  D  AREA re-zoning on UNCHANGED geometry: (area_d1 -> area_d4) transitions over geometry-matched Terrain tris.
  E  THE PIN-PATH PREFIX BUG (discmirror.py:323 -> extract.read_block substring match): a dry-run mirror of a
     scratch cell whose Donor.txt names disc-1 (19,11) (River + RiverJoint) -- predicted to pin RiverJoint
     twice and never pin River. Control: donor (12,10) (no colliding part names) pins each part once.
Writes out/s6_semantic.json.
Run (from C:\\gd\\Dream-World-IX\\ff9mapkit):  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_disc4_edit_reach/s6_semantic.py
"""
import json
import pickle
import shutil
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402
import numpy as np                                    # noqa: E402

G = L.GAME
data = L.load_cache()
meshes, pairs = data["meshes"], data["pairs"]
s1g = json.loads((L.OUT / "s1_gate.json").read_text(encoding="utf-8"))
rows = {tuple(map(int, k.split(","))): r for k, r in s1g["rows"].items()}
refused = sorted(c for c, r in rows.items() if r["land"] and r["shipped"].startswith("SKIP"))
s2 = json.loads((L.OUT / "s2_footprint.json").read_text(encoding="utf-8"))
out = {}

# ---------------------------------------------------------------- A per-part refusal
cls_of = {}
for (x, y, p), pr in pairs.items():
    cls_of[(x, y, p)] = "IDENT" if pr["raw_identical"] else "PERM" if pr["perm"] else \
        "ATTR" if (pr["g1"].all() and pr["g4"].all()) else "GEOM"
ter_hist = Counter()
other_parts = Counter()
terrain_ok_cells = []
for c in refused:
    k = cls_of.get((c[0], c[1], "terrain"), "ONE-DISC")
    ter_hist[k] += 1
    if k in ("IDENT", "PERM"):
        terrain_ok_cells.append(c)
        cell = s2["cells"][f"{c[0]},{c[1]}"]["parts"]
        for p, v in cell.items():
            if v["cls"] not in ("IDENT", "PERM"):
                other_parts[p] += 1
print("A refused land cells by TERRAIN class:", dict(ter_hist))
print("  terrain identical/permuted (per-part gate recovers these for Terrain-only verbs):", len(terrain_ok_cells))
print("  parts that cause their refusal:", dict(other_parts))
out["A"] = {"refused_terrain_class": dict(ter_hist), "terrain_ok_cells": [list(c) for c in terrain_ok_cells],
            "refusing_parts": dict(other_parts)}

# ---------------------------------------------------------------- B overlay census
objs = L.mesh_objects()
ov_topo, ov_cells, ov_total, d4only_total = Counter(), Counter(), 0, 0
layers = pickle.load(open(L.CACHE_DIR / "s2_layers.pkl", "rb"))
ridge_keys = set()
for c, lay in layers["hazard"].items():
    for tri in lay.get("RIDGE", []):
        ridge_keys.add(tuple(np.round(np.asarray(tri)[:, [0, 2]].mean(0), 3)))
ov_in_ridge = 0
k5_tri = None
for (x, y, p), pr in pairs.items():
    if p != "terrain" or pr["perm"]:
        continue
    m4 = meshes[(4, x, y, p)]
    V, T, I = m4["V"], m4["T"], m4["idall"]
    pos = lambda vi: V[vi].tobytes()
    shared = set()
    for t in np.nonzero(pr["m4"])[0]:
        for vi in T[t]:
            shared.add(pos(vi))
    for t in np.nonzero(~pr["m4"])[0]:
        d4only_total += 1
        if not any(pos(vi) in shared for vi in T[t]):
            # does it share a corner with ANOTHER d4-only tri that is connected to matched geometry? (flood)
            ov_total += 1
            ov_topo[L.topo(int(I[t]))] += 1
            ov_cells[(x, y)] += 1
            cen = V[T[t]].mean(0)
            key = tuple(np.round(np.array([cen[0] + 64 * x, cen[2] - 64 * y]), 3))
            ov_in_ridge += key in ridge_keys
            if (x, y) == (19, 11) and t == 190:
                k5_tri = {"topograph": L.topo(int(I[t])), "event": L.event(int(I[t])), "area": L.area(int(I[t]))}
# component analysis: union d4-only tris by shared corner position; a component is FLOATING when none of its
# corner positions is a corner of a matched (has-a-disc-1-counterpart) tri; NEWPOS = corner position absent from
# every disc-1 terrain vertex of the cell (what a vertex-sharing closure can never key on)
fl_comp, fl_tris, fl_topo, newpos_tris, all_comp = 0, 0, Counter(), 0, 0
for (x, y, p), pr in pairs.items():
    if p != "terrain" or pr["perm"]:
        continue
    m4, m1 = meshes[(4, x, y, p)], meshes[(1, x, y, p)]
    V, T, I = m4["V"], m4["T"], m4["idall"]
    d1pos = {m1["V"][vi].tobytes() for vi in range(len(m1["V"]))}
    shared = {V[vi].tobytes() for t in np.nonzero(pr["m4"])[0] for vi in T[t]}
    only = list(np.nonzero(~pr["m4"])[0])
    parent = {t: t for t in only}
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    bypos = defaultdict(list)
    for t in only:
        for vi in T[t]:
            bypos[V[vi].tobytes()].append(t)
        if any(V[vi].tobytes() not in d1pos for vi in T[t]):
            newpos_tris += 1
    for lst in bypos.values():
        for t in lst[1:]:
            ra, rb = find(lst[0]), find(t)
            if ra != rb:
                parent[ra] = rb
    comps = defaultdict(list)
    for t in only:
        comps[find(t)].append(t)
    for comp in comps.values():
        all_comp += 1
        if not any(V[vi].tobytes() in shared for t in comp for vi in T[t]):
            fl_comp += 1; fl_tris += len(comp)
            for t in comp:
                fl_topo[L.topo(int(I[t]))] += 1
print(f"B components of disc-4-only terrain tris: {all_comp}; FLOATING (no corner on matched geometry): {fl_comp} "
      f"comps / {fl_tris} tris, topographs {dict(fl_topo.most_common(6))}; tris with a NEW corner position: {newpos_tris}")
out_B_extra = {"components": all_comp, "floating_components": fl_comp, "floating_tris": fl_tris,
               "floating_topo": dict(fl_topo), "tris_with_new_corner_position": newpos_tris}
print(f"B overlay-class disc-4-only terrain tris (no corner shared with matched geometry): {ov_total} of {d4only_total}"
      f" in {len(ov_cells)} cells; topographs {dict(ov_topo.most_common(8))}; in RIDGE layer {ov_in_ridge}")
print("  the K5 tri (19,11)#190:", k5_tri)
out["B"] = {"overlay_tris": ov_total, "d4only_tris": d4only_total, "cells": len(ov_cells),
            "topograph_hist": dict(ov_topo), "in_ridge_layer": ov_in_ridge, "k5_tri_19_11_190": k5_tri, **out_B_extra}

# ---------------------------------------------------------------- C dispatch of closed / opened entrance cells
from ff9mapkit.world import entrance as EN          # noqa: E402
from ff9mapkit.eb.model import EbScript              # noqa: E402
from ff9mapkit.eb import disasm as D                 # noqa: E402

alld = EN.load_all_dispatchers(game=G)


def cell_triggers(b):
    s = EbScript(b)
    funcs = s.entry(0).funcs
    case_at = {}
    for f in funcs:
        body = s.data[f.abs_start:f.abs_end]
        j = body.find(EN._BYTE39_PAT)
        if j >= 0 and j + 5 <= len(body):
            case_at[f.abs_start] = body[j + 3] | (body[j + 4] << 8)
    trig = {}
    for f in funcs:
        cell = EN.unpack_cell_tag(f.tag)
        if cell is not None:
            trig[cell] = case_at.get(f.abs_start)
    return trig


def case_fields(b):
    """locate.case_to_fields for an arbitrary dispatcher's bytes (same decode)."""
    from ff9mapkit.world import locate as LOC
    s = EbScript(b)
    fn = next((f for f in s.entry(1).funcs if f.tag == 1), None)
    if fn is None:
        return {}
    ins = list(D.iter_code(s.data, fn.abs_start, fn.abs_end))
    area_sw = next(((i, si) for i in ins if i.is_switch
                    for si in (D.decode_switch(i) or i.switch(),) if si and si.base == 2), None)
    if area_sw is None:
        return {}
    _, si = area_sw
    edges = [ed for ed in si.edges if not ed.is_default]
    order = sorted({ed.target for ed in edges})
    idx_at = lambda off: next((k for k, i in enumerate(ins) if i.off >= off), len(ins))
    res = {}
    for ed in edges:
        lo = idx_at(ed.target)
        nxt = next((t for t in order if t > ed.target), None)
        hi = idx_at(nxt) if nxt is not None else min(lo + 60, len(ins))
        br, cond = [], None
        for k in range(lo, hi):
            i = ins[k]
            if i.op == 0x05 and i.args and "opDC(0)" in str(i.args[0]):
                cond = LOC._sc_condition(str(i.args[0]))
            elif i.op == 0x2B:
                br.append((cond or "default", i.imm(0)))
                cond = None
            elif i.op == 0x01:
                cond = None
        res[ed.value] = br or [("default", None)]
    return res


disp = {n: alld[n]["us"] for n in alld if "us" in alld[n]}
names = sorted(disp)
trig = {n: cell_triggers(disp[n]) for n in names}
cf08 = case_fields(disp.get("evt_world_world08", b"")) if "evt_world_world08" in disp else {}
cf09 = case_fields(disp.get("evt_world_world09", b"")) if "evt_world_world09" in disp else {}
print("C dispatchers:", names, "| WORLD08 triggers:", len(trig.get("evt_world_world08", {})),
      "| WORLD00 triggers:", len(trig.get("evt_world_world00", {})))


def event_cells(d, x, y):
    m = meshes[(d, x, y, "terrain")]
    V, T, I = m["V"], m["T"], m["idall"]
    cells = set()
    for t in range(len(T)):
        e = L.event(int(I[t]))
        if e:
            c = V[T[t]].mean(0)
            cells.add((int((c[0] + 64 * x) / 32), int((c[2] - 64 * y) / -32), e))
    return cells


ent = json.loads((L.D4OUT / "entrance_check.json").read_text(encoding="utf-8"))
crows = []
for r in ent:
    x, y = r["block"]
    c1, c4 = event_cells(1, x, y), event_cells(4, x, y)
    lost, new = sorted(c1 - c4), sorted(c4 - c1)
    def tinfo(cells):
        o = []
        for cell in cells:
            t08 = trig.get("evt_world_world08", {}).get(cell, "none")
            t00 = trig.get("evt_world_world00", {}).get(cell, "none")
            t09 = trig.get("evt_world_world09", {}).get(cell, "none")
            dest = cf08.get(t08) if isinstance(t08, int) else None
            d09 = cf09.get(t09) if isinstance(t09, int) else None
            # world-entrance authors a NEW object-0 trigger in every dispatcher whose AREA switch carries the case
            # (entrance.py author_entrance target selection) -- 9008's switch arm for the case the place used:
            sw08 = cf08.get(t09) if isinstance(t09, int) else (cf08.get(t00) if isinstance(t00, int) else None)
            o.append({"cell": list(cell), "w00_case": t00, "w08_case": t08, "w09_case": t09, "w08_dest": dest,
                      "w09_dest": d09, "w08_switch_arm_for_case": sw08})
        return o
    crows.append({"block": [x, y], "verdict": r["verdict"], "landmark": r.get("landmark"),
                  "lost_cells": tinfo(lost), "new_cells": tinfo(new)})
reopen = sum(1 for r in crows for c in r["lost_cells"] if c["w08_case"] not in ("none", None))
reopen09 = sum(1 for r in crows for c in r["lost_cells"] if c["w09_case"] not in ("none", None))
lost_n = sum(len(r["lost_cells"]) for r in crows)
inert_new = sum(1 for r in crows for c in r["new_cells"] if c["w08_case"] == "none")
new_n = sum(len(r["new_cells"]) for r in crows)
print(f"  disc-1 entrance cells LOST on disc 4: {lost_n}; of those WORLD08 still has a trigger for {reopen}; "
      f"WORLD09 (the default state, and the ~ disc-switch's reload target) for {reopen09}")
print(f"  disc-4-only entrance cells: {new_n}; of those WORLD08 has NO trigger for {inert_new}")
for r in crows:
    if r["lost_cells"] and r["verdict"].startswith("CLOSED"):
        print("   ", r["block"], r["landmark"][0] if r["landmark"] else "", [(c["cell"], c["w08_case"], c["w09_case"], c["w09_dest"], c["w08_switch_arm_for_case"]) for c in r["lost_cells"]][:3])
out["C"] = {"rows": crows, "lost_cells": lost_n, "lost_cells_with_w08_trigger": reopen, "lost_cells_with_w09_trigger": reopen09,
            "new_cells": new_n, "new_cells_without_w08_trigger": inert_new, "dispatchers": names}

# ---------------------------------------------------------------- D area re-zone on unchanged geometry
trans = Counter()
for (x, y, p), pr in pairs.items():
    if p != "terrain" or pr["perm"]:
        continue
    a = L.decode(objs[(1, "0_1", x, y, p)], 1, x, y)
    b = L.decode(objs[(4, "0_1", x, y, p)], 4, x, y)
    k1 = [k[0] for k in L.tri_keys(a, L._prec(a))]
    k4 = [k[0] for k in L.tri_keys(b, L._prec(b))]
    pool = defaultdict(list)
    for j, k in enumerate(k4):
        pool[k].append(j)
    I1, I4 = meshes[(1, x, y, p)]["idall"], meshes[(4, x, y, p)]["idall"]
    for i, k in enumerate(k1):
        if pool.get(k):
            j = pool[k].pop()
            if L.area(int(I1[i])) != L.area(int(I4[j])):
                trans[(L.area(int(I1[i])), L.area(int(I4[j])))] += 1
print("D area transitions on unchanged geometry (a1->a4: tris):", dict(trans.most_common(12)))
out["D"] = {"area_transitions": {f"{a}->{b}": n for (a, b), n in trans.most_common()}}

# ---------------------------------------------------------------- E pin-path prefix bug (dry run, scratch)
from ff9mapkit.world import discmirror as DM        # noqa: E402
from ff9mapkit.world import mesh as M               # noqa: E402
r4 = DM._real_parts(4, "0_1", game=G)
r1 = DM._real_parts(1, "0_1", game=G)
ocean = [(x, y) for y in range(20) for x in range(24) if (x, y) not in r4 and (x, y) not in r1]
e_res = {}
for tag, donor in (("bug", (19, 11)), ("control", (12, 10))):
    cell = ocean[0] if tag == "bug" else ocean[1]
    mod = L.CACHE_DIR / f"pin_{tag}"
    if mod.exists():
        shutil.rmtree(mod)
    bm = L.decode(objs[(1, "0_1", 12, 10, "terrain")], 1, 12, 10)
    import dataclasses
    bm = dataclasses.replace(bm, x=cell[0], y=cell[1], name=f"Block[{cell[0]}][{cell[1]}] Terrain")
    M.write_ff9mesh(bm, mod / M.override_relpath(1, cell[0], cell[1], "0_1", "Terrain"))
    sc = mod / M.donor_sidecar_relpath(1, cell[0], cell[1], "0_1")
    sc.parent.mkdir(parents=True, exist_ok=True)
    sc.write_text(f"{donor[0]},{donor[1]}")
    log = []
    res = DM.mirror(str(mod), src_disc=1, dst_disc=4, lod="0_1", game=G, dry_run=True, log=log.append)
    pinned = [Path(p).name for p in res["pinned"]]
    extras = sorted(r1.get(donor, set()) - {"terrain"})
    e_res[tag] = {"cell": list(cell), "donor": list(donor), "donor_parts_to_pin": extras, "pinned_files": pinned,
                  "pin_log": [l for l in log if "PIN" in l]}
    print(f"E {tag}: donor {donor} parts {extras} -> pinned {pinned}")
bug = e_res["bug"]
assert "river" in bug["donor_parts_to_pin"] and "riverjoint" in bug["donor_parts_to_pin"]
n_rj = sum(1 for n in bug["pinned_files"] if n.endswith("RiverJoint.ff9mesh"))
n_r = sum(1 for n in bug["pinned_files"] if n.endswith(" River.ff9mesh"))
ctl = e_res["control"]
assert len(set(ctl["pinned_files"])) == len(ctl["pinned_files"]) == len(ctl["donor_parts_to_pin"]), "control must pin each part once"
print(f"  bug cell: RiverJoint pinned {n_rj}x, River pinned {n_r}x  (control pins each of its {len(ctl['donor_parts_to_pin'])} parts once)")
out["E"] = {"runs": e_res, "riverjoint_pins": n_rj, "river_pins": n_r}
(L.OUT / "s6_semantic.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print("wrote out/s6_semantic.json")
