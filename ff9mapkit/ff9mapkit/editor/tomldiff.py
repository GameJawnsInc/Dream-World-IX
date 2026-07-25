"""A SEMANTIC diff of two kit tomls -- "what changed since the last deploy?", in the kit's own vocabulary.

WHY THIS EXISTS. The loudest law in this project's brief is *"One change per in-game test. When a build
breaks, we need to know which edit did it."* -- and nothing in the toolkit could answer **which edit**. The
GUI had no surface that said what changed since the last deploy, so obeying the law meant remembering it by
hand across an edit session. This module is the part that can be reasoned about offline: pure, tk-free,
Qt-free, no I/O. The GUI wires it to a snapshot taken at deploy time.

NOT A TEXT DIFF, and not a rollback. Text diffs of a toml report reformatting, comment edits and key
reordering as changes, and report ONE deleted array entry as N changed entries. And rollback is git's job --
this repo has git and the user uses it; the scarce thing here is not storage, it is ATTENTION at the moment
of a playtest.

THE WHOLE PROBLEM IS ARRAY IDENTITY. A field.toml is mostly arrays of tables (`[[npc]]`, `[[gateway]]`,
`[[cutscene]]`, ~38 kinds and growing). Match those by INDEX and deleting npc #0 reports "npc[0] changed,
npc[1] changed, npc[2] removed" -- three rows for one edit, a text diff wearing a schema's clothes. Match
them by IDENTITY and it reports one removal.

SO THE KEY IS DERIVED FROM THE DATA, NOT DECLARED IN A TABLE. The first design was an ordered list of
candidate key fields; measured against every kit toml in the repo it missed `requires_flag` (the only thing
separating two gateways to the same field) and `give_folklore` (five events distinguished only by their
payload) -- **because a gating list rots, and this kit grows a new block most weeks.** The fix inverts it:
every field present on every entry is ELIGIBLE, the preference list only RANKS the ones that already work,
and the smallest unique key wins. Measured over the repo's 27 kit tomls / 34 array kinds / 41 multi-entry
arrays: **37 of 41 identified (90.2%), zero ambiguity**, and the only remainder is `cutscene.steps` --
an ORDERED SCRIPT, where a step's identity IS its position and index is the right answer.

TWO HONEST LIMITS, both stated rather than hidden:
  * **A rename reads as a remove + an add** when the renamed field is the key. That is inherent to matching
    by identity (git has the same problem with files) and :func:`diff` labels the pair so a reader can see
    it, rather than pretending to detect intent.
  * **The key is derived from the UNION of both sides.** It has to be: the census found `gateway` keyed by
    `to` in one file and by `requires_flag` in another, so a key derived from the old side alone can stop
    being unique on the new side (add a second gateway to the same field and `to` collides).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field as _dc_field

# Ranking ONLY. A field absent from this tuple is still eligible as a key -- it just sorts last. The order
# is "what reads best as a diff row's label", since the key doubles as the row's name (`npc "Boletta"`).
_PREFER = ("name", "id", "to", "label", "title", "image", "field", "flag", "key", "result", "text")

# Arrays whose identity IS their order, so index is correct and a derived key would be wrong. Suffix-matched
# on the dotted path. `steps` is the measured case (cutscene.steps, 4 occurrences in the repo); a beat's
# identity in a script is where it sits in the script, and keying it by `actor` would report a re-ordered
# scene as a pile of unrelated edits.
_ORDERED = ("steps",)

ADDED, REMOVED, CHANGED = "added", "removed", "changed"


@dataclass(frozen=True)
class Change:
    """One human-readable difference. ``where`` is the kit-vocabulary location, not a JSON pointer."""

    kind: str                 # ADDED | REMOVED | CHANGED
    where: str                # 'camera.pitch' | 'npc name="Boletta"' | 'npc name="Boletta" -> pos'
    old: object = None
    new: object = None
    detail: tuple = _dc_field(default=())    # for an added/removed entry: a few of its own fields, for context
    # WHICH FILE, kept OUT of `where` on purpose. Folding it in gave rows like
    # `A/A.field.toml.camera.pitch`, and worse, it could not survive an array label (which is rebuilt from
    # the array's own name). Separate, a multi-file project's rows GROUP by file in the UI and a single-file
    # project's rows simply have none.
    file: str = ""

    def render(self, *, with_file: bool = True) -> str:
        """One line, as a reader sees it. Values are shortened -- a diff row is a label, not a payload."""
        # A FILE-LEVEL change carries the file and no path within it, so it must not render a dangling
        # arrow ("B.field.toml → added"). Empty `where` means the file itself IS the subject.
        head = (f"{self.file} → " if self.where else self.file) if (with_file and self.file) else ""
        if self.kind == CHANGED:
            return f"{head}{self.where}: {_short(self.old)} → {_short(self.new)}"
        verb = "added" if self.kind == ADDED else "removed"
        bits = "  ".join(f"{k}={_short(v)}" if k else _short(v) for k, v in self.detail)
        subject = f"{head}{self.where}".rstrip()
        return (f"{subject} {verb}" + (f"  ({bits})" if bits else "")).lstrip()


def _short(v, limit: int = 44) -> str:
    """A value as a label. Long strings and big arrays are elided -- the point is which knob moved."""
    if isinstance(v, str):
        one = v.replace("\n", " ⏎ ")
        return f'"{one[:limit - 1]}…"' if len(one) > limit else f'"{one}"'
    if isinstance(v, bool) or v is None:
        return str(v)
    if isinstance(v, (int, float)):
        return f"{v}"
    if isinstance(v, list):
        if len(v) > 4 or any(isinstance(x, (list, dict)) for x in v):
            return f"[{len(v)} values]"
        return "[" + ", ".join(_short(x, 12) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}={_short(x, 12)}" for k, x in list(v.items())[:3]) + "}"
    return str(v)


def _is_table_array(v) -> bool:
    return isinstance(v, list) and bool(v) and all(isinstance(e, dict) for e in v)


def _repr_key(entry, combo):
    """A hashable identity for ``entry`` under ``combo``. ``repr`` so nested arrays (a zone quad) work."""
    return tuple(repr(entry.get(c)) for c in combo)


def derive_key(old_entries: list, new_entries: list) -> tuple | None:
    """The smallest field-set that uniquely identifies every entry on BOTH sides, or ``None`` for index.

    Derived from the UNION because a key unique on one side can collide on the other (measured: two
    gateways to the same ``to``). Preference only breaks ties among keys that already work.
    """
    both = list(old_entries) + list(new_entries)
    if not both:
        return None
    fields = sorted({k for e in both for k in e},
                    key=lambda f: (_PREFER.index(f) if f in _PREFER else len(_PREFER), f))
    eligible = [f for f in fields if all(f in e for e in both)]
    for n in (1, 2):                      # smallest key wins; the corpus never needs deeper than a pair
        for combo in itertools.combinations(eligible, n):
            if (len({_repr_key(e, combo) for e in old_entries}) == len(old_entries)
                    and len({_repr_key(e, combo) for e in new_entries}) == len(new_entries)):
                return combo
    return None


def _label(where: str, entry: dict, combo: tuple | None, idx: int) -> str:
    """How an array entry names itself: `npc name="Boletta"` / `cutscene flag=8712 → steps #2`.

    Takes the FULL path, not just the array's own name -- rebuilding from the name dropped every parent
    segment, so a nested array's rows silently lost their context (measured on a campaign's member file).
    """
    if combo is None:
        return f"{where} #{idx}"
    vals = "  ".join(f"{c}={_short(entry.get(c), 24)}" for c in combo)
    return f"{where} {vals}"


def _context(entry: dict, combo: tuple | None, limit: int = 3) -> tuple:
    """A few of an added/removed entry's OWN fields, so the row says what the thing was."""
    skip = set(combo or ())
    out = []
    for k in sorted(entry, key=lambda f: (_PREFER.index(f) if f in _PREFER else len(_PREFER), f)):
        if k in skip:
            continue
        out.append((k, entry[k]))
        if len(out) >= limit:
            break
    return tuple(out)


def _join(where: str, k: str) -> str:
    """Compose a path segment. A TABLE path joins with a dot (`camera.frame.back`); an ARRAY-ENTRY label
    joins with an arrow (`npc name="Boletta" → pos`), because `npc name="Boletta".pos` reads as gibberish.
    The two are told apart by a space: a toml key cannot contain one, and every entry label does."""
    if not where:
        return k
    return f"{where} → {k}" if " " in where else f"{where}.{k}"


def diff(old, new, *, where: str = "") -> list[Change]:
    """Every semantic difference between two parsed tomls (or two sub-trees), depth-first, stable order."""
    out: list[Change] = []
    if isinstance(old, dict) and isinstance(new, dict):
        for k in list(old) + [k for k in new if k not in old]:
            here = _join(where, k)
            if k not in new:
                out.append(Change(REMOVED, here, old=old[k], detail=_leaf_detail(old[k])))
            elif k not in old:
                out.append(Change(ADDED, here, new=new[k], detail=_leaf_detail(new[k])))
            else:
                out.extend(diff(old[k], new[k], where=here))
        return out

    if _is_table_array(old) and _is_table_array(new):
        return _diff_table_array(old, new, where)

    if old != new:
        out.append(Change(CHANGED, where, old=old, new=new))
    return out


def _leaf_detail(v) -> tuple:
    """Context for a whole table/array that appeared or vanished (so the row is not just a path)."""
    if isinstance(v, dict):
        return _context(v, None)
    if _is_table_array(v):
        return (("entries", len(v)),)
    return ()


def _diff_table_array(old: list, new: list, where: str) -> list[Change]:
    """Array-of-tables, matched by derived identity -- or by index for an ordered script."""
    kind = where.replace(" → ", ".").rsplit(".", 1)[-1]
    combo = None if kind in _ORDERED else derive_key(old, new)
    out: list[Change] = []

    if combo is None:                                     # ordered (or unkeyable): position IS identity
        for i in range(max(len(old), len(new))):
            if i >= len(new):
                out.append(Change(REMOVED, _label(where, old[i], None, i), old=old[i],
                                  detail=_context(old[i], None)))
            elif i >= len(old):
                out.append(Change(ADDED, _label(where, new[i], None, i), new=new[i],
                                  detail=_context(new[i], None)))
            else:
                out.extend(diff(old[i], new[i], where=_label(where, old[i], None, i)))
        return out

    o = {_repr_key(e, combo): e for e in old}
    n = {_repr_key(e, combo): e for e in new}
    for i, e in enumerate(old):                           # removals + modifications, in the OLD order
        k = _repr_key(e, combo)
        if k not in n:
            out.append(Change(REMOVED, _label(where, e, combo, i), old=e, detail=_context(e, combo)))
        else:
            out.extend(diff(e, n[k], where=_label(where, e, combo, i)))
    for i, e in enumerate(new):                           # then additions, in the NEW order
        if _repr_key(e, combo) not in o:
            out.append(Change(ADDED, _label(where, e, combo, i), new=e, detail=_context(e, combo)))
    return out


def summarize(changes: list) -> str:
    """``'3 changes'`` / ``'1 change'`` / ``'no changes'`` -- the chip's text, in one place so it cannot drift."""
    n = len(changes)
    return "no changes" if not n else ("1 change" if n == 1 else f"{n} changes")
