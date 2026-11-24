"""The sound catalog (:mod:`ff9mapkit.soundcat`) -- the read side of the audio pillar.

Everything here is OFFLINE: the ``.eb``, the AKB container, the Ogg stream and the manifests are all
assembled in this file (zero Square-Enix bytes), the cache dir is a tmp tree, and the install seams
(:func:`soundcat._stamp`, :func:`sound.read_text_assets`, :func:`soundcat._field_census`,
:func:`soundcat.read_akb`) are monkeypatched -- so nothing can read this machine's install or its kit
cache. The shipped names table is checked as data (its shape, never its taste).
"""
from __future__ import annotations

import json
import re
import struct

import pytest

from ff9mapkit import sound, soundcat as SC
from ff9mapkit.eb import opcodes


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Pin the kit cache to a tmp tree and forget the in-process memo, per test."""
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path / "kitdata"))
    SC._MEMO.clear()
    yield
    SC._MEMO.clear()


# ------------------------------------------------------------------------------- synthetic bytes ---
def _eb_file(entries) -> bytes:
    """A multi-entry ``.eb`` (EbScript's layout: 8-byte slots at 0x80; per entry etype, func count,
    a (tag, fpos) table, then the bodies). ``entries`` = per entry a list of ``(tag, body)``."""
    blobs = []
    for funcs in entries:
        fc = len(funcs)
        table, bodies, fpos = b"", b"", fc * 4
        for tag, body in funcs:
            table += struct.pack("<HH", tag, fpos)
            bodies += body
            fpos += len(body)
        blobs.append(bytes([0, fc]) + table + bodies)
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = len(blobs)
    slots, out, off = b"", b"", 8 * len(blobs)
    for b in blobs:
        slots += struct.pack("<HHBBH", off, len(b), 0, 0, 0)
        off += len(b)
        out += b
    return bytes(head) + slots + out


RET = b"\x04"


def _field_eb(*instrs) -> bytes:
    return _eb_file([[(0, b"".join(instrs) + RET)]])


def _akb2(ogg: bytes, *, rate=44100, loop=(0, 0), loop2=(0, 0)) -> bytes:
    hdr = bytearray(SC.AKB2_HEADER)
    hdr[0:4] = b"AKB2"
    struct.pack_into("<H", hdr, SC._AKB2_AUDIO + 6, rate)
    struct.pack_into("<7I", hdr, SC._AKB2_AUDIO + 8, len(ogg), 0, loop[0], loop[1], 0x10, loop2[0], loop2[1])
    return bytes(hdr) + ogg


def _ogg_page(payload: bytes, granule: int) -> bytes:
    return b"OggS" + bytes([0, 0]) + struct.pack("<q", granule) + bytes(12) + bytes([1, len(payload)]) + payload


def _ogg(*, rate=22050, channels=1, samples=44100, comments=()) -> bytes:
    ident = b"\x01vorbis" + struct.pack("<IBI", 0, channels, rate) + bytes(12)
    vendor = b"kit-test"
    body = struct.pack("<I", len(vendor)) + vendor + struct.pack("<I", len(comments))
    for c in comments:
        cb = c.encode("utf-8")
        body += struct.pack("<I", len(cb)) + cb
    return (_ogg_page(ident, 0) + _ogg_page(b"\x03vorbis" + body, 0)
            + _ogg_page(b"audio", samples // 2) + _ogg_page(b"audio", samples))


def _manifest(rows) -> str:
    return json.dumps({"data": [{"name": rid, "soundIndex": str(i), "type": "x"} for i, rid in rows]})


# --------------------------------------------------------------------------- the sound-code word ---
@pytest.mark.parametrize("code,expect", [
    (0, ("music", "start")),              # FF9SOUND_SONG_PLAY -- what `[music] song` compiles to
    (1792, ("music", "load")),            # the LOAD a field rescore must also rewrite
    (265, ("music", "stop")),             # SONG_STOPCURRENT: parm bits ride below the op
    (4096, ("sfx", "start")),
    (53248, ("sfx", "start")),            # RunSoundCode3's 3-arg form: argc bits ride above the kind
    (8192, ("stream", "start")),
    (12288, ("instr", "start")),
])
def test_the_sound_code_word_decodes_to_kind_and_operation(code, expect):
    assert SC.decode_sound_code(code) == expect


def test_an_operation_outside_the_table_is_recorded_not_raised():
    assert SC.decode_sound_code(4096 | (13 << 8)) == ("sfx", "op13")


def test_a_field_script_yields_the_sounds_it_names():
    eb = _field_eb(opcodes.run_sound_code(0, 9),                       # play song 9
                   opcodes.run_sound_code(1792, 9),                    # load song 9: the same sound, once
                   opcodes.encode(0xC8, 53248, 633, 0, 127, 128),      # a 3-arg sfx start
                   opcodes.run_sound_code(8192, 5),                    # a stream
                   opcodes.run_sound_code(265, 0xFFFF))                # "stop current" names nothing
    assert SC.scan_field_sounds(eb) == [("music", 9), ("sfx", 633), ("stream", 5)]


def test_a_script_with_no_sound_calls_yields_nothing():
    assert SC.scan_field_sounds(_field_eb()) == []


# ----------------------------------------------------------------------------- manifests + cache ---
def test_the_effect_manifest_inverts_to_sound_then_effects():
    text = json.dumps({"data": {"14": ["Sounds03/SE52/se520008", "Sounds02/SE02/se020020"],
                                "5": ["Sounds03/SE52/se520008"], "junk": ["x"]}})
    assert SC.parse_effect_manifest(text) == {"Sounds03/SE52/se520008": [5, 14],
                                              "Sounds02/SE02/se020020": [14]}


@pytest.mark.parametrize("bad", ["", "{", "[]", '{"data": [1, 2]}'])
def test_a_malformed_effect_manifest_is_empty_never_an_error(bad):
    assert SC.parse_effect_manifest(bad) == {}


def _sample_map(stamp="s1") -> SC.SoundMap:
    return SC.SoundMap(
        stamp=stamp,
        rows={"music": [{"id": 0, "resource_id": "Sounds01/BGM_/music006"},
                        {"id": 9, "resource_id": "Sounds01/BGM_/music008"}],
              "sfx": [{"id": 108, "resource_id": "Sounds02/SE00/se000004"},
                      {"id": 633, "resource_id": "Sounds02/SE00/se000012"},
                      {"id": 2000, "resource_id": "Sounds03/SE52/se520008"}],
              "stream": [{"id": 5, "resource_id": "Sounds02/song_/song0005_0"}],
              "movie": [{"id": 0, "resource_id": "Sounds02/Movie_/FMV001"}]},
        uses={"music": {9: [100, 101, 300]}, "sfx": {633: [100]}, "stream": {}, "movie": {}},
        effects={"Sounds03/SE52/se520008": [5, 14]}, field_count=3)


def test_the_map_survives_its_json_round_trip():
    sm = _sample_map()
    back = SC._from_cache_dict(json.loads(json.dumps(SC._to_cache_dict(sm))))
    assert back == sm
    assert back.uses["music"][9] == [100, 101, 300]            # int keys came back as ints


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(version=SC.CACHE_VERSION + 1),          # another version's cache
    lambda d: d.pop("uses"),                                   # a truncated one
    lambda d: d.update(rows="nope"),                           # a foreign shape
])
def test_a_stale_or_foreign_cache_is_ignored_not_misread(mutate):
    d = SC._to_cache_dict(_sample_map())
    mutate(d)
    assert SC._from_cache_dict(d) is None
    assert SC._from_cache_dict("not a dict") is None


def _seam_install(monkeypatch, *, stamp="s1", census_calls=None):
    """Stand in for the install: a stamp, the manifests, and a census that counts its own calls."""
    monkeypatch.setattr(SC, "_stamp", lambda game=None: stamp)
    texts = {sound.MANIFESTS["music"]: _manifest([(0, "Sounds01/BGM_/music006"), (9, "Sounds01/BGM_/music008")]),
             sound.MANIFESTS["sfx"]: _manifest([(633, "Sounds02/SE00/se000012")]),
             sound.MANIFESTS["stream"]: _manifest([(5, "Sounds02/song_/song0005_0")]),
             sound.MANIFESTS["movie"]: _manifest([(0, "Sounds02/Movie_/FMV001")]),
             SC.EFFECT_MANIFEST: json.dumps({"data": {"14": ["Sounds02/SE00/se000012"]}})}
    monkeypatch.setattr(sound, "read_text_assets", lambda names, game=None: dict(texts))

    def _census(game=None):
        if census_calls is not None:
            census_calls.append(1)
        return {"music": {9: [100, 101], 77: [100]}, "sfx": {633: [100]}, "stream": {}, "movie": {}}, 2

    monkeypatch.setattr(SC, "_field_census", _census)


def test_a_fresh_build_reads_the_install_once_then_the_disk_serves_it(monkeypatch):
    calls = []
    _seam_install(monkeypatch, census_calls=calls)
    assert SC.cached_map() is None                              # nothing warm yet -- and nothing built
    assert calls == []
    sm = SC.build_map()
    assert calls == [1]
    assert [r["id"] for r in sm.rows["music"]] == [0, 9]
    assert sm.uses["music"] == {9: [100, 101]}                  # id 77 is in no manifest: it places nothing
    assert sm.effects == {"Sounds02/SE00/se000012": [14]}
    SC._MEMO.clear()                                            # a NEW process: only the disk is warm
    assert SC.cached_map() == sm
    assert SC.build_map() == sm
    assert calls == [1], "a warm disk cache must not re-run the census"
    SC.build_map(force=True)
    assert calls == [1, 1], "force rebuilds"


def test_a_game_update_invalidates_the_disk_cache(monkeypatch):
    calls = []
    _seam_install(monkeypatch, stamp="before", census_calls=calls)
    SC.build_map()
    SC._MEMO.clear()
    _seam_install(monkeypatch, stamp="after", census_calls=calls)   # resources.assets changed
    assert SC.cached_map() is None, "another install's map must never be served"
    SC.build_map()
    assert calls == [1, 1]


# -------------------------------------------------------------------------------------- names ---
def test_names_parse_both_value_forms_and_drop_the_rest():
    text = ('[music]\nmusic008 = "Vivi\'s Theme"\n'
            '[sfx]\nSE000012 = { title = "Door opening", tags = ["Door", " wood "] }\n'
            'se000099 = { tags = "tagged" }\nse000100 = ""\nse000101 = 7\n'
            '[bogus]\nx = "y"\n')
    names = SC.parse_names(text)
    assert names == {"music": {"music008": {"title": "Vivi's Theme", "tags": []}},
                     "sfx": {"se000012": {"title": "Door opening", "tags": ["door", "wood"]},
                             "se000099": {"title": "", "tags": ["tagged"]}}}
    assert SC.parse_names("this is [not toml") == {}, "a broken file blanks nothing"


def test_names_serialize_back_to_what_they_parse_from():
    names = {"sfx": {"se000012": {"title": 'He said "creak"', "tags": ["door", "wood"]},
                     "se000004": {"title": "Receive item", "tags": []}},
             "music": {"music008": {"title": "Vivi's Theme", "tags": []}}}
    text = SC.serialize_names(names, header="# hello")
    assert text.startswith("# hello\n")
    assert SC.parse_names(text) == names
    assert text.index("[music]") < text.index("[sfx]"), "kinds in KINDS order"


def test_the_user_overlay_wins_per_sound_and_clearing_it_falls_back(tmp_path):
    baked = tmp_path / "baked.toml"
    baked.write_text('[sfx]\nse000012 = "Door opening"\nse000004 = "Receive item"\n', encoding="utf-8")
    user = tmp_path / "cfg" / "sound_names.toml"                # a directory that does not exist yet
    SC.save_user_name("sfx", "SE000012", "Heavy oak door", ["door", "wood"], path=user)
    names = SC.load_names(user, baked_path=baked)
    assert names["sfx"]["se000012"] == {"title": "Heavy oak door", "tags": ["door", "wood"]}
    assert names["sfx"]["se000004"]["title"] == "Receive item", "the rest of the baked table stands"
    SC.save_user_name("sfx", "se000012", "", [], path=user)     # clear -> the kit's name is back
    assert SC.load_names(user, baked_path=baked)["sfx"]["se000012"]["title"] == "Door opening"
    with pytest.raises(ValueError):
        SC.save_user_name("voices", "x", "y", path=user)


def test_saving_one_name_keeps_every_other_overlay_entry(tmp_path):
    user = tmp_path / "sound_names.toml"
    SC.save_user_name("sfx", "se000001", "One", path=user)
    SC.save_user_name("music", "music008", "Two", ["vivi"], path=user)
    SC.save_user_name("sfx", "se000002", "Three", path=user)
    over = SC.parse_names(user.read_text(encoding="utf-8"))
    assert set(over["sfx"]) == {"se000001", "se000002"} and over["music"]["music008"]["tags"] == ["vivi"]


def test_tags_parse_lowercased_and_deduplicated_in_order():
    assert SC.parse_tags(" Door, wood ,door,, ") == ["door", "wood"]
    assert SC.parse_tags("") == []


def test_the_shipped_names_table_is_well_formed():
    """Shape only: it parses, every key is a real-looking file stem of its kind, no title is empty or
    a placeholder, and no key is written twice (tomllib refuses a duplicate key, so parsing proves it)."""
    text = SC.baked_names_path().read_text(encoding="utf-8")
    names = SC.parse_names(text)
    assert len(names.get("music", {})) >= 100 and len(names.get("sfx", {})) >= 80
    assert all(re.fullmatch(r"music\d{3}", k) for k in names["music"]), "music keys are music###"
    assert all(re.fullmatch(r"se\d{6}", k) for k in names["sfx"]), "sfx keys are se######"
    for kind, tbl in names.items():
        for stem, ent in tbl.items():
            assert ent["title"] and "unknown" not in ent["title"].lower(), (kind, stem, ent)
    raw_keys = re.findall(r"^(\w+) = ", text, re.M)
    assert len(raw_keys) == sum(len(t) for t in names.values()), "an entry was dropped while parsing"


# ------------------------------------------------------------------------------------ entries ---
def test_entries_carry_names_counts_and_a_label():
    sm = _sample_map()
    names = {"music": {"music008": {"title": "Vivi's Theme", "tags": ["vivi"]}}}
    ents = SC.sounds(sm, names)
    assert [s.kind for s in ents] == ["music", "music", "sfx", "sfx", "sfx", "stream", "movie"]
    vivi = next(s for s in ents if s.stem == "music008")
    assert (vivi.title, vivi.tags, vivi.bank, vivi.n_fields) == ("Vivi's Theme", ("vivi",), "BGM_", 3)
    assert vivi.label == "Vivi's Theme  ·  id 9", "short: a row must never lose its id to an ellipsis"
    assert vivi.full_label == "Vivi's Theme — Sounds01/BGM_/music008, id 9  ·  tags: vivi"
    battle = next(s for s in ents if s.stem == "music006")
    assert battle.label == "music006  ·  id 0", "an unnamed sound leads with its file stem"
    assert battle.full_label == "Sounds01/BGM_/music006, id 0"
    assert next(s for s in ents if s.stem == "se520008").n_effects == 2


def test_a_mod_folders_added_rows_list_after_stock_flagged_custom():
    ents = SC.sounds(_sample_map(), {}, extra_rows={"music": [{"id": 1000, "resource_id": "Sounds01/BGM_/custom1000"}]})
    custom = [s for s in ents if s.custom]
    assert [(s.kind, s.id, s.stem) for s in custom] == [("music", 1000, "custom1000")]
    assert ents.index(custom[0]) == 2, "after the two stock music rows, before the sfx"


def test_filtering_by_kind_bank_name_state_and_text():
    sm = _sample_map()
    ents = SC.sounds(sm, {"music": {"music008": {"title": "Vivi's Theme", "tags": ["black-mage"]}}})
    assert [s.stem for s in SC.filter_sounds(ents, kind="sfx", bank="SE00")] == ["se000004", "se000012"]
    assert [s.stem for s in SC.filter_sounds(ents, kind="music", unnamed_only=True)] == ["music006"]
    assert [s.stem for s in SC.filter_sounds(ents, "VIVI")] == ["music008"]              # title, any case
    assert [s.stem for s in SC.filter_sounds(ents, "black-mage")] == ["music008"]        # a tag
    assert [s.stem for s in SC.filter_sounds(ents, "633")] == ["se000012"]               # an id
    assert [s.stem for s in SC.filter_sounds(ents, "se52")] == ["se520008"]              # a stem / bank
    assert SC.filter_sounds(ents, "vivi sfx") == [], "every term must match"
    by_place = SC.filter_sounds(ents, "treno", place_text_fn=lambda s: "Treno" if s.stem == "se000012" else "")
    assert [s.stem for s in by_place] == ["se000012"], "a place name is searchable text"
    assert SC.banks(ents, "sfx") == ["SE00", "SE52"]


# --------------------------------------------------------------------------------- where used ---
@pytest.mark.parametrize("raw,place", [
    ("A. Castle (ids 1200+)", "A. Castle"), ("Dali [vgdl]", "Dali"), ("Alexandria", "Alexandria"),
    ("Cargo Ship [cshp] (ids 300+)", "Cargo Ship"), ("", ""), (None, ""),
])
def test_a_catalog_arc_name_reads_as_a_place(raw, place):
    assert SC.place_label(raw) == place


def test_places_group_a_sounds_fields_by_place_with_unclaimed_fields_last():
    sm = _sample_map()
    join = ({100: "a_castle", 101: "a_castle_2"},
            {"a_castle": {"name": "A. Castle", "zone": "alxc"},
             "a_castle_2": {"name": "A. Castle (ids 1200+)", "zone": "alxc"}})
    assert SC.places(sm, "music", 9, join=join) == [{"name": "A. Castle", "fields": [100, 101]},
                                                    {"name": None, "fields": [300]}]
    assert SC.place_names(sm, "music", 9, join=join) == ["A. Castle"]
    two = ({100: "ice", 101: "alex", 300: "alex"}, {"ice": {"name": "Ice Cavern"}, "alex": {"name": "Alexandria"}})
    assert SC.place_names(sm, "music", 9, join=two) == ["Alexandria", "Ice Cavern"], "busiest place first"
    assert SC.places(sm, "music", 0, join=join) == []


def test_the_real_region_catalog_joins_fields_to_named_places():
    field_arc, arcs = SC.zone_join()                             # packaged data: install-free
    assert len(field_arc) > 700 and arcs
    assert all(a["name"] for a in arcs.values())


# ------------------------------------------------------------------------------ AKB + Ogg bytes ---
def test_an_akb2_asset_splits_into_its_ogg_and_its_loop_points():
    ogg = _ogg(rate=44100, channels=2, samples=88200)
    raw = _akb2(ogg, rate=44100, loop=(11025, 88199))
    assert SC.parse_akb(raw) == {"ogg_offset": 304, "rate": 44100, "loop_start": 11025,
                                 "loop_end": 88199, "loop_start2": 0, "loop_end2": 0}
    out, info = SC.akb_to_ogg(raw)
    assert out == ogg and out[:4] == b"OggS"
    assert (info["rate"], info["channels"], info["samples"]) == (44100, 2, 88200)
    assert info["seconds"] == pytest.approx(2.0)
    assert (info["loop_start"], info["loop_end"]) == (11025, 88199)


def test_the_header_rate_wins_over_the_streams_for_the_length():
    out, info = SC.akb_to_ogg(_akb2(_ogg(rate=22050, samples=44100), rate=44100))
    assert info["rate"] == 44100 and info["seconds"] == pytest.approx(1.0)


def test_an_ogg_reports_its_own_loop_comments_when_the_header_has_none():
    ogg = _ogg(samples=44100, comments=("LoopStart=100", "loopend=40000", "TITLE=x", "LoopStart2=bad"))
    _out, info = SC.akb_to_ogg(_akb2(ogg, rate=0))
    assert (info["loop_start"], info["loop_end"], info["rate"]) == (100, 40000, 22050)


@pytest.mark.parametrize("raw", [b"", b"RIFF" + bytes(400), b"AKB2" + bytes(10), b"AKB2" + bytes(400)])
def test_a_payload_that_is_not_akb_wrapped_ogg_is_refused(raw):
    with pytest.raises(ValueError):
        SC.parse_akb(raw)


def test_ogg_info_never_raises_on_garbage():
    for junk in (b"", b"OggS", b"\x03vorbis" + b"\xff" * 9, bytes(64)):
        assert SC.ogg_info(junk)["seconds"] == 0.0


def test_a_resource_names_its_bundles_and_container_key():
    assert SC.bundle_candidates("Sounds01/BGM_/music006") == (61, 601)
    assert SC.bundle_candidates("Sounds03/SE52/se520008") == (63, 621)
    assert SC.bundle_candidates("Elsewhere/x") == ()
    assert SC.container_key("Sounds02/SE00/se000012") == "assets/resources/sounds/sounds02/se00/se000012.akb.bytes"


def test_extraction_reads_the_install_once_then_serves_the_cache(monkeypatch):
    reads = []

    def _read(resource_id, game=None):
        reads.append(resource_id)
        return _akb2(_ogg(rate=44100, samples=44100), loop=(0, 0))

    monkeypatch.setattr(SC, "read_akb", _read)
    path, info = SC.extract_ogg("Sounds02/SE00/se000012")
    assert path.read_bytes()[:4] == b"OggS" and path.parent == SC.ogg_cache_dir()
    assert info["seconds"] == pytest.approx(1.0)
    path2, info2 = SC.extract_ogg("Sounds02/SE00/se000012")
    assert (path2, info2) == (path, info) and reads == ["Sounds02/SE00/se000012"]


def test_the_ogg_cache_is_pruned_oldest_first(monkeypatch):
    import os
    d = SC.ogg_cache_dir()
    d.mkdir(parents=True)
    for i, name in enumerate(("old", "mid", "new")):
        (d / f"{name}.ogg").write_bytes(bytes(100))
        (d / f"{name}.json").write_text("{}", encoding="utf-8")
        os.utime(d / f"{name}.ogg", (1000 + i, 1000 + i))
    SC._prune_ogg_cache(limit=250)
    assert sorted(p.name for p in d.iterdir()) == ["mid.json", "mid.ogg", "new.json", "new.ogg"]


def test_a_mod_folders_override_is_what_plays_and_what_exports(tmp_path, monkeypatch):
    monkeypatch.setattr(SC, "read_akb", lambda rid, game=None: _akb2(_ogg(samples=44100)))
    rid = "Sounds01/BGM_/music008"
    mod = tmp_path / "Mod"
    path, _info, source = SC.playable(rid, mod_folder=mod)
    assert source == "stock" and SC.override_path(mod, rid) is None
    loose = mod / sound.override_rel_path(rid)
    loose.parent.mkdir(parents=True)
    mine = _ogg(rate=48000, samples=96000, comments=("LoopStart=10", "LoopEnd=90000"))
    loose.write_bytes(mine)
    path, info, source = SC.playable(rid, mod_folder=mod)
    assert (path, source) == (loose, "override")
    assert (info["rate"], info["loop_end"]) == (48000, 90000) and info["seconds"] == pytest.approx(2.0)
    out = SC.export_ogg(rid, tmp_path / "out" / "x.ogg", mod_folder=mod)
    assert out.read_bytes() == mine


def test_a_mod_folders_manifest_contributes_only_the_ids_it_adds(tmp_path):
    sm = _sample_map()
    mod = tmp_path / "Mod"
    assert SC.mod_custom_rows(mod, sm) == {} and SC.mod_custom_rows(None, sm) == {}
    mp = sound.manifest_override_path(mod, "music")
    mp.parent.mkdir(parents=True)
    mp.write_text(sound.serialize_manifest([
        {"id": 0, "resource_id": "Sounds01/BGM_/music006", "type": "Music"},
        {"id": 9, "resource_id": "Sounds01/BGM_/music008", "type": "Music"},
        {"id": 1000, "resource_id": "Sounds01/BGM_/custom1000", "type": "Music"}]), encoding="utf-8")
    assert SC.mod_custom_rows(mod, sm) == {"music": [{"id": 1000, "resource_id": "Sounds01/BGM_/custom1000"}]}


@pytest.mark.parametrize("secs,text", [(84.7, "1:24"), (0.42, "0.4s"), (9.96, "10.0s"), (600, "10:00"), (0, "0.0s")])
def test_seconds_format_keeps_a_short_effect_from_reading_as_zero(secs, text):
    assert SC.format_seconds(secs) == text


# ------------------------------------------------------------------------------------- the CLI ---
def _cli(argv):
    from ff9mapkit import cli
    return cli, cli.build_parser().parse_args(argv)


def test_audio_export_resolves_the_id_and_writes_the_ogg(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sound, "resolve_resource_id",
                        lambda i, kind="music", game=None: {("sfx", 633): "Sounds02/SE00/se000012"}[(kind, i)])
    monkeypatch.setattr(SC, "read_akb", lambda rid, game=None: _akb2(_ogg(samples=44100)))
    out = tmp_path / "door.ogg"
    cli, args = _cli(["audio-export", "633", "--kind", "sfx", "--out", str(out)])
    assert args.func is cli._cmd_audio_export and args.game is None
    assert cli._cmd_audio_export(args) == 0
    assert out.read_bytes()[:4] == b"OggS"
    assert "exported sfx id 633 = Sounds02/SE00/se000012" in capsys.readouterr().out


def test_audio_export_reports_a_bad_id_instead_of_a_traceback(monkeypatch, capsys):
    def _no(i, kind="music", game=None):
        raise KeyError(f"{kind} id {i} not found")
    monkeypatch.setattr(sound, "resolve_resource_id", _no)
    cli, args = _cli(["audio-export", "99999"])
    assert cli._cmd_audio_export(args) == 2
    assert "audio-export failed" in capsys.readouterr().err


def test_the_list_verbs_print_the_kits_titles_and_filter_on_them(monkeypatch, capsys):
    monkeypatch.setattr(sound, "read_manifest", lambda kind="music", game=None, use_cache=True: [
        {"id": 0, "resource_id": "Sounds01/BGM_/music006", "type": "Music"},
        {"id": 9, "resource_id": "Sounds01/BGM_/music008", "type": "Music"},
        {"id": 500, "resource_id": "Sounds01/BGM_/music999", "type": "Music"}])
    cli, args = _cli(["music-list"])
    cli._cmd_sound_list(args)
    out = capsys.readouterr().out
    assert "      9  Sounds01/BGM_/music008  Vivi's Theme" in out
    assert "    500  Sounds01/BGM_/music999\n" in out, "an unnamed track prints no trailing column"
    cli, args = _cli(["music-list", "--filter", "vivi"])
    cli._cmd_sound_list(args)
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("1 music") and "music008" in out


def test_the_song_picker_shows_titles_and_a_rename_reaches_it(tmp_path, monkeypatch):
    from ff9mapkit import infohub
    monkeypatch.setattr(sound, "read_manifest", lambda kind="music", game=None, use_cache=True: [
        {"id": 9, "resource_id": "Sounds01/BGM_/music008", "type": "Music"},
        {"id": 500, "resource_id": "Sounds01/BGM_/music999", "type": "Music"}])
    user = tmp_path / "names.toml"
    monkeypatch.setattr(SC, "user_names_path", lambda: user)
    infohub.forget_songs()
    try:
        ents = infohub._song_entries(force=True)
        assert [(e.name, e.ident) for e in ents] == [("Vivi's Theme", 9), ("music999", 500)]
        assert "music008" in ents[0].summary, "the file name stays searchable"
        assert infohub.snippet(ents[0]) == "[music]\nsong = 9  # Vivi's Theme"
        SC.save_user_name("music", "music999", "My new theme", path=user)
        assert infohub._song_entries(force=True)[1].name == "music999", "memoized until told otherwise"
        infohub.forget_songs()
        assert infohub._song_entries(force=True)[1].name == "My new theme"
    finally:
        infohub.forget_songs()


def test_only_music_and_sfx_are_mintable(tmp_path):
    with pytest.raises(ValueError, match="mint"):
        sound.mint_song(tmp_path / "x.wav", tmp_path, kind="stream")
