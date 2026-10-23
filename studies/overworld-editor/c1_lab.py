"""Rung C1 in game: the forest the World tab's forest tool accepted into a draft, loaded by the game for one session.

    py studies/overworld-editor/c1_lab.py build      # the tool places + accepts the forest; identity; predictions
    py studies/overworld-editor/c1_lab.py run        # install the lab, reach the world, teleport, quit, uninstall
    py studies/overworld-editor/c1_lab.py install    # (owner playtest) the lab in, FolderNames first; nothing else
    py studies/overworld-editor/c1_lab.py front      # (owner playtest) put an installed lab first again
    py studies/overworld-editor/c1_lab.py uninstall  # ...and out again: the ini restored byte-exact

THE LAUNCHER REWRITES THE ORDER. Memoria's launcher writes BOTH `FolderNames` and `Priorities` from its mod list, and
a folder missing from `Priorities` is a new mod it APPENDS LAST -- on both lines. A lab put first in FolderNames
alone therefore loads LAST when the game is started from the launcher (owner playtest 2026-10-23: no forest; the
harness, which starts the game without the launcher, kept the order). The lab goes first on both lines.

THE EDITOR'S PATH, NOT A REPLAY OF IT. `build` drives the real ForestTool (workspace/worldforest.py) against the real
install with its real runner: the ghost is placed at SPOT with DONOR, the tool's Check runs `world-forest --dry-run`
as a subprocess, its Accept runs `world-forest` into a draft (world/draft.py) under out/c1_lab/drafts -- the same
calls a click makes. Then, on a second draft of the same folder, the hand-typed command runs, and every world file
of the two drafts is compared (I1: the C1 acceptance on the real island, the test suite's hermetic twin).

THE LAB (out of the install except for the one session; the launcher activates any folder left there, memory
project-ff9-launcher-activates-new-folders): FF9CustomMap-c1lab holds ONLY the files the draft edited, and goes
FIRST in FolderNames. The engine takes each file from the first folder holding it (STACK.md), so the game then
loads exactly the draft: the edited blocks from the lab, everything else as before.

REGISTERED PREDICTIONS (c1_prep.json, written by `build` before the game opens; tolerance 0.15):
  F1 at A and A2 (on the carried canopy) the game stands at the height point_info predicts on the stacked site (lab
     first), and that height differs by >= 0.5 from the height without the lab (the read-back tells them apart);
     at C (the grass zip round the rim) and K (the Landing Site control) the stacked prediction holds too;
  F2 Memoria.log: "[WorldMeshOverride] loaded" from FF9CustomMap-c1lab for every block the draft edited on disc 1.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))
import ff9mapkit                                                      # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(KIT), ff9mapkit.__file__

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
MAIN_BACKUPS = Path(r"C:\gd\Dream-World-IX\backups")
INI = GAME / "Memoria.ini"
LAB = "FF9CustomMap-c1lab"
SOURCE = "FF9CustomMap-world"
SPOT, DONOR = (1400.0, -460.0), (13, 15)                             # forest-grove on the north-east island
OUT = HERE / "out" / "c1_lab"
PREP = HERE / "out" / "c1_prep.json"
STATE = HERE / "out" / "c1_install.json"
RESULT = HERE / "out" / "c1_result.json"
CONTROL = ("Landing Site", 326.16, -569.09)
TOL = 0.15


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _world_files(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in (root / "FF9_Data" / "WorldMap").rglob("*.ff9mesh")}


def _drive_tool(drafts: Path, spot=SPOT, donor=DONOR) -> dict:
    """The forest tool, placed and accepted the way a click does, against the real install (offscreen: the tool
    needs no GL; its jobs are real world-forest subprocesses)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldforest import ForestTool, QProcessRunner
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    pal = pick_palette("dark")
    runner = QProcessRunner()
    argvs = []
    real_start = runner.start

    def start(argv, cwd, done):
        argvs.append([str(a) for a in argv])
        real_start(argv, cwd, done)
    runner.start = start
    tool = ForestTool(pal, WorldView3DPanel(pal), game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE,
                      runner=runner, drafts_root=drafts)
    tool.donor_box.setCurrentIndex(tool.donor_box.findData("{},{}".format(*donor)))
    tool.open_tool()

    def pump(until, sec):
        t = time.time()
        while time.time() - t < sec:
            app.processEvents()
            if until():
                return True
            time.sleep(0.02)
        return False
    assert pump(lambda: tool._ix is not None and tuple(donor) in tool._outlines, 120), "the tool never read the island"
    tool.place(*spot, 3.2)
    t0 = time.time()
    assert pump(lambda: tool._current_verdict() is not None, 180), tool.verdict_lbl.text()
    t_check = time.time() - t0
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    check_text = tool.verdict_lbl.text()
    t0 = time.time()
    tool.accept_btn.click()
    assert pump(lambda: tool._job is None and tool.center is None, 180), tool.verdict_lbl.text()
    t_accept = time.time() - t0
    return {"argvs": argvs, "check": check_text, "accepted": tool.verdict_lbl.text(), "draft": str(tool.draft()),
            "check_s": round(t_check, 1), "accept_s": round(t_accept, 1)}


def _ground(site, x, z, names):
    from ff9mapkit.world import pointinfo as PI
    return PI.point_info(site, x, z, stack=names, landmark=False)["ground"]


def build():
    from ff9mapkit.world import draft as D, render as R
    if OUT.exists():
        shutil.rmtree(OUT)
    drafts, hand_root = OUT / "drafts", OUT / "hand"
    drive = _drive_tool(drafts)
    draft = Path(drive["draft"])
    print(f"tool: check {drive['check_s']} s, accept {drive['accept_s']} s\n  {drive['check']}\n  {drive['accepted']}")
    # I1: the hand-typed command against a second draft of the same folder
    hand = D.ensure_draft(GAME / SOURCE, game=GAME, root=hand_root)
    hand_argv = [sys.executable, "-m", "ff9mapkit", "world-forest", "--mod-folder", str(hand),
                 "--center", "{:g},{:g}".format(*SPOT), "--donor", "{},{}".format(*DONOR)]
    r = subprocess.run(hand_argv, cwd=KIT, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr[-2000:]
    ed, hd = _world_files(draft), _world_files(hand)
    diff = sorted(k for k in set(ed) | set(hd) if ed.get(k) != hd.get(k))
    edits = D.edits(draft)
    i1 = {"identical": not diff, "differing": diff, "files": len(ed), "edited": edits,
          "hand_argv": hand_argv[3:], "tool_argvs": [a[3:] for a in drive["argvs"]]}
    print(f"I1 identity: {'IDENTICAL' if not diff else 'DIFFERS ' + str(diff)} over {len(ed)} world files; "
          f"the draft edited {len(edits)}: {edits}")
    assert not diff
    # the lab: only what the draft edited
    lab = OUT / LAB
    for rel in edits:
        dst = lab / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(draft / rel, dst)
    assert not (lab / "ModDescription.xml").exists()
    # the predictions: the stacked site resolves exactly as the installed lab will (same files, same order)
    names = [p.name for p in R.game_stack(GAME)]
    stacked = R.RenderSite(cells=(), disc=1, game=GAME, stack=(lab,) + tuple(GAME / n for n in names))
    without = R.RenderSite(cells=(), disc=1, game=GAME, stack=tuple(GAME / n for n in names))
    picks = [("A", SPOT)]
    for dx, dz in ((3, 3), (-3, 3), (3, -3), (-3, -3), (0, 5), (5, 0)):
        p = (SPOT[0] + dx, SPOT[1] + dz)
        g = _ground(stacked, *p, [LAB] + names)
        if g.get("canopy"):
            picks.append(("A2", p))
            break
    for dx in (14, 16, 18, -14, -16):
        p = (SPOT[0] + dx, SPOT[1])
        g = _ground(stacked, *p, [LAB] + names)
        if g["part"] == "Terrain" and not g.get("canopy") and g.get("walkable"):
            picks.append(("C", p))
            break
    picks.append(("K", CONTROL[1:]))
    targets = []
    for key, (x, z) in picks:
        g = _ground(stacked, x, z, [LAB] + names)
        w = _ground(without, x, z, names)
        targets.append({"key": key, "x": round(x, 2), "z": round(z, 2), "predict_y": g["stand_y"],
                        "canopy": bool(g.get("canopy")), "topograph": g.get("topograph"),
                        "without_lab_y": w["stand_y"], "separation": abs(g["stand_y"] - w["stand_y"]),
                        "block": (math.floor(x / 64), math.floor(-z / 64))})
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "stack": [LAB] + names, "tolerance": TOL, "spot": SPOT,
           "donor": DONOR, "tool": drive, "I1": i1, "targets": targets,
           "lab_files": {str(p.relative_to(OUT)): sha(p)[:16] for p in sorted(lab.rglob("*.ff9mesh"))}}
    PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for t in targets:
        print(f"  {t['key']} block {t['block']} at {t['x']}, {t['z']}: predict y {t['predict_y']:.3f}"
              f" ({'canopy' if t['canopy'] else 'topograph ' + str(t['topograph'])}); without the lab "
              f"{t['without_lab_y']:.3f}, separation {t['separation']:.2f}")
    bad = [t["key"] for t in targets if t["key"].startswith("A") and (t["separation"] < 0.5 or not t["canopy"])]
    assert not bad and len([t for t in targets if t["key"].startswith("A")]) == 2, \
        f"predictions cannot tell the lab from no lab at {bad}"
    print(f"-> {PREP}")


def _game_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq FF9.exe"], capture_output=True, text=True).stdout
    return "FF9.exe" in out


def install():
    if _game_running():
        raise SystemExit("FF9 is running: close it first (the ini is read at launch)")
    if (GAME / LAB).exists():
        raise SystemExit(f"{GAME / LAB} already exists: not touching it")
    raw = INI.read_bytes()
    m = re.search(rb'^(\s*FolderNames\s*=\s*)(.+)$', raw, re.M)
    if not m or LAB.encode() in m.group(2):
        raise SystemExit(f"FolderNames missing or already holds the lab: {m and m.group(2)!r}")
    if LAB.encode() in raw:
        raise SystemExit(f"Memoria.ini already names {LAB}: not touching it")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    MAIN_BACKUPS.mkdir(parents=True, exist_ok=True)
    bak = MAIN_BACKUPS / f"Memoria.ini.{stamp}.c1-lab"
    shutil.copyfile(INI, bak)
    assert sha(bak) == sha(INI)
    shutil.copytree(OUT / LAB, GAME / LAB)
    INI.write_bytes(_lab_first(raw))
    STATE.write_text(json.dumps({"backup": str(bak), "ini_sha": sha(bak), "installed_at": stamp}, indent=1),
                     encoding="utf-8")
    print(f"installed {LAB} first in FolderNames; ini backed up to {bak}")


def _lab_first(raw: bytes) -> bytes:
    """``raw`` with the lab first on BOTH the FolderNames and Priorities lines (any copy of it elsewhere removed)."""
    out = raw
    for key in (b"FolderNames", b"Priorities"):
        m = re.search(rb'^(\s*' + key + rb'\s*=\s*)([^\r\n]+)', out, re.M)
        if not m:
            if key == b"FolderNames":
                raise SystemExit("Memoria.ini has no FolderNames line")
            continue
        names = [n for n in re.findall(rb'"([^"]*)"', m.group(2)) if n != LAB.encode()]
        line = b", ".join(b'"' + n + b'"' for n in [LAB.encode()] + names)
        out = out[:m.start(2)] + line + out[m.end(2):]
    return out


def front():
    """An installed lab that the launcher moved last: put it first again on both lines (the backup is kept)."""
    if _game_running():
        raise SystemExit("FF9 is running: close it (and the launcher) first")
    if not STATE.is_file() or not (GAME / LAB).exists():
        raise SystemExit("the lab is not installed")
    INI.write_bytes(_lab_first(INI.read_bytes()))
    print([ln for ln in INI.read_text(encoding="utf-8").splitlines() if re.match(r"\s*(FolderNames|Priorities)", ln)])


def uninstall(run_dir: Path):
    if _game_running():
        raise SystemExit("FF9 is running: close it first")
    st = json.loads(STATE.read_text(encoding="utf-8"))
    shutil.copyfile(st["backup"], INI)
    if sha(INI) != st["ini_sha"]:
        raise SystemExit(f"Memoria.ini restore MISMATCH: {sha(INI)} vs {st['ini_sha']}")
    run_dir.mkdir(parents=True, exist_ok=True)
    if (GAME / LAB).exists():
        shutil.move(str(GAME / LAB), str(run_dir / f"{LAB}.moved"))
    STATE.unlink()
    print(f"uninstalled: Memoria.ini restored byte-exact (sha {st['ini_sha'][:16]}); the lab moved into {run_dir}")


def _sh(argv, timeout):
    print("$", " ".join(str(a) for a in argv), flush=True)
    r = subprocess.run([str(a) for a in argv], cwd=REPO, capture_output=True, text=True, timeout=timeout)
    print(r.stdout[-2000:], flush=True)
    if r.returncode:
        print(r.stderr[-2000:], flush=True)
    return r


def run():
    prep = json.loads(PREP.read_text(encoding="utf-8"))
    py = sys.executable
    log = GAME / "Memoria.log"
    run_dir = REPO / ".harness-runs" / f"{time.strftime('%Y%m%d-%H%M%S')}-c1-lab"
    rec = {"prep_t": prep["t"], "targets": []}
    install()
    try:
        r = _sh([py, "tools/play.py", HERE / "a1_reach.py", "--keep-open", "--label", "c1-reach"], 900)
        rec["reach_rc"] = r.returncode
        if r.returncode == 0:
            for t in prep["targets"]:
                r = _sh([py, "tools/world_teleport.py", f"{t['x']:.2f}", f"{t['z']:.2f}", "--shot",
                         f"c1-{t['key']}"], 300)
                back = json.loads(r.stdout.strip().splitlines()[-1])
                row = dict(t, back=back)
                if back["ok"] and back["world_y"] is not None:
                    row["dy"] = back["world_y"] - t["predict_y"]
                    row["F1"] = abs(row["dy"]) <= TOL
                else:
                    row["F1"] = False
                rec["targets"].append(row)
        _sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", "c1-quit"], 300)
        for _ in range(30):
            if not _game_running():
                break
            time.sleep(1)
        text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
        blocks = sorted({tuple(int(v) for v in re.findall(r"\[(\d+)\]", rel)[:2])
                         for rel in prep["I1"]["edited"] if "/Disc1/" in rel})
        rec["log"] = {}
        for bx, by in blocks:
            key = f"Block[{bx}][{by}] Terrain"
            rec["log"][f"{bx},{by}"] = [ln.strip() for ln in text.splitlines()
                                        if key in ln and "WorldMeshOverride" in ln][-4:]
        rec["F2"] = {k: any("loaded" in ln and LAB in ln for ln in v) for k, v in rec["log"].items()}
    finally:
        uninstall(run_dir)
        RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for row in rec["targets"]:
        b = row["back"]
        print(f"{row['key']}: F1 {row['F1']}  y {b.get('world_y')} vs predicted {row['predict_y']:.3f}"
              f" (without the lab {row['without_lab_y']:.3f})")
    print("F2", rec.get("F2"))
    print(f"-> {RESULT}")


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["build"]:
        build()
    elif cmd == ["run"]:
        run()
    elif cmd == ["install"]:
        install()
    elif cmd == ["front"]:
        front()
    elif cmd == ["uninstall"]:
        uninstall(REPO / ".harness-runs" / f"{time.strftime('%Y%m%d-%H%M%S')}-c1-playtest")
    else:
        raise SystemExit(__doc__)
