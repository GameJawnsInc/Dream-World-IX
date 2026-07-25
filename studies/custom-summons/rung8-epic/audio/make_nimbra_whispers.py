"""Rung 8 (NIMBRA) -- cue 100002 ``nimbra_whispers``: the P1 swell.

Per STORYBOARD.md §5: "Six overlapping band-passed noise bursts (1.2-3.5 kHz) with reversed
envelopes (slow in, hard out), each hard-panned alternately L/R via the `Panning` arg's neighbours
-- plus a 220 Hz sine that rises a minor third and never resolves." Peak <= 0.40.

STEREO by construction: the ``.seq`` only issues ONE ``PlaySound`` for this cue (one ``Panning=``
value for the whole call), so the only way to get six INDEPENDENTLY panned bursts is to bake the
L/R pan into the file itself at synthesis time. (Mono would collapse "hard-panned alternately"
into nothing.)

Fires: ``PlaySound`` t = 55 (P1) and again -- same file, second beat -- t = 405 (P5).

100% synthesized. Zero Square-Enix bytes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dsp  # noqa: E402

SOUND_ID = 100002
RESOURCE_ID = "Sounds02/SE00/nimbra_whispers"
NAME = "nimbra_whispers"

DURATION_S = 7.0
BURST_LO_HZ, BURST_HI_HZ = 1200.0, 3500.0
ONSETS_S = [0.00, 1.00, 2.00, 3.05, 4.10, 5.15]        # 6 bursts, overlapping tails
ATTACK_S = 1.30                                        # "slow in"
RELEASE_S = 0.20                                       # "hard out"
RISE_F_START = 220.0
RISE_SEMITONES = 3.0                                   # minor third
RISE_FADE_IN_S = 0.6
RISE_FADE_OUT_S = 0.3
PEAK_BUDGET = 0.40
TARGET_PEAK = 0.36


def _burst(sr: int, seed: int) -> np.ndarray:
    dur = ATTACK_S + RELEASE_S + 0.10
    m = int(round(dur * sr))
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(m)
    noise = dsp.bandpass_fft(noise, sr, BURST_LO_HZ, BURST_HI_HZ, edge_width=150.0)
    noise = dsp.normalize_peak(noise, 1.0)
    env = dsp.swell_env(m, sr, ATTACK_S, RELEASE_S)
    return noise * env


def render(sr: int = dsp.SR_DEFAULT) -> np.ndarray:
    n = int(round(sr * DURATION_S))
    left = np.zeros(n)
    right = np.zeros(n)

    for i, onset in enumerate(ONSETS_S):
        seg = _burst(sr, seed=1000 + i)
        start = int(round(onset * sr))
        end = min(start + len(seg), n)
        seg = seg[: end - start]
        if i % 2 == 0:
            left[start:end] += seg               # hard L
        else:
            right[start:end] += seg              # hard R

    t = np.arange(n) / sr
    rise = dsp.chirp_sine(t, sr, RISE_F_START, RISE_F_START * dsp.semitones_to_ratio(RISE_SEMITONES))
    rise *= dsp.fade_env(n, sr, RISE_FADE_IN_S, RISE_FADE_OUT_S)
    rise *= 0.9                                   # relative weight vs. the burst bed, pre-normalize

    left = left * 0.85 + rise                     # rise is centered -> equal in both channels
    right = right * 0.85 + rise

    stereo = np.stack([left, right], axis=-1)
    peak = dsp.peak_of(stereo)
    if peak > 0:
        stereo = stereo * (TARGET_PEAK / peak)
    return stereo.astype(np.float32)


if __name__ == "__main__":
    import wave

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / f"{NAME}_preview.wav"
    x = render()
    pcm = (np.clip(x, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(out), "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(dsp.SR_DEFAULT)
        w.writeframes(pcm.tobytes())
    print(f"wrote {out} ({len(x) / dsp.SR_DEFAULT:.2f}s, peak {dsp.peak_of(x):.4f})")
