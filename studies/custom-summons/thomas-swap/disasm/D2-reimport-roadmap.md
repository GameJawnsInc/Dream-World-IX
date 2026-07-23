# D2 — THE ROADMAP TO DECODABLE / RE-IMPORTABLE SUMMON CUTSCENES

**Slice D2 of the summon-cutscene disasm round.** The user's goal, verbatim: *"i'd like to eventually get
to a point where the summon cutscenes are decodable/re-importable like all the other aspects of the game
we've hit."* This document is the honest, staged plan to get there — anchored in what **M1–M5** actually
established, with everything undecoded marked as a **dependency**, never as an assumption.

Every stage carries: **delivers · depends on · effort · risk · provenance verdict**.
Effort units: **LOW** ≤ 1 working session · **MED** 2–4 sessions / 1 playtest round · **HIGH** 5+ sessions /
multiple playtest rounds.

RVAs are image-base-relative for the user's own `FF9SpecialEffectPlugin.dll`
(x64 `ImageBase 0x180000000`, x86 `0x10000000`). C# cites are relative to
`C:/gd/FFIX/Memoria/Assembly-CSharp/`. **No DLL was modified. No stock bytes were written into the repo.**

---

## 0. HEADLINE — four results that set the plan

1. **The READ half is essentially already won and is a packaging job, not a research job.** M2 decoded the
   container (372/372 files walk to their exact length), M4 decoded the geometry (1005/1005 blocks pass two
   independent chain-closure identities), M5 decoded the motion (8/8 Bahamut clips tile with 0 gaps /
   0 overlaps), M3 pinned all 216 native ops, and the camera sub-file shares the byte format the kit's
   `battle/camera_codec.py` **already round-trips byte-exact**. What remains for a full "summon-cutscene
   disassembler" is one decode (§2 R5) and a CLI.

2. **NEW THIS SLICE — the last opaque layer is readable with an off-the-shelf tool.** The id-3 payload is
   confirmed *raw little-endian MIPS R3000A machine code* (§1.1), and **capstone-MIPS is already installed**
   (5.0.7). M2 rated a MIPS disassembler `MED`; it is really "call capstone + annotate". The one genuine
   missing piece for *named* calls is a 4-byte constant (§1.2), not a decoder.

3. **NEW THIS SLICE — the whole WRITE tier hangs on one untested 2-cast experiment.** A modded
   `ef###.bytes` appears to be loadable straight out of a mod folder at
   `<modfolder>/FF9_Data/SpecialEffects/ef227` (extensionless), by the same disc-override mechanism every
   other kit asset uses (§1.3, source-traced end to end). If that holds, native re-import is **data-only,
   no DLL patch**. If it does not, the entire native write tier is dead without an engine change. **Test it
   before spending anything else on TIER W.**

4. **THE STRATEGIC ANSWER (§3): invest in READ, invest in the CHEAP half of WRITE, and do NOT build a
   from-scratch native summon.** The managed `FileList.txt` → `.sfxmodel` → FBX route (rung 7) already
   renders our own rigged, animated creature in a live battle, in-game proven. What it lacks is not the
   creature — it is the **camera** and **staging**, and both have cheaper doors than a container rewrite.
   The single highest-value item in this entire document is **§2 R6**, a ~20-line probe change that closes
   the round's motivating bug.

---

## 1. NEW FINDINGS THIS SLICE (reproducible; they change the effort estimates)

### 1.1 The id-3 code image is genuine MIPS R3000A — CONFIRMED on real bytes

Scanned every 32-bit word of the id-3 payloads in `ef227`, `ef431`, `ef261`, `ef210`, `ef381`, `ef000`,
`ef001`, `ef094` (locally-extracted blobs under `C:/gd/SCRATCH/summon-format/`; **statistics only, no
payload echoed or copied**):

* The opcode-field histogram is a textbook PS1 profile: `0` (SPECIAL/ALU) dominant, then `35` LW, `9` ADDIU,
  `43` SW, `41` SH, `37` LHU, `15` LUI, `33` LH, `40` SB, `5` BNE — and **`18` = COP2 (the GTE)**, 102
  occurrences in `ef261` alone, which independently corroborates M3 §3's "GTE command dispatch = VM op 0x41".
* **Every `J`/`JAL` resolves inside its own chunk's window** under the standard MIPS rule
  `(PC & 0xF0000000) | (imm26 << 2)`: `ef227` chunk 0 targets land in `0x801E7700 .. +0x5000`, chunk 1's in
  `0x801EC700 .. +0x5000` — exactly the `psxBase = 0x801E7700 + (slot & 1) * 0x5000` law
  (`fn 0xd390 @0xd431`, M2 §3.2). Nothing forces that unless the words really are MIPS.
* **Scale check (why this is tractable):** the *entire* Bahamut cinematic's native choreography is
  **two entry-point programs** — chunk 0 program 0 at image offset `0x9d4`, chunk 1 program 0 at `0x108c` —
  inside code regions of `0x3120` and `0x42BC` bytes = **≈ 7,400 instructions total**, the same order of
  magnitude as reading one field's `.eb`.

> **Effort consequence:** M2 §10's rung **R6 ("MIPS disassembler", MED)** drops to **LOW–MED**. Capstone
> (`CS_ARCH_MIPS`, `CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN`) does the decode; our work is annotation.

### 1.2 The HLE trap words are NOT in the effect file — they are a DLL-synthesised PS1 jump table

**Hypothesis tested and REFUTED:** that an effect's native-call manifest could be recovered by scanning the
file for `0xFF0000xx` trap words (M3 §3's `0xec31: if ((v & 0xFF000000) == 0xFF000000) nativeCall(ctx, v & 0x3FFFFF)`).
A sweep of **all 372** stock containers' id-3 payloads found **zero** such words. (It cannot work anyway:
a MIPS `JAL`'s `imm26 << 2` can never reach `0xFF000000`.)

**What is there instead — CONFIRMED, cross-arch:**

| item | x64 | x86 |
|---|---|---|
| trap-sentinel table | `.data` RVA **`0x68250`**, **exactly 216 dwords** `0xFF000000 \| i` for `i = 0..0xD7`, in opcode order; word 216 is `0` | `.data` RVA **`0x50910`**, identical 216-entry run |

216 = the dispatcher's own bound (`0xee98: cmp edx,0xd7 / ja`, M3 §0). Registration, read directly
(`0x30c20..0x30d44`, each block is `lea rdx,<hostPtr>; lea rcx,<bankTable 0x576a10>; mov [slot],eax /*previous result*/; call 0x12940`):

```
0x30d07  lea rdx,[rip+0x37542]   -> 0x68250   (the sentinel table)
0x30d0e  lea rcx,[rip+0x545cfb]  -> 0x576a10  (the PSX bank table, M4 §1)
0x30d1b  call 0x12940            (host ptr -> PSX address)
0x30d2e  mov  [rip+0x1ef244],eax -> RVA 0x21FF78     <-- the table's PSX base
0x30d20  lea rdx,[rip+0x38a09]   -> 0x69730  (the installed camera struct, FINDINGS §5)
0x30d39  mov  [rip+0x1ef23d],eax -> RVA 0x21FF7C     <-- the camera struct's PSX base
```

So an effect program reaches a native op by **loading an entry from that table and jumping through the
register** — the target `0xFF0000xx` is the trap the VM catches. **Consequence:** naming each call needs the
table's PSX base. That base must be a **fixed constant** (the on-disk PS1 code was compiled against it), so
**one 4-byte read settles it permanently**:

```csharp
Int32 hleTableBase = Marshal.ReadInt32(pluginBase + 0x21FF78);   // and 0x21FF7C = the camera struct
// then, offline forever: <loaded word at hleTableBase + 4*op>  ==  native opcode `op`
```

> ⚠ **Stated confidence.** The `store-before-next-call` pairing is the only self-consistent reading of that
> block (the first call's result cannot be stored before the first call), but an off-by-one reading would put
> the table at `0x21FF70` instead. **Read both dwords once; the one whose value indexes a 216×4 = 0x360-byte
> span the effect programs actually load from is the table.** Cost: one probe row. Do not guess.

### 1.3 A modded `ef###.bytes` looks loadable from a mod folder — the WRITE-tier gate

`SFX.cs:1974-1979` loads the container with `AssetManager.LoadBytes($"SpecialEffects/ef{effNum:D3}", true)`.
Tracing `AssetManager.LoadBytesMultiple` (`Global/Asset/AssetManager.cs:541-627`):

* `IsMemoriaAssets("SpecialEffects/…")` is false (needs a `Data/` prefix, `AssetManagerUtil.cs:417-421`).
* `GetBelongingBundleFilename("SpecialEffects/ef227")` returns **`""`** — `GetModuleStartPath`
  (`AssetManagerUtil.cs:87-117`) knows only `FieldMaps/ BattleMap/ WorldMap/ Models/ Animations/ Sounds/
  CommonAsset/`; `SpecialEffects/` matches none. So the bundle branch is skipped entirely.
* `ForceUseBundles` is a debug toggle, default `false` (`AssetManager.cs:909`, set false at
  `BundleScene.cs:182`) — so control reaches the disc loop at `AssetManager.cs:610-617`:
  `modfold.TryFindAssetInModOnDisc(name, out fullPath, GetResourcesAssetsPath(true) + "/")`, and
  `TryFindAssetInModOnDisc` (`AssetManager.cs:971-977`) computes
  `pathOnDisc = FolderPath + "FF9_Data/" + "SpecialEffects/ef227"` → `File.ReadAllBytes` (`:388-391`).

⇒ **predicted override path: `<modfolder>/FF9_Data/SpecialEffects/ef227` — no extension.** Mod folders are
walked high-to-low, so a stacked folder shadows lower ones (the familiar law). Caveat: if a mod folder ships
an `AssetList` index, `TryFindAssetInModOnDisc` consults that set instead of the filesystem.

**Confidence: MED-HIGH (source-traced, never run).** It is a $0, 2-cast experiment (§2 W0) and it gates every
write rung. **Do not build a container writer before proving it.**

---

## 2. THE STAGED ROADMAP

### TIER R — READ (a committable parser/inspector/disassembler). *This is the user's stated goal.*

| rung | delivers | depends on | effort | risk | provenance |
|---|---|---|---|---|---|
| **R1 — container inspector** | Ship `ef_container.py` into the kit + a `summon-inspect` CLI: chunk/resource table, all 10 resource types, sub-file directory, id-3 program table, creature-package header (motion count, texture pages, CLUT rows, motion offsets), and the loader-script listing with the full opcode **validity map** (refuses the illegal `0x30..0x4F` band and the NULL table-B slots for free). | nothing — M2 §3–§8, parser written and validated **372/372** | **LOW** (packaging + a CLI + install-gated tests) | LOW | **COMMITTABLE** — parser code, zero stock bytes |
| **R2 — geometry parser** | Skeleton (bone-link table), mesh table, vertex pools, all 8 `POLY_*` buckets, per-part tpage/clut binding, the UV V-offset bake. The `pMeshTable == 0x18 + (boneCount−1)*4` law + the two chain-closure identities double as a free self-validating linter. | R1 (to find geom blocks by table lookup instead of content scan — M4 §7.7) | **LOW–MED** (~300 lines; M4 §8 says the doc alone specifies it) | LOW–MED — 4 named opaque fields (M4 §7.1–3) must be carried **verbatim**; they don't block reading | **COMMITTABLE** parser; any dumped geometry is local-only |
| **R3 — motion parser** | Clip header, the 12-bit coarse+fine rotation encoding, root-translation tracks, the frame-advance rule. Makes a stock creature's **entire skeletal animation computable offline** from the container (M5 §9.5). | R2 (the skeleton lives in the model, not the clip — M5 §4) | **LOW–MED** | LOW | **COMMITTABLE** parser; decoded animation is local-only |
| **R4 — camera sub-file read/write** | Parse + re-emit an effect's camera keyframe tracks. **The format is already solved**: `SFXDataCamera.LoadFromSFX` (`SFXDataCamera.cs:112-128`) uses the *same* `Load(BinaryReader)` as `LoadFromBSC`, i.e. the exact stream the kit's `battle/camera_codec.py` round-trips byte-exact for raw17. | R1 (sub-file directory, M2 §5) + a corpus round-trip over the 24 creature effects | **LOW** (adapter + acceptance test) | **MED** — the *bytes* are readable; the **geometric meaning** (spherical pitch/orientation/roll/distance → eye/at) is applied inside the DLL and is a dead `// TODO` in managed code (`SFXDataCamera.cs:550-555`). We can write keyframes but not preview them until **W-CAM**. | **COMMITTABLE** |
| **R5 — the effect-program disassembler** (**the headline**) | A readable listing of a stock summon's *actual* choreography — the layer that has been opaque since this study began. Capstone-MIPS decodes the words; `M3-opcode-table.json` supplies the 216 op names/arities/operand kinds; a small `$a0..$a3` constant-tracker (`lui/ori/addiu/lw` back-walk) names the arguments. | §1.1 (done) + §1.2's 4-byte constant + `M3-opcode-table.json` (done) | **LOW–MED** (downgraded from M2's MED) | MED — argument tracking is a small dataflow problem; not every arg is a constant | **TOOL committable. The OUTPUT is not** — a disassembly listing of Square's PS1 code is derived stock content: keep listings under `C:/gd/SCRATCH/summon-format/`, same line as the extracted bytes. |
| **R6 — the runtime probe fix + trace** (**do this first**) | (a) The creature's *true* per-frame world pose: dereference `*(MATRIX*)(SummonData+0x38)` and read **bone 0** (M1 §6.2, M5 §5) — the composed matrix, of which the currently-logged `+0x40` is only one input; (b) `rec+0x54` (motion frame) and `DATA+0x78` (the scale triple) — 2 ints that make the log self-decoding; (c) a 32-slot EFFARR census row (M1 §10) that settles the eff-vs-summon question empirically in one cast; (d) optionally the opcode timeline via the pending-trap word (M3 Rung B). | the s52 probe exists and already resolves the module base (`SfxMeshProbe.cs:302-320`). (d) additionally needs the `PsxCtx*` (M3 §7.2, OPEN). | **LOW** for (a)–(c); **MED** for (d) | LOW — reads only | **SANCTIONED** — choreography/staging reads, the same class as the existing `ROOT` rows. **Hard limit (M1 §10): log bone 0 and a couple of named extremities only. Dumping `bones[1..N-1]` across a cast IS stock-animation extraction — blocked.** |

**R-tier exit criterion — "a summon cutscene is decodable":** `summon-inspect ef227` prints the container map,
the creature package (93 bones / 2 meshes / 8 clips / 6 texture pages), the camera keyframe tracks with their
absolute shot clock, the loader script, and an annotated MIPS listing of both effect programs naming every
`Hi_*` call. **That is the deliverable the user asked for, and nothing in it requires a write.**

---

### TIER G — GEOMETRY / MOTION EXPORT (validation + rig reference, *not* a content source)

| rung | delivers | depends on | effort | risk | provenance |
|---|---|---|---|---|---|
| **G1 — stock creature → glTF/FBX + clips** | Proves R2/R3 are right (a mangled export is an immediate falsification), and teaches the rig conventions a conformant custom creature must satisfy. | R2 + R3 | **MED** | MED — the real gate is textures: `tpage`/`clut` are VRAM coordinates and the pixels arrive through a *different* resource + `PSXTextureMgr` (M4 §7.5). Geometry/animation alone export cleanly. | **HARD LINE.** The exporter is committable. **Every byte it emits is Square-Enix content**: scratch only, never committed, never shipped, never placed in a mod folder we distribute. Its value is *validation and reference*, not content. |
| **G2 — our model → this format (emitter)** | The writer half: 8-bucket primitives, pooled UV/colour, run-length rigid skinning, the bone-link table, the 5 mesh sub-pointers. M4 §10.2 is right that emitting is *easier* than TMD — the writer chooses the bucket. | G1 (conventions) + R2/R3 | **MED** | MED — the 4 opaque fields (M4 §7.1–3) must be synthesised or copied; the two chain identities catch most errors offline | **CLEAN** (our geometry) |

---

### TIER W — WRITE / RE-IMPORT

| rung | delivers | depends on | effort | risk | provenance |
|---|---|---|---|---|---|
| **W0 — THE GATE: prove the container override loads** | Cast 1: drop a **byte-identical** copy of `ef227` at `<modfolder>/FF9_Data/SpecialEffects/ef227` → cast → the cinematic must be unchanged (proves the path + a faithful copy). Cast 2: flip one `WAIT` operand in the loader script at file `0x400+` (op `0x01`, in-sector, **zero relayout**) → cast → the pacing must visibly change (proves we can author). | §1.3 | **LOW** (2 casts) | LOW — revert = delete one file | Modified copy of the **user's own install asset**, built at deploy time into their own mod folder, **never committed** — the verbatim-fork precedent exactly |
| **W1 — container writer** | Rebuild a container from parsed parts; acceptance = **byte-identity round-trip on 372/372** (the cursor-lands-on-EOF invariant is the format's own checksum). Uses the **native** extra-field rule `info != 0`, not `SFXBinaryFile.cs`'s `chunkIndex == 0` correlate (M2 §3.3 — the two diverge on synthesised data and the C# rule silently corrupts every later offset). | R1 + W0 | **LOW–MED** | LOW | **COMMITTABLE** tool; outputs are per-install |
| **W2 — loader-script patcher + linter** | Retimed loads, camera/sound sub-file re-selection, program-run ordering, channel-flag waits. | W1 | **LOW** | LOW | **COMMITTABLE** |
| **W3 — texture / CLUT reskin** | **The first visible custom content through the native path.** The creature's pages are plain `64×128` 16bpp blocks at a known offset with an exact size law (`texBytes == pageCount*0x4000`, `clutBytes == clutRows*0x200`, both 24/24 — M2 §8). A recolour needs no code emission at all. | W1 | **LOW** | LOW | **CLEAN** (our pixels into the user's own container at deploy time) |
| **W4 — camera-track authoring** | Author a native summon's shot list: cuts, dollies, the near-Z/H zoom. | W1 + R4 (+ **W-CAM** for offline preview) | **MED** | MED — blind-write-and-playtest until W-CAM lands | **COMMITTABLE** |
| **W-CAM — decode the native spherical→matrix camera step** | Turns R4 from "we can write bytes" into "we can *author*". Bounded target set: `SFX_UpdateCamera` body `0x1e80..0x2030`, the stepper `@0x2030`, `resolve_position@0x145a0` (`anchor + 4096.8·(cos/sin θ)` — **K = 4096.8 already CONFIRMED**, FINDINGS §5), `lookup_anchor@0x148f0`, the installed struct `@0x69730` → the 13 floats `@0x211df0`. | R4 | **MED** | **LOW–MED — and its validation is free and airtight**: predict `VIEW`/`PROJ` offline from the parsed keyframes and compare against the s52 probe's *already-logged* `VIEW`/`PROJ` rows for the same cast. A closed-loop falsifiable check, no new playtest. | **COMMITTABLE** (algorithm, not content) |
| **W5 — MODEL-PACKAGE SWAP** ("our creature inside a stock summon's real cinematic, natively") | Replace the id-4 (texture) + id-5 (model image = geometry + motion clips) payloads while keeping the donor's id-3 program, loader script, cameras and sound. **The donor's choreography drives our creature.** This is the only path to stock-grade native parity. | W1 + G2 + **R5** (you must *read* what the donor program demands of the rig) | **HIGH** | **HIGH** | Our geometry + the donor's other sections ⇒ **build-time transform of the user's own install into their own mod folder; never committed, never redistributed.** Same lane as a verbatim field fork. |
| **W6 — a from-scratch native summon (MIPS emission)** | A genuinely new native effect: emit an id-3 program (`lui/ori/addiu/lw/sw/jal/jr/beq/bne/nop` + the yield — M3 Rung C estimates ~10 forms cover every summon op). | R5 + a mini MIPS assembler + W1 + G2 + W4 | **HIGH+** | **HIGH** | clean-but-pointless (see §3) |

#### W5's hard conformance constraints (all cited — a rig that violates any of these renders wrong, silently)

* **Parent index must be lower than the child's** — the hierarchy pass walks nodes in index order with no
  sorting pass (M5 §4).
* **A bone's local translation is a single scalar length along local Z**; only the root gets per-frame
  translation (M5 §4, §10). A DCC rig with arbitrary bone offsets must be pre-conformed.
* **Mesh ordinals are load-bearing**: the donor program's `Hi_ShowSummonModelMesh`/`Hi_HideSummonModelMesh`
  (ops **157/158**, M3 §2) address meshes by *bit index* in `SummonData+0x20`. Our mesh order must match the
  donor's intent, or the wrong parts vanish mid-cast.
* **Motion clip count and frame counts** must satisfy the program's `Hi_SetSummonMotion` (op 26) and
  `Hi_SetSummonMotFrame` (op 100) arguments — and note op 100 **wraps to 0** on an out-of-range seek rather
  than clamping (M3 §2).
* **Bone indices are queried by number**: `Hi_GetSummonBonePos`/`GetSummonBoneMatrix` (ops 149/164) and
  `Hi_DrawEffModelByBone` (op 162) attach the effect's beams/glows to *specific* creature bones
  (M1 §7). Our skeleton must keep those slots semantically where the donor put them.
* **≤ 6 material parts** per model (three tiled `u16[6]` tables ending exactly at the geometry pointer —
  M4 §2), **≤ 7000 vertices per mesh** (`cmp idx,0x1b58 @0x50b3`).
* **Model-image budget `modelBytes ≤ 0x50000`** — the loader keeps `0x50000 − modelBytes` as free space
  (`@0x3e40d`, M2 §8). Bahamut spends `0x26C74` of it.
* **VRAM budget**: `pageCount × 0x4000` + `clutRows × 0x200`.
* **Failure mode is a hang, not an exception**: a NULL `data` pointer routes to the `"HIRAISHI ERROR:"` stub
  that **spins forever** (`0x151f0: jmp 0x151f0`, M1 §3). Lint offline; never ship an unvalidated container.

#### The id-fork law (mirrors the field lane)

`SFX_Play` stores the effect number at `0x3678E8` and native code compares it against literals
(`0x12d`=301, `0x7e`=126, `0xb8`=184, `0x95`=149 — e.g. `@0xf5f8`, `@0x104b4`, `@0x112a9`; M2 §1), and
`SFX.cs` carries further name/id-keyed special cases (Ark's subOrder flips, per-summon sound tables).
**A fresh native effect id inherits none of them.** ⇒ For the native lane, **fork an existing id in place**;
mint fresh ids only on the managed lane.

---

## 3. THE STRATEGIC QUESTION — is native re-import even the right target?

**Asked plainly: rung 7 already renders OUR OWN rigged, animated model inside a live FF9 battle effect, with
zero native involvement. So why decode a native container at all?**

### 3.1 What each route actually delivers (no hedging)

| capability | managed route (`FileList.txt` → `.sfxmodel` → FBX) | native re-import (TIER W) |
|---|---|---|
| our own creature, rigged + animated | **PROVEN in-game** (rung 7, 3 casts: "upright, facing forward, and idling the whole time") | W5, HIGH effort |
| our own particles | **PROVEN** (rung 5 — the magenta ring, first new visual content ever in an FF9 summon) | via eff-model registration; more work |
| our own audio | **PROVEN** (rung 3, minted sfx 100000) | loader-script `PLAY_SOUND` swap, W2 |
| authored choreography | **PROVEN** — the managed `.seq` DSL, a real text language the kit can lint/emit (rung 6, 25 ops, damage landed) | **MIPS machine code** — there is no data command stream at that layer (M3 §3.1: no wait op, no camera op, timing *is* control flow) |
| the real native cinematic camera | **already available via the borrowed-donor hybrid** — the Thomas swap itself runs a second `LoadSFX` so our FBX renders *while* the stock donor plays with its forced `FixedCameraEffects` camera | W4 + W-CAM |
| native per-mesh hide / ABR / RGB / texanim | no (the managed `HideMeshes=` key filter is coarse) | yes — ops 11/12/65/147/157/158 |
| PS1-native render look | no (modern shading; 15fps sequence-tick sampling; no battle-actor lighting pass) | yes, by construction |
| **edit a stock summon in place** (fork fidelity) | **no — structurally impossible** | **yes — and only here** |
| provenance exposure | none | build-time-from-own-install only |
| effort remaining | **zero for the creature** | MED → HIGH per rung |

### 3.2 The reframe that decides it

**The managed route's missing piece was never the creature — it was STAGING.** The Thomas swap's whole
unsolved problem was *where to put our model each frame so it reads as "the summon"*: v7 was "in-frame by
construction", v8 a hybrid, and a flight built on the s52 log "made the promo worse."

M1 §6 and M5 §5/§8 just explained why, precisely:

* `SummonData+0x40` — what the probe logs — is the **anchor** the loader hands `Hi_DrawSummonModel`, not the
  drawn transform. The flight lives in the motion clip and only materialises in the composed matrices at
  `*(MATRIX*)(SummonData+0x38)`. The existing log's 261-frame freeze at `(0,−12288,−7168)` is exactly what
  that predicts.
* And `+0x40` is **`R·S`, not `R`** — column norms sweep **0.02 → 3.00** across a real cast. `root_reproject.py:43,75`
  divides by 4096 and calls the result a rotation, silently discarding an authored scale that Bahamut uses to
  fake perspective. That is a concrete, named defect in our own file.

⇒ **A ~20-line probe change (R6) plus a `root_reproject.py` fix is worth more to the actual deliverable than
every write-tier rung combined.** It is LOW effort, provenance-clean, needs no DLL patch, and it closes the
problem that motivated this entire round.

### 3.3 The recommendation

1. **INVEST — TIER R (R1→R6).** This *is* the user's stated goal, it is nearly all packaging, it is
   provenance-clean, and it makes every stock summon's choreography readable. **Start with R6** (it closes the
   live bug), then R1, then R5.
2. **INVEST — the cheap half of TIER W: W0 → W1 → W2 → W3, plus W-CAM.** These make **stock summons editable
   in place** — retimed, recoloured, re-shot — which is the project's own north star (*"recreate the game from
   forks"*) applied to the last opaque island. Total effort is roughly one rung of the overworld work, and
   W3 (reskin) buys visible custom content through the native path for LOW effort.
3. **DEFER — W5 (model-package swap).** It is the only path to a stock-grade *native* creature and it is
   specified well enough to attempt, but it must wait on **R5** (you cannot conform a rig to a program you
   cannot read) and on **W0**. Revisit once R5 lands and the fidelity gap is measured rather than assumed.
4. **DO NOT BUILD — W6 (from-scratch native summon).** It is strictly dominated. It would take a MIPS
   assembler, a full container emitter, a conformant creature *and* an authored camera to reach a place the
   managed route already occupies — while giving up the managed lane's linting, hot-reload, and text-DSL
   authorability. The only thing W6 adds over managed+hybrid is the PS1 render aesthetic, and that is not
   worth a HIGH+ multi-round build.
5. **Kit shape:** author `[[summon]]` against the **managed** lane (the proven one). Expose the native lane as
   a separate read/fork family (`summon-inspect`, `summon-disasm`, `summon-fork`). **Do not conflate them** —
   they have different provenance rules and different failure modes.

---

## 4. THE KNOWN-UNKNOWNS THAT MOST CHEAPLY UNBLOCK THE REST

Ranked by unblock-value ÷ cost. Each is falsifiable and none requires guessing.

| # | unknown | cost | unblocks |
|---|---|---|---|
| **1** | **Does a mod-folder `ef###.bytes` override load?** (§1.3, predicted `<mod>/FF9_Data/SpecialEffects/ef227`) | 2 casts, $0 | **ALL of TIER W.** Nothing else in the write tier is worth starting first. |
| **2** | **The HLE table's PSX base** — read `pluginBase+0x21FF78` (and `0x21FF7C`) once (§1.2) | one probe row | Turns R5 from "control flow" into **named choreography, offline, forever**. |
| **3** | **`SummonData+0x38` bone 0, `DATA+0x78` scale, `rec+0x54` frame** (M1 §10, M5 §9) | ~20 probe lines + 1 cast | **Closes the round's motivating bug.** Also makes the log self-decoding: with the frame counter, the offline clip decode (R3) reproduces every bone without any further probing. |
| **4** | **The live `PsxCtx*`** (M3 §7.2 — `0xd5d0` is called from `0x2300`; not a DLL global I could name statically) | MED | The runtime opcode trace ⇒ empirical ground truth for the ~180 unnamed ops, the exact frame each `HideSummonModelMesh` fires, and the EFFARR-vs-summon question settled in one cast. |
| **5** | **The camera's spherical→matrix step** (W-CAM) | MED, **validation free** against already-logged `VIEW`/`PROJ` | Offline camera authoring + preview; explains the 15 hard cuts and the 47°→24° push-in analytically. |
| **6** | **`geom+0x04`, `geom+0x08`, `MeshDesc+0x00`, `BoneLink.len`** (M4 §7.1–3; the arbiter for the last one is `fn 0x7de7`, only partially read) | LOW–MED | A byte-exact geometry **writer**. Carry-verbatim suffices for a whole-block swap; a *synthesised* block needs these. |
| **7** | **Which resource id carries a geom block, by table lookup** (M4 §7.7 — located by content scan so far) | LOW | Turns "find models by scanning" into "find models by parsing" — a correctness issue for a general tool. |
| **8** | **The `info` byte for ids 0/1/9** (bit-field, gated `@0x3df46`; M2 §9.3) | LOW–MED | Emitting *new* resources (not needed for round-trip). |
| **9** | **A `.pdata`-invisible-leaf sweep for `refkit`** (M1 §12d: `Hi_InitEffModel@0x15940` was invisible to `xrefs_to`/`xref_index`) | LOW | Makes every future "nothing references X" conclusion safe. Instrument hygiene — cheap, and this project has been bitten by uncalibrated instruments before. |

---

## 5. NAMING DISCIPLINE (four different things are called "seq" in this project)

Adopt these names in code and docs or the roadmap will be misread:

| name to use | what it is | who owns it |
|---|---|---|
| **battle sequence DSL** (`.seq`) | the **managed** text language (`BattleActionCode`) that rungs 1–7 author; `LoadSFX`/`PlaySFX`/`CreateVisualEffect`/`EffectPoint`/… | `UnifiedBattleSequencer`; kit `[[summon]]` should target this |
| **loader script** | the native 3-byte `(code,arg1,arg2)` stream at file offset `0x400` inside `ef###.bytes`: `LOAD_CHUNK`, `WAIT`, `SET_CHANNEL_FLAG`, `PLAY_CAMERA`, `PLAY_SOUND`, `0x80+N` = run program N | native `fn 0x315f1`; kit `summon-inspect` |
| **effect program** | the **MIPS R3000A code** in resource id 3 — **THE choreography**: timing, control flow, every `Hi_*` call | native VM `fn 0xe210`; kit `summon-disasm` (R5) |
| **battle-scene attack sequence** (raw17 `btlseq`) | the per-scene attack choreography + opening-camera block | kit `battle/seqcodec.py`, `seqdis.py`, `camera_codec.py` |

Corollary worth stating once: **the loader script is not the choreography.** M2 §10's rung R3 ("sequence
authoring") buys retimed *loads* and re-selected camera/sound sub-files — real, useful, cheap — but the beats
a viewer perceives live in the effect program.

---

## 6. WHAT WOULD FALSIFY THIS ROADMAP

* **W0 fails** (no mod-folder container override) ⇒ TIER W collapses to "read-only + an engine change";
  the managed route becomes the *only* content lane and the recommendation in §3.3 hardens.
* **§1.2's table base turns out to be per-run non-deterministic** ⇒ R5's naming pass becomes a runtime
  step rather than an offline constant (still workable; strictly worse ergonomics).
* **R6's bone-0 reprojection still fails to land on the `PRIM` centroid** ⇒ the remaining suspects are
  already named by M5 §8 Finding D (missing scale in the world→screen mapping; a wrong comparison target;
  bone 0 ≠ silhouette centre for a 93-bone dragon). All three are testable from one instrumented cast.
* **A stock donor's program turns out to hard-code bone/mesh counts** that no reasonable custom creature can
  match ⇒ W5 degrades from "swap the creature" to "reskin the creature" (W3), which is still a real win.

---

## 7. PROVENANCE LEDGER (this slice)

* All native claims come from **read-only** static analysis of the user's own installed
  `FF9SpecialEffectPlugin.dll` (x64 **and** x86): RVAs, mnemonics, struct offsets, table contents,
  control flow. **No DLL was modified or redistributed.**
* §1.1's MIPS confirmation and §1.2's refutation were produced by scanning already-extracted stock
  `ef###.bytes` under `C:/gd/SCRATCH/summon-format/` and emitting **opcode histograms, jump-target ranges and
  counts only** — no payload was echoed, copied, or written anywhere, and nothing was written into the repo.
* §1.3's override path was derived from **open-source** Memoria C# (`AssetManager.cs`, `AssetManagerUtil.cs`,
  `SFX.cs`), cited by `file:line`.
* Standing hard lines, unchanged: **extracted stock creature geometry / animation / textures / raw containers
  — and R5 disassembly listings of stock PS1 code — stay under `C:/gd/SCRATCH/summon-format/`, never committed,
  never shipped.** Parsers, emitters, disassemblers and opcode tables are **code** and are committable.
  **Never produce or ship a patched `FF9SpecialEffectPlugin.dll`.**
* Scratch scripts used for §1.1/§1.2 live in the session scratchpad (not the repo); both are ≤80 lines and
  reproduce from this document.

## 8. REPRODUCTION

```python
# §1.2 -- the 216-entry HLE trap-sentinel table (x64 and x86)
import refkit, struct
pe = refkit.load();  ws = struct.unpack('<216I', refkit.read_rva(pe, 0x68250, 216*4))
assert all(w == (0xFF000000 | i) for i, w in enumerate(ws))
assert struct.unpack('<I', refkit.read_rva(pe, 0x685b0, 4))[0] == 0          # run ends at exactly 216
pe86 = refkit.load('x86'); ws86 = struct.unpack('<216I', refkit.read_rva(pe86, 0x50910, 216*4))
assert all(w == (0xFF000000 | i) for i, w in enumerate(ws86))
list(refkit.disasm(pe, 0x30c20, 0x30d45))    # the registration block: lea/lea/mov/call x5

# §1.1 -- the id-3 payload is MIPS: opcode histogram + intra-chunk J/JAL targets
import ef_container as efc
blob = open(r"C:/gd/SCRATCH/summon-format/ef227.bytes", "rb").read()
c = efc.parse_header(blob)                    # 2 chunks; id-3 payloads at 0x2d000 / 0xc4000
# for each id-3 resource: img = efc.parse_chunk_image(blob, r, 0x801E7700 + (slot & 1) * 0x5000)
# word >> 26 histogram -> {0,35,9,43,41,37,15,33,40,5,18}; (word & 0x3FFFFFF) << 2 | 0x80000000
# lands inside [psx_base, psx_base + 0x5000) for every J/JAL.
```

Sanity assertions that must hold: `ef227` chunk 0 `headerRel == 0x3120` with one program at `0x9d4`;
chunk 1 `headerRel == 0x42bc` with one program at `0x108c`; `ef431` chunk 0 has live programs at indices
**0, 3, 7** and its loader script uses exactly `0x80`, `0x83`, `0x87` (M2 §7.3).
