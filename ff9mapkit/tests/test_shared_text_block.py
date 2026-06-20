"""Members that SHARE a ``text_block`` (the donor's real mesID) must MERGE their per-field text edits into
the single ``field/<text_block>.mes``, not last-writer-wins clobber each other.

The bug this guards (real, found in the Lindblum Castle campaign -- 21 fields share message file 22): a
verbatim member's ``[[logic_edit]]`` dialogue rewrite landed in its own build but was silently overwritten
when a PLAIN sibling sharing the block was written afterward (build_field wrote ``mes_path`` per member).
The fix lifts the ``.mes`` write into ``build_mod`` (:func:`ff9mapkit.build._reconcile_mes` /
:func:`ff9mapkit.build._write_field_mes`). ``_reconcile_mes`` takes ``[(name, base, inplace, suffix)]``."""
import pathlib

import pytest

import ff9mapkit.build as B
from ff9mapkit.build import (BuildError, FieldProject, _appended_txid_base, _assign_suffix_offsets,
                             _reconcile_mes, _SHARED_SUFFIX_STRIDE, build_mod)

EXAMPLE = pathlib.Path(__file__).resolve().parent.parent / "examples" / "vivi-hut" / "hut_int.field.toml"


def _body(*lines):
    """A minimal index-implicit ``.mes`` body: txid == position. ``[STRT=...]<text>[ENDN]`` per entry."""
    return "".join(f"[STRT=0,0]{ln}[ENDN]" for ln in lines)


BASE = _body("greeting", "a great ruler", "farewell")     # txids 0,1,2 -- the shared donor body
EDIT = _body("greeting", "a ASDF", "farewell")            # member rewrote txid 1


def test_plain_siblings_return_the_shared_base():
    # several members, none edited -> the base, written once (no clobber, no churn)
    out = _reconcile_mes(22, "us", [("A", BASE, BASE, ""), ("B", BASE, BASE, ""), ("C", BASE, BASE, "")])
    assert out == BASE


@pytest.mark.parametrize("members", [
    [("ASD", BASE, EDIT, ""), ("OBS", BASE, BASE, "")],   # editor FIRST  (plain sibling after)
    [("OBS", BASE, BASE, ""), ("ASD", BASE, EDIT, "")],   # editor LAST   (the old last-writer-wins order)
    [("P1", BASE, BASE, ""), ("ASD", BASE, EDIT, ""), ("P2", BASE, BASE, "")],   # editor in the middle
])
def test_one_editor_survives_plain_siblings_any_order(members):
    out = _reconcile_mes(22, "us", members)
    assert "a ASDF" in out and "a great ruler" not in out          # the edit is NOT clobbered
    assert "greeting" in out and "farewell" in out                 # the other donor lines are intact


def test_two_editors_disjoint_txids_merge():
    e0 = _body("HELLO", "a great ruler", "farewell")               # member X rewrote txid 0
    e2 = _body("greeting", "a great ruler", "BYE")                 # member Y rewrote txid 2
    out = _reconcile_mes(22, "us", [("X", BASE, e0, ""), ("Y", BASE, e2, ""), ("P", BASE, BASE, "")])
    assert "HELLO" in out and "BYE" in out and "a great ruler" in out


def test_two_editors_same_txid_conflict_is_a_clean_error():
    e1a = _body("greeting", "a ASDF", "farewell")
    e1b = _body("greeting", "a QWER", "farewell")
    with pytest.raises(BuildError, match="both rewrite txid 1"):
        _reconcile_mes(22, "us", [("X", BASE, e1a, ""), ("Y", BASE, e1b, "")])


def test_identical_rewrite_by_two_members_is_applied_once():
    out = _reconcile_mes(22, "us", [("X", BASE, EDIT, ""), ("Y", BASE, EDIT, "")])
    assert out.count("a ASDF") == 1 and "a great ruler" not in out


def test_different_base_dialogue_on_one_block_is_an_error():
    other = _body("greeting", "a great ruler", "farewell", "extra")   # a different donor message file
    with pytest.raises(BuildError, match="DIFFERENT base dialogue"):
        _reconcile_mes(22, "us", [("X", BASE, BASE, ""), ("Y", other, other, "")])


def test_appended_suffixes_union_when_txids_are_disjoint():
    sa = "[TXID=900][STRT=0,0]narration A[ENDN]"
    sb = "[TXID=901][STRT=0,0]narration B[ENDN]"
    out = _reconcile_mes(22, "us", [("A", BASE, BASE, sa), ("B", BASE, BASE, sb)])
    assert "narration A" in out and "narration B" in out and out.startswith(BASE)


def test_identical_suffix_from_two_members_is_deduped():
    sa = "[TXID=900][STRT=0,0]narration[ENDN]"
    out = _reconcile_mes(22, "us", [("A", BASE, BASE, sa), ("B", BASE, BASE, sa)])
    assert out.count("narration") == 1


def test_colliding_append_txids_are_a_clean_error():
    sa = "[TXID=900][STRT=0,0]A line[ENDN]"
    sb = "[TXID=900][STRT=0,0]B line[ENDN]"
    with pytest.raises(BuildError, match="collides"):
        _reconcile_mes(22, "us", [("A", BASE, BASE, sa), ("B", BASE, BASE, sb)])


def test_single_member_with_edit_returns_its_inplace():
    out = _reconcile_mes(22, "us", [("ASD", BASE, EDIT, "")])
    assert out == EDIT


# --- the upstream pieces that make a 2-editor / 2-appender shared block actually buildable ----------
class _Stub:
    """A minimal stand-in for the (text_block, suffix_txid_offset) view _assign_suffix_offsets needs."""
    def __init__(self, text_block):
        self.text_block = text_block
        self.suffix_txid_offset = 0


def test_assign_suffix_offsets_gives_shared_block_members_disjoint_windows():
    # finding 1: two members on one block must NOT both anchor their appended txids at the same base.
    a, b, c = _Stub(22), _Stub(22), _Stub(276)        # a,b share 22 ; c is alone on 276
    _assign_suffix_offsets([a, b, c])
    assert a.suffix_txid_offset == 0
    assert b.suffix_txid_offset == _SHARED_SUFFIX_STRIDE   # disjoint from a
    assert c.suffix_txid_offset == 0                       # unique block -> no shift (byte-identical output)


def test_appended_txid_base_honors_the_suffix_offset(monkeypatch):
    from ff9mapkit.content import textcarry
    monkeypatch.setattr("ff9mapkit.content.verbatim.verbatim_mes", lambda proj, lang: "")  # donor max -> floor

    class P:
        suffix_txid_offset = 2 * _SHARED_SUFFIX_STRIDE
    # base = CARRY_BASE_TXID floor + the member's disjoint-window offset -> its appended lines (and the .eb
    # WindowSync that reads the SAME base) land in a window no sibling on the block can reach.
    assert _appended_txid_base(P(), ["us"]) == textcarry.CARRY_BASE_TXID + 2 * _SHARED_SUFFIX_STRIDE


def test_build_mod_rejects_duplicate_member_names(tmp_path):
    # finding 5: two members with the same name would clobber each other's EVT_<name>.eb / FBG / mapconfig.
    p = FieldProject.load(EXAMPLE)
    q = FieldProject.load(EXAMPLE)                     # same name + id
    with pytest.raises(BuildError, match="share the field name"):
        build_mod([p, q], tmp_path)
