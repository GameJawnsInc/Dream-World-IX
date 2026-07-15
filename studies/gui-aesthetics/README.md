# Workspace GUI, round 2 — **aesthetics**

The [gui-makeover](../gui-makeover/) study (2026-07-14) shipped 10 phases: semantic role tokens, an elevation
ladder, WCAG AA contrast, focus rings, 24px targets, screen-reader names, an SVG icon family, teaching
empty-states, disclosure drawers, motion with a reduced-motion gate. It succeeded **on its own terms** — but
every one of those phases optimized *usability*. None asked "does this look good". So finishing them did not
make the app look good, and the user's verdict after the fact was: *"the cards don't read well… I want the GUI
to be beautiful to look at. I don't have a clear vision for how to proceed."*

This round asks only the aesthetic question. Research pass 2026-07-15 — **and then shipped, which is how
its headline was found to be wrong.** See *Outcome* below; the docs carry inline `SUPERSEDED`/`SHIPPED`
markers and [CORRECTIONS.md](CORRECTIONS.md) carries the audit.

- **[STATE.md](STATE.md)** — ⚠ **START HERE.** What shipped (19 commits), the seven live defects it found,
  and the ranked next steps. Nothing in this arc has been playtested — that is step 1.
- **[IDENTITY.md](IDENTITY.md)** — **SIGNET**, round 3: the FF9 front door + the opt-in Mist climate.
  Produced by a round framed to COMMIT rather than to refute — see the last section of STATE.md for why
  that reframing was necessary and what it says about research harnesses generally.
- **[CORRECTIONS.md](CORRECTIONS.md)** — ⚠ **READ BEFORE PLAN.md.** The audit of the three round-2 docs
  against the code actually built from them (126 claims re-verified; 25 auditor verdicts overturned on
  review). The plan's headline was wrong; this says how.
- **[PLAN.md](PLAN.md)** — the deliverable: the diagnosis, the named direction + three laws, a gated first
  spike, 7 phases (P0–P6) with file:line changes / token diffs / tests / an explicit *"you'll see:"* per phase,
  a **Rejected** table, and 5 open questions with recommendations.
- **[VISION.md](VISION.md)** — the art direction (**WORKSHOP**), synthesized across the 10 lenses.
- **[CRITIC.md](CRITIC.md)** — the adversarial rebuttal. **The most load-bearing of the three**: it reframed
  the plan by catching that the vision's headline was a 27-site refactor justified by a screenshot containing
  a one-line bug.
- **[evidence/](evidence/)** — runnable proof of the headline finding:
  - `prove_radio_border.py` — the pixel proof (colour-only, so offscreen-safe). Exits non-zero if it stops reproducing.
  - `shot_builddeploy.py` — renders the real panel before/after on the **native** platform → the two PNGs below.

## Outcome — what actually happened

**Round 2 shipped, and the plan's headline lost.** Five commits on `claude/gui-card-readability-eb5d9f`:
`86de3f5` Phase 0 (the selector bug + a contrast hole in 4 palettes) · `685ba1a` `section()` + `Prose` ·
`881e468` **the card reversal** · `58f7deb` tick + dot · `0ecfa75` all 27 sites. 2884 tests pass.

Two things were settled that no amount of research could settle:

1. **The screenshot was a one-line bug** (below). Fixing it first was correct — nobody in the dossier had
   ever looked at the panel without it.
2. **The card stays.** The plan's single highest-leverage change ("kill the QGroupBox, all 27") was built,
   shown, and overruled by the user: *"the cards were nice logical section indicators, they just looked
   ugly."* The dossier reached the wrong conclusion from correct arithmetic — it measured
   `surface→surface_2` (1.168) when a card is seen against the **page**: `bg→surface_2` is **1.308** in
   DARK, *stronger* than GitHub dark's card (1.094). The fill was never the problem and was never changed.
   What was ugly: the caption **on** the border, a title with **no presence** (unfixable while Qt draws
   it — QSS ignores `font-*` on `QGroupBox::title`, which is the real reason the box had to become a
   widget), and **no horizontal padding**. All three now fixed in `widgets.section()`.

**The lesson worth keeping:** ten lenses, 74 adversarial reviews and a completeness critic all agreed on a
prescription that one sentence from the person looking at the screen overturned. The research was right
about the *defect list* and wrong about the *cure*.

## The headline

**The screenshot is a bug, not a design failure.** [`style.py:126`](../../ff9mapkit/ff9mapkit/workspace/style.py#L126)
writes the pseudo-class before the pseudo-element:

```
QCheckBox:focus::indicator, QRadioButton:focus::indicator { border: 1px solid $focus; }
```

Qt does not reject this — it degrades to an unconditional `QRadioButton, QCheckBox { border: 1px solid $focus }`.
Every radio and checkbox in the app wears a permanent accent rectangle, and radios have had **no focus ring at
all** since the rule landed (the a11y test greps selector strings, so it passes regardless). Reorder to
`::indicator:focus`. One line.

Reproduce: `py studies/gui-aesthetics/evidence/prove_radio_border.py` → an unfocused, unchecked radio paints
`#4c8dff` on **4/4** edges before, **0/4** after.

The same panel, one selector reordered, **nothing else changed**:

| before | after |
|---|---|
| ![before](evidence/builddeploy_before.png) | ![after](evidence/builddeploy_after.png) |

**Nobody in the dossier looked at the panel without those rects** — the vision's headline ("kill all 27
QGroupBoxes") was a 27-site refactor across 7 files justified by *this* image. So the plan's order was: fix
the line, re-screenshot, *then* decide whether the boxes were ever the problem.

**That gate ran, and it saved the refactor from shipping for the wrong reason.** The answer came back: the
cards were worth keeping, they were just ugly. All 27 migrated to `widgets.section()` **cards** — fill and
border untouched. See *Outcome* above.

The "after" shot also earns Step 2 on sight: with the rects gone, the blue `role="accent"` paragraph is
plainly the loudest object on the card and the least important thing on it. (It is also *sub-AA as text in 6
of 7 palettes* — the aesthetic move and the accessibility fix are the same move.)

## The diagnosis, in one line

A complete design system exists and the app doesn't use it. `role="h1"` is set by nothing; `widgets.card()`,
`heading()`, `status_chip()`, `tabular()` have **zero call sites**; `space_1/3/4/6` are dead; `font-weight: 500`
resolves to Regular (Segoe UI ships no Medium). Every mechanism that could rank things was built, tokenized,
tested — and never spent, leaving one instrument: draw a 1px rectangle around it. **A rectangle cannot rank.**

## Method

90 agents: 3 recon (tokens · containers · constraints) → 10 independent design lenses (hierarchy, typography,
colour, space, components, identity, IA, craft, benchmark, motion) → per-proposal adversarial review → vision →
completeness critic → plan. **74 proposals reviewed; all 74 returned NEEDS_REVISION** — zero survived as first
drafted. Everything in the plan is a corrected proposal; the refuted set is preserved in **Rejected** so it
isn't re-proposed.

## ⚠ Harness warning — the trap this round fell into

`QT_QPA_PLATFORM=offscreen` **stubs the Qt font database and inflates every text advance 2–3×.**

[gui-makeover/README.md](../gui-makeover/README.md) already documented this ("that gives tofu boxes") and the
lenses fell into it anyway: the widest control in the app is **642px**, not the 1503px the dossier claimed, and
at 1280px there is ~1080px of content. **There is no horizontal-scroll emergency and there never was** — every
"collapse the tab's minimum width" argument is dead, and the padding amputation at `style.py:152-153` is
defended by a bug that may never have been real at that magnitude.

The rule, stated precisely enough to be useful:

> **Measure the pixels — and know which pixels your harness is lying about.**
> **Colour** is font-independent → offscreen renders are trustworthy (this is why the radio-border proof holds).
> **Width/geometry** is font-dependent → offscreen renders are fiction. Use the native platform +
> `WA_DontShowOnScreen` recipe from [gui-makeover/README.md](../gui-makeover/README.md).

Any width assertion added to CI needs `skipif "Segoe UI" not in QFontDatabase.families()` or it locks in the artifact.

## Live bugs found en route

The first two predate this round; both are now **fixed** (`86de3f5`). The rest were found by *building*
and are recorded in [CORRECTIONS.md](CORRECTIONS.md) — notably: Qt derives a control's screen-reader name
from its enclosing **QGroupBox title**, so removing the boxes silently stripped **13 names** (restored via
`setBuddy`); `hover == surface_btn` byte-identically in NORD/DRACULA/SOLARIZED_DARK/GRUVBOX_DARK, meaning
**four palettes have no button hover feedback at all** (still unfixed); and `field == surface_btn` in three
palettes. Also: **Phase 4 is now un-landable** — it would revert Phase 0's contrast floors on all five dark
palettes.

1. **`style.py:126`** — the unconditional radio/checkbox border above; radios have never had a focus ring.
2. **`muted` on `surface_2` is sub-AA today** — 3.87–4.07 in NORD / DRACULA / SOLARIZED-DARK / GRUVBOX. Uncaught
   because the contrast test only ever checks `bg` and `surface`. Any caption placed inside a QGroupBox lands on
   this untested surface, so **the assertion ships before the captions do** (Phase 0).
