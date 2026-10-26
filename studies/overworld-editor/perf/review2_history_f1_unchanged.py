"""Review-2 probe (history slice, ec347747): a refused Accept whose abort fails now says "The draft is unchanged".
The refusal it keeps includes the card's own synthesized one for a job that ended WITHOUT a verdict (it died: a
traceback, a kill) -- a job that may have written half its files first. This pytest probe uses the card test's own
fixtures; the scripted Accept writes one draft file and leaves no verdict, then the abort fails as F1's test fails
it (a real abort, i.e. a pending step, raises)."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))

import pytest  # noqa: E402

from ff9mapkit.world import draft as D  # noqa: E402
import tests.test_worldforest as TW  # noqa: E402
from tests.test_worldforest import _no_real_install  # noqa: E402,F401

assert Path(D.__file__).resolve().is_relative_to(WT), D.__file__
T00 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_a_dead_accept_whose_abort_fails_is_told_the_draft_is_unchanged(app, tmp_path, monkeypatch):
    box = {}

    def answer(kind, argv):
        if kind == "check":
            return {"ok": True, "dry_run": True, "center": [26, -26], "report": {}, "blocks": [[0, 0]],
                    "written": [], "refused": None}
        d = box["tool"].draft()
        box["before"] = (d / T00).read_bytes()
        (d / T00).write_bytes(b"half a forest")          # the verb wrote one file, then died: no verdict
        return None
    tool, _panel, _changed = TW._tool(app, tmp_path, TW.Scripted(answer))
    box["tool"] = tool
    tool.place(26.04, -25.97, 3.2)
    TW._settle(tool)
    real = D.abort_step

    def fails(d):
        if (Path(d) / D.HISTORY_DIR / D._PENDING / "step.json").is_file():
            raise PermissionError(13, "a reader holds it")
        return real(d)
    monkeypatch.setattr(D, "abort_step", fails)
    tool.accept_btn.click()
    text = tool.verdict_lbl.text()
    now = (tool.draft() / T00).read_bytes()
    print("\nCARD SAYS:", text)
    print("draft file before the Accept == now?", box["before"] == now, "| now:", now[:20])
    assert "unchanged" in text and now != box["before"]   # the card says unchanged; the draft holds the half write
