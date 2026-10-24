"""THE SCROLL BLIT (HLE op 144) in the texel lane -- ``summons/scroll_blit.py`` + ``repaint._gate_scroll_blit``.

op 144 copies a source band of VRAM into a destination band every frame it runs, so a repaint of a
texel inside a DESTINATION band is byte-correct on disk, deploys, verifies -- and never reaches the
screen. These tests pin the three verdicts on containers this file builds (the scenery fixture from
``test_summon_repaint``), with a synthetic op-144 table entry for effect 999 put in place per test:

* a destination edit REFUSES by name, with the measurement and the remedy (the source cell);
* the literal-boolean key lifts it, and the build says what was lifted;
* a SOURCE edit builds and discloses where it propagates -- never merged with the destination.

The table also carries six containers' OWN horizontal-scroll routine (``axis = "h"``), which closed the
headless census's open gap on ef226 / ef509; section 4c pins its arithmetic and the corpus case at the end
pins the four cells.

The table itself is a cache of a measurement; its re-derivation lives in
``studies/custom-summons/tier-w/scroll_blit_gates.py``. The corpus-gated case at the end is ef407, the
container whose named cast cell this check moved.
"""
from __future__ import annotations

import hashlib

import pytest

from ff9mapkit.summons import repaint as RP
from ff9mapkit.summons import reskin as RS
from ff9mapkit.summons import scroll_blit as SB
from tests.test_summon_repaint import (CORPUS, _bump_cell, _cell, _page_at, _row, _spec_dict,
                                       _write_cell_png, build_scenery_container, needs_corpus)

#: the fixture's tall rect is (704,256) over (704,384) -- ef407's own column-704 shape, so the
#: synthetic blit below is ef407's `dst (704,384) <- src (704,256)` at the fixture's coordinates.
FULL = SB.ScrollBlit(effect=999, dst=(704, 384), size=(64, 128), src=(704, 256), chunks=(0,), sites=1)
#: a PARTIAL band: the left half of (704,256) rewritten from its own right half -- ef211's pool shape.
HALF = SB.ScrollBlit(effect=999, dst=(704, 256), size=(32, 128), src=(736, 256), chunks=(0,), sites=2)


@pytest.fixture
def blits(monkeypatch):
    """Install a synthetic op-144 table entry for effect 999, restored after the test."""
    def _set(*bs):
        monkeypatch.setitem(SB.SCROLL_BLITS, 999, tuple(bs))
    return _set


def _edit(tmp_path, blob, page, keep=None):
    """A bumped copy of ``page`` -- every texel, or only those whose HALFWORD ``keep(col, row)``
    selects -- written as the PNG of record at the page's own depth."""
    raw = _page_at(blob, page)
    new = bytearray(_bump_cell(page, raw))
    if keep is not None:
        stride = page.page_bytes // (2 * page.h)
        for o in range(len(new)):
            hw = o // 2
            if not keep(hw % stride, hw // stride):
                new[o] = raw[o]
    return _write_cell_png(tmp_path, blob, page, bytes(new))


# ---------------------------------------------------------------- (1) the table, as shipped
def test_the_table_is_the_measurement_and_its_geometry_is_the_kits():
    assert SB.SITES == 167 and SB.CONTAINERS == 59
    assert (SB.HSCROLL_SITES, SB.HSCROLL_CONTAINERS, SB.ALL_CONTAINERS) == (11, 6, 63)
    assert sum(b.sites for bs in SB.SCROLL_BLITS.values() for b in bs) == SB.SITES + SB.HSCROLL_SITES
    assert sum(b.sites for bs in SB.SCROLL_BLITS.values() for b in bs if b.axis == "v") == SB.SITES
    assert (SB.CELL_W, SB.CELL_LINES) == (RS.PAGE_CELL_W, RS.PAGE_CELL_LINES)
    assert [(b.dst, b.size, b.src) for b in SB.blits(407)] == [
        ((704, 384), (64, 128), (704, 256)), ((640, 256), (64, 128), (640, 384))]
    assert SB.blits(None) == (), "no effect id is ignorance, never a clean bill"
    # the four sites whose folded SOURCE does not fit VRAM name no source cell
    odd = [b for b in SB.blits(22) if not b.src_in_vram]
    assert odd and odd[0].feeds(odd[0].dest_overlap((576, 384))) is None


def test_the_band_arithmetic_is_columns_one_to_one_and_rows_the_whole_period():
    assert FULL.dest_overlap((704, 384)) == (704, 384, 64, 128)
    assert FULL.dest_overlap((704, 256)) is None and FULL.source_overlap((704, 256)) == \
        (704, 256, 64, 128)
    assert len(SB.rewritten_halfwords((FULL,), (704, 384))) == 64 * 128
    assert len(SB.rewritten_halfwords((HALF,), (704, 256))) == 32 * 128
    # a band of rows 368..480 feeds BOTH stacked cells; the scroll rotates rows, so a column range
    # is fed by that column range over the WHOLE source period
    tall = SB.ScrollBlit(effect=0, dst=(576, 368), size=(28, 112), src=(604, 368), chunks=(0,),
                         sites=1)
    assert tall.dest_overlap((576, 384)) == (576, 384, 28, 96)
    assert tall.feeds((576, 384, 28, 96)) == (604, 368, 28, 112)
    assert SB.cells_under((604, 368, 28, 112)) == ((576, 256), (576, 384))


# ---------------------------------------------------------------- (2) the surface states it
def test_the_hazard_is_data_on_every_channel_set_and_stays_out_of_names(blits):
    blits(FULL)
    blob = build_scenery_container()
    for ch in (RP.CENSUS_CHANNELS, RP.EDIT_CHANNELS):
        pages = {p.name: p for p in RP.scenery_surface(blob, 999, channels=ch)[0]}
        dst, src = pages["cell.s0.x704_y384"].hazards, pages["cell.s0.x704_y256"].hazards
        assert dst.scroll_dst == (FULL,) and not dst.scroll_src
        assert src.scroll_src == (FULL,) and not src.scroll_dst
        assert "scroll" not in " ".join(dst.names), "its own field, its own gate -- not `names`"
        assert dst.scroll_remedy == (
            "paint the source cell `cell.s0.x704_y256` (704,256) instead -- op 144 copies its band "
            "(704,256) 64x128 into this one, scrolling",)
    # ...and the refusal LIST does not move: the verdict is about THIS edit's texels, at build time
    assert [r.name for r in RP.scenery_cell_refusals(blob, 999)] == ["cell.s0.x448_y256"]


# ---------------------------------------------------------------- (3) the build gate
def test_a_destination_edit_REFUSES_by_name_with_the_measurement_and_the_remedy(tmp_path, blits):
    blits(FULL)
    blob = build_scenery_container()
    p = _cell(blob, 704, 384)
    src = _edit(tmp_path, blob, p)
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [_row(p, src)]), "?", blob=blob)
    msg = str(e.value)
    assert msg.startswith("SCROLL-BLIT DESTINATION, cell.s0.x704_y384:")
    assert "of this edit's" in msg and "VRAM (704,384) 64x128" in msg
    assert "paint the source cell `cell.s0.x704_y256`" in msg
    assert "252 DR_MOVE blits" in msg, "the measurement rides along"
    assert "INVISIBLE" in msg and "(576,368) band's blit running on every frame" in msg, \
        "and the in-game reachability record"
    assert "eroded" not in msg, "cast 2b is not a counter-witness: its band is blitted at every draw"
    assert "`%s = true`" % SB.ACK_KEY in msg


def test_the_key_is_literal_boolean_and_the_build_says_what_it_lifted(tmp_path, blits):
    assert SB.ACK_KEY in RP._TEXEL_KEYS and RP.ACK_SCROLL_BLIT == SB.ACK_KEY
    blits(FULL)
    blob = build_scenery_container()
    p = _cell(blob, 704, 384)
    src = _edit(tmp_path, blob, p)
    with pytest.raises(RP.RepaintError, match="BOOLEAN"):
        RP.build(_spec_dict(blob, [_row(p, src, **{SB.ACK_KEY: "true"})]), "?", blob=blob)
    b = RP.build(_spec_dict(blob, [_row(p, src, **{SB.ACK_KEY: True})]), "?", blob=blob)
    t = b.enabled[0]
    assert t.ack_scroll_blit and t.changed
    note = "  ".join(t.hazard_notes)
    assert "SCROLL-BLIT DESTINATION, acknowledged" in note and SB.ACK_KEY in note
    # the key moves NO byte: the same art builds the same container whether or not a gate had to fire
    blits()
    assert RP.build(_spec_dict(blob, [_row(p, src)]), "?", blob=blob).sha_out == b.sha_out


def test_a_source_edit_builds_and_discloses_where_it_propagates(tmp_path, blits):
    blits(FULL)
    blob = build_scenery_container()
    p = _cell(blob, 704, 256)
    b = RP.build(_spec_dict(blob, [_row(p, _edit(tmp_path, blob, p))]), "?", blob=blob)
    b.check = RP.self_check(b)
    assert b.check.ok, [g.detail for g in b.check.gates if not g.ok]
    note = "  ".join(b.enabled[0].hazard_notes)
    assert "SCROLL-BLIT SOURCE (a disclosure, not a refusal)" in note and "(704,384)" in note
    assert "SCROLL-BLIT DESTINATION" not in note, "source and destination are never merged"


def test_a_partial_band_refuses_the_texel_not_the_cell(tmp_path, blits):
    """ef211's pool-wheel shape: the band is the LEFT half, fed from the right half of the SAME cell.
    An edit that stays out of the band loses nothing and builds; one halfword inside refuses."""
    blits(HALF)
    blob = build_scenery_container()
    p = _cell(blob, 704, 256)
    clear = _edit(tmp_path, blob, p, keep=lambda c, r: c >= 32)
    b = RP.build(_spec_dict(blob, [_row(p, clear)]), "?", blob=blob)
    note = "  ".join(b.enabled[0].hazard_notes)
    assert "SCROLL-BLIT DESTINATION, clear" in note and "4096 of this cell's halfwords" in note
    assert "SCROLL-BLIT SOURCE" in note, "the right half IS the band's source"
    one = _edit(tmp_path, blob, p, keep=lambda c, r: c >= 32 or (c, r) == (3, 9))
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [_row(p, one)]), "?", blob=blob)
    assert "1 of this edit's" in str(e.value)
    assert "is in THIS cell, outside the rewritten band" in str(e.value)


def test_a_disabled_row_on_a_destination_is_not_an_edit(tmp_path, blits):
    blits(FULL)
    blob = build_scenery_container()
    p = _cell(blob, 704, 384)
    keep = _cell(blob, 704, 256)
    b = RP.build(_spec_dict(blob, [_row(p, _edit(tmp_path, blob, p), enabled=False),
                                   _row(keep, _write_cell_png(tmp_path, blob, keep))]),
                 "?", blob=blob)
    assert [t.name for t in b.enabled] == ["cell.s0.x704_y256"]


# ---------------------------------------------------------------- (4) export + the report say it first
def test_export_records_both_directions_and_the_scaffold_states_the_key_before_painting(tmp_path,
                                                                                       blits):
    blits(FULL)
    blob = build_scenery_container()
    man = RP.export_art(blob, 999, tmp_path / "art", overlays=False)
    rec = {e["name"]: e["scroll_blit"] for e in man["scenery"]}
    assert rec["cell.s0.x704_y384"]["destination"][0]["band"] == [704, 384, 64, 128]
    assert rec["cell.s0.x704_y384"]["rewritten_halfwords"] == 8192
    assert rec["cell.s0.x704_y256"]["source"][0]["dst"] == [704, 384]
    assert rec["cell.s0.x576_y256"] == {"destination": [], "rewritten_halfwords": 0, "source": []}
    # export delta 0: the destination's picture is still handed back (the build is where bytes are
    # spent, and a partial band leaves the rest of a cell paintable)
    assert (tmp_path / "art" / "cell.s0.x704_y384.png").is_file()
    sc = (tmp_path / "art" / RP.SCAFFOLD_NAME).read_text(encoding="utf-8")
    row = sc.split('name = "cell.s0.x704_y384"')[1].split("[[reskin.texel]]")[0]
    assert "%s = false" % SB.ACK_KEY in row and "SCROLL-BLIT DESTINATION" in row
    assert "cell.s0.x704_y256" in row, "the remedy is on the row, before anyone paints"
    src_row = sc.split('name = "cell.s0.x704_y256"')[1].split("[[reskin.texel]]")[0]
    assert "SCROLL-BLIT SOURCE" in src_row and SB.ACK_KEY not in src_row


def test_the_report_never_reads_clean_on_a_destination_and_the_class_says_what_it_missed(blits):
    blits(FULL)
    blob = build_scenery_container()
    text = "\n".join(RP.scenery_lines(blob, 999))
    assert "SCROLL BLITS (HLE op 144)" in text
    assert "DESTINATION cell.s0.x704_y384" in text and "SOURCE      cell.s0.x704_y256" in text
    klass, why = RP.program_class(999)
    assert klass == "clean" and "op-144 SCROLL BLITS" in why
    blits()
    assert "SCROLL" not in "\n".join(RP.scenery_lines(blob, 999)), "silent where there is no blit"
    assert RP.program_class(999)[1] == ("ef999 declares no VRAM-transfer call site and no loader "
                                        "op 0x07")
    # the READ class no longer claims "only through StoreImage" where op 144 also writes
    assert "only through StoreImage" not in RP.program_class(211)[1]
    assert "StoreImage" in RP.program_class(211)[1] and "SCROLL BLITS" in RP.program_class(211)[1]


# ---------------------------------------------------------------- (4b) the refresh law
STALE = SB.RefreshRead(verdict="READ_STALE", stale_reads=32, reads=32, pages=("x640_y256@8",))
FROZEN = SB.RefreshRead(verdict="MIXED", stale_reads=16, reads=17, pages=("x640_y256@8",))


def _refresh(monkeypatch, read):
    monkeypatch.setitem(SB.REFRESH, (999,) + FULL.dst + FULL.size, read)


def test_the_refresh_table_is_the_census_and_closes_over_the_site_table():
    assert (SB.REFRESH_FRESH, SB.REFRESH_MIXED, SB.REFRESH_STALE) == (111, 9, 3)
    assert SB.REFRESH_PAIRS == sum(len(bs) for bs in SB.SCROLL_BLITS.values()) == 123
    assert all(b.refresh is None for bs in SB.SCROLL_BLITS.values() for b in bs if b.axis == "h"), \
        "the program scroll's 8 pairs all read fresh"
    ef499 = [b for b in SB.blits(499) if b.dst == (512, 256)][0]
    assert ef499.refresh.verdict == "READ_STALE" and ef499.refresh.pages == ("x448_y256@8",)
    assert [b.refresh for b in SB.blits(407)] == [None, None], \
        "ef407's copy is refreshed by its own column-640 roll -- the gain-half cast was seen"
    # every READ_STALE pair is a band in a LATER column of the multi-column page that samples it
    for (ef, x, y, w, h), r in SB.REFRESH.items():
        if r.verdict == "READ_STALE":
            assert all(x // 64 * 64 > int(pg.split("_")[0][1:]) for pg in r.pages), (ef, x, r.pages)
    assert "x448_y256@8" in ef499.refresh.describe() and "32 of 32" in ef499.refresh.describe()


def test_a_destination_on_a_stale_pair_still_refuses_and_says_the_premise_inverts(tmp_path, blits,
                                                                                monkeypatch):
    blits(FULL)
    _refresh(monkeypatch, STALE)
    blob = build_scenery_container()
    p = _cell(blob, 704, 384)
    src = _edit(tmp_path, blob, p)
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [_row(p, src)]), "?", blob=blob)
    msg = str(e.value)
    assert msg.startswith("SCROLL-BLIT DESTINATION, cell.s0.x704_y384:"), "headless is not a cast"
    assert "INVERTS THE PREMISE" in msg and "DOES show" in msg and "x640_y256@8" in msg
    b = RP.build(_spec_dict(blob, [_row(p, src, **{SB.ACK_KEY: True})]), "?", blob=blob)
    note = "  ".join(b.enabled[0].hazard_notes)
    assert "SCROLL-BLIT DESTINATION, acknowledged" in note and "INVERTS THE PREMISE" in note
    man = RP.export_art(blob, 999, tmp_path / "art", overlays=False)
    rec = {e["name"]: e["scroll_blit"] for e in man["scenery"]}
    assert "INVERTS THE PREMISE" in rec["cell.s0.x704_y384"]["destination"][0]["refresh"]
    sc = (tmp_path / "art" / RP.SCAFFOLD_NAME).read_text(encoding="utf-8")
    row = sc.split('name = "cell.s0.x704_y384"')[1].split("[[reskin.texel]]")[0]
    assert "INVERTS THE PREMISE" in row, "the scaffold says it before anyone paints"


@pytest.mark.parametrize("read, says, never", [
    (STALE, "does NOT appear at (704,384)", "ALSO appears"),
    (FROZEN, "FROZEN at one phase", "ALSO appears"),
    (None, "ALSO appears at (704,384), scrolling", "FROZEN"),
])
def test_a_source_disclosure_follows_the_measured_refresh(tmp_path, blits, monkeypatch, read, says,
                                                          never):
    blits(FULL)
    if read is not None:
        _refresh(monkeypatch, read)
    blob = build_scenery_container()
    p = _cell(blob, 704, 256)
    b = RP.build(_spec_dict(blob, [_row(p, _edit(tmp_path, blob, p))]), "?", blob=blob)
    note = "  ".join(b.enabled[0].hazard_notes)
    assert "SCROLL-BLIT SOURCE (a disclosure, not a refusal)" in note
    assert says in note and never not in note
    RP.export_art(blob, 999, tmp_path / "art", overlays=False)
    sc = (tmp_path / "art" / RP.SCAFFOLD_NAME).read_text(encoding="utf-8")
    row = sc.split('name = "cell.s0.x704_y256"')[1].split("[[reskin.texel]]")[0]
    assert says in " ".join(row.replace("#", " ").split()), "the scaffold says the same before painting"


# ---------------------------------------------------------------- (4c) the program's own scroll
#: ef226 / ef509's shape at the fixture's coordinates: the top 64 lines of (704,384) rewritten from
#: its own bottom 64, scrolled HORIZONTALLY by the container's own routine.
HSCROLL = SB.ScrollBlit(effect=999, dst=(704, 384), size=(64, 64), src=(704, 448), chunks=(0,), sites=1,
                        axis="h", routine="L_2558")


def test_the_program_scroll_rotates_columns_and_maps_rows_one_to_one():
    assert HSCROLL.label == "the program's own scroll (L_2558)" and HSCROLL.mechanism == SB.H_MECHANISM
    assert "horizontal" in HSCROLL.describe() and "L_2558" in HSCROLL.describe()
    # a part of the band is fed by the SAME rows of the source over its whole WIDTH -- op 144's rule
    # turned through 90 degrees
    assert HSCROLL.feeds((704, 400, 16, 8)) == (704, 464, 64, 8)
    assert FULL.feeds((704, 400, 16, 8)) == (704, 256, 16, 128)
    assert len(SB.rewritten_halfwords((HSCROLL,), (704, 384))) == 64 * 64
    shipped = [b for b in SB.blits(509) if b.axis == "h"]
    assert [(b.dst, b.size, b.src, b.routine) for b in shipped] == [
        ((448, 384), (128, 64), (448, 448), "L_2558"), ((576, 384), (128, 64), (576, 256), "L_2558")]


def test_a_program_scroll_destination_refuses_and_its_own_bottom_half_builds(tmp_path, blits):
    blits(HSCROLL)
    blob = build_scenery_container()
    p = _cell(blob, 704, 384)
    top = _edit(tmp_path, blob, p, keep=lambda c, r: r < 64)
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [_row(p, top)]), "?", blob=blob)
    msg = str(e.value)
    assert msg.startswith("SCROLL-BLIT DESTINATION, cell.s0.x704_y384:")
    assert "HORIZONTAL scroll" in msg and "THE PROGRAM SCROLL RUNS" in msg
    assert "252 DR_MOVE blits" not in msg, "op 144's executed record is not this band's"
    assert ("the source band (704,448) 64x64 is in THIS cell, outside the rewritten band: paint it "
            "there and the program's own scroll (L_2558) copies it in, scrolling") in msg
    bottom = _edit(tmp_path, blob, p, keep=lambda c, r: r >= 64)
    b = RP.build(_spec_dict(blob, [_row(p, bottom)]), "?", blob=blob)
    note = "  ".join(b.enabled[0].hazard_notes)
    assert "SCROLL-BLIT DESTINATION, clear" in note and "SCROLL-BLIT SOURCE" in note
    text = "\n".join(RP.scenery_lines(blob, 999))
    assert "SCROLL BLITS (the program's own scroll)" in text
    assert "program-scroll SCROLL BLITS" in RP.program_class(999)[1]


def test_a_source_the_executed_copies_contradict_names_no_cell(tmp_path, blits, monkeypatch):
    blits(FULL)
    monkeypatch.setattr(SB, "SOURCE_UNCERTAIN", SB.SOURCE_UNCERTAIN | {999})
    blob = build_scenery_container()
    pages = {p.name: p for p in RP.scenery_texel_pages(blob, 999)}
    assert pages["cell.s0.x704_y384"].hazards.scroll_remedy == (
        "its source folds to (704,256), but headless this container's copies read from elsewhere "
        "(scroll_blit.SOURCE_UNCERTAIN), so the fold names no cell to paint instead",)
    p = pages["cell.s0.x704_y256"]
    b = RP.build(_spec_dict(blob, [_row(p, _edit(tmp_path, blob, p))]), "?", blob=blob)
    assert "a fold, not a measurement" in "  ".join(b.enabled[0].hazard_notes)


# ---------------------------------------------------------------- (5) the corpus case
@needs_corpus
def test_ef407s_named_cast_cell_refuses_and_names_the_source(tmp_path):
    """ef407 ``cell.s0.x704_y384`` was the named vehicle for the gain-half cast. It is a FULL op-144
    destination (``dst (704,384) 64x128 <- src (704,256)``), so the build refuses it by name and sends
    the author to ``x704_y256`` -- where the mark is predicted to appear in the scrolling band."""
    blob = (CORPUS / "ef407.bytes").read_bytes()
    pages = {p.name: p for p in RP.scenery_texel_pages(blob, 407)}
    assert sorted(pages) == ["cell.s0.x640_y256", "cell.s0.x704_y256", "cell.s0.x704_y384"]
    p = pages["cell.s0.x704_y384"]
    assert len(p.hazards.scroll_rewritten) == 8192
    spec = {"reskin": {"effect": 407, "expect_sha256": hashlib.sha256(blob).hexdigest(),
                       "texel": [_row(p, _write_cell_png(tmp_path, blob, p,
                                                         _bump_cell(p, _page_at(blob, p))))]}}
    with pytest.raises(RP.RepaintError) as e:
        RP.build(spec, "?", blob=blob)
    assert "SCROLL-BLIT DESTINATION, cell.s0.x704_y384" in str(e.value)
    assert "paint the source cell `cell.s0.x704_y256`" in str(e.value)
    assert pages["cell.s0.x640_y256"].hazards.scroll_remedy[0].startswith(
        "its source (640,384) is not an editable cell")


@needs_corpus
@pytest.mark.parametrize("ef, routine", [(226, "L_5220"), (509, "L_2558")])
def test_the_open_gap_is_closed_ef226_and_ef509_refuse_their_top_halves(tmp_path, ef, routine):
    """The headless census's open gap: the plugin rewrites the top 64 lines of ``x448_y384`` and
    ``x512_y384`` every frame from their own bottom 64, through the container's OWN scroll routine,
    while the op-144 table named nothing there -- so the kit licensed them. Now both refuse by name
    and the bottom halves (the band's source) build and say where they propagate."""
    blob = (CORPUS / ("ef%03d.bytes" % ef)).read_bytes()
    pages = {p.name: p for p in RP.scenery_texel_pages(blob, ef)}
    names = ("cell.s0.x448_y384", "cell.s0.x512_y384")
    for name in names:
        assert [b.routine for b in pages[name].hazards.scroll_dst] == [routine]
        assert len(pages[name].hazards.scroll_rewritten) == 64 * 64

    def spec(keep, **kw):
        # both cells on one spec: a reader spills across them (THE NAME-EVERY-COLUMN gate); the cutout
        # law is a different question and is acknowledged so this test asserts one thing
        rows = [_row(pages[n], _edit(tmp_path, blob, pages[n], keep=keep), acknowledge_spill=True,
                     acknowledge_cutout_reshape=True, **kw.get(n, {})) for n in names]
        return {"reskin": {"effect": ef, "expect_sha256": hashlib.sha256(blob).hexdigest(),
                           "texel": rows}}

    with pytest.raises(RP.RepaintError) as e:
        RP.build(spec(lambda c, r: r < 64), "?", blob=blob)
    assert str(e.value).startswith("SCROLL-BLIT DESTINATION, cell.s0.x448_y384:")
    assert "the program's own scroll (%s)" % routine in str(e.value)
    with pytest.raises(RP.RepaintError) as e:      # the key is per row: the second cell still refuses
        RP.build(spec(lambda c, r: r < 64, **{names[0]: {SB.ACK_KEY: True}}), "?", blob=blob)
    assert str(e.value).startswith("SCROLL-BLIT DESTINATION, cell.s0.x512_y384:")
    b = RP.build(spec(lambda c, r: r >= 64), "?", blob=blob)
    for t in b.enabled:
        note = "  ".join(t.hazard_notes)
        assert "SCROLL-BLIT DESTINATION, clear" in note and "SCROLL-BLIT SOURCE" in note, t.name
