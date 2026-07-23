# V-M1-08 — adversarial verification of the 0x30-byte EFF-MODEL SLOT layout

**Claim under test (M1-08, source `M1-effmodel-array.md`):** the eff slot maps as
`+0x00 DATA*`, `+0x08` 24-byte texture-binding record, `+0x20` active, `+0x21` sliceOn,
`+0x22` handle (== slot index, the Register* return value), `+0x24` u16 shadeMode (0 Solid /
1 Gou / 2 Tex), `+0x26` u16 drawOffset, `+0x28` u16 sliceValue.

**VERDICT: CONFIRMED** — every cited instruction reproduced at its cited RVA from a fresh
`refkit` disassembly of the user's installed x64 DLL, plus **two independent corroborations the
original artifact did not use**: a second, separately-emitted x64 init loop at `0x30ca0`, and the
*entire x86 build*, whose slot is the same field map shifted by 4 (pointer narrowing 8→4).
Three qualifications are recorded in §6 — none refute the layout.

Method note: `locate_function` returns the MSVC cold error-funclet for several of these
(`Hi_DrawEffModel` resolves to the 29-byte funclet `0x16547..0x16564`, not the body). Every
disassembly below is anchored on a `.pdata` function START and read forward contiguously; nothing
here comes from a linear section sweep. `Hi_InitEffModel` has **no** debug string and **no**
`.pdata` entry — it is a frameless leaf in the `0x15938..0x159a0` gap, found by disassembling the
gap itself.

---

## 1. The array identity (base / stride / count) — CONFIRMED, and self-checking

`Hi_RegisterSolidEffModel` real body `0x15ac0..0x15b66` (the error paths at `0x15b32`/`0x15b4c`
load `0x4b0e0` = `"Hi_RegisterSolidEffModel()"`, so this is the body, not the funclet):

```
0x15acc  lea  rbx, [rip + 0x20a75d]        ; -> RVA 0x220230   (EFFARR base)
0x15ad5  cmp  byte ptr [rbx + 0x20], dil   ; dil = 0           (active flag, BYTE, @+0x20)
0x15ad9  je   0x15ae8                      ; free slot found
0x15add  add  rbx, 0x30                    ; STRIDE 0x30
0x15ae1  cmp  eax, 0x20                    ; 32 SLOTS
0x15ae4  jl   0x15ad5
```

Identical prologue in all five registrars (`0x15b7c`, `0x15c4e`, `0x15d4e`, `0x15e2e`), in
`Hi_FreeEffModel@0x159ab`, `Hi_SetEffModelOffset@0x18a4b`, `Hi_SetEffModelSlice@0x18a9b`,
`Hi_DrawEffModel@0x16160`, `0x15224`, `0x16587`, `0x16809`, `0x16cce`, `0x1719b`, `0x17aea`,
`0x17b37`, `0x1800a`, `0x189a3`, `0x189fa`, `0x18c07` — 20 xrefs total to `0x220230`, all with
stride 48 and the `+0x20` active test.

**Independent arithmetic check the prior artifact missed:**
`0x220230 + 32 × 0x30 = 0x220830` = **exactly** the summon-array base from the prior round. The
two arrays are adjacent with no gap, which over-determines both the stride and the count.

`0x220230` lives in `.data`'s virtual tail (`.data` VA `0x4f000`, VSize `0x5d3440`, RawSize
`0x1a000`) — **zero bytes on disk**. This is a LAYOUT claim only; slot *values* are runtime-only.
(Explicitly checked, because a prior round shipped a "STATIC_TABLE" with no on-disk bytes.)

## 2. The init loop — the field map's ground truth

Leaf function at `0x15940` (not in `.pdata`; disassembled from the `0x15938` gap start):

```
0x15943  lea  rax, [rip + 0x20a908]     ; -> 0x220252  == base + 0x22   (slot 0's handle field)
0x15950  mov  word ptr [rax],       r8w ;   +0x22 = loop counter      -> HANDLE = SLOT INDEX
0x15954  mov  byte ptr [rax - 2],   r9b ;   +0x20 = 0                 -> active, BYTE
0x15958  mov  qword ptr [rax-0x22], r9  ;   +0x00 = 0                 -> DATA*, 8 bytes
0x1595f  mov  qword ptr [rax-0x1a], r9  ;   +0x08 = 0   ┐
0x15963  mov  qword ptr [rax-0x12], r9  ;   +0x10 = 0   ├ 24 BYTES: +0x08..+0x1f
0x15967  mov  qword ptr [rax-0x0a], r9  ;   +0x18 = 0   ┘
0x1596b  lea  rax, [rax + 0x30]         ; stride
0x1596f  cmp  r8d, 0x20 / jl            ; 32 slots
```

Second pass, same function:
```
0x15975  lea  rax, [rip + 0x20a8b4]     ; -> 0x220230 (base)
0x15982  mov  qword ptr [rax], rcx      ; slot +0x00 <- DATA block pointer
0x15985  add  rcx, 0xc8                 ; DATA blocks are 0xc8 apart
```
⇒ `+0x00` is unambiguously the DATA pointer, and the 24 bytes at `+0x08..+0x1f` are a single
zero-initialised region distinct from it.

**Corroboration #1 (new):** a *second* init site at `0x30c20..0x30d45` emits the same loop
independently:
```
0x30c8b  lea  rax, [rip + 0x1ef5c0]   ; -> 0x220252 (base+0x22)
0x30ca0  mov  word ptr [rax], cx      ; handle = index
0x30ca5  mov  byte ptr [rax - 2], bl  ; +0x20 = 0
0x30ca8  mov  qword ptr [rax-0x22], rbx ; +0x00 = 0
0x30cac  lea  rax, [rax + 0x30] / cmp ecx,0x20 / jl
```
The same function also zeroes `0x220830` (qword) and `0x220880` (dword) — i.e. the summon
array's `+0x00` DATA* and its `+0x50` active flag, cross-validating the *summon* layout from the
prior round at zero extra cost.

## 3. Every accessor, re-derived at the cited RVA

| offset | width | writer (verified) | reader (verified) |
|---|---|---|---|
| `+0x00` | ptr | init `0x15982`, `0x30ca8` | null-guard in every accessor: `cmp qword [slot],0` at `0x15ae8`, `0x159bc`, `0x18a5d`, `0x18ab0`, `0x1617b`, `0x1523f`, `0x165a2`, `0x16827` |
| `+0x08..+0x1f` | 24 B | init zeroes (3 qwords); Tex `0x15cb8` `mov word[rdx],si` / `0x15cbb` `mov word[rbx+0xa],di`; TexList `0x15da7` `movups xmmword[rdx],xmm0` + `0x15daf` `movsd qword[rdx+0x10],xmm1` (rdx = rbx+8) | address passed as `rdx` to the DATA-setup call `0x180007120` (Tex `0x15cc7`, TexList `0x15db4`) |
| `+0x20` | u8 | `mov word[rbx+0x20],1` at `0x15aed/0x15b9d/0x15c77/0x15d6d/0x15e4d`; `mov byte[…+0x20],0` at `0x159c3` (Free) | `cmp byte[…+0x20],0` — 8 sites |
| `+0x21` | u8 | `mov byte[r8+0x21],1` @ **`0x18ab6`** (SetSlice) | **none — see §6.2** |
| `+0x22` | u16 | init only (`0x15950`, `0x30ca0`) | `movzx eax, word[rbx+0x22]` @ **`0x15b23`**, `0x15bd7`, `0x15ccc`, `0x15db9`, `0x15e88` — the return value of all five registrars |
| `+0x24` | u16 | `mov dword[rbx+0x24], 0/1/2` @ **`0x15afd` / `0x15bad` / `0x15c87`** (+ `0x15d7d`=2, `0x15e5d`=2) | `movzx ecx, word ptr [rdi+0x24]` @ **`0x163a6`** |
| `+0x26` | u16 | `mov word[rax+r8*8+0x26], dx` @ **`0x18a64`** (SetOffset) | `movzx r9d, word ptr [rdi+0x26]` @ **`0x162de`** |
| `+0x28` | u16 | `mov word[r8+0x28], dx` @ **`0x18abb`** (SetSlice); zeroed by every registrar (`0x15b00`, `0x15bb4`, `0x15c8e`, `0x15d84`, `0x15e64`) | `sub cx, word ptr [rbx+0x28]` @ **`0x1667f`** |
| `+0x2a..+0x2f` | — | never | never (§6.1) |

Every RVA the claim cited matches to the byte.

### 3a. The two READS that pin the semantics (the claim's weakest half, now closed)

`Hi_DrawEffModel` body, disassembled contiguously from `0x16184` (rdi = slot pointer):

```
0x162de  movzx r9d, word ptr [rdi + 0x26]
0x162e3  test  r9w, r9w
0x162e7  je    0x163a6                  ; +0x26 == 0  -> plain path
   ...   (nonzero -> alternate path, ends `add r8, r14` / `call 0x9150`)
0x163a6  movzx ecx, word ptr [rdi + 0x24]
0x163aa  test  ecx, ecx / je  ...       ; 0 -> case A
0x163ae  dec   ecx      / je  0x16404   ; 1 -> case B
0x163b2  dec   ecx      / jne 0x16523   ; 2 -> case C, else bail
```
A literal 3-way switch on **0 / 1 / 2** — the exact values the Solid / Gou / Tex registrars store.
`+0x26` gates an *offset* draw variant. Both read as **16-bit**, which is what makes `+0x24` and
`+0x26` two u16 fields rather than one u32 (the writes are 32-bit only because MSVC merged two
adjacent u16 zero-stores).

`Hi_DrawSliceEffModel` body (entry `0x16570`, rbx = slot pointer):
```
0x16678  movzx ecx, word ptr [rdi + 4]
0x1667f  sub   cx,  word ptr [rbx + 0x28]     ; sliceValue, u16
0x16683  mov   word ptr [rax + 0x7e], cx      ; into the DATA block
```

### 3b. Handle == slot index is airtight

Whole-image scan of every `.pdata`-anchored range for `mov word ptr [<reg>+0x22], …` with a
non-stack base: 16 hits, **all** in functions at `0x343c4`+ that never touch `0x220230`. Combined
with the two init loops writing the counter there, and with `Hi_SetEffModelOffset` /
`Hi_SetEffModelSlice` / `Hi_FreeEffModel` all indexing the array as `base + arg×0x30`, the handle a
registrar returns *is* the slot index, permanently.

## 4. Corroboration #2 (new): the x86 build is the same struct shifted by 4

`refkit.load('x86')`, string-immediate search in `.text`, bodies disassembled from their real
prologues. EFFARR base = RVA `0x20819c`, **stride 0x28**, 32 slots.

x86 init loop `0x12c00` (eax starts at `0x102081ba` = base+0x1e):
```
0x12c10  mov word ptr [eax], cx        ; +0x1e = counter        -> HANDLE
0x12c13  lea eax, [eax + 0x28]         ; stride 0x28
0x12c18  mov byte  ptr [eax-0x2a], 0   ; +0x1c                  -> ACTIVE
0x12c1c  mov dword ptr [eax-0x46], 0   ; +0x00                  -> DATA*
0x12c24  mov dword ptr [eax-0x42], edx ; +0x04  ┐
0x12c27  mov dword ptr [eax-0x3e], edx ; +0x08  │
0x12c2a  mov dword ptr [eax-0x3a], edx ; +0x0c  ├ SIX dwords = 24 BYTES  (+0x04..+0x1b)
0x12c2d  mov dword ptr [eax-0x36], edx ; +0x10  │
0x12c30  mov dword ptr [eax-0x32], edx ; +0x14  │
0x12c33  mov dword ptr [eax-0x2e], edx ; +0x18  ┘
0x12c36  cmp ecx, 0x20 / jl
0x12c50  mov dword ptr [eax], ecx      ; 2nd pass: DATA*, blocks 0x98 apart
```

| field | x64 | x86 | x86 evidence |
|---|---|---|---|
| DATA* | `+0x00` (8) | `+0x00` (4) | `cmp dword[esi],0` `0x12da1` |
| tex record | `+0x08` (24) | `+0x04` (24) | init 6 dwords; Tex writes `[esi+4]`/`[esi+6]` at `0x12ef3`/`0x12efa` |
| active | `+0x20` | `+0x1c` | `cmp byte[esi+0x1c],0` `0x12d90`; `mov byte[…+0x1c],0` `0x12c7d` (Free) |
| sliceOn | `+0x21` | `+0x1d` | `mov byte[ecx*8+0x102081b9],1` `0x149a1` (SetSlice) |
| handle | `+0x22` | `+0x1e` | `movzx eax, word[esi+0x1e]` `0x12ddb/0x12e5f/0x12f1d` (returned) |
| shadeMode | `+0x24` | `+0x20` | `mov dword[esi+0x20], 0 / 1 / 2` at `0x12db6 / 0x12e36 / 0x12ece` |
| drawOffset | `+0x26` | `+0x22` | `mov word[ecx*8+0x102081be],ax` `0x14951` (SetOffset) |
| sliceValue | `+0x28` | `+0x24` | `mov word[ecx*8+0x102081c0],ax` `0x149a9`; zeroed `0x12db9/0x12e3d/0x12ed5` |

Two compilers, two ABIs, identical field map with a uniform +4 shift from the pointer widening.
That is as close to independent replication as static analysis gets, and it *forces* the 24-byte
texture record: in x86 the active flag lands at `+0x1c`, leaving exactly 24 bytes between the
4-byte pointer and it.

## 5. What the layout means for a re-import pipeline

- A registrar **recycles** a slot: `mov word[slot+0x20],1` sets active *and clears sliceOn*, the
  `+0x24` dword store clears drawOffset, and `+0x28` is explicitly zeroed. So `Hi_Register*` is a
  full reset of the draw-modifier trio; sequence authoring must re-issue `SetEffModelOffset` /
  `SetEffModelSlice` **after** every register, never before.
- `Hi_FreeEffModel` clears **only** `+0x20`. The DATA pointer, tex record, handle, shadeMode,
  drawOffset and sliceValue survive a free — a freed slot is reusable, not scrubbed.
- shadeMode is a **3-valued shading mode, not a 5-valued registrar tag**: the TexList and TexPtr
  variants both store 2. A decoder cannot recover *which* registrar was called from the slot.
- Only 32 eff models can be live at once; the effect stream must free.

## 6. Qualifications (recorded, non-refuting)

1. **The map is not exhaustive to 0x30.** `+0x2a..+0x2f` (6 bytes) is never written or read
   anywhere in the image (scanned; the single `+0x2d` hit is `0x15130`, a different buffer).
   x86's tail is `+0x26..+0x27`. Tail padding to 8-byte alignment. The claim enumerates fields and
   does not assert completeness, but a reader should not infer the struct is fully mapped.
2. **`+0x21` "sliceOn" is WRITE-ONLY in this build.** A whole-image scan for
   `byte ptr [<reg>+0x21]` returns exactly two hits: the SetSlice write at `0x18ab6`, and
   `0x19f72` in an unrelated CRT-ish function at `0x19f30` that never touches `0x220230`. The
   offset, width and writer are confirmed; the *name* is an inference from its writer, and nothing
   in `FF9SpecialEffectPlugin.dll` ever reads it. Do not build a decoder that expects a
   slice-enable read.
3. **Two names in the cited evidence are invented, not from the binary.** There is no
   `Hi_InitEffModel` debug string; `0x15950` is a loop-body address inside a nameless
   `.pdata`-less leaf starting at `0x15940`. And the last two registrars' own error strings read
   `"Hi_RegisterTexListModel()"` (`0x4b170`) / `"Hi_RegisterTexPtrModel()"` (`0x4b1a0`) — no
   `Eff`. Cosmetic; the addresses and offsets are all correct.

## 7. Reproduction

```
cd studies/custom-summons/thomas-swap/disasm
py -c "import refkit; pe=refkit.load(); [print(hex(i.address-pe.OPTIONAL_HEADER.ImageBase),i.mnemonic,i.op_str) for i in refkit.disasm(pe,0x15938,0x159a0)]"   # init
py -c "import refkit; pe=refkit.load(); [print(hex(i.address-pe.OPTIONAL_HEADER.ImageBase),i.mnemonic,i.op_str) for i in refkit.disasm(pe,0x15ac0,0x15b66)]"   # RegisterSolid
py -c "import refkit; pe=refkit.load(); [print(hex(i.address-pe.OPTIONAL_HEADER.ImageBase),i.mnemonic,i.op_str) for i in refkit.disasm(pe,0x16184,0x16547)]"   # DrawEffModel body (reads +0x26,+0x24)
py -c "import refkit; pe=refkit.load('x86'); [print(hex(i.address-pe.OPTIONAL_HEADER.ImageBase),i.mnemonic,i.op_str) for i in refkit.disasm(pe,0x12c00,0x12c60)]"  # x86 init
```
No game bytes were written anywhere; all analysis reads the user's own installed DLL.
