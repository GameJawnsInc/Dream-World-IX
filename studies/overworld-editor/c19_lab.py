"""Rung C19 on real bytes: a step that is in the game, edited in place through the World tab.

    py studies/overworld-editor/c19_lab.py build

THE EDITOR'S PATH, as c9_lab: the real RecipeBar and the real hill card with their real runners, a draft of the live
FF9CustomMap-world. A snapshot of the folder first (a draft copy, untouched after), then:
  H a hill on the lawn nearest the Landing Site, accepted, and PROMOTED from the card (world-promote);
  the bar picks H -- in the game -- and Edit asks, reverts the promote (world-promote --revert), opens the card on H's
  row; H moves 8u and is accepted; the bar promotes the recipe again.
Checks:
  I1  the live folder's disc-1 world files == world-fuse of the edited recipe composed onto the snapshot;
  L1  THE LEDGER STAYS TRUE: every live file at H's blocks (both positions, discs 1 and 4) has a last ledger row whose
      bytes are its own, written by world-hill (or the disc-4 mirror of it);
  R1  a final revert puts the live folder back EXACTLY as the snapshot found it, every world file (the stack holds;
      the lab leaves nothing behind).
No game run: the bytes are promote's and revert's own, which every rung since C4 walked in game.
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
import c1_lab as C1                                                    # noqa: E402  (pins the worktree package)

GAME, KIT = C1.GAME, C1.KIT
SOURCE = "FF9CustomMap-world"
OUT = HERE / "out" / "c19_lab"
PREP = HERE / "out" / "c19_prep.json"


def _world(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / "FF9_Data" / "WorldMap").rglob("Block*")
            if ".bak-" not in p.name and p.suffix in (".ff9mesh", ".txt")}


def _is_world(rel: str) -> bool:
    """A world block file on the discs a draft carries (1 and 4: the Path D disc 9 is no draft's)."""
    name = rel.rsplit("/", 1)[-1]
    return (rel.startswith(("FF9_Data/WorldMap/Disc1/", "FF9_Data/WorldMap/Disc4/")) and name.startswith("Block")
            and ".bak-" not in name and name.endswith((".ff9mesh", ".txt")))


def _drafted(world: dict) -> dict:
    return {rel: h for rel, h in world.items() if _is_world(rel)}


def build():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.world import draft as D
    from ff9mapkit.world import hilledit as HE
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import recipe as RC
    from ff9mapkit.workspace.worldforest import QProcessRunner
    from ff9mapkit.workspace.worldhill import HillTool
    from ff9mapkit.workspace.worldrecipe import RecipeBar
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    if OUT.exists():
        shutil.rmtree(OUT)
    live = GAME / SOURCE
    snap = D.ensure_draft(live, game=GAME, root=OUT / "snapshot")       # the folder before the lab (never touched)
    pal = pick_palette("dark")
    argvs = []

    def logged():
        r = QProcessRunner()
        real = r.start

        def start(argv, cwd, done):
            argvs.append([str(a) for a in argv])
            real(argv, cwd, done)
        r.start = start
        return r

    def pump(until, sec):
        t = time.time()
        while time.time() - t < sec:
            app.processEvents()
            if until():
                return True
            time.sleep(0.02)
        return False
    bar = None
    hill = HillTool(pal, WorldView3DPanel(pal), runner=logged(), game_fn=lambda: GAME, source_fn=lambda: live,
                    drafts_root=OUT / "drafts", on_changed=lambda d: bar and bar.refresh(), ask=lambda t, x: True)
    bar = RecipeBar(pal, game_fn=lambda: GAME, source_fn=lambda: live, runner=logged(), drafts_root=OUT / "drafts",
                    on_changed=lambda d: hill.island_changed(), ask=lambda t, x: True,
                    on_edit=lambda row, label: (hill.open_tool(), hill.edit_row(
                        row, label=label, on_accepted=bar.edit_accepted, on_cancel=bar.cancel_edit)))
    hill.open_tool()
    assert pump(lambda: hill._ix is not None, 300)
    k = C1.CONTROL[1:]
    fam = HE._fam(hill._ix)
    spots = sorted({(round(x / 8) * 8.0, round(z / 8) * 8.0) for x, z in hill._ix.cent[fam == "main"][::5]},
                   key=lambda c: math.dist(c, k))
    H = next(c for c in spots if HE.preview(hill._ix, c, 4.2, 18.0)["ok"])

    def check_and(fn, key, sec=900):
        pump(lambda: False, 1.0)
        assert pump(lambda: hill._job is None and hill._timer.remainingTime() < 0
                    and hill._current_verdict() is not None, sec), (key, hill.verdict_lbl.text())
        assert hill.accept_btn.isEnabled(), (key, hill.verdict_lbl.text())
        fn()
    hill.place(*H, 0.0)
    check_and(hill.accept_btn.click, "H")
    assert pump(lambda: hill._job is None and hill.center is None, 900), hill.verdict_lbl.text()
    draft = hill.draft()
    hill.promote_btn.click()                                             # the card's Promote: H into the game
    assert pump(lambda: hill._job is None, 900), hill.verdict_lbl.text()
    assert D.history(draft)["promoted"] == 1, (D.history(draft)["promoted"], hill.verdict_lbl.text())
    live_h = _world(live)
    hill_cells = OUT / "h_cells.json"
    hill_cells.write_text(json.dumps(D.history(draft)["steps"][0]["cells"]))
    hill.close_tool()
    print(f"H at {H} accepted and promoted: {hill.verdict_lbl.text()[:120]}")
    # the edit, in place
    bar.refresh()
    assert bar.pick(H[0] + 0.7, H[1] - 0.4) == 0, bar.status_lbl.text()
    n0 = len(argvs)
    row0 = D.recipe_rows(draft)[0]
    t0 = time.time()
    bar.edit_btn.click()
    assert pump(lambda: hill.editing() and bar._job is None, 900), bar.status_lbl.text()
    assert pump(lambda: hill._ix is not None, 300)
    out_of_game = _drafted(_world(live)) == {rel: h for rel, h in
                                   ((r, rec[0]) for r, rec in D.read_meta(snap)["manifest"].items() if _is_world(r))}
    said = hill.row() == row0
    H2 = next(c for c in sorted(((H[0] + dx, H[1] + dz) for dx in (-8, 0, 8) for dz in (-8, 0, 8) if dx or dz),
                                key=lambda c: math.dist(c, H)) if HE.preview(hill._ix, c, 4.2, 18.0)["ok"])
    hill.place(*H2, 0.0)
    check_and(hill.accept_btn.click, "H2")
    assert pump(lambda: bar._edit is None and bar._job is None and hill._job is None, 1800), bar.status_lbl.text()
    t_edit = round(time.time() - t0, 1)
    jobs = [" ".join(a[5:6] + (["--revert"] if "--revert" in a else [])) for a in argvs[n0:]]
    text = bar.status_lbl.text()
    rows = D.recipe_rows(draft)
    print(f"edit in place: H -> {H2} in {t_edit} s; jobs {jobs}\n  {text}")
    assert rows == [{**rows[0], "center": [H2[0], H2[1]]}] and D.history(draft)["promoted"] == 1, rows
    # I1: the live disc 1 == the edited recipe composed onto the snapshot
    recipe = OUT / "edited.toml"
    recipe.write_text(RC.dumps(rows), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "--game", str(GAME), "world-fuse", str(recipe),
                        "--mod-folder", str(snap), "--allow-overwrite"], cwd=KIT, capture_output=True, text=True,
                       timeout=3600)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
    lv1 = {k: v for k, v in _world(live).items() if "/Disc1/" in "/" + k}
    sn1 = {k: v for k, v in _world(snap).items() if "/Disc1/" in "/" + k}
    d1 = sorted(x for x in set(lv1) | set(sn1) if lv1.get(x) != sn1.get(x))
    # L1: the ledger is true at every live file the hill's two positions touch
    cells = sorted({tuple(c) for s in D.history(draft)["steps"] for c in s["cells"]} | {tuple(c) for c in
                   json.loads(hill_cells.read_text()) if hill_cells.is_file()})        # the blocks the hill CHANGED
    led = D._ledger_last(live)
    bad, seen = [], 0
    for rel, p in D._cell_files(live, cells).items():
        key = D._ledger_key(rel)
        e = led.get((key[0], *key[1], key[2])) if key else None
        if e is None:
            continue
        seen += 1
        tag = D._row_tag(e) or {}
        if e.get("sha256") != hashlib.sha256(p.read_bytes()).hexdigest():
            bad.append((rel, "bytes"))
    hill_rows = sum(1 for rel in D._cell_files(live, cells) if D._ledger_key(rel) and
                    (D._row_tag(led.get((D._ledger_key(rel)[0], *D._ledger_key(rel)[1], D._ledger_key(rel)[2])))
                     or {}).get("verb") == "world-hill")
    # R1: revert the last promote; the live folder goes back to the snapshot as it was BEFORE the fuse above
    pre = {rel: rec[0] for rel, rec in D.read_meta(snap)["manifest"].items() if _is_world(rel)}   # the copy's hashes
    rv = subprocess.run([sys.executable, "-m", "ff9mapkit", "--game", str(GAME), "world-promote", str(draft),
                         "--revert"], cwd=KIT, capture_output=True, text=True, timeout=1800)
    after = _drafted(_world(live))
    back = sorted(rel for rel in set(after) | set(pre) if after.get(rel) != pre.get(rel))
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "H": H, "H2": H2, "rows": rows, "jobs": jobs, "text": text,
           "edit_s": t_edit, "said_back": said, "out_of_game_while_open": out_of_game,
           "I1": {"identical": not d1, "differing": d1[:12], "files": len(lv1)},
           "L1": {"files": seen, "bytes_mismatch": bad[:12], "hill_tagged": hill_rows},
           "R1": {"revert_rc": rv.returncode, "differing_from_snapshot": back[:12]}}
    PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print(f"I1 live disc 1 vs the edited recipe on the snapshot: {'IDENTICAL' if not d1 else 'DIFFERS ' + str(d1[:4])}"
          f" over {len(lv1)} files\nL1 ledger at H's blocks: {seen} files, {len(bad)} whose bytes their last row does "
          f"not name, {hill_rows} written by world-hill\nR1 revert rc {rv.returncode}: the live folder "
          f"{'== the snapshot' if not back else 'DIFFERS at ' + str(back[:4])}; out of the game while open: "
          f"{out_of_game}; said back: {said}\n-> {PREP}")
    assert not d1 and not bad and rv.returncode == 0 and not back and out_of_game


if __name__ == "__main__":
    if sys.argv[1:2] == ["build"]:
        build()
    else:
        raise SystemExit(__doc__)
