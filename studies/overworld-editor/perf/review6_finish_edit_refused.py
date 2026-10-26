"""Review-6 probe (finish_edit, C9; unguarded by rounds 4-5): an edit's close whose history write the disk refuses.

finish_edit deletes the parked lifted records (history/edit/) FIRST and only then writes the history with the edit
closed. A write refused there (a reader holding history.json past _retry's 3 s, the refusal class rounds 4-5 handle
everywhere else) leaves the history saying the edit is open, its lifted steps parked under history/edit/ -- which no
longer exist. The next cancel (the bar's Cancel edit, the only button it shows then, or the next launch's refresh,
automatically) undoes every put-back step, drops them from the history and deletes their folders, then finds the
lifted records gone and raises ValueError: the edited step and every step after it are lost, the edit stays open.

Run from ff9mapkit/:
  py -m pytest ../studies/overworld-editor/perf/review6_finish_edit_refused.py -q -s -p no:cacheprovider
      --basetemp=../studies/overworld-editor/out/perf/review6/finish_edit_refused"""
from __future__ import annotations

import pytest

from ff9mapkit.world import draft as D
from tests.test_world_forestedit import _no_real_install  # noqa: F401
from tests.test_worldrecipe import _edited_one_of_two, _tree


def _say(tag, d):
    h = D.history(d)
    e = h["edit"]
    print(f"[{tag}] cursor {h['cursor']} of {[s['label'] for s in h['steps']]}; edit open {bool(e)}"
          + (f" (lifted {[s['dir'] for s in e.get('lifted', [])]}, parked folders exist "
             f"{[(d / s['dir']).is_dir() for s in e.get('lifted', [])]})" if e else "")
          + f"; step folders exist {[(d / s['dir']).is_dir() for s in h['steps']]}")


def test_a_finish_whose_history_write_is_refused(tmp_path, monkeypatch):
    d, before, h0 = _edited_one_of_two(tmp_path)                          # [forest one, mountain two]; edit at 0
    mountain = D.history(d)["edit"]["lifted"][1]
    assert D.replay(d, mountain)                                          # the put-back: the mountain on top
    edited = _tree(d)
    _say("edit put back, about to close", d)
    real = D._write_history
    monkeypatch.setattr(D, "_write_history",
                        lambda *a: (_ for _ in ()).throw(PermissionError(13, "a reader holds history.json")))
    with pytest.raises(PermissionError):
        D.finish_edit(d)
    monkeypatch.setattr(D, "_write_history", real)
    _say("finish_edit refused", d)
    print(f"   draft == the edited recipe: {_tree(d) == edited}")
    try:
        D.cancel_edit(d)                                                  # Cancel edit, or the next refresh's
    except ValueError as err:
        print(f"cancel_edit -> ValueError: {err}")
    _say("after the cancel", d)
    print(f"   draft == the edited recipe: {_tree(d) == edited}; == the recipe before the edit: {_tree(d) == before}")
    folders = sorted(p.relative_to(d).as_posix() for p in (d / D.HISTORY_DIR).rglob("*") if p.is_dir()
                     and p.parent.name in (D.HISTORY_DIR, D.EDIT_DIR))
    print(f"   history folders left on disk: {folders}")
