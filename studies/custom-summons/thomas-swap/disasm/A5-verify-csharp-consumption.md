# Adversarial verification: `csharp-consumption`

VERDICT: **CONFIRMED** (independently re-derived from C# source; one citation-path typo noted, non-material).

## Claim under test
> Memoria C# reads the 13-float return each frame and builds `camera.worldToCameraMatrix`
> from floats 0-11 and `camera.projectionMatrix` using `float[12]` as the projection near/H;
> VIEW and PROJ are therefore fully live-recoverable in managed code without any eye position
> or anchor buffer.

## Re-derivation (fresh reads, not trusting prior evidence)

### 1. 13-float read each frame — CONFIRMED
`Global/SFX/SFX.cs:1590-1605` `SFX.UpdateCamera()` (runs each frame while `SFX.isSystemRun`):
```
1595  IntPtr source = SFX.SFX_UpdateCamera(isDebug);
1596  Single[] array = new Single[13];
1597  Marshal.Copy(source, array, 0, 13);
```
DllImport at `SFX.cs:735` `public static extern IntPtr SFX_UpdateCamera(Int32 isDebug)` — the export returns a
pointer; C# marshals exactly 13 `Single`s. ✓

### 2. worldToCameraMatrix from floats 0-11 — CONFIRMED
`SFX.cs:1603` `camera.worldToCameraMatrix = PsxCamera.PsxMatrix2UnityMatrix(array, SFX.cameraOffset);`
`Global/PSX/PsxCamera.cs:103-120` (note: file is at `Global/PSX/`, the claim cited bare `PsxCamera.cs`):
```
107-115  m00..m22  = pmat[0..8] / (+/-4096f)      ; 3x3 rotation, fixed-point /4096 (GTE 1.0 = 4096)
116      m03 =  pmat[9]                            ; translation X (eye offset)
117      m13 = -pmat[10]                           ; translation Y
118      m23 = -(pmat[11] + zoffset)               ; translation Z (+ cameraOffset)
```
Floats **0-11** wholly determine VIEW. Float 12 is NOT used here. The eye/translation is `pmat[9,10,11]` —
i.e. the camera position is *embedded in the returned floats*, so no separate eye vector is needed. ✓

`SFX.cameraOffset` is not an anchor buffer: declared `SFX.cs:2472 public static Single cameraOffset;`,
and the ONLY write to the static across the entire Assembly-CSharp tree is `SFX.cs:1945 SFX.cameraOffset = 0f;`
(all other `cameraOffset` grep hits are unrelated local variables in ETb/WalkMesh/UI/FieldCreator). It is a
constant `0f` scalar config, not runtime scratch. ✓

### 3. projectionMatrix from float[12] as near/H — CONFIRMED
`SFX.cs:1599-1604`:
```
1599  SFX.fxNearZ = array[12];
1600  SFX.fxFarZ  = 65535f;                        ; far is a constant, not from the floats
1604  camera.projectionMatrix = PsxCamera.PsxProj2UnityProj(SFX.fxNearZ, SFX.fxFarZ);
```
`PsxCamera.cs:172-178` `PsxProj2UnityProj(zNear, zFar)`: builds an off-center frustum where bottom/top come
from constants (`FieldMap.PsxScreenHeightNative`, `FieldMap.HalfScreenWidth`) and `zNear` = `array[12]` is the
PSX projection distance *h*. With fixed screen extents, larger h = narrower FOV = zoom. So `float[12]` is the
sole live driver of the projection/zoom — consistent with the prior round's "PROJ zooms 47->24 deg". ✓
(Note: `camera.nearClipPlane` is hardcoded to `0.1f` at `SFX.cs:1601` for clipping reasons; `fxNearZ` feeds the
projection *matrix* build, not the Unity near-clip plane. This does not affect the claim.)

### 4. "fully live-recoverable ... without any eye position or anchor buffer" — CONFIRMED
VIEW = f(array[0..11], const 0). PROJ = f(array[12], const 65535, const screen dims). Both matrices are total
functions of the 13 returned floats plus compile-time constants. No `Marshal.Copy` of any anchor/eye buffer,
no `SFX_GetPosition`-style side call, appears in `UpdateCamera`. ✓

## Corroborating independent call site (strengthens, not cited by prior agent)
`Memoria/Battle/SFX/SFXDataCamera.cs:570-585` (`CameraEngine.SFX_PLUGIN_SAVE` replay path) reconstructs the
camera with byte-identical logic:
```
577  Single[] array = SFXDataCamera.pluginSaveCamera.Dequeue();
579  SFX.fxNearZ = array[12];
583  camera.worldToCameraMatrix = PsxCamera.PsxMatrix2UnityMatrix(array, SFX.cameraOffset);
584  camera.projectionMatrix   = PsxCamera.PsxProj2UnityProj(SFX.fxNearZ, SFX.fxFarZ);
```
This path *enqueues and dequeues the 13-float arrays* to record/replay the camera. That a saved queue of these
arrays alone reproduces the camera is direct proof the 13 floats fully capture VIEW+PROJ with zero side state.

## Discrepancies found (none material to the verdict)
- Citation path typo: `PsxCamera.cs` is at `Global/PSX/PsxCamera.cs`, not repo root. Content matches.
- Cited line ranges `SFX.cs:1595-1604` and `PsxCamera.cs:103-118,172-179` are accurate.

## Scope caveat (honest boundary)
This claim is about the **C# consumption** side only, and it holds. It does NOT assert anything about how the
NATIVE DLL *computes* those 13 floats — the native side may well read the runtime camera-anchor scratch buffer
(RVA 0x220060, zero-on-disk) to produce them. The prior round's "per-frame camera is a NO-GO for static
recovery" concerns statically predicting the native output offline; it is not contradicted here, because this
claim is that *at runtime, in managed code*, the floats are already fully sufficient — which they are.
