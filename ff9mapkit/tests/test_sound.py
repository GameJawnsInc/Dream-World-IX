"""Tests for custom-audio authoring (ff9mapkit.sound). Pure logic + an ffmpeg round-trip when ffmpeg is
present; the resources.assets manifest EXTRACTION is install-gated (covered by the in-game proof, not here)."""
import json
import math
import shutil
import struct
import wave

import pytest

from ff9mapkit import sound as S

_MANIFEST = json.dumps({"data": [
    {"name": "Sounds01/BGM_/music006", "soundIndex": "0", "type": "Music"},
    {"name": "Sounds01/BGM_/music008", "soundIndex": "9", "type": "Music"},
    {"name": "bad", "soundIndex": "notanint", "type": "Music"},     # skipped (bad id)
]})

_HAS_FFMPEG = bool(shutil.which("ffmpeg"))


def test_parse_manifest_sorts_and_skips_bad():
    t = S.parse_manifest(_MANIFEST)
    assert [r["id"] for r in t] == [0, 9]                            # sorted, bad row dropped
    assert t[0] == {"id": 0, "resource_id": "Sounds01/BGM_/music006", "type": "Music"}


def test_override_rel_path():
    assert S.override_rel_path("Sounds01/BGM_/music006") == \
        "StreamingAssets/Assets/Resources/Sounds/Sounds01/BGM_/music006.ogg"


def test_resolve_resource_id(monkeypatch):
    monkeypatch.setattr(S, "read_manifest", lambda kind="music", game=None: S.parse_manifest(_MANIFEST))
    assert S.resolve_resource_id(9, "music") == "Sounds01/BGM_/music008"
    with pytest.raises(KeyError):
        S.resolve_resource_id(999, "music")


def _tiny_wav(path, secs=0.2, sr=22050, freq=440):
    n = int(sr * secs)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(2 * math.pi * freq * i / sr))) for i in range(n)))


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg not on PATH")
def test_encode_ogg_roundtrip_with_loop_tags(tmp_path):
    wav = tmp_path / "in.wav"
    _tiny_wav(wav)
    out = S.encode_ogg(wav, tmp_path / "out.ogg", loop_start=100, loop_end=4000)
    assert out.read_bytes()[:4] == b"OggS"                          # valid Ogg
    head = out.read_bytes()[:4000]
    assert b"LoopStart" in head and b"LoopEnd" in head              # loop tags embedded as Vorbis comments


def test_set_priority_to_ogg_edits_backs_up_and_is_idempotent(tmp_path, monkeypatch):
    ini = tmp_path / "Memoria.ini"
    ini.write_text("[Audio]\nPriorityToOGG = 0\nMusicVolume = 5\n", encoding="utf-8")
    monkeypatch.setattr(S.config, "find_game_path", lambda game=None: tmp_path)
    r = S.set_priority_to_ogg()
    assert r["changed"] and r["was"] == "0" and r["backup"]
    assert "PriorityToOGG = 1" in ini.read_text()
    r2 = S.set_priority_to_ogg()                                     # already 1 -> no-op, no new backup
    assert not r2["changed"] and r2["was"] == "1" and r2["backup"] is None


def test_set_priority_appends_when_key_missing(tmp_path, monkeypatch):
    ini = tmp_path / "Memoria.ini"
    ini.write_text("[Audio]\nMusicVolume = 5\n", encoding="utf-8")
    monkeypatch.setattr(S.config, "find_game_path", lambda game=None: tmp_path)
    S.set_priority_to_ogg()
    assert "PriorityToOGG = 1" in ini.read_text()


def test_volume_key_is_kind_aware():
    assert S.volume_key("music") == "MusicVolume"
    assert S.volume_key("sfx") == "SoundVolume"


def test_ini_volume_reads_the_governing_key(tmp_path, monkeypatch):
    (tmp_path / "Memoria.ini").write_text("[Audio]\nMusicVolume = 0\nSoundVolume = 7\n", encoding="utf-8")
    monkeypatch.setattr(S.config, "find_game_path", lambda game=None: tmp_path)
    assert S.ini_volume("music") == 0                      # muted -> the CLI warns
    assert S.ini_volume("sfx") == 7


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg not on PATH")
def test_deploy_audio_places_ogg_at_override_path(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "read_manifest", lambda kind="music", game=None: S.parse_manifest(_MANIFEST))
    wav = tmp_path / "in.wav"
    _tiny_wav(wav)
    res = S.deploy_audio(wav, 0, tmp_path / "mod", set_priority=False)
    assert res["resource_id"] == "Sounds01/BGM_/music006" and res["song_id"] == 0
    dest = tmp_path / "mod" / "StreamingAssets/Assets/Resources/Sounds/Sounds01/BGM_/music006.ogg"
    assert dest.exists() and dest.read_bytes()[:4] == b"OggS"


# --- new-song-id minting ---
def test_manifest_override_path_uses_ff9data_root(tmp_path):
    # the load-bearing correction: embedded-asset overrides live under FF9_Data/, NOT StreamingAssets/...
    assert S.manifest_override_path(tmp_path, "music") == \
        tmp_path / "FF9_Data" / "EmbeddedAsset" / "Manifest" / "Sounds" / "MusicMetaData.txt"


def test_serialize_manifest_roundtrips_through_parse():
    entries = [{"id": 0, "resource_id": "Sounds01/BGM_/music006", "type": "Music"},
               {"id": 1000, "resource_id": "Sounds01/BGM_/custom1000", "type": "Music"}]
    assert S.parse_manifest(S.serialize_manifest(entries)) == entries


def test_next_free_song_id_picks_the_band_then_skips_used():
    assert S.next_free_song_id([], "music") == 1000                # empty -> band base
    assert S.next_free_song_id([{"id": 1000, "resource_id": "x"}], "music") == 1001


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg not on PATH")
def test_mint_song_writes_manifest_ogg_and_accumulates(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "read_manifest", lambda kind="music", game=None: S.parse_manifest(_MANIFEST))
    wav = tmp_path / "in.wav"
    _tiny_wav(wav)
    mod = tmp_path / "mod"
    r1 = S.mint_song(wav, mod, set_priority=False)
    assert r1["minted"] and r1["song_id"] == 1000                  # auto-picked band base (stock max is 9)
    mpath = mod / "FF9_Data/EmbeddedAsset/Manifest/Sounds/MusicMetaData.txt"
    ogg = mod / "StreamingAssets/Assets/Resources/Sounds" / (r1["resource_id"] + ".ogg")
    assert mpath.exists() and ogg.exists() and ogg.read_bytes()[:4] == b"OggS"
    assert {e["id"] for e in S.parse_manifest(mpath.read_text())} == {0, 9, 1000}   # stock + minted
    r2 = S.mint_song(wav, mod, set_priority=False)                 # 2nd mint reads the OVERRIDE, not stock
    assert r2["song_id"] == 1001
    assert {e["id"] for e in S.parse_manifest(mpath.read_text())} == {0, 9, 1000, 1001}   # both preserved


# --- [music] file = build hook (content.music.mint_field_theme) ---
def test_mint_field_theme_mints_when_file_set(tmp_path, monkeypatch):
    from ff9mapkit.content import music as M
    called = {}

    def fake_mint(f, mod_root, **kw):
        called.update(f=str(f), mod_root=str(mod_root), kw=kw)
        return {"song_id": 1000, "resource_id": "Sounds01/BGM_/custom1000"}

    monkeypatch.setattr(S, "mint_song", fake_mint)                 # content.music calls sound.mint_song
    (tmp_path / "theme.ogg").write_bytes(b"x")
    r = M.mint_field_theme({"file": "theme.ogg", "loop_start": 5}, tmp_path, tmp_path / "mod")
    assert r["song_id"] == 1000
    assert called["kw"]["loop_start"] == 5 and called["kw"]["set_priority"] is False   # build never touches the ini
    assert called["f"].endswith("theme.ogg")                       # resolved relative to the field.toml dir


def test_mint_field_theme_noop_when_no_file_or_song_set(monkeypatch):
    from ff9mapkit.content import music as M
    monkeypatch.setattr(S, "mint_song", lambda *a, **k: pytest.fail("should not mint"))
    assert M.mint_field_theme(None, ".", ".") is None
    assert M.mint_field_theme({"song": 9}, ".", ".") is None       # a plain swap, no custom file
    assert M.mint_field_theme({"file": "x", "song": 9}, ".", ".") is None   # explicit song wins -> skip


def test_mint_field_theme_missing_file_raises(tmp_path):
    from ff9mapkit.content import music as M
    with pytest.raises(FileNotFoundError):
        M.mint_field_theme({"file": "nope.ogg"}, tmp_path, tmp_path / "mod")
