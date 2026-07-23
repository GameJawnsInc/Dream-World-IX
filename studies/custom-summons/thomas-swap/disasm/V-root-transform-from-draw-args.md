# Adversarial verification: root-transform-from-draw-args

**Claim id:** root-transform-from-draw-args
**Verdict: CONFIRMED** (independently re-derived from the DLL; all cited RVAs reproduce exactly)

## What the claim asserts
The creature's per-frame root world transform (`SummonData+0x40`) is rebuilt each Draw by the
pose evaluator at `0x186a0`, from a rotation-angle vector and a translation vector passed by
register into `Hi_DrawSummonModel` — NOT sourced from a persistent field of the struct or a global.

## Independent re-derivation (all RVAs are image-relative, base 0x180000000)

### 1. The call site — DrawSummon @ real body 0x17740..0x179f2 (690 bytes)
`0x17740` has a normal MSVC prologue (saves rbx/rbp/rsi/r12/r14/r15) ⇒ it is the true body, not
the 29-byte error funclet at `0x179f2` (which only names the fn for the malloc panic).

Register shuffle immediately before the pose-eval call:
```
0x1774f  mov r9, r8        ; r9  <- DrawSummon incoming r8  (4th vector = SCALE)
0x17752  mov r8, rdx       ; r8  <- DrawSummon incoming rdx (TRANSLATION vector)
0x1775a  mov rdx, r10      ; rdx <- r10                     (ROTATION-angle vector)
0x17767  call 0x1800186a0  ; pose evaluator
```
`rcx` is passed through untouched = the SummonData/object pointer. So into the pose-eval:
`rcx`=object, `rdx`=rotation vec, `r8`=translation vec, `r9`=scale vec. **Confirms `0x17767 call 0x1800186a0`.**

### 2. The pose evaluator — 0x186a0..0x187d8 (one logical fn, 4 contiguous .pdata funclets)
```
0x186b2  lea rbx,[rcx+0x40]            ; rbx = SummonData + 0x40  (a PSX MATRIX / GsCOORD)
0x186ca  mov [rbx+0xe]=0x10000000      ; init the 3x3 rotation matrix (m[3][3] s16 @ +0..+0x11)
0x186d1  mov [rbx+6]=0x10000000
0x186d8  mov word [rbx+4]=0
0x186dc  mov [rbx]=0x1000
0x186e4  mov r12,rdx  ; 0x186e1 mov r14,r8  ; 0x186c7 mov r15,r9
0x186ea  test rdx,rdx ; je 0x18710         ; rdx==NULL -> identity rotation
  0x186ef movsx ecx, word [rdx+4]   ; rz (s16) -> 0x180003910
  0x186fb movsx ecx, word [r12]     ; rx = [rdx+0] (s16) -> 0x1800037a0
  0x18708 movsx ecx, word [r12+2]   ; ry = [rdx+2] (s16) -> 0x180003850  (via 0x18726)
0x18733  test r14,r14 ; je 0x1874e        ; r8==NULL -> zero translation
  0x18738 mov eax,[r14]   ; mov [rbx+0x14],eax   ; t[0] <- [r8+0]  (s32)
  0x1873e mov eax,[r14+4] ; mov [rbx+0x18],eax   ; t[1] <- [r8+4]
  0x18745 mov eax,[r14+8] ; mov [rbx+0x1c],eax   ; t[2] <- [r8+8]
0x1875e  test r15,r15 ; je 0x187b2           ; r9==NULL -> default scale 0x1000 @ [rsi+0x78]
  0x18763 movzx ...[r15/+4/+8] ; call 0x180003b60 ; SCALE from the 4th vector (u16)
```

### 3. The two refutation conditions — both FALSE
* **"sources rot/pos from the struct or a global instead of rdx/r8"** — FALSE. Rotation angles are
  read exclusively from `[rdx+0/2/4]`; translation exclusively from `[r8+0/4/8]`. The only non-arg
  path is the NULL-fallback (identity rotation / zero translation) — never a struct field, never a
  global. No memory load other than the argument-pointer dereferences feeds rot/pos.
* **"does not write DATA+0x40"** — FALSE. `rbx = rcx+0x40` and every write (matrix init + rotation
  concat output + translation `[rbx+0x14/0x18/0x1c]`) lands in that region.

So the coordinate matrix at `+0x40` is a **per-call scratch OUTPUT**, fully overwritten each Draw
from the argument vectors. The *inputs* are not persisted in the struct — matching "not stored
persistently."

## Layout note (PSX MATRIX at SummonData+0x40)
`short m[3][3]` (18 B, +0x00..+0x11) then 2 pad then `long t[3]` at +0x14/+0x18/+0x1c. The
translation offsets in the code (`+0x14/+0x18/+0x1c`) are exactly `t[0..2]`, confirming this is a
standard libgte `MATRIX`. Rotation is fixed-point (s16, ONE=4096); translation is s32 world units.
Helpers `0x3910/0x37a0/0x3850` = the RotMatrix{Z,X,Y}-style concat chain; `0x3b60` = ScaleMatrix.

## Corrections / enrichments to the prior note (do not change the verdict)
1. The prior evidence stops at `[r8]/[r8+4]`; there is a **third** translation write at `0x18745`
   (`[r8+8] -> [rbx+0x1c]`, the z component). Full 3-component translation.
2. There is a **fourth argument** (`r9`, a SCALE vector) consumed at `0x18763` via `0x3b60`; the
   root transform is rot **+ trans + scale**, not just rot+trans.
3. Register-provenance precision: into the *pose-eval* it is genuinely `rdx`=rotation, `r8`=translation
   (as the cited evidence says). But inside *DrawSummon* the rotation vector arrives in **r10** and is
   moved to rdx at `0x1775a`; DrawSummon's own incoming `rdx`→r8 is the translation and incoming
   `r8`→r9 is the scale. The `r10` live-on-entry input means `0x17740` is an internal helper with a
   non-standard (5-pointer) register convention, reached from an exported SFX_* wrapper — not the
   C-ABI entry the C# `DllImport` binds directly. This does not affect the claim: all three vectors
   are register inputs to the Draw routine, none come from the struct/global.

## Runtime-vs-static honesty
The *layout and logic* are fully static-recoverable (above). The *runtime VALUES* of the rot/trans/
scale vectors are produced by the caller each frame and are not in the DLL image. Recovering a
creature's true per-frame transform therefore still requires intercepting these argument vectors at
the Draw call (or the `+0x40` matrix immediately after) at runtime — it cannot be reconstructed from
DLL bytes alone. This is consistent with, and sharpens, the prior "no data-side method recovers it."
