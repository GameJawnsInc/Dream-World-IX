# V-M1-03 — adversarial re-derivation of `Hi_DrawEffModelByBone` (independent)

**CLAIM M1-03:** `Hi_DrawEffModelByBone(scale*, effIdx, summonIdx, boneIdx)@0x16837` copies
`summonModels[summonIdx].data->bones[boneIdx]` — a full 32-byte world matrix — verbatim into the eff
model's root at `EffData+0x40`; it parents an eff model to a bone of the live summon creature and
therefore REQUIRES an active summon model and cannot substitute for one.

**VERDICT: CONFIRMED** (with 4 corrections/refinements, none of which touch the substance).

Re-derived from scratch with `refkit` against the user's own installed DLL — x64
(`ImageBase 0x180000000`, 646 `.pdata` functions) and the x86 twin (`ImageBase 0x10000000`).
No cited byte was trusted; every one was re-disassembled at its stated RVA.

---

## 1. The refutation condition was tested and NOT met

> *"WOULD BE REFUTED BY: showing the second index argument indexes EFFARR rather than the 0x58-stride
> summon array."*

The two arrays are **provably distinct** and the function touches **both**, with different indices:

| | base RVA | stride | active flag | indexed by |
|---|---|---|---|---|
| EFFARR | `0x220230` | `0x30` | `+0x20` | arg1 (`edx`) |
| summon array | `0x220830` | `0x58` | `+0x50` | arg2 (`r8d`→`rsi`) |

Re-derived RIP arithmetic (both done by hand from the fresh disassembly):

* `0x16809 lea rax,[rip+0x209a20]` → next-insn `0x16810` + `0x209a20` = **`0x220230`** (EFFARR);
  `0x16805 lea rbx,[rax+rax*2]` + `0x16813 shl rbx,4` = **×0x30**; `0x1681a cmp byte[rbx+0x20],0`.
* `0x168ea lea rcx,[rip+0x209f3f]` → next-insn `0x168f1` + `0x209f3f` = **`0x220830`** (summon);
  `0x168f1 imul rax,rsi,0x58`; `0x168f5 cmp byte[rax+rcx+0x50],r14b` (`r14`=0 from `0x16844`).

Different base, different stride, different active-flag offset, different argument. **REFUTED-BY
condition fails; the claim stands.**

## 2. The bone read reproduces instruction-for-instruction

Fresh x64 disassembly, `0x16900`–`0x16928`:

```
0x16900  mov   rax, [rax+rcx]          ; summonModels[i].data
0x16904  test  rax,rax / 0x16907 je 0x16c80
0x1690d  mov   rax, [rax+0x38]         ; -> bone matrix array
0x16911  mov   rdx, [rbx]              ; effModels[e].data
0x16914  mov   rcx, rbp                ; boneIdx (arg3, sign-extended @0x167ff)
0x16917  shl   rcx, 5                  ; * 0x20
0x1691b  movups xmm0,[rcx+rax]      -> 0x1691f  movups [rdx+0x40], xmm0
0x16923  movups xmm1,[rcx+rax+0x10] -> 0x16928  movups [rdx+0x50], xmm1
```

32 bytes, no arithmetic in between → **verbatim**, as claimed.

### 2a. Independent corroboration #1 — MSVC inlined `Hi_GetSummonBoneMatrix` here, and the linker left the proof

The bail target for the *summon* check is the funclet `0x16c80`:

```
0x16c80  lea rdx,[rip+0x34791]   -> 0x4b418 = "Hi_GetSummonBoneMatrix () "
0x16c8e  mov r8d, esi            ; the SUMMON index
0x16c91  call [rip+0x33479] ; 0x16c97 call 0x151a0 ; 0x16c9c int3
```

while the *eff* check bails to `0x16c9d` → `0x4b258 = "Hi_DrawEffModelByBone()"` with `r8d = edx`
(the eff index). Two different error strings for two different arrays, naming the **inlinee**
`Hi_GetSummonBoneMatrix` for exactly the code block under dispute. This is independent, non-circular
evidence that `0x168ea..0x16928` *is* "get summon bone matrix".

### 2b. Independent corroboration #2 — the standalone `Hi_GetSummonBoneMatrix` is byte-identical logic

`Hi_GetSummonBoneMatrix@0x18630..0x18692` (located by its own string xref `0x18678`):

```
0x18637 imul r9,rax,0x58
0x1863b lea  rax,[rip+0x2081ee]     -> 0x18642+0x2081ee = 0x220830   (same array)
0x18642 cmp  byte[r9+rax+0x50],0
0x1864a mov  rax,[r9+rax]
0x18653 mov  rax,[rax+0x38]
0x1865a shl  rcx,5
0x1865e/0x18666 movups 32 bytes -> [r8], [r8+0x10]
0x18675 (inactive) -> error "Hi_GetSummonBoneMatrix () " -> call 0x151a0 -> int3
```

Same base, same stride, same `+0x50`, same `+0x38`, same `<<5`, same 32-byte copy. The only
difference is the destination: an out-pointer vs `EffData+0x40`.

### 2c. `+0x38` really is a bone-matrix array, and the entry really is a 32-byte PSX `MATRIX`

`Hi_GetSummonBonePos@0x185b0..0x18625` reads the *same* array
(`0x185bb lea rax,[rip+0x20826e]` → `0x220830`; `0x185d3 mov rax,[r10+0x38]`; `0x185da shl rdx,5`)
and extracts the **position** from `+0x14 / +0x18 / +0x1c` of the entry (`0x185de`, `0x185eb`,
`0x185f9`). That is exactly the PSX `MATRIX` layout: `short m[3][3]` at `0x00..0x11`, pad, then the
translation longs at `0x14/0x18/0x1c`. So each entry is a full affine 32-byte matrix, not a raw
transform pair. ✔

*Caveat on the word "world":* this disassembly proves the entry is a full 32-byte matrix and that it
is the same datum the engine hands out as a bone's **position** via `Hi_GetSummonBonePos`. That it is
in *world* rather than model-local space is inherited from the prior artifacts (`B1`,
`V-bone-matrix-array`) and is **corroborated but not re-proved here** — it is however forced to be in
the *same* space as `Hi_DrawEffModel`'s own root matrix (§4), since both feed the identical draw path.

## 3. `EffData+0x40` really is the eff model's root matrix

Not taken on faith. `Hi_DrawEffModel` (entry `0x16150`, body `0x16184`) uses the same EFFARR
(`0x16160 lea rax,[rip+0x20a0c9]` → `0x16167+0x20a0c9` = **`0x220230`**, stride `0x30` via
`lea rdi,[rax+rax*2]`+`shl rdi,4`, active `+0x20`) and its **first** act is
`0x161a1 call 0x1800186a0`, whose first real instruction is:

```
0x186b2  lea rbx,[rcx+0x40]      ; rcx = effData
```

i.e. `Hi_DrawEffModel` *builds* the matrix at `EffData+0x40` from its own args, exactly where
`Hi_DrawEffModelByBone` *substitutes* the summon bone matrix. Same slot, same downstream. Confirmed.

Further, inside `ByBone` itself, `0x16957 add rcx,0x40` passes `EffData+0x40` as the target of the
optional post-scale (§5.4). Both entry points then converge on the identical body from `0x1697b`
onward.

## 4. `REQUIRES an active summon model` — stronger than claimed

An inactive summon slot does **not** degrade gracefully. `0x168fa je 0x16c80` and
`0x16907 je 0x16c80` land in the funclet that formats the error via `0x151a0` (a `sub rsp,0x138` +
`sprintf`-shaped reporter at `0x151a0..`) and then executes `int3` at `0x16c9c` — **non-returning**.
Identical structure in the x86 twin (`0x137aa` → `call 0x10012650` → `int3` at `0x137dc`).

So: with no active summon model, `Hi_DrawEffModelByBone` cannot draw anything at all — it aborts. It
is unambiguously a *consumer* of the summon slot, not an alternative to it.

## 5. Corrections / refinements to the claim as stated

1. **The entry point is `0x167f0`, not `0x16837`.** `.pdata` lists `0x167f0..0x16837` (prologue +
   EFFARR lookup: `mov [rsp+0x20],rbx; push rbp; push rsi; push rdi; sub rsp,0x40`) and
   `0x16837..0x16c80` as two ranges of one function; `0x16837` is the **continuation chunk**, not the
   function head. Cosmetic, but a caller-side citation of `0x16837` is wrong.
   (This is *not* the cold-funclet confusion — the cold funclets are the 29-byte `0x16c80` and
   `0x16c9d`, and both were correctly excluded.)
2. **`summonIdx` is not bounds-checked.** Only the active byte is tested — there is no `cmp` against a
   length. Since the summon array is **length 1** (`Hi_RegisterSummonModel@0x15ee0`:
   `0x15f01 lea rbx,[rip+0x20a928]`→`0x220830`, `0x15f10 add rbx,0x58`, `0x15f14 cmp eax,1; jl`), any
   `summonIdx != 0` silently reads `.data` past the array. Relevant to any future authoring surface.
3. **"verbatim" is true at the copy, but the root may be post-scaled.** If `arg0` is non-NULL
   (`0x1692c test rdi,rdi`), the code materialises a scale matrix on the stack — a 16-byte identity
   template at `.rdata 0x4b700` = `00 10 00 00 00 00 00 00 | 00 10 00 00 00 00 00 00`, i.e. `m00`=`m11`
   =4096, plus `mov qword[rsp+0x30],0x1000` for `m22`=4096 — and **overwrites the three diagonal
   entries** with `word[rdi+0]`, `word[rdi+4]`, `word[rdi+8]` (`0x16945`, `0x1694e`, `0x1696c`), then
   calls `0x3b60(EffData+0x40, scaleMat, EffData+0x40)`. The identity-diagonal template is decisive:
   **`arg0` genuinely is a scale triple**, so the claim's `scale*` label is correct.
4. **x86 cited numbers all reproduce, plus the missing ones.** `Hi_DrawEffModelByBone@0x13550`
   (x86 body; string xref for `Hi_DrawEffModelByBone` = `push 0x10036f20` @`0x137c4`, for
   `Hi_GetSummonBoneMatrix` = `push 0x100370c8` @`0x137ab` — same inlining tell):
   * EFFARR: `[esi*8+0x1020819c]` data / `[esi*8+0x102081b8]` active, `esi = effIdx*5` ⇒ **stride 0x28**,
     active `+0x1c`.
   * summon: `0x135b5 imul ecx,eax,0x54` (arg `[ebp+0x10]`), `0x135b8 add ecx,0x1020869c`,
     `0x135be cmp byte[ecx+0x4c],0` ⇒ **base `0x1020869c`, stride 0x54, active +0x4c** ✔ (cited).
   * `0x135d5 mov ecx,[ecx+0x20]` (bones) ✔ (cited), `0x135db shl eax,5` (arg `[ebp+0x14]`),
     `0x135eb movdqu [eax+0x24]` / `0x135f5 movdqu [eax+0x34]` ⇒ eff root matrix at **+0x24** ✔ (cited),
     confirmed again by `0x1361b add ecx,0x24` before the scale call.
   Two independent codegens from the same source agreeing on argument order, both array identities, and
   both field offsets is about as strong as static evidence gets.

## 6. Consequence for the open question (unchanged by this verification)

`Hi_DrawEffModelByBone` is structurally a **child-attachment** op: it hangs a rigid eff model off a
bone of the live summon creature. It cannot be the creature body, and it cannot run without the
summon slot being active. Any hypothesis in which "the creature is really an eff model, the summon
slot is vestigial" has to explain why the plugin hard-aborts when the summon slot is inactive.

## 7. What this verification does *not* establish

* That the summon slot is **actually active during a real Bahamut cast** — that is a runtime fact, only
  knowable from the s52 probe / a live log, not from the DLL.
* That `Hi_DrawEffModelByBone` is actually **called** by Bahamut's command stream (a dispatch-table /
  interpreter question, out of scope for M1-03).
* The space (world vs local) of the bone matrices — §2c, inherited.
* The exact math of `0x3b60` (the scale compose) — irrelevant to the claim.
