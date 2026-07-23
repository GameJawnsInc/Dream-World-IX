# V-M1-06 — adversarial verification: "the anchor FREEZE explains the tracking failure"

**Claim under test (M1-06, source `M1-effmodel-array.md` §11):** the reported "~40,000 units off" is
genuine staging data, not a corrupt read, **and** the tracking failure is explained by the anchor
*freezing* mid-cast — logged anchor sweeps z 9216 → −15104 → −39424 over f156-166 then holds constant at
(0,−12288,−7168) from f301 to 561 (~43% of the capture) **while the creature is still animating**.

**VERDICT: PARTIAL.**
* **Half 1 — "genuine staging data, not a corrupt read": CONFIRMED**, and more strongly than the artifact
  argued (§1, §2 below).
* **Half 2 — "the tracking failure is explained by the freeze": REFUTED.** The anchor mis-locates the
  creature *while it is animating per-frame*, not only while frozen. The last frame at which the anchor
  projects on-screen is **f107**; from **f108 to f561 — 454 of 512 ROOT frames, 89% —** it projects
  off-screen, including **126 frames (f108-233) where the anchor changes every single frame and all seven
  creature body meshes are being drawn** (§3). A freeze that begins at f234/f301 cannot explain a failure
  that is already total at f108.
* Two subsidiary numbers in the claim are wrong or incomplete: the freeze is **51.0%** of the capture, not
  ~43%; the claim **omits an equally-real earlier freeze** (f234-300, 67 frames); the ramp actually runs
  **f153-168**, not f156-166; and for **144 of the 261 frozen frames (f418-561) the creature is not drawn
  at all**, so "while the creature is still animating" is false for 55% of the very span cited.

Everything below was re-derived from scratch: fresh `refkit` disassembly of the user's own
`FF9SpecialEffectPlugin.dll`, and a from-scratch parse of `sfxmeshprobe.log` (the M1 aggregates were not
reused). Scripts: `C:/gd/SCRATCH/summon-format/m106_{root,b,c,d,e,f,g,h}.py` (scratch, not committed —
they only read the user's own log + DLL).

---

## 1. The read is at the right address (re-derived, not taken on trust)

`SfxMeshProbe.LogSummonRoot()` (`Memoria/Battle/SFX/SfxMeshProbe.cs:326-360`) reads
`base+0x220830`, `active` at `+0x50`, `DATA` at `+0x00`, matrix at `DATA+0x40`, translation
`s32 @ +0x14/+0x18/+0x1c`. Independently reproduced by fresh disassembly:

| probe constant | fresh evidence (x64, ImageBase 0x180000000) |
|---|---|
| record base `0x220830` | `Hi_DrawEffModelByBone` body: `lea rcx,[rip+0x209f3f]` @`0x1800168ea` (next=`0x1800168f1`) → RVA **0x220830** |
| stride `0x58` | `imul rax, rsi, 0x58` @`0x1800168f1` |
| active `+0x50` | `cmp byte ptr [rax+rcx+0x50], r14b` @`0x1800168f5` (r14b=0), `je` to the HIRAISHI stub `0x16c80` |
| DATA at `rec+0x00` | `mov rax,[rax+rcx]` @`0x180016900` |
| bones at `DATA+0x38` | `mov rax,[rax+0x38]` @`0x18001690d` (the *composed* array — §4) |
| root matrix at `DATA+0x40` | `pose_eval` entry `lea rbx,[rcx+0x40]` @`0x1800186b2`; translation stores `mov [rbx+0x14],eax` / `[rbx+0x18]` / `[rbx+0x1c]` @`0x18001873b`/`0x180018742`/`0x180018749`; fp12 identity seed `mov dword[rbx],0x1000` @`0x1800186dc`, `mov dword[rbx+6],0x10000000` @`0x1800186d1` |
| written every Draw | `Hi_DrawSummonModel` body `call 0x1800186a0` (pose_eval) @`0x180017767`, with `rdi` = the record (`mov rax,[rdi]` @`0x18001776c`, frame counter `word[rdi+0x54]` @`0x1800177c5`) |

So the probe reads exactly the field `pose_eval` writes. **No address error is available as an
explanation for the values.**

## 2. The values are structurally valid — the "~40,000" is real data (CONFIRMED)

Re-parsed from the log on disk (`sfxmeshprobe.log`, 28,116 lines, 2,045 `ROOT` rows, effect **227**,
frames **50-561**, 512 distinct frames, **no gaps**, `active==1` on every row):

* **146 distinct translations** — matches the claim exactly. 72 distinct rotations; 146 distinct
  (rot,trans) pairs; **zero frames carry more than one distinct value** (no read tearing).
* **The cited samples reproduce byte-for-byte**: f156 `(2048,−4096,9216)`, f161 `(2048,−4096,−15104)`,
  f166 `(2048,−4096,−39424)` — with rotation `(−12279,0,0, 0,12279,0, 0,0,12279)` at all three.
* **Every rotation is an exact orthogonal matrix times a uniform fp12 scale** (checked
  `Rᵀ R = I` to 2e-3): f107 → 6139.8/6140.0/6139.1, scale **1.4989**, det +1; f166 → 12279 ×3, scale
  **2.9978**, det −1 (a mirrored/flipped stage pose); f204 → 4093 ×3, scale **0.9993**;
  f301 → 6140/6139/6140, scale **1.4989**. Garbage memory does not produce orthonormal frames.
* **The ramps are exactly linear in integers**: f153→f168 steps z by a constant **−4864/frame**
  (23808 → −49152, 16 frames); f178→f204 steps y by a constant **−384/frame**.

⇒ **Half 1 is CONFIRMED.** These are authored staging numbers.

Caveat worth recording: the uniform scale factor *changes between segments*
(1.4989 → a 0→2.1 ramp over f128-152 → 2.9978 → 0.9993 → 1.4989). A single-slot array whose pose scale
jumps by 2× and 3× is consistent with the `.seq` re-posing the one summon slot for different staged
objects/shots — i.e. **not every anchor segment is necessarily the creature**. That is an open question,
not a finding.

## 3. THE REFUTATION — the anchor is wrong long before it freezes

Reprojected every ROOT translation through the **same frame's** logged `VIEW` then `PROJ`
(`matrix_solve.project_world_to_ndc`; on-screen ⇔ |ndc_x|<1 ∧ |ndc_y|<1 ∧ view_z<0), and cross-cut it
against the presence of the seven creature body-mesh keys (`matrix_solve.BODY_KEYS` =
`0033B990 0033B9D0 0035BAD0 0035BA90 0034BA10 0034BA50 0097BD02`).

Independent corroboration that those seven keys ARE the creature: they all appear for the first time at
**exactly frame 82** — the same frame the ROOT matrix stops being all-zero (frames 50-81 are zero, i.e.
`Hi_DrawSummonModel` had not yet run). They are present f82-417 (323 frames, only two gaps: f153-154 and
f167-177) and **never again after f417**.

| span | frames | body meshes drawn | anchor animated? | anchor projects on-screen | median \|ndc_y\| | median view_z |
|---|---|---|---|---|---|---|
| f50-81 | 32 | no (pre-draw) | all-zero | 32 (100%) — meaningless, it is the origin | — | — |
| f82-152 fly-in | 71 | **71/71** | per-frame | **26 (36.6%)** | 0.80 | −1067 |
| f153-177 fly-by | 25 | 12/25 | per-frame (f153-168) | **0 (0%)** | 0.78 | −35642 |
| f178-233 descent | 56 | **56/56** | **per-frame** | **0 (0%)** | **20.71** | **+2644 (BEHIND cam)** |
| f234-300 **FROZEN A** | 67 | 67/67 | frozen `(0,−23567,15878)` | 0 (0%) | 11.46 | +13998 |
| f301-417 **FROZEN B** | 117 | 117/117 | frozen `(0,−12288,−7168)` | 0 (0%) | 6.66 | −1146 |
| f418-561 **FROZEN B** | 144 | **0/144** | frozen (stale) | 0 (0%) | 13.05 | −4035 |

**The killer row is f178-233.** 56 consecutive frames, the anchor changing every frame
(y −8576 → −23567, z 21248 → 15878, all steps integral and smooth), all seven body meshes drawn every
frame — and the anchor projects **20 screen-heights off in Y and behind the camera** in every one of
them. A frozen anchor is not the mechanism; the anchor is simply **not the creature's world position**.

Exact on-screen census: **58 of 512** ROOT frames project on-screen; 32 of those are the pre-draw
all-zero frames and the other 26 are inside f82-107. **The last frame at which the anchor projects
on-screen is f107.** From f108 to f561 — 454 frames, 88.7% — it is off-screen, and that includes 126
animated-anchor frames before any freeze begins.

(The space/scale of the ROOT translation and of the logged `VIEW` do agree: the f82-107 window projects
coherently on-screen with median |ndc_y| 0.80 and camera distance 203-12031. A unit mismatch would fail
everywhere, not for exactly the frames after the fly-in.)

## 4. The mechanism that DOES fit (already stated in the same artifact, §6)

`pose_eval@0x1800186a0` writes `DATA+0x40` from *the arguments the `.seq` handed `Hi_DrawSummonModel`
this frame*. The matrix actually fed to the GTE is built by `build_world_matrices@0x7820` into
`*(MATRIX*)(DATA+0x38)`, composing `root ∘ motionRootTrack[frame] ∘ boneChain` —
`Hi_DrawEffModelByBone` proves the shape by copying `SummonData->bones[b]` out of `DATA+0x38`
(`0x18001690d`/`0x18001691b`). The anchor is one of two inputs; the flight lives in the motion clip and
only materialises in `bones[0]`.

**The freeze is a symptom of that, not the cause**: when the `.seq` parks the anchor and lets the motion
clip carry the creature, the anchor is *visibly* stale — but it is equally wrong in the spans where the
`.seq` does animate it, because it was never the creature's world position in the first place. Anyone
reading M1-06 as "unfreeze the anchor / interpolate through the freeze and tracking is fixed" will build
another wrong flight. The fix is the one dereference deeper (`DATA+0x38 → bones[0]`), which M1 §10 already
specifies.

## 5. Corrections to the record

1. `~43% of the capture` → the f301-561 hold is **261/512 = 51.0%** of ROOT frames (identically 51.0% of
   ROOT rows, 1043/2045). Over the whole logged effect (f11-561) it is 47.4%. 43% matches no denominator
   in the file.
2. `frames 156-166` → the ramp is **f153-168** (23808 → −49152, constant −4864/frame). f169-177 hold at
   −49152.
3. The claim omits **FROZEN A**: the anchor is *also* constant at `(0,−23567,15878)` for **f234-300**
   (67 frames). From f234 to f561 the anchor takes exactly **two** values over 328 frames (64% of the
   capture). The freeze is bigger than claimed, which makes it a *worse* explanation, not a better one:
   the failure predates it by 126 frames.
4. `while the creature is still animating` (of the f301-561 hold) → true only for **f301-417**; the seven
   body-mesh keys vanish after **f417** and never return, so for **f418-561 (144 of 261 frozen frames,
   55%)** the creature is not being drawn and the ROOT row is a stale leftover.
5. **M1 §12's residual doubt is itself resolvable and wrong**: it says "NOT proven that *Bahamut
   specifically* (effect 194) behaves like effect 227 — the log on disk is 227." Effect **227 IS
   Bahamut**: `Bahamut__Full` resolves to 227 (`studies/custom-summons/thomas-swap/README.md:113`, and
   `matrix_solve.BAHAMUT_EFFECT_ID = 227` at `matrix_solve.py:103`). The capture on disk *is* a real
   Bahamut cast; there is no id gap to close. (The orchestrating brief's "effect 194" is likewise a
   mis-id.)
6. Consequence for the claim's own falsifier ("re-capture a Bahamut cast and find the anchor varies
   smoothly throughout the charge") — it never needed a re-capture. The existing capture already contains
   a 56-frame span where the anchor **does** vary smoothly, the creature **is** drawn, and the tracking is
   **still** totally wrong. That is the refutation, in-file.

## 6. Where the user's "~40,000 units BELOW/BEHIND the camera" actually comes from

Distance from the camera to the logged anchor, per span (view-space magnitude):
f82-152 median **6,338**; f153-177 **41,817**; f178-233 **36,425**; f234-300 **45,188**; f301-417
**24,817**; f418-561 **14,731**. 26 frames sit in the 35k-45k band: f164-165, **f205-224**, f274-276,
f301. The 35k-47k regime therefore covers **f153-300** — spanning the animated descent (f178-233, where
view_z is **positive** = literally behind the camera, and ndc_y ≈ +20) and FROZEN A. So the user's report
is a faithful description of f178-300, **most of which has a moving anchor**. This is the same conclusion
as §3 arrived at from a different measurement.

## 7. Provenance

Static read-only disassembly of the user's own installed `FF9SpecialEffectPlugin.dll` (RVAs, mnemonics,
offsets only) plus aggregate statistics over the user's own `sfxmeshprobe.log` debug output
(choreography/staging class). No DLL was modified. No stock geometry, animation, or texture bytes were
read, extracted, or written. Scratch scripts live under `C:/gd/SCRATCH/summon-format/`.
