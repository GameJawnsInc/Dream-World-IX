# Rung 8 (NIMBRA) — THE AUDIO lane

Three synthesized SFX cues for the NIMBRA cast, per `../STORYBOARD.md` §5. Everything in this
folder and everything it produces is **100% original** — numpy DSP + stdlib `wave`, zero
Square-Enix bytes, zero sampled material. Fully committable (unlike a `.seq` edit against a stock
file, which can never be committed — see `rung2-seq-hot-edit/build_rung2.py`'s docstring).

## The three cues

| Id | Resource id | Length | File | Fires (per the `.seq`, Appendix A) |
|---|---|---|---|---|
| **100001** | `Sounds02/SE00/nimbra_drone` | **8.0 s**, mono | `make_nimbra_drone.py` | `PlaySound` t≈10 (P0) → `StopSound` t=135 (P5) |
| **100002** | `Sounds02/SE00/nimbra_whispers` | **4.0 s**, **stereo** | `make_nimbra_whispers.py` | `PlaySound` t≈10 (P0, with the dim) — once, not twice |
| **100003** | `Sounds02/SE00/nimbra_strike` | **2.0 s**, mono | `make_nimbra_strike.py` | `PlaySound` t=83 (P4), same tick as the relight, `RiftFlash` and the lunge peak |

> **RE-CUT 2026-07-24 — [`STORYBOARD.md` §11](../STORYBOARD.md) (THE RETIME).** The cast went from 32.3 s
> to **9.3 s**, so all three cues were re-rendered at new lengths (34.0/7.0/2.5 → 8.0/4.0/2.0 s). **Only
> time constants moved** — every recipe below still describes the synthesis exactly; the ids, resource
> ids, peak budgets and the `.seq`'s `Volume=` lines are unchanged. Two consequences worth knowing:
> the drone now **fades out naturally** at t ≈ 130 so `StopSound` is a safety rather than a 26-second-early
> cut, and the strike tick's voice stack is now drone + sting instead of drone + whispers + sting, which
> is real headroom against the no-limiter constraint below.

Ids continue from rung 3's precedent (`sound.MINT_ID_BASE["sfx"] == 100000`, minted there as the
probe chime). **100000 is left alone** — NIMBRA takes 100001-100003.

`nimbra_whispers` is stereo **by construction, not decoration**: the `.seq` issues exactly ONE
`PlaySound` for this cue (one `Panning=` argument for the whole call), so the storyboard's "six
bursts hard-panned alternately L/R" can only exist by baking the pan into the file itself at
synthesis time. A mono file would collapse that into nothing.

## DSP method (no scipy, no soundfile — neither is on this box)

`dsp.py` is the shared primitive set, pure `numpy` + stdlib:

- **`bandlimited_saw`** — additive sawtooth (Σ (-1)^(k+1) sin(2πkft)/k, capped below Nyquist), the
  scipy-free stand-in for a proper band-limited oscillator at the drone's low fundamentals.
- **`pink_noise`** — FFT-domain 1/√f shaping of white noise.
- **`bandpass_fft`** — zero every rFFT bin outside `[lo, hi]` with a raised-cosine taper at each
  edge (the scipy-free stand-in for a Butterworth bandpass; fine for atmosphere/particle-bed noise
  where exact filter shape doesn't matter).
- **`chirp_sine`** — a phase-continuous frequency sweep (integrates instantaneous frequency via
  `cumsum`, so there's no discontinuity click a naive `sin(2π·f(t)·t)` would introduce).
- **`fade_env`** — symmetric raised-cosine fade in/out.
- **`swell_env`** — THE REVERSED ENVELOPE the whispers cue needs: slow sine ease-in attack, hard
  cubic-ease-out release ("slow in, hard out").
- **`ramp_in`** — a *late-arriving* layer (0 until `start_s`, then ramps to 1 and holds) — the
  drone's 110 Hz partial "entering at 8s".

Each cue module (`make_nimbra_*.py`) is a standalone script: `render(sr=44100) -> np.ndarray`
(float32, `[-1, 1]`) plus a `__main__` that writes a quick preview WAV for by-ear checking without
running the full build.

### The recipes, mapped to STORYBOARD.md §5 line-for-line

- **`nimbra_drone`** — two "partials" at 55.0/82.5 Hz (bare fifth), each realized as a **pair** of
  sub-oscillators at ±3 cents (sine/saw blend); the ~0.095 Hz difference-tone between the pair *is*
  the "slow beating" — it falls out of the detuning, no separate LFO needed. A third, plain-sine
  110 Hz partial ramps in at **t=2.2s** (`ramp_in`, **1.0s** ramp — the same ~27% of the cue as the old
  8s-of-34s, so the octave still arrives with the creature). A pink-noise "breath" bandpassed to
  300-900 Hz is amplitude-modulated at 0.13 Hz. **1.5s fade-in / 2.0s fade-out** on the whole mix.
  At 8 s the ±3-cent beat (≈10.5 s period) and the 0.13 Hz breath (7.7 s) each land as ONE slow swell
  rather than a repeating pulse — deliberate: raising either rate to "fit more cycles in" turns a drone
  into a tremolo.
- **`nimbra_whispers`** — **still six** band-passed (1200-3500 Hz) noise bursts, now at onsets
  `[0, 0.55, 1.10, 1.65, 2.20, 2.75]`s, each shaped by `swell_env` (**0.8s** slow attack, **0.15s** hard
  release) and written hard-panned to alternating channels (even index → Left, odd → Right). Onsets and
  attack tighten together, so the overlap pattern is the same shape at 4/7 scale. A center
  (both-channel) 220 Hz→(minor-third-up) `chirp_sine` rises across the whole **4.0s** and fades out
  mid-rise — it never resolves to a landing pitch.
- **`nimbra_strike`** — a 45 Hz sine "thump" (25ms linear attack, `exp(-t/0.28s)` decay) plus a
  4-partial inharmonic "ring" at `640 × [1.0, 2.76, 5.40, 8.93]` Hz (deliberately non-integer
  ratios — "a bell that is not a bell"; the ratios are **unchanged**), common `exp(-t/0.45s)` decay,
  distinct per-partial phases so they don't null on top of each other. The decays tightened with the
  length so the sting still ends on its own tail (`exp(-2.0/0.45) = 0.011`) rather than on the click
  guard. A 50ms tail fade guards the hard 2.0s cutoff.

## Peak budgets (a hard constraint, not a preference — STORYBOARD.md §5.1)

There is **no limiter or compressor anywhere in the SaXAudio chain** — any voice stack on
`BusSoundEffect` hard-clips. Each cue is authored *under* its budget (0.45 / 0.40 / 0.55) with a
little headroom (targets 0.40 / 0.36 / 0.50), and `build_audio.py` verifies the peak **after** the
Vorbis round-trip too (encoders can overshoot the source peak slightly). The `.seq`'s own
`PlaySound … Volume=0.55/0.5/0.7` lines are the *second*, independent attenuation — both exist,
neither substitutes for the other.

## Build + validate

```
py studies/custom-summons/rung8-epic/audio/build_audio.py
```

For each cue: renders the WAV master, encodes it to Ogg Vorbis via `ff9mapkit.sound.encode_ogg`
(the exact function the mint-a-new-sfx-id lane uses — **not** `sound.mint_song`, which reads the
live install's `resources.assets` for its base manifest; that's the wiring lane's job, done for
real at deploy time), stages the result under `stage/audio/` in the layout a real mod-folder
deploy would use, and validates:

1. **decodes** — `ffprobe` reports `codec_name == "vorbis"` and the file starts `OggS`.
2. **duration_ok** — matches the storyboard's §5 "Length" column within 0.08s.
3. **pre/post_peak_under_budget** — the WAV master's peak *and* the peak after decoding the
   encoded `.ogg` back to raw PCM (via `ffmpeg … -f f32le …`) both stay at or under budget
   (with 5% slack for encoder reconstruction).

Outputs (git-ignorable build artifacts, not the committed source):

```
stage/audio/wav/nimbra_{drone,whispers,strike}.wav      -- masters, for by-ear review
stage/audio/mod/StreamingAssets/Assets/Resources/Sounds/Sounds02/SE00/nimbra_*.ogg
                                                          -- exactly where a mod-folder deploy drops them
stage/audio/manifest_fragment.json                       -- the 3 entries the wiring lane appends
                                                             to the SoundEffectMetaData.txt override
stage/audio/validation_report.json                       -- the full per-cue check matrix
```

**Last run (2026-07-24, post-retime): all 3 cues PASS** — 8.000 / 4.000 / 2.000 s probed, peaks
**0.4019 / 0.3523 / 0.5037** post-encode against budgets 0.45 / 0.40 / 0.55. Re-run any time; every step
is idempotent and deterministic (seeded RNG).

`test_nimbra_audio.py` — an offline (`numpy`-only, no ffmpeg) pytest suite covering the DSP
primitives and each cue's shape/duration/peak/character (14 tests, all passing). Run it standalone
with `py -m pytest studies/custom-summons/rung8-epic/audio/test_nimbra_audio.py` when iterating on
the DSP without wanting the full ffmpeg round-trip every time.

## Does NOT touch the live game install

`build_audio.py` calls `sound.encode_ogg` (a pure ffmpeg transcode — no install path resolution at
all). It never calls `sound.mint_song`, which reads the live install's `resources.assets` to build
its base manifest and writes into a real mod folder — that is the WIRING lane's job, applied at
deploy time (the orchestrator, not this script). `manifest_fragment.json` is precomputed here so
that lane doesn't have to re-derive the three entries by hand; it's the literal
`{"id", "resource_id", "type"}` triples `sound.serialize_manifest` expects, ready to merge with
whatever else the deploy's SFX manifest already carries.

To actually mint these for real (wiring lane, not this round):

```python
from ff9mapkit import sound
sound.mint_song(wav_or_source_path, mod_root, kind="sfx",
                 new_id=100001, resource_id="Sounds02/SE00/nimbra_drone")
# … 100002 / 100003 the same way, or merge manifest_fragment.json + copy the staged .ogg files
# directly into place if the wavs here are treated as already-final masters.
```

## THE RELAUNCH LAW (STORYBOARD.md §5.2 — restated, do not skip)

`SoundMetaData`'s id table loads **once at process start**. Three brand-new ids ⇒ **one relaunch,
after minting and before the first cast** — the same relaunch that registers the
`3DModel 6400 GEO_MON_B0_M400` DictionaryPatch line for the creature. One relaunch covers both.

> Silence on cast 1 with everything else (particles, creature, choreography) working correctly is
> **a missed relaunch, not a synthesis failure.** Diagnose in that order. Whether *replacing* the
> `.ogg` content at an already-registered id needs another relaunch is unproven — assume yes until
> measured (same open question the storyboard flags).
>
> **The retime is the first round where that open question BITES**, because 100001-100003 are already
> registered and only their content changed. STORYBOARD §11.7 rules it: assume yes. It is free to be safe
> — the same redeploy re-tunes `Actions.csv`, which is launch-gated anyway — and it is also a free chance
> to finally measure it (deploy the audio step alone, cast without relaunching, note whether the drone
> runs 8 s or 34 s).

## Provenance

Every byte in `stage/audio/` is generated by the scripts in this folder from mathematical DSP —
noise fields, additive oscillators, envelopes — seeded and reproducible, with zero reference to or
extraction from any Square-Enix asset. The generator code is the committable artifact; the audio
files are reproducible build output.
