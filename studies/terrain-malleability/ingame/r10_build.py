"""BUILD + REGISTERED PREDICTIONS for in-game round 10 (2026-10-09): LAND -> SEA, `world-sink` -- a whole real island
turned into open sea, the way disc 4 removed Shimmering Island. Writes ONLY into staging folders under
ingame/out/r10_stage/ (gitignored), through the scratch mod folder FF9CustomMap-lab (emptied around every build; not
in FolderNames while this runs).

THE SITE: the largest island `world-sink --list` takes -- 4,813u2 of bare-coast land up to y 26.5 over five blocks
(9,6) (9,7) (10,5) (10,6) (10,7), no building, no entrance. Disc 4 redrew two of its blocks, so the deploy REPLAYS
the sink on disc 4's own ground.
THE FILES (the kit's CLI, as a user would run it):
  FULL  world-sink --at 679.033 -386.717          (Disc1 + the replay on Disc4)
  OLD   the same with --skip-mirror                (Disc1 only: what disc 4 gets with no mirror)
THE STAGES (lab, disc / world):
  d1_stock   -     1 / 9011   on foot: the read points stand on the island (stock heights)
  d1_sink    FULL  1 / 9011   on foot: the read points are open sea, y 0 (topograph 57)
  boat_stock -     1 / 9003   the Blue Narciss sails east from open sea toward the island: it STOPS at the island's
                              coast (stock near-shore water, topograph 56)
  boat_sink  FULL  1 / 9003   the same lane: it sails straight across where the island was
  d4_old     OLD   4 / 9008   on foot: disc 4 keeps its island (the read points read disc 4's stock heights)
  d4_sink    FULL  4 / 9008   on foot: open sea on disc 4 too
Read points: P1 near the island's summit, P2 at mid height, P3 on its lowland (heights from the sky ground query,
stock and staged). The boat lane: found by the boat simulator (veh_prep.boat_drive, the engine's own rules, with this
round's override meshes in every block): the eastbound lane crossing the most island where the sunk sea passes with no
slide.
Writes out/r10_build.json.
Run:  py studies/terrain-malleability/ingame/r10_build.py
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3_build as RB                                # noqa: E402  (the sky ground query, the lab)
import veh_prep as VP                                # noqa: E402  (the boat simulator, the spawn record)

STAGE = HERE / "out" / "r10_stage"
KIT = RB.KIT
LAB = "FF9CustomMap-lab"
AT = (679.033, -386.717)
BLOCKS = [(9, 6), (9, 7), (10, 5), (10, 6), (10, 7)]
STAGES = {   # name: (files, disc, kind)
    "d1_stock": (None, 1, "foot"),
    "d1_sink": ("FULL", 1, "foot"),
    "boat_stock": (None, 1, "boat"),
    "boat_sink": ("FULL", 1, "boat"),
    "d4_old": ("OLD", 4, "foot"),
    "d4_sink": ("FULL", 4, "foot"),
}
TICKS = 260
#: the party ON FOOT sinks into some ground: w_movementSinkArray row 1 (ff9.cs:19), by topograph class
#: (w_movementGetSliceHeight, ff9.cs:5636-5667) -- 36/37/38 canopy 1.171875 (vertical lane V3, round 5) and open sea 57
#: 1.3671875 (450 in the table; launch 1 of this round, run 20261009-151643, read it at all six sunk points)
WALK_SINK = {36: 1.171875, 37: 1.171875, 38: 1.171875, 57: 1.3671875}


def foot_y(g: dict) -> float:
    """Where the published y of a party standing at ground ``g`` reads: the ground minus its walk sink."""
    return round(g["y"] - WALK_SINK.get(g["topo"], 0.0), 4)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


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


def extras(files: Path | None, disc: int) -> dict | None:
    """{(bx, by): {part: path}} of a staged file set, for the boat simulator."""
    if files is None:
        return None
    out = {}
    for p in (files / "FF9_Data" / "WorldMap" / f"Disc{disc}").rglob("*.ff9mesh"):
        cell, part = p.stem.split("] ", 1)
        bx, by = (int(v) for v in cell.replace("Block[", "").split("]["))
        out.setdefault((bx, by), {})[part] = str(p)
    return out


def boat(x0, z0, ext) -> list:
    """veh_prep.boat_drive with this round's overrides in every block they cover."""
    orig = VP.boat_query

    def bq(x, z, origin_y, cache, extra):
        bx, by = int(math.floor(x / 64.0)), int(math.floor(-z / 64.0))
        cm = VP.cell_meshes(bx, by, 1, (ext or {}).get((bx, by)))
        lx, lz = x - bx * 64.0, z + by * 64.0
        h = cache.test((bx, by), cm["meshes"], lx, lz, origin_y)
        if h:
            return h
        for mi, (name, V, ids) in enumerate(cm["meshes"]):
            r = VP._hit_in_mesh(V, ids, lx, lz, origin_y, False, True)
            if r is None or r[0] == "VETO":
                continue
            cache.push((bx, by), mi, r[0])
            return {"y": r[1], "id": r[2], "topo": VP.topo(r[2]), "mesh": mi, "tri": r[0], "part": name,
                    "cached": False}
        return None
    VP.boat_query = bq
    try:
        return VP.boat_drive(x0, z0, 0.0, TICKS, extra={"_multi": True})
    finally:
        VP.boat_query = orig


def read_points(full: Path):
    """P1 (summit), P2 (mid), P3 (lowland): off the 4u lattice, on the island's Terrain on BOTH discs."""
    from ff9mapkit.world.placement import WALK_OK
    rows = []
    for (bx, by) in BLOCKS:
        for i in range(0, 64, 2):
            for j in range(0, 64, 2):
                x, z = bx * 64.0 + i + 0.37, -by * 64.0 - j - 0.63
                a, b = RB.ground(None, 1, x, z), RB.ground(None, 4, x, z)
                if a["part"] != "Terrain" or b["part"] != "Terrain" or abs(a["y"] - b["y"]) > 0.01:
                    continue
                f = RB.ground(full, 1, x, z)
                if f["part"] != "Sea4":
                    continue
                rows.append((a["y"], (round(x, 2), round(z, 2)), a["topo"] in WALK_OK))
    rows.sort()
    p1 = rows[-1]
    p2 = min(rows, key=lambda r: abs(r[0] - p1[0] / 2.0))
    p3 = next(r for r in rows if r[2] and r[0] > 1.0)
    return {"P1": p1[1], "P2": p2[1], "P3": p3[1]}


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    shutil.rmtree(STAGE, ignore_errors=True)
    files = STAGE / "files"
    base = ["world-sink", "--mod-folder", LAB, "--at", str(AT[0]), str(AT[1])]
    res = {"at": AT, "blocks": BLOCKS, "receipts": {}, "files": {}, "stages": {}}
    RB._clear_lab()
    res["receipts"]["dry_run"] = kit(base + ["--dry-run"])
    assert "disc 4: the replay passes its gates -- the deploy edits both discs" in res["receipts"]["dry_run"]
    for name, extra in (("FULL", []), ("OLD", ["--skip-mirror"])):
        RB._clear_lab()
        res["receipts"][name] = kit(base + extra)
        res["files"][name] = snapshot(files / name)
    RB._clear_lab()
    full, old = res["files"]["FULL"], res["files"]["OLD"]
    want = sorted(f"FF9_Data/WorldMap/Disc1/0_1/r{by}/Block[{bx}][{by}] {p}.ff9mesh"
                  for (bx, by) in BLOCKS for p in ("Sea4", "Terrain"))
    assert sorted(old) == want, sorted(old)
    assert sorted(full) == sorted(want + [k.replace("Disc1", "Disc4") for k in want]), sorted(full)
    assert all(full[k] == old[k] for k in old)
    assert "REPLAYED" in res["receipts"]["FULL"] and "REPLAYING" in res["receipts"]["FULL"]
    pts = read_points(files / "FULL")
    res["points"] = pts
    # the boat lane
    land = [(x, z) for (bx, by) in BLOCKS for i in range(64) for j in range(64)
            for x, z in [(bx * 64.0 + i + 0.5, -by * 64.0 - j - 0.5)] if RB.ground(None, 1, x, z)["part"] == "Terrain"]
    xs, zs = [p[0] for p in land], [p[1] for p in land]
    ext = extras(files / "FULL", 1)
    best = None
    for z in [round(v + 0.37, 2) for v in range(int(min(zs)) + 4, int(max(zs)) - 3, 2)]:
        x0 = round(min(xs) - 24.0, 2)
        q = RB.ground(None, 1, x0, z)
        if q["part"] != "Sea4" or q["topo"] != 57:
            continue
        span = sum(1 for p in land if abs(p[1] - z) < 0.5)
        if span < 20:
            continue
        sunk = boat(x0, z, ext)
        stock = boat(x0, z, None)
        if not sunk or not stock:
            continue
        s_prog = max(r["x"] for r in sunk) - x0
        t_prog = max(r["x"] for r in stock) - x0
        clean = all(r["slide"] == 0 for r in sunk) and s_prog >= (max(xs) - x0) + 10.0
        if clean and t_prog + 10.0 < max(xs) - x0 and (best is None or span > best["span"]):
            best = {"z": z, "start": [x0, z], "span": span, "stock_progress": round(t_prog, 2),
                    "stock_stop": [round(stock[-1]["x"], 2), round(stock[-1]["z"], 2)],
                    "stock_stop_topo_ahead": None, "sunk_progress": round(s_prog, 2),
                    "island_x": [round(min(xs), 1), round(max(xs), 1)]}
    assert best, "no clean boat lane"
    best["goal"] = round(best["island_x"][1] - best["start"][0] + 10.0, 2)
    best["record"] = VP.record_bytes(best["start"][0], 0.0, best["z"], 192, 74)
    res["boat"] = best
    for name, (fset, disc, kind) in STAGES.items():
        stage = (files / fset) if fset else None
        row = {"files": fset, "disc": disc, "kind": kind,
               "lab_files": sum(1 for k in (res["files"][fset] if fset else {}) if f"/Disc{disc}/" in k)}
        if kind == "foot":
            row["points"] = {k: dict(g, y_foot=foot_y(g)) for k, p in pts.items()
                             for g in [RB.ground(stage, disc, *p)]}
        else:
            row["boat"] = {"pass": fset is not None}
        res["stages"][name] = row
        print(f"{name:11s} {fset or '-':4s} disc {disc} {kind:4s} lab files read {row['lab_files']:2d}  "
              + ("  ".join(f"{k} y {v['y']} (on foot {v['y_foot']}) {v['part']} t{v['topo']}"
                           for k, v in row.get("points", {}).items())
                 or f"boat {'PASSES' if fset else 'STOPS'}"))
    print("boat lane:", {k: best[k] for k in ("start", "span", "stock_progress", "stock_stop", "sunk_progress",
                                                "island_x", "goal")})
    out = HERE / "out" / "r10_build.json"
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
