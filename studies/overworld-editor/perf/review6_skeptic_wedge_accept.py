"""Review-6 skeptic probe (R6-1's consequence): after finish_edit's refused history write and one cancel, the edit
stays open with its lifted records gone. A new step accepted into that draft (a card's Accept: begin_step +
commit_step) is then undone and its record deleted by the next cancel -- the bar's refresh runs one automatically.

Run from ff9mapkit/:
  py -m pytest ../studies/overworld-editor/perf/review6_skeptic_wedge_accept.py -q -s -p no:cacheprovider
      --basetemp=../studies/overworld-editor/out/perf/review6/skeptic_wedge_accept"""
from __future__ import annotations

import pytest

from ff9mapkit.world import draft as D
from tests.test_world_forestedit import _no_real_install  # noqa: F401
from tests.test_worldrecipe import T10, _edited_one_of_two, _step, _tree


def test_the_wedge_eats_the_next_accept(tmp_path, monkeypatch):
    d, before, h0 = _edited_one_of_two(tmp_path)
    assert D.replay(d, D.history(d)["edit"]["lifted"][1])
    real = D._write_history
    monkeypatch.setattr(D, "_write_history",
                        lambda *a: (_ for _ in ()).throw(PermissionError(13, "a reader holds history.json")))
    with pytest.raises(PermissionError):
        D.finish_edit(d)
    monkeypatch.setattr(D, "_write_history", real)
    with pytest.raises(ValueError):
        D.cancel_edit(d)
    h = D.history(d)
    print(f"\n[wedged] cursor {h['cursor']} of {[s['label'] for s in h['steps']]}, edit open {bool(h['edit'])}")
    _step(d, [(1, 0)], {T10: b"a new accept"}, "a card's accept")
    h = D.history(d)
    after_accept = _tree(d)
    print(f"[a card accepts] cursor {h['cursor']} of {[s['label'] for s in h['steps']]}")
    try:
        D.cancel_edit(d)
    except ValueError as err:
        print(f"[the next refresh's cancel] ValueError: {err}")
    h = D.history(d)
    print(f"   cursor {h['cursor']} of {[s['label'] for s in h['steps']]}, edit open {bool(h['edit'])}; "
          f"draft == after the accept: {_tree(d) == after_accept}; "
          f"step folders: {sorted(p.name for p in (d / D.HISTORY_DIR).iterdir() if p.is_dir())}")
