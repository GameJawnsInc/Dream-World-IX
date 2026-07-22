"""A shared *result* surface for the GUI apps: a verdict banner + a structured problems list.

The kit's apps used to dump raw subprocess/traceback text into a scrolling log, leaving the user to
read tea leaves for "did it work, and what do I do next?". This module replaces that with two pieces:

  * a :class:`Verdict` -- a one-line outcome (ok / passed-with-warnings / failed / running) plus an
    optional next-action line ("Relaunch once, then ~ -> Warp -> 2640"), rendered as a coloured banner;
  * a flat list of :class:`Problem` rows (errors + warnings), rendered as a compact, colour-coded,
    selectable list -- the structured replacement for ``ERROR ...`` / ``warn ...`` log spam.

Following the same discipline as :mod:`.theme` / :mod:`.forms` / :mod:`.model`, the data layer
(``Verdict``/``Problem`` + the ``classify``/``from_returncode``/``problems`` builders) is **tk-FREE**
and unit-testable on a headless machine; the only Tk lives in :class:`FeedbackPanel`, which imports
tkinter lazily in ``__init__`` so importing this module never needs a display. The panel takes a
palette dict from :func:`.theme.apply_theme`, so it matches whatever app hosts it.
"""

from __future__ import annotations

import re
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


# --- failure-anchor extraction (the structured-failure lens) -------------------------------------
# A subprocess job (build / deploy / import) has NO structured error list -- only an exit code and a
# streamed log. On a crash the log is a grey wall in which the one line that says WHAT went wrong is the
# identical ink to forty `wrote ...` lines. This layer pulls that ONE line out so the shell can post it as
# a clickable Problems row that jumps to it in the Output console.
#
# THE "DON'T CRY WOLF" LAW (chair ruling, and the codified rule the console-tint already follows): fire
# ONLY on a non-zero exit AND a TIGHT anchor. Two anchor classes, both self-evident rather than sniffed:
#   * the terminal frame of a Python traceback -- the interpreter FIXES the header string and the final
#     exception line sits at column 0 below the indented frames, so it is an exact anchor, not a guess;
#   * the LAST ``error:``-classed CLI line -- ``error:`` with its colon, at the line head (optionally after
#     a short ``prog:``/``subcmd:`` prefix, so argparse's ``prog: error: ...`` and the kit's ``assemble
#     error: ...`` both match). The colon-immediately-after-``error`` is the tightness: a build log full of
#     paths and prose mentioning "error" (``wrote build/error_log``, "an error occurred") never matches.
# A non-zero exit with neither anchor yields NOTHING -- a no-anchor mess is not worth a false row.

_TRACEBACK_HEADER = "Traceback (most recent call last):"   # interpreter-fixed; matches shell.py's _TRACE_ANCHOR
# up to three short leading tokens (``prog:`` / ``build:``) then ``error:`` at a word boundary + a space.
_ERROR_LINE = re.compile(r"^(?:\S+ ){0,3}error\s*:\s", re.IGNORECASE)


@dataclass(frozen=True)
class FailureAnchor:
    """The single tightest 'this is what went wrong' line pulled from a failed job's captured stdout.

    ``text`` is the exact stripped line (shown as the Problems row's message AND searched for verbatim in
    the Output console to reveal it); ``line_no`` is 1-based within the captured text (for tests/debugging);
    ``kind`` is ``"traceback"`` or ``"error"``."""

    text: str
    line_no: int
    kind: str


def _traceback_anchor(lines):
    """The terminal exception line of the LAST traceback in ``lines`` (chained tracebacks -> the final one),
    or ``None``. Below the header the frame lines (``File ...`` / source) are all INDENTED, so the exception
    line is the FIRST non-empty column-0 line after the last header -- the ``ValueError: ...``. Scanning
    forward (not from the bottom) stops at the traceback's end, so any later program output isn't mistaken
    for the exception."""
    header = None
    for i, ln in enumerate(lines):
        if ln.strip() == _TRACEBACK_HEADER:
            header = i
    if header is None:
        return None
    for i in range(header + 1, len(lines)):
        ln = lines[i]
        if ln.strip() and not ln[:1].isspace():        # first non-empty column-0 line = the exception line
            return FailureAnchor(ln.strip(), i + 1, "traceback")
    return None


def _error_line_anchor(lines):
    """The LAST ``error:``-classed line in ``lines`` (see :data:`_ERROR_LINE`), or ``None``."""
    for i in range(len(lines) - 1, -1, -1):
        if _ERROR_LINE.match(lines[i].lstrip()):
            return FailureAnchor(lines[i].strip(), i + 1, "error")
    return None


def failure_anchor(output, code):
    """Pull the ONE tightest failure line out of a failed job's captured ``output``, or ``None``.

    ``None`` whenever ``code == 0`` (success noise is never an anchor) or ``output`` is empty. Otherwise the
    later (more terminal) of the two candidate anchors -- the traceback's exception line and the last
    ``error:`` line -- wins, honouring the "the failure is at the tail" reading; ``None`` if neither fires."""
    if code == 0 or not output:
        return None
    lines = output.splitlines()
    cands = [c for c in (_traceback_anchor(lines), _error_line_anchor(lines)) if c]
    if not cands:
        return None
    return max(cands, key=lambda c: c.line_no)


# --- plain-language error layer ------------------------------------------------------------------
# The raw CLI/engine/validation messages are precise but jargon-dense. This table maps the ones a
# NON-technical newcomer most often hits to a plain-language sentence + a single concrete next step, so the
# Problems dock can offer help on hover instead of leaving the user to read tea leaves. Each entry is
# (lowercase substring to match, friendly, next_step); the FIRST match wins, so keep specific rules first.
# Grounded against the real emit sites (discovered + spot-verified across build/lint/import/deploy/setup/
# forms/saves) -- NOT invented. Additive: the raw message still shows; this only enriches the tooltip.
_REWRITES = (
    ("could not locate the final fantasy ix install",
     "The app can't find your Final Fantasy IX game folder, so it can't read any of the game's data.",
     "Open Setup & Health and click “Locate game…”, then pick your FF9 install folder."),
    ("base templates not",
     "The app needs to copy some starter data out of your own FF9 game first, and that one-time setup "
     "step hasn't been run yet.",
     "Open Setup & Health and click Run setup (or run 'ff9mapkit extract-templates')."),
    ("unitypy",
     "Reading the game's fields and art needs a free helper add-on called UnityPy, which isn't installed.",
     "Install it by running: py -m pip install UnityPy, then try again."),
    ("pycryptodome",
     "Opening a real save file needs a free helper add-on called pycryptodome (it unlocks the save's "
     "encryption), which isn't installed.",
     "Install it by running: py -m pip install pycryptodome, then reopen the save."),
    ("tomldecodeerror",
     "Your project file (a .toml text file, like your field.toml) has a typo the app can't read — usually "
     "a missing quote, bracket, or = sign.",
     "Open the file, fix the line and column named in the error (look for an unclosed quote or bracket), "
     "then Check again."),
    ("area must be >= 10",
     "The field's Area number is under 10, and areas 0–9 make the game load a black screen.",
     "Set the [field] area to 10 or higher, then Check again."),
    ("[field] missing required key",
     "The field's [field] section is missing one of the three details it must always have: id, name, or area.",
     "Add the missing line — id, name, or area, whichever the error names — to the [field] section."),
    ("[camera] section is required",
     "This field has no camera set up, so the game would have no way to show the room.",
     "Add a [camera] section — either borrow a real field's camera or set pitch/distance/fov."),
    ("out of range 1-32767",
     "The field id you picked is below 1 or above 32767, and the game can't use an id outside that range.",
     "Pick a field id between 4000 and 9899 for a custom field."),
    ("custom band 4000",
     "The id you entered isn't a free custom one — it's either a real, locked game id (below 4000) or above "
     "the maximum allowed.",
     "Choose an id from 4000 to 9899 (the usual range for a custom field)."),
    ("id collision",
     "Another mod folder in your game already uses this field's id number, and every field needs its own id, "
     "so one of them would boot to a black screen.",
     "Give this field a different, unused id (any free id in 4000-9899), then deploy again."),
    ("try: ff9mapkit list-fields",
     "No real FF9 field matches the id or name you typed, so there's nothing to import or fork.",
     "Click Find… to look up the correct field, or run 'ff9mapkit list-fields' to see valid ones."),
    ("not a forkable field",
     "That id has no ordinary room background to fork — it's a special/cutscene screen (like the game's "
     "opening), not a normal explorable room.",
     "Pick a regular field that has art (use Find… or 'list-fields' to find one)."),
    ("reserved region",
     "The story flag (a saved on/off switch) you're setting sits in a range the game reserves for its "
     "moogle-mail system and its own bookkeeping, so writing there could corrupt the save.",
     "Use a flag number of 8712 or higher — the safe custom range for your own flags."),
    ("field id must be a number",
     "The 'Field id' box needs a plain number — the id to give your new forked field — and what you typed "
     "isn't one.",
     "Type a numeric id like 4003 (any free custom id, 4000–9899) in the Field id box, then press Import "
     "field again. (To name the field instead, use the Name box next to it.)"),
    ("pick a .field.toml",
     "You pressed Check, Build, or Deploy without first choosing a file to work on.",
     "Select a .field.toml (or campaign/journeys/battle .toml) file, then press the button again."),
    ("it will clone the player model",
     "An NPC (a non-player character, like a townsperson) has no character model chosen, so in-game it "
     "would appear as a copy of the main hero, Zidane.",
     "Give the NPC a model, preset, or archetype — or delete it if it was only a leftover placeholder marker."),
    ("that is a bundled example",
     "You're trying to save changes to one of the app's built-in example fields, which are locked so the "
     "originals stay intact.",
     "Make your own copy first — use the Field menu > New Field (Ctrl-N), or copy the example's folder — "
     "then edit that copy."),
    ("development deploy loop",
     "One-click Deploy (the quick test-slot + reload loop) only works from the full developer source-code copy "
     "of the app, not this installed copy.",
     "In the Build panel, pick “Install to game” — it writes the mod straight into your FF9 game folder with "
     "no developer checkout needed."),
    ("unknown item",
     "That item or equipment name doesn't match anything in the game's item list — usually a typo.",
     "Fix it to a real item name (the error lists close “Did you mean…?” matches), then re-enter it."),
    ("gil must be in",
     "The Gil amount you entered is higher than the game's maximum of 9,999,999.",
     "Enter 9,999,999 or less for Gil."),
    ("whole number",
     "A box that expects a plain number has letters, a decimal point, or is left blank.",
     "Type a plain whole number (like 5 or 4003) in that box."),
    ("invalid value — not saved",
     "One of the boxes on this form contains something the app can't read, so it won't save until that's "
     "fixed.",
     "Re-check the values you typed on this form, fix the box the app couldn't read (for example, put a "
     "plain number where a number is expected), then press Save again."),
)


def humanize(message):
    """Map a raw error/warning ``message`` to a ``(friendly, next_step)`` pair in plain language, or ``None``
    if there's no rewrite for it. Case-insensitive substring match; the first :data:`_REWRITES` entry that
    matches wins (order = specificity). Additive -- callers keep showing the raw message and use this only to
    enrich a tooltip / status tip, so an unmatched message simply gets no extra help."""
    if not message:
        return None
    low = str(message).lower()
    for match, friendly, next_step in _REWRITES:
        if match in low:
            return (friendly, next_step)
    return None


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
