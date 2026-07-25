"""A modern visual theme for the editor (palette + ttk styling).

The palette dicts, the OS dark-mode probe, and the palette picker are **tk-FREE** so they're
unit-testable on a headless machine (exactly like :mod:`.forms` / :mod:`.model`). The actual Tk/ttk
styling lives in :func:`apply_theme`, which imports tkinter lazily and only does anything useful with
a real display.

Why ``clam``: on Windows the default ttk theme (``vista``) draws widgets natively and ignores most
colour options, so a cohesive restyle is impossible. ``clam`` honours every colour we set, so we
build the modern look on top of it (flat widgets, an accent on the primary actions, a styled tree and
console log). ``apply_theme`` returns the chosen palette so the app can colour its own labels (muted
hints, the "placed in Blender" note, log lines) from the same source.
"""

from __future__ import annotations

# --- palettes ----------------------------------------------------------------------------
# Two cohesive schemes. Keep the KEY SET identical (a test asserts it) so the app can read any colour
# from whichever palette is active. Colours are plain "#rrggbb" strings.
LIGHT = {
    "dark": False,
    # A SOFT light scheme (toned down from the old pure-white look, which read as too bright): a calm
    # grey page with off-white surfaces, not glaring #ffffff panels.
    "bg": "#e8eaed",            # window background (soft grey, not white)
    "surface": "#f4f5f7",       # tree / form surface (off-white, not pure white)
    "surface_btn": "#f4f5f7",   # neutral button face
    "field": "#fbfcfd",         # entry / listbox background (just-off-white, so inputs still read as 'open')
    "text": "#1b1f24",          # primary text
    "muted": "#626974",         # secondary text (hints) -- retuned to WCAG AA 4.5:1 on bg + surface
    "accent": "#2f6feb",        # primary buttons, tree selection
    "accent_fg": "#ffffff",     # text on accent
    "accent_hover": "#2c68dd",
    "accent_pressed": "#275dc5",
    "help": "#7c3aed",          # help / info affordance (violet -- distinct from accent/success/warn)
    "help_hover": "#6d28d9",
    "border": "#d2d6dc",
    "success": "#1a8f5a",       # "placed in Blender" / OK lines
    "hover": "#dfe2e7",         # neutral button hover
    "pressed": "#d4d8de",
    "scroll": "#bcc1c9",        # scrollbar thumb
    # RAISED from #e1e3e7 -- this palette's own `field` hex, already in this dict two lines up and
    # described there as "just-off-white". The old well was a grey smudge sunk UNDER the page, and it left
    # no headroom for the log's registers: the console is a document, not a hole full of dust. It rises to
    # `field` rather than #ffffff because #ffffff IS this palette's surface_3 -- a well may not collide
    # with the top of the elevation ramp. Every register clears AA on it (worst 5.29, the trace tint).
    "log_bg": "#fbfcfd",
    "log_fg": "#374151",
    "error": "#c0392b",
    "warn": "#9a6b00",
}
DARK = {
    "dark": True,
    "bg": "#1e2127",
    "surface": "#262a31",
    "surface_btn": "#2b3038",
    "field": "#2b3038",
    "text": "#e6e8eb",
    "muted": "#a4acb5",         # lifted to AA 4.5 on surface_3 too -- the rail segment (4.13 -> 4.60)
    "accent": "#4c8dff",
    # Dark ink, not white. A 13px button label is NORMAL text (AA 4.5); white on this accent measures only
    # 3.20 -- the suite fenced accent_fg/accent at 3.0, the LARGE-text floor, which is the wrong bar for a
    # button label. The accent's own luminance (0.278) is well past the 0.220 crossover where dark ink beats
    # white, so the hue is untouched and only the ink flips: 3.20 -> 5.39. Same strategy dracula/gruvbox/
    # mist already use. #181b20 is this palette's OWN log_bg -- in-family, not an imported black.
    "accent_fg": "#181b20",
    "accent_hover": "#5593ff",
    "accent_pressed": "#4580e8",
    "help": "#9d7bff",          # help / info affordance (violet -- distinct from accent/success/warn)
    "help_hover": "#8b66f5",
    "border": "#3a404a",
    "success": "#46c98a",
    "hover": "#30353d",
    "pressed": "#373d46",
    "scroll": "#3f4651",
    "log_bg": "#181b20",
    "log_fg": "#c7ccd3",
    "error": "#ff6b6b",
    "warn": "#e0a93b",
}

# --- popular community palettes ------------------------------------------------------------
# Same KEY SET as LIGHT/DARK (a test asserts it across every theme), so the app reads any colour from
# whichever is active. Each is the well-known scheme's canonical hues, with `muted` lifted a touch where
# the original "comment" grey was too low-contrast for hint text, and `accent_fg` chosen for legible text
# ON the accent (dark text under light accents like Dracula purple / Gruvbox orange).
NORD = {                        # https://www.nordtheme.com  (Polar Night + Frost + Aurora)
    "dark": True,
    "bg": "#2e3440",            # nord0
    "surface": "#323a48",
    "surface_btn": "#3b4252",   # nord1
    "field": "#3b4252",
    "text": "#eceff4",          # nord6 (snow storm)
    "muted": "#b9c0cc",         # AA 4.5 on bg/surface/surface_2 AND surface_3 (the rail): 3.94 -> 4.57
    # nord10 #5e81ac, deepened 8%. Its luminance (0.211) falls in the DEAD BAND 0.183..0.220, where NEITHER
    # white ink (4.03) nor dark ink from nord's own ramp (nord0 = 3.10) clears 4.5 -- dark ink would need
    # #121419, far below Polar Night. So the accent moves instead, the minimum that works, and nord keeps
    # its white-on-frost convention. Visually still nord10; measured 4.03 -> 4.64.
    "accent": "#56779e",        # nord10, deepened to carry a button label
    "accent_fg": "#ffffff",     # white over the frost blue
    "accent_hover": "#537399",
    "accent_pressed": "#4a6688",
    "help": "#bc99b5",          # nord15, lifted to AA 4.5 as TEXT (4.04) -- it labels the Info Hub button
    "help_hover": "#c29bbb",
    "border": "#434c5e",        # nord2
    "success": "#a3be8c",       # nord14 (green)
    "hover": "#434c5e",         # nord2 -- was #3b4252 == surface_btn (nord1): NO hover feedback at all
    "pressed": "#4c566a",       # nord3. The Polar Night ramp: nord1 rest -> nord2 hover -> nord3 press
    "scroll": "#4c566a",        # nord3
    "log_bg": "#272c36",
    "log_fg": "#d8dee9",        # nord4
    "error": "#c36c74",         # nord11 red, nudged lighter to clear 3:1 (WCAG 1.4.11) on the elevated surface
    "warn": "#ebcb8b",          # nord13 (yellow)
}
DRACULA = {                     # https://draculatheme.com
    "dark": True,
    "bg": "#282a36",
    "surface": "#2d2f3b",
    "surface_btn": "#3a3d4d",
    "field": "#21222c",
    "text": "#f8f8f2",
    "muted": "#acb1cd",         # comment #6272a4, lifted to AA 4.5 on EVERY ground incl. surface_3 (3.86)
    "accent": "#bd93f9",        # purple
    "accent_fg": "#282a36",
    "accent_hover": "#c9a6fa",
    "accent_pressed": "#ac86e3",
    "help": "#ff79c6",          # pink
    "help_hover": "#ff92d0",
    "border": "#44475a",        # current line
    "success": "#50fa7b",       # green
    "hover": "#44475a",         # current line -- was #3a3d4d == surface_btn: NO hover feedback
    "pressed": "#4f5268",       # a rung above current-line (dracula ships no neutral above it)
    "scroll": "#44475a",
    "log_bg": "#21222c",
    "log_fg": "#f8f8f2",
    "error": "#ff5555",         # red
    "warn": "#f1fa8c",          # yellow
}
SOLARIZED_DARK = {              # https://ethanschoonover.com/solarized
    "dark": True,
    "bg": "#002b36",            # base03
    "surface": "#073642",       # base02
    "surface_btn": "#0b4350",
    "field": "#073642",
    # base1 #93a1a1 measured only 4.22:1 on surface_2 -- the ONLY palette whose BODY text was sub-AA on an
    # elevated panel. Lifted past its own 4.5 minimum on purpose: muted must clear 4.5 too AND stay dimmer
    # than text, and at text's bare minimum there is no headroom for both (the solver ran muted to #ffffff).
    "text": "#bec6c6",          # base1 +30%. Lifted TWICE, and the second lift is FORCED by muted:
                                # muted must clear 4.5 on surface_3 (the rail) too, which puts it at
                                # #a0b8b8 -- brighter than base1 itself, inverting the two text tiers.
                                # There is no headroom at base1, so text moves up and muted sits under it.
    "muted": "#a0b8b8",         # AA 4.5 on EVERY ground incl. surface_3; stays 1.23x dimmer than text
    "accent": "#268bd2",        # blue -- CANONICAL solarized, untouched
    # base03-deep ink (this palette's own log_bg), not white: white on solarized blue is 3.68, sub-AA for a
    # button label. accent lum 0.235 clears the 0.220 crossover, so the ink flips and the blue stays exact.
    "accent_fg": "#00212b",     # 3.68 -> 4.56
    "accent_hover": "#4b9fda",
    "accent_pressed": "#3191d4",
    "help": "#9296d3",          # violet, lifted to AA 4.5 as TEXT (2.97 -> 4.57). `help` has exactly ONE
                                # use -- the Info Hub button's label AND its border -- so there is no
                                # shape-role to protect and the lift happens in place.
    "help_hover": "#7e83cf",
    "border": "#0e4a59",
    "success": "#859900",       # green
    "hover": "#0e4a59",         # was #0b4350 == surface_btn: NO hover feedback (this hex was `pressed`)
    "pressed": "#135a6b",       # lifted so pressed still adds feedback above the new hover
    "scroll": "#586e75",        # base01
    "log_bg": "#00212b",
    "log_fg": "#839496",        # base0
    "error": "#df4340",         # red, nudged lighter to clear 3:1 (WCAG 1.4.11) on the elevated surface
    "warn": "#b58900",          # yellow
}
SOLARIZED_LIGHT = {
    "dark": False,
    # Uses base2 (#eee8d5) as the page rather than the brighter base3 (#fdf6e3) -- the dimmer canonical
    # Solarized-Light option, so it isn't glaring (the "too bright" feedback).
    "bg": "#eee8d5",            # base2
    "surface": "#f4eeda",
    "surface_btn": "#e8e1cd",
    "field": "#f7f1de",
    "text": "#4a6067",          # base01 deepened to WCAG AA 4.5:1 body text on the cream bg
    # Deepened AGAIN (#546a72 -> #4f646b): the old value said "AA 4.5 on EVERY ground" and was 4.37 on
    # surface_btn -- a ground the fence had never checked, and the one an UNSELECTED TAB LABEL lands on.
    # So the app shipped sub-AA text on the tab strip in this palette. Same shape as the hero's overline:
    # a fence that covers most grounds just moves the bug to the one it missed.
    # The window here is one step wide: at t=0.10 muted goes DARKER than text (#4a6067) and the hierarchy
    # inverts. #4f646b clears all six grounds (surface_btn 4.78) and stays lighter than text.
    "muted": "#4f646b",
    # Solarized blue #268bd2 deepened 12%: at lum 0.235 white ink gives only 3.68, and this is a LIGHT
    # theme -- every one of its own neutrals is far too light to serve as dark ink, so the flip that fixes
    # solarized-DARK is unavailable here. The blue deepens instead; 3.68 -> 4.62.
    "accent": "#217ab9",        # solarized blue, deepened to carry a button label
    "accent_fg": "#ffffff",     # white over the blue accent
    "accent_hover": "#2076b3",
    "accent_pressed": "#1d6aa1",
    "help": "#5d61a9",          # violet, deepened to AA 4.5 as TEXT on the cream page (3.57 -> 4.57)
    "help_hover": "#595fb8",
    "border": "#ddd6bf",
    "success": "#728a00",       # deepened green for light-bg legibility
    "hover": "#ded7c0",         # was #e6dfc9 -- present but ~invisible (btn->hover measured 1.0203)
    "pressed": "#d3cbb0",       # deepened so pressed still reads above the new hover
    "scroll": "#c9c2aa",
    # base3, RAISED from #e4ddc8: the console's own body text measured 3.97 on the old well -- sub-AA, on
    # the surface you stare at during every build, and never fenced because log_bg was not a ground any
    # text test knew about. It survives BECAUSE it rises: dropping the well to bg (#eee8d5) scores 4.39
    # and still fails. #ffffff is unavailable -- it IS this palette's surface_3, and a well may not
    # collide with the top of the elevation ramp. base3 clears at 4.99.
    "log_bg": "#fdf6e3",
    "log_fg": "#586e75",
    "error": "#dc322f",         # red
    "warn": "#a47c00",          # yellow, deepened to clear 3:1 (WCAG 1.4.11) on the cream page + surface
}
GRUVBOX_DARK = {                # https://github.com/morhetz/gruvbox
    "dark": True,
    "bg": "#282828",            # bg0
    "surface": "#32302f",       # bg0_s
    "surface_btn": "#3c3836",   # bg1
    "field": "#3c3836",
    "text": "#ebdbb2",          # fg1
    "muted": "#bdb2a2",         # gray, lifted to AA 4.5 on surface_2 AND surface_3 (the rail): 3.88 -> 4.66
    "accent": "#fe8019",        # bright orange
    "accent_fg": "#282828",
    "accent_hover": "#fe8e32",
    "accent_pressed": "#e57316",
    "help": "#d3869b",          # bright purple -- already AA 4.5 as text (4.78)
    "help_hover": "#dd9aab",
    "border": "#504945",        # bg2
    "success": "#b8bb26",       # bright green
    "hover": "#504945",         # bg2 -- was #3c3836 == surface_btn (bg1): NO hover feedback at all
    "pressed": "#665c54",       # bg3. The gruvbox ramp is built for this: bg1 rest -> bg2 hover -> bg3 press
    "scroll": "#665c54",        # bg3
    "log_bg": "#1d2021",        # bg0_h
    "log_fg": "#d5c4a1",        # fg2
    "error": "#fb4934",         # bright red
    "warn": "#fabd2f",          # bright yellow
}

# All selectable palettes (keyed by mode string). "auto" is a meta-mode (follow the OS) -- not in here.
# --- the FF9 climate (SIGNET, studies/gui-aesthetics/IDENTITY.md) ---------------------------
# The one palette permitted to be Final Fantasy IX. It is now the app's DEFAULT (prefs.theme() ships
# "mist") -- "auto"/Dark/Light and every neutral palette above are still one picker click away and remain
# byte-identical to before this landed; only the fresh-install SEED moved.
#
# WHY THERE IS NO GOLD IN HERE. The obvious FF9 palette is its menu: navy page, gold trim. It is
# buildable and it is wrong, on three measured grounds:
#   1. `warn` IS the accent. Gold #d9b45c is 5.9 deg from this tree's amber warn #e0a93b in hue and
#      near-identical in greyscale -- and derive() aliases info = accent, so gold would mean
#      "information" and "caution" simultaneously.
#   2. `selection_bg` = _mix(surface, accent, 0.16) is derived CENTRALLY, and navy sits 177.8 deg from
#      gold -- a near-complement. The mix CANCELS: measured #35393f, a desaturated mud, on the selected
#      tree row, which is the most-looked-at surface in a file-tree IDE. Blue + yellow = grey, in sRGB,
#      by construction. Mist cyan is 32.6 deg from the surface and keeps its chroma.
#   3. Gold-as-accent paints every checkbox, radio and focus ring in the app -- the costume permanently on.
# So the gold moved to the ONE place it earns: a single rule on the Home hero (workspace/hero.py), as a
# module constant identical in ALL palettes. The palette is the app's climate; the gold is its signature;
# a signature does not change colour when the weather does.
#
# AUTHORING LAW (a comment, deliberately NOT a test): keep every semantic hue >= 25 deg from every other.
# This palette's worst pair is accent(196.4) vs success(146.3) = 58.1 deg -- the widest in the tree. It is
# not asserted because MIST's own margin is the THINNEST here (1.48x vs gruvbox's 5.40x), and a fence whose
# tightest subject is the palette you are shipping is a trap, not a fence.
MIST = {                        # "Mist (FF9)" -- the Mist is the game's atmosphere; the world runs on it.
    "dark": True,
    "bg": "#0f1826",            # the Mist-blue night page
    "surface": "#16223a",
    "surface_btn": "#1e2d4a",
    "field": "#0c1420",         # input wells sit BELOW the page
    "text": "#e9e6dc",          # warm parchment white -- not #ffffff
    "muted": "#9fadc4",
    "accent": "#5fc9d8",        # THE MIST. derive() aliases info=accent and grows focus FROM it, so this
                                # hue is spent three times -- which is exactly why the gold is not here.
    "accent_fg": "#08171b",     # dark ink on a light accent (the dracula/gruvbox strategy); 9.43:1
    "accent_hover": "#7ad2df",
    "accent_pressed": "#51abb8",
    "help": "#9d8bd8",          # violet -- far from every other semantic hue
    "help_hover": "#b3a4e4",
    "border": "#2b3d5e",        # stays NEUTRAL. Gold here would be the costume, on all 27 cards, forever.
    "success": "#63cf7a",
    "hover": "#26385a",         # lighter than surface_btn (the dark-palette direction)
    "pressed": "#2f4468",
    "scroll": "#33456a",
    "log_bg": "#0b111c",
    "log_fg": "#cfd8e6",
    "error": "#ff6b6b",
    "warn": "#e0a93b",          # unchanged: amber sits 126.8 deg from the Mist and never collides with it
}

THEMES = {
    "light": LIGHT,
    "dark": DARK,
    "nord": NORD,
    "dracula": DRACULA,
    "solarized-dark": SOLARIZED_DARK,
    "solarized-light": SOLARIZED_LIGHT,
    "gruvbox-dark": GRUVBOX_DARK,
    "mist": MIST,
}

# (mode, display label) in picker order. "mist" leads (the default -- see prefs.theme()); the rest mirror
# THEMES, "auto" first among them since match-system is the next most likely pick.
THEME_CHOICES = [
    ("mist", "Mist (FF9) (default)"),   # ASCII ONLY -- this file has zero non-ASCII bytes and an em-dash
    ("auto", "Match system"),           # here would make the label the first non-ASCII byte. House style
    ("light", "Light"),                 # writes "--".
    ("dark", "Dark"),
    ("nord", "Nord"),
    ("dracula", "Dracula"),
    ("solarized-dark", "Solarized Dark"),
    ("solarized-light", "Solarized Light"),
    ("gruvbox-dark", "Gruvbox Dark"),
]


def detect_os_dark() -> bool:
    """True if Windows is set to dark mode (HKCU ``Personalize\\AppsUseLightTheme`` == 0).

    Pure + defensive: any failure (non-Windows, missing key, no winreg) -> ``False`` (light)."""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        try:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        finally:
            winreg.CloseKey(key)
        return value == 0
    except Exception:       # noqa: BLE001  (winreg missing / key absent / anything) -> light
        return False


def pick_palette(mode: str = "auto") -> dict:
    """Choose a palette by ``mode``: ``"auto"`` (match the OS light/dark, default), or any key in
    :data:`THEMES` (``"light"`` / ``"dark"`` / ``"nord"`` / ``"dracula"`` / ``"solarized-dark"`` /
    ``"solarized-light"`` / ``"gruvbox-dark"``). An unknown/empty mode falls back to ``"auto"`` so a stale
    saved preference never crashes the app."""
    if mode in (None, "", "auto"):
        return DARK if detect_os_dark() else LIGHT
    return THEMES.get(mode) or (DARK if detect_os_dark() else LIGHT)


# --- derived semantic tokens (Phase 1 token foundation) ------------------------------------
# A pure, idempotent function that EXTENDS a 22-key base palette with the semantic tokens the modern
# component layer consumes: an elevation ladder, a tinted selection, a third text tier, a focus token
# guaranteed to meet the WCAG 3:1 non-text floor, and an info status hue. All outputs are #rrggbb (no
# rgba) so the hex/parity guarantees still hold; QSS composites solid fills over the surface anyway, so a
# pre-blended hex is both simpler and more correct than a translucent overlay. tk-free + headless.
_DERIVED_KEYS = ("surface_2", "surface_3", "selection_bg", "selection_rail", "text_subtle", "focus",
                 "info", "success_text", "warn_text", "error_text",
                 "border_lit", "border_shade", "accent_lit", "accent_shade",
                 "warn_fg", "help_fg", "pressed_fg", "find_bg", "find_fg")

# INTAGLIO's one lever: how far each edge is mixed from $border toward white / black. THE taste call of
# the whole direction, isolated to one number on purpose -- and settled by RENDERING it at 6x, because no
# contrast ratio can tell "materially lit" from "Windows 95", and at 1x a 1px edge is invisible to review.
#
# The trade, measured across all 8:
#   t=0.18 -> carrier d33-d43, NON-carrier d8-d17. FIVE palettes (nord 17, mist 17, dracula 16,
#             solarized-dark 16, gruvbox 14) show a lit top AND a foot. Two edges on a raised rectangle
#             is a bevel, and a bevel is Win95.
#   t=0.14 -> carrier d26-d34, NON-carrier d6-d13. NO palette exceeds d13. One edge carries everywhere.
#
# 0.14, because the carrier is what does the work and it is still 3-4x stronger than the FILL differences
# it replaces (d3-d8 -- and d0 in LIGHT, where surface_btn IS surface). Giving up d7 of carrier to keep
# every non-carrier under d13 is the cheapest trade in the direction. The non-carrier ceiling is fenced
# (test_the_edge_never_becomes_a_bevel) so the taste call cannot silently decay into Win95 later.
EDGE_T = 0.14


def _mix(a: str, b: str, t: float) -> str:
    """Blend two #rrggbb colours: t=0 -> a, t=1 -> b. Returns #rrggbb."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(ca[i] + (cb[i] - ca[i]) * t):02x}" for i in range(3))


def _rel_lum(h: str) -> float:
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))

    def _lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _contrast(a: str, b: str) -> float:
    la, lb = _rel_lum(a), _rel_lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _selection_token(surface: str, accent: str, hover: str) -> str:
    """The selected row's fill: the surface tinted with the accent until it cannot be confused with HOVER.

    THE GROUND IS THE POINT. A selected row is not confused with the page -- it is confused with the row
    under your cursor, so the thing to solve against is `hover`, not `surface`. Tinting against the
    surface (a fixed 16%) left nord's selection 11/255 from its own hover, because nord's accent is
    nearly the same HUE as its surface and a 16% mix of a thing into a near-copy of itself barely moves.

    AND CONTRAST IS THE WRONG INSTRUMENT HERE, which is why this measures a raw channel distance instead.
    By contrast ratio, hover BEATS the old selection in four palettes -- yet rendered at 4x, gruvbox's
    selection wins decisively. Contrast is luminance-only and blind to the axis a tint actually uses:
    hover is a pure lightness step (dHue <=2.5deg, dSat ~0), a selection is a hue/chroma event (dSat up
    to +0.42). A ratio cannot see that; a channel distance can.

    The 20 floor is CALIBRATED against those two renders, not chosen: gruvbox reads decisively and sits
    at 26; nord reads marginally and sits at 11. Everything the metric calls fine, the eye called fine.
    Three palettes already clear it and are returned untouched (dark 21, solarized-light 21, gruvbox 26).
    """
    t, sel = 0.16, _mix(surface, accent, 0.16)
    while t < 0.60 and max(abs(a - b) for a, b in zip(
            [int(sel[i:i + 2], 16) for i in (1, 3, 5)],
            [int(hover[i:i + 2], 16) for i in (1, 3, 5)])) < 20:
        t += 0.02
        sel = _mix(surface, accent, t)
    return sel


# The quiet find tier's visibility floor -- raw channel distance from the console well. ONE number for the
# whole taste call, like EDGE_T, and CALIBRATED BY RENDER rather than inherited.
#
# `_selection_token` uses 20, AND 20 IS WRONG HERE. Its floor was calibrated against renders where the
# confusion partner is HOVER -- a fill against a mid-grey surface. This tier's partner is `log_bg`, the
# DEEPEST fill in the palette. At 20 the mist render painted the quiet match correctly (339 measured px of
# the token) and it still read as a smudge rather than a mark on a near-black ground: same delta, less
# perceived. A floor is calibrated per GROUND; it is not transferable between tokens.
#
# 44, swept at 4x nearest-neighbour on the two extremes -- mist (the default theme, deepest well) and
# solarized-light (a cream well, where the tint travels the other way). 20 reads as an artifact, 32 reads as
# a mark, 44 reads as a mark with no ambiguity, and even at 56 nothing "competes with the current match"
# because the loud tier is a SATURATED fill with inverted ink and this one is a tint. So the ceiling is not
# taste, it is the numbers: 44 keeps the derived ink at >=4.77:1 in all 8 (56 -> 4.69, its tightest) and
# keeps every palette >=60 raw channels from the accent (56 -> 48 on nord, whose accent sits nearest its own
# ground). 3x the separation floor, with ink headroom, at the first value that is unambiguous.
#
# AND THE SWEEP CORROBORATED THE INK TOKEN INDEPENDENTLY: `contrast(log_fg, find_bg)` FALLS as the floor
# rises (solarized-dark 4.52 -> 3.55, solarized-light 4.42 -> 3.86). Visibility and inherited legibility pull
# in OPPOSITE directions, so there is no floor at which the naive "let the log's own ink ride the tint" build
# is both visible and legible. The two tokens are not belt-and-braces; they are the only shape that works.
# See evidence/shot_find_tier.py (the renders) and evidence/probe_find_ground.py (the table).
FIND_TINT_FLOOR = 44


def _find_token(log_bg: str, accent: str) -> str:
    """The QUIET tier of a console find highlight: the WELL tinted with the accent until a matched line is
    visibly matched. (The CURRENT match is the full `accent` fill -- it needs no token.)

    WHY THIS IS NOT `selection_bg`. Both are "a tinted fill marking a hit", so the obvious move is to reuse
    the token. Measured, that is the study's most-repeated defect -- a fence set on the wrong GROUND.
    `selection_bg` is derived against `surface`/`hover`: the TREE's ground. A find highlight is painted in
    the console well, and `log_bg` is a different and DEEPER fill in every one of the 8 palettes (dark's
    `#181b20` vs surface `#20242c`; solarized-dark's `#00212b` vs `#073642`). A tint solved against one is
    not a tint solved against the other.

    THE METRIC IS A RAW CHANNEL DISTANCE, not a contrast ratio, for exactly REGISTER P1's reason: the thing
    a matched line is confused with is an UNMATCHED line, i.e. the well itself, and a tint moves along a
    hue/chroma axis a luminance-only ratio cannot see. Same 20/255 floor and the same walk as
    :func:`_selection_token`, whose floor was calibrated against renders.

    Every palette clears it early -- t lands 0.10-0.20 (nord highest, its accent being nearest its own
    ground, exactly as in `_selection_token`). The ceiling is the accent itself; the walk cannot pass it.
    """
    t, fill = 0.10, _mix(log_bg, accent, 0.10)
    while t < 0.60 and max(abs(a - b) for a, b in zip(
            [int(fill[i:i + 2], 16) for i in (1, 3, 5)],
            [int(log_bg[i:i + 2], 16) for i in (1, 3, 5)])) < FIND_TINT_FLOOR:
        t += 0.02
        fill = _mix(log_bg, accent, t)
    return fill


def _focus_token(accent: str, surface: str) -> str:
    """The accent, brightened toward white just enough to clear the WCAG 3:1 non-text floor on the
    surface (a focus ring must be perceivable). Most themes already pass -> the accent returns unchanged."""
    focus = accent
    for _ in range(24):
        if _contrast(focus, surface) >= 3.0:
            break
        focus = _mix(focus, "#ffffff", 0.06)
    return focus


def _text_token(hue: str, surfaces: tuple, dark: bool) -> str:
    """A status hue, moved toward the palette's ink just enough to clear WCAG AA 4.5:1 AS TEXT on EVERY
    surface it can land on. Mirrors :func:`_focus_token`; most hues in most themes pass unchanged.

    ``surfaces`` is every ground a status line sits on -- the page, a panel, a card -- and it must be all
    of them, because WHICH ONE IS TIGHTEST FLIPS WITH THE MODE. A dark theme writes LIGHT ink, so the
    lightest ground (surface_2, the card) is worst. A light theme writes DARK ink, so the DARKEST ground
    (bg) is worst. Tuning against surface_2 alone passed every dark palette and left light's success_text
    at 4.31 on a panel -- caught by the fence, which is the only reason this signature takes a tuple.

    WHY A DERIVED VARIANT INSTEAD OF FIXING THE HUE. `success`/`warn`/`error` are fenced at 3.0 -- the
    NON-TEXT floor -- because their first job is icons and stripes, where 3.0 is the correct bar. But the
    app also writes them as TEXT ("netsync MISSING", "overwrites, no undo"), and normal text needs 4.5.
    Measured on the card fill: error 2.67 on nord, 2.69 solarized-dark, 3.29 gruvbox; warn 3.51
    solarized-dark; success 3.52 solarized-dark. Sub-AA.

    Lifting the hues IN PLACE was measured and rejected: it needs +38% toward white on nord's aurora red,
    +38% on solarized-dark's, +30% on gruvbox's -- those are the palettes' signature reds and it washes
    them out. So the canonical hue KEEPS its job (shapes, 3.0) and text gets its own derived rung. The
    base palettes stay untouched and no new palette KEY is taxed -- the same trick `focus` has always used.
    """
    ink = "#ffffff" if dark else "#000000"        # a dark theme lifts toward light; a light theme deepens
    out = hue
    for _ in range(40):
        if all(_contrast(out, s) >= 4.5 for s in surfaces):
            break
        out = _mix(out, ink, 0.04)
    return out


def _fg_token(fill: str, pal: dict) -> str:
    """The ink that rides ON a saturated FILL (a chip, a round button) -- AA 4.5:1 as normal text.

    WHY THIS IS DERIVED WHILE `accent_fg` IS AUTHORED. Both answer "what ink goes on this fill", so the
    obvious move is one rule for both. Measured, that is wrong: a single argmax rule reproduces only 5 of
    the 8 hand-authored `accent_fg` values, and where it misses it picks MORE contrast than the author
    chose (dracula 6.55 vs 5.90, gruvbox 6.49 vs 5.84, mist 9.75 vs 9.43) -- because `#282a36` and
    `#282828` are those projects' signature backgrounds, not compromises. That is taste, and a formula
    must not overwrite it. `warn` and `help` are the opposite case: NOBODY EVER CHOSE, so there is no
    taste to overwrite -- only a hole that ships white-on-yellow at 1.12:1. Derive those; spend the
    authored token on `accent`. (`studies/gui-aesthetics/evidence/probe_fg_rule.py`)

    THE DIRECTION IS PER-FILL, NEVER PER MODE, and three palettes prove it: `nord` is DARK and its accent
    takes WHITE ink; `light` (#9a6b00) and `solarized-light` (#a47c00) want OPPOSITE inks on the SAME
    `warn` semantic -- light fails on black at 4.48, solarized-light fails on white at 3.85. So `target`
    is whichever extreme the fill can actually carry, chosen per fill.

    THE START MUST LIE ON THE TARGET'S SIDE. This is the whole subtlety and v1 shipped without it:
    starting at `log_bg` unconditionally and walking, as :func:`_text_token` does, ASSERTED ITSELF SUB-AA
    on solarized-light -- 3.56 in, **3.42 out**, having dipped to **1.02** on the way. Walking that
    palette's CREAM log ink toward black must cross its mid GOLD fill, so contrast collapses to invisible
    and only then climbs.

        A WALK TOWARD AN EXTREME IS MONOTONIC ONLY IF YOU START ON THAT EXTREME'S SIDE OF THE GROUND.

    `_text_token`/`_focus_token` are safe from this by accident of their inputs, not by construction --
    they pick the direction from the MODE and every ground they touch (bg/surface/surface_2) is on the
    mode's side. A saturated fill has arbitrary luminance and that guarantee evaporates.

    `log_bg` and `text` are the palette's two authored extremes and always sit opposite each other, so at
    least one lies on any achievable side. In 15 of 16 real cases the chosen one already clears AA and is
    used VERBATIM -- the walk is dead code for every palette except solarized-light's `warn`, whose fill
    (luminance 0.223, landing on the 0.220 crossover this file's `dark` accent_fg comment names) is
    carried by NONE of that palette's 35 hexes: best is #ffffff at 3.85. There the walk starts at `text`
    (#4a6067, darker than the fill, so monotonic) and lands #151b1d at 4.53 -- still in-family, never an
    imported black. Fenced by test_editor_theme::test_a_filled_ground_carries_its_ink.
    """
    target = max(("#ffffff", "#000000"), key=lambda c: _contrast(c, fill))
    up = _rel_lum(target) > _rel_lum(fill)              # the only direction that can reach AA
    side = [c for c in (pal["log_bg"], pal["text"]) if (_rel_lum(c) > _rel_lum(fill)) == up]
    out = max(side, key=lambda c: _contrast(c, fill)) if side else target
    for _ in range(40):
        if _contrast(out, fill) >= 4.5:
            break
        out = _mix(out, target, 0.04)
    return out


# THE ACCENT LADDER'S FEEDBACK FLOORS -- the app's OWN shipped minimums, measured across all 8 palettes
# BEFORE the ladder was narrowed: hover/accent 1.0560 (solarized-light), press/accent 1.0670 (nord),
# press/hover 1.1821 (light). They are here so a future edit to any accent_hover/accent_pressed can never
# be quieter than the quietest step that already shipped. Fenced by
# test_the_narrowed_accent_ladder_still_gives_feedback. The values themselves are AUTHORED in the palettes
# above -- see the accent_hover comments there for why they are what they are, and
# studies/gui-aesthetics/evidence/solve_accent_ladder.py for the search that produced them.
_ACCENT_FEEDBACK = (1.0560, 1.0670, 1.1821)


def derive(pal: dict) -> dict:
    """Return ``pal`` extended with the derived semantic tokens (idempotent -- an already-derived palette
    passes through, so a consumer can call it defensively on either a base or a derived dict)."""
    if all(k in pal for k in _DERIVED_KEYS):
        return pal
    dark = bool(pal.get("dark"))
    out = dict(pal)
    # Elevation ladder -- a raised surface catches more light in BOTH modes (lighter = higher). QSS has no
    # box-shadow, so depth is tint-on-tint (Material-3 style); Phase 3 adds real shadows to floating layers.
    out["surface_2"] = _mix(pal["surface"], "#ffffff", 0.05 if dark else 0.55)
    out["surface_3"] = _mix(pal["surface"], "#ffffff", 0.10 if dark else 1.00)
    # Tinted, and it finally RENDERS -- this token has existed since Phase 1 with zero rules. Solved
    # against HOVER rather than the surface, because those are the two states that get confused.
    out["selection_bg"] = _selection_token(pal["surface"], pal["accent"], pal["hover"])
    # The selected row's RAIL. _focus_token pointed at the ground the rail actually sits on -- the tinted
    # selection fill, not the plain surface -- because a 3:1 mark must clear the thing it is drawn ON.
    # Zero new math: nord lands 3.19 and solarized-dark 3.13 (both under 3.0 as the raw accent), and the
    # other six already clear and return the accent unchanged.
    out["selection_rail"] = _focus_token(pal["accent"], out["selection_bg"])
    out["text_subtle"] = _mix(pal["muted"], pal["bg"], 0.28)          # a third, dimmer text tier
    out["focus"] = _focus_token(pal["accent"], pal["surface"])        # meets WCAG 3:1 on the surface
    out["info"] = pal["accent"]                                       # info status hue (aliases accent for now)
    # The status hues AS TEXT. The canonical hue keeps its own job (icons + the banner stripe, where the
    # 3.0 non-text floor is right); these clear 4.5 as normal text on the CARD FILL, which is the tightest
    # surface any status line lands on -- so they are safe on bg and surface too. See _text_token for why
    # this is a derived rung and not a fix to the hue itself.
    _grounds = (pal["bg"], pal["surface"], out["surface_2"])   # every ground a status line lands on
    for _k in ("success", "warn", "error"):
        out[f"{_k}_text"] = _text_token(pal[_k], _grounds, dark)
    # The ink ON a saturated FILL -- the mirror of the *_text rung above. `*_text` is a hue moved until it
    # reads AS text ON a surface; `*_fg` is the ink that reads ON the hue when the hue is the ground.
    #
    # ONLY THE TWO FILLS THAT ACTUALLY CARRY TEXT. Censused by reading every `background:{...}` in an
    # inline setStyleSheet across `workspace/`: the breadcrumb chip (`$accent`, or `$warn` for BATTLE) and
    # the round help button (`$help`). `$success`/`$error` are NEVER fills -- they are borders and text
    # only -- so they get no `_fg` here. This file already carries the cost of the other habit: `info` was
    # derived "for now", has ZERO consumers to this day, and a design argument in MIST's own comment rests
    # on it. A token with no call site is not future-proofing, it is a wish with a keyword.
    #
    # `accent_fg` is DELIBERATELY ABSENT -- it is hand-authored per palette and _fg_token would overwrite
    # 3 of the 8 with more contrast than their authors wanted. See :func:`_fg_token`.
    for _k in ("warn", "help"):
        out[f"{_k}_fg"] = _fg_token(pal[_k], pal)
    # `pressed` IS A FILL TOO, and it is the one nobody noticed because it is TRANSIENT. Every button in
    # the app renders its label on it while held: measured, `text` on `pressed` is 4.09 in solarized-light
    # and 4.47 in solarized-dark -- sub-AA, in the generic rule, for every button in those two palettes.
    #
    # THE GROUND CANNOT MOVE, AND THAT IS WHY THIS IS AN INK. `pressed` is a rung of a TONAL LADDER
    # (surface_btn -> hover -> pressed) fenced at contrast(pressed, hover) >= 1.03. In BOTH failing
    # palettes the ladder's direction is the OPPOSITE of legibility's: solarized-light's press walks DARKER
    # (toward its dark text) and solarized-dark's walks LIGHTER (toward its light text). Retuning the fill
    # to clear 4.5 costs solarized-light 5 steps and lands contrast(pressed, hover) at 1.0192 -- UNDER the
    # fence. You would fix the label by making the press invisible.
    #
    # So the fill keeps its job and the ink gets its own rung -- the same trade `_text_token` documents
    # above ("the canonical hue KEEPS its job and text gets its own derived rung"), and `focus` before it.
    # NEARLY FREE: `_fg_token` returns `text` UNCHANGED in 6 of 8, so six palettes RENDER IDENTICALLY and
    # only the two that were broken move (solarized-dark 4.47 -> 4.57, solarized-light 4.09 -> 4.61).
    # RENDER-identical, not byte-identical: the generic :pressed rule had no `color` at all (the label
    # inherited `text` from the QWidget base), so naming the token changes the SHEET in all 8 while
    # changing the PIXELS in two. Worth the distinction -- "byte-identical" is a claim a fence can check,
    # and it would fail.
    out["pressed_fg"] = _fg_token(pal["pressed"], pal)
    # INTAGLIO -- one light, from above. The app's whole elevation ladder claims a light source ("higher =
    # lighter") and never draws the light, so an object's fill cannot say it is an object: LIGHT's
    # surface_btn IS surface (contrast 1.0000, the same hex); solarized-dark's field IS surface; mist's
    # button-in-a-card is 1.0017; nord/gruvbox 1.024/1.025. In 6 of 8 palettes the only thing saying "this
    # is a button" is a 1px border. These four tokens give every object a lit top and a shaded foot.
    #
    # ANCHORED ON $border, NOT ON THE FILL, and that is the whole trick. Fill-anchored, LIGHT gets d5 on a
    # card -- a no-op in the two palettes that need it most, because light's surface_3 is #ffffff and its
    # rungs step 1.043/1.046. Border-anchored the carrier delta is d33-d43 in EVERY palette, no exceptions.
    #
    # And it needs no `if dark:`, because $border is this app's one already-mode-aware token: measured, it
    # sits ABOVE its fill in all 6 dark palettes and BELOW it in both light ones, 8/8 without exception. So
    # every rule emits BOTH edges and each palette's own border eats the one it cannot hold -- in LIGHT the
    # lit edge lands at d8 (invisible) and the FOOT carries at d40; in dark the lit top carries at d33-d43.
    # Fenced by test_editor_theme.py::test_the_edge_tokens_carry_in_every_palette.
    for _k, _src in (("border", pal["border"]), ("accent", pal["accent"])):
        out[f"{_k}_lit"] = _mix(_src, "#ffffff", EDGE_T)
        out[f"{_k}_shade"] = _mix(_src, "#000000", EDGE_T)
    # The console FIND highlight's quiet tier -- and its ink, which is the whole reason it is two tokens.
    #
    # THE NINTH-GROUND LAW, on the one surface that had no ground but its own. `log_bg`/`log_fg` are an
    # authored PAIR, fenced at 4.5 by test_palette_contrast_invariants; a highlight paints a THIRD colour
    # under that same text and voids the fence silently. Measured (evidence/probe_find_ground.py), the naive
    # build -- paint the fill, let the log's own ink ride it -- is sub-AA in EVERY palette on the loud tier
    # (`log_fg` on `accent`: 1.16 solarized-dark, 1.17 solarized-light, 1.35 mist, ... 3.43 nord at best) and
    # sub-AA on the QUIET tier in solarized-light (4.42) with solarized-dark a rounding error clear (4.52).
    # So the current match reuses the AUTHORED `accent`/`accent_fg` pair (already fenced by
    # test_a_filled_ground_carries_its_ink) and the quiet tier gets these two: the fill from `_find_token`
    # and its ink from the same `_fg_token` rule every other fill in the app uses. 5.45-14.21, all 8.
    out["find_bg"] = _find_token(pal["log_bg"], pal["accent"])
    out["find_fg"] = _fg_token(out["find_bg"], pal)
    return out


# Motion tokens (Phase 1 constants; QSS cannot animate, so these feed QPropertyAnimation in Phase 10).


def apply_theme(root, mode: str = "auto") -> dict:
    """Style ``root`` (a Tk window) with the modern look and return the active palette.

    Builds on the ``clam`` ttk theme; reconfigures the named fonts to Segoe UI so classic and ttk
    widgets share typography. Safe to call once at startup before building widgets."""
    import tkinter as tk          # noqa: F401  (lazy: keep this module headless-importable)
    import tkinter.font as tkfont
    from tkinter import ttk

    pal = pick_palette(mode)

    # Typography: reconfigure the shared named fonts so EVERY widget (ttk + classic Text/Listbox) and
    # every ``font=("", 11, "bold")`` (family "" == TkDefaultFont) picks up Segoe UI.
    for name, size in (("TkDefaultFont", 10), ("TkTextFont", 10), ("TkMenuFont", 10),
                       ("TkHeadingFont", 10)):
        try:
            tkfont.nametofont(name).configure(family="Segoe UI", size=size)
        except Exception:       # noqa: BLE001  (a font name not present on this Tk)
            pass

    root.configure(background=pal["bg"])
    # Combobox dropdowns are classic Listboxes -> colour them via the option DB.
    root.option_add("*TCombobox*Listbox.background", pal["field"])
    root.option_add("*TCombobox*Listbox.foreground", pal["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", pal["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", pal["accent_fg"])
    # Plain classic Listboxes (the catalog picker) aren't ttk -> theme them via the option DB too, so a
    # widget that doesn't pass explicit colours (unlike the editor's own lists) still matches the app.
    root.option_add("*Listbox.background", pal["field"])
    root.option_add("*Listbox.foreground", pal["text"])
    root.option_add("*Listbox.selectBackground", pal["accent"])
    root.option_add("*Listbox.selectForeground", pal["accent_fg"])
    root.option_add("*Listbox.highlightColor", pal["accent"])
    root.option_add("*Listbox.highlightBackground", pal["border"])

    st = ttk.Style(root)
    try:
        st.theme_use("clam")    # the only built-in theme that honours our colours
    except tk.TclError:
        pass

    st.configure(".", background=pal["bg"], foreground=pal["text"],
                 fieldbackground=pal["field"], bordercolor=pal["border"],
                 lightcolor=pal["border"], darkcolor=pal["border"], focuscolor=pal["accent"])
    st.configure("TFrame", background=pal["bg"])
    st.configure("TLabel", background=pal["bg"], foreground=pal["text"])
    st.configure("TSeparator", background=pal["border"])
    st.configure("TPanedwindow", background=pal["bg"])

    # Buttons: flat + padded; neutral face with a hover, plus an Accent.TButton for primary actions.
    st.configure("TButton", background=pal["surface_btn"], foreground=pal["text"],
                 bordercolor=pal["border"], lightcolor=pal["surface_btn"],
                 darkcolor=pal["surface_btn"], relief="flat", padding=(12, 6))
    st.map("TButton",
           background=[("pressed", pal["pressed"]), ("active", pal["hover"]),
                       ("disabled", pal["bg"])],
           foreground=[("disabled", pal["muted"])],
           bordercolor=[("focus", pal["accent"]), ("active", pal["border"])])
    st.configure("Accent.TButton", background=pal["accent"], foreground=pal["accent_fg"],
                 bordercolor=pal["accent"], lightcolor=pal["accent"], darkcolor=pal["accent"],
                 relief="flat", padding=(12, 6))
    st.map("Accent.TButton",
           background=[("pressed", pal["accent_pressed"]), ("active", pal["accent_hover"]),
                       ("disabled", pal["border"])],
           foreground=[("disabled", pal["muted"])])

    # Entries + comboboxes: flat field, accent focus ring.
    for s in ("TEntry", "TCombobox"):
        st.configure(s, fieldbackground=pal["field"], foreground=pal["text"],
                     bordercolor=pal["border"], lightcolor=pal["border"],
                     darkcolor=pal["border"], insertcolor=pal["text"],
                     arrowcolor=pal["muted"], padding=4, relief="flat")
        st.map(s, bordercolor=[("focus", pal["accent"])],
               lightcolor=[("focus", pal["accent"])], darkcolor=[("focus", pal["accent"])])
    st.configure("TCombobox", background=pal["surface_btn"])     # the arrow-button area
    st.map("TCombobox",
           fieldbackground=[("readonly", pal["field"])],
           foreground=[("readonly", pal["text"])],
           selectbackground=[("readonly", pal["field"])],
           selectforeground=[("readonly", pal["text"])],
           arrowcolor=[("active", pal["text"])])

    # Checkbutton: a filled accent box with a light check when on.
    st.configure("TCheckbutton", background=pal["bg"], foreground=pal["text"],
                 indicatorbackground=pal["field"], indicatorforeground=pal["accent_fg"],
                 focuscolor=pal["bg"])
    st.map("TCheckbutton",
           indicatorbackground=[("selected", pal["accent"]), ("active", pal["hover"])],
           indicatorforeground=[("selected", pal["accent_fg"])])

    # Treeview: roomy flat rows, accent selection.
    st.configure("Treeview", background=pal["surface"], fieldbackground=pal["surface"],
                 foreground=pal["text"], rowheight=26, borderwidth=0, relief="flat")
    st.map("Treeview", background=[("selected", pal["accent"])],
           foreground=[("selected", pal["accent_fg"])])
    st.configure("Treeview.Heading", background=pal["surface_btn"], foreground=pal["text"],
                 relief="flat")

    # Scrollbars: subtle.
    for s in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        st.configure(s, background=pal["scroll"], troughcolor=pal["bg"],
                     bordercolor=pal["bg"], arrowcolor=pal["muted"], relief="flat")
        st.map(s, background=[("active", pal["muted"])])

    # Notebook (the Campaign Editor's tab strip): flat themed tabs, the active one on the page bg.
    st.configure("TNotebook", background=pal["bg"], bordercolor=pal["border"])
    st.configure("TNotebook.Tab", background=pal["surface_btn"], foreground=pal["muted"],
                 bordercolor=pal["border"], lightcolor=pal["surface_btn"], padding=(14, 7))
    st.map("TNotebook.Tab",
           background=[("selected", pal["bg"]), ("active", pal["hover"])],
           foreground=[("selected", pal["text"]), ("active", pal["text"])])

    return pal
