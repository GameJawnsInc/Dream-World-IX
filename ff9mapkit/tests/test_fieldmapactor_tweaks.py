"""FieldMapActor.cs PER-ACTOR TWEAKS a fork loses on a minted id -- catalog spot-checks + the fork-report wire.
Pure baked data (no install) -- unit-testable and safe on the install-free fork-report path, mirroring
test_walkmesh_hotfix.py.
"""
from __future__ import annotations

from ff9mapkit import data
from ff9mapkit import fieldmapactor_tweaks as fmt
from ff9mapkit import forkreport


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
