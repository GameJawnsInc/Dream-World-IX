# The Menu Shape-Language Study

**Opened 2026-07-21.** The prerequisite for the Folklore codex screen redesign (s45 Phase B follow-up).

## Why

The Phase B codex screen reached FUNCTIONAL over **16 playtest rounds** — every round paid for a mechanical
law (now `project-ff9-ngui-menu-construction` in project memory), but the *look* converged by trial and
error because we had no vocabulary for how stock FF9 menus compose. The user's call, verbatim:

> let's get a good shape language first, then design our menu. the way we're going about it now isn't good
> for discoverability

The NGUI laws answer *"how do I make a cloned piece behave?"* This study answers *"which pieces does stock
FF9 use, and how do they combine?"* — so the redesigned screen can be written as a sentence in the stock
language instead of debugged into one.

## Method

Multi-agent census over the Memoria engine source (`C:\gd\FFIX\Memoria\Assembly-CSharp`) — the baked NGUI
scenes are unreadable directly, but the source encodes the anatomy three ways: each `*UI` class's
scene-accessor bindings (`GetChild` paths = the baked hierarchy), the Memoria **widescreen relayout pass**
(`UpdateUserInterface` + the `Memoria/Scenes` `GO*` wrappers — explicit runtime geometry, the truest
record), and imperative code (SetRawRect / depth writes / `DisplayWindowBackground` sweeps / tweens).

- **10 screen readers:** MainMenu · Item (the user's reference) · Ability · Equip · Status · Config ·
  SaveLoad · Shop · **Chocograph** and **Card** (the two stock collection screens — the codex's cousins).
- **3 shared-machinery lanes:** the `GO*` wrapper shape inventory · UIScene/pointer/atlas chrome (incl. the
  dressing sprite names) · Memoria's own `MenuUIControlPanel`/`Control*` runtime-panel precedent + the
  Dialog frame grammar.
- **Synthesis** into the vocabulary, then **adversarial verification**: every load-bearing claim
  source-checked by a skeptic before it enters the document.

## Deliverables

- [`VOCABULARY.md`](VOCABULARY.md) — ★ **LANDED 2026-07-21**: the shape inventory (the window-weight
  ladder, the scrollable-list compound, the row/cell grammar, the pointer/help/dialog chrome), composition
  rules (the group ladder, the depth-stack recipe, the window-color law), the geometry-grammar table, the
  motion grammar (tween + SFX vocabulary), the 10-screen diff matrix, and 4 codex composition options
  (recommended: the **Chocograph sentence** — stock's own collection screen: browse list + persistent
  hover-populated detail + silhouette undiscovered slots). 18 claims skeptic-verified: 15 confirmed,
  3 refuted-and-corrected; 1 census conflict settled by direct grep. Raw census: [`census.json`](census.json).
- The Folklore screen redesign proposal (user-approved before building) — owns the two open Phase B
  defects: the ~3s first-open clone-burst hang, and row 1 overlapping the top rail.

→ `studies/folklore-codex/SUBMENU.md` (the Phase B record), `project-ff9-ngui-menu-construction` (the
mechanical laws this study composes with).
