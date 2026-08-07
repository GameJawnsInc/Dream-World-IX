"""The semantic toml diff + the deploy snapshot (editor/tomldiff.py, editor/deploysnap.py).

Pure and Qt-free, so this is where the reasoning lives. The GUI half is fenced in test_workspace_drift.py.

THE CLAIM UNDER TEST is that a project diff is worth having only if it is SEMANTIC: an index-matched diff
reports one deleted array entry as N changed entries, and a TEXT diff reports the kit serializer's own
re-ordering as a total rewrite. Both failure modes get an explicit fence here, because both are what a
reader would reach for first.
"""

from __future__ import annotations

import copy
import datetime
import json
import os
import tomllib
from pathlib import Path

import pytest

from ff9mapkit.editor import deploysnap, tomldiff

KIT = Path(__file__).resolve().parents[1]


@pytest.fixture
def field():
    """A real bundled field.toml, given three npcs so array identity is demonstrable."""
    d = tomllib.loads((KIT / "examples/boletta/boletta.field.toml").read_text(encoding="utf-8"))
    d["npc"] = [dict(d["npc"][0], name=n, pos=p) for n, p in
                (("Ada", [10, 20]), ("Bo", [30, 40]), ("Cy", [50, 60]))]
    return d


@pytest.fixture
def snapdir(tmp_path, monkeypatch):
    """Snapshots land in a tmp dir -- never provision.cache_dir(), which is the developer's checkout.

    A TEST THAT WRITES THE DEVELOPER'S REAL STATE IS THE DEFECT THIS SUITE HAS PAID FOR THREE TIMES
    (studies/gui-aesthetics/STATE.md: "the review's best find is always me touching the developer's machine
    from a test"). Patched at the module's own accessor, so no env var with wider meaning is involved.
    """
    monkeypatch.setattr(deploysnap, "snap_dir", lambda: tmp_path / "deploysnap")
    return tmp_path


# ------------------------------------------------------------------ array identity: the whole point
def test_deleting_the_first_of_three_entries_is_ONE_change(field):
    """THE INDEX TRAP. Matched by position, dropping npc #0 reports npc[0] changed + npc[1] changed +
    npc[2] removed -- three rows for one edit, which is a text diff wearing a schema's clothes."""
    after = copy.deepcopy(field)
    after["npc"] = after["npc"][1:]
    changes = tomldiff.diff(field, after)
    assert len(changes) == 1, [c.render() for c in changes]
    assert changes[0].kind == tomldiff.REMOVED
    assert 'name="Ada"' in changes[0].where


def test_reordering_an_array_is_NOT_a_change(field):
    """A toml array's order is not its meaning for keyed kinds, and the kit's serializer rewrites order
    freely -- so a diff that reported this would cry wolf on every save."""
    after = copy.deepcopy(field)
    after["npc"] = list(reversed(after["npc"]))
    assert tomldiff.diff(field, after) == []


def test_the_key_is_derived_from_the_union_of_both_sides():
    """A key unique on ONE side can collide on the other. Measured in the corpus: two gateways to the same
    `to`. Derived from the old side alone, `to` looks unique and the new side's two entries collapse."""
    old = {"gateway": [{"to": 30003, "requires_flag": 8602}, {"to": 30004, "requires_flag": 8603}]}
    new = {"gateway": [{"to": 30003, "requires_flag": 8602}, {"to": 30003, "requires_flag": 8603}]}
    key = tomldiff.derive_key(old["gateway"], new["gateway"])
    assert key is not None and "to" not in key, f"a colliding field must not be the key (got {key})"
    changes = tomldiff.diff(old, new)
    assert len(changes) == 1 and changes[0].kind == tomldiff.CHANGED, [c.render() for c in changes]


def test_eligibility_comes_from_the_data_and_the_preference_only_ranks():
    """THE FIX FOR A ROTTING TABLE. The first design gated keys through a candidate LIST, and measured over
    the repo it missed `requires_flag` and `give_folklore` -- both perfect keys, both simply unlisted. The kit
    grows a new block most weeks, so eligibility must come from the entries themselves."""
    entries = [{"zone": [[0, 0]], "give_folklore": "Mist Wraith"},
               {"zone": [[9, 9]], "give_folklore": "Village of Dali"}]
    key = tomldiff.derive_key(entries, entries)
    assert key == ("give_folklore",), f"an unlisted but unique field must still key (got {key})"
    # ...and a field NOT in the preference list still beats one that is, if the listed one does not work
    listed_but_useless = [{"name": "same", "seq": 1}, {"name": "same", "seq": 2}]
    assert tomldiff.derive_key(listed_but_useless, listed_but_useless) == ("seq",)


def test_a_nested_array_value_can_be_the_key():
    """A zone is a quad (a list of lists). `repr` keys so an entry distinguished only by geometry still
    matches -- the alternative silently fell back to index for every zone-only array."""
    a = [{"zone": [[0, 0], [1, 1]]}, {"zone": [[5, 5], [6, 6]]}]
    assert tomldiff.derive_key(a, a) == ("zone",)


def test_an_ordered_script_keeps_index_identity():
    """`cutscene.steps` is the corpus's one genuinely index-only array, and that is CORRECT: a beat's identity
    in a script is its position. Keying it by `actor` would report a re-ordered scene as unrelated edits."""
    a = {"cutscene": [{"flag": 8712, "steps": [{"say": "one"}, {"say": "two"}]}]}
    b = {"cutscene": [{"flag": 8712, "steps": [{"say": "one"}, {"say": "TWO"}]}]}
    changes = tomldiff.diff(a, b)
    assert len(changes) == 1
    assert "#1" in changes[0].where, f"a step is identified by POSITION ({changes[0].where})"
    assert changes[0].kind == tomldiff.CHANGED


def test_an_array_label_keeps_its_parent_path():
    """Rebuilding a label from the array's own name dropped every parent segment, so a nested array's rows
    silently lost their context (found on a campaign member's file)."""
    a = {"outer": {"npc": [{"name": "A", "pos": [0, 0]}]}}
    b = {"outer": {"npc": [{"name": "A", "pos": [1, 1]}]}}
    where = tomldiff.diff(a, b)[0].where
    assert where.startswith("outer"), where
    assert "npc" in where and 'name="A"' in where


# ------------------------------------------------------------------ rendering
def test_a_table_path_joins_with_a_dot_and_an_entry_label_with_an_arrow(field):
    after = copy.deepcopy(field)
    after["camera"]["frame"]["back"] = 180
    after["npc"][0]["pos"] = [99, 99]
    rendered = [c.render() for c in tomldiff.diff(field, after)]
    assert any(r.startswith("camera.frame.back:") for r in rendered), rendered
    assert any("→ pos:" in r for r in rendered), rendered


def test_a_long_value_is_elided_because_a_row_is_a_label(field):
    after = copy.deepcopy(field)
    after["npc"][0]["dialogue"] = "x" * 400
    row = tomldiff.diff(field, after)[0].render()
    assert len(row) < 200, "a diff row must stay a label, not become a payload"
    assert "…" in row


def test_summarize_is_the_single_owner_of_the_count_wording():
    assert tomldiff.summarize([]) == "no changes"
    assert tomldiff.summarize([1]) == "1 change"
    assert tomldiff.summarize([1, 2]) == "2 changes"


# ------------------------------------------------------------------ the snapshot
def test_a_snapshot_round_trips_and_reports_no_changes(snapdir, field):
    proj = snapdir / "x.field.toml"
    assert deploysnap.write(proj, {"x.field.toml": field}, dest=("test",), field_id=4004)
    snap = deploysnap.read(proj)
    assert snap["dest"] == ["test"] and snap["field_id"] == 4004
    assert deploysnap.changes(snap, {"x.field.toml": field}) == []


def test_a_datetime_does_not_read_as_a_change_forever(snapdir):
    """TOML has first-class dates, so tomllib can return datetime objects that JSON cannot hold. Stored
    stringified and compared against a live datetime, EVERY refresh would report a change. Both sides are
    normalized instead -- and this is the fence that says so."""
    data = {"meta": {"stamp": datetime.datetime(2026, 7, 24, 12, 0, 0),
                     "day": datetime.date(2026, 7, 24)}}
    proj = snapdir / "d.toml"
    deploysnap.write(proj, {"d.toml": data})
    assert deploysnap.changes(deploysnap.read(proj), {"d.toml": data}) == []


def test_a_corrupt_or_absent_snapshot_reads_as_absent(snapdir):
    """A truncated write must degrade to the honest 'never deployed' state, never to a traceback."""
    proj = snapdir / "broken.toml"
    assert deploysnap.read(proj) is None
    d = deploysnap.snap_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{deploysnap.key_for(proj)}.json").write_text("{not json", encoding="utf-8")
    assert deploysnap.read(proj) is None


def test_a_future_schema_reads_as_absent(snapdir):
    """Rather than half-interpreting a payload shape it does not know."""
    proj = snapdir / "s.toml"
    deploysnap.write(proj, {"s.toml": {"a": 1}})
    p = deploysnap.snap_dir() / f"{deploysnap.key_for(proj)}.json"
    payload = json.loads(p.read_text(encoding="utf-8"))
    payload["schema"] = deploysnap._SCHEMA + 99
    p.write_text(json.dumps(payload), encoding="utf-8")
    assert deploysnap.read(proj) is None


def test_write_never_raises_on_an_unwritable_cache(snapdir, monkeypatch):
    """NEVER LOAD-BEARING: a deploy must not fail because the cache cannot be written. Same rule deploylog
    states -- and the same SCOPE: only filesystem errors are swallowed, because "a silent swallow of a
    TypeError is how a guard rots".

    The mechanism is a real one: a FILE sitting where the snapshot directory should be, so mkdir raises
    NotADirectoryError/FileExistsError. (The first cut used a NUL byte in the path, which raises ValueError --
    not an OSError, and not a situation any machine is ever in. It failed, correctly, and the lesson is about
    the fence rather than the code: an unrealistic failure mechanism tests the wrong except clause.)
    """
    blocker = snapdir / "blocked"
    blocker.write_text("i am a file, not a directory", encoding="utf-8")
    monkeypatch.setattr(deploysnap, "snap_dir", lambda: blocker / "deploysnap")
    assert deploysnap.write(snapdir / "p.toml", {"p.toml": {"a": 1}}) is None
    assert deploysnap.read(snapdir / "p.toml") is None, "and reading it back is absent, not an exception"


@pytest.mark.skipif(os.name != "nt",
                    reason="normcase is identity on POSIX -- two spellings ARE two files there")
def test_the_key_is_case_insensitive_on_one_path(snapdir):
    """Windows paths are case-insensitive; two spellings of one project must not mint two snapshots."""
    a = deploysnap.key_for(Path("C:/Some/Proj/field.toml"))
    b = deploysnap.key_for(Path("c:/some/proj/FIELD.toml".replace("FIELD", "field")))
    assert a == b


def test_a_member_appearing_is_one_change_not_forty(snapdir, field):
    """Adding a room to a campaign is ONE edit. Naming every key inside the new file would bury that."""
    snap = {"schema": 1, "files": deploysnap.capture({"campaign.toml": {"c": 1}, "A": field})}
    changes = deploysnap.changes(snap, {"campaign.toml": {"c": 1}, "A": field, "B": field})
    assert len(changes) == 1
    assert changes[0].kind == tomldiff.ADDED and changes[0].file == "B"
    assert changes[0].where == "", "a whole-file change has no path WITHIN the file"
    assert changes[0].render() == "B added  (tables=7)", changes[0].render()


def test_changes_are_tagged_with_their_file_only_when_there_are_several(snapdir, field):
    """`file` is separate from `where` so a UI can GROUP by file -- and a single-file project's rows carry
    no file at all (a prefix nobody needs is noise)."""
    after = copy.deepcopy(field)
    after["camera"]["pitch"] = 45.0
    one = deploysnap.changes({"schema": 1, "files": deploysnap.capture({"a": field})}, {"a": after})
    assert one and all(c.file == "" for c in one)
    two = deploysnap.changes({"schema": 1, "files": deploysnap.capture({"a": field, "b": field})},
                             {"a": after, "b": field})
    assert two and all(c.file == "a" for c in two)


def test_age_str_is_coarse_and_survives_a_missing_stamp():
    now = 1_000_000.0
    assert deploysnap.age_str({"when": now - 5}, now=now) == "moments ago"
    assert deploysnap.age_str({"when": now - 600}, now=now) == "10 minutes ago"
    assert deploysnap.age_str({"when": now - 7200}, now=now) == "2 hours ago"
    assert deploysnap.age_str({"when": now - 3 * 86400}, now=now) == "3 days ago"
    assert deploysnap.age_str(None) == "at an unknown time"
    assert deploysnap.age_str({"when": "nonsense"}) == "at an unknown time"


# ------------------------------------------------------------------ the two diffs a reader would reach for
def test_a_text_diff_would_report_a_rewrite_where_this_reports_nothing(field):
    """WHY NOT difflib ON THE FILE. The kit's serializer preserves neither comments nor key order (its
    contract is round-trip VALUE equality), so the first GUI save of a hand-written toml rewrites the whole
    document. This asserts the two disagree -- i.e. that the semantic diff is buying something real."""
    import difflib

    from ff9mapkit.editor import model
    original = (KIT / "examples/boletta/boletta.field.toml").read_text(encoding="utf-8")
    resaved = model.dumps(tomllib.loads(original))
    text_changed = sum(1 for line in difflib.unified_diff(original.splitlines(), resaved.splitlines())
                       if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
    assert text_changed > 20, "a re-save really does move a lot of TEXT (that is the premise)"
    assert tomldiff.diff(tomllib.loads(original), tomllib.loads(resaved)) == [], \
        "...and zero MEANING -- which is the whole reason this is not a text diff"


def test_a_rename_reads_as_a_remove_plus_an_add_and_that_is_stated(field):
    """AN HONEST LIMIT, fenced so it stays honest rather than becoming a surprise. Matching by identity
    cannot see intent (git has the same problem with files); the module docstring says so."""
    after = copy.deepcopy(field)
    after["npc"][0]["name"] = "Adabelle"
    kinds = sorted(c.kind for c in tomldiff.diff(field, after))
    assert kinds == [tomldiff.ADDED, tomldiff.REMOVED]
    assert "rename" in tomldiff.__doc__.lower(), "the limit must be documented where a reader will find it"
