"""In-game ROUND 5 (2026-10-08): defects 19 and 20 in game, on the Black Mage Village cell (22,14). DEPLOYS into the
scratch mod folders FF9CustomMap-lab and FF9CustomMap-lab2 ONLY (owner's go 2026-10-08, "in-game session"; for the
round FolderNames starts "FF9CustomMap-lab", "FF9CustomMap-lab2", so lab2 is parsed BEFORE the lab). Both start
EMPTY; this scenario swaps r5_build's stages in while the player is inside field 6603 (FARSHORE), so each walk out
is a fresh world load: the engine re-reads Environment.txt and File.Exists-checks every override then.
RUN:   py tools/play.py studies/terrain-malleability/ingame/r5_session.py --label r5-forms

ROUTE: newgame -> warp 6603 -> walk out (round 3's FARSHORE exit) -> the world at scenario 0 -> teleport to five
read points by (22,14) -> world_warp 6603 -> swap -> walk out -> ... (r5_build.py: the stages and why).

REGISTERED PREDICTIONS (out/r5_build.json; tolerance 0.15, round 1's):
  every stage: the four off-lattice points m1-m4 read the stage's ground source, and the control (23u out) reads
  29.2506 -- sources: STOCK (form 1 = form 2 here), T27 (the kit's form-1 Terrain, flattened to 27), T2_26 (a
  Terrain2 flattened to 26, round 1's file):
  stock STOCK; d19_t_f1 T27; d19_t_f2 STOCK (DEFECT 19: the form-1 edit vanishes when the place switches);
  d19_t_t2_f2 T2_26 (a Terrain2 keeps the edit in form 2); d20_clear T27 (DEFECT 20 FIX: the lab's Clear drops
  lab2's true); d20_lower T2_26 (lab2 alone is read); d20_or T2_26 (the old kit output: OR keeps lab2's true);
  d20_clean T2_26 (Memoria's documented `Clean` does nothing); d20_clear2/3 T27 (between them, so no two
  neighbouring stages share a prediction across the d20 contrasts)
  every stage: Memoria.log binds each staged .ff9mesh from the lab on that world load
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent / "tools"))
sys.path.insert(0, str(HERE))
from harness import HarnessError                      # noqa: E402
from harness.logs import read_from                    # noqa: E402

import r3_session as R3                                # noqa: E402  (calibrate, here, FARSHORE's exit)

GAME = R3.GAME
LAB, LAB2 = GAME / "FF9CustomMap-lab", GAME / "FF9CustomMap-lab2"
BUILD = json.loads((HERE / "out" / "r5_build.json").read_text(encoding="utf-8"))
FILES = HERE / "out" / "r5_stage" / "files"
STAGES = list(BUILD["stages"])
TOL = 0.15
LOADED = re.compile(r"\[WorldMeshOverride\] loaded '([^']*Block\[22\]\[14\][^']*)' from (.+)$", re.M)
_RECORD: dict = {"build": {k: {kk: v.get(kk) for kk in ("rel", "sha", "via")} for k, v in BUILD["files"].items()},
                 "stages": []}


def _save(g):
    try:
        (g.run_dir / "r5_forms.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[r5] could not write the record: {err}")


def _empty(root: Path):
    root.mkdir(exist_ok=True)
    for child in root.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()


def set_labs(stage: str | None) -> dict:
    """Empty both labs, then place the stage's files (None = leave them empty). Every placed file is checked
    byte for byte against the build. Returns {lab: {relpath: sha}}."""
    placed = {}
    for root, key in ((LAB, "lab"), (LAB2, "lab2")):
        _empty(root)
        placed[key] = {}
        for name in (BUILD["stages"][stage][key] if stage else ()):
            rel = BUILD["files"][name]["rel"]
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(FILES / name / rel, dst)
            got = hashlib.sha256(dst.read_bytes()).hexdigest()
            if got != BUILD["files"][name]["sha"]:
                raise HarnessError(f"r5: {key} does not hold {name} byte for byte")
            placed[key][rel] = got
    return placed


def to_field(g, first: bool):
    if first:
        g.newgame()
        g.warp(R3.FARSHORE)
    else:
        g.world_warp(R3.FARSHORE)
    g.wait_playable(timeout=60)
    if g.state.field_id != R3.FARSHORE:
        raise HarnessError(f"r5: expected field {R3.FARSHORE}, found {R3.here(g)}")


def walk_out(g):
    g.wait_frames(45)
    R3.calibrate(g, [R3.FS_DOOR], lambda: g.warp(R3.FARSHORE))
    g.walk_to(*R3.FS_EXIT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()


def loads_since(mark) -> list:
    out = []
    for path, offset in mark.values():
        try:
            text = read_from(Path(path), int(offset))
        except OSError:
            continue
        out += [(m.group(1), m.group(2).strip()) for m in LOADED.finditer(text)]
    return out


def read_points(g) -> dict:
    rows = {}
    for k, p in BUILD["points"].items():
        g.teleport(*p)
        g.world_settle()
        g.wait_frames(20)
        rows[k] = g.state.world_y
    return rows


def run(g):
    g.note("r5_session: defects 19 and 20 on the Black Mage Village cell (22,14)")
    mark0 = g.log_mark()
    try:
        for i, stage in enumerate(STAGES):
            rec = {"stage": stage, "source": BUILD["stages"][stage]["ground"]}
            _RECORD["stages"].append(rec)
            to_field(g, first=i == 0)
            rec["placed"] = set_labs(None if stage == "stock" else stage)
            mark = g.log_mark()
            walk_out(g)
            rec["at"] = R3.here(g)
            rec["loads"] = loads_since(mark)
            rec["read"] = read_points(g)
            pred = BUILD["predict"][stage]
            rec["predict"] = pred
            ok = all(rec["read"][k] is not None and abs(rec["read"][k] - pred[k]) <= TOL for k in pred)
            g.check(ok, f"{stage}: the read points stand on {rec['source']} ground",
                    json.dumps({k: [rec["read"][k], pred[k]] for k in pred}))
            meshes = [rel for rel in rec["placed"]["lab"] if rel.endswith(".ff9mesh")]
            bound = all(any(key.endswith(Path(rel).stem) and re.search(r"FF9CustomMap-lab[\\/]", src)
                            for key, src in rec["loads"]) for rel in meshes)
            g.check(bound, f"{stage}: Memoria.log bound every staged lab mesh on this world load "
                           f"({len(meshes)} file(s))", json.dumps(rec["loads"]))
            if stage in ("d19_t_f1", "d19_t_f2", "d19_t_t2_f2"):
                g.teleport(*BUILD["points"]["m1"])
                g.world_settle()
                g.wait_frames(90)
                g.shot(f"r5-{stage}")
            _save(g)
    finally:
        set_labs(None)
        try:
            _RECORD["exceptions"] = [str(e) for e in g.exceptions_since(mark0)][:20]
        except Exception as err:                                        # noqa: BLE001
            _RECORD["exceptions_error"] = repr(err)
        _save(g)
