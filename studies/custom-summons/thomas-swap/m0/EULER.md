# EULER.md — the summon motion exporter's LAST DECODE (Milestone 0, TRANSPLANT.md §3.2)

**The question (verbatim):** settle the PSX RotMatrix Euler convention — the cos-vs-sin thunk assignment
and pre-vs-post multiply in `fn 0x3450` — so the future `ff9mapkit/ff9mapkit/summons/motion.py` can build
(and inverse-decompose) a node's rotation matrix from its three 12-bit Euler angles **exactly** as the
plugin does.

**VERDICT (CONFIRMED two independent ways — a `>1000×` log margin AND direct disasm):**

> **`R_local = Rz(az) · Ry(ay) · Rx(ax)`**, with the **standard** per-axis matrices
> (`cos` on the diagonal, `sin` off-diagonal), angles scaled `θ_rad = angle_12bit · 2π/4096`, composed by
> **PRE-multiplication** (each new axis matrix multiplied on the **left** of the accumulator), **no transpose**.

All three residual bits resolve to the *un-swapped, textbook* choice. `transplant_spike.py::_rotmat`
(`R = Rz @ Ry @ Rx`, standard cos/sin) — which flagged its own order as unverified — is now **fully
verified correct**; adopt its construction verbatim.

RVAs are image-base-relative for the user's own `FF9SpecialEffectPlugin.dll` (x64, `ImageBase 0x180000000`).

---

## 1. Implementation-ready pseudocode for `summons/motion.py`

### 1.1 Forward — build the 3×3 from the three 12-bit angles (what the DLL does)

```python
TWO_PI_OVER_4096 = 2*pi / 4096          # RotMatrix scales a movsx'd s16 angle by exactly this (fn 0x37a0)

def axis_matrices(ax, ay, az):
    # ax,ay,az are the three per-node Euler angles (any integer; cos/sin are periodic mod 4096).
    def cs(a):
        r = a * TWO_PI_OVER_4096
        return cos(r), sin(r)                       # COS on the diagonal, SIN off-diagonal (verified)
    cx, sx = cs(ax); cy, sy = cs(ay); cz, sz = cs(az)
    Rx = [[1, 0, 0], [0, cx, -sx], [0, sx,  cx]]    # fn 0x37a0  (Rx: -S on m12, +S on m21)
    Ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]     # fn 0x3850  (Ry: +S on m02, -S on m20)
    Rz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]     # fn 0x3910  (Rz: -S on m01, +S on m10)
    return Rx, Ry, Rz

def build_rotation(ax, ay, az):
    Rx, Ry, Rz = axis_matrices(ax, ay, az)
    return Rz @ Ry @ Rx                             # PRE-multiply chain: seed I; I·Rx; Ry·(Rx); Rz·(Ry·Rx)
```

Mechanically the DLL seeds an fp12 **identity**, then folds in `Rx`, then `Ry`, then `Rz`, each via
`0x3450(rcx = new_axis_matrix, rdx = accumulator, r8 = accumulator)` where `0x3450` computes
`OUT = rcx · rdx` into `[r8]`. So `acc ← axis · acc` each call ⇒ after all three, `acc = Rz · Ry · Rx`.
The angle order fed to the builders is `ax→Rx, ay→Ry, az→Rz` (angles `a[0]/a[1]/a[2]` = the clip's
X/Y/Z tracks; node builder `0x7d8a/0x7d9a/0x7daa`).

### 1.2 Inverse — decompose a DCC rotation matrix into the three 12-bit angles (what the EXPORTER needs)

`R = Rz·Ry·Rx` expands to (used to derive the closed-form inverse):

```
R = [ cz·cy   cz·sy·sx − sz·cx   cz·sy·cx + sz·sx ]
    [ sz·cy   sz·sy·sx + cz·cx   sz·sy·cx − cz·sx ]
    [ −sy     cy·sx              cy·cx            ]
```

```python
def decompose(R):                                   # R = a proper 3x3 rotation from the retargeted clip
    y = atan2(-R[2][0], hypot(R[0][0], R[1][0]))     # sy = −R20
    if cos(y) > 1e-6:
        x = atan2(R[2][1], R[2][2])                  # cy·sx , cy·cx
        z = atan2(R[1][0], R[0][0])                  # sz·cy , cz·cy
    else:                                            # gimbal lock (|y|≈90°): fold z into x
        x = atan2(-R[1][2], R[1][1]); z = 0.0
    to_units = 4096 / (2*pi)
    return tuple(round(v*to_units) % 4096 for v in (x, y, z))   # 12-bit angle per axis, 0..4095
```

Round-trips `build_rotation ∘ decompose` to float precision on every test triple (incl. clip-2's
multi-axis frames and the ±90/±180 literals; gimbal guard exercised). **Then split each 12-bit value into
the on-disk two-stream form** (M5 §2.3): `coarse = (v >> 4) & 0xFF` (the 1-byte/frame track), `fine =
v & 0xF` (the nibble, 2 frames/byte). A literal channel stores the s16 value directly in the RotKey.

---

## 2. The discrimination table (empirical, the s53 log)

**Method.** Per dual-logged frame: recover the pure node-0 clip rotation as `R_frame =
colnorm(R_anchor)⁻¹ · colnorm(composed)` — `R_anchor` = the s52 `ROOT` matrix (`SummonData+0x40`),
`composed` = the s53 `MODEL kind=S` node-0 matrix (`*(SummonData+0x38)`); column-normalisation strips the
uniform 0.02–3.0 scale folded into `+0x40`; keep frames whose `R_frame` is orthonormal (`‖RᵀR−I‖ < 0.05`).
By M5 §5, `composed = R_anchor · clipRot(node0)`, so `R_frame = clipRot(node0)` — exactly the matrix the
RotMatrix chain builds from node 0's decoded angles. Score all 8 conventions by
`‖R_candidate − R_frame‖_F`. **Bone 0 ONLY** (provenance: `bones[1..92]` are BLOCKED).

**1072 clean matched frames across all 5 casts** (frame→clip mapping in §3):

| convention | n | mean | median | p95 | max |
|---|---:|---:|---:|---:|---:|
| **cos/sin=std · order=ZYX (pre) · T=N**  ← **WINNER** | 1072 | **0.0145** | **0.0012** | **0.0015** | 2.8284 |
| cos/sin=std · order=XYZ (post) · T=N | 1072 | 0.1107 | 0.0012 | 0.8889 | 2.8284 |
| cos/sin=std · order=ZYX · T=Y | 1072 | 0.7829 | 0.0031 | 2.8284 | 2.8284 |
| cos/sin=std · order=XYZ · T=Y | 1072 | 0.8746 | 0.0031 | 2.8284 | 2.8284 |
| cos/sin=swap · order=ZYX · T=Y | 1072 | 1.9812 | 2.0000 | 2.0000 | 2.0237 |
| cos/sin=swap · order=ZYX · T=N | 1072 | 2.1997 | 2.0000 | 2.8284 | 2.8284 |
| cos/sin=swap · order=XYZ · T=N | 1072 | 2.5976 | 2.8284 | 2.8284 | 2.8284 |
| cos/sin=swap · order=XYZ · T=Y | 1072 | 2.8155 | 2.8284 | 2.8284 | 2.8284 |

The winner sits at the **1/4096 quantization floor** (median 0.0012; **99.1 %** of frames < 0.02). Its only
misses are **5 frames = one clip-transition-lag frame (f204) replicated across the 5 casts** (0.5 %; the
`composed` still shows the previous clip's tail pose one frame after `aux0` advanced into clip 4). Excluding
those 5: **mean 0.0013, median 0.0012, max 0.0239.** 2-session cross-check (casts 0,1, 424 frames): winner
mean 0.0146 vs next-distinct 0.7917 — same verdict.

### 2.1 Focused sub-tables (each isolates one axis on the angles that break it)

Because node 0 is **single-axis** (`ax,0,0`) in most clips, the full table's `ZYX`/`XYZ` twins nearly tie
and `T=Y` is degenerate on ±180. These sub-tables break each axis cleanly:

**clip 0, θ = −90° (breaks cos/sin AND transpose)** — n=240:

| convention | mean | max |
|---|---:|---:|
| **std · ZYX/XYZ · T=N** | **0.0011** | 0.0156 |
| std · T=Y (transpose) | 2.8284 | 2.8284 |
| swap (either T) | 2.0000 – 2.8284 | — |

→ **cos/sin=std** and **transpose=N** confirmed, ~1800× margin.

**clip 2, MULTI-AXIS frames (breaks pre/post — the only empirical pre/post signal)** — n=75:

| convention | mean | median | max |
|---|---:|---:|---:|
| **std · ZYX (pre) · T=N** | **0.0011** | **0.0011** | 0.0016 |
| std · XYZ (**post**) · T=N | 1.3767 | 1.4571 | 2.8010 |
| std · ZYX · T=Y | 0.1574 | 0.0038 | 1.0088 |
| swap · * | 1.73 – 2.64 | — | — |

→ **PRE-multiply (ZYX) confirmed empirically**, ~1250× over post-multiply. (Clip 2's node-0 Y/Z tracks are
non-zero on 16/26 frames — `(2143,209,0)`, `(0,933,2049)`, … — so the log *does* separate pre from post
here, independently of the disasm.)

**single-axis ~180° (transpose DEGENERATE by construction)** — n=697: std `T=N` (0.0013) and `T=Y`
(0.0031) both pass because `Rx(180)ᵀ = Rx(180)`; swap still fails (≥2.0). This is why transpose is pinned by
the −90° and multi-axis frames above, not the ±180 bulk.

---

## 3. The frame→clip mapping validated on

Solved from the engine's **own** motion-frame counter — `MODEL kind=S` column `aux0` = `rec+0x54`, logged
post-increment (M5 §6) — segmented into runs at resets; each run's clip = the unique `frameCount` match in
`[24,30,26,48,40,68,82,28]`; `clip_frame = aux0 − 1`. Identical in all 5 casts:

| native frames | max aux0 | clip | node-0 signature |
|---|---:|---:|---|
| 82 – 105 | 24 | **clip 0** | literal −90° |
| 106 – 126 | 21 | (unident. — 30-frame clip 1 cut short; excluded) | −90° |
| 127 – 151 | 24 | clip 0 | −90° |
| 177 – 203 | 26 | **clip 2** | **sweeping** −91°→…→ Rz(180°) (multi-axis f10–24) |
| 204 – 234 | 40 | **clip 4** | literal +180° |
| 237 – 300 | 64 | (unident. — 68-frame clip 5 cut short; excluded) | −180° |
| 301 – 381 | 82 | **clip 6** | literal −180° |
| 385 – 413 | 28 | **clip 7** | literal −180° |

Clips exercised in the scored set: **{0, 2, 4, 6, 7}** — angle diversity (−90°, a full multi-axis sweep,
+180°, −180°) covers every discrimination axis. Unidentified runs (max aux0 not a unique frameCount) and
the sparse held-frame region 152–176 (PROBE.md §8) are excluded by the `min_len=6` run filter; they are not
needed — the identified runs already pin the convention `>1000×`. The `aux0−1` offset was validated by the
1/4096 fit; the sole `aux0`-vs-pose lag (f204) is the documented transition artifact, not a mapping error.

---

## 4. The disasm confirmation (read-only, the user's own DLL) — settles pre/post directly

Because node 0 is single-axis, the log **cannot** separate pre from post on bone 0 (the anticipated tie —
`Rx·I·I == I·I·Rx`). Clip 2's multi-axis node-0 frames break it empirically (§2.1) **and** the disasm reads
it directly:

- **cos vs sin** — Rx builder `0x37a0`: the **first** thunk call (`0x37e0 → 0x49cd2`) resolves to
  `jmp [MSVCR120.dll!cos]` and its result is stored on the **diagonal** (`m11=m22`, `[rsp+0x28]/[rsp+0x30]`);
  the **second** (`0x37f4 → 0x49ce4`) resolves to `MSVCR120.dll!sin`, stored **off-diagonal** with the `-S`
  sign on `m12` (`0x3832 neg ax`). ⇒ **standard** `Rx=[[1,0,0],[0,cos,-sin],[0,sin,cos]]`, **no swap**.
- **matmul direction** — `0x3450` computes `OUT[i][j] = Σ rcx[i][k]·rdx[k][j]` (`OUT[0][0] = rcx.row0 ·
  rdx.col0`, i.e. `rcx · rdx`) and writes it to `[r8]` (tail pack `0x3750: rdx=r8`, return `0x3769: rax=r8`).
- **pre vs post** — inside `0x37a0` the `0x3450` call is set up as `rcx = lea [rsp+0x20]` (the freshly built
  axis matrix, `0x382d`), `rdx = rdi` (the accumulator, `0x3803`), `r8 = rdi` (the accumulator, output,
  `0x37fb`). So `acc ← rcx·rdx = axisMatrix · acc` — the new axis **pre-multiplies**.
- **chain order** — node builder seeds identity (`0x7d5a–0x7d77`) then calls `Rx@0x37a0` (`0x7d8a`),
  `Ry@0x3850` (`0x7d9a`), `Rz@0x3910` (`0x7daa`). ⇒ `acc = Rz·(Ry·(Rx·I)) = Rz·Ry·Rx`.

Independently reproduced by `confirm_disasm()` in `euler_validate.py`.

---

## 5. Reproduction & provenance

> **⚠ ADDENDUM 2026-07-24:** the live `sfxmeshprobe.log` this section's command reads was
> **overwritten** by a concurrent relaunch at 2026-07-23 ~16:40 (before any archive existed), so
> `py euler_validate.py` currently parses 0 matched frames — the §2/§2.1/§3 empirical tables are
> records, not currently reproducible. The verdict STANDS on the disasm leg alone (§4), which the
> round-2 adversarial verifier re-derived independently two ways (`VERIFY-EULER.md`; refuted=NO).
> One fresh instrumented Bahamut cast (ROOT+MODEL rows, per `CAST-PROTOCOL.md`) re-establishes the
> empirical leg; archive it to SCRATCH immediately and point this command at the snapshot.
> Precision note from verification: the DLL's internal fixed-point factor is **4096.8** (build
> ×4096.8 @0x4b6c8, matmul ÷4096.8 @0x4b6d8) — it cancels and column-norm strips it, so nothing
> above changes, but raw fixed-matrix comparisons must use 4096.8, not 4096.0.
>
> **ADDENDUM 2026-07-24 — empirical leg RE-ESTABLISHED** on the archived cast
> `C:/gd/SCRATCH/summon-transplant/logs/sfxmeshprobe.20260724-012109.log` (one Bahamut cast, effect
> 227, frames 11..561; `py euler_validate.py --log <path>`, the script now takes `--log`). The table
> reproduces: winner `cos/sin=std order=ZYX T=N` mean **0.0144** (216 clean matched frames; single
> cast so fewer frames than round 1's 1072, same floor), next-distinct (T=Y) mean 0.7771 => margin
> **x54.1** — matches round 1's own margin. The clip0 (-90°) and clip2 (multi-axis) sub-tables
> reproduce to 4 decimal places (e.g. clip2 std-ZYX-T=N mean 0.0011, XYZ-post mean 1.3767, T=Y mean
> 0.1574 — identical to §2.1, since the scripted cast replays the same clip angles every time). The
> one outlier is the same f204 clip-transition-lag frame. Disasm confirmation reproduces unchanged
> (reads the same installed DLL). Verdict unchanged; the log leg is no longer dead.

```
cd studies/custom-summons/thomas-swap/m0
py euler_validate.py            # log validation (5 casts) + focused sub-tables + disasm confirmation
py euler_validate.py --log C:/gd/SCRATCH/summon-transplant/logs/sfxmeshprobe.20260724-012109.log
```

Reads: the user's own `sfxmeshprobe.log`; the LOCAL `C:/gd/SCRATCH/summon-format/ef227.bytes` (Bahamut,
never copied into the repo); the user's own installed DLL (RVAs/mnemonics only, via `disasm/refkit.py`).
Decode delegated to the committable `disasm/transplant_spike.py` + `disasm/ef_container.py`. Bone 0 ONLY —
no per-bone animation is dumped or reconstructed. Emits numbers only; embeds no stock bytes. `euler_validate.py`
is committable analysis code.

**Bottom line for TRANSPLANT.md §3.2 / risk #5:** the exporter's last decode is CLOSED with zero playtests.
`R_local = Rz·Ry·Rx`, standard cos/sin, pre-multiply — drop `transplant_spike._rotmat` straight into
`summons/motion.py` and pair it with the §1.2 inverse for the DCC→clip exporter.
