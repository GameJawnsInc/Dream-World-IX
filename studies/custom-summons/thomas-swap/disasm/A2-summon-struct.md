# A2 — The Summon Model Struct + Globals

Slice A2 of the FF9SpecialEffectPlugin.dll (x64) disasm round. Decodes the summon-model
record array (base RVA `0x220830`, stride `0x58`), its nested DATA block, the MOTION /
BONE-MATRIX / TEXANIM sub-blocks, the array length, and the mesh-visibility mask.

All RVAs are image-relative (`load()` base `0x180000000`); addresses printed by capstone as
`0x180xxxxxx` = RVA `0xxxxxxx`. Every claim is cited by `fn@rva : ins@rva`.

---

## 0. Function roster (real bodies vs error stubs)

`refkit.locate_function` often returns the MSVC cold **error funclet** that merely names the
function via the "…memory not enough!" string. The real bodies (found via the record-base
xref graph `xrefs_to(0x220830)` + jump-to-stub scan) are:

| Hi_ function            | error stub (names it) | **REAL body**        | notes |
|-------------------------|-----------------------|----------------------|-------|
| RegisterSummonModel     | `0x16112`,`0x1612c`   | **`0x15ee0..0x15f35`+** | thin; slot search + init |
| SetSummonMotion         | (inline)              | **`0x17a10..0x17a61`** | +0x10 motion, +0x54=0 |
| SetSummonMotFrame       | (inline)              | **`0x17a70..0x17ad3`** | clamps frame vs count |
| GetSummonBonePos        | (inline)              | **`0x185b0..0x18625`** | reads bone translation |
| GetSummonBoneMatrix     | `0x16c80`             | **`0x18630..0x18692`** | copies full 32B matrix |
| DrawSummonModel         | `0x179f2`             | **`0x17710..0x179f2`** | frame advance + pose |
| ShowSummonModelMesh     | (inline)              | **`0x187e0..0x18834`** | clears hide bit |
| HideSummonModelMesh     | (inline)              | **`0x18840..0x18892`** | sets hide bit |
| StartSummonTexAnim      | (inline)              | **`0x188a0..0x1892a`** | DATA+0x70 tex array |
| StopSummonTexAnim       | (inline)              | **`0x18930..0x18985`** | clears tex flags |
| ModifySummonModelAbr    | (inline)              | **`0x18af0..0x18b4a`** | tail-jmp `0x8c880` |
| ModifySummonModelRGB    | (inline)              | **`0x18b50..0x18b9c`** | tail-jmp `0x83d0` |
| **pose evaluator** (no export / no string) | — | **`0x186a0..`** | called by Draw; builds root matrix |

`FUNC[0x16837..0x16c80]` (1097 B) is a **GetSummonBoneMatrix *consumer*** (reads a bone matrix
into a game object) — it borrows the GetSummonBoneMatrix error string, it is NOT the constructor.

---

## 1. The record array — base, stride, LENGTH

```c
// base RVA 0x220830 — runtime .bss scratch (ZERO on disk; layout recoverable, values are runtime-only)
// stride 0x58, ARRAY LENGTH = 1  (single summon-model slot)
SummonRec  g_SummonModel[1];   // @ 0x220830
```

* **Base = `0x220830`**: `SetSummonMotion@0x17a10 : lea rax,[rip+0x208e0e]` @`0x17a1b`
  (RIP `0x17a22` + `0x208e0e` = `0x220830`). Every accessor `imul idx,0x58; add base`.
* **Stride `0x58`**: `imul r8, idx, 0x58` in every accessor (`0x17a17`, `0x17a77`, `0x185b7`, …).
* **LENGTH = 1**: the Register slot-search loop
  `RegisterSummonModel@0x15ee0`: `cmp [rbx+0x50],0 (free?) → inc eax; add rbx,0x58; cmp eax,1; jl loop`
  (`0x15f08`–`0x15f17`). The bound constant is **1** → only index 0 is ever allocated; a second
  register attempt falls through to the "no free slot" error (`jmp 0x16112` @`0x15f19`). One
  summon model exists at a time. Accessors do **not** bound-check the caller's index (they trust it).
* **No separate "current summon index" global.** The index is a caller argument (edx/ecx/r9d);
  Register only ever fills slot 0. The only summon global is the array itself at `0x220830`.

### SummonRec (0x58 bytes)

```c
struct SummonRec {          // stride 0x58 @ 0x220830, length 1
/*+0x00*/ SummonData* data; // ptr to DATA block; 0 => accessors hit the error stub
/*+0x08*/ // (unused by the Hi_ summon fns in this build; padding)
/*+0x50*/ u8   active;       // 1 = registered/active; 0 = free slot
/*+0x54*/ u16  frame;        // current motion frame counter
};
```

* `+0x00 data`: read by every accessor as `mov rax,[rec]; test rax,rax; je error`
  (`SetSummonMotion@0x17a2c`, `GetBonePos@0x185ca`, …). **Allocated at battle init** and stored
  into `rec[0].data` by `FUNC@0x30c20 : mov [rip+0x1efb60],rbx` @`0x30cc9` (→ `0x220830`).
  **Cleared on teardown** by the giant SFX fn `FUNC@0xeea4 : mov [rip+0x210f1c],r12(=0)` @`0xf90d`.
  Ptr is runtime → its target address is NOT knowable statically.
* `+0x50 active`: set to 1 at `RegisterSummonModel@0x15f27`; the gate byte in every accessor
  (`cmp byte [rec+0x50],0; je error`).
* `+0x54 frame`: zeroed by `RegisterSummonModel@0x15f2e` and `SetSummonMotion@0x17a36`; set/clamped
  by `SetSummonMotFrame@0x17aac/0x17aa2`; advanced each Draw (`0x177d4`/`0x177de`).

---

## 2. The DATA block (rec+0x00 → SummonData)

```c
struct SummonData {           // runtime-allocated; base ptr in SummonRec.data
/*+0x08*/ u32     modelId;    // copied from arg[+0x3c] at register
/*+0x10*/ Motion* motion;     // motion/animation clip pointer
/*+0x18*/ void*   p18;        // zeroed at register-time (list/next?)  [tentative]
/*+0x20*/ u32     hideMask;   // MESH-VISIBILITY bitmask: SET bit = mesh HIDDEN  << HideMeshes
/*+0x38*/ PSXMATRIX* bones;   // -> array of per-bone matrices, stride 0x20
/*+0x40*/ PSXMATRIX  root;    // 32B root/world transform (rot@+0x40, trans@+0x54)
/*+0x70*/ TexAnim*  texAnim;  // -> texture-animation control array, stride 0x18
};
```

* **`+0x08 modelId`**: `RegisterSummonModel@0x15f32 : mov eax,[rsi+0x3c]; mov [data+8],eax` @`0x15f3f`
  (`rsi` = the managed model/mesh arg).
* **`+0x10 motion`** (the animation clip): written by
  `SetSummonMotion@0x17a3b : mov [data+0x10],rcx`; read by `SetSummonMotFrame@0x17a94`,
  `DrawSummonModel@0x17776`. Motion sub-block layout in §4.
* **`+0x18`**: set 0 near register (`mov [rax+0x18], r14(0)` @`0x1697e` in the bone consumer that
  shares the DATA shape) — role unconfirmed; likely a link/dirty field. Marked tentative.
* **`+0x20 hideMask`** — the native equivalent of the `.seq HideMeshes` lever:
  * `ShowSummonModelMesh@0x18803`: `mov eax,1; shl eax,cl; not eax; and [data+0x20],eax` — clears bit `meshIdx` (SHOW).
  * `HideSummonModelMesh@0x18863`: `mov eax,1; shl eax,cl; or [data+0x20],eax` — sets bit `meshIdx` (HIDE).
  * u32 → up to 32 mesh slots; **a set bit means the mesh is HIDDEN** during Draw. Matches our
    `HideMeshes=<hex>` (first native use of the op) — the hex IS this bitmask.
* **`+0x38 bones`** (per-bone matrices) — see §3.
* **`+0x40 root`** (root world transform) — see §5 (the per-frame placement).
* **`+0x70 texAnim`** — see §6.

---

## 3. Per-bone matrices — `SummonData.bones` (DATA+0x38)

`bones` points to an array of PSX-`MATRIX` structs, **stride `0x20` (32 B)**, one per bone.

```c
struct PSXMATRIX {   // 32 B (PSX GTE MATRIX)
/*+0x00*/ s16 m[3][3]; // 3x3 rotation, 18 B
/*+0x12*/ s16 pad;
/*+0x14*/ s32 t[3];    // translation X,Y,Z (12 B) — GetBonePos reads the low word of each
};
```

* **stride `0x20`**: `GetBonePos@0x185da : shl rdx,5`; `GetBoneMatrix@0x1865a : shl rcx,5`.
* **base = DATA+0x38**: `GetBonePos@0x185d3 : mov rax,[r10+0x38]`; `GetBoneMatrix@0x18653 : mov rax,[rax+0x38]`.
* **translation @ +0x14/+0x18/+0x1c**: `Hi_GetSummonBonePos@0x185de/0x185eb/0x185f9` reads
  `word[bone+0x14]`, `word[bone+0x18]`, `word[bone+0x1c]` → writes a 3×s16 vec to the out ptr
  (returns the low word of each `t[k]`).
* **full 32-B matrix**: `Hi_GetSummonBoneMatrix@0x18630` copies `bones[boneIdx]` verbatim with two
  `movups` (`0x1865e`,`0x18666`) into the caller's out buffer — i.e. it exposes the complete
  per-bone rotation+translation.

These matrices are **filled per frame** by the pose evaluator (§5) from the motion clip at the
current frame counter. They are the creature's bone-space transforms; because `bones` lives in the
runtime DATA block, the VALUES are runtime-only. `Hi_GetSummonBoneMatrix(0, boneIdx, &out)` is the
sanctioned runtime read (a probe hook can dump every bone's matrix each frame).

---

## 4. The MOTION block (DATA+0x10)

```c
struct Motion {
/*+0x02*/ u16 frameCount;  // number of frames in the clip
/*+0x0c*/ u32 offA;        // VA-relocatable sub-table offset (fixed up on first Draw)
/*+0x10*/ u32 offB;        // "
};
```

* **`+0x02 frameCount`**: `SetSummonMotFrame@0x17a98 : movzx ecx,word[motion+2]` (clamp gate) and
  `DrawSummonModel@0x177c1 : movzx ecx,word[rax+2]`.
* **frame clamp/loop (SetSummonMotFrame)**: if `frameCount >= requested` → `frame = requested`
  (`0x17aac`), else `frame = 0` (`0x17aa2`).
* **frame advance (Draw)**: `if frameCount > frame: keep; else if loopFlag: frame=0 (0x177d4)
  else frame = frameCount-1 (0x177de)` — loop-vs-hold decided by a Draw stack-arg bit `[rsp+0x60]&1`.
* **`+0x0c/+0x10`**: `DrawSummonModel@0x17785/0x1779e` — bounds-checked (`< 0x10000`/`< 0x100000`)
  offsets into the clip, VA-fixed via helper `0x12b00` (a "resolve packed offset → pointer" util).

---

## 5. The ROOT world transform (DATA+0x40) — the per-frame placement

**This is the answer to "recover the summoned creature's true per-frame transform."**

`DrawSummonModel(recIdx, rotPtr, posPtr, camPtr?, loopFlag)` first calls the **pose evaluator
`0x186a0`** with `rcx=DATA, rdx=rotPtr, r8=posPtr`. The evaluator builds a full 32-B PSX MATRIX
**at DATA+0x40**:

* `0x186b2 : lea rbx,[rcx+0x40]` — works on DATA+0x40.
* Seeds a fixed default matrix: `[rbx]=0x1000` (1.0 in 1/4096 fixed), `[rbx+6]=[rbx+0xe]=0x10000000`
  (`0x186ca`–`0x186dc`).
* **Rotation from `rotPtr` (rdx)**: reads `s16 rx=[rdx], ry=[rdx+2], rz=[rdx+4]` and calls the PSX
  RotMatrix chain `0x3910`(X) → `0x37a0`(Y) → `0x3850`(Z) (`0x186ef`–`0x18729`), composing the 3×3
  into `[rbx+0..0x11]` (= DATA+0x40..0x51).
* **Translation from `posPtr` (r8)**: `mov eax,[r14]; mov [rbx+0x14],eax; mov eax,[r14+4]; mov
  [rbx+0x18],eax; …` (`0x18738`–) → the `t[]` at DATA+0x54/0x58/0x5c.

So the creature's **root pose = (rotation-angle vec, translation vec) passed as ARGUMENTS to
`Hi_DrawSummonModel` each frame** — it is NOT stored in the model struct between frames; it is
recomputed into DATA+0x40 every Draw from caller-supplied data. The constructor seeds DATA+0x40/0x50
once from `bones[bp]` (`RegisterSummonModel-family@0x1691f/0x16928`), but Draw overwrites it per frame.

**Implication for authoring / tracking:** the true per-frame world transform of the summoned
creature decomposes into two runtime inputs, neither of which is a static asset:
1. **root** (DATA+0x40) ← the `(rot, pos)` args the managed SFX/camera code feeds `Hi_DrawSummonModel`;
2. **per-bone local** (DATA+0x38[]) ← the motion clip sampled at `rec+0x54`.
Statically we recover the *layout* and the *update inputs*; the *values* are runtime-only (DATA is
zero-on-disk scratch). The prior round's "per-frame camera eye is a NO-GO for static recovery" **still
holds for the summon path**: the root pos/rot enter as Draw arguments sourced from the runtime camera
anchor / SFX sequence, exactly the scratch buffers flagged before. A runtime probe on
`Hi_DrawSummonModel` (capturing `rdx`/`r8`) OR a per-frame `Hi_GetSummonBoneMatrix` dump is the only
faithful way to record the transform — no data-side method can.

---

## 6. Texture-animation array (DATA+0x70)

```c
struct TexAnim {          // stride 0x18 (24 B); indexed idx*0x18 via lea (rax*3)*8
/*+0x08*/ u8  flags;      // bit0/bit1 = enable; StopTexAnim &= 0xFC
/*+0x10*/ u32 timer;      // reset 0 on start
/*+0x16*/ u16 scale;      // set 0x1000 (1.0 fixed) on start
};
```

* base **DATA+0x70**: `StartSummonTexAnim@0x188cb : mov rax,[r10+0x70]`; `StopSummonTexAnim@0x1895a`.
* stride 0x18: `lea rcx,[rax+rax*2]; lea rdx,[rcx*8]` (`0x188c7`/`0x188cf`).
* start (enable): `or [tex+8],3` (both bits) or `or [tex+8],1` depending on the `r8b` mode arg
  (`0x188dc`/`0x18906`); then `[tex+0x10]=0`, `[tex+0x16]=0x1000` (`0x188e8`/`0x188fc`).
* stop: `and [tex+8],0xFC` (`0x1895e`).

---

## 7. Abr / RGB modifiers (not struct fields, mesh walkers)

* `ModifySummonModelAbr@0x18af0`: guards on active + DATA ptr, `shl dx,5` (abr<<5), tail-`jmp 0x8c880`
  (shared mesh-ABR/semi-transparency applier). `dx==0xff` = no-op sentinel (`0x18af7`).
* `ModifySummonModelRGB@0x18b50`: guards, `movzx r8d,r10w`, tail-`jmp 0x83d0` (shared RGB applier).
Both operate on the DATA block's mesh list via the shared helpers; they do not add new record fields.

---

## 8. Consolidated C annotation

```c
// FF9SpecialEffectPlugin.dll (x64). Base 0x180000000. All offsets proven by fn@rva.
// Record array: RVA 0x220830, stride 0x58, LENGTH 1 (single summon slot). Runtime .bss (zero on disk).

struct SummonRec {          // 0x58
/*+0x00*/ SummonData* data; // alloc @0x30cc9, clear @0xf90d; 0 => error stub
/*+0x50*/ u8   active;      // Register@0x15f27 ; gate in every accessor
/*+0x54*/ u16  frame;       // motion frame counter (Set*@0x17a36/0x17aac, Draw@0x177de)
};

struct SummonData {
/*+0x08*/ u32        modelId;  // Register@0x15f3f  <- arg[+0x3c]
/*+0x10*/ Motion*    motion;   // SetMotion@0x17a3b / Draw@0x17776
/*+0x18*/ void*      p18;      // tentative (zeroed near register)
/*+0x20*/ u32        hideMask; // Show@0x1880e clears / Hide@0x1886c sets bit; SET=HIDDEN  << HideMeshes
/*+0x38*/ PSXMATRIX* bones;    // GetBonePos@0x185d3 / GetBoneMatrix@0x18653 ; stride 0x20
/*+0x40*/ PSXMATRIX  root;     // pose-eval@0x186a0 builds from Draw's (rot,pos) args; rot@+0x40 trans@+0x54
/*+0x70*/ TexAnim*   texAnim;  // Start@0x188cb / Stop@0x1895a ; stride 0x18
};

struct PSXMATRIX { s16 m[3][3]; s16 pad; s32 t[3]; }; // 32 B; GetBonePos reads low word of t[]
struct Motion   { /*+0x02*/ u16 frameCount; /*+0x0c*/ u32 offA; /*+0x10*/ u32 offB; };
struct TexAnim  { /*+0x08*/ u8 flags; /*+0x10*/ u32 timer; /*+0x16*/ u16 scale; }; // 24 B
```

## 9. Answers to the slice's explicit asks

* **Every record offset**: §1 (`+0x00 data`, `+0x50 active`, `+0x54 frame`; rest padding).
* **Nested DATA block map**: §2 (`+0x08 modelId`, `+0x10 motion`, `+0x18 ?`, `+0x20 hideMask`,
  `+0x38 bones`, `+0x40 root`, `+0x70 texAnim`).
* **Array length / bound check**: **1 slot** — the Register loop `cmp eax,1; jl` @`0x15f14`.
* **"Current summon index" global**: none — index is a caller arg; Register only fills slot 0.
* **Mesh-visibility mask (native HideMeshes)**: `SummonData+0x20`, u32, **set bit = hidden**;
  written by Show(`and ~1<<i`)/Hide(`or 1<<i`). This is precisely the `.seq HideMeshes=<hex>` mask.
* **True per-frame transform recovery**: §5 — decomposes into the Draw-time `(rot,pos)` args (root,
  DATA+0x40) + the motion-sampled per-bone matrices (DATA+0x38). Runtime-only values; recover via a
  `Hi_DrawSummonModel` arg probe and/or per-frame `Hi_GetSummonBoneMatrix` dump. No static/data-side
  method recovers them — confirmed for the summon path.

## 10. Provenance

Analysis only (RVAs, mnemonics, struct layout). No extracted geometry/animation bytes; no DLL
modification. DATA/`bones`/`root`/`motion` values are runtime scratch (`0x220830` is zero on disk).

---

## 11. ADVERSARIAL VERIFICATION — claim `rec-fields` (independent re-derivation)

**Verdict: CONFIRMED.** Re-disassembled fresh with refkit (x64, base 0x180000000); every cited
site reproduced, and all three "would-be-refuted-by" conditions were actively checked and NOT met.
Stride `0x58` confirmed at every accessor (`imul ...,0x58`).

### +0x00 — DATA pointer (dereferenced, 0 => error stub)
- `SetSummonMotion` real body @0x17a10: `imul r8,rax,0x58; add r8,base` then @0x17a2c `mov rax,[r8]`;
  @0x17a2f `test rax,rax; je error` — dereferenced + null-checked. Then @0x17a3b `mov [rax+0x10],rcx`
  writes the motion ptr into DATA+0x10.
- `Register` real body @0x15ee0 (distinct from the 0x16112 error stub): @0x15f1e `cmp qword[rbx],rdi`(0)
  null-check; @0x15f2b `mov rcx,[rbx]` reads the DATA ptr.
- `GetSummonBonePos` @0x185ca `mov r10,[r9+rax]; test r10,r10; je error` — same deref+null pattern.
- `Draw` @0x177b7 `mov r9,[rdi]` then @0x177bd `mov rax,[r9+0x10]` (the motion ptr) — confirms +0x00 is
  the DATA ptr and DATA+0x10 is the motion ptr.

### +0x50 — u8 active flag (0 => inactive/error)
- `SetSummonMotion` @0x17a25 `cmp byte ptr [r8+0x50],0; je error`.
- `Register` @0x15f08 `cmp byte ptr [rbx+0x50],dil`(0) slot-scan; @0x15f27 `mov byte ptr [rbx+0x50],1` sets it.
- `GetSummonBonePos` @0x185c2 `cmp byte ptr [r9+rax+0x50],0; je error`.
- Every access is `byte ptr` — consistent u8. No accessor treats it as non-flag.

### +0x54 — u16 motion frame counter
- `Register` @0x15f2e `mov word ptr [rbx+0x54],di`(0) — zeroed on register.
- `SetSummonMotion` @0x17a34 `xor edx,edx` / @0x17a36 `mov word ptr [r8+0x54],dx` — zeroed on set-motion.
- `Draw` (aligned run from 0x177a0, no desync): @0x177c5 `movzx eax,word[rdi+0x54]` reads current frame;
  compares against the motion's total-frame count `word[rax+2]` (rax=motion ptr from DATA+0x10);
  steps it (`dec cx` / reset to 0) and stores @0x177de `mov word ptr [rdi+0x54],cx`; re-reads @0x177e9
  `movzx ebp,word[rdi+0x54]`. All `word ptr` — consistent u16, semantically a playback frame counter.

Note: the initial linear disasm of Draw entered mid-instruction at 0x177c0 (garbage `mov bh,0x48`);
a run aligned from 0x177a0 resolved it. This is exactly the desync trap flagged — flagging it here so the
cited 0x177de is confirmed on the ALIGNED stream, not the desynced one.

No error-stub confusion: the Register/Draw/SetMotion bodies used here are the real work bodies (sizes
85/690/81), not the `lea->panic->int3` funclets. Cited RVAs reproduce to the byte.
