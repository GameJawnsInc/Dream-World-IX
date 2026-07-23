# A3 — THE MANAGED → NATIVE BOUNDARY (C# side)

How a summon cinematic reaches `FF9SpecialEffectPlugin.dll`, what crosses the P/Invoke line in
each direction, where the "summon" path is distinguished from an ordinary spell, and — the load-
bearing question — **whether the summoned creature's geometry is ever visible to managed code.**

All cites are `Assembly-CSharp` relative to `C:/gd/FFIX/Memoria/Assembly-CSharp/`.

---

## 0. Headline answers

1. **The creature's 3D geometry / per-frame transform NEVER crosses the boundary.** Managed code
   only ever receives **already-projected 2D PSX-GPU primitives** (screen-space `Int16 x0,y0` +
   a coarse ordering-table depth `otz`) out of `SFX_GetPrim`. The creature is drawn entirely
   inside the DLL against the DLL's own internal camera; only its 2D footprint escapes. There is
   no managed-visible world-space vertex, bone, or model matrix for the creature. (`SFXRender.cs:77-86`)

2. **The per-frame CAMERA is fully managed-visible, every frame.** `SFX_UpdateCamera` **returns a
   pointer to 13 floats** = a 3×4 world→camera VIEW matrix (PSX fp12) + a per-frame near-Z. Managed
   code copies it out and stamps it onto the Unity `Camera` as `worldToCameraMatrix` +
   `projectionMatrix` (`SFX.cs:1595-1604`). This **refutes the prior round's "per-frame camera eye
   is a static-recovery NO-GO" only for the RUNTIME/managed path**: the DLL's camera anchor is
   zero-on-disk (unrecoverable statically), but at runtime the boundary hands the whole VIEW+near-Z
   over cleanly — which is exactly what the s50 `VIEW`/`PROJ` probe rows capture.

3. So for authoring: the **camera is recoverable** (VIEW matrix + the near-Z that drives the zoom);
   the **creature transform is not** — the best you can get for the creature is its projected 2D
   primitive footprint + `otz`, which is lossy (pre-transformed, OTZ ≠ true Z).

---

## 1. The DllImport surface (13 externs) — `SFX.cs:714-753`

`private class DLLMethods` — the entire native contract. Signatures verbatim:

| # | Export | Signature | Direction / payload |
|---|--------|-----------|---------------------|
| 1 | `SFX_InitSystem` | `void(Callback method)` | OUT: registers the managed `BattleCallback` fn-ptr the DLL calls back through (`SFX.cs:832`). |
| 2 | `SFX_StartPlungeCamera` | `void(IntPtr btlseq, Int32 len, Int32 camOffset, Int32 projOffset)` | IN→DLL: pins `btlseq.instance.data` (the battle-intro camera sequence). `SFX.cs:1683-1692`. |
| 3 | `SFX_SkipCameraAnimation` | `void(Int32 skip)` | scalar in. |
| 4 | `SFX_InitBattle` | `void(IntPtr param)` | IN→DLL: pinned `SFX_INIT_PARAM` (party/monster positions, fixed-cam flags). `SFX.cs:1694+`. |
| 5 | `SFX_Update` | `Boolean(ref Int32 frameIndex)` | **the per-frame tick.** DLL advances its sim, writes `frameIndex` back, returns "still running". |
| 6 | `SFX_LateUpdate` | `void()` | end-of-frame native housekeeping (called just before `SFX_GetPrim` harvest). |
| 7 | `SFX_UpdateCamera` | `IntPtr(Int32 isDebug)` | **OUT←DLL: ptr → 13 floats = VIEW matrix + near-Z.** §4. |
| 8 | `SFX_MoveFreeCamera` | `void(Int32 type, Int32 x, Int32 y)` | debug free-cam nudge. |
| 9 | `SFX_SendFloatData` | `Int32(Int32 type, Int32 btl_id, Single a0,a1,a2)` | IN→DLL, typed. `type 1` = camera-target world pos. §5. |
| 10 | `SFX_SendIntData` | `Int32(Int32 type, Int32 a0,a1,a2)` | IN→DLL / query, typed 1..12. §5. Some are GETTERS (return value used). |
| 11 | `SFX_Play` | `void(Int32 effnum, IntPtr bin, Int32 size, IntPtr req)` | **loads the effect.** `bin` = `ef###.bytes`, `req` = pinned `SFX.request`. §3. |
| 12 | `SFX_BeginRender` | `Boolean()` | gate before the `SFX_GetPrim` harvest loop. `SFXRender.cs:54`. |
| 13 | `SFX_GetPrim` | `IntPtr(ref Int32 otz)` | **OUT←DLL: ptr → one PSX `P_TAG` primitive; `otz` = its OT depth.** §6. |

`Callback` (the fn-ptr passed to `SFX_InitSystem`) is `Int32(Int32 fullCode, Int32 a0,a1,a2,a3,
void* p)` — the DLL→managed reverse channel (VRAM TIM upload/store, sound play, controller vibra,
btl_seq bumps, background intensity, cursor). Handled in `BattleCallback` `SFX.cs:832-959` and
`BattleCallbackWithBtl` `SFX.cs:961+`. **Note callback code 1 "Get Position"/2 "Set Position"
(`SFX.cs:975-1007`) exchange a battler's `pos` as `Int16` — but that is the CASTER/TARGET battler's
position, not the summoned-creature model's.** The creature model has no `btl_id` and is never a
`BTL_DATA`; it is pure DLL-internal.

---

## 2. The full per-cast call sequence

```
Battle sequencer decodes a btlseq "Set Spell Animation" (wSeqCode 8/26)
   BattleActionThread.cs:300-314
      sfxNum = the SpecialEffect id (e.g. Bahamut__Full)
      if SFXData.FixedCameraEffects.Contains(sfxNum)   <-- SUMMON/big-effect gate (§7)
          -> LoadMonsterSFX ... UseCamera=true          (DLL drives the plunge camera)
      else
          -> LoadMonsterSFX ... (no UseCamera)
        |
        v
SFX.Play(SpecialEffect effNum)                          SFX.cs:1937-1987
   currentEffectID = effNum
   path = "SpecialEffects/ef{effNum:D3}"                <-- the ef###.bytes asset
   binAsset = AssetManager.LoadBytes(path)
   Marshal SFX.request  --> pinned requestRaw
   SFX_Play(effNum, pin(binAsset), len, pin(request))   <-- HAND THE EFFECT + REQUEST TO THE DLL
        |
        v
  --- per frame, until SFX_Update returns false ---
   [legacy]    SFX.UpdatePlugin()      SFX.cs:584-594 : SFX_Update(ref frameIndex)
   [SFXRework] SFXDataMesh.Render()    SFXDataMesh.cs:528-563,:582 : SFX_LateUpdate + SFX_Update
        |
        v
   SFXRender.Update()                  SFXRender.cs:51-121
      if SFX_BeginRender():
         loop: P_TAG* p = SFX_GetPrim(ref otz)          <-- HARVEST 2D PRIMITIVES (§6)
               if p==null break
               GzDepth = -otz
               SFXRender.Add(p)        SFXRender.cs:209  <-- s48 SfxMeshProbe.LogPrim hook :215
        |
        v
   SFX.UpdateCamera()                  SFX.cs:1590-1605
      src = SFX_UpdateCamera(isDebug)  --> 13 floats     <-- HARVEST THE CAMERA (§4)
      camera.worldToCameraMatrix = PsxMatrix2UnityMatrix(floats, camOffset)
      camera.projectionMatrix   = PsxProj2UnityProj(nearZ, 65535)
        |
        v
   SFXRender.Render() / SFXDataMesh.Render() draw walk   SFXRender.cs:123 / SFXDataMesh.cs:635
      (s47 SfxMeshProbe.LogFrame + LogCamera hooks       SFXDataMesh.cs:641-648)
```

The two drive modes: **legacy** ticks `SFX_Update` from `SFX.UpdatePlugin` (`SFX.cs:584-594`);
**SFXRework** (`Configuration.Battle.SFXRework`) drives it from inside `SFXDataMesh.Render`
(`SFXDataMesh.cs:528-563` init/exec, `:582` per-frame) — legacy `UpdatePlugin` explicitly skips
in that mode (`SFX.cs:591-592`). Either way, `SFXRender.Update()` (`:530`, `:619`) is what runs
the `SFX_GetPrim` harvest loop.

---

## 3. `SFX_Play` — the effect load (data IN) — `SFX.cs:1937-1987`

- `effnum` = `(Int32)SpecialEffect` enum value; also stashed in `SFX.currentEffectID` (`:1941`),
  which every downstream probe row stamps as `effectId`.
- `bin` = the raw bytes of `SpecialEffects/ef{effNum:D3}` (`:1974-1975`), pinned. This is the
  effect's compiled script/geometry container — **the creature model + its animation live in
  here, opaque to managed code**; managed only forwards the byte blob and its length. If the
  asset is missing, `SFX_Play` is still called with `(null,0)` (`:1984`).
- `req` = a pinned marshalled `SFX.request` struct (`:1968-1970`). Carries caster/target
  identity + flags the DLL needs to place the effect. (`SFX.request.exe.btl_id` etc.)
- The bit-twiddling on `playParam[effNum]` (`:1946-1959`) sets **render ordering / blend-order**
  knobs (`subOrder`, `addOrder`, `colIntensity`, `colThreshold`) — a per-effect table, not a
  per-frame transform. These bias the mesh push order in `SFXRender.PushCommandBuffer` (`SFXRender.cs:476-492`).

Nothing here reads back any geometry; `SFX_Play` is `void`.

---

## 4. `SFX_UpdateCamera` — THE recoverable per-frame camera (data OUT) — `SFX.cs:1590-1605`

```csharp
IntPtr source = SFX.SFX_UpdateCamera(isDebug);
Single[] array = new Single[13];
Marshal.Copy(source, array, 0, 13);          // <-- 13 floats out of the DLL
...
SFX.fxNearZ = array[12];
camera.worldToCameraMatrix = PsxCamera.PsxMatrix2UnityMatrix(array, SFX.cameraOffset);
camera.projectionMatrix    = PsxCamera.PsxProj2UnityProj(SFX.fxNearZ, 65535f);
```

**13-float layout** (from `PsxCamera.PsxMatrix2UnityMatrix(Single[] pmat, Single zoffset)`,
`PsxCamera.cs:103-120`):

| index | meaning | Unity mapping |
|-------|---------|---------------|
| `pmat[0..8]` | 3×3 rotation, PSX fp12 (÷4096) | `m00..m22`, with Y-row/col sign flips (`m01,m10,m12,m20,m22` negated) for the RH→LH handedness swap |
| `pmat[9]` | translation X | `m03 = pmat[9]` |
| `pmat[10]` | translation Y | `m13 = -pmat[10]` |
| `pmat[11]` | translation Z | `m23 = -(pmat[11] + zoffset)` |
| `pmat[12]` | **near-Z (per-frame)** | `SFX.fxNearZ` → feeds PROJ |

The **PROJ matrix is rebuilt managed-side from near/far only** (`PsxProj2UnityProj`,
`PsxCamera.cs:172-178`): a **fixed off-center frustum** — half-width `FieldMap.HalfScreenWidth`,
vertical split `PsxScreenHeightNative/2.2` — through `PerspectiveOffCenter` (`:122-158`). Because
the frustum's near-plane extent is fixed while `near` (=`pmat[12]`) varies per frame, **the
per-frame near-Z IS the zoom/FOV control** — this reconciles the calibration note's "PROJ zooms
47°→24°": the DLL emits a shrinking near-Z, not a changed FOV field. `far` is pinned at `65535`
(`SFX.cs:1600`).

**Consequence for authoring:** the full per-frame MVP is `PROJ · VIEW`, both managed-visible and
both captured by the s50 probe (`VIEW`/`PROJ` rows, `SfxMeshProbe.cs:229-238`). You can place a
replacement model at any target screen NDC by inverting this MVP. What you cannot get from the
boundary is where the DLL PUT the native creature — see §6.

Gated by `SFX.isSystemRun && !isTutorial && !isDebugCam` (`SFX.cs:1592`). The camera write targets
`Camera.main` or the "Battle Camera" GameObject's camera (`SFX.cs:1598`).

---

## 5. `SFX_SendFloatData` / `SFX_SendIntData` — typed IN/query — `SFX.cs:1989-2091`

The `type` argument is a command selector; args 0..2 are payload. Callers set
`SFXDataCamera.currentCameraEngine = SFX_PLUGIN` when the command steers the camera. Decoded set:

| call | export | meaning |
|------|--------|---------|
| `SetCameraTarget` | Float `type=1` (+ Int `1`/`2`) | target **world pos** (x,y,z) + caster btl_id (Int 1) + target btl_id (Int 2). `SFX.cs:1989-1995` |
| `SetCamera` | Int `type=3` (cam, arg) | select a predefined battle camera; `arg` = per-boss distance/fov tweak. `:1997-2027` |
| `SetEnemyCamera` | Int `type=4` (btl_id, arg) | enemy-framed camera. `:2029-2051` |
| `GetEffectOvRun` | Int `type=5` (query) | effect over-run flag. `:2053` |
| `GetEffCamTrigger` / `SetEffCamTrigger` | Int `type=6` / `7` | effect camera trigger get/set. `:2058-2065` |
| `GetTaskMonsteraStartOK` / `SetTaskMonsteraStart` | Int `type=8` / `9` | creature-task ("Monstera") start handshake. `:2068-2076` |
| `GetCameraPhase` / `SetCameraPhase` | Int `type=10` / `11` (phase) | camera-phase state machine (drives battle phase transition, `SFX.cs:1606-1626`). `:2078-2086` |
| `GetEffectJTexUsed` | Int `type=12` (query) | jitter-texture-used flag. `:2088-2091` |

Float `type=1`'s (x,y,z) is a **battler-derived world position** (caster/target), not the
creature's — it tells the DLL where to aim, not where the creature ends up.

---

## 6. `SFX_GetPrim` — the primitive harvest (the ONLY geometry OUT) — `SFXRender.cs:77-86`

```csharp
for (;;) {
    Int32 num = 0;
    P_TAG* ptr = (P_TAG*)SFX.SFX_GetPrim(ref num);   // one PSX GPU primitive per call
    if (ptr == null) break;
    SFXMesh.GzDepth = -num;                            // num = OT depth (otz)
    SFXRender.Add(ptr);                                // dispatch by tag->code
    primCount++;
}
```

Each returned `P_TAG*` is a **PlayStation GPU primitive packet** (`PSX_LIBGPU.cs`): an 8-byte
header (OT-link word + `r0/g0/b0/code`) then, at fixed byte offset 8, the first vertex `x0,y0`
as **`Int16` SCREEN coordinates** — already run through the DLL's internal geometry+projection.
`SFXRender.Add` (`SFXRender.cs:209-322`) switches on `tag->code & 252` into POLY_F3/FT3/F4/FT4/
G3/GT3/G4/GT4, LINE_F2/G2, TILE/SPRT (+ DR_* state tags), building Unity meshes whose vertices ARE
those screen coords with `GzDepth` (the negated OTZ) as Z.

**Why this is lossy for creature-tracking (confirming prior-round FALSIFIED verdicts):**
- The vertices are **post-projection 2D**; the 3D model-space position is gone.
- `otz` is a coarse **ordering-table depth** (a sort bucket), not a metric Z — you cannot invert
  it to a world Z with any fidelity.
- Primitives are **undifferentiated** — the creature's polys arrive in the same stream as the
  swirl/flare/fire-column effect polys. They are only separable by **mesh KEY** (`SFXMeshBase._key`,
  the `SFXKey`-computed ABR/texture/tpage hash), which is what `HideMeshes` / the probe MESH rows
  key on — and even then a key groups by blend/texture state, not by "this is the creature".
- The commented-out `SFXRender.SaveSFXDataMeshes` experiments (`SFXRender.cs:150-183`) are the
  engine authors' own abandoned attempt to reconstruct caster/target-relative world positions from
  these vertices — direct evidence the world transform is not cleanly present here.

So: **the managed side can see the creature's projected silhouette per frame, never its transform.**

---

## 7. Where "summon" is distinguished from a normal spell

There is no single "isSummon" branch; the distinction is spread across three orthogonal axes, none
of which exposes the creature model to managed code:

1. **`SFXData.FixedCameraEffects`** (`SFXData.cs:1339-1371`) — the HashSet of `SpecialEffect`s that
   take a **DLL-driven fixed/plunge camera**. Contains every full summon (`Shiva__Full`,
   `Ifrit__Full`, ... `Bahamut__Full`, `Ark__Full`, `Madeen__Full`) plus a few big spells
   (Meteor, Doomsday, Holy, Grand_Cross). The gate is `BattleActionThread.cs:310`: members get
   `LoadMonsterSFX ... UseCamera=true`, i.e. the DLL's `SFX_UpdateCamera` output (§4) is allowed
   to steer the Unity camera for the whole cast. **This is the flag that makes a summon a
   cinematic** — it is per-effect data, not a code path that touches geometry.

2. **`btl_cmd.DecideSummonType`** (`btl_cmd.cs:1583-1615`, called from `:1028`) — despite the name,
   this ONLY chooses **short vs full** variant by an MP check (`cmd.info.short_summon = 1` when
   `cur.mp <= aa.MP*2`, probabilistically). It selects WHICH `ef###` (short/full) plays; it does
   not load or expose any model. The full/short choice ultimately maps to distinct
   `SpecialEffect` ids (e.g. `Bahamut__Full` vs `Bahamut__Short`, some short variants commented
   out of `FixedCameraEffects`). Also gated on the summon-seen achievement flags (`summon_bahamut`
   etc.) which suppress the short-cut so a first-time summon always plays full.

3. **The creature model itself** is loaded **inside the DLL** from the `ef###.bytes` blob handed to
   `SFX_Play` (§3). It is **not** a Unity `GameObject`, **not** a `BTL_DATA`, and **not** an
   `SFXChannel`. (`SFXChannel`, `SFXChannel.cs` / `UnifiedBattleSequencer.cs:445`, is the SFXRework
   **net-new** channel-model system for reworked/added effects — a separate, managed-side mesh path
   — but the stock native summons still route through `SFX_Play`→`SFX_GetPrim`, not through it.)

**Net:** the "summon" identity lives in (a) the `SpecialEffect` id, (b) its membership in
`FixedCameraEffects` (→ `UseCamera`), and (c) the bytes inside `ef###`. None of (a)/(b)/(c) makes
the creature's geometry or transform visible to managed code.

---

## 8. What `SfxMeshProbe.cs` actually hooks + logs — `Memoria/Battle/SFX/SfxMeshProbe.cs`

Default-OFF (`[SfxProbe] Enabled`), permanent debug instrumentation. Four hooks, five row types:

| row | hook site | coordinate space |
|-----|-----------|------------------|
| `MESH,effectId,frame,index,keyHex,vtx,tri,cx,cy,cz,ex,ey,ez` | `SFXDataMesh.cs:643` `LogFrame(commandBuffer)` — the post-batch draw walk | mesh `bounds` center/extents. Drawn via `Graphics.DrawMeshNow(_mesh, Matrix4x4.identity)` so object==world — **but the vertices are the baked SCREEN-space primitive coords** (§6), so "world" here is effectively screen space + OTZ-Z. `SfxMeshProbe.cs:156-188` |
| `CAM,frame,px..rz` | `SFXDataMesh.cs:648` `LogCamera(camera)` | resolved Unity camera `transform` position + eulerAngles — **INERT during SFX playback** (the DLL overrides the matrices directly, transform stays at Awake pose). `SfxMeshProbe.cs:208-221` |
| `VIEW,frame,m00..m33` | same `LogCamera`, s50 | `camera.worldToCameraMatrix` = the DLL's real per-frame VIEW (§4). `SfxMeshProbe.cs:229-233` |
| `PROJ,frame,m00..m33` | same `LogCamera`, s50 | `camera.projectionMatrix` = the near-Z-driven off-center frustum (§4). `SfxMeshProbe.cs:234-238` |
| `PRIM/STATE,effectId,frame,index,code,label,otz,x,y` and `PRIMSUM,...` | `SFXRender.cs:215` `LogPrim(tag, primCount)` — top of `Add()`, one call per raw `SFX_GetPrim` result | vertex0 = raw `x0,y0 + drOffsetX/Y` (post-drOffset **screen space**); `otz` = `SFXMesh.GzDepth`. `SfxMeshProbe.cs:300-353` |

Key correctness notes baked into the source: the CAM/VIEW/PROJ hook was **moved from
`SFXDataCamera.UpdateCamera` to `SFXDataMesh.Render`** (s48) because (1) `Camera.main` is routinely
null during native SFX so the old hook logged 0 CAM rows, and (2) it wasn't gated on the native
frame actually advancing (`SfxMeshProbe.cs:190-207`). All rows share `SFX.frameIndex` as the
correlation column. The probe reads **decoded OUTPUT**, never shippable asset bytes.

**Therefore the probe's own design already encodes the boundary truth:** it can hand you the
per-frame camera (VIEW/PROJ) exactly, and the creature only as 2D primitive/mesh footprints keyed
by `_key` — which is why the study needs a *DLL-side* per-frame transform recovery (round A1/A2's
`Hi_Summon*` slice), not a managed hook, to place a replacement creature correctly.

---

## 9. Cite index (fast lookup)

- DllImport block: `Global/SFX/SFX.cs:714-753`; wrappers `:755-830`; callback `:832-1588`.
- `Play` / ef### load: `Global/SFX/SFX.cs:1937-1987`.
- Per-frame tick: legacy `Global/SFX/SFX.cs:584-594`; SFXRework `Memoria/Battle/SFX/SFXDataMesh.cs:528-563,:582`.
- `SFX_GetPrim` harvest + `Add` dispatch: `Global/SFXRender/SFXRender.cs:77-86,:209-322`.
- `UpdateCamera` + 13-float copy: `Global/SFX/SFX.cs:1590-1605`.
- Camera matrix builders: `Global/PSX/PsxCamera.cs:103-120` (VIEW), `:122-158` (`PerspectiveOffCenter`), `:172-178` (PROJ).
- SendData type codes: `Global/SFX/SFX.cs:1989-2091`.
- Summon gates: `Memoria/Battle/SFX/SFXData.cs:1339-1371` (`FixedCameraEffects`);
  `Memoria/Battle/SFX/BattleActionThread.cs:300-314` (`UseCamera`); `Global/btl_cmd.cs:1583-1615` (`DecideSummonType`).
- Probe: `Memoria/Battle/SFX/SfxMeshProbe.cs` (hooks `SFXDataMesh.cs:641-648`, `SFXRender.cs:215-216`).
