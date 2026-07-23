# V-C1 — Adversarial verify: "Managed camera is stamped from the native camera each summon frame"

**Claim id:** C1 · **Source:** T4-sync-and-camera.md §1.1 · **Cited evidence:** SFX.cs:1590-1605
**Verdict: CONFIRMED** (re-derived from Memoria C# source, not trusting the cite).

## What I reproduced (all first-hand)

1. **The cited lines do exactly what's claimed.** `SFX.UpdateCamera()` (`Global/SFX/SFX.cs:1590-1605`)
   under guard `SFX.isSystemRun && !FF9StateSystem.Battle.isTutorial && !SFX.isDebugCam`:
   - `IntPtr source = SFX.SFX_UpdateCamera(isDebug)` → `Marshal.Copy(source, array, 0, 13)` (13 floats)
   - `SFX.fxNearZ = array[12]`
   - `camera.worldToCameraMatrix = PsxCamera.PsxMatrix2UnityMatrix(array, SFX.cameraOffset)` (VIEW)
   - `camera.projectionMatrix = PsxCamera.PsxProj2UnityProj(SFX.fxNearZ, SFX.fxFarZ)` (PROJ)
   - `camera` = `Camera.main` else the "Battle Camera" GameObject's Camera (SFX.cs:1598).

2. **The source IS the native DLL camera.** `SFX_UpdateCamera` (SFX.cs:791-796) is a thin wrapper over
   `DLLMethods.SFX_UpdateCamera` — a real P/Invoke `[DllImport("FF9SpecialEffectPlugin")]` returning
   `IntPtr` (SFX.cs:734-735; native body RVA 0x211df0 per prior rounds). Not a managed re-derivation:
   the 13 floats are copied straight out of the DLL's installed per-frame camera.

3. **It is actually driven every battle-loop tick (the "each frame" part).** Caller chain, re-traced:
   - `battle.BattleMain()` calls `SFXDataCamera.UpdateCamera()` **unconditionally** at `Global/battle/battle.cs:86`.
   - `SFXDataCamera.UpdateCamera()` (SFXDataCamera.cs:540-546): if `currentCameraEngine == SFX_PLUGIN`
     → `SFX.UpdateCamera()`.
   - `currentCameraEngine` is set to `SFX_PLUGIN` at battle start (`StartBattle` SFX.cs:1639) **and** in
     the SFXRework summon-mesh path `SFXDataMesh.Runtime.Begin()` (SFXDataMesh.cs:607). Cleared to NONE
     only on teardown (SFXData.cs:304, SFXDataMesh.cs:520).
   - Corroborated by the in-repo comment at SFXDataCamera.cs:553-556: BattleMain() "calls UpdateCamera()
     UNCONDITIONALLY every Unity Update() tick."

## Nuance (refinement, NOT a refutation)

The stamping is per **Unity Update tick**, not gated on the native SFX frame advancing (`SFX.isUpdated`).
That is a *superset* of "each summon frame": the managed camera is re-stamped from the DLL's currently
installed camera every tick, so it is never *stale* relative to the native camera. The DLL camera itself
advances on native ticks; the only runtime residual (T4 §1.4) is a possible ≤1-step phase **lead** (fresher,
not staler). This strengthens the claim's spirit rather than weakening it.

## Guard caveats (when stamping is skipped — none apply to a normal cast)

`SFX.UpdateCamera()` no-ops if: `isDebugCam` (free/debug cam), `isTutorial`, `!isSystemRun`, or
`currentCameraEngine != SFX_PLUGIN`. For a real summon cast all four hold the productive way, so the path
is live. A transplanted managed model rendered during the cast therefore inherits VIEW+PROJ for free — the
core enabler C1 asserts.

**No refutation found.** The one thing I did NOT independently re-verify (out of scope for C1, and it is a
separate downstream claim) is that `PsxProj2UnityProj`'s off-center frustum reproduces the native GTE
principal point *exactly* (T4 §1.2). C1 as stated — that the managed camera is *stamped from* the native
camera each frame — is proven at the source level regardless of that reconstruction's fidelity.
