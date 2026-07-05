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


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg not on PATH")
def test_deploy_audio_places_ogg_at_override_path(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "read_manifest", lambda kind="music", game=None: S.parse_manifest(_MANIFEST))
    wav = tmp_path / "in.wav"
    _tiny_wav(wav)
    res = S.deploy_audio(wav, 0, tmp_path / "mod", set_priority=False)
    assert res["resource_id"] == "Sounds01/BGM_/music006" and res["song_id"] == 0
    dest = tmp_path / "mod" / "StreamingAssets/Assets/Resources/Sounds/Sounds01/BGM_/music006.ogg"
    assert dest.exists() and dest.read_bytes()[:4] == b"OggS"
