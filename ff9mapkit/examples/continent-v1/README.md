# continent-v1 — the first custom continent

A four-island archipelago composed of **verbatim real-FF9 donor landmasses**, fused into the
open ocean pocket in the SW corner of the disc-1 overworld with one `world-fuse` layout —
plus a **real-scale minted beach** on island B (a kit-made shore: the mesa rim sunk to a
sandy cay, a new 4-column beach minted on it). **In-game proven 2026-07-09** (every island
renders and walks; the strait between the two fused islands is seam-free) and **2026-07-11**
(the minted beach + its lip-anchored cliff walls). A fifth, fully **synthetic grassland
island E** (a `world-island` mint, below) joined the archipelago as the interior-topography
canvas — **in-game proven 2026-07-12** (renders fully, the whole cliff loop walkable, the
meadows read right).

## Deploy

```
py -m ff9mapkit world-fuse continent_v1.toml --mod-folder FF9CustomMap-world --dry-run   # validate first
py -m ff9mapkit world-fuse continent_v1.toml --mod-folder FF9CustomMap-world             # deploy
py -m ff9mapkit world-island --mod-folder FF9CustomMap-world --center 344,-1152 --radius 46 --lobes 3 --seed 55   # island E
py -m ff9mapkit world-minimap --mod-folder FF9CustomMap-world                            # refresh the big map
```

Relaunch the game (or exit + re-enter the overworld) to apply — loose world assets aren't
hot-reloaded. Requires the custom engine bundle (the WorldMeshOverride patch + `Donor.txt`
donor-divert support). To remove, delete the deployed `Block[*]` files under
`<mod>\FF9_Data\WorldMap\Disc1\` rows 12–19.

> **Why a dedicated mod folder?** Campaign/journey deploys wholesale-replace their target
> folder — keeping the overworld in its own stacked `FolderNames` entry (here
> `FF9CustomMap-world`, auto-registered by Memoria on launch) means no campaign deploy can
> ever wipe it. Any stacked folder works; the engine searches them all for loose meshes.

## The islands

| | Donor | Target | What it is |
|---|---|---|---|
| A | (9,5) + 2×3 | cell (0,12) | The cliff/highland island — one of only two real multi-block landmasses that pass every carry gate. |
| B | (10,17) + 2×2 | cell (0,15) | The shore/shallows island — the other one. Fused directly south of A; the shared border (z=−960) is fuse-certified row-by-row. Carries the layout's `[placement.bank_lower]` + `[placement.virgin_mint]` shore tweaks: a minted beach on the (10,18) block's south rim, world ~(670,−1168) donor frame / ~(30,−1040) in place. |
| C | (7,17) | cell (3,18) | A real sandy-beach island, landable on foot. `land_margin = 0` because its land legitimately reaches its own east frame edge. Also the mint's `pins_from` reference — island B's foam/sand language is byte-read from here. |
| D | (0,0) Uaho | cell (5,19) | A genuine all-cliff peak — authentically reachable only by airship or flying chocobo, FF9's own hidden-isle design language. |
| E | *synthetic* | cells (4–5, 17–18) + (6,18) | The grassland island — a fully kit-synthesized ~112×114u lobed landmass (`world-island`, seed 55): native grass mains, two verbatim meadow stamps, rolling relief, the ~73° rock rim. The **interior-topography canvas** — now carrying a carried canopy FOREST (west lobe), two meadows, and a real-language grass HILL (south lobe). Its footprint deliberately skips block (6,17) — a REAL sea-skirt block (the open-ocean target law, now a `world-island` gate). |
| F | *synthetic* | cell (3,17) | The terrace islet — a compact patchless `world-island` mint (r26, seed 15) carrying the first synthesized **interior TERRACE**: a topo-13 grass mid-shelf at ~17u ringed by three stacked topo-49 rock-wall courses in the decoded band language. Between C and E. Regenerate: `world-island --center 224,-1120 --radius 26 --seed 15 --lobes 1 --patches 0` + `studies/overworld-topography/terrace_build.py deploy`. |

First-look world coordinates (approximate cell centers, e.g. for the debug-menu teleport):
A (64,−864) · B (64,−1024) · C (224,−1184) · D (352,−1248) · E (344,−1152).

## Notes

- **Empty cells deploy nothing by design.** A's NW corner cell (0,12) and B's east column
  carry no override files — the donor's land doesn't reach those cells, so they stay true
  prefab ocean and the block grid loads them untouched.
- **The shore tweaks are declarative and reproducible**: coordinates are donor-world
  coordinates, each verb's block derives from them, the mint composes on the bank
  automatically, and tweaked placements rebuild fresh for the gate pass and the deploy pass
  — re-running the layout over an existing deploy changes zero bytes. Delete the two
  sub-tables to get the original all-verbatim island B.
- The layout ships **no overworld entrance** (`world-entrance`) — the continent is a
  standalone explorable pocket reached by boat/airship. Wiring a door to a field is a
  separate, already-proven step once you pick a destination.
- Every placement is a byte-verbatim carry of real game data at deploy time (the shore
  tweaks re-derive from those bytes offline); nothing here contains or generates
  Square-Enix bytes in the repo.
