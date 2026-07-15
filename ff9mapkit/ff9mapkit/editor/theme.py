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
    "accent_hover": "#256ae0",
    "accent_pressed": "#1f5fcc",
    "help": "#7c3aed",          # help / info affordance (violet -- distinct from accent/success/warn)
    "help_hover": "#6d28d9",
    "border": "#d2d6dc",
    "success": "#1a8f5a",       # "placed in Blender" / OK lines
    "hover": "#dfe2e7",         # neutral button hover
    "pressed": "#d4d8de",
    "scroll": "#bcc1c9",        # scrollbar thumb
    "log_bg": "#e1e3e7",
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
    "muted": "#9aa3ad",
    "accent": "#4c8dff",
    # Dark ink, not white. A 13px button label is NORMAL text (AA 4.5); white on this accent measures only
    # 3.20 -- the suite fenced accent_fg/accent at 3.0, the LARGE-text floor, which is the wrong bar for a
    # button label. The accent's own luminance (0.278) is well past the 0.220 crossover where dark ink beats
    # white, so the hue is untouched and only the ink flips: 3.20 -> 5.39. Same strategy dracula/gruvbox/
    # mist already use. #181b20 is this palette's OWN log_bg -- in-family, not an imported black.
    "accent_fg": "#181b20",
    "accent_hover": "#3d7df0",
    "accent_pressed": "#356fda",
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
    "muted": "#aab2c1",         # lifted to WCAG AA 4.5:1 on bg/surface AND surface_2 (3.87 -> 4.61)
    # nord10 #5e81ac, deepened 8%. Its luminance (0.211) falls in the DEAD BAND 0.183..0.220, where NEITHER
    # white ink (4.03) nor dark ink from nord's own ramp (nord0 = 3.10) clears 4.5 -- dark ink would need
    # #121419, far below Polar Night. So the accent moves instead, the minimum that works, and nord keeps
    # its white-on-frost convention. Visually still nord10; measured 4.03 -> 4.64.
    "accent": "#56779e",        # nord10, deepened to carry a button label
    "accent_fg": "#ffffff",     # white over the frost blue
    "accent_hover": "#6a8cb6",
    "accent_pressed": "#547299",
    "help": "#b48ead",          # nord15 (aurora, purple)
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
    "muted": "#9ca2c4",         # comment #6272a4, lifted to AA 4.5:1 on bg/surface AND surface_2 (3.91 -> 4.56)
    "accent": "#bd93f9",        # purple
    "accent_fg": "#282a36",
    "accent_hover": "#caa6fb",
    "accent_pressed": "#a87ee8",
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
    "text": "#a2aeae",          # base1, lifted to AA 4.5:1 on surface_2 (4.22 -> 4.94)
    "muted": "#8eaaaa",         # lifted to AA 4.5:1 on base03/base02 AND surface_2 (3.91 -> 4.55)
    "accent": "#268bd2",        # blue -- CANONICAL solarized, untouched
    # base03-deep ink (this palette's own log_bg), not white: white on solarized blue is 3.68, sub-AA for a
    # button label. accent lum 0.235 clears the 0.220 crossover, so the ink flips and the blue stays exact.
    "accent_fg": "#00212b",     # 3.68 -> 4.56
    "accent_hover": "#3597db",
    "accent_pressed": "#1f78ba",
    "help": "#6c71c4",          # violet
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
    "muted": "#566c74",         # deepened for hint legibility -- AA 4.5:1, still lighter than text
    # Solarized blue #268bd2 deepened 12%: at lum 0.235 white ink gives only 3.68, and this is a LIGHT
    # theme -- every one of its own neutrals is far too light to serve as dark ink, so the flip that fixes
    # solarized-DARK is unavailable here. The blue deepens instead; 3.68 -> 4.62.
    "accent": "#217ab9",        # solarized blue, deepened to carry a button label
    "accent_fg": "#ffffff",     # white over the blue accent
    "accent_hover": "#1f7ec0",
    "accent_pressed": "#1a6ca8",
    "help": "#6c71c4",          # violet
    "help_hover": "#595fb8",
    "border": "#ddd6bf",
    "success": "#728a00",       # deepened green for light-bg legibility
    "hover": "#ded7c0",         # was #e6dfc9 -- present but ~invisible (btn->hover measured 1.0203)
    "pressed": "#d3cbb0",       # deepened so pressed still reads above the new hover
    "scroll": "#c9c2aa",
    "log_bg": "#e4ddc8",
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
    "muted": "#b1a390",         # gray, lifted to AA 4.5:1 on surface_2 (4.07 -> 4.58)
    "accent": "#fe8019",        # bright orange
    "accent_fg": "#282828",
    "accent_hover": "#ff8f33",
    "accent_pressed": "#e36f12",
    "help": "#d3869b",          # bright purple
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
# The one palette permitted to be Final Fantasy IX. OPT-IN, never the default: `auto` still resolves
# Dark/Light, and every neutral palette above is byte-identical to before this landed.
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
    "accent_hover": "#7ad7e4",
    "accent_pressed": "#46b0c0",
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

# (mode, display label) in picker order. "auto" leads (the default); the rest mirror THEMES.
THEME_CHOICES = [
    ("auto", "Match system"),
    ("light", "Light"),
    ("dark", "Dark"),
    ("nord", "Nord"),
    ("dracula", "Dracula"),
    ("solarized-dark", "Solarized Dark"),
    ("solarized-light", "Solarized Light"),
    ("gruvbox-dark", "Gruvbox Dark"),
    ("mist", "Mist (FF9)"),     # ASCII ONLY -- this file has zero non-ASCII bytes and an em-dash here
]                               # would make the label the first one. The house style writes "--".


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
_DERIVED_KEYS = ("surface_2", "surface_3", "selection_bg", "text_subtle", "focus", "info",
                 "success_text", "warn_text", "error_text")


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
    out["selection_bg"] = _mix(pal["surface"], pal["accent"], 0.16)   # tinted, replaces full-accent select
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
    return out


# Motion tokens (Phase 1 constants; QSS cannot animate, so these feed QPropertyAnimation in Phase 10).
MOTION = {"fast_ms": 140, "medium_ms": 220, "easing": (0.2, 0.0, 0.0, 1.0)}


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
