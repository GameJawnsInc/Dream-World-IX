# DEPTH-GATE — M0 item (d): the effect/creature depth-interleave verdict for Bahamut

**Round:** M0 READOUT (item d). **Input:** one full instrumented Bahamut cast, bench 30300, effect
**227**, frames 11..561, body **UNHIDDEN** (`build_thomas.py --calibrate`, donor line byte-identical to
stock). Archived snapshot: `C:\gd\SCRATCH\summon-transplant\logs\sfxmeshprobe.20260724-012109.log`
(30.8 MB; `PRIM=548045`, no truncation marker). **Tool:** `m0/depth_gate.py` (calibrated in place this
round; re-run any time with `py m0/depth_gate.py --log <snapshot>`).

**Bottom line:** **MIXED → NATIVE-NEEDED.** Bahamut's creature is depth-**interleaved** with its own
effect field — pervasively during the fly-in and, decisively, during the **Mega-Flare ground-reign
climax** (the summon's longest, headline phase). The hybrid's wholesale front/behind sort cannot order
that content; per TRANSPLANT §1.2/1.5 Bahamut is a **native-reserve** summon. The far/approach/charge
phases are behind-dominant and would composite acceptably under the hybrid. One honest hedge (below):
the gate proves the *content* interleaves; whether the hybrid's compositing actually bites is the
unconfirmed ZTest question M1a settles by eye.

---

## 1. Why the old table was garbage (and the four fixes)

The placeholder gate printed a saturated, non-discriminating table: `overlap==w/prims`, `near≈100%`
every phase, rates over 100% (117/187/700%), verdict NATIVE on placeholder constants. Its own docstring
said not to trust it. Root causes, each fixed:

| # | defect | why it saturated | fix |
|---|--------|------------------|-----|
| 1 | **staleness** | after the body stops drawing (~f413) the summon-slot BONES AABB is arena garbage (bands in the **billions**); the old gate reprojected garbage boxes on frames 416..561 and treated them as creature-present | creature-present = the summon `MODEL(kind=S)` row is **non-stale** (`bones32≠0` AND `\|world−anchor\|≤5000` every axis — flight_v9's own test). Yields frames **82..412**, matching the body-key MESH window 82..417. |
| 2 | **body-prim pollution** | `--calibrate` leaves the body visible, so the creature's own prims land inside its own silhouette at its own depth → counted as "nearer-overlapping effect" | a discriminator needing **no per-prim key** (see §2) — exclude the whole body depth band; score only prims clearly outside it |
| 3 | **placeholder constants** | `DEPTH_EPS=50` **absolute**, while raw otz spans ~230 (near) to ~35000 (far) across the 0.02→3.0× scale sweep — a fixed 50 is meaningless at distance | `AABB_PAD_PX=8` (measured); depth margin **proportional** to centroid depth (§4) |
| 4 | **>100% rates** | numerator (near-overlap) counted on ALL creature-present frames; denominator (framed) counted only framed → 117/187 etc. | every rate uses `frames_framed` as denominator; every numerator gated on framed |

---

## 2. Method + the discriminator

**Per reliable+framed frame:** reproject the 8 corners of the summon's BONES-AABB and its centroid
through the **native GTE** (`M`+OFX/OFY/H from the `PSXCAM` row; the zero-free-parameter identity reused
verbatim from `flight_v9_solve.py`) → the creature's **screen AABB** (padded) and its **depth band**
`[zmin, zmax]` in raw native otz (smaller = nearer). Widescreen `drOffsetX` is self-calibrated per run
(this cast: **+36 px**, i.e. 16:9 — matched on 40,082 body prims) and subtracted from every PRIM x
before the box test.

**The discriminator (body exclusion without per-prim keys).** PRIM rows carry **no mesh key**, and the
prim stream is **one depth-sorted ordering table** (idx 0 at otz≈23000 → idx 1584 at otz≈32, back to
front) with body and effect prims **interleaved by depth** — so neither index ranges nor the ABR/blend
state can attribute a prim to the 7 body keys. Instead: **exclude the creature's entire reprojected
depth band** `[zmin−Δ, zmax+Δ]` (Δ calibrated to contain the body, §4). Then classify each
inside-silhouette prim:

- **FRONT** = `raw otz < zmin−Δ` — **nearer than the whole body**. An effect by construction (the body
  has no geometry nearer than its own near face + Δ).
- **BEHIND** = `raw otz > zmax+Δ` — **farther than the whole body**. Also an effect by construction.
- **IN-BAND** = within the band — body prims **plus** any in-volume wrapping effect, **not separable on
  a body-visible cast**. Reported (`medIn`), never scored.

The decisive, body-exclusion-robust signals are therefore **FRONT** and **STRADDLE** (FRONT *and*
BEHIND on the same frame). Straddle = the creature is embedded in the effect depth field → **no single
wholesale front/behind order is correct**. A "side" counts only at ≥ `MIN_SIDE_PRIMS`=3 prims, so one
stray body-margin prim can't manufacture a straddle.

### 2.1 The stream structure this rests on (measured, frame 300)
Head of the stream (idx 0..148): **pure FT4/GT4**, otz 23360→8400, all **BEHIND** the body band — the
background aura. FT3 (the body, 80% of body prims) first appears only once otz enters the band, mixed
with GT4/FT4. Tail (idx ~1490..1584): otz drops below the band, ending in **FT4_BLUR at otz 32** (16
prims) — a **foreground** burst. So the creature is depth-sorted into the *middle* of a continuous
effect field: background behind → body+wrap → foreground in front.

---

## 3. Validation of the discriminator

1. **The body signal vanishes on the undrawn tail (the brief's key check).** Body FT3 prim count per
   frame: **f410 = 1008 → f411 = 158 → f412 = 7 → f413 = 0**, exactly when the creature stops drawing.
   The staleness filter cuts creature-present at f412, and the IN-BAND (body) population collapses at the
   same boundary — the excluded band tracks the *real* body, not an artifact.
2. **Phase structure is physically sensible.** Behind-effects present ~80–100% everywhere (a summon
   always has an energy backdrop); FRONT effects appear where the choreography puts energy near the
   camera — the fly-in (P1→P2) and the ground-reign Mega-Flare climax (P8→P9); the far/deep hold is
   front-only (the distant dragon behind a foreground charge glow); the approach/charge are behind-only.
3. **The band contains the body.** The body's own FT3 prims poke beyond the bone-cloud band by only
   **p50 = 0, p90 ≈ 395 units (≈5.5% of centroid depth), p99 ≈ 3064** — so at Δ = 5.5% the FRONT/BEHIND
   populations carry <10% body leakage, and that leakage is symmetric noise (guarded by `MIN_SIDE_PRIMS`).
4. **FRONT/BEHIND are type-distinct from the body where it matters.** BEHIND is **84% FT4** (billboards)
   vs the body's 80% FT3 — a genuinely different, depth-separated population, not misclassified body.

**Residual (stated honestly):** the IN-VOLUME wrap — an effect prim at the body's *own* depth — is
**masked by the visible body on this cast** and cannot be counted (`medIn` is body + wrap combined). It
can only widen the case for interleave, never narrow it; M1a (body hidden) is where it becomes visible.

---

## 4. Calibrated constants + derivations

| constant | value | derivation |
|---|---|---|
| `AABB_PAD_PX` | **8.0 px** | native-GTE reprojection residual, CAMERA-MATCH.md: radial p95 = 7.65 px (h p95 2.96 / v p95 7.16) |
| `DEPTH_EPS_FRAC` | **0.055** | p90 of body-FT3 overshoot beyond the bone-cloud band, as a fraction of centroid depth (overshoot p50=0, p90≈0.055, p99≈0.19). **Proportional** to depth because raw otz scales with distance across the 0.02→3.0× sweep — a fixed absolute margin (the old 50) is meaningless at otz≈35000. |
| `DEPTH_EPS_FLOOR` | **64** | otz quantization floor (distinct-value spacing p50=16, p90=48) — guards the rare near-camera frame where `0.055·depth` would underflow the noise |
| `MIN_SIDE_PRIMS` | **3** | one leaked body-margin prim must not fake a straddle; real effect layers hold tens–hundreds/side |
| `FRAMED_NDC_MARGIN` | 1.50 | unchanged (flight_v9's `NDC_CLAMP`) |
| staleness tol | 5000 | flight_v9's own `\|world−anchor\|` reliability test |

Sampled raw-otz readout the gate prints (inside-silhouette prims, n=20000): p5=2160 p50=5408 p95=12224
min=−16 max=35264 — the distribution the proportional margin is scaled against.

---

## 5. The final table (nominal Δ, gate output)

```
phase                       frmd  front  strad  behind   medFr medBh medIn   verdict
P1->P2 rise-to-far            52    65%    65%    100%      14    96   626    NATIVE-NEEDED
P2->P3 far-dip                 9    11%     0%     89%       0   120  1016    BORDERLINE
P3->P4 far-deep hold           8    25%     0%      0%       2     1  1028    BORDERLINE   (low-n)
P4->P5 return-cut              1     0%     0%    100%       2    31  1148    INSUFFICIENT-DATA
P5->P6 2nd-approach           25     8%     8%    100%       0    32  1057    BORDERLINE
P6->P7 charge-cut              3    33%    33%    100%       0    32   909    INSUFFICIENT-DATA
P7->P8 charge-hold            40     8%     8%    100%       0    58  1160    BORDERLINE
P8->P9 ground-reign          145    39%    28%     69%       0    44  1423    NATIVE-NEEDED
                             ----
VERDICT: MIXED (NATIVE-NEEDED in the fly-in and the Mega-Flare climax)
```
(`front`/`strad`/`behind` = % of the phase's framed frames with ≥3 effect prims nearer / on both sides /
farther than the body. `medFr`=0 with `front`=39% means >half the frames are under the 3-prim floor but
39% clear it. `medIn` = body + unresolved wrap, not scored.)

**Reading.** A **background** effect layer sits behind the creature on ~80–100% of frames everywhere
(the aura). The creature acquires a **foreground** layer during the fly-in (P1→P2, 65% front / 65%
straddle) and the **ground-reign Mega-Flare climax** (P8→P9, the 145-frame headline: 39% front / 28%
straddle). On those frames effects sit on **both** sides of the creature → the wholesale sort is
necessarily wrong. The far-dip/approach/charge phases (P2→P7) are **behind-dominant** with only stray
front prims → a hybrid that sorts effects behind the mesh composites them acceptably.

---

## 6. Verdict + sensitivity

**Per phase:** NATIVE-NEEDED = **P1→P2 (fly-in)** and **P8→P9 (Mega-Flare ground-reign)**. BORDERLINE
(behind-dominant, hybrid-tolerable) = P2→P3, P3→P4, P5→P6, P7→P8. INSUFFICIENT-DATA = the 1–3-frame cuts.
**Overall = MIXED, and because a summon is judged by its climax and the climax fails, the operative call
is NATIVE-NEEDED for Bahamut.**

**Sensitivity (Δ halved → nominal → doubled; run through the gate):**

| Δ | overall front / strad / behind | NATIVE-NEEDED phases |
|---|---|---|
| **0.5×** (frac 0.0275) | 39% / 31% / 82% | P1→P2, **P2→P3, P3→P4,** P8→P9 |
| **1×** (frac 0.055) | 35% / 28% / 81% | P1→P2, P8→P9 |
| **2×** (frac 0.110) | 32% / 25% / 81% | P1→P2, P8→P9 |

**The two headline phases (fly-in + Mega-Flare climax) are NATIVE-NEEDED across the ENTIRE Δ range** —
the verdict does not hinge on the margin. Doubling Δ only trims the borderline far phases; halving it
tips two more far phases into NATIVE. The MIXED-leaning-NATIVE conclusion is robust; only the count of
*additional* borderline phases moves.

**The one honest hedge (the crux for whether it bites in-game).** This gate proves the **content** is
interleaved — decisively. Whether the **hybrid's compositing** actually misorders depends on the
UNCONFIRMED ZTest/shared-ruler question: `SFXRender.Render()` draws the effect prims with
`worldToCameraMatrix=identity` and their raw `GzDepth` as Z, while our hybrid mesh renders through the
real view matrix in Unity units (TRANSPLANT §1.5 reads this as a **wholesale** sort — different Z
origins). If, contrary to that reading, the effect Z and our mesh's Unity eye-Z happened to share a
ruler through the common `projectionMatrix` (CALIBRATION.md pins the world scale at ~1) and ZTest is on,
the depth buffer could interleave them correctly and the hybrid would survive. The shaders are compiled
Unity assets not in the source tree, so this cannot be closed offline. **Default expectation: the
climax misorders → native reserve.**

---

## 7. What M1a's in-game cast must visually confirm

M1a = a rung-7 FBX in a Bahamut donor cast with the body hidden via the managed `HideMeshes=` split.
Point the eye at exactly the two questions this gate raised but cannot close offline:

1. **The IN-VOLUME wrap (the masked residual).** During the **ground-reign Mega Flare (frames ~250–410)**
   and the **fly-in (~82–140)**, does the swirling energy/flare read as **passing through / around** our
   mesh (some of it in front of near parts, occluded by far parts), or does the whole effect snap to one
   side of the mesh (all-in-front washout, or all-behind hidden flare)? A one-sided snap = the wholesale
   misorder this gate predicts; a correct wrap = the ZTest hedge held and Bahamut can stay hybrid.
2. **The foreground burst.** Watch the near foreground prims (the FT4_BLUR/flare that this gate places
   at otz≈30, well in front): are they drawn **over** the creature, or wrongly **occluded** by our opaque
   mesh? The latter is the visible failure mode.

The far/approach/charge phases are the *control*: they should look fine under the hybrid regardless (the
gate says behind-only there), so a defect confined to the climax/fly-in confirms the gate's phase map.

---

## 8. What this means for M1b (native slot or not?)

**Bahamut is a NATIVE-RESERVE summon by the depth test.** The hybrid (M1b) still delivers everything the
overlay never could — faithful articulation, root flight, the 0.02→3.0 scale sweep, the native camera,
clock-locked — for **all** phases, and it is the right build for the fly-by/charge beats. But its one
true ceiling, the effect-depth regime (TRANSPLANT §1.2/1.5), **is exercised hard by this donor**: the
Mega-Flare climax embeds the dragon in a front-and-behind effect field on ~28–65% of framed frames
(robust to Δ). So:

- **Build the hybrid (M1b) anyway** — it is the general engine and the correct build for most of the
  cast; do **not** gate the whole transplant on native.
- **Escalate Bahamut specifically to the native slot (M3) *iff* M1a's eye confirms the climax misorders.**
  M1a is the cheap decider — no new engine code, just the hide + a look. If M1a shows the wrap composites
  correctly (the ZTest hedge), Bahamut stays hybrid and the native lane isn't spent on it.
- **Run W0 (the $0 native load-gate) before committing to M3** — it de-risks the entire native path and
  is independent of this verdict.

**In one line:** the depth residual TRANSPLANT flagged as the hybrid's only ceiling **does bite for
Bahamut, at the climax** — so Bahamut is the summon that justifies keeping the native slot in reserve;
M1a's look is the final confirmation before spending it.

---

## VERIFICATION 2026-07-24 (adversarial skeptic, independent re-derivation)

A second agent re-derived the verdict from the same archived snapshot
(`sfxmeshprobe.20260724-012109.log`) WITHOUT importing `depth_gate.py` -- a separate parser +
reprojection + discriminator + rollup (`m0/verify_depth/independent_gate.py`, `diag.py`, `typecheck.py`,
`final_checks.py`, `scan_structure.py`). **Outcome: the arithmetic REPRODUCES exactly and the overall
MIXED / native-reserve conclusion SURVIVES; but two stated validations do NOT hold up, and the *decisive*
climax leg is materially weaker than "decisively fails, robust across the entire Delta range."**

### What reproduced / survived my refutation attempts (author vindicated)
- **The headline table reproduces to the digit** via an independent code path: P1->P2 65%/65%/100%
  NATIVE, P8->P9 39%/28%/69% NATIVE, overall MIXED, NATIVE-phases = {fly-in, ground-reign}. Same +36px
  self-calibrated offset (n=40082), same 325 creature / 283 framed frames, window 82..412.
- **Discrimination power confirmed** -- the verdict MOVES under its own knobs: `frac->2.0` (band swallows
  everything) zeroes the NATIVE signal (all HYBRID, 0 NATIVE phases); the centroid-split / no-body-
  exclusion variant SATURATES to 96%/96% all-NATIVE (reproducing the old placeholder disease). So the
  body-exclusion is load-bearing and the gate is measuring something real. DEPTH_EPS x4 (frac 0.22) keeps
  the two headline phases NATIVE but flips the far phases to HYBRID -- the machinery is not knob-invariant.
- **Body-signal validations pass**, cross-checked against a source the gate never uses (MESH rows):
  corr(summed body-MESH-tri, FT3-prim-count) = **0.960** over 318 drawn frames; the FT3 body signal
  collapses 1078->158->7->0 across f409-413 (confirmed a third way by raw awk), exactly at the staleness
  boundary. The excluded band tracks the real body.
- **My first refutation FAILED (author rescued).** I suspected the P8->P9 28% straddle was a bounding-box
  aggregation of spatially-separate near/far effects (a fixed 40x40-anchor probe gave ~0% straddle). A
  proper LOCALITY test (`final_checks.py` part B) refutes MY concern: requiring a front prim and a behind
  prim within **30px of each other** keeps the straddle at 28% (== the box straddle at every radius
  240->30). The near+far prims are genuinely co-located; the fixed anchors just missed the cluster. The
  straddle is real *local* interleave, not an artifact.
- **BEHIND is cleanly effect-typed** (69% FT4 fly-in, **88% FT4** climax, vs the body's 80% FT3) -- the
  background aura is real and depth-separated. Rate arithmetic is clean (every rate <=100% by
  construction, `frames_framed` denominator, each frame in exactly one phase); otz polarity is correct
  (raw = -logged; 547151/548045 = 99.8% negative-logged -> positive raw); phase windows match the real
  frame ranges (my reliable window 82..415 vs the gate's creature window 82..412; MESH body-key window
  82..417).

### Substantive weaknesses that SURVIVED my scrutiny (author over-claims the decisive leg)
1. **`DEPTH_EPS_FRAC = 0.055` is NOT independently reproducible -- it is ~17x too small.** The stated
   derivation is "p90 of body-FT3 overshoot beyond the bone-cloud band, as a fraction of centroid depth
   (p90 ~= 0.055)." Re-measuring that exact quantity gives **p50 ~= 0.46, p90 ~= 0.92** -- and NOT from
   climax whole-screen contamination: restricted to the clean **tight-box fly-in** frames (boxw<=320) it
   is still p50=0.469, p90=**0.922** (`final_checks.py` A). I could not reproduce 0.055 by any slicing.
2. **The FRONT population -- which supplies the "nearer than body" half of every straddle and the
   `front>33%` trigger -- is body-TYPE-dominated, i.e. confounded with body skin.** Type census of the
   inside-silhouette FRONT prims (`typecheck.py`): fly-in **80% FT3**, climax **52% FT3** (+21% G4), with
   the genuine-effect FT4/FT4_BLUR only ~5-17%. FT3 is the body's own signature (the gate itself argues
   "84% FT4 vs the body's 80% FT3" to prove BEHIND is effects). By that same logic a FRONT that is 52-80%
   FT3 looks like **body skin projecting forward of the joint-cloud zmin** -- exactly the leakage the
   0.055 margin was meant to exclude, and 0.055 is ~17x too small to exclude an overshoot whose p90 is
   ~0.92. The gate validates BEHIND's type-distinctness (sec 3.4) but never runs the same check on FRONT;
   FRONT does not pass it.
   - **This is the pivotal confound and it is unresolvable on a body-VISIBLE (--calibrate) cast:** body
     skin forward of the joint cloud and a foreground effect are indistinguishable (same FT3 type, same
     silhouette, both nearer than zmin, no per-prim key). The author flags this masking for IN-BAND
     (in-volume wrap, sec 3 residual) but not for FRONT. And it MATTERS to the hybrid decision: "body skin
     in front + effect aura behind" is the NORMAL case the wholesale sort handles CORRECTLY (our mesh
     renders its own skin in perspective, effects sorted behind) -- it is a hybrid failure ONLY if the
     FRONT prims are genuine foreground EFFECTS, which is precisely the part that cannot be established
     here.
3. **Consequently the climax P8->P9 verdict is margin-fragile, contra "robust across the ENTIRE Delta
   range."** A fine margin sweep (`diag.py`): P8->P9 stays NATIVE only to frac ~= 0.55, then flips to
   BORDER by 0.76 (front 6% / straddle 0%) -- i.e. it flips exactly at the body-skin overshoot my
   measurement (~0.9) says is the real margin. The fly-in P1->P2 is more robust (NATIVE to ~0.76). The
   published sensitivity table (0.5x/1x/2x = frac 0.0275..0.11) never reaches the body-skin overshoot
   scale, so it understates the fragility.
4. **Spatial-silhouette test is vacuous during the climax (documented, not fatal).** The reprojected
   bone-AABB exceeds the 320x240 screen on **145/145** P8->P9 frames (median 994x730 px; also 40/40 on
   P7->P8) -- so "inside the silhouette" == "anywhere on screen" there, and the climax verdict rests on
   the depth split alone, not on silhouette membership. The fly-in box IS creature-sized (165x156, only
   14/52 over-screen) and the fly-in straddle is spatially concentrated on the creature (46% at a 40x40
   centroid box vs 0-25% at off-centroid anchors) -- so the fly-in leg has genuine spatial specificity;
   the climax leg does not.
5. **Latent (harmless here): the gate never filters `effectId`.** The log holds two tiny lead-in bursts
   (eff 320: 100 PRIM / eff 329: 300 PRIM, frames 5-16) besides the Bahamut cast (eff 227: 547645 PRIM).
   Their frames (5-16) overlap eff-227 PSXCAM only at 11-16, BEFORE the creature is drawn (BONES starts
   82), so they fall entirely outside the scored 82..412 window -- verified zero contamination this run.
   But the frame-keyed join is effect-blind by construction; a future multi-cast or overlapping-effect
   log WOULD cross-contaminate. Harden by pinning the dominant effectId. (I filtered to eff 227 and got
   identical numbers, confirming it doesn't matter for THIS log.)

### Skeptic's bottom line
NOT refuted at the arithmetic level -- everything reproduces, discrimination power is real, the straddle
is genuine local interleave, and the BEHIND aura is a real effect layer. The overall "MIXED, Bahamut is a
native-reserve CANDIDATE, M1a settles it by eye" stands, and the author's own deferral to M1a (sec 6-7) is
the correct posture. **But the specific decisive framing -- "the Mega-Flare climax DECISIVELY fails,
NATIVE-NEEDED, robust across the entire Delta range" -- is overstated.** The clean, unconfounded offline
signal is only BEHIND (aura = HYBRID-OK); the FRONT/straddle evidence that drives the NATIVE call is
body-skin-confounded on a body-visible cast and margin-fragile (flips to BORDER at the empirically
measured body-skin overshoot). The honest offline conclusion is **NATIVE-LEANING-BUT-UNPROVEN, pending
M1a's body-HIDDEN cast** -- which is the one capture that removes the confound (no body skin -> FRONT is
unambiguously effect) and is exactly what sec 7 already orders. Recommend M1a additionally re-run this
gate on the body-HIDDEN log: FRONT there is decisive.
