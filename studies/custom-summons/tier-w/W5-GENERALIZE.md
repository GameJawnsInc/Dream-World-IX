# W5 — THE GENERALISATION (the W tools past ef227)

> **The rung:** make the three cast-proven ef227 levers — W2 reframe, W3 retime, W4 reskin — work on
> ANY stock summon, derivation-first, with named refusals where the proof does not reach, and ef227
> byte-compat pinned in gates. Second proof staged on TWO effects: **Phoenix ef211** (scenery reskin +
> camera rescore) and **Madeen ef251** (creature reskin). Built commit `b3ebdbf8`.
> **Status: ⛳ CLOSED 2026-07-26 — 3/3 levers CAST-PROVEN on second summons: creature (Madeen ef251
> glacial), scenery (Phoenix ef211 GLACIAL v2, after the magenta-probe calibration loop), camera
> (Phoenix H-pull, set edges clean — the SCENERY LAW's modest-pull rule validated). Cast record in
> PLAN.md §Status W5; resting state = combined-v2 live on ef211 + glacial ef251 + ef227 untouched.**

Process: 3 workflows (recon 5 agents / build 5 / verify+Madeen 4), every headline claim adversarially
re-derived from raw bytes by independent parsers (V1: 7/7 confirmed, rho reproduced to 4 dp; V2:
confirmed + 3 real defects found, all fixed; M1 corrected a build-round colour law with measurement).

---

## 1. What each lane became

### Reskin (`reskin.py` — D1–D11, all landed)
- **Slot-based naming** `pal.s{slot}.x{X}_y{Y}.e{entries}` + legacy aliases for ef227's shipped toml
  (aliases suppressed where `chunk_index` is ambiguous — ef381's nine chunks were a hard crash before).
- **Multi-writer + dual-depth CLUT detectors** with build refusals. Corpus truth: multi-writer cells
  exist only in ef381 (19 cells, max 5 writers — per-phase palette streaming into one VRAM cell) and
  ef447; dual-depth only ef447 `(0,242)` (16-entry AND 256-entry readings of one cell — refused
  outright, no acknowledge key). Multi-writer co-transform demands absolute `hue_to` on every writer
  (a shared `hue_rotate` delta lands writers on different hues — that IS the flicker).
- **THE TEXANIM GATE**: `mp.first_block != min(mp.motion_offsets)` ⇒ nonzero texanim region. Exactly
  {ef038: 116 B, ef177/493/494/495: 364 B} corpus-wide. Creature scope refused UNCONDITIONALLY (the
  record is per-creature-part, `SummonData+0x70` stride 0x18); scenery scope only via
  `acknowledge_texanim = true`, whose message states the claim exactly (orthogonality assumed, not
  proven). Side-recon: ef038's own id-3 programs reach NO VRAM-transfer HLE op (op 0/1/166 census) —
  evidence recorded, gate NOT lifted (the 116/364-byte table stays unread).
- **Headroom derivation** replaces the falsified L5: "stock leaves headroom" was an ef227 accident
  (its peaks are ≤28); 46/93 creature CLUT rows corpus-wide peak at 31, including all six of ef211's.
  Per-target `value_ceiling` = 31/peak; zero-headroom + `value > 1.0` refuses.
- **so-record attribution** (magic `0x6F73`) ported from SCRATCH recon into committable code: derived
  `shared` flags; below-100% coverage ⇒ un-attributed palettes are SHARED-UNKNOWN ⇒ `acknowledge_shared`
  required. `0/0` binders reads as NO EVIDENCE, never as 100%. ef227's English names survive only as an
  effect-227 overlay; the derivation reproduces the W4 hand table exactly (15/15, both SHARED rows).
- **`scaffold --ef N`**: emits a complete guarded toml (sha, spans, targets, measured H/S/V + headroom
  as comments, knobs at identity, refusal-stopped rows arriving `enabled = false` with the reason).
  372/372 corpus: 369 scaffold-and-build-clean, 3 refuse honestly (no CLUT palette at all).
- **Creature-optional mode**: the 348 non-creature effects are now scenery-reskinnable.
- Per-effect staging roots (`reskin-w5/ef%03d`); ef227 keeps `reskin-w4/` verbatim (revert-chain compat).

### Camera (`rescore.py`)
- **`init --ef N`** scaffold: shot table, per-shot alternates signatures (computed BEFORE any edit),
  computed `expect_sha256`, dynamic-op disclosure, and a phase-table cross-ref giving each shot a
  reframe-budget verdict (draws-effect-models ⇒ TIGHT — THE EFFECT-OWNED SCENERY LAW as a tool prior).
  `init --ef 227` re-derives W2's hand-authored target exactly (shot A/c0/sub6/seq0/f1, focal H=256).
- **THE DYNAMIC-OP DISCLOSURE GATE**: `PLAY_CAMERA arg2=3` ops resolve through battle-field-keyed
  runtime tables that are NOT in the container — no offline gate can enumerate which blocks they reach.
  Build refuses unless a literal-boolean `acknowledge_dynamic_ops = true`; a stale ack (key present,
  zero dynamic ops) also refuses. **324/372 effects carry at least one — ef227 was the outlier**, which
  is why W2's offline completeness claim was valid there and must not be quoted at ef000-shaped effects.
- Strict unknown-key refusals (a mistyped guard fails OPEN — the one direction a provenance guard may
  never fail); per-effect staging roots (`rescore-w5/ef%03d`); emitted revert scripts rebasable (`--root`).

### Retime (`retime.py` + NEW `retime_derive.py` — option B, the recon's verdict)
- **`report <ef>` / `--corpus`** — the two-clocks table this lane never had: machines, phases, program
  origins, lock pairs with HONEST pairing quality (pairs/beats, NN distance, duplicate-Code collisions;
  verdict `LOOSELY CORRELATED` unless ≥75% pair with zero collisions — it never manufactures "locked").
  Corpus: 12 clean-switch effects, ef125 the only LOCKED; ef227 itself pairs 12/12 but carries one c1
  s3/s4 Code collision nobody had seen. Footer count is END-TO-END (writer identity gated): **45 of 88
  boundaries derivable**.
- **`retime_derive`** auto-locates the threshold `slti` (from `summon_inspect`'s own `guard_off`),
  finds reciprocals by DATAFLOW (no scan window; the shift-0 and out-of-window blind classes both
  closed), resolves every peer `lui` by reaching definitions and **REFUSES any unresolved peer** (THE
  HALF-PATCH TRAP made a refusal instead of a risk — V2's corpus audit: 46 derivations, 53 edit sites,
  0 violations), classifies RETUNE-vs-KEEP by reading the DIVIDEND (`4096*(clock−origin)`-form), and
  self-gates every target on `build_edits(0)` == stock byte-identity. **Headline: it reproduces W3's
  hand-derived ef227 edits byte-for-byte at all 7 sites** — including the delay-slot peer `lui @0x0C04`
  and the shamt rewrite — with none of `w3_program_edits.py`'s pinned offsets. (Caveat, disclosed in
  the module: at N≠0 the replacement magics route through B0's own `pick_reciprocal` when the canonical
  add-back form mismatches the site skeleton; the N=0 identity half is fully independent.)
- `PlayerAudit.needs_retime` ENFORCED (it was a law in a docstring; ef418's outer-outer clock reaches
  tick 130); acknowledge keys must be literal booleans (both lanes, the R3 rule).
- **No new-effect retime artifact ships.** The writer stays gated: ef211:c0 s4 derives end-to-end with
  all four clocks green (beat 178, exact E2 WAIT anchor, E3 pass, E4 anchor — V2 built it offline at
  N=+10/+24 with all endpoints passing), but a cast-grade proof still lacks the per-tick emulator ef227
  had, so casting a generalised retime is a deliberate LATER rung, not an oversight.
- Soundness fix (V2 + V3, independently): the reaching-defs memo was keyed on `id(walk)` without the
  body — a recycled address could serve a stale reach map, i.e. the exact half-patch class the pass
  exists to prevent. Identity-checked now; the whole tier-w suite passes 358/0/1 in ONE process in
  both orders (the per-file gate runners were structurally blind to cross-file contamination — a
  single-process whole-suite run is now part of the record).

### Survey (`w_survey.py`) + gates (`w5_gates.py`)
Per-effect capability matrix (`--summons` / `--corpus` / `--ef N` / `--self-check`): texanim bytes,
creature package + **op-25 drawn check** (the ef447 lesson: a creature package with zero
`Hi_DrawSummonModel` calls is never drawn — Ark-short draws Ark via eff models only), R3 program class,
camera surface (shots/alternates/dynamic count), CLUT hazards, twin-texture groups re-derived from
bytes (`{210,226}` Fenrir⇄Fenrir, `{211,225}` Phoenix⇄Rebirth-Flame, `{431..498}` the six 1-part
specials), and the two DLL frame gates cited as engine facts (Ark `SFX.cs:607-613` f1004/f1193;
Atomos `SFX.cs:1378-1379` f350/f150 — **any W3 retime of those two desyncs an engine constant the
container cannot reach**). `w5_gates.py` = the rung's 9-gate falsifiable runner, 9/9.

---

## 2. The laws this rung minted

- **THE SATURATED-RAMP LAW (+ the TWO-LOBE refinement).** The reskin lever's hue headroom shrinks as
  creature saturation rises — at the extremes it is absolute: Phoenix/Rebirth-Flame (S̄ 0.711, the two
  most saturated) cannot reach ANY cold hue under the frozen rho≥0.90 luminance-ordering gate; their
  passing arc is stock ±25°. But saturation sets the *scale*, not the rank (ef186 S̄0.407 refuses 12
  deltas while ef210/226 S̄0.436 refuse 44). M1's refinement: where a trough exists, it sits on **the
  stock hue's complement** (8 of 9 troughs in 175–205° for warm ramps) with a passing lobe on each
  side — for a fire ramp, cyan/teal AND violet pass, pure blue does not. Methodology guard: a free
  sweep including `saturation = 0` returns a degenerate 360° arc (achromatic ordering can't break) —
  sweep only shippable knobs.
- **THE DYNAMIC-OP DISCLOSURE** (camera): what a table-lookup op reaches is not in the bytes; offline
  completeness claims stop at the first `arg2=3`. ef227 was the exception, not the rule (324/372).
- **THE END-TO-END DERIVABILITY RULE** (retime): an analysis flag is not a writer's promise — a
  boundary is DERIVABLE only if the N=0 identity gate passes (ef381:c4 s4 analyses clean and
  write-collides; 46 − 1 = 45).
- **A SAFETY ACKNOWLEDGE IS A LITERAL BOOLEAN** — `"false"` must refuse, never arm (both lanes).
- **The cache-identity rule**: a memo keyed on `id()` without the keyed content is a soundness bug in
  waiting; and per-file test runners cannot see cross-file contamination — keep one single-process
  whole-suite run in the gate record.

## 3. The second proof — staged artifacts (all offline-gated, previews orchestrator-approved)

| artifact | content | sha256 | changed bytes |
|---|---|---|---|
| ef211 reskin | **GLACIAL FRONTIER** — scenery-only, set key 250° (one row tops out at 240°, stated), `value = 1.00` everywhere, 7 greyscale rows declared-and-inert, 2 warm-locked rows OFF with their frontier measured; creature rows `enabled = false` carrying their measured refusals | `f8051475…` | 2,374 in the two id-0 CLUT rects; creature strip byte-identical (V1-proven) |
| ef211 rescore | H 384→288 (×0.75) at shot A f87 — **the shot's only focal keyframe** (V2-verified; ef227 had 3 more focals, ef211 has none), installs in s1, the one non-drawing phase; persists ticks 86→403 | `7979566f…` | 1 byte @`0x2b114` |
| ef211 combined | exact union, byte-disjointness proven both directions | `1463444b…` | 2,375 |
| ef251 reskin | **GLACIAL MADEEN** — creature-only, shared `hue_rotate = +160°` (the one-hue rule as a DELTA — `hue_to` per-part would fracture the cross-page body material), per-part sat/val, part5 (the face page, peak 31/31) binding at rho 0.9156 / value 0.95; scenery byte-identical to stock (measured, not implied) | `78b395f8…` | 3,054 in the creature CLUT strip |

Bench (`rung8.field.toml`, offline diff-gated 16+24 checks): **Stock Phoenix id 198** (211/211) and
**Stock Madeen id 199** (251/251), both `type = 0` `AllEnemy` mp 8, both on **STEINIV's "Rune"
command (35)** — appending to Vivi's Spark pool would renumber the live Iron Edge 197 (the 192+ band
allocator walks specs in TOML order; a shifted id is a live-state break, a different menu is not).
Existing rows 192–197 byte-identical to the live install; Commands.csv row 35 and learn list 21.csv
append-only. Vivi's Spark menu is untouched.

Twin disclosure: ef225 (Rebirth Flame) shares Phoenix's creature texture byte-for-byte but is a
separate container — it stays stock-fire while ef211's scenery goes glacial (unreachable from the
bench row; disclosed, not a blocker). ef251 has no twin. Madeen's SHORT (ef378) has no creature at
all — structurally unreachable from the bench row (vfx1 == vfx2).

## 4. Deploy + revert (the live actions of this rung)

Deployed (in order, each with its own revert):
1. Bench 30301 redeploy (rows 198/199) — `tools/deploy_field.py rung8-epic/bench/rung8.field.toml --id 30301`.
   **RELAUNCH required** (Actions.csv registration).
2. `py C:\gd\SCRATCH\summon-format\reskin-w5\ef211\artifacts\deploy_w5_ef211.py --variant reskin` —
   hot. Cast B's swap: same script `--variant combined` (reverts cleanly to reskin or out entirely).
3. `py C:\gd\SCRATCH\summon-format\reskin-w5\ef251\artifacts\deploy_w5_ef251.py` — hot.

Reverts: `revert_w5_ef211.py` / `revert_w5_ef251.py` (both `--root`-rebasable, snapshot-once,
delete-vs-restore aware) restore the pre-W5 state: NO ef211/ef251 override (stock plays). ef227's
resting spectral-mist reskin is untouched by this rung. Bench revert = the pre-existing
`revert_deploy_30301.py` chain is STALE (per the pair-lane record) — the bench's own prior deploy is
the baseline; rows 198/199 are additive and harmless to leave.

## 5. CAST — the protocol (three judgments, one relaunch)

Preflight: `[SfxHybrid] Enabled = 0` (verify — the WARM-MIRROR MASK law; it pins EffectId=227, so
even armed it would silently mask NOTHING here, which is the worst kind of wrong), `[SfxProbe]` is
armed and will log (archive to SCRATCH same-session), no `ModFileList.txt` in FF9CustomMap.

1. **RELAUNCH** (registers ability rows 198/199) → New Game → `~` Warp **30301** → encounter.
2. **Cast A — the scenery lever + the bench mint (ef211 reskin is live):** Steiniv → **Rune** →
   **Stock Phoenix**. Expect: the STOCK fire-bird (creature untouched — the gate's refusal is part of
   the proof) over **glacial blue-violet** fire-field/scenery, stock camera. Judge: does the scenery
   read glacial and coherent, does the bird still read right against it?
3. **Cast B — the camera lever:** tell me cast A's verdict; I swap to `--variant combined` (hot,
   `~ → Reload` not even needed — the container is re-read per cast). Recast Stock Phoenix. Expect:
   same glacial set, camera **~33% wider from t≈5.7s onward** (the f87 focal governs the rest of the
   cast — watch for the effect's own set edges per the SCENERY LAW; a modest pull was chosen for
   exactly that reason).
4. **Cast C — the creature lever (ef251 reskin is live):** Steiniv → Rune → **Stock Madeen**.
   Expect: **GLACIAL MADEEN** — frost-white body, teal wing, indigo swirls, amber eye — through the
   stock cinematic. Judge: does the creature read cold and still look modelled (the rho gate's whole
   job) in motion?

Failure table: nothing changed on a cast ⇒ (a) wrong menu (Rune, not Spark), (b) the silent-fallback
law — a wrong override path logs NOTHING (re-run the deploy script, it sha-pins), (c) `[SfxHybrid]`
re-armed. Phoenix looks stock-colour ⇒ that's the CREATURE (correct, refused); judge the fire-field
and sky. Any hang at damage ⇒ archive the probe log first, then revert.

## 6. Residuals / open items (named, not hidden)

- The `0x23 SETUP_CAMERA` install-tick question (does a 0x23-installed camera's visual tick equal its
  own seq_tick?) is UNVERIFIED for the 713/798-block majority — irrelevant to W2-shaped reframes
  (durations refused), prerequisite for any W3-shaped retime of a 0x23 effect. ef211's shot is 0x29.
- The generalised retime WRITER is deliberately uncast: ef211:c0 s4 is the first candidate (all four
  clocks derive), but it gets only the arithmetic endpoint proof — the per-tick emulator does not port.
  E2 on 71/85 boundaries needs a 3-byte WAIT-split insert that has never been cast; `boundary_outer_tick`'s
  cross-clock offset is still unmeasured.
- `madeen_reskin.toml`/`phoenix_*.toml` should join the pinned gate registries once cast-proven
  (w2_gates X7 already auto-discovers the rescore spec, unpinned).
- The texanim table's internal format stays unread (the gate refuses instead); the id-9 slot map's
  slots 4-7 pairing stays [I]-class (preview-only).
- w4_gates' nested w3_gates check now actually runs (timeout 900); the kit's whole-suite collection
  in fresh worktrees still depends on gitignored fixtures (provisioned here; `extract-templates` or
  a fixture copy is the general remedy).
