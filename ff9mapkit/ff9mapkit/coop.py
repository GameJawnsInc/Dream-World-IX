"""Co-op ghost-sync setup -- one command per player.

The multiplayer "ghost sync" (engine patch s36) lets two players see each
other walk a shared field; later netsync patches add following the host,
battle co-op and world-map co-op (the generations: health.NETSYNC_GENERATIONS).
Getting there used to mean hand-editing
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
                           -- never the character you walk as: a position the story
                           gives your leader passes to the next member (engine s143)
    --guest-wait 30        cap a guest turn's gauge-freeze at 30s; 0 = no cap
                                                                  -> GuestWaitMs
    --ghost-as auto        visitor mode. HOST: what your guest appears as on BOTH
                           screens -- an s140+ guest wears it itself unless its own
                           [Netsync] SelfDress=0 -- "auto" (the member they command),
                           a name (vivi, dagger, ..., cinna, marcus, blank, beatrix,
                           moogle) or "off". GUEST: only your view of the host (the
                           8 mains) -- normally off: an s140+ guest already wears
                           the host's pick, so the same pick on both machines shows
                           the guest two of that character        -> GhostAs
    --follow-host on       guest side: auto-warp to the host's field; your own
                           random encounters pause while paired   -> FollowHost
                           -- on the world map the host drives: you wait there
                           and rejoin their next field (engine s144); their
                           battles there boot on your screen too and return
                           you where you stood (engine s145)

(The battle diorama -- a following guest's screen boots the host's battles
live -- is always on since the s42 engine; the old ``--diorama`` knob is gone.
The text spectate panel remains as the automatic fallback whenever a diorama
can't boot, and the ~ debug menu's "Leave diorama" opts out of any single fight.)

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
3. **Code** -- the host reuses ITS OWN saved session code (``[Netsync]
   HostSessionCode``) or mints a random ``ff9-XXXXXXXX`` (the code is the only
   thing that pairs two players on the shared relay -- treat it like a private
   invite link); it is echoed big and copied to the clipboard. The guest passes
   the host's code to ``join``, which sets ``SessionCode`` (what the engine
   dials) and never the own code: a code you joined a friend with is never
   re-published when you host (:func:`own_host_code`; ``--new-code`` mints a
   fresh one; an explicit ``coop host <that code>`` dials it for that run only,
   :func:`joined_override`).
4. **Bridge** -- run the ws->wss bridge in-process and stay in the foreground
   while the game plays (FF9's old Mono has no TLS 1.2, so the bridge carries
   the connection to the relay). Its lines are wall-clock stamped and teed to
   ``%LOCALAPPDATA%\\ff9mapkit\\bridge-logs\\`` (``--bridge-log FILE`` overrides);
   a game that stops sending for 10 s (``--hang-after``) is logged as SILENT, and
   ``--hang-dump`` (or ``FF9_HANG_DUMP=1``; default off, a dump is 1-3 GB) also
   writes one full minidump of the hung FF9.exe + its logs to
   ``%LOCALAPPDATA%\\ff9mapkit\\hangdumps\\`` (``--hang-dump-dir DIR``).

Direct-LAN mode (no relay, no bridge, same WiFi): ``coop host --lan`` and
``coop join --lan <host-ip>``.

Requires the engine with the s36 netsync patch (the Dream World IX custom
Memoria bundle). Current engine builds HOT-RELOAD the ``[Netsync]`` section,
so a running game picks the new session up within seconds (from fully OFF,
at the next screen change); on older builds, relaunch FF9 after this runs.
"""

from __future__ import annotations

import re
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
_CODE_RE = re.compile(r"(?i:ff9-)?[A-Za-z0-9]{1,32}")   # everything validate_code() accepts

# The playable names the engine's visitor mode can dress a ghost as (NetSyncVisitor.NameToRig,
# s37) -- the 8 mains with proven field rigs; dagger/salamander are aliases. Until s140 anyone else
# had no proven rig row (the engine refused = undressed); customs still do. The s139/s140 rows follow.
# [ff9mapkit netsync s139] + "moogle" (rig row 8, GEO_NPC_F0_MOG): the same moogle the host's
# `auto` rule shows for a spectator or an empty puppet slot. It dresses the HOST's ghost of its
# guest only -- a client keeps the s138 rule and leaves the host's ghost undressed (the host is
# never a moogle), as does an engine before s139. A test pins this tuple to NameToRig's keys.
# [ff9mapkit netsync s140] + "cinna", "marcus", "blank", "beatrix" (rig rows 9-12, CharacterId 8-11:
# the owner's "their own models" -- each row from the install's census). Like the moogle, a name
# dresses the HOST's ghost of its guest only (a client's s138 rule caps names at the 8 mains); an
# engine before s140 leaves them undressed.
GHOST_NAMES = ("zidane", "vivi", "garnet", "dagger", "steiner",
               "freya", "quina", "eiko", "amarant", "salamander", "moogle",
               "cinna", "marcus", "blank", "beatrix")


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


HOST_FOLLOW_REFUSED = ("follow-host is for the joining side: a host never follows its guest (the engine "
                       "follows regardless of role, so a following host and its following guest chase each "
                       "other between screens)")


def playstyle_updates(guest_slots: str | None = None, guest_wait: int | None = None,
                      ghost_as: str | None = None, follow_host: bool | None = None,
                      *, role: str | None = None) -> dict:
    """The ``[Netsync]`` play-style updates for whichever knobs were actually given (None = leave
    the ini alone -- a re-run must not clobber hand-tuned values). ``guest_wait`` is SECONDS
    (0 = no cap); the ini key is milliseconds. (The ``Diorama`` knob was REMOVED with the s42
    engine -- the diorama is always-on for a follower; a stray ini line is silently ignored.)

    ``role="host"`` refuses ``follow_host=True`` (ValueError). The engine's follow tick has no role
    check, so this is the one place both the CLI and the Workspace pass through: the b20 smoke test
    had a host ticked to follow, and host and guest bounced between two fields every few seconds."""
    if follow_host and role == "host":
        raise ValueError(HOST_FOLLOW_REFUSED)
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
    return updates


def generate_code() -> str:
    """A random namespaced session code, e.g. ``ff9-K3QZ81MB``. The ``ff9-`` prefix keeps FF9 sessions
    out of other games' code namespace on the shared relay; pairing is case-insensitive."""
    return "ff9-" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))


def validate_code(code: str) -> str:
    """Check a session code the user typed or pasted and return it UNCHANGED. Accepts an optional
    case-insensitive ``ff9-`` prefix + 1-32 ASCII letters/digits -- everything :func:`generate_code`
    (and the engine's own ``GenerateSessionCode``, s36) can mint, plus any plausible hand-set code.
    Raises ValueError otherwise. An empty code is NOT a code: callers mean "none given" by that and
    must not hand it here (`coop host` mints one, `coop join` refuses with its own message).

    This is a security fence, not a spelling check. The code lands in Memoria.ini as one
    ``SessionCode = <code>`` line, and the engine's parser (``IniFile.Init``) is a sequential LINE
    reader that is last-write-wins per (section, key) and re-enters a section on a second
    ``[Netsync]`` header -- so a newline inside a "code" is not a typo, it is extra ini keys. A
    poisoned invite (``ff9-AAAA0000\\nGuestSlots = 15\\n...``) pasted into `coop join` would hand the
    sender your party slots or re-point ``RelayUrl`` at their server. The alphabet also excludes
    ``=`` ``;`` ``#`` ``[`` ``]`` and whitespace, so no accepted value can grow a second key, a
    comment, or a section header on the line it is written to.

    Nothing is normalized -- pairing compares the LITERAL stored string on both sides of the relay,
    so upper-casing or inserting the prefix here could break pairing with a peer on an older build."""
    if not isinstance(code, str) or not _CODE_RE.fullmatch(code):
        raise ValueError(f"bad session code {code!r}: give the host's code exactly as they sent it "
                         "-- letters and digits only, e.g. ff9-XXXXXXXX")
    return code


# ---------------------------------------------------------------- Memoria.ini


def _ini_path(game: Path) -> Path:
    return game / "Memoria.ini"


_BOM = b"\xef\xbb\xbf"


def read_ini_text(ini: Path) -> str:
    """Memoria.ini as text with a leading UTF-8 byte-order mark removed. THE BOM LAW (studies/coop-review/REVIEW.md
    §1.3): Notepad and Notepad++ can save the file with a BOM, and a plain ``utf-8`` read keeps U+FEFF glued to the
    first line -- so a ``[Mod]`` header on line 1 stopped matching, ``read_folder_names`` returned [], and the first
    co-op setup appended a SECOND ``[Mod]`` whose ``FolderNames = "FF9Coop"`` the engine (last write wins) then loaded
    ALONE: every other mod gone. Every reader in this module goes through here."""
    return ini.read_text(encoding="utf-8-sig", errors="replace")


def ini_write_encoding(ini: Path) -> str:
    """The encoding to write Memoria.ini back in: ``utf-8-sig`` when the file already carries a BOM (kept, so a
    co-op edit never changes the file's encoding marker), else ``utf-8``."""
    try:
        with open(ini, "rb") as f:
            return "utf-8-sig" if f.read(3) == _BOM else "utf-8"
    except OSError:
        return "utf-8"


def _split_lines(text: str):
    """Split preserving the file's newline style for the rewrite."""
    nl = "\r\n" if "\r\n" in text else "\n"
    return text.split(nl), nl


def read_ini_key(text: str, section: str, key: str) -> str | None:
    """The value of ``key`` inside ``[section]``, or None -- the value the ENGINE would use.

    LAST match wins, because Memoria's parser does. ``IniFile.Init`` walks the file line by line and
    ends each one with ``Options[new Key(section, key)] = value``, a plain dictionary assignment, and
    it re-enters a section on a repeated ``[Netsync]`` header -- so where a key appears twice the
    later line is the one the game obeys. Reading the FIRST match (what this did) made every caller
    describe a file the engine was not playing: `coop show` would print a clean session code and an
    empty guest-slot mask off a ini whose second, poisoned copy of those keys was live, and the host
    setup's stored-code check would vet a value the engine had already overridden.

    Deliberately more permissive than the engine on two axes, both toward NOT missing a live line:
    section/key names match case-insensitively (the engine's ``Key`` struct compares ordinally), and
    an inline ``;``/``#`` is stripped from the value (the engine keeps it, having already stopped at
    the ``=``). ``;``/``#`` at the head of a line is a comment in both."""
    in_sec = False
    found = None
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
                found = v.split(";")[0].split("#")[0].strip()
    return found


def duplicate_ini_keys(text: str, section: str) -> list[str]:
    """The keys that appear more than once inside ``[section]``, in first-seen order.

    A duplicate is not just untidy -- it is the fingerprint of the pre-fence ini splice (a pasted
    "session code" carrying ``\\nGuestSlots = 15``), or of a hand-edit that pasted a friend's whole
    ``[Netsync]`` block below the existing one. Either way the engine silently honours the LAST copy
    while the visible one higher up says something else, so the diagnostics say so out loud."""
    in_sec, seen, dupes = False, set(), []
    for line in text.splitlines():
        t = line.strip()
        if t.startswith(";") or t.startswith("#"):
            continue
        if t.startswith("["):
            in_sec = t.lower().startswith("[" + section.lower() + "]")
            continue
        if in_sec and "=" in line:
            k = line.split("=", 1)[0].strip()
            if not k:
                continue
            if k.lower() in seen and k not in dupes:
                dupes.append(k)
            seen.add(k.lower())
    return dupes


# ---------------------------------------------------------------- THE OWN-CODE LAW (s154)
#
# [ff9mapkit s154] ONE ini key used to carry two meanings. The ENGINE reads [Netsync] SessionCode as "the code to dial
# now" -- a host's own code, or, after `coop join`, the FRIEND's invite -- while `coop host` also read it back as "this
# PC's own code, kept stable across runs". Nothing recorded which meaning the stored value had, so a PC that had joined a
# friend and later hosted re-published the friend's code: anyone holding that invite walked into ITS game, and two hosts
# on one code evicted each other (studies/coop-review/REVIEW.md appendix 25). The own code now has a key of its own.

#: THIS PC's own host code, kept apart from SessionCode (what the engine DIALS). Kit-owned: written by `coop host` (equal to
#: the SessionCode it writes -- with ONE exception: an explicit `coop host <code>` naming a code this PC JOINED with, see
#: :func:`joined_override`, dials that code this run and keeps the own code, or mints one, so the invite is never
#: recorded as this PC's) and once by `coop join`'s migration of a pre-s154 host ini. The engine never reads it, and its
#: PersistSessionCode matches 'SessionCode' exactly, so a HostSessionCode line is never touched.
HOST_CODE_KEY = "HostSessionCode"


def own_host_code(text: str) -> tuple[str | None, str, str]:
    """THE OWN-CODE LAW: the code THIS PC hosts on, read from Memoria.ini text, as ``(code, why, key)``. Pure.

    ``key`` names the ini key the verdict came from; ``why`` is one of

    * ``"own"``      -- ``HostSessionCode`` is set and passes :func:`validate_code`: that is the code.
    * ``"unusable"`` -- the key named holds a value :func:`validate_code` refuses: ABSENT. An unusable HostSessionCode
      never falls back to SessionCode, which may be an invite.
    * ``"migrated"`` -- no HostSessionCode (a pre-s154 ini) and the LAST ``Role`` is ``host`` (lowercased and trimmed,
      as the engine reads it): SessionCode was written by hosting (`coop host`, an engine mint, then maybe `coop off`).
    * ``"joined"``   -- no HostSessionCode and the last Role is ``client``: SessionCode is the code this PC JOINED with,
      a friend's. Never reused.
    * ``"unowned"``  -- no HostSessionCode and the Role is absent (the engine's default is selftest), selftest or anything
      else: nothing says hosting wrote that code, so it is never adopted either.
    * ``"none"``     -- nothing stored at all.

    ``code`` is set exactly for ``own`` and ``migrated``. Last key wins (:func:`read_ini_key`), like the engine."""
    own = (read_ini_key(text, "Netsync", HOST_CODE_KEY) or "").strip()
    if own:
        try:
            return validate_code(own), "own", HOST_CODE_KEY
        except ValueError:
            return None, "unusable", HOST_CODE_KEY
    stored = (read_ini_key(text, "Netsync", "SessionCode") or "").strip()
    if not stored:
        return None, "none", "SessionCode"
    role = (read_ini_key(text, "Netsync", "Role") or "").strip().lower()   # the engine's Trim().ToLowerInvariant()
    if role == "client":
        return None, "joined", "SessionCode"
    if role != "host":
        return None, "unowned", "SessionCode"
    try:
        return validate_code(stored), "migrated", "SessionCode"
    except ValueError:
        return None, "unusable", "SessionCode"


def joined_override(code: str | None, text: str) -> bool:
    """[ff9mapkit s154] Is ``code`` -- an EXPLICIT `coop host <code>` -- a code this PC JOINED with? Pure, on ini text.

    True when ``code`` equals the stored SessionCode (case-insensitively, as pairing compares) and either

    * the last ``Role`` is ``client``: this PC joined a session with it (the first override), or
    * this PC's own code (:func:`own_host_code`) is set and is NOT that SessionCode: a host dialling a code other than its
      own, which only an earlier override writes (a REPEATED `coop host <code>`, from shell history say: by then the
      Role reads ``host``). An explicit code that is not a joined one writes both keys equal, so it never trips this.

    Such a run still dials ``code`` (`coop host <code>` is a documented override), but `_setup` never records it as the own
    code -- otherwise every later bare `coop host` re-published the friend's invite, silently. Last key wins, like the
    engine."""
    if not code:
        return False
    stored = (read_ini_key(text, "Netsync", "SessionCode") or "").strip()
    if not stored or code.strip().upper() != stored.upper():
        return False
    if (read_ini_key(text, "Netsync", "Role") or "").strip().lower() == "client":
        return True
    own = own_host_code(text)[0]
    return bool(own) and own.upper() != stored.upper()


#: [ff9mapkit s154] The pre-fix residue the migration cannot tell apart from a genuine own code: a PC that joined a friend
#: and then hosted under an older kit already has Role=host plus the FRIEND's code. Said once, when the code is adopted.
#: The cure is named in its BRIDGE-SAFE form: a bare `coop host --new-code` runs its own bridge on the same port beside a
#: running one (the Workspace's, or another terminal's), and SO_REUSEADDR lets both bind on Windows. `--no-bridge` keeps
#: the bridge already running; Start hosting again (bare `coop host`) then keeps the new code and copies it.
MIGRATION_CAVEAT = ("if this PC ever hosted with a code a friend gave you, that code is theirs too -- run  "
                    "ff9mapkit coop host --new-code --no-bridge  for a fresh one (a bridge already running keeps "
                    "going; in the Workspace, press Start hosting again after it)")


# Every C0 control + DEL + the three line breaks only Python knows about. THE UNION IS DELIBERATE:
# .NET's StreamReader.ReadLine (the engine's parser) breaks on \r\n only, while Python's
# str.splitlines() -- what read_ini_key uses to read the same file back -- ALSO breaks on
# \x0b \x0c \x1c-\x1e \x85 \u2028 \u2029, so a denylist tuned to either parser alone leaves the other
# one splittable. Keys refuse the ini's structural characters on top of that.
_INI_BAD_VALUE = re.compile(r"[\x00-\x1f\x7f\x85\u2028\u2029]")
_INI_BAD_KEY = re.compile(r"[\x00-\x1f\x7f\x85\u2028\u2029=\[\];#]")


def _check_ini_pair(key: str, value) -> str:
    """Vet one ``key = value`` pair on its way into an ini line; returns the value as text.

    THE FENCE under every ini writer in this module. :func:`update_ini_section` renders each pair as
    one ``f"{k} = {v}"`` line and joins the lot with newlines, so a control character in either half
    is not a funny-looking setting -- it is a structural edit to the player's Memoria.ini. Memoria's
    parser (``IniFile.Init``) is a sequential LINE reader, last-write-wins per (section, key), that
    re-enters a section on a repeated ``[Netsync]`` header, so an embedded newline SPLICES IN whatever
    keys follow it and the spliced value WINS. That is how a pasted "session code" could hand its
    sender your party slots (:func:`validate_code` fences that one at the door); this layer makes the
    whole bug class unreachable for the NEXT bare string someone wires into an ini key here.

    REJECT, never strip. A silently stripped value writes a subtly WRONG setting the user never asked
    for and cannot see -- the ini looks fine and the game just behaves oddly. A raise is loud, names
    the key, and lets the caller say something useful. Nothing in the kit passes a control character
    today, so refusing costs nothing.

    Keys additionally refuse ``= [ ] ; #`` and emptiness: an ``=`` in a key means the file gets a
    DIFFERENT (shorter) key than the caller asked for, a leading ``;``/``#`` comments the whole
    setting out, and brackets can open a section header. Same bug, other door.

    Non-str values are rendered with ``str()`` and vetted AFTER: several callers already pass
    ``str(int)``, and it is the rendered text that actually lands in the file."""
    if not isinstance(key, str) or not key.strip() or _INI_BAD_KEY.search(key):
        raise ValueError(f"unusable ini key {key!r}: a key cannot be blank or carry a control "
                         "character, '=', ';', '#' or brackets")
    text = value if isinstance(value, str) else str(value)
    bad = _INI_BAD_VALUE.search(text)
    if bad:
        raise ValueError(f"unusable value for ini key {key!r}: {text!r} contains {bad.group()!r} -- "
                         "a control character would split or corrupt the line it is written to")
    return text


def update_ini_section(text: str, section: str, updates: dict) -> str:
    """Rewrite ``[section]`` so every key in ``updates`` has the given value: existing key lines are
    replaced in place (comments elsewhere untouched), missing keys are added at the end of the section,
    and a missing section is appended to the file. Preserves the file's newline style.

    A key that already appears TWICE in the section is written once (at the first occurrence) and its
    later copies are DROPPED. Memoria's parser is last-write-wins, so leaving a stale duplicate below
    would hand the engine the old value and make this whole call a no-op the ini does not show -- and
    the duplicate that matters in practice is the residue of a poisoned ``SessionCode``/``GuestSlots``
    splice, which must not survive the rewrite that is meant to correct it. Duplicates of keys this
    call is not updating are left alone; they are not ours to guess at.

    Raises ValueError -- producing NO output at all -- if any key or value carries a control
    character, so no line this function emits can ever carry a raw break. See :func:`_check_ini_pair`
    for why a newline here is an ini injection rather than a typo."""
    lines, nl = _split_lines(text)
    out: list[str] = []
    pending = {k: _check_ini_pair(k, v) for k, v in updates.items()}   # keys not yet written
    written: set = set()                                              # lowercased keys already emitted
    in_sec = False
    found_sec = False

    def flush_pending():
        for k, v in pending.items():
            out.append(f"{k} = {v}")
            written.add(k.lower())
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
                written.add(hit.lower())
                continue
            if k.lower() in written:
                continue                 # a later copy of a key we just wrote -- the engine would obey IT
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
    Returns the backup path (None if the ini didn't exist -- refuse in that case). A refused update
    (a control character in a key or value -- :func:`_check_ini_pair`) raises BEFORE the backup, so
    a rejected write leaves no trace on disk at all, not even a stray snapshot."""
    ini = _ini_path(game)
    if not ini.is_file():
        raise FileNotFoundError(f"{ini} not found -- is this really the FF9 install "
                                "(and is Memoria set up)?")
    text = read_ini_text(ini)
    new_text = update_ini_section(text, "Netsync", updates)   # vets every pair before we touch the disk
    backup = _backup_ini(ini)
    fsutil.atomic_write_text(ini, new_text, encoding=ini_write_encoding(ini))
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


def warn_split_mod_section(text: str, *, out=print) -> bool:
    """Say so when ``[Mod]`` lists FolderNames more than once -- the fingerprint of the pre-fix BOM bug (THE BOM LAW,
    :func:`read_ini_text`), which appended a second ``[Mod]`` holding only "FF9Coop". The game obeys the LAST copy, so
    every other mod is off until it is merged back. True when it warned. Read-only: the original list is the first copy
    (and in every ``Memoria.ini.coop-bak-*`` backup)."""
    if "FolderNames" not in duplicate_ini_keys(text, "Mod"):
        return False
    out("  ! Memoria.ini lists [Mod] FolderNames more than once -- the game loads ONLY the last list "
        f"({read_ini_key(text, 'Mod', 'FolderNames')}). An older co-op setup could write that second list; your original "
        "mod list is the first one (and in the Memoria.ini.coop-bak-* backups). Merge them into one [Mod] FolderNames "
        "line, or re-run the Memoria launcher's mod manager.")
    return True


def ensure_folder_registered(game: Path, folder: str, *, out=print) -> bool:
    """Add ``folder`` to ``[Mod] FolderNames`` (at the END -- the room's assets are uniquely named, and
    last place keeps its text block from shadowing other folders'). True if the ini was changed.
    Writes FolderNames AND Priorities together (:func:`mod_order_updates` -- the launcher reverts a
    FolderNames-only edit at the next Play click). Backs the ini up first, same as :func:`write_netsync`
    -- this is the FIRST ini mutation of a default `coop host`/`coop join` run."""
    ini = _ini_path(game)
    text = read_ini_text(ini)
    warn_split_mod_section(text, out=out)
    names = read_folder_names(text)
    if any(n.lower() == folder.lower() for n in names):
        return False
    updates = mod_order_updates(text, names + [folder])
    backup = _backup_ini(ini)
    fsutil.atomic_write_text(ini, update_ini_section(text, "Mod", updates), encoding=ini_write_encoding(ini))
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
    text = read_ini_text(ini)
    needle = f"FieldScene {field_id} "
    for folder in read_folder_names(text) + [COOP_MOD]:
        dp = game / folder / "DictionaryPatch.txt"
        try:
            if dp.is_file() and needle in dp.read_text(encoding="utf-8-sig", errors="replace"):
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
    text = read_ini_text(ini)
    key = lambda k, d="": (read_ini_key(text, "Netsync", k) or d).strip()
    enabled = key("Enabled") == "1"
    out(f"FF9 install: {game}")
    dupes = duplicate_ini_keys(text, "Netsync")
    if dupes:
        # Everything below reports the LAST copy (what the engine obeys), so the numbers are right --
        # but a duplicated key means someone or something appended a second [Netsync] block, and the
        # earlier lines the user can see are dead. Worth naming before they debug the wrong ones.
        out(f"  ! [Netsync] lists {', '.join(dupes)} more than once -- the LAST copy is the one the "
            "game uses; the earlier lines do nothing (re-run  ff9mapkit coop host|join  to tidy it)")
    warn_split_mod_section(text, out=out)
    out(f"  co-op:       {'ON' if enabled else 'off'}")
    if not enabled:
        out("  (start one with  ff9mapkit coop host  /  ff9mapkit coop join <code>)")
        return 0
    role = key("Role", "host")
    relay = key("RelayUrl")
    target = key("TargetField", "0") or "0"
    out(f"  role:        {role}" + ("  (selftest = solo mirror)" if role not in ("host", "client") else ""))
    out(f"  transport:   " + (f"relay via {relay}" if relay else f"direct LAN ({key('PeerAddress') or 'listening'})"))
    session = key("SessionCode")
    out(f"  session:     {session or '(no code)'}"
        + ("  (the host's code you joined with)" if role.lower() == "client" and session else ""))
    # [ff9mapkit s154] THE OWN-CODE LAW: on a guest PC SessionCode is the FRIEND's code -- say which code is this PC's own
    # (and on a host whose HostSessionCode differs from what it dials: the next `coop host` goes back to the own one)
    own = own_host_code(text)[0]
    if own and (role.lower() != "host" or own.upper() != session.upper()):
        out(f"  your code:   {own}  (what `coop host` uses -- a code you join with never replaces it)")
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
    # [ff9mapkit netsync s140] the guest's own dress opt-out (default 1: an s140+ guest wears what its host's GhostAs
    # names); named only when switched off -- there is no kit writer for it (hand-edited)
    if key("SelfDress", "1").strip('"').strip() == "0":
        out("  self-dress:  OFF ([Netsync] SelfDress=0 -- as a guest my own body stays Zidane on my screen; the "
            "host's ghost of me still follows ITS GhostAs)")
    out(f"  follow-host: " + ("ON (auto-warp + encounter pause; their battles boot live on my "
                              "screen)" if key("FollowHost") == "1" else "off"))
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


def _bridge_options(args) -> dict:
    """The bridge's T1 knobs off a parsed ``coop`` namespace (absent attrs = defaults)."""
    return {"hang_dump": bool(getattr(args, "hang_dump", False)),
            "hang_dump_dir": getattr(args, "hang_dump_dir", None),
            "hang_after": getattr(args, "hang_after", None),
            "log_path": getattr(args, "bridge_log", None)}


def _bridge_flags_text(args) -> str:
    """The bridge flags this run was given, re-spelled for the ``--no-bridge`` hint -- so the bridge started
    later keeps the same relay, hang-dump arming and log file (a value with a space is double-quoted)."""
    parts = []
    for flag, attr in (("--relay", "relay"), ("--hang-dump-dir", "hang_dump_dir"),
                       ("--hang-after", "hang_after"), ("--bridge-log", "bridge_log")):
        value = getattr(args, attr, None)
        if value is None or value == "":
            continue
        text = f"{value:g}" if isinstance(value, float) else str(value)
        parts.append(f'{flag} "{text}"' if " " in text else f"{flag} {text}")
    for flag, attr in (("--insecure", "insecure"), ("--hang-dump", "hang_dump")):
        if getattr(args, attr, False):
            parts.append(flag)
    return "".join(" " + p for p in parts)


def _run_bridge_foreground(port: int, relay: str | None, insecure: bool, *, out=print,
                           hang_dump: bool = False, hang_dump_dir: str | None = None,
                           hang_after: float | None = None, log_path: str | None = None) -> int:
    from . import netsync_bridge as nb
    # T1: every bridge line is wall-clock stamped and teed to a per-run log file; a game hop silent
    # for --hang-after seconds is logged, and -- only with --hang-dump / FF9_HANG_DUMP=1 -- dumped.
    hang = nb.hangdump.HangDumper.from_options(flag=hang_dump, dump_dir=hang_dump_dir,
                                               after_s=hang_after, log=nb._late_log)
    relay_url = relay or nb.default_relay()
    session_log = nb.open_session_log(log_path)
    try:
        server, thread = nb.run_server("127.0.0.1", port, relay_url, insecure, hang=hang)
    except BaseException:
        nb.close_session_log()
        raise
    out(f"  bridge: running on ws://127.0.0.1:{port} -- leave this window open while you play "
        "(Ctrl+C to stop)")
    if session_log:
        out(f"  bridge log: {session_log}")
    out(f"  {hang.describe()}")
    try:
        while thread.is_alive():
            thread.join(timeout=1.0)
    except KeyboardInterrupt:
        out("  bridge: stopped")
    finally:
        server.close()
        nb.close_session_log()
    return 0


def _setup(args, role: str, code: str | None, *, out=print) -> int:
    game = find_game_path(args.game)
    out(f"FF9 install: {game}")

    # validate the play-style flags and the pasted code FIRST -- a typo must not cost the
    # minute-long room build, and a code carrying a newline must never reach write_netsync
    # (it would splice extra [Netsync] keys into the ini -- see validate_code)
    follow = getattr(args, "follow_host", None)
    try:
        style = playstyle_updates(getattr(args, "guest_slots", None),
                                  getattr(args, "guest_wait", None),
                                  getattr(args, "ghost_as", None),
                                  None if follow is None else follow == "on",
                                  role="host" if role == "host" else "client")
        if code:                      # empty/None = none given (host mints, LAN join needs none)
            validate_code(code)
        if getattr(args, "hang_after", None) is not None:      # a bad --hang-after fails HERE, not
            from .hangdump import HangDumper                     # after the room build + ini write
            HangDumper.from_options(after_s=args.hang_after)
    except ValueError as e:
        out(f"  {e}")
        return 2

    lan = getattr(args, "lan", None)
    target = int(getattr(args, "field", None) or 0)      # 0 = co-op EVERYWHERE; --field N restricts
    if not getattr(args, "no_room", False):
        # the co-op room stays the guaranteed meeting spot (both installs are certain to have it)
        ensure_room(game, rebuild=getattr(args, "rebuild_room", False), out=out)

    ini_text = read_ini_text(_ini_path(game))
    # [ff9mapkit s154] THE OWN-CODE LAW (own_host_code): which stored code is THIS PC's own. SessionCode alone cannot say
    # -- after `coop join` it holds the friend's invite, and re-reading it here re-published that invite as this PC's
    # session. Every branch that declines a stored value says why, once, in this run's output.
    own, own_why, own_key = own_host_code(ini_text)
    stored = (read_ini_key(ini_text, "Netsync", "SessionCode") or "").strip()
    last_role = (read_ini_key(ini_text, "Netsync", "Role") or "").strip().lower()
    adopted = False                                   # a pre-s154 host's stored code taken as its own (the caveat)
    # an explicit `coop host <code>` naming a code this PC JOINED with: dialled this run, never recorded as the own code
    joined_explicit = role == "host" and joined_override(code, ini_text)
    own_after = None                                  # the own code such a run keeps (or mints, never published)
    if role == "host" and not code:
        if not getattr(args, "new_code", False):
            if own_why == "unusable":
                # A stored code we can't vouch for (hand-edited, or left behind by a poisoned ini) is
                # treated as ABSENT -- minting a fresh one keeps the host's setup working instead of
                # dying on a line they didn't write, and stops a bad value being re-written verbatim.
                out(f"  ignoring the stored {own_key} {read_ini_key(ini_text, 'Netsync', own_key)!r} -- not a usable "
                    "code, minting a new one")
            elif own_why == "joined":
                out(f"  not reusing {stored!r} as your host code: this PC joined a session with it (it is the code a "
                    "host gave you) -- minting your own")
            elif own_why == "unowned":
                role_said = f"Role is {last_role!r}" if last_role else "Role is not set"
                out(f"  not reusing the stored SessionCode {stored!r} as your host code: no `coop host` wrote it "
                    f"([Netsync] {role_said}; only a host's own code is reused) -- minting your own")
            code = own
            adopted = own_why == "migrated"
        code = code or generate_code()
    elif joined_explicit:
        # an EXPLICIT code is honoured (`coop host <code>` is a documented override) -- but say what it is, and keep it
        # THIS run's: the own code stays (or is minted now, never published), so the note's advice is true and a repeat
        # of the same command (Role reads host by then) is caught too (joined_override)
        own_after = own or generate_code()
        what = ("is the code this PC last JOINED with (a host gave it to you)" if last_role == "client" else
                f"is not this PC's own code ({own}) -- most likely a code a host gave you, dialled by an earlier "
                f"`coop host {code}`")
        out(f"  note: {code} {what}: hosting on it shares their session code, this run only -- your own code is "
            f"{own_after} ([Netsync] {HOST_CODE_KEY}); leave the code off to host on it")

    updates = {
        "Enabled": "1",
        "Role": "host" if role == "host" else "client",
        "TargetField": str(target),
        "SessionCode": code or "",
    }
    kept = None                                      # the one-time migration's line, said once the ini write landed
    if role == "host":
        # explicit, minted or kept alike: the code this PC hosts on -- EXCEPT a joined override, which dials the
        # friend's code but keeps the own one (writing nothing is not safe: with Role host and SessionCode the invite, a
        # missing key reads 'migrated' and the next bare `coop host` would adopt the invite)
        updates[HOST_CODE_KEY] = own_after if joined_explicit else code
        if adopted:
            kept = (f"  adopting your stored session code {code} as your own ([Netsync] {HOST_CODE_KEY}); "
                    + MIGRATION_CAVEAT)
    elif own_why == "migrated":
        # a pre-s154 host about to join: keep its own code before the invite (or a LAN join's blank) replaces it
        updates[HOST_CODE_KEY] = own
        kept = (f"  keeping your own session code {own} as [Netsync] {HOST_CODE_KEY} (joining sets SessionCode to the "
                "host's code); " + MIGRATION_CAVEAT)
    if lan is not None:
        updates["RelayUrl"] = ""                     # blank -> the proven direct-TCP transport
        if role != "host":
            updates["PeerAddress"] = lan
    else:
        updates["RelayUrl"] = f"ws://127.0.0.1:{args.port}"
    updates.update(style)
    if role == "host":
        updates["FollowHost"] = "0"                  # a host never follows its guest -- FollowHost fires
                                                     # regardless of role, so a stale value would drag the
                                                     # host to the guest's field (playstyle_updates already
                                                     # refused an explicit --follow-host on)
    write_netsync(game, updates, out=out)
    if kept:
        out(kept)
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
        if role != "host" and gv:
            # [ff9mapkit netsync s140] the guest DRESSES ITSELF from the host's GhostAs; a guest-side value only re-dresses
            # the guest's own view of the HOST (the s138 client rule, kept byte for byte) -- the same pick on both
            # machines shows the guest two of that character, and the two screens disagree about who the host is
            out("  visitor: NOTE -- on an s140+ engine you already wear what the HOST's GhostAs names (your own "
                "[Netsync] SelfDress=0 opts out). A GhostAs on your side re-dresses only YOUR view of the host (the 8 "
                "mains): the same pick on both machines shows you two of that character. Normally leave it 'off' "
                "when joining (`--ghost-as off`).")
    if "FollowHost" in style:
        out("  visitor: follow-host " + ("ON -- your game auto-warps to their field, your random "
                                         "encounters pause while paired, and their battles boot "
                                         "live on your screen"
                                         if style["FollowHost"] == "1" else "off"))

    out("")
    if role == "host":
        clip = " (copied to clipboard)" if _copy_clipboard(code) else ""
        out(f"  session code:  {code}{clip}")
        out(f"  send it to your friend -- they run:  ff9mapkit coop join {code}")
    else:
        out(f"  joining session {code}")
    if target:
        out(f"  then: launch FF9 -> ~ -> Warp to field -> {target}   (both players)")
    elif role == "host":
        out("  then: launch FF9 and load your save -- a following guest is pulled to whatever screen you are on")
    else:
        out("  then: launch FF9 and load any save -- with follow-host on, your game jumps to the host's screen "
            "once you pair (your own save is never touched); without it, you see each other on a shared "
            f"screen (always-shared spot: ~ -> Warp -> {COOP_FIELD})")
    if lan is not None:
        # Windows' generic "Allow access" prompt ticks Private AND Public by default; clicking
        # through it on a cafe/hotel/campus network exposes the co-op listener to that whole
        # network, so name the profile explicitly rather than saying "allow it".
        out("  direct-LAN mode: no bridge needed. Same WiFi; allow FF9 through the firewall on both.")
        out("  in that Windows prompt untick Public and leave Private ticked -- Public opens the "
            "co-op listener to every machine on a cafe or campus network.")
        return 0
    out("")
    if getattr(args, "no_bridge", False):
        out(f"  --no-bridge: start it later with  ff9mapkit coop bridge --port {args.port}{_bridge_flags_text(args)}")
        return 0
    return _run_bridge_foreground(args.port, getattr(args, "relay", None),
                                  getattr(args, "insecure", False), out=out, **_bridge_options(args))


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
                                      getattr(args, "insecure", False), out=out, **_bridge_options(args))
    out(f"unknown coop action: {action}")
    return 2
