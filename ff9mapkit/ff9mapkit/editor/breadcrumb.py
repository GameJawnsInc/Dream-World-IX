"""A clickable breadcrumb -- the GUI's "you are here" across the game-data hierarchy.

The kit's data forms a containment hierarchy -- a JOURNEY (a playable arc) contains CAMPAIGNS, a
campaign contains FIELDS, a field contains OBJECTS (NPCs/gateways/events/the player & party). Today
that depth is split across windows; this widget renders the full resolved path as one line of
clickable segments (``◆ Dali Arc  ▸  ▣ Dali chain  ▸  ● DALI_INN  ▸  ▸ NPC: Innkeeper``) so a user
always reads, in plain words, where they are -- and clicking any ancestor segment navigates up to it.

Same discipline as :mod:`.theme` / :mod:`.feedback`: the data layer (``Crumb`` + :func:`trail`) is
tk-FREE and unit-testable; the only Tk lives in :class:`Breadcrumb`, which imports tkinter lazily.
"""

from __future__ import annotations

from dataclasses import dataclass

# the four hierarchy levels, outermost -> innermost, with a leading glyph (matches the navigator badges).
JOURNEY, CAMPAIGN, FIELD, OBJECT = "journey", "campaign", "field", "object"
GLYPH = {JOURNEY: "◆", CAMPAIGN: "▣", FIELD: "●", OBJECT: "▸"}


@dataclass(frozen=True)
class Crumb:
    """One breadcrumb segment: its hierarchy ``level``, the ``label`` shown, and a ``key`` the click
    handler uses to navigate (a member name for a field, a tree iid for an object, a sentinel for the
    journey/campaign roots)."""

    level: str
    label: str
    key: str = ""


def trail(journey=None, campaign=None, field=None, obj_label=None, obj_key="") -> list:
    """Build the ordered :class:`Crumb` list from whatever levels are currently resolved (each is
    optional; an unopened level is simply omitted, so the trail grows as the user drills in)."""
    out = []
    if journey:
        out.append(Crumb(JOURNEY, journey, "@journey"))
    if campaign:
        out.append(Crumb(CAMPAIGN, campaign, "@campaign"))
    if field:
        out.append(Crumb(FIELD, field, field))           # key = the campaign member name
    if obj_label:
        out.append(Crumb(OBJECT, obj_label, obj_key))     # key = the editor tree iid (e.g. "npc:2")
    return out


class Breadcrumb:
    """A one-line clickable path bar themed from a palette dict. ``on_navigate(crumb)`` fires when an
    ANCESTOR segment is clicked (the leaf -- where you already are -- is inert)."""

    def __init__(self, parent, palette, *, on_navigate=None):
        import tkinter as tk

        self.pal = palette
        self.on_navigate = on_navigate
        self.frame = tk.Frame(parent, background=palette["surface"],
                              highlightthickness=1, highlightbackground=palette["border"])
        self._empty = "No campaign open -- Open a campaign.toml to navigate it."
        self.set([])

    def set(self, crumbs):
        """Render ``crumbs`` (a :func:`trail` list); an empty list shows a muted placeholder."""
        import tkinter as tk

        for w in self.frame.winfo_children():
            w.destroy()
        if not crumbs:
            tk.Label(self.frame, text=self._empty, background=self.pal["surface"],
                     foreground=self.pal["muted"], font=("Segoe UI", 10)).pack(side="left", padx=10, pady=5)
            return
        last = len(crumbs) - 1
        for i, c in enumerate(crumbs):
            if i:
                tk.Label(self.frame, text="▸", background=self.pal["surface"],
                         foreground=self.pal["muted"], font=("Segoe UI", 10)).pack(side="left", padx=1)
            leaf = (i == last)
            lbl = tk.Label(self.frame, text=f"{GLYPH.get(c.level, '')} {c.label}",
                           background=self.pal["surface"],
                           foreground=self.pal["text"] if leaf else self.pal["accent"],
                           font=("Segoe UI", 10, "bold") if leaf else ("Segoe UI", 10),
                           cursor="arrow" if leaf else "hand2", padx=5, pady=4)
            lbl.pack(side="left", pady=1)
            if not leaf and self.on_navigate is not None:
                lbl.bind("<Button-1>", lambda _e, cc=c: self.on_navigate(cc))
