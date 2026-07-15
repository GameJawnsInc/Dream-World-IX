<!--
The adversarial completeness critic, 2026-07-15 -- the pass that reframed the plan.
It caught (a) the offscreen font-metric artifact that invalidated every width claim in the
dossier, and (b) that the vision headline was a 27-site refactor justified by a screenshot
containing a one-line bug. Both were independently re-verified before the plan was written.
-->

I have what I need. Both load-bearing facts are confirmed, and one of them invalidates a large slice of the dossier.

---

# COMPLETENESS CRITIC — final check before ship

## 0. The finding that reframes everything: **the measurement substrate is broken**

Every lens that measured a **width** measured a lie. Verified just now:

```
Segoe UI installed (offscreen): False
resolved family: ''          <- Qt's offscreen QPA stubs the font database
rb_test label:  stub 1079px  |  real Segoe UI 489px
```

| Claim in dossier | Real | Inflation |
|---|---|---|
| rb_test 1087px | 520px | **2.09×** |
| wire_newgame 1347px | 642px | **2.10×** |
| cb_single_folder 1425px | 568px | **2.51×** |
| coopdoc cb_follow 1503px | 528px | **2.85×** |

The widest non-wrapping control in the app is **642px**, not 1503px. At the 1280px default minus the nav rail there is ~1080px of content width. **There is no horizontal-scroll emergency. There never was.** The following premises are dead:

- typography #7 "one sentence dictates the entire tab's horizontal rhythm" — false
- space #2 "cap the measure at 860" — its stated hard prerequisite doesn't exist
- space #4 / ia #1 / benchmark #3 "1107px → 420px collapse" — measuring noise
- style.py:152-153's padding amputation is defended by a bug that may never have been real at this magnitude

Two reviewers caught this independently (space #4, benchmark #3). **The synthesis ignored both** and the vision statement doesn't mention it once.

And this is where the vision's concluding meta-law is actively dangerous:

> **"Measure the pixels. Don't reason about them."**

That law is *half right, stated as if whole*. I re-ran both kinds of probe:

- **Colour** measurements are font-independent → the renders were right. The radio border **is** `#4c8dff` on an unfocused, unchecked radio. Confirmed.
- **Width** measurements are font-dependent → the renders were wrong by 2–3×, in the *alarming* direction, and every lens that "verified by rendering" verified an artifact.

The law that actually holds is narrower: **measure the pixels, and know which pixels your harness is lying about.** Ship the law as written and the next agent will trust the next fake number. Any width assertion added to CI must `skipif "Segoe UI" not in QFontDatabase.families()` or it will lock in the artifact.

---

## 1. What every lens missed

**The Home page — and it's the one the headline fix cannot touch.** Seven lenses examined Build & Deploy. The vision's single-highest-leverage change is "kill the QGroupBox, all 27." Census: builddoc 6, importdoc 10, coopdoc 3, battledoc 3, modelsdoc 3, savedoc 1, shell 1. **Home has zero.** The first surface a user sees, the one with the most room to be beautiful, is *untouched by the plan's headline*. Home is a `role="display"` QLabel on `$bg` and a stack of `QFrame#card` rows. Nobody proposed anything for it that survived.

**The screenshot as the deliverable.** The user's complaint arrived *as a still image*. The vision correctly says "don't animate — the complaint came from a still" — then never asks the obvious follow-on: **what makes a still of this app good?** Nobody examined the README shot, the GitHub social card, the first-run frame. This is a public 1.0.0b1 project. The screenshot IS the product's face and no lens looked at it.

**Nobody costed shell.py.** 9274 lines, 16925 total. `widgets.section()` requires touching 27 sites across 7 files, and the reviewer's corrected factory returns `(box, lay)` — a **different call shape** from `box = QGroupBox(t)`, so it's 27 hand-edits, not a sed. That is the whole risk of the plan and it appears in no lens's effort estimate. (Fix: make `section(title)` return a QGroupBox with `setTitle("")` + an injected overline label, so it drops in at the exact call shape. Then it genuinely is mechanical.)

**Also unexamined:** high-DPI (every custom `paintEvent` proposal — RunStrip, ChoiceCard, Panel — has a devicePixelRatio half-pixel story nobody told); the window as an object (icon exists at `workspace/dreamworldix.ico`, `setWindowIcon` at shell.py:442 — never evaluated); dialogs; the Ctrl-K palette (one lens, in passing); and **dark-vs-light parity**, which the colour lens found and then buried: LIGHT's `surface_3` is literally `#ffffff` and its rungs step 1.043. That asymmetry — *dark gets depth from tone, light gets it from a border and a gap* — is a **law**, and it's currently a footnote inside a rejected finding.

---

## 2. Where the vision is wrong or overconfident

**It buries its own answer.** The vision names "Kill the QGroupBox" as §4, THE single highest-leverage change — then lists the `style.py:126` fix as a thing that "rides along free," while simultaneously admitting *"you cannot judge any redesign until it's gone."* Both cannot be true. If the redesign is unjudgeable until 126 is fixed, then **126 is not a rider — it is step zero, and the groupbox verdict is unproven until it lands.**

I verified 126 renders a full accent-blue border on an unfocused, unchecked radio. That is three full-width blue rects in the screenshot, from one malformed selector. **Nobody in this entire dossier rendered the panel with 126 fixed and asked "is it still ugly?"** The vision's headline is a 27-site refactor justified by a screenshot that contains a one-line bug. The honest position: *fix 126, re-screenshot, then decide about the groupbox.*

**"All 27, in one pass" is the scope explosion, stated as a virtue.** The reasoning ("one borderless tab beside five boxed ones reads as unfinished") is correct *as design* and reckless *as engineering*. It converts the plan into an all-or-nothing bet on the largest change, in a 16925-line codebase, with a test suite that (verified) cannot see any of it.

**Cascadia Code is not guaranteed.** The vision leans on mono-on-ids as "the one texture in the whole composition." Cascadia ships with VS/Windows Terminal, **not with Windows**. On a clean user machine the chain silently falls to Consolas. The dev box lies about this. Either bundle it (OFL, + a pyproject package-data entry the vision doesn't mention) or say "Consolas" and mean it.

**It never names the lamp.** "Exactly one thing under the lamp" is the whole thesis, and the vision never says what the one lifted surface on Build & Deploy *is*. It rules out `builddoc.go` (correctly). It deletes the groupbox. So what's lifted? The honest answer — *nothing; the crumb-row Deploy is the only accent and the page is flat type* — may be right, but it is a different design than "one lifted surface" and the vision doesn't own the difference.

---

## 3. Conflicts, adjudicated

**A. `self.dest` — three lenses, three fates.** hierarchy #2 wants it in a lifted card; ia #2 wants it deleted; typography #3 wants it split with bold marks. **Adjudication: ia #2's diagnosis, hierarchy #2's split, neither's mechanism.** Split into a value line (`role="strong"`) + a caption. Do **not** card it (lands `surface_2` on `surface_2` = 1.00 contrast, measured). Do **not** keep `role="accent"` — verified sub-AA in 6 of 7 palettes as text. **Blocker both missed:** `_update_dest` has four branches and one of them (`rb_game`) is the app's only *no-undo* warning. The vision's own "don't grey a diagnostic" law applies and no proposal honors it.

**B. ChoiceCard vs. label+caption.** components #1 builds a QAbstractButton card; ia #3 does a short label + caption QLabel. **Adjudicate: label+caption.** ChoiceCard's reviewer measured its hover at 1.00:1 against `surface_2` — invisible — and the vision explicitly forbids nesting a card inside the surviving box. label+caption is ~10 lines, needs no paintEvent, no retheme hook, no accessibility rescue.

**C. "Author the groupbox interiors" (space #3) vs. "delete the groupbox" (vision §4).** Direct contradiction — one tunes the padding of the thing the other deletes. **Vision wins.** Drop space #3 entirely; it's tuning a corpse.

**D. Accent the primary (colour #7, components #3, benchmark #2) vs. vision's refusal.** **Vision wins, verified:** shell.py:1058-1064 already ships an `setObjectName("accent")` "Deploy F9" whose `_deploy_now` calls `self.build_deploy.on_go()` — the identical method. Accenting `builddoc.go` = two blue buttons, 100px apart, same function. `coopdoc.btn_start` is the *only* legitimate promotion (no crumb equivalent).

**E. MIST vs. Law II.** MIST's gold `$accent` + `derive()`'s `info = accent` aliasing means info/focus/accent are all gold — "one hue spent once" fails on arrival in the identity lens's own palette. **Adjudicate: MIST ships as flavour, explicitly not as the fix, and not this round.** It cannot be evaluated until the hierarchy work lands.

**F. craft #1 gradient vs. vision "don't gradient the buttons."** **Vision wins** — measured +4/255 in dark, nil in gruvbox, inverted in light. But note craft #1's corrected version (derive the edge from `border`, not `surface_btn`) gets +0.12–0.14 uniformly and is *not* refuted by the vision's numbers. Park it; don't cite the vision's rebuttal against the corrected form.

---

## 4. The real risk, plainly

1. **A half-migrated look, and the plan mandates the conditions for it.** "All 27 at once" in a 9274-line shell means a long-lived branch. Any partial landing is *worse than today's consistent dull*, and the vision says so itself.
2. **The a11y phases break silently, in the direction nobody is watching.** The tests are string greps. Verified live holes the suite cannot see: `muted`-on-`surface_2` is 3.87–4.07 (sub-AA) in NORD/DRACULA/SOLARIZED-DARK/GRUVBOX **today** — the contrast test only ever checks `bg` and `surface`. Radios have had **no focus ring at all** since 126 shipped, and `test_focus_rings_are_defined_for_keyboard_users` greps four selector strings and passes. Every caption this plan adds inside a groupbox lands on the untested surface. **Ship the missing `surface_2` assertion before any caption.**
3. **Scope explosion is the base case, not the tail.** Nine lenses × ~7 findings = ~60 proposals. Most were NEEDS_REVISION. Landing "the vision" means ~20 coordinated edits across theme.py, style.py, widgets.py, and 7 doc modules.
4. **The plan may be solving a bug.** Stated once more because it's the real risk: the screenshot's three nested rects are `style.py:126`. Nobody has looked at the panel without them.

---

## 5. The minimum that gets "yes, that's it"

The user wants to **see** progress. Four edits, one afternoon, one screenshot each. No refactor, no new file, no palette key, no test rewrite.

**Step 1 — one line. Ship it in the next 10 minutes.** `style.py:126`:
```
QCheckBox::indicator:focus, QRadioButton::indicator:focus { border: 1px solid $focus; }
QCheckBox::indicator:checked:focus, QRadioButton::indicator:checked:focus { border: 1px solid $accent_fg; }
```
Deletes three full-width blue rects from the exact image they complained about, and restores a focus ring that has never existed. **Re-screenshot and send it before doing anything else.** This is the highest impact-per-character change available and it costs nothing.

**Step 2 — the radios become names.** `"Test slot 4003"` + an 11px `role="caption"` line under it, indented 31px (measured `SE_RadioButtonContents.x()`, not the 26/28 the lenses guessed). Justify it as **type hierarchy** — *not* width. The width story is dead.

**Step 3 — demote the blue paragraph.** `self.dest` → a short value line + caption. Keep the `rb_game` no-undo warning at full weight. This removes the loudest wrong thing on the tab and fixes a real AA violation.

**Step 4 — land the `surface_2` contrast assertion** so steps 2–3 are provably legal in all 7 palettes.

That is Build & Deploy: **BUILD TO** / three named options each with a quiet line / air / actions — with **zero** borders removed. If it reads well, the groupbox verdict was never needed. If it still reads badly, *now* you know the box is the problem and the 27-site refactor has earned its risk.

**Do not** start with §4. Start with the one-liner, and let the screenshot tell you whether the vision is right.
