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
| `7eaf343` | **The hero writes in `$text`** — defects #8 and #9; the NINTH-GROUND LAW |
| `eb44b96` `9b7d8c6` | **INTAGLIO** (round 4) — one light, from above: four edge tokens, the button ladder finally renders, wells are cut, the console gets a lit lip |

## INTAGLIO — the material (round 4's first build)

**The app was never flat-and-minimal, it was unfinished, and there is a number for it: in LIGHT,
`surface_btn` and `surface` are THE SAME HEX.** A button's fill is 1.0000 against its page.
solarized-dark's `field` IS `surface`. mist's button-in-a-card is 1.0017. The elevation ladder claims a
light source ("higher = lighter") and never drew the light.

**THE RULE:** a control is **RAISED** (lit on top); a container of content is **CUT** (the exact inverse).
Raised and cut are the same two colours in opposite order — that inversion is what makes it read as one
light source rather than as trim on unrelated widgets.

**Anchored on `$border`, never the fill.** Fill-anchored, LIGHT gets d5 on a card — a no-op in the two
palettes that need it most. Border-anchored the carrier lands **d26–d34 in all 8**. And it needs **no
`if dark:`**: `$border` is the app's one already-mode-aware token — above its fill in all 6 dark palettes,
below it in both light ones, 8/8 — so each palette's own border eats the edge it cannot hold.
**Fenced**, because it holds only by convention and a ninth palette that broke it would light every object
upside down rather than fail.

**`EDGE_T = 0.14`, and the render chose it.** At the proposed 0.18 the non-carrier reaches d13–d17 and
five palettes grow a second visible edge — two edges on a raised rectangle is a bevel, and a bevel is
Windows 95. At 0.14 no quiet edge exceeds d13 while the carrier stays 3–4× the fill deltas it replaces.
The ceiling is fenced so the taste call cannot silently decay.

**The rule the accent taught, which was not in the proposal:** *emit both edges only where one of them is
quiet; emit one where neither is.* `$border` is a desaturated grey and has a quiet edge. `$accent` is
**saturated and has none** — dark's `#4c8dff` has B=255, so mixing toward black drops B by 36 while
mixing toward white cannot move it at all (nord: carrier 24 / quiet 22, a symmetric bevel on the loudest
object on screen). So the primary takes a lit top only. Premise and consequence both fenced.

**Not done, deliberately:** the spec's *"kill the bottom radius — a hole in a plate has no rounded floor."*
Rendered first: the wells are inset 8px inside a panel above a `QStatusBar` that draws its own border-top.
The metaphor assumes the hole reaches the plate's **edge**; this one doesn't. Flush would butt the well's
1px lit foot against the status bar's 1px border. **A spec written without the geometry in front of it
does not get to overrule the geometry** — same call as Phase 5's splitter docs.

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

### CONTRAST IS NOT THE INSTRUMENT FOR A TINT (REGISTER P1 — the sharpest finding in round 4)

> **A contrast ratio is luminance-only. It is blind to the axis a coloured fill actually uses.**

The tree's selected row painted the **full accent** — the same fill as the primary CTA, on a *persistent*
selection. Replacing it with the tinted `selection_bg` looked fatal by the numbers: **hover out-contrasts
the new selection in four palettes** (gruvbox 1.488 vs 1.294, nord 1.327 vs 1.161, dracula, sol-dark).

Rendered at 4× with a real synthetic hover, gruvbox's selection **wins decisively** — because hover is a
pure *lightness* step (ΔHue ≤2.5°, ΔSat ≈0) while a selection is a *hue/chroma* event (ΔSat up to +0.42,
ΔHue up to 93.8°). The ratio cannot see the thing doing the work.

**But the render also refused to rubber-stamp the argument.** Nord came back *marginal*, honestly so: its
accent is nearly its own surface's hue, so a fixed 16% tint of a thing into a near-copy of itself barely
moves — 11/255 from its own hover, with the rail carrying it alone.

**So the ground and the metric both changed.** A selected row is never confused with the *page*; it is
confused with **hover**. `_selection_token` now raises the tint until the fill is ≥20/255 from that
palette's own hover, as a raw channel distance. **The floor is calibrated to the two renders, not chosen**
— gruvbox reads and sits at 26, nord didn't and sat at 11 — and the metric then independently reproduces
both verdicts: it leaves gruvbox/dark/solarized-light untouched and lifts nord to 0.50. An earlier solve
against *contrast* was discarded for over-tinting gruvbox, which the eye says needs nothing.

**The transferable rule:** when a fence and a render disagree, the render is not automatically right
either — it tells you the fence is measuring the wrong axis. Then go find the axis.

### THE CUT LIST IS PER-FAMILY (REGISTER P2)

NAMEPLATE P1 measured Segoe UI's real weight cuts — `[100-300][350][400-500][550-650][700-800][900]` —
and fenced them. **That list is Segoe's, and the console is not Segoe.** Measured natively:

| face | 550 | 600 |
|---|---|---|
| **Cascadia Code** (dev boxes; ships with VS / Windows Terminal) | a real SemiBold | SemiBold |
| **Consolas** (the clean-Windows fallback; Regular + Bold only) | **byte-identical to 400 — a no-op** | Bold |

So the log's head/echo register is **600**, the first weight that lands heavier in *both* — otherwise it
would silently flatten on exactly the machines without a developer's fonts installed. And note the
advance test that caught Segoe's dead 500 is **blind** here: mono advances never move, only the ink does.

### A SOURCE-GREPPING FENCE MUST READ CODE, NOT PROSE

Three fences in this arc tripped on their **own docstrings** — because the prose beside a rule is exactly
where the rule gets *named*. A docstring saying *"never appendHtml"* fails a naive
`"appendHtml" not in src` on the very file that obeys it. `LedeCard`'s docstring states the gold-stripe
law and failed the gold-stripe fence. `tests/_code_only()` now strips docstrings and comments via
`ast.unparse`; what's left is what executes.

### AND THE BUG THE SOURCE-GREPPING FENCES COULDN'T SEE

The log's `trace` branch called `derive()`, which **was not imported into shell.py**. Every source fence
passed. The whole 3569-test suite passed. The first traceback the console ever streamed would have
crashed the drain. **A probe that DROVE the branch found it in one run.** Reading source proves what the
code says; only running it proves what it does.

### The instrument, and the two that lied first

`audit_contrast.py` **cannot see the hero at all** — it reads ink from `w.palette().color(...)`, a QLabel
API, and the band is 100% `QPainter` with no QLabel children. The front door is invisible to the
instrument **by construction**. Two replacements failed before one worked:

| method | why it lied |
|---|---|
| **model the ground** (bg → gradient → bloom) | needs `_axis()`'s geometry to be right. Applied the bloom at full alpha 40 where the render says ~32. **Wrong by a full point.** |
| **mode of a row strip** | the ground is a *gradient* — hundreds of near-identical colours, few px each — while the ink is **one flat colour**. So the mode returns the ground for a SHORT string and **the ink itself** for a long one. It scored the status line at **1.00 against "ground" == muted** and looked plausible. |
| ✅ **render twice, suppress `drawText`, read the ground under the glyphs** | exact. Legal *only* because the band is paint-only with no layout, so the reflow objection that killed blank-and-diff for the QSS audit does not apply here. |

### THE COMMENT-PLACEHOLDER LAW (it bit twice; a comment could not hold it)

> **`string.Template` has no concept of a CSS comment.** A `$name` inside `/* */` still substitutes — and
> KeyErrors every palette at import the moment that token is renamed or removed. A bare `$` is worse: an
> Invalid-placeholder **ValueError** at import.

It broke the build in Phase 5 (`$gb_margin_top` in a comment explaining the deleted token), then **again**
in INTAGLIO P2 (`$well` in a comment explaining the rejected token) — *after* the file had grown a comment
saying never to do it. So it is now `test_no_placeholder_hides_in_a_qss_comment`, and the fence
immediately found **11 live instances**: comments that had been shipping with their token names silently
replaced by hex values, so the generated sheet's own commentary was lying about itself.

**The transferable bit:** a law that only lives in a comment gets broken by the next person writing a
comment. If a rule can be checked, check it.

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

---

## Round 5 — the type floor. And a claim of mine that was false.

**SHIPPED: QUARTO P1 + RUBRIC.** The hint rung 11 -> 12, the body 13 -> 14 (paid for with `tb_space`
6 -> 4), the `forms_qt.py:98` pin 16 -> 18, and `role="cardtitle"` so a card's title stops being the
size and colour of its own footnotes. 3583 tests. **Still unplaytested, like everything since Mist.**

### THE SIMULATED-MECHANISM LAW (the one worth carrying out of this round)

I told the user, and then briefed 23 agents as GROUND TRUTH, that *"every hard-coded QSS px is deaf to
the Windows accessibility text-size slider"* — a WCAG 1.4.4 defect. **It is false, and the research pass
killed it:**

- The slider writes `HKCU\...\Accessibility\TextScaleFactor`. It does **not** touch
  `NONCLIENTMETRICS.lfMessageFont`, which is where Qt reads its font. (Set the key to 150, broadcast
  `WM_SETTINGCHANGE`, `lfMessageFont` stays at −12 Segoe UI.)
- `TextScaleFactor` appears in **0 of 338 Qt DLLs**. **Qt cannot see that slider. No Qt app can.**
- The app *already* honours Display->Scale correctly — QSS px are logical px, multiplied by dpr.

**The mechanism of the error, which is the durable part.** My probe `probe_os_text_scale.py` *simulated*
the slider with `app.setFont()` and never checked that the slider does that. It carried a control, the
control **passed**, and it still measured nothing — because the control validated the PLUMBING while the
PREMISE went untested. This study already had the law *"a probe whose control fails is measuring
nothing."* Round 5 mints its complement:

> **A PASSING CONTROL LICENSES THE INSTRUMENT, NOT THE PREMISE.** Before simulating a mechanism, prove
> the mechanism exists. A control can only tell you your measurement is sound; it can never tell you
> that you are measuring the right thing.

The same error, twice more in the same probe:
- **`em` does not work.** Qt QSS `font-size` takes only px and pt; `em`/`ex`/`%` are **silently
  discarded** and fall back to the inherited size. My probe reported "qss_em TRACKS x1.50" — it was
  `inherit` under another name, and **the disproof was in my own output**: the em row read 15.94/23.94,
  *byte-identical* to the inherit row, when 1.1em should have been 10% larger at both ends. My verdict
  function only asked "did it grow", so a fallback read as a success. **Assert the DISTINGUISHING value,
  not the direction of travel.**
- **"offscreen forces Fusion while the app runs windows11" is HALF FALSE** and had been repeated across
  this study for rounds. `shell.py:129 _apply_app_theme` calls `app.setStyle("fusion")` deliberately
  ("the one built-in style that fully honours stylesheets"). **The app runs Fusion.** Offscreen's Fusion
  is *correct*; only its stubbed font DB lies. A bare probe `QApplication` left on the platform default
  is the thing rendering chrome the app never ships — **`app.setStyle("fusion")` in every shot.**

The honest accessibility position: **the app resizes fine. It lacks a text-only lever, and on Windows
the only lever that can exist is one we ship.** That is CALIBRE (user-selected, queued).

### What I also got wrong, in the same direction

I claimed the hint tier "runs at 116 chars/line". **That is the CAP's capacity, not what anything
renders at** — the same mistake `test_the_caption_measure_is_unchanged_on_purpose` makes. The 3 real
`option()` captions average **61 chars, inside the band**. But the pass found the real defect I had
walked past: **`option()` is 3 of 38 caption sites.** The other ~35 are raw `QLabel` + `setWordWrap`
with **no cap at all**, growing 1:1 with the window — **125 chars at 1280px, 257 at 1920, 388 at 2560**.
That is COLUMN, un-chosen, and it is the bigger half of "the hints are hard to read".

### Verified and durable

- **The hint tier's problem was ONLY size.** Contrast passes AA in all 8 palettes (`muted` worst 4.59
  in light; `error_text` worst 4.87 in solarized-light). And **growing text can never loosen a contrast
  requirement** — every rung except `name` is below WCAG's 24px large-text threshold, so 4.5:1 applies
  before and after. `theme.derive()` reads no font size at all.
- **The toolbar budget is now SPENT.** 13px = 15/15 at 1280. 14px naive = **14/15** (a button in Qt's
  hidden chevron — the exact bug `style.py`'s QToolBar comment guards). 14px + `tb_space` 4 = 15/15.
  **15px = 13/15 and tightening does NOT recover it.** Any future body bump must find another payer.
  → `evidence/probe_toolbar_budget.py`
- **The ramp is not a scale**: 26/16/15/13/12/11 has five different ratios, and h2->h3 is a **6.7%
  cap-height step** — a tier Segoe cannot draw. The size analogue of the PER-FAMILY CUT LIST law. QUARTO
  P2 (merge h2+h3 into one `type_head`) is un-chosen and still open.
- **8 sizes ship, not 6** — including a **10px** header at `shell.py:6630`. The declared ramp is not the
  shipped one.
- **`h3`'s docstring is a lie**: it says "a sub-h2 section title"; **zero** h3 sites nest under an h2.
- **A real bug, un-chosen (DICTION):** `forms_qt.py:265` **destroys** a field's help text on a parse
  error and only restores it when the value parses. The teaching vanishes exactly when the user is
  failing.
- **The `<` footgun**, if LEADING is ever taken: `'ids < 4003 are real'` renders as `'ids '`. Silent
  truncation, no error, in an app whose whole subject is field ids.
- **THE COMMENT-PLACEHOLDER LAW BIT A FOURTH TIME**, in this very round, while writing RUBRIC's comment
  *about* tokens. It fires precisely when you explain a token in prose. The fence caught all three.

### The instrument note

`evidence/shot_quarto.py` renders ONE state; `shot_quarto_ab` stashes and re-runs it in a fresh process.
That indirection is not ceremony: the first cut faked the "before" by patching the stylesheet, which was
**structurally impossible** for RUBRIC — its change is in *Python* (`widgets.section` picks the role and
drops the `.upper()`). No QSS patch can reproduce the old widget. **The only faithful before is the old
code, run as the old code.** The anchor guard refusing to render a dishonest shot is what surfaced it.

---

## Round 5, part 2 — QUARTO P3 + CALIBRE shipped; PUNCH FALSIFIED by its own condition

**SHIPPED:** QUARTO P3 (one `_TYPE` table, gated byte-identical on effective CSS 16/16) and **CALIBRE**
(Preferences -> Text size 100/110/125/150%, live + persisted + Cancel-reverts). 3591 tests.

**NOT shipped: PUNCH.** It was user-selected, built up to the render, and the render killed it. That is
the FORM LESSON doing its job, not a wasted round — *statistics reproduce a thing's measured properties
and never its look*, and PUNCH's axis was **measured and real**:

- The six-cut optical family IS installed and IS a genuine axis (x/px: Segoe .500 · Sitka Small .503 ·
  Text .477 · Subheading .462 · Heading .449 · Display .439 · Banner .430), each cut itself
  scale-invariant — so the axis lives ACROSS the family: you pick the cut for the size.
- **And the app already spends it correctly at the top.** The 40px wordmark wears Sitka Banner (the most
  extreme display cut); the 26px crown wears Sitka Display. "Spends only 2 of 6" was true and was never
  a defect — those are the right 2 for those sizes. The display end was already done.
- **P1 (tracking) buys nothing an eye can see.** Rendered at 1x and at 3x nearest-neighbour: the crown at
  0 / −0.25 / −0.50 measures 153.56 / 150.06 / 146.56px — a 3.5px change on a 153px word. Sitka Display
  is *already drawn tight*; tightening reveals no flaw, it just narrows. The hint at +0.15/+0.30/+0.50 is
  noise at best and stretches the app's worst-measure tier at worst.
- **P2 (a small optical cut for captions) dies on arithmetic:** Sitka Small buys **+0.5% x-height for
  +17.9% width**. A small optical cut exists to give MORE x-height at small sizes — but Segoe UI is
  already a UI face drawn for exactly that job at 0.500 vs Sitka Small's 0.503. It buys nothing it was
  chosen for. **`test_only_the_nameplate_wears_the_serif` was RIGHT and stays.**

### What PUNCH did produce (all durable, all recorded in `style._TYPE`'s comment)

- **THE RAMP IS NOT OPTICALLY LINEAR.** `_TYPE`'s numbers are NOMINAL px; the eye reads x-height and the
  faces differ. The crown's true size over the body is **1.63×**, not the 1.86× its numbers imply.
- **My brief's FACT 2 ("x-height scales exactly linearly") is corrected**: true WITHIN Segoe, false across
  the shipped ramp. Its `name 26px -> x 13.00` row was **Segoe 26 — the fallback**, not the face the
  nameplate wears.
- **A live, unlooked-for finding: QUARTO P1 quietly demoted the crown.** Optical dominance moves INVERSELY
  with the body while the crown's own number never changes — body 13 -> 14 took the nameplate from 1.76×
  to 1.63×, and nobody noticed because 26 stayed 26. Left as-is (the user approved the result live), but
  any future round that moves `type_body` is also moving the crown.
- **QSS `letter-spacing` works exactly** (±0.500px/char, to the hundredth) and is spent on 1 QSS rule
  (`overline`) plus `hero._WORD_TRACK = 0.5` in QPainter, which the sheet cannot see.

### THE INSTRUMENT LESSONS OF THIS ROUND (three, and they rhyme)

All three are the same error as [the simulated-mechanism law](#) one layer down — **asserting a condition
without checking it took**:

1. **`resize(1280)` is a REQUEST.** On a 1920 screen the window ignored it, so `probe_toolbar_budget`
   printed "@1280" while measuring 1920. Now: `setFixedWidth` + **assert `win.width() == width`**.
2. **A baseline that reads the current code is not a baseline.** That probe's `"body 14, naive"` case
   passed `tb_space=None`, inheriting whatever SHIPS — so once QUARTO P1 shipped `tb_space` 4, "naive"
   silently meant *"with the fix already applied"*, and the probe appeared to **refute the claim it
   existed to prove**. Pin every condition explicitly.
3. Those two **cancelled into a confident, self-consistent, wrong table** that nearly made me revert a
   correct change. Re-measured at a real asserted 1280, QUARTO P1's receipt stands exactly as committed:
   body 14 + `tb_space` 6 = 14/15, `tb_space` 4 buys it back to 15/15, body 15 recovers at neither.

Also corrected, repo-wide: **"offscreen forces Fusion while the app runs windows11" is HALF FALSE.**
`shell.py:129` calls `setStyle("fusion")` deliberately — **the app runs Fusion**. Offscreen's Fusion is
CORRECT; only its stubbed font DB lies. Every shot/probe now calls `app.setStyle("fusion")`, because a
bare probe QApplication on the platform default is the thing rendering chrome the app never ships.

### CALIBRE's measured price, not hidden

The toolbar chevrons at 1280: **15/15 at 100% · 14/15 at 110% · 13/15 at 125% · 11/15 at 150%**; 15/15 at
1600+. Chevroned items stay reachable (and Ctrl-K reaches everything), and the a11y suite already fences
graceful overflow. Recorded in `prefs.TEXT_SCALES`. **The hero band does not scale** — QPainter at hard px,
no stylesheet reaches it. That is PLINTH, unbuilt, and at 150% the front door stays put while the app
grows around it.

**Live-confirmed this round:** the user has now seen QUARTO P1 + RUBRIC in the running app — *"fonts look
much better"*. That is the first live judgement since Mist. CALIBRE + P3 are **not** yet playtested.

---

## Round 5, part 3 — PLINTH: the front door measures itself

**SHIPPED.** The band tracks the text-size dial, and its two private faces joined the ramp. 3596 tests.

- **The wiring already existed and was inert.** `shell._apply_text_scale` was ALREADY calling
  `self._hero.set_density(...)` on every scale change — and `set_density` read only `_METRICS[density]`,
  so the scale was dropped on the floor. The call site even carried a comment saying PLINTH was unbuilt
  and "the dial deliberately does not touch it". One argument closed it.
- **The 100% tuples are the DESIGN, not a derivation.** `band_metrics(d, 100)` returns the shipped tuple
  **identically** (asserted `==`, not "within a pixel"). 106.5 and 94.5 are half-pixel rule positions
  chosen by eye against a 40px serif; re-deriving them from `QFontMetricsF` would swap a composition for
  an average — and the regression would be indistinguishable from an improvement, since both arrive as
  "the numbers changed slightly". So this SCALES the design. Every other scale is that same composition,
  larger: band 156 → 172 → 195 → 234, wordmark 40 → 44 → 50 → 60, verified through the real dial.
- **The ramp-join** (the other half): the band kept private 11px/13px faces, so after QUARTO P1 raised the
  caption floor to 12, **the hero was the only surface in the app still shipping 11px text** — the front
  door wearing exactly the small type the user asked us to fix everywhere else. Now `type_caption` /
  `type_body`. Rendered as an isolated delta with the geometry frozen (`plinth_ramp_*.png`) and it reads
  as **almost nothing**, which is the correct outcome. The WORDMARK deliberately does not join: 40px
  Sitka Banner is a brand constant, type chosen as a drawing rather than as a tier. It scales; it never
  tiers, and a fence asserts it is not equal to any rung.
- **THE INVARIANT THAT WAS TRUE BY TASTE.** `signet_elbow`'s docstring promised the mark "can never
  overflow the column". "Bound to `adv`" binds the arm to the **wordmark**; nothing bound the wordmark to
  the **column**. At 100% it never mattered (~300px against a 604–860px column) — but PLINTH grows the arm
  with the dial while the column does not, so a scaled band in a narrow window would run the mark out of
  its own composition. Now `min(adv, col)`: structural, not lucky. **An invariant a new feature can
  falsify was never an invariant** — and this one had shipped, documented, for three rounds.
- **Fenced at the source, not per-number:** `test_the_hero_holds_no_private_type_sizes` walks the AST and
  refuses any `setPixelSize(<literal>)` in the module. Reads code, not prose — this module's comments are
  full of "11px" and would pass a naive grep vacuously. The ramp fences assert the RELATIONSHIP (`==
  type_px("type_caption")`), never the values 12/14, because pinning values passes happily while the ramp
  moves away underneath them, which is the exact bug being closed.
- The overflow fence carries a **self-invalidation guard**: it asserts the wordmark at max scale really
  does outrun the narrowest column, so it fails loudly if it ever stops testing anything rather than
  passing vacuously.

**Still open:** GAUGE — `PROSE_W` is a fixed 420px, so the measure decays as the type grows.
(⚠ The numbers first written here — "61.9ch at 100%, 41.3 at 150%, below the 45 floor" — are WRONG, from a
synthetic rate. Measured on the app's real prose it is 67.6–71.9ch at 100% and **45.0 at 150%: ON the
floor, not below it.** See part 4 below; the defect is real but it is not this.)

---

## Round 5, part 4 — GAUGE. And the measure was never the defect.

**SHIPPED**, but for a reason nobody predicted — and the numbers going in were wrong three times.

### The measure's real history (native, `evidence/probe_measure_rate.py`)

| claim | source | verdict |
|---|---|---|
| 61.9 ch | my alphabet probe | **wrong** — synthetic rate, ~9% off |
| 77.5 ch | round 5's audit | **was true**, at the 13px body |
| 41.3 ch @150%, "below the floor" | me, told to the user | **wrong** — it is 45.0, ON the floor |
| **67.6–71.9 ch** | the app's real strings @ 14px | measured |

**My instrument lied and I published it.** `'abcdefghijklmnopqrstuvwxyz '` has ONE space in 27; English has
~1 in 6, and the space is the narrowest glyph in the face. A synthetic rate overstates px/char, which
understates the measure. **A rate measured on the alphabet is a measurement of the alphabet, not of prose.**

**And QUARTO P1 fixed the real defect by accident.** At 13px the Build & Deploy crown note ran 77.5ch —
over the band. At 14px it runs 71.9 — inside it. **Raising the body NARROWS the measure in characters**,
because every character got wider. The type bump the user asked for closed the case GAUGE was chartered for.

### So GAUGE shipped for the reason that survived: nothing could TELL

The measure held at every dial setting **by luck** (45.0ch at 150%, zero headroom), and the fence could not
have noticed if it stopped: it divided `PROSE_W` by `WORST_13PX = 5.72` — **a constant over a constant, a
rate from a font size the app no longer sets.** It passed at 150% exactly as happily as at 100%, and would
have kept passing with the cap welded to 420 forever.

### The mechanism: scale, don't re-derive (PLINTH's move again)

Segoe's advance is **LINEAR in px** (12→28px, max error 0.065%), so `chars = (cap·k)/(rate·k) = cap/rate`
— **the character count is INVARIANT under scaling.** Proven end-to-end on the real string through the real
dial: **71.9ch at 100 / 110 / 125 / 150%**, flat; `cap/px` exactly 30.00 at every rung.

Re-deriving from a "characters" target would need a calibrated rate, and every honest candidate misses 420:
`averageCharWidth()` reads 5.953 at 13px, **above every real string in the app** (5.42–5.89), because it
averages a glyph set nobody types. **Scaling needs no rate at all.**

`Prose` reads its OWN polished font (`changeEvent` → `FontChange`) rather than being told the scale — so it
is right no matter who changed the type. A cap threaded from the shell would be a second source of truth
for the same fact, and the two would drift the first time one was missed.

### THE OFFSCREEN LIE, THIRD INSTANCE — and this one wrote a PASSING FENCE FOR A BROKEN FEATURE

**`QFontInfo(...).pixelSize()` returns `-1` under `QT_QPA_PLATFORM=offscreen`**, even for a font with an
explicit `setPixelSize(21)` — offscreen stubs the font engine QFontInfo consults. A QFontInfo-only
`_resolve_cap` hit its `k=1.0` guard in *every* test, held the cap at 420 forever, and **the fence written
to catch exactly that failure reported it as a pass.** Fixed by asking `QFont.pixelSize()` first (explicit,
survives the stub) and falling back to `QFontInfo` (resolves a point-size font — the Windows system font is
Segoe 9pt and reports `-1`, which would multiply every cap by a negative). Neither source alone suffices.

The standing warning "offscreen lies about the font DB" was already here. What is new: **it lies to your
fences, in the direction of green.**

### Corrected en route

`test_the_caption_measure_is_unchanged_on_purpose` laundered an approval (620 was approved for PROSE at
13px, then inherited onto the 11px caption where the same number is strictly worse) *and* cited evidence
describing 1 of its 3 strings. Rewritten to say what is true — and to name the real caption defect:
`option()` is 3 of ~38 sites; **the other ~35 are raw QLabels with NO cap, growing 1:1 with the window**
(125ch at 1280 → 388 at 2560). That is COLUMN, unbuilt, and now the largest un-taken readability win here.

**The user cleared ALL standing playtest debt before this landed** (CALIBRE, QUARTO P3, the badge bump, the
spine cut, PLINTH — all validated live). GAUGE itself is unplaytested, though invisible at 100% by
construction.
