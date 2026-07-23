# V — Adversarial verification of CLAIM `data-block-map`

Independent re-derivation of the `SummonData` (rec+0x00 target) offset map asserted in
`A2-summon-struct.md` §2/§8. Disassembly done fresh with `refkit` against
`FF9SpecialEffectPlugin.dll` (x64, base `0x180000000`). Script: `verify_a2.py` (+ inline probes).

**VERDICT: CONFIRMED.** All six offsets reproduce with the claimed width and role. No error-stub
confusion, no linear-disasm desync, no endianness/fixed-point misread affects the map.

---

## Per-offset re-derivation (every cite reproduced)

### +0x08 u32 modelId ← arg[+0x3c] — Register real body @0x15ee0
The `.pdata` funclet holding `0x15f3f` is `0x15f35..0x15fda`, but the real body starts at `0x15ee0`.
Disassembling from there (in sync):
- `0x15efc: mov rsi, rcx` — rsi = the managed model arg.
- `0x15f2b: mov rcx, qword ptr [rbx]` — rcx = rec.data (`[rbx]` = rec+0x00).
- `0x15f32: mov eax, dword ptr [rsi + 0x3c]` — eax = arg[+0x3c].
- `0x15f3f: mov dword ptr [rcx + 8], eax` — **u32 store to data+0x08**.
CONFIRMED: 32-bit field at DATA+0x08, sourced from managedArg+0x3c. (Label "modelId" is a soft
semantic read of an id pulled from the model object; the *structural* claim — u32 @+0x08 from
arg+0x3c — is exact.)

### +0x10 qword motion ptr — SetSummonMotion @0x17a10 & Draw @0x17740
- `0x17a2c: mov rax, qword ptr [r8]` (r8 = rec) → rax = data.
- `0x17a3b: mov qword ptr [rax + 0x10], rcx` — **qword motion ptr written to data+0x10** (rcx = arg).
- Draw: `0x1776c: mov rax,[rdi]` (data) → `0x17776: mov rbx, qword ptr [rax + 0x10]` — reads the same
  qword; then `0x17785: mov eax,[rbx+0xc]` consumes it as a Motion block (matches §4).
CONFIRMED: 64-bit motion pointer at DATA+0x10.

### +0x20 u32 mesh-hide bitmask — Show @0x187e0 / Hide @0x18840
- Show `0x18805: mov eax,1; 0x1880a: shl eax,cl; 0x1880c: not eax; 0x1880e: and dword ptr [r8+0x20], eax`
  — clears bit `meshIdx` (SHOW).
- Hide `0x18865: mov eax,1; 0x1886a: shl eax,cl; 0x1886c: or dword ptr [r8+0x20], eax` — sets bit (HIDE).
- In both, `r8 = [r8+rax]` = rec.data.
CONFIRMED: 32-bit bitmask at DATA+0x20, set-bit = hidden. (The native `HideMeshes` lever.)

### +0x38 qword bone-matrix array ptr, stride 0x20 — GetBonePos @0x185b0 / GetBoneMatrix @0x18630
- GetBonePos `0x185d3: mov rax, qword ptr [r10 + 0x38]` (r10 = data), then `0x185da: shl rdx,5`
  (idx × 0x20), reads `word[rdx+rax+0x14/0x18/0x1c]` — bone translation low words.
- GetBoneMatrix `0x18653: mov rax, qword ptr [rax + 0x38]`, `0x1865a: shl rcx,5` (× 0x20), then two
  `movups` copy a full 32-byte matrix (`0x1865e`,`0x18666`).
CONFIRMED: pointer at DATA+0x38 to a bone-matrix array of stride 0x20 (32-byte PSX MATRIX per bone).

### +0x40 32-byte root transform — pose evaluator @0x186a0
- `0x186b2: lea rbx, [rcx + 0x40]` (rcx = data) → rbx = &DATA+0x40.
- Identity seed of a PSX MATRIX: `[rbx]=0x1000`, `[rbx+6]=0x10000000`, `[rbx+0xe]=0x10000000`
  → diagonal 0x1000 (=1.0 in 1/4096 fixed) at m[0][0]=+0, m[1][1]=+8, m[2][2]=+0x10 (18-byte 3×3).
- Rotation from rotPtr: `movsx` of `word[rotPtr+4/+0/+2]` → RotMatrix chain `0x3910`(X)/`0x37a0`(Y)/`0x3850`(Z).
- Translation from posPtr: `[r14]/[r14+4]/[r14+8]` → `[rbx+0x14]/[rbx+0x18]/[rbx+0x1c]` (s32[3] at DATA+0x54/0x58/0x5c).
CONFIRMED: a 32-byte PSX MATRIX (rot 3×3 + s32 translation) built at DATA+0x40. The `.pdata` split at
`0x186b8` is only an unwind boundary; linear disasm continues in sync through `0x18759`.

### +0x70 qword texanim array ptr, stride 0x18 — StartSummonTexAnim @0x188a0
- `0x188cb: mov rax, qword ptr [r10 + 0x70]` (r10 = data) → texAnim base.
- Stride: `0x188c7: lea rcx,[rax+rax*2]` (idx×3), `0x188cf: lea rdx,[rcx*8]` (×8) = idx × 0x18.
- Then `or byte[rax+rdx+8],3`, `mov dword[..+0x10],0`, etc. (matches §6 TexAnim layout).
CONFIRMED: pointer at DATA+0x70 to a texanim array of stride 0x18.

---

## Skeptic checklist
- **Error-stub confusion:** avoided. Each cite was verified in the REAL body (Register @0x15ee0, not
  the naming funclet @0x15f35/0x16112; GetBoneMatrix @0x18630, not the string stub @0x16c80).
- **Linear-disasm desync:** none. Every cited instruction decoded exactly at its marked RVA; the
  pose-eval body decoded cleanly past its `.pdata` boundary.
- **Scratch-buffer mislabel:** the OFFSETS/WIDTHS/logic are recovered from code and are static truth;
  only the DATA block's runtime VALUES are unknowable (base `0x220830` region is zero-on-disk). The
  claim is about layout, which is fully derivable. Consistent with prior-round caveat.
- **Endianness/fixed-point:** not load-bearing for the offset map. The 0x1000 diagonal reads as a
  proper 1/4096 fixed-point PSX identity, corroborating the +0x40 "root transform" role.

## Residual nuance (not a refutation)
- "modelId" @+0x08 is a semantic interpretation; binary only proves `u32 @+0x08 = managedArg[+0x3c]`.
- +0x18 (`void* p18`) is NOT part of this claim and remains tentative in A2.
