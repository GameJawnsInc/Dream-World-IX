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
from pathlib import Path

from . import config
from . import eventscan
from ._fieldtable import FBG_TO_EVT
from .scene import bgs, bgi, cam


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
    """(folder, bundle) for a field name (full FBG, bare mapid, or unique substring) via the index."""
    want = re.sub(r"^fbg_n\d+_", "", field.strip().lower())
    index = build_field_index(game, verbose=True)
    if field.strip().lower() in index:
        f = field.strip().lower()
        return f, index[f]
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
        UnityPy = _unitypy()
        env = UnityPy.load(str(_streaming_assets(game) / bundle))
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
        UnityPy = _unitypy()
        env = UnityPy.load(str(_streaming_assets(game) / bundle))
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
        UnityPy = _unitypy()
        bundle = _events_bundle(game)
        if not bundle:
            raise RuntimeError(
                "could not locate the field event bundle (eventbinary/field/...) in StreamingAssets/p0data*.bin")
        self.lang = lang
        env = UnityPy.load(str(_streaming_assets(game) / bundle))
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
    n_retargeted = n_seamed = 0
    if gws:
        if id_remap is None:
            parts.append(
                "# --- EXITS imported from the real field (LIVE). `to` is the REAL destination field id --\n"
                "# retarget each to your own room ids, or leave them to walk back into the live game. ---")
        else:
            parts.append("# --- EXITS retargeted to this chain's own field ids (import-chain). "
                         "Out-of-chain exits are commented seam stubs. ---")
        for g in gws:
            zone = ", ".join(f"[{x}, {z}]" for x, z in g["zone"])
            raw_to = int(g["to"])
            if id_remap is None or raw_to in id_remap:
                to = id_remap[raw_to] if id_remap else raw_to
                parts.append(f"[[gateway]]\nto = {to}\nentrance = {g['entrance']}\nzone = [{zone}]")
                n_retargeted += 1 if id_remap is not None else 0
            elif live_seams:
                parts.append(f"# SEAM (live): real field {raw_to} -- a door back into the live game\n"
                             f"[[gateway]]\nto = {raw_to}\nentrance = {g['entrance']}\nzone = [{zone}]")
                n_seamed += 1
            else:
                parts.append(f"# SEAM (out-of-chain): real field {raw_to} via this zone -- author by hand.\n"
                             f"# [[gateway]]\n# to = {raw_to}\n# entrance = {g['entrance']}\n# zone = [{zone}]")
                n_seamed += 1
    enc = content["encounter"]
    if enc:
        block = f"[encounter]\nscene = {enc['scenes'][0]}\nfreq = {enc['freq']}"
        if len(set(enc["scenes"])) != 1:
            block += f"\nscenes = [{', '.join(str(s) for s in enc['scenes'])}]"
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
               "control_direction": content["control_direction"], "ladders": n_ladders,
               "jumps": n_jumps, "objects": n_objects, "player_funcs": n_player_funcs,
               "carry_text": n_carry_text, "save_moogle": n_save_moogle,
               "spawn_flash": sum(1 for o in objs if o.get("spawn_flash")),   # P6.1: Init pose != rest -> flashes on a fork
               "spawn_flash_fixed": (1 if (graft_savepoint and n_save_moogle) else 0),
               "gateways_retargeted": n_retargeted, "gateways_seamed": n_seamed}
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
    fid = None
    if carry_text or graft_savepoint:                    # both want the resolved donor field id
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
    UnityPy = _unitypy()
    sa = _streaming_assets(game)
    folder = None
    if not bundle:
        folder, bundle = resolve_field(field, game)
    env = UnityPy.load(str(sa / bundle))
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
    _oncam_verts = [(px, pz) for px, pz in zip(wx, wz) if _oncam(px, pz)]
    _clear_oncam = [p for p in _oncam_verts if _clear(*p)]
    _spawn = next((p for p in _cp if _inb(*p) and _oncam(*p) and _clear(*p)), None)
    if _spawn is None and _oncam_verts:                       # nearest-to-centre visible vert, clear if any
        mcx = sum(p[0] for p in _oncam_verts) / len(_oncam_verts)
        mcz = sum(p[1] for p in _oncam_verts) / len(_oncam_verts)
        pool = _clear_oncam or _oncam_verts
        _spawn = min(pool, key=lambda p: (p[0] - mcx) ** 2 + (p[1] - mcz) ** 2)
    if _spawn is None:                                        # no on-camera verts: in-bounds / centroid
        _spawn = next((p for p in _cp if _inb(*p)), (sum(wx) / len(wx), sum(wz) / len(wz)))
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
    if it hasn't been exported in-game yet (StreamingAssets/FieldMaps/<FBG>/Overlay*.png)."""
    folder, _ = resolve_field(field, game)
    d = config.find_game_path(game) / "StreamingAssets" / "FieldMaps" / folder.upper()
    return d if (d / "Overlay0.png").is_file() else None


def compose_background(field: str, out_path, *, game=None, bundle=None, upscale=4,
                       draw_footprint=True):
    """Composite the field's OPAQUE base art into one background PNG, for the Blender backdrop.

    Uses Memoria's engine-exported per-overlay PNGs (correct tile assembly) placed by the .bgs
    overlay positions/depths; skips additive/subtractive light+shadow overlays (the "splotches").
    When `draw_footprint` (default), also draws the walkable footprint -- the .bgi tris projected by
    the EXACT GTE->canvas map (cam.to_canvas), with NO offset: the engine projects the raw walkmesh
    frame directly, so this lands exactly where the player walks in-game. The walkmesh may extend
    past the canvas edges (tunnels) -- that's correct, not a misalignment. Returns (w, h) or None
    if the field hasn't been exported in-game yet."""
    art = field_art_dir(field, game)
    if art is None:
        return None
    from PIL import Image, ImageDraw  # noqa: PLC0415 - only the art path needs PIL
    _, _, roles, env = find_field(field, game=game, bundle=bundle)
    bgs_bytes = _raw_bytes(env.container[roles["bgs"]].read())
    h, overlays = bgs.parse_overlays(bgs_bytes)
    bgs.resolve_sprites(bgs_bytes, overlays, 2048, 40)        # atlas params irrelevant for positions
    sOrgX, sOrgY = h.bounds[2], h.bounds[3]
    c0 = bgs.parse_cameras(bgs_bytes)[0]
    W, H = c0.range[0] * upscale, c0.range[1] * upscale
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    opaque = [(i, o) for i, o in enumerate(overlays) if o.sprites and o.sprites[0].trans == 0]
    opaque.sort(key=lambda io: -(io[1].curZ + io[1].orgZ))    # back (high depth) -> front
    for i, o in opaque:
        png = art / f"Overlay{i}.png"
        if not png.is_file():
            continue
        im = Image.open(png).convert("RGBA")
        mnX = min(s.offX for s in o.sprites)
        mnY = min(s.offY for s in o.sprites)
        canvas.alpha_composite(im, ((sOrgX + o.orgX + mnX) * upscale, (sOrgY + o.orgY + mnY) * upscale))

    if draw_footprint and "bgi" in roles:
        wm = bgi.BgiWalkmesh.from_bytes(_raw_bytes(env.container[roles["bgi"]].read()))
        wv = wm.world_verts()                          # vert + orgPos + per-floor floor.org
        draw = ImageDraw.Draw(canvas, "RGBA")
        for t in wm.tris:
            pts = []
            for vi in t.vtx:
                cx, cy = cam.to_canvas(wv[vi], c0)      # exact GTE projection, world frame
                pts.append((cx * upscale, cy * upscale))
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


def extract_layers(field: str, out_dir, *, game=None, bundle=None, upscale=4, include_blend=True,
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

    Tiles are cropped from the engine's exported `Overlay{i}.png` (correct tile assembly) via
    `bgs.tile_box`. `depth_tolerance` buckets nearby depths into one layer (1 = exact per-distinct-depth);
    the default 8 keeps each smooth surface whole (real surfaces vary only a few depth units per tile)
    while still splitting at the big depth jumps that actually occlude. `max_layers` then auto-coarsens
    the tolerance until the count fits (default 48) -- a real field can split into HUNDREDS of distinct
    tile depths (field 122 = 215 at tol 1), which both lags the load (one GameObject/texture per layer)
    and multiplies tile-cut seams. `bleed` edge-extends opaque layers to hide the bilinear cut seams.
    Tune `depth_tolerance` up for fewer layers (snappier load, coarser occlusion) or down for finer
    occlusion. Returns None if the field hasn't been `[Export] Field=1`'d in-game yet (no per-overlay PNGs
    on disk). `include_blend` (default) emits the additive/subtractive light+shadow overlays too.

    Co-located tiles sharing a (depth-bucket, shader) merge into one layer (correct for a tiled plane,
    approximate for overlapping animation frames at the same depth -- a known v1 simplification)."""
    art = field_art_dir(field, game)
    if art is None:
        return None
    from PIL import Image  # noqa: PLC0415 - only the art path needs PIL
    _, _, roles, env = find_field(field, game=game, bundle=bundle)
    bgs_bytes = _raw_bytes(env.container[roles["bgs"]].read())
    h, overlays = bgs.parse_overlays(bgs_bytes)
    bgs.resolve_sprites(bgs_bytes, overlays, 2048, 40)        # atlas params irrelevant for off/depth
    sOrgX, sOrgY, sOrgZ = h.bounds[2], h.bounds[3], h.bounds[0]
    c0 = bgs.parse_cameras(bgs_bytes)[0]

    def _has_png(i):
        return (art / f"Overlay{i}.png").is_file()

    tol = max(1, int(depth_tolerance))
    groups, skipped = _depth_groups(overlays, sOrgX, sOrgY, sOrgZ, _has_png,
                                    include_blend=include_blend, depth_tolerance=tol)
    while len(groups) > max_layers and tol < 4096:            # runaway-field backstop: coarsen the bucket
        tol *= 2
        groups, skipped = _depth_groups(overlays, sOrgX, sOrgY, sOrgZ, _has_png,
                                        include_blend=include_blend, depth_tolerance=tol)

    png_cache = {}
    def _png(i):
        im = png_cache.get(i)
        if im is None:
            im = png_cache[i] = Image.open(art / f"Overlay{i}.png").convert("RGBA")
        return im

    layers, blend = _render_depth_groups(groups, _png, out_dir, upscale=upscale, bleed=bleed)
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


def write_editable_project(field: str, out_dir, *, name: str | None = None, field_id: int = 4003,
                           text_block: int = 1073, game=None, bundle=None,
                           id_remap=None, live_seams=False, graft_player_funcs=False, carry_text=False,
                         graft_savepoint=False):
    """Fork a real field as a fully EDITABLE custom scene (vs BG-borrow): re-export its walkmesh via the
    world-frame builder + extract its art as per-DEPTH layers (occlusion preserved) + reuse its camera.

    Emits a custom-scene `field.toml` (NO borrow_bg) ready for `ff9mapkit build` and for repainting any
    single `layer_*.png` / editing `walkmesh.obj`. Returns (metadata, field_toml_path). Requires the
    field to have been `[Export] Field=1`'d in-game once (per-overlay PNGs on disk); raises RuntimeError
    with guidance otherwise (use plain import for a BG-borrow fork that reuses the art as-is)."""
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
    wm = bgi.BgiWalkmesh.from_bytes((out / "walkmesh.bgi").read_bytes())
    nfloors = len(wm.floors)
    (out / "walkmesh.obj").write_text(_world_walkmesh_obj_text(wm), encoding="utf-8", newline="\n")
    nseams = _write_links_toml(wm, out / "walkmesh.links.toml") if nfloors > 1 else 0

    layers_info = extract_layers(field, out, game=game, bundle=bundle)
    if layers_info is None:
        raise RuntimeError(
            f"{meta['field']}: editable art needs the field exported in-game once. Set Memoria.ini "
            f"[Export] Enabled=1 + Field=1, visit the field, then retry -- OR use `ff9mapkit import "
            f"{field}` (BG-borrow: reuses the real art as-is, no repaint).")
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
        f"{remap_note}\n"
        f"[field]\n"
        f"id = {field_id}\n"
        f'name = "{name}"\n'
        f"area = {safe_area}\n"
        f"text_block = {text_block}\n\n"
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


def write_native_project(field: str, out_dir, *, name: str | None = None, field_id: int = 4003,
                         text_block: int = 1073, game=None, bundle=None,
                         id_remap=None, live_seams=False, graft_player_funcs=False, carry_text=False,
                         graft_savepoint=False):
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

    content_blocks, control_dir, content_summary = _content_for_import(
        field, game, out_dir=out, name=name, id_remap=id_remap, live_seams=live_seams,
        graft_player_funcs=graft_player_funcs, carry_text=carry_text, graft_savepoint=graft_savepoint)
    meta["imported_content"] = content_summary
    cm = meta["camera"]
    wb = meta["walkmesh_bounds"]
    x, z = meta["player_start"]
    scroll = "[camera.scroll]\nenabled = true\n" if meta["scrolling"] else ""
    control_line = f"control_direction = {control_dir}   # imported WASD-vs-camera tuning\n" if control_dir is not None else ""

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
        f"# --- add NPCs/dialogue (uncomment + edit); keep positions within the walkmesh bounds above ---\n"
        f'# [[npc]]\n# name = "Vivi"\n# preset = "vivi"\n# pos = [{x}, {z}]\n# dialogue = "Hello, traveler."\n\n'
        f"{_content_section(content_blocks, x, z)}"
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
