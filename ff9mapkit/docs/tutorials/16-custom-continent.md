# 16 — A custom continent on the overworld

```toml
[tutorial]
track = "D"
goal = "Deploy a proven four-island archipelago onto the world map, walk it, and iterate on it with the one-second reload loop."
requires = ["game", "engine-bundle"]
```

This puts new land on FF9's overworld: a four-island archipelago of **verbatim real-FF9
landmasses** fused into an open ocean pocket, plus a fully synthetic fifth island. The whole
build is the shipped, in-game-proven example
[`examples/continent-v1`](../../examples/continent-v1/continent_v1.toml) — this walkthrough
deploys it, verifies it in-game, and then shows the verbs that iterate on it. The mechanism:
per-block loose mesh overrides in a mod folder, composed from a declarative layout file — the
repo never contains Square-Enix bytes; every placement is carried from your own install at
deploy time.

**Prerequisites:** the Dream World IX engine bundle ([ENGINE.md](../ENGINE.md)) — the overworld
override patch lives there; stock Memoria ignores the deployed files. Plus the kit's `assets`
extra (the carries read your install).

## 0. One safety rule before anything

Overworld geometry is the one place in the kit where a bad deploy can **brick a save silently**
(a black screen with no log) — and the brick is baked into the save file, so deleting the bad
geometry does not fix an already-parked save. The shipped layout deploys into empty ocean far
from anywhere the game puts you, so this walkthrough is safe — but adopt the working practice
now, before experimenting:

- **Keep a safe save in a field or town**, not on the world map near anything you edit.
- **Never save while parked on land you just changed.** Teleport in, look, teleport out.
- If a save does brick: load the field save, or New Game.

The deeper guardrails live at the top of [OVERWORLD_RECIPES.md](../OVERWORLD_RECIPES.md) and in
the coast-law references it names — required reading before editing coasts, optional for
deploying this example as-is.

## 1. Validate, deploy, refresh the map

From the repo root (or anywhere, with the kit installed):

```bash
py -m ff9mapkit world-fuse ff9mapkit/examples/continent-v1/continent_v1.toml --mod-folder FF9CustomMap-world --dry-run
```

`--dry-run` runs every offline gate — seam welds, placement census, water-carry checks — and
writes nothing. A clean report is the go signal; then deploy, add the synthetic island, and
draw the new land onto the in-game world map:

```bash
py -m ff9mapkit world-fuse ff9mapkit/examples/continent-v1/continent_v1.toml --mod-folder FF9CustomMap-world
```

```bash
py -m ff9mapkit world-island --mod-folder FF9CustomMap-world --center 344,-1152 --radius 46 --lobes 3 --seed 55
```

```bash
py -m ff9mapkit world-minimap --mod-folder FF9CustomMap-world
```

The overworld gets its **own mod folder** (`FF9CustomMap-world`, stacked alongside your field
mods) for one standing reason: campaign deploys wholesale-replace their target folder, and a
dedicated stacked entry means no campaign deploy can ever wipe the continent.

## 2. See it in-game

**Relaunch once** — the fresh mod folder registers at launch. Then load a save with world-map
access (or any save plus the debug menu) and press **~ → World → teleport**. First-look world
coordinates, straight from the example's README: island A `(64,-864)` · B `(64,-1024)` ·
C `(224,-1184)` · D `(352,-1248)` · E `(344,-1152)`.

**What you should see:** each island renders and walks. A is cliffed highland; B is shore and
shallows, fused seam-free against A across their strait; C is a sandy beach island landable on
foot; D is an all-cliff peak reachable only by airship or flying chocobo — FF9's own
hidden-isle design language, carried verbatim; E is the synthetic grassland island, its whole
cliff rim walkable. Opening the world map shows the archipelago drawn in the SW ocean.

## 3. The one-second iteration loop

After the first relaunch, geometry edits need no relaunch at all: redeploy, then
**~ → World → "Reload overworld on state"** (or exit to any field and return) — the world scene
rebuilds from the loose files on disk. A relaunch is only for a new mod-folder registration, a
DictionaryPatch/BattlePatch line, or an engine rebuild. Disc 4 has its own asset tree, and the
kit mirrors every override there automatically — custom land does not vanish late-game.

## 4. Iterate — the verbs that work on deployed land

Each of these operates on the deployed continent, runs its own offline gates first, and
**refuses rather than deploys a stranding**:

- **Interior relief** — carve a real rock massif, a canopy forest, or a rolling grass hill into
  a deployed island:

  ```bash
  py -m ff9mapkit world-mountain --mod-folder FF9CustomMap-world --target-disc 9
  ```

  (`world-forest` and `world-hill` follow the same shape.)
- **A second ground** — the one-command desert retile on a carried mass:

  ```bash
  py -m ff9mapkit world-transplant --mod-folder FF9CustomMap-world --ground desert
  ```

- **Reshape stock ground** — hills, craters, ridges, by displacing the real verts:

  ```bash
  py -m ff9mapkit world-terrain --mod-folder FF9CustomMap-world --at 396 -478 --radius 10 --raise 6
  ```

  The standing law here: **reshape, never overlay.** Displacing existing verts keeps one
  walkable surface; a new mesh laid over intact ground is never walkable — decoration only.
- **Look without launching** — engine-faithful offline stills of the deployed bytes:

  ```bash
  py -m ff9mapkit world-render --around 396,-478
  ```

## 5. Removing it

The deploy is loose files only: delete the deployed `Block[*]` files under
`<mod folder>\FF9_Data\WorldMap\Disc1\` (this layout's rows 12–19) and reload. The real map
underneath was never touched.

Two scope notes: the layout ships **no overworld entrance** — the continent is a standalone
explorable pocket reached by boat or airship (`world-entrance` wires a door to a field once you
pick a destination). And editing **coasts, beaches, or cliffs** — as opposed to deploying and
iterating inland as above — is governed by a body of in-game-proven laws; read the guardrails
in [OVERWORLD_RECIPES.md](../OVERWORLD_RECIPES.md) before starting there.

## Next

- The example's [README](../../examples/continent-v1/README.md) — what each island is, donor by
  donor, and the shore-mint tweaks in the layout file.
- [OVERWORLD_RECIPES.md](../OVERWORLD_RECIPES.md) — the proven command sequences this page
  walks, plus their guardrails.
- [OVERWORLD_ENGINE.md](../OVERWORLD_ENGINE.md) — the engine model underneath: dispatchers,
  vehicles, encounters, entrances.
