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
#   * --building-at 48 -1160.2 : THE TRIGGER-AT-THE-FOOT LAW (pass 4), re-solved for pass 5's entrance
#                        steps. Pass 3 stood the tower at z -1157, ~12u north of the trigger cluster,
#                        and the owner reported "the entrance is heavily offset to the south" -- the "!"
#                        fired in open grass with the tower standing apart. The hull must stay >=1u off
#                        the trigger rect (z -1164), and the hull is the mesh's FULL XZ extent:
#                            pass 4, half-depth 2.30           ->  cz >= -1160.70  (used -1160.5)
#                            pass 5, half-depth 2.30 + 0.45    ->  cz >= -1160.25  (uses  -1160.2)
#                        The steps reach z -1162.95, so the STRUCTURE is 0.15u closer to the trigger
#                        than pass 4 even though the centre moved 0.30u north. Do NOT go south of
#                        -1160.25 while the steps exist. MUST match ANCHOR in mint_quay_beacon.py.
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

SITE="${1:-}"
if [ -z "$SITE" ]; then
  echo "usage: $0 <ashvale|tidefall|grimhorn|larkspur|lamplight>" >&2
  exit 2
fi

# Per-site deploy arguments. Each row is: cell  trigger  --building-at  obj
#
# ⚠ AT IS THE MESH'S BBOX CENTRE, NOT THE ANCHOR -- they differ by 0.225u since pass 5.
# `build_from_obj` re-anchors the XZ BOUNDING-BOX CENTRE onto --building-at. The entrance steps
# project 0.45u south, so the bbox centre sits 0.225u south of the tower centre; passing the anchor
# slides the whole beacon 0.225u NORTH of where the 29 gates measured it. `mint_quay_beacon.py`
# prints the correct value (Site.building_at) at the end of every generate -- use that, never the
# anchor. (Caught on the first Tidefall deploy; the gap to the trigger merely grew, but the deployed
# mesh no longer matched the gated one, which is how drift starts.)
# The beacon anchor's SOUTHERN LIMIT is derived per site in mint_quay_beacon.py's SITES table: the hull
# must stay >= 1.0u clear of the trigger rect, and the hull is the mesh's FULL XZ extent, which since
# pass 5 includes the entrance steps projecting 0.45u south. So the limit is
#     cz >= (trigger north edge) + 1.0 + 2.30 + 0.45
# Ashvale: trigger north -1164.0 -> cz >= -1160.25, uses -1160.2 (0.05u slack).
# Tidefall/Grimhorn/Larkspur: same derivation against each site's own trigger rect; every value below
# was gate-verified by `mint_quay_beacon.py` (29 gates) before being recorded here.
# All five sites ride the VIRGIN nameplate lane (self-summon trigger, no switch surgery): the four
# quays warp to the hall (6601) under their OWN island names on cases 65-68 (the EXTENDED band --
# needs `world-entrance --extend-nameplate-band` deployed, which any 65+ deploy auto-runs), and
# Lamplight warps to the lamp room (6602) on case 61. THE ONE-CASE FERRY (all quays on dead case 53,
# shared "Lantern Quay" plate) is SUPERSEDED by the per-quay pass; case 53's switch arm is still
# deployed but orphaned (no tile summons it), and split[53] keeps "Lantern Quay" as the network name.
#
# ⚠ NEVER use case 52: it looks switch-dead but the main loop hardcodes `Byte[24]==52 && Confirm ->
# Battle(0,144)` -- the desert quicksand's Antlion ambush (the R3 playtest fired it at the beacon).
# ⚠ NEVER use cases 91-93: the vehicle HUD trio (Byte[24] 191-193).
case "$SITE" in
  ashvale)  CELL="1 36";   TRIG="48 -1168";    AT="48 -1160.425";    OBJ="quay_beacon.obj"
            FIELD=6601; NAME="Ashvale"; CASE=65 ;;
  tidefall) CELL="13 38";  TRIG="420 -1232";   AT="420 -1224.425";   OBJ="quay_beacon_tidefall.obj"
            FIELD=6601; NAME="Tidefall"; CASE=66 ;;
  grimhorn) CELL="37 37";  TRIG="1204 -1192";  AT="1204 -1184.425";  OBJ="quay_beacon_grimhorn.obj"
            FIELD=6601; NAME="Grimhorn"; CASE=67 ;;
  larkspur) CELL="21 19";  TRIG="700 -616";    AT="700 -608.425";    OBJ="quay_beacon_larkspur.obj"
            FIELD=6601; NAME="Larkspur"; CASE=68 ;;
  lamplight) CELL="44 36"; TRIG="1424 -1168";  AT="1424 -1160.425";  OBJ="quay_beacon_lamplight.obj"
            FIELD=6602; NAME="Lamplight"; CASE=61 ;;
  *) echo "unknown site: $SITE" >&2; exit 2 ;;
esac

# (re)generate this site's OBJ -- committed, but this keeps mesh and deploy in lockstep and re-runs
# the 29 geometry gates (closed / orientable / outward / buried skirt / siting / panel scale / UVs)
py "$HERE/mint_quay_beacon.py" --site "$SITE"

cd "$ROOT/ff9mapkit"
py -m ff9mapkit world-entrance     --cell $CELL     --field-direct $FIELD     --nameplate-name "$NAME"     --nameplate-case $CASE     --trigger-at $TRIG     --trigger-radius 3.0     --no-tile-area     --mod-folder FF9CustomMap-world     --building "../studies/overworld-topography/southern-ring/$OBJ"     --building-at $AT     --no-seat     --replace-town     --building-idall 4078

echo
echo "Re-deployed $SITE. Now verify from the DEPLOYED bytes:"
echo "  py \"$HERE/probe_marker/probe_quay_beacon.py\""
