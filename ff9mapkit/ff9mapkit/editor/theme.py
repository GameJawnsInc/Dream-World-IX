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
THEMES = {"light": LIGHT, "dark": DARK}


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
    """Choose a palette. ``mode``: ``"light"`` / ``"dark"`` / ``"auto"`` (match the OS, default)."""
    if mode == "light":
        return LIGHT
    if mode == "dark":
        return DARK
    return DARK if detect_os_dark() else LIGHT


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
