"""THE ISLE RECT STUDY -- registered in ISLE-RECT-STUDY.md (read it first; read-only, every dry run writes nothing).

Q1 every candidate donor rect around Daguerreo through the verb's own `excise_plan`, then a real
   `transplant_region(dry_run=True, shift=(0,0))` for each rect that keeps the island;
Q2 every open-ocean target window per size, ranked by distance to our continent (the verb accepts no
   wrapping target: transplant.py checks 0 <= bx, bx+w <= 24, 0 <= by, by+h <= 20);
Q3 the weld-audit pairs located, against the donor's OWN stock bytes (inherited vs introduced).

    py -X utf8 studies/overworld-topography/west-seam-continent/isle_rect_study.py
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.world import extract as X                  # noqa: E402
from ff9mapkit.world import mesh as M                     # noqa: E402
from ff9mapkit.world import transplant as TR              # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
MOD_WM = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
BENCH = Path(r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\4defe9bc-0f55-44e7-952d-bd74e20446f5"
             r"\scratchpad\bench-isle\FF9CustomMap-world")
R4PRE = Path(r"C:\gd\Dream-World-IX\backups\west-seam-continent\r4-pre.20260828-103332\Disc1")
ISLAND_BLOCKS = (5, 7, 15, 16)                             # bx0, bx1, by0, by1 (the raster island bbox)
SIZES = [(3, 2), (3, 3), (3, 4), (4, 3), (4, 4)]


def candidates():
    bx0, bx1, by0, by1 = ISLAND_BLOCKS
    out = []
    for nx, ny in SIZES:
        for dbx in range(bx1 - nx + 1, bx0 + 1):
            for dby in range(by1 - ny + 1, by0 + 1):
                if dbx >= 0 and dby >= 0 and dbx + nx <= 24 and dby + ny <= 20:
                    out.append(((dbx, dby), (nx, ny)))
    return out


def main():
    # ---- Q2 first: who is free, and where our continent is ----
    env = X._worldmap_env(1, None)
    pat = re.compile(r"worldmap/disc1/0_1/r\d+/block\[(\d+)\]\[(\d+)\] (\w+)")
    stock = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            stock[(int(m.group(1)), int(m.group(2)))].add(m.group(3))

    def mod_has(bx, by):
        d = MOD_WM / f"r{by}"
        return d.is_dir() and any(d.glob(f"Block[[]{bx}[]][[]{by}[]] *.ff9mesh"))
    free = {(bx, by): not stock.get((bx, by)) and not mod_has(bx, by) for bx in range(24) for by in range(20)}
    cont = sorted({(int(m.group(1)), int(m.group(2))) for p in R4PRE.rglob("*Terrain.ff9mesh")
                   for m in [re.search(r"Block\[(\d+)\]\[(\d+)\] Terrain", p.name)] if m})
    print(f"our continent: {len(cont)} Terrain blocks {cont[:6]}...; free blocks on the grid: {sum(free.values())}/480")

    def dist(cells):                                       # Chebyshev block distance, x wraps for distance only
        best = 99
        for (a, b) in cells:
            for (c, d) in cont:
                dx = min(abs(a - c), 24 - abs(a - c))
                dz = min(abs(b - d), 20 - abs(b - d))
                best = min(best, max(dx, dz))
        return best
    windows = {}
    print("\n==== Q2: OPEN-OCEAN TARGET WINDOWS (no wrap: the verb refuses it) ====")
    for nx, ny in SIZES:
        ws = []
        for bx in range(0, 24 - nx + 1):
            for by in range(0, 20 - ny + 1):
                cells = [(bx + i, by + j) for i in range(nx) for j in range(ny)]
                if all(free[c] for c in cells):
                    ws.append((dist(cells), (bx, by)))
        ws.sort()
        windows[(nx, ny)] = ws
        print(f"  {nx}x{ny}: {len(ws)} windows; nearest to our continent: "
              + ", ".join(f"{w} (d {d})" for d, w in ws[:5]))

    # ---- Q1: the builder's own excise plan per rect ----
    print("\n==== Q1: EXCISE PLAN PER CANDIDATE RECT ====")
    rows = []
    for donor, size in candidates():
        try:
            tw, rep = TR.excise_plan(donor, size, disc=1)
        except Exception as err:
            rows.append({"donor": donor, "size": size, "error": str(err)[:200]})
            print(f"  {donor}+{size[0]}x{size[1]}: ERROR {str(err)[:160]}")
            continue
        r = {"donor": donor, "size": size, "assemblies": rep["assemblies"][:6], "foreign": rep["foreign"],
             "kept": rep.get("kept_land"), "dropped": rep.get("dropped_land"), "refused": rep.get("refused"),
             "fill": rep.get("fill_tris"), "n_tweaks": len(tw), "tweaks": tw}
        rows.append(r)
        print(f"  {donor}+{size[0]}x{size[1]}: assemblies {r['assemblies']} foreign {r['foreign']} "
              f"kept/dropped {r['kept']}/{r['dropped']} fill {r['fill']} "
              + (f"REFUSED: {r['refused'][:90]}" if r["refused"] else f"ok ({len(tw)} tweaks)"))

    # ---- Q1b: a real dry run per rect that keeps the island; Q3 captures the weld pairs ----
    captured = {}
    real = M.weld_audit

    def spy(meshes, **kw):
        meshes = list(meshes)
        out = real(meshes, **kw)
        captured["pairs"] = out
        return out
    print("\n==== Q1b: DRY RUNS (shift 0,0; nothing written) ====")
    dry = []
    for r in rows:
        if r.get("error") or r.get("refused"):
            continue
        ws = windows.get(tuple(r["size"]))
        if not ws:
            print(f"  {r['donor']}+{r['size'][0]}x{r['size'][1]}: no open-ocean target of this size anywhere")
            continue
        tgt = ws[0][1]
        captured.clear()
        M.weld_audit = spy
        try:
            s = TR.transplant_region(str(BENCH), cell=tgt, donor=r["donor"], size=r["size"], shift=(0.0, 0.0),
                                     tweaks=r["tweaks"], dry_run=True, skip_mirror=True)
            gates = {g["gate"]: g for g in s["gates"]}
            fails = [g["gate"] for g in s["gates"] if not g.get("ok", True)]
            d = {"donor": r["donor"], "size": r["size"], "target": tgt, "target_dist": ws[0][0],
                 "carried": s.get("carried"), "fails": fails,
                 "land_fit": {k: gates.get("land-fit", {}).get(k) for k in ("bbox", "ok")},
                 "weld": {k: gates.get("weld-audit", {}).get(k) for k in ("pairs", "frame_pairs", "border_t_pairs")},
                 "wang": gates.get("wang-carry", {}).get("incoherent"),
                 "census": {k: gates.get("census", {}).get(k) for k in ("miss", "inherited", "introduced")},
                 "weld_pairs_region": captured.get("pairs", [])}
        except Exception as err:
            d = {"donor": r["donor"], "size": r["size"], "target": tgt, "error": str(err)[:300]}
        finally:
            M.weld_audit = real
        dry.append(d)
        if "error" in d:
            print(f"  {d['donor']}+{d['size'][0]}x{d['size'][1]} -> target {tgt}: ERROR {d['error'][:200]}")
        else:
            print(f"  {d['donor']}+{d['size'][0]}x{d['size'][1]} -> target {tgt} (d {d['target_dist']}): carried "
                  f"{d['carried']}; FAILS {d['fails'] or 'none'}; weld {d['weld']}; wang {d['wang']}; census {d['census']}")

    # ---- Q3: are the interior weld pairs inherited from the donor's own stock bytes? ----
    print("\n==== Q3: WELD PAIRS vs THE DONOR'S OWN STOCK BYTES ====")
    for d in dry:
        if "error" in d or not d["weld"]["pairs"]:
            continue
        (dbx, dby), (nx, ny) = d["donor"], d["size"]
        meshes = []
        for by in range(dby, dby + ny):
            for bx in range(dbx, dbx + nx):
                for p in TR.PARTS:
                    try:
                        bm = X.read_block(bx, by, disc=1, part=p)
                    except Exception:
                        continue
                    meshes.append(SimpleNamespace(verts=[(v[0] + 64 * (bx - dbx), v[1], v[2] - 64 * (by - dby))
                                                         for v in bm.verts]))
        stock_pairs = set(M.weld_audit(meshes))
        ext = (64.0 * nx, 64.0 * ny)

        def on_frame(p):
            return (min(abs(p[0]), abs(p[0] - ext[0])) < 1e-3 or min(abs(p[2]), abs(p[2] + ext[1])) < 1e-3)
        sp_int = {q for q in stock_pairs if not (on_frame(q[0]) and on_frame(q[1]))}
        # the carry's pairs are in REGION frame (rot 0, shift 0): the same frame as the stock list above
        carry = [tuple(map(tuple, q)) for q in d["weld_pairs_region"]]
        inh = [q for q in carry if q in stock_pairs]
        print(f"  {d['donor']}+{nx}x{ny}: carry pairs {len(carry)} (gate interior {d['weld']['pairs']}); stock pairs "
              f"{len(stock_pairs)} ({len(sp_int)} off-frame); carry pairs ALSO in stock: {len(inh)}")
        for q in carry[:6]:
            print(f"    {'INHERITED' if q in stock_pairs else 'introduced'}  {q[0]} ~ {q[1]}")

    out = HERE / "isle_rect_study.json"
    for r in rows:
        r.pop("tweaks", None)
    out.write_text(json.dumps({"windows": {f"{k[0]}x{k[1]}": v[:20] for k, v in windows.items()},
                               "excise": rows, "dry": dry}, indent=1, default=str), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
