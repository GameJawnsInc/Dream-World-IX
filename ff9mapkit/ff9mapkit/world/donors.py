"""The read-only overworld donor catalog (audit rec 13).

``data/donors.toml`` is the ONE human-readable statement of which real blocks are qualified
donors for the world pillar's carry verbs -- the fact used to live only in CLAUDE.md
section 8, a 1200-line study README, and code comments, where it contradicted itself.
Read by the CLI (the ``world-donors`` verb, the home-ground warning, and a massif's alcove for ``world-mountain`` /
``world-fuse``); the geometry modules keep their frozen literals and never parse it, and
``tests/test_world_donors.py`` pins each literal to a row here.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

DONORS_TOML = Path(__file__).resolve().parent / "data" / "donors.toml"


def load_donors() -> list:
    """The ``[[donor]]`` rows, verbatim."""
    with open(DONORS_TOML, "rb") as fh:
        return tomllib.load(fh).get("donor", [])


def donors_by_blocks() -> dict:
    """``{blocks_spec: row}`` -- the drift test's join key (the CLI rect spec string)."""
    return {r["blocks"]: r for r in load_donors()}


def spec_blocks(spec: str) -> frozenset:
    """A row's ``blocks`` rect spec (``"BX,BY"`` / ``"BX0-BX1,BY0-BY1"``) -> its block set."""
    def rng(s):
        a, _, b = s.partition("-")
        return range(int(a), int(b or a) + 1)
    xs, ys = spec.split(",")
    return frozenset((x, y) for x in rng(xs) for y in rng(ys))


def row_for_blocks(blocks, *, klass: str = "massif"):
    """The ``klass`` row naming exactly this donor block set (a ``--donor`` rect, any order), else None."""
    want = frozenset((int(b[0]), int(b[1])) for b in blocks)
    for r in load_donors():
        if r.get("class") == klass and spec_blocks(r["blocks"]) == want:
            return r
    return None


def catalog_alcove(blocks):
    """The catalogued massif's alcove as ``carve_mountain(alcove=)`` takes it -- ``((x0, x1), (z0, z1), y_min)``, plus
    the floor topographs as a 4th element when the row names ``alcove_floor`` -- else ``None`` (not a catalogued massif,
    or one without an alcove: the caller keeps ``"auto"``). Uaho's row equals ``interior.UAHO_ALCOVE`` (the drift
    test pins it), so handing it in carves the same bytes as ``"auto"``."""
    r = row_for_blocks(blocks)
    box = r.get("alcove") if r else None
    if not box:
        return None
    x0, x1, z0, z1, ymin = (float(v) for v in box)
    spec = ((x0, x1), (z0, z1), ymin)
    if r.get("alcove_floor"):
        spec += (tuple(int(t) for t in r["alcove_floor"]),)
    return spec


def home_ground_note(blocks, ground: str):
    """THE HOME-GROUND WARNING (terrain study, mountain donors): every massif donor stands on ONE ground family at
    home -- its rim's feet (Uaho, comp20, the horseshoe: grass; the crag and the desert peak: desert). Carried onto
    another ground, its foot meets a ground it never meets in stock (THE OVERHANG-CONTEXT LAW), which the gates
    cannot see. A WARNING, not a refusal: the carry is lawful, the context is the owner's call. ``None`` when the
    donor is not a catalogued massif or the ground matches."""
    r = row_for_blocks(blocks)
    home = r.get("home_ground") if r else None
    if not home or home == ground:
        return None
    return (f"!! WARNING home ground: the {r['name']} massif stands on {home} at home (world/data/donors.toml); "
            f"carried onto {ground}, its foot meets a ground it never meets in stock. Mint the island with "
            f"`world-island --ground {home}` and carve with `--ground {home}`, or keep it knowingly.")
