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
    assert set(theme.LIGHT) == set(theme.DARK)


def test_palettes_have_every_key_the_app_uses():
    for pal in (theme.LIGHT, theme.DARK):
        assert _USED <= set(pal)


def test_colours_are_hex_and_modes_flagged():
    for pal in (theme.LIGHT, theme.DARK):
        for key, val in pal.items():
            if key == "dark":
                continue
            assert _HEX.match(val), f"{key}={val!r} is not #rrggbb"
    assert theme.LIGHT["dark"] is False and theme.DARK["dark"] is True
    assert theme.LIGHT["text"] != theme.DARK["text"]     # the two schemes actually differ


def test_pick_palette_explicit():
    assert theme.pick_palette("light") is theme.LIGHT
    assert theme.pick_palette("dark") is theme.DARK


def test_pick_palette_auto_returns_a_known_palette():
    assert theme.pick_palette("auto") in (theme.LIGHT, theme.DARK)
    assert theme.pick_palette() in (theme.LIGHT, theme.DARK)       # default mode is auto


def test_detect_os_dark_is_a_safe_bool():
    assert isinstance(theme.detect_os_dark(), bool)              # never raises, always a bool
