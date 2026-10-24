"""THE RENDER TARGET in the texel lane -- ``summons/render_target.py`` + ``repaint._gate_render_target``.

Memoria hands a 15bpp key VRAM only as its last resort: once an effect has rendered into its DR_AREA
target, every 15bpp page at x >= 384 samples that target instead. So a ``direct15`` repaint there is
byte-correct on disk, deploys, verifies -- and no 15bpp read samples it. These tests pin the verdicts on
the scenery fixture from ``test_summon_repaint`` (whose 15bpp DIRECT cell is ``x512_y256``), with a
synthetic census entry for effect 999 put in place per test:

* a NEVER_VRAM edit REFUSES by name, with the measurement, whether the cell's own bytes reach the
  screen at all, and the remedy -- the cells that DRAW the target;
* the literal-boolean key lifts it, the build says what was lifted, and the key moves no byte;
* every other verdict is a disclosure and never refuses.

The table itself is a cache of a measurement; its re-derivation lives in
``studies/custom-summons/tier-w/render_target_gates.py``.
"""
from __future__ import annotations

import hashlib

import pytest

from ff9mapkit.summons import render_target as RT
from ff9mapkit.summons import repaint as RP
from tests.test_summon_repaint import (CORPUS, _bump_cell, _cell, _page_at, _row, _spec_dict,
                                       _write_cell_png, build_scenery_container, needs_corpus)


@pytest.fixture
def census(monkeypatch):
    """Install a synthetic routes-census entry for effect 999 -- the fixture's 15bpp page (512,256)
    read ``kind``, a target from f10, and four feeders: the lawful 8bpp cell (704,256), this cell's
    own bytes at 8bpp, the refused (448,256) and a cell no writer uploads."""
    def _set(kind="GENERATED", target=10, own=True):
        monkeypatch.setattr(RT, "CENSUS_IDS", RT.CENSUS_IDS | {999})
        monkeypatch.setitem(RT.ROUTES, 999, (RT.Route(page=(512, 256), kind=kind, renders=12,
                                                      frames=(11, 40)),))
        if target is None:
            monkeypatch.delitem(RT.TARGETS, 999, raising=False)
            monkeypatch.delitem(RT.FEEDS, 999, raising=False)
            return
        monkeypatch.setitem(RT.TARGETS, 999, target)
        feeds = [RT.Feed(cell=(704, 256), bpp=8, pixels=600, frames=30),
                 RT.Feed(cell=(448, 256), bpp=4, pixels=200, frames=30),
                 RT.Feed(cell=(640, 256), bpp=8, pixels=100, frames=5)]
        if own:
            feeds.append(RT.Feed(cell=(512, 256), bpp=8, pixels=100, frames=30))
        monkeypatch.setitem(RT.FEEDS, 999, tuple(sorted(feeds, key=lambda f: -f.pixels)))
    return _set


def _edit(tmp_path, blob, page):
    return _write_cell_png(tmp_path, blob, page, _bump_cell(page, _page_at(blob, page)))


# ---------------------------------------------------------------- (1) the table, as shipped
def test_the_table_is_the_measurement_and_its_counts_close():
    assert (RT.CENSUS_CONTAINERS, RT.ROUTE_ROWS, RT.TARGET_CONTAINERS, RT.FEED_ROWS) == (372, 181, 66, 280)
    assert RT.KIND_COUNTS == {"GENERATED": 70, "BLUR": 88, "BACKGROUND": 13, "IMAGE": 10}
    assert sum(len(v) for v in RT.ROUTES.values()) == RT.ROUTE_ROWS
    assert len(RT.CENSUS_IDS) == 372 and 16 not in RT.CENSUS_IDS and 510 in RT.CENSUS_IDS
    assert RT.UNPORTED == {126, 250, 274, 395, 435}
    assert sum(RT.SURFACE_15BPP_VERDICTS.values()) == RT.SURFACE_15BPP == 22
    assert sum(RT.WIDE_15BPP_VERDICTS.values()) == RT.WIDE_15BPP == 87
    assert RT.ACK_KEY == "acknowledge_render_target" and RT.ACK_KEY in RP._TEXEL_KEYS
    assert RP.ACK_RENDER_TARGET == RT.ACK_KEY


def test_a_page_covers_four_columns_and_one_256_line_band():
    r = RT.Route(page=(448, 256), kind="GENERATED", renders=1, frames=(0, 0))
    assert all(r.covers((x, y)) for x in (448, 512, 576, 640) for y in (256, 384))
    assert not r.covers((704, 256)) and not r.covers((384, 256)) and not r.covers((448, 128))


@pytest.mark.parametrize("ef, cell, verdict, own", [
    (429, (448, 256), RT.NEVER_VRAM, ()),              # the cast that never showed
    (446, (448, 256), RT.NEVER_VRAM, (4, 8)),          # the salmon checker
    (251, (512, 256), RT.NEVER_VRAM, (8, 4)),          # the bumper strip
    (434, (576, 256), RT.NEVER_VRAM, ()),              # the target AND the ground capture
    (177, (576, 256), RT.MIXED, ()),                   # Carbuncle: VRAM before its target, then not
    (493, (576, 256), RT.READS_VRAM, ()),              # Carbuncle's gem variant: never a target
    (133, (576, 256), RT.UNREAD, ()),
    (274, (448, 256), RT.UNPORTED_VERDICT, ()),        # Devour: the port does not model its key
    (16, (448, 256), RT.UNMEASURED, ()),               # not a corpus id
    (None, (448, 256), RT.UNMEASURED, ()),
])
def test_the_shipped_verdicts_on_the_cells_the_record_names(ef, cell, verdict, own):
    rt = RT.cell_route(ef, cell)
    assert rt.verdict == verdict
    assert tuple(f.bpp for f in rt.own_feeds) == own
    assert rt.never_vram == (verdict == RT.NEVER_VRAM)
    assert rt.describe().startswith(verdict + ":")


def test_the_own_feed_line_says_which_road_the_bytes_take():
    assert "no measured road" in RT.cell_route(429, (448, 256)).own_feed_line()
    salmon = RT.cell_route(446, (448, 256)).own_feed_line()
    assert "4bpp (52%" in salmon and "8bpp (6%" in salmon and "palette indices" in salmon
    assert RT.cell_route(493, (576, 256)).own_feed_line() == "", "only a NEVER_VRAM cell has the line"


# ---------------------------------------------------------------- (2) the hazard, as data
def test_the_route_rides_on_the_15bpp_page_only_and_stays_out_of_names(census):
    census()
    blob = build_scenery_container()
    pages = {p.name: p for p in RP.scenery_texel_pages(blob, 999)}
    hz = pages["cell.s0.x512_y256"].hazards
    assert hz.render_route.verdict == RT.NEVER_VRAM
    assert "render" not in " ".join(hz.names), "its own field, its own gate -- not `names`"
    assert all(p.hazards.render_route is None for n, p in pages.items() if n != "cell.s0.x512_y256")
    # the remedy names the feeders against the surface, largest first, and skips the cell's own bytes
    r = hz.render_remedy
    assert r.startswith("the target this cell's page reads is DRAWN from x704_y256 at 8bpp (60%")
    assert "paint `cell.s0.x704_y256` in the indexed lane" in r
    assert "`cell.s0.x448_y256`, which the kit refuses as `depth-unknown`" in r
    assert "x640_y256 at 8bpp (10% of the target's fragments): no writer in this container" in r
    assert "x512_y256" not in r


def test_a_target_drawn_only_from_the_ground_capture_names_no_cell(census, monkeypatch):
    census(kind="BACKGROUND", target=None)
    blob = build_scenery_container()
    hz = _cell(blob, 512, 256).hazards
    assert hz.render_route.verdict == RT.NEVER_VRAM
    assert "battle-ground capture" in hz.render_remedy and "no cell to paint instead" in hz.render_remedy


# ---------------------------------------------------------------- (3) the build gate
def test_a_never_vram_edit_REFUSES_by_name_with_the_measurement_and_the_remedy(tmp_path, census):
    census()
    blob = build_scenery_container()
    p = _cell(blob, 512, 256)
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [_row(p, _edit(tmp_path, blob, p))]), "?", blob=blob)
    msg = str(e.value)
    assert msg.startswith("RENDER TARGET, cell.s0.x512_y256:")
    assert "NEVER_VRAM: every 15bpp read" in msg and "the 15bpp page (512,256) read the render target" in msg
    assert "isCreateGenTexture" in msg, "the law rides along"
    assert "this cell's OWN bytes do feed the target, read at 8bpp" in msg
    assert "paint `cell.s0.x704_y256` in the indexed lane" in msg
    assert "three for three" in msg and "bumper strip" in msg, "and the cast record"
    assert "`%s = true`" % RT.ACK_KEY in msg


def test_the_key_is_literal_boolean_and_moves_no_byte(tmp_path, census):
    census()
    blob = build_scenery_container()
    p = _cell(blob, 512, 256)
    src = _edit(tmp_path, blob, p)
    with pytest.raises(RP.RepaintError, match="BOOLEAN"):
        RP.build(_spec_dict(blob, [_row(p, src, **{RT.ACK_KEY: "true"})]), "?", blob=blob)
    b = RP.build(_spec_dict(blob, [_row(p, src, **{RT.ACK_KEY: True})]), "?", blob=blob)
    t = b.enabled[0]
    assert t.ack_render_target and t.changed
    note = "  ".join(t.hazard_notes)
    assert "RENDER TARGET, acknowledged" in note and RT.ACK_KEY in note
    # the same art with no census entry at all builds the same container: the key moves NO byte
    census(kind="IMAGE", target=None)
    assert RP.build(_spec_dict(blob, [_row(p, src)]), "?", blob=blob).sha_out == b.sha_out


@pytest.mark.parametrize("kind, target, verdict", [
    ("IMAGE", None, RT.READS_VRAM), (None, None, RT.UNMEASURED)])
def test_every_other_verdict_builds_and_discloses(tmp_path, census, kind, target, verdict):
    if kind:
        census(kind=kind, target=target)
    blob = build_scenery_container()
    p = _cell(blob, 512, 256)
    b = RP.build(_spec_dict(blob, [_row(p, _edit(tmp_path, blob, p))]), "?", blob=blob)
    note = "  ".join(b.enabled[0].hazard_notes)
    assert "RENDER ROUTE (a disclosure, not a refusal): %s:" % verdict in note
    assert "Battle Speed >= 3" in note, "and which cast path the verdict holds on"


def test_an_unchanged_or_disabled_row_is_not_an_edit(tmp_path, census):
    census()
    blob = build_scenery_container()
    p = _cell(blob, 512, 256)
    b = RP.build(_spec_dict(blob, [_row(p, _write_cell_png(tmp_path, blob, p))]), "?", blob=blob)
    assert any(n.startswith("RENDER TARGET, clear") for n in b.enabled[0].hazard_notes)
    keep = _cell(blob, 704, 256)
    b = RP.build(_spec_dict(blob, [_row(p, _edit(tmp_path, blob, p), enabled=False),
                                   _row(keep, _write_cell_png(tmp_path, blob, keep))]),
                 "?", blob=blob)
    assert [t.name for t in b.enabled] == ["cell.s0.x704_y256"]


# ---------------------------------------------------------------- (4) export + the report say it first
def test_export_records_the_route_and_the_scaffold_states_the_key_before_painting(tmp_path, census):
    census()
    blob = build_scenery_container()
    man = RP.export_art(blob, 999, tmp_path / "art", lane="direct15", overlays=False)
    rec = {e["name"]: e["render_route"] for e in man["scenery"]}
    r = rec["cell.s0.x512_y256"]
    assert r["verdict"] == RT.NEVER_VRAM and r["target_from"] == 10
    assert r["reads"] == [{"page": [512, 256], "kind": "GENERATED", "renders": 12, "frames": [11, 40]}]
    assert r["own_feeds"][0]["bpp"] == 8 and "cell.s0.x704_y256" in r["remedy"]
    assert (tmp_path / "art" / "cell.s0.x512_y256.png").is_file(), "export delta 0"
    sc = (tmp_path / "art" / RP.SCAFFOLD_NAME).read_text(encoding="utf-8")
    row = sc.split('name = "cell.s0.x512_y256"')[1].split("[[reskin.texel]]")[0]
    assert "%s = false" % RT.ACK_KEY in row and "** RENDER TARGET" in row
    assert "cell.s0.x704_y256" in row, "the remedy is on the row, before anyone paints"
    # an indexed export's cells are not 15bpp and carry no route
    man = RP.export_art(blob, 999, tmp_path / "idx", overlays=False)
    assert all(e["render_route"] is None for e in man["scenery"])


def test_the_report_never_reads_clean_on_a_never_vram_cell(census):
    census()
    blob = build_scenery_container()
    text = "\n".join(RP.scenery_lines(blob, 999))
    assert "RENDER TARGET: 1 15bpp cell(s); this effect renders into its DR_AREA target from f10" in text
    assert "NEVER_VRAM  cell.s0.x512_y256" in text and "own bytes feed the target at 8 bpp" in text
    census(kind="IMAGE", target=None)
    text = "\n".join(RP.scenery_lines(blob, 999))
    assert "READS_VRAM  cell.s0.x512_y256" in text and "never renders into a DR_AREA target" in text


# ---------------------------------------------------------------- (5) the corpus case
@needs_corpus
def test_every_default_surface_15bpp_cell_of_ef446_refuses(tmp_path):
    """ef446 is the cast whose cyan 15bpp bands showed as a salmon checker: its 15bpp page reads the
    target from f60. Every 15bpp cell its default surface hands out refuses at build, by name."""
    blob = (CORPUS / "ef446.bytes").read_bytes()
    pages = [p for p in RP.scenery_texel_pages(blob, 446) if p.bpp == 15]
    assert sorted(p.name for p in pages) == ["cell.s0.x448_y384", "cell.s0.x512_y384"]
    assert all(p.hazards.render_route.verdict == RT.NEVER_VRAM for p in pages)
    # both cells on one spec, because ef446's reader spills across them (the NAME-EVERY-COLUMN gate)
    rows = [_row(p, _edit(tmp_path, blob, p), acknowledge_spill=True) for p in pages]
    spec = {"reskin": {"effect": 446, "expect_sha256": hashlib.sha256(blob).hexdigest(),
                       "texel": rows}}
    with pytest.raises(RP.RepaintError) as e:
        RP.build(spec, "?", blob=blob)
    assert str(e.value).startswith("RENDER TARGET, cell.s0.x448_y384:")
    assert "this effect's target exists from f60" in str(e.value)
    # the key on the first row moves the refusal to the second: it is per cell, never per spec
    rows[0][RT.ACK_KEY] = True
    with pytest.raises(RP.RepaintError) as e:
        RP.build(spec, "?", blob=blob)
    assert str(e.value).startswith("RENDER TARGET, cell.s0.x512_y384:")


# ---------------------------------------------------------------- (7) CHANNEL D: the depth a cell is DRAWN at
DARK = "cell.s0.x448_y256"


@pytest.fixture
def drawn(monkeypatch):
    """A synthetic feed for effect 999: the fixture's depth-unknown cell (448,256) drawn into the target
    at ``bpps`` through CLUT (0,245) (declared, 256 entries) and (0,246) (not declared)."""
    def _set(*bpps):
        monkeypatch.setitem(RT.TARGETS, 999, 10)
        monkeypatch.setitem(RT.FEEDS, 999, tuple(
            RT.Feed(cell=(448, 256), bpp=b, pixels=500, frames=9,
                    cluts=(((0, 245), 400), ((0, 246), 100))) for b in bpps))
    return _set


def test_the_shipped_channel_is_the_census_split_by_clut():
    d = RT.drawn_depth(150, (448, 256))
    assert d.depths == (8,) and not d.dual and d.bpp == 8
    assert d.clut_cells == ((0, 245), (0, 246)), "display binding = the lowest address, first"
    assert "DRAWN into the render target at 8bpp" in d.evidence()
    two = RT.drawn_depth(429, (512, 256))
    assert two.dual and two.depths == (4, 8) and two.bpp is None and two.clut_cells == ()
    assert RT.drawn_depth(150, (0, 0)) is None
    assert RT.FEED_CLUT_ROWS == len(RT._FEED_CLUT_ROWS) == 371
    assert "drawn" in RP.DEPTH_SOURCES and "drawn" in RP.EDIT_CHANNELS
    assert "drawn" not in RP.LICENSED_CHANNELS, "the bound reading stays the W6b-3 kit"
    assert RT.DRAWN_ACK_KEY in RP._TEXEL_KEYS and RP.ACK_DRAWN_DEPTH == RT.DRAWN_ACK_KEY


def test_consulted_it_discloses_and_moves_no_page(drawn):
    drawn(8)
    blob = build_scenery_container()
    no_d = tuple(c for c in RP.EDIT_CHANNELS if c != "drawn")
    a, ar = RP.scenery_surface(blob, 999, channels=RP.EDIT_CHANNELS)
    b, br = RP.scenery_surface(blob, 999, channels=no_d)
    assert [(p.name, p.bpp, p.depth_source) for p in a] == [(p.name, p.bpp, p.depth_source) for p in b]
    assert sorted((r.name, r.klass) for r in ar) == sorted((r.name, r.klass) for r in br)
    hit = [r for r in ar if r.name == DARK]
    assert [r.klass for r in hit] == ["depth-unknown"]
    assert "A DRAW READS IT (CHANNEL D, MEASURED)" in hit[0].reason
    assert "`%s = true`" % RT.DRAWN_ACK_KEY in hit[0].reason and "`expect_bpp = 8`" in hit[0].reason
    assert "CHANNEL D" not in [r for r in br if r.name == DARK][0].reason, "unconsulted, it says nothing"


def test_behind_its_key_it_emits_a_keyed_page_and_a_dual_draw_never_does(drawn):
    drawn(8)
    blob = build_scenery_container()
    p = RP.texel_page(blob, DARK, 999, allow_drawn_depth=True)
    assert (p.bpp, p.depth_source, p.palette_name) == (8, "drawn", "pal.s0.x0_y245.e256")
    assert p.hazards.column_clut_cells == ((0, 245), (0, 246))
    with pytest.raises(RP.RepaintError, match="A DRAW READS IT"):
        RP.texel_page(blob, DARK, 999)
    bound = RP.scenery_surface(blob, 999, channels=RP.READINGS["bound"], drawn_depth=True)[0]
    assert DARK not in {q.name for q in bound}, "the bound reading never consults channel D"
    drawn(4, 8)
    with pytest.raises(RP.RepaintError, match="AT TWO DEPTHS"):
        RP.texel_page(blob, DARK, 999, allow_drawn_depth=True)


def test_the_build_wants_the_key_AND_the_number(tmp_path, drawn):
    drawn(8)
    blob = build_scenery_container()
    p = RP.texel_page(blob, DARK, 999, allow_drawn_depth=True)
    src = _edit(tmp_path, blob, p)
    with pytest.raises(RP.RepaintError, match="depth-unknown"):
        RP.build(_spec_dict(blob, [_row(p, src)]), "?", blob=blob)
    with pytest.raises(RP.RepaintError, match="states NO `expect_bpp`"):
        RP.build(_spec_dict(blob, [_row(p, src, **{RT.DRAWN_ACK_KEY: True})]), "?", blob=blob)
    with pytest.raises(RP.RepaintError, match="a draw INTO THE TARGET read this cell at"):
        RP.build(_spec_dict(blob, [_row(p, src, expect_bpp=4, **{RT.DRAWN_ACK_KEY: True})]), "?",
                 blob=blob)
    with pytest.raises(RP.RepaintError, match="must be a BOOLEAN"):
        RP.build(_spec_dict(blob, [_row(p, src, expect_bpp=8, **{RT.DRAWN_ACK_KEY: "true"})]), "?",
                 blob=blob)
    b = RP.build(_spec_dict(blob, [_row(p, src, expect_bpp=8, **{RT.DRAWN_ACK_KEY: True})]), "?",
                 blob=blob)
    assert b.patched != blob
    notes = "  ".join(b.targets[0].hazard_notes)
    assert "DEPTH FROM CHANNEL D" in notes and RT.DRAWN_ACK_WARNING in notes


def test_export_hands_it_out_behind_the_flag_as_a_commented_block(tmp_path, drawn):
    drawn(8)
    blob = build_scenery_container()
    man = RP.export_art(blob, 999, tmp_path / "plain", overlays=False)
    assert DARK not in {e["name"] for e in man["scenery"]}
    man = RP.export_art(blob, 999, tmp_path / "d", overlays=False, drawn_depth=True)
    e = [e for e in man["scenery"] if e["name"] == DARK][0]
    assert e["depth_source"] == "drawn" and e["drawn_depths"] == [8]
    assert (tmp_path / "d" / e["png"]).is_file()
    txt = (tmp_path / "d" / RP.SCAFFOLD_NAME).read_text(encoding="utf-8")
    assert "# CHANNEL D -- A DRAW INTO THE TARGET" in txt and "# %s = true" % RT.DRAWN_ACK_KEY in txt
    assert '\nname = "%s"' % DARK not in txt, "the row ships COMMENTED"
    import tomllib
    rows = tomllib.loads(txt)["reskin"]["texel"]
    assert DARK not in {r["name"] for r in rows}
    assert RP.build(tomllib.loads(txt), str(tmp_path / "d" / "s.toml"), blob=blob).patched == blob, \
        "the scaffold's first build is still a no-op"
    with pytest.raises(RP.RepaintError, match="does not consult channel D"):
        RP.export_art(blob, 999, tmp_path / "x", overlays=False, drawn_depth=True,
                      channels=RP.READINGS["bound"])


def test_the_remedy_names_a_drawn_feeder_with_its_key(census, monkeypatch):
    census()
    blob = build_scenery_container()
    # the census fixture's (448,256) feeder, at 4bpp -- now WITH its CLUT, a declared 16-entry one
    feeds = tuple(RT.Feed(cell=f.cell, bpp=f.bpp, pixels=f.pixels, frames=f.frames,
                          cluts=((((0, 244), f.pixels),) if f.cell == (448, 256) else ()))
                  for f in RT.FEEDS[999])
    monkeypatch.setitem(RT.FEEDS, 999, feeds)
    rem = _cell(blob, 512, 256).hazards.render_remedy
    assert ("`cell.s0.x448_y256`, refused as `depth-unknown` -- paint it with `%s = true` and "
            "`expect_bpp = 4`" % RT.DRAWN_ACK_KEY) in rem
    p = RP.texel_page(blob, DARK, 999, allow_drawn_depth=True)
    assert p.bpp == 4 and p.depth_source == "drawn", "the claim resolves exactly as written"


def test_the_cli_flag_exports_and_is_refused_where_it_would_do_nothing(tmp_path, drawn, capsys):
    from ff9mapkit import cli
    drawn(8)
    blob = build_scenery_container()
    ef = tmp_path / "ef999.bytes"
    ef.write_bytes(blob)
    art = tmp_path / "art"
    assert cli.main(["summon-reskin", "export-art", "--ef", "999", "--from", str(ef), "--out", str(art),
                     "--acknowledge-drawn-depth"]) == 0
    import json
    man = json.loads((art / RP.ART_MANIFEST).read_text(encoding="utf-8"))
    assert DARK in {e["name"] for e in man["scenery"]}
    capsys.readouterr()
    assert cli.main(["summon-reskin", "plan", str(art / RP.SCAFFOLD_NAME), "--from", str(ef),
                     "--acknowledge-drawn-depth"]) == 2
    assert "is an export-art flag" in capsys.readouterr().err
