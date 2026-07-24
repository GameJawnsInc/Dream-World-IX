# VERIFY-EULER.md — adversarial verify pass of EULER.md (Milestone 0)

**Charge:** try to REFUTE the round-1 verdict `R_local = Rz(az)·Ry(ay)·Rx(ax)`, standard cos/sin
(cos on diagonal), pre-multiply, no transpose — by INDEPENDENT re-derivation.

**RESULT: could NOT refute. The convention is CONFIRMED by the fully-reproducible disasm (the direct
authority, and per EULER.md's own design the SOLE authority for pre-vs-post) plus my own
discrimination math.** BUT one required leg is dead: the live probe log has been OVERWRITTEN, so the
empirical 1072-frame discrimination table is **currently unreproducible**. This is a disasm+math
confirmation, not the disasm+log triangulation round-1 claimed. `refuted = false`, confidence
**medium** (the log loss + the fact that the clip-2 pre/post *direction* now rests entirely on the
disasm).

Scratch scripts: `m0/verify_euler/` (`dump_disasm.py`, `read_consts.py`, `my_validator.py`).

---

## Check 1 — re-run `euler_validate.py`: FAILS TO REPRODUCE (the log is gone)

`py euler_validate.py` now parses **1 cast / 0 matched frames** and crashes (`ZeroDivisionError` at
line 468). Cause: `C:/…/FINAL FANTASY IX/sfxmeshprobe.log` (mtime **2026-07-23 16:40**, i.e. AFTER
EULER.md was written 13:31) is a **different capture** — the s47+s48 mesh/camera/raw-primitive probe:

| what EULER.md used | what the log holds now |
|---|---|
| 5 Bahamut casts, frames ~11..561 | effectId **0**, single frame **42** |
| ROOT rows (anchor matrix) | **0 ROOT rows** |
| BONES rows | **0 BONES rows** |
| MODEL kind=S with live matrices | **1** kind=S row, all-zero (`bones32=00000000`, skipped) |
| 1072 clean matched frames | **0** |

The `R_frame = colnorm(R_anchor)⁻¹·colnorm(composed)` recovery needs BOTH ROOT and MODEL kind=S; there
are no ROOT rows, so every frame yields `R_frame=None`. Searched for a saved copy (study tree, SCRATCH,
scratchpad, game dir, git history) — **none exists** (the log is a user file, never committed; round-1's
structured hand-off failed before it was snapshotted). **The empirical table in EULER.md §2/§2.1/§3
cannot be reproduced against the current install.**

## Check 4 — disasm re-check vs the user's own DLL: FULLY CONFIRMED (two independent ways)

Re-derived from scratch (`dump_disasm.py`, my own byte-level interpretation) AND cross-checked against
round-1's `euler_validate.confirm_disasm()` — both agree on every point. DLL =
`…/FINAL FANTASY IX/x64/FF9_Data/Plugins/FF9SpecialEffectPlugin.dll` (ImageBase `0x180000000`).
*(NB: the task's literal path `…/x64/FF9SpecialEffectPlugin.dll` does not exist; refkit's real path,
with the `FF9_Data/Plugins/` segment, is the one present and the one used.)*

- **cos/sin (std, no swap).** `Rx@0x37a0`: first thunk `0x37e0→0x49cd2` = `MSVCR120!cos`, its
  `*4096.8`-truncated result stored on the **diagonal** (`[rsp+0x28]`=m11, `[rsp+0x30]`=m22); second
  `0x37f4→0x49ce4` = `MSVCR120!sin`, stored **off-diagonal** with `-S` on m12 (`0x3832 neg ax →
  [rsp+0x2a]`) and `+S` on m21 (`[rsp+0x2e]`); m00=`0x1000`=1.0. ⇒ `Rx=[[1,0,0],[0,c,-s],[0,s,c]]`.
  `Ry@0x3850`=`[[c,0,s],[0,1,0],[-s,0,c]]`, `Rz@0x3910`=`[[c,-s,0],[s,c,0],[0,0,1]]` — all standard,
  matching `euler_validate._axis_mats` byte-for-byte.
- **matmul `0x3450` = `OUT = rcx·rdx` into `[r8]`.** Traced the arithmetic: `OUT[0][0] =
  A0·B0+A1·B3+A2·B6 = A.row0·B.col0` with A=rcx, B=rdx (verified on OUT[0][0] and OUT[0][1]).
  Output packed to `r8` (`0x373e mov rdx,r8`; `0x3750` pack; `0x3769 mov rax,r8`; returns r8).
- **pre-multiply.** In `0x37a0` the `0x3450` args are `rcx=lea[rsp+0x20]` (the freshly built axis),
  `rdx=rdi` (accumulator), `r8=rdi` (accumulator/out) ⇒ `acc ← axis·acc` — the new axis **left-multiplies**.
- **chain ⇒ `Rz·Ry·Rx`.** `0x7d5a` seeds an fp12 identity (`0x1000` on the diagonal), then calls
  `0x37a0(Rx)`, `0x3850(Ry)`, `0x3910(Rz)` with angles from consecutive words `[0x212040/42/44]`
  (a[0]→Rx, a[1]→Ry, a[2]→Rz). Pre-multiply × that order ⇒ `acc = Rz·(Ry·(Rx·I)) = Rz·Ry·Rx`.
- **angle scale = 2π/4096 EXACT.** Builder constants (`read_consts.py`): `(1/4096)·360·π/180 =
  0.0015339807878856412 = 2π/4096` to machine precision.

**Observation (not a refutation):** the fixed-point factor is **4096.8**, not 4096.0
(`@0x4b6c8`=4096.8 build, `@0x4b6d8`=4096.7998 matmul divisor). It cancels (build ×4096.8, read
÷4096.8) and column-normalisation strips the residue, so it never reaches the convention or the
angle-emitting exporter — worth one line in the exporter doc only if anyone compares raw fixed matrices.

## Checks 2 & 3 — independent discrimination (`my_validator.py`, own code path)

Ground truth synthesised from the disasm-confirmed convention on **real ef227 angles** (the log being
gone). Decoder cross-check: both EULER-cited multi-axis angles reproduce exactly — `(2143,209,0)`@f12,
`(0,933,2049)`@f17.

**Clip-2 multi-axis (the only pre/post lever) — my numbers vs EULER.md §2.1:**

| convention | my mean | EULER.md mean |
|---|---:|---:|
| std ZYX (pre) T=N — winner | 0 (exact GT) / **0.00009** quantized | 0.0011 |
| std XYZ (**post**) T=N | **1.37689** | 1.3767 |
| std ZYX **T=Y** | **0.15811** | 0.1574 |
| swap · * | **1.73–2.64** | 1.73–2.64 |

The wrong-convention separations reproduce EULER.md to 3–4 digits. **Caveat:** `||pre−post||` is
symmetric, so this proves discrimination POWER (pre and post are 1.377 apart, transpose 0.158, swap
1.73+), **not** the winning DIRECTION. Which one matches the *live* `R_frame` needed the now-gone log;
the **disasm settles the direction** (and EULER.md's own docstring names the disasm the sole pre/post
authority because single-axis node 0 makes `Rx·I·I == I·I·Rx`).

**>100× margins (realistic engine quantization ×4096.8 + column-norm, all 346 node0 frames):** winner
floor mean **0.00009**; nearest distinct wrong conv (transpose) **0.520 → ×6,082**; nearest swap
**1.988 → ×23,262**. Two+ wrong conventions fail at ≫100×. ✓

## Check 5 — frame→clip mapping is NOT circular

Clip-2 frame-to-frame `||R(f)−R(f+1)||` = mean **0.25**, and **24/25** transitions move R by >0.05
(≫ the ~0.001 floor). So an off-by-one `clip_frame` would inflate the winner's error far above the
floor — the `aux0−1` offset is pinned BY the tight fit, not assumed. On single-axis clips the delta is
~0 (offset-insensitive AND pre/post-degenerate) — precisely why the DISASM, not the mapping/log, is the
authority for pre/post.

---

## Verdict & required follow-up

- **Not refuted.** Every sub-claim (cos-diagonal / sin-off-diagonal, `Rz·Ry·Rx` order, pre-multiply,
  no transpose, 2π/4096 scale) is independently confirmed by the disasm; discrimination power and the
  clip-2 separation magnitudes are independently confirmed by my math. Adopt
  `transplant_spike._rotmat` (= `Rz@Ry@Rx`, std cos/sin) as EULER.md directs.
- **Confidence: medium, with a live gap.** The empirical log leg is dead. The `py euler_validate.py`
  reproduction command in EULER.md §5 no longer works. If the empirical table must stand as
  reproducible evidence, **RE-RUN the 5-cast Bahamut probe and PRESERVE the log** (copy to SCRATCH);
  the disasm alone already settles the convention, but the end-to-end pipeline check (live `R_frame` ==
  the built matrix) is only re-establishable with a fresh capture.

---

**POSTSCRIPT 2026-07-24 — the dead leg is live again.** A fresh instrumented Bahamut cast was archived
to `C:/gd/SCRATCH/summon-transplant/logs/sfxmeshprobe.20260724-012109.log` and `py euler_validate.py
--log <path>` (the script now accepts `--log`) reproduces the discrimination table on it: winner mean
0.0144 (216 matched frames, single cast), margin x54.1 to the next-distinct convention — see EULER.md
§5's addendum for the full numbers. This does not change this file's verdict (not refuted, medium
confidence stands as written above) — it only retires the "currently unreproducible" complaint in
Check 1: the `py euler_validate.py` command is reproducible again when pointed at an archived log.
