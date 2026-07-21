"""Battle locations -- map battle scene ids to the real places that trigger them (mirroring
``world/locate.py``'s naming precedent for the overworld's tile->field dispatch).

FF9's battle scenes (``_scenedb.SCENES``, 856 ``BSC_<region>_<n>`` ids) have no built-in reverse index to
the field(s) that fight them, and no monster-name field anywhere in the per-enemy data. Both are derivable
from the user's own install, never guessed:

  * **field -> scene** -- a field's compiled ``.eb`` says exactly which battle scene(s) it triggers, via
    ``SetRandomBattles`` (:func:`eventscan.scan_encounter`, random encounters) and ``Battle``/``BattleEx``
    (:func:`eventscan.scan_battle_scenes`, scripted/boss fights). Looping both over every real field
    (``_fieldtable.FIELD_BY_ID``) and joining the result to ``data/region_catalog.toml`` (via
    :func:`refarc.load_region_catalog`) gives ``scene -> [(field, place), ...]`` for free -- this module
    adds zero new bytecode decoding, only the census loop + join + cache.
  * **scene -> monster name** -- an enemy's display name is string index ``0..TypCount-1`` of the SAME
    per-scene embedded text pool the field/item/ability text families use (``EmbeddedAsset/Text/<lang>/
    Battle/<id>.mes``, engine ``btl_init.cs`` / ``TranslationExporter.cs``), in the exact ``SB2_MON_PARM``
    type order the raw16 header (``TypCount``) already gives (:func:`battle.scene_data.parse_counts`).
    Entries ``TypCount..TypCount+AtkCount-1`` are attack names, same pool.

See ``studies/battle-locations/PLAN.md`` for the full research trail (rungs 1-5 implemented here).

**Provenance**: the census (field<->scene links, decoded from real ``.eb`` bytecode) and the monster-name
table (decoded from an embedded MES text pool) are BOTH decoded-from-the-user's-own-install content -- the
same bucket as ``battlecsv.py``/``itemstats.py``'s read-live pattern. Neither is committed as a baked
table; both are generated on demand and cached under ``provision.cache_dir()/battlemap/`` (gitignored),
existence-check + ``force=True`` invalidation, mirroring ``extract.cache_field``. This module never
modifies ``eventscan.py``/``_scenedb.py``/``_fieldtable.py``/``region_catalog.toml`` or reads/writes the
game install -- read-only in, JSON cache out.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field as _dc_field
from pathlib import Path

from .. import catalog
from .. import eventscan
from .. import provision
from .. import refarc
from .._fieldtable import FIELD_BY_ID
from .._scenedb import SCENES
from ..dialogue import parse_mes, strip_tags
from ..eb import EbScript
from ..fsutil import atomic_write_text
from .scene_data import parse_counts

CACHE_VERSION = 1                 # bump when the cache SHAPE changes -- an old-shaped file is ignored, not misread
_CACHE_SUBDIR = "battlemap"
_CACHE_FILE = "battlemap.json"

# the folder/container patterns the p0data2 raw16 scan pairs (mirrors battle.extract.read_scene_assets)
_RAW16_RE = re.compile(r"battlescene/evt_battle_([^/]+)/dbfile0000\.raw16\.bytes$")
_RAW17_RE = re.compile(r"battlescene/evt_battle_([^/]+)/(\d+)\.raw17\.bytes$")
# the mainData ResourceManager container path the battle-text bulk scan matches (mirrors
# battle.extract._read_battle_text's per-scene lookup key, generalised to every id at once)
_BATTLE_TEXT_RE = re.compile(r"^embeddedasset/text/([a-z]+)/battle/(\d+)\.mes$")


# ------------------------------------------------------------------------------------- the map object ---
@dataclass
class BattleMap:
    """The built battle-location map. Never construct directly -- use :func:`build_map`. All dict keys
    that are field/scene ids are ``int`` in memory (JSON forces string keys on disk; the cache round-trip
    converts both ways)."""
    version: int
    census: dict = _dc_field(default_factory=dict)          # field_id -> {random:[sid,..], scripted:[sid,..], computed:bool}
    computed_fields: list = _dc_field(default_factory=list)  # field ids with a computed-operand SetRandomBattles (latent)
    scene_sites: dict = _dc_field(default_factory=dict)      # scene_id -> [(field_id, 'random'|'scripted'), ...] deduped
    field_arc: dict = _dc_field(default_factory=dict)        # field_id -> arc_key ('region_catalog.toml' key), absent = no arc
    arcs: dict = _dc_field(default_factory=dict)             # arc_key -> {"name": str, "zone": str|None}
    classification: dict = _dc_field(default_factory=dict)   # scene_id -> 'placed'|'model-bucket'|'overworld'|'unplaced'
    junk_ids: list = _dc_field(default_factory=list)         # engine-skipped "Junk?" scene ids (220, 238)
    names: dict = _dc_field(default_factory=dict)            # scene_id -> {typecount, atkcount, names:{lang:[..]}, attacks:{lang:[..]}}
    name_gaps: list = _dc_field(default_factory=list)        # scene ids with raw16 XOR text (or unparsable) -- no name data
    scene_count: int = 0                                      # len(_scenedb.SCENES) at build time
    field_count: int = 0                                      # fields with SOME battle content (len(census))


# -------------------------------------------------------------------------------------- rung 1-3: census ---
def _srb_status(eb_bytes) -> str:
    """Mirrors :func:`eventscan.scan_encounter`'s decision on the FIRST ``SetRandomBattles`` instruction:
    ``'none'`` (no such instruction at all -- a normal, correct encounter-less field), ``'ok'`` (present,
    all-immediate operands -- ``scan_encounter`` already decoded it), or ``'computed'`` (present, but at
    least one operand is a runtime expression -- ``scan_encounter`` correctly declined to guess; this is
    the honest 'latent' case the field census must not silently drop)."""
    eb = EbScript.from_bytes(eb_bytes)
    ins = next(eventscan._first_instr(eb, eventscan.SET_RANDOM_BATTLES), None)
    if ins is None:
        return "none"
    return "computed" if any(ins.arg_is_expr[:5]) else "ok"


def _field_record(eb_bytes) -> "dict | None":
    """One field's battle record from its raw ``.eb`` bytes: ``{random, scripted, computed}``, or None if
    the field has no random scenes, no scripted scenes, AND no computed-operand ambiguity (truly
    encounter-less). ``random``/``scripted`` are sorted, deduped scene-id lists (a field's 4
    ``SetRandomBattles`` slots may repeat one id -- e.g. field 250's all-Goblin table -- collapsed to one
    row); ``computed`` is True when a ``SetRandomBattles`` exists but its operand can't be read statically
    (0/818 observed today, but the field is recorded honestly rather than mislabeled encounter-less)."""
    enc = eventscan.scan_encounter(eb_bytes)
    is_computed = False
    random_scenes: list = []
    if enc is not None:
        random_scenes = sorted({int(s) for s in enc["scenes"]})
    else:
        is_computed = _srb_status(eb_bytes) == "computed"
    scripted = list(eventscan.scan_battle_scenes(eb_bytes))
    if not random_scenes and not scripted and not is_computed:
        return None
    return {"random": random_scenes, "scripted": scripted, "computed": is_computed}


def _census(game=None) -> tuple:
    """Loop every real field id (``_fieldtable.FIELD_BY_ID``), collect its battle record. Returns
    ``(census, computed_fields)``: ``census`` = ``{field_id: {random, scripted, computed}}`` for every
    field with SOME battle content; ``computed_fields`` = the sorted subset flagged ``computed``. An id
    with no FBG/event mapping or an absent binary (``EventBundle.eb_for_id`` -> None) is skipped, never
    raises -- ~674-818 real fields load in one bundle read (~1s) + one instruction walk each (~6s total)."""
    from .. import extract as _extract
    bundle = _extract.EventBundle(game=game)
    census: dict = {}
    computed: list = []
    for fid in sorted(FIELD_BY_ID):
        eb_bytes = bundle.eb_for_id(fid)
        if eb_bytes is None:
            continue
        rec = _field_record(eb_bytes)
        if rec is None:
            continue
        census[fid] = rec
        if rec["computed"]:
            computed.append(fid)
    return census, sorted(computed)


def _scene_site_index(census: dict) -> dict:
    """``census`` -> ``{scene_id: [(field_id, kind), ...]}``, sorted + deduped. A ``(scene, field)`` pair
    that is BOTH random and scripted (4 real cases: scenes 6/893/897/901) keeps both rows -- kind is part
    of the dedup key, not collapsed away."""
    idx: dict = {}
    for fid, rec in census.items():
        for sid in rec["random"]:
            idx.setdefault(sid, set()).add((fid, "random"))
        for sid in rec["scripted"]:
            idx.setdefault(sid, set()).add((fid, "scripted"))
    return {sid: sorted(sites) for sid, sites in idx.items()}


# ------------------------------------------------------------------------------------ rung 2: zone join ---
def _zone_join() -> tuple:
    """``refarc.load_region_catalog()`` -> ``(field_arc, arcs)``: ``field_arc`` = ``{field_id: arc_key}``
    for every field id ANY arc's ``members`` names (817/818 real ids -- field 70 is the one documented
    gap, left simply ABSENT from the dict rather than mapped to a fake arc); ``arcs`` = ``{arc_key:
    {"name": str, "zone": str|None}}`` for every arc in the catalog (even ones with no census hits, so a
    caller can still look up a name). Pure data join over the packaged/generated catalog -- no install
    needed, safe to call offline."""
    arcset = refarc.load_region_catalog()
    field_arc: dict = {}
    arcs: dict = {}
    for arc in arcset.arcs:
        arcs[arc.key] = {"name": arc.name, "zone": arc.zone}
        for fid in (arc.members or ()):
            field_arc.setdefault(int(fid), arc.key)
    return field_arc, arcs


# --------------------------------------------------------------------------------- rung 3: classification ---
_JUNK_SCENE_IDS = (220, 238)      # engine-skipped "Junk?" ids (both BSC_WM_*) -- recorded, not a separate bucket


def _classify_scenes(census: dict) -> tuple:
    """Every ``_scenedb`` id classified into exactly one honest bucket -- NEVER guessed from a name prefix
    for placed-ness (the census, i.e. whether the id was actually REACHED by a real field, always wins):

      * ``'placed'``      -- the id appears in the census (some field's random or scripted table).
      * ``'model-bucket'``-- unreached AND a ``BSC_B3_*`` name (:func:`catalog._is_model_bucket`) -- a
        model-preload holder, not a fightable encounter.
      * ``'overworld'``   -- unreached AND a ``BSC_WM_*`` name -- world-map scoped, not field-scoped.
      * ``'unplaced'``    -- unreached and neither of the above (``BSC_CAM_*``, dev/test names, or any
        residue) -- honestly "don't know", never mislabeled as one of the other three.

    Returns ``(classification, junk_ids)``. When an id has multiple ``_scenedb`` name aliases, the FIRST
    name (table order, same convention as :func:`catalog.scene_name`) decides the name-based buckets --
    reached-ness depends only on the id, so 'placed' is alias-independent."""
    reached: set = set()
    for rec in census.values():
        reached.update(rec["random"])
        reached.update(rec["scripted"])
    out: dict = {}
    for name, sid in SCENES.items():
        if sid in out:
            continue
        if sid in reached:
            out[sid] = "placed"
        elif catalog._is_model_bucket(name):
            out[sid] = "model-bucket"
        elif str(name).upper().startswith("BSC_WM_"):
            out[sid] = "overworld"
        else:
            out[sid] = "unplaced"
    junk_ids = sorted({sid for sid in _JUNK_SCENE_IDS if sid in SCENES.values()})
    return out, junk_ids


# -------------------------------------------------------------------------------- rung 5: monster names ---
def _scan_battle_text_pools(game=None) -> dict:
    """ONE mainData+resources.assets load -> ``{scene_id: {lang: raw_text}}`` for every embedded battle
    text pool the ResourceManager container knows (``EmbeddedAsset/Text/<lang>/Battle/<id>.mes``), keyed
    by the container PATH (never by TextAsset name -- field and battle ``.mes`` share bare ``<id>.mes``
    names elsewhere in ``resources.assets``, so a name-keyed read would collide). Mirrors
    ``battle.extract._read_battle_text``'s index lookup, generalised to grab every id in one pass instead
    of probing one id at a time. ``{}`` if the ResourceManager itself can't be read (an odd/old install)."""
    from .. import extract as _extract
    from .extract import _ff9_data_dir, _unitypy
    UnityPy = _unitypy()
    data_dir = _ff9_data_dir(game)
    env = UnityPy.load(str(data_dir / "mainData"), str(data_dir / "resources.assets"))
    rm = next((o.read() for o in env.objects
               if getattr(getattr(o, "type", None), "name", "") == "ResourceManager"), None)
    if rm is None:
        return {}
    out: dict = {}
    for path, ptr in rm.m_Container:
        m = _BATTLE_TEXT_RE.match(str(path).lower())
        if not m:
            continue
        lang, sid = m.group(1), int(m.group(2))
        try:
            raw = _extract._raw_bytes(ptr.read())
        except Exception:                                    # noqa: BLE001 -- one bad pointer shouldn't kill the scan
            continue
        if raw is None:
            continue
        out.setdefault(sid, {})[lang] = raw.decode("utf-8", "replace")
    return out


def _scan_raw16(game=None) -> dict:
    """ONE p0data2 pass -> ``{scene_id: raw16_bytes}``, pairing each ``battlescene/evt_battle_<name>/``
    folder's ``dbfile0000.raw16.bytes`` with the numeric scene id embedded in that SAME folder's
    ``<id>.raw17.bytes`` filename (mirrors ``battle.extract.read_scene_assets``'s per-donor pairing,
    generalised to every scene folder in one scan instead of one ``UnityPy.load`` per donor name)."""
    from .. import extract as _extract
    from .extract import _p0data2, _unitypy
    UnityPy = _unitypy()
    env = UnityPy.load(str(_p0data2(game)))
    folder_raw16: dict = {}
    folder_id: dict = {}
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        c = (getattr(o, "container", None) or "").lower()
        m16 = _RAW16_RE.search(c)
        if m16:
            folder_raw16[m16.group(1)] = _extract._raw_bytes(o.read())
            continue
        m17 = _RAW17_RE.search(c)
        if m17:
            folder_id[m17.group(1)] = int(m17.group(2))
    out: dict = {}
    for folder, sid in folder_id.items():
        raw16 = folder_raw16.get(folder)
        if raw16 is not None:
            out[sid] = raw16
    return out


def _pool_names(body: str, start: int, count: int) -> list:
    """``count`` display names starting at pool index ``start`` (monsters: start=0; attacks:
    start=TypCount), stripped of ``.mes`` control tags. A missing/dead slot -> None (never crash on a
    gap -- some real scenes have unused type slots, and a dead pattern still consumes an index)."""
    entries = parse_mes(body)
    return [strip_tags(entries[start + i].text) if (start + i) in entries else None for i in range(count)]


def _build_names(raw16_by_scene: dict, pools_by_scene: dict) -> tuple:
    """Join the raw16 (TypCount/AtkCount) + text-pool scans into per-scene name data:
    ``{scene_id: {typecount, atkcount, names:{lang:[..]}, attacks:{lang:[..]}}}`` + a sorted list of scene
    ids that had ONE of the two sources but not both (or an unparsable raw16 header) -- recorded as a gap,
    never silently dropped or crashed on."""
    out: dict = {}
    gaps: list = []
    for sid in sorted(set(raw16_by_scene) | set(pools_by_scene)):
        raw16 = raw16_by_scene.get(sid)
        pools = pools_by_scene.get(sid)
        if raw16 is None or not pools:
            gaps.append(sid)
            continue
        try:
            _pat, typ, atk = parse_counts(raw16)
        except Exception:                                    # noqa: BLE001 -- a malformed/truncated raw16 -> a gap, not a crash
            gaps.append(sid)
            continue
        rec = {"typecount": int(typ), "atkcount": int(atk), "names": {}, "attacks": {}}
        for lang, body in pools.items():
            rec["names"][lang] = _pool_names(body, 0, int(typ))
            rec["attacks"][lang] = _pool_names(body, int(typ), int(atk))
        out[sid] = rec
    return out, sorted(gaps)


# --------------------------------------------------------------------------------------- build + cache ---
_MEMO: dict = {}          # memo_key ("" for the default install) -> BattleMap, in-process only


def _memo_key(game) -> str:
    return str(game) if game else ""


def _cache_dir_path() -> Path:
    return provision.cache_dir() / _CACHE_SUBDIR


def _cache_file_path() -> Path:
    return _cache_dir_path() / _CACHE_FILE


def _to_cache_dict(bm: BattleMap) -> dict:
    """``BattleMap`` -> a JSON-safe dict (int keys stringified; tuples listified)."""
    return {
        "version": bm.version,
        "census": {str(k): v for k, v in bm.census.items()},
        "computed_fields": list(bm.computed_fields),
        "scene_sites": {str(k): [list(t) for t in v] for k, v in bm.scene_sites.items()},
        "field_arc": {str(k): v for k, v in bm.field_arc.items()},
        "arcs": bm.arcs,
        "classification": {str(k): v for k, v in bm.classification.items()},
        "junk_ids": list(bm.junk_ids),
        "names": {str(k): v for k, v in bm.names.items()},
        "name_gaps": list(bm.name_gaps),
        "scene_count": bm.scene_count,
        "field_count": bm.field_count,
    }


def _from_cache_dict(d: dict) -> "BattleMap | None":
    """The inverse of :func:`_to_cache_dict`, or None if ``d`` isn't a dict, is missing a required key, or
    was written by a different :data:`CACHE_VERSION` (a stale/foreign cache is IGNORED, not misread)."""
    if not isinstance(d, dict) or d.get("version") != CACHE_VERSION:
        return None
    try:
        return BattleMap(
            version=int(d["version"]),
            census={int(k): v for k, v in d["census"].items()},
            computed_fields=list(d["computed_fields"]),
            scene_sites={int(k): [tuple(t) for t in v] for k, v in d["scene_sites"].items()},
            field_arc={int(k): v for k, v in d["field_arc"].items()},
            arcs=dict(d["arcs"]),
            classification={int(k): v for k, v in d["classification"].items()},
            junk_ids=list(d["junk_ids"]),
            names={int(k): v for k, v in d["names"].items()},
            name_gaps=list(d["name_gaps"]),
            scene_count=int(d["scene_count"]),
            field_count=int(d["field_count"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _write_cache(bm: BattleMap) -> None:
    d = _cache_dir_path()
    d.mkdir(parents=True, exist_ok=True)
    atomic_write_text(_cache_file_path(), json.dumps(_to_cache_dict(bm)))


def _build_fresh(game=None) -> BattleMap:
    """The cold build: census (rungs 1-3) + zone join (rung 2) + classification (rung 3) + the bulk
    raw16/text-pool scans and name join (rung 5). ~6s census + one raw16 pass (~161MB) + one
    mainData/resources.assets pass -- everything the caller pays for ONCE per :func:`build_map` call that
    misses both the in-process memo and the disk cache."""
    census, computed = _census(game)
    field_arc, arcs = _zone_join()
    sites = _scene_site_index(census)
    classification, junk_ids = _classify_scenes(census)
    raw16 = _scan_raw16(game)
    pools = _scan_battle_text_pools(game)
    names, gaps = _build_names(raw16, pools)
    return BattleMap(version=CACHE_VERSION, census=census, computed_fields=computed,
                      scene_sites=sites, field_arc=field_arc, arcs=arcs,
                      classification=classification, junk_ids=junk_ids,
                      names=names, name_gaps=gaps,
                      scene_count=len(SCENES), field_count=len(census))


def build_map(game=None, *, force: bool = False) -> BattleMap:
    """Build (or load the cached) battle-location map -- the entry point every other function in this
    module calls implicitly. Resolution order: the in-process memo, then the on-disk JSON cache
    (``provision.cache_dir()/battlemap/battlemap.json``, version-gated), then a fresh install build (~6s
    census + one raw16 pass + one text-pool pass). ``force=True`` skips straight to a fresh build and
    overwrites both caches (use after a game update, or if the install content changed).

    ``game`` is the install root override passed through to ``config.find_game_path`` (None = the kit's
    normal auto-detected install). NOTE the on-disk cache path is NOT keyed by ``game`` (one cache slot,
    like ``extract.cache_field``) -- pass a consistent ``game`` across a session, or ``force=True`` when
    switching installs."""
    key = _memo_key(game)
    if not force and key in _MEMO:
        return _MEMO[key]
    bm = None
    if not force:
        cf = _cache_file_path()
        if cf.is_file():
            try:
                bm = _from_cache_dict(json.loads(cf.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                bm = None
    if bm is None:
        bm = _build_fresh(game)
        _write_cache(bm)
    _MEMO[key] = bm
    return bm


def _map(game=None) -> BattleMap:
    return build_map(game=game)


# ------------------------------------------------------------------------------------------ public API ---
def scene_sites(scene_id, *, game=None) -> list:
    """``[(field_id, 'random'|'scripted'), ...]`` -- every real field that fights ``scene_id``, sorted +
    deduped (a field appears twice only if it triggers the scene BOTH as a random encounter and a scripted
    fight). ``[]`` if the scene was never statically reached by the census (see :func:`classify`)."""
    return list(_map(game).scene_sites.get(int(scene_id), []))


def scene_places(scene_id, *, game=None) -> list:
    """``scene_sites`` grouped by zone/arc: ``[{arc, arc_name, fields, kinds}, ...]``, ``arc``/``arc_name``
    None for the one documented arc-less field (70). ``fields`` is the sorted field-id list in that arc
    that fight this scene; ``kinds`` is the sorted union of 'random'/'scripted' seen across those fields
    (NOT per-field -- use :func:`field_battles` for a single field's own kind split)."""
    bm = _map(game)
    groups: dict = {}
    for fid, kind in bm.scene_sites.get(int(scene_id), []):
        arc_key = bm.field_arc.get(fid)
        g = groups.setdefault(arc_key, {
            "arc": arc_key,
            "arc_name": bm.arcs.get(arc_key, {}).get("name") if arc_key else None,
            "fields": set(), "kinds": set(),
        })
        g["fields"].add(fid)
        g["kinds"].add(kind)
    out = [{"arc": g["arc"], "arc_name": g["arc_name"],
            "fields": sorted(g["fields"]), "kinds": sorted(g["kinds"])}
           for g in groups.values()]
    out.sort(key=lambda g: (g["arc"] is None, g["arc_name"] or "", g["arc"] or ""))
    return out


def scene_label(scene_id, *, lang: str = "us", game=None) -> str:
    """A one-line human string for a scene, e.g. ``"Goblin, Fang -- Evil Forest (field 250, random)"``.
    Falls back to the ``BSC_`` catalog name (or a bare ``"scene <id>"``) when no monster names are
    resolvable, and to ``"-- unplaced"`` when the census never reached the scene at all."""
    sid = int(scene_id)
    names = monster_names(sid, lang=lang, game=game)
    who = ", ".join(n for n in names if n) if names else (catalog.scene_name(sid) or f"scene {sid}")
    places = scene_places(sid, game=game)
    if not places:
        return f"{who} -- unplaced"
    descs = []
    for g in places:
        loc = g["arc_name"] or "an unmapped field"
        fids = g["fields"]
        fdesc = f"field {fids[0]}" if len(fids) == 1 else f"fields {', '.join(str(f) for f in fids)}"
        descs.append(f"{loc} ({fdesc}, {'/'.join(g['kinds'])})")
    return f"{who} -- {'; '.join(descs)}"


def field_battles(field_id, *, game=None) -> dict:
    """``{random: [scene_id,...], scripted: [scene_id,...], computed: bool}`` for one field --
    ``computed`` True means the field HAS a ``SetRandomBattles`` instruction whose operand couldn't be
    read statically (an honest gap, not "no encounters"). All-empty/False for a field with no battle
    content in the census (including ids the census never reached, e.g. no FBG mapping)."""
    rec = _map(game).census.get(int(field_id))
    if rec is None:
        return {"random": [], "scripted": [], "computed": False}
    return {"random": list(rec["random"]), "scripted": list(rec["scripted"]), "computed": bool(rec["computed"])}


def monster_names(scene_id, *, lang: str = "us", game=None) -> "list | None":
    """The scene's enemy display names, in raw16 ``SB2_MON_PARM`` type order (index 0..TypCount-1) --
    ``None`` if the scene has no resolvable text pool AND raw16 (see :func:`classify` / the
    ``name_gaps`` in :func:`unresolved_report`). A returned list may itself contain ``None`` entries for a
    dead/unused type slot (degrades gracefully, never crashes). Falls back to the 'us' pool when
    ``lang`` wasn't captured for this scene (rare -- most scenes ship all 7 languages)."""
    rec = _map(game).names.get(int(scene_id))
    if rec is None:
        return None
    names = rec["names"].get(lang)
    if names is None:
        names = rec["names"].get("us")
    return list(names) if names is not None else None


def attack_names(scene_id, *, lang: str = "us", game=None) -> "list | None":
    """The scene's attack names (pool indices TypCount..TypCount+AtkCount-1) -- the sibling of
    :func:`monster_names`, same fallback/None contract."""
    rec = _map(game).names.get(int(scene_id))
    if rec is None:
        return None
    atks = rec["attacks"].get(lang)
    if atks is None:
        atks = rec["attacks"].get("us")
    return list(atks) if atks is not None else None


def find_monster(query: str, *, lang: str = "us", game=None) -> list:
    """``[(scene_id, monster_name), ...]`` -- every scene/name pair whose name contains ``query``
    (case-insensitive substring), sorted by scene id. The "where does Goblin appear" reverse lookup."""
    q = str(query).strip().lower()
    if not q:
        return []
    out = []
    for sid, rec in _map(game).names.items():
        names = rec["names"].get(lang) or rec["names"].get("us") or []
        for nm in names:
            if nm and q in nm.lower():
                out.append((sid, nm))
    return sorted(out)


def classify(scene_id, *, game=None) -> str:
    """One of ``'placed'`` / ``'model-bucket'`` / ``'overworld'`` / ``'unplaced'`` for a ``_scenedb`` id
    (see :func:`_classify_scenes`). An id the table doesn't know at all returns ``'unplaced'`` too (the
    honest "don't know" default -- never raises on an out-of-table id)."""
    return _map(game).classification.get(int(scene_id), "unplaced")


def unresolved_report(game=None) -> dict:
    """A self-describing summary of everything this module could NOT resolve, for a browse UI's "coverage"
    panel: classification totals, fields with a computed-operand encounter, the engine-skipped junk scene
    ids, scene ids with partial name data, and real field ids the zone join never placed in an arc (the
    one documented gap is field 70)."""
    bm = _map(game)
    return {
        "cache_version": bm.version,
        "scene_count": bm.scene_count,
        "field_count": bm.field_count,
        "classification_totals": dict(Counter(bm.classification.values())),
        "computed_operand_fields": list(bm.computed_fields),
        "junk_scene_ids": list(bm.junk_ids),
        "name_gaps": list(bm.name_gaps),
        "fields_without_arc": sorted(set(FIELD_BY_ID) - set(bm.field_arc)),
    }
