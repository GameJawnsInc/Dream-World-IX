# V — anchor-buffer-runtime (adversarial re-derivation)

CLAIM: `lookup_anchor` @RVA `0x148f0` maps `type&0x1f` to a 3-short position by indexing the
scratch table @RVA `0x220060` (stride 8) for `type>0x14`, or reading `0x6971c`/`0x6971e` for
`type==11`; `0x220060` is bss-tail (zero-on-disk) ⇒ eye/anchor not static-recoverable.

VERDICT: **CONFIRMED** (independently reproduced from a fresh disasm + section-table check).

## Fresh disassembly (`refkit.disasm(pe, 0x148f0, 0x149c4)`)

Function prologue @`0x148f0`. Argument routing: `type=ecx`(→esi/ebp), out1=`rdx`, out2=`r8`, out3=`r9`.
Zeroes all three outputs up front, then:

```
0x14924  and  esi, 0x1f                 ; type &= 0x1f
0x14927  je   0x14c1a                    ; type==0 -> zeros (early ret path)
0x1492d  cmp  esi, 0x14
0x14930  jle  0x14998                    ; type<=0x14 -> the type-11 branch
0x14932  lea  rdx, [rip + 0x20b727]      ; -> table base
0x14939  sub  esi, 0x15                  ; idx = type - 0x15
0x1493c  movsxd rax, esi
0x1493f  lea  rcx, [rax*8]               ; * STRIDE 8 *
0x14947  movzx eax, word [rcx+rdx]       ; short @ +0
0x1494e  movzx eax, word [rcx+rdx+2]     ; short @ +2
0x14957  movzx eax, word [rcx+rdx+4]     ; short @ +4  -> 3-short position into out1
0x14960  cmp  esi, 4                     ; if idx<4 also copy a 2nd 3-short block @ +0x30 into out2
0x14969  ...   [rcx+rdx+0x30 / +0x32 / +0x34]
--- type-11 branch @0x14998 ---
0x14998  cmp  esi, 0xb
0x1499b  jne  0x149c4                    ; only type==11 handled here
0x1499d  movzx eax, word [rip + 0x54d78] ; -> 0x6971c  (out1 +0)
0x149a7  movzx eax, word [rip + 0x54d70] ; -> 0x6971e  (out1 +4)
```

## RIP-relative target math (recomputed, VA base 0x180000000)

| site | insn | next-RIP | disp | target VA | RVA |
|---|---|---|---|---|---|
| 0x14932 | `lea rdx,[rip+0x20b727]` | 0x14939 | 0x20b727 | 0x180220060 | **0x220060** |
| 0x1499d | `movzx …[rip+0x54d78]` | 0x149a4 | 0x54d78 | 0x18006971c | **0x6971c** |
| 0x149a7 | `movzx …[rip+0x54d70]` | 0x149ae | 0x54d70 | 0x18006971e | **0x6971e** |

All three match the cited evidence exactly. Stride = `lea rcx,[rax*8]` = **8** (matches). Base =
**0x220060** (matches). Type gate = `type>0x14` for the table, `type==11` for the pair (matches).

## Section / zero-on-disk check (`pe.sections`)

`.data`: VA `0x4f000`, VirtualSize `0x5d3440` (vaEnd `0x622440`), **SizeOfRawData `0x1a000`**
⇒ raw-backed portion covers RVA `0x4f000..0x69000` only.

* `0x220060` > `0x69000` ⇒ **bss tail, zero-on-disk.** File offset would be `0x21ec60`, past the
  section's raw extent (file `0x4dc00..0x67c00`). `pe.get_data(0x220060,16)` returns **empty** (no
  mapped raw bytes). CONFIRMED runtime-only.
* `0x6971c`/`0x6971e` are ALSO > `0x69000` ⇒ also bss-tail zero-on-disk (consistent with the
  `curCam @0x69730` region being runtime-only). The type-11 "player/target" pair is equally
  non-static.

## Refutation conditions — none hold

* "0x220060 falling within file-backed raw data with nonzero content" — FALSE; it is `0x1b7060`
  bytes past raw end, `get_data` yields zero bytes.
* "a different stride/table base" — FALSE; stride is byte-exact 8 (`[rax*8]`), base byte-exact
  `0x220060`.

## Notes / minor nuances (do not change the verdict)

* Type-11 writes only out1+0 and out1+4 (two shorts, the +2 slot left zero), vs the table path's
  three contiguous shorts — a cosmetic detail the claim's "3-short position" phrasing glosses, but
  the anchor VALUES are runtime-only either way, so the static-recoverability conclusion is
  unaffected.
* The claim's downstream consequence ("eye/anchor not static-recoverable") is therefore sound: the
  anchor POSITIONS come from a bss buffer filled by battle/SFX setup at runtime. The static
  recoverable part is the ACCESS PATH (base, stride 8, short offsets, the type gate), not the data.
