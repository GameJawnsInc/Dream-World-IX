# V-C6 — ADVERSARIAL VERIFICATION: "resource id semantics (10-entry dispatch @0x3ed54)"

**Claim id:** C6 · **Source artifact:** `M2-container-format.md` §4 · **Prior confidence:** high
**VERDICT: PARTIAL** — the dispatch table, the id-5→`Hi_RegisterSummonModel` chain, the id-4 page
geometry and the whole corpus census reproduce **exactly**. The conclusion that **id 10 is
"silently skipped"** is **REFUTED**: a *second*, disjoint 10-entry dispatch table @**0x3ed7c**
inside the same function covers ids **1..10** and gives id 10 a real handler @**0x3ea4c**.

Everything below was re-derived this session from a fresh `refkit` disassembly of the user's own
`FF9SpecialEffectPlugin.dll` (x64, ImageBase `0x180000000`) and from an **independently written**
container walker (transcribed from fn `0xd390`'s instruction stream, *not* from `ef_container.py`).
No claim below is taken from the cited artifact.

---

## 1. What reproduced exactly (CONFIRMED)

### 1.1 The table and its guard

`0x3de37` is a genuine `.pdata` function `[0x3de37, 0x3ed32)` (900 instructions decode cleanly, no
desync). Its state-5 arm:

```
0x3df5c  movzx eax, byte ptr [rip + 0x2e52a3]     ; -> the resource id byte @0x323206
0x3df63  cmp   eax, 9
0x3df66  ja    0x18003e607                        ; id > 9 -> no interpret handler
0x3df6c  mov   ecx, dword ptr [rsi + rax*4 + 0x3ed54]
0x3df73  add   rcx, rsi
0x3df76  jmp   rcx
```

`rsi` is the image base (`0x3de77: lea rsi,[rip - 0x3de6a]` → RVA `0x0`), so the table holds **RVAs**.
Dumping `0x3ed54`:

| idx | value | claimed |
|---|---|---|
| 0 | `0x3e01c` | ✔ |
| 1 | `0x3e11a` | ✔ |
| 2 | `0x3df78` | ✔ |
| 3 | `0x3e13a` | ✔ |
| 4 | `0x3e272` | ✔ |
| 5 | `0x3e373` | ✔ |
| 6 | `0x3e46a` | ✔ |
| 7 | `0x3e476` | ✔ |
| 8 | `0x3e49f` | ✔ |
| 9 | `0x3e4ab` | ✔ |

**All ten match byte-for-byte.** The table is bounded at exactly 10 entries on both sides: the
`cmp eax,9/ja` guard, and the fact that `0x3ed54 + 10*4 = 0x3ed7c` is the base of the *next* table
(§2). There is **no eleventh entry in this table** — the claim's own stated refutation condition
does not fire.

Three jump tables live back-to-back after the function body:
`0x3ed38` (7 entries, the **state** machine, `cmp eax,6/ja` @`0x3dea3` after a `dec eax`) ·
`0x3ed54` (10 entries, the **interpret** dispatch) · `0x3ed7c` (10 entries, the **load** dispatch,
followed by `0xcc` padding). State table: 1→`0x3e697`, 2→`0x3deba`, 3→`0x3deeb`, 4→`0x3e6b9`,
5→`0x3df3d`, 6→`0x3e65d`, 7→`0x3ecf7`.

### 1.2 id 5 reaches the real `Hi_RegisterSummonModel` (cold-funclet trap avoided)

Handler `0x3e373` tail:

```
0x3e441  mov   rdx, r15
0x3e444  cmp   rbx, rax
0x3e447  mov   rcx, rsi
0x3e44a  cmove rdx, r12
0x3e44e  call  0x180015ee0        ; Hi_RegisterSummonModel
```

`0x15ee0` is the **real body** (`.pdata` `[0x15ee0,0x15f35)`), proven by its content, not by a name:

```
0x15f01  lea rbx, [rip + 0x20a928]     ; -> 0x220830   (the summon array)
0x15f08  cmp byte ptr [rbx + 0x50], dil ; active flag @+0x50
0x15f10  add rbx, 0x58                  ; stride 0x58
0x15f14  cmp eax, 1                     ; LENGTH 1
```

The debug string `'Hi_RegisterSummonModel()'` @`0x4b1d0` is referenced **only** from
`[0x16112,0x16146)` — the MSVC cold error funclet, reached from `0x15f19`/`0x15f21`.
`locate_function` returns that funclet; the id-5 handler calls the **body**. ✔

### 1.3 id 4 page geometry

```
0x3e2ec  mov  r14d, 0x40                 ; width  = 0x40
0x3e2fe  lea  r13d, [r14 + 0x40]         ; height = 0x80
0x3e302  ...  loop body ...
0x3e354  add  rsi, 0x4000                ; 0x40*0x80*2 = 0x4000 stride
0x3e36c  jl   0x18003e302
```
Plus a CLUT strip before it: `0x3e286 mov dword[rsp+0x60], 0xe60100` → `{x=0x100, y=0xe6}`,
`0x3e2a0` `w=0x100`, `h = word[rax+6]`, uploaded via the host callback `[0x1c1de8]` with tag
`0x64000000`. ✔ exactly as claimed.

### 1.4 The corpus census — reproduced independently

I transcribed the resource-table walker straight from fn `0xd390`'s disassembly
(`0xd3a3` chunkCount s16 · `0xd3ab` pos=0x800 · `0xd3d2` resourceCount · `0xd3f5` id **s8** ·
`0xd3f0` size s16 `<<11` · `0xd3fc/0xd405` the id==2 / id==3 arms · `0xd49f/0xd4af` the
`info != 0` extra-word rule) and ran it over all 372 stock `ef*.bytes`:

* **372/372 walk to their exact file length.**
* id histogram (records): `0:385  1:316  2:385  3:385  4:24  5:24  6:24  7:13  8:1  9:37  10:4`
* **id 10 occurs exactly 4×: `ef381` ×3, `ef447` ×1.** ✔
* id 8's single record is in **`ef407`**. ✔
* id 2's `info` ∈ {0,1} (372 ones / 13 zeros); id 9's `info` ∈ {1,2,3,48,51,52,55,63}. ✔

**Corpus authenticity re-checked**, not assumed: a fresh `UnityPy` extraction of
`ef227/ef381/ef407/ef447` from `x64/FF9_Data/resources.assets` is **byte-identical** (sha256) to the
`C:/gd/SCRATCH/summon-format/` copies. `ef227` = 823,296 B, sha `fe590d00a01d95c6…`.

---

## 2. THE REFUTATION — id 10 is NOT skipped; it has its own handler

### 2.1 A second dispatch on the same id byte

The id byte @`0x323206` and the info byte @`0x323207` are **written** by the state-4 arm, which
reads the 4-byte resource record directly:

```
0x3e73d  movzx r8d, byte ptr [rsi]              ; id
0x3e748  mov   byte ptr [rip+0x2e4ab7], r8b     ; -> 0x323206
0x3e74f  movzx ebx,  byte ptr [rsi + 1]         ; info
0x3e753  mov   byte ptr [rip+0x2e4aae], bl      ; -> 0x323207
0x3e80f  movzx ebp,  word ptr [rsi + 2]         ; sizeSectors
0x3e813  add   rsi, 4                           ; <-- the {u8 id,u8 info,u16 size} record of fn 0xd390
0x3e817  movzx eax, r8b
0x3e81e  dec   eax                              ; index = id - 1
0x3e825  cmp   eax, 9
0x3e828  ja    0x18003eca6
0x3e82e  lea   r13, [rip - 0x3e835]             ; -> RVA 0 (image base)
0x3e837  mov   ecx, dword ptr [r13 + rax*4 + 0x3ed7c]
0x3e83f  add   rcx, r13
0x3e842  jmp   rcx
```

`index = id − 1`, guarded at 9 ⇒ this table covers **ids 1..10**. Its 10 entries:

| id | handler | id | handler |
|---|---|---|---|
| 1 | `0x3eaf1` | 6 | `0x3ec14` |
| 2 | `0x3e844` | 7 | `0x3ec63` |
| 3 | `0x3eb73` | 8 | `0x3ec73` |
| 4 | `0x3eb84` | 9 | `0x3ec83` |
| 5 | `0x3ebf6` | **10** | **`0x3ea4c`** |

`0x3ea4c` is a **distinct address**, not the out-of-range target `0x3eca6`. Entry [10] onward is
`0xcccccccc` padding — the table is exactly 10 long.

### 2.2 What the id-10 handler does

```
0x3ea4c  mov ecx, dword ptr [rip+0x2e47c6]   ; -> 0x323218  (a PSX-address cursor)
   ... the PsxVirtualAddrMapper 3-way resolve, identical in shape to every sibling arm:
       0x80xxxxxx main RAM  -> r14 = ecx - [0x5789d8] + [0x5789e0]
       0xC0xxxxxx           -> r14 = (ecx & 0x3fffff) + chunkRec[hi].hostPtr
       0x1F800000 scratchpad-> r14 = (ecx - 0x1f800000) + 0x5789e8
0x3ea7d  mov dword ptr [rip+0x2e4795], ecx   ; cursor += payload size (ebp)
0x3ea83  jmp 0x18003eca6                     ; the shared load tail
```

The shared tail is the copy:

```
0x3eca6  ...
0x3ecb8  mov   rcx, r14                       ; dst = the arm's resolved host pointer
0x3ecc6  movsxd r8, eax                       ; len = sectorCount << 11
0x3ecdb  lea   rax, [rip + 0x328c0e]          ; -> 0x3678f0 (the static blob)
0x3ece2  add   rdx, rax                       ; src = blob + (cursor - 0x3678ec) * 0x800
0x3ece5  call  0x180049cd8                    ; -> IAT 0x4a198 = MSVCR120!memcpy
0x3ecea  add   dword ptr [rip+0x2e4500], ebp  ; advance the sector cursor
0x3ecf0  mov   eax, 5                         ; -> state 5 (interpret)
```

`0x49cd8` is an import **thunk** (`jmp qword[rip+0x4ba]` → IAT RVA `0x4a198`), resolved through the
import directory to `MSVCR120.dll!memcpy`. So **every** resource — id 10 included — is memcpy'd into
the destination its state-4 arm resolves.

### 2.3 Where id 10's arena comes from (self-consistent, and corpus-corroborated)

The cursor `0x323218` is created by the **id-2** state-4 arm when `info != 0`:

```
0x3e856  movzx ebx, word ptr [rsi]          ; the EXTRA sector count (fn 0xd390's conditional field)
0x3e859  lea   r14, [rip + 0x1ec070]        ; -> 0x22a8d0  (the PSX arena base)
0x3e875  call  0x180012940                  ; register host ptr -> PSX address
0x3e881  mov   dword ptr [rip+...], eax     ; -> 0x323218  cursor  = that PSX address
0x3e887  mov   dword ptr [rip+...], eax     ; -> 0x323210  base
0x3e88d  mov   dword ptr [rip+...], ecx     ; -> 0x323214  remaining = 0xC800 - extra
```

So **id 10 = "append this payload at the running PSX-RAM cursor, then advance it."** The corpus
layout confirms the reading: in *every* one of the 4 occurrences the id-10 record sits between an
`id 2` and an `id 3` (the MIPS program image) —

```
ef381 chunk[2]:  ... id2 info0 2048 | id10 32768 | id3 20480
ef381 chunk[4]:  ... id2 info0 6144 | id10 30720 | id3 20480
ef381 chunk[7]:  ... id2 info0 6144 | id10  2048 | id3 20480
ef447 chunk[2]:  ... id2 info0 26624| id10 10240 | id3 20480
```

…i.e. bulk data staged into PSX RAM immediately before the PS1 program that reads it.
(Both files establish the cursor in **chunk 0**, whose id-2 carries `info=1`.)

### 2.4 Why the claim went wrong

`0x3ed54` is the **interpret** dispatch (state 5, ids **0..9**). `0x3ed7c` is the **load** dispatch
(state 4, ids **1..10**). The two states alternate: state 4 resolves a destination + memcpys, then
sets state 5, which interprets and sets state 4 again (`0x3e5f2 mov edx,4` … `0x3e63d mov word[0x3231fc],dx`).
The union covers ids **0..10** — **eleven resource ids exist**, not ten. (Symmetrically, **id 0 has
no state-4 arm**: `0` − 1 wraps to `0xffffffff`, `ja` → the tail with `r14` at its default staging
buffer `0x5c08d0` set at `0x3de77`.)

---

## 3. Two further label defects found while verifying

**(a) "6/7/8 = load-state markers"** — true only of the *state-5* half. Their state-4 arms set real
destinations (`0x3ec14` id 6 → a resolved host ptr with `[0x323248]/[0x32324c]` window bookkeeping;
`0x3ec63` id 7 and `0x3ec73` id 8 → `r14 = &0x171dc0`) and the tail memcpys their payloads, which
are **large**: id 6 spans 2 KB–170 KB (24 records), id 7 24–40 KB (13), id 8 38,912 B (1).
Zero-size records: **none, for any id.** Calling them "markers only" implies no payload; false.

**(b) "2 = sub-file archive + AKAO sound"** — the *sub-file archive* half stands; the **AKAO sound**
half is **unsupported**. The id-2 state-5 handler's terminal call is `0x3d670`, which I disassembled
in full: it is a **linear-allocator/arena initializer** — `if (size < 0x80) return;` then
`arena->head = arena+0x10; arena->size = arena->cap = size-0x10;` and `rep stosd 0xFFFFFFFF` over the
region. Its sibling `0x3d6c0` is the matching bump-allocator, asserting through
`psx_compatibility.cpp` line `0x312`. Nothing on the id-2 path touches sound, SPU or the `AKAO`
literals (which live at `0x64644+` in unrelated data). The correct reading of `0x3dfb8-0x3e002` is:
*sub-file[0] is the region base, sub-file[info] its end; the delta sizes an allocator arena.*

---

## 4. Corrected statement (drop-in replacement for M2 §4's headline)

> **Eleven resource ids exist (0..10), dispatched through TWO 10-entry tables in fn `0x3de37`.**
> **Load** (state 4, `0x3ed7c`, index `id−1`, ids 1..10): each arm resolves a destination host
> pointer; the shared tail @`0x3eca6` `memcpy`s the payload there. id 0 has no arm and lands in the
> default staging buffer. **Interpret** (state 5, `0x3ed54`, index `id`, ids 0..9): `0 =` VRAM image
> list · `1 =` continuation · `2 =` sub-file archive (arena init — *not* sound) · `3 =` PSX RAM image
> → pre-decoder `0xd1a0` · `4 =` creature texture pages (0x40×0x80, 0x4000 stride) · `5 =` summon
> model image → `Hi_RegisterSummonModel@0x15ee0` · `6/7/8 =` payload loads whose state-5 arm only
> flips a load-state byte · `9 =` second texture-page path. **`id 10` has NO interpret arm but DOES
> have a load arm (`0x3ea4c`): it appends its payload at the PSX-RAM cursor `0x323218` (arena base
> `0x22a8d0`, established by an `id 2` with `info != 0`) and advances the cursor.**

**Consequence for the re-import pillar:** a writer that emits only ids 0..9 cannot reproduce `ef381`
or `ef447` — their id-10 payloads are exactly the PSX-RAM data their own MIPS programs read. And a
*reader* that treats ids 6/7/8 as zero-payload markers will desynchronise the sector cursor on 24 of
the 372 stock files (it does not, today, only because the table walk in fn `0xd390` adds the size
unconditionally).

---

## 5. Reproduce

```
cd studies/custom-summons/thomas-swap/disasm
PYTHONPATH=. py -c "import refkit,struct; pe=refkit.load(); \
print([hex(v) for v in struct.unpack('<10I', refkit.read_rva(pe,0x3ed54,40))]); \
print([hex(v) for v in struct.unpack('<10I', refkit.read_rva(pe,0x3ed7c,40))])"
py refkit.py --func Hi_RegisterSummonModel      # shows the COLD FUNCLET 0x16112 -- body is 0x15ee0
```
Walker + census script (self-contained, reads only `C:/gd/SCRATCH/summon-format/`):
`C:/Users/skaki/AppData/Local/Temp/claude/c6/walk.py`.

**Runtime-only caveats (explicitly not claimed):** the *value* in `0x323218` at any instant, whether
`0x22a8d0`'s arena ever overflows its `0xC800` window, and what the id-10 bytes *mean* to the MIPS
program are all runtime/PS1-code facts. What is static-recoverable and proven here is that the
id-10 arm exists, resolves a destination, and the payload is copied.
