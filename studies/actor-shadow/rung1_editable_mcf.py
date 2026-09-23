"""RUNG 1 of the actor-shadow arc -- an `--editable` fork's grafted donor objects, lit + shadowed by the donor MCF.

The bench is an editable fork of field 1607 (Madain Sari kitchen: 14 carried objects -- soup pots, fish,
moogles -- that the donor's MapConfigData gives a size-11, intensity-6..8 shadow, on an 8-floor walkmesh with
per-floor lights). It is SE-derived, so it is regenerated, never committed:

    cd ff9mapkit && py -m ff9mapkit import 1607 --editable --name MCF_KTN --id 30930 \\
        --out ../studies/actor-shadow/imported/rung1

Five variants, each deployed to the SAME slot and shot at the same moments:

    on             the import as written (ships mapconfig.bytes)      -> the fix
    control        the same toml without its `mapconfig` line         -> every editable fork before the fix
    empty          control minus every [[object]] block               -> the background, for masking
    probe          `on` with the player spawned in view on donor floor 0 only -> the reference for:
    reshape        probe with the walkmesh rebuilt from walkmesh.obj, floors written 3,1,2,0,... -> donor
                   floors 0 and 3 swap indices, and the build re-keys the MCF's per-floor lights to match
    reshape-nokey  the same reshape with the re-key cancelled (the donor MCF ships verbatim on the
                   renumbered walkmesh) -> the negative control for the re-key

    py studies/actor-shadow/rung1_variants.py              (writes every variant toml from the import)
    py tools/deploy_field.py <variant toml> --id 30930 --name MCF_KTN
    RUNG1_VARIANT=<v> py tools/play.py studies/actor-shadow/rung1_editable_mcf.py --label mcf-rung1-<v>
    py studies/actor-shadow/measure_rung1.py <on run> <control run> <empty run>

PRE  the DEPLOYED files are the variant's: the MCF under EVT_MCF_KTN (on / reshape-nokey: byte-equal to the
     donor's; reshape: the donor's re-keyed through the swap; control/empty: absent), the .eb's shadow ops
     (with an MCF: none anywhere -- it owns every actor; control/empty: the player's census SetShadowSize +
     SetShadowAmplifier, nothing on any grafted object), and for the reshapes the deployed walkmesh floor
     under the probe spot -- donor floor 0 -- is really built floor 3
P0   (probe variants) the player really stands at the probe spot, on donor floor 0 only
A0   no exception THROUGH the MCF / shadow path (fldmcf, ff9shadow, SetRenderer, DoEventCode); every other
     exception reported by name + count for comparison across the variants
F1   the spawn frame (+ a later repeat), read by eye and by measure_rung1.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit import mapconfig  # noqa: E402
from ff9mapkit.config import ModLayout, find_game_path  # noqa: E402
from ff9mapkit.scene import bgi  # noqa: E402
from ff9mapkit.content.ladder import find_player_entry  # noqa: E402
from ff9mapkit.eb import EbScript  # noqa: E402

FIELD = 30930
NAME = "MCF_KTN"
BENCH = HERE / "imported" / "rung1"
VARIANT = os.environ.get("RUNG1_VARIANT", "on")
assert VARIANT in ("on", "control", "empty", "probe", "reshape", "reshape-nokey"), VARIANT
SWAP = {0: 3, 1: 1, 2: 2, 3: 0, 4: 4, 5: 5, 6: 6, 7: 7}      # donor floor -> built floor (rung1_variants.SWAP)
PROBE = (-72, 571)                                            # the player spawn in the probe variants
LIVE = ModLayout(find_game_path() / "FF9CustomMap")
SHADOW_OPS = (0x81, 0x85)                      # SetShadowSize, SetShadowAmplifier


def _shadow_ops_by_entry(data: bytes) -> dict:
    eb = EbScript.from_bytes(data)
    out = {}
    for e in eb.entries:
        if e.empty:
            continue
        ops = [(i.op, tuple(i.args)) for f in e.funcs for i in eb.instrs(f) if i.op in SHADOW_OPS]
        if ops:
            out[e.index] = ops
    return out


def _preflight(g) -> None:
    mcf = LIVE.mapconfig_path(f"EVT_{NAME}")
    donor = (BENCH / "mapconfig.bytes").read_bytes()
    if VARIANT in ("on", "probe", "reshape-nokey"):
        g.check(mcf.is_file() and mcf.read_bytes() == donor,
                "PRE: the deployed MCF is the donor's, byte for byte", str(mcf))
    elif VARIANT == "reshape":
        g.check(mcf.is_file() and mcf.read_bytes() == mapconfig.remap_light_floors(donor, SWAP),
                "PRE: the deployed MCF is the donor's with its floor lights re-keyed through the swap", str(mcf))
    else:
        g.check(not mcf.exists(), "PRE: no MCF deployed (the pre-fix editable fork)", str(mcf))
    if VARIANT.startswith("reshape"):
        wm = bgi.BgiWalkmesh.from_bytes(
            (LIVE.fieldmap_dir(f"FBG_N34_{NAME}") / f"FBG_N34_{NAME}.bgi.bytes").read_bytes())
        fl = wm.floors_at(*PROBE)
        g.check(fl == [SWAP[0]], "PRE: the deployed walkmesh is renumbered -- the probe spot's donor floor 0 "
                "is built floor 3, alone", f"floors {fl}")
    data = LIVE.eb_path("us", f"EVT_{NAME}.eb.bytes").read_bytes()
    pe = find_player_entry(EbScript.from_bytes(data))
    got = _shadow_ops_by_entry(data)
    want = ({pe: [(0x81, (9, 9)), (0x85, (32,))]} if VARIANT in ("control", "empty")   # Zidane's census (9, 4)
            else {})
    print(f"[mcf-rung1] {VARIANT}: deployed shadow ops by entry {got} (player entry {pe})")
    g.check(got == want, "PRE: the deployed .eb carries the variant's shadow ops and none on any grafted "
            "object", f"{got} vs {want}")


SHADOW_PATHS = ("fldmcf", "ff9shadow", "FF9Shadow", "SetRenderer", "DoEventCode")


def _exceptions(g, mark, when: str) -> None:
    ex = g.exceptions_since(mark)
    ours = [e for e in ex if e.through(*SHADOW_PATHS)]
    g.check(not ours, f"A0: no exception through the MCF / shadow path ({when})", "; ".join(map(str, ours[:3])))
    tally: dict = {}
    for e in ex:
        if e not in ours:
            tally[str(e)] = tally.get(str(e), 0) + 1
    print(f"[mcf-rung1] {VARIANT}: other exceptions {when}: {tally or 'none'}")


def run(g) -> None:
    _preflight(g)
    g.note(f"editable-fork MCF rung 1 -- variant {VARIANT}")
    g.newgame()
    mark = g.log_mark()
    g.warp(FIELD)
    s = g.settle()
    if VARIANT in ("probe", "reshape", "reshape-nokey"):
        donor_wm = bgi.BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())
        at = (s.player_x, s.player_z)
        g.check(g.distance_to(*PROBE) < 40 and donor_wm.floors_at(*at) == [0],
                "P0: the player stands at the probe spot, on donor floor 0 only",
                f"at {at}, donor floors {donor_wm.floors_at(*at)}")
    g.wait_frames(90)
    g.shot("1-spawn")
    g.wait_frames(120)
    g.shot("2-spawn-later")
    _exceptions(g, mark, "entering the field and standing")
