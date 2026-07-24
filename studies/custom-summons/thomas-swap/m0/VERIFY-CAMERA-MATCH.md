# VERIFY-CAMERA-MATCH — adversarial re-derivation of M0 (a)+(b)

**Verdict: the headline is CONFIRMED, not refuted.** Every load-bearing number reproduces under a fully
independent parser + reprojection (`m0/verify_camera_match/indep_verify.py`, `focal_check.py`), and the
validation is strongly *discriminating* — every deliberately-wrong variant fails by large margins.

Reproduce: `py m0/verify_camera_match/indep_verify.py` and `py m0/verify_camera_match/focal_check.py`.

## What I re-derived independently (own code, own parse, all 5 sessions)

| claim | their number | my independent number | verdict |
|---|---|---|---|
| on-screen X p95 | 2.96 px | **2.956** | reproduced exactly |
| on-screen Y p95 | 7.16 px | **7.164** | reproduced exactly |
| on-screen radial p95 | 7.65 px | **7.646** | reproduced exactly |
| signed bias (X,Y) | +0.79 / −0.76 | **+0.786 / −0.762** | reproduced exactly |
| median radial | ~1 px | **1.045** | reproduced |
| `near=110·P11` vs `H` (coherent) | max 0.0001 | **max 0.00005, mean 0.00004, 0/2580 exceed 0.01** | confirmed, tighter |
| `VIEW.R = DL·(M/4096)·DR` coherent | ≤0.0198 | **cohRmax 0.019–0.020, 97.5% coherent** | reproduced |
| cameraOffset (clean cast S1) | ~0, mean +0.5 | **median 0.0000, mean +0.04 on S1** | confirmed ≈0 |

Frame-11 hand check: `VIEW.R` matches `DL·(M/4096)·DR` element-for-element; `VIEW.T=DL·M.T`, offset 0;
`110·2.727273 = 300.0 = H`. Source-grounded: `PsxScreenHeightNative=220` (FieldMap.cs:2336) ⇒ HALF_H=110;
`VIEW = PsxMatrix2UnityMatrix(array, cameraOffset)` is literal engine code (SFX.cs:1603, PsxCamera.cs:103-120).

## Discrimination power (session 2, coherent on-screen) — wrong variants FAIL

| variant | Rmed | Yp95 | Rp95 | |
|---|---|---|---|---|
| **SOURCE (1,−1,1), s1, HALF_H=110** | **1.00** | **6.54** | **6.68** | the answer |
| HALF_H=120 (the 240/2 trap) | 4.46 | 10.57 | 12.20 | FAILS |
| HALF_H=100 | 3.24 | 6.93 | 8.52 | FAILS |
| signs (1,1,1) no Y-flip | 33.1 | 236 | 245 | FAILS (35 frames stay on-screen) |
| signs (1,−1,−1) Z-flip | 78.0 | 195 | 245 | FAILS |
| signs (−1,−1,1) X-flip | 1.24 | 42.0 | 42.1 | FAILS |
| scale 1.05 | 56.9 | 100 | 102 | FAILS |
| scale 0.95 | 17.5 | 78.2 | 88.7 | FAILS |

The 220-vs-240 unit trap, sign errors, and even a 5% scale error are all rejected decisively. The validation
is not loose. Focal discrimination pooled: mean|110·P11−H|=0.074, mean|120·P11−H|=**37.9** — the wrong
constant is off by ~38 px of focal on the average frame.

Alt on-screen definition (native SX∈[0,320], SY∈[0,240], independent of the managed-NDC gate): X p95=3.04,
Y p95=7.41, R p95=8.00 — the headline is *not* an artifact of the framing criterion.

Phase-lead: part (b) rotation residual is cleanly best at offset 0 (mean 0.0036 vs 0.037/0.044 at ±1, ~10×);
part (a) median radial is flat within noise across offsets −2..+2 (0.998–1.036), i.e. no meaningful lead.

## Non-refuting nuances (disclosed, do not threaten the verdict)

1. **`near=110·P11==H` holds only on *coherent* frames** (which the report always qualifies). On the raw
   pooled set the 68 cut-transition frames deviate up to 57 — but I confirmed **0 of 2580 coherent frames**
   exceed 0.01, so those outliers are genuinely the probe's VIEW/M one-tick slip, not a broken relation.
2. **The signed bias (+0.79/−0.76 px) is small but *consistent* across sessions** (+0.74..+0.93 / −0.59..−1.39).
   It is the expected float-vs-integer-GTE truncation half-bias, sub-pixel and harmless — but calling it
   "no systematic offset" is very slightly overstated; the honest phrasing is "sub-pixel systematic bias
   from fixed-vs-float rounding."
3. **X-tighter-than-Y is real and reproduced**, but the report's *mechanism* ("PROJ12 off-center makes
   vertical more sensitive") is loose — the algebra shows *both* axes reduce to the same `110·P11==H`
   condition, so the gap is more plausibly the creature's larger vertical (py) excursion, not PROJ12 per se.
   An explanation nuance, not a numeric error.
4. **Session 1 (short cast) has a heavier tail** (Rp95 11.2 vs ~6.7 elsewhere) but the same sub-pixel center
   (med 0.86/0.89) — exactly as the report discloses. No hidden session inconsistency.

Scope (already flagged by the report and re-affirmed): this measures 2D screen-*position* of composed node-0
only; silhouette overlay (needs PRIM rows, absent here) and per-poly depth-interleave (P4) are separate.
