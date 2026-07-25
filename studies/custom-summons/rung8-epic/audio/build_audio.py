"""Rung 8 (NIMBRA) -- THE AUDIO build + validate.

Renders the three synthesized cues (100001 ``nimbra_drone``, 100002 ``nimbra_whispers``, 100003
``nimbra_strike``; see STORYBOARD.md §5), encodes each to Ogg Vorbis via the kit's own
``ff9mapkit.sound.encode_ogg`` (the exact function the mint-a-new-sfx-id lane uses), stages the
result under ``rung8-epic/stage/audio/`` in the layout a real mod-folder deploy would use, and
validates: decodes cleanly, duration matches the storyboard's §5 table, and peak stays under the
per-cue budget both pre- and post-encode.

DOES NOT TOUCH THE LIVE GAME INSTALL. This calls ``sound.encode_ogg`` (a pure ffmpeg transcode,
no install path resolution at all) -- never ``sound.mint_song`` (which reads the install's
``resources.assets`` for its base manifest and is therefore the WIRING lane's job, done for real at
deploy time). ``manifest_fragment.json`` (written alongside the audio) is the entries that lane
would append, precomputed here so it doesn't have to re-derive them.

100% synthesized content; this script and its three cue modules are the committable source of
truth. Zero Square-Enix bytes anywhere in the chain.

Run:
    py studies/custom-summons/rung8-epic/audio/build_audio.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent                 # .../rung8-epic/audio
RUNG8 = HERE.parent                                     # .../rung8-epic
STUDY = RUNG8.parent                                    # .../custom-summons
REPO = STUDY.parents[1]                                 # studies/custom-summons -> <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(HERE))

from ff9mapkit import sound  # noqa: E402

import make_nimbra_drone as drone_mod       # noqa: E402
import make_nimbra_whispers as whispers_mod  # noqa: E402
import make_nimbra_strike as strike_mod      # noqa: E402

STAGE = RUNG8 / "stage" / "audio"
WAV_DIR = STAGE / "wav"
MOD_DIR = STAGE / "mod"                      # mirrors <mod_folder>/StreamingAssets/Assets/Resources/Sounds/...

SR = 44100

CUES = [
    # (module, mono/stereo channels, budget peak)
    (drone_mod, 1, drone_mod.PEAK_BUDGET),
    (whispers_mod, 2, whispers_mod.PEAK_BUDGET),
    (strike_mod, 1, strike_mod.PEAK_BUDGET),
]

DURATION_TOL_S = 0.08        # ffmpeg/Vorbis framing rounds to the nearest packet; generous but tight
PEAK_TOL_FRAC = 1.05         # 5% headroom on the budget check (Vorbis reconstruction can overshoot slightly)


# --------------------------------------------------------------------------- WAV write
def write_wav(path: Path, x: np.ndarray, sr: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    x = np.clip(x, -1.0, 1.0)
    nch = 1 if x.ndim == 1 else x.shape[1]
    data = x.reshape(-1)                     # row-major flatten of (n,2) IS correctly interleaved L,R,L,R,...
    pcm = (data * 32767.0).astype("<i2")
    with wave.open(str(path), "w") as w:
        w.setnchannels(nch)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


# --------------------------------------------------------------------------- ffprobe / decode-back
def ffprobe_info(path: Path) -> dict:
    ffprobe = sound.find_ffmpeg().replace("ffmpeg", "ffprobe")
    # sound.find_ffmpeg() resolves via shutil.which/$FFMPEG; ffprobe ships alongside every ffmpeg
    # build this kit targets, so swapping the exe name in the same directory is safe -- verified
    # against the actual resolved path below, not assumed.
    import shutil
    if not shutil.which(ffprobe) and not Path(ffprobe).exists():
        ffprobe = shutil.which("ffprobe") or "ffprobe"
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_name",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(out.stdout)
    duration = float(data["format"]["duration"])
    codec = data.get("streams", [{}])[0].get("codec_name", "")
    return {"duration": duration, "codec": codec}


def decode_ogg_peak(path: Path, sr: int, channels: int) -> float:
    """Decode the ENCODED ogg back to raw float PCM via ffmpeg and return its peak -- the real
    post-lossy-encode level, not just the pre-encode WAV's (Vorbis can overshoot slightly)."""
    ffmpeg = sound.find_ffmpeg()
    proc = subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(path),
         "-f", "f32le", "-acodec", "pcm_f32le", "-ar", str(sr), "-ac", str(channels), "pipe:1"],
        capture_output=True, check=True,
    )
    arr = np.frombuffer(proc.stdout, dtype="<f4")
    return float(np.max(np.abs(arr))) if arr.size else 0.0


# --------------------------------------------------------------------------- main
def build_one(mod, channels: int, budget: float) -> dict:
    name = mod.NAME
    x = mod.render(sr=SR)
    pre_peak = float(np.max(np.abs(x)))
    duration_authored = len(x) / SR if channels == 1 else x.shape[0] / SR

    wav_path = WAV_DIR / f"{name}.wav"
    write_wav(wav_path, x, SR)

    dest_rel = sound.override_rel_path(mod.RESOURCE_ID)      # StreamingAssets/Assets/Resources/Sounds/...
    ogg_path = MOD_DIR / dest_rel
    sound.encode_ogg(wav_path, ogg_path, quality=6)           # raises on a bad encode -- no silent corrupt file

    info = ffprobe_info(ogg_path)
    post_peak = decode_ogg_peak(ogg_path, SR, channels)

    checks = {
        "decodes": info["codec"] == "vorbis" and ogg_path.read_bytes()[:4] == b"OggS",
        "duration_ok": abs(info["duration"] - mod.DURATION_S) <= DURATION_TOL_S,
        "pre_peak_under_budget": pre_peak <= budget * PEAK_TOL_FRAC,
        "post_peak_under_budget": post_peak <= budget * PEAK_TOL_FRAC,
    }
    result = {
        "name": name,
        "sound_id": mod.SOUND_ID,
        "resource_id": mod.RESOURCE_ID,
        "channels": channels,
        "wav_path": str(wav_path),
        "ogg_path": str(ogg_path),
        "target_duration_s": mod.DURATION_S,
        "authored_duration_s": round(duration_authored, 4),
        "probed_duration_s": round(info["duration"], 4),
        "codec": info["codec"],
        "peak_budget": budget,
        "pre_encode_peak": round(pre_peak, 4),
        "post_encode_peak": round(post_peak, 4),
        "checks": checks,
        "pass": all(checks.values()),
    }
    return result


def main() -> int:
    WAV_DIR.mkdir(parents=True, exist_ok=True)
    MOD_DIR.mkdir(parents=True, exist_ok=True)

    results = [build_one(mod, ch, budget) for mod, ch, budget in CUES]

    manifest_fragment = [
        {"id": r["sound_id"], "resource_id": r["resource_id"], "type": "SoundEffect"} for r in results
    ]
    (STAGE / "manifest_fragment.json").write_text(json.dumps(manifest_fragment, indent=2), encoding="utf-8")

    report_path = STAGE / "validation_report.json"
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"{'cue':<18} {'id':>7} {'dur target':>10} {'dur probed':>10} "
          f"{'peak budget':>11} {'pre-peak':>9} {'post-peak':>9}  result")
    all_ok = True
    for r in results:
        ok = r["pass"]
        all_ok &= ok
        print(f"{r['name']:<18} {r['sound_id']:>7} {r['target_duration_s']:>10.2f} "
              f"{r['probed_duration_s']:>10.3f} {r['peak_budget']:>11.2f} "
              f"{r['pre_encode_peak']:>9.4f} {r['post_encode_peak']:>9.4f}  {'PASS' if ok else 'FAIL'}")
        if not ok:
            for k, v in r["checks"].items():
                if not v:
                    print(f"    FAILED CHECK: {k}")

    print()
    print(f"wav masters   : {WAV_DIR}")
    print(f"staged oggs   : {MOD_DIR}")
    print(f"manifest frag : {STAGE / 'manifest_fragment.json'}")
    print(f"report        : {report_path}")
    print()
    print("RELAUNCH LAW (STORYBOARD.md §5.2): SoundMetaData's id table loads ONCE at process start.")
    print("These three ids (100001-100003) will not resolve on an already-running game even after a")
    print("real mint_song deploy -- one relaunch is required before the first cast, same relaunch that")
    print("registers the `3DModel 6400 GEO_MON_B0_M400` DictionaryPatch line (rung 8 wiring lane).")
    print("Silence on cast 1 with everything else working = a missed relaunch, not a design failure.")

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
