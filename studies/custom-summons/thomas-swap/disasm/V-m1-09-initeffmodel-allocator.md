# V — M1-09 adversarial verification: `Hi_InitEffModel@0x15940` is the EFFARR allocator

**VERDICT: CONFIRMED** (every cited byte reproduced from a fresh disassembly of the user's own DLL;
three nuances + one doc erratum recorded below — none of them refutes the claim).

Arch/base: x64 `ImageBase 0x180000000`, x86 `0x10000000`. All addresses are RVAs.
Method: `refkit.disasm` at the cited RVAs (never `locate_function`, so the cold-funclet trap does not
apply — `0x15940` has **no `.pdata` entry**, it is a no-prologue leaf, and I disassembled it by explicit
range); plus a **raw whole-`.text` rel32 scan** for callers (desync-immune, does not depend on `.pdata`
coverage) and a raw displacement scan for every RIP-relative reference into both arrays.

---

## 1. The body — reproduced instruction-for-instruction

```
0x15940  xor  r9d, r9d
0x15943  lea  rax, [rip + 0x20a908]        ; 0x1594a + 0x20a908 = 0x220252  (EFFARR base 0x220230 + 0x22)
0x1594a  mov  r8d, r9d                      ; slot index := 0
0x15950  mov  word  [rax], r8w              ; slot+0x22  handle := index      <-- "handle := index"
0x15954  mov  byte  [rax-0x02], r9b         ; slot+0x20  active := 0
0x15958  mov  qword [rax-0x22], r9          ; slot+0x00  data   := NULL
0x1595c  inc  r8d
0x1595f  mov  qword [rax-0x1a], r9          ; slot+0x08
0x15963  mov  qword [rax-0x12], r9          ; slot+0x10
0x15967  mov  qword [rax-0x0a], r9          ; slot+0x18
0x1596b  lea  rax, [rax+0x30]               ; STRIDE 0x30
0x1596f  cmp  r8d, 0x20                     ; 32 SLOTS
0x15973  jl   0x15950
0x15975  lea  rax, [rip + 0x20a8b4]         ; 0x1597c + 0x20a8b4 = 0x220230  (EFFARR[0].data)
0x1597c  test edx, edx
0x1597e  jle  0x15995                       ; count <= 0 -> nothing distributed
0x15980  mov  edx, edx
0x15982  mov  qword [rax], rcx              ; slot.data := poolCursor
0x15985  add  rcx, 0xc8                     ; <<< pool advance 0xC8
0x1598c  lea  rax, [rax+0x30]
0x15990  dec  rdx
0x15993  jne  0x15982
0x15995  ret
```

Every cited RVA/constant matches exactly: `0x15943`→`0x220252`, zero loop `0x15950-0x15973`
(`cmp r8d,0x20`), `0x15982 mov qword[rax],rcx`, `0x15985 add rcx,0xc8`, `0x1598c lea rax,[rax+0x30]`.
Signature is `(rcx = poolBase, edx = count)`.

**Independent structural proof of base/stride/count (not in the original artifact):**
`0x220230 + 32 × 0x30 = 0x220830` — *exactly* the SUMMON array base. The two arrays are byte-adjacent,
which cross-validates the EFFARR base RVA, the 0x30 stride and the 32-slot count simultaneously.

---

## 2. "The missing allocator" — corroborated by a hard failure path

`Hi_RegisterSolidEffModel` real body `@0x15ac0` (fresh disasm) walks the same array
(`0x15acc lea rbx,[rip+0x20a75d]` → `0x220230`; `cmp byte[rbx+0x20],dil`; `add rbx,0x30`;
`cmp eax,0x20; jl`) and then:

```
0x15ae8  cmp  qword [rbx], rdi     ; slot.data == NULL ?
0x15aeb  je   0x15b4c              ; -> fatal
0x15b4c  lea  rdx,[rip+0x3558d]    ; -> 0x4b0e0 = "Hi_RegisterSolidEffModel()\nmemory not enough!"
         call qword [rip+0x345b0] ; report
         call 0x1800151a0 ; int3
```
(String bytes read at RVA `0x4b0e0`: `b'Hi_RegisterSolidEffModel()\nmemory not enough!\x00'`.)

Register **never allocates** — it hard-faults on a NULL `.data`. So a cast that uses eff models *must*
have executed the allocator first. That is decisive corroboration, obtained without trusting M1.
(`0x15b17 mov qword[rax+0x10], rdi` = motion-clip pointer NULL, also reproduced.)

---

## 3. Sole caller — verified image-wide, not just over `.pdata`

Raw `.text` scan (0x1000, 0x49000 bytes) for every `E8`/`E9` rel32 whose target == `0x15940`:

| target | callers found |
|---|---|
| `0x15940` (InitEffModel) | **exactly one: `0xf8b8` (`E8`)** |
| `0x15a20` (the summon twin) | two: `0xf8e2`, `0x3e420` |

`0xf8b8` lies inside the mega-interpreter function `0xeea4`. The call-site prologue reproduces verbatim:

```
0xf888  cmp   dword [rip+0x358056], 0x12d      ; guard
0xf892  je    0x122f1
0xf898  movsxd rbx, dword [r13+0xda0]          ; channel/current index
0xf89f  xor   edx, edx                          ; operand #0
0xf8a1  mov   rcx, r13
0xf8a4  shl   rbx, 7                            ; * 0x80  (arg-block stride)
0xf8a8  call  0x12740                           ; resolve operand #0 as a pointer
0xf8ad  mov   edx, dword [rbx + r13 + 0xcac]    ; operand #1 RAW  == count
0xf8b5  mov   rcx, rax                          ; == pool base
0xf8b8  call  0x15940
```

`0x12740` decodes to `resolveArgAsPointer(ctx, n)`: `n=0→[+0xca8]`, `1→[+0xcac]`, `2→[+0xcb0]`,
`3→[+0xcb4]`, `n>=4→` indexed load off the overflow array pointer at `[+0xd0c]`; the raw value is then
passed to `0x10e0`, which is a **PSX-address→host-pointer decoder** (`shr ecx,0x18; cmp ecx,0x80;
and eax,0xfffffff; sub edx,[r8+0x1fc8]` — the classic `0x80xxxxxx` segment decode). So operand 0 is a
PSX pointer into the effect's own data and operand 1 is a raw immediate. Arity 2. ✔

**Opcode identity (fresh, then cross-checked):** the prior `M3-opcode-table.json` entry
`{op:28, handler_x64:63624 (=0xF888), fn_x64:88384 (=0x15940), fn_x86:76800 (=0x12C00), arity:2}`
agrees with everything I derived independently.

---

## 4. x86 twin — reproduced

```
0x12c00  push ebp / mov ebp,esp
0x12c05  mov  eax, 0x102081ba              ; RVA 0x2081ba = EFFARR(0x20819c) + 0x1e  (handle field)
0x12c10  mov  word [eax], cx                ; handle := index
0x12c13  lea  eax, [eax+0x28]               ; STRIDE 0x28 (x86)
0x12c18  mov  byte  [eax-0x2a], 0           ; slot+0x1c active
0x12c1c  mov  dword [eax-0x46], 0           ; slot+0x00 data := NULL
         ... +0x04,+0x08,+0x0c,+0x10,+0x14,+0x18 zeroed ...
0x12c36  cmp  ecx, 0x20                     ; 32 slots
0x12c3b  mov  edx, [ebp+0xc]                ; count
0x12c3e  mov  eax, 0x1020819c               ; EFFARR base RVA 0x20819c
0x12c43  mov  ecx, [ebp+8]                  ; poolBase
0x12c50  mov  dword [eax], ecx
0x12c52  lea  eax, [eax+0x28]
0x12c55  add  ecx, 0x98                     ; <<< pool advance 0x98
```
`add ecx,0x98` at exactly `0x12c55`. ✔ Same two-phase shape, same 32-slot bound, x86 slot stride 0x28.

---

## 5. Nuances found while trying to refute (none refute the claim)

**N1 — there ARE other writers of `EFFARR[i].data`, but no other allocator.**
A raw displacement scan of all of `.text` for RIP-relative references landing in
`[0x220230,0x220290)` returned 23 real sites (+1 false positive at `0x2028a`). Two of them write
`+0x00` besides `Hi_InitEffModel`:
* `0x159f0` — a second no-`.pdata` leaf, identical zero loop (`0x15a08 mov qword[rax-0x22], rdx=0`,
  stride 0x30, `cmp ecx,0x20`), **no pool phase**. Pure reset. Called from `0xf8fc` (another interpreter arm).
* `0x30ca8` — inside `0x30c20`, a global "reset all effect state" routine that also NULLs the summon
  slot's `.data` (`0x30cc9 mov qword[rip+0x1efb60], rbx` → `0x220830`).

Both write **NULL only**. `InitEffModel@0x15982` remains the only site that installs a real pointer.
The claim (as stated: *the allocator*) survives; the M1 doc's field comment *"assigned ONCE by
Hi_InitEffModel"* is imprecise and should read *"the only non-NULL assignment"*.

**N2 — "a literal operand of the effect's own command stream" is right, but the slot is shared.**
The arg slots `+0xca8..+0xcb4` (+ overflow array `+0xd0c`) are read ~113× across the interpreter body
`0xeea4..0x12321` (`0xcac` 28, `0xcb0` 28, `0xcb4` 22, `0xca8` 21, `0xd0c` 14) — they are the universal
operand source for opcode handlers. They are written by exactly four sites:
* `0x127e0` = `SetArgRaw(ctx,n,val)` and `0x12880` = `SetArgPtr(ctx,n,hostPtr)` (the latter converts via
  `0x12940`/`0x12b00`), both driven from the staging loop at `0xdd16`, which iterates the decoded
  argument table at `ctx+0x2de0` (16-byte records, a raw/ptr flag byte at `-8`) for
  `dword[ctx+0x2eb8]` entries — i.e. **the current command's decoded operands**. The command stream
  itself is an array of 16-byte records with base `ctx+chan*0x40+0xc30`, PC at `+0xc40`, remaining at
  `+0xc38` (`0xd91e`, `0xe240`, `0xe254`).
* `0xde90`/`0xdfd0` — the **effect-entry** path (`0xd820`, `0xd980`) stuffs the *host's* call arguments
  into the same slots (pointers converted to PSX addresses).

So a decoder must not assume `arg[n]` is always a stream literal: at the top of an effect the same slots
carry the invocation parameters. For opcode 28 specifically, on the interpreter path, it is the command's
own operand pair. Also note `[ctx+0xda0]` is a **channel/instance index** (`word[rbx+8] & 1`, 2 channels,
sentinel `-1` @`0xd676`), *not* a command index — the `shl rbx,7` is per-channel arg-block addressing.

**N3 — `0xC8` is proven as the pool STRIDE; "sizeof(ModelData)" is an interpretation (well supported).**
Supporting evidence gathered fresh: (a) the SUMMON initializer `0x15a20` advances *its* pool by the
**same** `add rcx,0xc8` (`0x15a83`) while stepping slots by 0x58 — the eff DATA block and the summon
DATA block are the same type/size; (b) a sweep of every constant displacement in the eff/summon family
bodies (`0x15ac0-0x15f00`, `0x16150-0x16d00`, `0x17740-0x17b60`, `0x185b0-0x18c60`) tops out at
**0x7E** — nothing dereferences past 0xC8. No contradiction found.

**N4 (new, actionable) — opcode 28's `count` is UNCLAMPED.**
Neither `0x15940` nor the call site compares `count` against `0x20`. Since `EFFARR[32]` ends exactly at
`0x220830` = the summon record, an authored effect passing `count > 32` writes the **summon slot's data
pointer** (and beyond). Same hazard on the summon twin `0x15a20`, whose zero phase writes exactly one
slot (`0x220830..0x22087c`, individual RIP-relative stores, no loop → array length 1 re-confirmed
independently) yet whose pool loop is also `count`-driven at stride 0x58. Any future `[[summon]]`
emitter/linter must clamp `count <= 32` (eff) / `<= 1` (summon).

**Erratum in `M1-effmodel-array.md`:** the parenthetical explaining the x64/x86 size delta,
"(= 8 pointers × 4 B, matching B5's monotone shift ladder)", is arithmetically wrong.
`0xC8 - 0x98 = 0x30` = 48 bytes = **12** pointer fields × 4 B. The size constants themselves are correct.

---

## 6. What would still refute this

* A dynamic capture showing `EFFARR[i].data` non-NULL before opcode 28 runs (would imply a runtime
  allocator outside `.text`, e.g. through an import). Not visible statically; the raw scan covered
  direct rel32 calls only — an indirect/table call to `0x15940` was not searched exhaustively (no
  absolute `0x180015940` was found in the E8/E9 scan, and `M3`'s dispatch table stores it as the
  op-28 handler target, consistent with the single direct call).
* A real `ef###.bytes` parse showing opcode 28's operand 1 is not an immediate. Not attempted this
  slice (offline container work belongs to M2/M4).
