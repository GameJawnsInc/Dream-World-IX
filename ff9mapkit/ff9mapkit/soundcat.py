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

Provenance: nothing here is baked from the game. Manifests, the census and every extracted Ogg are
read LIVE from the user's own install and cached under :func:`provision.cache_dir` (gitignored); the
only shipped data is the names file, which holds titles and no game bytes.

Cost model (measured): one bundle open is ~0.1 s and holds ~400 MB while the handle lives, so
:func:`read_akb` opens, reads and RELEASES -- it never joins ``extract``'s long-lived bundle memo.
The field census is ~5 s cold and one JSON read warm.
"""
from __future__ import annotations

import json
import re
import shutil
import struct
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import fsutil, provision, sound

KINDS = ("music", "sfx", "stream", "movie")
KIND_LABEL = {"music": "Music", "sfx": "Sound effects", "stream": "Streams", "movie": "Movie audio"}
KIND_NOUN = {"music": "music track", "sfx": "sound effect", "stream": "stream", "movie": "movie audio track"}

CACHE_VERSION = 1
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


def _field_census(game=None) -> tuple:
    """``(uses, field_count)`` -- one pass over every real field's ``.eb`` (the ``battle.locate`` census
    shape: one bundle load, then an instruction walk per field)."""
    from . import extract as _extract
    from ._fieldtable import FIELD_BY_ID
    bundle = _extract.EventBundle(game=game)
    acc: dict = {k: {} for k in KINDS}
    n = 0
    for fid in sorted(FIELD_BY_ID):
        eb_bytes = bundle.eb_for_id(fid)
        if eb_bytes is None:
            continue
        n += 1
        for kind, sid in scan_field_sounds(eb_bytes):
            acc[kind].setdefault(sid, []).append(fid)
    return acc, n


def _build_fresh(game=None) -> SoundMap:
    texts = sound.read_text_assets(list(sound.MANIFESTS.values()) + [EFFECT_MANIFEST], game=game)
    rows = {}
    for kind in KINDS:
        body = texts.get(sound.MANIFESTS[kind])
        rows[kind] = [{"id": r["id"], "resource_id": r["resource_id"]}
                      for r in (sound.parse_manifest(body) if body else [])]
    uses, n = _field_census(game)
    known = {kind: {r["id"] for r in rows[kind]} for kind in KINDS}
    uses = {kind: {sid: fids for sid, fids in sorted(uses[kind].items()) if sid in known[kind]}
            for kind in KINDS}                      # a script naming an id the manifest lacks places nothing
    return SoundMap(version=CACHE_VERSION, stamp=_stamp(game), rows=rows, uses=uses,
                    effects=parse_effect_manifest(texts.get(EFFECT_MANIFEST, "")), field_count=n)


def _to_cache_dict(sm: SoundMap) -> dict:
    return {"version": sm.version, "stamp": sm.stamp, "rows": sm.rows,
            "uses": {k: {str(i): v for i, v in d.items()} for k, d in sm.uses.items()},
            "effects": sm.effects, "field_count": sm.field_count}


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
            field_count=int(d["field_count"]))
    except (KeyError, TypeError, ValueError, AttributeError):
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


def build_map(game=None, *, force: bool = False) -> SoundMap:
    """The sound map for the install: memo, then the stamp-checked disk cache, then a fresh read (the
    manifests + a ~5 s census of every field script). ``force`` rebuilds and overwrites both. The disk
    write is best-effort -- a failed write must not lose the map that was just built."""
    stamp = _stamp(game)
    if not force:
        sm = _MEMO.get(stamp) or _read_disk(stamp)
        if sm is not None:
            _MEMO[stamp] = sm
            return sm
    sm = _build_fresh(game)
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

    @property
    def label(self) -> str:
        """The row text: the title (or, unnamed, the file stem) and the id it answers to. Short on
        purpose -- a list pane is narrow, and the id is the part a row must never lose to an ellipsis."""
        return f"{self.title or self.stem}  ·  id {self.id}"

    @property
    def full_label(self) -> str:
        """Everything about the sound in one line (a row's tooltip)."""
        text = f"{self.title} — {self.resource_id}, id {self.id}" if self.title else \
            f"{self.resource_id}, id {self.id}"
        return text + (f"  ·  tags: {', '.join(self.tags)}" if self.tags else "")

    @property
    def key(self) -> tuple:
        return (self.kind, self.id)


def _split(resource_id: str) -> tuple:
    parts = str(resource_id).split("/")
    return parts[-1], (parts[-2] if len(parts) >= 2 else "")


def sounds(sm: SoundMap, names=None, *, extra_rows=None) -> list:
    """Flatten the map into :class:`Sound` entries (kind order, then id). ``names`` is
    :func:`load_names`'s dict; ``extra_rows`` = ``{kind: [rows]}`` of a mod folder's own minted ids
    (:func:`mod_custom_rows`), listed after the stock ones and flagged ``custom``."""
    names = names or {}
    out = []
    for kind in KINDS:
        nm = names.get(kind) or {}
        use = sm.uses.get(kind) or {}
        stock = [(r, False) for r in sm.rows.get(kind) or []]
        for r, custom in stock + [(r, True) for r in (extra_rows or {}).get(kind) or []]:
            stem, bank = _split(r["resource_id"])
            ent = nm.get(stem.lower()) or {}
            out.append(Sound(kind=kind, id=int(r["id"]), resource_id=r["resource_id"], stem=stem,
                             bank=bank, title=ent.get("title") or "", tags=tuple(ent.get("tags") or ()),
                             n_fields=len(use.get(int(r["id"]), ())),
                             n_effects=len(sm.effects.get(r["resource_id"], ())), custom=custom))
    return out


def banks(entries, kind=None) -> list:
    """The distinct banks among ``entries`` (optionally one kind), in first-seen order."""
    out = []
    for s in entries:
        if (kind is None or s.kind == kind) and s.bank not in out:
            out.append(s.bank)
    return out


def matches(s: Sound, query: str, *, place_text: str = "") -> bool:
    """Every whitespace-separated term of ``query`` must appear in the sound's title, stem, id, tags,
    bank, or ``place_text`` (the caller's where-used names) -- case-insensitive."""
    q = str(query or "").lower().split()
    if not q:
        return True
    hay = " ".join((s.title, s.stem, str(s.id), " ".join(s.tags), s.bank, place_text)).lower()
    return all(term in hay for term in q)


def filter_sounds(entries, query="", *, kind=None, bank=None, unnamed_only=False, place_text_fn=None) -> list:
    out = []
    for s in entries:
        if kind is not None and s.kind != kind:
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


def place_label(arc_name: str) -> str:
    """A region-catalog arc name as a PLACE: ``"A. Castle (ids 1200+)"`` and ``"Dali [vgdl]"`` are the
    catalog telling one place's visits and sub-areas apart, which a where-used list does not need --
    both collapse to the place (``"A. Castle"``, ``"Dali"``)."""
    name = str(arc_name or "")
    while True:
        cut = _PLACE_SUFFIX.sub("", name)
        if cut == name:
            return name.strip()
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
