"""The tk-FREE half of editor/theme.py: palette tables, the palette picker, and the OS dark-mode
probe. No display, no tkinter (like the other editor headless tests). The Tk styling in
``apply_theme`` is verified by the human in the running editor (can't drive a UI offline)."""

from __future__ import annotations

import re

from ff9mapkit.editor import theme

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
# every palette colour the app reads by name (app.py + theme.apply_theme) -- guards against drift.
_USED = {"bg", "surface", "surface_btn", "field", "text", "muted", "accent", "accent_fg",
         "accent_hover", "accent_pressed", "border", "success", "hover", "pressed", "scroll",
         "log_bg", "log_fg", "error", "warn"}


def test_palettes_share_one_key_set():
    keys = set(theme.LIGHT)
    for mode, pal in theme.THEMES.items():           # every selectable palette, not just LIGHT/DARK
        assert set(pal) == keys, f"{mode} has a different key set"


def test_palettes_have_every_key_the_app_uses():
    for pal in theme.THEMES.values():
        assert _USED <= set(pal)


def test_colours_are_hex_and_modes_flagged():
    for mode, pal in theme.THEMES.items():
        assert isinstance(pal["dark"], bool), mode
        for key, val in pal.items():
            if key == "dark":
                continue
            assert _HEX.match(val), f"{mode}.{key}={val!r} is not #rrggbb"
    assert theme.LIGHT["dark"] is False and theme.DARK["dark"] is True
    assert theme.LIGHT["text"] != theme.DARK["text"]     # the two schemes actually differ


def test_theme_choices_cover_every_palette():
    # the picker order must offer "auto" plus exactly the THEMES keys (no orphan choice, none missing).
    choice_modes = [m for m, _label in theme.THEME_CHOICES]
    assert choice_modes[0] == "auto"
    assert set(choice_modes[1:]) == set(theme.THEMES)
    assert len({m for m, _ in theme.THEME_CHOICES}) == len(theme.THEME_CHOICES)   # no dup
    assert all(label for _m, label in theme.THEME_CHOICES)                        # every choice is labelled


def test_pick_palette_explicit():
    assert theme.pick_palette("light") is theme.LIGHT
    assert theme.pick_palette("dark") is theme.DARK
    for mode, pal in theme.THEMES.items():
        assert theme.pick_palette(mode) is pal


def test_pick_palette_auto_returns_a_known_palette():
    assert theme.pick_palette("auto") in (theme.LIGHT, theme.DARK)
    assert theme.pick_palette() in (theme.LIGHT, theme.DARK)       # default mode is auto


def test_pick_palette_unknown_mode_falls_back_to_auto():
    # a stale/garbage saved preference must never crash -> resolve to the OS default (light or dark)
    assert theme.pick_palette("no-such-theme") in (theme.LIGHT, theme.DARK)
    assert theme.pick_palette("") in (theme.LIGHT, theme.DARK)
    assert theme.pick_palette(None) in (theme.LIGHT, theme.DARK)


def test_pick_palette_auto_follows_os_dark(monkeypatch):
    # pin the OS probe so BOTH arms (the DARK one never runs on a light-mode CI box) are exercised; the
    # unknown-mode fallback shares the same resolution, so check it too.
    monkeypatch.setattr(theme, "detect_os_dark", lambda: True)
    assert theme.pick_palette("auto") is theme.DARK
    assert theme.pick_palette("no-such") is theme.DARK
    monkeypatch.setattr(theme, "detect_os_dark", lambda: False)
    assert theme.pick_palette("auto") is theme.LIGHT
    assert theme.pick_palette("no-such") is theme.LIGHT


# --- contrast / legibility invariants (tk-free WCAG relative-luminance) -------------------
def _luminance(hexstr: str) -> float:
    r, g, b = (int(hexstr[i:i + 2], 16) / 255 for i in (1, 3, 5))

    def _lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _contrast(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def test_palette_contrast_invariants():
    # Lenient floors (current 7 palettes pass) so this fires only on a real regression: invisible button
    # text (accent_fg == accent), unreadable hints (muted ~ bg), or a mislabeled dark/light flag.
    for mode, pal in theme.THEMES.items():
        assert _contrast(pal["text"], pal["bg"]) >= 4.0, f"{mode}: body text on bg"
        assert _contrast(pal["text"], pal["surface"]) >= 4.0, f"{mode}: body text on surface"
        assert _contrast(pal["accent_fg"], pal["accent"]) >= 3.0, f"{mode}: text on the accent button"
        assert _contrast(pal["muted"], pal["bg"]) >= 2.7, f"{mode}: hint text on bg"
        assert (_luminance(pal["bg"]) < 0.5) is pal["dark"], f"{mode}: dark flag disagrees with bg luminance"


def test_detect_os_dark_is_a_safe_bool():
    assert isinstance(theme.detect_os_dark(), bool)              # never raises, always a bool
