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


def test_an_explicit_text_size_always_beats_the_windows_slider(tmp_path, monkeypatch):
    """HEED's whole ordering, and the only part of it that can do harm if wrong.

    A saved value means the user went to Preferences and SAID what they want. Windows does not get to
    override that, ever -- the OS slider is a better FIRST GUESS, never a correction of a decision already
    made. Get this backwards and the app silently un-does a real choice on every launch.
    """
    _isolate(tmp_path, monkeypatch)
    monkeypatch.setattr(prefs, "os_text_scale", lambda: 150)      # Windows says 150
    prefs.set_text_scale(110)                                     # ...the user says 110
    assert prefs.text_scale() == 110, "an explicit choice was overridden by the OS slider"
    # and 100 is a CHOICE too, not an absence -- the seed must not resurrect itself over it
    prefs.set_text_scale(100)
    assert prefs.text_scale() == 100, "choosing 100% must stick even when Windows asks for more"


def test_with_nothing_saved_the_windows_slider_seeds_the_default(tmp_path, monkeypatch):
    """The feature: someone who has already told Windows they want bigger text gets it on first launch,
    with no preference to discover. Only when nothing is saved."""
    _isolate(tmp_path, monkeypatch)
    monkeypatch.setattr(prefs, "os_text_scale", lambda: 150)
    assert prefs.text_scale() == 150, "a fresh install ignored the OS text slider"
    monkeypatch.setattr(prefs, "os_text_scale", lambda: 100)
    assert prefs.text_scale() == 100


def test_a_corrupt_text_size_degrades_to_the_seed_not_to_100(tmp_path, monkeypatch):
    """A hand-edited or corrupt value must not silently cost a low-vision user their text size -- it is
    an absence of a valid choice, so it takes the same path an absence does."""
    _isolate(tmp_path, monkeypatch)
    monkeypatch.setattr(prefs, "os_text_scale", lambda: 125)
    for junk in ("big", 137, None, 3.5, True):
        prefs.put("text_scale", junk)
        assert prefs.text_scale() == 125, f"a {junk!r} value dropped the user to 100 instead of the seed"


def test_os_text_scale_is_inert_when_the_slider_was_never_touched(tmp_path, monkeypatch):
    """The COMMON case, and the one that must be boring: on a machine where the slider has never moved the
    key does not exist at all (verified on this one). Every failure path -- non-Windows, no winreg, missing
    key, junk value -- degrades to 100, the provably-inert setting. Same shape as theme.detect_os_dark,
    which has shipped this pattern for rounds.
    """
    _isolate(tmp_path, monkeypatch)
    import builtins
    real_import = builtins.__import__

    def no_winreg(name, *a, **k):
        if name == "winreg":
            raise ImportError("no winreg here")      # i.e. every non-Windows machine
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_winreg)
    assert prefs.os_text_scale() == 100, "a machine without winreg must land on the inert default"


def test_the_os_slider_snaps_into_the_rungs_we_actually_ship(tmp_path, monkeypatch):
    """Microsoft documents [100, 225]; we ship (100, 110, 125, 150). Windows' common stops must land
    exactly, anything above our top must clamp to it, and junk outside the documented range must not be
    obeyed -- a registry value is user-writable and 10000 is not a text size.
    """
    _isolate(tmp_path, monkeypatch)
    seen = {}

    def fake_reg(val):
        import winreg
        monkeypatch.setattr(winreg, "QueryValueEx", lambda *a: (val, 4))
        monkeypatch.setattr(winreg, "OpenKey", lambda *a, **k: object())
        monkeypatch.setattr(winreg, "CloseKey", lambda *a: None)
        return prefs.os_text_scale()

    for raw, want in ((100, 100), (125, 125), (150, 150),
                      (175, 150), (200, 150), (225, 150),      # above our top -> our top
                      (10000, 150), (0, 100), (-5, 100)):      # junk is clamped, never obeyed
        seen[raw] = fake_reg(raw)
        assert seen[raw] == want, f"TextScaleFactor={raw} -> {seen[raw]}, expected {want}"
    assert all(v in prefs.TEXT_SCALES for v in seen.values()), "the seed left the rungs we ship"
