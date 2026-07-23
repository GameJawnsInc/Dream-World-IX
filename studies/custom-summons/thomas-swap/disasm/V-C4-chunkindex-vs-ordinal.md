# V-C4 — ADVERSARIAL VERIFICATION: `chunkIndex` is a flag, `LOAD_CHUNK` keys on the chunk COUNTER

**Claim under test (C4, from `M2-container-format.md` §3.3 / §7.3):** the per-chunk `u16` at table
offset +0 ("chunkIndex") is not an ordinal — it is `0` for the first chunk and `1` for every later one;
`LOAD_CHUNK` (seq opcode `0x05`) keys on the chunk's POSITION in the table, resolved by fn `0x30bd0`
against the 2-word table `@0x32321c` that fn `0x3de37 @0x3e265` fills with the chunk counter.

**VERDICT: CONFIRMED** (every mechanical assertion re-derived from a fresh disassembly; every corpus
assertion re-derived from a from-scratch parser that shares no code with `ef_container.py`).
**One cited statistic does not reproduce** (§4) and **one material fact is missing from M2** (§5):
`chunkIndex` is *not* dead — it is read at runtime and gates the streaming double-buffer.

All RVAs are for x64 `FF9SpecialEffectPlugin.dll`, ImageBase `0x180000000`. Re-derivation scripts:
`vc4_dis.py`, `vc4_rip2.py`, `vc4_scan.py`, `vc4_bytescan.py`, `vc4_tab.py`, `vc4_corpus.py`,
`vc4_null.py`, `vc4_adv.py` (this dir; pure analysis code, zero game bytes). Corpus = the 372 stock
`ef###.bytes` under `C:/gd/SCRATCH/summon-format/` (385 chunks).

---

## 1. The native mechanism, re-derived instruction by instruction

### 1.1 `fn 0x30bd0` — the resolver (fresh disasm, whole .pdata function `0x30bd0..0x30c1f`)

```asm
0x30bd0  push rbx / sub rsp,0x20
0x30bd6  xor  ebx, ebx                       ; index = 0
0x30bd8  lea  rdx, [rip+0x2f263d]            ; -> RVA 0x32321c   (table base)
0x30bdf  lea  r8,  [rip+0x2f263a]            ; -> RVA 0x323220   (table end)
0x30be6  movsx eax, word [rdx]               ; s16 entry
0x30be9  cmp  ecx, eax                       ; ecx = LOAD_CHUNK arg1
0x30beb  je   0x30bf8
0x30bed  add  rdx, 2 / inc ebx / cmp rdx,r8 / jl 0x30be6
0x30bf8  cmp  ebx, 2 / jl 0x30c17
0x30bfd  ... call [assert]                   ; index >= 2 => _wassert
0x30c17  mov  eax, ebx / ret                 ; returns the SLOT index
```
Exactly as cited: a linear search over **two** `u16` entries at `0x32321c`/`0x32321e`, asserting on miss.
It returns the **slot**, not the argument.

### 1.2 `fn 0x31712` — the `0x05` handler (and it *is* opcode `0x05`)

Jump table `@0x31f58` read directly (`vc4_tab.py`): `idx 0x03 -> 0x316c0`, **`idx 0x05 -> 0x31712`**,
`0x10..0x13 -> 0x316da` (the assert stub). Handler body:

```asm
0x31712  movsx ecx, dx                        ; ecx = arg1
0x31715  mov  word [rip+0x2f1a5a], dx         ; -> RVA 0x323176 (raw arg kept)
0x3171c  call 0x30bd0
0x31721  mov  word [rip+0x2f1a50], ax         ; -> RVA 0x323178 (resolved SLOT)
```

### 1.3 `fn 0x3de37 @0x3e265` — what actually goes into the table

```asm
0x3de63  lea  rsi, [rip-0x3de6a]              ; -> RVA 0x0  => rsi = IMAGE BASE  (checked)
...
0x3e1f0  movzx eax, word [rip+0x2e5013]       ; -> RVA 0x32320a   (the counter C)
0x3e1f7  mov  r10, [rip+0x3296e2]             ; -> RVA 0x3678e0   (ctx)
0x3e1fe  lea  rcx, [rax+rax*2] / shl rcx,5    ; C * 0x60          (ChunkRec stride)
0x3e204  lea  r8,  [r10+0x18] / add r8,rcx    ; &ChunkRec[C]
0x3e208  and  edx, 1                          ; C & 1 = buffer parity
0x3e21c  mov  [r10+rax*8+0xda8], r8           ; live ChunkRec ptr, indexed by parity
0x3e246  call 0xd1a0                          ; MIPS pre-decode
0x3e24b  movsxd rcx, dword [rip+0x2e4fa6]     ; -> RVA 0x3231f8   (write slot, 0/1)
0x3e25e  movzx eax, word  [rip+0x2e4fa5]      ; -> RVA 0x32320a   (the counter C)
0x3e265  mov  word [rsi+rcx*2+0x32321c], ax   ; table[writeSlot] = C
```
Cited store reproduced verbatim, including `rsi = ImageBase` (so the displacement really is RVA
`0x32321c`) and `ax = [0x32320a]`.

### 1.4 `[0x32320a]` really is a sequential counter — its only two writers

A byte-level scan of `.text` for RIP-relative displacements resolving to `0x32320a` (`vc4_bytescan.py`,
which finds code the `.pdata` walk misses) turns up exactly two writes, both in a **leaf function with no
`.pdata` entry** (gap `0x3dadb..0x3dc50` — `refkit.functions()` alone does *not* see these; a
disassembly-only search returns "reads only" and would have left this unproven):

```asm
; fn 0x3db90  (INIT; called from 0x31ea2 and 0x10de5)
0x3dbb0  mov dword [rip+0x2e5662], 0xffffffff ; -> RVA 0x32321c : BOTH table words = 0xFFFF
0x3dbbc  mov dword [rip+0x2e5636], ecx        ; -> RVA 0x3231f8 : writeSlot = 0
0x3dbc2  mov word  [rip+0x2e5641], cx         ; -> RVA 0x32320a : counter = 0

; fn 0x3dbf0  (ADVANCE; called from 0x316c0 = seq opcode 0x03, and 0x10df2)
0x3dbfe  inc word  [rip+0x2e5605]             ; -> RVA 0x32320a : counter++
0x3dc07  lea rdx,  [rip+0x2e560e]             ; -> RVA 0x32321c : table base
0x3dc23  mov eax,  [rip+0x2e55cf]             ; -> RVA 0x3231f8 : writeSlot
0x3dc33  inc eax / and eax,1 / mov [..0x3231f8], eax   ; writeSlot ^= 1
0x3dc44  mov word [rdx+rcx*2], 0xffff         ; invalidate the new slot until its id-3 lands
```

So the table is a **2-slot double buffer mapping `slot -> chunk counter`**, the counter is zeroed at init
and incremented **only** by sequence opcode `0x03`. `LOAD_CHUNK arg1` is therefore matched against
"how many chunk advances have happened", i.e. the chunk's **position in the file's table** — never
against the file's `chunkIndex` field. **Claim's mechanism: CONFIRMED.**

### 1.5 The consumer chain closes (`0x49170 -> 0xd820`)

`0x48b10 @0x48b9e`: `cmp ebp,0x80; jl` → `mov [rbx+0x14], code-0x80`; handler `0x49170`.
`0x49170 @0x49189`: `mov edx,[r10+0x14]` → `call 0xd820`.
`0xd820 @0xd849`: `movsx eax, word [rbx+8]` (the slot) `; and eax,1` → `mov rcx,[r14+rax*8+0xda8]`
(the ChunkRec stored at `0x3e21c`), then `@0xd906  mov r8d,[rax+rbp*4+0x18]` = `programOffset[N]`,
`@0xd932 test r8d,r8d; jne` → `0xe210` (MIPS interpreter), else return −1. Reproduced as cited.

### 1.6 The header layout, re-derived from the walker `fn 0xd390/0xd3bf`

```asm
0xd3a3  movsx eax, word [r8]      ; chunkCount     (s16)
0xd3a7  add   r8, 2
0xd3d2  movsx eax, word [r8+2]    ; resourceCount  <-- reads +2, SKIPS +0
0xd3d7  add   r8, 4
0xd3f5  movsx ecx, byte [r8]      ; id
0xd3f0  movsx eax, word [r8+2] ; shl eax,0xb   ; sizeSectors * 0x800
0xd49f  movsx ecx, byte [r8+1]    ; info     -- id==2 && info!=0 -> extra u16 (@0xd4af)
0xd4c8  add   rdi, 0x60           ; ChunkRec stride
```
and the id-3 arm (`0xd415..0xd499`): `psxBase = 0x801e7700 + (ordinal&1)*0x5000` (`lea ebx,[rax+rax*4];
shl ebx,0xc; add ebx,0x801e7700`), `headerRel = (ptr&0xFFFFFFF) - (psxBase&0xFFFFFFF)` → `ChunkRec+0x58`,
program pointer array at `payload + headerRel + 8`, 16 entries, each relocated the same way, `0` = absent.
All as M2 states; I used exactly this to build an independent parser.

---

## 2. Corpus re-derivation (from-scratch parser, `vc4_corpus.py`)

| check | result |
|---|---|
| files parsed | **372** |
| chunks | **385** |
| walker cursor lands exactly on file length (using the native `info != 0` rule) | **372 / 372** |
| sequence streams at `0x400` terminating in `0x00` | **372 / 372** |
| total sequence opcodes | **11,807** (matches M2's independently-obtained figure) |
| max ops in one file | **216** (matches) |
| `0x80+N` opcodes | **723** |

**`chunkIndex` vector census (all 385 chunks):**

| vector | files |
|---|---|
| `(0,)` | 367 |
| `(0,1)` | 3 — `ef225`, `ef227`, `ef251` |
| `(0,1,1)` | 1 — **`ef447`** |
| `(0,1,1,1,1,1,1,1,1)` | 1 — **`ef381`** |

Both cited vectors reproduce **byte for byte**, and the rule "0 for the first chunk, 1 for every later
chunk" holds for **385/385** chunks corpus-wide. **Statement part 1: CONFIRMED.**

---

## 3. The refutation attempt — and why the ordinal key survives it

The claim's own falsifier is *"a file where an `0x80+N` opcode resolves to a live program under the
chunkIndex key but not under the ordinal key."* Three independent tests:

**(a) Arity — this alone is decisive.** Corpus-wide `LOAD_CHUNK` argument histogram (`vc4_adv.py`):

```
arg: 0 -> 372   1 -> 5   2 -> 2   3 -> 1   4 -> 1   5 -> 1   6 -> 1   7 -> 1   8 -> 1
```
The `chunkIndex` field's corpus-wide value set is `{0, 1}`. **Seven `LOAD_CHUNK` arguments (values 2–8)
have no possible referent under the chunkIndex key.** Meanwhile *no* `LOAD_CHUNK` arg is ever `>= chunkCount`
(0 violations / 372 files). `ef381`'s sequence loads `0,1,2,3,4,5,6,7,8` against a chunkIndex vector of
`[0,1,1,1,1,1,1,1,1]` — the arguments enumerate the ordinals exactly.

**(b) Program liveness.** Replaying every sequence and testing "is program N live in the selected chunk":

| key | `0x80+N` ops | failures |
|---|---|---|
| **table ordinal** | 723 | **0** |
| chunkIndex field (first match) | 723 | **11** (10 × `ef381`, 1 × `ef447`) |

**(c) Non-vacuity (the null test, `vc4_null.py`).** If every chunk carried every program, (b) would be
worthless. Permuting the chunk assignment inside the multi-chunk files:

| file | chunks | `0x80+N` ops | identity (ordinal) failures | permutations with 0 failures |
|---|---|---|---|---|
| `ef225` | 2 | 3 | 0 | 0/1 |
| `ef227` | 2 | 2 | 0 | 1/1 (degenerate — both chunks live prog 0 only) |
| `ef251` | 2 | 9 | 0 | 0/1 |
| `ef381` | 9 | 13 | 0 | **7/2000 (0.3 %)** |
| `ef447` | 3 | 5 | 0 | 1/5 |

The ordinal key is *selected*, not merely *permitted*: e.g. `ef381` chunk 6 and chunk 7 are the only
chunks with program 3 live (`liveProgs [0,3]`), and `0x83` is issued exactly after `LOAD_CHUNK 6` and
`LOAD_CHUNK 7`. Same in `ef447` (chunk 1 = `[0,3]`, `0x83` follows `LOAD_CHUNK 1`).

**(d) A fourth structural corroboration that M2 does not claim.** Since `0x32320a` advances only on
opcode `0x03`, the ordinal key requires exactly one `0x03` per chunk transition. Corpus-wide:
**`#(opcode 0x03) == chunkCount − 1` in 372/372 files, zero exceptions.** This is the runtime-side proof
of the static ordinal reading, and it is an *authoring constraint*: a synthesized container must emit
exactly one `0x03` per chunk, in file order, or `LOAD_CHUNK` will assert.

No falsifier found. **Statement part 2: CONFIRMED.**

---

## 4. CORRECTION — the cited "13 failures (all `ef381`)" does not reproduce

My independent count under the chunkIndex key is **11 failures: 10 in `ef381` + 1 in `ef447`**
(`ef447 @0x49c`, opcode `0x80`, after the unresolvable `LOAD_CHUNK 2`).

* `13` happens to be **`ef381`'s total `0x80+N` opcode count**, so the prior round most likely scored
  the whole file as failing rather than the individual opcodes downstream of an unresolvable load.
* **"all `ef381`" is wrong under every scoring convention I could construct.** `ef447` issues
  `LOAD_CHUNK 2` while its chunkIndex values are `{0,1}`, so the chunkIndex key must fail there too —
  unless unresolved loads are silently treated as "keep the previous chunk", in which case the count
  drops to 3 (all `ef381`) and `ef447` reaches 0, still not 13.

Everything the number was offered to support is unaffected (0 vs non-zero, and §3(a) is stronger than the
liveness census anyway). Downstream artifacts should cite **11 (10 `ef381` + 1 `ef447`)**, or better,
cite the arity argument.

---

## 5. MATERIAL ADDITION — `chunkIndex` is NOT dead; it selects the streaming buffer

M2 §3.1 shows the walker skipping the field, which invites the inference "the field is unused". **That
inference is wrong, and it matters for authoring.** The *streaming state machine* (`fn 0x3de37`) reads it:

```asm
0x3deeb  movzx eax, word [rip+0x2e5316]   ; -> 0x323208 chunkCount
0x3def2  cmp   word [rip+0x2e5311], ax    ; -> 0x32320a counter ; jae -> done
0x3deff  mov   edx, dword [rip+0x2e5307]  ; -> 0x32320c header cursor
0x3df08  call  0x10e0                     ; PSX addr -> host ptr
0x3df12  movzx ecx, word [rax]            ; the chunkIndex FIELD
0x3df15  mov   word [rip+0x2e52e4], cx    ; -> RVA 0x323200      <== stored
0x3df1c  movzx eax, word [rax+2]          ; resourceCount
0x3df20  add   dword [rip+0x2e52e5], 4    ; cursor += 4
0x3df27  mov   word [rip+0x2e52d4], ax    ; -> 0x323202 (the per-resource countdown, dec'd @0x3e607)
```

`[0x323200]` has exactly **three** consumers in the whole DLL (RIP scan + byte scan agree), all the same
shape — `chunkIndex == 1 && writeSlot == 0` picks the alternate stream buffer (`r13` vs `r14`):

| site | in handler |
|---|---|
| `0x3e01c  cmp word [..0x323200], 1` → `0x3e029 cmp dword [..0x3231f8],0` → `cmove r15` | id-0 (VRAM image list) |
| `0x3e13a  cmp word [..0x323200], 1` → `0x3e142`/`0x3e154 cmove rax` | **id-3 (the PS1 code image)** |
| `0x3e7f5  cmp word [..0x323200], 1` → `0x3e7fd`/`0x3e808 cmove r13` | resource-entry walk |

**Reading:** `chunkIndex` is a boolean *"this is not the first chunk, so my payload arrives in the other
half of the double buffer"* flag. That is exactly why its value set is `{0,1}` and why it correlates
perfectly with the `info != 0` gate (M2 §3.3) — both are "first chunk vs. later chunk" in disguise.

**Authoring consequence (for the format writer, and it is load-bearing):** a synthesized container must
still emit `chunkIndex = 0` for chunk 0 and `1` for every later chunk. It is *not* a free/ignored field.
Writing an ordinal there (2, 3, …) would make all three tests take the `!= 1` arm and point the loader at
the wrong buffer half.

---

## 6. Summary of what reproduced

| item | status |
|---|---|
| `chunkIndex` = 0 first / 1 later, `ef381 [0,1×8]`, `ef447 [0,1,1]` | ✔ reproduced, and holds 385/385 chunks |
| `fn 0x30bd0` = 2-entry linear search of `0x32321c..0x323220`, asserts `>= 2`, returns slot | ✔ verbatim |
| `fn 0x3de37 @0x3e265` writes `table[writeSlot@0x3231f8] = counter@0x32320a` (`rsi` = ImageBase) | ✔ verbatim |
| `0x32320a` is a pure counter (zeroed `@0x3dbc2`, `inc @0x3dbfe` from seq opcode `0x03` only) | ✔ (needed a byte-scan — the writers live in a `.pdata`-less leaf) |
| `LOAD_CHUNK` key = table position, not the field | ✔ 3 independent proofs (§3 a/b/d) |
| "13 failures, all `ef381`" | ✘ **11 failures: 10 `ef381` + 1 `ef447`** |
| `chunkIndex` is unused by the port | ✘ **not stated by C4, but implied by M2 §3.1 — it is read `@0x3df12` and gates the double buffer** |
