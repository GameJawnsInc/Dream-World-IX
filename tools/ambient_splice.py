#!/usr/bin/env python3
"""F-REDEPLOY by splice: restore the ambient clear in ONE already-deployed synthesized field, touching nothing else.

WHY NOT A REBUILD. ``build_script`` restores stock's ambient clear (``content/ambient.py``) on every build since
master d98ca2a4, so the obvious redeploy is ``deploy_field.py`` from the field's own source. But a field deployed
weeks earlier rebuilds with every OTHER kit change made since, too. Measured on the Southern Ring (4600, 6601-6603,
FF9CustomMap-world): the rebuild was +51 bytes, not +38 -- the entry-settle hold moved before ``set MAP159 = 1``,
blob shadows on the player and NPCs, the animation-block padding, and on 6602 a movement lock around the keeper's
talk window -- plus a newer ``JournalPatch.txt`` catalog. Several behaviour changes in one in-game test. This tool
instead writes exactly ``ambient.restore_clear(live)``: the live ``.eb`` plus the 38-byte tail, the same function
``build_script`` runs, so the deployed field changes by the fix alone.

WHAT IT WRITES. Only the field's ``EVT_<NAME>.eb.bytes`` in the 7 languages. No DictionaryPatch, ``.mes``,
JournalPatch or any other file is written, so a ~ Reload field (or the next entry) picks it up; no relaunch.

HOW IT CHECKS. Independently of ``restore_clear``: both scripts are parsed, every function of every entry must be
instruction-for-instruction identical, except entry 0's Main_Init, which must be the old instruction list with the
TAIL's six instructions inserted as one run immediately before the first ``set MAP159 = 1`` after the prologue's
``Byte[14] := 1``. Also ``classify``: every language ``missing`` before, ``restored`` after, lengths +38.

SAFETY. Dry run by default; ``--apply`` refuses while FF9.exe runs, holds the mod-folder lock, backs up each file
create-exclusive to the MAIN repo's ``backups/`` (``<lang>-EVT_<NAME>.eb.bytes.preDEPLOY.<stamp>``), writes
atomically, re-reads and re-checks, and writes ``tools/scroll_out/revert_ambient_<id>.py`` (it restores only files
that still hold the spliced bytes). One id per call.

Usage:  py tools/ambient_splice.py <id> --mod-folder FF9CustomMap-world [--apply]
"""
import argparse, contextlib, hashlib, os, re, subprocess, sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repo_root import main_repo_root
from ff9mapkit import deploybackup as _bkp, deploylog as _dlog
from ff9mapkit.config import LANGS, ModLayout, find_game_path
from ff9mapkit.content import ambient
from ff9mapkit.content import entry_settle as _entry_settle
from ff9mapkit.eb import EbScript
from ff9mapkit.fsutil import FileLockTimeout, atomic_write_bytes, locked_mod_folder

_REPO = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
_MAIN = main_repo_root()


def field_name(dictionary_patch: Path, fid: int) -> str:
    """The NAME of the one ``FieldScene <fid> <area> <map> <NAME> <textid>`` line; raises if not exactly one."""
    rows = [ln.split() for ln in dictionary_patch.read_text(encoding="utf-8-sig").splitlines()]
    hits = [r for r in rows if len(r) >= 6 and r[0] == "FieldScene" and r[1] == str(fid)]
    if len(hits) != 1:
        raise SystemExit(f"!! {dictionary_patch}: want exactly one `FieldScene {fid}` line, found {len(hits)}")
    return hits[0][4]


def _funcs(data: bytes) -> dict:
    """``{(entry, tag): [instruction bytes, ...]}`` for every function of every entry."""
    eb = EbScript.from_bytes(data)
    out = {}
    for ei, e in enumerate(eb.entries):
        if e is None:
            continue
        for f in e.funcs:
            out[(ei, f.tag)] = [bytes(data[i.off:i.end]) for i in eb.instrs(f)]
    return out


_TAIL_INSTRS = [ambient.TAIL[i:j] for i, j in ((0, 8), (8, 11), (11, 19), (19, 27), (27, 30), (30, 38))]


def check_splice(old: bytes, new: bytes) -> None:
    """Raise AssertionError unless ``new`` is ``old`` plus exactly the TAIL, at stock's position (see module doc)."""
    assert b"".join(_TAIL_INSTRS) == ambient.TAIL
    assert ambient.classify(old) == "missing", f"old reads {ambient.classify(old)!r}, not 'missing'"
    assert ambient.classify(new) == "restored", f"new reads {ambient.classify(new)!r}, not 'restored'"
    assert len(new) == len(old) + len(ambient.TAIL), f"length {len(old)} -> {len(new)}, want +{len(ambient.TAIL)}"
    fo, fn = _funcs(old), _funcs(new)
    assert fo.keys() == fn.keys(), f"entry/function tables differ: {sorted(fo.keys() ^ fn.keys())}"
    for key in fo:
        if key != (0, 0):
            assert fo[key] == fn[key], f"entry {key[0]} tag {key[1]} changed"
    a, b = fo[(0, 0)], fn[(0, 0)]
    end14 = a.index(ambient._let1(14))                                  # the prologue's last statement
    k = next(i for i in range(end14 + 1, len(a)) if a[i] == _entry_settle._SET_MAIN_READY)
    want = a[:k] + _TAIL_INSTRS + a[k:]
    assert b == want, "Main_Init is not the old one with the TAIL inserted before `set MAP159 = 1`"


def _ff9_running() -> bool:
    if os.name != "nt":
        return False
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq FF9.exe", "/NH"], capture_output=True, text=True).stdout
    return "FF9.exe" in out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Splice the ambient clear into one deployed synthesized field's .eb "
                                             "(7 languages), nothing else. Dry run unless --apply.")
    ap.add_argument("id", type=int, help="the deployed field id")
    ap.add_argument("--mod-folder", required=True, help="the Memoria mod folder the id is deployed in")
    ap.add_argument("--apply", action="store_true", help="write the live files (default: dry run)")
    args = ap.parse_args(argv)
    game = find_game_path()
    live = ModLayout(game / args.mod_folder)
    name = field_name(live.dictionary_patch, args.id)
    paths = {L: live.eb_path(L, f"EVT_{name}.eb.bytes") for L in LANGS}
    missing = [str(p) for p in paths.values() if not p.is_file()]
    if missing:
        raise SystemExit("!! missing live .eb: " + ", ".join(missing))
    olds = {L: p.read_bytes() for L, p in paths.items()}
    states = {L: ambient.classify(b) for L, b in olds.items()}
    if set(states.values()) == {"restored"}:
        print(f"{args.id} {name}: already 'restored' in all {len(LANGS)} languages -- nothing to do.")
        return 0
    if set(states.values()) != {"missing"}:
        raise SystemExit(f"!! {args.id} {name}: languages disagree or are not 'missing': {states}")
    news = {L: ambient.restore_clear(b) for L, b in olds.items()}
    for L in LANGS:
        check_splice(olds[L], news[L])
    sha = lambda b: hashlib.sha256(b).hexdigest()
    print(f"{args.id} {name} in {args.mod_folder}: every language is the live .eb plus exactly the "
          f"{len(ambient.TAIL)}-byte TAIL before `set MAP159 = 1`, nothing else changed")
    for L in LANGS:
        print(f"  {L}: {len(olds[L])} {sha(olds[L])[:16]} -> {len(news[L])} {sha(news[L])[:16]}")
    if not args.apply:
        print("dry run -- nothing written (pass --apply)")
        return 0

    if _ff9_running():
        raise SystemExit("!! FF9.exe is running -- close the game first. Nothing written.")
    bk = _MAIN / "backups"
    bk.mkdir(parents=True, exist_ok=True)
    with contextlib.ExitStack() as stack:
        try:
            stack.enter_context(locked_mod_folder(live.root))
        except FileLockTimeout as e:
            raise SystemExit(f"!! {e}\n!! another deploy holds {args.mod_folder}'s lock. Nothing written.")
        # re-read under the lock: another writer may have landed since the dry-run half above
        if any(paths[L].read_bytes() != olds[L] for L in LANGS):
            raise SystemExit("!! a live .eb changed while this ran -- re-run. Nothing written.")
        first = LANGS[0]
        stamp = _bkp.claim_stamp(bk, paths[first], f"{first}-EVT_{name}.eb.bytes")
        backups = {first: bk / _bkp.backup_name(f"{first}-EVT_{name}.eb.bytes", stamp)}
        for L in LANGS[1:]:
            backups[L] = _bkp.backup_exclusive(paths[L], bk / _bkp.backup_name(f"{L}-EVT_{name}.eb.bytes", stamp))
        for L in LANGS:
            assert backups[L].read_bytes() == olds[L], f"backup {backups[L]} does not hold the live bytes"
        for L in LANGS:
            atomic_write_bytes(paths[L], news[L])
        for L in LANGS:
            got = paths[L].read_bytes()
            assert got == news[L] and ambient.classify(got) == "restored", f"{paths[L]} did not land"
    revert = _MAIN / "tools" / "scroll_out" / f"revert_ambient_{args.id}.py"
    revert.parent.mkdir(parents=True, exist_ok=True)
    rows = ",\n".join(f"    ({str(paths[L])!r}, {str(backups[L])!r}, {sha(news[L])!r})" for L in LANGS)
    revert.write_text(
        "#!/usr/bin/env python3\n"
        f'"""Undo tools/ambient_splice.py on field {args.id} ({name}, {args.mod_folder}), stamp {stamp}.\n'
        "Restores each .eb from its backup ONLY if the live file still holds the spliced bytes; a file changed\n"
        'since (a redeploy) is left alone and reported."""\n'
        "import hashlib, shutil, sys\n"
        f"ROWS = [\n{rows},\n]\n"
        "bad = 0\n"
        "for live, backup, spliced in ROWS:\n"
        "    if hashlib.sha256(open(live, 'rb').read()).hexdigest() != spliced:\n"
        "        print(f'  !! {live} changed since the splice -- left alone'); bad += 1; continue\n"
        "    shutil.copyfile(backup, live)\n"
        "    print(f'  restored {live}')\n"
        "sys.exit(1 if bad else 0)\n", encoding="utf-8", newline="\n")
    _dlog.record(game, _dlog.DEPLOYED, args.id, args.mod_folder, checkout=str(_REPO),
                 note=f"{name} <- ambient_splice (+{len(ambient.TAIL)} B x{len(LANGS)}, stamp {stamp})")
    print(f"APPLIED. backups: {bk}\\*-EVT_{name}.eb.bytes.preDEPLOY.{stamp}\n"
          f"revert:  py {revert}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
