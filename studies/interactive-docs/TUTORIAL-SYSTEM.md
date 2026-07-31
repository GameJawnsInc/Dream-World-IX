# The tutorial system — the binding contract for the revamp

The owner is revamping the tutorial set wholesale. This file is the contract the revamp authors
against — the source format, the gates that keep a rewritten tutorial from rotting, and the jobs
that feed them. Sibling of PLAN.md (the arc's status) — this file owns the tutorial format only.

## The idea in one line

A tutorial's three volatile ingredients — **screenshots, UI names, commands** — each get a
machine-checked tie to the real toolkit, so the prose can be rewritten freely while the facts in
it cannot silently go stale.

| Ingredient | Tie to truth | Job (local, Windows+Qt) | Gate (CI-safe, Qt-free) |
|---|---|---|---|
| Figures | rendered by the headless Workspace | `py docsite/shots.py --all` / `--check` | manifest↔assets↔pages integrity tests |
| UI names in prose | harvested label inventory | `py docsite/uiharvest.py` / `--check` | `[[tutorial.ui]]` declarations verified at build |
| Commands | the real argparse tree | — (fully offline) | every `ff9mapkit` line in every shell fence verb+flag-checked at build |

## Source format

Tutorials stay **plain markdown** in `ff9mapkit/docs/tutorials/` (canonical, GitHub-browsable —
the one-copy law). Three conventions on top, all degrading gracefully on GitHub:

1. **Frontmatter** — the first ```toml fence opening with `[tutorial]` (TOML, never YAML — the
   frontmatter-truncation trap). GitHub shows it as an informative code block; the site strips it
   and renders a goal line + requirement chips under the title.

   ```
   [tutorial]
   goal = "One sentence: what the reader will have built."
   requires = ["game", "gui"]     # game, templates, gui, assets, engine-bundle, blender, repo
   ```

2. **UI declarations** — every control the prose names in **bold** gets a `[[tutorial.ui]]`
   entry: `label` (the exact rendered string) + `widget` (the attr path — the same vocabulary
   shots.toml callouts use). The build fails when: the widget is gone from the inventory, the
   label no longer matches its real text/a11y/placeholder, or the label never appears in the
   prose. Renames become build errors pointing at the exact tutorial — never silent rot, and
   never silent auto-rewrite either (a label swap mid-sentence is a human's edit to make).

3. **Figures** — plain image links into `docsite/assets/shots/<name>_light.png`, declared in
   `shots.toml` with `used_by` back-pointing. GitHub renders the light PNG; the site upgrades to
   the theme pair + SVG callouts from the sidecar.

Commands go in `bash` fences exactly as runnable; the build validates each `ff9mapkit` line's
verb and flags against `cli.build_parser()` (72 lines across the current corpus, all clean).
Placeholder lines (`<...>`) verb-check only. A fence tagged `text` is exempt (for deliberately
hypothetical shapes).

Template to start from: `docsite/templates/tutorial.md`. House shape: goal-first title, numbered
acts, **every act ends with a "what you should see" verification step**, offline checks before
in-game ones, honest about which is which (offline ≠ in-game proof).

## The inventory

`docsite/assets/ui-inventory.json` (committed) — per surface, per attr-path: kind + the nameable
strings (button/radio/checkbox/groupbox text, a11y name, placeholder; mnemonic `&` stripped;
value-carrying widgets contribute a11y/placeholder only, never their value). Harvested from the
same pinned fixtures as shots. `--check` diffs a fresh harvest against the committed file — run
it (and shots `--check`) after any Workspace change; the site build then names every tutorial
whose declared labels no longer hold.

Coverage today: the six ribbon-tab docs + seven dialogs (new-field, new-campaign, new-journey,
fork-regions, import-fields, setup, prefs) — 220 controls. **Dialogs hold no attr paths** (their
widgets are built from locals), so dialog controls are LABEL-keyed (a11y name preferred, else
text — the `_child_named` handle gui_snap already drives dialogs by), declarations scope to the
dialog (`widget = "dlg:new-journey"`), and shot pins/annotations on dialogs address controls by
label with an optional `kind = "QLineEdit"` disambiguator (a dir row's edit and Browse button
share a caption by design — `_dir_row` now sets both accessible names, which was also a real
a11y gap). The New Journey figure ships pinned and ready for the rewritten 07 to embed.

**The gate's boundary, stated:** the inventory records controls that exist, INCLUDING ones
hidden in a surface's default state (the New Journey "Pick FF9 regions…" button lives under the
Multi-campaign Type — a one-state screenshot once mis-called it removed). So the gate proves
existence + spelling, never state-reachability; a step's "click X after choosing Y" ordering is
the author's claim, verified by the figure of that state, not by the inventory.

## What the revamp does per tutorial

1. Copy the template; write the prose freely.
2. Declare every bolded control; `py docsite/build.py` — fix what the gates name.
3. Figures: add `[shot.*]` entries (new pinned states go into gui_snap first — it stays the one
   owner of surface pins), `py docsite/shots.py <names>`, embed the `_light.png` links.
4. `py -m pytest docsite/tests -q` — the integrity suite ties manifest, assets, and pages.

## Not built yet (deliberate)

- **Runnable fences** (rung 3): execute offline-safe command blocks against a scratch project at
  build time and embed transcripts. The command gate above already kills the typo/stale-flag
  class corpus-wide; execution adds semantic proof and stays a local ratchet (needs templates).
- **Label styling**: rendering declared labels as UI chips in prose (pure presentation; the
  gates don't need it).
- **Generated tutorials index** from frontmatter (order/requirements table) — nav lists them
  fine meanwhile.
