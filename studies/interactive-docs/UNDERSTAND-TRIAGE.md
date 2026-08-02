# TODO — retire the "Understand" shelf (deferred)

**Status: DECIDED, NOT SCHEDULED.** The triage below is complete and ratified; execution is
deliberately deferred. Nothing here is in progress. Triage taken against the shelf as of
`b57a92d0` (22 docs, 9,006 lines); re-verify the census before executing if the corpus has moved.

## Why deferred, and what unblocks it

Two conditions, both mechanical rather than preferential:

1. **A lull in feature work.** The cut re-points ~32 link sites across `ff9mapkit/docs/`, a tree
   many concurrent lanes touch. Executed mid-flight it collides with every in-progress doc edit,
   and the link gate turns each collision into a failing build for whoever merges second.
2. **The overworld pillar reaching a pause-worthy state.** `OVERWORLD_ENGINE.md` is the one
   conflicted row (below). Its hold resolves only when there is an overworld walkthrough to
   replace it with — which requires the pillar to be stable enough to write one against.

## The finding

The shelf holds three different kinds of document that were merged because none of them is a
tutorial. Length is not the discriminant — `FORMAT.md` is 2,417 lines and unambiguously belongs.
**Register and audience** are: most of this shelf was written to a developer, as an engineering
record, and then shelved as if it were user explanation. Diátaxis explanation means *why the
system behaves this way and what it costs you*, not *how it was figured out* or *how done it is*.

Two docs survive the shelf, which means the shelf itself does not. Fold `ENGINE.md` and
`PIPELINE.md` into **Start** and retire the section. Eight further docs are not cut at all — they
document authoring surfaces and were simply shelved wrong; they move to **Reference**.

## The census

Five mechanical tells per doc: a `Status:`/`Recon synthesis` block in the opener, date stamps,
internal `.py` references, `studies/` paths (internal-only — a user cannot open them), and
`file:line` citations.

```
DOC                     LINES  STATUS DATES PY_REF  STUDIES FILELINE
PIPELINE                  216       0     0      0        0        0
ENGINE                    120       0     0      0        0        0
TECHNICAL                 188       0     0      0        0        0
FORK_FIDELITY             421       0    16     19        1        7
OBJECT_CARRY              397       1     1     39        0        8
TEXT_CARRY                133       0     0      3        0        0
PLAYER_GRAFT              273       1     0     19        0        1
CAMPAIGN_IMPORT           494       2     7     48        0       16
JOURNEYS                  408       1     8      9        0        0
OVERWORLD_ENGINE         1098       0    57     18        5       82
DIALOGUE                  141       0     0      0        0        0
ATE_SYSTEM                393       0     4     11        0       28
BEHAVIOR                  817       0     0      1        3        0
BATTLE_DESIGN             669       2    10     67        0       75
ATB_DESIGN                360       2     3      4        0       77
SUMMONS                  1361       1     1     22       15        2
SPS                       184       0     1      0        0        0
SCRIPTS_DLL               585       1     2     11        0        6
CUSTOM_MODELS             675       1    12     25        0       46
ANIMATION_EDITING         155       0     0      0        0        0
WALKMESH_EDITING          219       1     0      2        0        0
SAVEPOINT                 382       1     7     14        0        1
```

**The census ranks; it does not decide.** `TECHNICAL.md` scores zero on all five yet is plainly a
reverse-engineering record (*"this document records the non-obvious parts"*). Register still needs
a human read — the counts only sort the queue.

## The triage table

Re-point cost counts inbound links **from pages that stay**; links from pages that move in the same
batch are free.

| Doc | Lines | Verdict | Why | Re-point |
|---|---|---|---|---|
| **ENGINE** | 120 | **Keep** (→ Start) | Zero tells. Answers "do my players need the engine bundle?" — the question S7's zip step needs. Most-linked doc on the shelf. | — |
| **PIPELINE** | 216 | **Keep** (→ Start) | Zero tells. Idea → playable field. Actual explanation. | — |
| **DIALOGUE** | 141 | Demote → Reference | Zero tells; documents `ff9mapkit dialogue` + the editor forms. Never was explanation. | — |
| **BEHAVIOR** | 817 | Demote → Reference | Opens on the `[behavior]` block and CLI usage. Clean but for 3 `studies/` refs. | — |
| **SAVEPOINT** | 382 | Demote → Reference | Documents `[[savepoint]]`. Strip the status block + 7 dates. | — |
| **SPS** | 184 | Demote → Reference | Browse/preview/re-skin tiers. User-facing as written. | — |
| **SCRIPTS_DLL** | 585 | Demote → Reference | Documents `script = {…}` in field.toml. Strip status + provenance. | — |
| **JOURNEYS** | 408 | Demote → Reference | Self-describes as "the journey schema reference + job list" — keep the schema, cut the job list. | — |
| **SUMMONS** | 1361 | Demote → Reference | Real surfaces (`[[summon]]`, reskin, rescore), but the heaviest edit of the keepers: 15 `studies/` paths a user cannot open. | — |
| **CUSTOM_MODELS** | 675 | Demote → Reference *(rewrite)* | Titled "Feasibility & Design"; 46 `file:line`, 12 dates. The verbs live in the generated CLI reference, so what remains is a concept page. **Judgment call — see open questions.** | — |
| **ANIMATION_EDITING** | 155 | **Move → Tutorials** | Subtitled "a basic tutorial". Mis-shelved, not misjudged; it is Track D content. | none |
| **ATB_DESIGN** | 360 | Move → internals | "RESEARCH + PLAN, not built." Nothing shipped, zero user-facing inbound. The cleanest cut available. | 0 |
| **PLAYER_GRAFT** | 273 | Move → internals | "began as an implementation-ready design doc." | 0 |
| **TEXT_CARRY** | 133 | Move → internals | Subtitled "Implementation." | 0 |
| **OBJECT_CARRY** | 397 | Move → internals | "began as a design doc"; 39 `.py` refs. | 1 |
| **TECHNICAL** | 188 | Move → internals | "records the non-obvious parts." `ENGINE.md` already carries the user-facing half. | 2 |
| **WALKMESH_EDITING** | 219 | Move → internals *(salvage)* | "Spec —", v1/v2/v3 status. Salvage: "why does my multi-floor fork disconnect" → TROUBLESHOOTING. | 2 |
| **ATE_SYSTEM** | 393 | Move → internals *(salvage)* | "byte-accurate teardown", 28 `file:line`. Salvage: the authoring half → FORMAT. | 4 |
| **CAMPAIGN_IMPORT** | 494 | Move → internals *(salvage)* | "P1–P5 implemented", 48 `.py`. The verb is already in the generated CLI reference. Salvage: the `--whole-zone` 41%-miss trap. | 4 |
| **BATTLE_DESIGN** | 669 | Move → internals *(salvage)* | Self-declared "the honest gap map", the battle analog of FORK_FIDELITY. Salvage: what is tunable without a DLL → a real reference page. | 8 |
| **FORK_FIDELITY** | 421 | Move → internals *(salvage)* | "~75% and advancing", "deferred graft items unblocked" — an internal roadmap. Salvage: the short honest page (below). | 11 |
| **OVERWORLD_ENGINE** | 1098 | **Hold — conflicted** | Worst census score on the board, and the only overworld documentation that exists. Cutting it leaves the largest pillar with nothing. Resolves when an overworld walkthrough exists (REVAMP-CRITIQUE item 3). | 3 |

## Three findings from the fallout analysis

**The gap maps are load-bearing as link targets even though their content is internal.**
FORK_FIDELITY (11) and BATTLE_DESIGN (8) carry roughly two-thirds of the total re-point cost,
because everything that needs to admit a limitation points at the honest-limitations doc. This is
the strongest argument for salvage over deletion: those 19 links need somewhere real to land.

**The carry trio is a free cut.** OBJECT_CARRY, TEXT_CARRY, and PLAYER_GRAFT link almost
exclusively to each other, plus FEATURES and FORK_FIDELITY. Moved together, the cost is one file.

**`FEATURES.md` is one edit regardless of scope.** It links to essentially all 22 and sits on the
Reference shelf — the concentrator for every scenario.

## The mechanical blocker

There is no way to drop a page from the site today. `docsite/build.py:49` takes an allowlist of
source **roots** (`ff9mapkit/docs` wholesale), deliberately — *"an allowlist cannot rot open the
way a denylist can."* `nav.toml` curation only orders; an unlisted page falls into an automatic
"More" bucket rather than vanishing.

So "move to internals" means physically relocating files to a root the builder does not ingest
(e.g. `docs/internals/`) — still in the repo, still GitHub-browsable, simply not in the manual.
Preferred over teaching the builder per-file exclusions: it keeps the allowlist honest and makes
the audience split visible in the tree.

The link gate bills the fallout correctly — the build **fails** on a dead link, so every cut
surfaces its own re-pointing work instead of leaving rot.

## Suggested execution order

1. **The free cuts, to prove the mechanics** — ATB_DESIGN + the carry trio (1 re-point total).
   Establishes the `docs/internals/` root and confirms the link gate catches the fallout.
2. **The cheap moves** — TECHNICAL, WALKMESH_EDITING, ATE_SYSTEM, CAMPAIGN_IMPORT (12 total),
   with their salvage extractions.
3. **The salvage page**, before the expensive moves: one short honest page carrying the single
   user-facing fact currently buried in FORK_FIDELITY — a forked room reproduces the place but not
   the story state. It becomes the landing target for FORK_FIDELITY's 11 links.
4. **The expensive moves** — FORK_FIDELITY, BATTLE_DESIGN (19).
5. **The demotions** — 8 docs to Reference, plus the status/provenance stripping each needs.
   SUMMONS (15 `studies/` paths) and CUSTOM_MODELS are the heavy ones.
6. **Retire the shelf** — fold ENGINE + PIPELINE into Start, delete the section from `nav.toml`.
7. **OVERWORLD_ENGINE** — only once its replacement exists.

## Open questions (owner calls, not mechanical)

- **CUSTOM_MODELS** — demote-and-rewrite, or move-and-salvage? It is a design brief that grew a
  user surface; the CLI reference already covers its verbs, so the residue may be too thin to
  justify a Reference page.
- **The internals root's name and contract** — `docs/internals/` vs somewhere outside `docs/`
  entirely. Whatever is chosen must not be a `SOURCE_ROOTS` entry, and skills/memory that cite
  these paths (several do) need updating in the same pass.
- **Whether the moved set stays in the repo at all.** The recommendation is yes — these are real
  engineering records with continuing value to development; the objection is only to shipping them
  as user documentation.

## Related

- `REVAMP-CRITIQUE.md` — the ranked structural items; item 3 (overworld has no tutorial) gates the
  OVERWORLD_ENGINE row here.
- `PLAN.md` — the arc's rung status.
- `CURRICULUM.md` — track architecture; the demoted docs are the fallback for pillars with no
  tutorial (REVAMP-CRITIQUE item 8), which is why they are demoted rather than cut.
