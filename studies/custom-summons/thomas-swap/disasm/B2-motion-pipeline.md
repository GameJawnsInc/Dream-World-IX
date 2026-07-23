# B2 — The MOTION + MESH-VISIBILITY pipeline (deep decode)

Slice B2 of the FF9SpecialEffectPlugin.dll (x64) summon-cutscene disasm round. Decodes how a summon
animation ADVANCES and where bone posing happens, and separates the native mesh-hide mechanism from
our managed `.seq HideMeshes` lever. Every claim is cited `fn@rva : ins@rva` (image base
`0x180000000`; RVA = VA − base) or `file:line` for the C# side. Builds on A1/A2 (struct calibration:
base `0x220830`, stride `0x58`, DATA offsets) — all re-verified here by direct disassembly.

Runtime scratch (`0x220830`+ and the DATA block) is zero-on-disk: layouts/update logic are
STATIC-recoverable, VALUES are RUNTIME-ONLY. No geometry/animation bytes extracted; no DLL modified.

---

## 0. TL;DR — the two asks answered

**(1) How does animation advance / where is bone posing?**
`DrawSummonModel` is the per-frame driver and it does BOTH the advance and the pose. The frame
counter `rec+0x54` is **auto-incremented once per Draw call** (`inc word[rdi+0x54]` @`0x17888`), with
a loop/hold clamp at the top of Draw; `Hi_SetSummonMotFrame` is a **seek/override** (`JumpToFrame`),
not the normal advance. Posing is two stages inside each Draw: (a) the **root** 32-B matrix at
`DATA+0x40` is rebuilt every frame from Draw's `(rotPtr,posPtr)` args by the pose-eval `0x186a0`;
(b) the **per-bone** matrices are produced by fn `0x7820`, which **re-points `DATA+0x38` to the
current frame's bone block inside the motion clip** and adds the root-motion accumulators.

**(2) Native mesh-hide vs our `.seq HideMeshes` — SAME or TWO layers?**
**TWO independent layers, different identifier, different stage.** Native `Hi_Hide/ShowSummonModelMesh`
toggles a bit in `DATA+0x20` keyed by the summon model's **ordinal mesh index**, consumed INSIDE the
DLL's Draw loop (`bt [DATA+0x20],meshIdx; jb skip` @`0x17913`) so the mesh's primitives are **never
emitted** (before `SFX_GetPrim` ever sees them). Our authoring `HideMeshes=<keys>` is the **managed
SFXRework** path (`SFXData.preventedMeshKeys/Indices`), keyed by the **SFXKey blend/texture hash** (or
harvest-order ordinal), filtering at **render time AFTER the harvest** (`SFXDataMesh.cs:344`). A third
thing named "HideMesh" (`btl_mot.HideMesh`) is the battler-model subsystem, unrelated to summons.

---

## 1. Frame advance — the exact state machine

### `Hi_SetSummonMotion(idx=edx, motionPtr=rcx)` — body `0x17a10..0x17a61` (Pattern A)
```
rec = 0x220830 + idx*0x58                     ; 0x17a17 imul, 0x17a1b lea → 0x220830
if rec[0x50]==0 or rec[0x00]==0 → error       ; 0x17a25 / 0x17a2f
rec[0x54] = 0                                  ; 0x17a36  (ZERO the frame counter)
DATA[0x10] = motionPtr                          ; 0x17a3b  (bind the motion clip)
```
Binding a new motion resets the frame counter to 0. (`fn@0x17a10`.)

### `Hi_SetSummonMotFrame(idx=ecx, frame=edx)` — body `0x17a70..0x17ad3` (Pattern A) — the SEEK
```
rec = 0x220830 + idx*0x58
if rec[0x50]==0 or rec[0x00]==0 → error
motion    = DATA[0x10]                           ; 0x17a94
frameCount= u16[motion+2]                         ; 0x17a98
if frameCount >= frame:  rec[0x54] = frame        ; 0x17a9e jge → 0x17aac
else:                    rec[0x54] = 0             ; 0x17aa2  (out-of-range seek → rewind)
```
This is an **externally driven seek**, invoked by the `.seq` interpreter (caller `0x10d6a`, A1) — it
is what services `JumpToFrame`/`SkipSequence`-style commands, NOT the per-frame tick.

### `Hi_DrawSummonModel(rotPtr=rcx, posPtr=rdx, arg3=r8, idx=r9d, loopFlag=[rsp+0x60])` — validator `0x17710`, body `0x17740..0x179f2`
The per-frame driver. Order of operations, all in ONE Draw call:

1. **Root pose** — `call 0x186a0` (pose-eval) with `rcx=DATA, rdx=rotPtr, r8=posPtr` (`0x17767`). §3.
2. **Motion fixup** — `rbx = DATA[0x10]` (motion); relocate its packed sub-offsets `[motion+0xc]`,
   `[motion+0x10]` in-place via helper `0x12b00` (bounds `<0x10000`/`<0x100000`) (`0x17776`–`0x177b4`).
3. **Frame clamp / wrap** (`0x177b7`–`0x177de`):
   ```
   frameCount = u16[motion+2]                      ; 0x177c1
   cur        = u16[rec+0x54]                       ; 0x177c5
   if frameCount >  cur:  keep cur                  ; 0x177cb jg → past the clamp
   else if (loopFlag & 1):  rec[0x54] = 0           ; 0x177d4  (LOOP: wrap to 0)
   else:                    rec[0x54] = frameCount-1 ; 0x177de  (HOLD: clamp to last)
   ```
   **`loopFlag` = stack arg bit0 (`[rsp+0x60]&1`, `0x177cd`): set = LOOP, clear = HOLD-last.**
4. **Per-bone pose** — `ebp = u16[rec+0x54]` (the clamped frame, `0x177e9`); resolve the current
   frame's data pointer; `call 0x7820` with `rcx=DATA, edx=ebp(frame)` (`0x1786e`). §4.
5. **ADVANCE** — `inc word[rec+0x54]` (`0x17888`). The frame counter increases by exactly 1 per Draw.
6. **Mesh draw loop** — §5 (consumes the hide mask, emits primitives).

**Conclusion (ask 1a):** the frame counter is **internally advanced by DrawSummonModel, +1 per call**;
Draw is invoked once per rendered frame by the `.seq`/SFX interpreter (`SFX_Update` tick → interp
`0xeea4` → `Hi_DrawSummonModel` call `0xf851`, A1). The `.seq` "drives" the animation only in that it
calls Draw each tick; the increment itself is native. `SetSummonMotFrame` overrides the counter for
seeks. There is **no separate timestep/speed field** — one motion frame per rendered frame, wrap or
hold decided by the per-call `loopFlag`.

---

## 2. `Hi_RegisterSummonModel` — the constructor (what a summon-model record is built from)

Body `0x15ee0..0x1606c` (real work) + finalizer `0x7120` + error stubs `0x16112/0x1612c` (Pattern B).
`RegisterSummonModel(modelArg=rcx→rsi, arg2=rdx→r9)`:

```
slot search: rbx = 0x220830; while rbx[0x50]!=0 { rbx+=0x58; if ++i>=1 → "no free slot" (0x16112) }
                                                ; LENGTH 1 (cmp eax,1; jl @0x15f14) — single summon slot
if rbx[0x00]==0 → error 0x1612c                  ; DATA must be pre-allocated (battle init @0x30cc9, A2)
rbx[0x50] = 1                                     ; 0x15f27  active
rbx[0x54] = 0                                     ; 0x15f2e  frame counter
DATA[0x08] = u32[rsi+0x3c]                          ; 0x15f3f  modelId / packed model-geom address
DATA[0x10] = reloc(u32[rsi+0x180])                  ; 0x15fc6  INITIAL motion ptr (PSX addr-fixup 0x15f42..)
rbx[0x51]  = (arg2 != 0)                            ; 0x15fcd  a bool flag from the 2nd arg
boneCount  = s16[rsi+4]                              ; 0x15fd0 / loop bound 0x1604f
  for b in 0..boneCount:  copy per-bone shorts       ; loop 0x16000..0x16065 (3 src arrays @rsi+0x18/+0x24/+0x30)
                          into a stack buffer + scratch, later consumed by 0x7120
call 0x7120(DATA, rbx+8, &stackBuf)                  ; 0x16078  the DATA-block INITIALIZER (§2.1)
DATA[0x70] = reloc(u32[rsi+0x40])                    ; 0x160f5  TEXANIM array ptr (PSX addr-fixup)
```

So a "summon-model record" is constructed from the managed **model arg** (`rsi`) fields:
`+0x04` = **bone count**, `+0x24…` = per-bone table (3 short-arrays), `+0x3c` = model-geom packed
address, `+0x40` = texanim-array packed address, `+0x180` = **initial motion** packed address.
`SetSummonMotion` can later REBIND `DATA+0x10` to a different motion.

### 2.1 `0x7120` — the DATA-block initializer (`0x7120..0x7240`)
Called with `rcx=DATA`. It (a) resolves `DATA[0x08]` (the packed model-geom address) to a real pointer
via the same PSX addr-fixup, (b) **zeroes the mutable per-frame fields**, (c) parses the TMD/model
(`call 0x12940`, the model-primitive walker):
```
DATA[0x28] = rec+8                                  ; 0x71d9
DATA[0x20] = 0                                       ; 0x7217  hideMask CLEARED → all meshes visible
DATA[0x38] = 0                                        ; 0x71f7  bones ptr cleared (re-pointed per frame, §4)
DATA[0x18] = 0 ; DATA[0x70]=0 ; DATA[0x30]=0 ; DATA+0x7c=0x1000 ; DATA+0x78=0x10001000 ; DATA[0]=0
```
**`DATA+0x20` (hideMask) starts all-clear at register time** — every model mesh visible until a Hide.

---

## 3. Root world transform — pose-eval `0x186a0` (verifies A2 §5)

Called first in every Draw with `rcx=DATA, rdx=rotPtr, r8=posPtr`. Builds a 32-B PSX MATRIX at
`DATA+0x40`:
```
rbx = DATA+0x40                                    ; 0x186b2
seed default:  [rbx]=0x1000, [rbx+6]=[rbx+0xe]=0x10000000, [rbx+4]=0, [rbx+0xa]=0   ; 0x186ca..0x186de
if rotPtr!=0:  RotMatrixX(s16[rotPtr+4]) 0x3910 → RotMatrixY(s16[rotPtr]) 0x37a0
               → RotMatrixZ(s16[rotPtr+2]) 0x3850   ; 0x186ef..0x18729   (3×3 into DATA+0x40..0x51)
if posPtr!=0:  [rbx+0x14]=s32[posPtr]; [rbx+0x18]=s32[posPtr+4]; [rbx+0x1c]=s32[posPtr+8]  ; 0x18738..0x18749
               (→ DATA+0x54/0x58/0x5c translation)
```
The root pose is **recomputed each frame from the `(rot,pos)` arguments** — it is NOT persisted between
frames. Those args are runtime data sourced from the SFX sequence / camera anchor (A4/A5): the creature's
true world placement is **runtime-only**; statically we recover only the layout + that the inputs are
Draw arguments. (rotPtr slot order: `+0`=Y, `+2`=Z, `+4`=X angle, s16 each; minor, matches the RotMatrix
call order.)

---

## 4. Per-bone pose — fn `0x7820` (`0x7820..0x7a31`, 529 B): the animated skeleton

Called per Draw with `rcx=DATA, edx=frameIndex(bp), r8=frameDataPtr(r13)`.

```
motion = DATA[0x10]                                 ; 0x7838
DATA[0x38] = r8   (= this frame's bone block)        ; 0x7842   << RE-POINTS the bone-matrix array
...
rootBone = u8[DATA+4]                                ; 0x7860 / 0x7898   (root/base bone index)
src = DATA[0x38] + rootBone*0x20                     ; stride 0x20 (PSX MATRIX)
copy src rot(+0..+0xc) and trans(+0x10..+0x1c) into DATA[0x38][0]   ; 0x7868..0x78cf
mirror rot/trans into globals @0x211f40.. and call 0x40d0 (compose) ; 0x78d3..0x7921
add root-motion accumulators: DATA[0x38][0].t += (@0x211fe4,@0x211fe8,@0x211fec)  ; 0x795a/0x7965/0x796c
```

**Key refinement of A1/A2:** `DATA+0x38` (`bones`) is **NOT a fixed allocation** — each frame fn `0x7820`
sets it to a pointer INTO the motion clip's current-frame bone block (stride-0x20 PSX `MATRIX` per bone).
So `Hi_GetSummonBoneMatrix(idx,bone,out)` / `Hi_GetSummonBonePos` read whatever the LAST Draw pointed
`DATA+0x38` at — i.e. the pose for the frame just drawn. The array is re-based every frame; the root
bone additionally accumulates root motion (globals `0x211fe4/e8/ec`, runtime scratch). This is where
the "animated pose" physically lives at runtime, and confirms A1 §4's per-frame read target:
`[[0x220830+idx*0x58]+0x38] + bone*0x20`, translation at `+0x14/+0x18/+0x1c`.

The individual PSX `MATRIX` structs are the classic GTE form: `s16 m[3][3]` (+0, fp12 /4096) · `s16 pad`
(+0x12) · `s32 t[3]` (+0x14/+0x18/+0x1c). `Hi_GetSummonBonePos` returns the low 16 bits of each `t`.

---

## 5. The mesh-visibility mask — native layer (`DATA+0x20`)

### Toggles
`Hi_ShowSummonModelMesh(idx=ecx, meshIdx=edx)` `0x187e0`: `eax=~(1<<meshIdx); DATA[0x20] &= eax`
(`0x1880e`) → **clear bit = VISIBLE**.
`Hi_HideSummonModelMesh(idx=ecx, meshIdx=edx)` `0x18840`: `DATA[0x20] |= (1<<meshIdx)` (`0x1886c`)
→ **set bit = HIDDEN**. `u32` ⇒ up to 32 model meshes.

### Consumption — the Draw mesh loop (`0x17900..0x179c6`)
```
meshCount = u8[modelGeom+3]                          ; 0x17900
for ebx in 0..meshCount:
    eax = DATA[0x20]                                  ; 0x17913
    if bt(eax, ebx):  continue  (SKIP — mesh HIDDEN)  ; 0x17916 bt / 0x17919 jb → 0x179c2 (inc)
    call 0x4eb0(edx=meshIdx)     ; per-mesh pose prep
    ... resolve frame data ...
    call 0x56c0(rcx=DATA, edx=meshIdx)  ; EMIT this mesh's PSX primitives  ; 0x179a8
    call 0x12940
```
The hide bit index **IS the ordinal mesh index** within the summon model's mesh list (0..meshCount−1,
`meshCount = byte[modelGeom+3]`). A set bit means the loop **skips primitive emission entirely** for
that mesh — the polys never enter the ordering table and never reach `SFX_GetPrim`. Cheap, side-effect
free (no state beyond the bit).

### Reachable from the native `.seq` (ef###.bytes)
The interpreter has an opcode that calls each: Show `call 0x187e0` @`0x117df`, Hide `call 0x18840`
@`0x11806`. Both first fetch two operands from the current `.seq` command via `0x126c0` (the
operand-slot reader: `cmd = ctx[0xd0c + cmdIdx*0x80]`, selector `edx∈{0,1}`) — `ecx=summonIdx`,
`edx=meshIdx`. So a `.seq` program CAN hide/show the creature's model meshes by ordinal index natively.

---

## 6. Managed `HideMeshes` — the OTHER layer (SFXRework)

Our authoring lever is entirely managed and does NOT touch `DATA+0x20`.

**Parse** (`Memoria/Battle/SFX/UnifiedBattleSequencer.cs:366`):
`code.TryGetArgMeshList("HideMeshes", out meshKeyList, out meshIndexList)` — `HideMeshes=` yields two
lists: hex **mesh KEYS** and plain ordinal **indices**. Fed to `sfx.PlaySFX(...)` (`:368`), which builds
a `RunningInstance` (`SFXData.cs:1383-1391`): `preventedMeshKeys = HashSet(keys)`,
`preventedMeshIndices = indices`, `meshKeyList = new()`.

**Consumption — two managed sub-paths, both in `SFXDataMesh.Render`:**
- *Harvested primitive meshes* (`SFXDataMesh.cs:334-346`): as each unique `EffectMaterial.meshKey`
  (an **SFXKey hash** of ABR/texture/tpage/blend state) is first seen, its **harvest-order ordinal**
  `meshKeyList.Count` is matched against `preventedMeshIndices` → its key is added to
  `preventedMeshKeys`; then `if (preventedMeshKeys.Contains(key)) continue;` (`:344`) skips the
  mesh's `Render` — AFTER `SFX_GetPrim` already returned those primitives.
- *Custom FBX ModelSequences* (`SFXDataMesh.cs:796-807`): `model[modelIndex]` skipped when
  `modelIndex ∈ preventedMeshIndices` (or its `key` already in `meshKeyList`). This is the net-new
  SFXChannel/FBX path (e.g. a rung-7 Thomas FBX).

### 6.1 The two layers, side by side
| axis | NATIVE `DATA+0x20` (`Hi_Hide/ShowSummonModelMesh`) | MANAGED `preventedMesh*` (`HideMeshes=`) |
|---|---|---|
| identifier | **ordinal mesh index** in the summon MODEL (`u8[geom+3]` meshes) | **SFXKey hash** of blend/tex state, OR harvest-order ordinal / FBX model index |
| stage | inside the DLL, skips primitive **EMISSION** (before `SFX_GetPrim`) | managed, skips **RENDER** after the `SFX_GetPrim` harvest |
| storage | `u32` bitmask in the DATA block | `HashSet<u32>` keys + `List<u32>` indices per RunningInstance |
| driven by | native `.seq` opcode inside `ef###.bytes` (interp `0x117df/0x11806`) | Memoria `BattleActionCode` `HideMeshes=` arg (managed) |
| precision | exact 1 bit ↔ 1 model mesh, stable | a KEY can span multiple model meshes; index mode depends on harvest order |
| cost | polys never generated | polys generated + harvested, then discarded |

**A third, unrelated "HideMesh":** `btl_mot.HideMesh(BTL_DATA, mesh, isVanish)` (`FF9/btl_mot.cs:835`,
callers `btlseq.cs:728`, `SFX.cs:1259`, `VanishStatusScript.cs`) operates on a **battler**'s model mesh
mask (`BTL_DATA.mesh_current/mesh_banish`) — Vanish/banish/trance-swap. It has nothing to do with the
summon creature or the SFX plugin; do not conflate.

### 6.2 Implication for authoring precise creature part hide/show
- The lever we use today (`HideMeshes=<hex keys>`) is the MANAGED layer: it groups the harvested
  Bahamut primitives by SFXKey and drops the chosen keys at render. It worked for "hide the 7 body
  meshes" because those bodies hash to distinguishable keys — but a KEY groups by blend/texture state,
  so it is coarser than per-model-mesh and the index mode is fragile (harvest-order dependent).
- The NATIVE `Hi_HideSummonModelMesh` is **more precise and cheaper**: exact per-model-mesh ordinal,
  stable, and it prevents emission (the polys never cost harvest/render). It is **already reachable
  from `ef###.bytes`** via the interpreter opcode (§5) — so the way to hide/show native creature parts
  precisely is to **emit that native Show/Hide `.seq` opcode into the effect's byte stream** (operands:
  summonIdx=0, meshIdx=ordinal), rather than relying on the managed key filter. Identifying the exact
  opcode NUMBER (the interpreter dispatch case that lands at `0x117df`/`0x11806`) is the concrete next
  step to productize this — the call sites and operand reader (`0x126c0`) are pinned above.

---

## 7. Texanim + Abr/RGB (completeness; verifies A2 §6/§7)

- `Hi_StartSummonTexAnim(idx=ecx, partIdx=edx, mode=r8b)` `0x188a0`: `tex = DATA[0x70] + partIdx*0x18`;
  `tex[8] |= (mode? 3 : 1)` (`0x188dc`/`0x18906`), `tex[0x10]=0` (timer), `tex[0x16]=0x1000` (scale 1.0).
- `Hi_StopSummonTexAnim` `0x18930`: `tex[8] &= 0xFC` (clear both enable bits).
- `Hi_ModifySummonModelAbr(idx=ecx, abr=edx)` `0x18af0`: `abr==0xFF` = no-op sentinel (`0x18af7`);
  else guards + `shl dx,5` and **tail-jmp `0xc880`** (shared mesh semi-transparency applier, `rcx=DATA`).
- `Hi_ModifySummonModelRGB` `0x18b50`: guards + tail-jmp `0x83d0` (shared RGB applier).
These are per-mesh appearance modifiers over the DATA mesh list; they add no new record fields.

---

## 8. Cite index / next steps

Native (DLL): SetSummonMotion `0x17a10`; SetSummonMotFrame `0x17a70`; DrawSummonModel body `0x17740`
(clamp `0x177c1-0x177de`, per-bone call `0x1786e`, advance `inc 0x17888`, mesh loop `0x17900-0x179c6`,
hide test `bt 0x17913`); pose-eval `0x186a0`; per-bone pose `0x7820` (bones re-point `0x7842`);
Register `0x15ee0` (boneCount `s16[rsi+4]`, initial motion `[rsi+0x180]`, texanim `[rsi+0x40]`);
DATA init `0x7120` (hideMask clear `0x7217`); Show `0x187e0`/Hide `0x18840`; interp opcodes
`0x117df`/`0x11806`; operand reader `0x126c0`.
Managed (C#): `UnifiedBattleSequencer.cs:366` (parse), `SFXData.cs:1373-1392` (RunningInstance),
`SFXDataMesh.cs:334-346` (primitive filter), `SFXDataMesh.cs:796-807` (FBX filter),
`btl_mot.cs:835` (unrelated battler HideMesh).

**Next steps flagged:** (a) identify the native `.seq` opcode NUMBER for Show/Hide (interpreter
dispatch case → `0x117df/0x11806`) to expose precise per-model-mesh hide from authoring; (b) the
runtime VALUES of `DATA+0x38`/`+0x40`/`+0x54` remain the only faithful source of the creature's true
per-frame transform — read via a `Hi_GetSummonBoneMatrix` probe or a Draw-arg hook (A1/A2/A4/A5).

Provenance: read-only static analysis (RVAs, mnemonics, struct offsets) of the user's installed DLL +
open Memoria C# source. No stock geometry/animation bytes extracted; no DLL modified.
