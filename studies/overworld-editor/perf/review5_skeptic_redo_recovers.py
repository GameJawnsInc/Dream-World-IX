"""Review-5 skeptic probe for R5-2: after the cancel whose second redo was refused, is anything LOST, or does the
bar's Redo put the draft back exactly as it was (bytes == what the history says)?

Run from ff9mapkit/:
  py -m pytest ../studies/overworld-editor/perf/review5_skeptic_redo_recovers.py -q -s -p no:cacheprovider
      --basetemp=../studies/overworld-editor/out/perf/review5/skeptic_redo_recovers"""
from __future__ import annotations

from pathlib import Path

from ff9mapkit.world import draft as D
from ff9mapkit.world import recipe as RC
from tests.test_world_forestedit import _no_real_install  # noqa: F401
from tests.test_worldrecipe import _doc, _tree, _two_islands, app  # noqa: F401


def test_redo_recovers(monkeypatch, tmp_path, app):  # noqa: F811
    game = _two_islands(monkeypatch, tmp_path)
    saved = tmp_path / "two.toml"
    saved.write_text(RC.dumps([{"table": "forest", "center": [26.0, -26.0], "donor": "15,15"},
                               {"table": "mountain", "center": [90.0, -26.0], "donor": "0,0"}]), encoding="utf-8")
    doc, _run = _doc(app, game, tmp_path, saved)
    doc.set_view_mode("3d", sync=True)
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    doc._recipe.open_btn.click()
    composed = _tree(draft)
    D.undo(draft)
    one = _tree(draft)                                   # the draft with only the forest applied
    D.redo(draft)
    bar = doc._recipe
    bar.refresh()
    bar.select(0)
    bar.edit_btn.click()
    tool = doc._forest
    real, calls = D.redo, []

    def redo(d):
        calls.append(1)
        if len(calls) != 2:
            return real(d)
        held = open(Path(d) / D.HISTORY, "rb")
        try:
            return real(d)
        finally:
            held.close()
    monkeypatch.setattr(D, "redo", redo)
    tool.close_btn.click()
    monkeypatch.setattr(D, "redo", real)
    h = D.history(draft)
    print(f"\n[after the refused cancel] cursor {h['cursor']} of {len(h['steps'])}, edit open {bool(h['edit'])} | "
          f"draft == 'forest only' (what cursor 1 says): {_tree(draft) == one} | leftover park dir: "
          f"{(draft / D.HISTORY_DIR / D.EDIT_DIR).exists()}")
    bar.select(None)
    print("   bar (no pick):", repr(bar.status_lbl.text()), "| Redo enabled:", bar.redo_btn.isEnabled())
    bar.redo_btn.click()
    h = D.history(draft)
    print(f"[after Redo] cursor {h['cursor']} | draft == the recipe as it was: {_tree(draft) == composed} | bar: "
          f"{bar.status_lbl.text()!r}")
