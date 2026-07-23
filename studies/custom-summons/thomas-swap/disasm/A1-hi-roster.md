# A1 — The full `Hi_*` roster + call graph (FF9SpecialEffectPlugin.dll, x64)

Shared blackboard for the summon-cutscene disasm round. All RVAs are image-relative
(`ImageBase = 0x180000000`). Ground-truth calibration (stride 0x58, base 0x220830,
`SetSummonMotion` @0x17a10) is CONFIRMED and extended below.

Reproduce: `py a1_roster.py` / `a1_callgraph.py` / `a1_table.py` / `a1_callers.py` / `a1_reach.py`
in this dir (each stands on `refkit`).

---

## 0. TL;DR for the round's core goal (recover the creature's true per-frame transform)

The DLL DOES compute and store every summoned creature's per-bone **world transform each frame**,
and already exposes two getters for it. The values are runtime-only (scratch `.bss`, zero on disk),
but the **struct path is fully static-recoverable** and is a stable probe/read target:

```
summonModels[idx]  (rec, stride 0x58, base RVA 0x220830)
  rec+0x00 -> DATA block
                DATA+0x38 -> BONE-MATRIX ARRAY   (stride 0x20 per bone)
                   bone[k]+0x00 : 3x3 rotation, 9x int16  (PSX MATRIX.m)
                   bone[k]+0x14 : translation X  (int32; GetSummonBonePos reads low16)
                   bone[k]+0x18 : translation Y
                   bone[k]+0x1c : translation Z
```

`Hi_GetSummonBoneMatrix(idx, boneIdx, out)` @**0x18630** copies the full 32-byte matrix;
`Hi_GetSummonBonePos(idx, boneIdx, out)` @**0x185b0** copies just the int16 X/Y/Z translation.
The prior round's "no data-side method can recover the transform" holds for STATIC bytes only —
the correct recovery is to read `[[0x220830 + idx*0x58] + 0x38] + boneIdx*0x20` **per frame at
runtime** (probe hook or calling the getter), which is where the animated pose actually lives.
This array is written by the DrawSummon/animation update, not by any data file.

---

## 1. The runtime structs (fully decoded from code)

### `summonModels[]` record — base RVA **0x220830**, stride **0x58** (88 B), `rec = base + idx*0x58`
| off | type | meaning | evidence |
|-----|------|---------|----------|
| +0x00 | qword | ptr to model DATA block (0 ⇒ not loaded) | 0x18630, 0x17a10, all getters |
| +0x50 | byte  | registered/active flag (0 ⇒ error stub fires) | `cmp byte [rec+0x50],0; je err` everywhere |
| +0x54 | u16   | current motion frame index (clamped vs motion frame-count) | SetSummonMotion zeros it @0x17a36; SetSummonMotFrame writes/clamps it @0x17aac |

### model DATA block (pointed by rec+0x00)
| off | type | meaning | evidence |
|-----|------|---------|----------|
| +0x10 | qword | MOTION pointer; motion frame-count = `u16 [motion+2]` | SetSummonMotion @0x17a3b writes it; SetSummonMotFrame @0x17a94 reads `[[+0x10]+2]`; DrawSummon @0x17776 loads it |
| +0x20 | dword | mesh-hide bitmask (bit set = mesh hidden) | Show @0x1880e `and ~(1<<n)`; Hide @0x1886c `or (1<<n)` |
| +0x38 | qword | **BONE-MATRIX ARRAY** ptr, stride 0x20 (PSX MATRIX) | GetSummonBoneMatrix @0x18653; GetSummonBonePos @0x185d3 |
| +0x70 | qword | per-mesh-part **texanim** control array, stride 0x18 | StartTexAnim @0x188cb (`+8 |=3`, `+0x10 frame=0`, `+0x16 =0x1000`); StopTexAnim; RegisterSummonModel pointer-fixup @0x160f5 stores `[+0x70]` |

### PSX MATRIX entry (bone-matrix array element, 0x20 B)
`m[3][3]` int16 @+0x00 (18 B) · pad @+0x12 · translation int32 `t[0]`@+0x14 `t[1]`@+0x18 `t[2]`@+0x1c.
This is the classic PSX `MATRIX` layout; `GetSummonBonePos` returns the int16-truncated `t`.

---

## 2. Dispatch architecture (how these are reached)

- **ONE mega-interpreter @0xeea4** (range `[0xeea4..0x12321]`, ~13.4 KB) is the `.seq`/SFX **command
  executor**. Every summon `Hi_*` op is invoked from a *distinct call site inside it* (see caller
  column). This is the native side of the `.seq` sequencer.
- A **function-pointer dispatch table** in `.rdata` (`tbl@~0x68780 … 0x68cf8`, one qword per SFX
  opcode) also holds each handler's ENTRY. Summon/Eff handler slots are called out in §3
  (`tbl@…`). The table entry is always the *entry/validator*, never the cold stub.
- The 13 exports (`SFX_Play`@0x2880, `SFX_GetPrim`@0x1800, `SFX_Update`@0x13a0,
  `SFX_UpdateCamera`@0x1e80, `SFX_BeginRender`@0x1630, …) are **double-thunked** (`jmp` @0x1cf0-0x1e70
  → `jmp` → real body below the `.pdata` floor 0x2300). A `.pdata`-only forward-BFS therefore shows
  no direct export→`Hi_*` edge: the linkage is **interpreter-mediated** (exports drive the `.seq`
  interpreter @0xeea4, which calls the handlers). Every summon `Hi_*` has exactly one caller and it
  is 0xeea4 (or, for Register, also the init paths 0x3de37/0x47330).

### Two code shapes (how to read the table)
- **Pattern A — flat handler:** one `.pdata` range; the debug-string `lea` sits inline on the tail
  malloc/arg-fail path; called directly from the interpreter. (All the getters/setters/modifiers.)
- **Pattern B — validator → cold-split body → separate cold error stub:** MSVC split the arg-check
  entry, the hot work body, and the cold `printf+abort` funclet into 3 `.pdata` ranges. The **entry
  = the small validator** (in the dispatch table, references EFFARR/SUMMON, `je` to the stub); it
  falls through to the big work body; the **stub carries the debug string**. (All `Draw*` + all
  `Register*`.) `locate_function` returns the STUB — the real body is the range just below it.

---

## 3. The roster table

Columns: **name | entry (dispatch) | real work body | cold error stub | callers | role**.
"Pattern A" ⇒ entry == body == stub-tail (one range). RVAs verified by string-xref + branch graph.

### (a) Summon subsystem — the creature renderer
| name | entry rva | body range | cold stub | dispatch / caller | role |
|------|-----------|------------|-----------|-------------------|------|
| **Hi_RegisterSummonModel** | 0x15ee0 (85B) | 0x15ee0→0x15f35→0x1606c(ptr-fixup) | 0x16112 (52B, 2 aborts) | tbl@0x68838; call 0xf75a + init 0x3e44e/0x47491 | register a creature model into `summonModels[idx]`; PSX TMD/addr relocation (`[+0x70]` fixup @0x1606c) |
| **Hi_DrawSummonModel** | 0x17710 (48B validator) | 0x17740 (690B) | 0x179f2 (29B) | tbl@0x68848; call 0xf851 | draw the creature: walks motion+primitive stream (`[DATA+0x10]`, helpers 0x12940/0x12b00); **writes the per-frame bone matrices** |
| **Hi_SetSummonMotion** | 0x17a10 (81B, Pattern A) | — | inline @0x17a44 | tbl@0x68850; call 0xf87e | bind motion ptr → `[DATA+0x10]`; zero frame counter `[rec+0x54]` |
| **Hi_SetSummonMotFrame** | 0x17a70 (99B, A) | — | inline @0x17ab6 | tbl@0x68aa0; call 0x10d6a | set `[rec+0x54]` = frame, clamped to `[[DATA+0x10]+2]` frame-count |
| **Hi_GetSummonBonePos** | 0x185b0 (117B, A) | — | inline @0x18608 | tbl@0x68c28; call 0x115cb | read bone int16 X/Y/Z from `[[DATA+0x38]+k*0x20 +0x14/0x18/0x1c]` |
| **Hi_GetSummonBoneMatrix** | 0x18630 (98B, A) | — | inline @0x18675 | tbl@0x68ca0; call 0x1195a | **copy full 32-B PSX MATRIX** (rot+trans) for a bone — the true per-frame transform getter |
| **Hi_ShowSummonModelMesh** | 0x187e0 (84B, A) | — | inline @0x18817 | tbl@0x68c68; call 0x117df | clear mesh-hide bit in `[DATA+0x20]` (bit clear = visible) |
| **Hi_HideSummonModelMesh** | 0x18840 (82B, A) | — | inline @0x18875 | tbl@0x68c70; call 0x11806 | set mesh-hide bit in `[DATA+0x20]` — this is the `HideMeshes=<hex>` op |
| **Hi_StartSummonTexAnim** | 0x188a0 (138B, A) | — | inline @0x1890d | tbl@0x687e0; call 0xf439 | enable a mesh-part's UV/texture animation in `[DATA+0x70]` (stride 0x18) |
| **Hi_StopSummonTexAnim** | 0x18930 (85B, A) | — | inline | tbl@0x687d8; call 0xf408 | disable a part's texanim in `[DATA+0x70]` |
| **Hi_ModifySummonModelAbr** | 0x18af0 (90B, A) | — | inline @0x18b2d | tbl@0x68c18; call 0x1157a | set per-bone semi-transparency (ABR) mode; arg 0xff = skip; tail-jmp helper 0xc880 with `idx<<5` |
| **Hi_ModifySummonModelRGB** | 0x18b50 (76B, A) | — | inline | tbl@0x68988; call 0x10106 | set per-bone RGB tint |

### (b) Eff-model family — generic effect meshes (shared substrate, NOT the creature)
| name | entry rva | body range | cold stub | dispatch / caller | role |
|------|-----------|------------|-----------|-------------------|------|
| Hi_FreeEffModel | 0x159a0 (74B, A) | — | inline | tbl@0x68c38 | free an eff-model slot |
| Hi_RegisterSolidEffModel | 0x15ac0 (166B, A) | — | inline | tbl@0x68828 | register flat-shaded eff mesh |
| Hi_RegisterGouEffModel | 0x15b70 (170B, A) | — | inline | tbl@0x687b0 | register Gouraud eff mesh |
| Hi_RegisterTexEffModel | 0x15c20 (260B, A) | — | inline | tbl@0x68830 | register textured eff mesh |
| Hi_RegisterTexListModel | 0x15d30 (214B, A) | — | inline | tbl@0x68818 | register tex-list eff mesh |
| Hi_RegisterTexPtrModel | 0x15e10 (197B, A) | — | inline | tbl@0x68cd8 | register tex-ptr eff mesh |
| Hi_DrawEffModel | 0x16150 (52B val) | 0x16184 (963B) | 0x16547 (29B) | tbl@0x68840 | draw an eff model |
| Hi_DrawSliceEffModel | 0x16570 (62B val) | 0x165ae (543B) | 0x167cd (29B) | (interp 0x16587 area) | draw sliced eff model |
| Hi_DrawEffModelByBone | 0x167f0 (71B val) | 0x16837 (1097B) | 0x16c9d (29B) | tbl@0x68c90 | draw eff model attached to a bone; inlines bone-matrix fetch (reuses stub 0x16c80) |
| Hi_DrawMorphEffModel | 0x16cc0 (99B val) | 0x16d23 (437B) | 0x17156 (55B, 2 aborts) | tbl@0x68c98; call 0x11920 | draw morph-target eff model |
| Hi_DrawMorphModelByBone | 0x17190 (95B val) | 0x171ef (358B) | 0x176d4 (55B, 2 aborts) | tbl@0x68c08; call 0x113f9 | draw morph eff model on a bone; inlines bone-matrix fetch (reuses stub 0x176ba) |
| Hi_ModifyEffModelAbr | 0x18990 (93B, A) | — | inline | tbl@0x68c50 | eff-model ABR |
| Hi_ModifyEffModelRGB | 0x189f0 (80B, A) | — | inline | tbl@0x68c58 | eff-model RGB |
| Hi_SetEffModelOffset | 0x18a40 (76B, A) | — | inline | (interp) | eff-model position offset |
| Hi_SetEffModelSlice | 0x18a90 (82B, A) | — | inline | (interp) | eff-model slice param |
| Hi_SplitMdlVertex | 0x17ae0 (79B, A) | — | inline | call 0x11f1e | split model vertex (variant 1) |
| Hi_SplitMdlVertex | 0x18c00 (72B, A) | — | inline | call 0x12015 | split model vertex (variant 2; shares debug name) |
| Hi_GetSplitMdlVertex | 0x17b30 (76B, A) | — | inline | (interp) | read a split vertex |
| Hi_GetMdlVertexPtr | 0x18000 (79B, A) | — | inline | (interp) | get raw model-vertex ptr |

### (c) helpers / panic
| rva | role |
|-----|------|
| 0x1534c (29B) | **Hi_DebugPSGData** cold stub (validator/body @0x15200) — PSG debug dump |
| 0x186a0 (24B) | shared draw helper (called by all Draw* bodies: 0x16184/0x165ae/0x16d23/0x17740) |
| 0x1800151a0 | the panic/abort trampoline every cold stub tail-calls after `printf` |
| 0x220890 | DBGCTX — the global error/printf context every stub loads before aborting (not an array) |
| 0x220230 | EFFARR — the eff-model registry base (distinct from summonModels 0x220830) |

---

## 4. Notes for downstream agents

- To **track the creature per frame**: read `[[0x220830 + idx*0x58] + 0x38]` then index `boneIdx*0x20`;
  translation at `+0x14/+0x18/+0x1c`. `idx` is the summon-model slot (the same index passed to every
  `Hi_*Summon*` op). This array is filled by `Hi_DrawSummonModel` @0x17740 each frame — a hook right
  after that draw (or a per-frame call to the 0x18630 getter) yields the animated world pose.
- `Hi_HideSummonModelMesh` @0x18840 (mesh-hide bit in `[DATA+0x20]`) is the documented `HideMeshes`
  mechanism — Show/Hide are pure bitmask toggles, cheap and side-effect-free.
- The camera path (`SFX_UpdateCamera`@0x1e80, resolve_position @0x1800145a0, anchor scratch @0x220060)
  is a SEPARATE subsystem from the summon-model array; the anchor @0x220060 remains runtime scratch.
  The summon per-frame *model* transform (this file) does NOT route through the camera anchor — it is
  its own `[DATA+0x38]` matrix array, so it is independently readable.
- All Register/Draw follow Pattern B; all get/set/modify/texanim follow Pattern A. `locate_function`
  returns the Pattern-B **stub** — always step to the body range immediately below the stub (or the
  validator/table entry above it).

Provenance: read-only static analysis of the user's installed DLL; RVAs/mnemonics/struct offsets only.
No stock geometry or animation bytes extracted; no DLL modified.
