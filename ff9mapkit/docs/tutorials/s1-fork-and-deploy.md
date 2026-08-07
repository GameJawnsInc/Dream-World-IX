# S1 — Fork and deploy a field

```toml
[tutorial]
track = "S"
step = 1
goal = "Fork a real FF9 room, deploy it under your own id, and walk it in the game."
requires = ["game", "gui", "assets", "engine-bundle"]

[[tutorial.ui]]
label = "Suggest a test room…"
widget = "import_field.rooms_btn"

[[tutorial.ui]]
label = "Preview fidelity"
widget = "import_field.preview_btn"

[[tutorial.ui]]
label = "Import field"
widget = "import_field.import_btn"
```

By the end of this step, FINAL FANTASY IX loads a field that belongs to your mod, under your own
id, and your party walks it. Every later tutorial in the core track builds on the room made here.

The whole track works inside the **Workspace** — the desktop GUI. One thing to know up front: the
Workspace is a front-end over the same engine as the `ff9mapkit` command line — every action it
runs streams into the Output console at the bottom, and the
[CLI track](c1-cli-fork-edit-deploy.md) picks that thread up later.

**Starting from:** a set-up toolkit ([Setup](../../../SETUP.md) §1–§3). Launch the Workspace:
`ff9mapkit-workspace` (installed copy) or `py apps\ff9_workspace.pyw` (repo checkout) (the
Workspace needs the `gui` extra — if the launcher is missing, see
[Troubleshooting](../TROUBLESHOOTING.md#the-gui-wont-launch)). The in-game debug menu (`~`) used
from step 4 onward ships in the Dream World IX engine bundle — install it with
`ff9mapkit setup --install-engine <dwix-custom-memoria-*.zip>`
([ENGINE.md](../ENGINE.md#installing-the-custom-engine)). On stock Memoria, use the In-place
route in step 3 and enter the room normally.

## 1. Check setup on Home

The **Home** tab is the setup checklist. The first two rows — game install found, base templates
extracted — must show done; fix them from the Setup & Health dialog if not (the toolkit ships no
Square Enix data; templates are derived from your own install, once).

![The Workspace Home screen with the setup checklist and quick-start cards](../../../docsite/assets/shots/home-ready_light.png)

## 2. Fork a room

A *fork* copies one real FF9 screen — art, walkable floor, camera — into an editable project.

![The Assets ▸ Import tab — ① the donor field, ② Preview fidelity, ③ the fork mode, ④ Import field](../../../docsite/assets/shots/import-fork_light.png)

1. Open the **Assets ▸ Import** tab.
2. Click **Suggest a test room…** and take a suggestion — they are vetted starters (small, no
   story machinery in the way). Donor names and ids both work in the field box (①).
3. **Preview fidelity** (②) shows what the fork will and won't reproduce, before anything is
   written.
4. Leave **Fork mode** on Verbatim (③) — the truest copy — pick an output folder under
   **Write to:**, and click **Import field** (④).

The forked project opens in the left-hand tree.

## 3. Deploy

![The Build & Deploy tab with a verbatim fork open — ① In-place on the real field, ② Test slot, ③ Install to game, ④ Build only](../../../docsite/assets/shots/build-deploy_light.png)

Open **Ship ▸ Build & Deploy**. For a first fork the two routes that matter:

- **In-place on the real field** (①) — your fork replaces the donor room in-game, reachable the
  normal way. Reversible; pre-selected for a verbatim fork.
- **Test slot** (②) — a throwaway scratch id, used for the rest of the track.

Press **Deploy** (or **F9**). The Output console shows the build; the first deploy of a new id
needs one game relaunch (it registers the id) — after that, never again.

## 4. Verify in-game

In the game, press **~** (tilde) to open the debug menu → **Warp to field** → your id (an
in-place deploy needs no warp — enter the room normally).

**What you should see:** the forked room renders under your id, and the party walks the same
floor the original did. If the screen is black, the id was never registered — relaunch once, and
see [Troubleshooting](../TROUBLESHOOTING.md) for the rest.

## Next

- [S2 — Add an NPC and dialogue](s2-add-an-npc.md): put a character in the room and learn the
  edit → deploy → reload loop.
- What a fork actually carries: [fork fidelity](../FORK_FIDELITY.md).
