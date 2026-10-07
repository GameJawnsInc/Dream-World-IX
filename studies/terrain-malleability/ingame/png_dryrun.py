"""OFFLINE DRY RUN of png_session.py against the harness FakeGame, with SYNTHETIC FRAMES -- proves the scenario's
world part runs (world_face, the lawn -> A -> lawn -> B routing, shots, receipts) and that every registered check
CAN FAIL: each hypothesis below paints the frames (and writes the receipts) of one possible world, and the judge
must pass the predicted world and fail exactly the check aimed at each wrong one.

Frames: png_judge.render_labels (the camera model calibrated on session 7, IoU 0.956) at A's stand for each pose,
colourised with the measured shading (k0 0.757) and fog (png_prep's fit), a per-shot sea texture jitter standing in
for the stock animation, and a player sprite inside PLAYER_BOX. Receipts: lines in Memoria.Prime's format appended
to the FakeGame's Memoria.log. The FakeGame's teleport keeps height (the stand-in for memory law 5); the dry run
re-grounds after each teleport the way the engine's w_movementChrInitSlice does (Ff9mkDebugMenu.cs:1851-1852).

    py studies/terrain-malleability/ingame/png_dryrun.py
    PNG_DRY_KEEP=predicted py ...png_dryrun.py   (also keeps that hypothesis's run dir under out/ for png_post.py)
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools"))
import numpy as np                                      # noqa: E402
from PIL import Image                                   # noqa: E402

from harness import Session                             # noqa: E402
from harness.fakegame import FakeGame                   # noqa: E402
import png_judge as J                                   # noqa: E402
import png_session as S                                 # noqa: E402
from png_prep import scene_from, PARTS                  # noqa: E402

SKY = np.array([205.0, 217.0, 247.0])
FOG = np.array([190.0, 205.0, 235.0])
SEA = np.array([95.0, 128.0, 155.0])
ISLET = np.array([93.0, 108.0, 54.0])                    # the islet lawn's mean atlas colour (png_prep inspection)
K0 = 0.757

HYPOTHESES = {
    # name: (vivid parts at A per shot index -> colour, receipts at A, the checks that MUST fail)
    "predicted":     ({"sea4": "Sea4"}, ["Terrain", "Sea4"], set()),
    "terrain_shows": ({"sea4": "Sea4", "terrain": "Terrain"}, ["Terrain", "Sea4"], {"T1"}),
    "sea3_shows":    ({"sea4": "Sea4", "sea3": "Sea3"}, ["Terrain", "Sea4"], {"S3"}),
    "nothing":       ({}, ["Terrain", "Sea4"], {"S4", "S4m", "S4s"}),
    "animated_away": ({"sea4": "Sea4", "_drop_k": 1}, ["Terrain", "Sea4"], {"S4", "S4s"}),
    "sea3_receipt":  ({"sea4": "Sea4"}, ["Terrain", "Sea4", "Sea3"], {"visit1"}),
}


def colourise(lab, dist, vivid, k, fog_fit, rng):
    h, w = lab.shape
    b = J.fog_b(np.where(np.isfinite(dist), dist, 1e3), fog_fit)[..., None]
    img = np.zeros((h, w, 3))
    for name, base in (("outside", SEA), ("sea1", SEA * 1.15), ("sea3", SEA * 1.08), ("sea4", SEA),
                       ("sea5", SEA * 1.04), ("terrain", ISLET), ("hole", SEA)):
        m = lab == J.LABELS.index(name)
        part = name if name != "outside" else None
        col = np.asarray(J.PNG_COLOR[vivid[part]], float) if (part in vivid and vivid.get("_drop_k") != k) else base
        tex = 1.0 + (rng.normal(0, 0.05, size=(h, w)) if name.startswith("sea") or name == "outside" else 0.0)
        o = (K0 * (1 - b[..., 0]) * tex)[..., None] * col[None, None, :] + b * FOG[None, None, :]
        img[m] = o[m]
    img[lab == J.LABELS.index("sky")] = SKY
    x0, x1, y0, y1 = (int(J.PLAYER_BOX[0] * w) + 12, int(J.PLAYER_BOX[1] * w) - 12,
                      int(J.PLAYER_BOX[2] * h) + 8, int(J.PLAYER_BOX[3] * h) - 8)
    img[y0:y0 + (y1 - y0) // 3, x0:x1] = (230, 190, 70)          # the sprite: hair, then a blue body
    img[y0 + (y1 - y0) // 3:y1, x0:x1] = (60, 80, 160)
    return np.clip(img, 0, 255).astype(np.uint8)


def receipt_lines(parts_tex):
    ts = "07.10.2026 12:00:00 |M| "
    lines = []
    for cell in (J.CELL_A, J.CELL_B):
        x, y = cell
        for part in ("Terrain", "Sea4"):
            rp = f"WorldMap/Disc1/0_1/r{y}/Block[{x}][{y}] {part}"
            lines.append(f"{ts}[WorldMeshOverride] loaded '{rp}' from FF9CustomMap-lab/{J.lab_relpath(cell, part, 'ff9mesh')}")
            if cell == J.CELL_A and part in parts_tex:
                lines.append(f"{ts}[WorldMeshOverride] loaded texture '{part}' from FF9CustomMap-lab/"
                             f"{J.lab_relpath(cell, part, 'png')}")
        if cell == J.CELL_A and "Sea3" in parts_tex:
            lines.append(f"{ts}[WorldMeshOverride] loaded texture 'Sea3' from FF9CustomMap-lab/"
                         f"{J.lab_relpath(cell, 'Sea3', 'png')}")
    return "\n".join(lines) + "\n"


def main():
    from ff9mapkit.world import extract as X
    prep = S.PREP
    donor = {p: X.read_block(J.DONOR[0], J.DONOR[1], disc=J.DISC, part=p) for p in PARTS}
    scene = scene_from(donor)
    gy = prep["stand_ground"]["y"]
    fog_fit = prep["shading_fog"]["fog_fit_a0_a1"]
    labels = {}
    for tag, brg in S.POSES:
        actor = (S.STAND["A"][0], gy, S.STAND["A"][1])
        labels[tag] = J.render_labels(scene, J.CELL_A, actor, brg, w=640, h=360, fov_setting=prep["fov_setting"])
    stands = {c: S.STAND[c] for c in ("A", "B")}

    def height(x, z):
        for c, (sx, sz) in stands.items():
            if abs(x - sx) < 12 and abs(z - sz) < 12:
                return gy
        return 3.2

    results = {}
    for name, (vivid, tex, must_fail) in HYPOTHESES.items():
        tmp = Path(tempfile.mkdtemp(prefix="png-dry-"))
        try:
            (tmp / "x64").mkdir()
            (tmp / "x64" / "FF9.exe").write_bytes(b"MZ")
            (tmp / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
            (tmp / "FF9CustomMap").mkdir()
            (tmp / "FF9CustomMap" / "DictionaryPatch.txt").write_text("FieldScene 6603 1 X X 6603\n", encoding="utf-8")
            fake = FakeGame(tmp)
            g = Session(game_path=tmp, run_dir=tmp / "run", save_dir=tmp / "saves", pid_probe=lambda: [],
                        launcher=lambda exe: fake.start(), boot_timeout=15.0, verbose=False)
            with g:
                g.newgame(settle=0)
                fake.overworld = {"speed": 1.0, "turn": 2.8125, "cam": 0.0, "lag": 3, "height": height}
                fake.world.update({"id": 9011, "x": S.LANDING[0], "z": S.LANDING[1]})
                fake._ow_y = 3.2
                fake.ui_state = "WorldHUD"
                g.wait_for(lambda s: s.on_world and s.world_x is not None, timeout=5.0, what="the stand-in world")
                rng = np.random.default_rng(7)
                orig_tp, orig_shot = g.teleport, g.shot

                def teleport(x, z, **kw):
                    st = orig_tp(x, z, **kw)
                    fake._ow_y = height(x, z)                   # the engine's InitSlice re-ground
                    return st

                def shot(nm, **kw):
                    p = orig_shot(nm, **kw)
                    tag, cell, k = nm.split("-") if nm.count("-") == 2 else ("P1", "A", "0")
                    lab, dist = labels.get(tag, labels["P1"])
                    v = vivid if cell == "A" else {}
                    img = colourise(lab, dist, v, int(k) if k.isdigit() else 0, fog_fit, rng)
                    Image.fromarray(np.repeat(np.repeat(img, 2, 0), 2, 1)).save(p)
                    return p

                g.teleport, g.shot = teleport, shot
                S._RECORD.update({"visits": [], "poses": {}, "notes": [], "reload": {}})
                mark = S.log_mark(g)
                with open(tmp / "x64" / "Memoria.log", "a", encoding="utf-8") as fh:
                    fh.write(receipt_lines(tex))
                for tag, brg in S.POSES:
                    S.do_pose(g, tag, brg)
                S.take_receipts(g, "visit1", mark)
                checks = J.evaluate(S._RECORD, prep)
            failed = {w.split(" ")[0].rstrip(":") for ok, w, _ in checks if not ok}
            ok = failed == must_fail
            results[name] = {"ok": ok, "failed": sorted(failed), "must_fail": sorted(must_fail),
                             "n_checks": len(checks),
                             "counts": {t: {c: [(s["magenta"], s["red"], s["lime"]) for s in J._shots(S._RECORD, t, c)]
                                            for c in ("A", "B")} for t, _ in S.POSES}}
            print(f"{'OK  ' if ok else 'BAD '} {name:14s} failed {sorted(failed)} (must fail {sorted(must_fail)})")
        finally:
            keep = os.environ.get("PNG_DRY_KEEP")
            if keep and keep == name:
                dst = J.OUT / f"png_dryrun_{name}"
                shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(tmp / "run", dst)
                print(f"     kept the run dir as {dst} (png_post.py can re-score it)")
            shutil.rmtree(tmp, ignore_errors=True)
    (J.OUT / "png_dryrun.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    bad = [k for k, v in results.items() if not v["ok"]]
    print("dry run:", "ALL hypotheses judged as registered" if not bad else f"MISJUDGED {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
