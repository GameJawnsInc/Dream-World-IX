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
| `53d2ed9` | **Phase 2a** — the quiet button tier; the action row gets an entry point; coop's Start becomes the accent |
| `cbc0eb0` `7bb91d8` | **Phase 5** — nine radii → three tokens + three geometric pins; one card language; the dead QGroupBox block; the grid gets an int rung and the form docs stop each inventing a page frame |

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

8. **The hero's overline inked in `text_subtle`** — 2.5:1, sub-AA in **8 of 8**, on the front door. The
   Rejected table forbids that token for text *in writing*; PLAN.md's Phase 6 spec prescribed `muted`.
   **The implementation drifted from its own spec inside one round** (found by the round-4 workflow).
9. **The hero's status line inked in `muted`** — sub-AA in **3 of 8** (light 3.63, sol-light 3.98,
   dracula 4.35). Found only by measuring #8 properly. Nobody had ever measured it.

**The pattern:** 4, 5, 6 and 7 were all *fences set at the wrong bar, green the whole time.* A fence that
covers 3 of 4 grounds just moves the bug to the 4th.

### THE NINTH-GROUND LAW (from #8 and #9 — durable)

> **Every text tier is fenced against the elevation ramp. A surface that paints itself off the ramp
> voids every one of those fences, silently.**

The mist bloom composites `$text` over the plate and lifts the ground **past `surface_3` in 7 of 8
palettes**. `muted` clears 4.5 on `surface_3` in all 8 (4.57–5.70) and **still fails on that band**
(overline 4.09–4.79, status 3.63–5.37) because it is fenced to sit *at* the floor and has no headroom for
a lifted ground. It cannot acquire any: swept `_MIST_ALPHA` to **zero** and it still only reaches 4.72.
**There is no alpha that makes a dim tier legal on the mist.**

So the hero writes **everything in `$text`** (overline 5.16–12.34, status 4.64–10.85, 8/8), and
subordination comes from **type** — PLAN.md's own law, written before the band existed. The render
confirms it: the 28px serif wordmark still dominates an 11px tracked overline in the same ink.

**Corollary for any future painted surface:** if you invent a ground, you owe it a fence. The ramp's
guarantees stop at the ramp.

### The instrument, and the two that lied first

`audit_contrast.py` **cannot see the hero at all** — it reads ink from `w.palette().color(...)`, a QLabel
API, and the band is 100% `QPainter` with no QLabel children. The front door is invisible to the
instrument **by construction**. Two replacements failed before one worked:

| method | why it lied |
|---|---|
| **model the ground** (bg → gradient → bloom) | needs `_axis()`'s geometry to be right. Applied the bloom at full alpha 40 where the render says ~32. **Wrong by a full point.** |
| **mode of a row strip** | the ground is a *gradient* — hundreds of near-identical colours, few px each — while the ink is **one flat colour**. So the mode returns the ground for a SHORT string and **the ink itself** for a long one. It scored the status line at **1.00 against "ground" == muted** and looked plausible. |
| ✅ **render twice, suppress `drawText`, read the ground under the glyphs** | exact. Legal *only* because the band is paint-only with no layout, so the reflow objection that killed blank-and-diff for the QSS audit does not apply here. |

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
- **The 24px page frame** (Phase 5) is the one deliberately VISIBLE thing in an otherwise silent phase.
  It is a ratio, not a taste: `section()` insets content by 16, so a 16px page frame put each card's
  border exactly halfway between the page edge and its own content — cards stop reading as *on* a page.
  If it now reads loose, `widgets.PAGE_PAD` is one number in one place.
- **Co-op's Start is now the accent** and Package/Disable are unfilled. Verified by probe rather than by
  eye (Start inks `accent_fg` `#181b20`, Disable inks full `$text`, Stop greys to `$muted` when disabled)
  — but *seen* only in an offscreen grab.

### 2. Merge to master.
Disjoint from master's overworld work; merge is clean.

### 3. Both plans are now SPENT — the phase accounting

The question *"do we still have a many-phased plan for beauty?"* has a precise answer: **no, and mostly by
design.** Eleven planned phases across two rounds; here is every one of them. **All eleven are now closed.**

**PLAN.md — round 2, WORKSHOP, 7 phases:**

| | phase | status |
|---|---|---|
| P0 | contrast hole + the selector bug | ✅ shipped `86de3f5` |
| P1 | name the options, demote the paragraph | ✅ shipped `c1073dc` |
| P2 | button ladder **+** mono register | ✅ mono `c1073dc`; **the ladder `53d2ed9`** |
| P3 | ~~kill all 27 QGroupBoxes~~ | ✅ mechanism shipped `881e468` `0ecfa75` — **premise overruled by the user** |
| P4 | widen the dark span | ⛔ **DEAD** — verified: it reverts P0's contrast floors on all 5 dark palettes |
| P5 | radius / spacing / role hygiene | ✅ `cbc0eb0` (radius + roles) `7bb91d8` (the grid) |
| P6 | the Home page | ⇢ **superseded** — SIGNET's hero did this surface instead |

**IDENTITY.md — round 3, SIGNET, 4 phases: ✅ 4 / 4 shipped.** palette `5ed0a21` · stretch fix `5ed0a21` ·
hero `11fae9e` · record `764ca74` (+ `5e61ebd`, the Ctrl-K opt-in).

**So: the small stuff was all that was left — that was not drift.** Of the 7 WORKSHOP phases, 5 shipped,
1 is dead, 1 is superseded. The round framed as the beauty plan produced a hygiene plan; the round framed
to commit produced SIGNET. See the last section for *why* — it is structural, not accidental.

**What Phase 5 found by trying to SPEND the grid rather than read it** (the pattern holds: a fence, or a
constant, that covers most of the app just moves the bug to the rest):
- **`SECTION_GAP` existed, was documented, and had exactly ONE consumer.** Build and Import each hardcoded
  `12` next to a comment calling it "4pt-grid rhythm". Co-op's page frame was an asymmetric `18/14/18/18`
  that nothing explained.
- **Nine radii** (3/4/5/6/7/8/9/10/11). `#search` and `#railSeg` wore a `7px` rung that existed nowhere
  else — a value nobody could have chosen deliberately.
- **A comment the card reversal falsified**: Co-op's gap was annotated *"the box borders are gone — this
  gap IS the grouping now"*. The borders came back.
- **`string.Template` has no concept of a CSS comment.** Naming a dead token as `$name` inside `/* */`
  still substitutes (KeyError); a bare `$` is an Invalid-placeholder ValueError that takes down every
  palette at import. Both broke the build *while the comment warning about them was being written.*

**One spec claim was wrong and was not followed:** PLAN.md prescribed the 24px page frame for **all six**
docs. Models and Battle are **splitter browsers** — their panes *are* the page, edge-to-edge is the
convention, and an outer margin only eats pane width. Only the three **form docs** (one scrolling column
of cards: Build & Deploy / Import / Co-op) take the page rung. The fence says so.

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
- **The quiet tier is SUBTLE in the two light palettes.** A quiet button is `transparent` (so it shows
  `$bg`); a default button is `$surface_btn`. That delta measures **1.215–1.382 in the six dark palettes**
  but only **1.105 in light and 1.066 in solarized-light**. The *mechanism* is right everywhere (fill vs
  no fill) and the magnitude is bounded by light's compressed surface ramp — the same wall PLAN.md's
  Rejected table already hit ("LIGHT's `surface_3` is `#ffffff` and its rungs step 1.046/1.043. Dies
  there."). Not fenced on a ratio, because a ratio fence would fail light and the honest fix isn't a
  number. Worth a look in light before deciding it needs anything.
- **`PROSE_W = 620`** is wide (~109 chars vs the 45–75 band). User: *"fine with 620 for the moment."*
- **`SECTION_GAP = 14` is deliberately OFF-GRID** — the one number in `widgets.py` that is. Its grid
  neighbours are 12 (too close to the 8px in-card row gap to read as a different *kind* of gap) and 16
  (ties the card's own interior padding). The grid does not have to own every number; it has to stop
  numbers being anonymous.
- **`page_margins()` is comfortable-only.** The docs are constructed without knowing the density, so
  layout density fan-out is a separate job (it needs `_apply_density` **and** `_finish`'s Cancel path, or
  QSS reverts while layouts stay at the previewed density). `style.space()` already takes a density.
- **The audit's chip false positive** — `audit_contrast.py` reports the breadcrumb chip as
  `#ffffff on #f4f5f7 = 1.09 INVISIBLE` in light/solarized-light. **It is fine** (filled `#2f6feb`, 847px,
  27px of white text; spot-checked). It is shown dynamically, so its geometry is stale at grab time. This is
  the tool's one known limit and its header says so. 8 of the 8 remaining findings are this.

---

## The instruments

`evidence/audit_contrast.py` — every text-bearing control, every tab, every palette. **78 → 8 distinct
findings** over this arc. Read its header before believing any output: it documents two methods that
failed (ink-counting measures antialiasing fringes; blank-and-diff reflows the layout) and the one that
works (ink from `QPalette`, background from pixels).

`evidence/shot_ladder.py` — the action row + page frame, rendered on the **native** platform, with the
quiet rules stripped in the A/B so it varies exactly one thing. It is honest about what it *cannot*
isolate: the button order and the page frame are Python, so both shots share the new layout.

**The eye failed here and the pixels did not — again.** The flat/ranked shots looked *identical* to me at
a glance; sampling the Package button's interior showed `#2b3038` (the default fill) vs `#1e2127` (the
page). A 1.215 delta is real and legible in situ, and invisible in a downscaled review. Sample the
button, don't squint at the screenshot.

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
