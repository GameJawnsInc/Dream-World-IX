# B3 — Hi_DrawSummonModel → the PSX primitive stream (the mechanical backbone)

How a summoned creature's geometry becomes the already-projected 2D primitives that
`SFX_GetPrim` hands to managed code. This slice decodes the **draw → project → emit** pipeline
inside `FF9SpecialEffectPlugin.dll` (x64, image base `0x180000000`; VA = RVA + base), connects it
to A4's "primitives are screen space" verdict from the DLL side, and states exactly where a
creature transform can and cannot be recovered.

Every claim is `fn@rva : ins@rva`. Runtime `.bss`/scratch values are zero-on-disk and flagged
RUNTIME-ONLY; only layout + logic are static.

---

## 0. Headline (one paragraph)

`Hi_DrawSummonModel` (@`0x17710`) drives a **software PSX GTE**. It builds the creature's root
matrix from its `(rot,pos)` arguments, walks the model's meshes, and for every vertex runs a real
**GTE RotTransPers** — matrix-multiply (`>>12`) then a **perspective divide `q=(H<<16)/SZ`** (integer
`idiv` @`0x4001b`) — writing final **screen-pixel** `(x,y)` into a per-vertex array `@RVA 0x2191a0`
and an ordering-table depth into `@RVA 0x212440`. It then assembles PSX primitive packets whose
`x0,y0` are those screen pixels and whose OT bucket is `(Σ per-vertex otz)>>6`, and links them into
the ordering table that `SFX_GetPrim` later walks. **The projection is done, and the camera zoom/pan
is folded in, entirely inside the DLL. The primitives that escape are screen space; the creature's
world/view transform is consumed at the perspective divide and never reaches the primitive stream.**
This confirms A4 §0 from the native side and pins the mechanism.

---

## 1. `Hi_DrawSummonModel` body — the control flow (@`0x17710..0x179f2`)

Signature (recovered from the prologue): `Draw(arg0=rcx, arg1=rdx, arg2=r8, idx=r9d, loopBit=[rsp+0x60]&1)`.
The record index is the **4th** arg (`r9d`), not `rcx`.

```
0x17716  movsxd rax,r9d ; imul rdi,rax,0x58 ; add rdi,0x220830   ; rdi = &summonRec[idx]
0x1772a  cmp byte[rdi+0x50],0 ; je stub                          ; active gate (A1/A2 +0x50)
0x17734  mov rcx,[rdi] ; test; je stub                           ; DATA ptr (rec+0x00)
--- body @0x17740 ---
0x17767  call 0x186a0            (rcx=DATA, rdx=arg0, r8=arg1, r9=arg2)   ; §2 POSE EVAL -> DATA+0x40 root
0x17776  rbx=[DATA+0x10] motion ; call 0x12940 ; VA-fix motion offA/offB via 0x12b00 ; §5 fixups
0x177bd  frameCount=[motion+2] ; frame=[rec+0x54] ; clamp/loop-or-hold on loopBit ; write [rec+0x54]
0x177e2  G=[rip+0x4f47f](=[0x1c7268]) ; r12=0x5789e8 ; ebp=frame
0x1786e  call 0x7820            (rcx=DATA, edx=frame, r8=matbuf<-decode[G+0x24]) ; §3 ROOT EMIT
0x1787e  [G+0x24]=eax           ; advance OT/matrix write cursor
0x17888  inc word[rec+0x54]     ; frame++ for next call
0x1788c  [DATA+0x18]=0
0x17896  meshTbl = decode([DATA+0x08]) ; meshCount = byte[meshTbl+3]      ; §4 mesh list
0x17910  LOOP i in [0,meshCount):
0x17913     if bt([DATA+0x20], i): continue          ; hide-bit (Hi_HideSummonModelMesh mask)
0x17922     call 0x4eb0          (rcx=DATA, edx=i)    ; §6a per-mesh matrix compose
0x179a8     call 0x56c0          (rcx=DATA, edx=i, r8=decode[G+0x24])  ; §6b set GTE globals + EMIT
0x179b8     [G+0x24]=eax                              ; advance OT cursor
```

`G` = the SFX draw context pointer `@[0x1c7268]`; `G+0x24` = the current ordering-table / matrix
write cursor (a **packed VA handle**, resolved through the 0x80/0xc00000 decode blocks that appear
~15× in this subsystem). The two emit calls (`0x7820` root, `0x56c0` per-mesh) each return the
advanced cursor.

---

## 2. Pose evaluator `0x186a0` — builds the ROOT matrix at DATA+0x40

(`.pdata` splits this into a 24-byte head; the real body runs contiguously to `0x186a0..0x187d7`.)
Args: `rcx=DATA, rdx=rot, r8=pos, r9=optMtx`.

```
0x186b2  rbx = DATA+0x40                      ; the 32-B PSX MATRIX destination (root)
0x186ca  seed identity: m00=m11=m22=0x1000 (1.0 in 1/4096), off-diагs 0
0x186ef  if rot: RotMatrix chain              ; ecx=word[rot+4]->0x3910 ; word[rot+0]->0x37a0 ; word[rot+2]->0x3850
                                              ;   (three GTE RotMatrix builders compose the 3x3 into DATA+0x40)
0x18738  if pos: t[0..2]=[pos],[pos+4],[pos+8] -> DATA+0x54/0x58/0x5c   ; i32 translation
0x18763  if optMtx: build a MATRIX from word[optMtx +0/+4/+8] on a 0x1000 diagonal template,
0x1879d           call 0x3b60 (MulMatrix)  -> root = optMtx · root       ; fold the extra orientation in
0x187b2  else: DATA+0x78 = (0x1000,0x1000,0x1000) scale default ; call 0x5560
```

So **root(DATA+0x40) = RotMatrix(rot) [ ·optMtx ] , translation = pos**. It is **recomputed every
Draw from the caller's arguments** — not persisted between frames (A2 §5 confirmed). `optMtx`
(pose-eval `arg2` = Draw `arg2`) is a caller-supplied 3-short orientation multiplied into the root;
its provenance (camera view vs a scripted tilt) is the one residual — see §8.

RotMatrix `0x3910/0x37a0/0x3850` and MulMatrix `0x3b60` are the DLL's GTE-emulation matrix ops
(the same family the projection reads); they write the shared GTE matrix region `@0x211f40`
(`xrefs_to 0x211f40` shows `0x3b60@0x3b72`, `0x2030@0x20f3`, etc.).

---

## 3. Root emit `0x7820` — installs the bone-matrix buffer + root bone (@`0x7820..0x7a31`)

Args: `rcx=DATA, dx=frame, r8=matbuf`.

```
0x7842  [DATA+0x38] = r8            ; INSTALL the working bone-matrix array ptr (A1/A2 DATA+0x38 = bones)
0x7846  r14=[DATA+0x10] motion ; if motion != 0 -> 0x7a20 (animated path: sample clip at frame)
        else (static): copy parent pose from [DATA+0x30]+0x38 into bone[byte[DATA+4]]
0x78d3  copy the resulting 3x3 (bone[k]+0..0x10) into GTE globals @0x211f40 region
0x7904  [DATA+0xa0/0xa4] scale -> globals ; call 0x40d0 (GTE compose) ; add translation back
```

`0x7820` is where **DATA+0x38 (the per-bone matrix array) is set and its root entry filled**; the
animated branch `0x7a20` samples the motion clip (frame counter `rec+0x54`) — this is the array
`Hi_GetSummonBoneMatrix`@`0x18630` reads. The values are RUNTIME-ONLY (DATA is zero-on-disk scratch).

---

## 4. The mesh list + the per-mesh descriptor

`meshTbl = decode([DATA+0x08])` (DATA+0x08 = the packed geometry-table handle written at
`RegisterSummonModel@0x15f3f`). `meshCount = byte[meshTbl+3]` (`Draw@0x17900`). The engine indexes
mesh descriptors at **stride 0x28 (40 B)**: `emit@0x58fe : lea rcx,[rax+rax*4]; lea r8,[rdx+rcx*8]`
(= `rdx + i*0x28`); descriptor `+0x20` = the packed handle of mesh i's primitive/geometry list
(`emit@0x590b`). Per-mesh hide is `bt [DATA+0x20], i` (`Draw@0x17916`) — the `Hi_HideSummonModelMesh`
`HideMeshes` bitmask (A2 §2).

---

## 5. The VA-fixup layer (`0x12940`, `0x12b00`) — resource relocation, NOT geometry

The model/motion sub-tables are stored as **packed 32-bit VA handles**. Two utilities against the SFX
resource heap context (`r15 = [rip+0x55f29a] = 0x570a10` in Draw):
- `0x12b00(ctx, va)` : linear-search `ctx+0x10` range table (count `ctx+0x1fc0`, stride 0x20) → emit a
  packed handle `0x80…`/`0xc00000…` (§6 decode is the inverse). `resolve_12b00@0x12b0a..0x12bb9`.
- `0x12940(ctx, va)` : companion relocation (early-out to a printf-warn pair if `va==0`).

The recurring inline block `shr edx,0x18; cmp 0x80; …; and 0x3fffff; add [rax+base+8]` (seen ~15×)
is the **handle→pointer decoder**: top byte selects a heap band, low bits are the offset. It moves
pointers around; it performs **no coordinate math**.

---

## 6. The projection + emit engine (`0x56c0` → `0x58f9`/`0x4ff9`)

### 6a. `0x4eb0` (per-mesh compose) — @`0x4eb0..0x4ff9`
Loads `meshTbl=decode([DATA+0x08])`, a per-mesh sub-table `decode([meshTbl+0x10])` (stride 0x28),
and `bones=[DATA+0x38]`, then composes the mesh's working matrix from the bone matrices and stores it
where `0x56c0` reads it. (Vertices carry a per-vertex bone index — the transform is **skinned**, §6c.)

### 6b. `0x56c0` (set GTE state, then fall into the engine) — @`0x56c0..0x58f9`
Copies the mesh's composed matrix into the **emulated PSX-GTE global registers**:
- rotation 3×3 → `@0x211f40` (`0x576f..0x5794`, five stores of the 18-byte matrix)
- translation → `@0x211f54` (`0x57fd..0x5812`)

then falls through into the 6 KB engine at `0x58f9` (mesh descriptor stride 0x28; `[DATA+0x20]` bit4
= a cull/skip early-return at `0x581c`). **These are exactly the globals the projection reads** (§6d),
and they are set from the *model* matrix, per mesh, immediately before drawing.

### 6c. The projection pass `0x4ff9` (@`0x4ff9..0x5544`) — fills the SXY / OTZ arrays
For each vertex `idx` (r13):
```
0x50f6  &OTZ = 0x212440 + idx*4        ; per-vertex OT-depth array
0x50fe  &SXY = 0x2191a0 + idx*4        ; per-vertex SCREEN-XY array
0x509d  bone = word[boneIdxTbl + …]    ; per-vertex bone index (skinning)
0x51fa  call 0x3b60 (MulMatrix)        ; compose bone[bone] · base -> GTE matrix @0x211f40
        call 0x3d60 / 0x3e80           ; RotTrans + perspective (§6d)  -> writes GTE result regs
        store result -> SXY[idx], OTZ[idx]
```
`calls 0x3b60, 0x3d60, 0x3e80` confirmed by scan of `0x4ff9`.

### 6d. `0x3e80` — the GTE **RotTransPers** (perspective divide) — @`0x3e80..0x40c1`
Input: a vertex register `V[ecx]` from the GTE vertex bank `@0x211fc0` (stride 8; V0/V1/V2).
```
view.X = (R00·vx + R01·vy + R02·vz) >>12 + TRX     ; R @0x211f40, TRX @0x211f54 (set by 0x56c0)
view.Y, view.Z likewise                            ; clamped to i16 [-0x8000,0x7fff]
SZ     = clamp(view.Z, 0..0xffff)
q      = (H << 16) / SZ                             ; H @0x211fa8 ; idiv @0x4001b  <-- PERSPECTIVE DIVIDE
screenX = (view.X · q) >>16 + OFX                  ; OFX @0x211fa0 ; clamp [-1024,1023]
screenY = (view.Y · q) >>16 + OFY                  ; OFY @0x211fa4 ; clamp [-1024,1023]
OTZ     = (q · hz) >>12                             ; clamp [0,0xfff]
store: SXY0 @0x211ff8 (x|y<<16), OTZ0 @0x211fe0     ; GTE result regs, then copied to the arrays (§6c)
```
This is a byte-faithful software `RTPS/RTPT`: matrix-multiply, `/z` perspective, screen offset, depth
bucket. **The `H`, `OFX`, `OFY` screen registers are the camera's** (H = the near-Z/zoom that A5 §3
tracks; OFX/OFY = pan). They are written by the camera path, not by the summon code (§7).

### 6e. Primitive assembly (`emit@0x58f9`, inner loop `0x5b30..`)
Per face, from the source packet at `rsi`:
```
0x5b3a  v0=word[rsi] ; v1=word[rsi]>>16 ; v2=word[rsi+4]      ; vertex indices (bounds-checked < 0x1b58)
0x5bc2  xy0 = SXY[v0] ; xy1 = SXY[v1] ; xy2 = SXY[v2]         ; already-projected SCREEN coords @0x2191a0
0x5c7e  prim+8 = xy0 ; prim+0x10 = xy1 ; prim+0x18 = xy2      ; PSX P_TAG packet (xy at +8/+0x10/+0x18)
0x5c8b  prim+7 = code 0x2c (POLY_FT4)                          ; C# reads prim+8 as Int16 x0,y0
0x5ca1  otz = (OTZ[v0]+OTZ[v1]+OTZ[v2]+OTZ[v3]) ; sar 6       ; OT bucket = Σotz >>6 ; clamp ≥0 @0x5df2
        + UV/color/tpage from @0x212440 (uv) / @0x2191a0 companions ; link packet into the OT at otz
```
The 34 `call qword ptr [rip+0x44xxx]` sites in the engine are all **one bounds-check assert**
(`cmp idx,0x1b58; call assert@0x4e398`, `r8d`=source line) — not GTE, not projection. There is **no
inline divide in the engine**; all projection lives in `0x3e80`.

---

## 7. The camera relationship (why the world transform is lost)

- The summon draw functions (`0x17710`, `0x186a0`, `0x7820`, `0x4eb0`, `0x56c0`, `0x4ff9`) have
  **zero references to the camera struct** `curCam@0x69730` (`xrefs_to 0x69730` = the camera body
  `0x1e80`, reset `0x2300`, init `0x13c4/0x13540`, alloc `0x30c20` — no draw fn).
- The camera reaches the creature purely through **shared GTE state**: the camera-animation stepper
  `FUNC 0x2030` and init `FUNC 0x13c4` write the rotation matrix `@0x211f40` (`xrefs_to` shows
  `0x2030@0x20f3`, `0x13c4@0x1513`) and the projection register `H@0x211fa8` (`0x13c4@0x1542`), which
  `0x3e80` consumes. Per mesh, `0x56c0` overwrites `@0x211f40` with the *model* matrix, so the
  creature's on-screen **orientation** rides the model/`optMtx` matrix while its **zoom + pan** ride
  the camera's `H/OFX/OFY`.
- Net: at `0x3e80` the perspective divide collapses (view.X, view.Y, view.Z) → 2 screen pixels + 1
  depth bucket. **The metric transform is consumed there.** Everything downstream (`SXY@0x2191a0`,
  the primitive packets, `SFX_GetPrim`, the probe `PRIM` rows) is screen space. This is the DLL-side
  proof of A4 §0.1 and A3 §0.1: the creature transform never reaches the primitive stream.

---

## 8. Where the transform IS recoverable (tracking)

Upstream of `0x3e80`, two runtime structures hold the creature pose **before** the perspective
divide, both RUNTIME-ONLY (DATA is zero-on-disk) but with a static access path:

1. **DATA+0x40 root** = `RotMatrix(rot)[·optMtx] + trans(pos)` — the `(rot,pos,optMtx)` **arguments to
   `Hi_DrawSummonModel`** (rebuilt every Draw by `0x186a0`). A runtime probe capturing Draw's
   `arg0/arg1/arg2` records the root placement inputs directly.
2. **DATA+0x38 bone[k]** = per-bone GTE MATRIX (rot 3×3 i16 /4096 + i32 trans), filled by `0x7820`
   from the motion clip at `rec+0x54`. `Hi_GetSummonBoneMatrix(idx,k,&out)@0x18630` copies it whole;
   `Hi_GetSummonBonePos@0x185b0` gives just translation. A per-frame call (or a hook right after the
   `0x7820`/mesh loop) yields the animated pose.

**Residual (the one open item):** whether these matrices are **model space** or already **view
space** turns on `optMtx` (pose-eval `arg2`, folded via MulMatrix `0x3b60`). If the sequencer passes
the camera view as `optMtx`, DATA+0x40/DATA+0x38 are view-space; if it passes a scripted tilt (or
nothing), they are model space with the camera applied only as `H/OFX/OFY` at projection. Settling it
needs the **interpreter call-site `0xf851`** argument trace (what `arg2` is loaded from) — a next-step
item, not resolvable from the draw bodies alone. Either way these matrices are **pre-perspective and
free of the camera zoom/pan** (`H/OFX/OFY` enter only at `0x3e80`), so pairing them with the logged
VIEW/PROJ (A3/A5) places a replacement puppet without touching the primitive stream.

---

## 9. The exact space ladder (the asked-for relationship)

```
ef###.bytes model vertex  (i16 SVECTOR, model space)
   │  loaded into GTE vertex bank @0x211fc0 (V0/V1/V2)
   ▼  0x3e80: view = (R·v)>>12 + T          R@0x211f40, T@0x211f54  (R = bone·root·… set by 0x56c0)
view-space (SX,SY,SZ) int  (camera orientation via shared 0x211f40; NOT read from curCam by draw)
   ▼  0x3e80: q=(H<<16)/SZ ; x=(SX·q)>>16+OFX ; y=(SY·q)>>16+OFY    H@0x211fa8, OFX/OFY@0x211fa0/a4  (CAMERA)
screen-space (x,y) pixels  clamp[-1024,1023]  +  otz=(q·hz)>>12  clamp[0,0xfff]
   ▼  0x4ff9: store -> SXY[idx]@0x2191a0 , OTZ[idx]@0x212440
   ▼  0x58f9: gather 3-4 verts -> P_TAG packet (prim+8/+0x10/+0x18 = xy0/1/2, code@+7),
   ▼          face otz bucket = (Σ OTZ[idx])>>6 ; link into ordering table (cursor G+0x24)
   ▼  SFX_GetPrim(ref otz) walks the OT -> returns packet ptr + otz         (A3 §6)
   ▼  C# SFXMesh: vert = (x0+drOffsetX, y0+drOffsetY, GzDepth=-otz)         (A4 §2, SFXMesh.cs:340)
probe PRIM row: x = screen px , y = screen px , otz = OT bucket             (A4 §5)
```

**Are the emitted primitives GTE-projected already? YES — inside the DLL, at `0x3e80` (idiv
@`0x4001b`), before anything crosses P/Invoke.** The probe's `PRIM.x,PRIM.y` are the `SXY@0x2191a0`
screen pixels; `PRIM.otz` is the `(Σ OTZ)>>6` bucket. The creature's world transform is upstream at
DATA+0x40 / DATA+0x38 and must be read there (runtime), never reconstructed from primitives.

---

## 10. Function ledger (this slice)

| rva | role | key evidence |
|-----|------|--------------|
| `0x17710` | Hi_DrawSummonModel body | validator + pose+frame+mesh-loop driver |
| `0x186a0` | pose evaluator → DATA+0x40 root | `lea rbx,[rcx+0x40]`; RotMatrix chain; MulMatrix `0x3b60` |
| `0x7820` | root emit; installs DATA+0x38 bone buffer | `[DATA+0x38]=r8@0x7842`; motion branch `0x7a20` |
| `0x4eb0` | per-mesh matrix compose (skinned) | reads `[DATA+0x38]` bones, mesh sub-table stride 0x28 |
| `0x56c0` | set GTE globals from model matrix → engine | writes `@0x211f40` rot / `@0x211f54` trans |
| `0x58f9` | 6 KB mesh/primitive engine | SXY gather `@0x2191a0`; packet build; OT bucket |
| `0x4ff9` | projection pass (per-vertex) | writes `SXY@0x2191a0` / `OTZ@0x212440`; calls `0x3e80` |
| `0x3e80` | GTE RotTransPers (perspective divide) | `idiv @0x4001b`; H`@0x211fa8`, OFX/OFY`@0x211fa0/a4` |
| `0x3910/0x37a0/0x3850` | GTE RotMatrix builders | pose-eval angle compose |
| `0x3b60` | GTE MulMatrix | pose-eval optMtx fold + per-vertex bone compose |
| `0x12940/0x12b00` | VA handle ↔ pointer relocation | resource heap `@0x570a10`; no coord math |
| `0x4e398` | bounds-check assert (the 34 indirect calls) | `cmp idx,0x1b58; call` — not GTE |

### Global data (RUNTIME-ONLY values; static layout)
| rva | role |
|-----|------|
| `0x220830` | summonRec[1] (stride 0x58) — A1/A2 |
| `0x211f40` | GTE current rotation matrix (3×3 i16) — set by `0x56c0`/camera stepper `0x2030` |
| `0x211f54` | GTE translation (TRX/TRY/TRZ) |
| `0x211fa8 / 0x211fa0 / 0x211fa4` | GTE projection H / OFX / OFY (the camera's zoom+pan) |
| `0x211fc0` | GTE input vertex bank (V0/V1/V2, stride 8) |
| `0x211fe0 / 0x211ff8` | GTE result regs (OTZ0 / SXY0) |
| `0x2191a0` | per-vertex **screen-XY** array (u32 x|y<<16) — the projected result |
| `0x212440` | per-vertex **OTZ** array (u32 depth bucket) |
| `[0x1c7268]` | SFX draw context `G`; `G+0x24` = OT/matrix write cursor (packed handle) |
| `0x69730` | curCam (camera struct) — **never referenced by the summon draw path** |

## 11. Provenance
Read-only static analysis of the user's installed DLL: RVAs, mnemonics, struct offsets, control flow,
and cross-references to the open-source Assembly-CSharp / prior A-slices. No creature geometry or
animation bytes extracted; no DLL modified. All DATA/bone/matrix VALUES are runtime scratch
(`0x220830`, `0x211f40`, `0x2191a0`, etc. are zero on disk); only layout + logic are recovered.
