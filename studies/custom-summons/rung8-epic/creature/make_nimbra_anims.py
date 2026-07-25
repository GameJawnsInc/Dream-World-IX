"""RUNG 8 -- EMIT NIMBRA'S THREE CLIPS as engine-ready ``.anim`` JSON, and PROVE they satisfy the
kit's own authored-clip contract.

    py studies/custom-summons/rung8-epic/creature/make_nimbra_anims.py

Writes NOTHING to the game install:

    stage/creature/clips/emerge.anim | drift.anim | strike.anim   <- what `[[summon]] clips = [...]` eats
    stage/creature/CLIPS.json                                     <- keys, tick math, the TOML fragment
    creature/nimbra/*.anim                                        <- the same bytes, kept beside the build

--------------------------------------------------------------------------------------------------
 THE CLIP-NAMING QUESTION IS SETTLED -- and not by this lane
--------------------------------------------------------------------------------------------------
STORYBOARD 6.4 listed K2 (authored ``clips = [<paths>]``) as work still to do, and while this lane was
building the creature the kit lane LANDED it. So the answer is read off the shipped code, not chosen:

  * ``summons/deploy.py:authored_clip_paths`` tells an authored path list from a donor index list BY
    CONTENT -- all-digit entries mean donor indices, anything else means files. Our three named paths
    take the authored branch.
  * ``summons/deploy.py:clip_key_of`` gives a NON-numeric stem the key ``AUTHORED_CLIP_KEY_BASE +
    index`` = **60000 + i** (the kit's own new-anim mint band, clear of every stock key -- stock tops
    out at 14739). A numeric stem like ``0.anim`` would instead be taken at its word.
  * ``summons/deploy.py:clip_name_map`` then lets ``[[summon.staging.play]] clip = "emerge"`` resolve
    to that key, so the TOML stays readable while the on-disc file stays a key the engine is happy to
    treat as a clip NAME (``Path.GetFileNameWithoutExtension``, SFXDataMesh.cs:789).

**THEREFORE: ship NAMED clips, let the kit mint 60000/60001/60002, and write ``play.clip = "emerge"``.**
An earlier draft of this lane hedged by shipping a numeric set as well; that is now removed, because
shipping ``0.anim`` would opt into the pin-your-own-key branch and quietly leave the mint band.

NO ``3DModelAnimation`` REGISTRATION LINE is needed: the SFX route resolves a clip by literal asset
path, not through the DictionaryPatch animation table. Clips are RECAST-only; only the
``3DModel 6400 GEO_MON_B0_M400`` mint line needs the one relaunch.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
try:
    import ff9mapkit  # noqa: F401
except ImportError:
    sys.path.insert(0, str(ROOT / "ff9mapkit"))

import nimbra_clips as NC                                        # noqa: E402
import nimbra_spec as NS                                         # noqa: E402
from ff9mapkit.models import anim as manim                       # noqa: E402
from ff9mapkit.summons import deploy as sdeploy                  # noqa: E402

OUT = HERE / "nimbra"
STAGE = HERE.parent / "stage" / "creature"
CLIPDIR = STAGE / "clips"
TPS = 15.0          # the bench's Memoria.ini [Graphics] BattleTPS

#: THE ONE SOURCE OF TRUTH for the playlist and the window is the bench TOML's ``[summon.staging]``.
#: It used to be a hand-copied constant here ("STORYBOARD 3.2's playlist + window, verbatim"), and the
#: 2026-07-24 RETIME (STORYBOARD 11) found THREE independent copies of those numbers -- this one,
#: ``bench/build_rung8_bench.py``'s PLAY_SFX_TICK/DRAIN_TICK, and ``build_rung8_stage.py``'s ``play_at``
#: -- every one of which goes stale silently the moment the cast is re-cut. This lane now READS them.
BENCH_TOML = HERE.parent / "bench" / "rung8.field.toml"


def load_staging() -> tuple:
    """``(start, end, playlist)`` straight out of ``bench/rung8.field.toml``'s ``[summon.staging]``."""
    import tomllib
    st = tomllib.loads(BENCH_TOML.read_text(encoding="utf-8"))["summon"][0]["staging"]
    return int(st["start"]), int(st["end"]), [dict(p) for p in st["play"]]


def main():
    bones = NS.build_bones()
    WINDOW_START, WINDOW_END, PLAYLIST = load_staging()
    #: the Speed each clip is played at on its FIRST appearance in the playlist (a clip may appear more
    #: than once at different divisors -- `drift` is the look at Speed 3 and the dissolve at Speed 1)
    first_speed = {}
    for p in PLAYLIST:
        first_speed.setdefault(str(p["clip"]), int(p.get("speed", 1)))
    OUT.mkdir(parents=True, exist_ok=True)
    CLIPDIR.mkdir(parents=True, exist_ok=True)

    print(f"NIMBRA clips -> {NS.GEO_NAME} ({NS.GEO_ID})")
    written, index = [], []
    for i, (name, spec) in enumerate(NC.all_clips().items()):
        clip = manim.new_clip(bones, spec["curves"], name=name, sample_rate=NC.RATE)
        text = manim.clip_to_anim_json(clip)

        # every skeleton bone must carry a channel: new_clip's rest-fill is what stops the engine's
        # head-focus offset accumulating on an unkeyed neck (anim.py:551-556)
        doc = json.loads(text)
        paths = {e["bone"] for e in doc["transform"]}
        assert len(paths) == len(bones), f"{name}: {len(paths)} bone channels, expected {len(bones)}"

        dest = CLIPDIR / f"{name}.anim"
        dest.write_text(text, encoding="utf-8", newline="\n")
        (OUT / f"{name}.anim").write_text(text, encoding="utf-8", newline="\n")
        written.append(dest)

        # THE KEY IS THE KIT'S, NOT OURS -- ask the shipped function rather than reproducing its rule
        key = sdeploy.clip_key_of(i, dest)
        # ...and the FRAME COUNT is read back through the kit's own deriver, so a disagreement between
        # what we authored and what the deploy-time coverage check will compute is caught HERE
        frames = sdeploy.anim_frame_count(dest)
        assert frames == spec["frames"], (f"{name}: kit derives {frames} frames, authored "
                                          f"{spec['frames']} -- the tick table would be wrong")
        speed = first_speed.get(name, spec["speed"])
        ticks = -(-frames // speed)                         # ceil(frames / Speed), SFXDataMesh.cs:852
        index.append({
            "name": name, "kit_key": key, "speed": speed, "frames": frames,
            "playlist_speeds": [int(p.get("speed", 1)) for p in PLAYLIST if str(p["clip"]) == name],
            "length_s": round((frames - 1) / NC.RATE, 6),
            "clip_file": str(dest.relative_to(STAGE)).replace("\\", "/"),
            "manifest_path": f"Animations/{NS.GEO_ID}/{key}",
            "disc_path": f"StreamingAssets/Assets/Resources/Animations/{NS.GEO_ID}/{key}.anim",
            "sequence_ticks": ticks, "sequence_seconds": round(ticks / TPS, 3),
            "keyed_bones": sorted(spec["curves"]), "bytes": len(text.encode("utf-8")),
        })
        print(f"  {name:<7} kit key {key}  {frames:>3} frames @{NC.RATE:g}fps  Speed {speed}"
              f"  -> {ticks:>3} ticks ({ticks / TPS:.2f}s)  {len(text) // 1024} KiB")

    # ---- the tick table, re-derived by THE KIT'S OWN coverage checker ------------------------------
    spec = {"clips": [str(p) for p in written],
            "staging_curves": {"start": WINDOW_START, "end": WINDOW_END, "play": PLAYLIST}}
    cov = sdeploy.playlist_coverage(spec)
    assert cov is not None, "playlist_coverage returned None -- the kit could not read our clips"
    print(f"  kit coverage: playlist {cov['playlist_ticks']} ticks vs window {cov['window']} "
          f"(short_by {cov['short_by']})  [{', '.join(cov['detail'])}]")
    assert cov["short_by"] <= 0, ("THE ANIMATION-PLAYLIST LAW: the playlist would run out and FREEZE "
                                  f"on a last frame for {cov['short_by']} ticks")
    by = {c["name"]: c for c in index}
    # DERIVED cross-check, not a retyped table: every playlist entry's ceil(frames/Speed) must sum to
    # exactly what the kit computed. (This replaces a hardcoded `== (45, 75, 30)`, which was a fourth
    # copy of the pre-retime tick table and would have had to be edited by hand every re-cut.)
    ours = sum(-(-by[str(p["clip"])]["frames"] // int(p.get("speed", 1))) * int(p.get("repeat", 1))
               for p in PLAYLIST)
    assert ours == cov["playlist_ticks"], (
        f"this lane derives {ours} playlist ticks, the kit derives {cov['playlist_ticks']}")

    doc = {
        "geo": NS.GEO_NAME, "geo_id": NS.GEO_ID, "rate": NC.RATE, "battle_tps": TPS,
        "authored_clip_key_base": sdeploy.AUTHORED_CLIP_KEY_BASE,
        "clips": index,
        "playlist": PLAYLIST, "window": {"start": WINDOW_START, "end": WINDOW_END},
        "playlist_ticks": cov["playlist_ticks"],
        "name_map": sdeploy.clip_name_map([str(p) for p in written]),
        "toml_fragment": {
            "model": "studies/custom-summons/rung8-epic/stage/creature/6400.fbx",
            "id": NS.GEO_ID, "name": NS.GEO_NAME, "group": "MON",
            "clips": [f"studies/custom-summons/rung8-epic/stage/creature/{c['clip_file']}"
                      for c in index],
        },
        "notes": [
            "clips are RECAST-only: no 3DModelAnimation line (the SFX route loads by literal path)",
            "only the `3DModel 6400 GEO_MON_B0_M400` mint line needs the one relaunch",
            "the .png must be staged beside the .fbx -- _stage_model globs the FBX's own folder",
        ],
    }
    (STAGE / "CLIPS.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(STAGE / "CLIPS.json", OUT / "CLIPS.json")
    print(f"  wrote {CLIPDIR} + CLIPS.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
