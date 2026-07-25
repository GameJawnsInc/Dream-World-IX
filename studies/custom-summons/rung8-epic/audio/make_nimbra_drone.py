"""Rung 8 (NIMBRA) -- cue 100001 ``nimbra_drone``: the P0/P1/.../P5 bed.

Per STORYBOARD.md §5: "Two detuned saw/sine partials at 55.0 Hz and 82.5 Hz (a bare fifth) with
±3 cent slow beating; a third partial at 110 Hz entering at 8 s; over it a band-passed pink-noise
"breath" (300-900 Hz) amplitude-modulated at 0.13 Hz. 6 s fade-in, 4 s fade-out. Peak <= 0.45."
Fires: ``PlaySound`` t ≈ 10 (P0), ``StopSound`` t = 480 (P5) -- the file is a 34.0 s MASTER; the
engine only ever plays ~31.3 s of it (StopSound lands mid-file), which is by design (§5 of the
storyboard), not a bug in this generator.

100% synthesized (numpy FFT-noise-shaping + additive-harmonic saw + phase-continuous sines).
Zero Square-Enix bytes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dsp  # noqa: E402

SOUND_ID = 100001
RESOURCE_ID = "Sounds02/SE00/nimbra_drone"
NAME = "nimbra_drone"

DURATION_S = 34.0
F1 = 55.0                      # root
F2 = 82.5                      # bare fifth above F1 (82.5/55 == 1.5)
F3 = 110.0                     # octave above F1, enters late
DETUNE_CENTS = 3.0             # ±3 cents -> two sub-oscillators per partial, natural slow beating
F3_ENTRY_S = 8.0
F3_RAMP_S = 2.5
BREATH_LO_HZ, BREATH_HI_HZ = 300.0, 900.0
BREATH_AM_HZ = 0.13
FADE_IN_S = 6.0
FADE_OUT_S = 4.0
PEAK_BUDGET = 0.45
TARGET_PEAK = 0.40              # authored under budget -- headroom for the Vorbis re-encode


def _detuned_partial(t: np.ndarray, sr: int, f0: float, amp: float, saw_mix: float = 0.4) -> np.ndarray:
    """One "partial" = two sub-oscillators at f0*(+/-3 cents), each itself a sine/saw blend. The
    ~0.095 Hz difference tone between the +/-3-cent pair at 55 Hz (~10.5 s period) IS the "slow
    beating" the storyboard calls for -- no separate LFO needed, it falls out of the detuning."""
    f_hi = f0 * dsp.cents_to_ratio(+DETUNE_CENTS)
    f_lo = f0 * dsp.cents_to_ratio(-DETUNE_CENTS)

    def osc(f):
        sine = np.sin(2 * np.pi * f * t)
        saw = dsp.bandlimited_saw(t, f, sr)
        return (1 - saw_mix) * sine + saw_mix * saw

    return amp * 0.5 * (osc(f_hi) + osc(f_lo))


def render(sr: int = dsp.SR_DEFAULT) -> np.ndarray:
    n = int(round(sr * DURATION_S))
    t = np.arange(n) / sr

    p1 = _detuned_partial(t, sr, F1, amp=0.55)
    p2 = _detuned_partial(t, sr, F2, amp=0.38)

    entry = dsp.ramp_in(n, sr, F3_ENTRY_S, F3_RAMP_S)
    p3 = 0.28 * np.sin(2 * np.pi * F3 * t) * entry     # plain sine -- keep the late layer clean

    breath = dsp.pink_noise(n, sr, seed=42)
    breath = dsp.bandpass_fft(breath, sr, BREATH_LO_HZ, BREATH_HI_HZ, edge_width=60.0)
    breath = breath / (np.max(np.abs(breath)) + 1e-12)
    am = 0.45 + 0.55 * (0.5 + 0.5 * np.sin(2 * np.pi * BREATH_AM_HZ * t))
    breath = 0.30 * breath * am

    mix = p1 + p2 + p3 + breath
    mix *= dsp.fade_env(n, sr, FADE_IN_S, FADE_OUT_S)
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
