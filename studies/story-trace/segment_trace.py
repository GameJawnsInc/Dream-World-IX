"""THE STORY-WRITE TRACE's segment engine, shared by O1 and O2 (research/o2_design.md 1.2).

A SEGMENT is one stretch of the story played twice per run pair -- stock (S) against a verbatim fork chain (F) --
by one driver, traced, cut, digested and compared (studies/story-trace/PLAN.md, "O1"). O1's machinery lives here,
moved and parameterised; ``o1_opening`` keeps every public name as a thin wrapper, and the O1 regression gate
(``segment_regress.py``) proves its outputs byte-identical.

This part is the module's PURE helpers: the predictions' small readers, the FROZEN place of a row, the strict noise
matcher, the two cuts, the digest's row -> key map and the verdict. Everything here reads only its arguments
(``stock_lang`` and ``chain_from_campaign`` read the install / a campaign file when called).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))

from ff9mapkit import storytrace as T                                   # noqa: E402

SIDES = ("S", "F")
#: THROW: the exceptions a session fails on when thrown through the engine's story machinery (``WHERE``).
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "KeyNotFoundException"}
WHERE = ("EventEngine", "EBin", "StoryTrace", "HarnessAgent")
#: Where a run is taken before the soft reset back to the title: the Southern Ring hub, a field that gives control
#: at once (the F-REDEPLOY sessions warped there after New Game).
RECOVERY_FIELD = 4600

#: The eight fields of a ``storytrace.WriteKey`` a full-key noise pattern names, and their JSON types.
KEY_FIELDS = ("donor", "m", "src", "sid", "tag", "off", "target", "value")
_KEY_TYPES = {"donor": int, "m": int, "src": str, "sid": int, "tag": int, "off": int, "target": str, "value": int}
#: The metadata a full-key pattern may carry besides them (never matched on: ``ip``/``op`` are O2-KEYS's).
NOISE_META = ("ip", "op", "why")
#: O1's legacy noise shape: every key of ``target`` whose mode is NOT ``not_m``.
LEGACY_NOISE = frozenset({"not_m", "target", "why"})


# ======================================================================== the predictions' small readers
def members_of(pred: dict) -> dict:
    return {int(f): int(d) for f, d in pred["members"].items()}


def wkey(k: dict) -> T.WriteKey:
    return T.WriteKey(k["donor"], k["m"], k["src"], k["sid"], k["tag"], k["off"], k["target"], k["value"])


def chain_from_campaign(campaign) -> tuple:
    """``({fork id: donor}, {fork id: member name})`` of a built chain (its ``campaign.toml``)."""
    import tomllib
    d = tomllib.loads(Path(campaign).read_text(encoding="utf-8"))
    return ({int(f["id"]): int(f["source"]) for f in d["field"]}, {int(f["id"]): f["name"] for f in d["field"]})


def stock_lang(game=None):
    """``get(field id, lang) -> the stock .eb bytes | None`` over the install's event bundles, one per language."""
    from ff9mapkit.extract import EventBundle
    bundles: dict = {}

    def get(fid: int, lang: str) -> bytes | None:
        if lang not in bundles:
            bundles[lang] = EventBundle(game, lang=lang)
        return bundles[lang].eb_for_id(fid)
    return get


# ======================================================================== places, keys, noise
def place(fld: int, members: dict) -> int:
    """The FROZEN place of a field: a member's donor (by the predictions' members map, never the engine's ``don``),
    else the id itself. The S side passes no members: its place is its field."""
    return members.get(fld, fld)


def _check_pattern(p: dict) -> None:
    """A full-key noise pattern names EXACTLY the eight WriteKey fields, each a plain value of its type, plus at
    most the metadata ``ip``/``op``/``why``: anything else raises, so a typo is an error, never a wider match."""
    unknown = sorted(set(p) - set(KEY_FIELDS) - set(NOISE_META))
    missing = [f for f in KEY_FIELDS if f not in p]
    if unknown or missing:
        raise ValueError(f"noise pattern {p!r}: " + "; ".join(
            ([f"unknown field(s) {unknown}"] if unknown else []) + ([f"missing {missing}"] if missing else []))
            + f" -- a full-key pattern names exactly {', '.join(KEY_FIELDS)} (plus {', '.join(NOISE_META)})")
    for f in KEY_FIELDS:
        v = p[f]
        if isinstance(v, bool) or not isinstance(v, _KEY_TYPES[f]):
            raise ValueError(f"noise pattern {p!r}: {f} is {v!r}, not a plain {_KEY_TYPES[f].__name__} -- noise "
                             f"carries no operators (ranges, lists): only forbidden patterns do")


def key_matches(k: T.WriteKey, pattern: dict) -> bool:
    """Whether key ``k`` is exactly the full-key ``pattern`` (all eight fields equal, and ``k`` aligned). Strict:
    raises on a pattern that is not exactly that shape (4.6)."""
    _check_pattern(pattern)
    return k.aligned and all(getattr(k, f) == pattern[f] for f in KEY_FIELDS)


def is_noise(k: T.WriteKey, pred: dict) -> bool:
    """Whether ``k`` is registered noise. Two shapes, told apart by their key sets: O1's legacy
    ``{not_m, target, why}`` (every key of that target whose mode is not ``not_m`` -- so O1's battle-AI noise never
    covers a FIELD-mode key of the same byte), and the full-key form (:func:`key_matches`). Every pattern is
    checked first, so a malformed one raises even when another matches."""
    legacy = [set(n) == LEGACY_NOISE for n in pred["noise"]]
    for n, old in zip(pred["noise"], legacy):
        if not old:
            _check_pattern(n)
    return any((k.m != n["not_m"] and k.target == n["target"]) if old else key_matches(k, n)
               for n, old in zip(pred["noise"], legacy))


# ======================================================================== the cuts (frozen places)
def cut_at_end(rows: list, end_places, members: dict) -> tuple:
    """``(the run up to its first write in an end place, that row's line or None)``. Kept after the cut: the epoch
    rows (so the run still reads closed) and the epoch's closing ``c`` counts of every site whose place is NOT an
    end place (a site is per field, so none of those was written after the cut). Places are FROZEN
    (:func:`place`); with no member whose donor is an end place, this is O1's field rule exactly."""
    ends = set(end_places)
    at = next((r.line for r in rows if r.k in ("w", "r") and place(r.fld, members) in ends), None)
    if at is None:
        return rows, None
    return [r for r in rows if r.line < at or r.k == "e" or (r.k == "c" and place(r.fld, members) not in ends)], at


def cut_at_start(rows: list, start_place: int, members: dict) -> tuple:
    """``(kept, at, pre)``: the run from its START ROW -- the first ``w`` row whose (frozen) place is
    ``start_place``; never an ``r`` row, so residue landing in the start place cannot become the start and hide
    itself among the kept rows. Every row before it but the epoch rows is cut and returned in ``pre`` (line order),
    and so is each ``c`` row whose site was written only before it (field 70's). ``at`` is None when no ``w`` row
    stands in the start place: then nothing is cut (the caller's "never reached the start field")."""
    at = next((r.line for r in rows if r.k == "w" and place(r.fld, members) == start_place), None)
    if at is None:
        return list(rows), None, []
    before = [r for r in rows if r.line < at and r.k != "e"]
    gone = {r.site for r in before if r.k == "w"}
    kept_sites = {r.site for r in rows if r.k == "w" and r.line >= at}
    late = [r for r in rows if r.line >= at and r.k == "c" and r.site in gone and r.site not in kept_sites]
    cut = {id(r) for r in before} | {id(r) for r in late}
    return [r for r in rows if id(r) not in cut], at, before + late


# ======================================================================== a digest's rows -> its keys
def row_keys(d: T.RunDigest) -> dict:
    """``{(Row.site, value): WriteKey}`` from the digest's own Observed entries, its keys then its seam keys: every
    row the digest keyed, looked up with :func:`key_of` -- so a check reads each row on its JOINED key (donor through
    the members map, ``off`` as the digest aligned it), never its raw ``ip``. Keyed by value too: one site can store
    several values (a counter), each its own key. A row the digest did not key (a join failure, a masked site, a
    harness poke) has no entry."""
    out: dict = {}
    for keys in (d.keys, d.seam_keys):
        for k, o in keys.items():
            out.setdefault((o.row.site, k.value), k)
    return out


def key_of(rk: dict, r: T.Row) -> T.WriteKey | None:
    """The key :func:`row_keys` gave a ``w`` row (its ``new``) or a ``c`` row (its suppressed ``last``)."""
    return rk.get((r.site, r.new if r.k == "w" else r.last))


# ======================================================================== the verdict
def verdict(checks: list) -> str:
    fails = [w.split(":")[0] for ok, w, _d in checks if ok is False]
    voids = [w.split(":")[0] for ok, w, _d in checks if ok is None]
    if fails:
        return "NOT PROVEN: " + ", ".join(fails)
    if voids:
        return "VOID: " + ", ".join(voids)
    return "PROVEN"
