# A3 managed-boundary — ADVERSARIAL RE-VERIFICATION

Independently re-derived from `Assembly-CSharp` source (not from A3's evidence). Verdict: **CONFIRMED.**
Every load-bearing citation in `A3-managed-boundary.md` reproduces exactly against the current source.

## What I reproduced fresh (file:line = my own read, not A3's)

| A3 claim | My independent check | Result |
|---|---|---|
| 13 DllImport externs, exact signatures | `SFX.cs:714-753` — all 13 present, signatures byte-match A3's table incl. `SFX_UpdateCamera(Int32)->IntPtr`, `SFX_GetPrim(ref Int32)->IntPtr`, `SFX_Play(Int32,IntPtr,Int32,IntPtr)` | ✓ |
| Camera crosses as ptr→13 floats, copied out | `SFX.cs:1595-1604`: `SFX_UpdateCamera(isDebug)` → `Marshal.Copy(source, array, 0, 13)`; `array[12]`→`fxNearZ`; `worldToCameraMatrix = PsxMatrix2UnityMatrix(array,...)`; `projectionMatrix = PsxProj2UnityProj(fxNearZ, 65535f)` | ✓ |
| 13-float = 3×3 rot (÷4096) + 3 trans + near-Z, with Y sign-flips | `PsxCamera.cs:103-120`: m01/m10/m12/m20/m22 use `/-4096f`; `m03=pmat[9]`, `m13=-pmat[10]`, `m23=-(pmat[11]+zoffset)`. Exactly A3's index table. `far` pinned 65535 at `SFX.cs:1600-1602` | ✓ |
| PROJ rebuilt managed-side from near/far via fixed off-center frustum | `PsxCamera.cs:172-178` `PsxProj2UnityProj`: fixed `HalfScreenWidth` + `PsxScreenHeightNative/2.2` split → `PerspectiveOffCenter(...,zNear,zFar)` at `:122-149`. Frustum extents fixed, only near varies. | ✓ |
| SFX_GetPrim harvest: one P_TAG/call, `GzDepth=-otz`, `Add(ptr)` | `SFXRender.cs:77-86` verbatim (`num`=otz, `GzDepth=-num`) | ✓ |
| Primitives are post-projection 2D `Int16` screen coords | `PSX_LIBGPU.cs:148` P_TAG = OT-link `addr_len`(4B)+r0/g0/b0/`code`@offset7; POLY_* structs `[FieldOffset(8)] Int16 x0`, `[FieldOffset(10)] Int16 y0`. **Vertices are Int16 SCREEN coords — no world-space vertex escapes.** | ✓ |
| `Add` dispatches on `tag->code & 252` into POLY_F3/FT3/… | `SFXRender.cs:217` `switch (tag->code & 252)` cases 32/36/40/44/48/52/56/60… | ✓ |
| Commented-out caster/target-relative reconstruction = authors' abandoned attempt | `SFXRender.cs:150-183` `SaveSFXDataMeshes` dead block: `SwitchToWorldCoordinates`, `isAtCaster/isAtTarget/isAtMonBone0…`, "find where pieces are placed wrt. caster and target" — confirms world transform is NOT cleanly present | ✓ |
| FixedCameraEffects = the summon/big-effect gate | `SFXData.cs:1339-1371`: all `*__Full` summons + Meteor/Doomsday/Holy/Grand_Cross/Night; short variants mostly commented | ✓ |
| UseCamera gate | `BattleActionThread.cs:310-313`: `if FixedCameraEffects.Contains(sfxNum)` → `LoadMonsterSFX ... "UseCamera", true` else without | ✓ |
| SFX_Play loads `ef{effNum:D3}` bytes, pins request, null-safe | `SFX.cs:1937-1987`: `path=$"SpecialEffects/ef{...:D3}"`, `AssetManager.LoadBytes`, pinned `request`, else `SFX_Play(effNum, null, 0, req)` | ✓ |
| Probe emits VIEW/PROJ rows from the Unity camera matrices; CAM row inert | `SfxMeshProbe.cs:208-238`: `LogCamera` logs transform pos+eulerAngles (inert), plus `VIEW`=`cam.worldToCameraMatrix`, `PROJ`=`cam.projectionMatrix`; `:194` note "Camera.main routinely null during native SFX" | ✓ |

## Refutation attempts (all failed → claim stands)

- **Error-stub-vs-real-body confusion**: N/A — A3 is a C#-source analysis, no DLL disasm, so the
  MSVC funclet trap cannot apply.
- **Mislabeled scratch buffer**: A3 does NOT claim any scratch-buffer value; it explicitly says the
  DLL camera anchor is zero-on-disk / unrecoverable statically and that recovery is *runtime/managed*
  via the boundary hand-off. That distinction is correct and is the whole point.
- **Is the 13-float really a VIEW matrix?** Managed assigns it to `worldToCameraMatrix` — it IS
  world→camera by construction (9 rot + 3 trans + 1 near = 13). Confirmed, not assumed.
- **Does creature geometry sneak across elsewhere?** Checked the only geometry-bearing exports:
  `SFX_GetPrim` (2D screen prims only) and the callback code 1/2 pos exchange (`SFX.cs` BattleCallback)
  which is the **caster/target BTL_DATA** pos, not the creature. `SetCameraTarget(Vector3, BTL_DATA exe,
  BTL_DATA trg)` at `SFX.cs:1989` confirms the world pos handed in is battler-derived (a target to AIM
  at), not the creature's own transform. No creature handle crosses.

## One nuance worth flagging (does NOT change the verdict)

A3 §4 asserts the per-frame near-Z "IS the zoom/FOV control" and reconciles a "47°→24°" calibration
note. The MECHANISM is sound (frustum L/R/B/T are fixed constants, only `zNear` varies per frame, so
FOV = 2·atan(halfExtent/near) is driven purely by near). The exact numeric direction/degrees is an
interpretive read of the s50 probe rows, not re-derived here — but it is a *secondary* interpretation
and is orthogonal to the boundary-crossing facts, which are the load-bearing content and are all
confirmed.

## Bottom line
A3's three headlines hold: (1) the creature's 3D transform never crosses — only post-projection 2D
`Int16` PSX primitives + coarse `otz`; (2) the per-frame camera (VIEW 3×4 + near-Z) DOES cross cleanly
and is fully managed-visible at runtime; (3) camera recoverable, creature transform not — hence the
study's need for a DLL-side `Hi_Summon*` per-frame transform recovery. No refutation found.
