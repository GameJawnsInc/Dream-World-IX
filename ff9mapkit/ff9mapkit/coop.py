"""Co-op ghost-sync setup -- one command per player.

The multiplayer "ghost sync" (engine patch s36) lets two players see each
other walk a shared field. Getting there used to mean hand-editing
``Memoria.ini``, deploying a co-op room, digging a session code out of a log,
and running the TLS bridge in its own console. This module folds all of that
into one command per side:

    ff9mapkit coop host              set up + host a session (prints/copies the code)
    ff9mapkit coop join ff9-XXXX     set up + join a friend's session
    ff9mapkit coop show              print the current co-op config in human terms
    ff9mapkit coop off               switch co-op off in Memoria.ini
    ff9mapkit coop bridge            run just the ws->wss bridge (advanced)

PLAY STYLE (engine s37; every knob hot-reloads into a running game within ~2s).
``host``/``join`` take optional flags that write the matching ``[Netsync]`` keys --
each is only written when its flag is given, so re-runs never clobber hand tuning:

    --guest-slots 2        battle co-op: your friend commands YOUR party slot 2
                           (positions 1-4 as the party menu shows them; "2,3" = two
                           slots, "none" = spectate only)         -> GuestSlots (mask)
    --guest-wait 30        cap a guest turn's gauge-freeze at 30s; 0 = no cap
                                                                  -> GuestWaitMs
    --ghost-as auto        visitor mode: dress their ghost as the party member they
                           command ("auto"), a name (vivi, dagger, ...), or "off"
                                                                  -> GhostAs
    --follow-host on       guest side: auto-warp to the host's field; your own
                           random encounters pause while paired   -> FollowHost
    --diorama on           guest side (s40 engine): when the host fights, your
                           screen boots the SAME battle live (render-only);
                           "off" keeps the text spectate panel    -> Diorama

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

from . import fsutil
from .config import find_game_path

COOP_FIELD = 30003          # the co-op hangout room's field id
COOP_DONOR = "1953"         # Quan's Dwelling overlook -- the room is a --native fork of it
COOP_MOD = "FF9Coop"        # dedicated mod folder (never touched by campaign redeploys)
COOP_NAME = "COOP"          # field/script name inside the built mod
BRIDGE_PORT = 49201         # local ws:// port FF9 connects to
_CODE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# The playable names the engine's visitor mode can dress a ghost as (NetSyncVisitor.NameToRig,
# s37) -- the 8 mains with proven field rigs; dagger/salamander are aliases. Anyone else
# (Cinna/Marcus/Blank/Beatrix/customs) has no proven rig row, so the engine refuses = undressed.
GHOST_NAMES = ("zidane", "vivi", "garnet", "dagger", "steiner",
               "freya", "quina", "eiko", "amarant", "salamander")


def parse_guest_slots(spec: str) -> int:
    """A human slot spec -> the engine's ``GuestSlots`` bitmask. The spec lists PARTY POSITIONS
    1-4 (as the in-game party menu shows them), comma-separated: ``"2"`` = the second member,
    ``"2,3"`` = second + third. ``"0"``/``"none"``/``"off"`` = no slots (spectate only),
    ``"all"`` = every slot. Raises ValueError with a usable message otherwise."""
    t = (spec or "").strip().lower()
    if t in ("0", "none", "off", ""):
        return 0
    if t == "all":
        return 0x0F
    mask = 0
    for part in t.replace(" ", ",").split(","):
        if not part:
            continue
        if not part.isdigit() or not 1 <= int(part) <= 4:
            raise ValueError(f"bad guest slot {part!r}: give party positions 1-4 "
                             "(comma-separated), 'all', or 'none'")
        mask |= 1 << (int(part) - 1)
    return mask


def format_guest_slots(mask: int) -> str:
    """The engine bitmask back in human terms: ``6`` -> ``"2, 3"``; ``0`` -> ``"none (spectate)"``."""
    slots = [str(i + 1) for i in range(4) if mask & (1 << i)]
    return ", ".join(slots) if slots else "none (spectate)"


def parse_ghost_as(name: str) -> str:
    """Normalize a ``--ghost-as`` value to what the engine accepts: ``""`` (their own model),
    ``"auto"``, or a playable name from :data:`GHOST_NAMES`. Raises ValueError on anything else --
    the engine would just silently un-dress, better to say so up front."""
    t = (name or "").strip().lower()
    if t in ("", "off", "none", "0"):
        return ""
    if t == "auto" or t in GHOST_NAMES:
        return t
    raise ValueError(f"unknown ghost outfit {name!r}: use auto, off, or one of "
                     + ", ".join(n for n in GHOST_NAMES))


def playstyle_updates(guest_slots: str | None = None, guest_wait: int | None = None,
                      ghost_as: str | None = None, follow_host: bool | None = None,
                      diorama: bool | None = None) -> dict:
    """The ``[Netsync]`` play-style updates for whichever knobs were actually given (None = leave
    the ini alone -- a re-run must not clobber hand-tuned values). ``guest_wait`` is SECONDS
    (0 = no cap); the ini key is milliseconds. ``diorama`` follows the engine default ON (s40):
    only an explicit off writes ``0``."""
    updates: dict = {}
    if guest_slots is not None:
        updates["GuestSlots"] = str(parse_guest_slots(guest_slots))
    if guest_wait is not None:
        if guest_wait < 0:
            raise ValueError("--guest-wait takes seconds >= 0 (0 = no cap)")
        updates["GuestWaitMs"] = str(guest_wait * 1000)
    if ghost_as is not None:
        updates["GhostAs"] = parse_ghost_as(ghost_as)
    if follow_host is not None:
        updates["FollowHost"] = "1" if follow_host else "0"
    if diorama is not None:
        updates["Diorama"] = "1" if diorama else "0"
    return updates


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


def _backup_ini(ini: Path) -> Path:
    """Snapshot ``ini`` to a timestamped sibling before any in-place edit -- the ONE backup
    mechanism every Memoria.ini writer in this module routes through."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = ini.with_name(f"Memoria.ini.coop-bak-{stamp}")
    shutil.copyfile(ini, backup)
    return backup


def write_netsync(game: Path, updates: dict, *, out=print) -> Path | None:
    """Apply ``updates`` to ``[Netsync]`` in Memoria.ini, backing the file up first.
    Returns the backup path (None if the ini didn't exist -- refuse in that case)."""
    ini = _ini_path(game)
    if not ini.is_file():
        raise FileNotFoundError(f"{ini} not found -- is this really the FF9 install "
                                "(and is Memoria set up)?")
    backup = _backup_ini(ini)
    text = ini.read_text(encoding="utf-8", errors="replace")
    fsutil.atomic_write_text(ini, update_ini_section(text, "Netsync", updates), encoding="utf-8")
    out(f"  Memoria.ini: [Netsync] updated (backup: {backup.name})")
    return backup


def read_folder_names(text: str) -> list[str]:
    raw = read_ini_key(text, "Mod", "FolderNames") or ""
    return [p.strip().strip('"') for p in raw.split(",") if p.strip().strip('"')]


def mod_order_updates(text: str, names: list[str]) -> dict:
    """The ``[Mod]`` updates that set ``FolderNames`` to exactly ``names`` -- ALWAYS rewriting
    ``Priorities`` in the same breath. THE LAUNCHER LAW (root-caused 2026-07-12): the Memoria
    Launcher treats ``Priorities`` as the MASTER order -- ``LoadModSettings`` builds its mod list
    in Priorities order and ``UpdateModSettings`` REWRITES FolderNames from that list at every
    Play click (``Memoria.Launcher/MainWindow_ModManager.cs``), so a FolderNames-only edit is
    silently reverted on the next launch. EVERY kit writer that sets or reorders FolderNames must
    route through here. Invariant kept: the active folders appear in Priorities in the SAME
    sequence as FolderNames; entries only in Priorities (the launcher's inactive mods) keep their
    positions; a missing Priorities key is left missing (the launcher then seeds it from
    FolderNames, order intact)."""
    updates = {"FolderNames": ", ".join(f'"{n}"' for n in names)}
    prio = read_ini_key(text, "Mod", "Priorities")
    if prio is not None:
        old = [p.strip().strip('"') for p in prio.split(",") if p.strip().strip('"')]
        active = {n.lower() for n in names}
        queue = list(names)                  # actives, in the order FolderNames will declare
        merged: list[str] = []
        for p in old:
            if p.lower() in active:
                if queue:                    # each old active slot takes the NEXT active in order
                    merged.append(queue.pop(0))
            else:                            # inactive mod: keep its position untouched
                merged.append(p)
        merged.extend(queue)                 # newly-added actives with no old slot go last
        updates["Priorities"] = ", ".join(f'"{n}"' for n in merged)
    return updates


def ensure_folder_registered(game: Path, folder: str, *, out=print) -> bool:
    """Add ``folder`` to ``[Mod] FolderNames`` (at the END -- the room's assets are uniquely named, and
    last place keeps its text block from shadowing other folders'). True if the ini was changed.
    Writes FolderNames AND Priorities together (:func:`mod_order_updates` -- the launcher reverts a
    FolderNames-only edit at the next Play click). Backs the ini up first, same as :func:`write_netsync`
    -- this is the FIRST ini mutation of a default `coop host`/`coop join` run."""
    ini = _ini_path(game)
    text = ini.read_text(encoding="utf-8", errors="replace")
    names = read_folder_names(text)
    if any(n.lower() == folder.lower() for n in names):
        return False
    updates = mod_order_updates(text, names + [folder])
    backup = _backup_ini(ini)
    fsutil.atomic_write_text(ini, update_ini_section(text, "Mod", updates), encoding="utf-8")
    out(f'  Memoria.ini: added "{folder}" to [Mod] FolderNames + Priorities (backup: {backup.name})')
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


def show_config(game: Path, *, out=print) -> int:
    """Print the current ``[Netsync]`` state in human terms -- the CLI twin of the Workspace
    tab's status panel. Read-only; safe with the game running."""
    ini = _ini_path(game)
    if not ini.is_file():
        out(f"{ini} not found -- is this really the FF9 install?")
        return 2
    text = ini.read_text(encoding="utf-8", errors="replace")
    key = lambda k, d="": (read_ini_key(text, "Netsync", k) or d).strip()
    enabled = key("Enabled") == "1"
    out(f"FF9 install: {game}")
    out(f"  co-op:       {'ON' if enabled else 'off'}")
    if not enabled:
        out("  (start one with  ff9mapkit coop host  /  ff9mapkit coop join <code>)")
        return 0
    role = key("Role", "host")
    relay = key("RelayUrl")
    target = key("TargetField", "0") or "0"
    out(f"  role:        {role}" + ("  (selftest = solo mirror)" if role not in ("host", "client") else ""))
    out(f"  transport:   " + (f"relay via {relay}" if relay else f"direct LAN ({key('PeerAddress') or 'listening'})"))
    out(f"  session:     {key('SessionCode') or '(no code)'}")
    out(f"  where:       " + ("everywhere (any shared screen)" if target == "0" else f"field {target} only"))
    try:
        mask = int(key("GuestSlots", "0") or "0") & 0x0F
    except ValueError:
        mask = 0
    out(f"  battle:      friend commands slot(s) {format_guest_slots(mask)}")
    try:
        wait = int(key("GuestWaitMs", "30000") or "30000")
    except ValueError:
        wait = 30000
    out(f"  wait cap:    " + (f"{wait // 1000}s per guest turn" if wait else "none (guest can hold the gauges)"))
    ghost = key("GhostAs").lower()
    out(f"  ghost as:    " + ("their own model" if ghost in ("", "off", "0") else
                              "auto (the party member they command)" if ghost == "auto" else ghost))
    out(f"  follow-host: " + ("ON (auto-warp + encounter pause)" if key("FollowHost") == "1" else "off"))
    out(f"  diorama:     " + ("ON (their battles boot live on my screen; s40 engine)"
                              if key("Diorama", "1") != "0" else "off (text spectate panel)"))
    return 0


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

    # validate the play-style flags FIRST -- a typo must not cost the minute-long room build
    follow = getattr(args, "follow_host", None)
    diorama = getattr(args, "diorama", None)
    try:
        style = playstyle_updates(getattr(args, "guest_slots", None),
                                  getattr(args, "guest_wait", None),
                                  getattr(args, "ghost_as", None),
                                  None if follow is None else follow == "on",
                                  None if diorama is None else diorama == "on")
    except ValueError as e:
        out(f"  {e}")
        return 2

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
    if role == "host":
        updates["FollowHost"] = "0"                  # a host never follows its guest -- FollowHost fires
                                                     # regardless of role, so a stale selftest value would
                                                     # drag the host to the guest's field (--follow-host still
                                                     # overrides via `style` below if ever explicitly wanted)
    updates.update(style)
    write_netsync(game, updates, out=out)
    if "GuestSlots" in style:
        out("  battle: your friend commands party slot(s) "
            + format_guest_slots(int(style["GuestSlots"]))
            + " (0 keys them to spectating)")
    if "GuestWaitMs" in style:
        ms = int(style["GuestWaitMs"])
        out("  battle: guest turns can hold the gauges for "
            + (f"up to {ms // 1000}s" if ms else "as long as they like (no cap)"))
    if "GhostAs" in style:
        gv = style["GhostAs"]
        out("  visitor: their ghost appears as "
            + ("its own model" if not gv else
               "the party member they command in battle" if gv == "auto" else gv))
    if "FollowHost" in style:
        out("  visitor: follow-host " + ("ON -- your game auto-warps to their field and your "
                                         "random encounters pause while paired"
                                         if style["FollowHost"] == "1" else "off"))
    if "Diorama" in style:
        out("  battle diorama " + ("ON -- when they fight, your screen boots the same battle "
                                   "live (render-only; needs the s40 engine on this machine)"
                                   if style["Diorama"] == "1" else
                                   "off -- their battles show as the text spectate panel"))

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
    if action == "show":
        return show_config(find_game_path(args.game), out=out)
    if action == "bridge":
        return _run_bridge_foreground(args.port, getattr(args, "relay", None),
                                      getattr(args, "insecure", False), out=out)
    out(f"unknown coop action: {action}")
    return 2
