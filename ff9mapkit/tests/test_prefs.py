"""The tiny persistent-UI-preferences store (ff9mapkit.prefs). stdlib-only, never raises; the config dir
is redirected to a tmp path via provision._user_dir so the test never touches the real %LOCALAPPDATA%."""

from __future__ import annotations

from ff9mapkit import prefs


def _isolate(tmp_path, monkeypatch):
    """Point prefs at a throwaway config dir (mirrors how update_check is isolated)."""
    monkeypatch.setattr(prefs.provision, "_user_dir", lambda sub: tmp_path / sub)


def test_defaults_when_no_file(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert prefs.load() == {}
    assert prefs.theme() == "auto"                    # the built-in default
    assert prefs.get("nope", "fallback") == "fallback"


def test_set_theme_round_trips(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    prefs.set_theme("nord")
    assert prefs.theme() == "nord"
    assert prefs.load()["theme"] == "nord"            # actually persisted to disk


def test_put_preserves_unrelated_keys(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    prefs.set_theme("dracula")
    prefs.put("other", 7)
    assert prefs.theme() == "dracula"                 # not clobbered by the second write
    assert prefs.get("other") == 7


def test_corrupt_file_degrades_to_defaults(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    p = prefs._path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ this is not json", encoding="utf-8")
    assert prefs.load() == {}                         # no raise
    assert prefs.theme() == "auto"


def test_non_string_theme_falls_back(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    prefs.put("theme", 123)                           # a malformed value must not break theme()
    assert prefs.theme() == "auto"


def test_density_defaults_and_round_trips(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert prefs.density() == "comfortable"           # the built-in default (newcomer-friendly)
    prefs.set_density("compact")
    assert prefs.density() == "compact" and prefs.load()["density"] == "compact"
    prefs.set_density("bogus")                         # an unknown value is coerced back to the default
    assert prefs.density() == "comfortable"
    prefs.put("density", 5)                            # a malformed on-disk value degrades to the default
    assert prefs.density() == "comfortable"


def test_guided_mode_defaults_and_round_trips(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert prefs.guided() is True                      # Guided is the newcomer-friendly default
    prefs.set_guided(False)
    assert prefs.guided() is False and prefs.load()["guided"] is False
    prefs.set_guided(True)
    assert prefs.guided() is True


def test_motion_defaults_and_round_trips(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert prefs.motion() == "auto"                    # follow the OS by default
    prefs.set_motion("off")
    assert prefs.motion() == "off" and prefs.load()["motion"] == "off"
    prefs.set_motion("on")
    assert prefs.motion() == "on"
    prefs.set_motion("bogus")                          # an unknown value coerces back to auto
    assert prefs.motion() == "auto"
