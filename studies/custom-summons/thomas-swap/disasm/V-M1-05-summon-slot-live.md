# V-M1-05 — adversarial verification: "the summon slot is LIVE and DRAWN during a real cast"

**Claim id:** M1-05 · **Source artifact:** `M1-effmodel-array.md` §6.1 / §7
**Verdict: PARTIAL** — the *mechanism* half is CONFIRMED and is in fact stronger than stated;
the *log-description* half ("smoothly varying matrix from frame 82 onward") is **REFUTED**, and the
word "DRAWN" over-reaches for the last 261 of 512 logged frames.

Everything below was re-derived from scratch: fresh `refkit` disassembly at the cited RVAs (never
trusting the quoted listings), a fresh independent parse of the live probe log, and a fresh read of
`SfxMeshProbe.cs`. Scripts used are throwaway (scratchpad); every claim carries an `fn@rva` or a
reproducible log statistic.

---

## 1. Static leg — CONFIRMED (and one near-miss fifth writer found)

### 1.1 `pose_eval@0x186a0` has exactly four direct call sites — reproduced

Whole-image, per-`.pdata`-function scan for `call`/`jmp` targeting `0x186a0`:

```
0x161a1 call   in FUNC[0x16184..0x16547]   (Hi_DrawEffModel body)
0x165c0 call   in FUNC[0x165ae..0x167cd]   (Hi_DrawSliceEffModel body)
0x16db4 call   in FUNC[0x16d23..0x16ed8]   (Hi_DrawMorphEffModel body)
0x17767 call   in FUNC[0x17740..0x179f2]   (Hi_DrawSummonModel body)
```

The cited caller set is exact. I additionally swept **every section** for a qword equal to
`imagebase+0x186a0` (a dispatch-table / function-pointer entry that would allow an *indirect* fifth
caller): **zero hits**. So the four direct sites are the complete caller set.

`0x186a0` is a 0x18-byte `.pdata` chunk (`FUNC[0x186a0..0x186b8]`) whose body continues in
`FUNC[0x186b8..0x18738]` + `[0x18738..0x18763]` + `[0x18763..0x187d8]` — a split MSVC body, **not** a
cold error funclet (it contains the real GTE work, verified below).

### 1.2 `pose_eval` writes only `DATA+0x40` — reproduced

```
0x186b2: lea   rbx, [rcx + 0x40]          <- the ONLY base it ever writes through
0x186bd: mov   ebp, 0x1000
0x186ca: mov   dword ptr [rbx + 0xe], 0x10000000
0x186d1: mov   dword ptr [rbx + 6],   0x10000000
0x186dc: mov   dword ptr [rbx], ebp        <- m00 = 0x1000 (fp12 identity seed)
0x186f6/0x18703/0x18729: call 0x3910 / 0x37a0 / 0x3850  (PSX RotMatrix chain)
```

**This is load-bearing for §2.3 below:** `pose_eval` *unconditionally* seeds a fp12 identity
(m00 = m11 = m22 = 4096) before it touches the rotation args. It is therefore **impossible** for a
`pose_eval` execution to leave an all-zero 3×3 — unless the optional scale multiply (`call 0x3b60`
@`0x187ab`) is handed an exactly-zero scale vector.

### 1.3 Only `Hi_DrawSummonModel` hands `pose_eval` the summon DATA — reproduced

Entry chunk `FUNC[0x17710..0x17740]`, disassembled fresh:

```
0x17716: movsxd rax, r9d
0x1771c: imul   rdi, rax, 0x58            <- stride 0x58
0x17720: lea    rax, [rip + 0x209109]     -> RVA 0x220830   <- summon array base
0x1772a: cmp    byte ptr [rdi + 0x50], 0  <- active flag @ rec+0x50
0x1772e: je     0x179f2                   (bail)
0x17734: mov    rcx, qword ptr [rdi]      <- rcx = SummonData
0x1773a: je     0x179f2                   (bail if NULL)
   ...falls through into FUNC[0x17740..0x179f2]...
0x17767: call   0x186a0                   <- pose_eval(rcx = SummonData, ...)
```

Base `0x220830`, stride `0x58`, active `+0x50`, `DATA = [rec+0x00]` — all four confirmed.

**Array length = 1**, independently re-derived from `Hi_RegisterSummonModel@0x15ee0`:

```
0x15f01: lea rbx,[rip+0x20a928]  -> 0x220830
0x15f08: cmp byte ptr [rbx+0x50], dil
0x15f0e: inc eax
0x15f10: add rbx, 0x58
0x15f14: cmp eax, 1
0x15f17: jl  0x15f08              <- loop bound is literally 1
```

The other three `pose_eval` callers take their record from **EFFARR @ `0x220230`, stride `0x30`,
active `+0x20`** (e.g. `Hi_DrawEffModelByBone` entry `0x16809`/`0x1681a`) — a disjoint array.

### 1.4 The near-miss FIFTH writer of a `DATA+0x40` — found, and it is NOT the summon's

This is the one thing the source artifact does not mention and that a skeptic must check. Two
functions perform a raw 32-byte `MATRIX` store into `DATA+0x40`:

```
Hi_DrawEffModelByBone body   FUNC[0x16837..0x16c80]
  0x168ea: lea    rcx, [rip+0x209f3f]  -> 0x220830        <- the SUMMON array
  0x168f1: imul   rax, rsi, 0x58
  0x168f5: cmp    byte ptr [rax+rcx+0x50], r14b           <- summon active?
  0x16900: mov    rax, qword ptr [rax+rcx]                <- SummonData
  0x1690d: mov    rax, qword ptr [rax+0x38]               <- summon BONE-MATRIX array
  0x16911: mov    rdx, qword ptr [rbx]                    <- rbx = EFF record  => EffData
  0x16917: shl    rcx, 5                                  <- boneIdx * 0x20
  0x1691b: movups xmm0,  [rcx+rax]
  0x1691f: movups [rdx+0x40], xmm0                        <- writes EffData+0x40
  0x16923: movups xmm1,  [rcx+rax+0x10]
  0x16928: movups [rdx+0x50], xmm1

Hi_DrawMorphModelByBone body FUNC[0x171ef..0x17355] + [0x17355..]
  0x1731f/0x1732a/0x17335/0x17342/0x17346/0x1735e/0x17367 — byte-for-byte the same shape
```

`rdx` comes from `[rbx]` / `[rdi]`, and the entry chunk `Hi_DrawEffModelByBone@0x167f0` sets that
record from **EFFARR** (`0x16809: lea rax,[rip+0x209a20] -> 0x220230`; `0x16805/0x16813: rax*3<<4` =
stride 0x30; `0x1681a: cmp byte[rbx+0x20],0`). So the destination is an **eff** model's DATA, not the
summon's. **The "nothing but pose_eval writes SummonData+0x40" claim survives** — but only because of
which array supplies `rdx`, which is exactly the kind of detail the original artifact asserted without
showing. (Residual, unfalsifiable from statics: if a slot in EFFARR were ever handed the *same* DATA
pointer as the summon slot. No evidence of that — the summon's DATA is set once at `0x47449` to
`rbp+0x90` inside the setup struct, while eff DATA blocks are bump-allocated `+0xc8` apart into EFFARR
at `0x15982`–`0x15993`.)

**This finding is worth more than the claim it was checking:** it is direct, static proof that the
32-slot eff-model family *parents itself to the summon's per-bone world matrices* (`SummonData+0x38`,
`boneIdx*0x20`). The single summon slot is the skeleton the 32 eff models hang off — which is strong
counter-evidence against the orchestrator's "maybe the creature is drawn through EFFARR instead"
hypothesis in its exclusive form.

### 1.5 The other writers of the summon RECORD (not of `+0x40`)

`refkit.xrefs_to(pe, 0x220830)` — 17 references, all re-disassembled:

| site | fn | what it does |
|---|---|---|
| `0x47449` | `FUNC[0x47330..0x474b5]` | `mov [0x220830], rax` where `rax = rbp+0x90`; also zeroes rec `+0x08..+0x4c` (`0x47434`–`0x4747a`), then `call 0x15ee0` (`Hi_RegisterSummonModel`) — **the summon setup path** |
| `0x30cc9` | `FUNC[0x30c20..]` | `mov [0x220830], rbx` with `rbx = 0`, immediately after a 32-slot × 0x30 EFFARR clear loop, plus `mov [0x220880], ebx` — **global init/clear** |
| `0xf90d` | mega-interpreter `0xeea4` | `mov [0x220830], r12` + `mov [0x220880], r12d` — an opcode that **frees/clears** the summon slot |
| `0x15f01`, `0x17720`, `0x17a1b`, `0x17a7b`, `0x185bb`, `0x1863b`, `0x187eb`, `0x1884b`, `0x188ab`, `0x1893b`, `0x18b03`, `0x18b5a` | the `Hi_*Summon*` roster | `lea` the base — reads |
| `0x168ea`, `0x1731f` | the two `*ByBone` bodies | `lea` the base — reads (§1.4) |

None writes `DATA+0x40`. Note `0xf90d`/`0x30cc9` also clear `rec+0x50` (`0x220880`) — so if the `.seq`
had freed the summon mid-cast, the probe would have **stopped emitting ROOT rows**. It did not (§2.1).

---

## 2. Runtime leg — the log. Two sub-claims confirmed, one REFUTED.

Log: `<game>/sfxmeshprobe.log`, 2 759 846 bytes, mtime 2026-07-23 08:53. Row census:
`MESH 19461 · VIEW 2201 · PROJ 2201 · CAM 2201 · ROOT 2045`. `LogSummonRoot()` is called from
`SFXDataMesh.cs:653` (`Runtime.Render()`), ~4× per frame.

### 2.1 CONFIRMED — 2045 rows, effect 227 only, `active == 1` on every row

`set(effectId) == {227}`; `set(active) == {1}`; frames 50 … 561 (512 distinct frames; 503 frames with
4 rows, 6 with 3, 3 with 5). The 4 rows inside any one frame are **byte-identical** in all 512 frames
(0 frames with intra-frame variation), i.e. `DATA+0x40` is written at most once per frame.
`CAM` rows span frames 11 … 561, so the summon slot is registered from frame 50 (39 frames after the
effect starts) and stays registered to the last logged frame.

### 2.2 CONFIRMED — all-zero for frames 50–81, first non-zero at frame 82

127 all-zero rows, covering exactly frames 50–81 (32 frames). First non-zero row:

```
ROOT,227,82,1, 0,-6140,0, 0,0,-6140, 6139,0,0, -1224,-4096,0
```

**Correction to the cited evidence:** the artifact says `|m00| = 6140`. In that row `m00 = 0`; the
6140 sits at `m01`/`m12` (the pose is a 90° yaw). The *magnitude* 6140 is real and 6140/4096 = 1.4990,
so the "the scale multiply `call 0x3b60`@`0x187ab` landed" inference stands — but the element index
in the artifact is wrong, and an element index is exactly the sort of thing a downstream re-projection
gets silently wrong. Diagonal scales observed elsewhere in the track: 4093 (≈1.0 after fp12 rounding),
6140 (1.5), 12279 (≈3.0).

### 2.3 STRENGTHENED — the zero prefix means "registered but never DRAWN", not merely "zero"

Because `pose_eval` seeds `m00 = 0x1000` at `0x186dc` *before* any conditional (§1.2), an all-zero 3×3
cannot be produced by a `pose_eval` execution. Frames 50–81 therefore prove **`Hi_DrawSummonModel` was
not called at all** for those 32 frames despite `active == 1` and `DATA != NULL`. That is a *sharper*
statement than the artifact makes, and it is the clean "register ≠ draw" boundary the roadmap needs.
*Caveat, stated honestly:* a `.seq` Draw carrying an exactly-zero scale SVECTOR would also zero the
matrix through `call 0x3b60`, and the translation args were zero too — the log alone cannot exclude
that. It is the far less likely of the two explanations (32 consecutive frames of it), not an
impossibility.

### 2.4 REFUTED — "a smoothly varying matrix from frame 82 onward"

Independently run-length-encoded (one state per frame, all 512 frames):

* **146 distinct states in 512 frames. The matrix changes on only 145 of 511 frame transitions (28 %). Median per-frame translation delta = 0.**
* The track is **piecewise**, not smooth — four smooth segments separated by hard cuts:

| frames | len | behaviour | translation at start → end |
|---|---|---|---|
| 50–81 | 32 | **not drawn** (all-zero) | — |
| 82–127 | 46 | smooth arc | (−1224,−4096,0) → (−17,16384,16) |
| **128** | — | **HARD CUT, Δ = 23 749 u** | → (0,−7168,3072) |
| 128–152 | 25 | smooth | → (0,−2856,1634) |
| **153** | — | **HARD CUT, Δ = 22 303 u** | → (2048,−4096,23808) |
| 153–167 | 15 | linear z sweep, exactly −4864 u/frame | → (2048,−4096,−44288) |
| 168–177 | 10 | **frozen** | (2048,−4096,−49152) |
| **178** | — | **HARD CUT, Δ = 70 572 u** | → (0,−8576,21248) |
| 178–233 | 56 | smooth, easing asymptotically | → (0,−23554,15878) |
| 234–300 | **67** | **frozen** | (0,−23567,15878) |
| **301** | — | **HARD CUT, Δ ≈ 26 100 u** | → (0,−12288,−7168) |
| 301–561 | **261** | **frozen** | (0,−12288,−7168) |

261 frozen frames = **51 % of the ROOT span**, and 328 of 512 frames (64 %) are inside a frozen run.
Describing this as "a smoothly varying matrix from frame 82 onward" is materially wrong and is
precisely the description that would license building a flight path out of it.

### 2.5 "DRAWN" is proven for frames 82–301 only

`DATA+0x40` is a *last-write-wins* cell. A **change** proves `Hi_DrawSummonModel` ran that frame; an
**unchanged** value cannot distinguish "drawn again with identical args" from "not drawn, value
stale". So:

* frames **82–301**: DRAWN is proven on the 145 change-frames, and by density (changes on nearly every
  frame from 82 to 233) the whole 82–301 window is safe. Note the state *changes* at frame 301, so the
  creature was drawn at least once at 301.
* frames **302–561** (260 frames, 51 % of the span): **UNPROVEN either way** by this instrument.

Corroborating (not proof) from the same log: 5 `MESH` keys (`0039BE40`, `0099BD00`, `009DBD02`,
`00BDBD40`, `00BDBE00`) appear only in frames 82–300 and never after 301, while 17 keys appear only
after 301 — consistent with the creature's meshes retiring and the fire-column effects starting,
i.e. the user's video phase (4). A `HideMeshes`-style hide-mask (`SummonData+0x20`) would also
suppress rendering while `+0x40` kept updating, so "drawn" in the primitive-emission sense needs the
mask read too — not currently in the probe.

### 2.6 Consistency with the video ground truth — a genuinely useful coincidence

The window in which the root is *actively updated*, frames 82–300, is **219 of 512 logged frames =
42.8 %**, against the user's independent "~40 % of the cast has the creature framed". Independent
agreement to ~3 points. Combined with §1.4 (32 eff models parented to this slot's bone matrices), the
weight of evidence is that the single summon slot **is** the creature — the s52 trajectory problem is a
*tracking* bug (reading the staging anchor `+0x40` instead of the composed world matrix
`*(MATRIX*)(SummonData+0x38)`, per `M1` §6.2, plus the `diag(1,−1,−1)` flip at `0x797a`–`0x7a12` and
the motion-clip-sourced root translation at `0x7ba5`–`0x7bcc`), **not** a wrong subsystem.

---

## 3. What would still refute what survives

* A cast in which ROOT rows stay all-zero while the creature visibly renders. (Not observed; the one
  available cast is the opposite.)
* An EFFARR slot observed at runtime holding the same DATA pointer as `[0x220830]` — would break the
  §1.4 disambiguation. Testable by extending the probe to log `[0x220830]` and the 32 `[0x220230 +
  i*0x30]` DATA pointers once at frame 0 of a cast (cheap, no new provenance surface).
* For §2.5: extend the probe to log `SummonData+0x38` (the pointer value only, plus `boneCount`) and
  the hide-mask `SummonData+0x20` per frame. A per-frame *changing* `+0x38` pointer proves
  `build_world_matrices@0x7820` ran (`mov [rcx+0x38], r8` @`0x7842`, a bump cursor that necessarily
  changes each frame), which proves the draw ran — closing the 302–561 gap without dumping any
  skeletal content.

---

## 4. Verdict

| sub-claim | verdict |
|---|---|
| `pose_eval@0x186a0` caller set = exactly those 4, no indirect callers | CONFIRMED |
| only `Hi_DrawSummonModel@0x17767` passes the summon DATA | CONFIRMED |
| `pose_eval` writes only `DATA+0x40` | CONFIRMED |
| no fifth writer of **Summon**Data+0x40 | CONFIRMED (with the `*ByBone` near-miss documented) |
| 2045 ROOT rows, effect 227, `active == 1` throughout | CONFIRMED |
| all-zero frames 50–81, first non-zero frame 82 | CONFIRMED (and sharpened to "not drawn") |
| `|m00| = 6140` in the first non-zero row | WRONG ELEMENT (m00 = 0; 6140 is at m01) — the 1.4990 scale inference still holds |
| "smoothly varying matrix from frame 82 onward" | **REFUTED** — piecewise, 3 hard cuts, 64 % of frames inside frozen runs, 261-frame constant tail |
| "the summon slot is LIVE" | CONFIRMED |
| "…and DRAWN [for the whole cast]" | CONFIRMED for frames 82–301; UNPROVEN for 302–561 |

**Overall: PARTIAL.** Keep the mechanism; discard the phrase "smoothly varying"; treat the ROOT track
as a segmented *staging anchor* with 4 keyed segments and 2 long holds, and do not build any flight on
it — the composed matrix at `SummonData+0x38` is the thing to read next.
