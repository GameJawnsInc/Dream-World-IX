#!/usr/bin/env python3
"""RUNG 8 -- THE PLAYLIST SAMPLER SIMULATOR (adversarial round, 2026-07-24).

    py studies/custom-summons/rung8-epic/playlist_sim.py

WHY THIS EXISTS. STORYBOARD 1.7's "Speed compensation" equation was derived from TWO of the three lines
that drive an ``Animations[]`` playlist -- ``animMaxFrame`` and ``animFrame`` -- and never checked the
THIRD, the one that actually poses the rig:

    SFXDataMesh.cs:851   animMaxFrame[i] = max(0, ceil(geoAnimGetNumFrames(obj, clip_i) / Speed_i))
    SFXDataMesh.cs:853   while (frame >= startFrame + frameCounter + animMaxFrame[animIndex])
                             frameCounter += animMaxFrame[animIndex++];
    SFXDataMesh.cs:858   animFrame = floor((frame - startFrame - frameCounter) * Speed_i)
    SFXDataMesh.cs:863   else { animIndex = last; animFrame = animMaxFrame[animIndex]; }   <-- the tell
    SFXDataMesh.cs:869   clipState.time = clipState.length * animFrame / animMaxFrame[animIndex]

``animFrame`` is a CLIP-FRAME index (line 858 multiplies ticks by Speed). ``animMaxFrame`` is a TICK
count (line 853 accumulates it against ``frame``). Line 869 divides one by the other. The two are equal
ONLY when Speed == 1 -- and line 863 proves the divisor was MEANT to be "the value animFrame takes at
the end of the clip", which for Speed != 1 is ~numFrames, not animMaxFrame.

CONSEQUENCE: a playlist entry at Speed s advances the clip at s^2 clip-frames per tick, so the clip
finishes after 1/s of its entry and the remaining (1 - 1/s) is spent past ``length`` (Unity clamps or
wraps at Sample()). Speed 1 is the only self-consistent value -- and, decisively, it is the value at
which BOTH readings of line 869 agree, which is why the fix is to author every entry at Speed 1 and
size the CLIP to the beat.

This script is READ-ONLY and touches nothing. It prints the tick-by-tick clip-frame trajectory for any
playlist so a claim like "the lunge peak lands on t 83" can be checked instead of asserted.
"""
from __future__ import annotations

import math

TPS = 15.0


def sample(playlist, window_end, start_frame=0, play_sfx_tick=25):
    """Reproduce SFXDataMesh.Render's per-frame clip sampling exactly.

    ``playlist`` = [(name, numFrames, speed, fps), ...]. Yields one row per manifest frame:
    ``(manifest_frame, seq_tick, entry_name, animFrame, clipState.time, displayed_clip_frame)``.
    ``displayed_clip_frame`` is what Unity poses after Sample(): time * fps, CLAMPED to the clip's own
    last frame (WrapMode.Once / ClampForever -- the pessimistic-but-standard legacy default)."""
    m = [max(0, math.ceil(n / s)) for (_, n, s, _) in playlist]
    for frame in range(start_frame, window_end):
        idx, counter = 0, 0
        while idx < len(playlist) and frame >= start_frame + counter + m[idx]:
            counter += m[idx]
            idx += 1
        if idx < len(playlist):
            anim_frame = math.floor((frame - start_frame - counter) * playlist[idx][2])
        else:
            idx = len(playlist) - 1
            anim_frame = m[idx]
        name, n, _s, fps = playlist[idx]
        length = (n - 1) / fps                       # Unity clip.length for keys at 0..(n-1)/fps
        t = length * anim_frame / m[idx] if m[idx] else 0.0
        shown = min(t * fps, n - 1.0)
        yield frame, play_sfx_tick + frame, name, anim_frame, t, shown


def report(title, playlist, window_end, marks):
    print(f"\n=== {title} ===")
    m = [max(0, math.ceil(n / s)) for (_, n, s, _) in playlist]
    bounds, acc = [], 0
    for (name, n, s, _), mm in zip(playlist, m):
        bounds.append((name, n, s, acc, acc + mm))
        acc += mm
    for name, n, s, a, b in bounds:
        print(f"  entry {name:<10} N={n:<3} Speed={s}  frames {a:>3}..{b:<3} ({b - a} ticks)")
    print(f"  playlist {acc} ticks vs window {window_end}  "
          f"[{'covers' if acc >= window_end else 'SHORT -- freezes'}]")

    rows = list(sample(playlist, window_end))
    # per entry: the tick at which the clip runs out of itself
    seen = {}
    for frame, tick, name, af, t, shown in rows:
        key = (name, frame)
        length = None
        for nm, n, s, a, b in bounds:
            if a <= frame < b and nm == name:
                length = (n - 1) / 30.0
                if shown >= n - 1.0001 and (nm, a) not in seen:
                    seen[(nm, a)] = (frame, tick)
        _ = key, length
    for nm, n, s, a, b in bounds:
        hit = seen.get((nm, a))
        if hit:
            print(f"  {nm:<10} reaches its LAST pose at manifest frame {hit[0]} (t {hit[1]}) -- then "
                  f"FROZEN for {b - hit[0]} of its {b - a} ticks")
        else:
            print(f"  {nm:<10} never over-runs (plays cleanly across all {b - a} ticks)")

    for label, want_clip, want_tick in marks:
        best = None
        for frame, tick, name, af, t, shown in rows:
            if name != want_clip[0]:
                continue
            d = abs(shown - want_clip[1])
            if best is None or d < best[0]:
                best = (d, frame, tick, shown)
        if best:
            _, frame, tick, shown = best
            verdict = "OK" if tick == want_tick else f"OFF BY {tick - want_tick:+d} ticks"
            print(f"  {label}: clip frame {want_clip[1]} of '{want_clip[0]}' shows at t {tick} "
                  f"(manifest {frame}, shown {shown:.1f}); the .seq fires at t {want_tick}  -> {verdict}")


if __name__ == "__main__":
    F = 30.0
    report("AS SHIPPED THIS ROUND -- emerge@6 | drift@3 | strike@2 | drift@1",
           [("emerge", 90, 6, F), ("drift", 75, 3, F), ("strike", 60, 2, F), ("drift", 75, 1, F)],
           110, [("THE LUNGE PEAK", ("strike", 36), 83)])

    report("THE PLAYTESTED BUILD -- emerge@2 | drift@1 x2 | strike@2 | drift@1 x2",
           [("emerge", 90, 2, F), ("drift", 75, 1, F), ("drift", 75, 1, F),
            ("strike", 60, 2, F), ("drift", 75, 1, F), ("drift", 75, 1, F)],
           330, [])

    # The lunge peak is the strike envelope's `(36, 1.0)` breakpoint, authored against 60 frames and
    # rescaled by (N-1)/(REF-1) -- on the shipped 30-frame clip that is frame 36 * 29/59 = 17.695.
    report("THE FIX (SHIPPED) -- every entry Speed 1, the CLIP sized to the beat",
           [("emerge", 15, 1, F), ("driftlook", 25, 1, F), ("strike", 30, 1, F), ("drift", 75, 1, F)],
           110, [("THE LUNGE PEAK", ("strike", 36 * 29 / 59), 83)])
