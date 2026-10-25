"""Rung C23: a carry across the world's x seam -- the comma carried by the World tab onto (23, 1), its land in columns
23 and 0, promoted and stood on from both sides of x = 0.

    py studies/overworld-editor/c23_lab.py before   # the kit as master ships it refuses the rect (recorded)
    py studies/overworld-editor/c23_lab.py build    # the card accepts it; I1 hand, I2 recipe, I3 off-seam identity
    py studies/overworld-editor/c23_lab.py run      # the game: before / promote / reload / after on both sides; quit

THE TARGET. Columns 23 and 0 are free on rows 1-3 (the live stack holds nothing there, and stock has no land), and the
comma (donor (9, 5), 2x3, qualified) unturned puts 214 land tris west of x = 1536 and 703 east of it. The card is
clicked at x 3 (east of the seam, as the World tab folds a click on the view's west copy): its anchor wraps to (23, 1).

I3, THE SEAM MOVES NO BYTE. A carried block's verts are block-local, so the same carry onto an off-seam rect of open
ocean must write the same bytes block for block: Block[23][1+j] == Block[bx][by+j], Block[0][1+j] == Block[bx+1][by+j],
every part and the Donor.txt. The off-seam rect is the first stock-open 2x3 in columns 2-20 of a scratch draft, its
own files cleared first (the scratch is not the live folder).

REGISTERED PREDICTIONS (c23_prep.json, written by `build` before the game opens; tolerance 0.15), as C20's:
  N0 before the promote, at a probe on the carried land WEST of x = 0 (column 23) and one EAST of it (column 0), the
     party is in open sea;
  N1 after the promote and the reload, at the Landing Site (the control) it stands where it stood;
  N2 at both probes it stands on the carried land, at the height point_info predicts with the draft in place;
  N3 Memoria.log: the reload loaded both probes' blocks from FF9CustomMap-world.
The game is closed at the end (the harness quit).
"""
from __future__ import annotations

import json
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
import c5u_lab as U                                                    # noqa: E402  (the world hash, the kit call)

GAME, KIT, REPO = C1.GAME, C1.KIT, C1.REPO
SOURCE = "FF9CustomMap-world"
DONOR, SIZE, ROT, TARGET = (9, 5), (2, 3), 0, (23, 1)
CLICK = (3.0, -160.0)                       # east of the seam, the rect's middle row: the anchor wraps to (23, 1)
OUT = HERE / "out" / "c23_lab"
BEFORE = HERE / "out" / "c23_before.json"
PREP = HERE / "out" / "c23_prep.json"
RESULT = HERE / "out" / "c23_result.json"
MASTER_KIT = Path(r"C:\gd\Dream-World-IX\ff9mapkit")
TOL = 0.15


def _argv(folder, cell, *, dry_run):
    from ff9mapkit.world import transplantedit as TE
    return ["--game", str(GAME)] + TE.command(folder, cell, DONOR, rot=ROT, size=SIZE, dry_run=dry_run)


def before():
    """The rect through the kit as master ships it (the main repo's checkout, before this rung): refused."""
    from ff9mapkit.world import draft as D
    scratch = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "before")
    r = subprocess.run([sys.executable, "-m", "ff9mapkit"] + _argv(scratch, TARGET, dry_run=True), cwd=MASTER_KIT,
                       capture_output=True, text=True, timeout=900)
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "kit": str(MASTER_KIT), "rc": r.returncode,
           "said": (r.stderr or r.stdout).strip().splitlines()[-1:]}
    BEFORE.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(rec)
    assert r.returncode != 0


def _drive_tool(drafts: Path) -> dict:
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
    tool.donor_box.setCurrentIndex(tool.donor_box.findData("{},{}@{}x{}".format(*DONOR, *SIZE)))
    tool.rot_box.setCurrentIndex(tool.rot_box.findData(ROT))
    assert pump(lambda: tool._ix is not None and tool.donor() in tool._outlines, 300), tool.verdict_lbl.text()
    tool.place(*CLICK, 0.0)
    cell, blocks = tool.cell(), tool.blocks()
    assert cell == TARGET, cell
    t0 = time.time()
    assert pump(lambda: tool._current_verdict() is not None, 300), tool.verdict_lbl.text()
    check = {"text": tool.verdict_lbl.text(), "s": round(time.time() - t0, 1), "cell": cell, "blocks": blocks}
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    t0 = time.time()
    tool.accept_btn.click()
    assert pump(lambda: tool._job is None and tool.center is None, 600), tool.verdict_lbl.text()
    return {"check": check, "accepted": tool.verdict_lbl.text(), "accept_s": round(time.time() - t0, 1),
            "argv": argvs[-1], "draft": str(tool.draft())}


def _block_files(root: Path, cells) -> dict:
    """``(bx, by) -> {part file name tail: sha}`` for the drafted disc-1 files at ``cells``."""
    import hashlib
    out = {}
    for bx, by in cells:
        d = root / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / f"r{by}"
        pre = f"Block[{bx}][{by}] "
        out[(bx, by)] = {p.name[len(pre):]: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in d.glob(f"Block[[]{bx}[]][[]{by}[]] *") if ".bak-" not in p.name}
    return out


def build():
    from ff9mapkit.world import draft as D, islandedit as IE, recipe as RC, render as R, transplantedit as TE
    if OUT.exists():
        for sub in ("drafts", "hand", "composed", "offseam"):
            shutil.rmtree(OUT / sub, ignore_errors=True)
    drive = _drive_tool(OUT / "drafts")
    draft = Path(drive["draft"])
    print(f"tool: check {drive['check']['s']} s at {drive['check']['cell']} {drive['check']['blocks']}:\n"
          f"  {drive['check']['text']}\n  accept {drive['accept_s']} s: {drive['accepted']}")
    # I1 the same command by hand; I2 the [[transplant]] row through world-fuse
    hand = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "hand")
    U._kit(_argv(hand, TARGET, dry_run=False))
    verb = TE.command("-", TARGET, DONOR, rot=ROT, size=SIZE, dry_run=False)
    recipe = OUT / "comma.toml"
    recipe.write_text(RC.dumps([RC.row_for(verb)]), encoding="utf-8")
    composed = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "composed")
    U._kit(["--game", str(GAME), "world-fuse", str(recipe), "--mod-folder", str(composed)])
    ed, hd, cd = U._world(draft), U._world(hand), U._world(composed)
    d1 = sorted(k for k in set(ed) | set(hd) if ed.get(k) != hd.get(k))
    d2 = sorted(k for k in set(ed) | set(cd) if ed.get(k) != cd.get(k))
    edits = D.edits(draft)
    seam = [(c, r) for r in range(TARGET[1], TARGET[1] + 3) for c in (23, 0)]
    print(f"I1 hand: {'IDENTICAL' if not d1 else 'DIFFERS ' + str(d1[:6])}; I2 recipe: "
          f"{'IDENTICAL' if not d2 else 'DIFFERS ' + str(d2[:6])}; over {len(ed)} world files; the draft edited "
          f"{len(edits)}: {edits}")
    assert not d1 and not d2
    assert not any("Block[24]" in e or "Block[-1]" in e for e in edits)
    # I3 the same carry off the seam: the bytes, block for block
    land = IE.stock_land(game=GAME)
    off = next((x, y) for y in range(0, 18) for x in range(2, 21)
               if not any((x + i, y + j) in land for i in range(2) for j in range(3)))
    scratch = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "offseam")
    ocells = [(off[0] + i, off[1] + j) for j in range(3) for i in range(2)]
    cleared = []
    for d in (1, 4):
        for bx, by in ocells:
            for p in (scratch / "FF9_Data" / "WorldMap" / f"Disc{d}" / "0_1" / f"r{by}").glob(
                    f"Block[[]{bx}[]][[]{by}[]] *"):
                p.unlink()
                cleared.append(p.name)
    U._kit(_argv(scratch, off, dry_run=False))
    a = _block_files(draft, seam)
    b = _block_files(scratch, ocells)
    pairs = [((23 + i) % 24, TARGET[1] + j) for j in range(3) for i in range(2)]
    i3 = {f"{pa}": a[pa] == b[ob] for pa, ob in zip(pairs, ocells)}
    print(f"I3 off-seam at {off} (cleared {len(cleared)} scratch files): "
          + ", ".join(f"{k} {'==' if v else '!='}" for k, v in i3.items()))
    assert all(i3.values()) and any(a[p] for p in pairs)
    # the predictions: the carried land's highest walkable point WEST of x = 0 and EAST of it
    names = [p.name for p in R.game_stack(GAME)]
    live = R.RenderSite(cells=(), disc=1, game=GAME, stack=tuple(GAME / n for n in names))
    with_draft = R.RenderSite(cells=(), disc=1, game=GAME,
                              stack=tuple(draft if n == SOURCE else GAME / n for n in names))
    dnames = [draft.name if n == SOURCE else n for n in names]
    carried = TE.placed(TE.donor_land(DONOR, size=SIZE, game=GAME), DONOR, TARGET, rot=ROT, size=SIZE)
    cands = sorted(((t[:, 1].mean(), tuple(t[:, [0, 2]].mean(axis=0))) for t in carried), reverse=True)
    probes = {}
    for side, keep in (("W", lambda x: x < 1536.0 - 2.0), ("E", lambda x: x > 1536.0 + 2.0)):
        for _y, (x, z) in cands:
            if not keep(x):
                continue
            fx, fz = round((x + 0.37) % 1536.0, 2), round(z - 0.29, 2)
            g, w = C1._ground(with_draft, fx, fz, dnames), C1._ground(live, fx, fz, names)
            if g.get("part") == "Terrain" and g.get("walkable") and (w.get("stand_y") or 0.0) <= 0.05:
                probes[side] = (fx, fz)
                break
        assert side in probes, f"no walkable carried point {side} of x = 0"
    probes["K"] = C1.CONTROL[1:]
    rec_t = []
    for key, (x, z) in probes.items():
        g, w = C1._ground(with_draft, x, z, dnames), C1._ground(live, x, z, names)
        rec_t.append({"key": key, "x": x, "z": z, "predict_y": g["stand_y"], "part": g.get("part"),
                      "topograph": g.get("topograph"), "live_y": w["stand_y"], "live_part": w.get("part"),
                      "block": [int(x // 64) % 24, int(-z // 64)]})
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "draft": str(draft), "tool": drive, "edits": edits,
           "I1": {"identical": not d1, "files": len(ed)}, "I2": {"identical": not d2},
           "I3": {"offseam": list(off), "pairs": i3, "cleared": len(cleared)}, "stack": names, "tolerance": TOL,
           "targets": rec_t}
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
    sides = ("W", "E")
    K = (tg["K"]["x"], tg["K"]["z"])
    rec = {"prep_t": prep["t"], "steps": {}}

    def tele(key, at):
        r = C2._sh([py, "tools/world_teleport.py", f"{at[0]:.2f}", f"{at[1]:.2f}", "--shot", f"c23-{key}"], 300)
        rec["steps"][key] = C2._last_json(r)

    r = C2._sh([py, "tools/play.py", HERE / "a1_reach.py", "--keep-open", "--label", "c23-reach"], 900)
    rec["reach_rc"] = r.returncode
    try:
        if r.returncode == 0:
            for s in sides:
                tele(f"N0-{s}", (tg[s]["x"], tg[s]["z"]))
            tele("K0-before", K)
            rec["promote"] = C2._promote(prep)
            if rec["promote"]["rc"] == 0:
                mark = log.stat().st_size if log.is_file() else 0
                r = C2._sh([py, "tools/world_reload.py", f"{K[0]:.2f}", f"{K[1]:.2f}", "--shot", "c23-N1-reload"], 600)
                rec["steps"]["N1-reload"] = C2._last_json(r)
                text = log.read_bytes()[mark:].decode("utf-8", "replace") if log.is_file() else ""
                rec["log"] = {s: [ln.strip() for ln in text.splitlines() if "WorldMeshOverride" in ln
                                  and "Block[{}][{}]".format(*tg[s]["block"]) in ln] for s in sides}
                for s in sides:
                    tele(f"N2-{s}", (tg[s]["x"], tg[s]["z"]))
                tele("K1-back", K)
    finally:
        C2._sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", "c23-quit"], 300)   # close the game
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")

    def y(key):
        return (rec["steps"].get(key) or {}).get("world_y")
    ran = (rec.get("promote") or {}).get("rc") == 0
    verdict = {"N1": ran and y("N1-reload") is not None and abs(y("N1-reload") - tg["K"]["predict_y"]) <= TOL}
    for s in sides:
        verdict[f"N0-{s}"] = y(f"N0-{s}") is not None and y(f"N0-{s}") <= 0.05
        verdict[f"N2-{s}"] = ran and y(f"N2-{s}") is not None and abs(y(f"N2-{s}") - tg[s]["predict_y"]) <= TOL
        lines = (rec.get("log") or {}).get(s) or []
        verdict[f"N3-{s}"] = ran and len(lines) >= 1 and all(SOURCE in ln and "loaded" in ln for ln in lines)
    rec["verdict"] = verdict
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for k in [f"N0-{s}" for s in sides] + ["N1-reload"] + [f"N2-{s}" for s in sides] + ["K1-back"]:
        key = k.split("-", 1)[1] if k.startswith(("N0-", "N2-")) else "K"
        print(f"{k}: y {y(k)}  (live {tg[key]['live_y']:.3f}, with the draft {tg[key]['predict_y']:.3f})")
    print(verdict, "promote", (rec.get("promote") or {}).get("seconds"), "s")
    print(f"-> {RESULT}")


if __name__ == "__main__":
    fn = {"before": before, "build": build, "run": run}.get((sys.argv[1:2] or [""])[0])
    if fn is None:
        raise SystemExit(__doc__)
    fn()
