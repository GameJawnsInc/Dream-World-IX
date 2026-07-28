# TIER W — EDIT A STOCK SUMMON IN PLACE

> **The strategy line this executes** (custom-summons memory): *"the cheap half of TIER W
> (writer/script/reskin + camera, makes stock summons editable in place)"*. TIER R made the cinematics
> **readable**; this tier makes them **editable** — Bahamut rescored, not replaced.

**WHAT TIER R HANDED US** (`../tier-r/`, all three rungs ★):

- **The camera is NOT in the program.** It is played by the SEQUENCE — op `0x29 PLAY_CAMERA` (ef227:
  shots 6/16/47), reading camera sub-files out of the id-2 archive. The effect program cannot reach
  them (id-2/id-5 are never mapped into the id-3 address space). **So a rescore is `.seq` + camera-data
  work, in a layer whose codec we already own** (`ff9mapkit/ff9mapkit/battle/camera_codec.py` — parse /
  serialize / splice / author, shipped for battle cameras).
- **THE TWO-CLOCKS LAW.** Camera cuts land 1–2 frames after program phase boundaries (H → 256 @f58 vs
  phase @f57; → 415 @f153 vs @f152; → 512 @f302 vs @f300). The shots and the phases are **two clocks the
  original author kept aligned by construction.** Change one clock's TIMING and the cut drifts off the
  beat. → this splits the tier's rungs (content vs timing, below).
- **The phase spine is recovered and validated** — `summon-inspect` gives frame→phase→code for ef227 and
  33 other switch-driven effects, with 15/15 capture agreement.
- **One deliberately unsettled question**, R3 §4a: does `op 146` **write** the projection registers or
  only **read** them? (`hle_ops.json`'s `touches` does not distinguish.) Non-gating while READING;
  **gating before the first camera WRITE** — settle it with the named s53 probe row at W2, not before.

---

## The ladder

| Rung | Deliverable | Gate (falsifiable) |
|---|---|---|
| **W1** | **THE READ-OUT** — `summon-camera read <ef>`: which shots the sequence plays, each shot decoded to human terms (keyframes, pose, projection distance, durations), on ONE timeline against R3's program phases | **BYTE-EXACT ROUND-TRIP on every stock summon camera in the corpus** (decode → re-encode == original bytes). **This gate IS the camera recon**: it either proves FORMAT's "same format as the battle camera" claim with an artifact, or names exactly how the summon camera differs |
| **W2** | **THE CONTENT RESCORE** — reframe a real summon's shot (pose / aim / projection distance) with **durations UNCHANGED**, so the two clocks stay aligned and no program byte moves | the op-146 read-vs-write probe row settled FIRST; then a deployed, **cast** proof: the camera looks different, the beats land where they always did, stock data reverts clean |
| **W3** | **THE TIMING RESCORE** — durations change, so the program's phase thresholds must move WITH them (R3 recovered exactly where those constants live) | the retimed cast holds phase↔cut alignment; a deliberate mis-retime is shown to drift (the law demonstrated, not just asserted) |
| **W4** | **THE RESKIN** — retexture a stock creature in place | a cast showing our texture on the stock cinematic, stock bytes untouched |
| **W5** | **THE GENERALISATION** — the W tools take ANY stock summon (scaffold verbs, derivation-first, named refusals: texanim / multi-writer / dual-depth / dynamic-op / half-patch / headroom) | offline: 372/372 corpus sweeps + ef227 byte-compat pinned in gates; in-game: a SECOND summon's cast on each lever — Phoenix ef211 (scenery + camera) and Madeen ef251 (creature) |
| **W6a** | **THE TEXEL REPAINT** — lever #2: rewrite a stock creature page's **indices**, so shape / edge / silhouette become editable at all (a recolour is a colour function and structurally cannot). `summon-reskin export-art` + `[[reskin.texel]]`, indexed lane, creature pages only; every other texel class REFUSES by name (W6b) | offline: the indexed round trip byte-identical **93/93** stock pages, the composed artifact's changed-byte set proven = the CLUT set ∪ the texel set with the two **disjoint**, the three cast-proven CLUT shas unmoved; in-game: a hard-edged brand on ef227's wing membrane that no palette map could produce |
| **W6b-1** | **THE SCENERY TEXEL LANE** — the other 2,572 page-cells: a per-VRAM-cell page map keyed `(writer, x, y)` (the rect key cannot name the lower half of an `h=256` rect at all), the 4bpp nibble pack and the 15bpp direct codec beside the 8bpp one, and four remedies where W6a had four flat refusals — co-transform (name every writer), name-every-column (name every cell a spilling model reads), the display-palette rule, and the program-VRAM DIRECTION law. 93 % of the surface still refuses, BY NAME | offline: 8bpp **and** 4bpp byte-identical on all 2,648 cell-writer records, 15bpp identical over all **65,536** halfwords exhaustively, the nibble order re-proved with a within-row-invariant control (**36/36 with signal**, 8bpp control 93/93), the id-0 rect-table gate proven non-vacuous by a synthetic perturbation, and the kit's program-VRAM lists **re-walked from 385 id-3 images** and compared; in-game: a hard-edged ring with three radial spokes on ef211's full-screen fire field, with the fire bird itself UNCHANGED as the control |
| **W7** | **THE TEXANIM READ** — read the id-5 model image's texture-animation table, the one hazard W5 could only refuse, and replace the refusal with whatever the bytes actually license. New kit module `summons/texanim.py` (a READER; no writer, R2), both lanes' gates rewritten, one new hard rule minted | offline: `encode(parse(region))` byte-identical on every armed region + `parse` never raises across all 372 containers; the §4.1 lift matrix executed on the five REAL packages (build or refuse, each with its stated message class); the co-transform refusal naming the untouched sibling rects; and **THE REGION INVARIANT** — `firstBlock`, `min(motionOffsets)` and every region byte unchanged after a real reskin AND repaint on all five, with the check proven non-vacuous; in-game: ★ THE ONE-FRAME VERDICT — cast Shiva (ef038, the only effect that arms op 12), one captured frame, magenta creature ⇒ the lift is correct |

**Done = "editable in place":** a stock summon can be re-framed, re-timed, and re-skinned from our own
declarative surface, with the stock install revertible at every step. **W6a adds the second reskin
lever**: not only *what colour* a texel is, but *which texel it is* — the first lever in this tier that
can change a silhouette.

---

## Hard rules for this tier

- **Never modify stock game data in place.** Everything ships as mod-folder overrides through the
  existing deploy lanes, with a revert script — the summons deploy engine's `_Ledger` posture.
- **READ rungs touch nothing.** W1 is offline and read-only: no deploy, no install writes.
- **Provenance unchanged** (the FORMAT/TIER-R posture): tools, tests, reports, and *our own* authored
  camera data are committable; **decoded stock camera dumps and listings are SCRATCH-only**
  (`C:\gd\SCRATCH\summon-format\`). Zero SE bytes in the repo.
- **The two-clocks law is a gate, not a note** — any rung that changes timing must show both clocks.

## ★ THE EFFECT-OWNED SCENERY LAW — what W2's cast actually minted (2026-07-25)

> ⚠ **A FIRST READING OF THIS CAST WAS WRONG AND IS RETRACTED.** It called the folding surface the
> *battle background* and concluded the envelope was per-battle-location. **The owner falsified it with
> a one-cast experiment: he cast the same summon in ICE CAVERN and the ground was NOT SNOWY — it was the
> same satellite-view terrain.** The surface is not the arena. Kept visible because the wrong version
> pointed the tier at the wrong ceiling.

**What the cast really showed.** Bahamut's cinematic **ships its own scenery** — an authored ground
plane that travels with the effect and displaces the arena during the aerial beats. (The real battle
background *does* show at other points in the same cutscene; the two alternate.) Widening the entrance
shot revealed that ground's edges and seams, because it is finite geometry modelled to look right from
the shot it was authored for.

**Confirmed in the container, offline:** ef227's chunk 0 carries, beyond `SUMMON_MODEL` (Bahamut
himself, 156 KB), a `MARK_6` (26 KB) and two `MARK_7` (70 KB) geometry resources plus two VRAM texture
pages — the FORMAT round's "32 eff slots = the effect's beams and props." R3's phase table shows the
entrance phase we rescored (`c0` state 0, f57–126) **draws effect models**, and other phases do not.
So: effect-owned geometry, drawn on a schedule we can already read.

> ⚠ **CORRECTION 2026-07-26 (W4 recon, `w4-recon/A2-ATTRIBUTION.md` §8) — the resource attribution above
> is WRONG about `MARK_7`.** Both `MARK_7` payloads (`0x090800` and `0x099800`) open with the ASCII tag
> `AKAO` and contain **zero** `GEOM` blocks; the corpus-wide `GEOM` census (FORMAT §2.3) also lists no
> id-7 blocks anywhere. `MARK_7` is **AKAO audio, not geometry.** The effect's own scenery actually lives
> in **`MARK_6` (6 models: sky gradient shell + cloud sheet + cloud bands A/B, 26 KB) and the two id-2
> sub-file archives** (2 models in chunk 0's archive — the aerial ground plane + the water/ice sheet —
> plus 7 in chunk 1's, including the fire column and the impact/energy rings; 11 textured effect models
> total, per A2 §3.2). **The law itself stands** — the scenery is still effect-owned, self-contained, and
> drawn on the schedule R3's phase table already read — **only the byte-level resource attribution was
> wrong.** Left visible rather than silently fixed, per this tier's own house rule: a wrong reading stays
> on the record so a later reader does not re-cite it. (Note: `W2-RESCORE.md`'s own retracted-finding
> section at the bottom of that report repeats the same `MARK_7`-is-geometry mistake, inherited from this
> paragraph before it was corrected — not re-edited there, since W2-RESCORE.md is a closed, cast-verified
> report and this correction lives at its source.)

**THE LAW:** *a summon's cinematic is a self-contained set — creature, props, AND scenery — authored to
look right from its own camera. Rescoring the camera without regard for that set will show the set's
edges.* The constraint is **per-SUMMON and lives INSIDE the container**, not per-battle-location.

**Why this expands the tier rather than capping it.** The folding surface is not the game's; it is
**ef227's, in a container we can now read, patch, and ship**. The scenery is in scope — the same
override path that carried four camera bytes can carry a re-authored ground. So the ceiling on
"rescore stock summons" is not FF9's arenas at all: it is only that the camera and the effect's own
scenery must be re-authored *together*.

**Practical rules (unchanged in substance, re-derived on the right cause):**
1. **Focal distance (H) is the safest lever** — it reframes without moving the eye, so it exposes less
   of the effect's own set than a pose change does.
2. **Back-and-up is the riskiest direction** — it grows the visible footprint, which is exactly what
   finds the scenery's edge. Lateral/inward stays inside the authored set.
3. **Judge each shot against the phase table** (`summon-inspect`): a phase that draws effect models is a
   phase where the set is on screen and the reframe budget is tight; a phase that draws only the
   creature is far more forgiving.
4. **W4's scope grows:** "reskin" should be read as the effect's whole set — creature *and* scenery.

## Status

- **W1 — ★ DONE** (`W1-READOUT.md`, `summon_camera.py`, `test_summon_camera.py`, `w1_gates.py`;
  5/5 gates). **THE RECON ANSWER: outcome 1 — 798/798 stock summon camera blocks across 372/372
  effects round-trip BYTE-IDENTICAL through the unmodified battle `camera_codec.py`.** The FORMAT
  claim is proven with an artifact. Three corrections fell out (`0x23 SETUP_CAMERA` names 713 of
  the 798 blocks; the id-2 directory sits AFTER the extra-sector region; the Code `frame` word
  carries flags in its top 3 bits), and the two-clocks law is now a number: the authored cut LEADS
  the beat by 1/1/0 ticks and the runtime install lags by a constant 2.
- **W2 — ★ BUILT, awaiting the cast** (`W2-RESCORE.md`, `rescore.py`, `bahamut_rescore.toml`,
  `test_rescore.py`, `w2_gates.py`; 6/6 gates, 34 tests). **ef227 shot A's opening keyframe reframed
  in 4 BYTES of an 823,296-byte container** — yaw, roll and the projection distance, all in place.
  Every duration byte, every frame word, all 83 other sub-files and the whole id-2 directory are
  byte-identical, and the patched container still round-trips byte-exact through the unmodified W1
  path. The op-146 probe row is settled ahead of it (op 146 WRITES `gteOFX`/`gteOFY` but restores
  them before its single `ret`, and only READS `gteH`; 121/122 have no corpus call site) — so no
  effect program sets zoom and a rescore is a sequence/camera-data edit, as W1 assumed. STAGED only,
  under `C:\gd\SCRATCH\summon-format\rescore-w2\`; the cast protocol is `W2-RESCORE.md` §6.
- **W3 — ★★ CAST-PROVEN 2026-07-26 ("worked as described"; both casts + revert run; live install
  verified back at W2's resting state)** (`W3-RETIME.md`, `retime.py`, `w3_program_edits.py`,
  `w3_clock_emu.py`, `bahamut_retime.toml`, `test_retime.py`, `w3_gates.py`; X0-X7 all PASS, 256
  tests, two independent from-bytes re-derivations (V1/V2) could not refute the offline proof).
  `ef227:c0` state 0 stretched 70→118 ticks (N=+48, exactly two loops of the creature's 24-frame
  float clip) and all four clocks it touches moved with it in one build: the effect program (7
  splices, 12 differing bytes — the threshold plus the two magic reciprocals that normalise the
  arrival/progress ramps to the new length), the sequence stream (1 byte, a `WAIT` delta), the
  camera's shot-A frame words (10 writes, 11 bytes, zero duration bytes touched), and the outer
  text `Sequence.seq` clock (1 `Wait:` line) that SFXRework silently substitutes for the binary's
  own sounds/fades/damage cue. A twin MIS-RETIME artifact ships the same three edits with the
  program edit omitted, byte-identical to the ALIGNED build outside those 12 bytes — the offline
  lock table (12 pairs, recovered from stock and re-timed by identity) shows ALIGNED keeping every
  authored camera-vs-phase lead and MIS-RETIME drifting by exactly N on every post-cut `c0` pair
  while all six `c1` pairs stay put, which is the two-clocks law made falsifiable rather than
  asserted. Residual risk is small and disclosed (the light column reads 38% through its ramp
  instead of 65% at the cut, by the locked policy's own design — the one place a discrete-beat
  constraint stops a ramp from being retuned in full); nothing else moves that shouldn't.
  Staged under `C:\gd\SCRATCH\summon-format\retime-w3\`; **the ALIGNED artifact + text co-retime
  are LIVE in FF9CustomMap** (deployed during verification by an errant sandbox harness, then
  byte-verified and adopted — `W3-RETIME.md` §6.1's LIVE-STATE NOTE; snapshot + revert chain
  verified intact). Cast 1 needs no deploy step; `deploy_misretime.py` swaps to the falsifier;
  `revert_summon_retime_227.py` restores W2's resting state. The cast protocol is `W3-RETIME.md`
  §6, and the rung does not close until both casts are judged.
- **W4 — ★★ CAST-PROVEN 2026-07-26 ("all good", after cast 1 minted THE HYBRID MASK law and the
  recast ran with `[SfxHybrid]` disarmed). THE TIER IS COMPLETE — 4/4: re-framed, re-timed,
  re-skinned, all in place, all revertible. Resting: the reskin LIVE, SfxHybrid disarmed.**
  (`W4-RESKIN.md`, `reskin.py`,
  `bahamut_reskin.toml`, `test_reskin.py`, `w4_gates.py`; X0–X6 + 7/7 negative refusals, 38 new tests
  / 294 tier-wide). **THE WHOLE-SET CLUT RECOLOUR of ef227 — creature AND the effect's own scenery,
  lever #1 (CLUT recolour) only, no texel moved.** 4,832 of 823,296 bytes changed (0.587 %, a 2×
  margin under A2's 8,192-byte whole-set ceiling), all inside four header-derived spans, all palette
  data — 0 geometry/UV/program/sequence/camera bytes touched, proven by rebuilding W2's rescore and
  W3's retime from their own specs and intersecting the changed-offset sets (both empty). One hue for
  the creature's six pages (+182°, settled by sweep so the shared hide material does not fracture
  across pages) turns Bahamut spectral-mist-green with cold silver-blue plating; the scenery (sky
  dome, aerial ground, fire column, energy rings) recolours independently into a matching deep-teal /
  ghost-blue key, licensed by A2's proof the creature and scenery share no page, no CLUT, not one VRAM
  halfword. `scenery.cloud_bands` is measured pure greyscale (S=0.00) and reports 0 changed bytes,
  declared ON anyway so the gap is stated rather than hidden. STP population, the 234 transparent
  entries and every `0x0000` cutout held identical stock-vs-patched on all 13 palettes; a B3 finding
  (a channel-clamp counter that could never fire) was fixed into a real HSV blow-out gate, worst
  target 4.7 % against its 10 % refusal ceiling, artifact bit-identical before/after the fix. Lever #2
  (texel repaint) is explicitly DEFERRED — A2's dual-depth VRAM pack and time-shared upload columns are
  named repaint hazards a palette edit is structurally immune to — and the texanim generalisation gate
  (A1: `ef038`/`ef177`/`ef493-495` carry a nonzero texanim region ef227 does not) does not gate this
  rung but must gate any future one past ef227. Staged under `C:\gd\SCRATCH\summon-format\reskin-w4\`
  (13 previews reviewed offline); the cast protocol is `W4-RESKIN.md` §6, and the rung does not close
  until the cast is judged.
- **W5 — ★ BUILT + DEPLOYED, casts pending** (`W5-GENERALIZE.md`, `retime_derive.py`, `w_survey.py`,
  `w5_gates.py`, `phoenix_reskin.toml`/`phoenix_rescore.toml`/`madeen_reskin.toml`; commit
  `b3ebdbf8`; suite 358/0/1 single-process, gates 5/5·8/8·8/8·8/8·9/9; every headline claim
  adversarially re-derived from bytes). The three levers generalise with named refusals: reskin
  refuses texanim (ef038/177/493-495 creature scope, unconditionally), multi-writer-unless-all-named
  (ef381), dual-depth (ef447), zero-headroom blow-outs; camera refuses undisclosed dynamic ops
  (324/372 effects carry one — ef227 was the outlier); retime's writer refuses unresolved peer-lui
  (THE HALF-PATCH TRAP), non-derivable dividends, and anything failing the N=0 stock-identity gate —
  its READER (`report --corpus`: lock tables + pairing quality + per-boundary derivability, 45/88)
  ships; its writer deliberately stays uncast. NEW LAWS: THE SATURATED-RAMP / TWO-LOBE LAW (hue
  headroom shrinks with creature saturation; the refusal trough sits on the stock hue's complement —
  Phoenix/Rebirth-Flame alone can reach NO cold hue, so ef211 ships GLACIAL FRONTIER scenery-only and
  **Madeen ef251 carries the creature-lever proof**, GLACIAL MADEEN +160°, rho 0.9156). Bench rows
  Stock Phoenix **198** / Stock Madeen **199** on STEINIV's Rune menu (Spark would renumber the live
  Iron Edge 197). Cast protocol = `W5-GENERALIZE.md` §5 (one relaunch, three judgments); the rung
  does not close until the casts are judged.
  **CAST RESULTS so far (2026-07-26): Madeen ★ PROVEN ("madeen looked glacial") — the CREATURE
  lever generalises in-game, second witness after ef227. Phoenix cast A read STOCK — the scenery
  recolor did not visibly land, the first-ever cast of a PURE id-0-palette recolor (W4's ef227 cast
  bundled creature+scenery, so the scenery half was never proven in isolation and is now also in
  question). Offline discriminators run: the 5 so-bound cells were exactly the recolored ones; ef211's
  program does NO VRAM re-upload (one StoreImage = a read; 0 LoadImage/MoveImage; ef227/ef251 have
  none); one bound model has neutral (128,128,128) prim colors. THE MAGENTA PROBE is LIVE on ef211
  (sha f625ea32…, all 315 live entries of the five bound palettes → pure magenta, STP/cutouts
  preserved; `reskin-w5/ef211/probe-magenta/`): any magenta in the next Stock Phoenix cast ⇒ upload
  path works, the glacial key was perceptually swamped (prim modulation — L17 was only ever proven
  for the CREATURE path); still stock ⇒ the id-0 scenery-palette path is DEAD at runtime — a
  structural finding that re-opens W4's scenery attribution. Cast B (camera) deliberately held
  until this resolves.**
  **PROBE VERDICT ("magenta showed up in the flames") — THE UPLOAD PATH IS LIVE.** The id-0
  scenery-palette path works at runtime (W4's ef227 scenery mechanism re-grounded); cast A's miss
  was COMPOSITIONAL — the v1 key was blue-leaning AND desaturated (×0.85) into additive compositing
  where stock flame cores wash to white. **THE ADDITIVE-COMPOSITING COROLLARY: for VFX textures the
  in-game read keeps the channel the blend favours — pick hues that keep R on warm effects, and
  never LOWER saturation on an already-max-sat ramp (v2's ×1.25 attempt clipped 100% of entries and
  the blow-out gate refused — stock fire IS max-sat; the lawful punch is hue at sat 1.0).**
  GLACIAL v2 deployed (hue_to 280, saturation 1.00 on the two vivid bound cells; container sha
  4daab8ad…); combined-v2 (reskin+rescore, 17b6dcb6…) staged for cast B.
  **v2 RECAST ★ PROVEN ("stock phoenix has magenta/violet") — THE SCENERY LEVER IS CAST-PROVEN on
  a second summon.** Two of three levers now have their second witness (creature = Madeen, scenery
  = Phoenix v2); the calibrated key reads exactly as designed (violet with magenta-hot cores).
  Combined-v2 (17b6dcb6…) swapped live for CAST B — the camera lever, the last judgment: same
  violet, H 384→288 from f87 (~33% wider from ~t 5.7 s through the rest of the cast).
  **CAST B ★ PROVEN ("the pull back works, set edges look fine - no custom fit viewport stuff this
  time") — ⛳ W5 IS CLOSED, 3/3 levers cast-proven on SECOND summons: creature (Madeen ef251),
  scenery (Phoenix ef211 v2), camera (Phoenix H-pull). The W2 failure mode (the widened ef227
  frame exposing the effect's own set edges) did NOT recur — the SCENERY LAW's modest-pull +
  phase-budget rules held on a persistent 33% widening, which is the law validated as a design
  rule, not just a post-mortem. RESTING STATE: combined-v2 (17b6dcb6…) LIVE on ef211 (violet
  scenery + wide camera, owner-approved as cast), GLACIAL MADEEN (78b395f8…) LIVE on ef251,
  ef227's spectral-mist untouched; reverts in reskin-w5/ef{211,251}/artifacts/ (delete-vs-restore
  aware; the artifacts' v1-pinned deploy variants are superseded by the *-v2 files + the committed
  tomls, which regenerate v2).**
  ⚠ **THAT RESTING STATE NO LONGER EXISTS ON THE INSTALL** — see `W6-TEXEL.md` §7:
  `FF9CustomMap/FF9_Data/` was wholesale-replaced by another concurrent session on 2026-07-27 08:55
  and now holds only `embeddedasset/text`, so the ef211 / ef227 / ef251 overrides are all gone. The
  staged artifacts and their revert kits are intact under SCRATCH; only the live folder was wiped.
- **W6a — ★★ CAST-PROVEN (posture (b); the brand read hard-edged on both wings in the spectral
  key, owner-confirmed; cast record → `W6-TEXEL.md` §7)** (`W6-TEXEL.md`,
  `ff9mapkit/ff9mapkit/summons/repaint.py`, `ff9mapkit/tests/test_summon_repaint.py`,
  `bahamut_emblem.toml`, `emblem_stamp.py`, `w6_gates.py`; gates 7/7, kit summon tests 250, tier-w
  suite 358/1 single-process, w4_gates 8/8, w5_gates 9/9). **LEVER #2: THE TEXEL REPAINT.** `summon-reskin` grows
  `export-art` (every creature page → a P-mode indexed PNG + a UV `<name>.coverage.png` overlay +
  `art.manifest.json` + a pre-seeded-OFF scaffold, under the local-only guard) and `[[reskin.texel]]`
  alongside `[[reskin.target]]` in ONE spec — two levers, one container, one ledger, one revert.
  **THE FORMAT OF RECORD IS AN INDEXED PNG**: `decode → P-mode PNG (palette = the CLUT row, tRNS =
  the transparent entry) → reload → indices` is byte-identical **93/93** stock creature pages, while
  an identity **RGBA** round trip already moves 1,844 of 16,384 texels on ef251 part 0 (8.31 % of the
  corpus's palette entries are duplicates of the full 16-bit word) — so the RGBA / quantize /
  mint-CLUT lanes REFUSE by name carrying that measurement rather than half-working. **THE PROOF
  ARTIFACT**: W4's spectral-mist recolour rebuilt (`7fef205f…`, 4,832 CLUT bytes) with a procedurally
  stamped **emblem** composed on top — a stroked ring + three radial bars on ef227 part 0's wing
  membrane, ink idx 255 / edge idx 1 (both already-live entries ⇒ **0 CLUT bytes**), r = 26 at the
  sampled-island centroid (63.8, 59.8), 1,037 texels stamped / **1,032 bytes moved**, **0 dead-pad
  bytes, 0 cutout flips** — composed sha **`813a7ea4…`**, verified INDEPENDENTLY of the kit's own
  self-report (changed-vs-stock = the CLUT set ∪ the emblem set, the two DISJOINT, all 817,432 other
  bytes identical to stock). The art is SCRATCH-only Square-Enix content, so what ships is the
  GENERATOR (`emblem_stamp.py`, every parameter re-derived from the user's own container); the
  byte-literal scan over all five new committable files finds 1 literal, an ASCII fixture word,
  appearing in 0 of 372 corpus containers. **NEW / CORRECTED LAWS**: CO-TRANSFORM == MULTI-CHUNK (34
  multi-writer page cells in exactly the 5 multi-chunk containers; **0 of 156 writer pairs
  byte-identical** — there is no "repaint once, copy twice" case anywhere in the corpus);
  SAME-BYTES-TWO-BINDINGS supersedes "dual-depth" as the general gate (ef211 col 640 shares 1,659
  halfwords between two **4bpp** bindings with different palettes — a depth-only test misses it); THE
  U-SPILL LAW (41/316 so-bound models sample past their own column, sometimes into another resource,
  so a template must be keyed on the MODEL); **A2's "100 % of its own page block" was a BBOX claim —
  polygon coverage is 64.00 %** (975,202 / 1,523,712), so ~1/3 of every summon's texture budget is
  never sampled by any face; and **THE MARGIN LAW is CORRECTED DOWN** — R2's ">99.6 %" held on its
  two-effect sample (ef227 99.68 %, ef211 99.91 %) but this rung's 93-page sweep measures **98.767 %**
  (worst effect ef381 95.65 %, worst page ef261 part 1 87.06 %), which is exactly why the overlay
  hatches outer pad green and interior hole red. `reskin.py` gains exactly ONE load-bearing seam —
  `_regions(partition="clut"|"texel")`, proven to partition the id-4 resource with no overlap and no
  gap — and all three cast-proven CLUT artifacts still build their exact shas (ef227 `7fef205f…`,
  ef211 `4daab8ad…`, ef251 `78b395f8…`). **W6b DEFERRED with reasons**: the scenery texel lane
  (co-transform / same-bytes-two-bindings / u-spill / 15bpp), the RGBA + mint-CLUT lanes, and the
  program-VRAM refusal list. Staged under `C:\gd\SCRATCH\summon-format\repaint-w6\ef227\`; the cast
  protocol is `W6-TEXEL.md` §6 (`[SfxHybrid]` disarmed preflight, bench 30301 row 196 → Iviv → Spark
  → Stock Bahamut, hot — a PAGE upload is itself the cache-invalidating event, so no `~` reload and
  no relaunch), with §7 naming the two honest cast postures now that the live baseline was wiped, and
  the rung does not close until the cast is judged.
- **W7 — ★★ CAST-PROVEN, both verdicts (magenta Shiva on screen; her eye never changes — nothing
  blits, the fourth independent confirmation; cast record → `W7-TEXANIM.md` §6)** (`W7-TEXANIM.md`,
  `ff9mapkit/ff9mapkit/summons/texanim.py`, `ff9mapkit/tests/test_summon_texanim.py`, `w7_gates.py`;
  w7_gates 5/5, w5_gates 9/9, w6_gates 7/7, tier-w suite 360/1 single-process, the three kit summon
  reskin/repaint/texanim test files 195).
  **THE TEXANIM READ — the rung that turned a refusal into a lift.** W5 minted a gate whose own words
  were *"this is not a knob: read the table first"*; W7 read it, from three parallel recon lanes (a
  static disassembly of the user's own `FF9SpecialEffectPlugin.dll` in x64 AND x86, a measurement
  sweep over the 372-container corpus, and a `file:line` census of this repo). **THE FORMAT**: `u32
  clipCount` + one 20-byte CLIP record per clip + one 12-byte destination WINDOW per clip + packed
  4-byte frame lists — three sub-arrays that tile the region EXACTLY, which is why the only two sizes
  corpus-wide are `4+60+36+16 = 116` (ef038, 3 clips) and `4+180+108+72 = 364` (the ef177 family, 9
  clips), and why neither ever divided by `partCount * 0x18` (`0x18` is the **x64 runtime** row —
  `nodeOff` widens to a pointer — the FILE record is `0x14`, and the count counts **clips**, not
  parts). **WHAT IT DESCRIBES**: a texel BLIT — a `w×h` rect of 8-bit palette INDICES copied inside
  ONE creature part's own 128×128 page. It binds no CLUT word (no `u16` in any of the five tables is a
  TPAGE or CLUT word), writes no CLUT contents (the rects cannot reach a 3–5-row strip), and touches
  no UV (0 UV entries inside every frame rect on 39/39 clips, vs 16–272 inside every window rect).
  **AND NOTHING RUNS IT**: by exhaustion over both builds, the only code that dereferences
  `SummonData+0x70` is `Hi_Start/StopSummonTexAnim`, which write three state fields and return — no
  ticker, no draw-path read, no VRAM write; op 11 is never called by any of the 372 containers and op
  12 by exactly two sites in one effect. **THE FALSIFIABLE COROLLARY**: Shiva's eyes never close
  during her cast on the PC port, and Carbuncle's nine eye/mouth clips are dormant content the
  shipping game never plays. **THE LIFT**: creature recolour, scenery recolour and whole-page texel
  repaint all build with NO key on all five armed packages; a LOCALISED texel repaint builds once the
  protected rect set is co-transformed and otherwise refuses **naming the clip and the exact rects
  left stock** (`acknowledge_texanim_frames = true` is the escape hatch for a deliberately asymmetric
  strip); `acknowledge_texanim` becomes a deprecated no-op and the scaffold stops emitting it; and
  every readout now prints the DECODED table instead of "TEXANIM ARMED (N bytes)" — the opaque line
  that made the old refusal unanswerable. **THE LIFT IS CONDITIONAL ON A SUCCESSFUL PARSE**, never on
  the absence of an exception, so an unknown future shape degrades to the pre-W7 refusal verbatim.
  **★ THE ONE NEW HARD RULE — THE REGION INVARIANT (R1)**: never resize, relocate or zero
  `[firstBlock, min(motionOffsets))` and never edit `firstBlock` — `firstBlock == motionOffsets[0]` is
  a LIVE engine predicate that `cmove`s `Hi_RegisterSummonModel`'s second argument and so changes what
  `summonRecord+0x20..0x51` holds; enforced at BOTH lanes' build call sites
  (`reskin.assert_region_invariant`), proven non-vacuous by tampering. **STILL REFUSED**: authoring
  the table itself (W7 ships a READER — there is no consumer, so no edit could be verified, and on
  x64 the arming op already writes PAST the record it means to arm and corrupts it). Gate pins moved
  in lockstep: `w5_gates` G3 `THE FIVE TEXANIM REFUSALS` → **G3′ THE FIVE TEXANIM LIFTS**,
  `w6_gates` G4's texanim row → **the L3/L4 matrix**; the W5 corpus sweep, `w4_gates` X7 and
  `w_survey.self_check` KEPT UNCHANGED. **The cast**: ef038 = Shiva, the maximal-risk member of the
  class, magenta/violet creature recolour shipped WITH a frame-strip marker in one build — verdict 1
  is ONE captured frame (magenta ⇒ the lift is correct), verdict 2 needs video (does the eye window
  ever show the marker? ⇒ whether L4's co-transform is mandatory or merely prudential). The bench row
  is an `Actions.csv`/BattlePatch change ⇒ RELAUNCH. The rung does not close until the cast is judged.
- **W6b-1 — ⛳ CAST LADDER CLOSED (7 owner casts, 2026-07-28; the full record is `W6b-SCENERY.md`'s
  cast block). In-game proven: the scenery byte→screen chain (the striped cell census banded the
  fire owner-visibly; the kit-built bold wheel measured +11.6pp near-black at burst-peak-aligned
  cast-time), THE PER-CELL MAP (the confirmed vortex cell is an h=256 LOWER half) and the 4bpp
  nibble codec (casts 2/2b were 4bpp kit builds). Two laws minted in-game: BINDING-IS-NOT-A-DRAW
  (the wheel on (704,256) was invisible twice — an `so` reader is not a draw; the dome actually
  reads the READERLESS (704,384)) and THE UV-SHREDDING BOUND (sheared mirrored panel UVs turn
  figures into diffuse erosion; stripes read because translation-invariant). Cast 1e: the pool =
  (640,256) by elimination (cell-5 stripes left it clean; they DID band the intro background
  flames, so (576,256) is drawn). OPEN: the pool's positive confirm + the photographable shape
  verdict (one cast on (640,256) can carry both if its UVs are flat), the 15bpp cast.**
  `ff9mapkit/ff9mapkit/summons/{repaint,reskin,texture}.py`,
  `ff9mapkit/tests/test_summon_{repaint,reskin}.py`; w6b_gates 7/7, w6_gates 7/7, w7_gates 5/5,
  w5_gates 9/9, tier-w suite 360/1 single-process, the four kit summon test files 382).
  **THE SCENERY TEXEL LANE — the other 2,572 page-cells, and an honestly asymmetric rung: the codec
  never fails and the gate refuses 93 % of the surface.** The wall is not the format, it is
  ATTRIBUTION: **2,385 of 2,572 scenery cells (92.7 %) declare no `so` reader**, so their bit depth is
  not a fact the container states, and the coherence probe built to guess it was **FALSIFIED at 54.5 %
  on a 3-way choice** — refused outright, not even shipped as a disclosure. **THE ADDRESSABLE UNIT IS
  THE VRAM PAGE-CELL** (`reskin.page_cells`, keyed `(writer tag, x, y)`): 1,214 of 1,317 stock page
  rects are `h=256` and cover TWO stacked cells, so the old `(tag, x)` rect key could not name **1,179
  cells** at all — on ef211 column 576 the top half is a two-palette refusal and the bottom half is
  clean 4bpp, and only the hazardous half had a name. **LAWFUL 56 = 50 page-scope-safe + 6
  model-scope** (a spilling reader hands the author half a picture: 58/58 spilling pictures are wider
  than a page, **0/58** spill by ≤ 2 %), **+ 20 class-B2 lower halves the map unlocks = 76**. **THREE
  CODECS, ONE DISPATCH ON THE DERIVED DEPTH**: 8bpp and 4bpp byte-identical on **2,648/2,648**
  cell-writer records (the 4bpp PNG carries one byte per texel 0..15, never Pillow's `bits=4`, so no
  PNG bit-order convention can reach the container), and 15bpp direct as **RGBA + an explicit STP
  sidecar** — identical over all **65,536** halfwords exhaustively, by SHIFT rather than
  `bgr555_rgba`'s scale, which is lossless only under a rounding inverse and fails 30 of 32 channels
  under a flooring one (*a rounding rule is a place for the no-op to stop being a no-op*). **★ THE
  NIBBLE ORDER HAD NO SURVIVING PROOF** — W6a's "empirically confirmed" left no artifact, so it was
  re-proved at corpus scale with a within-row-invariant vertical control, calibrated first on the
  cast-proven 8bpp answer (**93/93 unanimous**) and then answering the 4bpp question **44/48, and
  36/36 above a signal floor with no dissent**. **FOUR REFUSALS BECAME REMEDIES**: co-transform (name
  every writer, art for each, `acknowledge_cotransform` a literal boolean — **16 of 34 expressible**,
  and NO "same art for all writers" shorthand, because 0 of 156 corpus writer pairs is byte-identical);
  NAME-EVERY-COLUMN for spilling models on the **UV-exact 70**, not a rect-conservative superset;
  the class-C display-palette rule (**25 cells**: editable in the lowest-addressed binding's key,
  every other key a NAMED read-only alternate view of the same index bytes) and the class-E3
  shared-read disclosure (**93 cells / 38 effects**). **★ THE DIRECTION LAW is what makes a cast
  possible**: `LoadImage`/`MoveImage` are WRITES but **`StoreImage` is a READ**, so **113 cells over 12
  containers move from REFUSE to DISCLOSE** — and ef435 comes OFF the write list as a false positive
  (a switch dispatch through the image's own pointer table read as HLE op 0), six containers go ON as
  READ-only, and the old 15-vs-22 count flag is settled arithmetically (both were right about
  different sets; the corrected 15 is a DIFFERENT 15). **★ THE ONE REAL GATE GAP CLOSED**: `_regions`
  never listed the id-0 resource under either partition, so a scenery splice would have run with the
  page-block header and rect table UNGATED — `pixelDataRel` now inverts a second split, with
  `assert_page_cells_identical` RE-DERIVING the map beside it, and `w6b_gates` G3 proves the fail-safe
  catches a synthetically perturbed rect table. **THE CAST VEHICLE IS ef211 `(704,256)`, the Phoenix
  fire field** — single writer, single reader, zero hazards, 8,128 of 8,192 halfwords live art, and
  the ONLY candidate whose upload path is already cast-proven live (W5's magenta probe: *"magenta
  showed up in the flames"*). Bench 30301 row 198 already exists ⇒ **no relaunch, no `~` reload, no
  `Actions.csv` edit**, and cast 2 (the 4bpp lower half `(576,384)`) is the same container, row and
  deploy script. Staged posture only — nothing deployed. The rung does not close until the cast is
  judged; the ladder and the verdict statement are `W6b-SCENERY.md` §5.
