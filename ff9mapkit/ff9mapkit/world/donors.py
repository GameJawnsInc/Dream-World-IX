"""The read-only overworld donor catalog (audit rec 13).

``data/donors.toml`` is the ONE human-readable statement of which real blocks are qualified
donors for the world pillar's carry verbs -- the fact used to live only in CLAUDE.md
section 8, a 1200-line study README, and code comments, where it contradicted itself.
Read by exactly one consumer (the ``world-donors`` CLI verb); the geometry modules keep
their frozen literals, and ``tests/test_world_donors.py`` pins each literal to a row here.
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
