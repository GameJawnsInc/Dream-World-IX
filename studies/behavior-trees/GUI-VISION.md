# The Behavior GUI — architectural vision

> **Status: DESIGN ONLY (2026-07-26).** No code. This is the charter for the Workspace's
> `[behavior]` surface, written now because the precondition the study set for itself is met:
> *"a Workspace GUI section (tree editor + the live blackboard/node-trace watch; built per the
> GUI study's call-site law, and not before the CLI exists)"* — `behavior compile|lint|view`
> exists, the TOML surface is in-game proven through the vector substrate, and the Workspace
> has zero `[behavior]` surface today (verified: no hit in `workspace/`). A companion HTML
> mockup was produced with this doc (see §7).

## 1. The semantic argument: a LADDER, not wires

The instinctive picture for "visual script editor" is boxes-and-wires (Blueprints, Behavior
Designer). **That picture would misrepresent this language.** The compiled model is: every
tick, each unit's branches are tried top to bottom; the first branch whose `when` conds all
hold selects its `do`. Nothing flows between nodes; there are no execution edges; **priority
IS vertical position**. Wires would be fiction drawn over a decision list.

The honest visual form already exists and is famous: **FF12's gambit system** — an ordered
list of `[condition → action]` rows, first-match-wins, reprogrammed by reordering. Millions of
players wrote real AI in exactly this model without knowing they were programming. That is the
center editor: **the Ladder** — one unit's branches as guarded rows, drag-to-reorder as the
priority edit. It is also byte-honest: the ladder on screen is line-for-line the TOML, which
is branch-for-branch the compiled dispatch.

What boxes-and-wires would also miss is that **half this language is geometry**: `near` radii,
`chase` standoff, `engage` radius/contact, patrol/march routes, flee refuge lists, wander
boxes, scan boxes, posts, HUD `MPOS`. And the *diagnostics* are geometry too — the route sweep
names the exact jam spot; the pursuit sweep reports a worst pair as two coordinates. Those
belong painted on the field, not printed as text. That is the second surface: **the Stage**.

## 2. The three surfaces (the Workspace's own tree/document/inspector shape)

- **The Cast (left rail)** — the roster: units (hp, pooled badge, pool), groups with member
  chips, pools (price/item, live `hireable` note), and the data layer (counters, tables,
  schedules, scans, huds). Selecting a cast member scopes the Ladder; selecting a data row
  scopes the Instruments to its indices.
- **The Ladder (document)** — the selected unit's branches as ordered rows. Each row: WHEN
  chips (ANDed, one per cond), a DO chip with its option values inline, decorator tags
  (`once`/`cooldown`/`raise_flags`/`clear_flags`) on the row's shoulder. The unconditional
  fallback is **pinned last with distinct treatment** (the compiler requires it; the GUI makes
  it structural — you cannot drag below it, deleting it is refused with the compiler's own
  message). Verb chips open pickers; pickers are **generated from the compiler's tables** (§3).
- **The Stage (document, second view)** — the field's art/walkmesh under a behavior overlay:
  posts, routes (with `route="auto"` detour splices drawn as such), refuge flags in priority
  order, radius rings per selected row, scan/wander boxes, group rosters color-coded — and the
  lint findings **in place** (a jam leg highlighted at the named spot; a pursuit worst-pair as
  pursuer▸quarry with the off-mesh run marked). Selecting a ladder row lights its geometry;
  selecting geometry lights its rows. All of this rides the settled mapview/worlddoc grammar
  (QGraphicsScene, Ctrl+scroll zoom, Ctrl+0 fit, CALIBRE-wired `scale=`, screen-fixed
  furniture).
- **The Instruments (inspector)** — the compile truth, from a real dry-compile (never a GUI
  reimplementation): the three budget meters (file/64KB · ticker · blackboard/820B), the
  `size_report()` per-unit byte histogram, the blackboard map (public-flag and `hireable`
  indices with **Copy `set_flag = [N, 1]`** buttons — the exact string a `[[choice]]` row
  needs), and the findings list (lint warnings/errors, each click landing on the Stage or the
  Ladder row it names).

## 3. The anti-rot laws (how the GUI stays true without maintenance)

1. **Vocabulary is DERIVED, never copied.** `behaviortoml.COND_VERBS` / `ACTION_VERBS` (verb →
   allowed option keys) and the `*_KEYS` sets are the single source for every picker, chip
   renderer, and option form. A new verb lands in the GUI with zero GUI edits. (The round-12
   law: *a gating list rots; derive eligibility from the data.*)
2. **The compiler is the only truth.** Every instrument reads `behavior compile`'s own outputs
   (report, `size_report()`, `validate()`, the lint sweeps). The GUI never re-derives byte
   costs, indices, or legality. Where the CLI prints, the GUI paints — same data.
3. **TOML stays the source of truth; the GUI is a projection.** Edits write back through the
   editor backend into the same open document the form editor holds (one doc, two views, no
   sync problem). The plain form remains the fallback surface for anything the Ladder doesn't
   render yet — progressive disclosure in both directions.
4. **`validate()` is pure and fast → live legality.** Unknown-key/one-verb/fallback-static
   errors surface as you type, with the compiler's own messages verbatim.
5. **The GUI-study laws apply from day one:** every mechanism names its spender at design time
   (call-site law); no compile on the GUI thread uninvited (warm-only — dry-compile behind an
   explicit action or a debounced worker); one accent per surface; `gui_snap` grows a
   `behavior:*` surface with the first commit, seeded by a synthetic fixture (the round-14
   pattern) so the worktree-skip trap never covers this tab.

## 4. The rung ladder (build order, each rung shippable alone)

- **Rung A — READ. ★ BUILT 2026-07-26** (`workspace/behaviorscan.py` pure layer +
  `workspace/behaviordoc.py` doc + shell wiring + `gui_snap behavior:guide|doc|compiled` over
  the synthetic BGLADE fixture owned by `tests/test_behaviordoc.py`; suites
  `test_behaviorscan`/`test_behaviordoc`). A per-field Behavior document rendering an
  existing `[behavior]` block: Cast, Ladders, Stage overlay, Instruments. Read-only.
  Owner rulings taken at build time: ladder+stage STACKED (Q1), archetypes will stamp a
  high-level `[minigame]` block (Q2, rung D's design), stepper after archetypes (Q3), live
  watch bookmarked (Q4).
- **Rung B — EDIT the ladder. ★ BUILT 2026-07-26** (same modules; snap `behavior:edit`).
  Structural ops are first-class GUI (reorder/add/delete branches, add/remove units); branch
  CONTENT edits as the branch's own TOML fragment in an inline editor with insert menus
  derived from the verb tables + live `validate()` — chip-level pickers stay open for a later
  rung without changing the data path. Edits ride the shell's real undo (one step per edit,
  focus `"behavior"` lands undo back on the tab). Two snap-caught laws: a right-aligned
  control inside an h-scrolling row lives off-screen (row buttons pin LEFT, the unit bar sits
  OUTSIDE the scroll), and an opening editor must take height from the ladder, not crush the
  stage.
- **Rung C — AUTHOR on the stage. ★ BUILT 2026-07-26** (same modules; snaps
  `behavior:stage|sweep`; the fixture gained a REAL synthetic walkmesh sidecar so the sweep
  lane runs genuinely end-to-end). Stage-edit mode: draggable handles over every writable
  point (`stage_handles` ids — a NAME reference moves the NAMED owner, never silently
  literalised; its list slot rides along for right-click insert/delete, floor 2 points),
  ring-resize grips on the selected unit's rings, the layout-probe guides (world compass in
  the probe's own words, the ~192u jam-spacing ring while dragging a post, live coords).
  Sweeps: `sweep_geometry` is the CLI lint lane AS DATA (same refs, dedupe, routed-line-for-
  autoroute, `describe_*` text verbatim) — verdicts paint IN PLACE (jam sub-segment + ✕,
  wall-hug dashes, pursuit worst-pairs + rate caption on its own tier); first Sweep press =
  the disk touch (walkmesh from the SAVED file, geometry always the OPEN doc), then edits
  re-judge debounced on the warm mesh; a generation guard drops in-flight sweeps on field
  switch. Deferred within C: drawing a NEW route point-by-point on an empty stage (point
  insert/move/delete shipped; a from-scratch route still starts in the branch editor), and
  the live-updating jam %% WHILE dragging the ring (it updates on drop via the armed
  re-sweep).
- **Rung D — ARCHETYPES. D1 ★ BUILT 2026-07-26** (`behaviorscan.BEHAVIOR_ARCHETYPES` +
  `stamp_archetype`; the cast rail's "＋ Archetype…" + the no-behavior guide's second
  action). Three player-bound proven trees stamp through one pure op + one undo step:
  sentry (watch/alarm/chase + a minted auto-routed beat), patroller, civilian (flee to
  refuges, wander home) — all fenced by a REAL dry-compile of the stamped doc
  (`editor.model.dumps` → disk → the genuine lane, `route="auto"` resolved over the
  fixture's walkmesh). Minted beat markers dedupe (`<npc>_beat_2`); rung C's drag handles
  are the shaping tool. **D2 ★ BUILT 2026-07-26:** the guard archetype (needs_target — the
  enemy picked through a third modal seam; BEHAVIOR.md's front example verbatim) + THE
  [SIEGE] READ-ONLY VIEW: a [siege] field renders its DESUGARED behavior
  (`behaviorscan.siege_view` — the build's own expansion) with full cast/ladders/stage/
  sweeps over the GENERATED routes, every edit affordance disabled and the banner naming
  the truth; rendering writes nothing into the open doc (fenced); snap `behavior:siege`.
  **D's remainder:** the shift patrol pair archetype, the Info Hub archetype cards, and
  the `[siege]` whole-block STAMP (authoring a new [siege] from the GUI — the read-only
  view is the rendering half; the stamp is the authoring half).
- **Rung E — TIME.** (1) **The offline tick-stepper**: a pure-Python interpreter of the same
  documented tree semantics stepping simulated positions — scrub a timeline, watch selection
  sweep the ladder rows and units move on the stage. Catches the priority/starvation family of
  authoring bugs before a playtest. It is an *instrument* and must be calibrated as one:
  offline ≠ in-game proof, and the sim must say so on its face. (2) **The live blackboard
  watch** (the charter's "node-trace watch"): the `selected` byte per unit is already a live
  trace and the debug menu already reads flags in-game; a GUI bridge is engine work
  (confirm-first, prefer-data-over-engine per the s59 lesson) — horizon, not v1.

## 5. Analyses the GUI makes worth building (shared with the CLI as lint verbs)

- **Shadow/reachability**: a row whose cond set is subsumed by an earlier row's (same-target
  `near 700` below a `near 900`, an `hp_le 1` below an `hp_le 2`) can never select — the
  interval domain of these verbs (`hp_le/gt`, `counter_*`, `time_*`, `near`) makes sound
  subsumption checks cheap. The Ladder greys the row and says why; the CLI gains the same
  check so headless authors get it too. (`once`/`cooldown` release semantics must be modeled
  — a sticky-Once row above does NOT shadow; the event-Once releases.)
- **Starvation family**: a sticky `once` over a monotonic cond (the BTTABLE round-2 class) is
  already a compiler law for announces; the ladder can flag remaining monotonic-sticky shapes.
- **Budget forecasting**: the histogram is per-unit today; the Ladder can price a row as you
  add it (~135B ticker + ~90B body for a pair branch — the measured constants), so the 64KB
  wall is a visible meter while authoring, not a build failure later.

## 6. Placement

A **Behavior tab** (per-field document, like Map/World), scoped to the open field's
`[behavior]` block, with the Editor tab's plain form as fallback. Rationale: the block is
field content, but its working set (walkmesh, sweeps, compile report, stage) is a document of
its own; the precedent is exactly how Map/World/Battle earned tabs. Ctrl-K gains
"Go to · Behavior" and per-unit rows ("Go to · watchman's ladder").

## 7. The mockup

The companion HTML mockup renders the full frame in the Workspace's own mist/light tokens:
Cast + Ladder (with a shadowed-row warning, a pursuit-sweep chip on a chase row, decorators,
the pinned fallback) + Stage (routes, rings, refuges, scan box, a jam marker, an auto-route
splice) + Instruments (budget meters, histogram, blackboard indices with copy rows, findings).
It is a *vision artifact*, not a spec: pane proportions, chip grammar, and exact affordances
are for the build rungs to settle against the real `fit_dialog`/CALIBRE machinery.

## 8. Open questions (owner's call, none blocking rung A)

1. Ladder+Stage stacked (one scroll) vs toggled (two views of the document)? The mockup
   stacks; a 12-unit siege field may want the toggle.
2. Does rung D stamp TOML text (visible, diffable) or a higher-level `[minigame]` block that
   expands at build? (Ties to the productization decision the handoff left open.)
3. Is the tick-stepper worth its calibration burden before the archetype rung, or after?
4. Live watch (rung E2): worth an engine lane at all, or does the debug menu's Flags panel +
   the stepper cover the need?
