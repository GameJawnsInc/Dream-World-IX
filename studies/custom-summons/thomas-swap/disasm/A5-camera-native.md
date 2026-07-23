# A5 — The Native Camera Path (SUMMON case), re-examined

Slice A5 of the FF9SpecialEffectPlugin disasm round. All RVAs are image-base-relative
(image base `0x180000000`; VA = RVA + base). DLL = `FF9SpecialEffectPlugin` (x64, MSVC2013).
C# citations are `Assembly-CSharp/…:line`. Everything here is decoded from code; runtime
VALUES in the `.data` bss tail are zero-on-disk and marked RUNTIME-ONLY.

---

## TL;DR — the reframe is answered, the camera is SOLVED as a live snapshot

* **`SFX_UpdateCamera` returns the complete camera as a 13-float array.** Its whole job is:
  copy the animator's "next camera" into the installed camera (conditionally), then convert
  that installed camera from PSX int16 form to 13 floats and **return a pointer to them**.
* **VIEW and PROJ are 100% live-recoverable in managed code, with NO anchor buffer and NO
  eye position.** C# already does exactly this every frame: `SFX.cs:1595` calls the DLL,
  `Marshal.Copy`s the 13 floats, and builds `camera.worldToCameraMatrix` (from floats 0–11)
  and `camera.projectionMatrix` (from float 12). A probe can read `Camera.main.worldToCameraMatrix`
  / `.projectionMatrix`, or call `SFX_UpdateCamera` and copy the 13 floats — either way, live.
* **The prior "camera eye = static-recovery NO-GO" still holds, and is now IRRELEVANT.** The
  eye/anchor lives in the runtime scratch buffer `@0x220060` (zero on disk). But we never need
  the eye: VIEW+PROJ fully define the camera and both are live. See §4.
* **K = 4096.8 branch-A CONFIRMED.** `resolve_position` (`0x145a0`) = `anchor + 4096.8·(cos/sin θ)`
  with real `MSVCR120!cos`/`sin`, `π`, `2.0`, `±4096.8` constants. See §5.
* **Shortest path to (creature transform + VIEW + PROJ) per frame:** all three are live-only
  reads, none require static byte recovery. See §6.

---

## 1. The export thunk → real body

* `SFX_UpdateCamera` export @ **`0x1dd0`** is a thunk: `jmp 0x180001e80`.
* Real body @ **`0x1e80..0x2030`** (432 bytes). Signature (C#, `SFX.cs:734`):
  `extern IntPtr SFX_UpdateCamera(Int32 isDebug)` — `isDebug` arrives in `ecx`→`ebx`.
* Body returns `rax = lea [rip+0x20fdd9] → RVA 0x211df0` (the base of the 13-float array).

---

## 2. The installed-camera struct (PSX int16 form) — RVA `0x69730`

Read/written by the body as an int16 GTE camera. Layout (34 bytes):

| offset (RVA) | type | field | meaning |
|---|---|---|---|
| `0x69730`+0x00…0x10 | 9 × int16 | `R[0..8]` | 3×3 rotation, GTE fixed-point /4096 |
| `0x69744` | int32 | `TRX` | translation X (GTE) |
| `0x69748` | int32 | `TRY` | translation Y |
| `0x6974c` | int32 | `TRZ` | translation Z |
| `0x69750` | int16 | `H` | projection distance (drives FOV/zoom) |

* Written wholesale (keyframe install) at `0x1ed2`–`0x1ef3`; read back + converted at `0x1f1c`–`0x2022`.
* RVA `0x69730` is in `.data` **beyond raw size ⇒ zero-on-disk, RUNTIME-ONLY values**. The
  layout + update logic are fully static-recoverable; the numbers are not (they come from the
  loaded btlseq camera track).
* Defaults installed by the reset paths: `TRX = 0xffffffcf (−49)`, `TRY = 0x1d9 (473)`,
  `TRZ = 0x16d6 (5846)` — written by fn `0x2300` (`0x2558`/`0x2562`/`0x256c`) and mirrored
  into the keyframe source.

## 3. The 13-float output array — RVA `0x211df0` (the return value)

`array[i]` (Single), `i = 0..12`, contiguous at `0x211df0` stride 4:

| i | source | C# use (`PsxCamera.cs`) |
|---|---|---|
| 0..8 | `R[0..8]` (int16→float) | `m00..m22`, scaled `±1/4096` (`PsxMatrix2UnityMatrix`, `PsxCamera.cs:106-115`) |
| 9 | `TRX` (`ecx`←`0x69744`) | `m03 = pmat[9]` (`:116`) |
| 10 | `TRY` (`edx`←`0x69748`) | `m13 = -pmat[10]` (`:117`) |
| 11 | `TRZ` (`r8d`←`0x6974c`) | `m23 = -(pmat[11] + zoffset)` (`:118`) |
| 12 | `H` (`r9w`←`0x69750`) | `SFX.fxNearZ = array[12]` → projection near-plane (`SFX.cs:1600`) |

**This is the entire VIEW+PROJ input.** `SFX.cs:1603-1604`:
```
camera.worldToCameraMatrix = PsxCamera.PsxMatrix2UnityMatrix(array, SFX.cameraOffset);
camera.projectionMatrix    = PsxCamera.PsxProj2UnityProj(SFX.fxNearZ, SFX.fxFarZ);   // fxFarZ=65535
```
`PsxProj2UnityProj` (`PsxCamera.cs:172-179`) → `PerspectiveOffCenter` with fixed screen dims and
`near = array[12] = H`. **So per-frame ZOOM = float[12] (H)** — matches the prior study's "PROJ
zooms 47°→24°": those are two different H values, nothing to do with an eye position.

## 4. The gate logic (which camera gets installed)

```
w[0x323170] == -1 ?  ── yes ─▶ if (isDebug != 0) install keyframe else just read back
      │ no
kf_flag[0x211e24] == 1 ? ── yes ─▶ install keyframe src (0x211e28) into curCam (0x69730)
      │ no
      └────────────────────────▶ just read back current curCam
        (always) convert curCam int16 → 13 floats @0x211df0, return &floats
```
* keyframe source struct @ **`0x211e28`** (same 9×i16 + 3×i32 + i16 layout), produced by the
  **camera-animation stepper fn `0x2030`** (immediately after the body). That stepper does the
  per-frame interpolation: e.g. `add dword[0x211e50], edx` / `add dword[0x211e58], ebx`
  (`0x2087`/`0x207c`) accumulate the translation track. Reset/seed by fn `0x2300`.
* `kf_flag @0x211e24`, `gate word @0x323170`, keyframe src `@0x211e28` — **all `.data` bss ⇒
  zero-on-disk, RUNTIME-ONLY**.

## 5. resolve_position / lookup_anchor — K=4096.8 branch-A CONFIRMED

### lookup_anchor `@0x148f0..0x149c4` (212 B)
`lookup_anchor(type=ecx, out1=rdx, out2=r8, out3=r9)` maps an anchor index (`type & 0x1f`) to a
3-short position:
* `type == 0` → zeros.
* `type ∈ [0x15..0x1f]` (i.e. >0x14) → index the table @ **RVA `0x220060` (stride 8)**
  (`0x14932 lea rdx,[rip+0x20b727] → 0x220060`); copies 3 shorts (@+0,+2,+4); if index<4 also a
  second 3-short block @+0x30. **This is exactly the prior-round anchor scratch buffer `@0x220060`.**
* `type == 0xb (11)` → the pair @ RVA `0x6971c` / `0x6971e` (adjacent to curCam; the target/player position).
* `@0x220060` is `.data` bss ⇒ **zero-on-disk, RUNTIME-ONLY** (per-actor battle anchor positions,
  filled live by the battle/SFX setup, not by this DLL statically).

### resolve_position `@0x145a0..0x148f0` (848 B)
Calls `lookup_anchor` twice (`0x145db`, `0x14604`) to fetch two anchor points, then does polar
placement. Double constants used:

| RVA | value | role |
|---|---|---|
| `0x4b698` | `2.0` | angle scaling |
| `0x4b6a0` | `3.141592653589793` (π) | angle → radians |
| `0x4b6c8` | **`4096.8`** | branch-A radius K (+) |
| `0x4b6e8` | **`−4096.8`** | branch-A radius K (−) |

Trig calls resolve to **`MSVCR120.dll!cos` (`0x49cd2`)** and **`MSVCR120.dll!sin` (`0x49ce4`)**
(verified via IAT). Shape: integer direction (`imul …, r15d`) → `cos`/`sin` → `mulsd ±4096.8` →
offset from the looked-up anchor. **Verdict: the prior K=4096.8 branch-A formula
`pos = anchor + 4096.8·(cos/sin θ)` is CONFIRMED**, cos/sin are the real CRT trig, not a custom
GTE table. (`resolve_position` at `0x147f4` also `cmovbe`s in `curCam @0x69700`-region data, so it
can seat the result relative to the current camera basis — still all runtime data.)

## 6. Creature world transform — `Hi_GetSummonBoneMatrix` (real body `@0x18630`)

The self-test's `locate` returns the **error funclet `@0x16c80`** (29 B, `lea rdx,→"…memory not
enough!"; call panic; int3`). The **real getter is `@0x18630..0x18692`** (its fail path jumps to
that funclet's string, `0x18678`):
```
idx=ecx; rec = summonModels[idx]           ; base 0x220830, stride 0x58 (imul rax,0x58)
if rec[+0x50]==0 (inactive) → error
data = rec[+0x00]                          ; model DATA block ptr
mtxArr = data[+0x38]                        ; bone-matrix array
out(32B) = mtxArr[bone << 5]               ; copy 0x20 bytes: a PSX MATRIX (3x3 i16 + 3 i32 trans)
```
* Output = a **32-byte PSX MATRIX per bone** (3×3 int16/4096 rotation + 3×int32 translation) — the
  same GTE convention as the camera. `summonModels @0x220830` and the model DATA block are
  **RUNTIME-ONLY** (zero-on-disk; populated when the model loads + each animated frame).
* **Static-recoverable:** the ACCESS PATH (index×0x58, `+0x50` active flag, `+0x00` data ptr,
  `+0x38` matrix array, bone stride 0x20, 32-byte layout). **Runtime-only:** the matrix VALUES.

### The two creature representations (for tracking Thomas)
1. **Native SFXMesh summon** — drawn as PSX primitives; `SFX_GetPrim(ref otz)` returns primitives
   whose `x0`/`y0` are already **SCREEN-space** + `otz` depth (`SFXMesh.cs:340,892` — GTE done
   inside the DLL). This is what the s50 probe logs. The bone transform behind them =
   `Hi_GetSummonBoneMatrix` (runtime).
2. **rung-7 Unity model creature (ModelFactory)** — a Unity `GameObject`; its
   `Transform.localToWorldMatrix` is world-space and projects via `Camera.main` matrices.

## 7. Shortest path to (creature world transform + VIEW + PROJ) per frame

All three are **live-only reads; none need static byte recovery:**

* **VIEW** = `Camera.main.worldToCameraMatrix` right after `SFX.UpdateCamera()`
  (equivalently: call `SFX_UpdateCamera(isDebug)`, `Marshal.Copy` 13 floats, apply
  `PsxMatrix2UnityMatrix`; or snapshot the 13 floats @ RVA `0x211df0`).
* **PROJ** = `Camera.main.projectionMatrix` (equivalently `PsxProj2UnityProj(array[12], 65535)`).
* **Creature world transform** = Unity `Transform.localToWorldMatrix` (rung-7 model) **or**
  `Hi_GetSummonBoneMatrix(idx, boneRoot, out)` → PSX matrix (native summon). For the *native*
  path you can also skip transforms entirely and read the already-projected `SFX_GetPrim`
  screen primitives.

**Projection identity:** `screen = PROJ · VIEW · (creature world pos)`. Because VIEW+PROJ are the
same values C# applies to the Unity camera, a Thomas puppet parented in Unity world space is
tracked for free by `Camera.main`; no PSX-world reconstruction, no anchor buffer, no eye needed.

## 8. Static-recoverable vs runtime-only — the ledger

| Item | RVA / source | Static? |
|---|---|---|
| `SFX_UpdateCamera` logic, 13-float layout, gate flow | `0x1e80..0x2030` | **STATIC** (fully) |
| curCam int16 struct layout | `0x69730` (+0x14/18/1c trans, +0x20 H) | **STATIC** layout / RUNTIME values |
| 13-float output values | `0x211df0` | **RUNTIME** (but live-readable = the return ptr) |
| keyframe src + stepper + flags | `0x211e28` / fn `0x2030` / `0x211e24` / `0x323170` | STATIC logic / RUNTIME values |
| anchor scratch buffer | `0x220060` (stride 8) | **RUNTIME-ONLY** (eye/actor anchors) |
| resolve_position formula K=4096.8, cos/sin | `0x145a0`, consts `0x4b6c8/6e8/6a0/698` | **STATIC** (confirmed) |
| summon bone matrix access path | `0x18630`, `summonModels 0x220830` stride 0x58, data+0x38, bone×0x20 | **STATIC** path / RUNTIME matrix values |
| `PsxMatrix2UnityMatrix` / `PsxProj2UnityProj` | `PsxCamera.cs:103-179` | managed, open source |

**Bottom line for authoring/tracking:** the camera is no longer any kind of blocker. VIEW+PROJ
are a trivial live snapshot (managed camera matrices or the 13-float return); pair them with the
creature's Unity world transform (or `Hi_GetSummonBoneMatrix` for the native path) and the
per-frame on-screen position of Thomas is fully determined without touching the runtime eye/anchor.
