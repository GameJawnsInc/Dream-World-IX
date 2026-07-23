# D1-1 — ADVERSARIAL VERIFICATION of D1-pipeline.md (the HYBRID recommendation)

**Verdict: CONFIRMED** (with one minor wording overstatement noted). The document's decisive
finding and its recommendation were independently re-derived from the Memoria C# source — not
trusting the cited evidence, re-read fresh. Every load-bearing source cite reproduces exactly.

## What I re-derived (all reproduced, not trusted)

1. **Camera inheritance by the managed path — the finding that decides the design — PROVEN in source.**
   `SFX.UpdateCamera()` (`Global/SFX/SFX.cs:1590-1604`) stamps `Camera.main` (or the "Battle Camera"
   fallback, :1598) `.worldToCameraMatrix = PsxCamera.PsxMatrix2UnityMatrix(array,…)` and
   `.projectionMatrix = PsxCamera.PsxProj2UnityProj(...)` every native tick, gated on
   `isSystemRun && !tutorial && !isDebugCam`. Driven by `battle.cs:86` →
   `SFXDataCamera.UpdateCamera()` (`SFXDataCamera.cs:540-546`) when `currentCameraEngine==SFX_PLUGIN`.
   A normal Unity object (our SMR) renders through that same stamped camera. **Reproduced verbatim.**

2. **The OFY=120 "proven by constants" claim — PROVEN.** `PsxProj2UnityProj` (`PsxCamera.cs:172-177`):
   `bottom = 220/2.2 = 100`, `top = 220-100 = 120` → off-center frustum vertical split = native
   OFY=120. `FieldMap.PsxScreenHeightNative = 220` (`FieldMap.cs:2336`) confirmed. The vertical
   principal point matches the native GTE by construction. **Reproduced.**

3. **All §4 hook cites — PROVEN.** `SFXDataMesh.cs`: `:607` sets `currentCameraEngine=SFX_PLUGIN`;
   `:618-619` `SFX_LateUpdate()`+`SFXRender.Update()`; `:635` `Camera.main`-or-"Battle Camera"
   resolve; `:659` `SfxMeshProbe.LogModels()` (the co-location point); `:769`
   `ModelFactory.CreateModel(tok.fbxPath,…)`. All exact.

4. **"FileList path exposes no settable bones → the drive loop is new code" — PROVEN.**
   `grep SkinnedMeshRenderer|\.bones|bindposes Memoria/Battle/SFX/` = **zero hits**. The drive loop
   is genuinely new managed code, not dead code cited as validated.

5. **Depth-interleave residual (§1.1/§1.5) — real and correctly bounded.** `SFXRender.Render()`
   sets `camera.worldToCameraMatrix = Matrix4x4.identity` for the effect prims
   (`SFXRender.cs:130`) then restores (`:135`). So effect prims render in a **screen-space regime**
   while our perspective SMR does not share their Z. D1 characterizes this as the hybrid's ONLY
   residual vs. native — neither overstated nor understated. **Reproduced.**

## Skeptical audit of confidence labels — honest

- Camera-inherited: labeled PROVEN, and it is (source). The drive-loop build (§4.2) and M1b are
  labeled **PLAUSIBLE, not PROVEN** — correct: no one has run a SMR-bone-write inside
  `Runtime.Render()`. The genuine un-traced risk (do 93 bone-Transform writes at `:659` land
  before Unity's skinning pass; does our SMR render in this camera pass) is real, but the document
  does **not** claim it proven and **does not stake a playtest on it first**.
- The milestone ladder is the opposite of the "plausible-but-wrong burns a playtest" failure mode:
  **M0** (offline, read-only, zero content — measures the camera match + calibration) → **M1a**
  (our model + native camera + hide via already-proven rung-7 FileList + FLIGHT `HideMeshes=`, no
  new engine code) → **M1b** (the s54 drive feature, only after M0 measured it). Matches the
  project's `feedback-incremental-verbatim-first` law.

## The ONE blemish (does not change the verdict)

§0 says the managed projection reproduces the native principal point **"exactly"** and a Unity
object projects to the **"same screen pixel … for free."** This is exact **only on the vertical
principal point** (OFY=120, by construction). The horizontal half-width is aspect-scaled under
widescreen (`FieldMap.CalcPsxScreenWidth` = `PsxScreenHeightNative*Screen.width/Screen.height`),
so horizontal pixel-equality is *not* free — it is what M0/P2 must measure. The document already
carries this honestly as a gate (§2.1, §8-P2: "sub-pixel modulo fp12 + widescreen aspect"), so §0
merely states as-proven what its own gate re-lists as to-be-measured. Recommend softening the §0
wording; the recommendation is unaffected.

## Native-side dependency (not re-derived here, flagged)

The `*(SummonData+0x38)` 93-world-matrix read is treated as PROVEN from prior rounds (B1, the s53
probe already reads bone-0 from it). I did not re-disassemble the DLL this pass — it is not the new
synthesis D1 introduces, and it is the dependency, not the claim. If it were ever refuted, P1 (§8)
is the correct falsifier and the hybrid falls with it.

**Bottom line:** the HYBRID recommendation and its decisive camera-inheritance finding are
independently reproducible from source and honestly labeled. No plausible-but-unverified step is
mislabeled PROVEN, and no playtest is staked on an untraced mechanism ahead of the offline M0 gate.
