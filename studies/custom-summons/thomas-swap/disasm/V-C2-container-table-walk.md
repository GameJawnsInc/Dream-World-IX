# V-C2 — ADVERSARIAL VERIFICATION: the `ef###.bytes` resource-table walker (fn 0xd390)

**Verdict: PARTIAL.** The mechanism, the field layout, the sector cursor and the endpoint invariant are
all **independently reproduced and CONFIRMED**. The claim **as literally stated is materially incomplete**:
it omits a conditional extra `u16` that the binary reads, and a walker built to the stated grammar
**fails on 372/372 stock files** — the claim's own named falsifier fires on 100% of the corpus.

Re-derived from a **fresh** disassembly (x64 **and** x86 builds) and a **from-scratch** parser
(`v_c2_walk.py`, `v_c2_mech.py`, `v_c2_x86.py`, `v_c2_xref.py`) that deliberately does **not** import
`ef_container.py`. No game bytes in the repo; corpus read from `C:/gd/SCRATCH/summon-format/`.

---

## 1. Is 0xd390 a real body, and is it live?

Not a cold error funclet. `.pdata` splits it into **three** contiguous entries —
`0xd390–0xd3bf`, `0xd3bf–0xd4e5`, `0xd4e5–0xd4ef` — a normal MSVC separated-code split; disassembling
`0xd390..0xd4ef` yields one coherent function with a single prologue and `ret` @0xd4ee.

Reachability (raw `E8/E9 rel32` scan of `.text`, since `refkit.xrefs_to` returned empty for this target):

```
0x3e6a4 --call--> 0x490d0 --call@0x490f5--> 0xd740 --call@0xd7f8--> 0xd390
```

Exactly one call site each. **Live code, chain independently confirmed.** ✔

## 2. The walker, re-derived instruction-by-instruction (x64)

```
0xd399  mov  r8,[rcx+8]                 ; blob base
0xd3a3  movsx eax, word [r8]            ; chunkCount   (SIGNED s16)
0xd3a7  add  r8,2
0xd3ab  mov  r11d,0x800                 ; CURSOR seed
0xd3b1  mov  [rcx+0x14],eax             ; store chunkCount
0xd3ce  lea  rdi,[rcx+0x20]             ; chunk-record walker
chunk: 0xd3d2  movsx eax, word [r8+2]   ; resourceCount (SIGNED s16)
       0xd3d7  add  r8,4                ;   -> 4-byte chunk header; [r8+0] IS NEVER READ HERE
 res:  0xd3f0  movsx eax, word [r8+2]   ; sizeSectors  (SIGNED s16)
       0xd3f5  movsx ecx, byte [r8]     ; id           (SIGNED s8)
       0xd3f9  shl  eax,0xb             ; << 11  (= *0x800)
       0xd3fc  sub  ecx,2 ; je 0xd49f   ;   id == 2 arm
       0xd405  dec  ecx  ; je 0xd415    ;   id == 3 arm
       0xd409  add  r11d,eax ; add r8,4 ; jmp 0xd4bd      [generic arm]
0xd415 [id==3] movsxd rdx,r11d ; add r11d,eax ; add r8,4
               add rdx,[r14+8]          ; blob + cursor = the id-3 PAYLOAD POINTER
               ... builds ChunkRec (psxBase 0x801e7700 @0xd437, 16 programs, headerRel @0xd450) ...
0xd49f [id==2] movsx ecx, byte [r8+1]   ; info
       0xd4a4  add  r11d,eax ; add r8,4
       0xd4ab  test ecx,ecx ; je 0xd4bd
       0xd4af  movsx eax, word [r8]     ; <<< THE EXTRA u16 — ABSENT FROM THE CLAIM
       0xd4b3  shl  eax,0xb
       0xd4b6  add  r11d,eax
       0xd4b9  add  r8,2                ;     entry becomes 6 bytes, not 4
0xd4bd  dec rsi ; jne res
0xd4c6  inc ebp ; add rdi,0x60 ; cmp ebp,[r14+0x14] ; jl chunk     ; stride 0x60 ✔
```

Everything the claim states about **positions, widths, the `<<11`, and the 0x800 seed is exactly right.** ✔

## 3. x86 cross-check — independent codegen, same rule

The 32-bit build's walker is **fn 0xbfc0** (located by its `mov edi,0x800` seed adjacent to `shl r32,0xb`;
called once, from 0x3532f). It is a different register allocation of the identical algorithm:

```
0xbfcf  mov  edi,0x800                  ; cursor
0xbfda  movsx eax, word [esi] ; add esi,2        ; chunkCount
0xbff0  movsx ebx, word [esi+2]; add esi,4       ; resourceCount, 4-byte chunk header
0xc000  movsx eax, byte [esi]  ; sub eax,2 ; je 0xc037     ; id==2
0xc008  dec eax ; movsx eax,word[esi+2] ; je 0xc019        ; id==3
0xc00f  shl eax,0xb ; add edi,eax ; add esi,4              ; generic
0xc037 [id==2] movsx eax,word[esi+2] ; movsx ecx,byte[esi+1] ; add esi,4
       0xc042  shl eax,0xb ; add edi,eax
       0xc047  test ecx,ecx ; je 0xc056
       0xc04b  movsx eax,word[esi] ; shl eax,0xb ; add edi,eax ; add esi,2   ; <<< SAME EXTRA FIELD
```

**Both independently-compiled builds carry the `id==2 && info!=0` extra-u16 arm.** It is not a codegen
artifact. (Chunk-record stride is 0x54 in x86 vs 0x60 in x64 — pointer-width difference, expected.)

## 4. Corpus test — the decisive result

Three grammars walked over all **372** stock `ef###.bytes`:

| grammar | rule for the extra field | cursor == file length |
|---|---|---|
| **A — claim C2 exactly as stated** | *(no extra field)* | **0 / 372** ❌ |
| **B — native** (`id==2 && info!=0`) | read u16, `<<11` into cursor, +2 bytes | **372 / 372** ✔ |
| C — `SFXBinaryFile.cs` (`id==2 && chunkIndex==0`) | same | **372 / 372** ✔ |

**Grammar A fails on every single stock file.** The claim's stated falsifier — *"any stock ef###.bytes
whose walked cursor differs from its byte length"* — is satisfied by **all 372**.

### 4.1 Failure mechanism (worked example, `ef000`)

Raw table bytes: `01 00 | 00 00 04 00 | 00 05 29 00 | 01 05 28 00 | 02 01 04 00 | 00 00 | 03 00 14 00`

| | grammar A (as stated) | grammar B (native) |
|---|---|---|
| entry 3 | `id=2 info=1 size=4` | `id=2 info=1 size=4` **extra=0** |
| entry 4 | `id=0 info=0 size=3` ← **misparsed** | `id=3 info=0 size=20` |
| cursor | `0x2C800` | `0x35000` |
| file len | `0x35000` | `0x35000` |

The extra `u16` is `0x0000`, so it contributes **no size** — the damage is purely the **2-byte pointer
desync**, which shifts every subsequent entry. Two consequences, the second far worse than the first:

1. the cursor undershoots by 0x8800 (17 sectors);
2. **the id-3 resource is silently lost** — grammar A reads it as a bogus `id=0` entry. id 3 is the
   **PS1 MIPS code image**, i.e. exactly the section the roadmap (M2 §9, R6) identifies as where the
   creature's staging lives. A parser built to the stated grammar would not merely miscount bytes; it
   would report that the most load-bearing section does not exist.

**Every one of the 372 files carries exactly one extra-bearing entry** (372 extras / 372 files). No file
escapes; this is not an edge case.

### 4.2 The extra field really is a SIZE (n=1 empirically, but proven by disassembly)

Extra-u16 values across the corpus: `0` ×371, `5` ×1 (**`ef251`**). A fourth grammar — consume the 2
bytes but do **not** add them to the cursor — passes 371/372 and fails only on `ef251`
(`0xc4000` vs `0xc6800`, delta exactly `-0x2800` = 5 sectors).

So the corpus alone would be a **hair's breadth from over-fitting**: one file separates "extra is a size"
from "extra is alignment padding". The disassembly settles it unambiguously in **both** builds
(`shl eax,0xb; add <cursor>,eax` @0xd4b3/0xd4b6 and @0xc04e/0xc051). Not an overfit — but a writer
(rung R2) must round-trip `ef251` or it will never exercise this path.

## 5. Independently reproduced census

385 chunks total (`367×1 + 3×2 + 1×3 + 1×9`), matching M2:

* chunkCount histogram `{1:367, 2:3, 3:1, 9:1}`
* resource ids `{0:385, 1:316, 2:385, 3:385, 4:24, 5:24, 6:24, 7:13, 8:1, 9:37, 10:4}`
* id-2 `(chunkIndex==0, info!=0)` census `{(True,True):372, (False,False):13}` — the two gates are
  **perfectly correlated in stock data**, exactly as M2 §3.3 says
* max table end offset `0x198` — the table never collides with the 0x400 sequence stream ✔
* `ef227` (Bahamut): len `0xc9000`, cursor `0xc9000`, table end **0x54**, 2 chunks, **18** resources
  (10 + 8) — reproduces M2's quoted numbers exactly ✔

## 6. Two corrections that matter for the roadmap

**6.1 The endpoint equality is NOT a native check.** Neither build ever compares the cursor to a length.
In x64 the cursor `r11d` is volatile, never stored, and used only at 0xd415–0xd41f
(`movsxd rdx,r11d; add rdx,[r14+8]`) to compute the id-3 payload pointer; x86 identically at
0xc019–0xc022. So *"the cursor must land exactly on the file length"* is an **empirical corpus property**
(true 372/372, and an excellent self-check for a container **writer**), **not** a format validation the
DLL performs. A malformed container will not be rejected — it will read garbage from a wrong offset.
Do not describe it as "the format's own checksum" in shipped docs.

**6.2 The 372/372 validation does not validate the *gate*.** Because grammars B and C both pass
372/372, the corpus test confirms the *shape* but is **blind** to which condition selects the extra
field. Only the disassembly distinguishes `info != 0` (native) from `chunkIndex == 0` (C#). On stock
data they never diverge; on a **synthesized** container they do. The cited evidence line
("validated 372/372 files cursor_end == len") therefore supports less than it appears to.

**6.3 Signedness (writer-relevant).** `chunkCount`, `resourceCount`, `sizeSectors` and `id` are **all**
`MOVSX` — signed. `id` is **s8** (an id ≥ 0x80 reads negative and falls through the generic arm);
`sizeSectors` is **s16**, so a single resource caps at 0x7FFF sectors (≈64 MB). The claim's "u16"/"u8"
labels are harmless on stock data (max id 10) but wrong for a writer's bounds checks.

**6.4 `chunkIndex` is a name, not a read.** fn 0xd390 never touches the chunk header's `+0` field; it
reads only `+2` and advances 4. The field exists at the stated position/width, but its *meaning* comes
from fn 0x3de37/0x30bd0, not from this walker.

## 7. What a corrected claim should say

> The resource table is walked by fn **0xd390** (body 0xd390–0xd4ef, three `.pdata` entries; reached
> 0x3e6a4 → 0x490d0 → 0xd740 → 0xd390). Layout: `s16 chunkCount`, then per chunk
> `{s16 chunkIndex (unread here), s16 resourceCount}`, then per resource
> `{s8 id, u8 info, s16 sizeSectors}` — **plus a trailing `s16 extraSectors` when `id == 2 && info != 0`,
> making that entry 6 bytes**. A running cursor starts at 0x800 and advances by `sizeSectors << 11`
> (and by `extraSectors << 11` when present). Empirically the cursor lands exactly on the file length in
> 372/372 stock files; the DLL itself does **not** check this.

## 8. Provenance

Read-only static analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (x64 and x86); no DLL
was modified. Stock `ef###.bytes` were read only from `C:/gd/SCRATCH/summon-format/`; nothing but
structural counts/offsets appears here or in the repo. Scripts added by this verification —
`v_c2_walk.py`, `v_c2_mech.py`, `v_c2_x86.py`, `v_c2_xref.py` — contain no game bytes.
