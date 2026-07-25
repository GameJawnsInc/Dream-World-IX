#!/usr/bin/env python3
"""RUNG 8 -- stage the NIMBRA effect folder OFFLINE, through the productized kit lane.

    py build_rung8_stage.py                      # stage into ./stage/ using input stubs where the
                                                 # creature lane's real files are not there yet
    py build_rung8_stage.py --check              # stage, then re-lint every emitted file and diff the
                                                 # emitted manifest against the storyboard's numbers

WHAT THIS PROVES. It is not a mock: it drives the real ``ff9mapkit.summons.deploy`` overlay emitter with
the real ``nimbra.summon.toml`` block, so what lands in ``stage/FF9CustomMap/StreamingAssets/Data/
SpecialEffects/ef091/`` is byte-for-byte what a live ``summon-deploy`` would write. That is the whole
point of wiring ``staging = "curves"`` FOR REAL this round -- the curve table in the TOML is what
produced the manifest you can read, not a hand-written sample of one.

IT NEVER TOUCHES THE GAME. ``game=None`` throughout: the authored lane reads no donor ``.seq``, opens no
``ef###.bytes``, and needs no install. The mod root is a directory under ``stage/``. The orchestrator
deploys after review.

THE INPUT STUBS. The creature lane owns ``nimbra/6400.fbx`` and ``nimbra/{emerge,drift,strike}.anim``.
Until those land, ``--stub-inputs`` (ON by default) writes obvious placeholders under
``stage/_stub-inputs/`` so the whole emit path runs today: a text FBX stub (the emitter only copies its
bytes) and three ``.anim`` clips shaped exactly like ``models/anim.py:clip_to_anim_json``'s output, with
the storyboard's frame counts (90 / 75 / 60 at 30 fps) so the playlist-coverage arithmetic is REAL.
Every stub file carries a banner. Point ``--creature-dir`` at the real artifacts to swap them in --
nothing else changes.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.summons import deploy as D          # noqa: E402
from ff9mapkit.summons import seqlint as SL        # noqa: E402

STUB_BANNER = "STUB -- NOT THE REAL ARTIFACT. The creature lane (make_nimbra.py) owns this file."

#: THE SHARED-STAGE SEAM (integration fix). ``stage/`` is not this lane's private scratch -- the AUDIO lane
#: writes ``stage/audio/``, the CREATURE lane writes ``stage/creature/``, and the BENCH lane writes
#: ``stage/final/``. A blanket ``rmtree(stage)`` on ``--clean`` silently destroyed all three (it did, once).
#: ``--clean`` now removes ONLY the subtrees this script produces.
OWNED = ("FF9CustomMap", "_stub-inputs", ".summon-revert", ".summon-backups")

#: the storyboard's authored clip lengths (section 1.7), used to shape the stubs so that the
#: playlist-coverage check exercises the REAL arithmetic rather than a placeholder's.
STUB_CLIPS = {"emerge": 90, "drift": 75, "strike": 60}
STUB_FPS = 30.0


def _stub_anim(name: str, frames: int) -> str:
    """A minimal but SCHEMA-TRUE ``.anim`` JSON: one bone, rest-pose keys at frame 0 and frame N-1, so
    ``deploy.anim_frame_count`` derives exactly ``frames`` (round(maxTime * frameRate) + 1)."""
    last = (frames - 1) / STUB_FPS
    doc = {
        "_stub": STUB_BANNER,
        "name": name,
        "frameRate": STUB_FPS,
        "transform": [{
            "bone": "bone000",
            "localRotation": [{"time": 0.0, "x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                              {"time": last, "x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}],
            "localPosition": [{"time": 0.0, "x": 0.0, "y": 0.0, "z": 0.0},
                              {"time": last, "x": 0.0, "y": 0.0, "z": 0.0}],
            "localScale": [{"time": 0.0, "x": 1.0, "y": 1.0, "z": 1.0},
                           {"time": last, "x": 1.0, "y": 1.0, "z": 1.0}],
        }],
    }
    return json.dumps(doc, indent=2) + "\n"


def make_stubs(out: Path, want: set) -> list:
    """Write a placeholder for each REQUESTED name that the creature lane has not produced yet. Per-file,
    not all-or-nothing: the moment ``creature/nimbra/6400.fbx`` exists the real mesh is used and only the
    clips stay stubbed."""
    out.mkdir(parents=True, exist_ok=True)
    made = []
    if "6400.fbx" in want:
        (out / "6400.fbx").write_text(
            f"; {STUB_BANNER}\n; A real Kaydara/ASCII FBX goes here (models/fbx_skin.py:emit_skinned_fbx).\n"
            "; The deploy emitter only COPIES these bytes, so the pipeline runs with a placeholder.\n"
            "; It references 6400.png by bare name so the texture check has something to see.\n",
            encoding="utf-8", newline="\n")
        (out / "6400.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"STUB-TEXTURE")
        made.append("6400.fbx")
    for name, frames in STUB_CLIPS.items():
        if f"{name}.anim" in want:
            (out / f"{name}.anim").write_text(_stub_anim(name, frames), encoding="utf-8", newline="\n")
            made.append(f"{name}.anim")
    return made


def resolve_block(toml_path: Path, creature_dir: Path, stub_dir: Path, *, stub: bool) -> tuple:
    """The first ``[[summon]]`` table, with every relative path made absolute: study-local files
    (``nimbra.seq``, the particle ``.sfxmodel``s) against this folder, creature-lane files
    (``nimbra/...``) against ``creature_dir`` -- falling back to a stub in ``stub_dir`` per missing file."""
    block = dict(tomllib.loads(toml_path.read_text(encoding="utf-8"))["summon"][0])
    missing: set = set()

    def fix(p: str) -> str:
        raw = Path(p)
        if raw.is_absolute():
            return str(raw)
        if raw.parts and raw.parts[0] == "nimbra":
            real = creature_dir / Path(*raw.parts[1:])
            if real.is_file() or not stub:
                return str(real)
            missing.add(real.name)
            return str(stub_dir / real.name)
        return str(HERE / raw)

    block["model"] = fix(block["model"])
    block["sequence"] = fix(block["sequence"])
    block["clips"] = [fix(c) for c in block["clips"]]
    block["particles"] = [fix(c) for c in block["particles"]]
    return block, missing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE / "stage"), help="staging root (default ./stage)")
    ap.add_argument("--creature-dir", default=str(HERE / "creature" / "nimbra"),
                    help="where the creature lane's 6400.fbx + *.anim live "
                         "(default ./creature/nimbra; anything missing there is stubbed)")
    ap.add_argument("--no-stub-inputs", dest="stub", action="store_false",
                    help="do NOT synthesize placeholders -- fail if a real input is missing")
    ap.add_argument("--check", action="store_true", help="re-lint + report the emitted set")
    ap.add_argument("--clean", action="store_true",
                    help=f"wipe THIS lane's outputs ({'/'.join(OWNED)}) -- never the sibling lanes' "
                         f"stage/audio, stage/creature or stage/final")
    args = ap.parse_args()

    out = Path(args.out)
    if args.clean and out.exists():
        for name in OWNED:                       # scoped, not rmtree(out) -- see OWNED
            victim = out / name
            if victim.is_dir():
                shutil.rmtree(victim)
            elif victim.exists():
                victim.unlink()
    creature = Path(args.creature_dir)
    stub_dir = out / "_stub-inputs"
    block, missing = resolve_block(HERE / "nimbra.summon.toml", creature, stub_dir, stub=args.stub)
    if missing:
        made = make_stubs(stub_dir, missing)
        print(f"creature lane: {creature}")
        print(f"  *** {len(made)} PLACEHOLDER(S) in {stub_dir}: {', '.join(made)} -- "
              f"swap in the real artifacts and re-run ***")
    else:
        print(f"creature lane: {creature}  (all real -- no placeholders)")

    mod_root = out / "FF9CustomMap"

    try:
        # game=None on purpose: the authored lane reads NOTHING from the install.
        res = D.emit_overlay(block, mod_root, None, work_dir=out)
    except D.SummonDeployError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2

    spec = res["spec"]
    print(f"\nstaged {spec['name']} (id {spec['id']}) -> private ef{spec['private_ef']:03d}, "
          f"lane={res['lane']}, staging={spec['staging']}")
    print(f"  mod root : {mod_root}")
    print(f"  host .seq: {res['seq']['seq_dest']}  (AUTHORED, verbatim from {Path(res['seq']['seq_source']).name})")
    ov = res["overlay"]
    print(f"  manifest : {ov['manifest_dest']}")
    print(f"  filelist : {ov['filelist_dest']}")
    for c in ov.get("clip_files", []):
        print(f"  clip     : {c['name']:<8} -> Animations/{spec['id']}/{c['key']}")
    for p in ov.get("particles", []):
        print(f"  particle : {p}")
    cov = ov.get("playlist_coverage")
    if cov:
        print(f"  playlist : {cov['playlist_ticks']} ticks over a {cov['window']}-tick window "
              f"({', '.join(cov['detail'])})")
        if cov.get("nonunit_speeds"):
            print(f"  *** THE SPEED-DIVISOR DEFECT (STORYBOARD 11.9): {cov['nonunit_speeds']} -- a clip "
                  f"at Speed s advances s^2 frames/tick, finishes after 1/s of its entry and FREEZES. "
                  f"Size the CLIP to the beat and keep every speed = 1. ***")
    print(f"  revert   : {res['revert_script']}")

    if args.check:
        return check(res, mod_root)
    return 0


def check(res: dict, mod_root: Path) -> int:
    """Re-lint everything that landed, and re-derive the storyboard's own numbers from the EMITTED file."""
    print("\n--- check ---")
    rc = 0
    spec = res["spec"]
    rep = SL.lint_seq_file(res["seq"]["seq_dest"], private_ef=spec["private_ef"],
                           particles=[Path(p).name for p in (spec.get("particles") or [])])
    print(f"  .seq        : {len(rep.errors)} error(s), {len(rep.warnings)} warning(s), "
          f"{rep.total_ticks} fixed-Wait ticks")
    for p in rep.problems:
        print(f"      {p}")
    rc |= 2 if rep.errors else 0

    for f in sorted(Path(res["overlay"]["manifest_dest"]).parent.glob("*.sfxmodel")):
        problems = SL.lint_sfxmodel_file(f)
        print(f"  {f.name:<28}: {len(problems)} problem(s)")
        for m in problems:
            print(f"      {m}")
        rc |= 2 if problems else 0

    man = json.loads(Path(res["overlay"]["manifest_dest"]).read_text(encoding="utf-8"))
    fbx = man["FBX"][0]
    play_at = 25                        # nimbra.seq: the fixed wait before PlaySFX (15) + the ~10-tick
                                        # clip-bound budget. RETIMED from 150 -- STORYBOARD 11.2.
    end = int(fbx["End"])
    print(f"  two clocks  : PlaySFX at tick ~{play_at}, FBX window {fbx['Start']}..{fbx['End']} "
          f"=> the instance drains at ~{play_at + end} (STORYBOARD 11.2 says 135)")
    for curve in ("Movement", "Rotation", "Scaling"):
        total = sum(int(p["Duration"]) for p in fbx[curve])
        flag = "ok" if total == end - int(fbx["Start"]) else "MISMATCH"
        print(f"  {curve:<12}: {len(fbx[curve])} piece(s), {total} ticks [{flag}]")
        rc |= 0 if flag == "ok" else 2
    print(f"  Animations  : {len(fbx['Animations'])} entr(y/ies) -> "
          f"{[e['Path'].rsplit('/', 1)[-1] + '@' + e.get('Speed', '1') for e in fbx['Animations']]}")
    fl = Path(res["overlay"]["filelist_dest"]).read_bytes()
    ok = fl.count(b" ") == 1 and b"\t" not in fl and fl.startswith(b"Model ")
    print(f"  FileList.txt: {fl!r} [{'ok' if ok else 'BAD GRAMMAR -- single spaces only'}]")
    rc |= 0 if ok else 2
    print("\n" + ("CHECK CLEAN" if rc == 0 else "CHECK FAILED"))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
