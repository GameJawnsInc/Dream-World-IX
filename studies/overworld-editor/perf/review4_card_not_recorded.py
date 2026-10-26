"""Review-4 probe (1fd9d1fa), the card itself: the REAL ForestTool (offscreen, the tests' Scripted runner and
synthetic island), two Accepts; during the second a reader holds history.json open (a real Windows refusal of
_write_history's replace, after the pending rename went through). The card's take-back finds no pending step, returns
cleanly, and the card says "the write was taken back and the draft is as it was" -- the write is in the draft, and no
step records it.

Run from ff9mapkit/:
  py -m pytest ../studies/overworld-editor/perf/review4_card_not_recorded.py -q -s -p no:cacheprovider
      --basetemp=../studies/overworld-editor/out/perf/review4/card_not_recorded"""
from __future__ import annotations

from ff9mapkit.world import draft as D
from tests.test_worldforest import Scripted, _no_real_install, _settle, _tool, app  # noqa: F401

REL = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"


def test_card_says_taken_back_over_an_unrecorded_write(app, tmp_path):  # noqa: F811
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    ok, n = Scripted().answer, []

    def answer(kind, argv):
        if kind == "accept":
            n.append(1)
            (draft / REL).write_bytes(b"forest %d" % len(n))              # the verb wrote the draft
        return ok(kind, argv)
    tool, _panel, _changed = _tool(app, tmp_path, Scripted(answer))
    tool.place(26.04, -25.97, 3.2)
    _settle(tool)
    tool.accept_btn.click()                                               # Accept 1: recorded
    assert D.history(draft)["cursor"] == 1
    tool.place(26.04, -25.97, 3.2)
    _settle(tool)
    held = open(draft / D.HISTORY, "rb")                                  # the window's thread reads the history
    try:
        tool.accept_btn.click()                                           # Accept 2
    finally:
        held.close()
    text = tool.verdict_lbl.text()
    h = D.history(draft)
    print("\nCARD:", text)
    print("draft file:", (draft / REL).read_bytes(), "| history cursor", h["cursor"], [s["label"] for s in h["steps"]],
          "| recorded after of step 1:", h["steps"][0]["after"].get(REL, "")[:12])
    print("orphan step folder history/0001:", (draft / D.HISTORY_DIR / "0001").is_dir(),
          "| pending:", (draft / D.HISTORY_DIR / D._PENDING).exists())
    try:
        D.undo(draft)
        print("Undo went through")
    except ValueError as e:
        print("Undo:", e)
    assert "the write was taken back and the draft is as it was" in text
    assert (draft / REL).read_bytes() == b"forest 2"                       # ...but it was not
