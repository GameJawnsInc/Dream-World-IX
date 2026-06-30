"""Offline tests for journey deploy (ff9mapkit.deploy.deploy_journey, extracted from tools/deploy_journey.py
-- now a thin shim). The revert renderers + name/capture helpers need no game; a dry-run uses the bundled
example manifest. The actual --apply install + in-game playtest are verified by a human (Hard Constraint §2)."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ff9mapkit import deploy

REPO = Path(__file__).resolve().parents[2]
EXAMPLE = REPO / "ff9mapkit" / "examples" / "world_hub" / "journeys.toml"


def test_render_unified_revert_runs_in_reverse_order():
    txt = deploy._render_unified_revert(["a.py", "b.py", None], "x")
    ast.parse(txt)
    assert "runpy.run_path" in txt
    assert txt.index("'b.py'") < txt.index("'a.py'")          # reverse deploy order (undo last first)
    assert "None" not in txt.split("REVERTS = [")[1].split("]")[0]   # the None step is dropped


def test_render_folder_revert_restores_snapshot(tmp_path):
    live, snap = tmp_path / "live", tmp_path / "snap"
    snap.mkdir(); (snap / "m.txt").write_text("snap", encoding="utf-8")
    live.mkdir(); (live / "stale.txt").write_text("stale", encoding="utf-8")
    txt = deploy._render_folder_revert(live, snap, "x")
    ast.parse(txt)
    exec(compile(txt, "<r>", "exec"), {})
    assert (live / "m.txt").exists() and not (live / "stale.txt").exists()


def test_render_link_revert_restores_backups(tmp_path):
    live = tmp_path / "a.eb"; live.write_bytes(b"NEW")
    bkp = tmp_path / "a.eb.bk"; bkp.write_bytes(b"OLD")
    txt = deploy._render_link_revert([{"backups": [(str(live), str(bkp))]}], "x")
    ast.parse(txt)
    exec(compile(txt, "<r>", "exec"), {})
    assert live.read_bytes() == b"OLD"


def test_capture_path_copies_and_skips_none(tmp_path):
    src = tmp_path / "revert_campaign.py"; src.write_text("print('x')", encoding="utf-8")
    dst = deploy._capture_path(str(src), tmp_path / "rv", "revert_journey_campaign_foo.py")
    assert dst and Path(dst).name == "revert_journey_campaign_foo.py"
    assert Path(dst).read_text(encoding="utf-8") == "print('x')"
    assert deploy._capture_path(None, tmp_path / "rv", "x.py") is None        # nothing to capture


@pytest.mark.skipif(not EXAMPLE.is_file(), reason="no bundled example journeys.toml")
def test_single_folder_name():
    from ff9mapkit import journey
    m = journey.load_journeys(EXAMPLE)
    assert deploy._single_folder_name(m, "X") == "FF9CustomMap-X"             # bare name -> prefixed
    assert deploy._single_folder_name(m, "FF9CustomMap-Y") == "FF9CustomMap-Y"  # already prefixed -> as-is
    assert deploy._single_folder_name(m, None).startswith("FF9CustomMap-")    # derived from the hub name


@pytest.mark.skipif(not EXAMPLE.is_file(), reason="no bundled example journeys.toml")
def test_deploy_journey_dry_run_touches_nothing(tmp_path):
    report = deploy.deploy_journey(EXAMPLE, apply=False, backups_dir=tmp_path / "bk", reverts_dir=tmp_path / "rv",
                                   verbose=False)
    assert report["ok"] is True and report["rc"] == 0 and report["revert"] is None
    assert not (tmp_path / "rv").exists() and not (tmp_path / "bk").exists()   # dry-run writes nothing
