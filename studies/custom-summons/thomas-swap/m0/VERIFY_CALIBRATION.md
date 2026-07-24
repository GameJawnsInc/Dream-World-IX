# VERIFY_CALIBRATION.md — adversarial re-derivation of M0(c) (the PSX→Unity calibration)

**Verdict: NOT REFUTED.** All seven headline claims survive independent re-derivation. The map
`PsxToUnityPos(tx,ty,tz) = (tx, -ty, tz)` with **scale exactly 1** and `PsxToUnityRot(M)=B·R·B`
(`B=diag(1,-1,1)`) is source-forced (zero free parameters) and validated on the log. My checks used my
own parser, my own reprojection, the sessions the analyst did **not** headline (session 4 full, session 1
short), a by-hand source/log spot-check, and hostile discrimination tests the analyst did not run — every
one confirms. Confidence: **HIGH**.

Scripts: `m0/verify_calibration/refute.py` (independent). I ran the analyst's `m0/calibrate.py` once (it
reproduces its own numbers).

## What I re-derived independently

**Column indices (vs the C# writers, not the analyst's parser).** Checked every index against
`SfxMeshProbe.cs` `WriteModelRow`/`WriteNativeCamera`/`WriteBoneAabb` + the `VIEW`/`PROJ` writers: PSXCAM
`p[3:12]`=M, `p[12:15]`=T, `p[17]`=H; MODEL `p[11:14]`=anchor, `p[14:17]`=composed world, `p[17:26]`=3×3,
`p[26]`=bones32; BONES `p[7:10]`/`p[10:13]`=min/max; VIEW/PROJ `p[2:18]`=16 row-major floats. **All match.**

**Session split (external cross-check).** My 4 boundaries land at log lines `[50605, 72189, 122729,
173217]` — exactly **3 lines before** the orchestrator's MODEL-reset lines `[50608, 72192, 122732,
173220]` (PSXCAM precedes MODEL by 3 rows each frame). **5 casts confirmed**, frames ~11..561, reset per
cast.

**C1 — `(x,-y,z)`, scale 1 — CONFIRMED.** `PsxCamera.cs:103-120` `PsxMatrix2UnityMatrix(pmat,z)` verified
line-for-line (sign pattern `[+,-,+ / -,+,- / -,+,-]`, `m03=pmat9`, `m13=-pmat10`, `m23=-(pmat11+z)`);
`SFX.cs` `cameraOffset=0`. Requiring `W·U==(pv.x,-pv.y,-pv.z)` solves uniquely to `U=(x,-y,z)` with `M.t`
raw on both sides ⇒ scale 1. **Validated on UNUSED session 4:** candidate A wins node-0 **2.49 px** /
corners **29.63 px** (session 1: 2.13/28.95; control session 0: 2.61/29.63 — matches the analyst).

**C1/C3 discrimination — the analyst's refutation of TRANSPLANT §2.1 HOLDS, and is stronger than shown.**
On session 4, node-0 median |d|:

| map | node-0 | corners | note |
|---|---|---|---|
| **A (x,-y,z) s1** | **2.49** | **29.63** | winner every session/target |
| B (x,-y,-z) s1 *(§2.1 guess)* | 230.2 | 377.2 | z-sign wrong — 92× worse |
| C (x,y,z) s1 | (huge) | (huge) | Y must flip |
| D (-x,-y,z) s1 | 4.81 | 270.5 | near-tie at node-0, x-sign pinned by corners |
| **A s0.9** | **96.2** | 131.7 | *my tight test* — scale pinned to 1.0, not just "≠/256" |
| **A s1.1** | **96.3** | 98.6 | *my tight test* |
| A s0.5 | 75.4 | 209 | |
| A s2.0 | 249.8 | 286 | |

The tight scale variants (0.9/1.1) failing at ~96 px is a **stronger** refutation of "a scale to
calibrate" than the analyst's /256, ×256 — scale is pinned to 1.0 within ±10 %.

**C2 — VIEW == PsxMatrix2UnityMatrix(M) — CONFIRMED.** Hand-checked frame 11 exactly: PSXCAM
M=[-3560,0,-2021,-285,4053,500,2000,576,-3524], T=[-316,286,2651] → predicts VIEW m00=-3560/4096=
**-0.869141**, m11=4053/4096=**0.989502**, m03=**-316**, m13=**-286**, m23=**-2651** — the logged VIEW row
matches every field. Programmatic on unused sessions 4 & 1: rotation residual at the 1/4096 quantization
(mean 1.2e-3, hard-cut-inflated). The translation residual (mean ~8–44 u, up to ~200 at the 15 cuts) is
the ≤1-step temporal lag the analyst names, not a calibration error.

**C4 — vertical sub-pixel — CONFIRMED, and the test is TIGHT not loose.** Map A dy median **0.56–0.58 px**
everywhere. It is sub-pixel *by construction*: PROJ's frustum asymmetry `m12=(top+bottom)/(top−bottom)=
20/220=0.0909` (logged) shifts NDC so `SY = 110 − 110·ndcy = 120 + near·(vy/vz)`, and `near==H` (mean
+0.08). **Discrimination proof:** forcing the managed vertical center to 120 (the plausible "unit error",
since OFY=120) blows dy to **10.58 px** median — exactly the 120−110=10 offset — so the 0.58 px result is
real, not a slack test.

**C5 — widescreen factor — CONFIRMED.** HalfScreenWidth=**195.00** constant (from PROJ m00=300/195=
1.538462; source: `HalfScreenWidth=PsxScreenHeightNative·Screen.width/Screen.height/2`=220·(16/9)/2→195),
near==H, factor 160/195=**0.8205**. The 29.6 px corner residual = (1−0.8205)·~160 px, i.e. the frustum
width mismatch — correctly attributed downstream of `PsxToUnityPos` (dy stays sub-pixel; a position-scale
error would move dy too). The "220 vs 240" hostile check fails the wrong value: NH=240 would give near=
m11·120=327≠300=H, breaking the near==H identity that holds to +0.08. `PsxScreenHeightNative=220`
confirmed at `FieldMap.cs:2336`.

**C6 — scale sweep inherited — CONFIRMED (with one wording caveat).** ROOT +0x40 anchor col-norm sweeps
**0.0156× → 2.9978×** = the authored 0.02→3.0, on unused session 4 and control 0. *Caveat:* the analyst's
§5 "composed node-0 col-norm 0.0154→**2.9958×**" is true only under the `sane_model` filter; the **raw**
composed col-norm reaches **9.22×** on stale post-creature frames — e.g. f512, where the composed world
point is `(-5.2e8, 6.4e7, 2.0e9)` garbage from a recycled arena while the ROOT anchor stays clean
(`0,-12288,-7168`, col-norm 1.5×). The load-bearing datum is the ROOT anchor, which is robust; the sweep
conclusion is unaffected.

**C7 — det<0 climax hold — CONFIRMED to the frame.** Exactly **25 improper (det<0) frames, f153..f177**,
on BOTH unused session 4 and control session 0. f153 composed = `[-12271,0,0; 0,0,12270; 0,-12271,0]`
(the exact matrix §7 cites), a proper-3.0×-scaled reflection (col-norms 2.996×). The sign-map argument is
correct: `det(B·R·B)=det(B)²·det(R)=det(R)`, so a mixed raw det is unfixable by any diagonal signs — the
`if det<0 flip col2` guard is genuinely required. Which flip reads correct in-game is honestly deferred to
M1b.

## Bottom line

No load-bearing number failed. The one imprecision (C6 §5's composed col-norm being filter-dependent) does
not touch any conclusion. The analyst's summary, if anything, understates the discrimination: scale is
pinned to 1.0 within ±10 %, and the sub-pixel vertical is demonstrably a tight test. Headline **not
refuted**.
