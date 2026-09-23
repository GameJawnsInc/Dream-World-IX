"""The seam re-key, in-game: walk across a cross-floor seam that only the re-key keeps (rung-1 bench, slot 30930).

The rung-1 `reshape` variant writes the 1607 fork's `o floor_N` blocks in the order 3,1,2,0,..., so the rebuild
swaps donor floors 0 and 3. The links sidecar numbers its seams by the donor's floors: without the re-key
(`build._donor_floor_map` -> `apply_seams(seams, floor_map)`) every seam of donor floor 0 is looked up on the
wrong floor and dropped. The probe spawn stands on donor floor 0, about 80 units north of its seam with donor
floor 5 (both at y -433), so the seam decides whether the player can walk south.

    SEAM_BUILD   new | old -- which reconcile built the deployed walkmesh (old = apply_seams without its map)
    RUNG1_BENCH  the imported rung-1 bench (default studies/actor-shadow/imported/rung1, see rung1_editable_mcf.py)

    py tools/deploy_field.py <bench>/MCF_KTN.reshape.field.toml --id 30930 --name MCF_KTN
    SEAM_BUILD=new py tools/play.py studies/actor-shadow/seam_rekey_ingame.py --label seam-rekey-new

PRE  the deployed walkmesh is the reshape: the spawn is built floor 3 (donor 0) alone, the target built floor 5
     (donor 5) alone, and the donor 0<->5 seam is linked (new) or absent (old) in the deployed bytes
S1   from the spawn, walk south across the seam to TARGET: arrives on donor floor 5 (new) / stops on donor floor 0 (old)
S2   (new) walk back north across the same seam: ends on donor floor 0, past the seam (the spawn itself sits inside
     an edge's collision radius, so arrival at it is not the test)
A0   exceptions while walking, tallied by name (the MovePC NullReferenceException predates this change)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.config import ModLayout, find_game_path  # noqa: E402
from ff9mapkit.scene import bgi  # noqa: E402

FIELD = 30930
NAME = "MCF_KTN"
BENCH = Path(os.environ.get("RUNG1_BENCH", HERE / "imported" / "rung1"))
BUILD = os.environ.get("SEAM_BUILD", "new")
assert BUILD in ("new", "old"), BUILD
SWAP = {0: 3, 1: 1, 2: 2, 3: 0, 4: 4, 5: 5, 6: 6, 7: 7}      # donor floor -> built floor (rung1_variants.SWAP)
PROBE = (-72, 571)                                            # the spawn: donor floor 0 only
TARGET = (-72, 380)                                           # donor floor 5 only; the seam crosses x=-72 at z~491
SEAM_Z = 491
LIVE = ModLayout(find_game_path() / "FF9CustomMap")


def _donor() -> bgi.BgiWalkmesh:
    return bgi.BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())


def _preflight(g) -> None:
    wm = bgi.BgiWalkmesh.from_bytes(
        (LIVE.fieldmap_dir(f"FBG_N34_{NAME}") / f"FBG_N34_{NAME}.bgi.bytes").read_bytes())
    g.check(wm.floors_at(*PROBE) == [SWAP[0]] and wm.floors_at(*TARGET) == [SWAP[5]],
            "PRE: the deployed walkmesh is the reshape -- the spawn is built floor 3 (donor 0), the target built "
            "floor 5 (donor 5)", f"spawn {wm.floors_at(*PROBE)}, target {wm.floors_at(*TARGET)}")
    pairs = {tuple(sorted((a, b))) for (a, _e, b, _f) in wm.extract_seams()}
    linked = tuple(sorted((SWAP[0], SWAP[5]))) in pairs
    print(f"[seam-rekey] {BUILD}: deployed seam floor pairs {sorted(pairs)}")
    g.check(linked == (BUILD == "new"),
            f"PRE: the donor 0<->5 seam is {'linked' if BUILD == 'new' else 'absent'} in the deployed walkmesh",
            f"pairs {sorted(pairs)}")


def _where(g, donor) -> tuple:
    """The player's position and the donor floors under it AT HIS HEIGHT. floors_at is 2-D, and 1607 stacks
    floor 4 (y ~-1500, a basement) under floors 0 and 5 (y -433), so XZ alone reads [0, 4] beside the seam.
    The published y is sign-flipped against the walkmesh's (433 on the y -433 plateau)."""
    s = g.settle()
    at = (s.player_x, s.player_z)
    wv = donor.world_verts()
    span = {}
    for t in donor.tris:
        ys = [wv[v][1] for v in t.vtx]
        lo, hi = span.get(t.floor_ndx, (min(ys), max(ys)))
        span[t.floor_ndx] = (min(lo, *ys), max(hi, *ys))
    y = -s.player_y
    return at, [f for f in donor.floors_at(*at) if span[f][0] - 60 <= y <= span[f][1] + 60]


def run(g) -> None:
    _preflight(g)
    donor = _donor()
    g.note(f"seam re-key in-game -- {BUILD} build")
    g.newgame()
    mark = g.log_mark()
    g.warp(FIELD)
    at, fl = _where(g, donor)
    g.check(g.distance_to(*PROBE) < 40 and fl == [0], "S0: the player spawns at the probe spot, on donor floor 0",
            f"at {at}, donor floors {fl}")
    g.shot("0-spawn")

    arrived = g.walk_to(*TARGET, strict=False)
    at, fl = _where(g, donor)
    g.shot("1-south")
    if BUILD == "new":
        g.check(arrived and fl == [5], "S1: walking south crosses the seam onto donor floor 5",
                f"arrived={arrived}, at {at}, donor floors {fl}")
        # judged by the floor reached, not by arrival: the spawn is ~22u from a walkmesh edge, inside the ~80u
        # collision radius, so the walk back stops short of it (first run: 60u short, on floor 0, 54u past the seam)
        back = g.walk_to(*PROBE, strict=False)
        at, fl = _where(g, donor)
        g.shot("2-back-north")
        g.check(fl == [0] and at[1] > SEAM_Z + 20, "S2: walking back north crosses the same seam onto donor floor 0",
                f"arrived={back}, at {at}, donor floors {fl}")
    else:
        g.check(not arrived and fl == [0], "S1: without the re-key the seam is a wall -- the player stays on "
                "donor floor 0", f"arrived={arrived}, at {at}, donor floors {fl}")

    tally: dict = {}
    for e in g.exceptions_since(mark):
        tally[str(e)] = tally.get(str(e), 0) + 1
    print(f"[seam-rekey] {BUILD}: exceptions while walking: {tally or 'none'}")
