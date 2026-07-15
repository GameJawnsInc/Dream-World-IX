# GUI aesthetics — state + next steps

**Branch:** `claude/gui-card-readability-eb5d9f` · **20 commits** · ✅ **MERGED to master 2026-07-15** as
`5c212e2` · 2911 tests + `--smoke` green on the merged tree.

> **⚠ MOSTLY UNPLAYTESTED.** Every judgement in this arc was made from offscreen renders and computed
> contrast ratios. **Confirmed live: Mist** (user, 2026-07-15: *"Mist looks good"*). **Still unseen:** the
> hero's signet, and the retuned `accent`/`accent_fg` in dark / nord / solarized-dark / solarized-light —
> in particular **dark's Deploy button is now dark-ink-on-blue, not white-on-blue** (3.20 → 5.39). That is
> the most visible unjudged change in the tree. Cheap to close: launch `apps/ff9_workspace.pyw` and look.

**Merge, as it actually went.** Master moved ~10 commits ahead (overworld/beach work) while this ran. The
earlier claim of *zero* file overlap went **stale before landing** — `CLAUDE.md` ended up touched by both
sides (master's mountain work, this arc's §10 line). Git auto-merged it; both survived. The trap was real
and was avoided: the main repo sits on `claude/interior-topography-plan-b61671`, so a `cd repo && git merge`
would have landed the GUI work on the topography branch. Master was checked out in **none** of the 11
worktrees, so the landing was `git fetch . <branch>:master` from here — fetch refuses a non-fast-forward,
which is the property that makes it safe. See [[project-ff9-main-repo-branch-trap]].

---

## What shipped

| | |
|---|---|
| `86de3f5` | **Phase 0** — the `:focus::indicator` selector bug **that was the original screenshot**, + the untested `surface_2` contrast rung |
| `685ba1a` `881e468` `0ecfa75` | **The card** — `widgets.section()`, kept and fixed, all 27 sites |
| `58f7deb` | Checked box gets a **tick**, checked radio a **dot** |
| `c1073dc` | **The type pass** — names + captions, the mono register, the accent focus hole |
| `6cab262` | **Hover** — 4 palettes had none |
| `2e7a939` | Co-op Status → a definition list; diagnostics shout |
| `764ca74` `5ed0a21` `11fae9e` `5e61ebd` | **SIGNET** — the Mist palette, the stretch fix, the hero, the Ctrl-K theme command |
| `f1c3867` `b758182` `721fb81` `0dcb2c4` `49c3df4` | **The contrast sweep** — the transparent-container bug, the audit tool, accent-as-text, the accent floor, the status hues, `help`/`muted` |

## Seven live defects found — none visible to a test that reads source

Every one needed a **rendered pixel** or a **computed ratio**, in a codebase that had just finished ten
phases of accessibility work:

1. `:focus::indicator` — a malformed selector boxed **every radio in the app**, and radios had **no focus
   ring at all**. This *was* the "cards don't read well" screenshot.
2. `#accent` out-ranks `:focus` — **every accent button, including the crumb Deploy, had no focus ring.**
3. `hover == surface_btn` byte-identically in 4 palettes — **no button hover feedback at all.**
4. A container's bare `background: transparent` out-ranks the app sheet — the newcomer's primary CTA was
   **unfilled in all 8 palettes, invisible in 5.**
5. `accent` as body text — sub-AA in **6 of 8**.
6. `accent_fg/accent` fenced at **3.0** (the *non-text* floor) guarding a **13px button label** — sub-AA in 4 of 8.
7. `help` fenced against **nothing**; `muted` fenced on 3 of 4 grounds.

**The pattern:** 4, 5, 6 and 7 were all *fences set at the wrong bar, green the whole time.* A fence that
covers 3 of 4 grounds just moves the bug to the 4th.

---

## Next steps, ranked

### 1. PLAYTEST. (blocks everything else)
Launch it. Look at **Mist** (Ctrl-K → "Theme: Mist (FF9)"), the **hero**, and the **retuned accents** in
dark/nord/solarized. Specifically judge:
- the hero's signet — if it lands thin, IDENTITY.md says **raise `_MIST_ALPHA` before adding a second gold
  element**. One corner, once, or it is a costume.
- **dark's Deploy button is now dark-ink-on-blue, not white-on-blue.** Correct by measurement (3.20 → 5.39)
  and it matches dracula/gruvbox/mist — but it is the most visible change on the branch and it has never
  been seen.
- **solarized-dark's body text was lifted twice** off base1 (+30%). It is the palette with no headroom;
  if it now reads washed, the honest fix is to drop the `surface_3` fence for it, not to re-invert the tiers.

### 2. Merge to master.
Disjoint from master's overworld work; merge is clean.

### 3. Both plans are SPENT — the phase accounting

The question *"do we still have a many-phased plan for beauty?"* has a precise answer: **no, and mostly by
design.** Eleven planned phases across two rounds; here is every one of them.

**PLAN.md — round 2, WORKSHOP, 7 phases:**

| | phase | status |
|---|---|---|
| P0 | contrast hole + the selector bug | ✅ shipped `86de3f5` |
| P1 | name the options, demote the paragraph | ✅ shipped `c1073dc` |
| P2 | button ladder **+** mono register | ◐ **split** — mono shipped `c1073dc`; **the ladder (2a) is unshipped** |
| P3 | ~~kill all 27 QGroupBoxes~~ | ✅ mechanism shipped `881e468` `0ecfa75` — **premise overruled by the user** |
| P4 | widen the dark span | ⛔ **DEAD** — verified: it reverts P0's contrast floors on all 5 dark palettes |
| P5 | radius / spacing / role hygiene | ✗ unshipped — *PLAN.md's own words: "land it silently; never bill it as beauty"* |
| P6 | the Home page | ⇢ **superseded** — SIGNET's hero did this surface instead |

**IDENTITY.md — round 3, SIGNET, 4 phases: ✅ 4 / 4 shipped.** palette `5ed0a21` · stretch fix `5ed0a21` ·
hero `11fae9e` · record `764ca74` (+ `5e61ebd`, the Ctrl-K opt-in).

**So: we are on small stuff because small stuff is all that is left — that is not drift.** Of the 7 WORKSHOP
phases, 3 shipped, 1 is dead, 1 is superseded, and the **2 remaining are explicitly labelled hygiene by the
plan that proposed them.** The round that was framed as the beauty plan produced a hygiene plan; the round
framed to commit produced SIGNET, and SIGNET is complete. See the last section for *why* that happened —
it is structural, not accidental.

Still unshipped and cheap, all hygiene:
- **Phase 2a — the button ladder**: a `role="quiet"` tier so the action row has one entry point. Spec is
  exact, incl. the `:disabled`/`:pressed` trap.
- **Phase 5 — hygiene**: 9 radii → 3, spend `space_*`.
- **`widgets.section()` interiors are still hard-coded** (16/12/16/16, `SECTION_GAP = 14`) and not tokenized.
  The dead-`space_*` finding is now *stronger*, not weaker.
- **The `QGroupBox` QSS block (`style.py`) + `$gb_margin_top`/`$gb_pad_top` are dead code** — QGroupBox is
  constructed nowhere. Sweep.

### 3b. If you want MORE beauty, it is a contract renegotiation — not a phase

There is no "make Build & Deploy beautiful" phase to run, and that is **deliberate**. SIGNET's contract
([IDENTITY.md](IDENTITY.md), *What we are NOT doing*) is:

> *identity where you look for 5 seconds, restraint where you work for 3 hours.*

Every work surface — dialogs, console, tree, inspector, toolbar, crumb row, tab strip — is neutral **on
purpose**, and the gold is confined to one corner of one band because *"one corner, once, or it's a costume."*
So extending the identity inward is not the next phase of SIGNET; it is the thing SIGNET forbids. Round 4
would have to argue the contract is wrong.

**The one genuine unresolved beauty question**, already measured and never answered, is PLAN.md's **Open
Question #2 — "what is under the lamp on Build & Deploy?"** The pages are flat type with a single accent
verb in the crumb row. That may be exactly right (*a form's focal point is its verb*). If it reads
rudderless, the honest lift is already specced and already measured: **`role="card"` + a 4px accent
left-stripe — 2.44–4.73 against `surface_2` in all 7 palettes**, the one delineation that survives the light
themes, applied to **one** element per screen and nothing else. That is the highest-value unshipped
*aesthetic* move in either plan, and it is gated on a playtest verdict, not on more research.

### 4. Known, deliberate, not bugs
- **`PROSE_W = 620`** is wide (~109 chars vs the 45–75 band). User: *"fine with 620 for the moment."*
- **The audit's chip false positive** — `audit_contrast.py` reports the breadcrumb chip as
  `#ffffff on #f4f5f7 = 1.09 INVISIBLE` in light/solarized-light. **It is fine** (filled `#2f6feb`, 847px,
  27px of white text; spot-checked). It is shown dynamically, so its geometry is stale at grab time. This is
  the tool's one known limit and its header says so. 8 of the 8 remaining findings are this.

---

## The instrument

`evidence/audit_contrast.py` — every text-bearing control, every tab, every palette. **78 → 8 distinct
findings** over this arc. Read its header before believing any output: it documents two methods that
failed (ink-counting measures antialiasing fringes; blank-and-diff reflows the layout) and the one that
works (ink from `QPalette`, background from pixels).

**The rule this arc kept re-learning, six times:** *measure the pixels — and know which pixels your harness
is lying about.* Colour is font-independent and trustworthy. Width, geometry, and anything from a
dynamically-shown widget are not. A finding derivable from the palette needs no render at all — prefer that.

## Docs

- **[CORRECTIONS.md](CORRECTIONS.md)** — ⚠ read first. The round-2 plan's headline ("kill all 27
  QGroupBoxes") was **wrong**, and this says how: it measured `surface→surface_2` (1.17) when a card is seen
  against the *page* (`bg→surface_2` = **1.31**, stronger than GitHub's dark card). The user overruled it.
- **[IDENTITY.md](IDENTITY.md)** — SIGNET: the direction, the palette + its fence table, the hero, the build
  order. Generated by a round framed to **commit**, not to refute.
- **[PLAN.md](PLAN.md)** / **[VISION.md](VISION.md)** — round 2. Carry `SUPERSEDED`/`SHIPPED` markers.
- **[CRITIC.md](CRITIC.md)** — the pass that reframed round 2. Still the best doc of the three.

## The methodological finding (the reason round 3 exists)

Round 2 ran 90 agents and produced **hygiene, not beauty** — structurally, not by accident. Its review pass
was tuned to skepticism, and **skepticism is asymmetric**: a defect has a measurement and survives review;
a decoration has only taste and dies. Every decorative proposal was refuted, each refutation individually
correct, and the sum was a plan with no positive vision.

Round 3 inverted the frame — generators had to **commit**, taste was an allowed input, and measurement's job
was to make a committed idea *work* rather than to veto it. That produced SIGNET. **A research harness
optimized to refute will converge on correctness and never on beauty.**
