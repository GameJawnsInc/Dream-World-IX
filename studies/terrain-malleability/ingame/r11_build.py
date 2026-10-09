"""BUILD + REGISTERED PREDICTIONS for in-game round 11 (2026-10-09): LAND -> SEA IN SHALLOW WATER, `world-sink` on two
islands that stand in mid water. Writes ONLY into staging folders under ingame/out/r11_stage/ (gitignored), through the
scratch mod folder FF9CustomMap-lab (emptied around every build; not in FolderNames while this runs).

THE SITES (`world-sink --list`, land2sea/sh_q5_census.py):
  A  (1082.667, -1057.732), blocks (16,16) (17,16): a 448u2 island with a beach, in a lagoon of mid water (sea3). Its
     own beach water (32 sea1/sea2 tris) goes with it; its tiles re-band as mid water and six transition tiles.
  B  (278.667, -1006.732), block (4,15): a 601u2 island on the edge of a shelf, mid water to its north, deep sea to its
     south. Its tiles re-band as both, with the transition band (sea5) carried across where it stood.
THE FILES (the kit's CLI, as a user would run it, both sites into one folder):
  FULL  world-sink --at A; world-sink --at B          (Disc1 + the replay on Disc4)
  OLD   the same with --skip-mirror                    (Disc1 only: what disc 4 gets with no mirror)
THE STAGES (lab, disc / world):
  d1_stock   -     1 / 9011   on foot: the read points stand on the islands (stock heights)
  d1_sink    FULL  1 / 9011   on foot: the read points are water, each at its new class's walk sink
  boatA_stock / boatA_sink, boatB_stock / boatB_sink   - / FULL   1 / 9003   the Blue Narciss, eastbound across each
             island's lane: it STOPS at the island on stock, and sails across where it stood once sunk
  d4_old     OLD   4 / 9008   on foot: disc 4 keeps both islands
  d4_sink    FULL  4 / 9008   on foot: water on disc 4 too
Read points per site: the summit, and one point per new water class the sink lays on the island's footprint (site A
also one on its old beach); heights and classes from the sky ground query, stock and staged.
Writes out/r11_build.json.
Run:  py studies/terrain-malleability/ingame/r11_build.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3_build as RB                                # noqa: E402  (the sky ground query, the lab)
import veh_prep as VP                                # noqa: E402  (the boat simulator, the spawn record)
from r10_build import boat, extras, sha  # noqa: E402,F401  (round 10's multi-block boat wrapper)

STAGE = HERE / "out" / "r11_stage"
KIT = RB.KIT
LAB = "FF9CustomMap-lab"
SITES = {"A": (1082.667, -1057.732), "B": (278.667, -1006.732)}
STAGES = {   # name: (files, disc, kind, site)
    "d1_stock": (None, 1, "foot", None),
    "d1_sink": ("FULL", 1, "foot", None),
    "boatA_stock": (None, 1, "boat", "A"),
    "boatA_sink": ("FULL", 1, "boat", "A"),
    "boatB_stock": (None, 1, "boat", "B"),
    "boatB_sink": ("FULL", 1, "boat", "B"),
    "d4_old": ("OLD", 4, "foot", None),
    "d4_sink": ("FULL", 4, "foot", None),
}
#: the party ON FOOT sinks into some ground: w_movementSinkArray row 1 (ff9.cs:19) minus 100, /256, by topograph class
#: (w_movementGetSliceHeight, ff9.cs:5636-5667): 36-38 canopy 400, 53 150, 54 250, 55 200, 56 450, 57 450, 51 300,
#: 48 300, the rest 0. Round 10 read 57's at six points; 54 and 55 are this round's first reads.
WALK_SINK = {36: 1.171875, 37: 1.171875, 38: 1.171875, 53: 0.1953125, 54: 0.5859375, 55: 0.390625, 56: 1.3671875,
             57: 1.3671875, 51: 0.78125, 48: 0.78125}


def foot_y(g: dict) -> float:
    """Where the published y of a party standing at ground ``g`` reads: the ground minus its walk sink."""
    return round(g["y"] - WALK_SINK.get(g["topo"], 0.0), 4)


def kit(argv) -> str:
    p = subprocess.run([sys.executable, "-m", "ff9mapkit"] + argv, cwd=str(KIT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert p.returncode == 0, (argv, p.stdout[-3000:], p.stderr[-3000:])
    return p.stdout


def snapshot(dst: Path) -> dict:
    lab = RB.A.GAME / LAB
    out = {}
    for q in sorted(lab.rglob("*")):
        if not q.is_file() or q.name.startswith(".ff9world") or ".bak-" in q.name:
            continue
        rel = q.relative_to(lab).as_posix()
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(q, dst / rel)
        out[rel] = sha(q)
    return out


def site_blocks(site) -> list:
    from ff9mapkit.world import transplant as TR
    plan, rep = TR.sink_plan(SITES[site])
    return sorted({tuple(b) for b in rep["blocks"]} | set(plan)), rep


def read_points(full: Path, site: str, blocks) -> dict:
    """The summit, then one point per (part, class) the sink lays on the island's footprint (the highest of each), and
    for a beach island one on its old beach: off the 4u lattice, on the island on BOTH discs at the same height."""
    rows = []
    for (bx, by) in blocks:
        for i in range(0, 64, 2):
            for j in range(0, 64, 2):
                x, z = bx * 64.0 + i + 0.37, -by * 64.0 - j - 0.63
                a, b = RB.ground(None, 1, x, z), RB.ground(None, 4, x, z)
                if a["part"] not in ("Terrain", "Beach1") or a["part"] != b["part"] or abs(a["y"] - b["y"]) > 0.01:
                    continue
                f = RB.ground(full, 1, x, z)
                if f["part"] not in ("Sea3", "Sea4", "Sea5"):
                    continue
                rows.append((a["y"], (round(x, 2), round(z, 2)), a["part"], (f["part"], f["topo"])))
    assert rows, f"site {site}: no read point"
    rows.sort()
    pts = {f"{site}1": rows[-1][1]}
    seen = {rows[-1][3]}
    for r in reversed(rows):
        if r[3] not in seen and r[0] > 0.2:
            seen.add(r[3])
            pts[f"{site}{len(pts) + 1}"] = r[1]
    beach = [r for r in rows if r[2] == "Beach1" and r[0] > 0.1]
    if beach:
        pts[f"{site}{len(pts) + 1}"] = beach[-1][1]
    return dict(list(pts.items())[:4])


def boat_lane(full: Path, site: str, blocks) -> dict:
    """The eastbound lane across the island where stock stops the boat at the island and the sunk water carries it
    clean across (no slide before the goal, 10u past the island's east side), crossing the most island; started on
    sailable water (53/54/57) 24u west of it."""
    land = [(x, z) for (bx, by) in blocks for i in range(64) for j in range(64)
            for x, z in [(bx * 64.0 + i + 0.5, -by * 64.0 - j - 0.5)]
            if RB.ground(None, 1, x, z)["part"] in ("Terrain", "Beach1")
            and RB.ground(full, 1, x, z)["part"].startswith("Sea")]
    xs, zs = [p[0] for p in land], [p[1] for p in land]
    ext = extras(full, 1)
    best = None
    for z in [round(v + 0.37, 2) for v in range(int(min(zs)) + 2, int(max(zs)) - 1, 2)]:
        row = [p[0] for p in land if abs(p[1] - z) < 0.5]
        if len(row) < 8:
            continue
        x0 = round(min(row) - 24.0, 2)
        q = RB.ground(None, 1, x0, z)
        if not q["part"].startswith("Sea") or q["topo"] not in (53, 54, 57):
            continue
        sunk = boat(x0, z, ext)
        stock = boat(x0, z, None)
        if not sunk or not stock:
            continue
        s_prog = max(r["x"] for r in sunk) - x0
        t_prog = max(r["x"] for r in stock) - x0
        far = max(row) - x0
        # no slide on the way to the goal (past it the boat runs on into other coasts)
        clean = all(r["slide"] == 0 for r in sunk if r["x"] - x0 <= far + 10.0) and s_prog >= far + 10.0
        if clean and t_prog + 6.0 < far and (best is None or len(row) > best["span"]):
            best = {"z": z, "start": [x0, z], "span": len(row), "stock_progress": round(t_prog, 2),
                    "stock_stop": [round(stock[-1]["x"], 2), round(stock[-1]["z"], 2)],
                    "sunk_progress": round(s_prog, 2), "island_x": [round(min(row), 1), round(max(row), 1)],
                    "sunk_topos": sorted({r["topo"] for r in sunk})}
    assert best, f"site {site}: no clean boat lane"
    best["goal"] = round(best["island_x"][1] - best["start"][0] + 10.0, 2)
    best["record"] = VP.record_bytes(best["start"][0], 0.0, best["z"], 192, 74)
    return best


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    shutil.rmtree(STAGE, ignore_errors=True)
    files = STAGE / "files"
    res = {"sites": SITES, "receipts": {}, "files": {}, "stages": {}, "blocks": {}, "plans": {}}
    for s in SITES:
        blocks, rep = site_blocks(s)
        res["blocks"][s] = blocks
        res["plans"][s] = {k: rep[k] for k in ("tiles", "land_tris", "land_u2", "shore_tris", "bands", "band_flips",
                                               "fill_tris", "keel_to_open", "edge_welds")}
    RB._clear_lab()
    for s, at in SITES.items():
        out = kit(["world-sink", "--mod-folder", LAB, "--at", str(at[0]), str(at[1]), "--dry-run"])
        res["receipts"][f"dry_run_{s}"] = out
        assert "disc 4: the replay passes its gates -- the deploy edits both discs" in out, out[-2000:]
    for name, extra in (("FULL", []), ("OLD", ["--skip-mirror"])):
        RB._clear_lab()
        for s, at in SITES.items():
            res["receipts"][f"{name}_{s}"] = kit(["world-sink", "--mod-folder", LAB, "--at", str(at[0]), str(at[1])]
                                                 + extra)
        res["files"][name] = snapshot(files / name)
    RB._clear_lab()
    full, old = res["files"]["FULL"], res["files"]["OLD"]
    assert old and all("/Disc1/" in k for k in old), sorted(old)
    assert sorted(full) == sorted(list(old) + [k.replace("Disc1", "Disc4") for k in old]), sorted(full)
    assert all(full[k] == old[k] for k in old)
    for s in SITES:
        assert "REPLAYED" in res["receipts"][f"FULL_{s}"] or "copies this edit" in res["receipts"][f"FULL_{s}"]
    all_blocks = sorted({b for bs in res["blocks"].values() for b in bs})
    res["all_blocks"] = all_blocks
    pts = {}
    for s in SITES:
        pts.update(read_points(files / "FULL", s, res["blocks"][s]))
    res["points"] = pts
    res["boat"] = {s: boat_lane(files / "FULL", s, res["blocks"][s]) for s in SITES}
    for name, (fset, disc, kind, site) in STAGES.items():
        stage = (files / fset) if fset else None
        row = {"files": fset, "disc": disc, "kind": kind, "site": site,
               "lab_files": sum(1 for k in (res["files"][fset] if fset else {}) if f"/Disc{disc}/" in k)}
        if kind == "foot":
            row["points"] = {k: dict(g, y_foot=foot_y(g)) for k, p in pts.items()
                             for g in [RB.ground(stage, disc, *p)]}
        else:
            row["boat"] = {"pass": fset is not None}
        res["stages"][name] = row
        print(f"{name:12s} {fset or '-':4s} disc {disc} {kind:4s} lab files read {row['lab_files']:2d}  "
              + ("  ".join(f"{k} {v['part']} t{v['topo']} y {v['y']} (foot {v['y_foot']})"
                           for k, v in row.get("points", {}).items())
                 or f"boat {site} {'PASSES' if fset else 'STOPS'}"))
    for s, b in res["boat"].items():
        print(f"boat lane {s}:", {k: b[k] for k in ("start", "span", "stock_progress", "stock_stop", "sunk_progress",
                                                     "island_x", "goal", "sunk_topos")})
    out = HERE / "out" / "r11_build.json"
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
