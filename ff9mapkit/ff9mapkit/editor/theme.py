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
    "bg": "#f4f5f7",            # window background
    "surface": "#ffffff",       # tree / form surface
    "surface_btn": "#ffffff",   # neutral button face
    "field": "#ffffff",         # entry / listbox background
    "text": "#1b1f24",          # primary text
    "muted": "#6b7280",         # secondary text (hints)
    "accent": "#2f6feb",        # primary buttons, tree selection
    "accent_fg": "#ffffff",     # text on accent
    "accent_hover": "#256ae0",
    "accent_pressed": "#1f5fcc",
    "help": "#7c3aed",          # help / info affordance (violet -- distinct from accent/success/warn)
    "help_hover": "#6d28d9",
    "border": "#d6dae0",
    "success": "#1a8f5a",       # "placed in Blender" / OK lines
    "hover": "#eef1f4",         # neutral button hover
    "pressed": "#e3e7ec",
    "scroll": "#c3c8cf",        # scrollbar thumb
    "log_bg": "#eef0f3",
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
    "accent_fg": "#ffffff",
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
    "muted": "#8a93a5",
    "accent": "#5e81ac",        # nord10 (frost, deep blue)
    "accent_fg": "#ffffff",     # white over the mid-blue accent (snow-storm #eceff4 was a touch low-contrast)
    "accent_hover": "#6a8cb6",
    "accent_pressed": "#547299",
    "help": "#b48ead",          # nord15 (aurora, purple)
    "help_hover": "#c29bbb",
    "border": "#434c5e",        # nord2
    "success": "#a3be8c",       # nord14 (green)
    "hover": "#3b4252",
    "pressed": "#434c5e",
    "scroll": "#4c566a",        # nord3
    "log_bg": "#272c36",
    "log_fg": "#d8dee9",        # nord4
    "error": "#bf616a",         # nord11 (red)
    "warn": "#ebcb8b",          # nord13 (yellow)
}
DRACULA = {                     # https://draculatheme.com
    "dark": True,
    "bg": "#282a36",
    "surface": "#2d2f3b",
    "surface_btn": "#3a3d4d",
    "field": "#21222c",
    "text": "#f8f8f2",
    "muted": "#8b91b8",         # comment #6272a4, lifted for hint legibility
    "accent": "#bd93f9",        # purple
    "accent_fg": "#282a36",
    "accent_hover": "#caa6fb",
    "accent_pressed": "#a87ee8",
    "help": "#ff79c6",          # pink
    "help_hover": "#ff92d0",
    "border": "#44475a",        # current line
    "success": "#50fa7b",       # green
    "hover": "#3a3d4d",
    "pressed": "#44475a",
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
    "text": "#93a1a1",          # base1
    "muted": "#6b8a8a",
    "accent": "#268bd2",        # blue
    "accent_fg": "#ffffff",     # white over the blue accent (base3 cream reads low-contrast on it)
    "accent_hover": "#3597db",
    "accent_pressed": "#1f78ba",
    "help": "#6c71c4",          # violet
    "help_hover": "#7e83cf",
    "border": "#0e4a59",
    "success": "#859900",       # green
    "hover": "#0b4350",
    "pressed": "#0e4a59",
    "scroll": "#586e75",        # base01
    "log_bg": "#00212b",
    "log_fg": "#839496",        # base0
    "error": "#dc322f",         # red
    "warn": "#b58900",          # yellow
}
SOLARIZED_LIGHT = {
    "dark": False,
    "bg": "#fdf6e3",            # base3
    "surface": "#fbf3da",
    "surface_btn": "#f4ecd3",
    "field": "#fffdf5",
    "text": "#586e75",          # base01
    "muted": "#657b83",         # base00 (base1 #93a1a1 is too low-contrast for hint text on the cream bg)
    "accent": "#268bd2",        # blue
    "accent_fg": "#ffffff",     # white over the blue accent
    "accent_hover": "#1f7ec0",
    "accent_pressed": "#1a6ca8",
    "help": "#6c71c4",          # violet
    "help_hover": "#595fb8",
    "border": "#e6dcc0",
    "success": "#728a00",       # deepened green for light-bg legibility
    "hover": "#f3ebd2",
    "pressed": "#ece3c8",
    "scroll": "#cfc8b0",
    "log_bg": "#eee8d5",        # base2
    "log_fg": "#586e75",
    "error": "#dc322f",         # red
    "warn": "#b58900",          # yellow
}
GRUVBOX_DARK = {                # https://github.com/morhetz/gruvbox
    "dark": True,
    "bg": "#282828",            # bg0
    "surface": "#32302f",       # bg0_s
    "surface_btn": "#3c3836",   # bg1
    "field": "#3c3836",
    "text": "#ebdbb2",          # fg1
    "muted": "#a89984",         # gray
    "accent": "#fe8019",        # bright orange
    "accent_fg": "#282828",
    "accent_hover": "#ff8f33",
    "accent_pressed": "#e36f12",
    "help": "#d3869b",          # bright purple
    "help_hover": "#dd9aab",
    "border": "#504945",        # bg2
    "success": "#b8bb26",       # bright green
    "hover": "#3c3836",
    "pressed": "#504945",
    "scroll": "#665c54",        # bg3
    "log_bg": "#1d2021",        # bg0_h
    "log_fg": "#d5c4a1",        # fg2
    "error": "#fb4934",         # bright red
    "warn": "#fabd2f",          # bright yellow
}

# All selectable palettes (keyed by mode string). "auto" is a meta-mode (follow the OS) -- not in here.
THEMES = {
    "light": LIGHT,
    "dark": DARK,
    "nord": NORD,
    "dracula": DRACULA,
    "solarized-dark": SOLARIZED_DARK,
    "solarized-light": SOLARIZED_LIGHT,
    "gruvbox-dark": GRUVBOX_DARK,
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
