"""RUNG 2 of the actor-shadow arc -- a plain (BG-borrow) `import`'s grafted donor objects, lit + shadowed by
the donor MCF.

Rung 1 proved it for an `--editable` fork of field 1607 (Madain Sari kitchen: 14 carried objects -- soup
pots, fish, moogles -- that the donor's MapConfigData gives a size-11, intensity-6..8 shadow). Field 1607 is
area 34, so it also forks as a BG-borrow: the engine renders the donor's own art + walkmesh + camera while
running the fork's script, and loads the MCF by the fork's event name. The bench is SE-derived, so it is
regenerated, never committed:

    cd ff9mapkit && py -m ff9mapkit import 1607 --name MCF_KTB --id 30935 \\
        --out ../studies/actor-shadow/imported/rung2

Three variants, each deployed to the SAME slot and shot at the same moments:

    on        the import as written (ships mapconfig.bytes)        -> the fix
    control   the same toml without its `mapconfig` line           -> every plain `import` before the fix
    empty     control minus every [[object]] block                 -> the background, for masking

    py studies/actor-shadow/rung2_variants.py               (writes control + empty from the import)
    py tools/deploy_field.py <variant toml> --id 30935 --name MCF_KTB
    RUNG2_VARIANT=<v> py tools/play.py studies/actor-shadow/rung2_borrow_mcf.py --label mcf-rung2-<v>
    py studies/actor-shadow/measure_rung1.py objects <on run> <control run> <empty run>

PRE  the DEPLOYED files are the variant's: the MCF under EVT_MCF_KTB (on: byte-equal to the donor's;
     control/empty: absent), still a BG-borrow (the DictionaryPatch borrow line, no scene of its own shipped),
     and the .eb's shadow ops (on: none anywhere -- the MCF owns every actor; control/empty: the player's
     census SetShadowSize + SetShadowAmplifier, and in control the refused graft's [[prop]] stub -- a kit
     moogle, which casts per STOCK_CASTS -- the same; nothing on any grafted object)
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
from ff9mapkit import eventscan  # noqa: E402
from ff9mapkit.config import ModLayout, find_game_path  # noqa: E402
from ff9mapkit.content.ladder import find_player_entry  # noqa: E402
from ff9mapkit.eb import EbScript  # noqa: E402

FIELD = 30935
NAME = "MCF_KTB"
AREA = 34
BORROW = "MDSR_MAP579_MS_KTN_0"
BENCH = HERE / "imported" / "rung2"
VARIANT = os.environ.get("RUNG2_VARIANT", "on")
assert VARIANT in ("on", "control", "empty"), VARIANT
LIVE = ModLayout(find_game_path() / "FF9CustomMap")
SHADOW_OPS = (0x81, 0x85)                      # SetShadowSize, SetShadowAmplifier
PROP_STUB = (431, 825)                         # the import's refused-graft [[prop]] stub (GEO_NPC_F0_MOG)


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
    if VARIANT == "on":
        g.check(mcf.is_file() and mcf.read_bytes() == donor,
                "PRE: the deployed MCF is the donor's, byte for byte", str(mcf))
    else:
        g.check(not mcf.exists(), "PRE: no MCF deployed (the pre-fix BG-borrow fork)", str(mcf))
    reg = [ln.split() for ln in LIVE.dictionary_patch.read_text(encoding="utf-8").splitlines()
           if ln.startswith(f"FieldScene {FIELD} ")]
    g.check(len(reg) == 1 and reg[0][2:5] == [str(AREA), BORROW, NAME],
            "PRE: the slot is registered as a BG-borrow of the donor's scene", str(reg))
    own = LIVE.fieldmap_dir(f"FBG_N{AREA}_{NAME}")
    shipped = sorted(p.name for p in own.glob("*")) if own.is_dir() else []
    g.check(not any(n.endswith((".bgx", ".bgi.bytes", ".bgs.bytes")) for n in shipped),
            "PRE: no scene of its own is deployed -- the donor's renders", str(shipped))
    data = LIVE.eb_path("us", f"EVT_{NAME}.eb.bytes").read_bytes()
    pe = find_player_entry(EbScript.from_bytes(data))
    got = _shadow_ops_by_entry(data)
    # the refused graft's [[prop]] stub is KIT content: on a field with no MCF it casts its model's census
    # like any set piece stock lets cast (content.shadow STOCK_CASTS -- the moogle does). Found by position.
    stub = [o["donor_idx"] for o in eventscan.scan_objects_verbatim(data)
            if any((i["x"], i["z"]) == PROP_STUB for i in o["instances"])]
    want = {}
    if VARIANT != "on":
        want[pe] = [(0x81, (9, 9)), (0x85, (32,))]                    # Zidane's census (9, 4)
    if VARIANT == "control":
        g.check(len(stub) == 1, "PRE: the [[prop]] stub is the one kit object at its spot", str(stub))
        want[stub[0]] = [(0x81, (6, 6)), (0x85, (16,))]              # the moogle's census (6, 2)
    print(f"[mcf-rung2] {VARIANT}: deployed shadow ops by entry {got} (player entry {pe}, prop stub {stub})")
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
    print(f"[mcf-rung2] {VARIANT}: other exceptions {when}: {tally or 'none'}")


def run(g) -> None:
    _preflight(g)
    g.note(f"BG-borrow fork MCF rung 2 -- variant {VARIANT}")
    g.newgame()
    mark = g.log_mark()          # before the warp, so a throw while the MCF LOADS counts; field 70's MovePC
    g.warp(FIELD)                # NREs land in the "other" tally (they pass through no shadow path)
    g.settle()
    g.wait_frames(90)
    g.shot("1-spawn")
    g.wait_frames(120)
    g.shot("2-spawn-later")
    _exceptions(g, mark, "entering the field and standing")
