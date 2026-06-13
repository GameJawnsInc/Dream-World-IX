"""A shared *result* surface for the GUI apps: a verdict banner + a structured problems list.

The kit's apps used to dump raw subprocess/traceback text into a scrolling log, leaving the user to
read tea leaves for "did it work, and what do I do next?". This module replaces that with two pieces:

  * a :class:`Verdict` -- a one-line outcome (ok / passed-with-warnings / failed / running) plus an
    optional next-action line ("Relaunch once, then F6 -> Warp -> 2640"), rendered as a coloured banner;
  * a flat list of :class:`Problem` rows (errors + warnings), rendered as a compact, colour-coded,
    selectable list -- the structured replacement for ``ERROR ...`` / ``warn ...`` log spam.

Following the same discipline as :mod:`.theme` / :mod:`.forms` / :mod:`.model`, the data layer
(``Verdict``/``Problem`` + the ``classify``/``from_returncode``/``problems`` builders) is **tk-FREE**
and unit-testable on a headless machine; the only Tk lives in :class:`FeedbackPanel`, which imports
tkinter lazily in ``__init__`` so importing this module never needs a display. The panel takes a
palette dict from :func:`.theme.apply_theme`, so it matches whatever app hosts it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- the four outcome levels (also the problem severities, minus "ok"/"running") -----------------
OK = "ok"
WARN = "warn"
ERROR = "error"
RUNNING = "running"

# glyphs read fine in Segoe UI (the themed default font); kept ASCII-safe-ish for any console echo.
_GLYPH = {OK: "✓", WARN: "⚠", ERROR: "✕", RUNNING: "…"}  # ✓ ⚠ ✕ …


@dataclass(frozen=True)
class Problem:
    """One row in the problems list: an error or a warning, with an optional location label."""

    severity: str          # ERROR | WARN
    message: str
    where: str = ""        # optional: a field/member/line the problem belongs to (for a future jump-to)


@dataclass(frozen=True)
class Verdict:
    """A one-line outcome to show in the banner."""

    level: str             # OK | WARN | ERROR | RUNNING
    headline: str
    next_action: str = ""  # the single most useful next step (e.g. an in-game warp), shown under the banner


def _n(count: int, word: str) -> str:
    """``2, 'error' -> '2 errors'`` / ``1, 'warning' -> '1 warning'`` (naive English pluralisation)."""
    return f"{count} {word}" + ("" if count == 1 else "s")


def classify(errors, warnings, *, subject="", clean_headline=None, next_action="") -> Verdict:
    """Turn two message lists into a :class:`Verdict`.

    ``subject`` prefixes the headline ("Build", "Check", "Campaign lint"). Errors win over warnings:
    any error -> a failed verdict; warnings only -> passed-with-warnings; neither -> ``clean_headline``
    (default "<subject> -- all clear")."""
    ne, nw = len(errors), len(warnings)
    subj = subject.strip()
    if ne:
        tail = _n(ne, "problem") + (f", {_n(nw, 'warning')}" if nw else "") + " to fix"
        head = f"{subj} -- {tail}" if subj else tail
        return Verdict(ERROR, head, next_action)
    if nw:
        head = f"{subj} -- passed with {_n(nw, 'warning')}" if subj else f"passed with {_n(nw, 'warning')}"
        return Verdict(WARN, head, next_action)
    head = clean_headline or (f"{subj} -- all clear" if subj else "all clear")
    return Verdict(OK, head, next_action)


def from_returncode(code, *, subject="", ok_headline=None, ok_next="", fail_hint="") -> Verdict:
    """A :class:`Verdict` for a subprocess result (the import/deploy shell-outs that have no structured
    error list -- only an exit code + a streamed log). ``code == 0`` -> ok; anything else -> failed,
    pointing the user at the streamed details."""
    subj = subject.strip()
    if code == 0:
        return Verdict(OK, ok_headline or (f"{subj} -- done" if subj else "done"), ok_next)
    head = f"{subj} -- failed (exit {code})" if subj else f"failed (exit {code})"
    return Verdict(ERROR, head, fail_hint or "See the details below.")


def problems(errors=(), warnings=()) -> list:
    """Flatten ``(errors, warnings)`` string lists into a severity-tagged :class:`Problem` list
    (errors first, then warnings -- the natural read order)."""
    rows = [Problem(ERROR, str(m)) for m in errors]
    rows += [Problem(WARN, str(m)) for m in warnings]
    return rows


# --- the Tk widget (lazy import keeps the data layer above headless-importable) ------------------
class FeedbackPanel:
    """A coloured verdict banner + a structured problems list, themed from a palette dict.

    Construct it on a ttk parent and ``.frame.pack(...)`` it where the old log used to dominate. Drive
    it from the UI thread: ``running(headline)`` when a job starts, then ``show(verdict, problems)``
    when it finishes. ``on_select(problem)`` (optional) fires when a problem row is clicked -- the seam
    a future unified shell will use to jump to the offending node.
    """

    def __init__(self, parent, palette, *, on_select=None):
        import tkinter as tk
        from tkinter import ttk

        self.pal = palette
        self.on_select = on_select
        self._rows: list = []

        self.frame = ttk.Frame(parent)

        # the banner: a coloured status stripe + a glyph + the headline, and a next-action line beneath.
        self._banner = tk.Frame(self.frame, background=palette["surface"],
                                highlightthickness=1, highlightbackground=palette["border"])
        self._stripe = tk.Frame(self._banner, width=4, background=palette["muted"])
        self._stripe.pack(side="left", fill="y")
        inner = tk.Frame(self._banner, background=palette["surface"])
        inner.pack(side="left", fill="both", expand=True, padx=10, pady=7)
        self._glyph = tk.Label(inner, text="", background=palette["surface"], foreground=palette["muted"],
                               font=("Segoe UI", 13, "bold"))
        self._glyph.pack(side="left", padx=(0, 8))
        headwrap = tk.Frame(inner, background=palette["surface"])
        headwrap.pack(side="left", fill="x", expand=True)
        self._headline = tk.Label(headwrap, text="", background=palette["surface"],
                                  foreground=palette["text"], font=("Segoe UI", 11, "bold"),
                                  anchor="w", justify="left")
        self._headline.pack(fill="x", anchor="w")
        self._next = tk.Label(headwrap, text="", background=palette["surface"],
                              foreground=palette["accent"], font=("Segoe UI", 10), anchor="w",
                              justify="left", wraplength=560)
        # _next is packed only when there's a next-action string.

        # the problems list: a compact tree (severity glyph + message), colour-coded, selectable.
        self._plist_wrap = ttk.Frame(self.frame)
        self._plist = ttk.Treeview(self._plist_wrap, show="tree", selectmode="browse", height=5)
        self._plist.column("#0", width=560, stretch=True)
        self._plist.pack(side="left", fill="both", expand=True)
        psb = ttk.Scrollbar(self._plist_wrap, orient="vertical", command=self._plist.yview)
        psb.pack(side="right", fill="y")
        self._plist.configure(yscrollcommand=psb.set)
        self._plist.tag_configure(ERROR, foreground=palette["error"])
        self._plist.tag_configure(WARN, foreground=palette["warn"])
        self._plist.bind("<<TreeviewSelect>>", self._on_row_select)

        # both pieces start hidden; show() / running() reveal them.

    # -- public API (call on the UI thread) --
    def running(self, headline="Working…"):
        """Show a neutral 'in progress' banner and clear any prior problems."""
        self._set_banner(Verdict(RUNNING, headline))
        self._set_problems([])

    def show(self, verdict, problem_rows=()):
        """Render a finished :class:`Verdict` + its (possibly empty) :class:`Problem` rows."""
        self._set_banner(verdict)
        self._set_problems(list(problem_rows))

    def clear(self):
        """Hide the banner + problems entirely (back to the resting state)."""
        self._banner.pack_forget()
        self._plist_wrap.pack_forget()

    # -- internals --
    def _color(self, level):
        return {OK: self.pal["success"], WARN: self.pal["warn"], ERROR: self.pal["error"],
                RUNNING: self.pal["muted"]}.get(level, self.pal["muted"])

    def _set_banner(self, verdict):
        col = self._color(verdict.level)
        self._stripe.configure(background=col)
        self._glyph.configure(text=_GLYPH.get(verdict.level, ""), foreground=col)
        self._headline.configure(text=verdict.headline)
        if verdict.next_action:
            self._next.configure(text=verdict.next_action)
            self._next.pack(fill="x", anchor="w", pady=(2, 0))
        else:
            self._next.pack_forget()
        if not self._banner.winfo_ismapped():
            kw = {"fill": "x", "padx": 10, "pady": (8, 4)}
            if self._plist_wrap.winfo_ismapped():    # keep the banner above an already-shown problems list
                kw["before"] = self._plist_wrap
            self._banner.pack(**kw)

    def _set_problems(self, rows):
        self._rows = rows
        self._plist.delete(*self._plist.get_children())
        if not rows:
            self._plist_wrap.pack_forget()
            return
        for i, p in enumerate(rows):
            label = f"{_GLYPH.get(p.severity, '')}  {p.message}"
            if p.where:
                label += f"   ({p.where})"
            self._plist.insert("", "end", iid=str(i), text=label, tags=(p.severity,))
        # size the list to its contents (capped), so a single problem isn't a tall empty box.
        self._plist.configure(height=max(2, min(len(rows), 8)))
        if not self._plist_wrap.winfo_ismapped():
            self._plist_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 6))

    def _on_row_select(self, _evt=None):
        if not self.on_select:
            return
        sel = self._plist.selection()
        if sel and sel[0].isdigit():
            idx = int(sel[0])
            if 0 <= idx < len(self._rows):
                self.on_select(self._rows[idx])
