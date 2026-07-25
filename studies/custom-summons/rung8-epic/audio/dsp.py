"""Rung 8 (NIMBRA) -- shared DSP primitives for the three synthesized cues.

Pure ``numpy`` + stdlib only (no scipy, no soundfile -- neither is on this box; see
``studies/custom-summons/rung8-epic/audio/README.md`` §Environment). Every function here is a plain
array-in/array-out transform, unit-testable without touching ffmpeg or the game install.

100% original signal-processing code. Zero Square-Enix bytes anywhere in this file or its outputs.
"""
from __future__ import annotations

import numpy as np

SR_DEFAULT = 44100


# --------------------------------------------------------------------------- pitch helpers
def cents_to_ratio(cents: float) -> float:
    return 2.0 ** (cents / 1200.0)


def semitones_to_ratio(semitones: float) -> float:
    return 2.0 ** (semitones / 12.0)


# --------------------------------------------------------------------------- oscillators
def bandlimited_saw(t: np.ndarray, f0: float, sr: int, max_harmonics: int = 40, phase: float = 0.0) -> np.ndarray:
    """A band-limited sawtooth via additive synthesis (no scipy needed): sum of odd+even harmonics
    with 1/k falloff and alternating sign, capped below Nyquist so it doesn't alias. Cheap enough at
    low fundamentals (this rung only calls it at 55/82.5/110 Hz) to just loop in Python."""
    n_harm = max(1, min(max_harmonics, int(0.45 * sr / max(f0, 1e-6))))
    out = np.zeros_like(t)
    for k in range(1, n_harm + 1):
        out += ((-1) ** (k + 1)) * np.sin(2 * np.pi * k * f0 * t + phase) / k
    return out * (2.0 / np.pi)


def chirp_sine(t: np.ndarray, sr: int, f_start: float, f_end: float) -> np.ndarray:
    """A phase-continuous sine sweeping linearly in frequency from ``f_start`` to ``f_end`` across
    the full length of ``t``. Integrates frequency -> phase via cumulative sum so there is no
    discontinuity (a naive ``sin(2*pi*f(t)*t)`` click on every sample would NOT be phase-continuous)."""
    n = len(t)
    freq = np.linspace(f_start, f_end, n)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    return np.sin(phase)


# --------------------------------------------------------------------------- noise
def pink_noise(n: int, sr: int, seed: int | None = None) -> np.ndarray:
    """1/f ("pink") noise via FFT-domain shaping of white noise, normalized to peak 1.0. No scipy
    needed -- the whole "filter" is a single elementwise scale of the rfft bins."""
    rng = np.random.default_rng(seed)
    white = rng.standard_normal(n)
    spec = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    freqs = freqs.copy()
    if len(freqs) > 1:
        freqs[0] = freqs[1]                 # avoid /0 at DC
    else:
        freqs[0] = 1.0
    spec = spec / np.sqrt(freqs)
    pink = np.fft.irfft(spec, n)
    peak = np.max(np.abs(pink))
    return pink / peak if peak > 0 else pink


def _edge(freqs: np.ndarray, center: float, width: float, rising: bool) -> np.ndarray:
    """A smooth (raised-cosine) 0->1 transition centered at ``center`` over ``width`` Hz."""
    lo, hi = center - width / 2.0, center + width / 2.0
    x = np.clip((freqs - lo) / max(hi - lo, 1e-9), 0.0, 1.0)
    curve = 0.5 - 0.5 * np.cos(np.pi * x)
    return curve if rising else (1.0 - curve)


def bandpass_fft(x: np.ndarray, sr: int, lo_hz: float, hi_hz: float, edge_width: float = 60.0) -> np.ndarray:
    """Zero every FFT bin outside ``[lo_hz, hi_hz]`` with a raised-cosine taper (``edge_width`` Hz)
    at both edges so the mask doesn't ring. This is the scipy-free stand-in for a Butterworth
    bandpass -- fine for atmosphere/particle-bed noise where exact filter shape doesn't matter."""
    n = len(x)
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    mask = _edge(freqs, lo_hz, edge_width, rising=True) * _edge(freqs, hi_hz, edge_width, rising=False)
    return np.fft.irfft(spec * mask, n)


# --------------------------------------------------------------------------- envelopes
def fade_env(n: int, sr: int, fade_in_s: float = 0.0, fade_out_s: float = 0.0) -> np.ndarray:
    """A unity envelope with raised-cosine (equal-power-ish, click-free) fades at each end."""
    env = np.ones(n)
    fi = int(fade_in_s * sr)
    fo = int(fade_out_s * sr)
    if fi > 0:
        fi = min(fi, n)
        env[:fi] = 0.5 * (1 - np.cos(np.linspace(0, np.pi, fi)))
    if fo > 0:
        fo = min(fo, n)
        env[-fo:] = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fo)))
    return env


def ramp_in(n_total: int, sr: int, start_s: float, ramp_s: float) -> np.ndarray:
    """0 up to ``start_s``, then a raised-cosine ramp to 1.0 over ``ramp_s``, then holds at 1.0.
    Used for "a third partial entering at 8s" -- a late-arriving layer, not a fade from t=0."""
    t = np.arange(n_total) / sr
    x = np.clip((t - start_s) / max(ramp_s, 1e-9), 0.0, 1.0)
    return 0.5 * (1 - np.cos(np.pi * x))


def swell_env(n: int, sr: int, attack_s: float, release_s: float) -> np.ndarray:
    """THE REVERSED ENVELOPE (storyboard §5, cue 100002): a slow, smooth attack (sin ease-in, not
    linear -- avoids a perceptible "ramp" corner) followed by a comparatively hard/fast release
    (cubic ease-out -- steeper than the attack). Whatever doesn't fit in ``n`` samples is silence."""
    env = np.zeros(n)
    a = min(int(attack_s * sr), n)
    if a > 0:
        env[:a] = np.sin(np.linspace(0, np.pi / 2, a))
    r = min(int(release_s * sr), max(n - a, 0))
    if r > 0:
        x = np.linspace(0, 1, r)
        env[a:a + r] = (1.0 - x) ** 3
    return env


# --------------------------------------------------------------------------- level
def peak_of(x: np.ndarray) -> float:
    return float(np.max(np.abs(x))) if x.size else 0.0


def normalize_peak(x: np.ndarray, target_peak: float) -> np.ndarray:
    p = peak_of(x)
    return x * (target_peak / p) if p > 0 else x
