"""`ff9mapkit reid` -- moving a campaign's field ids as a verified, comment-preserving text refactor.

The invariant under every test: OUR ids move, DONOR ids do not. Getting that backwards silently
un-forks a member (a retarget key that matches nothing, a `source` pointing at the wrong real field),
which is exactly the class reid exists to prevent rather than create.
"""

from __future__ import annotations

import json
import tomllib

import pytest

from ff9mapkit import campaign, reid

MANIFEST = """\
# A campaign the author annotated by hand -- these comments must survive a move.
[campaign]
name            = "T"
mod_folder      = "FF9CustomMap-t"
id_base         = 6000
flag_base       = 8712
flags_per_field = 64
entry_field     = "A"
entry_entrance  = 0

[[field]]
name = "A"
source = 300          # the DONOR real field -- must NOT move
id = 6000
mode = "borrow"
toml = "A/A.field.toml"

[[field]]
name = "B"
source = 301
id = 6001
mode = "borrow"
toml = "B/B.field.toml"

[[edge]]
from = "A"
to = "B"
entrance = 0
"""

MEMBER = """\
[field]
id = {fid}
name = "{nm}"
area = 11
{tb}
[camera]
borrow = "camera.bgx"

[walkmesh]
bgi = "walkmesh.bgi"

[player]
start = [0, 0]
{extra}"""


def _write(tmp_path, *, manifest=MANIFEST, a_extra="", b_extra="", a_tb="", b_tb=""):
    (tmp_path / "campaign.toml").write_text(manifest, encoding="utf-8")
    for nm, fid, extra, tb in (("A", 6000, a_extra, a_tb), ("B", 6001, b_extra, b_tb)):
        d = tmp_path / nm
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{nm}.field.toml").write_text(
            MEMBER.format(fid=fid, nm=nm, extra=extra, tb=tb), encoding="utf-8")
    return tmp_path / "campaign.toml"


def _member(tmp_path, nm):
    return tomllib.loads((tmp_path / nm / f"{nm}.field.toml").read_text(encoding="utf-8"))


def _run(cpath, **kw):
    rp = reid.plan_reid(cpath, **kw)
    reid.apply_reid(rp)
    return rp


# ---- the move itself ---------------------------------------------------------------------
def test_reid_moves_every_copy_of_a_member_id(tmp_path):
    """The id is stored twice (manifest + the member's own toml) and named again by every door."""
    cpath = _write(tmp_path, a_extra='\n[[gateway]]\nto = 6001\nentrance = 0\n')
    _run(cpath, id_base=6500)
    man = tomllib.loads(cpath.read_text(encoding="utf-8"))
    assert [f["id"] for f in man["field"]] == [6500, 6501]
    assert man["campaign"]["id_base"] == 6500
    assert _member(tmp_path, "A")["field"]["id"] == 6500
    assert _member(tmp_path, "B")["field"]["id"] == 6501
    assert _member(tmp_path, "A")["gateway"][0]["to"] == 6501, "the door followed its destination"
    assert campaign.lint_campaign(campaign.load_campaign(cpath), tmp_path)[0] == []


def test_reid_never_moves_a_donor_id(tmp_path):
    """`source`, a retarget table's KEYS and `[[seam]] to_real` all name the REAL game."""
    man = MANIFEST + '\n[[seam]]\nfrom = "A"\nto_real = 301\nkind = "portal"\nnote = ""\n'
    cpath = _write(tmp_path, manifest=man,
                   a_extra='\n[verbatim_eb]\nbin = "a.eb"\nretarget = { 300 = 6000, 301 = 6001 }\n')
    _run(cpath, id_base=6500)
    assert [f["source"] for f in tomllib.loads(cpath.read_text(encoding="utf-8"))["field"]] == [300, 301]
    rt = _member(tmp_path, "A")["verbatim_eb"]["retarget"]
    assert sorted(rt) == ["300", "301"], "donor KEYS untouched"
    assert sorted(rt.values()) == [6500, 6501], "our VALUES moved"
    assert tomllib.loads(cpath.read_text(encoding="utf-8"))["seam"][0]["to_real"] == 301


def test_text_block_moves_only_when_it_is_the_members_own_block(tmp_path):
    """An explicit block that DIFFERS from the id is the donor's real mesID, which a fork keeps (voice
    acting + dual language key off it). An ABSENT one needs no edit -- default_text_block is identity."""
    cpath = _write(tmp_path, a_tb="text_block = 6000\n", b_tb="text_block = 1073\n")
    _run(cpath, id_base=6500)
    assert _member(tmp_path, "A")["field"]["text_block"] == 6500, "own block followed the id"
    assert _member(tmp_path, "B")["field"]["text_block"] == 1073, "a DONOR block must not move"


def test_logic_edit_new_moves_only_on_a_kind_field_row(tmp_path):
    """`new` is our id on kind="field"; on kind="gil"/"flag_index" the same key holds an amount or a flag
    index, and the custom id band OVERLAPS both -- so an unconditional rewrite corrupts an unrelated number."""
    cpath = _write(tmp_path, a_extra=(
        '\n[[logic_edit]]\nkind = "field"\nentry = 0\ntag = 4\nold = 301\nnew = 6001\n'
        '\n[[logic_edit]]\nkind = "gil"\nentry = 0\ntag = 4\nold = 5\nnew = 6001\n'))
    _run(cpath, id_base=6500)
    les = _member(tmp_path, "A")["logic_edit"]
    assert les[0]["new"] == 6501, "the field-warp edit followed the move"
    assert les[0]["old"] == 301, "the donor literal in the .eb must not move"
    assert les[1]["new"] == 6001, "a GIL amount that merely looks like an id must not move"


def test_id_base_shift_preserves_gaps(tmp_path):
    """A removed member leaves a hole and _next_member_id is max+1, so compacting would reuse a retired
    id -- the one number a stale save must never land on."""
    man = MANIFEST.replace("id = 6001", "id = 6005")
    cpath = _write(tmp_path, manifest=man)
    (tmp_path / "B" / "B.field.toml").write_text(
        MEMBER.format(fid=6005, nm="B", extra="", tb=""), encoding="utf-8")
    _run(cpath, id_base=6500)
    assert [f["id"] for f in tomllib.loads(cpath.read_text(encoding="utf-8"))["field"]] == [6500, 6505]


def test_map_moves_only_the_named_ids(tmp_path):
    cpath = _write(tmp_path)
    _run(cpath, mapping=["6001=6900"])
    assert [f["id"] for f in tomllib.loads(cpath.read_text(encoding="utf-8"))["field"]] == [6000, 6900]


# ---- the file the author actually holds ---------------------------------------------------
def test_the_rewrite_is_surgical_not_a_re_render(tmp_path):
    """render_campaign_toml and editor.model.dumps both drop hand-written comments. reid must not:
    the annotated 40-field campaign is precisely the one worth moving."""
    cpath = _write(tmp_path, a_extra='\n[[gateway]]\nto = 6001   # onward to B (the vault)\n')
    before = cpath.read_text(encoding="utf-8").splitlines()
    _run(cpath, id_base=6500)
    after = cpath.read_text(encoding="utf-8").splitlines()
    assert len(before) == len(after), "no lines added or removed"
    assert [x for x in before if x.lstrip().startswith("#")] == \
           [x for x in after if x.lstrip().startswith("#")], "comment lines byte-identical"
    gw = (tmp_path / "A" / "A.field.toml").read_text(encoding="utf-8")
    assert "to = 6501   # onward to B (the vault)" in gw, "the trailing comment survived the edit"


def test_crlf_line_endings_survive(tmp_path):
    """A git checkout under autocrlf hands you CRLF. Reading with universal newlines and writing back
    would rewrite every line ending -- a three-number edit as a whole-file diff."""
    cpath = _write(tmp_path)
    for p in list(tmp_path.rglob("*.toml")):                  # normalize first: write_text already gave
        p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))   # CRLF on Windows
    _run(cpath, id_base=6500)
    for p in sorted(tmp_path.rglob("*.toml")):
        b = p.read_bytes()
        assert b.count(b"\n") == b.count(b"\r\n"), f"{p.name} lost its CRLF endings"


def test_floorplan_json_moves_too(tmp_path):
    """floorplan.json is the SOURCE OF TRUTH for a click-authored dungeon. Leave it and the next Compose
    silently re-emits the campaign at the OLD ids."""
    cpath = _write(tmp_path)
    (tmp_path / "floorplan.json").write_text(json.dumps(
        {"version": 1, "name": "T", "id_base": 6000,
         "rooms": [{"name": "A", "id": 6000}, {"name": "B", "id": 6001}]}, indent=2), encoding="utf-8")
    _run(cpath, id_base=6500)
    fp = json.loads((tmp_path / "floorplan.json").read_text(encoding="utf-8"))
    assert fp["id_base"] == 6500
    assert [r["id"] for r in fp["rooms"]] == [6500, 6501]


def test_residual_scan_reports_an_unmodelled_site(tmp_path):
    """The net under the rule table: a key reid does not model keeps its old id and is REPORTED, never
    silently shipped."""
    cpath = _write(tmp_path, a_extra='\n[some_future_block]\nwarp_somewhere = 6001\n')
    rp = reid.plan_reid(cpath, id_base=6500)
    assert any("warp_somewhere" in h for h in rp.residual), rp.residual


def test_a_flag_index_that_looks_like_an_id_is_not_reported(tmp_path):
    """The custom id band (4000-9899) OVERLAPS the flag band (8712+), so a [[flag]] index can equal an old
    field id by coincidence. Reporting it would train the author to ignore the residual list."""
    man = MANIFEST.replace("id = 6001", "id = 8800")
    cpath = _write(tmp_path, manifest=man)
    (tmp_path / "B" / "B.field.toml").write_text(
        MEMBER.format(fid=8800, nm="B", extra="\n[[chest]]\nitem = \"potion\"\nflag = 8800\n", tb=""),
        encoding="utf-8")
    rp = reid.plan_reid(cpath, id_base=6500)
    assert not any("flag" in h for h in rp.residual), rp.residual


def test_apply_invalidates_the_toml_cache(tmp_path):
    """tomlcache memoizes on (mtime_ns, size) and names its one stale window as an edit preserving BOTH.
    A reid 6000->6500 is byte-length-preserving BY CONSTRUCTION, so without an explicit clear a same-process
    re-read (lint, build, the Workspace) can be served the pre-move tree."""
    import os

    from ff9mapkit import tomlcache
    cpath = _write(tmp_path)
    before = tomlcache.load_toml(cpath)                              # prime the cache
    assert before["field"][0]["id"] == 6000
    st = os.stat(cpath)
    rp = reid.plan_reid(cpath, id_base=6500)
    reid.apply_reid(rp)
    # FORCE the documented window rather than hope for it: NTFS mtime_ns is fine-grained enough that a
    # same-process rewrite usually LOOKS fresh, which would make this assertion pass with or without the
    # clear -- a check that cannot fail. Restoring the original mtime reproduces the exact condition
    # tomlcache says it cannot detect (same mtime_ns AND same size -- and a reid preserves size).
    os.utime(cpath, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert os.stat(cpath).st_size == st.st_size, "a same-digit-count reid is size-preserving"
    assert tomlcache.load_toml(cpath)["field"][0]["id"] == 6500, "a cached pre-move tree survived the write"


def test_a_seam_to_real_naming_a_moved_id_is_reported_not_rewritten(tmp_path):
    """to_real is donor-by-default but CAN hold a sibling campaign's fork id (journey.campaign_connectivity
    resolves it against sibling ownership). Rewriting it silently would be wrong in one direction and
    destructive in the other, so reid leaves it and surfaces it."""
    man = MANIFEST + '\n[[seam]]\nfrom = "A"\nto_real = 6001\nkind = "portal"\nnote = ""\n'
    cpath = _write(tmp_path, manifest=man)
    rp = reid.plan_reid(cpath, id_base=6500)
    assert tomllib.loads(cpath.read_text(encoding="utf-8"))["seam"][0]["to_real"] == 6001, "not rewritten"
    assert any("to_real" in h for h in rp.residual), rp.residual


def test_room_coordinates_are_not_reported_as_leftover_ids(tmp_path):
    """A campaign at 6000-6039 sits inside the normal x/z range of a room. Flagging walkmesh geometry
    would train the author to ignore the residual list -- and an ignored list is not a net."""
    cpath = _write(tmp_path, a_extra='\n[[npc]]\nname = "G"\npos = [6000, 6001]\nzone = 6000\n')
    rp = reid.plan_reid(cpath, id_base=6500)
    assert not any("pos" in h or "zone" in h for h in rp.residual), rp.residual


# ---- refusals ----------------------------------------------------------------------------
@pytest.mark.parametrize("kw, needle", [
    (dict(id_base=9005), "world-map hole"),
    (dict(id_base=100), "outside the custom band"),
    (dict(id_base=32767), "outside the custom band"),      # 2 members -> 32767/32768
    (dict(mapping=["6000=6001"]), "collides inside the campaign"),
    (dict(mapping=["9999=1"]), "not members of this campaign"),
    (dict(id_base=6000), "no-op"),
    (dict(), "--id-base"),
])
def test_reid_refuses(tmp_path, kw, needle):
    cpath = _write(tmp_path)
    with pytest.raises(reid.ReidError) as ex:
        reid.plan_reid(cpath, **kw)
    assert needle in str(ex.value), str(ex.value)


def test_reid_refuses_a_live_id_collision(tmp_path):
    cpath = _write(tmp_path)
    with pytest.raises(reid.ReidError, match="already registered"):
        reid.plan_reid(cpath, id_base=6500, reserved_ids={6501})


def test_reid_refuses_the_coop_room_id(tmp_path):
    """COOP_FIELD lives in its own folder, deliberately absent from Memoria.ini FolderNames -- so the live
    registration sweep structurally cannot see it and every other gate would pass."""
    from ff9mapkit.coop import COOP_FIELD
    cpath = _write(tmp_path)
    with pytest.raises(reid.ReidError, match="co-op room"):
        reid.plan_reid(cpath, id_base=COOP_FIELD)


def test_reid_refuses_a_campaign_that_does_not_lint_clean(tmp_path):
    """Moving a campaign whose manifest and member toml already disagree would carry the disagreement
    into the new band. lint (e3) is exactly that check."""
    cpath = _write(tmp_path)
    (tmp_path / "B" / "B.field.toml").write_text(
        MEMBER.format(fid=7777, nm="B", extra="", tb=""), encoding="utf-8")
    with pytest.raises(reid.ReidError, match="does not lint clean"):
        reid.plan_reid(cpath, id_base=6500)
    rp = reid.plan_reid(cpath, id_base=6500, skip_lint=True)      # explicit override still available
    assert rp.moved == 2


def test_nothing_is_written_until_apply(tmp_path):
    cpath = _write(tmp_path)
    before = {p: p.read_bytes() for p in sorted(tmp_path.rglob("*.toml"))}
    rp = reid.plan_reid(cpath, id_base=6500)
    assert rp.moved == 2
    assert {p: p.read_bytes() for p in sorted(tmp_path.rglob("*.toml"))} == before, "plan_reid is pure"
    reid.apply_reid(rp)
    assert {p: p.read_bytes() for p in sorted(tmp_path.rglob("*.toml"))} != before


def test_a_rewrite_that_disagrees_with_the_semantic_result_refuses(tmp_path):
    """The two-implementation gate: if the surgical text edit and the pure dict transform ever disagree,
    reid raises instead of writing. Forced here by making the semantic pass see a different remap."""
    cpath = _write(tmp_path)
    p = tmp_path / "A" / "A.field.toml"
    import ff9mapkit.reid as R
    real = R.rewrite_text
    try:
        R.rewrite_text = lambda t, *a, **k: (t, ["lie"], [])      # rewrite nothing, claim success
        with pytest.raises(reid.ReidError, match="disagrees with the expected result"):
            reid.plan_reid(cpath, id_base=6500)
    finally:
        R.rewrite_text = real
    assert "6000" in p.read_text(encoding="utf-8"), "nothing was written"
