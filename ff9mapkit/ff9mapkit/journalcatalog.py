"""The full-fidelity ENTRY catalog -- the walkthrough-shaped journal's data layer.

:mod:`journal` is the COUNTER catalog (48 aggregate rows, T1b, code). This module is the second
layer the frozen schema defines (studies/completion-journal/SCHEMA.md): one row per obtainable
THING, keyed on the engine predicate that proves the player has it, authored in
``data/journal_catalog.toml`` and machine-seeded from the treasure_join v2 reward-event atlas
(studies/completion-journal/research/treasure_join.py -- 410 events over 410 distinct latch bits,
mined from 818 real fields' ``.eb``).

THE ONE LAW OVER BOTH LAYERS: every displayable fact is either derivable from a declared
predicate, or explicitly labelled NOT TRACKED -- never silently omitted, never invented.

THE EIGHT SCHEMA LAWS, and where each is enforced (a law in a docstring is a wish -- CLAUDE.md
s7 -- so each lint below is provable-breakable in tests/test_journalcatalog.py):

  1. exactly ONE predicate per row                       -> :func:`lint_catalog` (L1)
  2. atlas exhaustiveness, both directions               -> :func:`lint_against_atlas` (research-
     time: the atlas JSON is derived from the user's own install and gitignored; the shipped half
     -- no duplicate bits, bits inside the engine's story range -- is in :func:`lint_catalog` (L2)
  3. a catch-up bit is REFUSED as a predicate            -> :func:`lint_catalog` (L3) against
     :data:`CATCHUP_BITS`
  4. missable verdicts gate on confidence                -> :func:`lint_catalog` (L4) validates the
     column; the RENDERER may print "PERMANENTLY MISSED" only for ``confidence = "owner"``
  5. runtime name resolution                             -> the in-game renderer publishes the item
     id into a gMesValue slot and tags ``[ITEM=slot]`` (NGUIText.cs:87-90 ->
     ``ETb.GetItemName``, ETb.cs:237-246 -- regular/important/card off the LIVE tables, so a
     Moguri rename shows the Moguri name). The lint half (L5): the id must be in range for its
     pool, and a title may not bake the stock name next to an id-keyed row.
  6. text budgets are measured, not inherited            -> :func:`lint_catalog` (L6) measures
     title/detail with :func:`content.text.measure` against the T1b wrap datum
     (:data:`TITLE_BUDGET` / :data:`DETAIL_BUDGET`) until the owed pane measurement lands
  7. totals are per run_mode                             -> structural half in :func:`lint_catalog`
     (L7: an ``exclusive_group`` of one is a typo); the totals math ships with the totals renderer
  8. ``provenance = "crosscheck"`` rows never ship text  -> :func:`lint_catalog` (L8)

Provenance: the catalog carries OUR original prose and engine-derived integers (bit indices, item
ids, TH points). No Square-Enix text, no third-party guide text -- a guide may only ever CONFIRM a
census fact (the owner's ruling, PLAN.md SS5), which is what the ``crosscheck`` provenance tag and
L8 make unrepresentable to violate silently.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field as _field
from pathlib import Path

from .content import text as _text

# ============================ engine ranges (transcribed, with their file:line) ============================
#: gEventGlobal is Byte[2048] (EventState.cs) -> valid GLOB bit indices 0..16383.
GLOB_BIT_MAX = 16383

#: Treasure-Hunter-scored latch band, EventState.cs:62-70: bytes 896-960 + 966-975. A catalog row may
#: cite bits OUTSIDE these bands (16 atlas events do -- e.g. the Chocobo-forest key item at bit 1084);
#: the band is data for renderers ("counts toward the rank"), not a validity gate.
TH_BANDS = ((896 * 8, 960 * 8 + 7), (966 * 8, 975 * 8 + 7))

#: LAW 3's refusal list: bits some field's Main_Init MASS-SETS under a ScenarioCounter guard (the
#: 3818 class) -- the engine "catches up" a late-joining save, so the bit going high does not prove
#: the player DID the thing. Derived by treasure_join v2.2 (its ``catchup_bits`` output, 33 bits,
#: regenerable from the user's own install); transcribed here because the shipped lint must run
#: without the research artifact. A row for one of these can only be ``manual`` with the reason.
CATCHUP_BITS = frozenset((
    3228, 3229, 3230, 3231, 3235, 3242, 3243, 3244, 3245, 3246, 3247, 3248, 3249, 3250,
    3251, 3252, 3253, 3254, 3255, 3262, 3263, 3816, 3817, 3818, 3819, 3823, 3825, 3826,
    3827, 3828, 3829, 3830, 3831,
))

#: The unified item-id space ``ETb.GetItemName`` resolves (ETb.cs:237-246 via ff9item):
#: regular 0..255, important (key) 256..511, cards 512.. -- one [ITEM=slot] tag covers all three.
ITEM_ID_MAX = 611

# ============================ vocabulary (SCHEMA.md, frozen v1) ============================
PREDICATES = ("latch", "window", "inventory", "counter", "manual")
CATEGORIES = ("treasure", "keyitem", "card", "chocograph", "minigame", "mognet", "story",
              "party", "combat", "meta")
PROVENANCES = ("engine", "census", "owner", "crosscheck")
VERIFIES = ("unverified", "save-diffed", "playtested")
CONFIDENCES = ("derived", "owner", "none")

#: LAW 6's ceilings -- the T1b wrap datum (content/text.py:500 DEFAULT_WRAP_WIDTH 28.0; the
#: dashboard designs lines to 26.0). Pinned as the schema requires until the owed live pane
#: measurement (PLAN.md SS7.2 Q6) replaces them.
TITLE_BUDGET = 26.0
DETAIL_BUDGET = 26.0

_CATALOG_PATH = Path(__file__).resolve().parent / "data" / "journal_catalog.toml"


# ============================ the rows ============================
@dataclass(frozen=True)
class Section:
    """One walkthrough-spine section -- OUR arrangement of the game's own order, joined to
    ScenarioCounter by the curated anchor table (flags.py SCENARIO_MILESTONES; sc values are
    anchors, never hand-invented). ``sc_leave == 0`` is the open sentinel for side content."""
    id: str
    disc: int                 # 1-4, or 0 for side content
    title: str
    sc_enter: int
    sc_leave: int
    side: bool = False
    areas: tuple = ()         # manifest area ids; filled by the generator pass, not by hand
    objective: str = ""       # the main story's "what you are doing now", imperative, OUR prose.
                              # Empty -> the section TITLE is the honest fallback (a place name is a
                              # direction, not an invention); authored section by section with the
                              # prose pass, same as entry detail.


@dataclass(frozen=True)
class Entry:
    """One obtainable/completable THING. Exactly one predicate field is set (LAW 1)."""
    id: str
    section: str
    category: str
    title: str = ""           # OUR prose; empty for an id-keyed row whose display name IS the item
    detail: str = ""          # OUR prose, original wording
    # --- the five predicate kinds (exactly one set) ---
    latch: "int | None" = None            # a monotone GLOB once-bit
    window: "tuple | None" = None         # (on_bit, off_bit) -- the set-then-clear population
    inventory: "int | None" = None        # unified item id -- the item IS the latch (B_HAVE_ITEM)
    counter: str = ""                     # delegate to a journal.ROWS id
    manual: str = ""                      # NOT TRACKED -- the reason, rendered as such
    # --- optional columns ---
    item: "int | None" = None             # unified item id; display name resolves at RUNTIME (LAW 5)
    gil: "int | None" = None              # a gil reward's amount (literal text; no id to resolve)
    th: int = 0                           # Treasure-Hunter points this event scores (engine bands)
    missable: "dict | None" = None        # {close_sc: int, confidence: derived|owner|none} (LAW 4)
    exclusive_group: str = ""
    run_mode: str = ""
    provenance: str = "census"
    source: str = ""                      # the derivation, e.g. "treasure_join v2 bit 7171"
    verify: str = "unverified"

    def predicate(self) -> str:
        """Which predicate kind this row declares (LAW 1 guarantees exactly one after lint)."""
        kinds = [k for k, v in (("latch", self.latch), ("window", self.window),
                                ("inventory", self.inventory), ("counter", self.counter),
                                ("manual", self.manual)) if v not in (None, "")]
        return kinds[0] if len(kinds) == 1 else "|".join(kinds) or "none"


# ============================ loading ============================
@dataclass(frozen=True)
class Deferred:
    """A DECLARED omission -- an atlas event whose rooms overlap an authored section but which
    belongs to a later one (a different story visit of the same room, a shop not yet open). LAW 2
    says nothing is silently omitted; this is the non-silent form. A deferred bit that later gains
    a real row is a STALE deferral and the lint refuses it."""
    bit: int
    why: str


def load_catalog(path: "Path | None" = None) -> tuple:
    """``(sections, entries, deferred)`` from the shipped ``data/journal_catalog.toml`` (or ``path``)."""
    raw = tomllib.loads(Path(path or _CATALOG_PATH).read_text(encoding="utf-8"))
    sections = tuple(
        Section(id=s["id"], disc=int(s["disc"]), title=s["title"],
                sc_enter=int(s["sc"]["enter"]), sc_leave=int(s["sc"]["leave"]),
                side=bool(s.get("side", False)), areas=tuple(s.get("areas", ())),
                objective=s.get("objective", ""))
        for s in raw.get("section", ()))
    entries = []
    for e in raw.get("entry", ()):
        win = e.get("window")
        entries.append(Entry(
            id=e["id"], section=e["section"], category=e["category"],
            title=e.get("title", ""), detail=e.get("detail", ""),
            latch=e.get("latch"), window=(int(win["on"]), int(win["off"])) if win else None,
            inventory=e.get("inventory"), counter=e.get("counter", ""), manual=e.get("manual", ""),
            item=e.get("item"), gil=e.get("gil"), th=int(e.get("th", 0)),
            missable=e.get("missable"), exclusive_group=e.get("exclusive_group", ""),
            run_mode=e.get("run_mode", ""), provenance=e.get("provenance", "census"),
            source=e.get("source", ""), verify=e.get("verify", "unverified")))
    deferred = tuple(Deferred(bit=int(d["bit"]), why=d.get("why", ""))
                     for d in raw.get("deferred", ()))
    return sections, tuple(entries), deferred


# ============================ the lint (LAWS 1-8, structural halves) ============================
def lint_catalog(sections, entries, deferred=()) -> list:
    """Every structural law over the loaded catalog. Returns problem strings; [] is a pass.

    The atlas-join half of LAW 2 lives in :func:`lint_against_atlas` because the atlas artifact is
    derived from the user's own install; everything HERE runs from the wheel alone."""
    probs = []
    for d in deferred:
        if not d.why:
            probs.append(f"deferred bit {d.bit}: LAW 2 -- a declared omission must say why")
    sec_ids = [s.id for s in sections]
    for dup in {i for i in sec_ids if sec_ids.count(i) > 1}:
        probs.append(f"section {dup}: duplicate id")
    sec_by_id = {s.id: s for s in sections}
    for s in sections:
        if s.side:
            if s.disc != 0:
                probs.append(f"section {s.id}: side content is disc 0, not {s.disc}")
        elif not (1 <= s.disc <= 4):
            probs.append(f"section {s.id}: disc {s.disc} out of range 1-4")
        if s.sc_leave != 0 and s.sc_leave <= s.sc_enter:
            probs.append(f"section {s.id}: sc window {s.sc_enter}..{s.sc_leave} is empty")
        # LAW 6 over the next-objective ladder: every MAIN section's rendered row (the authored
        # objective, or the title fallback) must fit the window line -- the ladder renders whichever
        # exists, so both are budgeted here, not at render time.
        if not s.side:
            row = s.objective or s.title
            if _text.measure(row) > DETAIL_BUDGET:
                probs.append(f"section {s.id}: LAW 6 -- objective row measures "
                             f"{_text.measure(row):.1f}u > {DETAIL_BUDGET}u: {row!r} (author a "
                             f"shorter `objective`)")

    ids, bits = [], {}
    for e in entries:
        ids.append(e.id)
        # LAW 1 -- exactly one predicate.
        kinds = e.predicate()
        if kinds == "none" or "|" in kinds:
            probs.append(f"entry {e.id}: LAW 1 -- exactly one predicate required, got {kinds!r}")
        if e.section not in sec_by_id:
            probs.append(f"entry {e.id}: unknown section {e.section!r}")
        if e.category not in CATEGORIES:
            probs.append(f"entry {e.id}: unknown category {e.category!r}")
        if e.provenance not in PROVENANCES:
            probs.append(f"entry {e.id}: unknown provenance {e.provenance!r}")
        if e.verify not in VERIFIES:
            probs.append(f"entry {e.id}: unknown verify {e.verify!r}")
        # LAW 2, shipped half -- bits valid and unique across the whole catalog (EventDB-style:
        # a bit is one event; two rows on one bit is either a split-bit event needing ONE shared
        # row, or a typo).
        for b in ((e.latch,) if e.latch is not None else ()) + (e.window or ()):
            if not (0 <= int(b) <= GLOB_BIT_MAX):
                probs.append(f"entry {e.id}: bit {b} outside gEventGlobal (0..{GLOB_BIT_MAX})")
            elif b in bits:
                probs.append(f"entry {e.id}: LAW 2 -- bit {b} already claimed by {bits[b]}")
            else:
                bits[b] = e.id
        # LAW 3 -- a catch-up bit cannot prove the player did the thing.
        for b in ((e.latch,) if e.latch is not None else ()) + (e.window or ()):
            if b in CATCHUP_BITS:
                probs.append(f"entry {e.id}: LAW 3 -- bit {b} is a Main_Init catch-up bit "
                             f"(the 3818 class); only a `manual` row may reference it")
        # LAW 4 -- the missable column's vocabulary.
        if e.missable is not None:
            conf = e.missable.get("confidence")
            if conf not in CONFIDENCES:
                probs.append(f"entry {e.id}: LAW 4 -- missable.confidence {conf!r} not in "
                             f"{CONFIDENCES}")
            if conf != "none" and not isinstance(e.missable.get("close_sc"), int):
                probs.append(f"entry {e.id}: LAW 4 -- missable.close_sc must be an int SC anchor")
        # LAW 5 -- id-keyed display names resolve at runtime.
        for label, iid in (("item", e.item), ("inventory", e.inventory)):
            if iid is None:
                continue
            if not (0 <= int(iid) <= ITEM_ID_MAX):
                probs.append(f"entry {e.id}: {label} id {iid} outside the unified item space "
                             f"(0..{ITEM_ID_MAX})")
            elif iid <= 255:
                from ._itemdb import ITEMS
                stock = ITEMS.get(int(iid), "")
                if stock and e.title.replace(" ", "").lower() == stock.lower():
                    probs.append(f"entry {e.id}: LAW 5 -- title {e.title!r} bakes the stock name "
                                 f"of item {iid}; the renderer resolves it live ([ITEM=] tag)")
        if e.gil is not None and not (0 < int(e.gil) < 10_000_000):
            probs.append(f"entry {e.id}: gil {e.gil} out of range")
        # LAW 6 -- measured budgets.
        for label, txt, budget in (("title", e.title, TITLE_BUDGET),
                                   ("detail", e.detail, DETAIL_BUDGET)):
            if txt and _text.measure(txt) > budget:
                probs.append(f"entry {e.id}: LAW 6 -- {label} measures "
                             f"{_text.measure(txt):.1f}u > {budget}u budget: {txt!r}")
        # LAW 8 -- crosscheck rows never ship text.
        if e.provenance == "crosscheck" and (e.title or e.detail):
            probs.append(f"entry {e.id}: LAW 8 -- provenance=crosscheck may not carry prose")
    for dup in {i for i in ids if ids.count(i) > 1}:
        probs.append(f"entry {dup}: duplicate id")
    # LAW 7, structural half -- an exclusive_group of one is a typo.
    groups = {}
    for e in entries:
        if e.exclusive_group:
            groups.setdefault(e.exclusive_group, []).append(e.id)
    for g, members in groups.items():
        if len(members) < 2:
            probs.append(f"exclusive_group {g!r}: LAW 7 -- only one member ({members[0]}); "
                         f"a group of one excludes nothing")
    return probs


def lint_against_atlas(entries, atlas: dict, deferred=()) -> list:
    """LAW 2's atlas join, both directions, SCOPED to what the catalog covers -- run at research
    time against ``treasure_join.json`` (regenerated from the user's own install; gitignored).

      direction 1: every catalog ``latch``/``window`` bit exists in the atlas (a bit no script
                   writes is a typo caught here, not in a playtest);
      direction 2: every atlas event whose fields are ALL covered by the catalog's own entries
                   appears as exactly one row OR as a declared ``[[deferred]]`` omission -- so
                   finishing a room means finishing it, while sections not yet authored stay out
                   of scope instead of failing the whole run.

    A stale deferral (a deferred bit that HAS a row, or that the atlas does not know) is refused,
    so the deferred list can only shrink toward the finished catalog, never rot."""
    probs = []
    by_bit = {ev["bit"]: ev for ev in atlas["events"]}
    covered_fields = set()
    for e in entries:
        for b in ((e.latch,) if e.latch is not None else ()) + (e.window or ()):
            ev = by_bit.get(b)
            if ev is None:
                probs.append(f"entry {e.id}: LAW 2 -- bit {b} not in the reward-event atlas")
            else:
                covered_fields.update(ev["fields"])
    have = {b for e in entries for b in ((e.latch,) if e.latch is not None else ())}
    have |= {b for e in entries for b in (e.window or ())}
    deferred_bits = {d.bit for d in deferred}
    for d in deferred:
        if d.bit in have:
            probs.append(f"deferred bit {d.bit}: STALE -- the catalog now carries a row for it; "
                         f"delete the deferral")
        elif d.bit not in by_bit:
            probs.append(f"deferred bit {d.bit}: not in the reward-event atlas -- a deferral for "
                         f"an event that does not exist is a typo")
    for ev in atlas["events"]:
        if (ev["fields"] and set(ev["fields"]) <= covered_fields
                and ev["bit"] not in have and ev["bit"] not in deferred_bits):
            probs.append(f"atlas bit {ev['bit']} ({'/'.join(sorted(set(ev['names'])))}): LAW 2 -- "
                         f"its rooms are covered by the catalog but the event has no row and no "
                         f"declared deferral")
    return probs


# ============================ accessors ============================
def entries_for(section_id: str, *, catalog=None) -> tuple:
    """The section's entries in authored (walkthrough) order."""
    sections, entries, _deferred = catalog if catalog is not None else load_catalog()
    return tuple(e for e in entries if e.section == section_id)


def render_patch(*, catalog=None) -> str:
    """The ``JournalPatch.txt`` body -- the WHOLE catalog as JSON for the s81+ JournalUI menu
    screen (sections + entries + deferred), so the in-game menu and this module read one truth
    and catalog authoring never rebuilds the DLL.

    Emitted deterministically (sorted keys, fixed indent) so the deploy artifact diffs cleanly
    and a golden test can pin emitted == loaded. Display names stay LAW-5 runtime: an entry
    carries only its unified item ID -- the DLL renders the name off the live tables."""
    import json
    sections, entries, deferred = catalog if catalog is not None else load_catalog()
    doc = {
        "version": 1,
        "sections": [
            {"id": s.id, "disc": s.disc, "title": s.title, "objective": s.objective,
             "enter": s.sc_enter, "leave": s.sc_leave, "side": s.side}
            for s in sections],
        "entries": [
            {"id": e.id, "section": e.section, "category": e.category, "title": e.title,
             "detail": e.detail, "latch": e.latch,
             "window": list(e.window) if e.window else None,
             "inventory": e.inventory, "counter": e.counter, "manual": e.manual,
             "item": e.item, "gil": e.gil, "th": e.th, "missable": e.missable,
             "verify": e.verify}
            for e in entries],
        "deferred": [{"bit": d.bit, "why": d.why} for d in deferred],
    }
    return json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def main_story_ladder(*, catalog=None) -> tuple:
    """``(enters, rows)`` for the main story's NEXT-OBJECTIVE ladder -- the ONE source both the
    offline reader and the in-game expression/table are generated from, so an index computed by
    one always names the row the other renders.

      ``enters``: the main-path sections' ``sc_enter`` anchors, ascending (side content excluded --
      it has no place on a linear clock);
      ``rows``: one display string per section, same order -- the authored ``objective`` when the
      prose pass has reached that section, else the section TITLE (a place name is an honest
      direction, never an invention).

    The current-section index is ``sum(SC >= enters[i] for i in 1..N-1)`` -- the rank-ladder
    expression class (`journal._rank_ladder`, in-game proven on the Treasure-Hunter rank), with the
    FIRST enter excluded so a fresh save (SC below the first anchor) indexes row 0 instead of -1.
    ScenarioCounter is not strictly monotonic (7 real fields decrement it -- journal.ROWS
    story.scenario's note), so the index is "where the story clock stands", not a progress bar,
    and nothing here renders an N/44."""
    sections, _entries, _deferred = catalog if catalog is not None else load_catalog()
    main = sorted((s for s in sections if not s.side), key=lambda s: s.sc_enter)
    return (tuple(s.sc_enter for s in main),
            tuple(s.objective or s.title for s in main))
