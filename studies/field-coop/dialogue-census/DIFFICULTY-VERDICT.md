# F3 difficulty verdict — the census synthesis (2026-07-23)

> Three byte-grounded census lanes over all 818 real field scripts (window lifecycle /
> choices / divergence — findings in this directory) joined with the F3 engine recon.
> The owner's directive: "make sure the cutscene/dialogue system is robust; accurately
> assess the difficulty — we have rich access to the scripts."

## VERDICT: MODERATE, WELL-BOUNDED — and cheaper than the ratified design priced it.

Three repricings, each census-proven:

### 1. The MAP mirror is DEAD WEIGHT — do not build it. (divergence lane)
MAP-scoped flags were the assumed hard problem (39% of windows gate on them, never
mirrored). The census proves MAP state is DERIVED, not root: zeroed at every field entry
and a deterministic function of the mirrored GLOB snapshot + the script itself. Under L1
(same script, same GLOB, same start point) MAP-gated windows align on their own.
93.9% of locked cutscene spans read NO structural root (rng/timing) and replay in perfect
lockstep. Building a MAP mirror would be wasted engineering.

### 2. Choices cannot desync the STORY — lockstep buys presentation parity. (choices lane)
2,134 choice reads, 392 fields. Every durable consequence of every stock choice is a GLOB
write — which the state mirror already overwrites host→guest. ~74% of choice branch sites
are story-safe even if the guest picked differently; the genuinely divergent set is 376
transient-only sites in 216 fields, and those diverge in PRESENTATION (which lines play
this visit), never in story state. Forcing at GetChoose/DialogManager.SelectChoice covers
all three consumption idioms (switch 30% / if 54% / store 16%) with zero special-casing.

### 3. The structural failure floor is ~1%, outside the lockstep domain. (divergence lane)
Un-mirrorable divergence = RNG (1.2% of windows, 0.9% of cutscene windows) + timing (0.3%),
concentrated in ambient async idle-NPC chatter (e.g. field 563's random crowd lines) that
lockstep should never touch. Scoped to L1-pinned host-driven scenes, the timeout fallback
fires on ~6% of cutscene spans, usually one leaf window, and re-syncs on the next literal
textId. It is a rare escape hatch — the "robust" bar is met by construction, not hope.

## What IS the work (the honest hard part)

- **The L2 confirm/choice mirror is mandatory, not optional**: 82.7% of all windows
  (23,713) are confirm/choice-gated on a blocking thread; ~26% of cutscene windows are
  choice/input-gated. Without L2 the guest's stream diverges constantly. The engine recon
  found single clean funnels for both directions (Dialog.OnKeyConfirm; the SelectChoice
  global slot, forcible race-free), so the mechanism is tractable — but it is the round.
- **FIFO discipline**: the alignment triple is unique-while-live but NOT an instance id
  (14.2% duplicate reopens) — the designed peek-until-match FIFO is load-bearing.
- **winnum-scoped matching**: ~19% of fields can hold two live windows / cross-thread
  opens; the design's per-winnum targeting already covers it.
- **Every wait state needs its escape**: the per-window DialogWaitMs timeout + the ~2s
  lane-staleness release. Two independent escapes at every node; the timeout ships first
  and is never disabled.

## Constraints to document (cheap)

- **Same-language sessions required**: ~7 engine-hardcoded language-conditional dialogue
  overrides (fields 1060/1650/1652/1657/1659/1850/2172/2209) diverge across a
  cross-language pair. Document; do not special-case.
- Menu(4,·) party-change windows (65 fields) are a different construct (opcode 0x75),
  already F1-gated for guests — excluded from the choice lane by design.
- SetTextVariable number substitution can render different numbers guest-side (15.9% of
  sites) — cosmetic; never moves the alignment key.
- AteCheckArray is never READ by any .eb expression (write-side achievement state only) —
  it cannot drive window divergence.

## Scope decisions (recon S1-S5 + census repricings) — for owner ratification

| # | Decision | Recommendation | Census support |
|---|---|---|---|
| S1 | Engage scope | Only under L1 (host event flag + co-located) | RNG chatter is ambient/unlocked → auto-excluded by the L1 scope |
| S2 | Guest solo dialogue | Fully local, never suppressed | falls out of S1 for free |
| S3 | Suppress arming | Engage-on-first-match per window | kills the R4 softlock class |
| S4 | Pacing granularity | Per-page lockstep (tap OnKeyConfirm) | page rate = line rate; 8-byte frames make volume a non-issue |
| S5 | Scripted closes | Filtered (never emitted) | script-paced windows are the free 17% |
| S6 (new) | MAP mirror | DO NOT BUILD | divergence lane repricing |
| S7 (new) | Language | Require same-language sessions | the 7 hardcoded overrides |

With this scope, F3 = wire v12 + TypeDialog FIFO lane + the OnKeyConfirm tap + the guest
force/suppress/timeout state machine. No MAP mirror, no ATE machinery, no per-field
special cases. Difficulty: comparable to F2, larger surface than s54-s56, with the
softlock-escape invariant as the one non-negotiable.
