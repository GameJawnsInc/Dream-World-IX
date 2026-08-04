"""The UI inventory's STABILITY fence: a harvest must record the UI, never the machine.

The defect this exists for: `build_deploy.dep_hint` paints the live mod folder's deploy ledger
("410 deployed here · ..."), and the mod folders are SHARED by every concurrent session -- so the
committed ui-inventory.json drifted 410 -> 422 during unrelated work, and `uiharvest --check` (the
gate that is supposed to alarm on a renamed control) alarmed on somebody else's deploy instead.
Same class: where New Game currently points, this worktree's .ff9deploy.toml slot, this box's
ffmpeg path and PySide6 version.

Unlike its neighbours these tests DRIVE QT (a rendered label only exists once Qt builds it), so
they carry gui_snap's own constraints: Windows + native platform. They skip loudly, never silently
-- a skip line naming the reason, per the worktree-skip trap. A full harvest is ~4s.

Nothing here touches the real install: the live reads are injected with fake values, so a "deploy
between two runs" is simulated rather than performed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import uiharvest as U  # noqa: E402

pytestmark = [
    pytest.mark.skipif(os.name != "nt", reason="gui_snap asserts Windows (the prefs pin repoints "
                                                "LOCALAPPDATA, honoured only on nt)"),
    pytest.mark.skipif(os.environ.get("QT_QPA_PLATFORM") == "offscreen",
                       reason="gui_snap refuses offscreen: its font DB is fiction"),
]
pytest.importorskip("PySide6", reason="the harvest drives the real Workspace")


# Two different "worlds" the harvest must be blind to: a ledger with a different count, a different
# New-Game target, a different worktree deploy pin. Substituted for the LIVE readers, so the pin (if
# it holds) overrides them and (if it were removed) they reach the labels verbatim.
WORLD_A = {
    "rows": [{"kind": "field", "id": "4003", "name": "a", "script": "r.py", "mtime": 0.0}],
    "newgame": 4003,
    "target": ("FF9CustomMap", 30001),
}
WORLD_B = {
    "rows": [{"kind": "field", "id": str(i), "name": f"f{i}", "script": None, "mtime": None}
             for i in range(4000, 4042)],                       # 42 rows -- a very different count
    "newgame": 9999,
    "target": ("FF9CustomMap-world", 30777),
}


class _inject_world:
    """Stand in for the LIVE machine: what the ledger / New-Game / deploy-target readers return."""

    def __init__(self, world):
        from ff9mapkit.editor import jobs
        self.jobs, self.world = jobs, world
        self._orig = (jobs.scan_deployed_reverts, jobs.current_newgame_target,
                      jobs.detect_deploy_target)

    def __enter__(self):
        w = self.world
        self.jobs.scan_deployed_reverts = lambda *_a, **_k: [dict(r) for r in w["rows"]]
        self.jobs.current_newgame_target = lambda *_a, **_k: w["newgame"]
        self.jobs.detect_deploy_target = lambda *_a, **_k: w["target"]
        return self

    def __exit__(self, *exc):
        (self.jobs.scan_deployed_reverts, self.jobs.current_newgame_target,
         self.jobs.detect_deploy_target) = self._orig
        return False


def _build(world, *, pin_live=True):
    with _inject_world(world):
        return U.harvest(pin_live=pin_live)["surfaces"]["tab:build"]


@pytest.fixture(scope="module")
def surfaces():
    """One harvest per world, reused by every test below (~4s each, so pay it once)."""
    return {"a": _build(WORLD_A), "b": _build(WORLD_B), "unpinned_b": _build(WORLD_B, pin_live=False)}


def test_the_injection_actually_reaches_the_labels(surfaces):
    """TEETH FIRST. If the fake worlds never reached a label, the stability test below would pass
    on a harvest with no pin at all -- a check that cannot fail. Prove the potency before spending
    it: UNPINNED, world B must paint differently from pinned world A."""
    assert surfaces["unpinned_b"] != surfaces["a"], (
        "with pin_live=False the injected ledger/New-Game/deploy state did NOT change any harvested "
        "label -- the fence is measuring nothing; re-check which readers the Build tab paints")
    assert "42 deployed here" in surfaces["unpinned_b"]["build_deploy.dep_hint"]["text"], \
        "the injected 42-row ledger did not reach dep_hint -- the reader moved"


def test_inventory_is_stable_across_a_deploy(surfaces):
    """The fix, stated as the requirement: two consecutive harvests with the deploy ledger changed
    between them (42 rows vs 1, a different New-Game target, a different .ff9deploy.toml pin) must
    produce a byte-identical Build surface."""
    drift = [f"{k}: {surfaces['a'][k]} -> {surfaces['b'][k]}"
             for k in surfaces["a"].keys() & surfaces["b"].keys()
             if surfaces["a"][k] != surfaces["b"][k]]
    assert not drift and surfaces["a"].keys() == surfaces["b"].keys(), (
        "the harvest recorded live machine state -- it moves when an unrelated session deploys:\n  "
        + "\n  ".join(drift))


def test_harvest_matches_the_committed_inventory_under_any_world(surfaces):
    """Stability alone would be satisfied by two equally-wrong runs. The committed file is the
    thing the site build reads, so anchor to it: whatever the live ledger says, the harvest must
    reproduce what is on disk."""
    import json
    committed = json.loads((HERE.parent / "assets" / "ui-inventory.json").read_text(
        encoding="utf-8"))["surfaces"]["tab:build"]
    assert surfaces["b"] == committed, (
        "docsite/assets/ui-inventory.json disagrees with a pinned harvest -- if this is a deliberate "
        "UI change run `py docsite/uiharvest.py` and commit; if not, a live-state label slipped the pin")
