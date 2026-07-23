# V-C3 — the id-2 extra-u16 gate: `info != 0`, not `chunkIndex == 0`

**Claim C3 (from `M2-container-format.md` §3.3).** *The extra u16 after an `id == 2` resource entry is
gated on `info != 0` natively, NOT on `chunkIndex == 0` as `SFXBinaryFile.cs:64` claims; the two
conditions are perfectly correlated across all 385 shipped chunks (372× `(chunkIndex==0, info!=0)`,
13× `(chunkIndex!=0, info==0)`), so the C# rule is right on stock data and wrong for any synthesized
container.*

## VERDICT: **CONFIRMED** (all three parts independently re-derived; nothing refuted)

Re-derived from scratch: fresh `refkit` disassembly at the cited RVAs (I did not read `ef_container.py`
before writing my own walker), a fresh x86 cross-check, and a fresh census over the 372 stock files with
my own parser. No cited number was taken on faith.

---

## 1. The native gate — re-disassembled (x64, ImageBase 0x180000000)

`fn 0xd390` is a **real body, not a cold error funclet**: MSVC split it across three `.pdata` ranges
(`0xd390-0xd3bf`, `0xd3bf-0xd4e5`, `0xd4e5-0xd4ef`) — `refkit.functions()` returns the first chunk only,
so disassembling `0xd390..0xd4ef` is required to see the loop. It contains no error string and has
exactly one caller. Call chain re-derived by scanning every `.pdata` function for `call rel32`:

```
0x3de37 --call@0x3e6a4--> 0x490d0 --call@0x490f5--> 0xd740 --call@0xd7f8--> 0xd390
```

The resource-entry arm, verbatim from my own disassembly:

```asm
0xd3d2  movsx eax, word ptr [r8+2]   ; resourceCount  <-- [r8+0] (chunkIndex) IS NEVER READ
0xd3d7  add   r8, 4
...
0xd3f0  movsx eax, word ptr [r8+2]   ; sizeSectors
0xd3f5  movsx ecx, byte ptr [r8]     ; id
0xd3f9  shl   eax, 0xb               ; size * 0x800
0xd3fc  sub   ecx, 2
0xd3ff  je    0xd49f                 ; id == 2
0xd405  dec   ecx
0xd407  je    0xd415                 ; id == 3   (no extra field)
0xd409  add   r11d, eax              ; default: pos += size*0x800
...
0xd49f  movsx ecx, byte ptr [r8+1]   ; <<< INFO byte of the CURRENT entry (r8 not yet advanced)
0xd4a4  add   r11d, eax              ; pos += size*0x800
0xd4a7  add   r8, 4
0xd4ab  test  ecx, ecx               ; <<< THE GATE
0xd4ad  je    0xd4bd                 ;     info == 0  -> no extra field
0xd4af  movsx eax, word ptr [r8]     ;     extra u16
0xd4b3  shl   eax, 0xb
0xd4b6  add   r11d, eax
0xd4b9  add   r8, 2
```

Two facts settle the claim on their own:

1. The gate operand is `byte [r8+1]` = **`info`**, read *before* `add r8,4` (@0xd4a7), so it is the
   current entry's info byte. Exactly as cited.
2. **`chunkIndex` is never loaded anywhere in the walker.** The chunk header read @0xd3d2 takes only
   `word [r8+2]`; the field at `[r8+0]` is skipped by the `add r8,4`. The native walker therefore
   *cannot* be gating on it.

## 2. x86 cross-check — independently compiled, same rule

The 32-bit build has no `.pdata`, so I located the same function by the unique `0x801e7700` psxBase
immediate (one site in `.text`, @0xc092) and disassembled the enclosing region. Same walker:

```asm
0xbff0  movsx ebx, word ptr [esi+2]  ; resourceCount   ([esi+0] chunkIndex NEVER read)
0xbff4  add   esi, 4
0xc000  movsx eax, byte ptr [esi]    ; id
0xc003  sub   eax, 2 / je 0xc037     ; id == 2
...
0xc037  movsx eax, word ptr [esi+2]  ; size
0xc03b  movsx ecx, byte ptr [esi+1]  ; INFO
0xc03f  add   esi, 4
0xc042  shl   eax, 0xb
0xc045  add   edi, eax
0xc047  test  ecx, ecx               ; THE SAME GATE
0xc049  je    0xc056
0xc04b  movsx eax, word ptr [esi]    ; extra u16
0xc04e  shl   eax, 0xb / add edi,eax / add esi,2
```

Two builds, different codegen, identical rule. (Incidentally the x86 chunk-record helper @0xc070 uses
`imul ebx, edx, 0x54` — stride 0x54 vs x64's 0x60; consistent with B5's pointer-width shrink, and
irrelevant to C3.)

## 3. The census — reproduced exactly

My own walker (transcribed from the disassembly above) and a literal transcription of
`SFXBinaryFile.cs:38-77`, run over all 372 extracted stock `ef###.bytes`
(`C:/gd/SCRATCH/summon-format/`, read-only):

```
files                              : 372
chunks                             : 385
id-2 entries per chunk             : {1: 385}      (exactly one, always)
census (chunkIndex==0, info!=0)    : {(True,True): 372, (False,False): 13}
CONTRADICTIONS                     : 0
chunkIndex values across corpus    : {0: 372, 1: 13}
id-2 info values across corpus     : {1: 372, 0: 13}
native cursor != file length       : none (372/372 land exactly on EOF)
C#     cursor != file length       : none (372/372)
native vs C# divergence on stock   : 0 files (identical cursor AND identical table-end offset)
```

The refutation condition — a stock chunk with `chunkIndex!=0 && info!=0`, or `chunkIndex==0 && info==0`
— **does not occur**. The correlation is exact and, notably, degenerate: `chunkIndex ∈ {0,1}` and
`info ∈ {1,0}` are literally the same bit inverted across the corpus.

Table-parse integrity check: re-emitting `ef227`'s parsed table byte-for-byte reproduces the file's own
first 0x54 bytes, so my field decode is exact, not merely self-consistent.

## 4. The "wrong for a synthesized container" half — demonstrated, not asserted

I built a **native-legal** container the stock corpus does not contain: `ef227` with chunk 0's id-2
entry re-emitted as `info = 0` and the extra u16 omitted (offline, scratch only).

| walker | final cursor | table end | lands on EOF (0xc9000)? |
|---|---|---|---|
| native rule (`info != 0`) | `0xc9000` | `0x52` | **yes** |
| `SFXBinaryFile.cs` rule (`chunkIndex == 0`) | `0x767914800` | `0x434` | **no** — off by 994 table bytes |

The C# walker consumes 2 bytes that are not there, desynchronizes the entry stream, and reinterprets
payload bytes as table entries (it invents resource ids 10/48/50/78 and a 13065-sector resource). That
is the silent corruption C3 predicts. A writer must use `info != 0` — and must *emit* `info != 0`
whenever it emits the extra field.

## 5. Adjacent finding (NOT part of C3, flagged for later phases)

While reproducing the census I found an unrelated divergence in the same C# branch: native adds
`size*0x800` **then** `extra*0x800` (@0xd4a4 then @0xd4b6), whereas `SFXBinaryFile.cs:64-69` adds
`extra*0x800` first and only then sets `smallFileBaseOffset`. Totals match, so cursors agree — but the
*sub-region ordering* differs. `extra` is 0 in 371/372 files, so this is unobservable except in
**`ef251`** (chunk 0, `size=6, extra=5`, region base `0x29800`):

- anchoring the sub-file directory at `0x29800` (native ordering) → a valid but degenerate 2-entry table;
- anchoring at `0x2c000` (C# ordering) → a 33-entry table, shaped like every other file's.

`ef251` therefore looks like a counterexample to M2 §5's "the directory is the start of the id-2
payload" — but **fn 0xd390 does not decide this**: it never records an id-2 base. The ordering is
established at runtime by the id-2 stream handler `0x3df78`, which I did not read. **Status:
UNVERIFIED lead, one file, needs 0x3df78 read before any writer relies on either anchor.**

## 6. Reproduce

```
cd studies/custom-summons/thomas-swap/disasm
py -c "import refkit; pe=refkit.load(); [print(i) for i in refkit.disasm(pe,0xd390,0xd4ef)]"
```
Census/mutation script (scratch, not committed):
`<scratchpad>/v_c3.py` — re-transcribes both walkers from the disassembly and censuses
`C:/gd/SCRATCH/summon-format/*.bytes`.

**Provenance.** Static read-only analysis of the user's own installed `FF9SpecialEffectPlugin.dll`
(x64 + x86). Stock `ef###.bytes` were read from `C:/gd/SCRATCH/summon-format/` and never copied into
the repo; the synthetic mutant existed only in memory. No DLL was modified.
