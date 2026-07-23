# T3-4 — ADVERSARIAL VERIFICATION of the "angle→matrix Euler composition" claim

**Claim T3-4 (from `T3-blender-export.md` §0/§2.4/§10):** the one genuinely-new decode left for the
Blender exporter is the clip's angle→matrix Euler composition — three `RotMatrix` fns
`0x37a0`/`0x3850`/`0x3910` + their order — which is **bounded** (~3 small fns, one session) and
**validates for free** against the s52/s53 probe's already-logged composed bone-0 matrix.

**VERDICT: CONFIRMED.** Independently re-derived from the user's own `FF9SpecialEffectPlugin.dll`
(x64) + the live `sfxmeshprobe.log` + the Memoria C# probe source. Both refutation conditions fail to
fire; two documentation-cite errors noted (do not affect the claim).

---

## 1. The three RotMatrix fns ARE clean per-axis rotations (refutation #1 REFUTED)

Fresh `refkit` disasm of each function. Each: sign-extends the 16-bit angle `cx`, converts to double,
scales by `1/4096 · 360 · π/180` (= exactly **2π/4096** — constants read from the image: `0.000244140625`,
`360.0`, `π`, `180.0`), calls libc `cos`/`sin` (IAT thunks `0x49cd2`/`0x49ce4`), quantises to 1/4096
fixed (`×4096.8`), lays the sin/cos into a 3×3 PSX MATRIX at `[rsp+0x20]`, and multiplies it into the
caller's accumulator via the fixed-point matmul `0x3450`. Decoding the byte-store offsets:

| fn | matrix built | axis |
|----|--------------|------|
| **`0x37a0`** | `[[1,0,0],[0,C,-S],[0,S,C]]` | **Rx** |
| **`0x3850`** | `[[C,0,S],[0,1,0],[-S,0,C]]` | **Ry** |
| **`0x3910`** | `[[C,-S,0],[S,C,0],[0,0,1]]` | **Rz** |

These are the textbook per-axis rotation matrices. The composition is **fully decomposable into per-axis
rotations** — the exact condition that would have refuted the claim does the opposite. `0x3450` reads both
operand matrices as 1/4096 fixed (divisor `4096.7998` confirmed from the image), a standard 3×3 multiply.

**Call order is readable and fixed** (node builder `0x7820`, disasm `0x7d78..0x7db4`):
`angle[0]`→`Rx@0x37a0` (`0x7d8a`), `angle[1]`→`Ry@0x3850` (`0x7d9a`), `angle[2]`→`Rz@0x3910` (`0x7daa`),
all accumulated into one matrix seeded with fp12 identity. The angle sources are `[0x212040/42/44]` — the
three decoded 12-bit Euler angles of M5 §2.3. The **only** residual determinations are (a) which libc
thunk is cos vs sin (both are `jmp [IAT]`; resolvable by the `-S` placement convention or one test) and
(b) pre- vs post-multiply in `0x3450`. Both are trivial. **"Bounded, ~3 small fns + order" holds.**

## 2. The validation is genuinely FREE and airtight (refutation #2 not triggered)

The s53 `SfxMeshProbe.LogModels()` path logs, per active summon frame, **node 0 of `*(SummonData+0x38)`**
— the composed bone-0 matrix `m00..m22` + translation `wx,wy,wz` (`SfxMeshProbe.cs:636–651`) — alongside
the s52 ROOT row's **anchor** matrix (`SummonData+0x40` = `R·S`).

The **existing** on-disk log `<game>/sfxmeshprobe.log` (from the FORMAT round) already contains, for
Bahamut (`effectId=227`): **8,520** active summon MODEL rows with a populated composed matrix, and **480**
frames that carry BOTH the anchor (ROOT) and the composed (MODEL) matrix. No re-cast needed — "already
logged" is literally true.

**Numerical cross-check (this slice).** For all 12 sampled dual-logged frames (representative of the 480):
`clipRot := (anchorR/‖·‖)⁻¹ · (composed/‖·‖)` recovers a **proper rotation** — orthonormality error
`‖RᵀR−I‖ ≈ 0.0026`, `det ≈ +0.998` — i.e. `composed = anchor · (pure per-bone rotation)` to within pure
1/4096 quantization. The anchor translation in every MODEL row equals its ROOT translation exactly
(e.g. f82 `(-1224,-4096,0)`). This is precisely M5 §5's law and precisely what an offline Euler decode of
`clip[0]` must reproduce: compose the logged anchor with the offline-decoded `clip[0].rot` and compare to
the logged composed bone-0. Every structural fact is consistent with a correct decode reproducing it.

## 3. Two documentation-cite errors (do NOT affect the claim)

1. `T3 §2.4` cites the composed bone-0 read at **`SFXDataMesh.cs:659`**. It is actually
   **`SfxMeshProbe.cs:636–651`** (`WriteModelRow`); `:659` is the row-counter increment, and the file is
   `SfxMeshProbe.cs`, not `SFXDataMesh.cs`.
2. The composed bone-0 is logged specifically by **s53** (`CaptureModels=1` → MODEL rows), not s52. s52
   (`CaptureRoot=1` → ROOT rows) logs only the anchor `+0x40`. The claim's "s52/s53" is fine (you want
   both: s52 anchor to compose offline + s53 composed to compare), but M5 §9 reads as if `+0x38` logging
   were future work — it is already implemented and already in the log.

## 4. Residual (honest scope)

I verified the **path is sound and self-validating** but did NOT run the offline clip decoder itself
(it is the T3 deliverable; building it here would be constructing, not verifying). So refutation #2 —
"offline decode fails to reproduce the logged matrix" — is structurally excluded but not positively
exercised. Recommend the implementer's first check be exactly the frame-82 reproduction above.

**Reproduction:** `py -c` disasm of `0x37a0/0x3850/0x3910/0x3450` via `refkit`; row-type histogram +
composed/anchor consistency over `<game>/sfxmeshprobe.log` (MODEL kind `S`, `$4=kind $6=active $27=bones32`;
ROOT `$4=active`).
