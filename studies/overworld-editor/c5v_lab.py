"""The multi-block carry, the candidates walked: the crystal reef and the terminus pair, carried by the World tab's
transplant tool into one draft, promoted, stood on -- so donors.toml can qualify them as the comma was (c5u_lab).

    py studies/overworld-editor/c5v_lab.py build   # the tool accepts each unit; identity; predictions
    py studies/overworld-editor/c5v_lab.py run     # reach the world; before / promote / reload / after; quit

THE EDITOR'S PATH (as c5u_lab): the real TransplantTool with its real runner against the real install, each unit
picked, turned and fitted to a click in free open ocean (UNITS: the targets measured free on the folder as it stands),
Check (`--size --shift 0,0 --dry-run`) then Accept into ONE fresh draft, one after the other. Then the same commands
typed by hand into a second draft (I1) and the two [[transplant]] rows composed into a third (I2), every world file
compared.

REGISTERED PREDICTIONS (c5v_prep.json, written by `build` before the game opens; tolerance 0.15), per unit U:
  N0-U before the promote, at U's probe (its carried land's highest walkable point) the party is in the open sea
       (y <= 0.05);
  N1   after the promote and the reload, at the Landing Site K (the control) it stands where it stood;
  N2-U at U's probe it stands on the carried land, at the height point_info predicts with the draft in place;
  N3-U Memoria.log: the reload loaded U's probe block from FF9CustomMap-world.
The party is put back on K, and the game is closed at the end (the harness quit).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lab as C1                                                    # noqa: E402  (the paths, the ground probe)
import c2_lab as C2                                                    # noqa: E402  (the shell steps, the promote)
import c5u_lab as U                                                    # noqa: E402  (the world hash, the kit call)

GAME, KIT, REPO = C1.GAME, C1.KIT, C1.REPO
SOURCE = "FF9CustomMap-world"
#: (name, donor, size, rot, target cell): the targets measured free and dry-run clean on the live folder
UNITS = [("crystal-reef", (6, 4), (2, 2), 0, None), ("terminus-pair", (10, 17), (1, 2), 0, None)]
OUT = HERE / "out" / "c5v_lab"
PREP = HERE / "out" / "c5v_prep.json"
RESULT = HERE / "out" / "c5v_result.json"
TOL = 0.15


def _drive_tool(drafts: Path, units) -> dict:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldforest import QProcessRunner
    from ff9mapkit.workspace.worldtransplant import TransplantTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    pal = pick_palette("dark")
    runner = QProcessRunner()
    argvs = []
    real_start = runner.start

    def start(argv, cwd, done):
        argvs.append([str(a) for a in argv])
        real_start(argv, cwd, done)
    runner.start = start
    tool = TransplantTool(pal, WorldView3DPanel(pal), game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE,
                          runner=runner, drafts_root=drafts)
    tool.open_tool()

    def pump(until, sec):
        t = time.time()
        while time.time() - t < sec:
            app.processEvents()
            if until():
                return True
            time.sleep(0.02)
        return False
    steps = []
    for name, donor, size, rot, cell in units:
        tool.donor_box.setCurrentIndex(tool.donor_box.findData("{},{}@{}x{}".format(*donor, *size)))
        tool.rot_box.setCurrentIndex(tool.rot_box.findData(rot))
        assert pump(lambda: tool._ix is not None and tool.donor() in tool._outlines, 300), tool.verdict_lbl.text()
        tw, th = (size[1], size[0]) if (rot // 90) % 2 else size
        tool.place(64.0 * (cell[0] + tw / 2.0), -64.0 * (cell[1] + th / 2.0), 0.0)
        assert tool.cell() == tuple(cell), (name, tool.cell())
        t0 = time.time()
        assert pump(lambda: tool._current_verdict() is not None, 300), tool.verdict_lbl.text()
        check = {"text": tool.verdict_lbl.text(), "s": round(time.time() - t0, 1)}
        assert tool.accept_btn.isEnabled(), (name, tool.verdict_lbl.text())
        t0 = time.time()
        tool.accept_btn.click()
        assert pump(lambda: tool._job is None and tool.center is None, 600), tool.verdict_lbl.text()
        steps.append({"unit": name, "check": check, "accepted": tool.verdict_lbl.text(),
                      "accept_s": round(time.time() - t0, 1), "argv": argvs[-1]})
    return {"steps": steps, "draft": str(tool.draft())}


def build():
    from ff9mapkit.world import draft as D, recipe as RC, render as R, transplantedit as TE
    room = json.loads((HERE / "out" / "c5v_room.json").read_text(encoding="utf-8"))
    units = [(n, d, s, room[n]["rot"], tuple(room[n]["cell"])) for n, d, s, _r, _c in UNITS]
    if OUT.exists():
        shutil.rmtree(OUT)
    drive = _drive_tool(OUT / "drafts", units)
    draft = Path(drive["draft"])
    for st in drive["steps"]:
        print(f"tool: {st['unit']}: check {st['check']['s']} s: {st['check']['text']}\n  accept {st['accept_s']} s")
    hand = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "hand")
    rows = []
    for st in drive["steps"]:
        argv = st["argv"][3:]
        i = argv.index("--report-json")
        argv = argv[:i] + argv[i + 2:]
        U._kit([str(hand) if a == drive["draft"] else a for a in argv])
        verb = argv[argv.index("world-transplant"):]
        rows.append(RC.row_for(["-" if a == drive["draft"] else a for a in verb]))
    recipe = OUT / "units.toml"
    recipe.write_text(RC.dumps(rows), encoding="utf-8")
    composed = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "composed")
    U._kit(["--game", str(GAME), "world-fuse", str(recipe), "--mod-folder", str(composed)])
    ed, hd, cd = U._world(draft), U._world(hand), U._world(composed)
    d1 = sorted(k for k in set(ed) | set(hd) if ed.get(k) != hd.get(k))
    d2 = sorted(k for k in set(ed) | set(cd) if ed.get(k) != cd.get(k))
    print(f"I1 hand: {'IDENTICAL' if not d1 else 'DIFFERS ' + str(d1[:6])}; I2 recipe: "
          f"{'IDENTICAL' if not d2 else 'DIFFERS ' + str(d2[:6])}; over {len(ed)} world files; the draft edited "
          f"{len(D.edits(draft))}")
    assert not d1 and not d2
    names = [p.name for p in R.game_stack(GAME)]
    live = R.RenderSite(cells=(), disc=1, game=GAME, stack=tuple(GAME / n for n in names))
    with_draft = R.RenderSite(cells=(), disc=1, game=GAME,
                              stack=tuple(draft if n == SOURCE else GAME / n for n in names))
    dnames = [draft.name if n == SOURCE else n for n in names]
    targets = []
    for name, donor, size, rot, cell in units:
        land = TE.placed(TE.donor_land(donor, size=size, game=GAME), donor, cell, rot=rot, size=size)
        cands = sorted(((t[:, 1].mean(), tuple(t[:, [0, 2]].mean(axis=0))) for t in land), reverse=True)
        probe, surface = None, None
        for _y, (x, z) in cands:
            x, z = round(x + 0.37, 2), round(z - 0.29, 2)
            g, w = C1._ground(with_draft, x, z, dnames), C1._ground(live, x, z, names)
            if g.get("part") != "Terrain" or (w.get("stand_y") or 0.0) > 0.05:
                continue
            if g.get("walkable"):
                probe = (x, z)
                break
            surface = surface or (x, z)                        # the highest carried surface, walkable or not
        if probe is None:
            # THE REEF: its land is topograph 59 (the crystal shards), nowhere walkable. Its acceptance is the geometry:
            # the teleport grounds by a ray from the sky, so the party lands on the shard surface at its height
            assert surface is not None, f"no carried surface over open sea on {name}"
            probe = surface
        targets.append((name, probe))
    targets.append(("K", C1.CONTROL[1:]))
    rec_t = []
    for key, (x, z) in targets:
        g, w = C1._ground(with_draft, x, z, dnames), C1._ground(live, x, z, names)
        walk = bool(g.get("walkable"))
        rec_t.append({"key": key, "x": round(x, 3), "z": round(z, 3),
                      "predict_y": g["stand_y"] if walk else g.get("y"), "walkable": walk, "part": g.get("part"),
                      "topograph": g.get("topograph"), "live_y": w["stand_y"], "live_part": w.get("part"),
                      "block": [int(x // 64) % 24, int(-z // 64)]})
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "units": [list(u) for u in units], "draft": str(draft),
           "tool": drive, "I1": {"identical": not d1, "files": len(ed)}, "I2": {"identical": not d2},
           "stack": names, "tolerance": TOL, "targets": rec_t}
    PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for t in rec_t:
        print(f"  {t['key']} at {t['x']}, {t['z']} (block {t['block']}): with the draft y {t['predict_y']:.3f} "
              f"({t['part']} topograph {t['topograph']}); live y {t['live_y']:.3f} ({t['live_part']})")
    print(f"-> {PREP}")


def run():
    prep = json.loads(PREP.read_text(encoding="utf-8"))
    py = sys.executable
    log = GAME / "Memoria.log"
    tg = {t["key"]: t for t in prep["targets"]}
    units = [t["key"] for t in prep["targets"] if t["key"] != "K"]
    K = (tg["K"]["x"], tg["K"]["z"])
    rec = {"prep_t": prep["t"], "steps": {}}

    def tele(key, at):
        r = C2._sh([py, "tools/world_teleport.py", f"{at[0]:.2f}", f"{at[1]:.2f}", "--shot", f"c5v-{key}"], 300)
        rec["steps"][key] = C2._last_json(r)

    r = C2._sh([py, "tools/play.py", HERE / "a1_reach.py", "--keep-open", "--label", "c5v-reach"], 900)
    rec["reach_rc"] = r.returncode
    try:
        if r.returncode == 0:
            for u in units:
                tele(f"N0-{u}", (tg[u]["x"], tg[u]["z"]))
            tele("K0-before", K)
            rec["promote"] = C2._promote(prep)
            if rec["promote"]["rc"] == 0:
                mark = log.stat().st_size if log.is_file() else 0
                r = C2._sh([py, "tools/world_reload.py", f"{K[0]:.2f}", f"{K[1]:.2f}", "--shot", "c5v-N1-reload"], 600)
                rec["steps"]["N1-reload"] = C2._last_json(r)
                text = log.read_bytes()[mark:].decode("utf-8", "replace") if log.is_file() else ""
                rec["log"] = {u: [ln.strip() for ln in text.splitlines() if "WorldMeshOverride" in ln
                                  and "Block[{}][{}]".format(*tg[u]["block"]) in ln] for u in units}
                for u in units:
                    tele(f"N2-{u}", (tg[u]["x"], tg[u]["z"]))
                tele("K1-back", K)
    finally:
        C2._sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", "c5v-quit"], 300)   # close the game
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")

    def y(key):
        return (rec["steps"].get(key) or {}).get("world_y")
    ran = (rec.get("promote") or {}).get("rc") == 0
    verdict = {"N1": ran and y("N1-reload") is not None and abs(y("N1-reload") - tg["K"]["predict_y"]) <= TOL}
    for u in units:
        verdict[f"N0-{u}"] = y(f"N0-{u}") is not None and y(f"N0-{u}") <= 0.05
        verdict[f"N2-{u}"] = ran and y(f"N2-{u}") is not None and abs(y(f"N2-{u}") - tg[u]["predict_y"]) <= TOL
        lines = (rec.get("log") or {}).get(u) or []
        verdict[f"N3-{u}"] = ran and len(lines) >= 1 and all(SOURCE in ln and "loaded" in ln for ln in lines)
    rec["verdict"] = verdict
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for k in [f"N0-{u}" for u in units] + ["N1-reload"] + [f"N2-{u}" for u in units] + ["K1-back"]:
        key = k.split("-", 1)[1] if k.startswith(("N0-", "N2-")) else "K"
        key = key if key in tg else "K"
        print(f"{k}: y {y(k)}  (live {tg[key]['live_y']:.3f}, with the draft {tg[key]['predict_y']:.3f})")
    print(verdict, "promote", (rec.get("promote") or {}).get("seconds"), "s")
    print(f"-> {RESULT}")


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["build"]:
        build()
    elif cmd == ["run"]:
        run()
    else:
        raise SystemExit(__doc__)
