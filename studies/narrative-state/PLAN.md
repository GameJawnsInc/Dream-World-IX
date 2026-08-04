# The Narrative-State Engine — arc plan

> **Goal:** derive, from FF9's own event scripts, the coherent story-state at any beat —
> ScenarioCounter + the `gEventGlobal` flag constellation + party roster — and surface it as tooling
> (`story-seed` / `story-model`) so a forked field, campaign, or New Game boots *mid-story* instead of
> at scenario-zero. This is the direct successor to the eb-roundtrip arc: the byte-exact decompiled
> corpus (9753 binaries, annotated `.ebs`) is the instrument this arc's census runs on.
>
> **Scoped by the 4-lane recon of 2026-08-03** (tooling inventory · research data assets · Opus design
> sketch with a measured 818-field probe · real-save corpus decode). Measured numbers below are from
> that probe (`scratchpad/sc_probe.py`, re-runnable in ~3 min from `ff9mapkit/`).

## Non-goals (say them now, not at rung 6)

- **Non-heap character state** — levels, equipment, learned abilities, gil live in the save's character
  structures, not `gEventGlobal`. `save-edit` owns them; the model emits membership + heap only.
- **ATE seen-state / ATE80 trophy** — `AchievementState.AteCheck`, not the heap, and id-gated
  (`docs/ATE_SYSTEM.md`). Documented limit, not a rung.
- **The semantic lift** of `.ebs` into `field.toml` vocabulary — still the deferred sibling arc.
- **Inventing story order the scripts don't attest.** Author game-knowledge overrides every derived
  value (an override table that always wins); the model makes the answer *discoverable*, the author
  still asserts the beat.

## What already exists (do not rebuild)

| capability | where |
|---|---|
| flag registry, reserved bands, safe-band constants, 52-anchor SC→beat table | `flags.py` |
| decode/diff/edit a REAL save's `gEventGlobal` (incl. the Memoria extra file + AES codec) | `flags.py`, `save.py`, `flags-inspect`/`flags-diff`/`save-edit` |
| `[startup]` scenario/flags/words/byte_writes compiler; `[party] add`; gateway `set_scenario` | `content/startup.py`, `content/party.py`, `content/gateway.py` |
| single-field scanners: flags set/required, party ops, story-writes (noise-filtered), SC gates, roster-by-beat symbolic walk | `eventscan.py`, `forkreport.py` |
| per-bit evidence corpus: writers, readers, dialogue, gate bodies, coarse `beats:` (43% of 937 bits) | `research/FLAG_LORE.md` + regenerable JSONs (gitignored) |

**The verified gap:** nothing composes these. No tool answers "the CUMULATIVE state at SC=N", nothing
walks fields in story order, nothing classifies mainline-vs-optional, nothing auto-writes a
`[startup]` block, and no synthetic-blob generator exists. `scan_story_writes`' own docstring frames
today's workflow as one-hop manual.

## The scoping finding that shapes the ladder

**The demand side is tiny.** Per the 818-field probe: the median field references **1** GLOB story
bit; 315/818 reference none; 702/818 reference ≤5. What most fields need to behave at beat N is the
**ScenarioCounter** (568/818 read it) plus, for ATE hubs, an availability **word** — not a thousand
bits. So the arc has two deliverables that must not be conflated:

1. **The demand-driven seed** (small surface, shippable early): for a fork of field F at beat N,
   resolve *only the bits F actually reads* and emit `[startup]`. ~1–12 bits per fork.
2. **The full beat model** (large surface): synthesize the entire heap — needed for multi-field
   campaigns, New Game at beat N, and the north star.

Rungs 0–2 ship the demand-driven seed and are simultaneously the cheapest falsification of the full
model's premise. **Decision gate after rung 2:** if demand-driven seeding satisfies playtests broadly,
rungs 3–6 shrink to a convenience and the arc jumps to party/campaign (7–8). That outcome would be the
scoping working, not failing.

Other load-bearing measurements:
- Naive byte-adjacency SC-window attribution covers only **32.6%** of the 12322 bit-write sites
  (the same ceiling `gen_flag_lore.py` admits). The step change is real **dominance analysis** over
  the `.ebs` CFG — rung 0's falsifiable prediction is that dominance lifts coverage past ~55%.
- **94 bits are explicitly cleared** somewhere (85 genuine set-then-clear toggles, e.g. the Desert
  Palace sanctum-cast band 3536–3542, Cleyra 3882/3883) — a monotone "latch" model is wrong for them;
  they need windows `[on, off)`.
- **412 of 1110 written bits sit in Treasure-Hunter-scored bytes** — TH membership is a *cost* signal
  (seeding inflates the player's rank), not a class signal. ΔTH-points joins the metric permanently.
- **889 absolute SC writes vs 2 relative** — the counter is near-pure absolute assignment, good for
  order inference. (Reconcile vs the old census's "7 fields with ++/--" before trusting either count.)
- 706/1110 bits single-writer; 271 real multi-writer bits need the disjoint-vs-overlapping-writers
  probe before `min()` is trusted.

## Calibration corpus (decoded 2026-08-03, read-only)

19 populated save states, zero decode errors: a dense band SC 2540–3110 (Ice Cavern→Lindblum, 5
points), one isolated SC 6000 (Fossil Roo — exists ONLY in the encrypted container, no Memoria extra),
and a 6-save pile-up at SC 7200 (Alexandria Castle). **Nothing after 7200 — discs 3–4 have zero ground
truth.** Consequences:
- Early-game validation (rungs 1–5) diffs against real saves; late-game validation leans on the
  offline self-consistency checks + owner playtests until later-game saves exist.
- Ask the owner whether they can supply (or play toward) any disc-3/4 saves; otherwise the plan
  accepts playtest-only validation for the back half.
- ⚠ Several 7200 saves carry CoopPeer* words and the directory shows prior tool-session `.bak`s — the
  corpus is not purely organic. Exclude the coop cells (already reserved) and treat 7200-save oddities
  with suspicion before blaming the model.

## The rung ladder

Each rung lands independently with its own falsifier. ★ = owner playtest.

| # | rung | exit test / falsifier |
|---|---|---|
| **0** | **Dominance instrument.** Bulk-decompile the corpus locally (never committed — provenance), build a CFG+dominator pass over `.ebs` labels; emit per bit-write site `{bit, value, field, entry, func, dominating SC conds, dominating flag conds, sibling ops}`. Pure derivation, regenerable, deterministic. | The stated prediction: SC-window coverage rises 32.6% → >55% of write sites. If not, E1/E2 aren't the primary estimators — re-plan here, cheaply. |
| **1** | **Demand-driven seed.** `ff9mapkit story-seed <field> --beat <N|name>` → the `[startup]` block for only the bits the field READS, per-bit provenance, an explicit "unknown → defaulting clear" list. Hard refusal: every emitted bit passes `not is_reserved()` and `named_word_at() is None`. | ★ 2–3 verbatim forks of story-gated donors across discs boot in the right state. |
| **2** | **Word-var beat table.** Curated named-word seeds (ATE avail words, Navi masks, transport, trance/Garnet), emitted as `byte_writes` by default (the UInt16-neighbour trap). | ★ Reproduce the *known-good* result: verbatim Lindblum 552 @ scenario 3115 + byte 236=0x0F boots the real Small-Town Knight ATE. Calibrates the instrument against a proven answer. |
| — | **DECISION GATE** — review rung-1/2 playtests with the owner; scope rungs 3–6 accordingly. | |
| **3** | **Classifier.** The signal cascade (reserved → transient → shared-block → cleared-toggle → reward-adjacency → TH-cost-tag → engine-reader → SC-co-location → lore-curation → unknown) over the whole corpus → `{bit → class, deciding_signal, evidence}`, generated + human-override file. | 60-bit stratified hand-label probe agrees ≥80%; FP on reserved/transient = 0 by construction. |
| **4** | **Order intervals.** Estimators E1–E5 (equality gate / window gate / co-located SC advance / writer-field envelope / milestone fallback) + reader-side tightening as an interval-constraint solve; `[lo,hi]` per M-bit, `[on,off)` per W-bit. | Zero unexplained empty intervals; the three self-consistency checks (empty intervals, gate-contradiction sweep, reachability) clean. |
| **5** | **Calibration harness.** `story-model --beat N --diff-save <save>` reusing `diff_reports`/`render_diff`; per-class FP/FN + ΔSC + ΔTH + Δmognet. | The metric can FAIL: corrupt one mainline bit deliberately, harness reports FP(M)=1. Then: FP(R/T/M)=0 on every real save; FN(M) target set AFTER the first measurement, not before. |
| **6** | **Full beat model.** `model(N)` → a complete heap blob; `save-edit --beat N` seeds a real save. | Metric green on the calibration set. ★ Load a synthesized mid-game save, walk the real game — owner verdict. |
| **7** | **Party-by-beat.** Roster fold over party ops in order() sequence + the `SetPartyReserve` operand census the source corpus newly enables + `field_resets_party` interlock; `[party]` emission. | `B_PARTYCHK` consistency: no field at beat N requires a character the model says absent. ★ Playtest a split-party beat. |
| **8** | **Campaign entry at beat N.** Wire into campaign/journey entry + New Game; closes the standing `[initial_flags]` TODO. | ★ New Game → a multi-field campaign opening mid-story, coherent. The north-star demo. |
| **9** | **Corpus widening + docs.** World binaries (the 13 dispatchers were never censused — disc/world resets live there), the `jp` cross-check (bytecode differs for 71% of fields), FORK_FIDELITY.md update, memory entry. | jp-vs-us derived-table diff empty or every divergence explained. |

## Risks (ranked; each has a cheap probe — full detail in the recon transcript)

1. **Framing oversized** — the demand-driven seed may be enough (that's rung 1 + the gate).
2. **Class errors move the metric's own denominator** — the 60-bit hand-label probe.
3. **Cleared-mid-story bits** break monotone latching — the 91-bit window extraction probe.
4. **Multi-writer bits**: `min()` invalid when writers are alternative story paths — disjointness probe.
5. **SC reuse / non-monotone segments** — dump every SC write site, look for descents; reconcile the
   889-vs-7-fields count discrepancy while there.
6. **UInt16 seeding clobbers the neighbour byte** — `byte_writes` default + a unit test on every table row.
7. **World-state resets unmeasured** — rung 9's world-binary sweep.
8. **TH rank inflation** — ΔTH in the metric from rung 5 on.
9. **The heap isn't the whole state** (ATE seen, party structs, inventory) — non-goals + `save-edit`.
10. **Language divergence** — rung 9's jp regeneration diff.
11. **Byte-var aliasing** (the 8512 lesson) — the rung-1 hard refusal, enforced at the emitter.

## Infrastructure & process notes

- **Decompiled corpus location:** regenerate locally (e.g. a gitignored scratch/reference dir); `.ebs`
  files are derived from Square-Enix bytes and are NEVER committed (provenance gate).
- **Generated tables ship like `SCENARIO_MILESTONES`:** a generator under `research/`, a curated
  frozen table in the package, and a test that regeneration reproduces it.
- **Playtests decide; the metric is a regression harness, not an oracle** (the Path-D 0/13 lesson).
- **Deploy hygiene:** scratch ids from the 30000-band, always `--id`, worktree `.ff9deploy.toml` pins
  `mod_folder` only.

## Status

- **Rung 0: DONE — instrument built, prediction FALSIFIED, re-plan recorded (2026-08-03).**
  - Built: `eb/cfg.py` — `FuncFlow` (basic blocks, dominators, sound guard attribution:
    if/else polarity, switch-case `==`/`in`, compound-AND atoms, join points kill claims,
    loop-exit negation, dead code = no claim, malformed = loud `CfgError`) + `FieldFlow`
    (arm/call-graph context propagation via `eventscan.armed_slot` + `resolve_uid`; per-cond
    `armed` flag: held-at-arming vs held-at-invocation; available-expressions fixpoint,
    all-in-edges-known before claiming). 27 tests in `tests/test_ebcfg.py`, incl. real-bytes
    smoke (field 206's 1900/2005 dispatch); eb-domain battery 219 green.
  - Census: `research/dominance_census.py` → gitignored JSON; 818 fields, 34 867 funcs,
    **0 degraded**, deterministic.
  - **Measured (the falsifier):** the raw 12 268-site denominator was 77% compiled dispatch
    noise (byte-23 handshake + Mognet bands). On the **2 832 genuine story sites**: direct
    dominance 18.3% · +armed context 29.4% · +E3 co-located SC advance = **36.2% — the >55%
    prediction is FALSIFIED**. 257 of 974 story bits get hard SC windows. The naive 32.6%
    baseline was inflated (stale byte-adjacency past joins), and ~90% of story sites live
    outside Main_Init — the arm-context layer recovered what's soundly recoverable; the rest
    of the corpus is genuinely once-flag-gated (32% of story sites) and interaction-driven,
    not beat-gated.
  - **The re-plan (cheap, as budgeted):** E1–E3 are the *precision core*, not the primary
    estimators. The order model leans on **E4 (writer-field SC envelope) + E5 (milestone
    fallback)** for the long tail, with rung 4's reader-side constraints + the once-flag
    reader logic doing the tightening. The ladder is unchanged; only the estimator weighting
    moved. Per-arm-site edges are preserved in `FieldFlow.edges` for rung 4's intervals
    (merged ctx correctly drops equalities for multi-beat arms — the rotating-cast shape).
- **Rung 0 adversarial review (ultracode, 18 agents: 4 finder lenses → refute-by-default
  verification): 39 raw findings → 7 confirmed, 7 refuted at verification. ALL 7 FIXED
  (2026-08-03):**
  - **HIGH — no kill/def analysis**: guards survived assignment to their own variable (the
    once-latch `if(bit==0){bit=1;...}` idiom; 304/2832 story sites carried a provably-false
    guard, byte-exact repros on fields 1109/701/100). Fixed: `guards_at_ex` — per-instruction
    kills inside the block + cross-block path kills, with bit/byte/word ALIASING; unknown-target
    writes (0xD3 statements, computed assigns) kill everything; a `killed_guards` counter makes
    the loss visible (47 759 corpus-wide). Arm/call edges now stamp the guards at the ARMING
    INSTRUCTION, kill-aware. Honest residual, flagged not hidden: opcode side effects and
    cross-script interleaving are unmodeled — each site carries `yields_crossed`/`calls_crossed`
    flags so rung 4 can discount.
  - MED×3 / LOW×3: the all-in-edges-known fixpoint rule now mutant-tested (mixed root+orphan
    in-edge); call-context propagation tested (call-only main-entry target = direct ctx; an
    armed entry's intersection correctly drops a call guard — per-edge data kept for rung 4);
    explicit-uid Inits resolved via a per-field uid→slot map (the engine defaults uid=sid only
    when the operand is 0 — Obj.cs; 376 formerly-unresolvable call sites, and the entry-index
    rule now refuses remapped slots instead of possibly mis-targeting); Instance-source conds no
    longer cross edges (per-object state); JMP_IF false-edge negation tested; the vacuous
    `unsure_conds >= 0` assertion replaced (the counter was DEAD — now live: 32 140 corpus-wide);
    `innermost_guard_block`/`dominated_by` unit-tested. 41 tests total.
  - Post-fix census: sound coverage essentially unchanged (SC-direct 499 vs 518 pre-fix — the
    falsified verdict stands on honest numbers; windowed bits 255).
- **Rung 1: DONE ★ (2026-08-03, all 3 playtest slots owner-confirmed — PLAYTEST.md).**
  `story-seed <field> --beat <N|name>` + `--beats` (staged-beat discovery) + `[party]`
  emission (adds∩gates cast + non-Zidane donor player; dormant checks assert-by-hand; solo
  hint). Four playtest rounds: the bit model never failed; all misses were input affordances.
  Small follow-up queued: a shared-FBG sibling hint on story-seed/import (the wrong-sibling
  trap hit twice across arcs). DEFERRED by owner: the researched SC→ExpectedParty map (rung 7).
- **Rung 2: DONE ★ (2026-08-03).** The planned curated word table was replaced by MECHANICAL
  detection: `ate_word_seed` finds any word-var condition dominating an `ATE(1)` arm via the
  rung-0 guards (552/200 -> byte 236 = the proven case; Dali 351 -> 239/296 unaided). Emitted
  as `words = [{byte, value=1}]` + the widen-to-beat comment. Calibration playtest at 30823
  owner-confirmed (the July Small-Town-Knight result reproduced through the tool path).
- **DECISION GATE: RESOLVED (owner, option a)** — rungs 3–6 SHELVED unless a campaign
  playtest demands them; next = the campaign lane (demand-driven seeding across every member
  of a chain, the rung-8 flavor). — demand-driven seeding satisfied all single-field playtests;
  rungs 3–6 (full beat model) are now a campaign/New-Game-at-beat-N concern, not a
  single-fork one. Owner to scope.
- Open question for the owner: any path to disc-3/4 calibration saves, or accept playtest-only
  validation for the late game? (Answered 2026-08-03: playtest-only for now, tentatively.)

## Next block (from the chain playtest, 2026-08-03): BEAT-WINDOWED party + word derivation

Chain round 3 surfaced two derivation gaps with ONE shared cause -- party ops and word
writes are censused WITHOUT the rung-0 guards that bit writes get:
- **Marcus seeded into the Dali morning party** (donor 350 adds-and-gates him -- in a branch
  whose SC window is a DIFFERENT visit; Vivi's own add lives in a window the beat-blind
  heuristic ignored). The adds∩gates heuristic must become: adds whose SITE guards' windows
  cover the seeded beat.
- **The ATE mask is underivable** (story-REQUIRED at Dali: without one ATE, Garnet never
  reaches the weapon shop). The avail word's bits are written by story scripts under SC
  windows; capturing Global WORD/BYTE literal writes with guards makes the mask = OR of
  values whose windows <= beat.

The fix is NOT new rules -- it is the same guard machinery applied to two more op classes:
1. census + storyseed capture `party_sites` (B_PARTYADD/RemoveParty/SetPartyReserve tokens
   inside SET statements, with guards_at_ex at the site) and `word_sites` (vtype 4-7 literal
   assigns incl. OR-compounds, any Global index, with guards).
2. `party_seed(beat)` filters adds by window; `ate word value` = OR of windowed writes.
Owner's standing directive honored: derive, never exception-patch.
