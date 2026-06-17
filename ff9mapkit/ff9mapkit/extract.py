#!/usr/bin/env python3
"""Import support: pull a REAL FF9 field's scene data out of the game's p0data bundles, OFFLINE.

This is the data-gathering half of `ff9mapkit import` ("fork any field as a base"). It reads a
field's native assets straight from StreamingAssets/p0data*.bin (UnityRaw 5.2.3 assetbundles) with
no in-game step, and hands them to the kit's existing parsers:

    <fbg>.bgs.bytes  -> scene.bgs.parse_cameras   (the field's camera(s))
    <fbg>.bgi.bytes  -> scene.bgi.BgiWalkmesh     (walkmesh + player start)
    atlas.png        -> the packed background art (only pulled when want_atlas=True)

UnityPy is imported lazily: only `extract`/`import` need it, the core kit stays pure-stdlib.

Proven against GRGR in the offline spike (2026-06-04): the decoded camera matched the engine's own
.bgx export byte-for-byte.
"""
from __future__ import annotations

import glob
import json
import os
import re
from collections import OrderedDict
from pathlib import Path

from . import config
from . import eventscan
from ._fieldtable import FBG_TO_EVT
from .scene import bgart, bgs, bgi, cam


def _unitypy():
    try:
        import UnityPy  # noqa: PLC0415
        return UnityPy
    except ImportError as e:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "extraction needs UnityPy (reads FF9's p0data assetbundles). Install it:\n"
            "    py -m pip install UnityPy"
        ) from e


def _raw_bytes(data):
    """Raw bytes of a TextAsset across UnityPy versions."""
    for attr in ("m_Script", "script"):
        v = getattr(data, attr, None)
        if isinstance(v, bytes):
            return v
        if isinstance(v, str):
            return v.encode("utf-8", "surrogateescape")
    return None


_FBG_RE = re.compile(r"^fbg_n(\d+)_(.+)$", re.I)


def parse_fbg_folder(folder: str):
    """('fbg_n21_grgr_map420_gr_cen_0') -> (area:int=21, mapid:str='GRGR_MAP420_GR_CEN_0').

    `mapid` is the DictionaryPatch BG id (the part after `FBG_N<area>_`); the engine rebuilds
    `FBG_N<area>_<mapid>` for the BG lookup (proven Session-4 BG-borrow)."""
    m = _FBG_RE.match(folder.strip().lower())
    if not m:
        raise ValueError(f"not an FBG field folder: {folder!r}")
    return int(m.group(1)), m.group(2).upper()


def _streaming_assets(game=None) -> Path:
    return config.find_game_path(game) / "StreamingAssets"


def _bundles(game=None):
    return sorted(glob.glob(str(_streaming_assets(game) / "p0data*.bin")))


# In-process cache of loaded STATIC base-game bundles (read-only: StreamingAssets/p0dataN.bin never
# change under us at runtime). Keyed by absolute path, bounded LRU -- so a long-lived process (the test
# suite, the import-chain walk, a fork that reads the event bundle for .eb + MapConfig) loads the hot
# 68 MB event bundle ONCE instead of re-reading it on every call. Re-reading it cold is exactly what
# starves callers when other processes thrash the OS file cache. Mirrors _load_mod_bundle, but kept
# SEPARATE: mod-folder bundles DO mutate on deploy, base-game bundles never do. The cap bounds memory
# while the constantly-touched event bundle naturally stays resident (LRU recency keeps the hot one).
_STREAM_ENV_CACHE: "OrderedDict[str, object]" = OrderedDict()
_STREAM_ENV_CACHE_MAX = 8


def _load_env(path):
    """``UnityPy.load`` a static base-game bundle, memoized (bounded LRU) by absolute path. Read-only
    base data ONLY -- never a mod-folder bundle (those mutate on deploy; use ``_load_mod_bundle``)."""
    key = os.path.abspath(str(path))
    env = _STREAM_ENV_CACHE.get(key)
    if env is not None:
        _STREAM_ENV_CACHE.move_to_end(key)
        return env
    env = _unitypy().load(key)
    _STREAM_ENV_CACHE[key] = env
    while len(_STREAM_ENV_CACHE) > _STREAM_ENV_CACHE_MAX:
        _STREAM_ENV_CACHE.popitem(last=False)
    return env


# ---- field -> bundle index (built once, cached; so lookups don't rescan ~50 bundles) ----
INDEX_NAME = ".ff9mapkit-field-index.json"


def _index_path(game=None) -> Path:
    return _streaming_assets(game) / INDEX_NAME


def build_field_index(game=None, *, force=False, verbose=True) -> dict:
    """Map every field folder -> its p0data bundle. Cached next to the bundles; first build scans
    them all (~1-2 min), then it's instant. `force=True` rebuilds."""
    UnityPy = _unitypy()
    idx = _index_path(game)
    if idx.exists() and not force:
        try:
            return json.loads(idx.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    index = {}
    bundles = _bundles(game)
    for i, path in enumerate(bundles):
        if verbose:
            print(f"  indexing {i + 1}/{len(bundles)} {os.path.basename(path)} ...", flush=True)
        try:
            env = UnityPy.load(path)
        except Exception:
            continue
        bn = os.path.basename(path)
        for k in env.container:
            m = re.search(r"fieldmaps/([^/]+)/", k.lower())
            if m:
                index.setdefault(m.group(1), bn)
    try:
        idx.write_text(json.dumps(index, indent=0), encoding="utf-8")
    except OSError:
        pass
    if verbose:
        print(f"  indexed {len(index)} fields -> {idx}")
    return index


def resolve_field(field: str, game=None):
    """(folder, bundle) for a field token via the index. A pure-DIGIT token is a FIELD ID (parity with
    ``fork-report`` / ``eb_for_id`` -- so ``import <id>`` forks the SAME field the analysis commands describe),
    NOT a folder substring: field ids and the folder ``map<NNN>`` numbers are UNRELATED schemes (id 100 =
    Alexandria, not the ``map100`` Dali field). To match a folder by its map number, pass an FBG/mapid
    substring (e.g. ``map100`` / ``vgdl_map100``)."""
    index = build_field_index(game, verbose=True)
    tok = field.strip()
    if tok.isdigit() and int(tok) in ID_TO_FBG:        # a field id -> its folder (NOT a map<NNN> substring)
        folder = ID_TO_FBG[int(tok)]
        if folder in index:
            return folder, index[folder]
        raise FileNotFoundError(f"field id {tok} ({folder}) has no live field bundle -- not a forkable field")
    want = re.sub(r"^fbg_n\d+_", "", tok.lower())
    if tok.lower() in index:
        return tok.lower(), index[tok.lower()]
    hits = [f for f in index if want in f]
    if not hits:
        raise FileNotFoundError(f"no field matches {field!r}. Try: ff9mapkit list-fields {want}")
    if len(hits) > 1:
        raise ValueError(f"{field!r} matches {len(hits)} fields; be more specific. e.g. {sorted(hits)[:8]}")
    return hits[0], index[hits[0]]


def list_fields(pattern=None, game=None):
    """Sorted (folder, area, mapid) for all fields (optionally filtered by substring)."""
    index = build_field_index(game, verbose=False)
    pat = pattern.lower() if pattern else None
    out = []
    for folder in sorted(index):
        if pat and pat not in folder:
            continue
        try:
            area, mapid = parse_fbg_folder(folder)
        except ValueError:
            continue
        out.append((folder, area, mapid))
    return out


def _repo_root() -> Path:
    """Repo root (…/ff9mapkit/ff9mapkit/extract.py -> repo) -- to locate the user-local reference data
    (the HW manifest + the import-all archive). Both are gitignored, so callers degrade if absent."""
    return Path(__file__).resolve().parents[2]


def _manifest_field_names() -> dict:
    """{field_id: friendly name} from the (gitignored, user-local) HW `reference/field-manifest.tsv`, or
    {} if it isn't present. col2 = id, col3 = name (e.g. 'Memoria/Outside')."""
    p = _repo_root() / "reference" / "field-manifest.tsv"
    names: dict = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split("\t")
            if len(parts) >= 3 and parts[1].isdigit():
                names.setdefault(int(parts[1]), parts[2])
    return names


def _archive_folder_index(archive_dir=None) -> dict:
    """{UPPER-FBG: folder path} for an `import-all` archive (default `reference/all-fields-import`), or {}
    if that dir is absent -- so find_fields can show where a field was imported without requiring it."""
    base = Path(archive_dir) if archive_dir else (_repo_root() / "reference" / "all-fields-import")
    if not base.is_dir():
        return {}
    return {p.name.upper(): str(p) for p in base.glob("*/*") if p.is_dir()}


def find_fields(query, *, archive_dir=None) -> list:
    """Resolve a field id / name / FBG-or-EVT substring -> the matching real fields: a list of
    {id, fbg, evt, name, folder} dicts sorted by id. A DIGIT query is an EXACT id match; otherwise a
    case-insensitive substring over id / FBG folder / EVT name / friendly name. `name` is the friendly
    HW-manifest name when the manifest is present (else ''); `folder` is the field's subdir under the
    import-all archive when present (else None). PURE table lookup (the in-package FBG_TO_EVT) -- no
    install / UnityPy needed; the manifest name + archive folder are best-effort extras."""
    from ._fieldtable import FBG_TO_EVT
    q = str(query).strip()
    by_id = q.isdigit()
    qid = int(q) if by_id else None
    ql = q.lower()
    names = _manifest_field_names()
    folders = _archive_folder_index(archive_dir)
    rows = []
    for fbg, (fid, evt) in FBG_TO_EVT.items():
        name = names.get(fid, "")
        hit = (fid == qid) if by_id else (ql in f"{fid} {fbg} {evt} {name}".lower())
        if hit:
            rows.append({"id": fid, "fbg": fbg, "evt": evt, "name": name,
                         "folder": folders.get(fbg.upper())})
    rows.sort(key=lambda r: r["id"])
    return rows


# ---- event script (.eb) extraction: fork a field WITH its gateways/music/encounters -----
EVT_LANG = "us"                       # event binaries are per-language; the bytecode we scan is identical
_EVENTS_BUNDLE_CACHE = ".ff9mapkit-events-bundle.txt"


def _events_bundle(game=None):
    """The p0data bundle holding field event binaries (``eventbinary/field/...``). Cached next to the
    bundles; on a miss it's detected p0data7-first (where they historically live), so the common case
    loads one bundle, not all of them."""
    cache = _streaming_assets(game) / _EVENTS_BUNDLE_CACHE
    if cache.exists():
        name = cache.read_text(encoding="utf-8").strip()
        if name:
            return name
    UnityPy = _unitypy()
    bundles = sorted(_bundles(game),
                     key=lambda p: (0 if "p0data7." in os.path.basename(p) else 1, p))
    for path in bundles:
        try:
            env = UnityPy.load(path)
        except Exception:
            continue
        if any("eventbinary/field/" in k.lower() for k in env.container):
            name = os.path.basename(path)
            try:
                cache.write_text(name, encoding="utf-8")
            except OSError:
                pass
            return name
    return None


def event_name_for(field: str, game=None):
    """The ``EVT_<name>`` event-script name for an imported field's FBG folder, or None if it isn't a
    standard field map (world/special fields have no field event). Uses the baked FBG->event table."""
    folder, _ = resolve_field(field, game)
    rec = FBG_TO_EVT.get(folder)
    return rec[1] if rec else None


def extract_event_script(field: str, *, game=None, lang: str = EVT_LANG):
    """The compiled ``.eb`` bytes of a real field's event script (``lang``, default us), or None if it
    can't be located (no FBG->event mapping, or the binary isn't present). Used by ``import`` to
    extract gateways / music / encounters / movement from the real field -- it never raises, so a
    missing script just means the fork imports without that content (camera/walkmesh/art are
    unaffected). ``lang`` is also used by provisioning to extract the per-language blank base."""
    try:
        evt = event_name_for(field, game)
        if not evt:
            return None
        bundle = _events_bundle(game)
        if not bundle:
            return None
        env = _load_env(_streaming_assets(game) / bundle)
        want = f"eventbinary/field/{lang}/{evt}.eb".lower()
        for k, obj in env.container.items():
            kl = k.lower()
            if want in kl and kl.endswith(".eb.bytes"):
                return _raw_bytes(obj.read())
    except Exception:
        return None
    return None


def extract_mapconfig(field: str, *, game=None):
    """The field's **MapConfigData** bytes (``CommonAsset/MapConfigData/<EVT_name>``), or None if absent.

    This config drives the 3D-model LIGHTING the engine applies at field load (``fldmcf.cs``): per-FLOOR
    lights (``DMSMapLight``, keyed by the walkmesh floor) + per-object base colors (``DMSMapChar``) +
    per-floor shadow intensity/scale. A native fork that ships its own scene but NOT this config renders
    every field model untinted/bright (the cave's dim lighting is gone). Shipping it verbatim under the
    fork's event name restores it -- the per-floor lights key on the ``.bgi`` the native fork already
    carries verbatim, so the floors line up. Lives in the SAME bundle as the field event scripts
    (``_events_bundle``); never raises (a missing config just means the fork renders with default light)."""
    try:
        evt = event_name_for(field, game)
        if not evt:
            return None
        bundle = _events_bundle(game)
        if not bundle:
            return None
        env = _load_env(_streaming_assets(game) / bundle)
        want = f"commonasset/mapconfigdata/{evt}.bytes".lower()
        for k, obj in env.container.items():
            if want in k.lower():
                return _raw_bytes(obj.read())
    except Exception:
        return None
    return None


# ---- id-keyed event extraction (the chain walk) -----------------------------------------
# resolve_field()/event_name_for() are NAME-keyed (substring match on FBG folders), so a bare
# numeric field id mis-resolves. The graph walk needs id -> .eb DIRECTLY, so invert the baked table.
ID_TO_FBG = {rec[0]: folder for folder, rec in FBG_TO_EVT.items()}    # field id -> FBG folder
ID_TO_EVT = {rec[0]: rec[1] for folder, rec in FBG_TO_EVT.items()}    # field id -> EVT_ script name


class EventBundle:
    """The field event-script bundle loaded ONCE, with id -> ``.eb`` bytes lookup + per-id cache.

    For walking many fields (``import-chain``) without re-loading the bundle per field. Never raises on
    a miss: an id with no FBG/event mapping (world/special field) or whose binary is absent returns None,
    so the walk terminates that branch cleanly (same contract as ``extract_event_script``)."""

    def __init__(self, game=None, lang: str = EVT_LANG):
        bundle = _events_bundle(game)
        if not bundle:
            raise RuntimeError(
                "could not locate the field event bundle (eventbinary/field/...) in StreamingAssets/p0data*.bin")
        self.lang = lang
        env = _load_env(_streaming_assets(game) / bundle)
        marker = f"eventbinary/field/{lang}/"     # container keys carry a leading path -> substring match
        self._by_evt = {}
        for k, obj in env.container.items():
            kl = k.lower()
            i = kl.find(marker)
            if i >= 0 and kl.endswith(".eb.bytes"):
                self._by_evt[kl[i + len(marker):-len(".eb.bytes")]] = obj
        self._cache: dict = {}

    def eb_for_id(self, field_id: int):
        """``.eb`` bytes for a field id, or None (no FBG/event mapping, or binary absent)."""
        fid = int(field_id)
        if fid in self._cache:
            return self._cache[fid]
        data = None
        evt = ID_TO_EVT.get(fid)
        if evt is not None:
            obj = self._by_evt.get(evt.lower())
            if obj is not None:
                data = _raw_bytes(obj.read())
        self._cache[fid] = data
        return data


def _inst_tbl(it) -> str:
    """One ``InitObject`` instance as a TOML inline table -- the spawn ``arg`` (+ the resolved x/z when
    known, informational; build reads only ``arg`` and the entry self-positions)."""
    parts = [f"arg = {int(it.get('arg', 0))}"]
    if it.get("x") is not None and it.get("z") is not None:
        parts += [f"x = {it['x']}", f"z = {it['z']}"]
    return "{ " + ", ".join(parts) + " }"


def _object_block(o, fn: str, seq_fns=None) -> str:
    """A ``[[object]]`` graft block: the verbatim-entry sidecar + what ``build`` needs to append + arm
    it. ``carry_tags`` is emitted only for an ``init_only`` carry (a ``clean`` object carries whole);
    ``needs_d9`` only for a ``Main_Init``-D9-positioned object (else the entry self-positions); ``seqs``
    (``seq_fns`` = ``[(entry, sidecar)]``) only when the closure carries STARTSEQ helpers for this object."""
    lines = [f'[[object]]\nbin = "{fn}"\nkind = "{o["kind"]}"\ndonor_idx = {o["donor_idx"]}']
    if o.get("donor_player_entry") is not None:
        lines.append(f'donor_player_entry = {o["donor_player_entry"]}')
    dpes = o.get("donor_player_entries") or []
    if len(dpes) > 1:                                    # multi-DefinePlayerCharacter -> the grafter normalizes ALL
        lines.append("donor_player_entries = [" + ", ".join(str(p) for p in dpes) + "]")
    if o["graft_safety"] == "init_only":
        lines.append("carry_tags = [" + ", ".join(str(t) for t in o["carry_tags"]) + "]")
    if o.get("needs_d9"):
        lines.append("needs_d9 = { " + ", ".join(f"{k} = {v}" for k, v in sorted(o["needs_d9"].items())) + " }")
    lines.append("instances = [" + ", ".join(_inst_tbl(it) for it in o["instances"]) + "]")
    if seq_fns:
        lines.append("seqs = [" + ", ".join(f'{{ entry = {ei}, bin = "{sfn}" }}' for ei, sfn in seq_fns) + "]")
    return "\n".join(lines)


def _object_stub(o) -> str:
    """A REFUSED object (its render funcs reference field state a fork lacks) -> a ``[[prop]]``/``[[npc]]``
    author stub (the lossy player-clone path, to fix up by hand)."""
    inst = o["instances"][0] if o["instances"] else {}
    x = inst.get("x") if inst.get("x") is not None else 0
    z = inst.get("z") if inst.get("z") is not None else 0
    mref = f'"{o["model"]}"' if isinstance(o["model"], str) else str(o["model_id"])
    face = f"\nface = {o['face']}" if o.get("face") is not None else ""
    head = "# REFUSED graft (its render funcs reference field state a fork lacks) -- author by hand:\n"
    if o["kind"] == "npc":
        short = o["model"].split("_")[-1] if isinstance(o["model"], str) else str(o["model_id"])
        return (f'{head}[[npc]]\nname = "{short}_{o["donor_idx"]}"\nmodel = {mref}\npos = [{x}, {z}]\n'
                f'dialogue = "..."   # TODO: author this NPC\'s dialogue (text not carried){face}')
    pose = f"\npose = {o['pose']}" if o.get("pose") is not None else ""
    return f'{head}[[prop]]\nmodel = {mref}{pose}\npos = [{x}, {z}]{face}'


def _donor_battle_song(field_id, enc, game):
    """The donor field's real random-battle BGM (akao song-play id) for this encounter's PRIMARY scene, or
    ``None`` when unknown / not mapped / the install can't be read. FF9 keys the battle song on
    ``(field id, scene)`` (``battle_bgm``); a fork to a custom id loses that lookup, so ``import`` prefills
    ``[encounter] battle_music`` and the build reproduces it via a SCENE-keyed ``Music:`` BattlePatch line.
    Best-effort: never fails an import over BGM detection."""
    if field_id is None or not enc:
        return None
    try:
        from . import battle_bgm as _bbgm
        return _bbgm.song(field_id, int(enc["scenes"][0]), game)
    except Exception:                                    # noqa: BLE001 -- BGM is a nicety, never block the fork
        return None


def _imported_content_toml(eb_bytes, *, out_dir=None, name="field", id_remap=None, live_seams=False,
                           graft_player_funcs=False, carry_text=False, field_id=None, game=None,
                           graft_savepoint=False):
    """field.toml blocks (gateways / encounter / music / ladders) + the control-direction value,
    extracted LIVE from a real field's ``.eb``. Returns (blocks_text, control_dir, summary). blocks_text
    is appended at the end of the toml; control_dir (or None) goes in the [camera] block; summary feeds
    the CLI. Ladders carry a binary climb, so they're emitted only when ``out_dir`` is given (each climb
    written verbatim to a ``<name>.ladder<i>.climb.bin`` sidecar that ``build`` grafts faithfully).

    ``id_remap`` (import-chain / campaign): a ``{real_dest_id: new_id}`` map. When given, each gateway's
    ``to`` is RETARGETED -- in-chain targets become the sibling NEW id; targets OUTSIDE the chain are NOT
    emitted as a live gateway (that would warp the player back into the live game) but as a commented
    seam stub for the author. ``live_seams=True`` keeps out-of-chain targets as live doors instead. When
    ``id_remap is None`` the output is byte-identical to before (single-field ``import`` is unchanged).
    NOTE: the retarget touches ONLY gateway ``to`` ids -- the encounter ``scene =`` (a battle-scene id,
    not a field) is deliberately left alone."""
    content = eventscan.scan_content(eb_bytes)
    parts = []
    gws = content["gateways"]
    n_retargeted = n_seamed = n_story_branch = 0
    # #2b (FORK_FIDELITY.md): a STORY-GATED door (its firing/destination guarded by a complex GLOB-flag
    # conditional) is carried VERBATIM -- the declarative rebuild can't reproduce that state machine. Route
    # self-contained gated entries to a [[gateway_carry]] block (+ a .gatewayN.bin sidecar) and EXCLUDE their
    # zones from the declarative emission below. Needs an out_dir (the sidecar); ref-bearing gated entries
    # (~30%) can't be door-only-carried -> they fall through to declarative + a warning.
    gentries = eventscan.scan_gateway_entries(eb_bytes) if out_dir is not None else []
    carry = [x for x in gentries if x["story_gated"] and x["self_contained"]]
    carried_zones = {tuple(map(tuple, x["zone"])) for x in carry}
    n_gateway_carry = len(carry)
    n_gateway_gated_seam = sum(1 for x in gentries if x["story_gated"] and not x["self_contained"])
    if gws:
        if id_remap is None:
            parts.append(
                "# --- EXITS imported from the real field (LIVE). `to` is the REAL destination field id --\n"
                "# retarget each to your own room ids, or leave them to walk back into the live game. ---")
        else:
            parts.append("# --- EXITS retargeted to this chain's own field ids (import-chain). "
                         "Out-of-chain exits are commented seam stubs. ---")
        # #2 (FORK_FIDELITY.md): a STORY-BRANCH door = one zone with >1 DISTINCT destination -- FF9's
        # if(flag){Field(A)}else{Field(B)} stacked door. scan_gateways emits each branch as its own [[gateway]]
        # at that shared zone; left ungated BOTH arm in the fork (the player hits the wrong branch). Group by
        # zone here (scan_gateways doesn't carry the flag -- scan_all_warps does) to mark them for gating.
        dests_by_zone: dict = {}
        for g in gws:
            dests_by_zone.setdefault(tuple(map(tuple, g["zone"])), set()).add(int(g["to"]))
        for g in gws:
            if tuple(map(tuple, g["zone"])) in carried_zones:
                continue                                          # carried VERBATIM as a [[gateway_carry]] below
            zone = ", ".join(f"[{x}, {z}]" for x, z in g["zone"])
            raw_to = int(g["to"])
            cond = len(dests_by_zone[tuple(map(tuple, g["zone"]))]) > 1
            n_story_branch += 1 if cond else 0
            note = ("# STORY-BRANCH door: this zone has >1 conditional exit (the real field picks one by story\n"
                    "# flag). Gate each branch with requires_flag / requires_flag_clear so only the right one\n"
                    "# arms per beat -- else both fire and you hit the wrong exit.\n") if cond else ""
            stub = ("\n# requires_flag =        # the GlobBool that selects THIS branch (flags-inspect to find it)"
                    if cond else "")
            if id_remap is None or raw_to in id_remap:
                to = id_remap[raw_to] if id_remap else raw_to
                parts.append(f"{note}[[gateway]]\nto = {to}\nentrance = {g['entrance']}\nzone = [{zone}]{stub}")
                n_retargeted += 1 if id_remap is not None else 0
            elif live_seams:
                parts.append(f"{note}# SEAM (live): real field {raw_to} -- a door back into the live game\n"
                             f"[[gateway]]\nto = {raw_to}\nentrance = {g['entrance']}\nzone = [{zone}]{stub}")
                n_seamed += 1
            else:
                parts.append(f"# SEAM (out-of-chain): real field {raw_to} via this zone -- author by hand.\n"
                             f"# [[gateway]]\n# to = {raw_to}\n# entrance = {g['entrance']}\n# zone = [{zone}]")
                n_seamed += 1
    if carry:                                                     # the verbatim story-gated doors + sidecars
        out_path = Path(out_dir)
        parts.append("# --- STORY-GATED doors carried VERBATIM (their conditional state machine preserved; the\n"
                     "# GLOB conditions read the [startup]-preset story state). Destinations are the REAL field\n"
                     "# ids -- add `retarget = { <real id> = <your id> }` to redirect into your own rooms. ---")
        for x in carry:
            fn = f"{name}.gateway{x['entry_idx']}.bin"
            out_path.joinpath(fn).write_bytes(x["entry_bytes"])
            dests = sorted({fid for fid, _ent in x["fields"]})
            retarget = ""
            if id_remap:                                          # import-chain: pre-fill in-chain retargets
                pairs = [(fid, id_remap[fid]) for fid in dests if fid in id_remap]
                if pairs:
                    retarget = "\nretarget = { " + ", ".join(f"{a} = {b}" for a, b in pairs) + " }"
            parts.append(f'[[gateway_carry]]\nbin = "{fn}"{retarget}\n'
                         f"# verbatim story-gated door (real dest field id(s): {', '.join(map(str, dests))}). "
                         f"To redirect: retarget = {{ {dests[0]} = <your id> }}")
    enc = content["encounter"]
    donor_song = _donor_battle_song(field_id, enc, game) if enc else None
    if enc:
        block = f"[encounter]\nscene = {enc['scenes'][0]}\nfreq = {enc['freq']}"
        if len(set(enc["scenes"])) != 1:
            block += f"\nscenes = [{', '.join(str(s) for s in enc['scenes'])}]"
        if donor_song:                                    # non-zero only: 0 == the build's default Battle Theme
            block += (f"\nbattle_music = {donor_song}   # the donor's real battle song (akao song-play id), "
                      f"auto-detected from the real field -- a mint loses it (build emits a Music: line)")
        parts.append("# random battles imported from the real field (build adds the after-battle "
                     "reinit)\n" + block)
    if content["music"] is not None:
        parts.append(f"# field BGM imported from the real field\n[music]\nsong = {content['music']}")
    lads = content["ladders"]
    n_ladders = 0
    if lads and out_dir is not None:                    # ladders carry a binary climb -> need out_dir
        out_path = Path(out_dir)
        from .content import ladder as _ladder
        blocks = ["# --- LADDER(s) imported from the real field (LIVE) -- the EXACT climb (the real,\n"
                  "# perspective-correct jump arcs), verbatim. Walk into the zone -> '!' -> press action\n"
                  "# to climb; the climb reads your height to go up or down. The zone is auto-widened to\n"
                  "# span BOTH climb ends (the real zone only covers the entry side -> a fork couldn't\n"
                  "# climb back); tighten it if you don't want the '!' along the whole column. ---"]
        for i, lad in enumerate(lads):
            fn = f"{name}.ladder{i}.climb.bin"
            (out_path / fn).write_bytes(lad["climb"])
            # the concurrent helper entries the climb launches via STARTSEQ (e.g. the SetPitchAngle
            # forward-lean) -- one sidecar per referenced entry; build auto-loads them by the climb's
            # STARTSEQ refs + this naming, grafts them at free slots, and remaps the climb's args.
            for ei, sbytes in lad.get("sequences", {}).items():
                (out_path / f"{name}.ladder{i}.seq{ei}.bin").write_bytes(sbytes)
            zone_pts = _ladder.widen_zone_for_climb(lad["zone"], lad["climb"])
            zone = ", ".join(f"[{x}, {z}]" for x, z in (zone_pts or []))
            blocks.append(f'[[ladder]]\nzone = [{zone}]\nclimb = "{fn}"')
        parts.append("\n\n".join(blocks))
        n_ladders = len(lads)
    jmps = content.get("jumps") or []
    n_jumps = 0
    if jmps and out_dir is not None:                    # jumps carry a binary arc -> need out_dir
        out_path = Path(out_dir)
        blocks = ["# --- JUMP(s) imported from the real field (LIVE) -- navigable ledge/gap hops (Ice\n"
                  "# Cavern style). Each carries the EXACT, perspective-tuned jump arc verbatim (the real\n"
                  "# world coords -- only copyable, like a ladder climb). trigger=\"action\" = walk to the\n"
                  "# ledge -> '!' -> press the button to hop; trigger=\"tread\" = auto-hop on walk-in. The\n"
                  "# arc moves the player along a parabola, so the zone must sit at the take-off ledge. ---"]
        for i, jp in enumerate(jmps):
            fn = f"{name}.jump{i}.bin"
            (out_path / fn).write_bytes(jp["jump"])
            zone = ", ".join(f"[{x}, {z}]" for x, z in (jp["zone"] or []))
            extra = "" if jp.get("bubble", True) else "\nbubble = false"
            blocks.append(f'[[jump]]\nzone = [{zone}]\njump = "{fn}"\ntrigger = "{jp["trigger"]}"{extra}')
        parts.append("\n\n".join(blocks))
        n_jumps = len(jmps)
    # faithful object carry. The STARTSEQ-helper closure (graft_seq_helpers) is a pure fidelity win -- it
    # carries the benign Seq an object launches, un-refusing it -- so it's ALWAYS on: the default path reads
    # it via scan_content (objects_verbatim is scanned with it), and the graft_player_funcs path (which also
    # touches the fork PLAYER, opt-in) requests it directly. graft mode flips init_only -> whole-entry; the
    # closure flips refuse -> graftable. docs/OBJECT_CARRY.md S2 v1.5.
    objs = ((eventscan.scan_objects_verbatim(eb_bytes, graft_player_funcs=True, carry_text=carry_text,
                                             graft_seq_helpers=True, graft_savepoint=graft_savepoint)
             if graft_player_funcs else content.get("objects_verbatim")) or [])
    n_objects = 0
    n_save_moogle = 0
    if objs and out_dir is not None:                    # objects carry a verbatim entry -> need out_dir
        out_path = Path(out_dir)
        blocks = ["# --- OBJECTS imported from the real field -- the persistent NPCs/props (set-dressing the\n"
                  "# fork would otherwise DROP: the cask, signs, the save moogle's barrel, ...). Each is\n"
                  "# carried by GRAFTING the object's REAL .eb entry VERBATIM (renders byte-identical -- not a\n"
                  "# lossy player-clone). `bin` is the entry sidecar; `carry_tags` (init_only objects) keeps\n"
                  "# only the render-defining funcs, dropping interactive funcs that call a player function a\n"
                  "# blank fork lacks (those can't port). A REFUSED object falls back to a [[prop]]/[[npc]]\n"
                  "# author stub. The DIALOGUE text of a talkable NPC is still not carried -- author it. ---"]
        for i, o in enumerate(objs):
            if o["graft_safety"] in ("clean", "init_only"):
                fn = f"{name}.object{i}.bin"
                (out_path / fn).write_bytes(o["entry_bytes"])     # the verbatim entry build grafts
                seq_fns = []                                       # the closure's STARTSEQ helper sidecars
                for h in (o.get("seqs") or []):
                    sfn = f"{name}.object{i}.seq{h['entry']}.bin"
                    (out_path / sfn).write_bytes(h["bytes"])
                    seq_fns.append((int(h["entry"]), sfn))
                blocks.append(_object_block(o, fn, seq_fns))
            else:
                blocks.append(_object_stub(o))
        parts.append("\n\n".join(blocks))
        n_objects = len(objs)
        # the save-Moogle marker (docs/SAVEPOINT.md): when --save-moogle carried a real save point, flag it so
        # the build + the author see it as ONE faithful save point (the hidden Moogle + book/feather/tent are in
        # the [[object]] blocks above; its pose surgery in the [[player_func]] blocks). It's the user-facing
        # handle -- and the forward-compatible slot for a future AUTHORED save Moogle (jump arc + distance).
        if graft_savepoint and any(o.get("model") == "GEO_NPC_F0_MOG" for o in objs):
            src = f'from = "{field_id}"\n' if field_id is not None else ""
            # the save-sequence DIRECTOR (donor entry-0 tag-1) puppeteers the Moogle via shared MAP vars; carry
            # it too -- the object carry misses it (it's main-loop logic, not an object) so without it the Moogle
            # has no driver. Emitted as a gitignored sidecar the build grafts into the fork's empty entry-0 tag-1.
            director_ref = ""
            director = eventscan.extract_savepoint_director(eb_bytes)
            if director and out_dir is not None:
                dfn = f"{name}.savemoogle_director.bin"
                (Path(out_dir) / dfn).write_bytes(director)
                director_ref = f'director = "{dfn}"\n'
            parts.append("# --- SAVE MOOGLE: a faithful FF9 save point, carried VERBATIM from the donor field --\n"
                         "# the hidden Moogle pops out of its barrel + the full save flourish, exactly as the\n"
                         "# original (cluster = the [[object]]+[[player_func]] blocks above; `director` = the donor's\n"
                         "# save-sequence loop that drives the Moogle through shared MAP vars). ---\n"
                         f"[[save_moogle]]\n{src}{director_ref}carried = true")
            n_save_moogle = 1
    # player-function graft (docs/PLAYER_GRAFT.md): the donor player gesture funcs a carried object
    # RunScripts -- carried onto the fork player so the INTERACTIONS fire (the cask turns to face you on
    # examine, the boxes gesture). Emitted ONLY with graft_player_funcs; CLEAN funcs always, plus TEXT funcs
    # when --carry-text ships the words they show (else a text func stays refused -> its object init_only).
    n_player_funcs = 0
    all_pfuncs = (eventscan.scan_player_funcs(eb_bytes, graft_savepoint=graft_savepoint)
                  if (graft_player_funcs and out_dir is not None) else [])
    pf_ok = {"clean", "text"} if carry_text else {"clean"}
    if graft_player_funcs and out_dir is not None:
        pfuncs = [s for s in all_pfuncs if s["safety"] in pf_ok]
        if pfuncs:
            out_path = Path(out_dir)
            blocks = ["# --- PLAYER FUNCTION(S) grafted onto the fork player so the carried objects'\n"
                      "# INTERACTIONS fire (the cask EXAMINE turn, the box gestures). Each is a real donor player\n"
                      "# gesture func (turn/animation) carried VERBATIM at a fresh tag; the build remaps each\n"
                      "# object's RunScript(player, tag) to it + splices the donor's animation packs. ---"]
            for i, p in enumerate(pfuncs):
                fn = f"{name}.playerfunc{i}.bin"
                (out_path / fn).write_bytes(p["body"])
                packs = ", ".join("[" + ", ".join(str(x) for x in pk) + "]" for pk in p["donor_init_packs"])
                blocks.append(f'[[player_func]]\nbin = "{fn}"\ndonor_tag = {p["donor_tag"]}\n'
                              f'safety = "{p["safety"]}"\ndonor_init_packs = [{packs}]')
            parts.append("\n\n".join(blocks))
            n_player_funcs = len(pfuncs)
    # faithful TEXT CARRY (docs/TEXT_CARRY.md): ship the donor's referenced field text VERBATIM + remap the
    # grafted windows so the forked interactions show the REAL words (a carried NPC's talk, a grafted text
    # player func). Needs graft_player_funcs (so the carrying objects/funcs exist) + the field id + game (to
    # read the donor's per-language .mes). The plan is written to a gitignored .carrytext.json sidecar the
    # build consumes; an empty plan (no grafted windows) emits no [carry_text].
    n_carry_text = 0
    if carry_text and graft_player_funcs and out_dir is not None and field_id is not None:
        from .content import textcarry as _tc
        loader = _tc._field_text_loader(field_id, game=game)
        plan = _tc.collect_carry(eb_bytes, objs, all_pfuncs, field_id, loader)
        if plan:
            fn = f"{name}.carrytext.json"
            _tc.write_sidecar(Path(out_dir) / fn, plan, field=field_id)
            parts.append(
                "# --- TEXT CARRY: the donor field's referenced dialogue text, shipped VERBATIM (per language)\n"
                "# + the grafted windows remapped to it, so the carried NPCs' talk + grafted text interactions\n"
                "# show the REAL words. This is the FAITHFUL path (vs `import --dialogue`'s editable stubs); the\n"
                "# words are SE-derived -> the .carrytext.json sidecar is gitignored. Remove this block (and the\n"
                "# sidecar) to author the dialogue yourself instead. ---\n"
                f'[carry_text]\nbin = "{fn}"')
            n_carry_text = len(plan)
    summary = {"gateways": len(gws), "encounter": enc is not None, "music": content["music"],
               "battle_music": donor_song,   # the donor's real battle BGM (auto-detected), or None if unknown/default
               "control_direction": content["control_direction"], "ladders": n_ladders,
               "jumps": n_jumps, "objects": n_objects, "player_funcs": n_player_funcs,
               "carry_text": n_carry_text, "save_moogle": n_save_moogle,
               "spawn_flash": sum(1 for o in objs if o.get("spawn_flash")),   # P6.1: Init pose != rest -> flashes on a fork
               "spawn_flash_fixed": (1 if (graft_savepoint and n_save_moogle) else 0),
               "gateways_retargeted": n_retargeted, "gateways_seamed": n_seamed,
               "story_branch": n_story_branch,   # #2: doors sharing a zone (gate each with requires_flag)
               "gateway_carry": n_gateway_carry,         # #2b: story-gated doors carried VERBATIM
               "gateway_gated_seam": n_gateway_gated_seam}   # #2b: story-gated but ref-bearing -> can't carry yet
    return "\n\n".join(parts), content["control_direction"], summary


def _content_for_import(field: str, game, *, out_dir=None, name="field", id_remap=None, live_seams=False,
                        graft_player_funcs=False, carry_text=False, graft_savepoint=False):
    """(content_blocks, control_dir, summary) for a field's import. Locates + scans the real .eb;
    returns ("", None, None) if it can't (no mapping / no game / UnityPy absent) so import still works.
    ``out_dir``/``name`` let ladder climbs be written as sidecars next to the field.toml.
    ``id_remap``/``live_seams`` retarget gateway ``to`` ids for import-chain (see _imported_content_toml).
    ``graft_player_funcs`` emits the player-function graft (the carried objects' interactions).
    ``carry_text`` additionally ships the donor's referenced dialogue text verbatim + remaps the grafted
    windows (the faithful text carry, docs/TEXT_CARRY.md) -- needs the resolved field id + game install."""
    eb_bytes = extract_event_script(field, game=game)
    if not eb_bytes:
        return "", None, None
    # Resolve the donor's real field id for EVERY import: carry_text / graft_savepoint need it, AND the
    # encounter block uses it to auto-detect the donor's battle BGM (battle_bgm keys on the field id). It's a
    # pure table lookup (no install), so it's cheap and best-effort -- None just disables the BGM prefill.
    from .dialogue import _resolve_field_id
    try:
        fid = _resolve_field_id(field)
    except (FileNotFoundError, ValueError):
        fid = None
    return _imported_content_toml(eb_bytes, out_dir=out_dir, name=name, id_remap=id_remap,
                                  live_seams=live_seams, graft_player_funcs=graft_player_funcs,
                                  carry_text=carry_text, field_id=fid, game=game,
                                  graft_savepoint=graft_savepoint)


def _content_section(content_blocks: str, x: int, z: int) -> str:
    """The trailing content of the field.toml: the LIVE imported blocks, or a commented gateway stub
    when nothing was imported (the old hand-authoring hint)."""
    if content_blocks:
        return content_blocks + "\n"
    return ("# [[gateway]]\n# to = 100          # destination field id\n# entrance = 204\n"
            "# zone = [[-200, 200], [200, 200], [200, 400], [-200, 400]]\n")


def find_field(field: str, game=None, bundle: str | None = None):
    """Locate a field's bundle + container paths. Returns (bundle_path, folder, {role: key}, env).

    Uses the cached field index unless `bundle` (e.g. 'p0data141.bin') is given to short-circuit it."""
    sa = _streaming_assets(game)
    folder = None
    if not bundle:
        folder, bundle = resolve_field(field, game)
    env = _load_env(sa / bundle)
    if folder is None:                                  # explicit bundle: match within it
        want = re.sub(r"^fbg_n\d+_", "", field.strip().lower())
        folders = {m.group(1) for k in env.container
                   if (m := re.search(r"fieldmaps/([^/]+)/", k.lower()))}
        hits = [f for f in folders if want in f]
        if not hits:
            raise FileNotFoundError(f"field {field!r} not in {bundle}")
        folder = field.strip().lower() if field.strip().lower() in hits else hits[0]
    roles = {}
    for k in env.container:
        kl = k.lower()
        if f"fieldmaps/{folder}/" not in kl:
            continue
        base = kl.rsplit("/", 1)[-1]
        if base == "atlas.png":
            roles["atlas"] = k
        elif base.endswith(".bgi.bytes"):
            roles["bgi"] = k
        elif base.endswith(".bgs.bytes") and not re.search(r"_(es|fr|gr|it|jp)\.bgs", base):
            roles["bgs"] = k                            # default (us/en) scene
    return str(sa / bundle), folder, roles, env


def field_camera_info(field: str, *, game=None, bundle: str | None = None) -> dict | None:
    """A field's lens, read cheaply -- pitch/FOV/scrolling/camera-count from the scene `.bgs` ONLY (no
    walkmesh/atlas extraction). Returns None if the install/scene can't be read (so callers degrade
    gracefully). Read-only. Used by `fork-report` (the Camera axis) and reusable for a room finder."""
    try:
        _, _, roles, env = find_field(field, game=game, bundle=bundle)
        if "bgs" not in roles:
            return None
        objs = {k: v for k, v in env.container.items()}
        cams = bgs.parse_cameras(_raw_bytes(objs[roles["bgs"]].read()))
        if not cams:
            return None
        c0 = cams[0]
        fov = cam.decompose(c0)["fov_x_deg"]
        return {
            "pitch": round(cam.pitch_deg(c0), 1),
            "fov": round(fov, 1) if fov else None,
            "scrolling": bool(c0.range[0] > 384 or c0.range[1] > 448),
            "count": len(cams),
            # the camera's visible extent (screen units). range_h is the physically-meaningful "how far back"
            # signal -- FF9's projection is orthographic-like (k~0.93) so FOV is a scale artifact, not a frustum.
            "range_w": int(c0.range[0]), "range_h": int(c0.range[1]),
        }
    except Exception:
        return None


def _pt_in_quad(px, pz, quad) -> bool:
    """True if (px, pz) is inside the convex polygon ``quad`` ([x, z] corners), top-down. Convex
    same-side-of-every-edge test (the trigger zones are convex quads, the IsInQuad norm)."""
    n = len(quad)
    if n < 3:
        return False
    sign = 0
    for i in range(n):
        ax, az = quad[i]
        bx, bz = quad[(i + 1) % n]
        cross = (bx - ax) * (pz - az) - (bz - az) * (px - ax)
        if cross != 0:
            s = 1 if cross > 0 else -1
            if sign == 0:
                sign = s
            elif s != sign:
                return False
    return True


def _trigger_zones(field: str, game=None) -> list:
    """Every trigger polygon in a field's event script (exits + interaction/trap regions), or [] if the
    script can't be read. Lets ``extract_field`` keep the spawn off a trigger without the caller plumbing
    the zones through. Never raises -- a missing script just means no zones to avoid."""
    try:
        eb_bytes = extract_event_script(field, game=game)
        return eventscan.scan_region_zones(eb_bytes) if eb_bytes else []
    except Exception:
        return []


def cache_field(field_id, *, game=None, force=False) -> dict:
    """Extract a real field's camera + walkmesh into the WORKSPACE CACHE (gitignored), idempotently.

    The centralized alternative to copying a ``.bgx`` next to every BG-borrow project: extract a room ONCE
    into ``provision.field_cache_dir(field_id)`` and have any number of tomls reference that single copy.
    Skips the extraction when the camera is already cached (unless ``force``). Returns
    ``{dir, camera, walkmesh, cached}`` (``camera``/``walkmesh`` are Paths; ``walkmesh`` is None if absent).
    Needs the install + UnityPy (lazily, via :func:`extract_field`)."""
    from . import provision
    dest = provision.field_cache_dir(field_id)
    cam = dest / "camera.bgx"
    wmp = dest / "walkmesh.bgi"
    if cam.is_file() and not force:
        return {"dir": dest, "camera": cam, "walkmesh": wmp if wmp.is_file() else None, "cached": True}
    dest.mkdir(parents=True, exist_ok=True)
    meta = extract_field(str(field_id), dest, game=game)
    return {"dir": dest, "camera": cam, "walkmesh": wmp if wmp.is_file() else None, "cached": False,
            "meta": meta}


def extract_field(field: str, out_dir, *, game=None, bundle=None, want_atlas=False, avoid_zones=None) -> dict:
    """Extract a real field's camera + walkmesh (+ optional atlas) to `out_dir`; return metadata.

    ``avoid_zones`` ([x, z]-corner quads) are trigger polygons the spawn must stay OUT of (so a forked
    field doesn't instant-warp on arrival); when None they're auto-scanned from the field's event script."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path, folder, roles, env = find_field(field, game=game, bundle=bundle)
    if "bgs" not in roles or "bgi" not in roles:
        raise FileNotFoundError(f"{folder}: missing .bgs/.bgi (have {sorted(roles)})")

    objs = {k: v for k, v in env.container.items()}
    bgs_bytes = _raw_bytes(objs[roles["bgs"]].read())
    bgi_bytes = _raw_bytes(objs[roles["bgi"]].read())

    cameras = bgs.parse_cameras(bgs_bytes)
    wm = bgi.BgiWalkmesh.from_bytes(bgi_bytes)
    area, mapid = parse_fbg_folder(folder)

    # write the camera as a borrowable .bgx (reference + drives movement/scroll) + the raw walkmesh
    (out / "camera.bgx").write_text("".join(cam.format_bgx_camera(c) for c in cameras), encoding="utf-8")
    (out / "walkmesh.bgi").write_bytes(bgi_bytes)
    if want_atlas and "atlas" in roles:
        try:
            objs[roles["atlas"]].read().image.save(out / "atlas.png")
        except Exception:
            pass

    c0 = cameras[0]
    d = cam.decompose(c0)
    scrolling = c0.range[0] > 384 or c0.range[1] > 448
    # real .bgi verts are corner-origin per FLOOR; world_vert = vert + orgPos + floor.org puts the
    # whole (multi-floor) walkmesh in the world (camera) frame, on the painted art + the engine frame.
    wv = wm.world_verts()
    wx = [p[0] for p in wv]
    wz = [p[2] for p in wv]
    ox, oz = wm.orgPos.x, wm.orgPos.z         # header offset (for the charPos spawn guesses below)
    # spawn: charPos is stored per-field in EITHER the corner frame or already world, and is unreliable
    # for multi-floor fields. Prefer it only if it lands on the walkmesh, on-camera, AND clear of every
    # trigger zone; else spawn at the centre of the ON-CAMERA walkmesh (a real walkmesh often runs far
    # past the screen into gated tunnels, so the player should appear on-screen). The trigger-zone check
    # matters because a field's stored charPos is usually right at the MAIN door -- which is the exit
    # that warps you BACK out -- so a naive spawn lands inside that gateway and instant-warps on arrival.
    bx0, bx1, bz0, bz1 = min(wx), max(wx), min(wz), max(wz)
    rw, rh = c0.range
    trigger_zones = avoid_zones if avoid_zones is not None else _trigger_zones(field, game=game)
    def _inb(px, pz):
        return bx0 <= px <= bx1 and bz0 <= pz <= bz1
    def _oncam(px, pz):
        cx, cy = cam.to_canvas((px, 0.0, pz), c0)
        return 0 <= cx <= rw and 0 <= cy <= rh
    def _clear(px, pz):                                       # outside every exit/trigger polygon
        return not any(_pt_in_quad(px, pz, q) for q in trigger_zones)
    _cp = [(wm.charPos.x + ox, wm.charPos.z + oz), (wm.charPos.x, wm.charPos.z)]
    # c.1: on a SPLIT walkmesh (e.g. a shop counter walls the behind-counter pocket off from the customer
    # area) keep the spawn in the MAIN region -- the connected walkmesh component with the most on-camera
    # verts -- so a fork doesn't strand the player in a trapped pocket (the donor charPos is often that
    # pocket: a cutscene staging spot). No-op on a single-region walkmesh -> byte-identical there.
    _comps = wm.tri_components()
    _multi = len(_comps) > 1
    if _multi:
        _oncam_idx = {i for i in range(len(wx)) if _oncam(wx[i], wz[i])}
        _main_vtx = {vi for t in max(_comps, key=lambda c: len({vi for t in c for vi in wm.tris[t].vtx}
                                                               & _oncam_idx)) for vi in wm.tris[t].vtx}
        def _in_main(px, pz):                                 # the nearest walkmesh vert is in the main region
            vi = min(range(len(wx)), key=lambda i: (wx[i] - px) ** 2 + (wz[i] - pz) ** 2)
            return vi in _main_vtx
    else:
        def _in_main(px, pz):
            return True
    _oncam_verts = [(wx[i], wz[i]) for i in range(len(wx))
                    if _oncam(wx[i], wz[i]) and (not _multi or i in _main_vtx)]
    _clear_oncam = [p for p in _oncam_verts if _clear(*p)]
    mcx = mcz = None
    if _oncam_verts:                                          # the visible centroid (the on-screen "middle")
        mcx = sum(p[0] for p in _oncam_verts) / len(_oncam_verts)
        mcz = sum(p[1] for p in _oncam_verts) / len(_oncam_verts)
    # #9 spawn: prefer a REAL per-entrance ARRIVAL -- where the engine actually spawns the player walking in a
    # door -- over the donor charPos (often a cutscene staging spot) or a synthetic centroid. The player Init's
    # D9(0)/D9(4) arrival blocks are world coords in the same frame as the walkmesh; among those valid HERE
    # (in-bounds, on-camera, clear of triggers, in the main region) take the one nearest the visible centroid:
    # the natural main-entrance spawn, and FAITHFUL (a coord the game uses). Falls through to the c.1 charPos/
    # centroid cascade when none qualifies (a single-spawn field, a frame mismatch, all arrivals off-screen/gated)
    # -> byte-identical there. A synth fork can't reconstruct the per-DOOR table (gateways are retargeted), but
    # the default landing now matches the real field's main arrival instead of a centroid guess.
    _arrivals = []
    try:
        _aeb = extract_event_script(field, game=game)
        if _aeb:
            _arrivals = [(ax, az) for ax, az, _f in eventscan.scan_player_arrivals(_aeb)["arrivals"]]
    except Exception:                                         # a missing/odd script just disables the preference
        _arrivals = []
    _valid_arr = [p for p in _arrivals if _inb(*p) and _oncam(*p) and _clear(*p) and _in_main(*p)]
    _spawn = None
    if _valid_arr and mcx is not None:                       # the real arrival nearest the visible centre
        _spawn = min(_valid_arr, key=lambda p: (p[0] - mcx) ** 2 + (p[1] - mcz) ** 2)
    if _spawn is None:                                        # c.1: a trustworthy charPos (clear + in-main)
        _spawn = next((p for p in _cp if _inb(*p) and _oncam(*p) and _clear(*p) and _in_main(*p)), None)
    if _spawn is None and _oncam_verts:                       # nearest-to-centre visible vert, clear if any
        pool = _clear_oncam or _oncam_verts
        _spawn = min(pool, key=lambda p: (p[0] - mcx) ** 2 + (p[1] - mcz) ** 2)
    if _spawn is None:                                        # no on-camera verts: in-bounds / centroid
        _spawn = next((p for p in _cp if _inb(*p) and _in_main(*p)), (sum(wx) / len(wx), sum(wz) / len(wz)))
    _spawn = [round(_spawn[0]), round(_spawn[1])]
    meta = {
        "field": folder,
        "bundle": os.path.basename(path),
        "area": area,
        "mapid": mapid,
        "cameras": len(cameras),
        "camera": {
            "pitch_deg": round(cam.pitch_deg(c0), 2),
            "yaw_deg": round(cam.yaw_deg(c0), 2),
            "fov_deg": round(d["fov_x_deg"], 2) if d["fov_x_deg"] else None,
            "range": list(c0.range),
            "proj": c0.proj,
        },
        "scrolling": scrolling,
        "frame_offset": [wm.orgPos.x, wm.orgPos.y, wm.orgPos.z],   # header base (+ per-floor floor.org)
        "player_start": _spawn,
        "walkmesh_bounds": {     # WORLD frame (vert + orgPos + floor.org) = where content goes
            "x": [round(min(wx)), round(max(wx))],
            "z": [round(min(wz)), round(max(wz))],
            "verts": len(wm.verts),
            "tris": len(wm.tris),
        },
        "out": str(out),
    }
    return meta


def field_art_dir(field: str, game=None):
    """The folder where Memoria's `[Export] Field=1` dumped this field's per-overlay PNGs, or None
    if it hasn't been exported in-game yet (StreamingAssets/FieldMaps/<FBG>/Overlay*.png).

    This is now only the FALLBACK source -- the art functions assemble the overlays OFFLINE from the
    atlas by default (`_overlay_art` / scene.bgart), so they no longer require the in-game export."""
    folder, _ = resolve_field(field, game)
    d = config.find_game_path(game) / "StreamingAssets" / "FieldMaps" / folder.upper()
    return d if (d / "Overlay0.png").is_file() else None


def _overlay_art(field: str, game=None, bundle=None):
    """``(overlays, provider, factor, source, atlas)`` for a field's background art -- OFFLINE-FIRST.

    ``overlays`` are the field's sprite-resolved overlays; ``provider(i)`` yields overlay ``i``'s
    ``Overlay{i}.png`` as a PIL RGBA image (or None); ``factor`` (= active TileSize // 16) is the
    overlay PNGs' pixels-per-tile -- the scale ``compose_background`` / ``extract_layers`` must crop
    and place at; ``source`` is ``"offline"`` or ``"export"``; ``atlas`` is the source atlas PIL image
    on the offline path (for an `export-art` ``atlas.png`` dump), else None. Returns None when no art
    is available.

    DEFAULT = assemble each overlay straight from the atlas the engine itself would render with (the
    highest-priority mod atlas -- Moguri -- else the base p0data atlas), via :mod:`scene.bgart`, so NO
    in-game ``[Export] Field=1`` is needed (it replaces the multi-minute startup dump). Falls back to
    Memoria's on-disk export only if the atlas can't be read. Sprites are resolved against the CHOSEN
    atlas width + active TileSize so the cells are correct (the legacy ``2048/40`` was valid only
    because the old path cropped the pre-assembled export, never the atlas itself). The offline path is
    proven byte-exact vs the engine's own ``atlas.png`` crop; a live install differs only by the sub-
    2/255 codec noise of re-decoding a DXT-compressed atlas offline (imperceptible, geometry-identical)."""
    import io  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415 - only the art path needs PIL
    try:
        _, folder, roles, env = find_field(field, game=game, bundle=bundle)
    except (FileNotFoundError, ValueError):
        return None
    if "bgs" not in roles:
        return None
    bgs_bytes = _raw_bytes(env.container[roles["bgs"]].read())
    ts = _active_tilesize(game)
    factor = ts // bgs.TILE
    atlas_img = None
    try:                                                     # the atlas AssetManager would load: mod, else base
        mod = _mod_field_atlas(folder, game=game)
        if mod is not None:
            atlas_img = Image.open(io.BytesIO(mod)).convert("RGBA")
        elif "atlas" in roles:
            atlas_img = env.container[roles["atlas"]].read().image.convert("RGBA")
    except Exception:                                        # noqa: BLE001 - unreadable atlas -> try the export
        atlas_img = None
    if atlas_img is not None:
        _, overlays = bgs.parse_overlays(bgs_bytes)
        bgs.resolve_sprites(bgs_bytes, overlays, atlas_img.size[0], ts)
        imgs = bgart.assemble_overlays(atlas_img, overlays, ts)
        return overlays, (lambda i, _m=imgs: _m.get(i)), factor, "offline", atlas_img
    art = field_art_dir(field, game)                         # FALLBACK: the on-disk [Export] dump
    if art is None:
        return None
    _, overlays = bgs.parse_overlays(bgs_bytes)
    bgs.resolve_sprites(bgs_bytes, overlays, 2048, 40)       # positions only -> the legacy params are fine here

    def _disk(i, _art=art):
        p = _art / f"Overlay{i}.png"
        return Image.open(p).convert("RGBA") if p.is_file() else None
    return overlays, _disk, factor, "export", None


def export_field_art(field: str, out_dir=None, *, game=None, bundle=None, write_atlas=True) -> dict:
    """Write a real field's per-overlay ``Overlay{i}.png`` (+ ``atlas.png``) to disk OFFLINE -- a drop-in
    for ONE field's slice of Memoria's ``[Export] Field=1`` dump, with NO in-game step.

    Assembles the overlays via :func:`_overlay_art` (offline-first) and writes them under
    ``<out_dir>/<FBG-UPPER>/``. ``out_dir`` defaults to the install's ``StreamingAssets/FieldMaps`` so the
    result lands exactly where the engine's own export would (a true drop-in). ``write_atlas`` also dumps
    the source ``atlas.png`` (as the engine does). Returns a summary dict; raises ``FileNotFoundError`` if
    the field has no readable art. NOTE: these PNGs are SE-derived ART -- keep them OUT of version control
    (the kit's .gitignore already excludes field assets)."""
    folder, _ = resolve_field(field, game)                   # canonical FBG folder -> the output dir name
    res = _overlay_art(field, game=game, bundle=bundle)
    if res is None:
        raise FileNotFoundError(f"{folder}: no readable field art (atlas + on-disk export both unavailable)")
    overlays, provider, _factor, source, atlas = res
    base = Path(out_dir) if out_dir is not None else (
        config.find_game_path(game) / "StreamingAssets" / "FieldMaps")
    dest = base / folder.upper()
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for i in range(len(overlays)):
        im = provider(i)
        if im is None:
            continue
        im.save(dest / f"Overlay{i}.png")
        n += 1
    wrote_atlas = bool(write_atlas and atlas is not None)
    if wrote_atlas:
        atlas.save(dest / "atlas.png")
    return {"folder": folder, "dir": str(dest), "overlays": n, "atlas": wrote_atlas, "source": source}


def export_field_composite(field: str, out_dir=None, *, game=None, bundle=None) -> dict:
    """Write ONE composited background PNG for a field -- the browsable "glimpse" artifact (clean opaque
    art, walkmesh footprint OFF), vs :func:`export_field_art`'s per-overlay layers. Lands FLAT at
    ``<out_dir>/<FBG-UPPER>.png`` so a whole-game export is a single scrollable folder. Returns a summary;
    raises ``FileNotFoundError`` if the field has no readable art."""
    folder, _ = resolve_field(field, game)
    base = Path(out_dir) if out_dir is not None else (
        config.find_game_path(game) / "StreamingAssets" / "FieldMaps")
    base.mkdir(parents=True, exist_ok=True)
    out_path = base / f"{folder.upper()}.png"
    dims = compose_background(field, out_path, game=game, bundle=bundle, draw_footprint=False)
    if dims is None:
        raise FileNotFoundError(f"{folder}: no readable field art (atlas + on-disk export both unavailable)")
    return {"folder": folder, "path": str(out_path), "size": list(dims)}


def _per_field_export(write_atlas: bool, composite: bool):
    """The per-field writer for :func:`_export_many` -- a composited PNG (glimpse) or per-overlay layers."""
    if composite:
        return lambda tok, out, game: export_field_composite(tok, out, game=game)
    return lambda tok, out, game: export_field_art(tok, out, game=game, write_atlas=write_atlas)


def _export_many(field_tokens, out_dir, *, game=None, per_field=None, on_field=None) -> dict:
    """Run ``per_field(token, out_dir, game) -> summary`` over many fields, never raising on a single bad
    one. ``on_field(k, total, folder, summary, err)`` is an optional progress callback. Returns
    {fields, units, failed:[(token, err)], total} (``units`` = total overlays in raw mode, 1/field in
    composite mode -- ``summary['overlays']`` or 1)."""
    fields = list(field_tokens)
    total = len(fields)
    n_fields = units = 0
    failed = []
    for k, f in enumerate(fields):
        try:
            summ = per_field(f, out_dir, game)
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            failed.append((str(f), str(e)))
            if on_field:
                on_field(k + 1, total, str(f), None, str(e))
            continue
        n_fields += 1
        units += summ.get("overlays", 1)
        if on_field:
            on_field(k + 1, total, summ["folder"], summ, None)
    return {"fields": n_fields, "units": units, "failed": failed, "total": total}


def export_campaign_art(campaign_toml, out_dir=None, *, game=None, write_atlas=True, composite=False,
                        on_field=None) -> dict:
    """Export the art for every REAL field a campaign forks (its members' ``source`` donor fields), OFFLINE.
    Reads the campaign manifest; dedups shared donors. ``composite`` = one glimpse PNG/field (else per-overlay
    layers). See :func:`export_field_art` / :func:`export_field_composite`."""
    from . import campaign as _camp
    plan = _camp.load_campaign(campaign_toml)
    ids = sorted({m.real_id for m in plan.members if m.real_id})
    if not ids:
        raise ValueError(f"{campaign_toml}: no member fields with a real `source` id to export")
    return _export_many((str(i) for i in ids), out_dir, game=game,
                        per_field=_per_field_export(write_atlas, composite), on_field=on_field)


def export_all_art(out_dir=None, *, game=None, pattern=None, write_atlas=True, composite=False,
                   on_field=None) -> dict:
    """Export art for EVERY real field (optionally filtered by ``pattern``), OFFLINE -- the full drop-in for
    the in-game ``[Export] Field=1`` startup dump, without launching the game (or its hang). ``composite`` =
    a one-PNG-per-field browsable gallery (the "full-journey glimpse") instead of per-overlay layers."""
    fields = [folder for folder, _a, _m in list_fields(pattern, game=game)]
    return _export_many(fields, out_dir, game=game,
                        per_field=_per_field_export(write_atlas, composite), on_field=on_field)


def compose_background(field: str, out_path, *, game=None, bundle=None, upscale=None,
                       draw_footprint=True, camera_index=None):
    """Composite the field's OPAQUE base art into one background PNG, for the Blender backdrop.

    Assembles the field's per-overlay art OFFLINE from the atlas (`_overlay_art` / scene.bgart),
    falling back to Memoria's `[Export] Field=1` dump if the atlas can't be read; places each overlay
    by the .bgs overlay positions/depths and skips additive/subtractive light+shadow overlays (the
    "splotches"). When `draw_footprint` (default), also draws the walkable footprint -- the .bgi tris
    projected by the EXACT GTE->canvas map (cam.to_canvas), with NO offset: the engine projects the raw
    walkmesh frame directly, so this lands exactly where the player walks in-game. The walkmesh may
    extend past the canvas edges (tunnels) -- that's correct, not a misalignment. `upscale` defaults to
    the active export factor (TileSize // 16) so placement matches the overlay PNGs' own pixels-per-tile;
    pass a value only to force it. Returns (w, h), or None if the field has no readable art at all.

    `camera_index` (default None) = composite ALL overlays onto camera 0's canvas (the glimpse). Pass
    an int K to composite ONLY the overlays camera K paints (`camNdx == K`) onto camera K's OWN range
    canvas + project the footprint via camera K -- the per-camera backdrop for a MULTI-camera field
    (each camera shows a different region of the scene; the all-overlays composite jams them onto one
    canvas as misplaced rectangles). For a single-camera field `camera_index=0` == None (all camNdx 0)."""
    res = _overlay_art(field, game=game, bundle=bundle)
    if res is None:
        return None
    overlays, provider, factor, _src, _atlas = res
    up = factor if upscale is None else upscale              # the overlay PNGs are `factor` px/tile
    from PIL import Image, ImageDraw  # noqa: PLC0415 - only the art path needs PIL
    _, _, roles, env = find_field(field, game=game, bundle=bundle)
    bgs_bytes = _raw_bytes(env.container[roles["bgs"]].read())
    h = bgs.parse_header(bgs_bytes)
    sOrgX, sOrgY = h.bounds[2], h.bounds[3]
    cams = bgs.parse_cameras(bgs_bytes)
    ci = 0 if camera_index is None else int(camera_index)
    cam_use = cams[ci] if 0 <= ci < len(cams) else cams[0]
    W, H = cam_use.range[0] * up, cam_use.range[1] * up
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # camera_index=None -> all overlays (glimpse); =K -> only the overlays camera K paints (camNdx==K).
    opaque = [(i, o) for i, o in enumerate(overlays) if o.sprites and o.sprites[0].trans == 0
              and (camera_index is None or o.camNdx == ci)]
    opaque.sort(key=lambda io: -(io[1].curZ + io[1].orgZ))    # back (high depth) -> front
    for i, o in opaque:
        im = provider(i)
        if im is None:
            continue
        mnX = min(s.offX for s in o.sprites)
        mnY = min(s.offY for s in o.sprites)
        canvas.alpha_composite(im, ((sOrgX + o.orgX + mnX) * up, (sOrgY + o.orgY + mnY) * up))

    if draw_footprint and "bgi" in roles:
        wm = bgi.BgiWalkmesh.from_bytes(_raw_bytes(env.container[roles["bgi"]].read()))
        # Project in the engine's RENDER frame: the engine negates the walkmesh Y before the GTE
        # (Memoria WalkMesh.cs:54), so flip Y here too. Without it a DEEP floor -- one whose .bgi
        # floor.org is 0, leaving it ~thousands of units off the floor plane (e.g. CPMP field 1554's
        # vine path) -- projects off the painting; near-plane floors were only ~20px off, masked by the
        # Blender view-offset. world_verts stays pre-flip (the BUILD ships it verbatim and the engine
        # applies its own flip), so the flip lives ONLY in this DISPLAY projection.
        wv = [(x, -y, z) for (x, y, z) in wm.world_verts()]
        draw = ImageDraw.Draw(canvas, "RGBA")
        for t in wm.tris:
            pts = []
            for vi in t.vtx:
                cx, cy = cam.to_canvas(wv[vi], cam_use)  # exact GTE projection, render frame
                pts.append((cx * up, cy * up))
            draw.polygon(pts, fill=(90, 180, 255, 45), outline=(120, 225, 255, 160))
    canvas.save(out_path)
    return (W, H)


_ABR_NONE = "PSX/FieldMap_Abr_None"


def _overlay_shader(sprite) -> str:
    """The PSX field-map shader for an overlay, from its first sprite -- mirrors Memoria's OWN .bgx
    exporter (BGSCENE_DEF.cs:611): opaque (trans==0) => Abr_None, else Abr_{min(3, alpha)} (the PSX
    ABR blend mode: 0 average, 1 additive, 2 subtractive, 3 add-quarter). The .bgx importer honors
    the `Shader:` directive (BGSCENE_DEF.cs:321), so light/shadow overlays blend correctly."""
    if sprite.trans == 0:
        return _ABR_NONE
    return f"PSX/FieldMap_Abr_{min(3, sprite.alpha)}"


def _depth_groups(overlays, sOrgX, sOrgY, sOrgZ, has_png, *, include_blend=True, depth_tolerance=1):
    """Bucket every renderable tile-sprite by (depth-bucket, shader) -- the PER-TILE occlusion split.

    FF9 occludes the player per 16px TILE: the engine places each tile-sprite at its OWN depth
    (BGSCENE_DEF.cs:1742 combined / :1846 separate, quad z = sprite.depth) and the player competes at a
    single projected eye-Z. A pure-`.bgx` OVERLAY carries only ONE depth per PNG, so faithful occlusion
    means one layer per distinct tile depth -- NOT one layer per overlay at min(sprite.depth) (the old
    flatten, which pinned a whole multi-depth overlay to its NEAREST tile and drew the player UNDER art
    physically behind him). `depth_tolerance` coarsens depths into buckets (1 = exact per-distinct-depth).

    Pure (no PIL/IO): `has_png(i)` reports whether overlay i has exported art on disk. Returns
    ((bucket_z, shader) -> [(overlay_index, sprite, scene_x, scene_y, mnX, mnY)], skipped_blend), where
    scene_x/scene_y are the tile's logical top-left on the canvas (sceneOrg + overlay.org + sprite.off,
    matching compose_background) and mnX/mnY are its overlay's min offsets (for the tile crop)."""
    tol = max(1, int(depth_tolerance))
    groups, skipped = {}, 0
    for i, o in enumerate(overlays):
        if not o.sprites:
            continue
        shader = _overlay_shader(o.sprites[0])
        if not include_blend and shader != _ABR_NONE:
            skipped += 1
            continue
        if not has_png(i):
            continue
        mnX = min(s.offX for s in o.sprites)
        mnY = min(s.offY for s in o.sprites)
        for s in o.sprites:
            bz = ((sOrgZ + o.orgZ + s.depth) // tol) * tol    # tol==1 => exact per-distinct-depth
            groups.setdefault((bz, shader), []).append(
                (i, s, sOrgX + o.orgX + s.offX, sOrgY + o.orgY + s.offY, mnX, mnY))
    return groups, skipped


def extract_layers(field: str, out_dir, *, game=None, bundle=None, upscale=None, include_blend=True,
                   depth_tolerance=8, max_layers=48, bleed=1):
    """Per-TILE-DEPTH art layers for an EDITABLE custom-scene fork that PRESERVES per-tile occlusion.

    Real FF9 fields occlude the player per 16px tile (each tile-sprite drawn at its own depth); a
    pure-`.bgx` OVERLAY can carry only ONE depth per PNG, so this SPLITS each overlay into one tight
    sub-PNG per distinct tile depth (within `depth_tolerance`), each emitted at that depth's own `z` +
    explicit `position`/`size`. The engine redraws the depth-ordered scene, so the 3D player is occluded
    by / occludes each layer exactly like the real field (smaller z = nearer = drawn in front), and
    light/shadow overlays blend (Abr shaders, BGSCENE_DEF.cs:597). This REPLACES the old
    one-PNG-per-overlay-at-min(sprite.depth) flatten (a verbatim port of Memoria's own lossy `.bgx`
    exporter, BGSCENE_DEF.cs:592), which drew the player UNDER any overlay whose nearest tile sat in
    front of him (the "Zidane under the boxes" bug).

    Tiles are cropped from each overlay's `Overlay{i}.png`, which is now assembled OFFLINE from the
    atlas (`_overlay_art` / scene.bgart -- no in-game `[Export] Field=1` needed), falling back to
    Memoria's on-disk export dump only if the atlas can't be read. `bgs.tile_box` gives each tile's
    crop. `depth_tolerance` buckets nearby depths into one layer (1 = exact per-distinct-depth); the
    default 8 keeps each smooth surface whole (real surfaces vary only a few depth units per tile) while
    still splitting at the big depth jumps that actually occlude. `max_layers` then auto-coarsens the
    tolerance until the count fits (default 48) -- a real field can split into HUNDREDS of distinct tile
    depths (field 122 = 215 at tol 1), which both lags the load (one GameObject/texture per layer) and
    multiplies tile-cut seams. `bleed` edge-extends opaque layers to hide the bilinear cut seams. `upscale`
    defaults to the active export factor (TileSize // 16) so the crop matches the overlay PNGs' own
    pixels-per-tile; pass a value only to force it. Returns None only if the field has no readable art at
    all. `include_blend` (default) emits the additive/subtractive light+shadow overlays too.

    Co-located tiles sharing a (depth-bucket, shader) merge into one layer (correct for a tiled plane,
    approximate for overlapping animation frames at the same depth -- a known v1 simplification)."""
    res = _overlay_art(field, game=game, bundle=bundle)
    if res is None:
        return None
    overlays, provider, factor, _src, _atlas = res
    up = factor if upscale is None else upscale              # the overlay PNGs are `factor` px/tile
    _, _, roles, env = find_field(field, game=game, bundle=bundle)
    bgs_bytes = _raw_bytes(env.container[roles["bgs"]].read())
    h = bgs.parse_header(bgs_bytes)
    sOrgX, sOrgY, sOrgZ = h.bounds[2], h.bounds[3], h.bounds[0]
    c0 = bgs.parse_cameras(bgs_bytes)[0]

    _png_cache = {}
    def _png(i):
        if i not in _png_cache:
            _png_cache[i] = provider(i)
        return _png_cache[i]

    def _has_png(i):
        return _png(i) is not None

    tol = max(1, int(depth_tolerance))
    groups, skipped = _depth_groups(overlays, sOrgX, sOrgY, sOrgZ, _has_png,
                                    include_blend=include_blend, depth_tolerance=tol)
    while len(groups) > max_layers and tol < 4096:            # runaway-field backstop: coarsen the bucket
        tol *= 2
        groups, skipped = _depth_groups(overlays, sOrgX, sOrgY, sOrgZ, _has_png,
                                        include_blend=include_blend, depth_tolerance=tol)

    layers, blend = _render_depth_groups(groups, _png, out_dir, upscale=up, bleed=bleed)
    return {"layers": layers, "blend_layers": blend, "skipped_blend_overlays": skipped,
            "range": list(c0.range), "depth_tolerance": tol,
            "tiles": sum(len(v) for v in groups.values())}


def _edge_bleed(img, px):
    """Dilate opaque pixels `px` px outward into transparent neighbours (edge-extend). The kit's `.bgx`
    layer PNGs load BILINEAR (Unity `LoadImage` default; the engine's `.memnfo` `FilterMode Point` hook is
    dummied), so a tile cut from a larger image samples TRANSPARENT just past its edge -> a 1px seam at
    every boundary between tiles split into different depth layers. Bleeding real edge colour into a 1px
    margin makes the bilinear tap land on art, not transparent, killing the seam. Pure PIL (no numpy):
    each pass composites eight 1px-shifted copies UNDER the image, filling only the still-transparent
    border with the nearest edge pixel."""
    from PIL import Image  # noqa: PLC0415 - only the art path needs PIL
    shifts = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1))
    for _ in range(px):
        under = Image.new("RGBA", img.size, (0, 0, 0, 0))
        for dx, dy in shifts:
            shifted = Image.new("RGBA", img.size, (0, 0, 0, 0))
            shifted.paste(img, (dx, dy))
            under = Image.alpha_composite(under, shifted)     # accumulate every neighbour shift
        img = Image.alpha_composite(under, img)               # original on top -> only the border fills
    return img


def _render_depth_groups(groups, png_provider, out_dir, *, upscale=4, bleed=1):
    """Composite each (depth-bucket, shader) group from `_depth_groups` into one tight sub-PNG and
    return its `[[layers]]` list (back-to-front by depth). `png_provider(i)` yields overlay i's exported
    `Overlay{i}.png` as an RGBA PIL image; each tile is cropped from it via `bgs.tile_box` and blitted at
    its own canvas spot. Each layer gets an EXPLICIT `position`/`size` (the group's tile bbox) so the
    engine maps the sub-PNG onto exactly the quad the tiles occupy.

    `bleed` (logical px) gives each OPAQUE layer a transparent margin that `_edge_bleed` fills with the
    tile edge colour, so the engine's bilinear sampling doesn't bleed a cut tile's edge to transparent
    (the 1px seams). Blend (additive) layers skip it: a transparent bleed only DIMS their glow (no dark
    seam) and a margin would double-add the glow where layers overlap. Split out for unit-testing the
    crop + placement (and the bleed) without a real `.bgs`."""
    from PIL import Image  # noqa: PLC0415 - only the art path needs PIL
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    layers, blend = [], 0
    for (bz, shader) in sorted(groups, key=lambda k: (-k[0], k[1])):    # back (large z) -> front
        tiles = groups[(bz, shader)]
        gx0 = min(t[2] for t in tiles)
        gy0 = min(t[3] for t in tiles)
        gx1 = max(t[2] + bgs.TILE for t in tiles)
        gy1 = max(t[3] + bgs.TILE for t in tiles)
        m = bleed if (shader == _ABR_NONE and bleed > 0) else 0         # opaque layers get a bleed margin
        px0, py0 = gx0 - m, gy0 - m
        sw, sh = (gx1 - gx0) + 2 * m, (gy1 - gy0) + 2 * m
        canvas = Image.new("RGBA", (sw * upscale, sh * upscale), (0, 0, 0, 0))
        for (i, s, sx, sy, mnX, mnY) in tiles:               # blit each tile at its own canvas spot
            canvas.alpha_composite(png_provider(i).crop(bgs.tile_box(s, mnX, mnY, upscale)),
                                   ((sx - px0) * upscale, (sy - py0) * upscale))
        if m:
            canvas = _edge_bleed(canvas, m * upscale)         # fill the margin with edge colour
        abr = shader.rsplit("_", 1)[-1]                       # None / 0 / 1 / 2 / 3
        name = f"layer_{int(bz):05d}_{abr}.png"
        canvas.save(out / name)
        L = {"image": name, "z": int(bz), "position": [int(px0), int(py0)], "size": [int(sw), int(sh)]}
        if shader != _ABR_NONE:
            L["shader"] = shader
            blend += 1
        layers.append(L)
    return layers, blend


def _world_walkmesh_obj_text(wm) -> str:
    """A world-frame Wavefront .obj (multi-floor aware) re-exported from a parsed walkmesh: the verts
    ARE the world coords (BgiWalkmesh.world_verts), one `o floor_N` per floor -- build with
    `[walkmesh] frame = "world"` (bgi.build, orgPos=0) so the engine renders them verbatim."""
    wv = wm.world_verts()
    faces = [tuple(t.vtx) for t in wm.tris]
    floor_ids = [t.floor_ndx for t in wm.tris]
    order = []
    for f in floor_ids:
        if f not in order:
            order.append(f)
    lines = ["# walkmesh re-exported by ff9mapkit (world frame, orgPos=0)"]
    for (x, y, z) in wv:
        lines.append(f"v {x} {y} {z}")
    if len(order) > 1:
        for fid in order:
            lines.append(f"o floor_{fid}")
            for (a, b, c), fl in zip(faces, floor_ids):
                if fl == fid:
                    lines.append(f"f {a + 1} {b + 1} {c + 1}")
    else:
        for (a, b, c) in faces:
            lines.append(f"f {a + 1} {b + 1} {c + 1}")
    return "\n".join(lines) + "\n"


def _write_links_toml(wm, path) -> int:
    """Write the adjacency sidecar (cross-floor seams + header) for an editable multi-floor walkmesh.
    walkmesh.obj carries geometry; this carries the seams geometry can't express. Reconciled on build
    by world position (build._apply_links). Returns the seam count. See docs/WALKMESH_EDITING.md."""
    seams = wm.extract_seams()
    L = ["# Adjacency sidecar for an editable multi-floor walkmesh (ff9mapkit). walkmesh.obj carries the",
         "# geometry; this carries the CROSS-FLOOR seams geometry can't express (FF9 floors use disjoint",
         "# vertex sets, so rebuild-from-geometry can't recover them). On build with `[walkmesh] obj +",
         "# links`, each seam is re-matched to your edited geometry by WORLD POSITION; a seam whose edge",
         "# you moved/deleted warns instead of silently dropping. Auto-generated -- rarely hand-edited.",
         "",
         "[header]",
         f"active_floor = {wm.activeFloor}",
         f"active_tri = {wm.activeTri}",
         f"char_pos = [{wm.charPos.x}, {wm.charPos.y}, {wm.charPos.z}]",
         ""]
    for (fa, a, fb, b) in seams:
        L += ["[[seam]]", f"a_floor = {fa}",
              f"a_edge = [[{a[0][0]}, {a[0][1]}, {a[0][2]}], [{a[1][0]}, {a[1][1]}, {a[1][2]}]]",
              f"b_floor = {fb}"]
        if b:
            L.append(f"b_edge = [[{b[0][0]}, {b[0][1]}, {b[0][2]}], [{b[1][0]}, {b[1][1]}, {b[1][2]}]]")
        L.append("")
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    return len(seams)


MIN_CUSTOM_AREA = 10   # engine builds 'FBG_N<area>' + reads exactly 2 chars -> areas 0-9 black-screen


def safe_custom_area(area: int) -> int:
    """An area a CUSTOM scene (ships its own art) can safely render: a source area >= 10 as-is, else a
    safe default (11). For BG-borrow the area MUST equal the real field's, so 0-9 can't borrow at all."""
    return area if area >= MIN_CUSTOM_AREA else 11


def _walkmesh_hotfix_line(field) -> str:
    """The ``[field] walkmesh_tri_toggles`` line for a fork of real ``field`` when that field has a LOAD-TIME
    engine walkmesh hotfix (``BGI_triSetActive`` keyed on its real ``fldMapNo``) the fork would lose on its
    custom id -- so the build reproduces it by prepending the toggles to Main_Init. ``""`` when the field has
    no statically-reproducible walkmesh hotfix (almost all). See :mod:`ff9mapkit.walkmesh_hotfixes`."""
    from . import walkmesh_hotfixes as _wh
    from .dialogue import _resolve_field_id
    try:
        h = _wh.info(_resolve_field_id(field))
    except Exception:
        return ""
    if not (h and h.auto):
        return ""
    arr = ", ".join(f"[{t}, {s}]" for t, s in h.toggles)
    return (f"walkmesh_tri_toggles = [{arr}]   # {h.name}: reproduce its load-time engine walkmesh hotfix\n"
            f"# (engine BGI_triSetActive keyed on real fldMapNo {h.field_id} is lost on a custom id; {h.source})\n")


def _area_title_hide_lines(meta, *, verbatim=False) -> str:
    """For a SYNTH (non-verbatim) native/editable fork of an AREA-TITLE field, auto-emit ``hide_area_title``
    + the overlay range so the inherited title card doesn't sit STATIC. The title overlays are active-by-
    default in the donor scene the fork ships; a synth fork has no donor ``.eb`` to run the show+fade, so the
    card would just sit there claiming to be that place (the same leak the World Hub's BG-borrow hit). A
    ``--verbatim`` fork CARRIES the donor ``.eb``'s scenario-gated show+fade, so it is left alone (the title is
    correct + wanted there). ``""`` when the field has no area title / the manifest is unreachable (offline).
    Reuses the proven hub mechanism (``content.areatitle`` via the ``[field] hide_area_title`` build hook)."""
    if verbatim or not meta:
        return ""
    from . import areatitle as _at
    fbg = f"FBG_N{int(meta['area']):02d}_{meta['mapid']}"
    rng = _at.title_range(fbg)
    if not rng:
        return ""
    s, e = rng
    return (f"# this synth fork borrows an area-title room ({fbg}); with no donor .eb to fade the card it would\n"
            f"# sit STATIC, so hide it (use --verbatim to keep the real, scenario-gated show+fade instead):\n"
            f"hide_area_title = true\n"
            f"area_title_overlays = [{s}, {e}]\n")


def write_editable_project(field: str, out_dir, *, name: str | None = None, field_id: int = 4003,
                           text_block: int = 1073, game=None, bundle=None,
                           id_remap=None, live_seams=False, graft_player_funcs=False, carry_text=False,
                         graft_savepoint=False):
    """Fork a real field as a fully EDITABLE custom scene (vs BG-borrow): re-export its walkmesh via the
    world-frame builder + extract its art as per-DEPTH layers (occlusion preserved) + reuse its camera.

    Emits a custom-scene `field.toml` (NO borrow_bg) ready for `ff9mapkit build` and for repainting any
    single `layer_*.png` / editing `walkmesh.obj`. Returns (metadata, field_toml_path). The art is now
    assembled OFFLINE from the atlas (`extract_layers` / scene.bgart) -- no in-game `[Export] Field=1`
    needed; raises RuntimeError only if the field has no readable atlas at all (use plain import for a
    BG-borrow fork that reuses the art as-is)."""
    out = Path(out_dir)
    meta = extract_field(field, out, game=game, bundle=bundle)     # writes camera.bgx + walkmesh.bgi
    name = name or (meta["mapid"].split("_")[0] + "_EDIT")
    # A custom scene ships its own art under FBG_N<area>_<name>, so the area is just a folder key --
    # any value >= 10 works (single-digit areas black-screen via the engine's 2-char FBG lookup).
    # Remap a low source area to a safe one so forks of early-game (area 0-9) fields build + render.
    safe_area = safe_custom_area(meta["area"])
    remap_note = ("" if safe_area == meta["area"] else
                  f"# NOTE: source area {meta['area']} < 10 black-screens via the engine's FBG_N<area> "
                  f"lookup, so this\n# custom scene uses area {safe_area} (it ships its own art -- the "
                  f"source area is just a folder key).\n")
    # A MULTI-camera field paints a different region per camera (BGOVERLAY_DEF.camNdx). An editable fork
    # resolves ONE camera from its single [camera] block and doesn't reconstruct the per-camera switch
    # zones, so it captures CAMERA 0 ONLY -- cameras 1+ and their art are dropped. --verbatim keeps the
    # real .eb's camera switching + all cameras' art (the faithful multi-camera path).
    multicam_note = ("" if meta.get("cameras", 1) <= 1 else
                     f"# WARNING: {meta['field']} is MULTI-CAMERA ({meta['cameras']} cameras); an editable fork\n"
                     f"# captures CAMERA 0 ONLY (switch zones for cameras 1+ aren't reconstructed, so their\n"
                     f"# walkmesh regions + art are dropped). For a faithful multi-camera fork use:\n"
                     f"#   ff9mapkit import {field} --verbatim\n")
    wm = bgi.BgiWalkmesh.from_bytes((out / "walkmesh.bgi").read_bytes())
    nfloors = len(wm.floors)
    (out / "walkmesh.obj").write_text(_world_walkmesh_obj_text(wm), encoding="utf-8", newline="\n")
    nseams = _write_links_toml(wm, out / "walkmesh.links.toml") if nfloors > 1 else 0

    layers_info = extract_layers(field, out, game=game, bundle=bundle)
    if layers_info is None:
        raise RuntimeError(
            f"{meta['field']}: editable art needs a readable field atlas (assembled offline). The atlas "
            f"couldn't be read from p0data -- OR use `ff9mapkit import {field}` (BG-borrow: reuses the "
            f"real art as-is, no repaint).")
    layers = layers_info["layers"]
    meta["layers"] = len(layers)
    meta["blend_layers"] = layers_info["blend_layers"]
    meta["editable_name"] = name
    # A single composited backdrop (opaque art) for the Blender modeling preview: the per-tile-depth
    # sub-layers are tight crops that don't FIT-stretch, so the add-on models against this instead.
    try:                                                          # preview-only -- never fatal
        compose_background(field, out / "background.png", game=game, bundle=bundle, draw_footprint=False)
    except Exception:
        pass

    content_blocks, control_dir, content_summary = _content_for_import(
        field, game, out_dir=out, name=name, id_remap=id_remap, live_seams=live_seams,
        graft_player_funcs=graft_player_funcs, carry_text=carry_text, graft_savepoint=graft_savepoint)
    meta["imported_content"] = content_summary
    cm = meta["camera"]
    wb = meta["walkmesh_bounds"]
    x, z = meta["player_start"]
    scroll = "[camera.scroll]\nenabled = true\n" if meta["scrolling"] else ""
    control_line = f"control_direction = {control_dir}   # imported WASD-vs-camera tuning\n" if control_dir is not None else ""

    def _layer_block(L):
        pos, sz = L.get("position", [0, 0]), L.get("size")
        s = (f'[[layers]]\nimage = "{L["image"]}"\nz = {L["z"]}\n'
             f'position = [{int(pos[0])}, {int(pos[1])}]')
        if sz:                                                 # tight per-tile-depth sub-PNG (vs full canvas)
            s += f'\nsize = [{int(sz[0])}, {int(sz[1])}]'
        return s + (f'\nshader = "{L["shader"]}"' if L.get("shader") else "")
    layer_blocks = "\n".join(_layer_block(L) for L in layers)

    if nfloors > 1:
        reshape = ('# To RESHAPE the geometry: edit walkmesh.obj, then replace the bgi line above with:\n'
                   '#   obj = "walkmesh.obj"\n#   links = "walkmesh.links.toml"\n#   frame = "world"\n'
                   f'# (the seam sidecar re-attaches this field\'s {nseams} cross-floor links to your edits\n'
                   '#  by world position; a seam whose edge you moved warns instead of dropping silently.)\n')
    else:
        reshape = ('# To RESHAPE: edit walkmesh.obj, then replace the bgi line above with:\n'
                   '#   obj = "walkmesh.obj"\n#   frame = "world"\n')
    walkmesh_toml = (
        f"[walkmesh]\n"
        f'bgi = "walkmesh.bgi"   # the real field\'s walkmesh ({nfloors} floor(s)) -- connectivity preserved\n'
        f"{reshape}"
    )
    toml = (
        f"# EDITABLE fork of {meta['field']} (area {meta['area']}) by ff9mapkit -- a full CUSTOM SCENE.\n"
        f"# Re-exported walkmesh + the real art split into one layer per TILE-DEPTH (per-tile occlusion\n"
        f"# preserved -- the player is occluded by each tile exactly as in the real field).\n"
        f"# Repaint any layer_*.png, reshape walkmesh.obj, add content -- then:  ff9mapkit build {name}.field.toml\n"
        f"# Camera: pitch {cm['pitch_deg']} deg, FOV {cm['fov_deg']} deg, range {cm['range'][0]}x{cm['range'][1]}"
        f"{' (SCROLLING)' if meta['scrolling'] else ''}.  Walkmesh bounds: x {wb['x']}  z {wb['z']}.\n"
        f"{remap_note}{multicam_note}\n"
        f"[field]\n"
        f"id = {field_id}\n"
        f'name = "{name}"\n'
        f"area = {safe_area}\n"
        f"text_block = {text_block}\n"
        f"{_walkmesh_hotfix_line(field)}"
        f"{_area_title_hide_lines(meta)}\n"
        f"[camera]\n"
        f'borrow = "camera.bgx"\n'
        f"{control_line}"
        f"{scroll}\n"
        f"{walkmesh_toml}\n"
        f"{layer_blocks}\n\n"
        f"[player]\n"
        f"spawn = [{x}, {z}]\n\n"
        f"# --- add NPCs/dialogue (uncomment + edit); keep positions within the walkmesh bounds above ---\n"
        f'# [[npc]]\n# name = "Vivi"\n# preset = "vivi"\n# pos = [{x}, {z}]\n# dialogue = "Hello, traveler."\n\n'
        f"{_content_section(content_blocks, x, z)}"
    )
    p = Path(out_dir) / f"{name}.field.toml"
    p.write_text(toml, encoding="utf-8", newline="\n")
    meta["field_toml"] = str(p)
    return meta, p


def _mod_folders(game=None) -> list:
    """Active mod folders (Memoria.ini [Mod] FolderNames), in listed order. The engine stacks these over
    the base assets, so a background mod (Moguri) supplies the field atlas the player actually sees."""
    try:
        ini = config.find_game_path(game) / "Memoria.ini"
        for line in ini.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if s.lower().startswith("foldernames") and "=" in s and not s.startswith(";"):
                return [v.strip().strip('"') for v in s.split("=", 1)[1].split(",") if v.strip().strip('"')]
    except OSError:
        pass
    return []


def _active_tilesize(game=None) -> int:
    """The effective field-map atlas TileSize (Memoria.ini; a mod folder's ini overrides the base). Vanilla
    32 / Moguri 64. The native atlas MUST be packed at this tile size or the engine samples the wrong cells
    (garbled art) -- it lays each tile out at i*(TileSize+pad)."""
    gp = config.find_game_path(game)
    ts = 32
    for ini in [gp / "Memoria.ini"] + [gp / f / "Memoria.ini" for f in _mod_folders(game)]:
        try:
            for line in ini.read_text(encoding="utf-8", errors="replace").splitlines():
                s = line.strip()
                if s.lower().startswith("tilesize") and "=" in s and not s.startswith(";"):
                    ts = int(s.split("=", 1)[1].split(";")[0].strip())
        except (OSError, ValueError):
            pass
    return ts


def _atlas_png_bytes(tex) -> bytes:
    import io  # noqa: PLC0415
    buf = io.BytesIO()
    tex.image.save(buf, format="PNG")
    return buf.getvalue()


_MOD_ENV_CACHE: dict = {}


def _load_mod_bundle(path):
    """Load + cache a mod-folder p0data bundle (read-only, static). A multi-member campaign that needs
    several fields' mod atlases then loads each bundle ONCE instead of re-loading it per member."""
    p = str(path)
    if p not in _MOD_ENV_CACHE:
        try:
            _MOD_ENV_CACHE[p] = _unitypy().load(p)
        except Exception:                                    # noqa: BLE001 - a non-bundle / unreadable bin
            _MOD_ENV_CACHE[p] = None
    return _MOD_ENV_CACHE[p]


def _mod_field_atlas(folder: str, game=None):
    """The field's ``atlas.png`` from the highest-priority MOD folder that ships it (Moguri's high-res
    atlas), as PNG bytes -- or None. Scans each mod folder's loose Fieldmaps, then its (cached) p0data."""
    gp = config.find_game_path(game)
    key = f"assets/resources/fieldmaps/{folder.lower()}/atlas.png"
    for mod in _mod_folders(game):
        sa = gp / mod / "StreamingAssets"
        loose = sa / "Assets" / "Resources" / "Fieldmaps" / folder / "atlas.png"
        if loose.is_file():
            return loose.read_bytes()
        for b in sorted(sa.glob("p0data*.bin")):
            env = _load_mod_bundle(b)
            if env is None:
                continue
            for path, obj in env.container.items():
                if path.lower() == key:
                    return _atlas_png_bytes(obj.read())
    return None


def _native_atlas(field: str, game=None, bundle=None):
    """(atlas_png_bytes, source) for a NATIVE fork: the field atlas packed at the ACTIVE TileSize. The base
    bundle atlas fits vanilla (32); when a mod raises TileSize (Moguri = 64) the base atlas no longer fits,
    so we ship the bg mod's high-res atlas -- a Moguri player gets Moguri art, seamless + faithful. Returns
    the first atlas whose dimensions accommodate the field's sprite coords at the active TileSize."""
    from PIL import Image  # noqa: PLC0415
    import io  # noqa: PLC0415
    folder, _ = resolve_field(field, game)
    _, _, roles, env = find_field(field, game=game, bundle=bundle)
    bgs_bytes = _raw_bytes(env.container[roles["bgs"]].read())
    ts = _active_tilesize(game)

    def _fits(png: bytes) -> bool:
        w, h = Image.open(io.BytesIO(png)).size
        _, ov = bgs.parse_overlays(bgs_bytes)                # fresh overlays (resolve_sprites appends)
        bgs.resolve_sprites(bgs_bytes, ov, w, ts)
        sprites = [s for o in ov for s in o.sprites]
        return (max((s.atlasX for s in sprites), default=0) <= w
                and max((s.atlasY for s in sprites), default=0) <= h)

    base = _atlas_png_bytes(env.container[roles["atlas"]].read()) if "atlas" in roles else None
    if base is not None and _fits(base):
        return base, "base"
    mod = _mod_field_atlas(folder, game=game)               # Moguri / a bg mod's high-res atlas
    if mod is not None and _fits(mod):
        return mod, f"mod (TileSize {ts})"
    return (base or mod), ("base (TILESIZE MISMATCH -- art will garble)" if base else "none found")


def apply_player_swap(toml_path, char, *, neutralize=False):
    """Swap the verbatim fork's player to ``char`` in place (patches the ``[verbatim_eb]`` sidecar `.eb`).
    Shared by the single ``import --swap-player`` and the chain (every member). When ``neutralize`` is set,
    also rewrites the player's scripted GESTURES to the rig's idle so a cutscene field stands cleanly instead
    of glitching (:func:`playerswap.neutralize_gestures`). Returns the count of scripted player GESTURES (the
    number that would glitch un-neutralized / were neutralized -- the caller phrases the message), or ``None``
    if the project has no verbatim sidecar to swap (a degraded / non-verbatim member). Raises ``ValueError``
    on an unknown char or a member with no swappable player entry."""
    import tomllib
    from . import playerswap
    toml_path = Path(toml_path)
    vb = tomllib.loads(toml_path.read_text(encoding="utf-8")).get("verbatim_eb")
    if not vb or "bin" not in vb:
        return None                              # not a verbatim fork (e.g. a logic-only stub) -> nothing to swap
    binp = toml_path.parent / vb["bin"]
    from .eb import EbScript
    original = binp.read_bytes()
    # resolve the swap targets ONCE on the original bytes: swap_targets keys on the Init SetModel id, which
    # swap_player MUTATES, so re-deriving on the swapped bytes drifts to a different entry on a Zidane-present
    # multi-PC field (neutralizing the wrong actor). Pin the set and reuse it for every pass.
    targets = playerswap.swap_targets(EbScript.from_bytes(original))
    swapped = playerswap.swap_player(original, char, entry=targets)
    n_gestures = playerswap.scripted_gesture_ops(swapped, entry=targets)
    if neutralize:
        swapped = playerswap.neutralize_gestures(swapped, char, entry=targets)
    binp.write_bytes(swapped)
    return n_gestures


def write_native_project(field: str, out_dir, *, name: str | None = None, field_id: int = 4003,
                         text_block: int = 1073, game=None, bundle=None,
                         id_remap=None, live_seams=False, graft_player_funcs=False, carry_text=False,
                         graft_savepoint=False, verbatim=False):
    """Fork a real field as a NATIVE custom scene: ship its OWN ``atlas.png`` + ``.bgs`` (the real
    per-tile-depth scene) + a custom walkmesh ``.bgi``, and NO ``.bgx``.

    The engine then renders it through the SEAMLESS native path (point-sampled atlas, per-tile-depth
    quads) -- exactly how Moguri ships (vanilla ``.bgs`` + a high-res atlas, no ``.bgx``), so the player
    is occluded per-tile with none of the bilinear tile seams a ``.bgx`` memoria-image fork has. The area
    is remapped >= 10 so the ``FBG_N<area>`` lookup doesn't black-screen, which also lets this fork
    area<10 fields that BG-borrow can't. Repaint by editing ``atlas.png`` (or the Memoria PSD pipeline).
    Returns (metadata, field_toml_path). Needs no in-game export (unlike ``--editable``)."""
    out = Path(out_dir)
    # camera.bgx (content logic) + walkmesh.bgi (real walkmesh)
    meta = extract_field(field, out, game=game, bundle=bundle)
    # atlas packed at the ACTIVE TileSize: base for vanilla, Moguri's high-res atlas when a mod raised it
    atlas_bytes, atlas_src = _native_atlas(field, game=game, bundle=bundle)
    if atlas_bytes is None:
        raise RuntimeError(f"{meta['field']}: no atlas.png in the field bundle -- can't ship a native scene "
                           f"(use `ff9mapkit import {field}` for a BG-borrow fork instead).")
    (out / "atlas.png").write_bytes(atlas_bytes)
    meta["atlas_source"] = atlas_src
    name = name or (meta["mapid"].split("_")[0] + "_NATIVE")
    safe_area = safe_custom_area(meta["area"])
    remap_note = ("" if safe_area == meta["area"] else
                  f"# NOTE: source area {meta['area']} < 10 black-screens via the engine's FBG_N<area> "
                  f"lookup, so this\n# native scene uses area {safe_area} (it ships its own art).\n")
    # ship the field's NATIVE .bgs VERBATIM -- it carries the per-tile depth the engine renders seamlessly
    _, _, roles, env = find_field(field, game=game, bundle=bundle)
    (out / "scene.bgs.bytes").write_bytes(_raw_bytes(env.container[roles["bgs"]].read()))
    meta["editable_name"] = name
    # ship the field's MapConfigData VERBATIM -- the 3D-model LIGHTING (per-floor lights + shadows + per-
    # object colors) the engine applies at load. Without it a native fork's models render bright/untinted.
    mc_bytes = extract_mapconfig(field, game=game)
    if mc_bytes:
        (out / "mapconfig.bytes").write_bytes(mc_bytes)
    meta["mapconfig"] = bool(mc_bytes)

    cm = meta["camera"]
    wb = meta["walkmesh_bounds"]
    x, z = meta["player_start"]
    scroll = "[camera.scroll]\nenabled = true\n" if meta["scrolling"] else ""
    if verbatim:
        # VERBATIM .eb fork (docs/FORK_FIDELITY.md, the entry-0 carry): ship the donor's WHOLE event script;
        # the build runs the real logic instead of synthesizing. No declarative content (it's all in the .eb).
        import json as _json

        from . import dialogue as _dlg
        from .config import LANGS
        from .content import verbatim as _vb
        from .eb import EbScript
        donor_eb = extract_event_script(field, game=game)
        (out / f"{name}.verbatim_eb.bin").write_bytes(donor_eb)
        _de = EbScript.from_bytes(donor_eb)
        dests = sorted({int(i.imm(0)) for e in _de.entries if not e.empty for f in e.funcs
                        for i in _de.instrs(f) if i.op == 0x2B and i.imm(0) is not None})
        # retarget the Field() exits: import-chain pre-fills a LIVE table (doors warp into the chain's own
        # member forks); a single-field import leaves the commented fill-in template (byte-identical golden).
        rt_text, n_retargeted = _vb.render_retarget(dests, id_remap)
        rt_intro = (
            "# The Field() exits are RETARGETED to this chain's own member forks (import-chain); ids left out\n"
            "# of the table stay live seams back into the real game:\n" if n_retargeted else
            "# The Field() exits below point at REAL fields (live seams back into the game). To redirect any to\n"
            "# your own fork, set its id and uncomment the table (omit a line to keep that exit a live seam):\n")
        # ship the donor's WHOLE text per language: the verbatim .eb's index-txids resolve straight into it
        # (no remap, unlike --carry-text). Per-lang is coarse (the dialogue reader groups langs) but us is right.
        mes_by_lang = {L: b for L in LANGS if (b := _dlg.extract_field_mes(field, L, game=game))}
        text_line = ""
        if mes_by_lang:
            (out / f"{name}.verbatim_mes.json").write_text(_json.dumps(mes_by_lang), encoding="utf-8")
            text_line = f'text = "{name}.verbatim_mes.json"   # the donor field text (its index-txids resolve in)\n'
        control_line = ""
        content_tail = (
            "# --- VERBATIM .eb fork: this field ships its REAL event script WHOLE (entry-0 + every object +\n"
            "# every gateway, slot layout intact) and runs the original logic, so the declarative blocks are\n"
            "# NOT used here. Add a [startup] block to boot a chosen story beat (its gating then responds). ---\n"
            "[verbatim_eb]\n"
            f'bin = "{name}.verbatim_eb.bin"\n'
            f"{text_line}"
            f"{rt_intro}{rt_text}")
        meta["imported_content"] = {"verbatim_eb": True, "field_exits": dests, "text": bool(mes_by_lang),
                                    "gateways_retargeted": n_retargeted}
    else:
        content_blocks, control_dir, content_summary = _content_for_import(
            field, game, out_dir=out, name=name, id_remap=id_remap, live_seams=live_seams,
            graft_player_funcs=graft_player_funcs, carry_text=carry_text, graft_savepoint=graft_savepoint)
        meta["imported_content"] = content_summary
        control_line = (f"control_direction = {control_dir}   # imported WASD-vs-camera tuning\n"
                        if control_dir is not None else "")
        content_tail = (
            "# --- add NPCs/dialogue (uncomment + edit); keep positions within the walkmesh bounds above ---\n"
            f'# [[npc]]\n# name = "Vivi"\n# preset = "vivi"\n# pos = [{x}, {z}]\n# dialogue = "Hello, traveler."\n\n'
            f"{_content_section(content_blocks, x, z)}")

    toml = (
        f"# NATIVE fork of {meta['field']} (area {meta['area']}) by ff9mapkit -- ships its OWN atlas.png +\n"
        f"# scene.bgs (the real per-tile-depth scene) + custom walkmesh, NO .bgx. The engine renders it via\n"
        f"# the SEAMLESS native path (point-sampled atlas, per-tile occlusion) -- exactly how Moguri ships.\n"
        f"# Repaint by editing atlas.png (or the Memoria PSD pipeline). Add content below, then build it.\n"
        f"# Camera: pitch {cm['pitch_deg']} deg, FOV {cm['fov_deg']} deg.  Walkmesh bounds: x {wb['x']}  z {wb['z']}.\n"
        f"{remap_note}\n"
        f"[field]\n"
        f"id = {field_id}\n"
        f'name = "{name}"\n'
        f"area = {safe_area}\n"
        f"text_block = {text_block}\n"
        f"{_walkmesh_hotfix_line(field)}"
        f"{_area_title_hide_lines(meta, verbatim=verbatim)}"
        f'bgs = "scene.bgs.bytes"   # NATIVE scene (per-tile depth) -> seamless render, NO .bgx / no tile seams\n'
        f'atlas = "atlas.png"\n'
        + ('mapconfig = "mapconfig.bytes"   # the real field LIGHTING (per-floor lights + shadows) for 3D models\n'
           if mc_bytes else "")
        + "\n"
        f"[camera]\n"
        f'borrow = "camera.bgx"   # content logic uses this; the RENDERED camera lives inside scene.bgs\n'
        f"{control_line}"
        f"{scroll}\n"
        f"[walkmesh]\n"
        f'bgi = "walkmesh.bgi"   # the real field\'s walkmesh -- connectivity preserved (faithful copy)\n\n'
        f"[player]\n"
        f"spawn = [{x}, {z}]\n\n"
        f"{content_tail}"
    )
    p = Path(out_dir) / f"{name}.field.toml"
    p.write_text(toml, encoding="utf-8", newline="\n")
    meta["field_toml"] = str(p)
    return meta, p


def write_field_project(field: str, out_dir, *, name: str | None = None, field_id: int = 4003,
                        text_block: int = 1073, game=None, bundle=None, want_atlas=False,
                        id_remap=None, live_seams=False, graft_player_funcs=False, carry_text=False,
                        graft_savepoint=False):
    """Extract a real field and emit a ready-to-edit BG-borrow field.toml + camera.bgx in out_dir.

    `name` is the custom script/field id (must be unique vs real fieldids; defaults to
    '<MAPID-first-token>_FORK', e.g. 'GRGR_FORK'). Returns (metadata, field_toml_path).
    `ff9mapkit build <path>` compiles it; the author fills in NPCs/gateways/dialogue first."""
    # BG-borrow reuses the REAL field's BG via FBG_N<area>_<mapid>; the engine builds that name with
    # no zero-padding and reads exactly 2 chars for the area, so single-digit areas (0-9) black-screen.
    # Catch it here with a clear pointer to --editable rather than emitting a field.toml that won't build.
    folder, _b = resolve_field(field, game)
    src_area, _m = parse_fbg_folder(folder)
    if src_area < MIN_CUSTOM_AREA:
        raise RuntimeError(
            f"{folder} is in area {src_area}: BG-borrow can't render single-digit areas (the engine "
            f"builds 'FBG_N<area>' and reads exactly 2 chars, so areas 0-9 black-screen). "
            f"Fork it as a custom scene instead:  ff9mapkit import {field} --editable  "
            f"(it ships its own art, so it runs at a safe area).")
    meta = extract_field(field, out_dir, game=game, bundle=bundle, want_atlas=want_atlas)
    name = name or (meta["mapid"].split("_")[0] + "_FORK")
    # real-art backdrop for the Blender import (only if the field was exported in-game once via
    # Memoria.ini [Export] Field=1). In-game still uses BG-borrow; this is the Blender modelling view.
    meta["background"] = None
    try:
        if compose_background(field, Path(out_dir) / "background.png", game=game, bundle=bundle):
            meta["background"] = "background.png"
    except Exception:
        pass
    # extract the real field's LIVE content (gateways / encounter / music / movement) from its .eb
    content_blocks, control_dir, content_summary = _content_for_import(
        field, game, out_dir=Path(out_dir), name=name, id_remap=id_remap, live_seams=live_seams,
        graft_player_funcs=graft_player_funcs, carry_text=carry_text, graft_savepoint=graft_savepoint)
    meta["imported_content"] = content_summary
    cm = meta["camera"]
    wb = meta["walkmesh_bounds"]
    x, z = meta["player_start"]
    scroll = "[camera.scroll]\nenabled = true\n" if meta["scrolling"] else ""
    control_line = f"control_direction = {control_dir}   # imported WASD-vs-camera tuning\n" if control_dir is not None else ""
    toml = (
        f"# Imported from {meta['field']} (area {meta['area']}) by ff9mapkit -- BG-borrow.\n"
        f"# Renders the REAL field's art + walkmesh + camera while running your script.\n"
        f"# Camera: pitch {cm['pitch_deg']} deg, FOV {cm['fov_deg']} deg, range {cm['range'][0]}x{cm['range'][1]}"
        f"{' (SCROLLING)' if meta['scrolling'] else ''}.\n"
        f"# Walkmesh bounds: x {wb['x']}  z {wb['z']}  -- place NPCs/gateways within these.\n"
        f"# Edit the content below, then:  ff9mapkit build {name}.field.toml\n\n"
        f"[field]\n"
        f"id = {field_id}\n"
        f'name = "{name}"\n'
        f"area = {meta['area']}\n"
        f'borrow_bg = "{meta["mapid"]}"\n'
        f"text_block = {text_block}\n\n"
        f"[camera]\n"
        f'borrow = "camera.bgx"\n'
        f"{control_line}"
        f"{scroll}\n"
        f"[walkmesh]\n"
        f'reference = "walkmesh.bgi"   # validation only -- NOT shipped (the engine uses the borrowed\n'
        f"# field's real walkmesh). The build WARNS if the content below sits off this walkable area.\n\n"
        f"[player]\n"
        f"spawn = [{x}, {z}]\n\n"
        f"# --- add NPCs/dialogue (uncomment + edit); keep positions within the walkmesh bounds above ---\n"
        f'# [[npc]]\n# name = "Vivi"\n# preset = "vivi"\n# pos = [{x}, {z}]\n# dialogue = "Hello, traveler."\n\n'
        f"{_content_section(content_blocks, x, z)}"
    )
    p = Path(out_dir) / f"{name}.field.toml"
    p.write_text(toml, encoding="utf-8", newline="\n")
    meta["field_toml"] = str(p)
    return meta, p


def write_lightweight_project(field: str, out_dir, *, name: str | None = None, field_id: int = 4003,
                              text_block: int = 1073, game=None, bundle=None):
    """A LIGHTWEIGHT, Blender model-against project for a real field: camera.bgx + walkmesh (.bgi + a
    reshapeable .obj, + links for multi-floor) + a composited ``background.png`` + a compact field.toml --
    and NO per-depth layer split. This is the per-field unit of the whole-game ``import-all`` archive:
    small + fast, enough to browse and to model markers/geometry against in Blender's *Import Field*.

    UNIVERSAL across areas (unlike BG-borrow, which black-screens area<10): an area>=10 field gets a
    buildable BG-borrow toml; an area<10 field gets a MODEL-AGAINST stub toml (you promote it with
    ``import <field> --editable``/``--native`` to actually build/ship). To repaint per-depth layers or
    reshape into a custom scene, re-run ``ff9mapkit import <field> --editable`` into the SAME folder."""
    out = Path(out_dir)
    meta = extract_field(field, out, game=game, bundle=bundle)        # camera.bgx + walkmesh.bgi
    wm = bgi.BgiWalkmesh.from_bytes((out / "walkmesh.bgi").read_bytes())
    (out / "walkmesh.obj").write_text(_world_walkmesh_obj_text(wm), encoding="utf-8", newline="\n")
    if len(wm.floors) > 1:
        _write_links_toml(wm, out / "walkmesh.links.toml")
    try:                                                             # the model-against backdrop (no footprint)
        compose_background(field, out / "background.png", game=game, bundle=bundle,
                           draw_footprint=False, camera_index=0)
        # MULTI-camera field: also write a clean per-camera backdrop (camera 0 = background.png above;
        # cameras 1.. here) so Blender's Import Field shows each camera its OWN art instead of all
        # overlays jammed onto camera 0's canvas (the "molded together" look). A single-camera field
        # writes nothing extra -- camera_index=0 already == the whole scene (every overlay is camNdx 0).
        ncams = len(cam.parse_bgx_cameras(str(out / "camera.bgx")))
        for k in range(1, ncams):
            compose_background(field, out / f"background_cam{k:02d}.png", game=game, bundle=bundle,
                               draw_footprint=False, camera_index=k)
    except Exception:                                                # noqa: BLE001 - preview only, never fatal
        pass
    name = name or (meta["mapid"].split("_")[0] + "_FORK")
    area = meta["area"]
    borrowable = area >= MIN_CUSTOM_AREA
    safe_area = area if borrowable else safe_custom_area(area)
    wb = meta["walkmesh_bounds"]
    x, z = meta["player_start"]
    scroll = "[camera.scroll]\nenabled = true\n" if meta["scrolling"] else ""
    note = ("" if borrowable else
            f"# area {area} < 10: BG-borrow can't render it in-game (the engine's FBG_N<area> 2-char lookup), so\n"
            f"# this is a MODEL-AGAINST stub. To build/ship, re-run `ff9mapkit import {field} --editable` (or --native).\n")
    borrow_line = f'borrow_bg = "{meta["mapid"]}"\n' if borrowable else ""
    wm_stanza = ('reference = "walkmesh.bgi"   # borrow: the engine uses the real field walkmesh (validation only)'
                 if borrowable else 'bgi = "walkmesh.bgi"')
    toml = (
        f"# LIGHTWEIGHT model-against fork of {meta['field']} (area {area}) -- camera + walkmesh + a composited\n"
        f"# background.png for Blender 'Import Field'. NOT a repaint project: promote with `--editable` to get\n"
        f"# repaintable per-depth layers / reshape into a custom scene.  Walkmesh bounds: x {wb['x']} z {wb['z']}.\n"
        f"{note}"
        f"[field]\nid = {field_id}\nname = \"{name}\"\narea = {safe_area}\n{borrow_line}text_block = {text_block}\n\n"
        f"[camera]\nborrow = \"camera.bgx\"\n{scroll}\n"
        f"[walkmesh]\n{wm_stanza}\n\n"
        f"[player]\nspawn = [{x}, {z}]\n\n"
        f"{_content_section('', x, z)}"
    )
    p = out / f"{name}.field.toml"
    p.write_text(toml, encoding="utf-8", newline="\n")
    meta["field_toml"] = str(p)
    return meta, p


def _bulk_import(entries, *, editable=False, game=None, on_field=None) -> dict:
    """Run the per-field writer over ``entries`` = [(token, dest_dir, label)], never raising on a single bad
    field. ``editable`` picks the full custom-scene fork vs the lightweight model-against project.
    ``on_field(k, total, label, dest|None, err|None)`` is an optional progress callback. Returns
    {fields, failed:[(label, err)], total}."""
    entries = list(entries)
    total = len(entries)
    n_fields = 0
    failed = []
    for k, (token, dest, label) in enumerate(entries):
        try:
            if editable:
                write_editable_project(token, dest, game=game)
            else:
                write_lightweight_project(token, dest, game=game)
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            failed.append((str(label), str(e)))
            if on_field:
                on_field(k + 1, total, str(label), None, str(e))
            continue
        n_fields += 1
        if on_field:
            on_field(k + 1, total, str(label), str(dest), None)
    return {"fields": n_fields, "failed": failed, "total": total}


def import_all(out_root, *, game=None, pattern=None, editable=False, on_field=None) -> dict:
    """Bulk-import EVERY real field (optionally filtered by ``pattern``) into a foldered Blender-ready
    archive at ``<out_root>/<ZONE>/<FBG>/``, OFFLINE -- a quick whole-game source-of-truth to browse and
    copy field folders out of. Lightweight by default (camera+walkmesh+background+toml); ``editable`` =
    full repaintable custom scenes. The output is SE-derived art -- point ``out_root`` at a gitignored path."""
    root = Path(out_root)
    entries = []
    for folder, _area, mapid in list_fields(pattern, game=game):
        zone = mapid.split("_")[0]                                   # FBG zone token (ICCV, ALXT, ...)
        entries.append((folder, root / zone / folder.upper(), folder))
    return _bulk_import(entries, editable=editable, game=game, on_field=on_field)


def import_campaign_fields(campaign_toml, out_root, *, game=None, editable=False, on_field=None) -> dict:
    """Bulk-import the real fields a campaign forks (its members' ``source`` donors) into
    ``<out_root>/<CAMPAIGN>/<MEMBER>/``, OFFLINE -- a campaign-foldered slice of the archive. See
    :func:`import_all`."""
    from . import campaign as _camp
    plan = _camp.load_campaign(campaign_toml)
    root = Path(out_root) / (plan.name or "CAMPAIGN")
    entries = []
    seen = set()
    for m in plan.members:
        if not m.real_id or m.real_id in seen:
            continue
        seen.add(m.real_id)
        entries.append((str(m.real_id), root / m.name, m.name))
    if not entries:
        raise ValueError(f"{campaign_toml}: no member fields with a real `source` id to import")
    return _bulk_import(entries, editable=editable, game=game, on_field=on_field)
