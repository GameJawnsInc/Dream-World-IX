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

## Interior relief on a deployed island

```bash
py -m ff9mapkit world-mountain --mod-folder FF9CustomMap-world --target-disc 9
```

`world-forest` / `world-hill` follow the same shape. All three carve the DEPLOYED
island (they read the override tree), gate on the placement census, and refuse
rather than deploy a stranding.

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
