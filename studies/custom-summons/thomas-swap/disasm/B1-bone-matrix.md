# B1 — `Hi_GetSummonBoneMatrix`, THE PRIZE: the creature's true per-frame WORLD transform

Deep-decode slice B1 of the FF9SpecialEffectPlugin.dll (x64) summon-cutscene disasm round.
Reads A1–A5 (all five phase-1 maps) and resolves the one live-open contradiction between them:
**are the `SummonData+0x38` bone matrices bone-LOCAL (A2) or the animated WORLD pose (A1)?**

Verdict up front: **they are WORLD-space per-node matrices, and the creature's overall per-frame
world placement is `SummonData+0x40` (== bone[0]'s world matrix). It is runtime-only in VALUE but
live-readable with NO DLL patch and NO export, via a module-base + RVA memory read. This is the
metric transform A4 declared "absent from this stream" — it is absent from the *managed primitive
stream*, but present and readable in the DLL's runtime scratch.**

All RVAs image-base-relative (`ImageBase 0x180000000`; VA = RVA + base). Every claim cited
`fn@rva : ins@rva`. C# cites relative to `C:/gd/FFIX/Memoria/Assembly-CSharp/`. DATA-block VALUES
are runtime `.bss` scratch (zero on disk) and are flagged RUNTIME-ONLY; the ACCESS PATH is static.

---

## 0. TL;DR for the orchestrator / FLIGHT

* `Hi_GetSummonBoneMatrix(idx, boneIdx, out)` real body **@0x18630** (98 B). Signature
  `void(int idx=ecx, int boneIdx=edx, PSXMATRIX* out=r8)` — copies a 32-byte PSX GTE MATRIX from
  `[[0x220830 + idx*0x58] + 0x38] + boneIdx*0x20`. Format: 3×3 `s16` rotation (fixed-point /4096)
  at `out+0x00..0x11`, `s16` pad `+0x12`, `s32` translation X/Y/Z at `+0x14/+0x18/+0x1c`. Same
  GTE convention as the camera VIEW matrix (A5 §2/§3).
* **The bone-matrix array holds WORLD matrices**, filled every Draw by the shared node-transform
  helper **0x7820**: the root node's slot is copied from **`SummonData+0x40`** (the `pose_eval`
  world TRS); child nodes = parent-world ∘ local. Proof in §3. (A1 "animated world pose"
  CONFIRMED; A2 "bone-space local" corrected.)
* **The creature's true per-frame world transform = `SummonData+0x40`** — a TRS built once per
  Draw by `pose_eval@0x186a0` from `Hi_DrawSummonModel`'s `(rotPtr, posPtr, scalePtr)` arguments,
  which the `.seq`/camera runtime feeds. Rotation 3×3 `s16` @`+0x40`, translation 3×`s32`
  @`+0x54`, scale 3×`s16` @`+0x78`. In **PSX-GTE world units** — the SAME world+units as the
  logged camera VIEW/PROJ, so `screen = PROJ · VIEW · (root translation)` (A5 §7 identity; B1
  supplies the missing operand). §4.
* **Recovery:** (i) statically **NO** (all values are zero-on-disk scratch); (ii) **LIVE — YES**,
  via a passive read of `SummonData+0x40` at `module_base + 0x220830 + 0x00 → +0x40`, added to
  `SfxMeshProbe` with zero DLL modification (§6); (iii) managed surface: none of the 13 DllImports
  exposes it (it is **not exported**), but the module-base+RVA read is itself managed-executable.
* This **hands FLIGHT Bahamut's true metric trajectory** and, via the already-logged
  VIEW/PROJ + PRIM-centroid, a **built-in faithfulness validator** — closing A4's "faithfulness
  cannot be validated from this data."

---

## 1. Locating the real getter (error stub vs body)

`refkit.locate_function("Hi_GetSummonBoneMatrix")` returns the **cold MSVC error funclet @0x16c80**
(29 B: `lea rdx,→str; call panic; int3`). Its self-naming string is at RVA **0x4b418**
(`'Hi_GetSummonBoneMatrix () '`, confirmed). That string is `lea`-referenced from **3 sites** —
matching the calibration:

| xref site | context | role |
|---|---|---|
| `0x16c80` | the shared cold error funclet itself | `Hi_DrawEffModelByBone`'s inlined bone-fetch borrows it |
| `0x176ba` | `Hi_DrawMorphModelByBone` cold stub (`0x176d4` region) | its inlined bone-fetch borrows the same string |
| `0x18678` | **inside the REAL getter's own abort path** | ← the getter is here |

So the real body is the `.pdata` range covering `0x18678`: **`0x18630..0x18692`** (98 B).

Called live from the `.seq`/SFX mega-interpreter: **`0xeea4 : call 0x18630 @0x1195a`** (one caller).
`Hi_GetSummonBonePos`'s real body @0x185b0 is likewise called from `0xeea4 @0x115cb`. So the game
DOES read summon bone matrices during a cast (a `.seq` opcode fetches a creature bone's world
matrix to hang sub-effects on it — semantic corroboration that the array is world-space).

---

## 2. `Hi_GetSummonBoneMatrix` — full disassembly (0x18630..0x18692)

```
0x18630: sub   rsp,0x28
0x18634: movsxd rax,ecx           ; idx  (arg0, ecx)
0x18637: imul  r9,rax,0x58        ; idx*0x58
0x1863b: lea   rax,[rip+0x2081ee] ; -> 0x220830  summonModels base
0x18642: cmp   byte[r9+rax+0x50],0 ; rec.active (+0x50)
0x18648: je    0x18675            ;   0 -> abort
0x1864a: mov   rax,[r9+rax]       ; data = rec[+0x00]
0x1864e: test  rax,rax
0x18651: je    0x18675            ;   null -> abort
0x18653: mov   rax,[rax+0x38]     ; mtxArr = data[+0x38]
0x18657: movsxd rcx,edx           ; boneIdx (arg1, edx)
0x1865a: shl   rcx,5              ; boneIdx*0x20
0x1865e: movups xmm0,[rcx+rax]         ; bytes  0..15
0x18662: movups [r8],xmm0              ; -> out (arg2, r8)
0x18666: movups xmm1,[rcx+rax+0x10]    ; bytes 16..31
0x1866b: movups [r8+0x10],xmm1
0x18670: add   rsp,0x28
0x18674: ret                       ; void (no return value)
0x18675: mov   r8d,ecx            ; abort: pass idx to diag
0x18678: lea   rdx,[rip+0x32d99]  ; -> 0x4b418  "Hi_GetSummonBoneMatrix () "
0x1867f: lea   rcx,[rip+0x20820a] ; -> 0x220890  DBGCTX
0x18686: call  [rip+0x31a84]      ; -> 0x4a110  (printf-family via IAT)
0x1868c: call  0x151a0            ; panic/abort trampoline
0x18691: int3
```

**Signature:** `void Hi_GetSummonBoneMatrix(int idx /*ecx*/, int boneIdx /*edx*/, PSXMATRIX* out /*r8*/)`.
Fastcall, no return (the failure path aborts; success writes 32 bytes to `out`). No bounds check on
`boneIdx` (trusts the caller). `Hi_GetSummonBonePos@0x185b0` is the same access path but copies only
the low `s16` of each translation (`word[bone+0x14/0x18/0x1c]` → 3×`s16` at `out`).

### Output format — the 32-byte PSX GTE MATRIX

```c
struct PSXMATRIX {          // 32 B; classic PSX libgte MATRIX, row-major
/*+0x00*/ s16 m[3][3];      // 3x3 rotation, fixed-point /4096 (1.0 == 0x1000)
/*+0x12*/ s16 pad;
/*+0x14*/ s32 t[3];         // translation X,Y,Z (GTE world units)
};
```

Identical convention to the camera's installed matrix (A5 §2 `R[0..8]` /4096 + `TRX/TRY/TRZ`).
Managed code converts the /4096 rotation exactly as `PsxCamera.PsxMatrix2UnityMatrix`
(`PsxCamera.cs:106-115`) does for the camera — see §5 for the correct (different) convention for a
MODEL matrix vs a VIEW matrix.

---

## 3. The array is WORLD-space — settling A1 vs A2

The `SummonData+0x38` array is filled each frame by the **shared node-world-matrix builder
`0x7820`** (called by ALL six draw bodies: `DrawEffModel@0x16184`, `DrawSliceEffModel@0x165ae`,
`DrawEffModelByBone@0x168d0`, `DrawMorphEffModel@0x16e39`, `DrawMorphModelByBone@0x172fd`,
**`DrawSummonModel@0x1786e`**). Signature `0x7820(rcx=DATA, dx=frame, r8=nodeBuf)`.

`0x7820` first does `mov [rcx+0x38], r8` (`@0x7842`) — i.e. `SummonData+0x38` is (re)pointed at the
node buffer — then writes ONE 32-byte matrix into that buffer via one of three branches:

| branch | condition | what it writes into the node matrix |
|---|---|---|
| motion | `[DATA+0x10] != 0` (has a motion clip) — `@0x7846 jne 0x7a20` | composes from the model-data base `0x5789e0` sampled at `frame` (the animated local) with the parent → **world** |
| parent | no motion, `[DATA+0x30] != 0` — `@0x784f` | reads the **parent's `[+0x38]` world matrix** rotation + copies parent translation → child **world** |
| **root** | no motion, `[DATA+0x30]==0` — `@0x797a` | copies **`DATA+0x40` (the `pose_eval` root TRS)** into the slot: rotation `word[DATA+0x40..0x50]` with **columns 1,2 negated** (`neg cx` @0x798a/0x799c/0x79b4/0x79c6/0x79de/0x79ed) + translation `[DATA+0x54/0x58/0x5c]` verbatim (`@0x79f4-0x7a0f`) |

The **root** branch is the proof: the root node's stored matrix = the `pose_eval` world placement
(`DATA+0x40`), sign-adjusted by the PSX Y,Z basis flip (`R · diag(1,-1,-1)`). Child branches chain
off the parent's already-world `[+0x38]` matrix. **Therefore every entry in the `SummonData+0x38`
array is that node's WORLD transform, not a bone-local one.** A1's reading is correct; A2's
"bone-space local" is corrected to "world-space, root == DATA+0x40."

**Which bone is root:** index **0**. In `DrawSummonModel` the pre-loop `0x7820` call (`@0x1786e`)
fills node slot 0 (writes at buffer `+0x00..+0x1c`, `0x7877`/`0x78c0`/`0x79f4`) from the root TRS,
before the per-mesh loop (`0x17910`) draws parts 0..N-1 (hide-masked on `DATA+0x20`, `bt eax,ebx`
`@0x17916` — the per-part `HideMeshes` gate in action). So
`Hi_GetSummonBoneMatrix(idx, 0, out)` returns the creature's **root world matrix**.

> Robustness note: `SummonData+0x38` is *re-pointed* per node/frame (`0x7842`), so the array base is
> only stable within a frame. The unambiguous, always-stable authoritative read is **`SummonData+0x40`
> directly** (§4) — written once per Draw by `pose_eval`, never touched by the mesh loop.

---

## 4. `SummonData+0x40` — the root world TRS (the creature's placement)

`pose_eval@0x186a0` (the shared root-TRS builder, called by the 4 non-slice draw bodies incl.
`DrawSummonModel@0x17767`). `DrawSummonModel` maps its own args in: pose_eval receives
`rcx=DATA, rdx=rotPtr, r8=posPtr, r9=scalePtr` where `(rotPtr,posPtr,scalePtr)` are
`Hi_DrawSummonModel`'s first three arguments (`0x1774f-0x1775a`). It builds `[DATA+0x40]`:

```
0x186b2: lea  rbx,[rcx+0x40]                 ; work on DATA+0x40
         ; --- seed identity 3x3 (fp12) ---
0x186bd: mov  ebp,0x1000
0x186ca: mov  dword[rbx+0xe],0x10000000      ; m7=0, m8=0x1000
0x186d1: mov  dword[rbx+6],0x10000000        ; m3=0, m4=0x1000
0x186d8: mov  word[rbx+4],di(0)              ; m2=0
0x186dc: mov  dword[rbx],ebp                 ; m0=0x1000, m1=0
0x186de: mov  dword[rbx+0xa],edi(0)          ; m5=0, m6=0
         ; --- rotation from rotPtr (rdx=r12): 3x s16 Euler @ +4,+0,+2 ---
0x186ef: movsx ecx,word[rdx+4]  ; call 0x3910   (GTE RotMatrix axis A)
0x186fb: movsx ecx,word[r12]    ; call 0x37a0   (axis B)
0x18708: movsx ecx,word[r12+2]  ; call 0x3850   (axis C)   -> 3x3 into DATA+0x40..0x51
         ; --- translation from posPtr (r8=r14): 3x s32 ---
0x18738: mov  eax,[r14];   mov [rbx+0x14],eax   ; t0 -> DATA+0x54
0x1873e: mov  eax,[r14+4]; mov [rbx+0x18],eax   ; t1 -> DATA+0x58
0x18745: mov  eax,[r14+8]; mov [rbx+0x1c],eax   ; t2 -> DATA+0x5c
         ; --- scale from scalePtr (r9=r15): 3x s16 via 0x3b60, else default 1.0 @ DATA+0x78 ---
0x187ab: call 0x3b60                           ; apply scale vector to DATA+0x40
0x187b5: mov  dword[rsi+0x78],0x10001000       ; (no-scale branch) default scale 1.0
```

So **`SummonData+0x40` = a full TRS world matrix**: `s16` rotation @`+0x40`, `s32` translation
@`+0x54`, and a `s16` scale triple @`+0x78`. Its inputs are the per-frame `(rot, pos, scale)` the
`.seq`/camera runtime feeds `Hi_DrawSummonModel` — i.e. the animated flight path of the creature.
Written **once** per Draw (before the node/mesh work); stable for the rest of the frame.

**Units + frame:** PSX-GTE world units (thousands scale; cf. A5 default camera `TRZ=5846`, A4 VIEW
translation `-2651`). The root translation and the camera VIEW live in the **same coordinate
system** — which is exactly why `PROJ · VIEW · rootPos` reproduces the creature's on-screen
position (A5 §7). A4's finding that this metric is "absent from the `SFX_GetPrim`/MESH stream"
stands; B1 finds it lives at `SummonData+0x40`, one pointer-chase away.

---

## 5. Placing a Unity puppet from the root (PSX → Unity)

The root `s16` 3×3 is a **model (local→world)** matrix — do **not** run it through
`PsxMatrix2UnityMatrix`, which is for a **VIEW (world→camera)** matrix (a different sign pattern:
it negates m01,m10,m12,m20,m22). For the creature transform the two useful reads:

* **Position (all FLIGHT strictly needs):** root translation `(tx,ty,tz)` @`DATA+0x54`. To place a
  Unity puppet so `Camera.main` (whose `worldToCameraMatrix` = the logged VIEW) projects it where
  Bahamut was, mirror the VIEW's own translation-column convention (`m03=+X, m13=-Y, m23=-Z`;
  `PsxCamera.cs:116-118`): **`unityPos ≈ (tx, -ty, -tz)` (÷ the scene's PSX-unit scale)**. The exact
  sign/scale is **empirically calibrated once** against the logged PRIM screen centroid (§6) — the
  probe already carries the validator.
* **Orientation (optional):** the root 3×3 /4096 with columns 1,2 negated (the same
  `diag(1,-1,-1)` flip `0x7820` applies at 0x797a) → a Unity rotation basis. Position alone gives a
  faithful trajectory; orientation makes Thomas *face* as Bahamut did.

The internal `pose_eval` → `0x7820` handedness flip (`R·diag(1,-1,-1)`) is consistent with the
camera's Y,Z negation, so a single scene-wide `(x,-y,-z)` world map ties creature and camera into
one Unity space.

---

## 6. THE PROBE EXTENSION (hand FLIGHT the real trajectory) — concrete sketch

`SfxMeshProbe` already logs `VIEW`/`PROJ` per frame from `LogCamera(Camera)`
(`SfxMeshProbe.cs:208-241`) and the un-pooled per-primitive `PRIM,x,y` screen points
(`:300-353`). Add a **`ROOT` row** read straight out of the DLL's summon scratch — **no DllImport,
no DLL patch, no call into the plugin** (a passive memory read of a struct the plugin already
filled this frame). `Hi_GetSummonBoneMatrix` is *not exported*, so name-based P/Invoke is
impossible; the module-base+RVA read is the sanctioned path (and safer than calling in mid-frame).

Resolve the module base once (the DLL is loaded in-process during any battle;
`435200`-byte file present on disk, verified):

```csharp
// --- one-time, cached ---
static IntPtr _sfxBase = ResolveModuleBase("FF9SpecialEffectPlugin");
static IntPtr ResolveModuleBase(String needle) {
    foreach (System.Diagnostics.ProcessModule m in
             System.Diagnostics.Process.GetCurrentProcess().Modules)
        if (m.ModuleName.IndexOf(needle, StringComparison.OrdinalIgnoreCase) >= 0)
            return m.BaseAddress;
    return IntPtr.Zero;
}
// --- static RVAs (from B1) ---
const long REC_BASE = 0x220830, STRIDE = 0x58, OFF_ACTIVE = 0x50, OFF_DATA = 0x00;
const long OFF_ROOT = 0x40 /*rot*/, OFF_ROOT_T = 0x54 /*trans*/, OFF_BONES = 0x38, BONE_STRIDE = 0x20;

// --- per frame, called from LogCamera(cam) alongside VIEW/PROJ (same gating, same SFX.frameIndex) ---
static void LogSummonRoot() {
    if (_sfxBase == IntPtr.Zero) return;
    IntPtr rec = _sfxBase + (int)(REC_BASE + 0 * STRIDE);      // idx 0 (LENGTH==1, A2 §1)
    if (Marshal.ReadByte(rec + (int)OFF_ACTIVE) == 0) return;  // no active summon model
    IntPtr data = Marshal.ReadIntPtr(rec + (int)OFF_DATA);
    if (data == IntPtr.Zero) return;
    // root world TRS @ data+0x40 : 9x Int16 rot (/4096) + 3x Int32 trans @ +0x54
    short[] R = new short[9];
    for (int i = 0; i < 9; i++) R[i] = Marshal.ReadInt16(data + (int)OFF_ROOT + i * 2);
    int tx = Marshal.ReadInt32(data + (int)OFF_ROOT_T);
    int ty = Marshal.ReadInt32(data + (int)OFF_ROOT_T + 4);
    int tz = Marshal.ReadInt32(data + (int)OFF_ROOT_T + 8);
    w.WriteLine($"ROOT,{SFX.frameIndex},{R[0]},{R[1]},{R[2]},{R[3]},{R[4]},{R[5]},{R[6]},{R[7]},{R[8]},{tx},{ty},{tz}");

    // OPTIONAL — every node's world matrix (bone[0]==root); needs a node count.
    // IntPtr bones = Marshal.ReadIntPtr(data + (int)OFF_BONES);   // re-pointed per frame; read AFTER the native tick
    // for (int k = 0; k < NBONES; k++) { read 32B @ bones + k*BONE_STRIDE -> "BONE,frame,k,..." }
}
```

Placement of the call: inside `LogCamera(Camera cam)` (`SfxMeshProbe.cs:208`), right after the
`PROJ` line, so ROOT correlates on `SFX.frameIndex` with VIEW/PROJ/PRIM and is read **after**
`SFX_Update` ticked the native sim (the plugin's `Hi_DrawSummonModel` ran during that tick, so
`DATA+0x40` holds this frame's placement). Guard everything in the existing `try/catch` (a probe
must never crash the render).

**Built-in faithfulness validator (closes A4 §6).** In the probe, project the just-read root
position through the frame's own `VIEW`/`PROJ` and log the resulting screen pixel next to the PRIM
centroid:
`screenNDC = PROJ * VIEW * new Vector4(tx*s, -ty*s, -tz*s, 1)` → viewport → pixel. If it lands on
the creature's PRIM-centroid (the un-pooled body-key primitives, A4 §7), the world read + sign
convention are proven; FLIGHT then places Thomas at `ROOT` for a **metric-faithful** flight, not
merely v7's in-frame-by-construction coverage.

**Bone-level option:** for per-limb attachment, read the `SummonData+0x38` array (`bone k` at
`bones + k*0x20`, world matrices) — but read it strictly *after* the native tick, since `0x7820`
re-points `+0x38` during the tick. For the flight trajectory, `bone[0]`/`DATA+0x40` is all that's
needed.

`SFX_SendFloatData type=1` is the caster/target world pos (A3 §5), **not** the creature's — it is
where the DLL is told to aim, not where the creature ends up; it is NOT a substitute for `DATA+0x40`.

---

## 7. Recovery ledger — the three asks answered

| Path | Verdict | Detail |
|---|---|---|
| **(i) Statically (bytes on disk)** | **NO** | `summonModels@0x220830`, the `SummonData` block, `+0x38` bone array, `+0x40` root TRS, the motion clip — all runtime-allocated `.bss`/heap scratch, zero on disk. Only the LAYOUT + ACCESS PATH are static-recoverable. |
| **(ii) LIVE probe** | **YES — the prize** | Passive read of `module_base(FF9SpecialEffectPlugin) + 0x220830 + 0x00 → +0x40` each frame (§6). No export, no P/Invoke-by-name, no DLL patch. Alternative: `Marshal.GetDelegateForFunctionPointer(base+0x18630)` to call the un-exported getter — works but riskier than the read. |
| **(iii) Managed-visible surface** | **NONE existing; ADDABLE** | The 13 DllImports (A3 §1) expose the camera (VIEW/PROJ) and 2D primitives only — never the creature transform (A3/A4). But (ii)'s memory read is itself managed code (`Process.Modules` + `Marshal`), so the managed surface is exactly the `SfxMeshProbe.LogSummonRoot()` of §6. |

---

## 8. Reconciliation with A1–A5

* **A1** ("`+0x38` = animated world pose; read it per frame"): **CONFIRMED** — the array is
  world-space (§3). B1 adds *why* (the `0x7820` root branch copies `DATA+0x40`) and that the stable
  authoritative read is `DATA+0x40` itself (the `+0x38` base is re-pointed per node).
* **A2 §5** ("root `DATA+0x40` from Draw's (rot,pos) args; bone matrices are bone-space local;
  runtime probe on Draw args or a per-frame `GetSummonBoneMatrix` dump is the only faithful way"):
  root/args **CONFIRMED**; "bone-space local" **CORRECTED to world-space** (bone[0]==DATA+0x40).
  B1 adds that a passive READ of `DATA+0x40` beats hooking Draw's args (no call interception).
* **A3 §0** ("creature transform never crosses the managed boundary; only 2D footprint escapes"):
  TRUE for the P/Invoke boundary; B1 shows the transform is nonetheless live-readable in the DLL's
  address space from managed code (module-base+RVA), which A3's DllImport-only view didn't cover.
* **A4 §0/§6** ("the creature's true per-frame 3D world transform is NOT present anywhere; every
  reproject-the-bounds conclusion is VOID"): the VOID verdict on the MESH/PRIM stream **stands**;
  the absolute "not present anywhere" is **narrowed** — it IS present at `SummonData+0x40`. A4 §7.2
  correctly nominated "the decoded summon-model array" as the candidate; B1 pinpoints `+0x40` and
  gives the validator that A4 said was missing.
* **A5 §6/§7** ("`screen = PROJ·VIEW·(creature world pos)`; both camera matrices live"): B1 supplies
  the missing operand — `creature world pos = SummonData+0x54` (root translation).

---

## 9. Provenance

Read-only static analysis of the user's installed DLL: RVAs, mnemonics, struct offsets, C#
citations, and format-parser pseudocode only. No stock geometry/animation/matrix VALUES extracted
(they are runtime scratch, zero on disk and unread here); no DLL modified or redistributed. The §6
probe sketch reads decoded RUNTIME state into a debug log — never shippable asset bytes.
