# continent-v1 — the first custom continent

A four-island archipelago composed entirely of **verbatim real-FF9 donor landmasses**, fused
into the open ocean pocket in the SW corner of the disc-1 overworld with one `world-fuse`
layout. **In-game proven 2026-07-09**: every island renders and walks; the strait between
the two fused islands is seam-free.

## Deploy

```
py -m ff9mapkit world-fuse continent_v1.toml --mod-folder FF9CustomMap --dry-run   # validate first
py -m ff9mapkit world-fuse continent_v1.toml --mod-folder FF9CustomMap             # deploy
```

Relaunch the game (or exit + re-enter the overworld) to apply — loose world assets aren't
hot-reloaded. Requires the custom engine bundle (the WorldMeshOverride patch + `Donor.txt`
donor-divert support). To remove, delete the deployed `Block[*]` files under
`<mod>\FF9_Data\WorldMap\Disc1\` rows 12–19.

## The islands

| | Donor | Target | What it is |
|---|---|---|---|
| A | (9,5) + 2×3 | cell (0,12) | The cliff/highland island — one of only two real multi-block landmasses that pass every carry gate. |
| B | (10,17) + 2×2 | cell (0,15) | The shore/shallows island — the other one. Fused directly south of A; the shared border (z=−960) is fuse-certified row-by-row. |
| C | (7,17) | cell (3,18) | A real sandy-beach island, landable on foot. `land_margin = 0` because its land legitimately reaches its own east frame edge. |
| D | (0,0) Uaho | cell (5,19) | A genuine all-cliff peak — authentically reachable only by airship or flying chocobo, FF9's own hidden-isle design language. |

First-look world coordinates (approximate cell centers, e.g. for the debug-menu teleport):
A (64,−864) · B (64,−1024) · C (224,−1184) · D (352,−1248).

## Notes

- **Empty cells deploy nothing by design.** A's NW corner cell (0,12) and B's east column
  carry no override files — the donor's land doesn't reach those cells, so they stay true
  prefab ocean and the block grid loads them untouched.
- The layout ships **no overworld entrance** (`world-entrance`) — the continent is a
  standalone explorable pocket reached by boat/airship. Wiring a door to a field is a
  separate, already-proven step once you pick a destination.
- Every placement is a byte-verbatim carry of real game data at deploy time; nothing here
  contains or generates Square-Enix bytes in the repo.
