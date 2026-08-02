# The interactive documentation base — design

**Status: RATIFIED ("go for it") — rungs 0, 1a, and 2 BUILT, all gates green, awaiting owner
review of the rendered site.** What shipped (branch `claude/interactive-docs-design-b3720c`):

- **Rung 0 ★** — `docsite/build.py` renders the corpus (README/SETUP/ff9mapkit-docs + a
  task-routed front page) into `docsite/_site/`: sidebar nav (`nav.toml` curation + auto-bucket),
  client search, light/dark, GitHub-parity heading slugs. The link/anchor gate FAILS the build —
  and its first run caught real rot: FORMAT.md's `#item_text` anchor (broken on GitHub too) and
  gallery/README's 13 dead image embeds. Preview: `py -m http.server -d docsite/_site`.
- **Rung 1a ★** — the CLI reference: one page per verb (127) from `cli.build_parser()`
  introspection, count-gated. Remaining 1b: the per-block data layer + example-linting.
- **Rung 2 ★** — `docsite/shots.py` + `shots.toml`: figures rendered by gui_snap in light+mist,
  widget-anchored annotations resolved at grab time into JSON sidecars (the site bakes SVG rings
  over clean PNGs), painted-path pins (cosmetic setText under blocked signals + statusbar),
  full-containment assert (caught the Import button clipping at 850px), provenance allowlist,
  `--check` proved byte-identical fresh-process re-renders. Tutorial 06 embeds three figures;
  the Build-tab one opens a kit-authored verbatim-fork FIXTURE (no bundled example can be a real
  fork — SE bytes). Gates: `py -m pytest docsite/tests -q` (22) — they FAIL, never skip, when
  assets are missing.

**Owner-review round (same session):** ring ④ on the Build figure pointed at a radio the SCROLL
VIEWPORT clipped — window-bounds containment was the wrong instrument. THE VIEWPORT LAW: a
callout rect must sit inside the window AND every ancestor scroll viewport (pure geometry, never
visibleRegion — paint-derived answers lie under WA_DontShowOnScreen). +2 figures shipped
(home-ready → SETUP §6, fork-regions → tutorial 07); a dlg:new-journey figure was PULLED — the
dialog paints the cwd into its Folder box (black-box surfaces cannot pin; a dlg ADAPTER is the
fix) and its teach text SEEMED to falsify tutorial 07's "Pick FF9 regions…" step. **CORRECTED by the
inventory:** that button EXISTS, hidden under the dialog's default Type (Bare) — 07's step 2
picks Multi-campaign first. A one-state screenshot cannot falsify a stateful flow (the
calibration law, again); the harvest records hidden controls precisely so existence-truth
survives state. 07 still gets rewritten on the rails (the teach note says region-as-campaign
forking moved to Import — the flow deserves re-verification), but it was not proven wrong.
10 committed PNGs `--check` clean.

**THE TUTORIAL SYSTEM (owner-directed pivot: "whole revamp of the tutorials — build the
system"):** ★ BUILT, contract = `TUTORIAL-SYSTEM.md` (sibling file). Three ties to truth, each
with a teeth-proven gate: figures (shots, above) · UI names (`docsite/uiharvest.py` → committed
`ui-inventory.json`, 129 controls; `[[tutorial.ui]]` declarations verified at build — widget
exists, label current, label used in prose whitespace-normalized) · commands (every `ff9mapkit`
line in every shell fence verb+flag-checked against `cli.build_parser()`; 72 corpus lines, clean;
calibrated by planted defects). Frontmatter = a `[tutorial]` TOML fence (TOML dodges the YAML
trap; GitHub renders it as an informative block, the site strips it into goal + requirement
chips). Template `docsite/templates/tutorial.md`; pilot = tutorial 06. The spot-fix tutorial-07
task was withdrawn — 07 gets rewritten on these rails. En route: the gate's own teeth test caught
its dead prose-containment check (raw included the declaration), and the corpus caught the
hard-wrap class (a label split across a markdown line break).

**Next:** the revamp itself (owner-authored on the rails; 07 first), rung 3 runnable fences,
the dlg adapter (dialog shots + dialog inventory), rung 1b (block data layer), rung 5 deployment
(owner, confirm-first). Design below is as-ratified.

**DEFERRED — retire the "Understand" shelf** (`UNDERSTAND-TRIAGE.md`, sibling file): the shelf's 22
docs triaged per-file — 2 keep, 8 demote to Reference, 11 move out of the manual, 1 held. Decided,
not scheduled. Two unblock conditions, both mechanical: a lull in feature work (the cut re-points
~32 link sites in a tree many lanes touch, and the link gate turns each collision into a failing
build for whoever merges second), and the overworld pillar reaching a state stable enough to write
a walkthrough against — which is what resolves the one conflicted row, `OVERWORLD_ENGINE.md`.

The charter: replace "a heap of AI-written `.md`s browsed raw in the repo" with an **explorable
documentation site, in its own module**, holding three things in one place:

1. **A language-grade reference** for the kit's authoring surface — every `field.toml` block and
   every CLI verb addressable at its own URL, formally tabulated, cross-linked like a programming
   language manual.
2. **System explanations with attached tutorials** — how the engine/kit actually works, each
   concept wired to the tutorial that exercises it.
3. **Visual GUI tutorials whose screenshots are generated by a job**, not shot by hand — re-run
   "gather screenshots" after a reskin/redesign and every figure in every tutorial updates itself.

---

## 1. Prior art this design builds on (owned before the lane was opened)

| Asset | What it contributes | What it must NOT become |
|---|---|---|
| `ff9mapkit/docs/` — 34 topic docs + 14 tutorials, accuracy-passed, tone conventions in force | THE CONTENT SEED. Prose stays canonical here; the site renders it. | Not forked — the site must never hold a second copy of a sentence. |
| `docs/FORMAT.md` (~1.7k lines, ~45 block sections) | The de-facto language reference; its heading grammar is regular enough to explode into per-block pages. | Not the formal layer — hand-maintained prose drifts (the 2026-07-07 pass caught would-fail recipes in it). |
| `SETUP.md` §7 — the grouped 114-verb CLI reference, regenerated via `cli.build_parser()` introspection | Proof that GENERATED reference already works here. The site generalizes the pattern. | |
| `tools/gui_snap.py` — 63 pinned, deterministic, headless Workspace surfaces | THE SHOT ENGINE'S CORE. Prefs pin, native-Qt law, modal stubs, fixture arsenal, pixel-diff stability — all paid for already. | Not forked. One owner for surface pins stays gui_snap; the docs job consumes it. |
| The Mist Codex (`website/ff9/`, unmerged branches `claude/ff9-interactive-wiki-76174a` + `claude/interactive-wiki-pages-1c7841`) | Platform laws proven in production shape: no-build ES modules, section registry, in-browser selftests, `aspect-ratio` stages, NO `<base>` tag, document-relative paths. | A DIFFERENT PRODUCT — an RE museum for jawnston.com with war-story plates. Borrow its laws, never its ambitions; the docs site is user documentation. |
| Workspace in-app teaching (Info Hub cards, concept cards, guide teach text) | Sibling teaching surfaces; long-term the ⓘ links could target site anchors. | Not a dependency of any rung below. |

## 2. Decisions

**D1 — The module is repo-root `docsite/`.** Generator + shot manifest + reference data +
templates + committed shot assets; rendered output at `docsite/_site/` (gitignored). Not inside the
pip package (docs are hosted/browsed, not imported); not under `website/` (unmerged branch, different
audience and contract). Working title "The Dream World IX Manual" — the name is the owner's call.

**D2 — Markdown stays the source of truth.** `ff9mapkit/docs/*.md` remain canonical and
GitHub-browsable; the builder ingests them. Generated pages (reference, catalogs, transcripts) exist
only in the site output. THE ONE-COPY LAW: any sentence living in both a `.md` and the site is a
build artifact of the `.md`, never a fork.

**D3 — A custom no-build generator, not an SSG.**
Considered: **mkdocs-material** (instant nav/search, but the interactive pieces — annotated-TOML
hovers, widget-anchored shot overlays, benches — fight the theme, and it drags a dep chain into a
kit that prizes minimal installs); **Sphinx** (rejected — Python-API center of gravity; our users
author TOML and click a GUI). Chosen: a small Python builder under a `docs` extra (`markdown` lib +
stdlib), emitting dependency-free static HTML + ES modules per the Mist Codex platform laws. Local
preview `py -m http.server` from `docsite/_site/`; deployable by scp or GitHub Pages unchanged.

**D4 — Reference pages are GENERATED FROM TRUTH wherever truth is machine-readable.**
- **CLI:** one page per verb from `cli.build_parser()` introspection (args, defaults, help,
  group), grouped as SETUP §7 is today. Follow-on: EMIT SETUP §7 from the same pass, ending its
  dual maintenance.
- **Blocks:** FORMAT.md stays the narrative; a new data layer `docsite/data/blocks/*.toml` (one
  small file per block: keys, types, defaults, required, cross-refs, owning tutorial) renders the
  formal tables. Two teeth against rot: (a) every example TOML on a block page is run through the
  REAL `ff9mapkit lint` at build time and the build fails on a finding; (b) where the kit exposes
  accepted-key sets (today scattered: `[party]`, `[[savepoint]]`+mognet in `build.py`,
  `[behavior]` in `behaviortoml.py`, `[chocobo]`) the build joins the data layer against them and
  FAILS on a key present in one and absent in the other. A REFERENCE ROW NOBODY CHECKS IS A WISH
  (the docstring-law corollary). Consolidating the scattered key sets into one kit-side registry is
  a rung-1 follow-on, not a blocker.
- **Catalogs:** models / songs / battle scenes / real fields / archetypes from the kit's own
  catalog + Info Hub modules — the pages users currently reach only inside the GUI.

**D5 — The shot engine** — §3, the core novelty.

**D6 — Tutorials are EXECUTED, not just proofread.** CLI tutorial command blocks tagged runnable
are executed at build time against a scratch project — the offline subset only (`new`, `lint`,
`build` dry-run, `walkmesh verify`; never deploy, never the game). Transcripts embed into the page;
a recipe that errors fails the build. This mechanizes the 2026-07-07 lesson (adversarial verify
caught would-fail recipes in the first docs pass): make the build the adversary. Offline ≠ in-game
proof — the pages still say so where it matters.

**D7 — Interactivity, tiered.**
- T1: build-time auto-linkifier (every `[[npc]]`-style mention or verb name in any page becomes a
  link to its reference page — the Codex's linkifier pattern) + client-side search over a
  build-time JSON index. This alone delivers "explorable".
- T2: the annotated-TOML explorer — example files render with every key hoverable, the hover card
  drawn from the same block data layer (parse the example, join against `docsite/data/blocks/`,
  emit annotations at build). This is the "language docs" feel.
- T3: interactive benches ONLY where a tutorial teaches spatial math (walkmesh frame, camera
  projection) — borrow Mist Codex widget laws (selftests, golden samples from kit Python). Never
  linear scrollytelling; never the museum voice.

**D8 — Deployment is DEFERRED and confirm-first** (outward-facing). Candidates: GitHub Pages on
the public repo, or jawnston.com beside the Codex. The design's only obligation now: the output is
a plain static tree so either works later. Versioning: build stamped with kit version + git sha;
per-release snapshots are a rung-5 question.

**Tone:** the 2026-07-07 doc conventions bind every site page verbatim — no first person, no
agent/workflow provenance, no superlatives.

## 3. The shot pipeline (the "gather screenshots" job)

**Reuse, don't fork.** `docsite/shots.py` consumes gui_snap's harness — the prefs pin, `_settle`,
`_grab`, `_no_modals`, `_grab_next_dialog`, and the whole fixture arsenal (synthetic demo campaign,
`_paint_room`, gradient thumbs, fake installs). First cut imports `tools/gui_snap.py` directly (its
module-import side effects ARE the wanted setup); extraction into a shared `tools/guisnaplib.py`
happens only once shots.py stabilizes, and gui_snap keeps sole ownership of surface-state pins — a
tutorial needing a state that defect-hunting never pinned adds it to gui_snap, then references it.

**The manifest** — `docsite/shots.toml`, one entry per figure:

```toml
[shot.import-fork-field]
surface  = "tab:import"            # a gui_snap surface, or surface + an action list
themes   = ["light", "mist"]       # the committed pair; the site swaps by prefers-color-scheme
scale    = 100
width    = 1280
subject  = "window"                # or a widget attr-path for a cropped subject
annotate = [
  { widget = "import_field.fork_box",  kind = "ring",  label = "1" },
  { widget = "import_field.find_btn",  kind = "ring",  label = "2" },
]
used_by  = ["tutorials/06-gui-field.md"]
```

**WIDGET-ANCHORED ANNOTATIONS — the load-bearing idea.** Callouts name widget identity, never
pixels. At grab time the runner resolves each widget to its rect and writes a JSON **sidecar** next
to the clean PNG; the SITE draws the rings/labels as SVG overlays. Consequences, each deliberate:
- a reskin or relayout re-anchors every callout correctly on re-run — the promise the whole
  feature makes;
- the PNG stays clean and pixel-diffable (no baked arrows to churn);
- overlays are theme-aware and crisp at any zoom;
- a widget that VANISHED in a redesign fails the job loudly — which is a documentation-drift
  alarm, not an inconvenience. That failure is the system working.

**Determinism laws, inherited and extended:** stable fixture paths (never mkdtemp — the coop
lesson), no-font synthetic art, pinned prefs/motion/guided, NO_THUMBS except thumb-warm surfaces —
plus one new law the §8 spike minted: **PIN EVERY PAINTED PATH.** The Import tab paints the
checkout path into its "Write to:" box; a shot surface must pin any such box to a neutral value
(`C:\FF9Projects\...`), or every machine's run diffs in its most prominent line (the coop
SessionCode class).

**THE PROVENANCE LAW (hard):** committed shot PNGs contain ZERO Square-Enix pixels. Every shot
surface uses kit-authored fixtures — the bundled examples, `_paint_room` art, gradient
placeholders, fake installs. The shots job REFUSES `--thumb-source` and any surface known to paint
real-install art. `docs/PROVENANCE.md` gains a docs-assets clause at rung 2.

**Outputs, committed:** `docsite/assets/shots/<name>_<theme>.png` + `<name>_<theme>.json`
(annotation rects, kit version, surface id, shown/sizeHint geometry). Committed because: pixel
diffs become reviewable in PRs (the stability engineering exists precisely to make that
meaningful); the site build then needs no Qt, no Windows, no game; and GitHub's raw `.md`
rendering can embed the same PNGs.

**Jobs:**
- `py docsite/shots.py --all | --shot NAME` — regenerate (the "gather screenshots" job).
- `py docsite/shots.py --check` — re-render to scratch, compare against committed, list drift.
  Native-Qt-on-Windows only (gui_snap's own law: offscreen lies about width), so shots regenerate
  LOCALLY; CI runs only the Qt-free integrity gates: manifest↔page↔file cross-check (no orphan
  figure, no missing figure, every `used_by` real), sidecar schema, provenance surface allowlist.
  Integrity tests FAIL when assets are missing — never skip (the worktree-skip trap).

**Theme swap payoff:** both palettes are generated for free by the same run, so every figure ships
light+dark and the page follows the reader's theme — a variant hand-shot docs never afford.

## 4. Information architecture

Diátaxis, which the corpus already matches:
- **Learn** — tutorials 01–14, illustrated (GUI ones) and executed (CLI ones).
- **Understand** — ENGINE, PIPELINE, TECHNICAL, FORK_FIDELITY, OVERWORLD_ENGINE, ATE_SYSTEM,
  DIALOGUE, BEHAVIOR, … the "how the system works" shelf.
- **Reference** — FORMAT exploded per-block; CLI verbs; catalogs; GLOSSARY; id/flag bands;
  KNOWN_ISSUES + TROUBLESHOOTING as the diagnostic index.
- **Front page** routes by task ("fork a room" / "build a field from scratch" / "make a world" /
  "add a character"), not by file name.

## 5. Rungs

- **0 — the skeleton.** Builder renders the EXISTING docs unchanged into a nav+search site;
  local preview. GATE: every existing page reachable; links + anchors resolve (the slugger
  double-hyphen trap from the 2026-07-07 pass is a named test); search finds sampled terms.
- **1 — the reference.** CLI pages from introspection; FORMAT split into per-block pages with
  data tables + linted examples; auto-linkifier live. GATE: verb count equals the parser's (never
  prose); every block example passes real lint; the key-set cross-check runs where sets exist.
- **2 — the shot engine.** Manifest + runner + tutorial 06 fully illustrated in both themes with
  widget-anchored overlays. GATE: two consecutive `--all` runs byte-identical; a deliberate QSS
  probe drifts ONLY the expected shots; provenance allowlist enforced.
- **3 — executed tutorials.** 01 + 02 transcripts run at build. GATE: a planted wrong flag in a
  tutorial fails the build.
- **4 — the explorable layer.** Annotated-TOML explorer + an example gallery built by the real
  builder from `ff9mapkit/examples/`.
- **5 — deployment + versioning.** Owner decision (confirm-first): Pages vs jawnston.com;
  per-release snapshots.

## 6. Risks & standing constraints

- **Shots are Windows-local** (native-Qt law). Accepted: `--check` is the local ratchet, CI owns
  integrity only. Stated honestly on the contributing page.
- **SE pixels in assets** — the provenance law above is the fence; it is enforced by allowlist,
  not by review.
- **Generated-reference rot** — every generated artifact carries a failing gate (introspected
  counts, linted examples, key-set joins, widget-anchor resolution). No gate, no artifact.
- **Shared install, many worktrees** — the shots job touches NO install and NO live mod folder
  (fixtures only), so it is safe to run from any concurrent session.
- **Scope creep toward the museum** — benches only where a tutorial needs one; the Codex owns war
  stories.

## 7. What this supersedes / leaves alone

- SETUP §7 eventually becomes an EMITTED artifact (rung 1 follow-on) — one owner for the CLI
  reference.
- `docs/gallery/` (a README stub today) is absorbed by the example gallery at rung 4.
- The Mist Codex, the in-app Info Hub, and the concept cards are untouched; unifying their content
  sources with `docsite/data/` is a post-rung-4 study, not scope here.

## 8. Spike record (2026-07-31, this worktree)

- `py tools/gui_snap.py --list` → 63 surfaces across 15 families.
- `home:ready` + `tab:import` rendered at mist/100, 1280×850, clean and legible — no game, no
  human, no window flash, straight from an agent harness. The core claim of this design is
  therefore not speculative: the screenshot engine exists and runs today.
- Minted the PIN-EVERY-PAINTED-PATH law (the Import tab's "Write to:" box painted this checkout's
  path into the record).
- Confirmed scattered accepted-key sets in `build.py` / `behaviortoml.py` / `chocobo.py` — the
  D4 cross-check has real anchors; consolidation is follow-on work.
- Workspace palette roster confirmed at 8 (`editor/theme.py THEMES`) — the light+dark pair costs
  one extra run flag.
