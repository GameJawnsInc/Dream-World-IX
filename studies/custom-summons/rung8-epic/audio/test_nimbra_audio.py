"""Offline (no ffmpeg) checks for the NIMBRA audio lane -- pure numpy, fast. The ffmpeg-dependent
decode/duration/peak-after-Vorbis checks live in ``build_audio.py``'s ``validation_report.json``;
these tests just guard the DSP + cue generators don't silently regress (wrong shape, NaN, clipping,
wrong sample count) independent of whether ffmpeg is on PATH.

Run: ``py -m pytest studies/custom-summons/rung8-epic/audio/test_nimbra_audio.py``
"""
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dsp                     # noqa: E402
import make_nimbra_drone as drone_mod        # noqa: E402
import make_nimbra_whispers as whispers_mod  # noqa: E402
import make_nimbra_strike as strike_mod      # noqa: E402

SR = 22050    # a lower rate than the build's 44100 -- exercises sr-parametrization, runs faster


# --------------------------------------------------------------------------- dsp primitives
def test_cents_and_semitones_ratio():
    assert dsp.cents_to_ratio(0) == 1.0
    assert abs(dsp.cents_to_ratio(1200) - 2.0) < 1e-9         # 1200 cents = one octave
    assert abs(dsp.semitones_to_ratio(12) - 2.0) < 1e-9       # 12 semitones = one octave
    assert abs(dsp.semitones_to_ratio(3) - 1.1892) < 1e-3     # a minor third


def test_bandlimited_saw_is_bounded_and_periodic():
    t = np.arange(SR) / SR                                    # 1 second
    saw = dsp.bandlimited_saw(t, 110.0, SR)
    assert np.max(np.abs(saw)) <= 1.25                        # Gibbs overshoot only (~1.18 typical), no blow-up
    assert not np.any(np.isnan(saw))


def test_pink_noise_peak_normalized_and_deterministic_with_seed():
    a = dsp.pink_noise(4096, SR, seed=1)
    b = dsp.pink_noise(4096, SR, seed=1)
    assert np.array_equal(a, b)                               # same seed -> identical (reproducible builds)
    assert abs(np.max(np.abs(a)) - 1.0) < 1e-6


def test_bandpass_fft_attenuates_out_of_band_energy():
    n = SR * 2
    t = np.arange(n) / SR
    tone_in_band = np.sin(2 * np.pi * 2000 * t)               # inside 1200-3500
    tone_out_of_band = np.sin(2 * np.pi * 100 * t)            # well below 1200
    mixed = tone_in_band + tone_out_of_band
    filtered = dsp.bandpass_fft(mixed, SR, 1200.0, 3500.0, edge_width=100.0)
    # correlate against the pure in-band tone -- should track it much better than the out-of-band one
    corr_in = abs(np.corrcoef(filtered, tone_in_band)[0, 1])
    corr_out = abs(np.corrcoef(filtered, tone_out_of_band)[0, 1])
    assert corr_in > 0.9
    assert corr_out < 0.2


def test_fade_env_endpoints():
    env = dsp.fade_env(SR, SR, fade_in_s=0.5, fade_out_s=0.5)
    assert env[0] < 0.05
    assert env[-1] < 0.05
    assert abs(env[SR // 2] - 1.0) < 0.05                      # mid-file should be ~unity


def test_swell_env_slow_in_hard_out():
    n = SR
    env = dsp.swell_env(n, SR, attack_s=0.3, release_s=0.05)
    peak_idx = int(np.argmax(env))
    # the attack occupies far more samples than the release -- "slow in, hard out"
    assert peak_idx > 0.25 * SR
    assert env[peak_idx] > 0.9
    assert env[-1] < 0.05


def test_chirp_sine_is_phase_continuous_and_bounded():
    t = np.arange(SR) / SR
    x = dsp.chirp_sine(t, SR, 220.0, 261.63)
    assert np.max(np.abs(x)) <= 1.0 + 1e-9
    # no sample-to-sample jump larger than a plain sine at the higher bound would produce
    max_step = np.max(np.abs(np.diff(x)))
    assert max_step < 2 * np.pi * 261.63 / SR * 1.5


def test_normalize_peak_hits_target():
    x = np.array([0.1, -0.4, 0.2])
    y = dsp.normalize_peak(x, 0.8)
    assert abs(np.max(np.abs(y)) - 0.8) < 1e-9


# --------------------------------------------------------------------------- the three cues
@pytest.mark.parametrize("mod,expect_channels", [
    (drone_mod, 1),
    (whispers_mod, 2),
    (strike_mod, 1),
])
def test_cue_render_shape_duration_and_peak(mod, expect_channels):
    x = mod.render(sr=SR)
    assert not np.any(np.isnan(x))
    assert x.dtype == np.float32

    if expect_channels == 1:
        assert x.ndim == 1
        n = len(x)
    else:
        assert x.ndim == 2 and x.shape[1] == expect_channels
        n = x.shape[0]

    duration = n / SR
    assert abs(duration - mod.DURATION_S) < 1.0 / SR + 1e-6    # exact to the sample at this sr

    peak = dsp.peak_of(x)
    assert peak <= mod.PEAK_BUDGET + 1e-6                      # authored under budget, never over
    assert peak > 0.05                                         # not silently near-silent


def test_drone_third_partial_absent_before_entry_and_present_after():
    """The 110 Hz layer must be absent before ``F3_ENTRY_S`` and present after the ramp completes.

    Derived from the module's own constants, NOT hardcoded seconds: the retime (STORYBOARD §11) moved
    the drone from 34.0 s to 8.0 s and the old literal `x[12*SR:]` sampled past the end of the file --
    a test that reads its subject's constants survives a re-cut, one that retypes them does not.

    The measurement is a RATIO against the 55 Hz fundamental in the SAME window, so the whole-mix fade
    envelope (which differs a lot between the two windows in a short cue) divides out."""
    x = drone_mod.render(sr=SR)
    n = len(x)

    def band_energy(sig, lo, hi):
        spec = np.fft.rfft(sig)
        freqs = np.fft.rfftfreq(len(sig), d=1.0 / SR)
        m = (freqs >= lo) & (freqs <= hi)
        return float(np.sum(np.abs(spec[m]) ** 2))

    def octave_ratio(a_s, b_s):
        seg = x[int(a_s * SR):min(n, int(b_s * SR))]
        return band_energy(seg, 105, 115) / (band_energy(seg, 50, 60) + 1e-12)

    entry, ramp = drone_mod.F3_ENTRY_S, drone_mod.F3_RAMP_S
    win = min(0.8, max(0.4, entry - 0.2))                      # a window that fits before the entry
    before = octave_ratio(entry - win, entry)                  # ends ON the entry -- 110 Hz still muted
    after_start = entry + ramp + 0.3                           # clear of the ramp
    after = octave_ratio(after_start, min(after_start + win, drone_mod.DURATION_S))
    assert after > before * 3                                  # clearly stronger once entered


def test_whispers_bursts_are_hard_panned_alternately():
    x = whispers_mod.render(sr=SR)
    left, right = x[:, 0], x[:, 1]
    # sample near each burst's peak (attack-heavy -> peak lands near attack_s after onset)
    for i, onset in enumerate(whispers_mod.ONSETS_S):
        idx = int((onset + whispers_mod.ATTACK_S * 0.9) * SR)
        if idx >= len(left):
            continue
        lo, hi = max(0, idx - 50), min(len(left), idx + 50)
        l_energy = float(np.sum(left[lo:hi] ** 2))
        r_energy = float(np.sum(right[lo:hi] ** 2))
        if i % 2 == 0:
            assert l_energy > r_energy                        # even bursts favor Left
        else:
            assert r_energy > l_energy                        # odd bursts favor Right


def test_strike_ring_partials_are_inharmonic_and_decay():
    x = strike_mod.render(sr=SR)
    n = len(x)
    early = x[: n // 4]
    late = x[3 * n // 4:]
    assert dsp.peak_of(early) > dsp.peak_of(late) * 1.5        # exponential decay -> tail much quieter
    ratios = strike_mod.RING_RATIOS
    assert ratios[0] == 1.0
    # none of the ratios are small-integer harmonics of each other -- "not a bell"
    for r in ratios[1:]:
        assert abs(r - round(r)) > 0.05
