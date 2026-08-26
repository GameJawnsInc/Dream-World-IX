"""Unknown-key detection for ``field.toml`` -- the schema is HARVESTED from the code's own reads.

The trap this module exists to dodge: a whitelist scraped from *authored* files is usage, not a
schema -- any valid-but-unused key false-positives, and a warning list nobody trusts is worse than
none. The key set here comes from the other side. :func:`wrap` clothes the parsed TOML tree in a
recording ``dict`` subclass; the harvester then runs the REAL consumers over it (load / validate /
lint / build) and records every key the code *asks about* (``get`` / ``in`` / ``[]`` /
``setdefault`` / ``pop``) -- whether or not the key is present in the data. Probes are not usage:
building any project with one ``[[npc]]`` records the full npc vocabulary the consumers support,
not the three keys that example happened to write.

``_regen_fieldschema.py`` runs that harvest over the bundled examples (plus targeted stubs) and
emits ``_fieldschema.py``:

* ``VOCAB``    -- normalized dotted path (``"field"``, ``"npc"``, ``"npc.anims"``) -> every key the
  consumers probed there. A list-of-tables shares its key's path (entries of ``[[npc]]`` are
  ``"npc"``), so a section that ships as either one table or an array checks the same either way.
* ``ENFORCED`` -- the paths where checking is ON. A path is enforced only if it occurred in a
  corpus project that completed the FULL offline pipeline (load + validate + lint + build), so a
  section whose consumers never all ran is *recorded* but never enforced against a user. Honest
  degradation beats a confident false positive.

:func:`check` / :func:`check_path` walk an AUTHORED file (pre scene-merge, pre desugar -- exactly
what the user typed) and report keys the build would silently ignore, with did-you-mean
suggestions from the local vocabulary and, failing that, the other sections that do read the key
(the cross-section typo class a flat usage list can never catch).
"""

from __future__ import annotations

import difflib
import tomllib
from contextlib import contextmanager
from pathlib import Path


# --------------------------------------------------------------------------- recording wrapper

class Recorder:
    """Accumulates probes: ``probes[path]`` = the set of keys any consumer asked about there."""

    def __init__(self) -> None:
        self.probes: dict[str, set[str]] = {}

    def record(self, path: str, key) -> None:
        if isinstance(key, str):
            self.probes.setdefault(path, set()).add(key)


def _child_path(path: str, key: str) -> str:
    return f"{path}.{key}" if path else str(key)


def _wrapv(v, rec: Recorder, path: str):
    """Wrap a value for recording: dicts become spies, lists keep their path (entries of a
    list-of-tables share the list key's path), scalars pass through."""
    if isinstance(v, _Spy):
        return v
    if isinstance(v, dict):
        return _Spy(v, rec, path)
    if isinstance(v, list):
        return [_wrapv(x, rec, path) for x in v]
    return v


class _Spy(dict):
    """A real ``dict`` (so every ``isinstance(x, dict)`` in the consumers still holds) that records
    which keys the consumers ask about. Children are wrapped AT CONSTRUCTION, so they stay wrapped
    no matter how they're reached -- including through the C-level fast paths (``{**d}`` /
    ``dict(d)``) that bypass method overrides: the copy is plain, but its values are still spies.
    Exhaustive reads (``items()`` / iteration / copies) record nothing on purpose -- copying a dict
    is not a claim that every key in it is legal."""

    __slots__ = ("_rec", "_path")

    def __init__(self, data: dict, rec: Recorder, path: str = ""):
        self._rec = rec
        self._path = path
        super().__init__({k: _wrapv(v, rec, _child_path(path, k)) for k, v in data.items()})

    # deepcopy/pickle degrade to a PLAIN dict: a dict subclass with __slots__ has no default
    # state protocol, and a consumer that deep-copies its section must never crash the harvest.
    def __reduce__(self):
        return (dict, (dict(self),))

    def _probe(self, key) -> None:
        self._rec.record(self._path, key)

    def __getitem__(self, key):
        self._probe(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        self._probe(key)
        return super().get(key, default)

    def __contains__(self, key):
        self._probe(key)
        return super().__contains__(key)

    def setdefault(self, key, default=None):
        self._probe(key)
        if not super().__contains__(key):
            super().__setitem__(key, _wrapv(default, self._rec, _child_path(self._path, key)))
        return super().__getitem__(key)

    def pop(self, key, *default):
        self._probe(key)
        return super().pop(key, *default)

    def __setitem__(self, key, value):
        # keep consumer rewrites recordable (e.g. flag-name -> index resolution writes back)
        super().__setitem__(key, _wrapv(value, self._rec, _child_path(self._path, key)))


def wrap(data: dict, rec: Recorder) -> _Spy:
    """The whole parsed tree as a recording dict (root path ``""``)."""
    return _Spy(data, rec, "")


@contextmanager
def harvesting(rec: Recorder):
    """While active, every :meth:`FieldProject.load` wraps its merged raw tree in ``rec``'s spy --
    the seam sits BEFORE flag resolution and the ferry/siege desugarers, so their probes record
    too. Production never enters this context; the seam is identity there."""
    from . import build
    prev = build._load_instrument
    build._load_instrument = lambda raw: wrap(raw, rec)
    try:
        yield rec
    finally:
        build._load_instrument = prev


# --------------------------------------------------------------------------- the checker

_REGEN_HINT = ("if this key is real, the harvested schema is stale -- regenerate it: "
               "py -m ff9mapkit._regen_fieldschema")


def load_schema() -> "tuple[dict[str, frozenset], frozenset]":
    """The shipped harvest (``_fieldschema.py``) as ``(vocab, enforced)``. Raises ImportError if the
    generated module is missing -- callers surface that loudly rather than silently passing."""
    from . import _fieldschema
    vocab = {p: frozenset(keys) for p, keys in _fieldschema.VOCAB.items()}
    return vocab, frozenset(_fieldschema.ENFORCED)


def _display(path: str, seg_is_list: bool) -> str:
    """A human label for the node holding the unknown key: ``[field]`` / ``[[npc]]`` /
    ``[[npc]].anims`` / ``the top level``."""
    if not path:
        return "the top level"
    head, *rest = path.split(".")
    label = f"[[{head}]]" if seg_is_list else f"[{head}]"
    # nested tables display as [head].sub -- the head's bracket shape carries the array-ness
    return label + ("." + ".".join(rest) if rest else "")


def _where_else(key: str, vocab: dict, not_path: str) -> list[str]:
    return sorted(p for p, keys in vocab.items() if key in keys and p != not_path and p)


# ⚠ KEYS THE BUILD READS EVERYWHERE AND WIRES ALMOST NOWHERE -- for these, and ONLY these, every
# other message this module can produce ("the build never reads it, so it is silently ignored") is
# a LIE, and it was a costly one: `polled` is read by content.text.window_polled from dress_window,
# which every dialogue-bearing block routes through, so `[[npc]] polled = true` DID change the
# shipped bytes (it defaults [NFOC] on) while the lint told the author it was inert.
#
# They are absent from those blocks' VOCAB on purpose -- the universal read goes through a plain
# copy so it harvests nothing (fieldschema._Spy records only `get`) -- so the unknown-key path is
# where the author meets them, and it has to tell the truth. `build.validate` REFUSES them outside
# their wired lanes; this text points at that refusal instead of contradicting it.
_READ_EVERYWHERE = {
    "polled": ("the build DOES read it here -- content/text.py:window_polled runs from "
               "dress_window on every dialogue block and would default [NFOC] onto a BLOCKING "
               "window with no script close -- so `ff9mapkit lint` REFUSES it rather than "
               "ignoring it. It is WIRED only on a [[choice.options]] / [ate] option reply, "
               "which opens its window async, polls for a real button edge and closes it."),
}


def _finding(path: str, key: str, value, local: frozenset, vocab: dict,
             entered_via_list: bool) -> str:
    loc = _display(path, entered_via_list)
    if not path and isinstance(value, (dict, list)):
        shape = f"[[{key}]]" if isinstance(value, list) else f"[{key}]"
        what = f"unknown section {shape}"
    else:
        what = f"unknown key '{key}' in {loc}"
    if key in _READ_EVERYWHERE and path:
        return f"{what} -- {_READ_EVERYWHERE[key]}"
    close = difflib.get_close_matches(key, sorted(local), n=2, cutoff=0.6)
    if close:
        alts = " or ".join(f"'{c}'" for c in close)
        return f"{what} -- did you mean {alts}? The build never reads '{key}' there, so it is silently ignored."
    elsewhere = _where_else(key, vocab, path)
    if elsewhere:
        secs = ", ".join(_display(p, False) for p in elsewhere[:3])
        return (f"{what} -- '{key}' is a key of {secs}, not of {loc}; here the build silently "
                f"ignores it.")
    return f"{what} -- the build never reads it, so it is silently ignored ({_REGEN_HINT})."


def check(data: dict, *, vocab: dict, enforced: frozenset) -> list[str]:
    """Findings for one AUTHORED tree (the parsed field.toml, pre-merge/desugar). Only enforced
    paths are checked; below an unknown key nothing is checked (the whole subtree is already
    suspect). Order: document order, stable."""
    out: list[str] = []

    def walk(node: dict, path: str, via_list: bool) -> None:
        local = vocab.get(path)
        if path not in enforced or not local:
            return
        for k, v in node.items():
            if k not in local:
                out.append(_finding(path, k, v, local, vocab, via_list))
                continue
            child = _child_path(path, k)
            if isinstance(v, dict):
                walk(v, child, False)
            elif isinstance(v, list):
                for elem in v:
                    if isinstance(elem, dict):
                        walk(elem, child, True)

    walk(data, "", False)
    return out


def check_path(toml_path) -> list[str]:
    """Findings for an authored ``field.toml`` on disk, against the shipped harvest. The sibling
    ``scene.toml`` is deliberately NOT checked: it is Blender-written, not hand-typed, so the typo
    surface this guards is absent there. Missing schema data is itself a (single) finding."""
    try:
        vocab, enforced = load_schema()
    except ImportError:
        return [f"the harvested field.toml schema is missing (_fieldschema.py) -- {_REGEN_HINT}"]
    p = Path(toml_path)
    try:
        with p.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, ValueError):
        return []                     # unreadable/malformed is FieldProject.load's error, not ours
    return check(data, vocab=vocab, enforced=enforced)
