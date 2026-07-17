"""Custom MUSIC / SFX authoring for FF9 (Steam/Memoria) — DLL-free, in-game proven 2026-07-05.

FF9 PC plays AKB2-wrapped Ogg Vorbis. A loose ``.ogg`` dropped at
``<mod>/StreamingAssets/Assets/Resources/Sounds/<ResourceID>.ogg`` OVERRIDES the bundled track: the engine
(``SoundLoaderResources.TryOpeningOgg``) finds it, wraps it in a 304-byte AKB2 header at RUNTIME, and plays it.
Music AUTO-LOOPS (engine sets LoopEnd = TotalSamples-1 when untagged); custom loop points ride as Vorbis
``LoopStart=``/``LoopEnd=`` comments (sample counts). The song-id -> ResourceID map lives in
``<game>/x64/FF9_Data/resources.assets`` as the ``MusicMetaData.txt`` / ``SoundEffectMetaData.txt`` TextAssets.

⚠ ``Memoria.ini [Audio] PriorityToOGG`` MUST be 1 — the base ``.akb`` always exists in the bundle, so the
default (0) loads it FIRST and the loose OGG is ignored. This module sets it (backed up) on deploy.

Provenance-clean: reads the user's own install; writes only to the caller's mod folder (gitignored assets).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import config, fsutil

# manifest TextAsset name per audio kind (in resources.assets); the ResourceID carries its own subfolder
# (music -> "Sounds01/BGM_/music###", sfx -> "Sounds02/SE##/name").
MANIFESTS = {"music": "MusicMetaData.txt", "sfx": "SoundEffectMetaData.txt"}


def override_rel_path(resource_id: str) -> str:
    """The mod-folder-relative path the engine probes for a loose override of this ResourceID
    (``SearchAssetOnDisc("Sounds/"+ResourceID+".ogg")`` under ``Assets/Resources/``)."""
    return f"StreamingAssets/Assets/Resources/Sounds/{resource_id}.ogg"


def resources_assets_path(game=None) -> Path:
    """``<game>/x64/FF9_Data/resources.assets`` — where the sound MetaData manifests live (NOT p0data)."""
    g = config.find_game_path(game)
    for sub in ("x64/FF9_Data", "FF9_Data", "x86/FF9_Data"):
        p = g / sub / "resources.assets"
        if p.exists():
            return p
    raise FileNotFoundError(f"resources.assets not found under {g} (looked in x64/FF9_Data, FF9_Data, x86/FF9_Data)")


def parse_manifest(json_text: str) -> list:
    """Parse a ``*MetaData.txt`` JSON body -> ``[{"id": int, "resource_id": str, "type": str}]`` sorted by id.
    Pure (no install) so it's unit-testable; the JSON shape is ``{"data":[{name, soundIndex, type}, ...]}``."""
    rows = json.loads(json_text).get("data", [])
    out = []
    for e in rows:
        try:
            out.append({"id": int(e["soundIndex"]), "resource_id": str(e["name"]), "type": str(e.get("type", ""))})
        except (KeyError, ValueError, TypeError):
            continue
    out.sort(key=lambda r: r["id"])
    return out


def _cache_path(ra: Path, manifest: str) -> Path:
    stamp = f"{ra.stat().st_size}-{int(ra.stat().st_mtime)}"
    return Path(tempfile.gettempdir()) / "ff9mapkit-sndcache" / f"{manifest}.{stamp}.json"


def read_manifest(kind: str = "music", game=None, use_cache: bool = True) -> list:
    """The id -> ResourceID table for ``kind`` ("music"|"sfx"), extracted once from resources.assets and
    cached (the 590 MB read is slow). Returns :func:`parse_manifest`'s list."""
    if kind not in MANIFESTS:
        raise ValueError(f"unknown audio kind {kind!r} (known: {', '.join(MANIFESTS)})")
    ra = resources_assets_path(game)
    manifest = MANIFESTS[kind]
    cache = _cache_path(ra, manifest)
    if use_cache and cache.exists():
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:       # noqa: BLE001 -- a corrupt cache just re-extracts
            pass
    from .models.extract import _unitypy
    env = _unitypy().load(str(ra))
    table = None
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        try:
            ta = o.read()
        except Exception:       # noqa: BLE001
            continue
        if getattr(ta, "m_Name", None) == manifest:
            txt = ta.m_Script if isinstance(ta.m_Script, str) else bytes(ta.m_Script).decode("utf-8", "replace")
            table = parse_manifest(txt)
            break
    if table is None:
        raise FileNotFoundError(f"{manifest} not found in {ra}")
    if use_cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(table), encoding="utf-8")
    return table


def resolve_resource_id(song_id: int, kind: str = "music", game=None) -> str:
    """id -> ResourceID (e.g. music id 0 -> "Sounds01/BGM_/music006"). Raises if the id isn't in the manifest."""
    for row in read_manifest(kind, game=game):
        if row["id"] == int(song_id):
            return row["resource_id"]
    raise KeyError(f"{kind} id {song_id} not found (see `ff9mapkit {kind}-list`)")


# --------------------------------------------------------------------------- ffmpeg (Ogg Vorbis encode)
def find_ffmpeg() -> str:
    """Path to an ffmpeg executable, or raise. Audio needs stock libvorbis (unlike the FMV libtheora
    landmine), so any recent ffmpeg works."""
    exe = shutil.which("ffmpeg") or (os.environ.get("FFMPEG") if shutil.which(os.environ.get("FFMPEG", "")) else None)
    if exe:
        return exe
    raise RuntimeError(
        "ffmpeg not found on PATH — install ffmpeg (any recent build with libvorbis) to encode audio, "
        "or set $FFMPEG to its path.")


def encode_ogg(in_path, out_path, *, loop_start=None, loop_end=None, quality: int = 6) -> Path:
    """Transcode any audio file to Ogg Vorbis at ``out_path``; embed ``LoopStart=``/``LoopEnd=`` Vorbis
    comments (sample counts) when given. Raises on a bad encode. ``quality`` = libvorbis -qscale:a (0-10)."""
    ff = find_ffmpeg()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    args = [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(in_path),
            "-vn", "-c:a", "libvorbis", "-qscale:a", str(int(quality))]
    if loop_start is not None:
        args += ["-metadata", f"LoopStart={int(loop_start)}"]
    if loop_end is not None:
        args += ["-metadata", f"LoopEnd={int(loop_end)}"]
    args += [str(out_path)]
    try:
        subprocess.run(args, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg encode failed:\n{e.stderr or e.stdout}") from e
    if not out_path.exists() or out_path.open("rb").read(4) != b"OggS":
        raise RuntimeError(f"ffmpeg did not produce a valid Ogg Vorbis file at {out_path}")
    return out_path


# --------------------------------------------------------------------------- Memoria.ini PriorityToOGG
def set_priority_to_ogg(game=None, value: int = 1, do_backup: bool = True) -> dict:
    """Set ``[Audio] PriorityToOGG = value`` in the game's Memoria.ini (REQUIRED for a loose OGG to win over
    the bundled AKB). Backs the ini up first. Returns ``{"changed", "was", "backup", "path"}``. No-op if
    already at ``value``."""
    import re
    import time
    ini = config.find_game_path(game) / "Memoria.ini"
    if not ini.exists():
        return {"changed": False, "was": None, "backup": None, "path": str(ini), "note": "Memoria.ini not found"}
    text = ini.read_text(encoding="utf-8")
    m = re.search(r"(?m)^(\s*PriorityToOGG\s*=\s*)(\S+)", text)
    was = m.group(2) if m else None
    if was == str(value):
        return {"changed": False, "was": was, "backup": None, "path": str(ini)}
    backup = None
    if do_backup:
        backup = f"{ini}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(ini, backup)
    if m:
        text = text[:m.start()] + m.group(1) + str(value) + text[m.end():]
    else:                                                  # no key -> append under [Audio], else a new section
        if re.search(r"(?m)^\[Audio\]", text):
            text = re.sub(r"(?m)^(\[Audio\]\s*)$", r"\g<1>\nPriorityToOGG = " + str(value), text, count=1)
        else:
            text += f"\n[Audio]\nPriorityToOGG = {value}\n"
    ini.write_text(text, encoding="utf-8")
    return {"changed": True, "was": was, "backup": backup, "path": str(ini)}


def volume_key(kind: str) -> str:
    """The Memoria.ini volume that governs this kind (SFX -> SoundVolume, else MusicVolume)."""
    return "SoundVolume" if kind == "sfx" else "MusicVolume"


def ini_volume(kind: str, game=None):
    """The current governing volume (0-10) from Memoria.ini, or None if unreadable. A 0 = muted = you
    won't hear the override even though it loaded (the gotcha that music muted at 0 bit the first test)."""
    import re
    ini = config.find_game_path(game) / "Memoria.ini"
    if not ini.exists():
        return None
    m = re.search(r"(?m)^\s*" + volume_key(kind) + r"\s*=\s*(\d+)", ini.read_text(encoding="utf-8"))
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------- deploy
def deploy_audio(in_path, song_id: int, mod_folder, *, kind: str = "music", loop_start=None, loop_end=None,
                 quality: int = 6, set_priority: bool = True, game=None) -> dict:
    """Encode ``in_path`` -> Ogg Vorbis and place it at the loose-override path in ``mod_folder`` for the
    given ``song_id`` (resolved to its ResourceID), clearing any stale ``.akb.bytes`` runtime cache and
    (``set_priority``) forcing ``PriorityToOGG=1``. Returns a manifest dict. RESTART the game to hear it
    (audio loads at startup; no F6 hot-reload)."""
    resource_id = resolve_resource_id(song_id, kind, game=game)
    dest = Path(mod_folder) / override_rel_path(resource_id)
    encode_ogg(in_path, dest, loop_start=loop_start, loop_end=loop_end, quality=quality)
    stale = dest.with_name(dest.stem + ".akb.bytes")       # engine writes <ResourceID>.akb.bytes next to the ogg
    if stale.exists():
        stale.unlink()
    prio = set_priority_to_ogg(game=game) if set_priority else None
    return {"kind": kind, "song_id": int(song_id), "resource_id": resource_id, "path": str(dest),
            "loop_start": loop_start, "loop_end": loop_end, "priority": prio,
            "volume_key": volume_key(kind), "volume": ini_volume(kind, game=game)}


# --------------------------------------------------------------------------- new-song-id minting
# ADD a track (a new id), not just swap an existing one. The engine reads a mod's override *MetaData.txt
# from the EMBEDDED-asset root <mod>/FF9_Data/EmbeddedAsset/ (NOT StreamingAssets/Assets/Resources --
# GetResourcesAssetsPath(true)="FF9_Data"); it REPLACES the stock table and GetSoundProfile is a dict with
# no bounds cap, so a fresh id resolves. In-game proven 2026-07-05. New ids sit in a band clear of stock.
MINT_ID_BASE = {"music": 1000, "sfx": 100000}     # stock music ids top out ~136; sfx in the thousands


def manifest_override_path(mod_folder, kind: str = "music") -> Path:
    """The mod-folder path for an override ``*MetaData.txt`` -- the EMBEDDED-asset root is ``FF9_Data/``,
    NOT ``StreamingAssets/Assets/Resources/`` (the load-bearing path correction, in-game proven)."""
    return Path(mod_folder) / "FF9_Data" / "EmbeddedAsset" / "Manifest" / "Sounds" / MANIFESTS[kind]


def serialize_manifest(entries) -> str:
    """``[{"id","resource_id","type"}]`` -> the engine's ``{"data":[{name, soundIndex, type}]}`` JSON. The
    override REPLACES the stock table, so ``entries`` must be the FULL set (stock + your additions)."""
    return json.dumps({"data": [{"name": e["resource_id"], "soundIndex": str(e["id"]),
                                 "type": e.get("type") or "Music"} for e in entries]})


def next_free_song_id(entries, kind: str = "music") -> int:
    used = {e["id"] for e in entries}
    i = MINT_ID_BASE[kind]
    while i in used:
        i += 1
    return i


def base_entries(mod_folder, kind: str = "music", game=None) -> list:
    """The entries a mint extends: the mod's EXISTING override manifest (preserving prior mints) if present,
    else the stock table extracted from the install."""
    mpath = manifest_override_path(mod_folder, kind)
    if mpath.exists():
        return parse_manifest(mpath.read_text(encoding="utf-8"))
    return read_manifest(kind, game=game)


def mint_song(in_path, mod_folder, *, kind: str = "music", new_id=None, resource_id=None, loop_start=None,
              loop_end=None, quality: int = 6, set_priority: bool = True, game=None) -> dict:
    """MINT a NEW song id (add, don't swap): extend the mod's override manifest with a fresh id + a new
    ResourceID and deploy the OGG. Accumulates onto an existing override manifest (mint several). Returns
    ``{song_id, resource_id, manifest, ogg, ...}``. TRIGGER it in a field: ``[music] song = <song_id>`` (or
    ``RunSoundCode(0, <song_id>)`` in the ``.eb``). ``new_id`` auto-picks a free id in the mint band."""
    base = base_entries(mod_folder, kind, game=game)
    if new_id is None:
        new_id = next_free_song_id(base, kind)
    elif any(e["id"] == int(new_id) for e in base):
        raise ValueError(f"{kind} id {new_id} already exists in the manifest -- omit --id to auto-pick a free one")
    new_id = int(new_id)
    if resource_id is None:
        sub = "Sounds01/BGM_" if kind == "music" else "Sounds02/SE00"
        resource_id = f"{sub}/custom{new_id}"
    dest = Path(mod_folder) / override_rel_path(resource_id)
    encode_ogg(in_path, dest, loop_start=loop_start, loop_end=loop_end, quality=quality)   # raises first -- no
    stale = dest.with_name(dest.stem + ".akb.bytes")                                       # manifest row on failure
    if stale.exists():
        stale.unlink()
    entries = base + [{"id": new_id, "resource_id": resource_id, "type": "Music" if kind == "music" else "SoundEffect"}]
    mpath = manifest_override_path(mod_folder, kind)
    mpath.parent.mkdir(parents=True, exist_ok=True)
    fsutil.atomic_write_text(mpath, serialize_manifest(entries))
    prio = set_priority_to_ogg(game=game) if set_priority else None
    return {"kind": kind, "song_id": new_id, "resource_id": resource_id, "manifest": str(mpath),
            "ogg": str(dest), "path": str(dest), "loop_start": loop_start, "loop_end": loop_end,
            "priority": prio, "minted": True, "volume_key": volume_key(kind), "volume": ini_volume(kind, game=game)}
