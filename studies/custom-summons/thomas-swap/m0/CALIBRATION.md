# CALIBRATION.md — M0(c): the PSX→Unity map for the s54 hybrid, DERIVED (zero free parameters), then VALIDATED

**Question (TRANSPLANT §2.1):** how does the s54 hybrid convert the creature's live world matrices
`*(SummonData+0x38)[k]` (a libgte MATRIX — s16 3×3 rotation in `/4096`, s32 world translation, in the
plugin's PSX battle-world space) into Unity world coordinates so our mesh, rendered by `Camera.main`, lands
where the native creature is? **Pin the SCALE and the exact SIGNS from the managed source, with zero free
parameters.**

**Answer — one line each, DERIVED from source and VALIDATED on `sfxmeshprobe.log` (5 casts):**

```csharp
Vector3    PsxToUnityPos(int tx, int ty, int tz) => new Vector3(tx, -ty, tz);   // NEGATE Y ONLY. scale = 1.
Quaternion PsxToUnityRot(Int16[9] m /*row-major /4096*/) => (B·R·B).rotation;   // B = diag(1,-1,1)
```

The scale is **exactly 1** (PSX world unit == Unity world unit — no `/256`, no `/4096`, no `*0.00390625`).
The only negation is **Y**. **TRANSPLANT §2.1's guessed `(tx,-ty,-tz)/scale` is WRONG on both the z-sign and
the scale** — stated loudly with numbers in §6.

---

## 1. THE DERIVATION (first principles — every constant cited)

`SFX.UpdateCamera()` stamps `Camera.main` every native tick from the plugin's own camera:

```
SFX.cs:1596-1597   Single[] array = new Single[13];  Marshal.Copy(source, array, 0, 13);   // = the native M
SFX.cs:1599        SFX.fxNearZ = array[12];                                                  // near = array[12]
SFX.cs:1603        camera.worldToCameraMatrix = PsxCamera.PsxMatrix2UnityMatrix(array, SFX.cameraOffset);
SFX.cs:1604        camera.projectionMatrix    = PsxCamera.PsxProj2UnityProj(SFX.fxNearZ, SFX.fxFarZ);
SFX.cs:1945        SFX.cameraOffset = 0f;                                       // ⟹ zoffset = 0, EXACTLY
```

`array[0..8]` is `M.R` (the native world→view rotation, `/4096`), `array[9..11]` is `M.t` (s32 translation),
`array[12]` is the near plane. `PsxMatrix2UnityMatrix(pmat, z)` builds `worldToCameraMatrix W`
(`PsxCamera.cs:103-120`):

```
W.m00= pmat0/4096   W.m01=-pmat1/4096   W.m02= pmat2/4096   W.m03= pmat9
W.m10=-pmat3/4096   W.m11= pmat4/4096   W.m12=-pmat5/4096   W.m13=-pmat10
W.m20=-pmat6/4096   W.m21= pmat7/4096   W.m22=-pmat8/4096   W.m23=-(pmat11 + z)     z = 0
```

The native GTE (FORMAT.md §5, RTPS `0x3e80`) computes view coords with **no sign flips**:
`pv = (M.R · v_psx) >> 12 + M.t`. Requiring the managed camera to project a Unity point `U` to the same place
the native GTE projects the PSX point `v` means `W·U == (pv.x, -pv.y, -pv.z)` (Unity camera space is +x right,
**+y UP, −z FORWARD**; the PSX GTE view space is +x right, **+y DOWN, +z FORWARD**). Substituting the `W`
rows above, that equation is solved **uniquely** by

```
U = ( v.x , -v.y , v.z )          — negate Y only, no scale.
```

Check (each row collapses exactly): `W.m00·v.x + W.m01·(-v.y) + W.m02·v.z + W.m03`
`= (M00·v.x + M01·v.y + M02·v.z)/4096 + M.t0 = pv.x` ✓; row 1 → `-pv.y` ✓; row 2 → `-pv.z` ✓ (because
`z=0`). Since `W` uses `M.t` **raw** (no scale) and the GTE uses `M.t` raw, the world units are 1:1 → **scale
= 1**. The projection then matches by construction on the vertical axis (`PsxProj2UnityProj`'s off-center
frustum encodes `PsxScreenHeightNative = 220` / `OFY = 120`, `PsxCamera.cs:172-178`, `FieldMap.cs:2336`); the
horizontal axis is widescreen-scaled — §4.

**Rotation.** The world basis change whose linear part is the position map is `B = diag(1,-1,1)` (`B = B⁻¹`).
A world orientation `R_psx` (the node's object→world 3×3) becomes `R_unity = B·R_psx·B`
(element form `R_unity[i][j] = s[i]·s[j]·R_psx[i][j]`, `s = (+1,-1,+1)` → sign pattern
`[[+,-,+],[-,+,-],[+,-,+]]`). This is a *world* transform, so it is **not** the `worldToCameraMatrix` sign
pattern (`PsxMatrix2UnityMatrix` additionally flips Z because it is a *view* matrix).

---

## 2. THE s54 CONSTANTS + FORMULAS (C#-ready pseudocode)

```csharp
// ============================================================================================
//  PSX battle-world  ->  Unity world.  ZERO free parameters.
//  Derived from SFX.cs:1603 + SFX.cs:1945 (cameraOffset=0) + PsxCamera.cs:103-120.
//  Validated on sfxmeshprobe.log (5 Bahamut casts): see CALIBRATION.md §3.
// ============================================================================================

// POSITION — negate Y only; PSX world unit == Unity world unit (scale 1).
// tx,ty,tz are the s32 translation at (MATRIX + 0x14) of node k in *(SummonData+0x38).
static Vector3 PsxToUnityPos(int tx, int ty, int tz) => new Vector3(tx, -ty, tz);

// ROTATION — change of basis by B = diag(1,-1,1):  R_unity = B * R_psx * B  (B == B^-1).
// m = the node's s16 3x3, row-major m00..m22, /4096 fixed point. It MAY carry the authored 0.02..3.0x scale
// (the scale is folded into the anchor 3x3 in place, FORMAT.md §1.4) — normalize it out; the mesh's SIZE is
// already carried by the node POSITION spread (§5), so per-bone localScale is NOT needed, only orientation.
static Quaternion PsxToUnityRot(short[] m /* len 9 */)
{
    Vector3 c0 = new Vector3(m[0], m[3], m[6]).normalized;   // world axes = columns of R_psx
    Vector3 c1 = new Vector3(m[1], m[4], m[7]).normalized;
    Vector3 c2 = new Vector3(m[2], m[5], m[8]).normalized;
    // B * R * B :  column j -> s[j] * (c_j.x, -c_j.y, c_j.z),  s = (+1,-1,+1)
    Matrix4x4 R = Matrix4x4.identity;
    R.SetColumn(0, new Vector4( c0.x, -c0.y,  c0.z, 0f));
    R.SetColumn(1, new Vector4(-c1.x,  c1.y, -c1.z, 0f));
    R.SetColumn(2, new Vector4( c2.x, -c2.y,  c2.z, 0f));
    // ~7.5% of frames (the ~3.0x climax hold) store an INTRINSICALLY IMPROPER matrix (det<0, §7) — a
    // reflection is not a Unity rotation. Guard it before quaternion extraction; confirm the visual at M1b.
    if (R.determinant < 0f) R.SetColumn(2, -R.GetColumn(2));
    return R.rotation;
}
```

The hybrid writes, per node `k` each frame (TRANSPLANT §2.1):
`smr.bones[k].position = PsxToUnityPos(M_k.t)` and `smr.bones[k].rotation = PsxToUnityRot(M_k.R)`.

---

## 3. VALIDATION — reprojection on the log (zero fitting), ≥ 2 sessions

`m0/calibrate.py` streams the 22 MB log, segments the **5** appended casts (frame drop > 50), and on the
creature's reliable frames projects `PsxToUnityPos(·)` of **(a)** the composed node-0 world point and **(b)**
the 8 `BONES`-AABB corners through the logged `VIEW·PROJ`, comparing against the **native GTE** screen output
(`M` + `OFX/OFY/H`, the identical reprojection `flight_v9_solve.py` uses). Residuals in **native px** (screen
320×220; `SX = 160 + 160·ndc.x`, `SY = 110 − 110·ndc.y`). Six candidate maps are scored so the winner is
*shown*, not asserted.

**(3a) The managed camera IS the native camera + the sign pattern (VIEW == `PsxMatrix2UnityMatrix(PSXCAM.M)`):**
rotation residual `mean 1.1e-3`, and on camera-stable frames `= 2.4e-4` (the `1/4096` quantization) — the
`[[+,-,+],[-,+,-],[-,+,-]]` view-matrix sign pattern reproduces **exactly**. Translation
(`m03−(+tx)`, `m13−(−ty)`, `m23−(−tz)`) residual `mean ≈ +8 u`, `p95 ≈ 48–115 u` — the **≤1-step temporal
residual** (the managed `VIEW` is sampled at a slightly different native tick than the drawing `M`; large only
at the 15 hard cuts). `OFX/OFY` constant `{160}/{120}` all cast.

**(3b) Reprojection residual (candidate A = `(x,-y,z)` scale 1 — the source-derived map):**

| mode | target | median \|dx\| | median \|dy\| | median \|d\| | p95 \|dx\| | p95 \|dy\| |
|---|---|---|---|---|---|---|
| **pure calib.** (VIEW rebuilt from same-frame `M`; temporal removed) | node-0 | **2.4 px** | **0.58 px** | **2.5 px** | 45.8 | 1.0 |
| pure calib. | AABB corners | 29.6 px | **0.55 px** | 29.6 px | 175 | 1.1 |
| **real hybrid** (logged `VIEW·PROJ`, camera-stable frames) | node-0 | 6.0 px | 0.58 px | 6.0 px | 46.7 | 1.5 |
| real hybrid | AABB corners | 27.4 px | 0.64 px | 27.4 px | 226 | 4.4 |

Identical (to ≤0.2 px) across sessions **0, 2, 3** (all five sessions parse identically; session 1 is a
shorter 444-frame cast). **The vertical axis is sub-pixel everywhere (0.55–0.64 px median)** — the native GTE
is reproduced vertically *exactly*, as FORMAT.md's "proven by construction (`OFY=120`)" predicted, now
**measured**. The horizontal residual is entirely the widescreen frustum (§4): sub-pixel at screen center,
growing toward the edges (node-0 sits near center → 2.4 px; the AABB corners span to the edges → 29.6 px, all
horizontal).

**(3c) Candidate comparison — A wins decisively (median \|d\| px, pure calibration, session 0):**

| candidate | node-0 | corners | verdict |
|---|---|---|---|
| **A `(x,-y, z)` scale 1  — SOURCE-DERIVED** | **2.6** | **29.6** | ✅ winner every session, both targets |
| B `(x,-y,-z)` scale 1  — *TRANSPLANT §2.1 guess* | 231 | 377 | ✗ **88× worse** (the z-negation is wrong) |
| C `(x, y, z)` scale 1  (no flip) | 844 | 1001 | ✗ (Y must flip) |
| D `(-x,-y, z)` scale 1 | 4.9 | 271 | ✗ near-tie at near-center node-0, **9× worse** on the spatially-spread corners → the AABB test pins the x-sign |
| A/256 `(x,-y,z)` scale 1/256 | 253 | 332 | ✗ (scale ≠ 1/256) |
| A×256 `(x,-y,z)` scale 256 | 304 | 377 | ✗ (scale ≠ 256) |

---

## 4. THE WIDESCREEN AXIS (the one honest caveat, now MEASURED)

The native GTE draws horizontally with `OFX = 160` (a 320-wide native screen); the managed
`PsxProj2UnityProj` uses `FieldMap.HalfScreenWidth` (`PsxCamera.cs:177`), which is **widescreen-dependent**
(`HalfScreenWidth = PsxScreenHeightNative · Screen.width / Screen.height / 2`, `FieldMap.cs:2380`). Measured
on this cast:

- `HalfScreenWidth = 195.00` constant all cast ⟹ aspect `2·195/220 = 1.773` = **16:9**.
- **`near == H`**: `PROJ.m11·110` (the reconstructed near) − `PSXCAM.H` has `mean +0.08`, so the managed near
  plane **is** the native projection distance `H`.
- Horizontal factor `160 / HalfScreenWidth = 0.8205` ⟹ off-center residual `≈ 28.7 px per unit
  native-ndc.x`, **zero at screen center**. General form (aspect-only, no fit):

  ```
  horizontal_factor = 160 / HalfScreenWidth = 160 / (110·aspect) = 1.4545 / aspect
     aspect 1.4545 (= 320/220, the native PSX ratio):  factor 1.000  (horizontal ALSO exact)
     aspect 1.778  (16:9):                              factor 0.820  (this cast)
     aspect 1.333  (4:3):                               factor 1.091
  ```

**This is a property of Memoria's camera reconstruction, NOT of the position map** — the calibration places
our mesh at the correct Unity *world* point; the residual is downstream in `PsxProj2UnityProj`. Because our
hybrid mesh renders through the SAME `Camera.main` as all Unity battle content and we hide the native body,
our mesh appears at the *widescreen-correct* position. It only diverges from the kept native **effect** prims
— which `SFXRender.Render()` draws in native-320 screen space with `worldToCameraMatrix = identity`
(`SFXRender.cs:130`) — off-center, by this factor. That is the horizontal analogue of the effect-depth
residual: measurable, decidable per-summon. If a summon needs edge-of-frame registration against those prims,
the fix is to drive `Camera.main` from the decoded native camera track (risk #2), **not** to touch
`PsxToUnityPos`.

---

## 5. THE SCALE SWEEP IS INHERITED FOR FREE (s54 needs no scale feed)

**M0 UPDATE 2026-07-23 (re-ordered per the adversarial re-derivation, `m0/VERIFY_CALIBRATION.md` C6):** the
**primary scale-sweep datum is the ROOT `+0x40` anchor's** column-norm sweep — **0.0156× → 2.9978×**, i.e. the
authored **0.02 → 3.0×**, reproduced on both the unused verification session (4) and the control session (0).
The composed node-0 3×3's own column-norm sweep is quoted alongside it (**0.0154× → 2.9958×**, `/4096`) but is
**sane-filter-dependent, not a second independent confirmation on the same footing**: the *raw*, unfiltered
composed col-norm reaches **~9.2×** on stale post-creature frames (e.g. f512, where the composed world point
is `(-5.2e8, 6.4e7, 2.0e9)` — garbage from a recycled arena) while the ROOT anchor stays clean at the same
frame (`col-norm 1.5×`). The ROOT anchor (where `ScaleMatrix @0x1879a` folds the authored scale, FORMAT.md
§1.4) is the robust load-bearing number; the composed-node-0 figure needs the `sane_model` filter to mean
anything. And the `BONES`-AABB **world diagonal tracks the anchor scale linearly** (`diag/scale ≈ 5448 u/×`;
0.016× → 85 u, 2.998× → 15543 u), so the scale **is** the node-position spread. Therefore the hybrid, which
writes each node's world *position* via `PsxToUnityPos`, **inherits the whole 0.02→3.0 scale sweep for free**
— the exact term `root_reproject.py:43/75` silently discarded in FLIGHT. Do **not** also apply it as
`localScale` (`PsxToUnityRot` already normalizes the scale out of the orientation) or the creature doubles in
size.

---

## 6. WHERE FIRST-PRINCIPLES CONTRADICT TRANSPLANT §2.1 — SAID LOUDLY

TRANSPLANT §2.1 wrote the map as a **PLAUSIBLE guess**: *"translation = the s32 triple mapped
`(tx,-ty,-tz)/scale`"* with the scale "calibrated once." **The source says, and the data confirms:**

1. **The z-sign is NOT negated.** `PsxToUnityPos = (x,-y,z)`, not `(x,-y,-z)`. The z-negated guess (candidate
   B) reprojects **231 px** off at node-0 vs **2.6 px** for the correct map — an **88×** miss. (The z flip
   belongs to the *view* matrix, `worldToCameraMatrix.m2*`, not to a *world* position.)
2. **There is NO scale to calibrate.** `scale = 1` exactly (`M.t` used raw on both sides). A `/256` or `×256`
   scale reprojects 100–130× worse. TRANSPLANT's "calibrated ONCE against the AABB" framing implied a free
   parameter; there is none — the map is fully determined by `PsxMatrix2UnityMatrix` + `cameraOffset = 0`.
3. **The rotation is a conjugation `B·R·B`, not "columns 1,2 negated."** TRANSPLANT's "s16 3×3 ÷ 4096 with
   columns 1,2 negated" (`R·diag(1,-1,-1)`) gives sign pattern `[[+,-,-],[+,-,-],[+,-,-]]`; the correct
   basis-change gives `[[+,-,+],[-,+,-],[+,-,+]]`. (No linear sign map can be validated on-screen from this
   log — orientation has no pure screen observable — but `B·R·B` is the map *consistent with the validated
   position map*, and it is the only one that keeps rotations proper under the position handedness.)

The recommendation is **unchanged and strengthened**: the map is exact and parameter-free, and the hybrid's
camera/motion/scale inheritance all hold.

---

## 7. THE ONE DOWNSTREAM CAVEAT FOR s54 (rotation, not position)

`PsxToUnityRot`'s `B·R·B` is **orthonormal on every frame** (`max‖UᵀUᵀ−I‖ = 0.0156`), **proper (det +1) on
308/333 frames**, but a **reflection (det −1) on 25 frames** — the ~3.0× climax hold (`f153..f177`), where the
raw stored `+0x38`/`+0x40` matrix is *intrinsically* improper (e.g. f153 `[-12271,0,0; 0,0,12270; 0,-12271,0]`,
col-norms all 2.996×, `det < 0`). Since **any** linear sign map preserves or *uniformly* flips det, and the
raw det is **mixed**, no choice of signs fixes it — the improper frames are a property of the PSX data. The
`if (R.determinant < 0) flip column 2` guard in §2 keeps the quaternion extraction valid; **which** correction
looks right is not screen-observable in this log and must be confirmed visually at **M1b**. This touches only
the ~7.5% climax-hold frames' *orientation* — **position is unaffected and fully validated**.

---

## 8. PROVENANCE

`m0/calibrate.py` reads only the user's own `sfxmeshprobe.log` (the sanctioned probe class — camera/staging,
same as s48/s52) and the open-source `Assembly-CSharp` cites; it computes screen residuals and aggregate
statistics, embeds no game bytes, and touches **bone 0 only** (the composed node-0 row + the irreversible
`BONES` AABB) — never `bones[1..92]`. No DLL read, no asset extraction, nothing deployed. Reproduce:
`py m0/calibrate.py` (log path is a constant at the top).
