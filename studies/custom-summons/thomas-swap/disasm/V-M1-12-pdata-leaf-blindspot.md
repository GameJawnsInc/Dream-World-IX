# V-M1-12 — adversarial verification: refkit's .pdata helpers are blind to no-unwind leaf functions

**CLAIM M1-12:** refkit's `.pdata`-driven helpers (`iter_instructions` / `xrefs_to` / `xref_index` / the
caller scan) silently MISS no-unwind leaf functions. `Hi_InitEffModel@0x15940` has no `RUNTIME_FUNCTION`
entry and was invisible to all of them, which is why "nothing ever writes `EFFARR[i].data`" looked true.
Any negative-existence conclusion drawn from those helpers needs a raw-immediate or leaf sweep first.

**VERDICT: CONFIRMED** (every cited fact independently reproduced against the user's own
`x64/FF9_Data/Plugins/FF9SpecialEffectPlugin.dll`, and the blind spot is *larger* than the claim states).

Scripts used (scratchpad only, not committed): `v_m112.py` / `v_m112b.py` / `v_m112c.py` / `v_m112d.py`.

---

## 1. The would-be refuter fails: 0x15940 is NOT in `refkit.functions(pe)`

```
n_pdata_funcs 646
covering 0x15940: []
func_of(0x15940): None
exact begin match: False
  pdata 0x1538e 0x1585a
  pdata 0x1585a 0x15938      <-- ends here
  pdata 0x159a0 0x159ea      <-- resumes here (Hi_FreeEffModel)
entries intersecting gap [0x1585a,0x159a0): [('0x1585a','0x15938')]
```

The table jumps `0x15938 → 0x159a0` exactly as cited. `refkit.func_of` returns `None`, so
`iter_instructions` (which disassembles strictly per `.pdata` range) never reaches a byte of this
function, and every helper built on it (`xrefs_to`, `xref_index`, the caller scan) inherits the hole.
The stated refutation condition ("0x15940 does appear in `refkit.functions(pe)`") is **not** met.

## 2. There IS real code at 0x15940 — a leaf with no prologue

Raw bytes at `0x15938`: `cc cc cc cc cc cc cc cc 45 33 c9 48 8d 05 08 a9 20 00 …` — eight `int3` pads,
then a function that starts with `xor r9d,r9d` (no `push`/`sub rsp` ⇒ no unwind data needed ⇒ MSVC emits
no `RUNTIME_FUNCTION`; legal for a leaf). Fresh disassembly, both from `0x15938` and from `0x15940`
(identical stream — no desync ambiguity):

```
0x15940  xor    r9d, r9d
0x15943  lea    rax, [rip + 0x20a908]      ; -> 0x220252   (EFFARR + 0x22, the handle field)
0x1594a  mov    r8d, r9d
0x15950  mov    word ptr [rax], r8w        ; handle := i
0x15954  mov    byte ptr [rax - 2], r9b    ; +0x20 active := 0
0x15958  mov    qword ptr [rax - 0x22], r9 ; +0x00 data := NULL
0x1595c  inc    r8d
0x1595f  mov    qword ptr [rax - 0x1a], r9 ; +0x08
0x15963  mov    qword ptr [rax - 0x12], r9 ; +0x10
0x15967  mov    qword ptr [rax - 0xa],  r9 ; +0x18   (the 24-B texInfo)
0x1596b  lea    rax, [rax + 0x30]          ; stride 0x30
0x1596f  cmp    r8d, 0x20                  ; 32 slots
0x15973  jl     0x180015950
0x15975  lea    rax, [rip + 0x20a8b4]      ; -> 0x220230   (EFFARR base)
0x1597c  test   edx, edx
0x1597e  jle    0x180015995
0x15982  mov    qword ptr [rax], rcx       ; <<< EFFARR[k].data := poolCursor
0x15985  add    rcx, 0xc8                  ; sizeof(ModelData) == 0xC8
0x1598c  lea    rax, [rax + 0x30]
0x15990  dec    rdx
0x15993  jne    0x180015982
0x15995  ret
```

Both cited RIP targets reproduce to the byte: `0x15943 → 0x220252`, `0x15975 → 0x220230`. The
`0x30` stride / `0x20` count / `+0x20` active / `+0x22` handle facts of M1 are re-derived here
independently of the `Hi_Register*EffModel` bodies. And `0x15982` **is** the store to `EFFARR[k].data`
— the very write whose absence the helpers implied.

## 3. The helpers demonstrably do not see it

`refkit.xref_index(pe, 0x220200, 0x220900)` (the exact window `m1_effarr_xref.py` uses):

```
total xref sites in [0x220200,0x220900): 103
0x15943 present: False
0x15975 present: False
any site in [0x15938,0x159a0): []
refs to 0x220230: 20 sites — 0x15224, 0x159ab, 0x15acc, 0x15b7c, 0x15c4e, 0x15d4e, 0x15e2e,
                  0x16160, 0x16587, 0x16809, 0x16cce, 0x1719b, 0x17aea, 0x17b37, 0x1800a,
                  0x189a3, 0x189fa, 0x18a4b, 0x18a9b, 0x18c07     (0x15975 ABSENT)
refs to 0x220252: 1 site — 0x30c8b                                 (0x15943 ABSENT)
xrefs_to(0x220230): 20 hits, contains 0x15975 = False
```

Two real `lea`s into the queried window, both missing from both helpers. Confirmed.

## 4. The blind spot is BIGGER than one function (strengthens the corollary)

`.text` = `0x1000..0x49edf` (298,719 B). Subtracting all 646 `.pdata` ranges leaves **353 gaps totalling
13,156 bytes**, of which **9,947 bytes are non-padding** (not `0xCC`/`0x00`), spread over **56 gaps with
≥16 real bytes**. Largest: `0x43d6..0x4cd0` (~2288 B), `0x40c1..0x42f0` (~533), `0x32ba..0x3450` (~388),
`0x3dadb..0x3dc50` (~363), `0x191ef..0x19350` (~347), `0x1d46..0x1e80` (~293), `0x159ea..0x15ac0` (~196).
Some of that is embedded jump-table/const data, but ~3.3% of `.text` is outside the instrument's reach
and it is *not* a one-off. (Note `0x1d46..0x1e80` sits right next to the camera thunk `SFX_UpdateCamera`
region — worth a leaf sweep before any camera negative-existence claim.)

## 5. Precision notes / what I did NOT verify

* The mechanism is "**no `RUNTIME_FUNCTION` entry**", of which "no-unwind leaf" is the common cause. The
  claim's wording is accurate for this instance; the general rule should be stated as the former.
* I did not exhaustively prove `0x15982` is the *only* writer of `EFFARR[i].data` (that would itself be a
  negative-existence claim through the same blind instrument). It is sufficient that the one known writer
  lies in the blind zone — the claim's causal story holds.
* Runtime values in `EFFARR` remain zero-on-disk `.bss`; nothing here is a runtime observation.

## 6. Recommended instrument fix (for whoever touches refkit next)

Add to `refkit.py`, and route every negative-existence question through it:
`gap_sweep(pe)` — compute `.text` minus `.pdata`, strip leading/trailing `0xCC`/`0x00` runs, disassemble
each residue from its first non-pad byte, and yield instructions so `xrefs_to`/`xref_index` can take an
`include_gaps=True`. Cross-check any resulting hit against the x86 build (no `.pdata` there at all, so
x86 analysis was never subject to this specific bias).
