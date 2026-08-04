""".ff9build.json -- the build stamp and its diff.

The gate this exists for: a member's story-flag window is `flag_base + i * flags_per_field` over its
POSITION in the manifest and is stored nowhere, so deleting or reordering a `[[field]]` row -- or a
recompose resetting flags_per_field -- slides every later member's save-persistent bits with nothing
able to detect it. The stamp is the missing baseline.
"""

from __future__ import annotations

import json

import pytest

from ff9mapkit import stamp


class _P:
    """A FieldProject stand-in: the stamp only reads name/id/text_block/flag_base/flags_per_field."""

    def __init__(self, name, fid, tb=None, flag_base=None, width=64):
        self.name, self.id = name, fid
        self.text_block = tb if tb is not None else fid
        self.flag_base, self.flags_per_field = flag_base, width


def _stamp(projects, **kw):
    return stamp.compute(projects, mod_name="M", **kw)


def test_a_stamp_records_the_resolution_not_just_the_identity(tmp_path):
    s = _stamp([_P("A", 6000, flag_base=8712), _P("B", 6001, flag_base=8776)])
    a, b = s["members"]
    assert (a["name"], a["id"], a["flag_lo"], a["flag_hi"]) == ("A", 6000, 8712, 8775)
    assert (b["name"], b["id"], b["flag_lo"], b["flag_hi"]) == ("B", 6001, 8776, 8839)
    assert s["kit_version"] and s["built_utc"].endswith("Z")


def test_round_trip_through_disk(tmp_path):
    s = _stamp([_P("A", 6000, flag_base=8712)])
    stamp.write(tmp_path, s)
    assert (tmp_path / stamp.STAMP_NAME).is_file()
    assert stamp.read(tmp_path) == s


@pytest.mark.parametrize("label, kw, want_blocking", [
    # a real journey rebase: EVERY member shifts by one delta and keeps its width
    ("uniform rebase of all members",
     dict(moved_flags=[("A", (8712, 8775), (9000, 9063)), ("B", (8776, 8839), (9064, 9127))]), False),
    # the case the first version missed: a delete slides ONE member, and an interleaved standalone build
    # flips the context, so the drift shipped labelled as the journey's assignment
    ("only one of two members slid", dict(moved_flags=[("B", (8776, 8839), (8712, 8775))]), True),
    ("non-uniform deltas",
     dict(moved_flags=[("A", (8712, 8775), (9000, 9063)), ("B", (8776, 8839), (9200, 9263))]), True),
    ("flags_per_field changed under it",
     dict(moved_flags=[("A", (8712, 8775), (9000, 9015)), ("B", (8776, 8839), (9016, 9031))]), True),
    ("a member vanished too", dict(moved_flags=[("A", (8712, 8775), (9000, 9063))], removed=["C"]), True),
])
def test_a_context_flip_exempts_only_the_moves_a_rebase_explains(label, kw, want_blocking):
    """A standalone build and a journey build share one <campaign>/dist/.ff9build.json, so the context flips
    routinely -- the Workspace's Build-campaign button is a bare build-all. Exempting EVERY moved window on a
    flip therefore disarmed the gate for exactly the workflow it was written for."""
    d = stamp.StampDiff(total=2, context_changed=("standalone", "journey"), **kw)
    assert d.blocking is want_blocking, label
    assert d.changed, "a context flip must never render as 'unchanged' -- the saves are not interchangeable"


def test_without_a_context_flip_any_moved_window_blocks():
    d = stamp.StampDiff(total=2, moved_flags=[("A", (8712, 8775), (9000, 9063))])
    assert d.blocking is True


def test_every_verb_that_can_hit_the_refusal_accepts_the_flag_it_advertises():
    """refusal() ends "re-run with --reflow-flags". It shipped on build-all and deploy-campaign only, while
    `build`, `deploy-journey` and tools/deploy_campaign.py can all raise it -- so the escape hatch the
    message named was rejected by the command that printed it, and the only way through was deleting
    .ff9build.json, which disarms the gate for that folder permanently."""
    import argparse

    from ff9mapkit import cli
    d = stamp.StampDiff(moved_flags=[("A", (8712, 8775), (8776, 8839))], total=1)
    assert "--reflow-flags" in d.refusal(), "the refusal no longer names the flag -- update this test"

    parser = cli.build_parser()
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    for verb in ("build", "build-all", "deploy-campaign", "deploy-journey"):
        opts = {s for a in sub.choices[verb]._actions for s in a.option_strings}
        assert "--reflow-flags" in opts, f"ff9mapkit {verb} can raise the refusal but rejects its own advice"


def _finalized(root, **kw):
    root.mkdir(parents=True, exist_ok=True)
    s = dict(stamp_version=1, kit_version="x", built_utc="now", mod_name="M",
             context="standalone", source=None, members=[], **kw)
    s = stamp.finalize(s, root)
    stamp.write(root, s)
    return s


def test_the_digest_covers_the_build_and_excludes_the_stamp(tmp_path):
    """The resolution table answers "did a member's window move". It cannot answer "is what is INSTALLED
    still what the build produced" -- and nothing else could either: ModDescription.xml carries no id, and
    the ledger records that an id was deployed, not what bytes landed."""
    (tmp_path / "sub").mkdir()
    (tmp_path / "DictionaryPatch.txt").write_text("FieldScene 6000 11 10 A 6000\n", encoding="utf-8")
    (tmp_path / "sub" / "EVT_A.eb.bytes").write_bytes(b"\x01\x02\x03")
    s = _finalized(tmp_path)
    assert set(s["files"]) == {"DictionaryPatch.txt", "sub/EVT_A.eb.bytes"}
    assert stamp.STAMP_NAME not in s["files"], "the stamp must not hash itself"
    assert "/" in "sub/EVT_A.eb.bytes", "keys are POSIX -- a stamp travels from a dist to an install"
    assert stamp.verify(tmp_path).clean


@pytest.mark.parametrize("mutate, field_name", [
    (lambda p: (p / "sub" / "EVT_A.eb.bytes").write_bytes(b"\x01\x02\x04"), "changed"),   # hand-edited install
    (lambda p: (p / "sub" / "EVT_A.eb.bytes").unlink(), "missing"),                       # half-finished copy
    (lambda p: (p / "STRAY.txt").write_text("x", encoding="utf-8"), "extra"),             # foreign leftovers
])
def test_verify_catches_every_drift_class(tmp_path, mutate, field_name):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "EVT_A.eb.bytes").write_bytes(b"\x01\x02\x03")
    _finalized(tmp_path)
    assert stamp.verify(tmp_path).clean
    mutate(tmp_path)
    rep = stamp.verify(tmp_path)
    assert not rep.clean and getattr(rep, field_name), rep.render()


def test_a_stamp_without_a_digest_reports_identity_and_no_false_drift(tmp_path):
    """Folders deployed before content hashing existed must say so, not invent drift -- a check that cries
    wolf on every pre-existing install is one nobody reads."""
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    s = _finalized(tmp_path)
    stamp.write(tmp_path, {k: v for k, v in s.items() if k != "files"})
    rep = stamp.verify(tmp_path)
    assert rep.has_stamp and not rep.has_digest
    assert rep.missing == [] and rep.changed == [] and rep.extra == []
    assert "identity only" in rep.render()


def test_verify_on_a_folder_with_no_stamp_says_so(tmp_path):
    rep = stamp.verify(tmp_path)
    assert not rep.has_stamp and f"NO {stamp.STAMP_NAME}" in rep.render()


def test_a_missing_or_malformed_stamp_reads_as_none(tmp_path):
    assert stamp.read(tmp_path) is None                       # first build
    (tmp_path / stamp.STAMP_NAME).write_text("{ not json", encoding="utf-8")
    assert stamp.read(tmp_path) is None
    (tmp_path / stamp.STAMP_NAME).write_text('{"members": "nope"}', encoding="utf-8")
    assert stamp.read(tmp_path) is None


def test_no_prior_stamp_is_silent_not_a_change(tmp_path):
    d = stamp.diff(None, _stamp([_P("A", 6000, flag_base=8712)]))
    assert not d.changed and not d.blocking


# ---- the blocking class ------------------------------------------------------------------
def test_a_moved_flag_window_blocks(tmp_path):
    """The whole point: deleting the middle member of a 3-field campaign slides the third member's
    window down by one block, and its save-persistent bits move with it."""
    old = _stamp([_P("A", 6000, flag_base=8712), _P("B", 6001, flag_base=8776),
                  _P("C", 6002, flag_base=8840)])
    new = _stamp([_P("A", 6000, flag_base=8712), _P("C", 6002, flag_base=8776)])
    d = stamp.diff(old, new)
    assert d.blocking
    assert d.removed == ["B"]
    assert d.moved_flags == [("C", (8840, 8903), (8776, 8839))]
    assert "8840-8903 -> 8776-8839" in d.refusal()
    assert "--reflow-flags" in d.refusal()


def test_a_moved_text_block_blocks(tmp_path):
    old = _stamp([_P("A", 6000, tb=6000, flag_base=8712)])
    new = _stamp([_P("A", 6000, tb=20000, flag_base=8712)])
    assert stamp.diff(old, new).blocking


def test_flags_per_field_change_moves_every_later_window(tmp_path):
    """The recompose bug's signature: flags_per_field 16 -> 64 relocates every member after the first."""
    old = _stamp([_P("A", 6000, flag_base=9000, width=16), _P("B", 6001, flag_base=9016, width=16)])
    new = _stamp([_P("A", 6000, flag_base=8712, width=64), _P("B", 6001, flag_base=8776, width=64)])
    d = stamp.diff(old, new)
    assert d.blocking and len(d.moved_flags) == 2


# ---- reported but NOT blocking -----------------------------------------------------------
def test_an_id_move_is_reported_not_blocked(tmp_path):
    """reid is the sanctioned way to move ids, and lint (e3) + reid's own report already make it loud.
    Blocking here would make every reid need --reflow-flags and train the flag away."""
    old = _stamp([_P("A", 6000, tb=6000, flag_base=8712)])
    new = _stamp([_P("A", 6500, tb=6500, flag_base=8712)])
    d = stamp.diff(old, new)
    assert d.moved_ids == [("A", 6000, 6500)] and not d.blocking


def test_diffing_keys_on_NAME_so_a_reid_is_not_a_wholesale_replacement(tmp_path):
    """Keying on id would report every reid as remove-all + add-all and hide any flag drift underneath."""
    old = _stamp([_P("A", 6000, flag_base=8712), _P("B", 6001, flag_base=8776)])
    new = _stamp([_P("A", 6500, flag_base=8712), _P("B", 6501, flag_base=8776)])
    d = stamp.diff(old, new)
    assert not d.added and not d.removed and len(d.moved_ids) == 2


def test_a_context_change_is_reported_not_blocked(tmp_path):
    """A journey assigns its campaigns' flag/text windows and builds into the SAME dist as a standalone
    build. Blocking that would fire on every alternation and train the author to always pass the flag."""
    old = _stamp([_P("A", 6000, tb=6000, flag_base=8712)], context="standalone")
    new = _stamp([_P("A", 6000, tb=20000, flag_base=12000)], context="journey")
    d = stamp.diff(old, new)
    assert d.moved_flags and d.moved_blocks, "the moves are still detected"
    assert not d.blocking, "but a context change is the assignment working, not drift"
    assert "NOT interchangeable" in d.render()


def test_appending_a_member_does_not_move_the_others(tmp_path):
    """Append-only growth is the safe edit -- it must stay silent, or the gate cries wolf."""
    old = _stamp([_P("A", 6000, flag_base=8712)])
    new = _stamp([_P("A", 6000, flag_base=8712), _P("B", 6001, flag_base=8776)])
    d = stamp.diff(old, new)
    assert d.added == ["B"] and not d.blocking


def test_render_says_n_of_m(tmp_path):
    old = _stamp([_P("A", 6000, flag_base=8712), _P("B", 6001, flag_base=8776)])
    new = _stamp([_P("A", 6500, flag_base=8712), _P("B", 6001, flag_base=8776)])
    assert "1 of 2 members changed" in stamp.diff(old, new).render()
    assert "unchanged" in stamp.diff(old, old).render()
