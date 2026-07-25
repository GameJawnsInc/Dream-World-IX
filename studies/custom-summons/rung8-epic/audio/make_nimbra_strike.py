"""Rung 8 (NIMBRA) -- cue 100003 ``nimbra_strike``: the P4 sting.

Per STORYBOARD.md §5: "A 45 Hz sine thump with a 25 ms attack, plus an inharmonic metallic
ring-out (partials at 1.0 / 2.76 / 5.40 / 8.93 x 640 Hz, exponential decay tau = 0.55 s) -- a bell
that is not a bell." Peak <= 0.55.

Fires: ``PlaySound`` t = 345 (P4), the SAME tick as ``RiftFlash`` and the Intensity=1 relight.

100% synthesized. Zero Square-Enix bytes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dsp  # noqa: E402

SOUND_ID = 100003
RESOURCE_ID = "Sounds02/SE00/nimbra_strike"
NAME = "nimbra_strike"

DURATION_S = 2.5
THUMP_HZ = 45.0
THUMP_ATTACK_S = 0.025
THUMP_TAU_S = 0.28
RING_BASE_HZ = 640.0
RING_RATIOS = [1.0, 2.76, 5.40, 8.93]           # inharmonic -- "a bell that is not a bell"
RING_AMPS = [1.0, 0.6, 0.35, 0.2]
RING_TAU_S = 0.55
RING_PHASES = [0.0, 0.9, 1.7, 2.4]              # distinct phases so the partials don't sum-cancel
TAIL_FADE_S = 0.05                              # click-guard at the hard 2.5s cutoff
PEAK_BUDGET = 0.55
TARGET_PEAK = 0.50


def render(sr: int = dsp.SR_DEFAULT) -> np.ndarray:
    n = int(round(sr * DURATION_S))
    t = np.arange(n) / sr

    a = min(int(THUMP_ATTACK_S * sr), n)
    attack_env = np.ones(n)
    if a > 0:
        attack_env[:a] = np.linspace(0.0, 1.0, a)
    thump = np.sin(2 * np.pi * THUMP_HZ * t) * attack_env * np.exp(-t / THUMP_TAU_S)

    ring = np.zeros(n)
    for ratio, amp, ph in zip(RING_RATIOS, RING_AMPS, RING_PHASES):
        ring += amp * np.sin(2 * np.pi * (RING_BASE_HZ * ratio) * t + ph)
    ring *= np.exp(-t / RING_TAU_S)
    if a > 0:
        ring[:a] *= attack_env[:a]              # same click-guard on the ring's own onset

    mix = thump * 0.90 + ring * 0.50
    fo = min(int(TAIL_FADE_S * sr), n)
    if fo > 0:
        mix[-fo:] *= np.linspace(1.0, 0.0, fo)

    mix = dsp.normalize_peak(mix, TARGET_PEAK)
    return mix.astype(np.float32)


if __name__ == "__main__":
    import wave

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / f"{NAME}_preview.wav"
    x = render()
    pcm = (np.clip(x, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(out), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(dsp.SR_DEFAULT)
        w.writeframes(pcm.tobytes())
    print(f"wrote {out} ({len(x) / dsp.SR_DEFAULT:.2f}s, peak {dsp.peak_of(x):.4f})")
