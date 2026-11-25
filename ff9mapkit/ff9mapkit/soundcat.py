"""The SOUND CATALOG -- every sound an FF9 install ships: listed, named, placed, and extractable.

:mod:`ff9mapkit.sound` owns WRITING audio (encode an Ogg, drop the loose override, mint a new id).
This module owns READING it, and it is what the Workspace's Sounds tab renders:

* **what exists** -- four kinds, each an id -> ResourceID manifest in ``resources.assets``:
  ``music`` (the BGM tracks), ``sfx`` (sound effects, in ``SE##`` banks), ``stream`` (the engine's
  "Song" profile: ambience and vocals under ``Sounds02/song_``) and ``movie`` (FMV audio);
* **what it is called** -- ``data/sound_names.toml`` (kit-authored titles keyed by FILE STEM) under a
  per-user overlay the browser writes when its user names a sound by ear;
* **where it is used** -- a census of every real field's ``.eb``: each ``RunSoundCode*`` names an
  object kind and an id (see :func:`decode_sound_code`), and on the shipping game every such operand
  is an immediate, so the join is exact. Battle-effect sounds are placed by the install's own
  ``SpecialEffectMetaData.txt`` instead (effect id -> the sounds that effect loads);
* **the audio itself** -- an ``.akb.bytes`` TextAsset in a ``p0data`` bundle is a 304-byte ``AKB2``
  header followed by a plain Ogg Vorbis stream, so :func:`extract_ogg` is a slice, not a transcode.

* **what it probably is** -- most effects have no name anywhere, so :func:`lore` DESCRIBES a sound
  from how the game uses it: the battle effect that loads it ("Fire (single)", names from
  ``_effectnames.py``), the monster whose death or battle cry it is (the battle scenes' own records),
  what a field script was doing when it played it (a door, a pickup, a Moogle's talk handler, an
  ambience loop), or -- failing all of that -- the area set its bank belongs to. A description is
  never a name: the browser shows it in italics and "Unnamed only" still counts it.

Provenance: nothing here is baked from the game. Manifests, the census and every extracted Ogg are
read LIVE from the user's own install and cached under :func:`provision.cache_dir` (gitignored); the
only shipped data is the names file, which holds titles and no game bytes.

Cost model (measured): one bundle open is ~0.1 s and holds ~400 MB while the handle lives, so
:func:`read_akb` opens, reads and RELEASES -- it never joins ``extract``'s long-lived bundle memo.
A cold map is ~16 s (field scripts ~5, every sound's header ~7, battle scenes ~3) and one JSON
read warm.
"""
from __future__ import annotations

import json
import re
import shutil
import struct
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path

from . import fsutil, provision, sound

KINDS = ("music", "sfx", "stream", "movie")
KIND_LABEL = {"music": "Music", "sfx": "Sound effects", "stream": "Streams", "movie": "Movie audio"}
KIND_NOUN = {"music": "music track", "sfx": "sound effect", "stream": "stream", "movie": "movie audio track"}

CACHE_VERSION = 2
_CACHE_SUBDIR = "soundmap"
_CACHE_FILE = "soundmap.json"
_OGG_SUBDIR = "sound_ogg"
OGG_CACHE_LIMIT = 256 * 1024 * 1024        # the extracted-Ogg cache is pruned oldest-first past this

EFFECT_MANIFEST = "SpecialEffectMetaData.txt"

# ---------------------------------------------------------------------------- the sound-code bitfield
# RunSoundCode* (0xC5-0xC8) arg 0 is a packed word (Memoria FF9Snd.cs, the FF9SOUND_* shifts):
#   bits 12-13 = the OBJECT kind, bits 8-11 = the operation. Arg 1 is that object's id.
_OBJ_KIND = {0: "music", 1: "sfx", 2: "stream", 3: "instr"}
_OP_NAME = {0: "start", 1: "stop", 2: "set", 3: "intpl", 4: "fade", 5: "setall", 6: "intplall",
            7: "load", 8: "suspend", 9: "restore", 10: "setglobal", 11: "fadeall", 12: "sync"}
RUN_SOUND_OPS = (0xC5, 0xC6, 0xC7, 0xC8)
NO_OBJECT = 0xFFFF                          # "whatever is current" -- names no sound


def decode_sound_code(code: int) -> tuple:
    """``(object kind, operation)`` for a ``RunSoundCode`` word, e.g. ``0 -> ("music", "start")``,
    ``1792 -> ("music", "load")``, ``4096 -> ("sfx", "start")``. An operation outside the engine's
    table decodes as ``"op<N>"`` rather than raising -- the census records, it never judges."""
    code = int(code)
    op = (code >> 8) & 15
    return _OBJ_KIND[(code >> 12) & 3], _OP_NAME.get(op, f"op{op}")


def scan_field_sounds(eb_bytes) -> list:
    """Every sound a field script names: sorted unique ``(kind, id)`` pairs from its ``RunSoundCode*``
    instructions. A computed (non-immediate) operand and the ``0xFFFF`` "current object" id name no
    particular sound and are skipped. Pure -- takes ``.eb`` bytes, touches no install."""
    from .eb.model import EbScript
    eb = EbScript.from_bytes(eb_bytes)
    out = set()
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op not in RUN_SOUND_OPS:
                    continue
                code, sid = ins.imm(0), ins.imm(1)
                if code is None or sid is None or int(sid) == NO_OBJECT:
                    continue
                kind, _op = decode_sound_code(code)
                if kind in KINDS:
                    out.add((kind, int(sid)))
    return sorted(out)


# ----------------------------------------------------------------------- how a script uses a sound
SETMODEL_OP, SETREGION_OP, FIELD_OP, WORLDMAP_OP, ADDITEM_OP, DEFINE_PC_OP = 0x2F, 0x29, 0x2B, 0xB6, 0x48, 0x2C
BATTLE_OPS = (0x2A, 0x8C)                   # Battle / BattleEx
WINDOW_OPS = (0x1F, 0x20, 0x95, 0x96)       # WindowSync / WindowAsync and their Ex forms
_PARM_NULL = 8                              # FF9SOUND_PARM_NULL: the code names a sound and does nothing
_MEM_RESIDENT = 128                         # FF9SOUND_MEM_FLAG_RESIDENT: a sound held in memory (loops)
_SHAPE_OPS = ("set", "intpl", "fade", "setall", "intplall", "fadeall", "setglobal")
_TAG_CLASS = {0: "init", 1: "loop", 2: "touch", 3: "talk", 10: "reinit"}   # else "routine"


def sound_op(code: int) -> str:
    """What a ``RunSoundCode`` word DOES to the sound it names:

    ``play`` (start it), ``sustain`` (start a RESIDENT effect -- the loops a script later fades and
    stops), ``stop``, ``shape`` (change volume / pan / pitch), ``load``, or ``preload``. ``preload`` is
    ``FF9SOUND_*_NULL``: the engine's own log line for it is "means ignore", a PSX-era "this script will
    need that sound" that plays nothing -- which is exactly why it is worth recording: a sound a
    character only ever preloads is one the ENGINE plays for it (footsteps), never a script."""
    kind, op = decode_sound_code(code)
    if op == "start":
        return "sustain" if kind == "sfx" and int(code) & _MEM_RESIDENT else "play"
    if op in ("stop", "load"):
        return op
    if op in _SHAPE_OPS:
        return "preload" if int(code) & 63 == _PARM_NULL else "shape"
    return "other"


def scan_field_usage(eb_bytes) -> list:
    """Every sound a field script names, WITH what the script was doing: one record per (function,
    sound, op) -- ``{"kind", "id", "op", "role", "tag", "flags", "model"}``.

    ``role`` is the script entry's part: ``main`` (entry 0), ``player`` (it defines the player
    character), ``object`` (it wears a model -- ``model`` is that id), ``region`` (a trigger polygon) or
    ``logic``. ``tag`` is the function's moment (init / loop / touch / talk / reinit / routine) and
    ``flags`` what else that function does: ``warp`` / ``battle`` / ``item`` / ``text``. Pure."""
    from .eb.model import EbScript
    eb = EbScript.from_bytes(eb_bytes)
    out = []
    for e in eb.entries:
        if e.empty:
            continue
        model, region, player, funcs = None, False, False, []
        for f in e.funcs:
            flags, refs = set(), set()
            for ins in eb.instrs(f):
                op = ins.op
                if op in RUN_SOUND_OPS:
                    code, sid = ins.imm(0), ins.imm(1)
                    if code is None or sid is None or int(sid) == NO_OBJECT:
                        continue
                    kind, _o = decode_sound_code(code)
                    if kind in KINDS:
                        refs.add((kind, int(sid), sound_op(code)))
                elif op == SETMODEL_OP:
                    if model is None and ins.imm(0) is not None:
                        model = int(ins.imm(0))
                elif op == SETREGION_OP:
                    region = True
                elif op == DEFINE_PC_OP:
                    player = True
                elif op in (FIELD_OP, WORLDMAP_OP):
                    flags.add("warp")
                elif op in BATTLE_OPS:
                    flags.add("battle")
                elif op == ADDITEM_OP:
                    flags.add("item")
                elif op in WINDOW_OPS:
                    flags.add("text")
            if refs:
                funcs.append((_TAG_CLASS.get(f.tag, "routine"), tuple(sorted(flags)), refs))
        if not funcs:
            continue
        role = ("main" if e.index == 0 else "player" if player else "object" if model is not None
                else "region" if region else "logic")
        for tag, flags, refs in funcs:
            for kind, sid, op in sorted(refs):
                out.append({"kind": kind, "id": sid, "op": op, "role": role, "tag": tag,
                            "flags": flags, "model": model})
    return out


# ------------------------------------------------------------------------------------------ the map
@dataclass
class SoundMap:
    """Everything the browser lists, in one JSON-cacheable value.

    ``rows[kind]`` = ``[{"id", "resource_id"}]`` sorted by id; ``uses[kind][id]`` = the sorted field ids
    whose script names that sound; ``effects[resource_id]`` = the sorted battle special-effect ids that
    load it. ``stamp`` identifies the ``resources.assets`` the map was read from, so a game update
    invalidates the disk cache instead of serving a stale list."""
    version: int = CACHE_VERSION
    stamp: str = ""
    rows: dict = field(default_factory=dict)
    uses: dict = field(default_factory=dict)
    effects: dict = field(default_factory=dict)
    field_count: int = 0
    # the DESCRIBING lanes (see lore()). ``contexts[kind][id]`` = ``{"ops": {op: n}, "play": [[role, tag,
    # "flag+flag", n]], "pre": [...], "models": [[model id, n]], "pmodels": [...]}`` -- how field scripts
    # use the sound (see summarize_usage);
    # ``monsters[sfx id]`` = ``{"die": [names], "start": [names]}`` from the battle scenes; ``audio[
    # resource_id]`` = ``[seconds, loops, channels]`` read from every sound's own header; ``gaps`` = the
    # lanes that could not be read (a missing bundle costs its lane, never the list).
    contexts: dict = field(default_factory=dict)
    monsters: dict = field(default_factory=dict)
    audio: dict = field(default_factory=dict)
    gaps: list = field(default_factory=list)


def parse_effect_manifest(text: str) -> dict:
    """``SpecialEffectMetaData.txt`` (``{"data": {"<effect id>": [resource ids]}}``) ->
    ``{resource_id: [effect ids]}``, sorted. Malformed input yields ``{}`` -- the file is data."""
    try:
        data = json.loads(text).get("data", {})
    except (ValueError, AttributeError):
        return {}
    out: dict = {}
    if not isinstance(data, dict):
        return out
    for eff, paths in data.items():
        try:
            eid = int(eff)
        except (TypeError, ValueError):
            continue
        for p in paths or ():
            out.setdefault(str(p), set()).add(eid)
    return {k: sorted(v) for k, v in out.items()}


def _stamp(game=None) -> str:
    ra = sound.resources_assets_path(game)
    st = ra.stat()
    return f"{st.st_size}-{int(st.st_mtime)}"


_CTX_KEEP, _MODEL_KEEP, _NAMES_KEEP = 6, 5, 12     # how much of each tally a map keeps per sound


class _Usage:
    """One sound's tally while the census runs (see :func:`summarize_usage` for what is kept)."""
    __slots__ = ("ops", "play", "pre", "play_models", "pre_models")

    def __init__(self):
        self.ops, self.play, self.pre = {}, {}, {}
        self.play_models, self.pre_models = {}, {}

    def add(self, rec):
        op = rec["op"]
        self.ops[op] = self.ops.get(op, 0) + 1
        lane = "play" if op in ("play", "sustain") else "pre" if op == "preload" else None
        if lane is None:                           # a stop / fade says nothing about what the sound IS
            return
        key = (rec["role"], rec["tag"], "+".join(rec["flags"]))
        tally = self.play if lane == "play" else self.pre
        tally[key] = tally.get(key, 0) + 1
        if rec["model"] is not None:
            models = self.play_models if lane == "play" else self.pre_models
            models[rec["model"]] = models.get(rec["model"], 0) + 1


def _top(tally: dict, keep: int) -> list:
    return sorted(tally.items(), key=lambda kv: (-kv[1], str(kv[0])))[:keep]


def summarize_usage(u: "_Usage") -> dict:
    """The JSON-able summary a map keeps: the op counts, the commonest PLAY contexts and (kept apart)
    PRELOAD contexts, and the models of the entries that play it (``models``) and of those that only
    preload it (``pmodels``) -- kept apart because a character's footstep is preloaded by thousands of
    scripts and played by a handful, and the thousands are the truth about it."""
    return {"ops": dict(sorted(u.ops.items())),
            "play": [[r, t, f, n] for (r, t, f), n in _top(u.play, _CTX_KEEP)],
            "pre": [[r, t, f, n] for (r, t, f), n in _top(u.pre, _CTX_KEEP)],
            "models": [[m, n] for m, n in _top(u.play_models, _MODEL_KEEP)],
            "pmodels": [[m, n] for m, n in _top(u.pre_models, _MODEL_KEEP)]}


def _field_census(game=None) -> tuple:
    """``(uses, contexts, field_count)`` -- one pass over every real field's ``.eb`` (the
    ``battle.locate`` census shape: one bundle load, then an instruction walk per field)."""
    from . import extract as _extract
    from ._fieldtable import FIELD_BY_ID
    bundle = _extract.EventBundle(game=game)
    uses: dict = {k: {} for k in KINDS}
    usage: dict = {k: {} for k in KINDS}
    n = 0
    for fid in sorted(FIELD_BY_ID):
        eb_bytes = bundle.eb_for_id(fid)
        if eb_bytes is None:
            continue
        n += 1
        seen = set()
        for rec in scan_field_usage(eb_bytes):
            kind, sid = rec["kind"], rec["id"]
            if (kind, sid) not in seen:
                seen.add((kind, sid))
                uses[kind].setdefault(sid, []).append(fid)
            usage[kind].setdefault(sid, _Usage()).add(rec)
    contexts = {k: {sid: summarize_usage(u) for sid, u in d.items()} for k, d in usage.items()}
    return uses, contexts, n


def scene_monster_sounds(raw16: bytes, names) -> dict:
    """One battle scene's ``{sfx id: {"die" | "start": {monster names}}}``. A monster record carries
    the sound it makes dying and the one it makes as the fight opens; ``names`` is that scene's own
    name list, by type index (a missing name names nothing). Pure."""
    from .battle import scene_codec
    out: dict = {}
    for i, mon in enumerate(scene_codec.parse_scene(raw16).monsters):
        name = names[i] if i < len(names) else None
        if not name:
            continue
        for slot, sid in (("die", mon.die_sfx), ("start", mon.start_sfx)):
            if sid not in (0, NO_OBJECT):
                out.setdefault(int(sid), {}).setdefault(slot, set()).add(str(name))
    return out


def _battle_census(game=None) -> dict:
    """``{sfx id: {"die": [names], "start": [names]}}`` across every battle scene: one bundle pass for
    the scene records, and the monsters' names from the battle map when one is warm, else from the
    install's battle text directly (NOT ``battle.locate.build_map`` -- its field census is 6 s of work
    this lane has no use for)."""
    from .battle import locate
    raw16s = locate._scan_raw16(game)
    bm = locate.cached_map(game)
    names = bm.names if bm is not None else locate._build_names(raw16s, locate._scan_battle_text_pools(game))[0]
    acc: dict = {}
    for sid, raw16 in raw16s.items():
        mon_names = ((names.get(sid) or {}).get("names") or {}).get("us") or []
        try:
            scene = scene_monster_sounds(raw16, mon_names)
        except Exception:       # noqa: BLE001 -- one unparsable scene must not cost the lane
            continue
        for sfx, slots in scene.items():
            for slot, who in slots.items():
                acc.setdefault(sfx, {}).setdefault(slot, set()).update(who)
    return {sfx: {slot: sorted(who)[:_NAMES_KEEP] for slot, who in slots.items()} for sfx, slots in acc.items()}


def audio_facts(raw: bytes) -> list:
    """``[seconds, loops, channels]`` from one ``.akb.bytes`` asset -- its length, whether it carries
    a loop region, and mono / stereo. Pure; raises ``ValueError`` on a non-audio payload."""
    _ogg, info = akb_to_ogg(raw)
    return [round(float(info["seconds"]), 2), 1 if info["loop_end"] > info["loop_start"] else 0,
            int(info["channels"])]


def _audio_census(rows: dict, game=None) -> dict:
    """``{resource_id: [seconds, loops, channels]}`` for every listed sound -- read from each asset's
    own header, a bundle at a time (open, read, RELEASE). ~7 s for the whole game, and what lets the
    list say "0.4s" or "loops" without extracting anything."""
    from . import config
    from .extract import _raw_bytes, _unitypy
    sa = config.find_game_path(game) / "StreamingAssets"
    want: dict = {}
    for kind in KINDS:
        for r in rows.get(kind) or []:
            rid = r["resource_id"]
            want.setdefault(str(rid).split("/")[0].lower(), {})[container_key(rid)] = rid
    out: dict = {}
    marker = "assets/resources/sounds/"
    for prefix, keys in want.items():
        path = next((sa / f"p0data{i}.bin" for i in _BUNDLES.get(prefix, ()) if (sa / f"p0data{i}.bin").exists()),
                    None)
        if path is None:
            continue
        env = _unitypy().load(str(path))
        try:
            for k, obj in env.container.items():
                kl = k.lower()
                i = kl.find(marker)
                rid = keys.get(kl[i:]) if i >= 0 else None
                if rid is None:
                    continue
                try:
                    out[rid] = audio_facts(_raw_bytes(obj.read()))
                except Exception:   # noqa: BLE001 -- one odd asset costs only its own facts
                    continue
        finally:
            del env
    return out


def _build_fresh(game=None, progress=None) -> SoundMap:
    """Read everything from the install. ``progress(text)`` is told each stage as it starts. The
    listing lanes (the manifests, the field scripts) are load-bearing; the two describing lanes (battle
    scenes, audio headers) are best-effort -- a failure is recorded in ``gaps`` and the list still loads."""
    say = progress or (lambda _text: None)
    say("Reading the sound tables…")
    texts = sound.read_text_assets(list(sound.MANIFESTS.values()) + [EFFECT_MANIFEST], game=game)
    rows = {}
    for kind in KINDS:
        body = texts.get(sound.MANIFESTS[kind])
        rows[kind] = [{"id": r["id"], "resource_id": r["resource_id"]}
                      for r in (sound.parse_manifest(body) if body else [])]
    say("Reading every field script…")
    uses, contexts, n = _field_census(game)
    known = {kind: {r["id"] for r in rows[kind]} for kind in KINDS}
    uses = {kind: {sid: fids for sid, fids in sorted(uses[kind].items()) if sid in known[kind]}
            for kind in KINDS}                      # a script naming an id the manifest lacks places nothing
    contexts = {kind: {sid: c for sid, c in sorted((contexts.get(kind) or {}).items()) if sid in known[kind]}
                for kind in KINDS}
    gaps, monsters, audio = [], {}, {}
    say("Reading the battle scenes…")
    try:
        monsters = {sid: v for sid, v in sorted(_battle_census(game).items()) if sid in known["sfx"]}
    except Exception as e:          # noqa: BLE001
        gaps.append(f"battle scenes: {e}")
    say("Measuring every sound…")
    try:
        audio = _audio_census(rows, game)
    except Exception as e:          # noqa: BLE001
        gaps.append(f"sound lengths: {e}")
    return SoundMap(version=CACHE_VERSION, stamp=_stamp(game), rows=rows, uses=uses,
                    effects=parse_effect_manifest(texts.get(EFFECT_MANIFEST, "")), field_count=n,
                    contexts=contexts, monsters=monsters, audio=audio, gaps=gaps)


def _to_cache_dict(sm: SoundMap) -> dict:
    return {"version": sm.version, "stamp": sm.stamp, "rows": sm.rows,
            "uses": {k: {str(i): v for i, v in d.items()} for k, d in sm.uses.items()},
            "effects": sm.effects, "field_count": sm.field_count,
            "contexts": {k: {str(i): v for i, v in d.items()} for k, d in sm.contexts.items()},
            "monsters": {str(i): v for i, v in sm.monsters.items()},
            "audio": sm.audio, "gaps": list(sm.gaps)}


def _from_cache_dict(d) -> "SoundMap | None":
    """The inverse of :func:`_to_cache_dict`, or None for anything that is not a current-version map
    (a stale or foreign cache is IGNORED, never misread)."""
    if not isinstance(d, dict) or d.get("version") != CACHE_VERSION:
        return None
    try:
        return SoundMap(
            version=int(d["version"]), stamp=str(d["stamp"]),
            rows={k: [{"id": int(r["id"]), "resource_id": str(r["resource_id"])} for r in v]
                  for k, v in d["rows"].items()},
            uses={k: {int(i): [int(f) for f in fl] for i, fl in v.items()} for k, v in d["uses"].items()},
            effects={str(k): [int(e) for e in v] for k, v in d["effects"].items()},
            field_count=int(d["field_count"]),
            contexts={k: {int(i): {"ops": {str(o): int(n) for o, n in c["ops"].items()},
                                   "play": [[str(r), str(t), str(f), int(n)] for r, t, f, n in c["play"]],
                                   "pre": [[str(r), str(t), str(f), int(n)] for r, t, f, n in c["pre"]],
                                   "models": [[int(m), int(n)] for m, n in c["models"]],
                                   "pmodels": [[int(m), int(n)] for m, n in c["pmodels"]]}
                          for i, c in v.items()} for k, v in d["contexts"].items()},
            monsters={int(i): {str(s): [str(x) for x in who] for s, who in v.items()}
                      for i, v in d["monsters"].items()},
            audio={str(k): [float(v[0]), int(v[1]), int(v[2])] for k, v in d["audio"].items()},
            gaps=[str(g) for g in d["gaps"]])
    except (KeyError, TypeError, ValueError, AttributeError, IndexError):
        return None


def _cache_file_path() -> Path:
    return provision.cache_dir() / _CACHE_SUBDIR / _CACHE_FILE


_MEMO: dict = {}                             # stamp -> SoundMap, in-process only


def _read_disk(stamp: str) -> "SoundMap | None":
    cf = _cache_file_path()
    if not cf.is_file():
        return None
    try:
        sm = _from_cache_dict(json.loads(cf.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None
    return sm if sm is not None and sm.stamp == stamp else None


def cached_map(game=None) -> "SoundMap | None":
    """The already-built map if one is warm for THIS install (memo, then the disk cache) -- else None.
    Never reads a bundle and never writes."""
    try:
        stamp = _stamp(game)
    except Exception:       # noqa: BLE001 -- no install -> nothing can be warm for it
        return None
    if stamp in _MEMO:
        return _MEMO[stamp]
    sm = _read_disk(stamp)
    if sm is not None:
        _MEMO[stamp] = sm
    return sm


def build_map(game=None, *, force: bool = False, progress=None) -> SoundMap:
    """The sound map for the install: memo, then the stamp-checked disk cache, then a fresh read (~16 s:
    the manifests, every field script, the battle scenes, every sound's header). ``force`` rebuilds and
    overwrites both; ``progress(text)`` hears each stage of a fresh read. The disk write is best-effort
    -- a failed write must not lose the map that was just built."""
    stamp = _stamp(game)
    if not force:
        sm = _MEMO.get(stamp) or _read_disk(stamp)
        if sm is not None:
            _MEMO[stamp] = sm
            return sm
    sm = _build_fresh(game, progress)
    try:
        cf = _cache_file_path()
        cf.parent.mkdir(parents=True, exist_ok=True)
        fsutil.atomic_write_text(cf, json.dumps(_to_cache_dict(sm)))
    except OSError:
        pass
    _MEMO[sm.stamp] = sm
    return sm


# ----------------------------------------------------------------------------------------- names
NAMES_FILE = "sound_names.toml"


def baked_names_path() -> Path:
    return Path(__file__).resolve().parent / "data" / NAMES_FILE


def user_names_path() -> Path:
    """The per-user overlay the browser writes (survives a kit upgrade and every worktree)."""
    return provision._user_dir("config") / NAMES_FILE


def _norm_entry(v) -> "dict | None":
    if isinstance(v, str):
        return {"title": v.strip(), "tags": []}
    if isinstance(v, dict):
        tags = v.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        return {"title": str(v.get("title") or "").strip(),
                "tags": [str(t).strip().lower() for t in tags if str(t).strip()]}
    return None


def parse_names(text: str) -> dict:
    """A names file -> ``{kind: {stem: {"title", "tags"}}}``. Each value is a bare title string or an
    inline table ``{ title = "...", tags = ["door", "wood"] }``. Unknown kinds and malformed values are
    dropped; an unparseable file yields ``{}`` (a broken overlay must never blank the whole catalog)."""
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return {}
    out: dict = {}
    for kind in KINDS:
        tbl = doc.get(kind)
        if not isinstance(tbl, dict):
            continue
        for stem, v in tbl.items():
            ent = _norm_entry(v)
            if ent is not None and (ent["title"] or ent["tags"]):
                out.setdefault(kind, {})[str(stem).lower()] = ent
    return out


def _read_names(path) -> dict:
    try:
        return parse_names(Path(path).read_text(encoding="utf-8"))
    except OSError:
        return {}


def load_names(user_path=None, *, baked_path=None) -> dict:
    """The effective names: the kit's baked table with the user overlay laid over it PER SOUND (an
    overlay entry replaces that sound's baked entry whole). ``user_path=None`` -> the real per-user
    file; pass a path (tests, snaps) to pin it."""
    names = _read_names(baked_path or baked_names_path())
    over = _read_names(user_path if user_path is not None else user_names_path())
    for kind, tbl in over.items():
        names.setdefault(kind, {}).update(tbl)
    return names


def _toml_key(k: str) -> str:
    return k if k and all(c.isalnum() or c in "_-" for c in k) else json.dumps(k)


def serialize_names(names: dict, *, header: str = "") -> str:
    """``{kind: {stem: {"title", "tags"}}}`` -> TOML text (titles as bare strings, the table form only
    when a sound carries tags). JSON string escaping is a subset of TOML's basic-string escaping."""
    lines = [header.rstrip("\n")] if header else []
    for kind in KINDS:
        tbl = names.get(kind) or {}
        if not tbl:
            continue
        if lines:
            lines.append("")
        lines.append(f"[{kind}]")
        for stem in sorted(tbl):
            ent = tbl[stem]
            title = json.dumps(ent.get("title") or "", ensure_ascii=False)
            if ent.get("tags"):
                tags = ", ".join(json.dumps(t, ensure_ascii=False) for t in ent["tags"])
                lines.append(f"{_toml_key(stem)} = {{ title = {title}, tags = [{tags}] }}")
            else:
                lines.append(f"{_toml_key(stem)} = {title}")
    return "\n".join(lines) + "\n"


_USER_HEADER = ("# Sound names you set in the Workspace's Sounds tab. Laid over the kit's own table\n"
                "# (ff9mapkit/data/sound_names.toml) per sound; delete a line to fall back to it.")


def save_user_name(kind: str, stem: str, title: str, tags=(), *, path=None) -> Path:
    """Set (or, with an empty title AND no tags, clear) one sound's entry in the user overlay. Reads the
    overlay, changes the one entry, and rewrites the file atomically. Returns the overlay path."""
    if kind not in KINDS:
        raise ValueError(f"unknown sound kind {kind!r} (known: {', '.join(KINDS)})")
    p = Path(path) if path is not None else user_names_path()
    over = _read_names(p)
    ent = _norm_entry({"title": title, "tags": list(tags)})
    key = str(stem).lower()
    if ent["title"] or ent["tags"]:
        over.setdefault(kind, {})[key] = ent
    else:
        over.get(kind, {}).pop(key, None)
    p.parent.mkdir(parents=True, exist_ok=True)
    fsutil.atomic_write_text(p, serialize_names(over, header=_USER_HEADER))
    return p


def parse_tags(text: str) -> list:
    """``"door, Wood ,door"`` -> ``["door", "wood"]`` (comma-separated, lowercased, de-duplicated in order)."""
    out = []
    for t in str(text or "").split(","):
        t = t.strip().lower()
        if t and t not in out:
            out.append(t)
    return out


# ------------------------------------------------------------------------------------- the entries
@dataclass(frozen=True)
class Sound:
    """One listed sound. ``stem`` is the file name (``music008`` / ``se000032``) and the key names hang
    on; ``bank`` is its folder (``BGM_`` / ``SE00`` / ``song_`` / ``Movie_``)."""
    kind: str
    id: int
    resource_id: str
    stem: str
    bank: str
    title: str = ""
    tags: tuple = ()
    n_fields: int = 0
    n_effects: int = 0
    custom: bool = False
    # what the kit DERIVED about it (see Lore): never a name, and never counted as one
    category: str = ""
    describe: str = ""
    hint: str = ""
    auto_tags: tuple = ()
    places: tuple = ()
    seconds: float = 0.0
    loops: bool = False

    @property
    def described(self) -> bool:
        """Unnamed, but the kit can say what it is -- the rows a browser shows in italics."""
        return not self.title and bool(self.describe)

    @property
    def label(self) -> str:
        """The row text. A NAMED sound is its title and its id; an unnamed one its DESCRIPTION and its
        id when the kit has one, else its file stem, its id and a trailing hint. The id tells apart two
        sounds that share a description -- so the stem stays out of a described row: a list pane is
        narrow, and a row that elides to "Moogle talk · Ale…050017" has spent its width on a fragment
        (snap-caught). The stem is in the tooltip and the detail pane."""
        if self.title or self.describe:
            return f"{self.title or self.describe}  ·  id {self.id}"
        return f"{self.stem}  ·  id {self.id}" + (f"  ·  {self.hint}" if self.hint else "")

    @property
    def full_label(self) -> str:
        """Everything about the sound in one line (a row's tooltip)."""
        text = f"{self.title} — {self.resource_id}, id {self.id}" if self.title else \
            f"{self.resource_id}, id {self.id}"
        if self.category:
            text += f"  ·  {CATEGORY_LABEL.get(self.category, self.category)}"
        if self.describe:
            text += f"  ·  {self.describe}"
        if self.seconds:
            text += f"  ·  {format_seconds(self.seconds)}" + (" loop" if self.loops else "")
        return text + (f"  ·  tags: {', '.join(self.tags)}" if self.tags else "")

    @property
    def key(self) -> tuple:
        return (self.kind, self.id)


def _split(resource_id: str) -> tuple:
    parts = str(resource_id).split("/")
    return parts[-1], (parts[-2] if len(parts) >= 2 else "")


def sounds(sm: SoundMap, names=None, *, extra_rows=None, index=None) -> list:
    """Flatten the map into :class:`Sound` entries (kind order, then id), each carrying its
    :func:`lore`. ``names`` is :func:`load_names`'s dict; ``extra_rows`` = ``{kind: [rows]}`` of a mod
    folder's own minted ids (:func:`mod_custom_rows`), listed after the stock ones and flagged
    ``custom``; ``index`` is a :class:`LoreIndex` to share (one is built otherwise)."""
    names = names or {}
    index = index or LoreIndex(sm)
    out = []
    for kind in KINDS:
        nm = names.get(kind) or {}
        use = sm.uses.get(kind) or {}
        stock = [(r, False) for r in sm.rows.get(kind) or []]
        for r, custom in stock + [(r, True) for r in (extra_rows or {}).get(kind) or []]:
            stem, bank = _split(r["resource_id"])
            ent = nm.get(stem.lower()) or {}
            facts = sm.audio.get(r["resource_id"]) or (0.0, 0, 0)
            s = Sound(kind=kind, id=int(r["id"]), resource_id=r["resource_id"], stem=stem,
                      bank=bank, title=ent.get("title") or "", tags=tuple(ent.get("tags") or ()),
                      n_fields=len(use.get(int(r["id"]), ())),
                      n_effects=len(sm.effects.get(r["resource_id"], ())), custom=custom,
                      seconds=float(facts[0]), loops=bool(facts[1]),
                      places=() if custom else tuple(index.places(kind, int(r["id"]))))
            lr = lore(sm, s, index)
            out.append(replace(s, category=(tag_category(s.tags) if kind == "sfx" else None) or lr.category,
                               describe=lr.describe, hint=lr.hint, auto_tags=lr.tags))
    return out


# a TAG that names a category files the sound there -- the user's (or the kit table's) word outranks
# anything derived. First matching tag wins.
TAG_CATEGORY = {
    "menu": "menu", "system": "menu", "ui": "menu",
    "ambience": "ambience", "ambient": "ambience",
    "door": "door", "exit": "door",
    "pickup": "pickup", "chest": "pickup", "reward": "pickup",
    "character": "character", "party": "character", "movement": "character", "footsteps": "character",
    "npc": "npc", "creature": "npc", "moogle": "npc",
    "object": "object", "prop": "object",
    "event": "event", "cutscene": "event",
    "world": "world", "minigame": "minigame",
    "spell": "ability", "ability": "ability", "magic": "ability", "summon": "summon",
    "monster": "monster", "hit": "hit", "weapon": "hit", "enemy": "hit",
}


def tag_category(tags) -> "str | None":
    """The category the first category-naming tag files a sound under, or None."""
    for t in tags or ():
        if t in TAG_CATEGORY:
            return TAG_CATEGORY[t]
    return None


def category_counts(entries) -> list:
    """``[(key, label, count)]`` for the categories that have any sound, in :data:`CATEGORIES` order."""
    tally: dict = {}
    for s in entries:
        tally[s.category] = tally.get(s.category, 0) + 1
    return [(key, label, tally[key]) for key, label in CATEGORIES if tally.get(key)]


def banks(entries, kind=None, *, category=None) -> list:
    """The distinct banks among ``entries`` (optionally one kind and/or one category): music first,
    then the SE banks in number order, then streams and movie audio."""
    found = {s.bank for s in entries
             if (kind is None or s.kind == kind) and (category is None or s.category == category)}
    lead = {"BGM_": 0, "song_": 2, "Movie_": 3}
    return sorted(found, key=lambda b: (lead.get(b, 1), b))


def matches(s: Sound, query: str, *, place_text: str = "") -> bool:
    """Every whitespace-separated term of ``query`` must appear somewhere in what is known about the
    sound: its title, stem, id, your tags, its bank, the places it plays, and what the kit derived (its
    description, hint, category and auto-tags) -- case-insensitive. ``place_text`` adds caller text."""
    q = str(query or "").lower().split()
    if not q:
        return True
    hay = " ".join((s.title, s.stem, str(s.id), " ".join(s.tags), s.bank, " ".join(s.places), s.describe,
                    s.hint, CATEGORY_LABEL.get(s.category, ""), " ".join(s.auto_tags), place_text)).lower()
    return all(term in hay for term in q)


def filter_sounds(entries, query="", *, kind=None, bank=None, unnamed_only=False, place_text_fn=None,
                  category=None) -> list:
    out = []
    for s in entries:
        if kind is not None and s.kind != kind:
            continue
        if category is not None and s.category != category:
            continue
        if bank is not None and s.bank != bank:
            continue
        if unnamed_only and s.title:
            continue
        if not matches(s, query, place_text=place_text_fn(s) if place_text_fn else ""):
            continue
        out.append(s)
    return out


# -------------------------------------------------------------------------------------- where used
def zone_join() -> tuple:
    """``(field_arc, arcs)`` from the packaged region catalog: ``{field id: arc key}`` and
    ``{arc key: {"name", "zone"}}``. Install-free; an unreadable catalog yields two empty dicts."""
    try:
        from . import refarc
        arcset = refarc.load_region_catalog()
    except Exception:       # noqa: BLE001
        return {}, {}
    field_arc: dict = {}
    arcs: dict = {}
    for arc in arcset.arcs:
        arcs[arc.key] = {"name": arc.name, "zone": arc.zone}
        for fid in (arc.members or ()):
            field_arc.setdefault(int(fid), arc.key)
    return field_arc, arcs


_PLACE_SUFFIX = re.compile(r"\s*(?:\(ids \d+\+\)|\[[a-z0-9]{4}\])\s*$")
# the region catalog abbreviates the way the game's own location strings do; a where-used list and a
# search box want the word a person would type ("lindblum" must find what plays in Lindblum).
_PLACE_FULL = {
    "A. Castle": "Alexandria Castle", "L. Castle": "Lindblum", "I. Castle": "Ipsen's Castle",
    "Pand.": "Pandemonium", "Mdn. Sari": "Madain Sari", "Palace": "Desert Palace",
    "Mage Village": "Black Mage Village", "N. Gate": "North Gate", "S. Gate": "South Gate",
    "Gulug": "Mount Gulug", "Marsh": "Qu's Marsh", "Gizamaluke": "Gizamaluke's Grotto",
}


def place_label(arc_name: str) -> str:
    """A region-catalog arc name as a PLACE: ``"A. Castle (ids 1200+)"`` and ``"Dali [vgdl]"`` are the
    catalog telling one place's visits and sub-areas apart, which a where-used list does not need --
    both collapse to the place, spelled out (``"Alexandria Castle"``, ``"Dali"``)."""
    name = str(arc_name or "")
    while True:
        cut = _PLACE_SUFFIX.sub("", name)
        if cut == name:
            name = name.strip().replace("\u2019", "'")
            return _PLACE_FULL.get(name, name)
        name = cut


def places(sm: SoundMap, kind: str, sound_id: int, *, join=None) -> list:
    """Where field scripts name this sound, grouped by PLACE: ``[{"name", "fields"}]`` sorted by name,
    the fields no region claims (``name`` None) last. ``join`` = a cached :func:`zone_join` result."""
    field_arc, arcs = join if join is not None else zone_join()
    groups: dict = {}
    for fid in (sm.uses.get(kind) or {}).get(int(sound_id), ()):
        arc = arcs.get(field_arc.get(fid)) or {}
        groups.setdefault(place_label(arc.get("name")) or None, []).append(fid)
    out = [{"name": k, "fields": sorted(v)} for k, v in groups.items()]
    out.sort(key=lambda g: (g["name"] is None, g["name"] or ""))
    return out


def place_names(sm: SoundMap, kind: str, sound_id: int, *, join=None) -> list:
    """The names of the places a sound is used in, busiest first -- what a search for "lindblum"
    matches, and (its first entry) the hint an unnamed row wears."""
    groups = [g for g in places(sm, kind, sound_id, join=join) if g["name"]]
    groups.sort(key=lambda g: (-len(g["fields"]), g["name"]))
    return [g["name"] for g in groups]


# ------------------------------------------------------------------------- what a sound probably is
# A DESCRIPTION, derived from how the game uses the sound -- never a name. Four lanes, most specific
# first: the battle effect that loads it, the monster whose cry it is, what a field script was doing
# when it played it, and (when nothing names it at all) the bank it ships in.
CATEGORIES = (
    ("music", "Music"),
    ("menu", "Menu & system"),
    ("ambience", "Ambience & loops"),
    ("door", "Doors & exits"),
    ("pickup", "Pickups & rewards"),
    ("character", "Party & named characters"),
    ("npc", "NPCs & creatures"),
    ("object", "Objects & props"),
    ("event", "Scene events"),
    ("moveset", "Character sound sets"),
    ("areaset", "Area sets, unplaced"),
    ("world", "World map"),
    ("minigame", "Minigames"),
    ("ability", "Battle: spells & abilities"),
    ("summon", "Battle: summons"),
    ("monster", "Battle: monster voices"),
    ("hit", "Battle: hits & weapons"),
    ("battle", "Battle: unplaced"),
    ("stream", "Streams & vocals"),
    ("movie", "Movie audio"),
)
CATEGORY_LABEL = dict(CATEGORIES)

# what each bank IS when nothing names a sound in it: (fallback category, the bank in a few words).
# SE05-SE15 are not listed -- they are AREA sets, and which areas is read from the install
# (LoreIndex.bank_areas); SE50-SE56 are the battle-effect banks.
_BANK_CLASS = {
    "BGM_": ("music", "Music"), "song_": ("stream", "Streams"), "Movie_": ("movie", "Movie audio"),
    "SE00": ("menu", "System & menu"), "SE01": ("hit", "Battle hits & weapons"),
    "SE02": ("battle", "Battle abilities"), "SE03": ("monster", "Monster voices"),
    "SE04": ("moveset", "Character sound sets"), "SE20": ("world", "World map"),
    "SE21": ("minigame", "Minigames"),
}


def bank_class(bank: str) -> tuple:
    """``(fallback category, what the bank is)`` for a bank folder name."""
    if bank in _BANK_CLASS:
        return _BANK_CLASS[bank]
    if bank.startswith("SE5"):
        return "battle", "Battle effects"
    if bank.startswith("SE"):
        return "areaset", "Area set"
    return "event", bank or "Other"


_SUMMON_WORDS = frozenset(("Shiva", "Ifrit", "Ramuh", "Atomos", "Odin", "Leviathan", "Bahamut", "Ark",
                           "Carbuncle", "Fenrir", "Phoenix", "Madeen"))


def effect_title(raw: str) -> str:
    """Memoria's enum spelling as words: ``Fire__Single`` -> ``Fire (single)``, ``Thunder_Slash_2`` ->
    ``Thunder Slash 2``, ``Special_Gizamaluke_Death`` -> ``Gizamaluke Death``, ``Unused_442`` ->
    ``Unused effect 442``."""
    name = str(raw or "")
    if name.startswith("Unused_"):
        return f"Unused effect {name[7:]}"
    if name.startswith("Special_"):
        name = name[8:]
    base, sep, variant = name.partition("__")
    text = base.replace("_", " ").strip()
    return f"{text} ({variant.replace('_', ' ').strip().lower()})" if sep and variant else text


def effect_name(effect_id: int) -> str:
    """A battle special effect's readable name, or ``effect <id>`` for one the table does not know."""
    from ._effectnames import EFFECT_NAMES
    raw = EFFECT_NAMES.get(int(effect_id))
    return effect_title(raw) if raw else f"effect {int(effect_id)}"


def _is_summon(effect_id: int) -> bool:
    from ._effectnames import EFFECT_NAMES
    return (EFFECT_NAMES.get(int(effect_id)) or "").split("_")[0] in _SUMMON_WORDS


# model TOKEN (GEO_<group>_<form>_<TOKEN>) -> who that is. CONSERVATIVE on purpose: each entry was
# checked against where the model appears in the game (a Moogle in Mognet Central, Doctor Tot in Treno).
# An unlisted token is shown as its group and token -- never guessed.
MODEL_FRIENDLY = {
    "ZDN": "Zidane", "VIV": "Vivi", "STN": "Steiner", "GRN": "Garnet", "FRJ": "Freya", "EIK": "Eiko",
    "KUI": "Quina", "SLM": "Amarant", "MOG": "Moogle", "BMG": "Black Mage", "CHO": "Chocobo",
    "BLN": "Blank", "CNA": "Cinna", "MRC": "Marcus", "BAK": "Baku", "RBY": "Ruby", "CID": "Cid",
    "KJA": "Kuja", "BTX": "Beatrix", "TOT": "Doctor Tot", "GRL": "Garland", "ZON": "Zorn",
    "BW1": "Black Waltz 1", "BW2": "Black Waltz 2", "BW3": "Black Waltz 3", "GRG": "Gargant",
    "FLT": "Fratley", "TBX": "Treasure chest",
}
_GROUP_WORD = {"MAIN": "party member", "SUB": "character", "NPC": "NPC", "MON": "creature",
               "ACC": "prop", "WEP": "weapon"}
_MODELS: dict = {}


def model_label(model_id) -> tuple:
    """``(label, group)`` for a model id: its friendly name when the kit is sure of one, else its group
    word and token (``NPC CSO``). ``("model 123", "")`` for an id the catalog does not know."""
    if not _MODELS:
        try:
            from . import catalog
            _MODELS.update({m.id: m for m in catalog.all_models()})
        except Exception:       # noqa: BLE001 -- no catalog -> ids stay ids
            _MODELS[None] = None
    m = _MODELS.get(int(model_id))
    if m is None:
        return f"model {int(model_id)}", ""
    return MODEL_FRIENDLY.get(m.token) or f"{_GROUP_WORD.get(m.group, 'model')} {m.token}", m.group


@dataclass(frozen=True)
class Lore:
    """What the kit can say about a sound without anyone having listened to it.

    ``category`` is one of :data:`CATEGORIES`. ``describe`` is SPECIFIC ("Fire (single) · sound 2 of 3",
    "Whale Zombie death cry", "Moogle talk · Mdn. Sari +6") and may lead a row; ``hint`` is generic
    (the bank a sound nothing names ships in) and only ever trails one. ``notes`` are the sentences behind
    it, ``tags`` extra search words (``loop``, ``short``, ``battle`` ...)."""
    category: str
    describe: str = ""
    hint: str = ""
    notes: tuple = ()
    tags: tuple = ()


class LoreIndex:
    """The per-map lookups :func:`lore` shares across all 3,000 sounds: the region join, each battle
    effect's sound list (for "sound 2 of 3"), each sound's places, and each area bank's areas."""

    def __init__(self, sm: SoundMap, join=None):
        self.sm = sm
        self.join = join if join is not None else zone_join()
        self.effect_members: dict = {}
        for rid in sorted(sm.effects):
            for eid in sm.effects[rid]:
                self.effect_members.setdefault(eid, []).append(rid)
        self._places: dict = {}
        tally: dict = {}
        for r in sm.rows.get("sfx") or []:
            names = self.places("sfx", r["id"])
            if names:
                bank = _split(r["resource_id"])[1]
                tally.setdefault(bank, {})
                tally[bank][names[0]] = tally[bank].get(names[0], 0) + 1
        self.bank_areas = {bank: [name for name, _n in _top(t, 5)] for bank, t in tally.items()}

    def places(self, kind: str, sound_id: int) -> list:
        key = (kind, int(sound_id))
        if key not in self._places:
            self._places[key] = place_names(self.sm, kind, sound_id, join=self.join)
        return self._places[key]


def bank_label(bank: str, index: "LoreIndex | None" = None) -> str:
    """A bank as the filter shows it: ``SE00 · System & menu``, ``SE06 · Dali, Ice Cavern, Cargo Ship``."""
    cat, what = bank_class(bank)
    if cat == "areaset" and index is not None and index.bank_areas.get(bank):
        what = ", ".join(index.bank_areas[bank][:3])
    return f"{bank} · {what}"


def _more(names) -> str:
    names = list(names)
    return names[0] + (f" +{len(names) - 1}" if len(names) > 1 else "") if names else ""


_WHEN = {("main", "init"): "at field startup", ("main", "reinit"): "after a battle",
         ("main", "loop"): "in the field's own loop", ("main", "routine"): "in a field routine",
         ("region", "touch"): "when you walk into a trigger", ("region", "talk"): "when you press on a trigger",
         ("object", "talk"): "when you talk to it", ("object", "touch"): "when you touch it",
         ("object", "loop"): "in its every-frame loop", ("object", "init"): "as it appears",
         ("player", "init"): "as the player appears", ("player", "loop"): "in the player's loop"}
_ALSO = {"warp": "leaves the field", "item": "gives an item", "battle": "starts a battle", "text": "shows text"}


def _when(role: str, tag: str, flags: str) -> str:
    base = _WHEN.get((role, tag)) or {"object": "in one of its routines", "player": "in a player sequence",
                                      "region": "in a trigger's routine", "logic": "in a helper script",
                                      "main": "in a field routine"}.get(role, "in a script")
    also = [_ALSO[f] for f in flags.split("+") if f in _ALSO and f != "text"]
    return base + (f" (that routine also {' and '.join(also)})" if also else "")


def _field_lore(s, c: dict, places: list, loops: bool) -> tuple:
    """``(category, describe, notes)`` from a sound's field-script usage summary."""
    ops, plays, pres = c.get("ops") or {}, c.get("play") or [], c.get("pre") or []

    def labels(key) -> list:
        out = []
        for mid, _n in c.get(key) or []:
            pair = model_label(mid)
            if pair not in out:
                out.append(pair)
        return out

    who, pre_who = labels("models"), labels("pmodels")
    where = _more(places)
    tail = f" · {where}" if where else ""
    n_play = sum(n for _r, _t, _f, n in plays)
    n_pre = ops.get("preload", 0)
    # A SOUND SET: preloaded by characters far more often than any script plays it. The engine plays
    # these itself (a footstep fires from the walk animation), so the preloaders are who it belongs to.
    if pre_who and n_pre >= 5 * max(n_play, 1):
        names = [label for label, _g in pre_who]
        note = (f"Preloaded {n_pre} times by {', '.join(names[:5])}{' …' if len(names) > 5 else ''}; "
                + (f"scripts play it only {n_play} times" if n_play else "no script plays it")
                + " -- the engine does (footsteps and other animation sounds work this way).")
        return "moveset", f"Sound set of {_more(names)}", (note,)
    if not plays:
        if pres:
            return ("moveset" if s.bank == "SE04" else "event", f"Preloaded only{tail}",
                    ("Scripts preload it and none plays it -- the engine does.",))
        return "event", f"Never started by a script{tail}", ("Scripts only stop or fade it.",)
    total = float(n_play) or 1.0

    def share(pred) -> float:
        return sum(n for r, t, f, n in plays if pred(r, t, f.split("+"))) / total

    sustain, play = ops.get("sustain", 0), ops.get("play", 0)
    top_role = plays[0][0]
    lead = who[0] if who else None
    # an entry that wears a model -- an NPC, a prop, or the PLAYER's own (a sound Zidane's script plays
    # is Zidane's, exactly as one Blank's script plays is Blank's)
    by_object = share(lambda r, t, f: r in ("object", "player"))
    with_item = share(lambda r, t, f: "item" in f)
    # WHO plays it outranks WHAT ELSE the function does: a Moogle's talk handler hands out items too,
    # and its greeting is still the Moogle's. Only a PROP that gives something is a pickup.
    if lead and by_object >= 0.4 and not (lead[1] == "ACC" and with_item >= 0.4):
        label, group = lead
        cat = "character" if group in ("MAIN", "SUB") else "object" if group == "ACC" else "npc"
        obj_tag = next((t for r, t, _f, _n2 in plays if r == "object"), "")
        what = _more([lab for lab, _g in who]) + {"talk": " talk", "touch": " touch"}.get(obj_tag, "")
    elif with_item >= 0.4:
        cat, what = "pickup", "Pickup" + (f" · {lead[0]}" if lead and by_object >= 0.3 else "")
    elif share(lambda r, t, f: r == "region" and "warp" in f) >= 0.3 or \
            (share(lambda r, t, f: "warp" in f) >= 0.6 and top_role != "object"):
        cat, what = "door", "Door or exit"
    elif (sustain and sustain >= play) or (loops and share(lambda r, t, f: r in ("main", "logic")) >= 0.5):
        cat, what = "ambience", "Ambience loop"
    elif share(lambda r, t, f: r == "player") >= 0.4:
        cat, what = "character", "Player action"
    else:
        cat, what = "event", "Scene event"
    notes = ["Played " + "; ".join(f"{_when(r, t, f)} ×{n}" for r, t, f, n in plays[:3]) + "."]
    control = [f"{ops[k]} {word}" for k, word in (("sustain", "held starts"), ("shape", "fades or pans"),
                                                  ("stop", "stops")) if ops.get(k)]
    if control:
        notes.append("Scripts also control it: " + ", ".join(control) + ".")
    if who and cat not in ("character", "npc", "object"):
        notes.append("Played by: " + ", ".join(label for label, _g in who[:4]) + ".")
    return cat, what + tail, tuple(notes)


_PLUS_N = re.compile(r"\s\+\d+")


def suggest_title(s) -> str:
    """A description reshaped into a starting NAME: ``Moogle talk · Lindblum +29`` -> ``Moogle talk,
    Lindblum``. For the Name box's "use the description" -- the user then says what they actually hear."""
    return _PLUS_N.sub("", str(getattr(s, "describe", "") or "")).replace("  ·  ", ", ").replace(" · ", ", ")


def lore(sm: SoundMap, s, index: "LoreIndex | None" = None) -> Lore:
    """Describe one sound from how the game uses it (see :class:`Lore`). ``s`` needs ``kind`` / ``id`` /
    ``resource_id`` / ``bank`` / ``custom``; ``index`` is a shared :class:`LoreIndex` (built if absent)."""
    index = index or LoreIndex(sm)
    facts = sm.audio.get(s.resource_id)
    loops = bool(facts and facts[1])
    tags = []
    if facts:
        secs = facts[0]
        tags.append("blip" if secs < 0.4 else "short" if secs < 1.5 else "long" if secs >= 8 else "medium")
        if loops:
            tags.append("loop")
    places = index.places(s.kind, s.id)
    if s.custom:
        return Lore("music" if s.kind == "music" else "event", "", "", (), tuple(tags))
    if s.kind == "music":
        if facts and not loops:
            tags.append("jingle")
        return Lore("music", "", "", (), tuple(tags))
    if s.kind == "movie":
        return Lore("movie", "", "movie audio", ("Movie audio plays with its video, not from a script.",),
                    tuple(tags))
    effects = sm.effects.get(s.resource_id) or []
    if effects:
        titles = [effect_name(e) for e in effects]
        members = index.effect_members.get(effects[0]) or []
        ordinal = f" · sound {members.index(s.resource_id) + 1} of {len(members)}" \
            if len(members) > 1 and s.resource_id in members else ""
        summon = any(_is_summon(e) for e in effects)
        shown = ", ".join(f"{t} (effect {e})" for e, t in list(zip(effects, titles))[:8])
        note = f"Loaded by battle effect{'s' if len(effects) != 1 else ''}: {shown}" \
               + (" …" if len(effects) > 8 else "") + "."
        cat = "stream" if s.kind == "stream" else "summon" if summon else "ability"
        return Lore(cat, _more(titles) + ordinal, "", (note,), tuple(tags + ["battle"] + (["summon"] if summon else [])))
    mon = sm.monsters.get(s.id) if s.kind == "sfx" else None
    if mon:
        die, start = mon.get("die") or [], mon.get("start") or []
        notes = []
        if die:
            notes.append("Death cry of: " + ", ".join(die) + ".")
        if start:
            notes.append("Cry as the battle opens: " + ", ".join(start) + ".")
        describe = f"{_more(die)} death cry" if die else f"{_more(start)} battle cry"
        return Lore("monster", describe, "", tuple(notes), tuple(tags + ["battle", "monster"]))
    c = (sm.contexts.get(s.kind) or {}).get(s.id)
    if c:
        cat, describe, notes = _field_lore(s, c, places, loops)
        if s.kind == "stream":
            cat = "stream"
        elif s.bank == "SE00" and cat in ("event", "character"):
            cat = "menu"                            # the system bank: a cue a scene borrows is still a cue
        return Lore(cat, describe, "", notes, tuple(tags))
    cat, what = bank_class(s.bank)
    if s.kind == "stream":
        return Lore("stream", "", "stream", ("No field script or battle effect names it.",), tuple(tags))
    if cat == "areaset":
        areas = index.bank_areas.get(s.bank) or []
        return Lore(cat, "", "area set: " + ", ".join(areas[:3]) if areas else "area set",
                    (("No script names it. Its bank holds the sounds of " + ", ".join(areas) + ".") if areas
                     else "No script names it.",), tuple(tags))
    return Lore(cat, "", what.lower(),
                ("No field script or battle effect names it -- the engine plays this bank itself.",),
                tuple(tags))


# ----------------------------------------------------------------------------- the audio: AKB + Ogg
AKB2_HEADER = 304
AKB1_HEADER = 204
_AKB2_AUDIO = 4 * 31 + 4 * 24 + 4           # 31 u32, four 6-u32 sections, one u32 -> the audio block


def parse_akb(raw: bytes) -> dict:
    """Split an ``.akb.bytes`` asset: ``{"ogg_offset", "rate", "loop_start", "loop_end", "loop_start2",
    "loop_end2"}`` (loop points in SAMPLES; 0/0 = no loop). Raises ``ValueError`` when the payload is
    not an AKB-wrapped Ogg -- the caller must not hand a player something that is not audio."""
    raw = bytes(raw)
    sig = raw[:4]
    if sig == b"AKB2" and len(raw) >= AKB2_HEADER:
        off = AKB2_HEADER
        rate, = struct.unpack_from("<H", raw, _AKB2_AUDIO + 6)
        _content, _count, ls, le, _c36, ls2, le2 = struct.unpack_from("<7I", raw, _AKB2_AUDIO + 8)
    elif sig == b"AKB " and len(raw) >= AKB1_HEADER:
        off = AKB1_HEADER
        rate, = struct.unpack_from("<H", raw, 14)
        ls, le = struct.unpack_from("<2I", raw, 20)
        ls2 = le2 = 0
    else:
        raise ValueError(f"not an AKB sound asset (magic {sig!r})")
    if raw[off:off + 4] != b"OggS":
        found = raw.find(b"OggS")
        if found < 0:
            raise ValueError("AKB asset carries no Ogg stream")
        off = found
    return {"ogg_offset": off, "rate": int(rate), "loop_start": int(ls), "loop_end": int(le),
            "loop_start2": int(ls2), "loop_end2": int(le2)}


def ogg_info(ogg: bytes) -> dict:
    """Best-effort facts from a Vorbis-in-Ogg stream: ``{"rate", "channels", "samples", "seconds",
    "loop_start", "loop_end"}`` (missing facts are 0). Reads the identification header, the LoopStart /
    LoopEnd comments, and the last page's granule position. Never raises -- a custom file with an odd
    layout still plays; it just reports less."""
    ogg = bytes(ogg)
    info = {"rate": 0, "channels": 0, "samples": 0, "seconds": 0.0, "loop_start": 0, "loop_end": 0}
    i = ogg.find(b"\x01vorbis")
    if 0 <= i and i + 16 <= len(ogg):
        info["channels"] = ogg[i + 11]
        info["rate"], = struct.unpack_from("<I", ogg, i + 12)
    c = ogg.find(b"\x03vorbis", 0, 1 << 18)
    if c >= 0:
        try:
            p = c + 7
            vlen, = struct.unpack_from("<I", ogg, p)
            p += 4 + vlen
            count, = struct.unpack_from("<I", ogg, p)
            p += 4
            for _ in range(min(count, 256)):
                n, = struct.unpack_from("<I", ogg, p)
                p += 4
                k, _eq, v = ogg[p:p + n].decode("utf-8", "replace").partition("=")
                p += n
                k = k.strip().lower()
                if k in ("loopstart", "loopend") and v.strip().isdigit():
                    info["loop_start" if k == "loopstart" else "loop_end"] = int(v.strip())
        except (struct.error, IndexError):
            pass
    last = ogg.rfind(b"OggS")
    if last >= 0 and last + 14 <= len(ogg):
        gran, = struct.unpack_from("<q", ogg, last + 6)
        if gran > 0:
            info["samples"] = int(gran)
    if info["rate"] and info["samples"]:
        info["seconds"] = info["samples"] / float(info["rate"])
    return info


def akb_to_ogg(raw: bytes) -> tuple:
    """``(ogg bytes, info)`` for one asset: the Ogg payload plus :func:`ogg_info`'s facts, with the AKB
    header's loop points and rate preferred over the Ogg's own (the header is what the engine reads)."""
    hdr = parse_akb(raw)
    ogg = bytes(raw)[hdr["ogg_offset"]:]
    info = ogg_info(ogg)
    for k in ("loop_start", "loop_end"):
        if hdr[k]:
            info[k] = hdr[k]
    info["loop_start2"], info["loop_end2"] = hdr["loop_start2"], hdr["loop_end2"]
    if hdr["rate"]:
        info["rate"] = hdr["rate"]
        if info["samples"]:
            info["seconds"] = info["samples"] / float(hdr["rate"])
    return ogg, info


# which p0data bundles hold a ResourceID, tried in order (the second of each pair is the same data
# split differently across disc sets -- measured: p0data62 is a superset of p0data611).
_BUNDLES = {"sounds01": (61, 601), "sounds02": (62, 611), "sounds03": (63, 621)}


def bundle_candidates(resource_id: str) -> tuple:
    return _BUNDLES.get(str(resource_id).split("/")[0].lower(), ())


def container_key(resource_id: str) -> str:
    return f"assets/resources/sounds/{str(resource_id).lower()}.akb.bytes"


def read_akb(resource_id: str, game=None) -> bytes:
    """The raw ``.akb.bytes`` for a ResourceID, read from its bundle. Opens the bundle, reads the one
    asset and RELEASES the handle (it is ~400 MB while it lives). Raises ``FileNotFoundError`` when no
    bundle carries it (a minted custom id has no bundled audio -- play its loose Ogg instead)."""
    from . import config
    from .extract import _raw_bytes, _unitypy
    sa = config.find_game_path(game) / "StreamingAssets"
    want = container_key(resource_id)
    for idx in bundle_candidates(resource_id):
        p = sa / f"p0data{idx}.bin"
        if not p.exists():
            continue
        env = _unitypy().load(str(p))
        try:
            for k, obj in env.container.items():
                if k.lower().endswith(want):
                    data = _raw_bytes(obj.read())
                    if data:
                        return bytes(data)
        finally:
            del env
    raise FileNotFoundError(f"no bundled audio for {resource_id!r} (looked in "
                            f"{', '.join(f'p0data{i}' for i in bundle_candidates(resource_id)) or 'no bundle'})")


def ogg_cache_dir() -> Path:
    return provision.cache_dir() / _OGG_SUBDIR


def _cache_paths(resource_id: str) -> tuple:
    base = ogg_cache_dir() / (str(resource_id).replace("/", "_").replace("\\", "_") + ".ogg")
    return base, base.with_suffix(".json")


def _prune_ogg_cache(limit: int = OGG_CACHE_LIMIT) -> None:
    try:
        files = [(p.stat().st_mtime, p.stat().st_size, p) for p in ogg_cache_dir().glob("*.ogg")]
    except OSError:
        return
    total = sum(sz for _m, sz, _p in files)
    for _m, sz, p in sorted(files):
        if total <= limit:
            break
        try:
            p.unlink()
            p.with_suffix(".json").unlink(missing_ok=True)
            total -= sz
        except OSError:
            continue


def extract_ogg(resource_id: str, game=None) -> tuple:
    """``(path, info)`` -- the sound as a playable Ogg file in the kit cache, extracted from the install
    on first use and served from disk after. ``info`` is :func:`akb_to_ogg`'s facts."""
    ogg_p, meta_p = _cache_paths(resource_id)
    if ogg_p.is_file() and meta_p.is_file():
        try:
            return ogg_p, json.loads(meta_p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    ogg, info = akb_to_ogg(read_akb(resource_id, game))
    ogg_p.parent.mkdir(parents=True, exist_ok=True)
    fsutil.atomic_write_bytes(ogg_p, ogg)
    fsutil.atomic_write_text(meta_p, json.dumps(info))
    _prune_ogg_cache()
    return ogg_p, info


def override_path(mod_folder, resource_id: str) -> "Path | None":
    """The mod folder's loose-Ogg override of this ResourceID, or None when it ships none."""
    if not mod_folder:
        return None
    p = Path(mod_folder) / sound.override_rel_path(resource_id)
    return p if p.is_file() else None


def playable(resource_id: str, *, mod_folder=None, game=None) -> tuple:
    """``(path, info, source)`` for a sound as the GAME would play it from ``mod_folder``: the folder's
    loose override when it has one (``source="override"``), else the install's own audio (``"stock"``)."""
    over = override_path(mod_folder, resource_id)
    if over is not None:
        try:
            info = ogg_info(over.read_bytes())
        except OSError:
            info = ogg_info(b"")
        return over, info, "override"
    path, info = extract_ogg(resource_id, game)
    return path, info, "stock"


def export_ogg(resource_id: str, out, *, mod_folder=None, game=None) -> Path:
    """Write the sound to ``out`` as a plain ``.ogg`` (any audio editor opens it). Returns the path."""
    path, _info, _src = playable(resource_id, mod_folder=mod_folder, game=game)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, out)
    return out


def mod_custom_rows(mod_folder, sm: SoundMap) -> dict:
    """``{kind: [rows]}`` of the ids a mod folder's override manifests ADD over the install's (the
    tracks ``audio-import --new-song`` / ``[music] file`` minted there). Empty without such a manifest."""
    out: dict = {}
    if not mod_folder:
        return out
    for kind in ("music", "sfx"):
        mp = sound.manifest_override_path(mod_folder, kind)
        if not mp.is_file():
            continue
        try:
            rows = sound.parse_manifest(mp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        stock = {r["id"] for r in sm.rows.get(kind) or []}
        extra = [{"id": r["id"], "resource_id": r["resource_id"]} for r in rows if r["id"] not in stock]
        if extra:
            out[kind] = extra
    return out


def format_seconds(seconds: float) -> str:
    """``84.7 -> "1:24"``; under ten seconds keeps a decimal (``0.42 -> "0.4s"``) so a short effect
    does not read as zero length."""
    s = float(seconds or 0.0)
    if s < 10:
        return f"{s:.1f}s"
    return f"{int(s // 60)}:{int(s % 60):02d}"
