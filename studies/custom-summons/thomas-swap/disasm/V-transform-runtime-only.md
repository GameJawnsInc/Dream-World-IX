# V — CLAIM `transform-runtime-only` (adversarial re-derivation)

**VERDICT: CONFIRMED** (with one correction to a piece of the *cited evidence* — the claim
STATEMENT itself is fully substantiated; the "allocated by FUNC@0x30c20" wording is imprecise).

Claim: *The summon DATA block (bones at +0x38, root at +0x40) is a runtime scratch allocation whose
values are zero on disk; the transform is only recoverable at runtime via a Hi_DrawSummonModel arg
probe or per-frame Hi_GetSummonBoneMatrix dump.*

All RVAs re-derived fresh with refkit against the installed x64 DLL (image base 0x180000000).
Scripts: `v_a2_claim.py`, `v_a2_ctx.py`, `v_a2_root.py`, `v_a2_final.py` (this dir).

---

## 1. 0x220830 is ZERO ON DISK — CONFIRMED (the refutation condition, NOT met)

`.data` section: `VA=0x4f000  VSize=0x5d3440  SizeOfRawData=0x1a000  PtrRaw=0x4dc00`.
0x220830 sits at **offset 0x1d1830 inside `.data`**, which is `>> SizeOfRawData 0x1a000` →
beyond the raw image → **implicitly zero (bss-style tail of a huge virtual `.data`)**.
`pe.get_data(0x220830,0x10)` and the spans at −0x20 / +0x38 / +0x40 all return **all-zero**.
The huge `VSize` with tiny `RawSize` is the classic uninitialized-scratch signature. There is
**no static table** of bone/root matrices anywhere behind this pointer — the refutation condition
("non-zero initialized bytes at/behind 0x220830, or a static matrix table") is **not satisfied**.

## 2. The record base is written at RUNTIME by code — CONFIRMED (both sites reproduced)

- `xrefs_to(0x220830)` reproduces **17** references. The two *stores* (writes) are exactly the cited pair:
  - `FUNC@0xeea4 : mov qword ptr [rip+0x210f1c], r12  @0xf90d  -> 0x220830`  (clear path)
  - `FUNC@0x30c20 : mov qword ptr [rip+0x1efb60], rbx @0x30cc9 -> 0x220830`  (init path)
- Every other xref is an accessor `lea` computing the base for `imul idx,0x58` (Register / SetMotion /
  SetMotFrame / GetBonePos / GetBoneMatrix / Draw / Show / Hide / TexAnim / ModifyAbr / ModifyRGB).
  Both writes also touch **rec+0x50** (the active flag, RVA 0x220880): `@0x30cc3 mov [..],ebx` and
  `@0xf906 mov [..],r12d`. So the two functions are a matched **init-to-zero / teardown-to-zero** pair.

### Correction to the cited evidence (does NOT change the verdict)
The cited evidence calls FUNC@0x30c20 the site that *allocates* rec[0].data. It is not an allocation —
**`@0x30c20 push rbx ; @0x30c2d xor ebx,ebx`**, so `rbx = 0` at the `@0x30cc9` store. FUNC@0x30c20
therefore writes **NULL** into rec[0].data (and 0 into rec+0x50) — it is a **zero-initializer**, not the
allocator. This actually *strengthens* the claim: the field is both zero-on-disk AND explicitly
zeroed at runtime init; the real DATA-block heap pointer is installed later by the Register/alloc
family. The claim STATEMENT ("runtime scratch … zero on disk") stands; only the word "allocated" in the
evidence is loose.

## 3. bones @ DATA+0x38 live behind a runtime pointer — CONFIRMED (double indirection)

`Hi_GetSummonBonePos@0x185b0` and `Hi_GetSummonBoneMatrix@0x18630` both:
1. `lea rax,[rip..]->0x220830 ; imul idx,0x58` — record base + stride 0x58 (re-confirmed).
2. `cmp byte[rec+0x50],0 ; je error` — gate on the active flag.
3. `mov rax,[rec+0x00]` — load the **DATA pointer** (a runtime heap address; null on disk → error branch).
4. `mov rax,[rax+0x38]` — **bones array = DATA+0x38**.
5. `shl idx,5` (**stride 0x20**); GetBonePos reads `word[bone+0x14/+0x18/+0x1c]` (translation);
   GetBoneMatrix `movups` copies the full **32 B** matrix. Both re-derived instruction-for-instruction.

Because 0x220830 (rec+0x00) is zero on disk, the DATA pointer is null until runtime; the bone matrices
sit two indirections deep behind it → **their values are unrecoverable statically**. Only
`Hi_GetSummonBoneMatrix(0,boneIdx,&out)` reads them at runtime.

## 4. root @ DATA+0x40 is built PER-DRAW from caller ARGS — CONFIRMED

Pose evaluator (`0x186a0`, real body continues past the .pdata funclet split at 0x186b8):
- `lea rbx,[rcx+0x40]` → works on **DATA+0x40** (`rcx` = DATA ptr).
- Seeds an **identity** matrix from code immediates only: `ebp=0x1000` (1.0 in 1/4096 fixed) → `[rbx]`;
  `0x10000000 → [rbx+6],[rbx+0xe]`. These are constants in `.text`, **not** a stored transform.
- **Rotation ← `rdx` (rotPtr arg):** `movsx word[rdx]/[rdx+2]/[rdx+4]` fed to the PSX RotMatrix chain
  `0x3910`(X)→`0x37a0`(Y)→`0x3850`(Z) @0x186ef–0x18729.
- **Translation ← `r8` (posPtr arg):** `[r8]/[r8+4]/[r8+8] → [rbx+0x14]/[rbx+0x18]/[rbx+0x1c]`
  @0x18738–0x18749 (root translation at DATA+0x54/0x58/0x5c).

So the creature's root world transform is **recomputed every Draw from `(rot,pos)` arguments** the
managed SFX/camera code supplies; it is not persisted as a static asset. (Minor note: r14=r8 branches
to a zero-fill at 0x1874e when posPtr is null — the default, not a stored value.)

## 5. r12 clear value (minor) — PLAUSIBLE
At the clear `@0xf90d`, r12 stores into both rec+0x00 and rec+0x50 (active). r12d is `xor`-zeroed at
several sites in the same function (0x10599, 0x11555, 0x11721, 0x11e61) though all *after* 0xf90d in
listing order; the semantics (clearing the active flag on teardown) require r12=0 here and MSVC keeps
r12 as a zero register through the block. Not load-bearing for the verdict — the write being at
runtime is what matters, not its exact zero value.

---

## Bottom line
Every substantive element of the claim reproduces independently: **zero-on-disk bss scratch**,
**runtime-written record base**, **bones two indirections deep behind a runtime pointer (DATA+0x38,
stride 0x20)**, **root rebuilt per-Draw from arguments (DATA+0x40)**, **no static matrix table**.
The transform is recoverable ONLY at runtime — via a `Hi_DrawSummonModel` (rdx=rot, r8=pos) arg probe
for the root, or a per-frame `Hi_GetSummonBoneMatrix(0,bone,&out)` dump for the bones. **CONFIRMED.**
Sole caveat: cited FUNC@0x30c20 is a zero-INITIALIZER (rbx=0 via `xor ebx,ebx@0x30c2d`), not the
allocator — a wording fix to the evidence, not a defect in the claim.
