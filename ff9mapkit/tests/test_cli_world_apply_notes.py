"""The world APPLY-note contract: the CLI must not resurrect the falsified relaunch claim.

Playtest-proven 2026-08-04 (hill deployed, byte-swapped to pristine mid-session, vanished on
the next ~ -> World reload; Memoria.log shows a fresh "[WorldMeshOverride] loaded" line per
block on EVERY reload): the world-scene rebuild re-reads every loose .ff9mesh override from
disk. "A loose asset isn't hot-reloaded" was measured FALSE, and it taxed every world
iteration with a relaunch. These are grep-level source gates -- delete the helper or re-add
the claim and they go red (a check that cannot fail is no check).
"""
from __future__ import annotations

import re
from pathlib import Path

CLI = (Path(__file__).resolve().parent.parent / "ff9mapkit" / "cli.py").read_text(encoding="utf-8")


def test_no_world_handler_claims_loose_assets_are_not_hot_reloaded():
    """The falsified claim may not appear anywhere in the CLI source."""
    assert "isn't hot-reloaded" not in CLI
    assert "aren't hot-reloaded" not in CLI


def test_the_shared_apply_note_exists_and_is_widely_wired():
    """One voice: the geometry writers route their APPLY instruction through the helper.
    11 sites were converted at the falsification; drift below 10 means someone deleted
    call sites without moving the instruction elsewhere."""
    assert "def _world_apply_note(" in CLI
    calls = re.findall(r"_world_apply_note\(", CLI)
    assert len(calls) - 1 >= 10, f"only {len(calls) - 1} call sites remain"


def test_the_note_text_carries_both_halves():
    """The note must state the reload path AND the honest RELAUNCH-only list -- the fix is
    an honesty fix, not a new lie in the opposite direction."""
    assert 'Reload overworld on state' in CLI
    assert "RELAUNCH only for" in CLI
