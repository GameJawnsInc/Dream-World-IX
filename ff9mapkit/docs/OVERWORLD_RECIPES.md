# Overworld recipes — the proven command sequences

The overworld pillar's working recipes, lifted from the shipped
[`examples/continent-v1`](../examples/continent-v1/README.md) build. Read the
`authoring-ff9-overworld` guardrails first if you are editing coasts or anything
under a spawn — bad geometry under the player bricks the save silently.

All of these need the custom engine bundle (the `WorldMeshOverride` patch); the
overworld lives in its own stacked mod folder (`FF9CustomMap-world`) so campaign
deploys cannot wipe it.

## Apply loop (~1 second, no relaunch)

Geometry edits apply via the world-scene rebuild — press `~ → World → "Reload
overworld on state"`, or exit to any field and return. The rebuild re-reads every
loose `.ff9mesh` override from disk (playtest-proven 2026-08-04; `Memoria.log`
prints a `[WorldMeshOverride] loaded` line per block each time). RELAUNCH only
for: a new DictionaryPatch/BattlePatch line, a `Memoria.ini` FolderNames change,
or an engine DLL rebuild.

## A continent from real coast pieces (the flagship path)

```bash
py -m ff9mapkit world-fuse continent_v1.toml --mod-folder FF9CustomMap-world --dry-run
```

```bash
py -m ff9mapkit world-fuse continent_v1.toml --mod-folder FF9CustomMap-world
```

```bash
py -m ff9mapkit world-minimap --mod-folder FF9CustomMap-world
```

Validate first (`--dry-run`), deploy, then refresh the big map. A desert (or any
second ground) on a carried mass is the one-command ground-retile carry:

```bash
py -m ff9mapkit world-transplant --mod-folder FF9CustomMap-world --ground desert
```

## A real river on a new island

`world-river` carries a stock river whole onto open ocean: its banks, its bridge,
the beached cove it runs into and the island in that cove, every byte as the game
ships it. A kit island is minted round them, joined at the two cliff columns and
knitted to the open sea across the cove's mouth. Check first, then deploy:

```bash
py -m ff9mapkit world-river --mod-folder FF9CustomMap-world --at auto --dry-run
```

```bash
py -m ff9mapkit world-river --mod-folder FF9CustomMap-world --at 512,128
```

`--at` is a translation in world units, with no rotation, and it moves whole 64u
blocks. `512,128` is the placement played in game; `--at auto` picks the nearest
open-ocean spot that no folder in the stack already overrides. Write a negative
offset with `=`, as in `--at=-1024,0`.

The dry run runs every gate, the written-bytes audit included: it writes the island
to a temporary folder outside the install, audits it there and deletes it. A real
run deploys exactly those audited bytes through the same ledgered, backed-up write
as every other world verb, then mirrors them to disc 4. It refuses rather than
overwrite, and names the gate: `T0`/`T1` (the placement), `B1` (a target cell is
not open ocean, or a stacked folder already overrides it), `W1` (the water seam),
and the geometry gates `J1`-`J4` and `G1`-`G6`. To place it somewhere else, deploy
again at a new `--at`.

To take a river back out, or to redeploy it at the same spot, remove it first with
the placement the deploy printed:

```bash
py -m ff9mapkit world-river --mod-folder FF9CustomMap-world --at 512,128 --remove
```

`--remove` deletes only files whose bytes the folder's deploy ledger says `world-river`
wrote on those cells at that placement, on disc 1 and the disc-4 mirror. It parks each
one beside itself as `<name>.bak-<time>` first. It is all or nothing. A hand edit,
another verb's file, or another placement's file on those cells refuses `R1`, and
nothing is removed. Cells that hold nothing refuse `R0`. Other folders in the stack
are never touched, and the next deploy still refuses them. Add `--dry-run` to list
what would go. Then run the ordinary command again to redeploy.

v1 ships one river, `cluster-c`, the lowland river and its cove (`ff9mapkit
world-donors --class river`). Its source ends in open lawn, and the verb warns and
prints where. In the original map every river rises at the foot of the mountain or
escarpment it was born at. This one was born at the continent's escarpment, which the
kit cannot carry. Don't put a `world-mountain` at the source: it is not the original
map's form, and it will not seat that close to the banks. Leave the lawn as it is: a
`world-forest` canopy does not fit on this narrow island either. Afterwards refresh the big
map with `ff9mapkit world-minimap`. To look before the game does, deploy into an
absolute scratch folder (`--mod-folder C:/path/to/scratch`) and render it with
`world-render --mod-root` (below).

A river can also be one row of a `world-fuse` recipe. It runs the same pipeline as the
command, so it writes the same bytes:

```toml
[[river]]
donor = "cluster-c"   # the default
at = [512, 128]       # "auto" only with --dry-run: copy the placement it prints into at
apron = true          # the default; area = N as --area
```

The row belongs to the first tier, with `[[island]]`, so a later `[[mountain]]`,
`[[forest]]` or `[[hill]]` row reads the island it minted. The relief verbs read and
write across the world's x seam (between columns 23 and 0), where the 512,128 island
sits, so the default `reach` works there. A dry run deploys nothing, so a relief row aimed at
the river island fails there and says why. A river row never builds over another
deploy, `--allow-overwrite` or not. To re-run a recipe, take its river out first with
`world-river --remove --at DX,DZ`: the ledger records that the rows came from
`world-river`'s pipeline, so the removal owns them although `world-fuse` wrote them.

## Interior relief on a deployed island

```bash
py -m ff9mapkit world-mountain --mod-folder FF9CustomMap-world --target-disc 9
```

`world-forest` / `world-hill` follow the same shape. All three carve the DEPLOYED
island (they read the override tree), gate on the placement census, and refuse
rather than deploy a stranding. An island across the world's seam (between columns
23 and 0) reads whole, so a carve can stand on the seam. The printed centre is
always inside the world (x 0..1535), ready to teleport to or copy into a recipe.

## Reshape stock ground (hills, craters, ridges)

```bash
py -m ff9mapkit world-terrain --mod-folder FF9CustomMap-world --at 396 -478 --radius 10 --raise 6
```

RESHAPE, never OVERLAY — displacing existing verts keeps a single walkable
surface. On a synthetic world add `--target-disc 9` (keep `--disc` at its
default: the read moves to the deployed override only when the discs differ).

## See what you deployed without launching the game

```bash
py -m ff9mapkit world-render --around 396,-478
```

Engine-faithful offline stills (UNLIT, NEAREST, alpha-0=white) from derived
cameras: one top-down, four ~60° close views, four low waterline grazes, one
overview. A clean render is a regression harness, not an oracle — the blind-spot
ledger prints with every run.

To render a build that never went into the game, point `--mod-root` at its
folder (laid out like a mod folder, `FF9_Data/WorldMap/...`), and add `--stock`
to fill in the real map around it:

```bash
py -m ff9mapkit world-render --mod-root path/to/build --around 1586,-955 --disc 1 --stock
```

A site across the world's seam (the edge between columns 23 and 0) renders whole:
give `--around` a point past x 1536 and the columns beyond wrap to the right files.
