"""The CLI ``behavior compile|view`` lane, driven end to end -- the first test that does.

The offline dry-compile exists in five places (this CLI lane, ``workspace.behaviorscan.dry_compile``,
``behaviortoml.published_flags``, ``siege.resolve_hireable`` and the ``build.lint_flag_bands``
recompute). The CLI copy once seated its placeholder entry slots per UNIT ROW and read ``u["npc"]``; a
CLASS row (``npcs = [...]``) has no such key, so ``behavior compile`` on the shipped ``[siege]``
example -- which desugars to four class rows -- tracebacked with ``KeyError: 'npc'`` while the
Workspace rendered the same file fine. Every lane now seats through ONE function,
``behaviortoml.placeholder_slots`` (per MEMBER, the way ``build.py`` seats the real slots); this file
pins the CLI to the Workspace lane AND pins all five lanes to that one seat, so none can drift again.
"""

from __future__ import annotations

from pathlib import Path

from ff9mapkit import cli

SIEGE = Path(__file__).resolve().parents[1] / "examples" / "siege" / "siege.field.toml"


def test_behavior_compile_runs_on_class_rows(capsys):
    rc = cli.main(["behavior", "compile", str(SIEGE)])
    out = capsys.readouterr()
    assert rc == 0, out.err
    assert "stable hash" in out.out
    assert "pool spawn-request flags" in out.out     # the [siege] hire menu


def test_behavior_view_runs_on_class_rows(capsys):
    # view falls through the compile lane (same seating), then disassembles every body
    rc = cli.main(["behavior", "view", str(SIEGE)])
    out = capsys.readouterr()
    assert rc == 0, out.err
    assert "stable hash" in out.out
    assert "--- " in out.out                       # at least one disassembled body header


def test_behavior_compile_report_matches_the_workspace_lane(capsys):
    """The CLI and ``behaviorscan.dry_compile`` are two copies of one dry compile; the report text
    is the observable of their slot seating, so it must be identical."""
    from ff9mapkit.workspace import behaviorscan as S      # Qt-free
    ws = S.dry_compile(SIEGE)
    assert ws.ok and not ws.problems, ws.problems
    rc = cli.main(["behavior", "compile", str(SIEGE)])
    out = capsys.readouterr()
    assert rc == 0, out.err
    assert ws.report.strip() in out.out


# ---- the one placeholder seat every dry lane shares -----------------------------------------

def test_placeholder_slots_seats_one_slot_per_member_once():
    """The contract the five lanes used to each re-implement: one slot per MEMBER of every row, TOML
    order from 2, a name seated once however many rows bind it (validate refuses a double binding,
    but the seat must not depend on that), and ``{}`` with no ``[behavior]`` table at all."""
    from ff9mapkit.content import behaviortoml as BT
    raw = {"behavior": {"unit": [{"npcs": ["a", "b"], "class": "guard"}, {"npc": "c"}]}}
    assert BT.placeholder_slots(raw) == {"a": 2, "b": 3, "c": 4}
    raw["behavior"]["unit"].append({"npcs": ["a", "d"], "class": "twice"})
    assert BT.placeholder_slots(raw) == {"a": 2, "b": 3, "c": 4, "d": 5}
    assert BT.placeholder_slots({}) == {} and BT.placeholder_slots({"behavior": {}}) == {}


def test_every_dry_lane_seats_through_placeholder_slots():
    """Source pin: the five dry lanes call ``placeholder_slots`` and none carries an inline seating any
    more (the drift this file exists for was three copies disagreeing on per-ROW vs per-MEMBER)."""
    import inspect
    from ff9mapkit import build
    from ff9mapkit.content import behaviortoml, siege
    from ff9mapkit.workspace import behaviorscan
    lanes = {"cli._cmd_behavior": cli._cmd_behavior, "behaviorscan.dry_compile": behaviorscan.dry_compile,
             "behaviortoml.published_flags": behaviortoml.published_flags,
             "siege.resolve_hireable": siege.resolve_hireable, "build.lint_flag_bands": build.lint_flag_bands}
    for name, fn in lanes.items():
        src = inspect.getsource(fn)
        assert "placeholder_slots(" in src, name
        assert "len(slots) + 2" not in src and "i + 2 for" not in src, f"{name} still seats inline"
