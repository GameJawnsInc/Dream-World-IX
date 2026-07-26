#!/bin/sh
# Re-deploy THE LANTERN QUAY MARKER after anything that clobbers block (0,18).
#
# WHY THIS EXISTS -- the standing trap:
#   `world/island.py` (HIDDEN_PARTS at :53, deployed at :955-957 and :966-969) UNCONDITIONALLY
#   re-deploys a 176-byte blanking stub for the Object part of every cell it mints, and a
#   `world-island` / `world-reclaim` re-run also rewrites the cell's TERRAIN from scratch.
#   Since pass 3 the marker is TWO things, not one:
#       * the beacon Object mesh          -> wiped by the stub re-deploy
#       * the topo-59 collision hull + the 6 event tiles, both in the TERRAIN idall bits
#                                          -> wiped by a terrain re-deploy
#   So a re-run needs BOTH halves restored. This script does both in one command, because it
#   re-runs the same `world-entrance` invocation that authored them.
#
# It is also the canonical record of the exact deploy arguments (recovered from R1's
# r1_build_report.json), and it is IDEMPOTENT: all 9 dispatchers skip (the cell already carries the
# surgery tag), the 6 event tiles re-stamp to the same values, and the beacon replaces whatever
# Object mesh is there.
#
#   * --no-tile-area   : R1 deployed the trigger tiles with area KEPT (idall 16384, area 0). Without
#                        this flag the tiles would be re-stamped area=53 and the probe's expectation
#                        (and possibly the entrance) would change.
#   * --no-seat        : the OBJ is authored in WORLD coords with its skirt 0.5u BELOW the y=3.00
#                        plateau. Seating would lift the lowest point ONTO the ground and un-bury the
#                        skirt, reintroducing the coplanar-face z-fighting the beacon exists to avoid.
#   * --replace-town   : block (0,18) has no stock town -- only the blanking stub -- so replacing is
#                        the clean option and yields a 222-tri Object mesh with nothing else in it.
#   * --building-idall 4078 : MANDATORY here. Block (0,18) is reclaimed and its Donor.txt names donor
#                        (0,0), which HAS a stock Object component -- so the engine takes
#                        RegisterBlockComponent(form1: true) -> AddWalkMeshForm1 and the model would
#                        be COLLISION (its culled walls + buried skirt = invisible collision), and it
#                        registers BEFORE Terrain so it would also shadow the quay trigger. 4078 is
#                        the WMPhysics skip id: render-only for real. Footprint collision still comes
#                        from the topo-59 terrain hull.
#
# Verify afterwards:
#   py studies/overworld-topography/southern-ring/probe_marker/probe_quay_beacon.py
#
# Run from the repo root. No relaunch is needed for the mesh/terrain halves (they load when the
# block streams in); the nameplate .mes rewrite is a no-op re-write of what R1 already deployed.

set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"

# (re)generate the beacon OBJ -- it is committed, but this keeps the mesh and the deploy in lockstep
# and re-runs the 20 geometry gates (closed / orientable / outward / buried skirt / panel scale / UVs)
py "$HERE/mint_quay_beacon.py"

cd "$ROOT/ff9mapkit"
py -m ff9mapkit world-entrance \
    --cell 1 36 \
    --field-direct 6601 \
    --nameplate-name "Lantern Quay" \
    --nameplate-case 53 \
    --trigger-at 48 -1168 \
    --trigger-radius 3.0 \
    --no-tile-area \
    --mod-folder FF9CustomMap-world \
    --building "../studies/overworld-topography/southern-ring/quay_beacon.obj" \
    --building-at 48 -1157 \
    --no-seat \
    --replace-town \
    --building-idall 4078

echo
echo "Re-deployed. Now verify from the DEPLOYED bytes:"
echo "  py \"$HERE/probe_marker/probe_quay_beacon.py\""
