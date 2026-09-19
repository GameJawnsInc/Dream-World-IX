"""The CLI ``behavior compile|view`` lane, driven end to end -- the first test that does.

The offline dry-compile exists in four places (this CLI lane, ``workspace.behaviorscan.dry_compile``,
``behaviortoml.resolve_pool`` and ``siege.resolve_hireable``). The CLI copy seated its placeholder
entry slots per UNIT ROW and read ``u["npc"]``; a CLASS row (``npcs = [...]``) has no such key, so
``behavior compile`` on the shipped ``[siege]`` example -- which desugars to four class rows --
tracebacked with ``KeyError: 'npc'`` while the Workspace rendered the same file fine. The lane now
seats per MEMBER the way ``build.py`` seats the real slots, and this file pins the CLI to the
Workspace lane so the two cannot drift apart again.
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
