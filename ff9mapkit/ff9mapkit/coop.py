"""Co-op ghost-sync setup -- one command per player.

The multiplayer "ghost sync" (engine patch s36) lets two players see each
other walk a shared field. Getting there used to mean hand-editing
``Memoria.ini``, deploying a co-op room, digging a session code out of a log,
and running the TLS bridge in its own console. This module folds all of that
into one command per side:

    ff9mapkit coop host              set up + host a session (prints/copies the code)
    ff9mapkit coop join ff9-XXXX     set up + join a friend's session
    ff9mapkit coop off               switch co-op off in Memoria.ini
    ff9mapkit coop bridge            run just the ws->wss bridge (advanced)

Co-op works EVERYWHERE by default: ghosts appear on any screen both players
share (``--field N`` restricts it to one field). What ``host``/``join`` do:

1. **Room** -- make sure the co-op hangout room (30003, a native fork of
   Quan's Dwelling overlook 1953) is registered in SOME active mod folder; if
   not, build it from the player's own install into a dedicated ``FF9Coop``
   mod folder (its own folder so campaign redeploys can never wipe it) and
   add that folder to ``[Mod] FolderNames``. The room is the guaranteed
   meeting spot -- both installs are certain to have the same field there.
2. **Config** -- back up ``Memoria.ini`` and write the ``[Netsync]`` section
   (role, target field, relay URL pointing at the local bridge, session code).
3. **Code** -- the host reuses its saved session code or mints a random
   ``ff9-XXXXXXXX`` (the code is the only thing that pairs two players on the
   shared relay -- treat it like a private invite link); it is echoed big and
   copied to the clipboard. The guest passes the host's code to ``join``.
4. **Bridge** -- run the ws->wss bridge in-process and stay in the foreground
   while the game plays (FF9's old Mono has no TLS 1.2, so the bridge carries
   the connection to the relay).

Direct-LAN mode (no relay, no bridge, same WiFi): ``coop host --lan`` and
``coop join --lan <host-ip>``.

Requires the engine with the s36 netsync patch (the Dream World IX custom
Memoria bundle). Current engine builds HOT-RELOAD the ``[Netsync]`` section,
so a running game picks the new session up within seconds (from fully OFF,
at the next screen change); on older builds, relaunch FF9 after this runs.
"""

from __future__ import annotations

import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .config import find_game_path

COOP_FIELD = 30003          # the co-op hangout room's field id
COOP_DONOR = "1953"         # Quan's Dwelling overlook -- the room is a --native fork of it
COOP_MOD = "FF9Coop"        # dedicated mod folder (never touched by campaign redeploys)
COOP_NAME = "COOP"          # field/script name inside the built mod
BRIDGE_PORT = 49201         # local ws:// port FF9 connects to
_CODE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def generate_code() -> str:
    """A random namespaced session code, e.g. ``ff9-K3QZ81MB``. The ``ff9-`` prefix keeps FF9 sessions
    out of other games' code namespace on the shared relay; pairing is case-insensitive."""
    return "ff9-" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))


# ---------------------------------------------------------------- Memoria.ini


def _ini_path(game: Path) -> Path:
    return game / "Memoria.ini"


def _split_lines(text: str):
    """Split preserving the file's newline style for the rewrite."""
    nl = "\r\n" if "\r\n" in text else "\n"
    return text.split(nl), nl


def read_ini_key(text: str, section: str, key: str) -> str | None:
    """The value of ``key`` inside ``[section]``, or None. Mirrors Memoria's parser: first match wins,
    ``;``/``#`` start comments, section/key names are case-insensitive."""
    in_sec = False
    for line in text.splitlines():
        t = line.strip()
        if t.startswith(";") or t.startswith("#"):
            continue
        if t.startswith("["):
            in_sec = t.lower().startswith("[" + section.lower() + "]")
            continue
        if in_sec and "=" in line:
            k, v = line.split("=", 1)
            if k.strip().lower() == key.lower():
                return v.split(";")[0].split("#")[0].strip()
    return None


def update_ini_section(text: str, section: str, updates: dict) -> str:
    """Rewrite ``[section]`` so every key in ``updates`` has the given value: existing key lines are
    replaced in place (comments elsewhere untouched), missing keys are added at the end of the section,
    and a missing section is appended to the file. Preserves the file's newline style."""
    lines, nl = _split_lines(text)
    out: list[str] = []
    pending = dict(updates)   # keys not yet written
    in_sec = False
    found_sec = False

    def flush_pending():
        for k, v in pending.items():
            out.append(f"{k} = {v}")
        pending.clear()

    for line in lines:
        t = line.strip()
        if t.startswith("[") and not (t.startswith(";") or t.startswith("#")):
            if in_sec:
                flush_pending()          # leaving our section -> add whatever wasn't present
            in_sec = t.lower().startswith("[" + section.lower() + "]")
            found_sec = found_sec or in_sec
            out.append(line)
            continue
        if in_sec and "=" in line and not (t.startswith(";") or t.startswith("#")):
            k = line.split("=", 1)[0].strip()
            hit = next((uk for uk in pending if uk.lower() == k.lower()), None)
            if hit is not None:
                out.append(f"{hit} = {pending.pop(hit)}")
                continue
        out.append(line)
    if in_sec:
        flush_pending()                  # section ran to EOF
    if pending:                          # section absent entirely
        if not found_sec:
            if out and out[-1].strip():
                out.append("")
            out.append(f"[{section}]")
        flush_pending()
    return nl.join(out)


def write_netsync(game: Path, updates: dict, *, out=print) -> Path | None:
    """Apply ``updates`` to ``[Netsync]`` in Memoria.ini, backing the file up first.
    Returns the backup path (None if the ini didn't exist -- refuse in that case)."""
    ini = _ini_path(game)
    if not ini.is_file():
        raise FileNotFoundError(f"{ini} not found -- is this really the FF9 install "
                                "(and is Memoria set up)?")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = ini.with_name(f"Memoria.ini.coop-bak-{stamp}")
    shutil.copyfile(ini, backup)
    text = ini.read_text(encoding="utf-8", errors="replace")
    ini.write_text(update_ini_section(text, "Netsync", updates), encoding="utf-8")
    out(f"  Memoria.ini: [Netsync] updated (backup: {backup.name})")
    return backup


def read_folder_names(text: str) -> list[str]:
    raw = read_ini_key(text, "Mod", "FolderNames") or ""
    return [p.strip().strip('"') for p in raw.split(",") if p.strip().strip('"')]


def ensure_folder_registered(game: Path, folder: str, *, out=print) -> bool:
    """Add ``folder`` to ``[Mod] FolderNames`` (at the END -- the room's assets are uniquely named, and
    last place keeps its text block from shadowing other folders'). True if the ini was changed."""
    ini = _ini_path(game)
    text = ini.read_text(encoding="utf-8", errors="replace")
    names = read_folder_names(text)
    if any(n.lower() == folder.lower() for n in names):
        return False
    updates = {"FolderNames": ", ".join(f'"{n}"' for n in names + [folder])}
    prio = read_ini_key(text, "Mod", "Priorities")
    if prio is not None:                 # keep the launcher's hint list in step when present
        pnames = [p.strip().strip('"') for p in prio.split(",") if p.strip().strip('"')]
        if not any(n.lower() == folder.lower() for n in pnames):
            updates["Priorities"] = ", ".join(f'"{n}"' for n in pnames + [folder])
    ini.write_text(update_ini_section(text, "Mod", updates), encoding="utf-8")
    out(f'  Memoria.ini: added "{folder}" to [Mod] FolderNames')
    return True


# ---------------------------------------------------------------- the room


def find_registered_field(game: Path, field_id: int) -> str | None:
    """Which ACTIVE mod folder (from FolderNames) registers ``field_id``? None if nobody does.
    (EventDB ids are global across stacked folders -- registering the same id twice black-screens,
    so an existing registration anywhere means the room is already available.)"""
    ini = _ini_path(game)
    if not ini.is_file():
        return None
    text = ini.read_text(encoding="utf-8", errors="replace")
    needle = f"FieldScene {field_id} "
    for folder in read_folder_names(text) + [COOP_MOD]:
        dp = game / folder / "DictionaryPatch.txt"
        try:
            if dp.is_file() and needle in dp.read_text(encoding="utf-8", errors="replace"):
                return folder
        except OSError:
            continue
    return None


def ensure_room(game: Path, *, field_id: int = COOP_FIELD, rebuild: bool = False, out=print) -> str:
    """Make sure ``field_id`` is registered in some active mod folder; build the FF9Coop room if not.
    Returns the folder name carrying the room."""
    existing = find_registered_field(game, field_id)
    if existing and not rebuild:
        out(f"  co-op room: field {field_id} already registered ({existing})")
        if existing.lower() == COOP_MOD.lower():
            ensure_folder_registered(game, COOP_MOD, out=out)
        return existing

    from . import extract                     # deferred: import machinery needs UnityPy
    from .build import FieldProject, build_mod

    out(f"  co-op room: building field {field_id} from your install "
        f"(a faithful fork of Quan's Dwelling overlook)...")
    mod_root = game / COOP_MOD
    with tempfile.TemporaryDirectory(prefix="ff9coop-") as tmp:
        _meta, toml = extract.write_native_project(
            COOP_DONOR, Path(tmp), name=COOP_NAME, field_id=field_id, game=game)
        project = FieldProject.load(toml)
        if mod_root.exists():
            shutil.rmtree(mod_root)           # wholly coop-owned folder -> safe to regenerate
        build_mod([project], mod_root, mod_name=COOP_MOD,
                  description="FF9 co-op hangout room (ghost sync)")
    # build_mod doesn't emit ForkDonorPatch; the engine's fork-donor remap (narrow-map width etc.)
    # wants the fork -> donor mapping, same header deploy_field writes.
    (mod_root / "ForkDonorPatch.txt").write_text(
        f"# ff9mapkit fork-fidelity: {field_id} {COOP_DONOR}\n{field_id} {COOP_DONOR}\n",
        encoding="utf-8")
    ensure_folder_registered(game, COOP_MOD, out=out)
    out(f"  co-op room: built -> {mod_root}  (first launch after this registers it)")
    return COOP_MOD


# ---------------------------------------------------------------- commands


def _copy_clipboard(text: str) -> bool:
    clip = shutil.which("clip")
    if not clip:
        return False
    try:
        subprocess.run([clip], input=text.encode("ascii"), check=True, timeout=5)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def _run_bridge_foreground(port: int, relay: str | None, insecure: bool, *, out=print) -> int:
    from . import netsync_bridge as nb
    relay_url = relay or nb.default_relay()
    server, thread = nb.run_server("127.0.0.1", port, relay_url, insecure)
    out(f"  bridge: running on ws://127.0.0.1:{port} -- leave this window open while you play "
        "(Ctrl+C to stop)")
    try:
        while thread.is_alive():
            thread.join(timeout=1.0)
    except KeyboardInterrupt:
        out("  bridge: stopped")
    finally:
        server.close()
    return 0


def _setup(args, role: str, code: str | None, *, out=print) -> int:
    game = find_game_path(args.game)
    out(f"FF9 install: {game}")

    lan = getattr(args, "lan", None)
    target = int(getattr(args, "field", None) or 0)      # 0 = co-op EVERYWHERE; --field N restricts
    if not getattr(args, "no_room", False):
        # the co-op room stays the guaranteed meeting spot (both installs are certain to have it)
        ensure_room(game, rebuild=getattr(args, "rebuild_room", False), out=out)

    ini_text = _ini_path(game).read_text(encoding="utf-8", errors="replace")
    if role == "host" and not code:
        code = None if getattr(args, "new_code", False) else read_ini_key(ini_text, "Netsync", "SessionCode")
        code = code or generate_code()

    updates = {
        "Enabled": "1",
        "Role": "host" if role == "host" else "client",
        "TargetField": str(target),
        "SessionCode": code or "",
    }
    if lan is not None:
        updates["RelayUrl"] = ""                     # blank -> the proven direct-TCP transport
        if role != "host":
            updates["PeerAddress"] = lan
    else:
        updates["RelayUrl"] = f"ws://127.0.0.1:{args.port}"
    write_netsync(game, updates, out=out)

    out("")
    if role == "host":
        clip = " (copied to clipboard)" if _copy_clipboard(code) else ""
        out(f"  session code:  {code}{clip}")
        out(f"  send it to your friend -- they run:  ff9mapkit coop join {code}")
    else:
        out(f"  joining session {code}")
    if target:
        out(f"  then: launch FF9 -> F6 -> Warp to field -> {target}   (both players)")
    else:
        out("  then: launch FF9 and stand on the SAME screen as your friend -- ghosts appear anywhere "
            f"you two share a field (guaranteed spot: F6 -> Warp -> {COOP_FIELD})")
    if lan is not None:
        out("  direct-LAN mode: no bridge needed. Same WiFi; allow FF9 through the firewall on both.")
        return 0
    out("")
    if getattr(args, "no_bridge", False):
        out(f"  --no-bridge: start it later with  ff9mapkit coop bridge --port {args.port}")
        return 0
    return _run_bridge_foreground(args.port, getattr(args, "relay", None),
                                  getattr(args, "insecure", False), out=out)


def run(args, out=print) -> int:
    """CLI entry -- dispatch ``ff9mapkit coop <action>``."""
    action = args.action
    if action == "host":
        return _setup(args, "host", args.code, out=out)   # bare --lan ('') is fine: the host listens
    if action == "join":
        code = args.code
        if getattr(args, "lan", None) is None and not code:
            out("join needs the HOST's session code:  ff9mapkit coop join ff9-XXXXXXXX")
            return 2
        if getattr(args, "lan", None) == "":
            out("join --lan needs the host's IP:  ff9mapkit coop join --lan 192.168.1.50")
            return 2
        return _setup(args, "client", code, out=out)
    if action == "off":
        game = find_game_path(args.game)
        write_netsync(game, {"Enabled": "0"}, out=out)
        out("  co-op disabled (Role/code kept -- `coop host`/`coop join` re-enables)")
        return 0
    if action == "bridge":
        return _run_bridge_foreground(args.port, getattr(args, "relay", None),
                                      getattr(args, "insecure", False), out=out)
    out(f"unknown coop action: {action}")
    return 2
