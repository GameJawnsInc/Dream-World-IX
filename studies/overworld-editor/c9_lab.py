"""Rung C9 on real bytes and in game: a placed hill picked, moved and retuned; the steps after it put back.

    py studies/overworld-editor/c9_lab.py build   # three hills, then the first edited; identity; predictions
    py studies/overworld-editor/c9_lab.py run     # reach; promote the first draft; walk; revert; promote the edit; walk

THE EDITOR'S PATH: the real RecipeBar and HillTool (workspace/worldrecipe.py, worldhill.py) with their real runners
against the real install, wired as the World tab wires them (WorldDoc._edit_step: the bar's Edit opens the card on
the step's row). On FF9CustomMap-world's deployed lawn, nearest the Landing Site:
  H1 at A, H2 at B (44-80u from A: its read window holds A's block, so an edit of H1 makes it run again),
  H3 at C (300u+ away: its window holds nothing H1 touches, so it is replayed from its record);
then H1 is picked by a click at A, opened with Edit, moved to A' and lowered, and accepted. Two drafts: ORIG (the three
as placed, a copy made before the edit) and the edited one.
  I1: the edited draft == `world-fuse` of the edited recipe (H1', H2, H3) composed onto a fresh draft;
  I2: H3's files in the edited draft == its files in ORIG (the replay), H2 ran again (a world-fuse job).

REGISTERED PREDICTIONS (c9_prep.json, written by `build` before the game opens; tolerance 0.15):
  N0 before anything, at A the party stands on the lawn, at its live height;
  N1 ORIG promoted, after the reload: at A the top of H1 (point_info with ORIG in place); K the control;
  N2 ORIG reverted and the EDITED draft promoted, after the reload: at A the lawn again (the hill moved away), at A'
     the top of H1' (lower), at B H2's top, at C H3's top (all point_info with the edited draft in place);
  N3 Memoria.log: the second reload loaded A''s block from FF9CustomMap-world.
The party is put back on K, and the game is closed at the end (the harness quit).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lab as C1                                                    # noqa: E402  (the paths, the ground probe)
import c2_lab as C2                                                    # noqa: E402  (the shell steps, the promote)

GAME, KIT, REPO = C1.GAME, C1.KIT, C1.REPO
SOURCE = "FF9CustomMap-world"
HEIGHT, RADIUS = 4.2, 18.0                                             # the verb's defaults: the proven hill
NEW_HEIGHT = 3.6                                                       # the edit lowers it (a retune) as it moves
OUT = HERE / "out" / "c9_lab"
PREP = HERE / "out" / "c9_prep.json"
RESULT = HERE / "out" / "c9_result.json"
TOL = 0.15


def _world(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / "FF9_Data" / "WorldMap").rglob("Block*")
            if ".bak-" not in p.name and p.suffix in (".ff9mesh", ".txt")}


def _lawful(ix, near, *, lo=0.0, hi=1e9, away=(), height=HEIGHT, step=8.0):
    """The lawful hill centre (the card's own preview) nearest ``near`` among the deployed lawn's grid points whose
    distance from ``near`` lies in [lo, hi] and that keep 44u from every point of ``away``."""
    from ff9mapkit.world import hilledit as HE
    fam = HE._fam(ix)
    mains = ix.cent[fam == "main"]
    cands = sorted({(round(x / step) * step, round(z / step) * step) for x, z in mains[::5]},
                   key=lambda c: math.dist(c, near))
    for c in cands:
        d = math.dist(c, near)
        if lo <= d <= hi and all(math.dist(c, a) >= 44.0 for a in away) and HE.preview(ix, c, height, RADIUS)["ok"]:
            return c
    raise AssertionError(f"no lawful hill spot {lo}-{hi}u from {near}")


class Lab:
    """The bar and the card, wired as WorldDoc wires them (on_edit opens the card on the row)."""

    def __init__(self, drafts):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        from ff9mapkit.editor.theme import pick_palette
        from ff9mapkit.workspace.worldforest import QProcessRunner
        from ff9mapkit.workspace.worldhill import HillTool
        from ff9mapkit.workspace.worldrecipe import RecipeBar
        from ff9mapkit.workspace.worldview3d import WorldView3DPanel
        pal = pick_palette("dark")
        self.argvs = []

        def logged():
            r = QProcessRunner()
            real = r.start

            def start(argv, cwd, done):
                self.argvs.append([str(a) for a in argv])
                real(argv, cwd, done)
            r.start = start
            return r
        self.tool = HillTool(pal, WorldView3DPanel(pal), game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE,
                             runner=logged(), drafts_root=drafts, on_changed=lambda d: self.bar.refresh())
        self.bar = RecipeBar(pal, game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE, runner=logged(),
                             drafts_root=drafts, on_changed=lambda d: self.tool.island_changed(),
                             on_edit=self._edit, ask=lambda t, x: True)

    def _edit(self, row, label):
        self.tool.open_tool()
        self.tool.edit_row(row, label=label, on_accepted=self.bar.edit_accepted, on_cancel=self.bar.cancel_edit)

    def pump(self, until, sec):
        t = time.time()
        while time.time() - t < sec:
            self.app.processEvents()
            if until():
                return True
            time.sleep(0.02)
        return False

    def soup(self):
        assert self.pump(lambda: self.tool._ix is not None, 300), self.tool.verdict_lbl.text()
        return self.tool._ix

    def place(self, center, height=HEIGHT):
        tool = self.tool
        tool.height_spin.setValue(height)
        tool.radius_spin.setValue(RADIUS)
        tool.place(*center, 0.0)
        t0 = time.time()
        assert self.pump(lambda: tool._current_verdict() is not None, 300), tool.verdict_lbl.text()
        check_s = time.time() - t0
        assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
        t0 = time.time()
        tool.accept_btn.click()
        return round(check_s, 1), t0


def build():
    from ff9mapkit.world import draft as D, recipe as RC, render as R
    if OUT.exists():
        shutil.rmtree(OUT)
    lab = Lab(OUT / "drafts")
    tool, bar = lab.tool, lab.bar
    tool.open_tool()
    k = C1.CONTROL[1:]
    A = _lawful(lab.soup(), k)
    timings = {}
    for key, at in (("H1", A), ("H2", None), ("H3", None)):
        ix = lab.soup()
        if key == "H2":
            at = B = _lawful(ix, A, lo=44.0, hi=80.0, away=(A,))
        elif key == "H3":
            at = C = _lawful(ix, A, lo=300.0, away=(A, B))
        check_s, t0 = lab.place(at)
        assert lab.pump(lambda: tool._job is None and tool.center is None, 600), tool.verdict_lbl.text()
        timings[key] = {"at": at, "check_s": check_s, "accept_s": round(time.time() - t0, 1)}
        print(f"{key} at {at}: check {check_s} s, accept {timings[key]['accept_s']} s")
    tool.close_tool()
    draft = tool.draft()
    orig = OUT / "orig" / draft.name                     # ORIG: the three as placed (a draft of its own)
    shutil.copytree(draft, orig)
    rows0 = D.recipe_rows(draft)
    # the edit: a click at A picks H1; Edit; the card moves it to A' and lowers it; Accept; the bar puts H2, H3 back
    picked = bar.pick(A[0] + 1.3, A[1] - 0.7)
    assert picked == 0, (picked, bar.status_lbl.text())
    picked_text = bar.status_lbl.text()
    t0 = time.time()
    bar.edit_btn.click()
    t_open = round(time.time() - t0, 2)
    assert tool.editing(), bar.status_lbl.text()
    ix = lab.soup()                                      # the draft as it was before H1 (H1, H2, H3 lifted out)
    A2 = _lawful(ix, A, lo=12.0, hi=60.0, away=(B,), height=NEW_HEIGHT)   # a move, clear of H2
    n_jobs = len(lab.argvs)
    check_s, t0 = lab.place(A2, NEW_HEIGHT)
    assert lab.pump(lambda: bar._edit is None and tool._job is None, 900), bar.status_lbl.text()
    t_edit = round(time.time() - t0, 1)
    edited_text = bar.status_lbl.text()
    jobs = [a[5] for a in lab.argvs[n_jobs:]]
    print(f"picked: {picked_text}\nedit: H1 to {A2} h{NEW_HEIGHT}: check {check_s} s, accept + put back {t_edit} s; "
          f"jobs {jobs}\n  {edited_text}")
    rows = D.recipe_rows(draft)
    assert rows[1:] == rows0[1:] and rows[0]["center"] == [float(A2[0]), float(A2[1])], rows
    # I1: the edited draft == world-fuse of the edited recipe onto a fresh draft of the folder
    recipe = OUT / "edited.toml"
    recipe.write_text(RC.dumps(rows), encoding="utf-8")
    composed = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "composed")
    t0 = time.time()
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "--game", str(GAME), "world-fuse", str(recipe),
                        "--mod-folder", str(composed)], cwd=KIT, capture_output=True, text=True, timeout=1800)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
    t_compose = round(time.time() - t0, 1)
    ed, cd, od = _world(draft), _world(composed), _world(orig)
    d1 = sorted(x for x in set(ed) | set(cd) if ed.get(x) != cd.get(x))
    h = D.history(draft)
    h3 = {rel for rel in h["steps"][2]["after"]}
    d2 = sorted(x for x in h3 if ed.get(x) != od.get(x))
    print(f"I1 recipe: {'IDENTICAL' if not d1 else 'DIFFERS ' + str(d1[:6])} over {len(ed)} world files "
          f"(compose {t_compose} s); I2 H3 replayed: {'IDENTICAL' if not d2 else 'DIFFERS ' + str(d2[:6])} over "
          f"{len(h3)} files; H2 ran again: {jobs.count('world-fuse') == 1}")
    assert not d1 and not d2 and jobs.count("world-fuse") == 1 and "1 as they were, 1 composed again" in edited_text
    names = [p.name for p in R.game_stack(GAME)]

    def site(folder):
        stack = tuple(GAME / n for n in names) if folder is None else \
            tuple(folder if n == SOURCE else GAME / n for n in names)
        return R.RenderSite(cells=(), disc=1, game=GAME, stack=stack), \
            [n if folder is None or n != SOURCE else folder.name for n in names]
    live, ln = site(None)
    s_orig, on = site(orig)
    s_edit, en = site(draft)

    def off(c):
        return round(c[0] + 0.37, 2), round(c[1] - 0.29, 2)  # off the 4u lattice, on the top

    targets = []
    for key, at, s, sn in (("A1", off(A), s_orig, on), ("K", k, s_orig, on), ("A2", off(A), s_edit, en),
                           ("A'", off(A2), s_edit, en), ("B", off(B), s_edit, en), ("C", off(C), s_edit, en)):
        g, w = C1._ground(s, *at, sn), C1._ground(live, *at, ln)
        targets.append({"key": key, "x": at[0], "z": at[1], "predict_y": g["stand_y"], "part": g.get("part"),
                        "topograph": g.get("topograph"), "live_y": w["stand_y"],
                        "block": [int(at[0] // 64) % 24, int(-at[1] // 64)]})
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "height": HEIGHT, "new_height": NEW_HEIGHT, "radius": RADIUS,
           "A": A, "B": B, "C": C, "A2": A2, "placed": timings, "rows0": rows0, "rows": rows,
           "picked": picked_text, "open_s": t_open, "edit": {"check_s": check_s, "accept_put_back_s": t_edit,
                                                               "jobs": jobs, "text": edited_text},
           "orig": str(orig), "draft": str(draft), "edits": D.edits(draft),
           "I1": {"identical": not d1, "differing": d1, "files": len(ed), "compose_s": t_compose},
           "I2": {"identical": not d2, "differing": d2, "files": len(h3)},
           "stack": names, "tolerance": TOL, "targets": targets}
    PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for t in targets:
        print(f"  {t['key']} at {t['x']}, {t['z']} (block {t['block']}): predict y {t['predict_y']:.3f} "
              f"({t['part']} topograph {t['topograph']}); live y {t['live_y']:.3f}")
    print(f"-> {PREP}")


def run():
    prep = json.loads(PREP.read_text(encoding="utf-8"))
    py = sys.executable
    log = GAME / "Memoria.log"
    tg = {t["key"]: t for t in prep["targets"]}

    def at(key):
        return tg[key]["x"], tg[key]["z"]
    rec = {"prep_t": prep["t"], "steps": {}}

    def tele(key, where):
        r = C2._sh([py, "tools/world_teleport.py", f"{where[0]:.2f}", f"{where[1]:.2f}", "--shot", f"c9-{key}"], 300)
        rec["steps"][key] = C2._last_json(r)

    def reload(key):
        r = C2._sh([py, "tools/world_reload.py", f"{at('K')[0]:.2f}", f"{at('K')[1]:.2f}", "--shot", f"c9-{key}"],
                   600)
        rec["steps"][key] = C2._last_json(r)

    r = C2._sh([py, "tools/play.py", HERE / "a1_reach.py", "--keep-open", "--label", "c9-reach"], 900)
    rec["reach_rc"] = r.returncode
    try:
        if r.returncode == 0:
            tele("N0-A", at("A1"))
            rec["promote1"] = C2._promote({"draft": prep["orig"]})
            if rec["promote1"]["rc"] == 0:
                reload("N1-reload")
                tele("N1-A", at("A1"))
                rec["revert1"] = C2._promote({"draft": prep["orig"]}, "--revert")
                if rec["revert1"]["rc"] == 0:
                    rec["promote2"] = C2._promote({"draft": prep["draft"]})
                    if rec["promote2"]["rc"] == 0:
                        mark = log.stat().st_size if log.is_file() else 0
                        reload("N2-reload")
                        text = log.read_bytes()[mark:].decode("utf-8", "replace") if log.is_file() else ""
                        rec["log"] = [ln.strip() for ln in text.splitlines() if "WorldMeshOverride" in ln
                                      and "Block[{}][{}]".format(*tg["A'"]["block"]) in ln]
                        for key in ("A2", "A'", "B", "C"):
                            tele(f"N2-{key}", at(key))
                        tele("K-back", at("K"))
    finally:
        C2._sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", "c9-quit"], 300)   # close the game
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")

    def y(key):
        return (rec["steps"].get(key) or {}).get("world_y")

    def near(key, want):
        return y(key) is not None and abs(y(key) - want) <= TOL
    ran1 = (rec.get("promote1") or {}).get("rc") == 0
    ran2 = (rec.get("promote2") or {}).get("rc") == 0
    rec["N0"] = near("N0-A", tg["A1"]["live_y"])
    rec["N1"] = ran1 and near("N1-reload", tg["K"]["predict_y"]) and near("N1-A", tg["A1"]["predict_y"])
    rec["N2"] = ran2 and all(near(f"N2-{key}", tg[key]["predict_y"]) for key in ("A2", "A'", "B", "C"))
    rec["N3"] = ran2 and len(rec.get("log") or []) >= 1 and all(SOURCE in ln and "loaded" in ln for ln in rec["log"])
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for step, key in (("N0-A", "A1"), ("N1-reload", "K"), ("N1-A", "A1"), ("N2-A2", "A2"), ("N2-A'", "A'"),
                      ("N2-B", "B"), ("N2-C", "C"), ("K-back", "K")):
        print(f"{step}: y {y(step)}  (live {tg[key]['live_y']:.3f}, predicted {tg[key]['predict_y']:.3f})")
    print({k: rec[k] for k in ("N0", "N1", "N2", "N3")})
    print(f"-> {RESULT}")


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["build"]:
        build()
    elif cmd == ["run"]:
        run()
    else:
        raise SystemExit(__doc__)
