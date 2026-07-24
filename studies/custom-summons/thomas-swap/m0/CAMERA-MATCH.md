# CAMERA-MATCH — M0 (a)+(b): the camera-inheritance measurement

**Question (TRANSPLANT.md §1.1):** the HYBRID transplant rests on one claim — a managed Unity object placed
at `PsxToUnity(creature world point)` and projected through `Camera.main` (which `SFX.UpdateCamera` stamps
every frame from the native camera) lands at the native creature's on-screen position, **including the
horizontal / widescreen axis** left open by the "OFY=120 by construction" argument. This measures it.

**Reproduce:** `py m0/camera_match.py` (reads the log path from the `LOG` constant; full run captured in
`m0/camera_match.out.txt`). `py m0/camera_match.py --recon` prints the session/frame facts only.
`py m0/camera_match.py --log <path>` overrides the log (the script already took `--log`; use it to
point at an archived snapshot).

> **2026-07-24 — empirical leg RE-ESTABLISHED** on the archived single cast
> `C:/gd/SCRATCH/summon-transplant/logs/sfxmeshprobe.20260724-012109.log` (effect 227, frames
> 11..561). On-screen coherent-frame p95 reproduces in the same family: X 2.634 px / Y 6.303 px
> (round 1: X 2.96 / Y 7.16), medians 0.694/0.647 px (round 1: 0.71/0.70). Fitted `PsxToUnity`
> signs=(1,-1,1) scale=1.00008, matching the source-derived zero-param map. Part (b)'s
> VIEW==PsxMatrix2UnityMatrix(M) identity holds on 98.9% of frames to the fp12 floor. Verdict
> unchanged.

**Log:** `…/FINAL FANTASY IX/sfxmeshprobe.log` (22 MB), one process, **5 complete Bahamut casts** (effect 227)
segmented by the >50-frame reset rule. Lanes used: `PSXCAM` (native world→view `M` + OFX/OFY/H), `MODEL`
kind=S (the creature's composed node-0 world point), `VIEW`/`PROJ` (the logged managed `Camera.main`
matrices). All 5 casts analysed; per-session numbers agree (medians 0.66–0.90 px), so the result replicates.

---

## VERDICT — **CONFIRMED**, horizontal included

> **A managed object at `PsxToUnity(creature world point)`, projected through the logged `Camera.main`
> VIEW·PROJ, renders within `N` px of the native creature's on-screen position, with `N` (p95, on the frames
> where the creature is on-screen) = 3.0 px horizontal / 7.2 px vertical / 7.6 px radial of a 320×240 native
> frame; median ≈ 1 px (sub-pixel).** The **horizontal/widescreen axis is CONFIRMED and is in fact the
> *tighter* axis** (p95 2.96 px = 0.9 % of screen width). The residual is floored by fp12 (1/4096)
> quantization of the native camera + world point, plus a **sub-pixel systematic bias (~0.8 px) from
> fixed-vs-float rounding, consistent across sessions** (signed bias +0.79 / −0.76 px — small and harmless,
> but not "no offset"; **M0 UPDATE 2026-07-23**, per the adversarial re-derivation `m0/VERIFY-CAMERA-MATCH.md`
> §"Non-refuting nuances" item 2).

The design's camera-inheritance premise is **measured-true**. The D4 fallback (drive `Camera.main` directly
from the decoded native camera track) is **not needed** for projection fidelity — the logged managed
`Camera.main` already *is* the native camera to the fp12 floor, and D4 could not do better because the native
track is itself fp12.

---

## Part (b) — the matrix-level check: VIEW **is** a fixed conversion of the native M

The managed VIEW comes from `PsxCamera.PsxMatrix2UnityMatrix(13 native camera floats, SFX.cameraOffset)`
(`SFX.cs:1603` → `PsxCamera.cs:103-120`); the native GTE matrix `M` (`PSXCAM` @RVA `0x1C1DC8`) is the *same*
installed camera (`0x69730/0x69740`) both readers copy from. The exact fixed relation (verified elementwise):

```
VIEW.R = DL · (M/4096) · DR        DL = diag(1,-1,-1)   DR = diag(1,-1,1)
VIEW.T = DL · M.T − (0,0, cameraOffset)
```

(PsxCamera.cs:107-118: `m00= pmat0/4096`, `m01=-pmat1/4096`, `m10=-pmat3/4096`, … `m03=pmat9`, `m13=-pmat10`,
`m23=-(pmat11+zoffset)` — the sign pattern is exactly `DL·(·)·DR` on the rotation and `DL` on the translation.)

**Measured, across all 5 casts (2648 camera frames):**

| quantity | result | meaning |
|---|---|---|
| `max‖VIEW.R − DL·(M/4096)·DR‖` on **97.4 %** (2580/2648) of frames | **≤ 0.0198** (fp12 floor = 2.4e-4) | rotation relation holds to quantization |
| the other **2.6 %** (68) frames | residual up to 0.56 | hard-cut frames — probe caught VIEW (managed clock) and M (native tick) ≤1 tick apart |
| best camera-frame offset | **0** (mean rot residual 0.0036 vs 0.044 / 0.037 at ±1) | **no phase lead** at offset 0 |
| `near = 110·PROJ[1][1]` vs native `H`, on coherent frames | `max|near − H| = 0.0001` | **managed focal == native GTE focal every frame**, through the whole 256→512 (H) / 47°→24° zoom |
| `cameraOffset = −VIEW.m23 − M.T2` on 843 translation-co-sampled frames | **mean +0.5 u, range [−4.6, +19.6]** | **SFX.cameraOffset ≈ 0** — no Z shift between managed & native cameras (this cast) |

The rotation matches to fp12; the focal (`near`) matches exactly; the translation matches exactly when the
probe samples VIEW and M on the same tick. During the fast fly-by the probe's ≤1-tick slip moves `VIEW.T`
by up to ~500 world units while `VIEW.R` still matches — a **probe-sampling artifact**, not a broken relation
(in the live hybrid the puppet-drive reads the same frame's state as `Camera.main`, so no such slip exists),
and it folds into part (a)'s measured screen delta, the honest end-to-end number.

---

## Part (a) — the projection match, per axis / session / phase band

**Method.** For each drawn-creature frame (`MODEL` kind=S, `bones32≠0`, composed ≈ anchor):
- **(i) native GTE (ground truth):** composed node-0 world `(wx,wy,wz)` through `M` + OFX=160/OFY=120/H →
  `(SX,SY)` (the proven `flight_v9_solve.parse_native_path` math: `p_view = (M.R·v)>>12 + M.T`,
  `SX = OFX + ((sat16(px)·((H<<16)/pz))>>16)`).
- **(ii) managed:** place a Unity object at `u = PsxToUnity(wx,wy,wz)` (per-axis **signs + one uniform scale**,
  **fit here by least squares**), project `VIEW·PROJ → NDC`, then map NDC → the same native-screen px:

  **Source-derived NDC→native-px** (`PsxProj2UnityProj` `PsxCamera.cs:172-178` + `PerspectiveOffCenter`
  `:122-148`, `FieldMap.cs:2336,2340`): `HalfScreenWidth = 110·PROJ11/PROJ00` (= `near/PROJ00`),
  vertical half = 110 (= `PsxScreenHeightNative/2`):
  ```
  SX = OFX + HalfScreenWidth·(ndc_x + PROJ02)
  SY = OFY − 110·(ndc_y + PROJ12)
  ```

**The fit recovers the source map from data alone:** `signs = (1, −1, 1)`, `scale = 1.00009` (robust median
over coherent frames) — i.e. **`PsxToUnity(v) = (vx, −vy, vz)`, unit scale, zero free parameters**, exactly the
`diag(1,-1,1)` handedness flip `PsxMatrix2UnityMatrix` applies. Source-predicted `(1,-1,1)`,1.0 gives an
identical median (≈1.1 px). Best camera-frame offset = **0**.

**Why the widescreen aspect cancels (the horizontal answer).** With `VIEW = PsxToUnity(M)` and the puppet at
`(vx,-vy,vz)`, the managed view point is `(px, −py, −pz − cameraOffset)`. Then
`SX = OFX + HalfScreenWidth·ndc_x = OFX + near·px/(pz+off)` — **HalfScreenWidth cancels** — which equals the
native `SX = OFX + H·px/pz` **iff near == H and off ≈ 0**, both measured true. So horizontal reduces to the same
`near==H` condition as vertical; the 16:9 expansion (`ShaderMulX = 1/HalfFieldWidth` for the native SFX creature
in `SFXMesh` vs `HalfScreenWidth` in the managed frustum) applies to both and drops out.

**Results — on-screen coherent frames (1256 of 1573), all 5 casts, offset 0, source map:**

| axis | mean | median | p95 | max | signed bias |
|---|---|---|---|---|---|
| **X (horizontal)** | 0.94 | 0.71 | **2.96** | 9.8 | +0.79 |
| **Y (vertical)** | 1.64 | 0.70 | **7.16** | 34.1 | −0.76 |
| radial | 2.04 | 1.05 | 7.65 | 35.4 | — |

- Units are px of the **320×240 native frame** (horiz p95 = 0.9 % of width, vert p95 = 3.0 % of height).
- Median ≈ 1 px = the fp12 quantization floor; signed bias sub-pixel — **M0 UPDATE 2026-07-23:** this is a
  real, sub-pixel systematic bias (~0.8 px) from fixed-vs-float rounding, consistent across sessions, not
  literally "no offset" (`m0/VERIFY-CAMERA-MATCH.md`).
- Vertical p95 (7 px) > horizontal (3 px). **M0 UPDATE 2026-07-23 (corrected mechanism):** the algebra shows
  *both* axes reduce to the same `110·PROJ11==H` condition, so `PROJ12`/the off-center frustum is not the
  differentiator; the gap is more plausibly the creature's larger vertical (py) world excursion on this cast
  (`m0/VERIFY-CAMERA-MATCH.md` §"Non-refuting nuances" item 3) — an explanation nuance, not a numeric error.

**Phase bands:** the creature is drawn only in the **82–412** window (it is undrawn 11–81 and after ~412,
where the camera follows the fire column — the design's phase 4). All part-(a) frames fall in 82–412.

**Off-screen / cut context (reported, not counted against the verdict):**
- *All* coherent frames incl. the deliberate off-screen swoop-by: horiz p95 3.4 / vert p95 11.0 px. The larger
  tail is frames where the creature is thousands of px off-frame (both puppet and creature off-screen, same
  direction) — a large *absolute* px difference that is irrelevant to what the viewer sees.
- 39 cut-transition frames (probe VIEW/M slip): median 5.4 px radial, p95 ~24 px. These **overstate** the
  live-hybrid error — the worst 8 are all at H=512 (the tightest push-in), confirming they are real shot
  changes, and the slip is a probe artifact only.

---

## Caveats / scope (honest)

1. **This measures projection geometry only** — where the puppet's node-0 origin lands in 2D. It does **not**
   measure per-poly **depth interleave** with the screen-space effect prims (P4, the separate M0 depth-gate,
   another agent) nor shading. The native SFX creature is drawn as screen-space pixel meshes in `SFXMesh`
   (`Graphics.DrawMeshNow(_mesh, Matrix4x4.identity)`, verts = raw `SX+drOffset,SY+drOffset,GzDepth`), whereas
   the managed puppet is a real 3D object through `Camera.main`; M0(a) proves they coincide in screen X/Y, the
   depth-regime difference is the hybrid's one true residual (measured separately).
2. **cameraOffset ≈ 0 for THIS summon** (Bahamut on the bench). If a summon sets a nonzero `SFX.cameraOffset`,
   the pure similarity `PsxToUnity` needs a +Z translation term (`u.z += cameraOffset`) — trivial to add, flagged.
3. **Provenance:** read-only over the user's own probe log; no stock bytes read or written. Only bone-0 /
   composed-node-0 world points and the camera matrices were used (staging/choreography class), never
   `bones[1..92]`.
