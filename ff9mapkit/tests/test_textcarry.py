"""Faithful TEXT carry -- ship a donor field's referenced .mes text verbatim + remap the grafted windows
(``content/textcarry.py``).

The carry closes the last gap the object + player grafts left: a window the grafted/carried bytes open names
a donor TXID a fork doesn't ship -> an EMPTY window. Carry ships the donor's words (per language, verbatim) +
remaps each grafted window's TXID to a fresh band (>= 1000), so the forked interactions show the REAL text.
These pin the mechanism offline (synthetic donors + the install-fed full path); the closing proof that a
forked NPC speaks the real line in-game is the human playtest (docs/TEXT_CARRY.md).
"""
from __future__ import annotations

import json
import struct

import pytest

from ff9mapkit import data, dialogue, eventscan
from ff9mapkit.config import LANGS
from ff9mapkit.content import object as _object
from ff9mapkit.content import player as _player
from ff9mapkit.content import textcarry as _tc
from ff9mapkit.eb import EbScript, edit, opcodes

CLEAN = data.blank_field_bytes("us")


def _entry(*funcs) -> bytes:
    """Assemble a raw entry from ``(tag, body)`` funcs (the same little builder the graft tests use)."""
    table, pos, bodies = b"", len(funcs) * 4, b""
    for tag, body in funcs:
        table += struct.pack("<HH", tag, pos)
        pos += len(body)
        bodies += body
    return bytes([0, len(funcs)]) + table + bodies


# --- the band + a same-length 2-byte patch ---------------------------------------------------------
def test_carry_base_is_clear_of_base_and_authored_bands():
    # the band must be a 2-byte immediate (<= 65535) AND clear of the base game (max real txid 863) and the
    # fork's own authored band (DEFAULT_BASE_TXID 500). 1000 is the first unconditionally-safe floor.
    from ff9mapkit.content import text as _text
    assert _tc.CARRY_BASE_TXID == 1000
    assert _tc.CARRY_BASE_TXID > 863                         # > the census max real txid
    assert _tc.CARRY_BASE_TXID > _text.DEFAULT_BASE_TXID     # > the authored band
    assert _tc.CARRY_BASE_TXID <= 0xFFFF                     # still a 2-byte immediate


def test_remap_windows_is_same_length_2byte_patch():
    # a talk func that opens window txid 132 (donor) -> carried 1000; the patch must be byte-length-preserving.
    talk = opcodes.window_sync(1, 0x80, 132) + opcodes.RETURN
    ent = _entry((0, opcodes.RETURN), (3, talk))
    slot = EbScript.from_bytes(CLEAN).first_free_slot()
    g = edit.append_entry(CLEAN, slot, ent)
    before = len(g)
    out = _tc._remap_windows_in_entry(g, slot, {132: 1000})
    assert len(out) == before                               # same length
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out                             # still valid
    win = next(i for i in eb.instrs(eb.entry(slot).func_by_tag(3)) if i.op == 0x1F)
    assert win.imm(2) == 1000                               # txid remapped


def test_remap_only_touches_carried_tags():
    # tag 1 also opens txid 132 but is NOT in carry_tags -> left untouched (only the kept funcs are patched).
    talk = opcodes.window_sync(1, 0x80, 132) + opcodes.RETURN
    loop = opcodes.window_sync(1, 0x80, 132) + opcodes.RETURN
    ent = _entry((0, opcodes.RETURN), (1, loop), (3, talk))
    slot = EbScript.from_bytes(CLEAN).first_free_slot()
    g = edit.append_entry(CLEAN, slot, ent)
    out = _tc._remap_windows_in_entry(g, slot, {132: 1000}, carry_tags=[0, 3])   # tag 1 dropped
    eb = EbScript.from_bytes(out)
    assert next(i for i in eb.instrs(eb.entry(slot).func_by_tag(3)) if i.op == 0x1F).imm(2) == 1000
    assert next(i for i in eb.instrs(eb.entry(slot).func_by_tag(1)) if i.op == 0x1F).imm(2) == 132   # untouched


def test_remap_leaves_uncarried_txid_alone():
    # a txid not in the map (e.g. a system window we chose not to carry) is left verbatim.
    talk = opcodes.window_sync(1, 0, 7) + opcodes.window_sync(1, 0x80, 132) + opcodes.RETURN
    ent = _entry((0, opcodes.RETURN), (3, talk))
    slot = EbScript.from_bytes(CLEAN).first_free_slot()
    g = edit.append_entry(CLEAN, slot, ent)
    out = _tc._remap_windows_in_entry(g, slot, {132: 1000})   # 7 not in the map
    eb = EbScript.from_bytes(out)
    wins = [i.imm(2) for i in eb.instrs(eb.entry(slot).func_by_tag(3)) if i.op == 0x1F]
    assert wins == [7, 1000]                                  # system txid 7 untouched, 132 remapped


# --- collect_carry: which txids a graft SHOWS ------------------------------------------------------
def _loader_from(table):
    """A lang_loader returning {txid: MesEntry} per language from a {lang: {txid: text}} table."""
    def _load(txids, lang):
        return {t: dialogue.MesEntry(txid=t, text=table.get(lang, {}).get(t, ""), strt="155,3")
                for t in txids if t in table.get(lang, {})}
    return _load


def test_collect_carry_scans_object_and_player_windows():
    # an object spec (tag-3 opens 132) + a text player func (opens 271) -> both txids enter the plan.
    obj_entry = _entry((0, opcodes.RETURN), (3, opcodes.window_sync(1, 0x80, 132) + opcodes.RETURN))
    donor = edit.append_entry(CLEAN, EbScript.from_bytes(CLEAN).first_free_slot(), obj_entry)
    dslot = EbScript.from_bytes(CLEAN).first_free_slot()
    ospecs = [{"donor_idx": dslot, "graft_safety": "clean", "carry_tags": None}]
    pspecs = [{"donor_tag": 11, "safety": "text",
               "body": opcodes.window_sync(1, 0x80, 271) + opcodes.RETURN}]
    table = {lang: {132: f"npc-{lang}", 271: f"pf-{lang}"} for lang in LANGS}
    plan = _tc.collect_carry(donor, ospecs, pspecs, field=999, lang_loader=_loader_from(table))
    assert [(e.donor_txid, e.new_txid) for e in plan] == [(132, 1000), (271, 1001)]
    assert plan[0].texts["us"] == "npc-us" and plan[0].texts["jp"] == "npc-jp"
    assert plan[1].texts["fr"] == "pf-fr"


def test_collect_carry_empty_when_no_grafted_windows():
    # a prop with no window + no player funcs -> empty plan (no carry, build unchanged).
    obj_entry = _entry((0, opcodes.RETURN))
    donor = edit.append_entry(CLEAN, EbScript.from_bytes(CLEAN).first_free_slot(), obj_entry)
    dslot = EbScript.from_bytes(CLEAN).first_free_slot()
    plan = _tc.collect_carry(donor, [{"donor_idx": dslot, "graft_safety": "clean", "carry_tags": None}],
                             [], field=1, lang_loader=_loader_from({}))
    assert plan == []


def test_collect_carry_skips_refused_and_dropped_tags():
    # a REFUSED object carries nothing; an init_only object's DROPPED tag-3 window is not shown -> not carried.
    obj_entry = _entry((0, opcodes.RETURN), (3, opcodes.window_sync(1, 0x80, 50) + opcodes.RETURN))
    donor = edit.append_entry(CLEAN, EbScript.from_bytes(CLEAN).first_free_slot(), obj_entry)
    dslot = EbScript.from_bytes(CLEAN).first_free_slot()
    table = {lang: {50: "x"} for lang in LANGS}
    refused = _tc.collect_carry(donor, [{"donor_idx": dslot, "graft_safety": "refuse"}], [], 1,
                                _loader_from(table))
    assert refused == []                                     # refused carries nothing
    init_only = _tc.collect_carry(donor, [{"donor_idx": dslot, "graft_safety": "init_only",
                                           "carry_tags": [0]}], [], 1, _loader_from(table))
    assert init_only == []                                   # tag-3 dropped -> its window isn't shown


# --- per-language emit: verbatim, empty stays empty, geometry preserved ----------------------------
def test_carried_mes_is_verbatim_and_per_language():
    plan = [_tc.CarriedEntry(132, 1000, {l: f"line-{l}" for l in LANGS}, strt="155,3", tail=None)]
    us = _tc.carried_mes_body(plan, "us")
    jp = _tc.carried_mes_body(plan, "jp")
    assert "[TXID=1000][STRT=155,3]line-us[ENDN]" in us     # the donor STRT is preserved verbatim
    assert "line-jp" in jp and "[TAIL=" not in us           # no TAIL emitted when the donor had none
    # the carried block round-trips through the reader at the new txid
    back = dialogue.parse_mes(us)
    assert back[1000].text == "line-us" and back[1000].strt == "155,3"


def test_carried_empty_entry_stays_empty_no_us_fallback():
    # the field-357 case: us empty, fr populated -> carry each language verbatim; an empty us must NOT be
    # back-filled from another language (that would WIPE the language that legitimately differs).
    plan = [_tc.CarriedEntry(470, 1000, {"us": "", "uk": "", "fr": "Kab", "gr": "Gott", "it": "Kapu",
                                         "es": "", "jp": "村長"}, strt="10,1", tail=None)]
    assert dialogue.parse_mes(_tc.carried_mes_body(plan, "us"))[1000].text == ""
    assert dialogue.parse_mes(_tc.carried_mes_body(plan, "fr"))[1000].text == "Kab"


def test_carried_mes_preserves_tail_when_present():
    plan = [_tc.CarriedEntry(5, 1000, {l: "hi" for l in LANGS}, strt="10,1", tail="LOR")]
    assert "[TAIL=LOR]" in _tc.carried_mes_body(plan, "us")


# --- the sidecar round-trips --------------------------------------------------------------------
def test_sidecar_roundtrips(tmp_path):
    plan = [_tc.CarriedEntry(132, 1000, {l: f"a-{l}" for l in LANGS}, strt="155,3", tail=None),
            _tc.CarriedEntry(133, 1001, {l: f"b-{l}" for l in LANGS}, strt="219,2", tail="UPR")]
    p = tmp_path / "f.carrytext.json"
    _tc.write_sidecar(p, plan, field=42)
    raw = json.loads(p.read_text(encoding="utf-8"))
    assert raw["field"] == 42 and raw["base_txid"] == 1000 and len(raw["entries"]) == 2
    back = _tc.load_sidecar(p)
    assert [(e.donor_txid, e.new_txid, e.strt, e.tail) for e in back] == \
           [(132, 1000, "155,3", None), (133, 1001, "219,2", "UPR")]
    assert all(e.texts.get(l) for e in back for l in LANGS)   # every shipped language present


def test_sidecar_load_fills_missing_language_empty(tmp_path):
    # a sidecar that lacks a language ships an empty window there (harmless), never errors.
    p = tmp_path / "f.carrytext.json"
    p.write_text(json.dumps({"version": 1, "entries": [
        {"donor_txid": 1, "new_txid": 1000, "strt": "10,1", "tail": None, "texts": {"us": "hi"}}]}),
        encoding="utf-8")
    back = _tc.load_sidecar(p)
    assert back[0].texts["us"] == "hi" and back[0].texts["jp"] == ""


# --- the un-refusal hook: text player funcs become graftable under carry ----------------------------
def test_graft_player_funcs_grafts_text_when_carry_on():
    pe = eventscan._player_entry_index(EbScript.from_bytes(CLEAN))
    specs = [{"donor_tag": 11, "safety": "text", "body": opcodes.window_sync(1, 0x80, 271) + opcodes.RETURN,
              "donor_init_packs": []}]
    # default (clean-only): NOT grafted
    off = _player.graft_player_funcs(CLEAN, specs, {11: 64})
    assert 64 not in {f.tag for f in EbScript.from_bytes(off).entry(pe).funcs}
    # carry on (clean+text): grafted
    on = _player.graft_player_funcs(CLEAN, specs, {11: 64}, graftable_safeties=("clean", "text"))
    assert 64 in {f.tag for f in EbScript.from_bytes(on).entry(pe).funcs}


def test_scan_objects_verbatim_unrefuses_text_func_under_carry(tmp_path):
    # the seeding object flips init_only -> clean ONLY when carry admits the text player func it calls.
    from ff9mapkit import extract
    if not _game_ready():
        pytest.skip("needs the FF9 install + UnityPy")
    donor = extract.EventBundle(lang="us").eb_for_id(164)    # Alexandria interior: a SUB NPC RunScripts text funcs
    without = {o["donor_idx"]: o["graft_safety"]
               for o in eventscan.scan_objects_verbatim(donor, graft_player_funcs=True, carry_text=False)}
    with_ct = {o["donor_idx"]: o["graft_safety"]
               for o in eventscan.scan_objects_verbatim(donor, graft_player_funcs=True, carry_text=True)}
    assert without[1] == "init_only" and with_ct[1] == "clean"


# --- the full install-fed pipeline (import -> build) -------------------------------------------------
def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_import_carry_text_npc_full_pipeline(tmp_path):
    # the headline (NPC talk): import a real talkable-NPC field with --carry-text, build it, and the grafted
    # NPCs' tag-3 windows resolve to the donor's VERBATIM per-language text in the carried band.
    from ff9mapkit import build, extract
    from ff9mapkit.config import ModLayout
    meta, toml = extract.write_native_project("fbg_n00_tshp_map007_th_orc_0", tmp_path / "proj",
                                              name="THORC", field_id=30003,
                                              graft_player_funcs=True, carry_text=True)
    assert meta["imported_content"]["carry_text"] == 5       # the 5 band-members' talk lines
    assert (tmp_path / "proj" / "THORC.carrytext.json").is_file()
    p = build.FieldProject.load(toml)
    assert build.validate(p) == []
    dist = tmp_path / "dist"
    build.build_mod([p], dist, mod_name="FF9CustomMap")
    lay = ModLayout(dist)
    data_us = lay.eb_path("us", "EVT_THORC.eb.bytes").read_bytes()
    eb = EbScript.from_bytes(data_us)
    assert eb.to_bytes() == data_us                          # the grafted+remapped fork round-trips byte-exact
    talk = sorted({c.txid for c in dialogue.scan_dialogue(data_us) if c.func_tag == 3 and c.txid is not None})
    assert talk == [1000, 1001, 1002, 1003, 1004]            # carried band, not the donor 132-136
    # the per-language .mes ships the donor text verbatim at the carried txids
    first = {}                                                # the first carried line per language
    for lang in ("us", "fr", "jp"):
        body = lay.mes_path(lang, p.text_block).read_text(encoding="utf-8")
        m = dialogue.parse_mes(body)
        assert all(t in m and m[t].text for t in talk)       # every carried txid resolves, non-empty
        first[lang] = m[1000].text
    # REAL per-language carry (no us-fallback): the same line differs across languages. Asserts the
    # property, not the words -- so no Square-Enix string is embedded in the repo (provenance-clean).
    assert first["us"] != first["fr"] != first["jp"]


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_import_carry_text_player_func_full_pipeline(tmp_path):
    # the second consumer (grafted TEXT player func): a SUB NPC whose interaction RunScripts a text player
    # func -> with carry the func grafts AND its window resolves to the carried band.
    from ff9mapkit import build, extract
    from ff9mapkit.config import ModLayout
    meta, toml = extract.write_native_project("fbg_n02_alxc_map056b_ac_lti_2", tmp_path / "proj",
                                              name="ALTI", field_id=30003,
                                              graft_player_funcs=True, carry_text=True)
    assert meta["imported_content"]["player_funcs"] == 2     # the 2 text player funcs (now grafted)
    assert meta["imported_content"]["carry_text"] >= 2
    p = build.FieldProject.load(toml)
    assert build.validate(p) == []
    dist = tmp_path / "dist"
    build.build_mod([p], dist, mod_name="FF9CustomMap")
    lay = ModLayout(dist)
    data_us = lay.eb_path("us", "EVT_ALTI.eb.bytes").read_bytes()
    eb = EbScript.from_bytes(data_us)
    assert eb.to_bytes() == data_us
    pe = eventscan._player_entry_index(eb)
    grafted = [f.tag for f in eb.entry(pe).funcs if f.tag >= _player.FIRST_OBJECT_PLAYER_TAG]
    assert grafted                                           # the text player funcs grafted onto the player
    for tag in grafted:                                      # every grafted-func window is in the carried band
        for ins in eb.instrs(eb.entry(pe).func_by_tag(tag)):
            opnd = dialogue.WINDOW_OPS.get(ins.op)
            if opnd is not None and ins.imm(opnd) is not None:
                assert ins.imm(opnd) >= _tc.CARRY_BASE_TXID


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_carry_does_not_disturb_authored_text(tmp_path):
    # carry APPENDS its band after the authored block: an authored NPC line keeps its 500-band txid and text,
    # carried lines sit at >= 1000 -- the two never overlap.
    from ff9mapkit import build, extract
    from ff9mapkit.config import ModLayout
    meta, toml = extract.write_native_project("fbg_n00_tshp_map007_th_orc_0", tmp_path / "proj",
                                              name="THORC", field_id=30003,
                                              graft_player_funcs=True, carry_text=True)
    # add an AUTHORED npc line to the imported field.toml
    txt = toml.read_text(encoding="utf-8")
    txt += '\n[[npc]]\nname = "mine"\npreset = "vivi"\npos = [0, 0]\ndialogue = "My own words"\n'
    toml.write_text(txt, encoding="utf-8")
    p = build.FieldProject.load(toml)
    build.build_mod([p], tmp_path / "dist", mod_name="FF9CustomMap")
    body = ModLayout(tmp_path / "dist").mes_path("us", p.text_block).read_text(encoding="utf-8")
    m = dialogue.parse_mes(body)
    assert m[500].text == "My own words"                     # authored line at the authored band, intact
    assert all(t >= 1000 for t in m if t != 500 and t >= 500)   # carried lines disjoint at >= 1000
