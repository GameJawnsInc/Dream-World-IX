# D4 — THE TWO NATIVE LEVERS: per-mesh SHOW/HIDE, and the CAMERA

**Slice D4 of the FF9SpecialEffectPlugin.dll summon-cutscene disasm round.** Question: of everything
decoded so far, which two levers can we spend *immediately*, without waiting for full re-import?
(a) the native per-mesh show/hide op, (b) the summon cutscene camera.

All RVAs image-base-relative (x64 `ImageBase 0x180000000`; x86 `0x10000000`). Every native claim cites
`fn@rva` from **read-only** static analysis of the user's own installed DLL; every managed claim cites
`file:line` against `C:/gd/FFIX/Memoria/Assembly-CSharp/`. Structural counts read from stock
`ef###.bytes` were taken from the extraction already under `C:/gd/SCRATCH/summon-format/` — **no stock
bytes were written into the repo, and none are quoted here; only counts, offsets and sizes.**

---

## 0. HEADLINE — the two answers, and they point in opposite directions

**(a) The native hide op is REACHABLE but COARSE — and FINDINGS §2.4's precision claim is REFUTED.**
The opcode numbers are settled (157 Show / 158 Hide, M3 §1.1) but they are **HLE library calls made by
the effect's own PS1 MIPS program**, not sequence-stream opcodes — so they are *unreachable from the
authorable `.seq`/container layer* (§1.2). Worse for the "precision" story: the bit index is the GEOM
**mesh ordinal**, and a census of **all 24 creature-bearing stock effects** finds `meshCount ∈ {2,3}`,
max 3 — **Bahamut (`ef227`) has exactly 2 meshes** (§1.4). So the native mask offers *2–3 bits of
granularity on a real summon*, where our managed `HideMeshes=` SFXKey filter distinguished 7 body groups
on the same creature. The native op is **not the finer lever; it is the TOTAL lever** — and *that* is
its actual value: `mask = (1<<meshCount)-1` is a guaranteed, hash-independent, emission-free FULL-BODY
hide, which is exactly what the Thomas swap wants. It is spendable **today** as a 1-line managed
`Marshal.WriteInt32` — the exact mirror of the s52 ROOT read, no DLL patch (§1.6).

**(b) The camera IS data-only authorable, and the path is short.** The summon camera is *not* an HLE op
(M3 §3.1 was right) — it is a **sequence-stream opcode `0x29 PLAY_CAMERA` pointing at a sub-file inside
`ef###.bytes`**, in **the same binary format `SFXDataCamera.Load` reads for raw17 battle cameras** — the
format `ff9mapkit/battle/camera_codec.py` **already round-trips byte-exact**. The whole of Bahamut's
camera choreography is **3 sub-files totalling 460 bytes** (§2.6). The full native chain from those
bytes to `Camera.main` is now named end to end (§2.1), the on-disk layout is confirmed against the
native parser with **two corrections to the C# model** (§2.2), and a same-size-or-smaller edit is an
**in-place byte patch** requiring no container writer at all (§2.5). Deployment is the existing loose-file
mod lane (§2.5.3). **A custom summon camera needs zero new native reach.**

---

# PART A — THE NATIVE PER-MESH SHOW/HIDE OP

## 1.1 The ops, their bodies, and their sole call sites (CONFIRMED)

| op | native body (x64) | native body (x86) | semantics |
|---:|---|---|---|
| **157** | `Hi_ShowSummonModelMesh` **0x187e0** | 0x14730 | `data->hideMask &= ~(1 << (ord & 31))` |
| **158** | `Hi_HideSummonModelMesh` **0x18840** | 0x14780 | `data->hideMask \|= (1 << (ord & 31))` |

Verbatim x64 body of 158 (`0x18840`):

```asm
0x18840  sub  rsp,0x28
0x18844  movsxd rax,ecx                      ; ecx = slot
0x18847  imul r8,rax,0x58                    ; stride 0x58
0x1884b  lea  rax,[rip+0x207fde]             ; -> RVA 0x220830 = summonModels[]
0x18852  cmp  byte [r8+rax+0x50],0           ; rec.active
0x18858  je   err
0x1885a  mov  r8,[r8+rax]                    ; rec.data
0x1885e  test r8,r8 / je err
0x18863  mov  ecx,edx                        ; edx = mesh ordinal
0x18865  mov  eax,1
0x1886a  shl  eax,cl                         ; <-- NO BOUNDS CHECK; x86 shl masks cl to 5 bits
0x1886c  or   [r8+0x20],eax                  ; DATA+0x20 = the hide mask
```

`0x187e0` is byte-identical modulo `not eax` + `and`. **Sole callers, proven by a whole-image direct-call
scan** (`d4_c.py`): `0x187e0 ← [0x117df]` and `0x18840 ← [0x11806]` — one site each, both inside the HLE
dispatcher `0xeea4..0x12321`, both preceded by two `getArgInt@0x126c0` calls (`$a0`=slot, `$a1`=ordinal).
No other code in the image calls them. The `.data` op→fn table agrees: `ft[157]-base == 0x187e0`,
`ft[158]-base == 0x18840` (`0x68780`, M3 §1.1).

## 1.2 REACHABILITY — the load-bearing negative result

**These ops are NOT in the authorable data stream.** Two layers exist and they are frequently conflated:

| layer | who executes it | is it data? | can our tooling emit it? |
|---|---|---|---|
| the **sequence stream** at file `0x400` (`0x00..0x87`, 3-byte records, fn `0x315f1`) | the DLL directly | **YES** — plain bytes in `ef###.bytes` | **YES** (M2 §7, `ef_container.parse_sequence`) |
| the **HLE library** (216 ops, 157/158 among them, dispatcher `0xee80`) | reached ONLY by a MIPS `jal 0xFF0000xx` executed by the effect's own PS1 program (id-3 resource) | **NO** — MIPS machine code | **NO** without a MIPS assembler (M3 §6 rung C) |

So the prior round's menu item #5 ("emit the native Show/Hide `.seq` opcode") is **not implementable as
stated**, and M3's refutation of the data-command-stream model holds here concretely: the *only* things
that can call op 158 are (i) the stock PS1 program, and (ii) nothing we can currently write.

## 1.3 Mask semantics + lifecycle (CONFIRMED)

- **Location:** `summonModels[0].data + 0x20`, a `u32`. x86: the same field at `DATA+0x14` (one 8→4
  pointer shrink; `and [..+0x14],~bit` @`0x14756`, `or [..+0x14],bit` @`0x147a4`, M3 §1.2).
- **Consumption (`Hi_DrawSummonModel` mesh loop):**
  ```asm
  0x17896  mov  ecx,[rax+8]        ; rax = DATA -> DATA+0x08 = the PSX geom pointer
  ...      (psxptr resolve)
  0x17900  movzx esi,byte [rcx+3]  ; meshCount = geom+0x03   (matches ef_container.parse_geom)
  0x17910  mov  rcx,[rdi]          ; DATA  -- RE-READ EVERY MESH ITERATION
  0x17913  mov  eax,[rcx+0x20]     ; the mask
  0x17916  bt   eax,ebx            ; ebx = mesh ordinal
  0x17919  jb   skip               ; hidden -> polys NEVER EMITTED
  ```
  Because the mask is re-read from memory on **every mesh of every frame**, an external write lands on
  the very next Draw — no caching, no latch.
- **Bits ≥ meshCount are inert** (the loop bound is `meshCount`), but the setter's `shl eax,cl` **wraps
  mod 32** — ordinal 33 sets bit 1. A linter must range-check.
- **Lifecycle — who clears it:**
  - `SFX_Play` → `0x30c20` zeroes `summonModels[0].data` (`0x30cc9`, RIP→`0x220830`) and the active
    dword at `0x220880` (`0x30cc3`) — and, in the same function, walks all **32 EFFARR** slots clearing
    `+0x00`/`+0x20` (`0x30ca0..0x30cb3`, stride 0x30 from `0x220252`). So each cast starts with **no
    summon DATA block at all**.
  - `Hi_RegisterSummonModel@0x15ee0` **does not touch `DATA+0x20`** (verified: the only `+0x20`-shaped
    operands in `0x15ee0..0x16140` are `[rsp+0x20]` stack refs, `d4_f.py`). It *requires* the DATA
    pointer to be non-NULL already (`0x15f1e cmp qword [rbx],rdi; je err`).
  - **The DATA block is installed by opcode 208** (native fn **0x47330**, handler `0x121f3`, called with
    `$a0..$a3` where `$a3` is a PSX pointer): `0x47423 lea rax,[rbp+0x90]` → `0x47449 mov [rip→0x220830],rax`.
    **`SummonData` is the sub-block at `+0x90` of the model struct the PS1 program supplies** — i.e. it
    lives in **PSX RAM owned by the effect program**, not the DLL heap. Fn `0x47330` writes `+0x02`,
    `+0x04`, `+0x18/+0x24/+0x30` (three `u16[pageCount]` arrays), `+0x3c`, `+0x40`, `+0x180[]` — it
    **never writes `+0x90..+0x17F`**, so it does not initialise the hide mask either.
  - ⇒ **OPEN (runtime-only):** the mask's *initial* value is whatever the PS1 program's RAM image holds
    at `modelStruct+0xB0`. If that buffer is program-image-resident it is file bytes (a potential
    data-authorable initial visibility set); if it is BSS it is zero. **Do not assume zero.** The probe
    in §1.6 settles it in one cast — log the mask on the first Draw before any op-158 fires.
  - ⚠ **Residual risk:** because the mask lives in PSX RAM, the MIPS program *could* also clear it with a
    plain `sw`, bypassing ops 157/158. Ops 157/158 exist precisely so it doesn't, but this is not
    statically excluded. The §1.6 probe's HIDEMASK log row detects it immediately (an external write that
    gets stomped shows as a mask that reverts).

## 1.4 ⚠ THE GRANULARITY REFUTATION — the census (the finding that changes the plan)

FINDINGS §2.4 rated the native mask **"precision: exact 1 bit ↔ 1 model mesh, stable"** against the
managed key filter's "a KEY can span multiple meshes." That comparison is backwards in practice.

The hide bit indexes the **GEOM `meshCount`** at `geom+0x03` (M4 §2, `ef_container.parse_geom`). Census of
**all 24 creature-bearing effects** (M2 §4's list), parsing the GEOM at each id-5 payload offset
(`d4_cen.py`):

```
meshCount distribution over 24/24 creature effects:   2 -> 21 effects,  3 -> 3 effects   (max 3)
ef227 (Bahamut): boneCount 93, meshCount 2
   mesh 0: 39 FT4 + 1326 FT3, 797 verts
   mesh 1: 44 FT4 + 1007 FT3, 642 verts
```

(`ef227`'s 93 bones / 2 meshes independently matches M4's own header line.)

**Consequences, stated plainly:**
1. **A stock summon creature has 2–3 hideable units, never more.** The 32-bit mask is 29–30 bits of dead
   space. Any design that assumed "hide the wings, keep the body" via the native op is dead on arrival —
   the wings are not a separate mesh.
2. **Our managed `HideMeshes=` is the FINER lever** (it partitions harvested primitives by SFXKey =
   blend/texture state, which cut Bahamut into 7 usable body groups). FINDINGS §2.4's precision row is
   **REFUTED**; the two levers' true relationship is *total-and-cheap* vs *partial-and-fragile*.
3. **The native op's real value is the TOTAL hide:** `mask = (1<<meshCount)-1` (= `0x3` for `ef227`).
   That is: complete, guaranteed, independent of key-hash stability and harvest order, and **free** —
   the hidden meshes' polys never enter the GTE, never enter the ordering table, never reach
   `SFX_GetPrim`. For the Thomas swap ("hide the donor body, keep every effect") this is strictly better
   than the managed filter on every axis except granularity, which the swap does not need.

## 1.5 What "hidden" actually removes (scope note)

The hide bit gates only the **summon model's own mesh emission**. It does **not** touch:
- the EFFARR eff-models parented to the creature's bones (M1 §0.2, `Hi_DrawEffModelByBone` copies
  `summonModels[i].data->bones[b]`, `0x168ea-0x16928`) — beams, glows and props keep rendering, **which
  is exactly the behaviour the Thomas swap wants**;
- the camera (§2), the sound, the background effects.

So a full-body native hide yields "the whole cinematic minus the donor creature" in one `u32`.

## 1.6 HOW WE WOULD DRIVE IT — three routes, ranked

### Route 1 (RECOMMENDED, LOW effort, no DLL patch) — the managed runtime WRITE
The exact mirror of the already-shipped s52 ROOT read. `SfxMeshProbe.cs` **already** resolves
`pluginBase` (`GetModuleHandle("FF9SpecialEffectPlugin.dll")`, `SfxMeshProbe.cs:302-322`) and already
walks `summonModels[0] → data` (`SfxMeshProbe.cs:334-348`). The addition is ~15 lines:

```csharp
// pluginBase + 0x220830 (x64) / +0x20869c (x86) = summonModels[0]
// rec+0x50 (x64) / rec+0x4c (x86) = active ; rec+0x00 = DATA ; DATA+0x20 (x64) / +0x14 (x86) = hideMask
public static void ApplySummonHideMask(UInt32 mask) {          // and a matching ReadSummonHideMask()
    IntPtr data = ResolveSummonData();                          // the SAME helper LogSummonRoot uses
    if (data == IntPtr.Zero) return;
    Marshal.WriteInt32(data + (IntPtr.Size == 8 ? 0x20 : 0x14), unchecked((Int32)mask));
}
```

- **Where to call it:** immediately **before** `SFX.SFX_Update(ref SFX.frameIndex)` —
  `Memoria/Battle/SFX/SFXData.cs:331` and `:347` (the two branches). That is the call that runs the PS1
  program and every `Hi_DrawSummonModel` for the frame, so the write is in place before the mesh loop
  reads it. (`SFX_LateUpdate`/`SFXRender.Update` at `SFXData.cs:362-363` are *after* emission — too late.)
- **Re-apply every frame.** The effect's own program may issue op 157 (Show) mid-cast; a one-shot write
  loses. Per-frame re-assert is one `Marshal.WriteInt32`.
- **Mask value:** read `meshCount` **offline** from the container (`ef_container.parse_geom(...).mesh_count`)
  and use `(1u << meshCount) - 1`, or just write `0xFFFFFFFF` — bits above `meshCount` are inert (§1.3),
  so `0xFFFFFFFF` is a safe total-hide with no per-effect lookup. Prefer the derived value for lintability.
- **Provenance:** a *write into the plugin's runtime state*, not a DLL patch and not asset bytes. It is
  one class more invasive than the s52 read and must be an **owner go/no-go** (M3 §6 rung D flagged this
  as a proposal, and that flagging stands). It writes nothing shippable and is `[SfxProbe]`-gated.
- **Fail-safe:** wrap in `try`, gate on a new `Memoria.ini [SfxProbe] HideSummonMeshes=<hex>` (0 = off,
  the current managed `HideMeshes=` lane untouched). Never take the render down.

### Route 2 (the honest full path, HIGH effort) — emit MIPS
Write `jal 0xFF00009E` with `$a0`/`$a1` set by `lui/ori/addiu` into the id-3 code region. M3 §6 rung C
scoped this: ~10 instruction forms, but it is a different project (needs the id-3 program's own layout,
a free code slot, and the M2 §7 open item "is the decoded stream really built from the blob"). **Not for
this round.**

### Route 3 (status quo) — keep the managed `HideMeshes=` SFXKey filter
Still the only lever with sub-mesh granularity. Keep it; the native mask complements it, does not
replace it. Recommended combination: **native total hide** for "remove the donor creature", **managed key
filter** when a *partial* body edit is genuinely wanted.

## 1.7 What a `[[summon]]` linter can check TODAY (all offline, no runtime)

`ef_container.py` already gives every input:

| rule | source | why |
|---|---|---|
| `mesh_ordinal < geom.mesh_count` | `parse_geom(...).mesh_count` | ordinals wrap mod 32 (`shl eax,cl`) — an out-of-range ordinal silently hides a *different* mesh |
| warn if `mesh_count <= 3` and the author expects sub-body granularity | census §1.4 | the single most likely design error; tell them to use the managed key filter |
| `hide_mask` fits `(1<<mesh_count)-1` | ditto | any higher bit is inert, not an error, but is dead intent |
| `motion_frame <= u16[motion+2]` | M3 §2 op 100 | an out-of-range seek **wraps to 0**, it does not clamp |
| ABR operand `!= 0xff` | M3 §2 op 147 | `0xff` is a silent no-op |

---

# PART B — THE CAMERA

## 2.1 THE FULL CHAIN, named end to end (CONFIRMED)

```
ef###.bytes @0x400  sequence stream
   op 0x29 PLAY_CAMERA (arg1 = sub-file index, arg2 = fixed/random/repeat)
        handler 0x3bbd0
          |-- arg2 dispatch: 0 = literal idx | 1 = last-used | 2 = RANDOM (LCG 0x41c64e6d @0x3bc51)
          |                  3 = table lookup keyed on a battle field (byte[..+0x53])
          |-- 0x3d800(chunkSlot = word[r9+8], idx)      = the sub-file resolver (M2 §5)
          `-- 0x12df0(camBlockPtr, 0)                    = INSTALL   [gated on dword@0x323268 != 0]
0x12df0  install: latch ptr, reset per-slot state, 3x 0x13d40 pre-roll -> tail-jmp
0x13030  PARSE the camera block  (see 2.2)      -> selected sequence ptr stored to global 0x220F00
0x13540  THE PER-FRAME STEPPER   [0x13540..0x13c03]
   called from SFX_UpdateCamera's real body 0x1e80 (@0x1e88, and AGAIN @0x1e91 if it returns nonzero
   -- a zero-duration keyframe consumes two steps), and from the seek loop 0x1d10 (@0x1d26/0x1d2f)
   |-- 0x13d40..0x14350  KEYFRAME EVALUATOR (spherical -> eye/target)
   |     |-- resolve_position 0x145a0   = anchor + 4096.8*(cos,sin)   [4 call sites 0x13fbd/0x140d7/0x14279/0x14313]
   |     `-- lookup_anchor    0x148f0                                  [0x1411b/0x1413f]
   |-- eye  = global 3x s16 @ RVA 0x2200B4  (x,y,z at +0/+2/+4)
   |-- tgt  = 3x s16 on the stepper's stack
   |-- 0x14450  CAMERA SHAKE: r = sqrt(dx^2+dz^2) [0x49cea], sin() [0x49ce4], adds to BOTH eye.y and tgt.y
   |-- 0x14c30  LOOK-AT MATRIX BUILDER(out = 0x69730, A = eye, B = tgt)  -- double-precision, 238 instrs
   |-- ROLL: atan2(eye.z-tgt.z, eye.x-tgt.x) [0x49ccc], negate, /2pi [6.28318530718 @0x4b6a8],
   |         *4096 [@0x4b6c0], then  installedRoll = -3072 - that     -> PSX 4096-units-per-turn
   `-- FOCAL/H: linear lerp  H = S*(1-t) + D*t,  t = remaining/duration  [1.0 @0x4b690]
              -> word @ RVA 0x69750  (@0x13aa7 read / @0x13abd write)
0x69730  THE INSTALLED PSX CAMERA: 9x s16 rot (fp12 /4096) @+0x00, s32 TRX/TRY/TRZ @+0x14/+0x18/+0x1c,
         s16 H @+0x20                                              [FINDINGS §5, re-verified here]
0x1e80   SFX_UpdateCamera body: copies 0x69730 (or the alt source @~0x222020 when mode==1 / isDebug)
         into the 13-float array @ RVA 0x211df0  ->  returned to managed
SFX.cs:1590-1605  Marshal.Copy 13 floats -> worldToCameraMatrix (floats 0..11, PsxCamera sign flips)
                                          -> projectionMatrix from float[12] (near-Z only)
```

**Structural facts that fall out of this and matter for authoring:**
- **The camera advances one step per `SFX_UpdateCamera` call**, i.e. once per managed frame — the same
  clock as `SFX.frameIndex`. This *independently ratifies* `ef_camera_decode.py`'s three-way-validated
  `absolute = play_camera_tick + local_frame - 1` shot clock.
- **eye and target are `s16` triples.** Any authored camera anchor must fit **±32767** in PSX world
  units — the same space as `SummonData+0x40`'s `s32` translation (the s52 log's `(0,-12288,-7168)` sits
  comfortably inside). This is a hard, falsifiable authoring bound.
- **The zoom is one lerped scalar** (H @`0x69750`), confirming FINDINGS §5's "47°→24° push-in is a
  single near-Z animation," now with the interpolator read.
- **The shake is a first-class, authored feature** (fn `0x14450`, amplitude/frequency from two globals,
  applied to eye.y and tgt.y together). Any faithful re-author must account for it or shots will read
  "too clean."
- **`0x12df0` has a second, independent producer at `0x47909`** (+ tail-jumps `0x479dd`/`0x479ef`).
  Since `SFXDataCamera.Load` is the single managed reader for **both** `LoadFromBSC` (raw17) and
  `LoadFromSFX`, that second producer is almost certainly the btlseq/raw17 path — i.e. **one native
  parser serves both camera families** (confidence MEDIUM; the managed-side unification is CONFIRMED,
  the native call-site attribution is inferred).

## 2.2 THE BLOCK FORMAT — native parser vs C# vs `camera_codec.py`

Verbatim head of the parser `0x13030` (`d4_p.py`):

```asm
0x13059  movsx edi,word [rcx]        ; OUTER FLAGS (u16); rcx = block base, rdx = rcx+2 (cursor)
  bit 0 -> u16 off @[rdx] ; seq0 = base+off ; rdx += 2        (0x1306e-0x13078)
  bit 1 -> u16 off        ; seq1                              (0x1308a-0x13094)
  bit 2 -> u16 off        ; seq2                              (0x130a6-0x130b0)
  bit 3 -> u16 off        ; r14 = base+off   <-- the "unknown" block                (0x130c5-0x130d0)
0x130d5  movzx esi,word [rdx] ; ONE more u16 off ; rsi = base+off  (custom-position area)
         loop x4 (r15=4), bits 4,5,6,7:
             set   -> memcpy(slot, rsi, 6) ; rsi += 6          (0x130f7-0x13109)
             clear -> zero the slot                            (0x1310f-0x13113)
0x13130  if (r14) parse it: word[r14]>>14 selects, then >>12 & 3, ...   <-- see below
0x134ea  idx = <selected> ; rdx = [rsp + idx*8 + 0x30]   ; store to global 0x220F00
0x134f8  bt r12d,9  ->  if outer flag bit 9: extra 2-bit field per sequence
```

**Agreement:** the block is `Flags u16` + one `u16` offset entry per *present* flag group + the
pointed-at blocks — **exactly** what `SFXDataCamera.Load` does (`SFXDataCamera.cs:29-82`) and exactly
what `ff9mapkit/battle/camera_codec.py` implements (`HAS_SEQ = 0x01/0x02/0x04`, `HAS_UNKNOWN = 0x08`,
`HAS_CUSTOM_POSITION = 0xF0`, one offset entry per present group, blocks delimited by the offset table).
Three independent derivations of the same layout. **`camera_codec.py`'s structure is CORRECT against the
native parser** — no change needed to make it valid for SFX cameras.

**Two corrections the native parser supplies:**

1. **`HAS_CUSTOM_POSITION` (bits 4-7) is FOUR records, not "3 Int16, sometimes more."**
   `SFXDataCamera.cs:76-80` reads a fixed `cpSize = 3` with the source's own comment *"There are not
   always 3 coordinates... sometimes more."* The native answer: **one `u16` offset for the whole group,
   then 1–4 consecutive 6-byte records (3×`Int16` each), one per SET bit of 4..7** — the count is
   `popcount(flags & 0xF0)`, and the records are packed in bit order. `camera_codec.py` carries the
   region verbatim as opaque bytes, so it is *lossless today* but cannot validate or author it; this
   decode upgrades it to a typed field. These 3×s16 records are in the **same s16 world space as the
   eye/target** (§2.1) — they are literal camera/target anchor points.

2. **`HAS_UNKNOWN` (bit 3) is the SEQUENCE SELECTOR, not opaque padding.**
   The block at the bit-3 offset is parsed as a command word (`word[r14]`, top-2-bit type, then
   `>>12 & 3` sub-type, `0x13139-0x134e2`) whose whole output is an **index 0..2 selecting which of
   `sequence0/1/2` becomes the live track** (`0x134ea: rdx = [rsp + idx*8 + 0x30]` →
   `0x134f1: [0x220F00] = rdx`). That is why every one of `ef227`'s 3 camera resources has outer
   `flags == 0x9` (`HAS_SEQUENCE_0 | bit 3`): one sequence plus its selector. **Naming it "unknown" was
   what made multi-sequence cameras look unusable.** Outer flag **bit 9** also exists and is live
   (`0x134f8 bt r12d,9` → a 2-bit per-sequence field); C# and `camera_codec` both ignore bits ≥ 8, which
   is lossless-by-verbatim but means an authored `Flags` must not invent bits.

## 2.3 THE CLOCK (already validated, now mechanically explained)

`ef_camera_decode.py`'s recovered rule — *absolute tick = `play_camera_tick + local_frame - 1`* —
validated three ways on real bytes. §2.1 supplies the mechanism: the stepper is driven **once per
`SFX_UpdateCamera`**, i.e. once per `SFX.frameIndex` advance, and the block's `frame` fields are consumed
by that stepper from the moment `0x12df0` installs it. Nothing re-bases or scales the clock. The one
wrinkle is the **double-step** at `0x1e88`/`0x1e91`: a keyframe whose duration resolves to zero is
consumed in the same frame as its successor, so a *pair* of same-frame keyframes is legal and must not
be linted as a collision.

## 2.4 VERDICT — is a summon camera authorable from our side?

**YES, data-only. No MIPS, no DLL patch, no new native reach.** The asymmetry with Part A is exact and
worth stating as a law:

> **The creature's staging is CODE (a PS1 MIPS program); the camera's staging is DATA (a sub-file the
> sequence stream points at).** That is why `HideMeshes` needs a memory write and the camera does not.

## 2.5 THE SHORTEST PATH — concretely, in rungs

### 2.5.1 Rung C1 — RE-POINT (zero new format work, ~1 hour)
The `0x29` op's `arg1` is a **sub-file index**. Changing one byte in the 3-byte sequence record at a
known file offset re-points a shot at a *different existing* camera block. Immediate uses: swap shot
order, reuse a later camera earlier, or point every cut at one wide shot to see the whole creature.
`ef_container.parse_sequence` already gives the byte offset of every op (`Op.at`). **Risk: none beyond a
bad index** — lint `arg1 < len(directory)` for the chunk selected by the last `0x05 LOAD_CHUNK`.

### 2.5.2 Rung C2 — IN-PLACE REWRITE (the real prize, small)
Because the sub-file directory is a table of **signed s32 offsets relative to the table itself**
(M2 §5, `0x3da8a`), a **same-size-or-smaller** replacement camera block is a pure in-place byte patch:
parse with `camera_codec.parse_camera`, edit keyframes, re-serialise, pad to the original length, splice.
**No container writer needed** (M2 R2 is *not* a prerequisite for this rung). Growing a block requires
re-emitting the directory and shifting later sub-files inside the id-2 payload — that *does* need R2, or
the free space that already exists inside the payload's 0x800-sector rounding.

**Sizes make this tractable.** `ef227` (`d4_cam2.py`):

| shot | chunk ordinal | sub-file idx | block size | outer flags |
|---|---:|---:|---:|---|
| A (opening) | 0 | 6 | **192 B** | 0x9 |
| B (mid) | 1 | 16 | **228 B** | 0x9 |
| C (outro) | 1 | 47 | **40 B** | 0x9 |

Sequence ops: `0x29 arg1=6` @file `0x40f` (chunk 0), `0x29 arg1=16` @`0x499` (chunk 1),
`0x29 arg1=47` @`0x508` (chunk 1). **The entire camera choreography of FF9's flagship summon is 460
bytes in 3 blocks, and we can already parse, edit and re-serialise every one of them.**

### 2.5.3 Rung C3 — DEPLOY (already solved by the existing stack)
`SFX_Play` is fed by `AssetManager.LoadBytes("SpecialEffects/ef227")` (`SFX.cs:1974-1979`), and
`LoadBytesMultiple` checks **mod folders on disc BEFORE the bundle**
(`Global/Asset/AssetManager.cs:541,568-583,590-600`). So a modified effect ships as a loose file at:

```
<mod folder>/StreamingAssets/Assets/Resources/SpecialEffects/ef227.bytes
```

(`GetResourcesBasePath() == "Assets/Resources/"`, `AssetManagerUtil.cs:33-36`;
`GetAssetExtension<TextAsset>() == ".bytes"`, `AssetManagerUtil.cs:425-426`.)
**No bundle rebuild, no DLL, and it rides the existing `deploy_*` lane.** ⚠ It is a *modified stock
container*, so the output is a **local-only artifact** (scratch, like every other stock-derived byte) —
committable code is the patcher, never the patched file.

### 2.5.4 Rung C4 — VALIDATE (the loop that makes it engineering, not guessing)
The s52 probe already logs `VIEW` + `PROJ` per `SFX.frameIndex`. So the authoring loop is closed
**without** an offline geometric predictor:
`author → deploy → cast → capture VIEW/PROJ → diff against the intended track`.
That is exactly how the kit validates walkmeshes and world blocks. Add one derived column
(`eyeWorld = inverse(VIEW) · 0`) and the log reads as a camera path directly.

### 2.5.5 Do we extend `camera_codec.py` or emit a native section?
**Extend `camera_codec.py`.** There is no such thing as a "native camera section" to emit — the camera IS
this format; the raw17 battle camera and the SFX camera are the same bytes read by the same managed
loader and (very likely, §2.1) the same native parser. Concretely:
- add an **SFX flavour** to `camera_codec` (identical block grammar; the container gives it the block
  bounds instead of raw17's set-offset table),
- type the **custom-position** group (`popcount(flags & 0xF0)` × 3×`s16`, §2.2 correction 1),
- name the **selector** block (§2.2 correction 2) so multi-sequence cameras become authorable,
- add a lint pass: `Flags` bits ≥ 8 preserved-not-invented; frame monotonic (allowing same-frame pairs,
  §2.3); anchors within ±32767; `0x29 arg1` in directory range.

## 2.6 THE ONE RESIDUAL — no offline geometric predictor (and why it is not a blocker)

`ef_camera_decode.py` correctly identified "the geometric gap": nothing managed turns
`(pitch, orientation, roll, distance)` into a world eye/look-at (`CameraEngine.SFX_DATA_CAMERA` is a
literal TODO, `SFXDataCamera.cs:550-555`). **This round locates that math in the DLL**: fn
`0x13d40..0x14350` (the evaluator), `resolve_position@0x145a0` = `anchor + 4096.8*(cos,sin)`,
`lookup_anchor@0x148f0`, and `0x14c30` (the look-at matrix builder), with the angle base confirmed as
**4096 units per revolution** (`2π` @`0x4b6a8`, `4096.0` @`0x4b6c0`) and the focal as a linear lerp
(`1.0` @`0x4b690`).

That makes a faithful offline predictor **tractable** (decode `0x13d40` + `0x14c30`, ~2 functions) —
worth doing eventually so an authored shot can be previewed without a playtest. **But it gates nothing:**
the DLL applies the format correctly by construction, and §2.5.4's capture loop measures the result.
Do not spend a native-RE round on the predictor before rungs C1–C3 have produced a shot worth previewing.

---

## 3. WHAT THIS ADDS TO THE ROADMAP

| # | item | tag | effort | gate | provenance |
|---|---|---|---|---|---|
| 1 | **Native TOTAL body hide via `Marshal.WriteInt32(DATA+0x20, (1<<meshCount)-1)`**, re-asserted each frame before `SFXData.cs:331/347` | AUTHOR | **LOW** | owner go/no-go (it is a runtime WRITE) | sanctioned-with-flag; no DLL patch, no asset bytes |
| 2 | **HIDEMASK probe row** (log `DATA+0x20` each frame alongside ROOT) — settles the initial-value OPEN and the "does the program stomp it" risk in one cast | TRACK | **LOW** | none | sanctioned (read) |
| 3 | **Camera rung C1** — re-point `0x29 arg1` (1 byte) to reorder/reuse existing shots | AUTHOR | **LOW** | none | patcher is code; output is scratch |
| 4 | **Camera rung C2** — in-place same-size camera-block rewrite via an SFX-flavoured `camera_codec` | AUTHOR | **LOW-MED** | #3 | ditto |
| 5 | **`camera_codec` decode upgrade** — type the custom-position group + name the selector block (§2.2) | AUTHOR | LOW | none | pure format work |
| 6 | **`[[summon]]` linter rules §1.7** (mesh ordinal, motion frame wrap, ABR 0xff, camera index range) | AUTHOR | LOW | none | pure format work |
| 7 | **Offline camera predictor** — decode `0x13d40` + `0x14c30` | TRACK | MED | deprioritise until #4 lands | read-only RE |
| 8 | **Native PARTIAL per-mesh hide beyond 2-3 groups** | **DEAD** | — | — | refuted by the census §1.4 — the meshes do not exist |
| 9 | **MIPS emission for Show/Hide** (M3 rung C) | DEFER | HIGH | the id-3 program decode (M2 R6) | — |

**The single highest-value pair this slice unlocks: #2 then #1** (measure the mask, then own it) —
that closes the Thomas-swap body-hide problem with native precision at LOW cost — **and #3+#4**, which
make the summon *camera* an authorable track for the first time, 460 bytes at a time.

---

## 4. OPEN ITEMS (do not guess these)

1. **The hide mask's initial value.** `SummonData` = `modelStruct + 0x90` in **PSX RAM** (op 208, fn
   `0x47330` @`0x47423/0x47449`); nothing in `SFX_Play`, op 208 or `Hi_RegisterSummonModel` writes
   `+0x20`. Whether that buffer is file-resident (⇒ an authorable initial visibility set) or BSS
   (⇒ zero) is **runtime-only**. Settle with roadmap #2.
2. **Whether the PS1 program ever writes the mask with a raw `sw`**, bypassing ops 157/158. Not
   statically excludable; detected instantly by #2.
3. **The `0x29 arg2` dispatch arms** — 0/1/2/3 are read (`0x3bbd0`: literal / last / LCG-random /
   table-lookup keyed on `byte[..+0x53]`) but only the *shape* is decoded, not which battle field
   `+0x53` is. `ef227` uses `arg2 == 0` on all three shots, so this does not gate authoring.
4. **The bit-3 selector block's own grammar.** Its *output* (an index 0..2) is proven; its input
   encoding (`word>>14` type, `>>12 & 3` sub-type, several arms reaching battle state at `0x131be+`)
   is only partially read. Authoring can copy a stock selector verbatim until this is finished.
5. **Outer flags bit 9** (`0x134f8`) — live, meaning undecoded. Preserve, do not invent.
6. **Confirming `0x47909` is the raw17/btlseq installer** (would prove one native parser serves both
   camera families). MEDIUM confidence today.

---

## 5. REPRODUCTION

From `studies/custom-summons/thomas-swap/disasm/` with `import refkit` (helpers written this slice:
`d4_a.py` … `d4_cen.py`, all read the user's own DLL / the scratch extraction and emit RVAs + counts):

```python
import refkit, struct
pe = refkit.load(); base = refkit.image_base(pe)
list(refkit.disasm(pe, 0x18840, 0x18875))   # Hi_HideSummonModelMesh -- shl/or, no bounds check
list(refkit.disasm(pe, 0x17896, 0x1791f))   # Draw mesh loop: meshCount @geom+3, bt mask, jb skip
list(refkit.disasm(pe, 0x30c20, 0x30d45))   # SFX_Play reset: 32 EFFARR slots + summonModels[0]
list(refkit.disasm(pe, 0x47330, 0x474b5))   # op 208 -> summonModels[0].data = $a3 + 0x90
list(refkit.disasm(pe, 0x3bbd0, 0x3bce0))   # op 0x29 PLAY_CAMERA -> 0x3d800 -> 0x12df0
list(refkit.disasm(pe, 0x13030, 0x13532))   # the camera-block parser (flags walk + selector)
list(refkit.disasm(pe, 0x13931, 0x13ad0))   # stepper: shake, look-at, roll atan2, focal lerp
list(refkit.disasm(pe, 0x1e80,  0x1f10))    # SFX_UpdateCamera body: 2x stepper, then the 13 floats
```

Assertions that must hold:
`ft[157]-base == 0x187e0`, `ft[158]-base == 0x18840` (table `0x68780`);
direct-call scan gives exactly one caller each (`0x117df`, `0x11806`);
`struct.unpack('<d', read_rva(pe,0x4b6a8,8)) == 2*pi`, `0x4b6c0 == 4096.0`, `0x4b690 == 1.0`;
`0x220230 + 32*0x30 == 0x220830`.

Corpus (from `C:/gd/SCRATCH/summon-format/`, `ef_container.py`):
`parse_geom(blob, id5.offset).mesh_count` over the 24 creature effects → `{2: 21, 3: 3}`;
`ef227` → `bone_count == 93`, `mesh_count == 2`;
`parse_sequence(blob)` → three `0x29` ops with `arg1 ∈ {6, 16, 47}`, all `arg2 == 0`;
those three sub-files → 192 / 228 / 40 bytes, outer flags `0x9` each.

---

## 6. PROVENANCE

- Read-only static analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (x64; x86 offsets
  quoted from M3/B5's cross-check). **No DLL was modified, patched or redistributed, and none will be.**
- Stock `ef###.bytes` were read from the existing `C:/gd/SCRATCH/summon-format/` extraction. **Nothing
  game-derived was written into the repo.** Only structural numbers appear above (mesh/bone counts,
  primitive counts, block sizes, file offsets, opcode arguments) — no geometry, texture, motion or
  container bytes.
- The proposed roadmap items patch **Memoria's open-source Assembly-CSharp** (the sanctioned lane) and
  emit **format parsers** (committable code). Roadmap #1 is a *write into the plugin's runtime state* and
  is explicitly flagged as an owner go/no-go, one class more invasive than the s52 ROOT read.
- Every native claim cites `fn@rva`; every managed claim cites `file:line`. Runtime-only values are
  labelled as such and asserted only as layout.
