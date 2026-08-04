"""THE BENCH PIPELINE — the Path D bench, reproducible from a stable anchor.

WHY THIS EXISTS (the P0 debt, stated plainly). The accepted bench was built by
a chain of study scripts, each reading the LIVE install and each anchored to a
TIMESTAMPED BACKUP in a gitignored folder shared by every concurrent session.
Two consequences, both bad: the only way to exercise the generator was to
mutate the owner's game, and re-running the generator silently reverted the
corner — with every gate still green, because the gates run on whatever is in
the blocks. Twelve playtests of work sat on that.

WHAT WAS MEASURED (2026-08-02), not assumed:
  * all 19 `terrace-strip-prewall.*` snapshots are BYTE-IDENTICAL — the root
    anchor is stable and redundantly stored;
  * `full_skirt.py --bench-src <prewall>` reproduces the corner's baseline
    Terrain for blocks (5,7) and (5,8) BYTE-IDENTICALLY;
  * so the chain prewall -> full_skirt -> corner is fully regenerable, and the
    timestamped backups are a snapshot of the truth rather than the truth.

WHAT THIS DRIVER DOES
  verify   the anchors exist, are self-consistent, and hash as expected
  regen    run the generator OFFLINE from the anchor (never touches the game)
  corner   build the accepted corner on the REGENERATED base
  check    compare the result against the live, owner-accepted bench

Usage:
  py bench_pipeline.py verify
  py bench_pipeline.py regen
  py bench_pipeline.py corner
  py bench_pipeline.py check
  py bench_pipeline.py all
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN_REPO = Path(r"C:\gd\Dream-World-IX")
BACKUPS = MAIN_REPO / "backups"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LIVE = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc9" / "0_1"
GEN_OUT = HERE / "out" / "terrace_strip" / "underlay_meshes"
STAGE = HERE / "out" / "bench_pipeline"
MANIFEST = HERE / "bench_manifest.json"

CELLS = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]
CORNER_BLOCKS = [(5, 7), (5, 8)]
# regenerable prerequisites that live in gitignored out/ dirs
PREREQS = [(HERE.parent / "overworld-topography" / "out" / "rock_tiles.json",
            "studies/overworld-topography/rock_wall_language.py")]


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def prewall_anchors():
    return sorted(BACKUPS.glob("terrace-strip-prewall.*"))


def cmd_verify():
    ok = True
    snaps = prewall_anchors()
    print(f"[anchor] {len(snaps)} prewall snapshots")
    if not snaps:
        print("   !! NO PREWALL ANCHOR — the bench is NOT rebuildable. STOP.")
        return False
    sig = {}
    for d in snaps:
        f = d / "Block[5][7] Terrain.ff9mesh"
        if f.is_file():
            sig.setdefault(md5(f), []).append(d.name)
    for h, names in sig.items():
        print(f"   {h[:12]}  x{len(names)}  e.g. {names[0]}")
    if len(sig) != 1:
        print("   !! prewall snapshots DIVERGE — pick one deliberately and record it")
        ok = False
    else:
        print("   all snapshots agree -> the root anchor is stable")
    for p, how in PREREQS:
        if p.is_file():
            print(f"[prereq] {p.name}: present ({md5(p)[:12]})")
        else:
            print(f"[prereq] {p.name}: MISSING -> regenerate with `py {how}`")
            ok = False
    if MANIFEST.is_file():
        man = json.loads(MANIFEST.read_text())
        print(f"[manifest] recorded {len(man.get('accepted', {}))} accepted block hashes")
    else:
        print("[manifest] none yet — run `check` after a verified build to record one")
    return ok


def cmd_regen(snap=None):
    snaps = prewall_anchors()
    assert snaps, "no prewall anchor"
    src = Path(snap) if snap else snaps[-1]
    print(f"[regen] full_skirt OFFLINE from {src.name} (the install is untouched)")
    r = subprocess.run([sys.executable, "-X", "utf8", "full_skirt.py",
                        "--bench-src", str(src)], cwd=HERE,
                       capture_output=True, text=True)
    tail = [ln for ln in r.stdout.splitlines() if ln.strip()][-4:]
    for ln in tail:
        print("   " + ln)
    if r.returncode != 0:
        print("   FAILED:\n" + r.stdout[-1500:] + r.stderr[-1500:])
        return False
    STAGE.mkdir(parents=True, exist_ok=True)
    for (bx, by) in CELLS:
        f = GEN_OUT / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if f.is_file():
            (STAGE / f.name).write_bytes(f.read_bytes())
    print(f"[regen] staged {len(list(STAGE.glob('*.ff9mesh')))} regenerated blocks -> {STAGE}")
    return True


def cmd_corner():
    """Build the accepted corner ON THE REGENERATED BASE, not on backups."""
    assert STAGE.is_dir(), "run `regen` first"
    env = dict(os.environ, FF9_BENCH_BASELINE=str(STAGE))
    print(f"[corner] FF9_BENCH_BASELINE={STAGE}")
    for verb in ("stage1", "stage2"):
        r = subprocess.run([sys.executable, "vcorner_transplant.py", verb],
                           cwd=HERE, capture_output=True, text=True, env=env)
        keep = [ln for ln in r.stdout.splitlines()
                if any(k in ln for k in ("TUCK WALL", "strip cover", "WELD AUDIT",
                                         "g_", "PASS", "FAIL", "!!"))]
        for ln in keep[:16]:
            print("   " + ln.strip())
        if r.returncode != 0:
            print("   FAILED:\n" + (r.stdout[-1200:] + r.stderr[-1200:]))
            return False
    return True


def cmd_check():
    """Does the regenerated+corner build match the LIVE, owner-accepted bench?"""
    from vcorner_transplant import OUTD2
    print("[check] regenerated build vs the live accepted bench")
    accepted, allsame = {}, True
    for (bx, by) in CELLS:
        live = LIVE / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if not live.is_file():
            continue
        hl = md5(live)
        accepted[f"{bx},{by}"] = hl
        built = OUTD2 / f"Block[{bx}][{by}] Terrain.ff9mesh" \
            if (bx, by) in CORNER_BLOCKS else STAGE / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if not built.is_file():
            print(f"   [{bx}][{by}]: no rebuilt file to compare")
            allsame = False
            continue
        hb = md5(built)
        same = hb == hl
        allsame &= same
        print(f"   [{bx}][{by}]: live={hl[:10]} rebuilt={hb[:10]} "
              f"-> {'MATCH' if same else 'DIFFERS'}")
    MANIFEST.write_text(json.dumps(
        {"accepted": accepted,
         "note": "md5 of the live, owner-accepted Disc9 bench Terrain blocks "
                 "(playtest 12). A rebuild that does not reproduce these is a "
                 "regression — diff it before deploying."}, indent=1))
    print(f"[check] manifest written -> {MANIFEST.name}")
    print(f"[check] {'FULL REPRODUCTION' if allsame else 'DIFFERENCES PRESENT'}")
    return allsame


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if verb == "verify":
        ok = cmd_verify()
    elif verb == "regen":
        ok = cmd_regen(sys.argv[2] if len(sys.argv) > 2 else None)
    elif verb == "corner":
        ok = cmd_corner()
    elif verb == "check":
        ok = cmd_check()
    elif verb == "all":
        ok = cmd_verify() and cmd_regen() and cmd_corner() and cmd_check()
    else:
        raise SystemExit(__doc__)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
