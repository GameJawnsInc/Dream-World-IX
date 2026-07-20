# 06 — One field in the Workspace

The GUI version of [tutorial 01](01-first-fork.md): fork a real field, edit it in forms, and
deploy — all inside the Workspace window.

**Prerequisites:** the `gui` extra (`pip install ff9mapkit[gui]`) and UnityPy (`assets` extra).
Launch:

- installed copy: **`ff9mapkit-workspace`** (also the Start-Menu shortcut),
- repo checkout: `py apps\ff9_workspace.pyw`.

If the toolbar's Setup & Health banner reports missing pieces (game not found, templates not
extracted), fix them from that dialog first.

## 1. Fork a field

1. Open the **Import** tab.
2. In **Fork a real field**, type a donor name or use **Find…** (or **Suggest a test room…** for
   a vetted starter). A background thumbnail previews the pick.
3. **Preview fidelity** runs the offline fork report; **Study logic…** opens the donor's decoded
   script with the story-beat roster slider — both before anything is written.
4. Pick a **Fork mode** (verbatim = most faithful; see [FORK_FIDELITY.md](../FORK_FIDELITY.md)),
   choose an output directory, and click **Import field**.

The forked project opens in the left-hand tree.

## 2. Edit

Select the field node → the **Editor** tab shows its forms (Field, NPCs, Gateways, Events,
Dialogue, Music, …). Add an NPC, set its `pos` inside the walkmesh (the Inspector shows the field
art and bounds), give it a dialogue line — the wrap preview renders the line in FF9's real window
geometry. **Ctrl-S** saves; Problems (bottom console) shows lint findings live.

## 3. Build & deploy

Open the **Build & Deploy** tab. Under **Build to (field)** choose:

- **In-place on field N** — appears only for a **verbatim fork of a real field** (its
  `[verbatim_eb] donor` is a base-game id). Deploys under the donor's own id so the engine loads your
  fork *instead of* the real field — reach it the normal way (or ~ → Warp N). This is the route that
  keeps engine behaviour hardcoded on the real id, most notably the **Chocobo Hot & Cold HUD** (a
  forest fork of 2950/2951/2952 must go in-place, or the dig game plays with no HUD chrome). Reversible;
  it's pre-selected for a fork of a real field.
- **Test slot** — the fast dev loop (repo checkout + the engine bundle's debug menu; grayed out on an
  installed copy unless `FF9_REPO` points at a checkout). **F9** does save-all + deploy in one
  keystroke. Deploys under a throwaway scratch id — good for a novel field, but a fork loses its real
  id here (use In-place instead).
- **Install to game (shipping mod folder)** — builds and installs into the game's mod folder.
- **Build only — to a folder** — a distributable mod folder; **Package (zip)…** wraps it for
  sharing.

Under **New Game entry**, **Point New Game here** lands New Game on the field (the stock-engine
route). Then launch and verify: field renders, NPC talks.

## Next

- The multi-arc GUI flow (fork whole regions, journeys, one-click deploy): [07 — Fork FF9 in the Workspace](07-gui-journey.md)
- The CLI equivalents of everything above: [01](01-first-fork.md) + [02](02-dev-loop.md)
