"""FieldMapActor.cs PER-ACTOR TWEAKS a fork loses on a minted id -- catalog spot-checks + the fork-report wire.
Pure baked data (no install) -- unit-testable and safe on the install-free fork-report path, mirroring
test_walkmesh_hotfix.py.
"""
from __future__ import annotations

import re

from ff9mapkit import data
from ff9mapkit import fieldmapactor_tweaks as fmt
from ff9mapkit import forkreport

from ._patchstack import WRAPPED, net_added, net_lines


# --- catalog: camera_priority --------------------------------------------------------------------------------
def test_catalog_camera_priority_is_functional():
    for fid in (1413, 1414, 2752, 1707):
        tweaks = fmt.info(fid)
        assert len(tweaks) == 1
        assert tweaks[0].kind == "camera_priority" and tweaks[0].severity == "FUNCTIONAL"


def test_catalog_camera_priority_2752_1707_share_site():
    t2752, t1707 = fmt.info(2752)[0], fmt.info(1707)[0]
    assert t2752.source == t1707.source == "FieldMapActor.cs:147"
    assert t2752.note == t1707.note                       # same shared out-of-depth-range fallback exemption


# --- catalog: geo_attach --------------------------------------------------------------------------------------
def test_catalog_geo_attach_is_functional():
    for fid in (1410, 1412, 2954, 3002):
        tweaks = fmt.info(fid)
        assert len(tweaks) == 1
        assert tweaks[0].kind == "geo_attach" and tweaks[0].severity == "FUNCTIONAL"


# --- catalog: shadow_render -------------------------------------------------------------------------------
def test_catalog_shadow_render_is_cosmetic():
    for fid in (2510, 661, 2107, 2102):
        tweaks = fmt.info(fid)
        assert len(tweaks) == 1
        assert tweaks[0].kind == "shadow_render" and tweaks[0].severity == "COSMETIC"


# --- two-site fields --------------------------------------------------------------------------------------
def test_catalog_two_site_fields():
    assert len(fmt.info(1659)) == 2                        # Queen_Brahne instance 1 + instance 2
    assert len(fmt.info(2363)) == 2                         # Thorn _CharZ + Zorn/Thorn shadow offset
    assert all(t.severity == "COSMETIC" for t in fmt.info(1659))
    assert all(t.severity == "COSMETIC" for t in fmt.info(2363))


# --- unknown field / census completeness --------------------------------------------------------------------
def test_catalog_unknown_field_is_empty_tuple():
    assert fmt.info(99999) == ()
    assert fmt.info(None) == ()


def test_census_completeness():
    assert set(fmt._TWEAKS) == {661, 1410, 1412, 1413, 1414, 1659, 1707, 2102, 2107, 2363, 2510, 2752, 2954, 3002}


# --- fork-report (lost-on-mint, of which the actor tweak is one entry) --------------------------------------
def _lost_labels(eb, fid):
    return [lbl for lbl, _ in forkreport.analyze_eb(eb, field_id=fid).lost_on_mint]


def test_fork_report_lost_on_mint_includes_actor_tweaks():
    eb = data.blank_field_bytes("us")
    assert "actor camera priority" in _lost_labels(eb, 1413)
    assert "actor shadow render" in _lost_labels(eb, 2510)
    assert _lost_labels(eb, 1659).count("actor shadow render") == 2   # the two-site field yields 2 entries
    txt = forkreport.format_report(forkreport.analyze_eb(eb, field_id=1413))
    assert "Lost on mint" in txt and "actor camera priority" in txt


def test_fork_report_counts_only_the_raw_tweaks_as_lost():
    eb = data.blank_field_bytes("us")
    for fid in (661, 2102, 2107, 3002):                            # s65 wraps these: reproduced, not a loss
        rep = forkreport.analyze_eb(eb, field_id=fid)
        assert all("reproduced" in det for lbl, det in rep.lost_on_mint if lbl.startswith("actor ")), fid
        assert "Loses actor" not in forkreport._verdict_line(rep), fid
    rep = forkreport.analyze_eb(eb, field_id=1413)
    assert "Loses actor camera priority" in forkreport._verdict_line(rep)


# --- the catalog follows the PATCH STACK (memoria-patches/): engine_remapped == every gate the tweak needs is
#     written in its EffectiveFieldId form. Each pattern carries the site's actor condition, so two tweaks on one
#     field (1659, 2363) are told apart.
def _w(op, fid, cond=""):
    return WRAPPED.format(op, fid) + cond


_ROO = [_w(">=", 1400), _w("<=", 1425)]                           # GeoAttach's shared Fossil Roo range gate
_GATES = {
    ("FieldMapActor.cs:135", 1413): [_w("==", 1413)],
    ("FieldMapActor.cs:141", 1414): [_w("==", 1414)],
    ("FieldMapActor.cs:147", 2752): [_w("!=", 2752)],
    ("FieldMapActor.cs:147", 1707): [_w("!=", 1707)],
    ("FieldMapActor.cs:243", 1410): _ROO + [_w("!=", 1410, r" && component\.isPlayer")],
    ("FieldMapActor.cs:243", 1412): _ROO + [_w("==", 1412)],
    ("FieldMapActor.cs:261", 2954): [_w("==", 2954, r" && PersistenSingleton")],
    ("FieldMapActor.cs:297", 3002): [_w("==", 3002, r" && component\.originalActor\.sid == 2")],
    ("FieldMapActor.cs:164", 2510): [_w("==", 2510, r" && this\.actor\.uid == 8\b")],
    ("FieldMapActor.cs:169", 2363): [_w("==", 2363, r" && this\.actor\.uid == 33\)")],
    ("FieldMapActor.cs:187", 2363): [_w("==", 2363, r" && \(this\.actor\.uid == 16")],
    ("FieldMapActor.cs:181", 661): [_w("==", 661, r" && this\.actor\.uid == 3\b")],
    ("FieldMapActor.cs:183", 1659): [_w("==", 1659, r" && this\.actor\.uid == 128\b")],
    ("FieldMapActor.cs:185", 1659): [_w("==", 1659, r" && this\.actor\.uid == 129\b")],
    ("FieldMapActor.cs:190", 2107): [_w("==", 2107, r" && this\.actor\.uid == 5\b")],
    ("FieldMapActor.cs:190", 2102): [_w("==", 2102, r" && this\.actor\.uid == 4\b")],
}


def test_catalog_engine_remap_follows_the_patch_stack():
    tweaks = {(t.source, t.field_id): t for ts in fmt._TWEAKS.values() for t in ts}
    assert set(_GATES) == set(tweaks)                              # every catalogued tweak names its engine gates
    for key, pats in _GATES.items():
        wrapped = [net_added("FieldMapActor.cs", p) >= 1 for p in pats]
        assert tweaks[key].engine_remapped == all(wrapped), (key, wrapped)
    assert {f for (_, f), t in tweaks.items() if t.engine_remapped} == {661, 2102, 2107, 3002}


def test_every_wrap_in_fieldmapactor_is_catalogued():
    """The other direction: a wrap the stack leaves in FieldMapActor.cs that no remapped tweak claims -- a newly
    wrapped gate, or a function-level alias -- means this catalog needs a re-audit."""
    claimed = [p for (src, fid), pats in _GATES.items() if fmt.info(fid) and any(
        t.engine_remapped and t.source == src for t in fmt.info(fid)) for p in pats]
    for line in net_lines("FieldMapActor.cs", r"EffectiveField"):
        assert any(re.search(p, line) for p in claimed), line
