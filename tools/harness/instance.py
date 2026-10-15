#!/usr/bin/env python3
# Windows-first tool: invoke via the py launcher --  py tools/harness/instance.py <verb> <root>
"""Instance roots: a second (third, ...) FF9 on this machine, each run from its own junctioned root.

!! TEAR A ROOT DOWN ONLY WITH :meth:`Instance.teardown` (``py tools/harness/instance.py teardown <root>``). A recursive
!! delete that follows the junctions -- PowerShell 5.1's ``Remove-Item -Recurse``, ``rmdir /s``, Explorer -- deletes the
!! REAL install's StreamingAssets and mod folders.

    py tools/harness/instance.py ensure   <root>    # build it if absent, else refresh: repair every drift (claimed)
    py tools/harness/instance.py verify   <root>    # read-only: every junction, every copy, the ini [--deep: sha256]
    py tools/harness/instance.py teardown <root>    # THE TEARDOWN LAW (claimed; refuses while its game runs)
    py tools/harness/instance.py pids     <root>    # the FF9.exe processes running FROM this root, and only those
    py tools/harness/instance.py status   [root...] # claim + running pids + verify, for every root under the home

Drive one with the harness: ``py tools/play.py --smoke --field 30602 --instance C:\\gd\\ff9-inst\\guest``, or
``Session(instance=...)``; two at once, paired over a local relay: :mod:`harness.duo`.

WHY A ROOT AND NOT A SECOND LAUNCH (studies/test-harness/multi-instance/RECON.md, probes P0-P4). Nothing in FF9, Unity
5.2.3, Memoria or Steam forbids a second process; the limits are paths. Memoria.ini, Memoria.log, StreamingAssets, the
root FF9_Data and the mod folders resolve against the process WORKING DIRECTORY, and the harness channel + save sandbox
against the EXE's directory (``Application.dataPath/../ff9harness``). Same cwd = the second game HANGS on Memoria.log
(P0); same exe dir = a shared channel. So a root is a REAL directory outside the Steam folder holding:

* junctions (no admin needed) for the big read-only trees: ``StreamingAssets``, the root ``FF9_Data``, one per ``[Mod]
  FolderNames`` entry named EXACTLY as in the ini (the Scripts loader derives its DLL name from the folder name), and
  ``x64\\FF9_Data\\{Managed,Mono,Plugins,Resources}`` -- so an engine rebuild reaches every instance at once;
* COPIES (never hardlinks: no file shares an inode with the install) of everything beside the exe -- ``x64\\FF9.exe``
  and its DLLs, the ~59 ``x64\\FF9_Data`` data files -- and ``Settings.ini``;
* its OWN ``Memoria.ini``: the install's, with :func:`base_overlay` on top (Netsync OFF and parked away from the owner's
  bridge port and session code, gamepad capture off, the SfxProbe off). The engine rewrites it in place (SessionCode
  write-back) and hot-reloads it by mtime, so it is a real copy, regenerated from the install at every refresh.

THE LAWS (each one cost a probe or is a hazard to the owner's install):

* **THE TEARDOWN LAW.** ``os.rmdir`` every reparse point in the root FIRST, prove none is left, only then delete the real
  files -- with a walker that never descends into a reparse point (``DirEntry.is_dir()`` is TRUE for a junction, so a
  naive walk would). A root carries a marker file; nothing without one is ever torn down.
* **THE CLAIM.** A root is claimed (``.ff9-instance.claim``) by whoever refreshes, tears down or runs it, and every
  mutation also refuses while an FF9.exe runs FROM the root (a path-scoped probe: QueryFullProcessImageNameW). An image
  path that cannot be read counts as "might be ours": refuse, never guess.
* **ARMED LAUNCHES ONLY.** An unarmed instance calls SteamAPI_RestartAppIfNecessary, quits, and Steam starts the REAL
  install. The harness writes the arm before every launch; never start a root's exe by hand.
* **NOTHING POINTS AT A ROOT** but the harness: a deploy or ``FF9_GAME_PATH`` aimed at one writes THROUGH the junctions.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import uuid
import weakref
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
if __package__ in (None, ""):                         # run as a script: make `harness` importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from harness.channel import HarnessError, pid_alive          # noqa: E402
else:
    from .channel import HarnessError, pid_alive                 # noqa: E402

#: Where instance roots live by default -- a REAL directory on the install's drive, outside the Steam folder.
INSTANCES_HOME = Path(os.environ.get("FF9_INSTANCES_HOME", r"C:\gd\ff9-inst"))

GAME_EXE = "FF9.exe"
#: Copied beside the exe (x64\). The exe must be a COPY: Application.dataPath follows it, and with it the harness
#: channel and the save sandbox.
EXE_FILES = ("FF9.exe", "steam_api64.dll", "XAudio2_9.dll", "msvcp120.dll", "msvcr100.dll", "msvcr120.dll")
#: x64\FF9_Data subdirectories that are JUNCTIONED (an engine rebuild reaches every instance; a frozen Managed copy would
#: pair mixed DLLs). Every other FILE in x64\FF9_Data is copied.
DATA_DIRS = ("Managed", "Mono", "Plugins", "Resources")
#: Root-level junctions besides the mod folders. Never ``FontList`` (the game writes it on every boot).
ROOT_LINKS = ("StreamingAssets", "FF9_Data")
#: Files of x64\FF9_Data that are never copied -- the game writes them per launch.
NEVER_COPY = frozenset({"output_log.txt"})
MARKER = ".ff9-instance.json"
CLAIM = ".ff9-instance.claim"
#: The [Netsync] RelayUrl a root boots with: the discard port, where nothing listens. The install's own value is the
#: owner's bridge (ws://127.0.0.1:49201), and a root that inherited it -- and its live SessionCode -- would evict the
#: laptop's leg on the public relay the moment anyone set Enabled=1 on it.
PARKED_RELAY = "ws://127.0.0.1:9"
#: How many trailing characters of the exe's canonical path FF9's ``-single-instance`` mutex is keyed on
#: (GetModuleFileNameW + PathCanonicalizeW, then non-alphanumerics -> '-': RECON.md doubt 1).
SINGLE_INSTANCE_TAIL = 30
#: A copy whose mtime is this close to its source's (and whose size matches) is the same file for the per-launch check.
#: copy2 keeps the 100 ns NTFS stamp, so this is slack, not precision; ``verify(deep=True)`` compares sha256.
MTIME_SLACK_S = 2.0

_FILE_ATTRIBUTE_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

#: Claim nonce -> the Instance object in THIS process holding it (weakly). A claim file naming this pid whose nonce maps
#: to a live holder is a live sibling -- e.g. a duo given the same root twice (refuse); any other same-pid claim is a
#: dead object's leak (adopt it).
_LIVE_CLAIMS: "weakref.WeakValueDictionary" = weakref.WeakValueDictionary()


class InstanceError(HarnessError):
    """A root cannot be built, refreshed, verified or torn down as asked -- nothing unsafe was done. A HarnessError, so
    every harness front end (play.py, duo.py) reports it as one."""


class InstanceBusy(InstanceError):
    """The root is claimed by another live run, or its game is running."""


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def _say(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------------------------- processes
def _default_procs() -> list:
    from ff9mapkit.hangdump import list_processes
    return list_processes()


def _default_image_of(pid: int) -> str:
    from ff9mapkit.hangdump import process_image_path
    return process_image_path(pid)


def _same_path(a, b) -> bool:
    try:
        ra, rb = os.path.realpath(a), os.path.realpath(b)
    except (OSError, ValueError):
        ra, rb = os.path.abspath(a), os.path.abspath(b)
    return os.path.normcase(os.path.normpath(ra)) == os.path.normcase(os.path.normpath(rb))


def scan_game(exe, *, procs=None, image_of=None) -> tuple[list[int], list[int], list[int]]:
    """``(mine, others, unknown)``: running FF9.exe pids whose image IS ``exe``, whose image is another path, and whose
    image could not be read. The path-scoped probe every multi-instance decision rests on -- the default harness probe
    (:func:`harness.session.ff9_pids`) answers "any FF9 at all", which is right for the shared install and wrong for a
    root. ``procs`` (a callable returning ``[(pid, basename)]``) and ``image_of`` are the test seams."""
    procs = procs or _default_procs
    image_of = image_of or _default_image_of
    mine, others, unknown = [], [], []
    for pid, name in procs():
        if str(name).lower() != GAME_EXE.lower():
            continue
        try:
            image = image_of(pid)
        except OSError:
            unknown.append(int(pid))
            continue
        (mine if _same_path(image, exe) else others).append(int(pid))
    return mine, others, unknown


def pids_at(exe, **seams) -> list[int]:
    """The FF9.exe pids running from ``exe`` -- and only those (see :func:`scan_game`)."""
    return scan_game(exe, **seams)[0]


def single_instance_key(exe) -> str:
    """The name FF9's ``-single-instance`` mutex takes for ``exe``: the last 30 characters of its canonical path, every
    non-alphanumeric turned into '-'. Two exes whose keys match cannot both run with the flag -- the second exits 0 in
    ~0.4 s (P0b), which a driver reads as "the game exited during boot"."""
    p = os.path.normpath(os.path.abspath(str(exe)))
    return re.sub(r"[^0-9A-Za-z]", "-", p[-SINGLE_INSTANCE_TAIL:])


def single_instance_clash(exe, others) -> list[str]:
    """The paths among ``others`` whose mutex key equals ``exe``'s (case-insensitively: the conservative reading).
    Empty = the stock ``-single-instance`` flag is safe for ``exe``, and worth keeping -- it turns a same-root double
    launch into a fast exit 0 instead of a hang on Memoria.log (P0)."""
    mine = single_instance_key(exe).lower()
    return [str(o) for o in others if not _same_path(o, exe) and single_instance_key(o).lower() == mine]


# --------------------------------------------------------------------------------------------- reparse points
def _is_reparse(p) -> bool:
    """A junction, a symlink or any other reparse point -- never followed, never recursed into."""
    try:
        st = os.lstat(p)
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & _FILE_ATTRIBUTE_REPARSE_POINT)


def _is_junction(p) -> bool:
    return bool(getattr(os.path, "isjunction", lambda _p: False)(p))


def _entry_reparse(e: os.DirEntry) -> bool:
    try:
        if e.is_symlink() or (hasattr(e, "is_junction") and e.is_junction()):
            return True
        return bool(getattr(e.stat(follow_symlinks=False), "st_file_attributes", 0) & _FILE_ATTRIBUTE_REPARSE_POINT)
    except OSError:
        return True                                  # cannot tell: treat as a link -- never descend into it


def walk_no_follow(top):
    """``(dir, subdirs, files, reparse)`` for ``top`` and every REAL directory under it, top-down. A reparse point is
    reported in ``reparse`` and never entered: ``os.walk`` decides recursion with ``is_dir()``, which is TRUE for a
    junction on Windows -- the exact descent into the install the teardown law forbids."""
    stack = [Path(top)]
    while stack:
        d = stack.pop()
        dirs, files, reparse = [], [], []
        with os.scandir(d) as it:
            for e in it:
                if _entry_reparse(e):
                    reparse.append(Path(e.path))
                elif e.is_dir(follow_symlinks=False):
                    dirs.append(Path(e.path))
                else:
                    files.append(Path(e.path))
        yield d, dirs, files, reparse
        stack.extend(reversed(dirs))


def make_junction(link, target) -> None:
    """Create the junction ``link`` -> ``target`` (no admin needed). Raises InstanceError if it did not come out one."""
    link, target = Path(link), Path(target)
    try:
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
    except (ImportError, AttributeError, OSError) as err:
        import subprocess
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, text=True)
        if r.returncode != 0:
            raise InstanceError(f"could not create the junction {link} -> {target} ({err}; mklink: "
                                f"{(r.stdout + r.stderr).strip()})") from err
    if not _is_junction(link):
        raise InstanceError(f"{link} did not come out a junction")


def remove_link(p) -> None:
    """Remove ONE reparse point -- the link, never what it points at. A junction or directory symlink goes with
    ``os.rmdir`` (RemoveDirectoryW on a reparse point removes the point), a file symlink with ``os.unlink``. Anything
    else (a non-link reparse point: a cloud placeholder, a dedup stub) is refused."""
    p = Path(p)
    st = os.lstat(p)
    is_link = stat.S_ISLNK(st.st_mode)
    if os.name != "nt" and is_link:
        os.unlink(p)                                 # POSIX: every symlink is unlinked, a directory one included
    elif _is_junction(p) or (is_link and getattr(st, "st_file_attributes", 0) & 0x10):   # FILE_ATTRIBUTE_DIRECTORY
        os.rmdir(p)
    elif is_link:
        os.unlink(p)
    else:
        raise InstanceError(f"{p} is a reparse point that is neither a junction nor a symlink -- refusing to touch it")


# --------------------------------------------------------------------------------------------- files
def sha256(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_text(p) -> str:
    """The ini as text, byte-faithfully: no newline translation (CRLF stays CRLF), undecodable bytes kept."""
    with open(p, "r", encoding="utf-8", errors="surrogateescape", newline="") as f:
        return f.read()


def _write_text(p, text: str, *, tries: int = 25, wait: float = 0.1) -> None:
    """Atomic (a sibling .tmp + os.replace), retried: on Windows os.replace onto a file another process has open for
    reading -- the engine's ini hot-reload poll, an AV scan, a tool reading it -- fails with WinError 5 for that moment
    (measured: a reader thread made a restore fail). A bounded retry, then the error."""
    import time
    p = Path(p)
    tmp = p.with_name(p.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
            f.write(text)
        for attempt in range(tries):
            try:
                os.replace(tmp, p)
                break
            except PermissionError:
                if attempt == tries - 1:
                    raise
                time.sleep(wait)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise


def _copy_ok(dst: Path, src: Path) -> bool:
    try:
        d, s = dst.stat(), src.stat()
    except OSError:
        return False
    return dst.is_file() and d.st_size == s.st_size and abs(d.st_mtime - s.st_mtime) <= MTIME_SLACK_S


def parked_code(root) -> str:
    """The SessionCode a root boots with: ``ff9-`` + 8 (GenerateSessionCode's shape), derived from the root's path, so
    stable per root and never anyone's live code."""
    h = hashlib.sha1(os.path.normcase(str(Path(root).resolve())).encode("utf-8")).hexdigest().upper()
    return "ff9-I" + h[:7]


def base_overlay(root) -> dict[str, dict[str, str]]:
    """What a root's Memoria.ini changes from the install's: Netsync OFF and parked (:data:`PARKED_RELAY`, a code of its
    own); gamepad capture OFF -- with it ON a pad press reaches even an UNFOCUSED FF9, which is what paused a P3 host;
    the SfxProbe off. A co-op run writes its [Netsync] role through :meth:`Instance.netsync` and restores this after."""
    return {
        "Netsync": {"Enabled": "0", "RelayUrl": PARKED_RELAY, "SessionCode": parked_code(root)},
        "Control": {"AlwaysCaptureGamepad": "0"},
        "SfxProbe": {"Enabled": "0"},
    }


def overlay_text(text: str, overlay: dict) -> str:
    """``text`` with every ``[section] key = value`` of ``overlay`` written the way the kit writes Memoria.ini
    everywhere (:func:`ff9mapkit.coop.update_ini_section`: last-wins duplicates collapsed, newline style kept)."""
    from ff9mapkit.coop import update_ini_section
    for section, updates in overlay.items():
        text = update_ini_section(text, section, updates)
    return text


@dataclass
class Plan:
    """What a root must hold, read from the install as it is NOW (FolderNames can grow between launches)."""
    links: dict = field(default_factory=dict)            # junction path -> its target in the install
    copies: dict = field(default_factory=dict)           # copy path -> its source in the install
    ini_src: Path | None = None
    ini_dst: Path | None = None


# --------------------------------------------------------------------------------------------- the root
class Instance:
    """One instance root. Cheap to construct (reads nothing); every mutation is claimed and refuses while its game runs.

    ``procs`` / ``image_of`` are the process-probe seams (see :func:`scan_game`); ``others`` are the exes this root's
    ``-single-instance`` key must not collide with (default: the install's and every sibling root's under the home).
    """

    def __init__(self, root, *, install=None, label: str | None = None, log=None, procs=None, image_of=None,
                 others=None):
        self.root = Path(os.path.abspath(str(root)))
        if install is None:
            from ff9mapkit.config import find_game_path
            install = find_game_path()
        self.install = Path(os.path.abspath(str(install)))
        self.label = label or self.root.name
        self._log_fn = log
        self._procs = procs
        self._image_of = image_of
        self._others = others
        self._nonce: str | None = None                  # our claim's nonce while we hold it
        self._claim_depth = 0

    def __repr__(self) -> str:
        return f"Instance({str(self.root)!r}, install={str(self.install)!r})"

    def _log(self, msg: str) -> None:
        (self._log_fn or _say)(f"[instance {self.label}] {msg}")

    # -- where things are ------------------------------------------------------------------------
    @property
    def exe(self) -> Path:
        return self.root / "x64" / GAME_EXE

    @property
    def channel_dir(self) -> Path:
        return self.root / "x64" / "ff9harness"

    @property
    def ini(self) -> Path:
        return self.root / "Memoria.ini"

    @property
    def marker(self) -> Path:
        return self.root / MARKER

    @property
    def claim_path(self) -> Path:
        return self.root / CLAIM

    def folder_names(self) -> list[str]:
        """The install's ``[Mod] FolderNames``, as the engine reads them (last key wins)."""
        from ff9mapkit.coop import read_folder_names
        try:
            return read_folder_names(_read_text(self.install / "Memoria.ini"))
        except OSError:
            return []

    def plan(self) -> Plan:
        inst = self.install
        if not (inst / "x64" / GAME_EXE).is_file():
            raise InstanceError(f"{inst} is not an FF9 install (no x64\\{GAME_EXE})")
        names = list(ROOT_LINKS) + [f for f in self.folder_names() if f not in ROOT_LINKS]
        links = {self.root / n: inst / n for n in names if (inst / n).is_dir()}
        links.update({self.root / "x64" / "FF9_Data" / d: inst / "x64" / "FF9_Data" / d
                      for d in DATA_DIRS if (inst / "x64" / "FF9_Data" / d).is_dir()})
        copies = {}
        if (inst / "Settings.ini").is_file():
            copies[self.root / "Settings.ini"] = inst / "Settings.ini"
        for f in EXE_FILES:
            if (inst / "x64" / f).is_file():
                copies[self.root / "x64" / f] = inst / "x64" / f
        data = inst / "x64" / "FF9_Data"
        if data.is_dir():
            for p in sorted(data.iterdir()):
                if p.is_file() and not _is_reparse(p) and p.name not in NEVER_COPY:
                    copies[self.root / "x64" / "FF9_Data" / p.name] = p
        return Plan(links, copies, inst / "Memoria.ini", self.ini)

    def overlay(self) -> dict:
        return base_overlay(self.root)

    def wanted_ini(self) -> str:
        return overlay_text(_read_text(self.install / "Memoria.ini"), self.overlay())

    # -- processes ---------------------------------------------------------------------------------
    def scan(self) -> tuple[list[int], list[int], list[int]]:
        return scan_game(self.exe, procs=self._procs, image_of=self._image_of)

    def pids(self) -> list[int]:
        """The FF9.exe pids running FROM this root (the Session's pid probe in instance mode)."""
        return self.scan()[0]

    def assert_not_running(self, why: str) -> None:
        mine, _others, unknown = self.scan()
        if mine:
            raise InstanceBusy(f"refusing to {why}: its game is running from {self.exe} (pid {mine[0]})")
        if unknown:
            raise InstanceBusy(f"refusing to {why}: FF9.exe pid(s) {unknown} have an image path this account cannot read,"
                               f" so one of them may be running from {self.root} -- close them or run elevated")

    def other_exes(self) -> list[Path]:
        if self._others is not None:
            return [Path(o) for o in self._others]
        out = [self.install / "x64" / GAME_EXE]
        home = self.root.parent
        with contextlib.suppress(OSError):
            for d in home.iterdir():
                if d.is_dir() and not _is_reparse(d) and (d / MARKER).is_file() and not _same_path(d, self.root):
                    out.append(d / "x64" / GAME_EXE)
        return out

    def single_instance_clash(self) -> list[str]:
        return single_instance_clash(self.exe, self.other_exes())

    # -- the claim ---------------------------------------------------------------------------------
    def claim_owner(self) -> dict | None:
        try:
            body = self.claim_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        try:
            doc = json.loads(body)
        except ValueError:
            return {"pid": -1, "nonce": "?", "label": "?", "unreadable": body[:80]}
        return doc if isinstance(doc, dict) else None

    def claim(self, label: str = "run") -> str:
        """Take the root's claim (reentrant for this object). Raises InstanceBusy while another live run holds it.

        Atomic (O_CREAT|O_EXCL). A claim whose pid is dead -- or is THIS process with a nonce no live Instance here
        holds (a leak) -- is adopted; one this process's live sibling holds is refused like any other."""
        if self._nonce is not None:
            self._claim_depth += 1
            return self._nonce
        if not self.root.is_dir():
            raise InstanceError(f"{self.root} does not exist -- ensure() it first")
        nonce = uuid.uuid4().hex[:16]
        body = json.dumps({"pid": os.getpid(), "nonce": nonce, "label": label, "started": _now(),
                           "cwd": os.getcwd(), "tool": "tools/harness/instance.py"})
        for _attempt in range(3):
            try:
                fd = os.open(self.claim_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                owner = self.claim_owner() or {}
                pid = int(owner.get("pid", -1) or -1)
                holder = _LIVE_CLAIMS.get(owner.get("nonce") or "")
                live_here = pid == os.getpid() and holder is not None and holder.holds_claim
                if (pid > 0 and pid != os.getpid() and pid_alive(pid)) or live_here:
                    raise InstanceBusy(
                        f"{self.root} is claimed by pid {pid} ({owner.get('label')!r}, since {owner.get('started')}, "
                        f"from {owner.get('cwd')}). One root, one run: wait for it, or delete {self.claim_path} if "
                        f"you know that run is dead.") from None
                self._log(f"adopting a stale claim ({owner.get('label')!r}, pid {pid})")
                with contextlib.suppress(FileNotFoundError):
                    self.claim_path.unlink()
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(body)
            self._nonce, self._claim_depth = nonce, 1
            _LIVE_CLAIMS[nonce] = self
            return nonce
        raise InstanceBusy(f"could not take the claim on {self.root} (it kept reappearing)")

    def release(self) -> None:
        """Drop our claim (the outermost release removes the file, and only if it is still OURS)."""
        if self._nonce is None:
            return
        self._claim_depth -= 1
        if self._claim_depth > 0:
            return
        nonce, self._nonce = self._nonce, None
        _LIVE_CLAIMS.pop(nonce, None)
        owner = self.claim_owner()
        if owner is not None and owner.get("nonce") == nonce:
            with contextlib.suppress(OSError):
                self.claim_path.unlink()

    @contextlib.contextmanager
    def claimed(self, label: str = "run"):
        self.claim(label)
        try:
            yield self
        finally:
            self.release()

    @property
    def holds_claim(self) -> bool:
        return self._nonce is not None

    # -- shape guards ------------------------------------------------------------------------------
    def _assert_placement(self) -> None:
        """A root is never the install, inside it, above it, a drive root, or itself a reparse point."""
        r, inst = self.root, self.install
        if _same_path(r, inst) or any(_same_path(p, inst) for p in r.parents) or any(
                _same_path(p, r) for p in inst.parents):
            raise InstanceError(f"{r} overlaps the install {inst} -- a root must live OUTSIDE it")
        if len(r.parts) < 3:
            raise InstanceError(f"{r} is too shallow to be an instance root")
        if str(r).startswith("\\\\"):
            raise InstanceError(f"{r} is a network path -- junctions need a local volume")
        if r.exists() and _is_reparse(r):
            raise InstanceError(f"{r} is itself a junction/link -- refusing")

    def _looks_like_root(self) -> bool:
        """An unmarked directory that is unmistakably a root (the study prototype built two): a real x64\\FF9.exe, and
        every top-level reparse point a junction into THIS install."""
        if not (self.exe.is_file() and not _is_reparse(self.exe)):
            return False
        links = [p for p in self.root.iterdir() if _is_reparse(p)]
        if not links:
            return False
        for p in links:
            if not _is_junction(p):
                return False
            tgt = os.path.realpath(p)
            if not (_same_path(tgt, self.install) or any(_same_path(q, self.install) for q in Path(tgt).parents)):
                return False
        return True

    def _write_marker(self, how: str) -> None:
        doc = {"kind": "ff9-instance-root", "install": str(self.install), how: _now(),
               "tool": "tools/harness/instance.py"}
        try:
            old = json.loads(self.marker.read_text(encoding="utf-8"))
            if isinstance(old, dict):
                old.update(doc)
                doc = old
        except (OSError, ValueError):
            pass
        self.marker.write_text(json.dumps(doc, indent=1), encoding="utf-8")

    # -- build / refresh / verify -------------------------------------------------------------------
    def ensure(self, label: str = "ensure") -> list[str]:
        """Build the root if it is absent, else refresh it. Returns what was done (empty: it was already right)."""
        if not self.root.exists():
            return self.build()
        return self.refresh(label)

    def build(self) -> list[str]:
        self._assert_placement()
        if self.root.exists():
            raise InstanceError(f"{self.root} exists -- refresh() it, or teardown() first")
        pl = self.plan()
        (self.root / "x64" / "FF9_Data").mkdir(parents=True)
        self._write_marker("built")
        with self.claimed("build"):
            done = self._apply(pl, building=True)
        self._log(f"built {self.root}: {len(pl.links)} junctions, {len(pl.copies)} copies + Memoria.ini")
        return done

    def refresh(self, label: str = "refresh") -> list[str]:
        """Repair every drift against the install as it is now: missing junctions (a newly registered FolderNames
        entry), junctions pointing elsewhere, copies that differ (size/mtime -- a Steam update), and the ini (regenerated
        from the install + the overlay). Claimed; refuses while the root's game runs."""
        self._assert_placement()
        if not self.root.is_dir():
            raise InstanceError(f"{self.root} does not exist -- build() it")
        if not self.marker.is_file():
            if not self._looks_like_root():
                raise InstanceError(f"{self.root} has no {MARKER} and does not look like an instance root -- "
                                    f"refusing to touch it")
            self._write_marker("adopted")
            self._log(f"adopted an unmarked root (built before {MARKER} existed)")
        with self.claimed(label):
            self.assert_not_running("refresh it")
            done = self._apply(self.plan())
        if done:
            self._log("refreshed: " + "; ".join(done[:8]) + (f" (+{len(done) - 8} more)" if len(done) > 8 else ""))
        return done

    def _apply(self, pl: Plan, *, building: bool = False) -> list[str]:
        done = []
        for dst, src in pl.copies.items():
            if not _copy_ok(dst, src):
                if _is_reparse(dst):
                    raise InstanceError(f"{dst} is a link where a COPY belongs -- refusing")
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                if not building:
                    done.append(f"recopied {dst.relative_to(self.root)}")
        if building:
            done.append(f"{len(pl.copies)} copies")
        want = self.wanted_ini()
        try:
            have = _read_text(pl.ini_dst)
        except OSError:
            have = None
        if have != want:
            _write_text(pl.ini_dst, want)
            done.append("Memoria.ini " + ("written" if have is None else "regenerated (install + overlay)"))
        for link, target in pl.links.items():
            if os.path.lexists(link):
                if not _is_reparse(link):
                    raise InstanceError(f"{link} is a REAL directory or file where a junction to {target} belongs -- "
                                        f"refusing to delete it; move it aside by hand")
                if _same_path(link, target):
                    continue
                remove_link(link)
                make_junction(link, target)
                done.append(f"re-pointed {link.relative_to(self.root)} -> {target}")
            else:
                link.parent.mkdir(parents=True, exist_ok=True)
                make_junction(link, target)
                if not building:
                    done.append(f"linked {link.relative_to(self.root)} (new)")
        if building:
            done.append(f"{len(pl.links)} junctions")
        return done

    def verify(self, *, deep: bool = False) -> list[str]:
        """Every problem found, read-only (empty = the root is exactly what :meth:`plan` + the overlay say). ``deep``
        compares every copy by sha256 instead of size + mtime."""
        if not self.root.is_dir():
            return [f"{self.root} does not exist"]
        bad = []
        pl = self.plan()
        for link, target in pl.links.items():
            if not _is_reparse(link):
                bad.append(f"junction {link.relative_to(self.root)} MISSING" if not os.path.lexists(link) else
                           f"{link.relative_to(self.root)} is a real directory, not a junction")
            elif not _same_path(link, target):
                bad.append(f"junction {link.relative_to(self.root)} -> {os.path.realpath(link)} (want {target})")
        for dst, src in pl.copies.items():
            ok = (dst.is_file() and dst.stat().st_size == src.stat().st_size and sha256(dst) == sha256(src)) if deep \
                else _copy_ok(dst, src)
            if not ok:
                bad.append(f"copy {dst.relative_to(self.root)} differs from the install")
        try:
            if _read_text(pl.ini_dst) != self.wanted_ini():
                bad.append("Memoria.ini drifted from install + overlay (a co-op run's [Netsync], or the install moved)")
        except OSError:
            bad.append("Memoria.ini missing")
        if not self.marker.is_file():
            bad.append(f"no {MARKER} (unmarked root: ensure() adopts it)")
        return bad

    # -- the ini ------------------------------------------------------------------------------------
    def netsync(self, updates: dict, *, backup_to=None, out=None) -> Path | None:
        """Set ``[Netsync]`` keys in THIS root's Memoria.ini through the kit's own writer
        (:func:`ff9mapkit.coop.write_netsync`: pairs vetted, last-wins duplicates collapsed, backed up first). The
        backup it leaves beside the ini is moved into ``backup_to`` (a run dir) when given, so roots do not accumulate
        them. Never the install's ini: this writes ``<root>\\Memoria.ini`` only."""
        from ff9mapkit.coop import write_netsync
        if _same_path(self.root, self.install):
            raise InstanceError("netsync() on the install itself -- refusing")
        bak = write_netsync(self.root, dict(updates), out=out or (lambda m: self._log(m.strip())))
        if bak is not None and backup_to is not None:
            dest = Path(backup_to)
            dest.mkdir(parents=True, exist_ok=True)
            final = dest / f"{self.label}-{Path(bak).name}"
            shutil.move(str(bak), str(final))
            return final
        return bak

    def restore_ini(self) -> bool:
        """Put the root's Memoria.ini back to install + overlay (after a co-op run). True when it had to be rewritten."""
        want = self.wanted_ini()
        try:
            if _read_text(self.ini) == want:
                return False
        except OSError:
            pass
        _write_text(self.ini, want)
        return True

    # -- teardown -----------------------------------------------------------------------------------
    def teardown(self) -> dict:
        """THE TEARDOWN LAW. Remove every reparse point in the root with :func:`remove_link` (the link only), prove none
        is left, then delete the real files bottom-up -- with :func:`walk_no_follow`, which never enters a reparse point.
        Refuses without the marker, while claimed by another run, or while the root's game runs. Returns counts."""
        self._assert_placement()
        if not self.root.is_dir():
            raise InstanceError(f"{self.root} does not exist")
        if not self.marker.is_file():
            raise InstanceError(f"{self.root} has no {MARKER} -- not tearing down what this tool did not build "
                                f"(ensure() adopts a prototype root first)")
        with self.claimed("teardown"):
            self.assert_not_running("tear it down")
            links = 0
            for _d, _dirs, _files, reparse in walk_no_follow(self.root):
                for p in reparse:
                    remove_link(p)
                    links += 1
            left = [str(p) for _d, _dirs, _files, reparse in walk_no_follow(self.root) for p in reparse]
            if left:
                raise InstanceError(f"reparse points left after unlinking -- refusing to delete any file: {left}")
            files = dirs = 0
            levels = list(walk_no_follow(self.root))
            for d, subdirs, fs, reparse in reversed(levels):
                assert not reparse
                for f in fs:
                    os.remove(f)
                    files += 1
                for s in subdirs:
                    os.rmdir(s)
                    dirs += 1
            os.rmdir(self.root)
            _LIVE_CLAIMS.pop(self._nonce, None)             # the claim file went with the root
            self._nonce, self._claim_depth = None, 0
        self._log(f"torn down {self.root}: {links} links removed (targets untouched), {files} files, {dirs} dirs")
        return {"links": links, "files": files, "dirs": dirs}

    # -- status -------------------------------------------------------------------------------------
    def status(self, *, deep: bool = False) -> dict:
        mine, _others, unknown = self.scan() if self.root.is_dir() else ([], [], [])
        return {"root": str(self.root), "exists": self.root.is_dir(), "marker": self.marker.is_file(),
                "claim": self.claim_owner(), "running": mine, "unreadable_ff9": unknown,
                "problems": self.verify(deep=deep) if self.root.is_dir() else ["absent"],
                "single_instance_clash": self.single_instance_clash() if self.root.is_dir() else []}


def install_fingerprint(install, names=None) -> dict:
    """``{tree: [files, bytes, newest mtime]}`` for every junction target + the ini's sha -- what a teardown must leave
    untouched (P1's check)."""
    install = Path(install)
    if names is None:
        from ff9mapkit.coop import read_folder_names
        names = list(ROOT_LINKS) + read_folder_names(_read_text(install / "Memoria.ini")) + [
            f"x64/FF9_Data/{d}" for d in DATA_DIRS]
    out = {}
    for t in names:
        p = install / t
        if not p.is_dir():
            continue
        n = size = 0
        newest = 0.0
        for dirpath, _dirs, files in os.walk(p):
            for f in files:
                st = os.stat(Path(dirpath) / f)
                n += 1
                size += st.st_size
                newest = max(newest, st.st_mtime)
        out[t] = [n, size, round(newest, 3)]
    if (install / "Memoria.ini").is_file():
        out["Memoria.ini"] = sha256(install / "Memoria.ini")[:16]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("verb", choices=("ensure", "verify", "teardown", "pids", "status", "fingerprint"))
    ap.add_argument("roots", nargs="*", help="instance root(s) (status: default every root under the home)")
    ap.add_argument("--install", default=None, help="the FF9 install (default: auto-detect)")
    ap.add_argument("--deep", action="store_true", help="verify/status: compare every copy by sha256")
    a = ap.parse_args(argv)
    if a.verb == "fingerprint":
        from ff9mapkit.config import find_game_path
        print(json.dumps(install_fingerprint(a.install or find_game_path()), indent=1))
        return 0
    roots = a.roots
    if a.verb == "status" and not roots:
        roots = [str(d) for d in sorted(INSTANCES_HOME.iterdir())] if INSTANCES_HOME.is_dir() else []
    if not roots:
        ap.error(f"{a.verb} needs a root")
    rc = 0
    for r in roots:
        inst = Instance(r, install=a.install)
        try:
            if a.verb == "ensure":
                done = inst.ensure()
                print(f"{inst.root}: " + ("; ".join(done) if done else "already right"))
            elif a.verb == "verify":
                bad = inst.verify(deep=a.deep)
                print(f"{inst.root}: " + ("VERIFY OK" if not bad else "VERIFY FAIL\n  " + "\n  ".join(bad)))
                rc |= 1 if bad else 0
            elif a.verb == "teardown":
                print(json.dumps(inst.teardown()))
            elif a.verb == "pids":
                mine, others, unknown = inst.scan()
                print(json.dumps({"root": str(inst.root), "pids": mine, "other_ff9": others, "unreadable": unknown}))
            else:
                print(json.dumps(inst.status(deep=a.deep), indent=1, default=str))
        except InstanceError as err:
            print(f"!! {inst.root}: {err}", file=sys.stderr)
            rc = 2
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
