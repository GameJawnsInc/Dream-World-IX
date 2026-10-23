# The 3D view draws the whole FolderNames stack

**Status:** built and in-game proven 2026-10-23 (`20261023-113717-stack-lab`, all predictions held). Owner request
after A1: "make the 3D view draw the whole FolderNames stack, the way the game resolves each file."

## The engine's rule (read from source)

From `Memoria/World/WorldMeshOverride.cs` and `Global/Asset/AssetManager.cs`:
- **The search order:** `AssetManager.FolderHighToLow` is `Memoria.ini`'s `FolderNames` in order, then `""` (the
  base game).
- **Three independent lookups per block, each over that order, first holder wins:**
  - each mesh part (`TryLoad`);
  - the divert's land check (`HasLandOverride`: a Terrain file in ANY folder);
  - the donor sidecar (`TryReadDonorPath`: the first folder holding a `Donor.txt`).
  So the Terrain may come from one folder and the donor from another.
- **A file the engine cannot read does not fall through.** `TryLoad` logs `failed to read` and returns null, and the
  engine keeps the STOCK mesh, not the next folder's file. `ReadMesh` refuses on:
  - bad magic, a version other than 1;
  - `vcount` outside 1..65535, `icount` outside 0..3*vcount;
  - a body shorter than its header declares.

## What changed

- **`world/render.py`:**
  - `RenderSite.stack` (folder roots, highest first) and `game_stack(game)`, which reads `FolderNames`;
  - `resolve_file`; `live_path` and `effective_prefab` now resolve through the roots (the land check and
    `Donor.txt` independently);
  - `engine_read_error` mirrors ReadMesh's checks, and `cell_meshes` draws a refused file the engine's way (stock)
    and reports it (`bad=`, `sources=`);
  - `load_batches` lists each folder's directory once per load instead of statting per part per folder per cell.
  - **Proven unchanged:** a site with no `stack` resolves exactly as before. The committed `render.py` and the new
    one load identical batches for the V-shore bench and for disc 1 whole, with and without stock.
- **`world/pointinfo.py`:** the owners come from the same resolution the view drew. It names every refused file ("the
  game refuses X's Terrain (reason) and draws stock here") and every folder the view resolves through that is
  missing from `FolderNames`.
- **The World tab:** the 3D page draws **As the game loads it** by default. **Only this folder** previews a folder the
  game does not load (C1's scratch folder). Its caption names the order it drew, e.g. "FF9CustomMap ›
  FF9CustomMap-world › MoguriMain › … › stock", and warns when the picked folder is not in `FolderNames`. The chooser
  sits on the 3D page's own bar: in the head row it clipped the wrapped scan summary at 150% (snap-caught).

Today only `FF9CustomMap-world` holds world files, so the stacked view and the one-folder view draw the same map
(287,319 triangles, 5.5 s). The rule matters the moment a second folder (a lab, a campaign, someone else's mod) holds
a block.

## In game (registered in `stack_lab.py build` before the install)

Two lab folders went FIRST in `FolderNames`, `FF9CustomMap-lab-hi` then `FF9CustomMap-lab-lo`, for one harness session.
The ini was backed up to `backups/Memoria.ini.20261023-113718.stack-lab`, restored byte-exact afterwards, and both labs
moved out of the install.

| case | what the lab holds there | predicted y (stacked site) | wrong rule's y | game y | log |
|---|---|---|---|---|---|
| A, stock land (3,12) | lab-lo stock +1.5, lab-hi stock +3.0 | 4.392 | 2.892 (lab-lo) | **4.391** | loaded from lab-hi |
| B, stock land (5,9) | lab-lo stock +1.5, lab-hi the same stamped version 2 | 16.790 (stock) | 18.290 (fall through) | **16.789** | lab-hi: "failed to read … unsupported version 2" |
| C, FF9CustomMap-world island (0,12) | lab-hi that island's Terrain +1.5 | 4.709 | 3.209 (-world alone) | **4.707** | loaded from lab-hi |
| K, Landing Site (control) | nothing | 4.286 | | **4.285** | |

Every case lies 1.5u from its wrong rule, ten times the 0.15 tolerance, so the read-back could only match one rule.
All four matched the stacked prediction within 0.002u.

## Tests

- **`tests/test_world_render_stack.py`** (14):
  - the first holder wins, per file; the order is the rule;
  - a refused top file hides the good one below it;
  - `engine_read_error`, case by case (magic, version, no vertices, too many vertices, too many indices, short);
  - the divert takes Terrain from any folder and the donor from the first;
  - one folder as a stack equals the one-folder site;
  - the listing scope answers as the disk does, and never leaks;
  - `game_stack`; an empty stack is stock everywhere.
- **`tests/test_world_pointinfo.py`:** plus the refused-file case (stock, not the next folder).
- **`tests/test_worldview3d.py`:** plus the default stack caption, a folder missing from `FolderNames`, the
  one-folder mode, and the unreadable-ini fallback.
- **Mutations:** resolve from the lowest folder (3 red); never refuse a file (8 red).
- **Found by the tests on the way:** a file sits five folders under its root, not six (a wrong `parents[6]` in
  `pointinfo` too), and an empty stack crashed `live_path`.

## Not here

The x-torus wrap; forms (`Terrain2`/`Object2` and `Form.txt` switching); the disc-4 view; an Environment.txt-driven
place. The view draws disc 1 form 1.
