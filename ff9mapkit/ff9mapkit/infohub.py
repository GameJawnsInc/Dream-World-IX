"""The Info Hub spine -- a UI-agnostic discovery API over the kit's reference catalogs + named archetypes.

This is the reusable CORE every Info Hub frontend sits on -- a standalone viewer today, the Campaign
Editor suite tomorrow, even a Blender panel -- so the expensive part (the data logic) is written and
tested once, independent of any UI. It answers three authoring questions:

  * ``browse(query)``  -> WHAT exists by this name? (search every catalog + archetype table at once)
  * ``detail(entry)``  -> WHAT is this exactly? (model, animations, composite parts, the line to author it)
  * ``snippet(entry)`` -> HOW do I drop it into a ``field.toml``? (the ``[[npc]]`` / ``[[prop]]`` block)

Pure-offline + provenance-clean: it reads only the baked catalogs (:mod:`catalog`) and the curated
archetype tables -- no game install. Game-dependent extras stay OUT of the spine and arrive via hooks:
:func:`detail` takes an optional ``usage_fn`` for "where does this appear in real FF9?", and a frontend
wires its own in-game *preview* by feeding the selection back to the gallery builders. Everything here is
a dataclass -- trivially rendered by Tkinter, a web view, or the CLI, and JSON-serializable.
"""
from __future__ import annotations

import re

from dataclasses import dataclass, field as _dc_field
from typing import Callable, Optional

from . import archetypes as _arch
from . import catalog as _cat
from . import prop_archetypes as _props
from .content.npc import PRESETS as _CHAR_PRESETS    # vivi / zidane -- explicit, byte-golden

# the kinds the Info Hub indexes, listed in browse priority order (curated/named first, raw last)
KINDS = ("archetype", "creature", "composite", "prop", "model", "item", "scene")


@dataclass(frozen=True)
class Entry:
    """One browsable result -- the unit a frontend lists and acts on. ``name`` is what you type to use it;
    ``model`` is the GEO model behind it (when any); ``ident`` is the numeric id for a model/item/scene."""
    kind: str
    name: str
    model: Optional[str] = None
    summary: str = ""
    ident: Optional[int] = None


@dataclass
class Detail:
    """The rich record for one entry -- everything an authoring detail pane shows."""
    name: str
    kind: str
    model: Optional[str] = None
    model_id: Optional[int] = None
    facts: list = _dc_field(default_factory=list)      # [(label, value)] -- generic key facts
    movement: Optional[dict] = None                    # {stand,walk,run,left,right} iff NPC-ready
    anims: list = _dc_field(default_factory=list)      # [(action, anim_id)] -- the full gesture list
    parts: list = _dc_field(default_factory=list)      # composite parts [(model_name, pose, dx, dz)]
    aliases: list = _dc_field(default_factory=list)    # other names mapping to the same model
    locations: Optional[list] = None                   # [(field_id, name)] iff a usage_fn was supplied
    snippet: str = ""


# ----------------------------------------------------------------- helpers ---
def _model_of_archetype(name) -> Optional[str]:
    """The GEO model NAME an archetype/creature maps to (or None). Cheap -- a direct model lookup, NOT
    ``archetypes.resolve`` (which also scans every animation to build the movement set)."""
    key = str(name).strip().lower()
    if key in _CHAR_PRESETS:
        model = _CHAR_PRESETS[key][0]
    else:
        spec = _arch.ARCHETYPES.get(key) or _arch.CREATURES.get(key)
        model = spec["model"] if spec else None
    m = _cat.model(model) if model is not None else None
    return m.name if m else None


_DESC_CACHE: Optional[dict] = None
_DESC_RE = re.compile(r'^\s*"([a-z0-9_]+)"\s*:\s*[\{\[].*?#\s*(.+)$')


def _descriptions() -> dict:
    """``{name: short description}`` parsed from the archetype/prop source comments (built once). The rich
    "what is it" text already lives in trailing comments (shelf -> 'a Dali ... shelf / box'; cask ->
    'a "CaSK" / barrel'); this surfaces it for SEARCH + display without migrating it into the data."""
    global _DESC_CACHE
    if _DESC_CACHE is None:
        d: dict = {}
        for mod in (_arch, _props):
            try:
                src = open(mod.__file__, encoding="utf-8").read()
            except OSError:
                continue
            for line in src.splitlines():
                mm = _DESC_RE.match(line)
                if mm:
                    d.setdefault(mm.group(1), mm.group(2).strip())
        _DESC_CACHE = d
    return _DESC_CACHE


def _build_entries() -> list:
    """Every indexed :class:`Entry`, in :data:`KINDS` order (built once, then cached). Each summary folds
    in the comment DESCRIPTION + (for raw models) the friendly archetype names that use it, so search
    matches what a thing IS ('box' -> shelf, 'zidane' -> the ZDN model), not just its cryptic GEO token."""
    desc = _descriptions()
    by_model = _model_names_index()
    out = []
    for name in sorted(set(_CHAR_PRESETS) | set(_arch.ARCHETYPES)):     # archetypes (playable + NPC types)
        mname = _model_of_archetype(name)
        m = _cat.model(mname) if mname else None
        role = m.kind if m else "npc"
        out.append(Entry("archetype", name, mname, f"{role} NPC -- {desc.get(name) or mname or '?'}",
                         m.id if m else None))
    for name in sorted(_arch.CREATURES):                               # creatures (GEO_MON field objects)
        mname = _arch.CREATURES[name]["model"]
        m = _cat.model(mname)
        out.append(Entry("creature", name, mname, f"monster -- {desc.get(name) or mname}", m.id if m else None))
    for name in sorted(_props.PROP_COMPOSITES):                        # composites (multi-part set pieces)
        d = desc.get(name) or f"{len(_props.PROP_COMPOSITES[name])} parts"
        out.append(Entry("composite", name, None, f"set piece -- {d}"))
    for name in sorted(_props.PROP_ARCHETYPES):                        # props (single static set-dressing)
        spec = _props.PROP_ARCHETYPES[name]
        m = _cat.model(_cat.resolve_model(spec["model"]))
        gname = m.name if m else spec["model"]
        out.append(Entry("prop", name, gname, f"prop -- {desc.get(name) or gname}", m.id if m else None))
    for m in _cat.all_models():                                        # raw models (anything by GEO name)
        friendly = by_model.get(m.name, [])
        extra = ("  -- " + ", ".join(friendly)) if friendly else ""
        out.append(Entry("model", m.name, m.name, f"{m.kind} model ({m.form}){extra}", m.id))
    for iid, nm in _cat.items():                                       # items
        out.append(Entry("item", nm, None, f"item #{iid}", iid))
    for nm, sid in _cat.battle_scenes():                              # battle scenes (encounters)
        out.append(Entry("scene", nm, None, f"battle scene #{sid}", sid))
    return out


_ENTRY_CACHE: Optional[list] = None


def _all_entries() -> list:
    """The indexed entries (lazily built once; the catalogs are static)."""
    global _ENTRY_CACHE
    if _ENTRY_CACHE is None:
        _ENTRY_CACHE = _build_entries()
    return _ENTRY_CACHE


_MODEL_NAMES_CACHE: Optional[dict] = None


def _model_names_index() -> dict:
    """``{model_name: [names...]}`` -- every archetype/creature/prop name grouped by its GEO model, built
    ONCE so :func:`_aliases_for` is an O(1) lookup instead of re-scanning every archetype per detail."""
    global _MODEL_NAMES_CACHE
    if _MODEL_NAMES_CACHE is None:
        idx: dict = {}
        for n in set(_CHAR_PRESETS) | set(_arch.ARCHETYPES) | set(_arch.CREATURES):
            mn = _model_of_archetype(n)
            if mn:
                idx.setdefault(mn, []).append(n)
        for n, spec in _props.PROP_ARCHETYPES.items():
            m = _cat.model(_cat.resolve_model(spec["model"]))
            if m:
                idx.setdefault(m.name, []).append(n)
        _MODEL_NAMES_CACHE = {k: sorted(v) for k, v in idx.items()}
    return _MODEL_NAMES_CACHE


def _aliases_for(name, model_name) -> list:
    """Other archetype/creature/prop names on the same GEO model (so a detail pane can show 'also: dagger,
    garnets_mother') -- an O(1) lookup into the cached :func:`_model_names_index`."""
    if not model_name:
        return []
    return [n for n in _model_names_index().get(model_name, []) if n != name]


# --------------------------------------------------------------- public API ---
def browse(query: str = "", kinds=None, limit=200) -> list:
    """Search every catalog + archetype table at once. ``query`` = a case-insensitive substring of an
    entry's name / model / SUMMARY (the summary folds in the comment description + friendly names, so you
    can search by what a thing IS); ``kinds`` restricts to a subset of :data:`KINDS`; ``limit`` caps the
    result (curated/named kinds come first) or ``None`` for no cap. The Info Hub's 'grab anything by name'."""
    q = (query or "").strip().lower()
    want = set(kinds) if kinds else set(KINDS)
    out = []
    for e in _all_entries():
        if e.kind not in want:
            continue
        if q and q not in e.name.lower() and not (e.model and q in e.model.lower()) \
                and q not in e.summary.lower():
            continue
        out.append(e)
        if limit is not None and len(out) >= limit:
            break
    return out


def find(name, kind=None) -> Optional[Entry]:
    """The first :class:`Entry` whose name matches ``name`` exactly (case-insensitive), optionally of a
    given ``kind`` -- for callers that have a name but no Entry (e.g. resolving a `field.toml` value)."""
    key = str(name).strip().lower()
    for e in _all_entries():
        if e.name.lower() == key and (kind is None or e.kind == kind):
            return e
    return None


def snippet(entry: Entry) -> str:
    """The ``field.toml`` block to author this entry (a frontend's 'copy / insert'). Placeables get a
    ``[[npc]]`` / ``[[prop]]`` block with a ``pos = [0, 0]`` placeholder; item/scene get the line they're
    used in."""
    e = entry
    if e.kind in ("archetype", "creature"):
        return f'[[npc]]\narchetype = "{e.name}"\npos = [0, 0]'
    if e.kind in ("prop", "composite"):
        return f'[[prop]]\nprop = "{e.name}"\npos = [0, 0]'
    if e.kind == "model":
        m = _cat.model(e.ident) if e.ident is not None else _cat.model(e.model)
        if m and m.group == "ACC":
            return f'[[prop]]\nmodel = "{m.name}"\npos = [0, 0]'
        return f'[[npc]]\nmodel = "{e.model}"\npos = [0, 0]'
    if e.kind == "item":
        return f'give_item = [{e.ident}, 1]  # {e.name} -- e.g. an [[event]] reward'
    if e.kind == "scene":
        return f'[encounter]\nscene = {e.ident}  # {e.name}'
    return e.name


def detail(entry: Entry, usage_fn: Optional[Callable] = None) -> Detail:
    """Resolve an :class:`Entry` to its full :class:`Detail`. ``usage_fn(model_id) -> [(field_id, name),
    ...]`` is an optional hook a frontend passes to add 'where it appears in real FF9' (the spine stays
    install-free -- field-usage needs the game); errors from it degrade to ``locations = None``."""
    e = entry
    d = Detail(name=e.name, kind=e.kind, model=e.model, model_id=e.ident, snippet=snippet(e))
    dsc = _descriptions().get(e.name)
    if e.kind == "composite":
        d.parts = [((_cat.model(mid).name if _cat.model(mid) else str(mid)), pose, dx, dz)
                   for mid, pose, dx, dz in _props.resolve_composite(e.name)]
        d.facts = [("kind", "composite set piece"), ("parts", str(len(d.parts)))]
        if dsc:
            d.facts.append(("desc", dsc))
        return d
    if e.kind == "item":
        d.facts = [("kind", "item"), ("id", str(e.ident))]
        return d
    if e.kind == "scene":
        d.facts = [("kind", "battle scene"), ("id", str(e.ident))]
        return d
    # archetype / creature / prop / model -- everything model-backed
    m = _cat.model(e.ident) if e.ident is not None else (_cat.model(e.model) if e.model else None)
    if m:
        d.model, d.model_id = m.name, m.id
        d.facts = [("kind", e.kind), ("model", m.name), ("role", m.kind), ("form", m.form)]
        if e.kind == "prop":
            d.facts.append(("pose", str(_props.resolve(e.name)[1])))
        if dsc:
            d.facts.append(("desc", dsc))
        d.anims = _cat.animation_actions(m.id)
        d.movement = _cat.npc_anims(m.id) or None
        d.aliases = _aliases_for(e.name, m.name)
        if usage_fn is not None:
            try:
                d.locations = list(usage_fn(m.id))
            except Exception:
                d.locations = None
    return d
