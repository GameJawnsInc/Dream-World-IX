# THE CELL-CLIPPED FILL in game -- owner verdict: PASS (2026-10-20)

The coast-morph grass-fill fix (coastmorph `_grass_fill_region`, master 7f063922), seen in game before and after.

## What ran
- **Lab:** `lab_build.py` built one scratch folder, FF9CustomMap-lab, in two variants outside the install. OLD was built
  by the pre-fix code (master 9b99d78c, exported) and NEW by the fix. Each holds the same four in-place cliff morphs on
  disc 1 (Terrain + Sea4, no disc-4 mirror) plus mist off. The four windows are world-morphs' certified deploy lines that
  carried one streaked fill tri each before the fix:
  | station | window | old streak tri |
  |---|---|---|
  | A | headland (13,17) D=3 | ratio 55.8, 1.91 u^2 |
  | B | headland (12,12) D=4 | 90.9, 1.48 u^2 |
  | C | bay (12,13) D=6 | 21.6, 1.49 u^2 |
  | D | bay (5,16) D=6 | rank 1, 1.25 u^2 |
  No live mod folder overrides any of the four cells.
- **Install:** `lab_install.py` put the lab first in FolderNames for the session, with Memoria.ini backed up into the main
  repo's backups/. `swap` changed the variant between launches. `uninstall` took only the lab's own entry back out; the
  ini read back as the backup byte for byte, both times.
- **Session:** `still_session.py`, four harness launches, saves sandboxed. Each one: New Game, bench 6603, the disc-1
  world at ScenarioCounter 0 (form 1 for the Lindblum cell), encounters off. Then per station:
  - a home on stock lawn 12u from the old streak tri (out/stations.json);
  - face the tri, two stills;
  - close-ups (run 2): teleport 3u short of the tri ("near"), then onto it ("on"), keeping the camera yaw.
  
  The second variant faces the heading the first reached (face_targets.json), so the pairs line up.

| run | label | checks |
|---|---|---|
| 1 | cellclip-old / cellclip-new | 10/10, 10/10 (every heading identical across the pair) |
| 2 | cellclip-old2 / cellclip-new2 | 18/18, 17/18 |

Run 2's one miss was A's face in the NEW run. All four camera quarters probed 1.70u in 40 frames from a home that faced
fine in the other three runs: a tick-rate stall, not geometry. A's NEW close-ups therefore look a different way.
Every height check landed within 0.002u of the prediction.

## What the stills show (`pairs.py` -> out/pairs/, the sheet: out/pairs/cellclip-verdict-sheet.png)
- **D, the rank-1 tri, is visible and fixed.** Standing on it at x6, BEFORE shows a band of parallel stripes along the
  lip from his feet: one texture row stretched across the tri. AFTER shows ordinary grass there.
- **B and C look the same either way.** Their single tri is under the sprite or below what the camera resolves.
- **The 12u views resolve none of the four.** A 1-2 u^2 tri is a few pixels from there; only the close-ups show it.
- **No AFTER frame shows a crack, shard or seam** at the rebuilt wall, the lip, the kept stock beside the refill, or
  a block border.
- A pixel diff of a pair proves nothing. Sub-pixel camera jitter lights up every textured surface; judge by eye.

**Owner verdict: PASS** (from the stills, 2026-10-20).

## Instrument lessons
- A single streaked tri is invisible from the 12u station camera. Calibrate with a close-up that stands ON the
  predicted spot before judging a small texture defect.
- `world_face` can stall in a launch (probes ~1.7u in 40 frames in every quarter) where the same home faced fine
  before. Retry in a fresh launch, not more rounds.
