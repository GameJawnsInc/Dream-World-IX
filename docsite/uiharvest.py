"""uiharvest -- the Manual's UI inventory: every referenceable Workspace control's REAL label,
harvested headlessly into a committed JSON. The prose counterpart of shots.py: screenshots keep
figures current; the inventory keeps WORDS current. A tutorial declares the UI labels it uses
(`[tutorial]` frontmatter, see TUTORIAL-SYSTEM.md); the site build verifies each declaration
against this file, so a renamed, moved, or removed control fails the build instead of rotting in
prose -- the exact class the New Journey dialog exposed (a tutorial step naming a button that no
longer exists).

Same laws and machinery as shots.py: gui_snap owns the harness, surfaces render from fixtures,
Windows + native Qt, no game read. Widget identity is the attribute path already used by shot
annotations -- ONE vocabulary across figures and prose.

Two harvests, one inventory:

  * the RENDERED half (`tab:` / `dlg:`) -- driven through the real Workspace headlessly, because a
    tab's controls only exist once Qt builds them;
  * the DECLARED half (`form:`) -- the editor's form labels, read straight out of
    ff9mapkit/editor/forms.py's `<THING>_SPEC` module globals. Those specs ARE the truth the Qt
    form renders from, so harvesting them needs no Qt at all, and every list-of-Field global is
    picked up mechanically: a spec added to forms.py later enters the inventory on the next run
    with no edit here.

Labels that PAINT LIVE MACHINE STATE (the deploy ledger's count, the New-Game target, this box's
ffmpeg) are pinned at the source first -- see _pin_live_state. Without that the committed file
drifts whenever any concurrent session deploys into the shared mod folder, and `--check` reports
the world rather than the UI.

Usage:
  py docsite/uiharvest.py            # write docsite/assets/ui-inventory.json
  py docsite/uiharvest.py --check    # re-harvest to memory, diff against the committed file
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
INVENTORY = HERE / "assets" / "ui-inventory.json"

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

# The safe dialog subset: plain openers with no cache pins (the anim pickers stay out). Keys are
# gui_snap DIALOG_OPENERS keys; inventory paths use the dash->underscore noun ("new_journey.x").
HARVEST_DIALOGS = ("new-field", "new-campaign", "new-journey", "fork-regions",
                   "import-fields", "setup", "prefs")


# --------------------------------------------------------------------------------- live-state pins
# Some rendered labels PAINT LIVE MACHINE STATE into their own text: the mod folder's deploy ledger
# ("410 deployed here · ..."), where New Game currently lands, this worktree's .ff9deploy.toml
# target, this box's ffmpeg and PySide6. Harvested raw they make the committed inventory drift on
# every unrelated deploy by any concurrent session (observed 410 -> 422 mid-session, and the mod
# folders are SHARED) and differ on every machine -- so `--check` would alarm on the WORLD instead
# of on the UI, which is the one thing it exists to watch. shots.toml pins exactly this painted text
# for FIGURES; below is that idiom applied to WORDS, pinned at the SOURCE the way gui_snap's
# _pin_setup_state / _pin_world_state / _pin_anim_cache family does, so the harvested sentence stays
# REAL prose in its real format instead of a placeholder a tutorial could never match.
#
# Values are fixed and plausible, never this machine's: three ledger rows, two of them undoable.
PINNED_LEDGER = (
    {"kind": "field", "id": "4003", "name": "glade", "script": "revert_deploy_4003.py", "mtime": 0.0},
    {"kind": "field", "id": "4005", "name": "hut_int", "script": None, "mtime": None},
    {"kind": "campaign", "id": None, "name": "revert_campaign.py", "script": "revert_campaign.py",
     "mtime": 0.0},
)
PINNED_NEWGAME = 4000                        # where the New-Game override reads as pointing
PINNED_DEPLOY_TARGET = ("FF9CustomMap", None)   # jobs.detect_deploy_target's own default -> slot 4003
PINNED_HEALTH = {"ffmpeg": "C:\\ffmpeg\\bin\\ffmpeg.exe",
                 "PySide6": "present"}       # health's OWN no-__version__ wording; never a version
# The absolute paths the pins deliberately paint (gui_snap's _pin_setup_state(game=True) resolves the
# install to C:/FF9; PINNED_HEALTH paints the ffmpeg row). Any OTHER drive-lettered path in the
# harvest is a leak -- see machine_leaks().
PINNED_PATHS = ("C:\\FF9", "C:\\ffmpeg\\bin\\ffmpeg.exe")


class _pin_live_state:
    """Replace every live read a harvested label paints with a fixed value.

    Each target is bound EAGERLY in __init__, so a renamed or moved function raises AttributeError
    right here -- at the pin -- instead of silently leaving the harvest un-pinned and machine-
    dependent again. The health rewrite additionally asserts it FIRED (a renamed row is a caught
    error, not a quiet no-op)."""

    def __init__(self):
        from ff9mapkit import health
        from ff9mapkit.editor import jobs
        self.jobs, self.health = jobs, health
        self._orig = (jobs.scan_deployed_reverts, jobs.current_newgame_target,
                      jobs.detect_deploy_target, health.health_report)

    def __enter__(self):
        real_report = self._orig[3]

        def report(*a, **k):
            rows = real_report(*a, **k)
            fired = set()
            for r in rows:
                if r["label"] in PINNED_HEALTH:
                    r["value"], r["level"], r["advice"] = PINNED_HEALTH[r["label"]], "ok", ""
                    fired.add(r["label"])
            missing = sorted(set(PINNED_HEALTH) - fired)
            if missing:
                raise SystemExit(f"uiharvest: health_report no longer emits {missing} -- the row was "
                                 f"renamed or dropped; fix PINNED_HEALTH or the harvest goes back to "
                                 f"recording this machine")
            return rows

        self.jobs.scan_deployed_reverts = lambda *_a, **_k: [dict(r) for r in PINNED_LEDGER]
        self.jobs.current_newgame_target = lambda *_a, **_k: PINNED_NEWGAME
        self.jobs.detect_deploy_target = lambda *_a, **_k: PINNED_DEPLOY_TARGET
        self.health.health_report = report
        return self

    def __exit__(self, *exc):
        (self.jobs.scan_deployed_reverts, self.jobs.current_newgame_target,
         self.jobs.detect_deploy_target, self.health.health_report) = self._orig
        return False


_ABS_PATH = re.compile(r"[A-Za-z]:[\\/][^\s]*")


def machine_leaks(inv: dict) -> list[str]:
    """Harvested strings carrying THIS machine's fingerprint -- the backstop for a volatile label
    added AFTER _pin_live_state was written.

    Honest about its reach: it catches PATHS (an unpinned drive-lettered path, or this box's home /
    temp / repo dir quoted anywhere). A live COUNT or version number in some future label is NOT
    path-shaped and slips past -- that class is caught by the twin-harvest fence in
    docsite/tests/test_uiharvest_pins.py, which harvests twice under different live state."""
    marks = [str(Path.home()), tempfile.gettempdir(), str(REPO)]
    leaks = []
    for skey, ents in inv["surfaces"].items():
        for key, ent in ents.items():
            for field in ("text", "a11y", "placeholder"):
                s = ent.get(field)
                if not s:
                    continue
                for m in marks:
                    if m.lower() in s.lower():
                        leaks.append(f"{skey} {key}.{field}: quotes this machine's {m!r}")
                for tok in _ABS_PATH.findall(s):
                    if not any(tok == p or tok.startswith(p + "\\") for p in PINNED_PATHS):
                        leaks.append(f"{skey} {key}.{field}: unpinned absolute path {tok!r}")
    return sorted(set(leaks))


class capture_next_dialog:
    """Patch QDialog.exec: hidden-show, HAND THE LIVE DIALOG to a callback, reject. The
    _grab_next_dialog idiom with the grab swapped for a visit -- file pickers and message
    statics stubbed for the same reason (a real modal hangs a headless run forever)."""

    def __init__(self, gs, visit):
        self.gs, self.visit = gs, visit

    def __enter__(self):
        from PySide6.QtWidgets import QDialog, QFileDialog
        self._QDialog, self._QFileDialog = QDialog, QFileDialog
        self._exec = QDialog.exec
        self._file = (QFileDialog.getOpenFileName, QFileDialog.getSaveFileName,
                      QFileDialog.getExistingDirectory)
        QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
        QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
        QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: "")
        me = self

        def exec_(dlg):
            me.gs._hide_flag(dlg)
            dlg.show()
            me.gs._settle()
            me.visit(dlg)
            dlg.close()
            return int(me._QDialog.DialogCode.Rejected)

        QDialog.exec = exec_
        self._modals = self.gs._no_modals()
        self._modals.__enter__()
        return self

    def __exit__(self, *exc):
        self._QDialog.exec = self._exec
        (self._QFileDialog.getOpenFileName, self._QFileDialog.getSaveFileName,
         self._QFileDialog.getExistingDirectory) = self._file
        self._modals.__exit__(*exc)
        return False


def _kit_version() -> str:
    with open(REPO / "ff9mapkit" / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]


def _load_gui_snap():
    spec = importlib.util.spec_from_file_location("gui_snap", REPO / "tools" / "gui_snap.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gui_snap"] = mod
    spec.loader.exec_module(mod)
    return mod


def _display(w) -> dict | None:
    """What a doc author could NAME in prose, per widget kind. QLineEdit's text() is the VALUE,
    never a label -- record its placeholder/a11y instead. Mnemonic ampersands stripped."""
    from PySide6.QtWidgets import (QAbstractButton, QComboBox, QGroupBox, QLabel, QLineEdit,
                                   QPlainTextEdit, QTextEdit)
    ent: dict = {"kind": type(w).__name__}
    if isinstance(w, QAbstractButton):
        ent["text"] = w.text().replace("&", "")
    elif isinstance(w, QGroupBox):
        ent["text"] = w.title().replace("&", "")
    elif isinstance(w, QLabel):
        t = w.text()
        if not t or len(t) > 120 or "<" in t:    # rich/long labels are prose, not nameable controls
            return None
        ent["text"] = t.replace("&", "")
    elif isinstance(w, (QLineEdit, QPlainTextEdit, QTextEdit, QComboBox)):
        pass                                      # value-carrying: a11y/placeholder only
    else:
        return None
    if hasattr(w, "accessibleName") and w.accessibleName():
        ent["a11y"] = w.accessibleName()
    if hasattr(w, "placeholderText") and getattr(w, "placeholderText", lambda: "")():
        ent["placeholder"] = w.placeholderText()
    return ent if len(ent) > 1 else None


def _harvest_doc(doc, prefix: str) -> dict[str, dict]:
    """One doc widget's nameable controls, keyed by the SAME attr paths shot annotations use.
    Only direct instance attributes: that is the vocabulary a shots.toml callout can reach, and
    it keeps the inventory stable (a full findChildren walk churns with layout internals)."""
    from PySide6.QtWidgets import QWidget
    out: dict[str, dict] = {}
    for name, w in vars(doc).items():
        if name.startswith("_") or not isinstance(w, QWidget):
            continue
        ent = _display(w)
        if ent:
            out[f"{prefix}.{name}"] = ent
    return out


def _harvest_dialog(dlg) -> dict[str, dict]:
    """A dialog's nameable controls. Dialogs do NOT hold their widgets as instance attributes
    (vars() is empty -- they are built from locals), so identity here is the LABEL itself:
    accessible name when set, else the rendered text -- the same handles gui_snap's _child_named
    drives dialogs by. Declarations therefore scope to the dialog (`widget = "dlg:<key>"`)."""
    from PySide6.QtWidgets import QWidget
    out: dict[str, dict] = {}
    for w in dlg.findChildren(QWidget):
        ent = _display(w)
        if not ent:
            continue
        key = ent.get("a11y") or ent.get("text") or ent.get("placeholder")
        if key:
            out[key] = ent
    return out


def _form_surface_key(global_name: str) -> str:
    """`FIELD_SPEC` -> `form:field`, `CHOICE_OPTION_SPEC` -> `form:choice-option`. Mechanical, so
    the surface set is whatever forms.py declares -- never a hand-kept list that can rot."""
    return "form:" + global_name[: -len("_SPEC")].lower().replace("_", "-")


def harvest_forms() -> dict[str, dict]:
    """The editor's FORM labels, keyed by the spec Field's own `key`. This is where the bulk of the
    core tutorial track's prose lives (the NPC / gateway / chest / cutscene / encounter / music
    forms), and none of it needs Qt: `<THING>_SPEC` is plain data.

    Entries use the same `{"text": ...}` shape as a rendered control, so the gate's truth-set logic
    is identical for a form field and a button."""
    sys.path.insert(0, str(REPO / "ff9mapkit"))   # the local package shadows any editable install
    from ff9mapkit.editor import forms

    surfaces: dict[str, dict] = {}
    for name, spec in vars(forms).items():
        if not name.endswith("_SPEC") or not isinstance(spec, list) or not spec:
            continue
        if not all(isinstance(f, forms.Field) for f in spec):
            continue                              # a same-named constant that is not a form spec
        ents: dict[str, dict] = {}
        for f in spec:
            ent = {"kind": f.kind, "text": f.label}
            if f.placeholder:                     # an authored placeholder is nameable prose too
                ent["placeholder"] = f.placeholder
            ents[f.key] = ent
        surfaces[_form_surface_key(name)] = ents
    if not surfaces:
        raise SystemExit("no <THING>_SPEC form specs found in ff9mapkit.editor.forms -- the specs "
                         "moved or were renamed; fix harvest_forms()")
    return surfaces


def harvest(*, pin_live: bool = True) -> dict:
    """The full inventory. ``pin_live=False`` un-pins the live-state reads -- ONLY the stability
    fence uses it, to prove the injected state actually reaches a label (a twin-harvest check that
    cannot tell pinned from unreachable is a check that cannot fail)."""
    gs = _load_gui_snap()
    ctx = gs._Ctx(SimpleNamespace(theme="light", scale=100, guided="guided", width=1280,
                                  height=850, campaign=None, thumb_source=None,
                                  out=str(gs._SCRATCH / "uiharvest")))
    surfaces: dict[str, dict] = {}
    live = _pin_live_state() if pin_live else contextlib.nullcontext()
    with gs._pin_setup_state(game=True, templates=True), live:
        win = gs._make_win(ctx)
        for tab, attr in sorted(gs.TAB_ATTRS.items()):
            surfaces[f"tab:{tab}"] = _harvest_doc(getattr(win, attr), attr)
        for key in HARVEST_DIALOGS:
            got: dict = {}
            with capture_next_dialog(gs, lambda d: got.update(_harvest_dialog(d))):
                gs.DIALOG_OPENERS[key](win)
            if not got:
                raise SystemExit(f"dlg:{key}: no dialog opened or no nameable controls -- "
                                 f"the opener flow changed; fix HARVEST_DIALOGS or the opener")
            surfaces[f"dlg:{key}"] = got
        gs._close(win)
    forms = harvest_forms()                       # additive, Qt-free -- appended last so the
    surfaces.update(forms)                        # committed JSON's existing order is untouched
    inv = {"kit_version": _kit_version(),
           "note": "generated by docsite/uiharvest.py -- do not hand-edit",
           "surfaces": surfaces}
    if pin_live:
        leaks = machine_leaks(inv)
        if leaks:
            raise SystemExit("uiharvest: the harvest recorded THIS MACHINE -- the committed "
                             "inventory would drift on every other box:\n  " + "\n  ".join(leaks)
                             + "\n(a new label paints live state: pin it at the source in "
                               "_pin_live_state, the way the ledger/newgame/health reads are)")
    n = sum(len(v) for v in surfaces.values())
    nf = sum(len(v) for v in forms.values())
    print(f"harvested {n} controls across {len(surfaces)} surfaces "
          f"({nf} form fields across {len(forms)} form surfaces, no Qt)")
    return inv


def flatten(inv: dict) -> dict[str, dict]:
    """key -> entry across all surfaces, for the --check diff. A tab entry's key is an attr path
    and globally unique; dialog and form entries are SCOPED names (a rendered label, a spec key)
    that repeat across surfaces, so they carry their surface -- otherwise one surface's drift
    silently overwrites another's."""
    flat: dict[str, dict] = {}
    for skey, ents in inv["surfaces"].items():
        for k, ent in ents.items():
            flat[k if skey.startswith("tab:") else f"{skey} {k}"] = ent
    return flat


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    inv = harvest()
    if not args.check:
        INVENTORY.parent.mkdir(parents=True, exist_ok=True)
        INVENTORY.write_text(json.dumps(inv, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"-> {INVENTORY}")
        return
    committed = json.loads(INVENTORY.read_text(encoding="utf-8"))
    a, b = flatten(committed), flatten(inv)
    drift = ([f"removed: {k}" for k in a.keys() - b.keys()]
             + [f"added: {k}" for k in b.keys() - a.keys()]
             + [f"changed: {k} {a[k]} -> {b[k]}" for k in a.keys() & b.keys() if a[k] != b[k]])
    if drift:
        print("DRIFT:\n  " + "\n  ".join(sorted(drift)))
        print("(a deliberate UI change? re-run `py docsite/uiharvest.py` and commit -- the site "
              "build will then point at any tutorial whose declared labels no longer hold)")
        raise SystemExit(1)
    print(f"check clean: {len(a)} controls match the committed inventory")


if __name__ == "__main__":
    main()
