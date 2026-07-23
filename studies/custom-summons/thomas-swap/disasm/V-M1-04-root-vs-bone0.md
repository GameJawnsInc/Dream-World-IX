# V-M1-04 — adversarial re-derivation: is `SummonData+0x40` only an ANCHOR, and is `bones[0] != DATA+0x40`?

**CLAIM UNDER TEST (M1-04):** `SummonData+0x40` is only the per-frame ANCHOR (the rot/trans/scale
arguments the `.seq` stream passes to Draw); the transform actually fed to the GTE is the composed
matrix array at `SummonData+0x38`, bone 0, whose translation equals
`rootR * motionRootTrack[frame] + rootT`. FINDINGS/B1's "`bones[0] == root == DATA+0x40`" is FALSE.

**VERDICT: CONFIRMED.** Independently re-derived from a fresh `refkit` disassembly of the user's own
`FF9SpecialEffectPlugin.dll` (x64, ImageBase `0x180000000`). Both stated refutation conditions were
tested and both FAILED to refute. Four refinements + one previously-unstated third branch are recorded
in §6; none of them weakens the claim.

All RVAs are image-base-relative. Every rip-relative target below was recomputed by hand from
`next_instruction_address + displacement` — none is taken from a prior artifact.

---

## 1. Calibration — the cited functions are real bodies, and they are CHUNKED

`.pdata` ranges (fresh `refkit.functions`):

| begin | end | note |
|---|---|---|
| `0x7820` | `0x7a31` | `build_world_matrices` chunk 1 (prologue + no-motion branches) |
| `0x7a31` | `0x7a42` | chunk 2 (falls through from `0x7a2a`) |
| `0x7a42` | `0x7de7` | chunk 3 |
| `0x7de7` | `0x83c7` | chunk 4 (contains **all** the cited motion-path RVAs `0x7edc`, `0x8039`, `0x80a6`) |
| `0x186a0` | `0x186b8` | `pose_eval` chunk 1 |
| `0x186b8`…`0x187d8` | | `pose_eval` chunks 2–4 (contains `0x18738`, `0x187b5`) |

**Trap check passed:** `func_of(0x7820)` returns only `0x7820..0x7a31`, so a naive "disassemble the
function" would have stopped 1000 bytes before the motion path and MISSED the entire composition.
The cited RVAs are inside a *different* `.pdata` chunk of the same function — they are real body code
reached by `jne 0x7a20`, not a cold error funclet (`0x3d60`, `0x41e0`, `0x40d0` have **no** `.pdata`
entry at all — they are leaf GTE helpers; disassembled linearly to their `ret`, verified non-desynced
by their clean prologue-free register-only bodies).

---

## 2. The branch structure of `build_world_matrices@0x7820` (reproduced)

```
0x7820  mov [rsp+0x18],r8      ; nodeBuf   (arg2)
0x7825  mov [rsp+0x10],dx      ; frame     (arg1)
0x782a  mov [rsp+8],rcx        ; DATA      (arg0)
0x7838  mov r14,[rcx+0x10]     ; motion clip ptr
0x783c  mov r13,r8             ; r13 = &node[0]
0x783f  mov rsi,rcx            ; rsi = DATA
0x7842  mov [rcx+0x38],r8      ; *** DATA+0x38 := nodeBuf  (the array is RE-POINTED here) ***
0x7846  test r14,r14
0x7849  jne  0x7a20            ; -> MOTION path
0x784f  mov rax,[rcx+0x30]     ; parent
0x7856  je   0x797a            ; -> ROOT-COPY branch (no motion, no parent)
        ...                    ; -> PARENT branch (no motion, has parent)
```

`0x7842` **CONFIRMED verbatim.** `DATA+0x38` is a *pointer field*, re-assigned every call — so the
correct C notation is `(*(MATRIX**)(DATA+0x38))[bone]`, matching `Hi_GetSummonBoneMatrix@0x18653`'s
own `mov rax,[rax+0x38]` chase. (M1-04 writes `*(MATRIX*)(SummonData+0x38)`; loose but harmless.)

### 2a. The ROOT-COPY branch `0x797a` — the one B1 cited — is UNREACHABLE for an animated summon

`0x797a..0x7a1f` does copy `DATA+0x40` into `node[0]`: rotation words `[rsi+0x40..0x50]` with
**columns 1 and 2 negated** (`neg cx` at `0x798a, 0x799c, 0x79b4, 0x79c6, 0x79de, 0x79ed` — keep at
index 0,3,6; negate at 1,2,4,5,7,8 ⇒ `R · diag(1,-1,-1)`) and translation `[rsi+0x54/0x58/0x5c]`
verbatim (`0x79f4-0x7a0f`).

But it is guarded by `test r14,r14 / jne` at `0x7846`, i.e. it runs **only when `DATA+0x10 == 0`
(no motion clip)**. And:

```
Hi_SetSummonMotion  real body @0x17a10  (verified: array base rip->0x220830, stride 0x58,
                                         active @+0x50, LENGTH 1 per Register@0x15f14 `cmp eax,1; jl`)
0x17a36  mov word [r8+0x54],dx    ; frame cursor := 0
0x17a3b  mov [rax+0x10],rcx       ; *** DATA+0x10 := motion clip pointer ***
```

So the moment a summon is given a motion clip — which is the entire point of an animated creature —
`0x7820` takes the motion path and the `0x797a` root-copy **never executes**. B1's proof for
`bones[0] == DATA+0x40` rests on a branch that an animated summon does not take.

Even in that branch `bones[0].R != DATA+0x40.R` (six of nine entries are sign-flipped), so the
literal identity "`bones[0] == root == DATA+0x40`" is false in *every* branch.

---

## 3. The motion path — the composition, instruction by instruction (all reproduced)

### 3a. `node[0].t` is seeded from the CLIP's root track, not from `DATA+0x54`

`r14` = motion clip; `si` = the frame argument (`movzx esi, word[rsp+0x88]`; `[rsp+0x88]` is the
`[rsp+0x10]` frame slot after `push rsi/r13/r14` + `sub rsp,0x60` = +0x78). `r13` = `&node[0]`.

```
0x7b9e  test byte [r14+0xa],1
0x7ba3  je   0x7bb8
0x7ba5  movsx eax,word [r14+4]          ; CONSTANT-channel value
0x7bb2  mov  [r13+0x14],eax             ;   -> node[0].t.x
0x7bb8  movzx eax,word [r14+4]          ; TRACK-channel: byte offset of the X track
0x7bc5  add  rax,r14
0x7bc8  movsx ecx,word [rax+rsi*2]      ;   *** indexed by the FRAME argument ***
0x7bcc  mov  [r13+0x14],ecx             ;   -> node[0].t.x
        (identical pairs for +0x18 via [r14+6] flag bit1, and +0x1c via [r14+8] flag bit2)
```
**CONFIRMED exactly as cited** (`0x7ba5`/`0x7bb2` constant, `0x7bb8-0x7bcc` per-frame track).

### 3b. `0x7edc..0x7f04` loads `DATA+0x40..+0x5C` into the GTE R/TR image at `0x211f40..0x211f5c`

Reached from `0x7de1 je 0x7edc` (the *no-parent* case, after the per-node rotation loop
`0x7c40..0x7dba`). `rsi` was restored to DATA at `0x7dc0` (`mov rsi,[rsp+0x80]`), `r13` to `&node[0]`
at `0x7dd6` (`mov r13,[rsp+0x90]`).

| instruction | reads | writes (recomputed rip target) |
|---|---|---|
| `0x7edc/0x7edf` | `[rsi+0x40]` | `0x211f40` |
| `0x7ee5/0x7ee8` | `[rsi+0x44]` | `0x211f44` |
| `0x7eee/0x7ef1` | `[rsi+0x48]` | `0x211f48` |
| `0x7ef7/0x7efa` | `[rsi+0x4c]` | `0x211f4c` |
| `0x7f00/0x7f04` | `word [rsi+0x50]` | `0x211f50` |
| `0x7f0a/0x7f0d` | `[rsi+0x54]` | `0x211f54` |
| `0x7f13/0x7f16` | `[rsi+0x58]` | `0x211f58` |
| `0x7f1c/0x7f1f` | `[rsi+0x5c]` | `0x211f5c` |

**CONFIRMED byte-for-byte, and CONFIRMED to be the GTE R/TR image** — not asserted, *proved* by
disassembling the consumer `0x3d60` (no `.pdata`; linear to its `ret` at `0x3e69`):

```
0x3d60  V0  <- s16 @ 0x211fc0(VX) / 0x211fc2(VY) / 0x211fc4(VZ)
        R   <- s16 @ 0x211f40,44,46,48,4a,4c,4e,50 (+0x211f42)     [9 entries]
        MAC = (R·V >> 12) + TR   where TR = s32 @ 0x211f54 / 0x211f58 / 0x211f5c
        MAC1/2/3 -> 0x212024 / 0x212028 / 0x21202c ; IR1/2/3 (clamped ±0x7fff) -> 0x211fe4/e8/ec
```
i.e. `0x3d60` **is** libgte `RotTrans`, and `0x211f40`/`0x211f54` **are** R and TR. Likewise `0x41e0`
is the same MAC computation **without** TR (pure `IR := R·IR >> 12`) — the rotation-only helper.

### 3c. `0x7f25..0x8034` — `node[0].R := rootR · node[0].R`, column by column

Three passes, each loading one *column* of `node[0]`'s 3×3 into IR1/2/3 and calling `0x41e0`:
`(+0x00,+0x06,+0x0c)` → `0x211fe4/e8/ec` → `call 0x41e0` → back to `(+0x00,+0x06,+0x0c)`; then
`(+0x02,+0x08,+0x0e)`; then `(+0x04,+0x0a,+0x10)`. Classic `MulMatrix0(rootR, node0R)`.

### 3d. `0x8039..0x80a6` — `node[0].t := rootR · node[0].t + rootT`

```
0x8039  movzx eax, word [r13+0x14]   -> [rsp+0x80]      ; *** LOW 16 BITS ONLY ***
0x8046  movzx eax, word [r13+0x18]   -> [rsp+0x82]
0x8053  movzx eax, word [r13+0x1c]   -> [rsp+0x84]
0x8060  movzx eax, word [r13+0x20]   -> [rsp+0x86]      ; 4th word = VECTOR pad
0x806d  mov eax,[rsp+0x80] ; mov [rip+0x209f46],eax     -> 0x211fc0  (VXY0)
0x807a  mov eax,[rsp+0x84] ; mov [rip+0x209f3d],eax     -> 0x211fc4  (VZ0)
0x8087  call 0x3d60                                     ; MAC = R·V>>12 + TR
0x808c  mov eax,[rip+0x209f92] -> 0x212024 ; mov [r13+0x14],eax
0x8096  mov eax,[rip+0x209f8c] -> 0x212028 ; mov [r13+0x18],eax
0x80a0  mov eax,[rip+0x209f86] -> 0x21202c ; mov [r13+0x1c],eax
```
**CONFIRMED.** `bones[0].t = (rootR · motionRootTrack[frame]) >> 12 + rootT`. Exactly the claim.

### 3e. The rest of the array is a real parent-chain (corroboration)

`0x81c0..0x83a8` loops the remaining nodes to `[rsp+0x98] = nodeBuf + nodeCount*0x20`
(`nodeCount = byte[resolve(DATA+0x8)+2]`, set at `0x7aba`/`0x7c1a`), each composing the parent's
already-world matrix (`byte[rbp+3]` = parent index, `shl rdi,5; add rdi,r13`) with the node's local
rotation (`0x41e0` ×2) and translation (`0x3d60` @`0x836a`). So `DATA+0x38` is unambiguously a
**world-space node array**, node 0 = root.

---

## 4. Refutation condition #1 — "0x7edc's GTE loads read something other than DATA+0x40..+0x5C"

**FAILS.** §3b table: eight loads, all `[rsi+0x40..0x5c]` with `rsi == DATA` (established at `0x783f`
and re-established at `0x7dc0` from the home slot `[rsp+0x80]` that received `rcx` at `0x782a`).

## 5. Refutation condition #2 — "the summon Draw feeds DATA+0x40 (not +0x38) to the projection pass"

**FAILS, decisively.** `Hi_DrawSummonModel@0x17740` per-mesh loop:

```
0x17910  mov  rcx,[rdi]            ; rcx = DATA
0x17913  mov  eax,[rcx+0x20]       ; hide mask
0x17916  bt   eax,ebx
0x17919  jb   0x1799c2             ; mesh hidden -> skip
0x1791f  movzx edx,bl              ; mesh index
0x17922  call 0x4eb0               ; <- the projection/matrix-install pass
...
0x179a8  call 0x56c0               ; <- the primitive emit
```

Inside `0x4eb0` (`.pdata` range `0x4eb0..0x4ff9`, `r9 := rcx = DATA` @`0x4ed7`):

```
0x4fcd  mov r9,[r9+0x38]           ; *** the node matrix array — DATA+0x38 ***
0x4fe0  mov [rsp+0xc8],r9          ; cached as the per-mesh cursor (advanced @0x551f)
...
0x51f2  lea r8,[rsp+0x48] ; mov rdx,r9 ; call 0x3b60     ; out = camera ∘ node[k]
0x53a1  movups [rip+0x20cb98],xmm0  -> 0x211f40          ; install composed R into the GTE
```

**A mechanical scan of the ENTIRE bodies of `0x4eb0` and `0x56c0` finds ZERO reads of
`[reg+0x40]/[+0x44]/[+0x48]/[+0x4c]/[+0x50]/[+0x54]/[+0x58]/[+0x5c]`** (script: filter every
instruction in both `.pdata` ranges on that offset set — empty result). The draw pass never touches
`DATA+0x40`. It reads `DATA+0x38` and nothing else from the DATA block for its transform.

---

## 6. Refinements / corrections to M1-04's wording (none change the verdict)

1. **"pose_eval writes ONLY +0x40" is very slightly overstated.** `pose_eval@0x186a0` (`lea rbx,[rcx+0x40]`
   @`0x186b2` CONFIRMED) writes the matrix exclusively at `DATA+0x40..+0x5f`, but its no-scale branch
   also writes `dword[rsi+0x78]=0x10001000` and `word[rsi+0x7c]=0x1000` (`0x187b5/0x187bc`, the default
   scale triple) and tail-calls `0x5560(DATA)`. The load-bearing part — **`pose_eval` never writes
   `DATA+0x38` or the node array** — holds.
2. **Caller list CONFIRMED exactly.** A full call-graph sweep of all 646 `.pdata` bodies finds precisely
   four `call 0x186a0`: `0x161a1` (in `0x16184`), `0x165c0` (in `0x165ae`), `0x16db4` (in `0x16d23`),
   `0x17767` (in `0x17740` = `Hi_DrawSummonModel`). Six callers of `0x7820`: `0x16234, 0x16653, 0x168d0,
   0x16e39, 0x172fd, 0x1786e`.
3. **The scale rides inside `rootR`.** `pose_eval` applies the scale vector into `DATA+0x40`'s own 3×3
   via `0x3b60(rcx=DATA+0x40, rdx=scaleVec, r8=DATA+0x40)` @`0x187ab`. So the composition is really
   `bones[0].t = (rootR·S · track) >> 12 + rootT` — the anchor's scale multiplies the motion excursion.
4. **The motion root track is fed to the GTE as s16.** `0x8039-0x8058` take `movzx word` of each s32
   node translation. Falsifiable prediction: a root track magnitude beyond ±32767 would wrap. Any
   re-implementation must truncate identically.
5. **A THIRD branch M1-04 does not mention: `DATA+0x30 != 0` (parented).** At `0x7dd2-0x7de1`, if the
   parent pointer is non-null the motion path *overwrites* `node[0]` wholesale with the parent's bone
   matrix (`0x7de7-0x7e43`) and offsets it by `DATA+0xa0/+0xa4` through `0x40d0` — **`DATA+0x40` is
   never read at all** in that case (`0x7edc` is only reached by the `je` when parent == NULL). The only
   store to a DATA-like `+0x30` anywhere in the DLL is `0x71dd` (`mov [rcx+0x30],rbp` with `rbp == 0`,
   in the shared eff-model DATA initializer `0x7120`), so a summon almost certainly runs parent-NULL —
   but that is **runtime-checkable, not statically proven**, because the summon DATA block is allocated
   outside this DLL. A probe should log `DATA+0x30` once and assert it is 0.

---

## 7. Operational consequence (why the s52 ROOT probe mistracked)

`SfxMeshProbe.cs:340` reads `rootOff = x64 ? 0x40 : 0x24` — i.e. it logs **the anchor**. Under §3 the
creature's actual root world matrix for an animated summon is `bones[0]`, and the anchor contributes
only the *rigid part* of it; the entire animated excursion lives in the clip's root track. That is
consistent with the reported ~40,000-unit offset, though this analysis proves the *mechanism*, not
that this specific magnitude is fully explained by it (the residual could also involve the ±32767
truncation of §6.4 or a parented case per §6.5).

**The corrected read** (still passive, still no DLL patch, still x64-only offsets):

```
rec   = moduleBase + 0x220830            // stride 0x58, LENGTH 1, active @+0x50
data  = *(void**)(rec + 0x00)
bones = *(void**)(data + 0x38)           // re-pointed every Draw -> read AFTER the native tick
root  = bones + 0                        // 32-byte PSX MATRIX: s16 R[9] @+0x00 (/4096), s32 t @+0x14/+0x18/+0x1c
```

This is exactly what `Hi_GetSummonBoneMatrix@0x18630` does (`mov rax,[rax+0x38]`; `shl rcx,5`;
two `movups`), so the read path is the game's own. `DATA+0x38` points into a per-frame bump arena
whose cursor lives at `[0x66c68+0x24]` and is advanced by `nodeCount*0x20` per Draw — the memory is
valid until the arena recycles, so the read must happen in the same frame, after `SFX_Update`.

## 8. x86 cross-check (partial — and it yields a CORRECTION)

`Hi_SetSummonMotion` located in the x86 build by its own error string (`0x370c8`, referenced by an
absolute `push imm32` at `0x137aa`; the x86 build has no `.pdata`, so only tight, prologue-anchored
windows were disassembled):

```
x86 0x13f40:  push ebp; mov ebp,esp
       0x13f43:  mov ecx,[ebp+0xc]          ; idx
       0x13f46:  imul eax,ecx,0x54          ; *** stride 0x54 (x64: 0x58) ***
       0x13f49:  add eax,0x1020869c         ; *** array base RVA 0x20869c (x64: 0x220830) ***
       0x13f4e:  cmp byte [eax+0x4c],0      ; *** active @+0x4c (x64: +0x50) ***
       0x13f5c:  mov word [eax+0x50],cx     ; frame cursor @+0x50 (x64: +0x54)
       0x13f63:  mov [edx+0xc],eax          ; *** motion clip @ DATA+0x0c (x64: DATA+0x10) ***
```

**Every x64 DATA/record offset shifts in the x86 build** (pointer-width members). Consequence: any
probe or parser must not reuse x64 offsets on x86. I did **not** verify `SfxMeshProbe`'s x86
`rootOff = 0x24`, nor the x86 node-array offset — both remain UNVERIFIED, and the x86 analogue of the
`0x7820` composition was not re-derived (linear disassembly desyncs badly there; it would need an
anchored entry point). The x86 evidence is therefore *supporting* (same record/array/motion-field
architecture) rather than a full independent confirmation of the composition.

## 9. Provenance

Read-only static analysis of the user's installed `FF9SpecialEffectPlugin.dll` plus one `grep` of
`Memoria/Battle/SFX/SfxMeshProbe.cs`. Output is RVAs, mnemonics, struct offsets. No game content
extracted, no binary written, no DLL modified.
