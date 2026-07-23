# FINDINGS — How FF9 builds summon cutscenes at the native level (and how to author/track them)

Round report for the FF9SpecialEffectPlugin.dll summon-cutscene disasm round. Synthesizes the phase artifacts A1–A5 + B1–B5 and their adversarial verifications. **Verified-only** — every claim here survived the round's skeptic pass; PARTIAL/REFUTED items are stated in their corrected form. All RVAs image-base-relative (x64 `ImageBase 0x180000000`; VA = RVA + base). C# cites are relative to `C:/gd/FFIX/Memoria/Assembly-CSharp/`. Runtime `.bss`/scratch VALUES are zero-on-disk and flagged RUNTIME-ONLY; only LAYOUT + LOGIC are static-recoverable.

**The one-line result:** the summoned creature's true per-frame world transform is NOT static, NOT in any managed-visible stream — but it IS live-readable at `SummonData+0x40` via a passive memory read of the plugin's own runtime state, with no DLL patch and no asset-byte extraction. That closes the Thomas-swap staging problem the prior round declared unrecoverable.

---

## 1. HEADLINE — how a summon cutscene is built at the native level

A stock Eidolon cast is a **software PlayStation-GTE renderer** running entirely inside `FF9SpecialEffectPlugin.dll`. The managed side never sees the creature in 3D; it only forwards a byte blob and harvests already-flattened 2D primitives. The native pipeline, per frame:

1. **Load.** Managed `SFX.Play` hands the DLL the effect's compiled blob `SpecialEffects/ef{NNN}.bytes` via `SFX_Play(effnum, bin, size, req)` (`SFX.cs:1937-1987`). The creature **model + its animation clip live inside that blob**, opaque to managed code. A summon is distinguished from an ordinary spell purely by data: its `SpecialEffect` id's membership in `SFXData.FixedCameraEffects` (`SFXData.cs:1339-1371`) sets `UseCamera=true` (`BattleActionThread.cs:310`) so the DLL's camera drives the shot. No code path exposes geometry.

2. **Register.** `Hi_RegisterSummonModel` (@0x15ee0) parses the model into the **summon-model record array** `summonModels[]` (base RVA **0x220830**, stride **0x58**, LENGTH **1** — only slot 0 ever exists). It builds the runtime `SummonData` block: bone count, per-bone table, packed model-geom address, texanim array, and the initial motion pointer.

3. **Drive.** A single **mega-interpreter @0xeea4** (range `[0xeea4..0x12321]`) executes the `.seq`/SFX command stream from `ef###.bytes`. Every summon `Hi_*` op is called from exactly one site inside it; each handler's entry pointer also sits in a function-pointer dispatch table at `~0x68780..0x68cf8` (in section **`.data`**, writable). This interpreter is the native embodiment of the `.seq` sequencer we already author against.

4. **Pose + advance (per frame, inside `Hi_DrawSummonModel` @0x17740).** Each Draw: (a) the pose evaluator @0x186a0 rebuilds the creature's **root world transform** at `SummonData+0x40` from rotation/translation/scale vectors passed as Draw arguments; (b) fn 0x7820 fills the **per-bone world-matrix array** at `SummonData+0x38` by sampling the motion clip at the current frame counter `rec+0x54`; (c) the frame counter auto-increments +1 (loop-or-hold clamp); (d) a mesh loop walks the model, skipping any mesh whose bit is set in the hide-mask `SummonData+0x20`.

5. **Project + emit (software GTE).** For every un-hidden vertex, `Hi_DrawSummonModel`'s engine runs a real GTE `RotTransPers` (@0x3e80): matrix-multiply `>>12`, then a **perspective divide** `q=(H<<16)/SZ` (integer `idiv` @0x4001b), producing final **screen-pixel** `(x,y)` + an ordering-table depth. The camera's zoom/pan (`H/OFX/OFY`) is folded in here. Primitives are assembled as PSX P_TAG packets (screen xy at packet+8/+0x10/+0x18) and linked into an ordering table.

6. **Harvest.** Managed `SFXRender` loops `SFX_GetPrim(ref otz)` (`SFXRender.cs:77-86`), receiving one already-projected 2D primitive at a time, and `SFX_UpdateCamera(isDebug)` once (`SFX.cs:1590-1605`), receiving 13 floats = the per-frame VIEW matrix + near-Z. It stamps those onto the Unity camera.

**Consequence that shapes everything downstream:** the 3D→2D projection happens *inside the DLL*. The metric creature transform is consumed at the perspective divide (step 5) and never crosses the P/Invoke boundary. Managed code sees the creature only as a post-GTE 2D silhouette; it sees the **camera** fully and cleanly.

---

## 2. THE SUMMON MODEL — the decoded struct + roster

### 2.1 The record array (CONFIRMED, cross-checked on x86)

```c
// base RVA 0x220830 (x64) — runtime .bss scratch, ZERO on disk. stride 0x58, LENGTH 1.
struct SummonRec {            // 0x58 bytes
/*+0x00*/ SummonData* data;   // ptr to DATA block; 0 => accessor hits the error stub
/*+0x50*/ u8   active;        // 1 = registered; the gate byte in every accessor
/*+0x54*/ u16  frame;         // current motion frame counter
};
```
- Base 0x220830: `SetSummonMotion@0x17a10 : lea rax,[rip+0x208e0e]`. Every accessor `imul idx,0x58; add base`.
- LENGTH = 1: the `RegisterSummonModel@0x15ee0` free-slot loop bound is `cmp eax,1; jl` (@0x15f14). A second register attempt falls to "no free slot." **One summon model exists at a time; slot 0.**
- **No dedicated "current summon index" global** — the index is a caller argument (Register only fills 0).
- x86 build (`b5_x86.py`): base 0x20869c, stride **0x54** (−4 = the one 8→4 pointer), LENGTH 1 byte-identical. Every structural claim reproduces; all divergences are pure pointer-size shrinkage.

### 2.2 The DATA block (rec+0x00 → SummonData) (CONFIRMED)

```c
struct SummonData {           // runtime-allocated; alloc @0x30cc9, cleared @0xf90d
/*+0x08*/ u32        modelId; // Register@0x15f3f  <- managed model arg[+0x3c]
/*+0x10*/ Motion*    motion;  // SetMotion@0x17a3b writes; Draw@0x17776 reads. frameCount = u16[motion+2]
/*+0x20*/ u32        hideMask;// MESH-HIDE bitmask, SET bit = HIDDEN. Show clears / Hide sets. <<HideMeshes
/*+0x38*/ PSXMATRIX* bones;   // -> per-bone WORLD matrices, stride 0x20 (re-pointed per frame, 2.4)
/*+0x40*/ PSXMATRIX  root;    // the creature's per-frame root world TRS (rot@+0x40, trans@+0x54, scale@+0x78)
/*+0x70*/ TexAnim*   texAnim; // Start@0x188cb / Stop@0x1895a ; stride 0x18 ; per-mesh UV animation
};
struct PSXMATRIX { s16 m[3][3]; s16 pad; s32 t[3]; }; // 32B classic libgte MATRIX; rot fp12 /4096, trans world units
struct Motion    { /*+0x02*/ u16 frameCount; /*+0x0c,0x10*/ u32 offA,offB; };  // VA-relocated on first Draw
```

### 2.3 The roster (fn → REAL body RVA → role) (CONFIRMED)

Every entry is called from exactly one site inside the interpreter @0xeea4 (verified: `verify_dispatch.py`). `refkit.locate_function` returns the MSVC cold **error funclet** that merely names the fn via its "…memory not enough!" string — the real bodies are:

| Hi_ function | real body | dispatch slot | role |
|---|---|---|---|
| RegisterSummonModel | 0x15ee0 | 0x68838 | build `summonModels[0]` from the managed model arg |
| DrawSummonModel | 0x17740 (entry 0x17710) | 0x68848 | per-frame driver: pose -> advance -> per-bone -> mesh-emit |
| SetSummonMotion | 0x17a10 | 0x68850 | bind motion -> `DATA+0x10`; zero frame counter |
| SetSummonMotFrame | 0x17a70 | 0x68aa0 | seek: set `rec+0x54`, clamped to `frameCount` |
| GetSummonBonePos | 0x185b0 | 0x68c28 | read one bone's int16 translation |
| **GetSummonBoneMatrix** | **0x18630** | 0x68ca0 | **copy a bone's full 32-B world matrix — the transform getter** |
| ShowSummonModelMesh | 0x187e0 | 0x68c68 | clear a hide bit in `DATA+0x20` |
| HideSummonModelMesh | 0x18840 | 0x68c70 | set a hide bit in `DATA+0x20` — the native `HideMeshes` op |
| StartSummonTexAnim | 0x188a0 | 0x687e0 | enable a mesh part's UV/texture animation |
| StopSummonTexAnim | 0x18930 | 0x687d8 | disable a part's texanim |
| ModifySummonModelAbr | 0x18af0 | 0x68c18 | per-mesh semi-transparency (ABR); 0xff = no-op |
| ModifySummonModelRGB | 0x18b50 | 0x68988 | per-mesh RGB tint |

*Code-shape note (corrected from A1's "Pattern B is universal"):* the validator-entry / cold-split-body / separate-29B-error-stub triad is genuine and reproducible for the **Draw\*** family only (e.g. DrawSummonModel 0x17710/0x17740/0x179f2; DrawEffModel 0x16150/0x16184/0x16547). It is **not** universal: the `Register*EffModel` family are single unified functions (string range IS the work body, error tail inlined), and `Hi_RegisterSummonModel`'s string range is a pair of pure error stubs with its work body *above* (0x1606c), not below. Pure taxonomy — no bearing on the transform goal.

### 2.4 The mesh-visibility mask (CONFIRMED) — and it is NOT our managed `HideMeshes`

`SummonData+0x20` is a u32 bitmask; **set bit = mesh hidden**. `Hi_HideSummonModelMesh@0x18840` sets `or (1<<meshIdx)`, `Hi_ShowSummonModelMesh@0x187e0` clears `and ~(1<<meshIdx)`. Consumed inside the Draw mesh loop (`bt [DATA+0x20], i; jb skip` @0x17916) so a hidden mesh's polys are **never emitted** — they never enter the ordering table and never reach `SFX_GetPrim`. Bit index = the model's **ordinal mesh index** (0..meshCount−1, `meshCount = byte[modelGeom+3]`). This is the native realization of the `HideMeshes=<hex>` lever and its **first use anywhere** was the Thomas swap.

**Critical correction (B2): the native mask and our shipping `HideMeshes=` are TWO DIFFERENT LAYERS.**

| axis | NATIVE `DATA+0x20` (`Hi_Hide/Show`) | MANAGED `preventedMesh*` (our `HideMeshes=`) |
|---|---|---|
| identifier | **ordinal mesh index** in the summon MODEL | **SFXKey hash** of blend/texture state (or harvest-order ordinal / FBX index) |
| stage | inside the DLL — skips primitive **EMISSION** | managed — skips **RENDER** after the `SFX_GetPrim` harvest |
| driven by | native `.seq` opcode in `ef###.bytes` (interp 0x117df/0x11806) | Memoria `BattleActionCode HideMeshes=` (`UnifiedBattleSequencer.cs:366`) |
| precision | exact 1 bit <-> 1 model mesh, stable | a KEY can span multiple meshes; index mode is harvest-order-fragile |

So A2's "the hex IS this bitmask" is imprecise: they are distinct culling mechanisms and can disagree. The native op is more precise and cheaper (polys never generated) — but reaching it means emitting the native Show/Hide `.seq` opcode into the byte stream (a next-step decode, 7). A third thing named "HideMesh" — `btl_mot.HideMesh` (`FF9/btl_mot.cs:835`) — is the *battler* Vanish/banish subsystem; unrelated to summons, do not conflate.

---

## 3. THE PRIZE — recovering the creature's true per-frame transform

**The prior round's verdict ("no data-side method can recover the creature transform") is corrected in exactly one way: it is unrecoverable *statically* and unrecoverable *from any managed-visible stream*, but it is fully recoverable *live* via a passive memory read.**

### 3.1 Where the transform physically lives (CONFIRMED, B1/B2/B3, x86-confirmed B5)

- **Root world placement = `SummonData+0x40`** — a full 32-byte PSX MATRIX: 3x3 s16 rotation (fp12 /4096) @+0x40, s32 translation @+0x54, and (corrected from A2) an s16 **scale** triple @+0x78. Built **every Draw** by pose_eval@0x186a0 from the `(rotation, translation, scale)` vectors passed as arguments to the draw routine — never persisted between frames, never sourced from a struct field or global (both refutation conditions actively checked FALSE in `V-root-transform-from-draw-args`).
- **Per-bone world matrices = `SummonData+0x38[]`** — stride 0x20, filled by fn 0x7820, which re-points `+0x38` at the motion clip's current-frame bone block and chains parent->child so **every entry is a WORLD transform** (B1 settled the A1-vs-A2 contradiction: bone[0] == the root == `DATA+0x40`). `Hi_GetSummonBoneMatrix(idx, boneIdx, out)@0x18630` copies one whole 32-byte matrix.
- **Units + frame:** PSX-GTE world units (thousands scale), the **same coordinate system** as the logged camera VIEW/PROJ — which is why `screen = PROJ · VIEW · rootTranslation` reproduces the creature's on-screen position. The transform is *pre-perspective* (the camera's zoom/pan enter only at 0x3e80), so pairing `DATA+0x40` with the logged VIEW/PROJ places a replacement puppet exactly.

### 3.2 The three recovery paths (CONFIRMED)

| Path | Verdict | Detail |
|---|---|---|
| **(i) Statically (disk bytes)** | **NO** | `summonModels@0x220830`, DATA, `+0x38`, `+0x40`, the motion clip are all runtime scratch, zero on disk. Only LAYOUT + ACCESS PATH are static. |
| **(ii) Live memory read** | **YES — the prize** | Passive read of `module_base(FF9SpecialEffectPlugin) + 0x220830 + 0x00 -> +0x40` each frame. No export, no P/Invoke-by-name, no DLL patch, no asset bytes. |
| **(iii) Managed DllImport surface** | **NONE existing; ADDABLE via (ii)** | The 13 exports expose the camera + 2D primitives only. `Hi_GetSummonBoneMatrix` is interpreter-internal, not exported. The (ii) read IS managed code (`Process.Modules` + `Marshal`). |

### 3.3 The concrete SfxMeshProbe extension (the FLIGHT-staging fix)

Add a `ROOT` row to `Memoria/Battle/SFX/SfxMeshProbe.cs`, called alongside `LogCamera` in `SFXDataMesh.Runtime.Render()` (so it correlates on `SFX.frameIndex` with the existing VIEW/PROJ/PRIM rows, and reads **after** the native tick has run this frame's Draw). Resolve the plugin base once via `Process.GetCurrentProcess().Modules`, then per frame:

```csharp
IntPtr rec = pluginBase + 0x220830;                 // slot 0 (LENGTH == 1)
if (Marshal.ReadByte(rec + 0x50) == 0) return;      // rec.active gate
IntPtr data = (IntPtr)Marshal.ReadInt64(rec);       // rec+0x00 -> DATA
if (data == IntPtr.Zero) return;
// root TRS @ DATA+0x40: 9x Int16 rot (/4096) then 3x Int32 trans @ +0x54
short r0..r8 = Marshal.ReadInt16(data + 0x40 + i*2);
int tx = Marshal.ReadInt32(data + 0x54), ty = +0x58, tz = +0x5C;
w.WriteLine("ROOT," + SFX.frameIndex + "," + r0..r8 + "," + tx + "," + ty + "," + tz);
```

Everything `try`-wrapped (a probe must never take the render down); gated on a new `[SfxProbe] CaptureRoot=1` sub-flag; zero-cost when disabled. **Files:** `SfxMeshProbe.cs` (+~45 lines), `SFXDataMesh.cs` (+1 call). Effort **LOW**. Then a **built-in faithfulness validator** (closes A4's gap): reproject the just-read root through the same frame's logged VIEW/PROJ and compare to the creature's `PRIM` screen centroid — if it lands, the world read + sign convention are proven and FLIGHT can hang Thomas on Bahamut's *metric* trajectory, not merely v7's in-frame-by-construction coverage.

**Hard provenance line (B4):** log the **root only**. Dumping the full per-bone array `DATA+0x38[]` across a whole cast would reconstruct the skeletal animation = extracting stock animation bytes = BLOCKED. The root transform is choreography/staging — the same class of data as the camera track we already log.

---

## 4. THE PRIMITIVE-SPACE RESOLUTION (A4) — post-projection, and what it voids

`SFX_GetPrim` emits **already-projected 2D PSX-GPU primitives**: each `x0,y0` (Int16) is a final **screen-pixel** coordinate (the output of the DLL's internal GTE @0x3e80), and `otz` is an **ordering-table depth-SORT scalar**, not a metric Z. Proven three ways: from C# (every consumer treats `x` as pixels, compares to 0/160/320; `GzDepth=-otz` is one shared Z per primitive), from the DLL (the perspective divide at `idiv @0x4001b` produces the screen xy that lands in the packet), and from the live `sfxmeshprobe.log` (PRIM x in [-12..386], y in [-78..63] = screen band, not thousands-scale world).

**Which prior conclusions this validates or voids:**
- **VALIDATES** A3 0 / B3 7 (the creature transform never crosses the boundary; only a 2D footprint + lossy `otz` escapes) — now proven from *both* the managed and the native side.
- **VOIDS** every study conclusion that read the probe's **MESH bounds** `cx,cy,cz` as *Bahamut's 3D world position* and re-projected them: `matrix_solve.py`'s "put Thomas at Bahamut's measured world position" premise, its "X,Y = bounds center," and its "Z = far corner = world depth." The MESH bounds are **pool-polluted**: `_mesh.vertices` is assigned a fixed 14000-slot array (vertCount == 14000 on every row), so every AABB contains the origin on all three axes (100.0% of 61,723 rows) and max.z pins to 0 (88.6%). The box is anchored to the origin, never fitted to the creature.
- **EXPLAINS** the study's own "only ~8/324 frames land on screen" self-diagnostic: pushing screen-space points back through a 3D perspective camera *should* scatter — it is evidence against the world-position reading, not a tuning knob.
- **Does NOT invalidate** deployed FLIGHT v7 (it constructs on-screen coverage directly, not from bounds).

**What IS recoverable from the primitive stream today:** the creature's per-frame **screen trajectory**, directly from the un-pooled **`PRIM` rows** (filter by body `keyHex`/`code`, take the screen AABB/centroid), no projection or matrices needed — off-screen swoops show as x<0/x>320. Never use MESH `cx,cy` for this. The **world** transform is absent from this stream and must come from 3's memory read.

---

## 5. THE CAMERA (A5) — recoverable vs runtime-only

**Fully live-recoverable, every frame, with no eye position and no anchor buffer.**

- `SFX_UpdateCamera` export @0x1dd0 is a thunk -> real body **0x1e80..0x2030** (432 B), returning a pointer to the 13-float array @RVA **0x211df0**.
- The installed camera is a PSX int16 GTE struct @RVA **0x69730**: 9 int16 rotation (fixed /4096) @+0x00, int32 TRX/TRY/TRZ @+0x14/+0x18/+0x1c, int16 **H** (projection distance) @+0x20. Converted to the 13 contiguous floats: [0..8] rotation, [9..11] translation, [12] = H/near-Z.
- Managed code (`SFX.cs:1595-1604`) `Marshal.Copy`s the 13 floats and builds `camera.worldToCameraMatrix` from floats 0–11 (`PsxCamera.PsxMatrix2UnityMatrix`, with the Y-row/col sign flips for the RH->LH swap) and `camera.projectionMatrix` from float[12] via a **fixed off-center frustum** whose only per-frame free variable is the near-Z. **So the per-frame zoom is a single scalar (H), not an FOV field** — this is the mechanism behind the observed "47->24 degree push-in."
- `resolve_position@0x145a0` = `anchor + 4096.8*(cos/sin theta)` — **K=4096.8 branch-A CONFIRMED** (real MSVCR120 cos/sin thunks, constants pi@0x4b6a0, +/-4096.8@0x4b6c8/0x4b6e8).

**Runtime-only (zero on disk):** the eye/anchor scratch buffer @RVA **0x220060** (indexed stride 8 by `lookup_anchor@0x148f0`), the keyframe source @0x211e28, and the installed-camera VALUES @0x69730. **But none of these is needed** — VIEW + PROJ fully define the camera and both cross the boundary cleanly.

**Shortest path to per-frame (VIEW + PROJ + creature transform):** all three are live-only reads. VIEW = `Camera.main.worldToCameraMatrix` after `SFX.UpdateCamera()` (already logged as the probe's `VIEW`/`PROJ` rows); creature transform = the 3 `ROOT` read at `SummonData+0x40`. Because both live in the same PSX-GTE world space, `screen = PROJ · VIEW · rootPos` — a Unity puppet parented at the root is tracked for free by `Camera.main`. **The camera is no longer any kind of blocker.**

---

## 6. AUTHORING ENABLEMENT (B4) — the ranked TRACK / AUTHOR / BLOCKED menu

| # | Item | Tag | Buys | Effort | Provenance |
|---|------|-----|------|--------|-----------|
| 1 | **ROOT-transform probe** (3.3) — log `SummonData+0x40` per frame via a managed memory read | TRACK | The staging fix: Bahamut's true per-frame world placement -> parent Thomas there faithfully | LOW | SANCTIONED (root = choreography, not asset bytes; a read, not a patch) |
| 2 | **Reprojection-validation pass** — reproject logged ROOT through logged VIEW/PROJ, compare to `PRIM` centroid | TRACK | Converts FLIGHT from "in-frame by construction" to *validated faithful*; settles model-space vs view-space empirically | LOW (analysis-only, once #1 lands) | SANCTIONED |
| 3 | **`.seq` summon-op linter / cutscene inspector** — commit a parser for the summon opcodes + record layout | AUTHOR | Lints a `[[summon]]` block (HideMeshes hex validity, motion-frame range, TexAnim/ABR/RGB targets); powers a cutscene inspector over the ROOT/VIEW/PROJ/PRIM streams | MEDIUM | SANCTIONED (parser for our own grammar; no stock bytes) |
| 4 | **Per-mesh ABR / RGB / TexAnim authoring** — expose the native fine-grained mesh ops | AUTHOR | Finer creature dressing than HideMeshes: per-mesh fade/tint/UV-scroll | MEDIUM (gated on decoding each op's `.seq` operand encoding) | SANCTIONED (emits `.seq` data) |
| 5 | **Native precise per-mesh Hide/Show** — emit the native Show/Hide `.seq` opcode into `ef###` | AUTHOR | Exact 1-bit-per-model-mesh hide, stable + emission-free (beats the coarse managed key filter) | MEDIUM (gated on the opcode-number decode, 7) | SANCTIONED |
| 6 | **Camera-track authoring (camera_codec attack-slot sweep)** — confirmed still the right play | AUTHOR | Author the summon camera; zoom = one animated scalar (near-Z/H); validate against captured VIEW/PROJ | existing lever | SANCTIONED (data track) |
| 7 | **Stock Eidolon geometry / animation extraction** | BLOCKED | — | never | provenance |
| 8 | **Patched / redistributed `FF9SpecialEffectPlugin.dll`** (e.g. adding a bone-matrix export) | BLOCKED | — | never | provenance |
| 9 | **Inverting `SFX_GetPrim` / MESH bounds -> a world transform** | BLOCKED | — | — | physics: transform consumed at the GTE divide (A4); every "reproject the bounds" method is VOID |

Note the camera decode *ratifies* our existing camera_codec lever and opens nothing better: the summon camera is a **data-driven keyframe track** (curCam @0x69730 fed by the stepper fn @0x2030 from the btlseq camera data), not a hidden native "camera brain" to hook.

---

## 7. NEXT STEPS

**Single highest-value next action:** land **TRACK #1 (the ROOT probe) + TRACK #2 (the reprojection check)**. It is LOW effort, managed-only on the `memoria-patches/` stack, provenance-clean (root = choreography, no DLL patch, no asset bytes), and it closes the study's actual open problem — the creature's true per-frame staging that "no data-side method could recover." A single instrumented cast yields the ROOT curve; the reprojection check confirms it is the faithful world placement AND simultaneously resolves B3's one residual (whether `DATA+0x40`/`+0x38` are model-space or already view-space — settled empirically by whether `PROJ·VIEW·root` lands on the PRIM centroid).

**The runway after it:**
1. FLIGHT re-staging: hang the rung-7 Thomas puppet on the captured ROOT curve (metric-faithful), replacing v7's constructed coverage. The Thomas-swap staging problem is then closed.
2. Decode the native `.seq` **opcode number** for Show/Hide (the interpreter dispatch case landing at 0x117df/0x11806; operand reader @0x126c0) -> productize precise per-mesh hide (menu #5).
3. Decode the `.seq` operand encoding for ABR/RGB/TexAnim (menu #4) against a real cast.
4. Commit the `.seq` summon-op linter / cutscene inspector (menu #3), consuming this dir's tables.

---

## 8. PROVENANCE LEDGER

- **No extracted stock creature geometry or animation bytes were written anywhere.** Every runtime value in the summon path (`summonModels@0x220830`, the `SummonData` block, the `+0x38` bone array, the `+0x40` root TRS, the motion clip, the camera scratch @0x69730/0x211df0/0x220060) is zero-on-disk `.bss`/heap scratch — read live at most, never asserted statically, never dumped as asset bytes.
- **No DLL was modified or redistributed.** All DLL work is read-only static analysis (RVAs, mnemonics, struct offsets, control flow) of the user's own installed `FF9SpecialEffectPlugin.dll` (x64 + x86).
- **Committable artifacts are analysis + format-parsers only:** this report + the A/B slice `.md` files + the verification `.md` files + `refkit.py` / `b5_x86.py` / the `a1_*`/`b3_*`/`v_a2_*`/`verify_dispatch.py` helpers (all read the user's own DLL; emit RVAs/offsets, no game bytes).
- **The proposed `SfxMeshProbe.ROOT` extension** patches the *open-source Memoria Assembly-CSharp* (the sanctioned lane, not the SE binary), reads the plugin's runtime memory (root transform only — never the per-bone array over time), and logs it to a debug file. It writes no shippable asset bytes.
- Every native claim cites `fn@rva`; every managed claim cites `file:line`. Runtime-only values are labeled as such throughout.
