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

# the kinds the Info Hub indexes, listed in browse priority order (curated/named first, raw + reference last)
KINDS = ("archetype", "creature", "composite", "prop", "model", "item", "scene", "storyflag")


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
    from . import itemstats as _istats                                # live stats from YOUR install (or None)
    for iid, nm in _cat.items():                                       # items
        out.append(Entry("item", nm, None, _istats.summary(iid) or f"item #{iid}", iid))
    for nm, sid in _cat.battle_scenes():                              # battle scenes (encounters)
        out.append(Entry("scene", nm, None, f"battle scene #{sid}", sid))
    out += _storyflag_entries()                                       # FF9 story-flag registry (reference)
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


# ------------------------------------------------------ story-flag registry ---
# The FF9 story-flag REGISTRY (flags.py) browsable as a reference kind: named engine vars, reserved bit
# regions, the census story clusters, the scenario-milestone table, and the safe custom band. Always
# available + install-free (flags.py is pure). Distinct from the campaign 'flag' kind (a campaign's own
# [[flag]] gates) -- this is FF9's built-in story state, for "what bit / scenario is X?".
_STORYFLAG_SUBLABEL = {"var": "story var", "RESERVED": "RESERVED region", "region": "bit region",
                       "story": "story cluster", "scenario": "scenario milestone", "band": "safe custom band"}
_STORYFLAG_TIER = {"a": "engine-grounded", "b": "empirical (census)", "c": "uncertain",
                   "a/b": "engine + census"}
_STORYFLAG_ROWS_CACHE: Optional[dict] = None


def _storyflag_rows() -> dict:
    """``{display_name: (sub, raw_name, location, meaning, tier)}`` from ``flags.registry_rows()`` (built
    once). Scenario rows display as 'Beat (value)' so they're unique + searchable by beat AND value."""
    global _STORYFLAG_ROWS_CACHE
    if _STORYFLAG_ROWS_CACHE is None:
        from . import flags as _flags
        rows: dict = {}
        for sub, name, loc, meaning, tier in _flags.registry_rows():
            disp = f"{meaning} ({name})" if sub == "scenario" else name
            rows[disp] = (sub, name, loc, meaning, tier)
        _STORYFLAG_ROWS_CACHE = rows
    return _STORYFLAG_ROWS_CACHE


def _storyflag_entries() -> list:
    out = []
    for disp, (sub, name, loc, meaning, tier) in _storyflag_rows().items():
        label = _STORYFLAG_SUBLABEL.get(sub, sub)
        ident = int(name) if sub == "scenario" else None
        out.append(Entry("storyflag", disp, None, f"{label} · {loc} · {meaning}", ident))
    return out


# ----------------------------------------------------------- campaign layer ---
def _campaign_entries(plan) -> list:
    """Field entries (kind='field') for the members of a campaign -- the ADDITIVE layer browse/detail
    expose when a frontend passes ``campaign_context``. Lets the Info Hub search 'the fields in THIS
    campaign' alongside the static catalogs. Duck-typed (anything with a ``.members`` list of objects
    carrying ``name``/``new_id``/``mode``) so the spine never imports campaign.py at module load."""
    out = []
    for m in getattr(plan, "members", None) or []:
        nm = getattr(m, "name", None)
        if not nm:
            continue
        nid = getattr(m, "new_id", None)
        mode = getattr(m, "mode", "") or ""
        out.append(Entry("field", nm, None, f"campaign field #{nid} ({mode})", nid))
    for fdef in getattr(plan, "flags", None) or []:               # shared NAMED story flags (cross-field gates)
        nm = fdef.get("name") if isinstance(fdef, dict) else None
        if nm:
            idx = fdef.get("index")
            out.append(Entry("flag", str(nm), None, f"campaign story flag (bit {idx})", idx))
    return out


# --------------------------------------------------------------- public API ---
def browse(query: str = "", kinds=None, limit=200, campaign_context=None) -> list:
    """Search every catalog + archetype table at once. ``query`` = a case-insensitive substring of an
    entry's name / model / SUMMARY (the summary folds in the comment description + friendly names, so you
    can search by what a thing IS); ``kinds`` restricts to a subset of :data:`KINDS`; ``limit`` caps the
    result (curated/named kinds come first) or ``None`` for no cap. The Info Hub's 'grab anything by name'.

    When ``campaign_context`` (a campaign.CampaignPlan) is given, that campaign's member fields are ALSO
    searchable as kind='field' entries, listed FIRST; with no context the result is exactly as before."""
    q = (query or "").strip().lower()
    field_entries = _campaign_entries(campaign_context) if campaign_context is not None else []
    if kinds:
        want = set(kinds)
    else:
        want = set(KINDS) | ({"field", "flag"} if campaign_context is not None else set())
    # no context -> iterate the cached list directly (no copy), preserving today's behavior exactly
    entries = (field_entries + _all_entries()) if field_entries else _all_entries()
    out = []
    for e in entries:
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
    if e.kind == "field":                              # a campaign member -- not a paste-able toml block
        return f"# campaign field: {e.name} (id {e.ident})"
    if e.kind == "flag":                               # a shared named story flag -> the gate line
        return f'requires_flag = "{e.name}"'
    if e.kind == "storyflag":                          # the FF9 registry -> a reference / authoring hint
        from . import flags as _flags
        sub = _storyflag_rows().get(e.name, ("",))[0]
        if sub == "band":
            return (f'[[flag]]\nname = "my_flag"\nindex = {_flags.FIRST_SAFE_FLAG}   '
                    f'# a custom story flag in the safe band')
        if sub == "scenario":
            return f'ff9mapkit save-edit <SavedData_ww.dat> --scenario {e.ident}   # jump to this story beat'
        loc = _storyflag_rows().get(e.name, ("", "", "?"))[2]
        return f"# {e.name}  ({loc})  -- FF9 engine state, reference only (do not allocate here)"
    return e.name


def _field_detail(entry: Entry, plan) -> Detail:
    """Detail for a campaign member (kind='field'): its place in the chain -- id/source/mode, the live
    doors it leads to + is entered from, onward seams, and entry/reachability/needs-export flags. Resolved
    through :func:`campaign.campaign_graph` (lazy import -- the spine stays campaign-free at module load)."""
    d = Detail(name=entry.name, kind="field", model=None, model_id=entry.ident, snippet=snippet(entry))
    d.facts = [("kind", "campaign field"), ("id", str(entry.ident))]
    if plan is None:
        return d
    from . import campaign as _camp
    node = _camp.campaign_graph(plan).by_name.get(entry.name)
    if node is None:
        return d
    d.facts = [("kind", "campaign field"), ("id", str(node.new_id)),
               ("source", str(node.real_id)), ("mode", node.mode)]
    if node.is_entry:
        d.facts.append(("role", "campaign entry"))
    if node.needs_export:
        d.facts.append(("needs_export", "yes -- export this field's art in-game"))
    if not node.reachable:
        d.facts.append(("reachable", "NO -- no live-door path from the entry"))
    if node.dead_end:
        d.facts.append(("dead_end", "no onward connection"))
    for oe in node.out_edges:
        d.facts.append(("door", f"-> {oe['to']} (entrance {oe['entrance']})"
                                + (" [gated]" if oe["gated"] else "")))
    for ie in node.in_edges:
        d.facts.append(("entered_from", f"<- {ie['frm']} (entrance {ie['entrance']})"))
    for s in node.seams:
        tgt = s["to_member"] or ("WORLDMAP" if s["to_real"] == "WORLDMAP" else s["to_real"])
        d.facts.append((f"seam:{s['kind']}", f"-> {tgt}"))
    return d


def detail(entry: Entry, usage_fn: Optional[Callable] = None, campaign_context=None) -> Detail:
    """Resolve an :class:`Entry` to its full :class:`Detail`. ``usage_fn(model_id) -> [(field_id, name),
    ...]`` is an optional hook a frontend passes to add 'where it appears in real FF9' (the spine stays
    install-free -- field-usage needs the game); errors from it degrade to ``locations = None``. When the
    entry is a campaign member (kind='field') and ``campaign_context`` (a CampaignPlan) is given, the
    detail is the member's place in the chain (doors/seams/reachability)."""
    e = entry
    if e.kind == "field":
        return _field_detail(e, campaign_context)
    if e.kind == "flag":                               # a shared named story flag (cross-field gate)
        d = Detail(name=e.name, kind="flag", model=None, model_id=e.ident, snippet=snippet(e))
        d.facts = [("kind", "campaign story flag"), ("index", str(e.ident)),
                   ("gate", f'requires_flag = "{e.name}"'), ("set", f'set_flag = ["{e.name}", 1]')]
        return d
    if e.kind == "storyflag":                          # an FF9 story-flag registry entry (reference)
        sub, name, loc, meaning, tier = _storyflag_rows().get(e.name, ("", e.name, "", e.summary, ""))
        d = Detail(name=e.name, kind="storyflag", model=None, model_id=None, snippet=snippet(e))
        d.facts = [("kind", _STORYFLAG_SUBLABEL.get(sub, sub)), ("location", loc),
                   ("confidence", _STORYFLAG_TIER.get(tier, tier))]
        if meaning:
            d.facts.append(("meaning", meaning))
        if sub == "RESERVED":
            d.facts.append(("note", "reserved -- a mod must NOT allocate flags here"))
        elif sub == "band":
            d.facts.append(("note", "allocate your custom story flags in this band"))
        return d
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
        from . import itemstats as _istats                            # live stat join from YOUR install
        d.facts = [("kind", "item"), ("id", str(e.ident))] + _istats.facts(e.ident)
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


_PLACEABLE = ("archetype", "creature", "composite", "prop", "model")


def _place_lines(entry, x, z) -> list:
    """The ``[[npc]]`` / ``[[prop]]`` block placing one entry at world (x, z) on a preview field."""
    e, pos = entry, f"pos = [{x}, {z}]"
    if e.kind in ("archetype", "creature"):
        return ["", "[[npc]]", f'archetype = "{e.name}"', pos]
    if e.kind in ("prop", "composite"):
        return ["", "[[prop]]", f'prop = "{e.name}"', pos]
    if e.kind == "model":
        m = _cat.model(e.ident) if e.ident is not None else _cat.model(e.model)
        if m and m.group == "ACC":
            return ["", "[[prop]]", f'model = "{m.name}"', pos]
        return ["", "[[npc]]", f'model = "{e.model}"', pos]
    return []


def preview_field_toml(entries, art_dir, *, screens: int = 3) -> Optional[str]:
    """Build a deployable arena ``field.toml`` that PLACES the given entries -- a gallery of your selection,
    so a frontend deploys it + F6-reloads to see them LIVE on the debug checkerboard. Writes the arena art
    into ``art_dir`` and returns the toml; returns ``None`` if nothing is placeable (items/scenes are not
    field objects). Game-free -- only the caller's deploy touches the install."""
    from .scene import arena as _arena
    placeable = [e for e in (entries or []) if e.kind in _PLACEABLE]
    if not placeable:
        return None
    n = len(placeable)
    meta = _arena.build_arena(art_dir, screens=max(screens, n))
    half = meta["quad"][1][0]
    margin = 700
    xs = [round(-(half - margin) + 2 * (half - margin) * i / max(1, n - 1)) for i in range(n)]
    zs = [z for _, z in meta["quad"]]
    z_lo, z_hi = min(zs), max(zs)
    row_z, spawn_z = (z_lo + z_hi) // 2, z_hi - 150
    lines = [f"# Info Hub preview -- {', '.join(e.name for e in placeable)}. F6 -> Reload field to see it."]
    lines += _arena.arena_scene_lines(meta, spawn_z=spawn_z, name="PREVIEW")
    for e, x in zip(placeable, xs):
        lines += _place_lines(e, x, row_z)
    return "\n".join(lines)
