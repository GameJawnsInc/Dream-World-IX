# V-M1-02 — adversarial verification: "an eff model is rigid and single-matrix"

**Claim under test (M1-02, from `M1-effmodel-array.md` §0.1 / §5 / §6.2):** every one of the five
`Hi_Register*EffModel` bodies stores `0` into `DATA+0x10` (the motion-clip pointer), and
`build_world_matrices@0x7820` branches on that field, emitting exactly ONE 32-byte matrix and returning
`cursor+0x20` when it is NULL — therefore an eff model is rigid and cannot be the animated creature.

**VERDICT: CONFIRMED** — every cited RVA, opcode and constant reproduced from a *fresh* disassembly of
the user's own `FF9SpecialEffectPlugin.dll`; both stated refutation conditions were hunted image-wide and
neither is met in any designed code path. Two corrections to the claim's *wording* follow in §5 — they do
not overturn the conclusion, but one of them (the consumer DOES walk `boneCount` matrices) matters
directly to the format/re-import pillar and must not be lost.

All RVAs image-base-relative (x64 `ImageBase 0x180000000`, x86 `0x10000000`). Helpers added this pass —
committable, read the user's own DLL, print RVAs only: `v_m1_02_a.py` (locate the five bodies),
`v_m1_02_b.py` (image-wide `[reg+0x10]` store census), `v_m1_02_c.py` (EFFARR xref census + the two
non-zero writers), `v_m1_02_d.py` (the `.pdata`-blind-spot gap sweep), `v_m1_02_e.py` (indexed stores /
block copies / `0xC8` sizes).

---

## 1. Leg A — `[DATA+0x10] = 0` in all five Registers: EXACT MATCH

Bodies located independently by debug-string xref (`v_m1_02_a.py`); in this family the string xref lands
inside the real body (the error stub is inline at the tail), so there is **no cold-funclet confusion**:

| variant | `.pdata` range | the store | zero source |
|---|---|---|---|
| `Hi_RegisterSolidEffModel` | `0x15ac0..0x15b66` | `0x15b17 mov qword [rax+0x10], rdi` | `xor edi,edi` @`0x15aca` |
| `Hi_RegisterGouEffModel` | `0x15b70..0x15c1a` | `0x15bcb mov qword [rax+0x10], rdi` | `xor edi,edi` @`0x15b7a` |
| `Hi_RegisterTexEffModel` | `0x15c20..0x15d24` | `0x15caf mov qword [rax+0x10], r14` | `xor r14d,r14d` @`0x15c41` |
| `Hi_RegisterTexListModel` | `0x15d30..0x15e06` | `0x15d9d mov qword [rax+0x10], rbp` | `xor ebp,ebp` @`0x15d44` |
| `Hi_RegisterTexPtrModel` | `0x15e10..0x15ed5` | `0x15e7c mov qword [rax+0x10], rbp` | `xor ebp,ebp` @`0x15e24` |

`rax` is the DATA pointer in every case (`mov rax, qword ptr [rbx]` immediately before, `rbx` = the EFFARR
slot). EFFARR identity re-derived, not taken on trust: `0x15acc lea rbx,[rip+0x20a75d]`, next instruction
`0x15ad3` ⇒ **`0x220230`**; gate `cmp byte [rbx+0x20], dil` @`0x15ad5`; `add rbx,0x30` @`0x15add`;
`cmp eax,0x20; jl` @`0x15ae1`. 32 slots, stride `0x30`, active `+0x20`. ✔

**x86 cross-check (independent codegen, same source):** `Hi_RegisterSolidEffModel@0x12d80` —
`mov esi,0x1020819c` (EFFARR), `cmp byte [esi+0x1c],0`, `add esi,0x28`, `cmp eax,0x20; jl`, then
**`0x12dcd mov dword ptr [eax+0xc], 0`** — the pointer-size-shifted motion field, explicitly zeroed. ✔

## 2. Leg B — the `0x7820` branch and the one-matrix rigid path: EXACT MATCH

`.pdata` splits the function into chained chunks `0x7820/0x7a31/0x7a42/0x7de7` (one logical body
`0x7820..0x83c7`). Fresh disassembly of `0x7820..0x7a42`:

```
007838  mov  r14, qword ptr [rcx + 0x10]     ; <- the motion-clip field
007842  mov  qword ptr [rcx + 0x38], r8      ; DATA+0x38 := this frame's matrix block
007846  test r14, r14
007849  jne  0x180007a20                     ; motion path
00784f  mov  rax, qword ptr [rcx + 0x30]     ; parent link
007856  je   0x18000797a                     ; -> RIGID path
...
00797a..007a0f   ONE 32-byte MATRIX: 9x s16 rot @ +0x00..+0x10 (cols 1,2 NEGATED -> M*diag(1,-1,-1)),
                 3x s32 translation @ +0x14/+0x18/+0x1c copied verbatim from DATA+0x54/+0x58/+0x5C
007a12  lea  rax, [r13 + 0x20]               ; return cursor + 0x20  == exactly one matrix
```

Every cited address is correct to the byte. **Additional finding the claim did not cite:** the *parented*
path (`DATA+0x30 != 0`, `0x785c..0x7979`) also returns `lea rax,[r13+0x20]` @`0x7961` — so **both**
non-motion paths emit exactly one matrix. The claim is if anything understated.

**Second corroboration the claim did not cite (strong):** all six call sites of `0x7820` were enumerated
(`0x16234`, `0x16653`, `0x168d0`, `0x16e39`, `0x172fd`, `0x1786e`). The five **eff** draws all pass
`edx = 0` — `xor edx,edx` @`0x16232`, `0x16651`, `0x168cb`, `0x16e37`, `0x172fb` — i.e. *frame 0*, a
meaningless argument for a rigid model. Only `Hi_DrawSummonModel` passes a real frame index:
`0x17868 movzx edx, bp`. The frame axis exists solely on the summon side.

## 3. Refutation hunt #1 — "a code path that assigns a non-zero motion pointer to an EFFARR slot"

Exhaustive census of every write that can land on `ModelData+0x10`:

* **`.pdata` functions** (`v_m1_02_b.py`): 161 `mov qword [reg+0x10], src`. Discarding the `[rsp+0x10]`
  prologue spills, the writers of a *heap* `+0x10` in the model subsystem are exactly:
  the five eff Registers (**zero**), `0x15fc6` and `0x17a3b`.
* **`0x15fc6`** is inside `Hi_RegisterSummonModel` (entry `0x15ee0`, chained chunk `0x15f35`): its base
  literal is `lea rbx,[rip+0x20a928]` → **`0x220830`**, stride `0x58`, bound `cmp eax,1`, active `+0x50`.
  The **SUMMON** array. It cannot reach EFFARR.
* **`0x17a3b`** is `Hi_SetSummonMotion@0x17a10`: `movsxd rax,edx; imul r8,rax,0x58;
  lea rax,[rip+0x208e0e]` → **`0x220830`**; gate `cmp byte [r8+0x50],0`. Also SUMMON-only.
* **`.pdata`-invisible leaves** (`v_m1_02_d.py` — the blind spot M1 §12(d) itself flagged, and which hides
  `Hi_InitEffModel@0x15940`): 353 gaps / 13 156 bytes swept from every 16-byte anchor. Four `+0x10`
  stores, all unrelated container initialisers (`0x324fb` stride-0x38 table, `0x34355` stride-0x6c table,
  `0x4883f`/`0x48887` `-1` fills). `Hi_InitEffModel` itself was read in full: it writes `slot+0x00` from
  the pool cursor (`0x15982`, `add rcx,0xc8`) and never touches `DATA+0x10`. Same for the summon-side
  init leaf `0x15a20` (stride `0x58`) and the two reset leaves `0x159f0` / `0x15aa0`.
* **Aliasing / block writes** (`v_m1_02_e.py`): **zero** indexed `qword [reg+reg*n+0x10]` stores; **zero**
  `rep movs` anywhere in `.text` (all "movs" hits are SSE `movsd` scalar loads); the only `0xC8`
  block-size arithmetic in the image is the two pool loops. No memcpy can smuggle a motion pointer in.
* 16-byte SSE stores overlapping `+0x10` exist at `0x1866b` (`Hi_GetSummonBoneMatrix`, writing the
  *caller's* out-buffer), `0x3130e`, `0x31bbe`, `0x48676` — none of those functions appears in the EFFARR
  xref census (`v_m1_02_c.py`: 0x15200, 0x159a0, the five Registers, 0x16150, 0x16570, 0x167f0, 0x16cc0,
  0x17190, 0x17ae0, 0x17b30, 0x18000, 0x18990, 0x189f0, 0x18a40, 0x18a90, 0x18c00, 0x30c20 — plus the
  two `.pdata`-invisible init leaves).

⇒ **No designed path exists. Refutation #1 fails.**

**One honest hole, stated in full (pathological, not a refutation).** `Hi_SetSummonMotion`'s index is
**sign-extended and unbounded** (`movsxd rax, edx` @`0x17a14`), and its caller — the mega-interpreter at
`0xf87e` — takes that index from the effect's own command stream: `mov edx, dword ptr [rbx+r13+0xcac]`
@`0xf873`. EFFARR sits *below* the summon array, and `0x220830 − k·0x58` lands exactly on an EFFARR slot
base for `k ≡ 0 (mod 6)`: `k=6` → slot 21, `k=12` → slot 10. So a stream carrying model index `−6` would
gate on EFFARR slot 22's active byte and then write a real motion pointer into EFFARR[21]`.data+0x10`.
This is an out-of-range-index bug, not a mechanism; stock `ef###.bytes` would have to carry a negative
summon-model index. It cannot explain a stock cast (where the summon slot is active and drawn), and it is
*not* a way to author an animated eff model — but any future `.seq` linter should reject negative model
indices for exactly this reason.

## 4. Refutation hunt #2 — "an eff Draw that loops over more than one output matrix"

The **producer** never emits more than one for an eff model (§2: both non-motion paths return
`cursor+0x20`). But the **consumer is shared and it does loop.** `Hi_DrawEffModel` calls the per-mesh
routine `0x4eb0` at `0x162d9` (`call 0x180004eb0`, `rcx = DATA`, `dl = meshIdx`), and inside it:

```
004fcd  mov   r9, qword ptr [r9 + 0x38]      ; r9 := DATA->bones  (the matrix block)
004fdc  movzx eax, byte ptr [rdx + 2]        ; boneCount, from the GEOMETRY header
004ff3  je    0x180005544                    ; boneCount == 0 -> nothing
005012  mov   qword ptr [rsp + 0xb0], rax    ; loop counter := boneCount
005001  lea   r10, [r9 + 0x1c]               ; &bones[i].t.z
...
00550c  add   r9,  0x20                      ; <<< advance ONE MATRIX per bone
005510  add   r10, 0x20
005514  dec   rax
00552c  jne   0x180005020                    ; <<< loop over boneCount matrices
```

`byte[geom+2]` is the same field `0x7820`'s motion path reads as its bone count (`0x7aba movzx r10d,
byte ptr [rcx+2]`), so this is unambiguously a per-bone skinning walk, and `Hi_DrawEffModel` and
`Hi_DrawSummonModel` both go through it.

**Interpretation — this is a wording correction, not a refutation.** With the motion pointer NULL only
`bones[0]` is ever *written*; the eff model therefore has no per-bone animation and no deformation. What
the loop shows is that nothing *structurally forbids* an eff geometry blob from declaring
`boneCount > 1` — it would simply read `bones[1..N−1]` out of the packet scratch (uninitialised /
stale), a buffer over-read. The DLL's implicit contract is **eff geometry must be single-bone**.

## 5. Corrections to carry forward

1. **"single-matrix" describes the PRODUCER, not the pipeline.** The rigid path *fills* one matrix; the
   shared per-mesh consumer `0x4eb0` *reads* `boneCount` of them at stride `0x20`. A format writer/linter
   for eff models must therefore assert `boneCount == 1` in the geometry header itself — the DLL will not
   catch it, it will read garbage. (Whether any stock eff blob violates this is **unverified** — it needs
   a real `ef###.bytes` geometry parse, out of scope here.)
2. **Rigid ≠ static.** `pose_eval@0x186a0` rewrites `DATA+0x40` from the Draw arguments *every frame*
   (call sites `0x161a1`, `0x165c0`, `0x16db4`, `0x17767`), and `Hi_DrawEffModelByBone` copies a live
   summon bone matrix straight into `EffData+0x40`. So an eff model can translate/rotate freely across a
   cast and be a genuinely moving on-screen object — it just cannot *deform*. Anyone using this verdict to
   dismiss EFFARR as a tracking target for **rigid props** would be over-reading it; what is excluded is
   an eff model being a skeletally animated creature.

## 6. What this verification does NOT establish

* Nothing here is about **effect 194 (Bahamut) specifically** — it is pure static structure. Whether the
  visible creature in that cast is the summon slot remains a runtime question (M1 §10's one-cast `EFF`
  row settles it empirically and is still worth doing).
* The `.pdata` gap sweep is a *union over 16-byte anchors*; it is thorough but not a proven-complete
  disassembly. Its four hits were all inspected by hand and are unrelated to `ModelData`.
* No claim is made about the x86 build's `0x7820` analogue; the x86 leg verified here is only the
  `[data+0x0c] = 0` store in `Hi_RegisterSolidEffModel@0x12d80`.

## 7. Provenance

Read-only static analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (x64 and x86): RVAs,
mnemonics, struct offsets, control flow. **No DLL was modified, patched or redistributed.** No stock
geometry, animation or texture bytes were read, extracted or written anywhere. The helper scripts added
here read the installed DLL at runtime and print addresses only.
