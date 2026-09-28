#!/usr/bin/env python3
"""Find -- and repair -- deploy reverts whose pre-deploy backups a same-second deploy overwrote.

THE DEFECT: ``tools/deploy_field.py`` stamped its backups (``backups/<file>.preDEPLOY.<STAMP>``) to the second
until the fix that added ``ff9mapkit.deploybackup``. When two deploys landed in one second, the later one's
backups replaced the earlier one's -- and by then they held the earlier id's OWN ``FieldScene`` line and
ForkDonorPatch row. The earlier id's ``revert_deploy_<id>.py`` re-adds every line it owns that it finds in its
backup, so running it deletes the field's ``.eb`` but RESTORES its registration: a FieldScene pointing at a
missing ``.eb``, the null-.eb black screen. The fix stops new collisions; the reverts written before it stay
defective until their backups are repaired.

THE REPAIR is backup-only and runs no revert. Two deploys that shared a stamp share its backup files, and each
revert consults only the lines IT owns in them. So dropping the earlier id's own lines from the shared
DictionaryPatch/ForkDonorPatch backups (a) makes the earlier id's revert remove its registration, and (b) leaves
the partner's revert byte-for-byte unchanged in effect -- refused outright if any dropped line is also the
partner's. The dropped lines are exactly the ones the earlier deploy itself wrote: the most recent earlier backup
(the predecessor snapshot) must show that only ONE other deploy changed the file in between, and any line the id
owned THERE is carried over instead of dropped. Every other backup the revert restores wholesale (.mes,
JournalPatch, CSVs) that the partner ALSO restores must be byte-identical to the predecessor's, or the id is
refused for a manual repair.
Originals are kept beside the backups as ``<name>.collided-orig``.

Usage (paths default to the main repo's tools/scroll_out, each script's own recorded backups dir, the found
game install; the live mod folder is only READ, to simulate the revert):
  py tools/repair_collided_backups.py                    # scan: every stamp-collided revert (read-only)
  py tools/repair_collided_backups.py --plan 30832 ...   # verify + simulate each repair (read-only)
  py tools/repair_collided_backups.py --repair 30832 ... # rewrite the collided backups (keeps originals)
"""
from __future__ import annotations

import argparse
import ast
import datetime
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # tools/ -- for repo_root

from ff9mapkit import deploybackup as _bkp  # noqa: E402
from ff9mapkit import deploylog as _dlog  # noqa: E402
from ff9mapkit import dictpatch as _dp  # noqa: E402
from ff9mapkit import forkdonor as _fd  # noqa: E402
from ff9mapkit.config import LANGS  # noqa: E402
from ff9mapkit.fsutil import atomic_write_bytes  # noqa: E402

DP, FD = "DictionaryPatch.txt", "ForkDonorPatch.txt"
SPLICED = {"BattlePatch.txt", "TextPatch.txt"}        # surgical by marker block, like DP/FD -- never wholesale
ORIG_SUFFIX = ".collided-orig"
_STAMP_RE = re.compile(r"^\d{8}-\d{6}(-\d{6}(-\d+)?)?$")   # the old one-second form, and deploybackup's
_READ_RE = re.compile(r'BK/f"([^"]+?)\.preDEPLOY\.\{STAMP\}"')


class RepairRefused(Exception):
    """The evidence does not prove which lines the earlier deploy wrote -- repair this id by hand."""


@dataclass
class RevertInfo:
    """What a generated ``revert_deploy_<id>.py`` restores, read from its source (never executed)."""
    fid: int
    path: Path
    stamp: str
    backup_dir: Path
    mod_folder: str
    kit: str
    model_ids: set = field(default_factory=set)
    anim_keys: set = field(default_factory=set)
    text_blocks: set = field(default_factory=set)
    reads: set = field(default_factory=set)            # backup labels restored from at STAMP ({L} expanded)

    def owns(self, line: str) -> bool:
        """The revert's own DictionaryPatch ownership rule (dictpatch.owns_registration), exactly."""
        return _dp.owns_registration(line.strip().lstrip("\ufeff"), fid=str(self.fid), model_ids=self.model_ids,
                                     anim_keys=self.anim_keys, text_blocks=self.text_blocks)

    def owns_row(self, line: str) -> bool:
        """The revert's own ForkDonorPatch rule (forkdonor.own_row): a data row whose FIRST token is the id."""
        s = line.strip().lstrip("\ufeff")
        return bool(s) and not s.startswith("#") and s.split()[0:1] == [str(self.fid)]

    def backup(self, label: str, stamp: "str | None" = None) -> Path:
        return self.backup_dir / _bkp.backup_name(label, stamp or self.stamp)


def _literal(node):
    return ast.literal_eval(node)


def parse_revert(path: Path) -> "RevertInfo | None":
    """Read a generated revert's data out of its AST; None for a script of an older/unknown shape."""
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None
    vals, kit, fid = {}, None, None
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            vals.setdefault(n.targets[0].id, n.value)
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "insert"
              and len(n.args) == 2 and isinstance(n.args[1], ast.Constant) and kit is None):
            kit = n.args[1].value
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "revert_dictionary_patch":
            fid = next((_literal(k.value) for k in n.keywords if k.arg == "fid"), None)
    m = re.fullmatch(r"revert_deploy_(\d+)\.py", path.name)
    try:
        stamp = _literal(vals["STAMP"])
        bk = vals["BK"]
        live = vals["live"]
        backup_dir = Path(_literal(bk.args[0]))
        mod_folder = _literal(live.args[0].right)
        sets = {k: {str(x) for x in _literal(vals[k].args[0])} for k in ("_MINT_IDS", "_MINT_ANIM_KEYS", "_MES_BLOCKS")}
    except (KeyError, AttributeError, IndexError, ValueError):
        return None
    if not m or str(fid) != m.group(1) or not isinstance(stamp, str):
        return None
    reads = set()
    for lab in _READ_RE.findall(text):
        reads |= {lab.replace("{L}", L) for L in LANGS} if "{L}" in lab else {lab}
    return RevertInfo(fid=int(m.group(1)), path=path, stamp=stamp, backup_dir=backup_dir, mod_folder=mod_folder,
                      kit=kit or "", model_ids=sets["_MINT_IDS"], anim_keys=sets["_MINT_ANIM_KEYS"],
                      text_blocks=sets["_MES_BLOCKS"], reads=reads)


def scan(scroll_out: Path):
    """(parsed reverts, unparsed script paths) for every ``revert_deploy_<id>.py`` in ``scroll_out``."""
    infos, unparsed = [], []
    for p in sorted(scroll_out.glob("revert_deploy_*.py")):
        info = parse_revert(p)
        (infos if info else unparsed).append(info or p)
    return infos, unparsed


def partners_of(info: RevertInfo, infos) -> list:
    """The OTHER reverts that restore from the very same backup files (same stamp, same backups dir)."""
    return [o for o in infos if o is not info and o.stamp == info.stamp and o.backup_dir == info.backup_dir]


def _lines(p: Path) -> list:
    return p.read_bytes().decode("utf-8").splitlines(keepends=True) if p.exists() else []


def held_own(info: RevertInfo) -> tuple:
    """(own DictionaryPatch lines, own ForkDonorPatch rows) found in this revert's backups -- the half-revert."""
    return ([l for l in _lines(info.backup(DP)) if info.owns(l)],
            [l for l in _lines(info.backup(FD)) if info.owns_row(l)] if FD in info.reads else [])


def _predecessor(info: RevertInfo, label: str) -> "Path | None":
    """The most recent ``<label>`` backup stamped BEFORE this one in the same backups dir (the prior snapshot)."""
    best = None
    prefix = f"{label}.preDEPLOY."
    for p in info.backup_dir.glob(f"{label}.preDEPLOY.*"):
        s = p.name[len(prefix):]
        if _STAMP_RE.match(s) and s < info.stamp and (best is None or s > best[0]):
            best = (s, p)
    return best[1] if best else None


def _reg_key(line: str):
    """Which single deploy a DictionaryPatch/ForkDonorPatch line belongs to: the id every per-deploy line is
    keyed by (column 2 of an id-keyed directive, column 1 of a fork row), or None when it is not id-keyed."""
    p = line.strip().lstrip("\ufeff").split()
    if len(p) >= 2 and p[0] in ("FieldScene", "LocationName", "MessageFile", "BattleScene"):
        return p[1]
    if len(p) == 2 and p[0].isdigit() and p[1].isdigit():
        return p[0]
    return None


@dataclass
class Plan:
    info: RevertInfo
    partners: list
    rewrites: list = field(default_factory=list)       # (path, new_bytes, dropped lines, carried lines)
    evidence: list = field(default_factory=list)


def _prelude_check(info: RevertInfo, ledger) -> str:
    """A deploy's prelude revert runs just before its backups are taken and can RE-ADD an older registration of
    the id -- invisible to every backup. The ledger shows it: a ``retired`` row for the id seconds before the
    stamp. Refuses when one is there; returns an evidence line otherwise."""
    if ledger is None:
        return "ledger: not read (no game install) -- a prelude re-add before this deploy is UNCHECKED"
    t = datetime.datetime.strptime(info.stamp[:15], "%Y%m%d-%H%M%S")
    for e in ledger:
        if e.field_id != info.fid or e.mod_folder != info.mod_folder or e.event != _dlog.RETIRED:
            continue
        try:
            when = datetime.datetime.fromisoformat(e.when)
        except ValueError:
            continue
        if t - datetime.timedelta(seconds=30) <= when <= t:
            raise RepairRefused(f"{info.fid}: a prelude revert ran right before this deploy (ledger 'retired' at "
                                f"{e.when}) -- whatever it re-added is invisible to the backups; repair by hand")
    return "ledger: no prelude revert ran right before this deploy"


def plan_repair(info: RevertInfo, infos, ledger=None, allow_other_deploys=False) -> Plan:
    """Prove which of the shared backups' lines this id's own deploy wrote, and compute the repaired bytes.
    ``ledger`` is ``deploylog.read(game)`` (None = unchecked). Raises :class:`RepairRefused` when the evidence
    does not settle it. An empty plan means nothing to drop.

    By default the predecessor snapshot must differ from the shared one by exactly ONE other deploy's lines (the
    deploy that ran in between), which also proves the snapshot is this mod folder's. ``allow_other_deploys``
    accepts several other ids' id-keyed lines -- still never a line keyed by this id, never an un-keyed one --
    for a gap where e.g. a ``deploy_battle`` registered BattleScenes in the same folder."""
    partners = partners_of(info, infos)
    if not partners:
        raise RepairRefused(f"{info.fid}: no other revert shares stamp {info.stamp} -- not a stamp collision; any "
                            f"own line in its backup pre-existed the deploy, so the revert is right to restore it")
    plan = Plan(info, partners)
    plan.evidence.append(f"stamp {info.stamp} shared with " + ", ".join(str(p.fid) for p in partners))
    plan.evidence.append(_prelude_check(info, ledger))
    pred_dp = _predecessor(info, DP)
    for label, own in ((DP, info.owns), (FD, info.owns_row)):
        if label == FD and FD not in info.reads:
            continue
        path = info.backup(label)
        lines = _lines(path)
        drop = [l for l in lines if own(l)]
        if not drop:
            continue
        for p in partners:
            if label == DP and any(p.owns(l) for l in drop) or label == FD and any(p.owns_row(l) for l in drop):
                raise RepairRefused(f"{info.fid}: a line to drop from {path.name} is ALSO owned by {p.fid} -- "
                                    f"dropping it would change {p.fid}'s revert")
        pred = pred_dp if label == DP else _predecessor(info, FD)
        if pred is None:
            raise RepairRefused(f"{info.fid}: no {label} backup earlier than {info.stamp} to prove the "
                                f"pre-deploy state from")
        pl = [l.strip() for l in _lines(pred) if l.strip()]
        cl = [l.strip() for l in lines if l.strip()]
        added = [l for l in cl if l not in set(pl) and not own(l)]
        removed = [l for l in pl if l not in set(cl) and not own(l)]
        keys = {_reg_key(l) for l in added + removed}
        if None in keys or str(info.fid) in keys:
            raise RepairRefused(f"{info.fid}: between {pred.name} and {path.name} the file gained/lost a line that "
                                f"is not another deploy's id-keyed registration: +{added} -{removed}")
        if len(keys) > 1 and not allow_other_deploys:
            raise RepairRefused(f"{info.fid}: between {pred.name} and {path.name} the file changed by more than "
                                f"one other deploy ({sorted(keys)}): +{added} -{removed} -- if those are all "
                                f"known neighbours, re-run with --allow-other-deploys")
        carried = [l for l in _lines(pred) if own(l)]
        kept = [l for l in lines if not own(l)]
        if kept and carried and not kept[-1].endswith("\n"):
            kept[-1] += "\n"
        new = "".join(kept + carried)
        plan.rewrites.append((path, new.encode("utf-8"), drop, carried))
        plan.evidence.append(f"{label}: predecessor {pred.name}; since then only deploy(s) {sorted(keys)} changed "
                             f"it besides {info.fid}; {info.fid} owned {len(carried)} line(s) there (carried)")
    if not plan.rewrites:
        return plan
    for label in sorted(info.reads - {DP, FD}):
        here = info.backup(label)
        if not here.exists():
            continue
        if label in SPLICED:
            raise RepairRefused(f"{info.fid}: its revert also restores a spliced {label} from the shared stamp -- "
                                f"repair by hand")
        if not any(label in p.reads for p in partners):
            # a deploy writes a backup only under a name its own revert restores from, so a name no partner
            # restores was written by this deploy alone: it is this id's own, genuine snapshot
            plan.evidence.append(f"{label}: this deploy's own snapshot (no partner restores it)")
            continue
        there = pred_dp and info.backup(label, pred_dp.name[len(f'{DP}.preDEPLOY.'):])
        if not there or not there.exists() or there.read_bytes() != here.read_bytes():
            raise RepairRefused(f"{info.fid}: {here.name} (restored wholesale) is not byte-identical to the "
                                f"predecessor's copy -- cannot tell whose snapshot it is; repair by hand")
        plan.evidence.append(f"{label}: byte-identical to the predecessor's copy")
    return plan


def apply_repair(plan: Plan) -> list:
    """Write the plan: each original kept as ``<name>.collided-orig`` (create-exclusive), then an atomic rewrite."""
    done = []
    for path, new, _drop, _carried in plan.rewrites:
        _bkp.backup_exclusive(path, path.with_name(path.name + ORIG_SUFFIX))
        atomic_write_bytes(path, new)
        done.append(path)
    return done


def simulate(info: RevertInfo, dp_backup_lines, fd_backup_text, live_dp_lines, live_fd_text) -> tuple:
    """What this revert would leave of its OWN registration, run against the live files -- pure, writes nothing.
    Returns (own DictionaryPatch lines left, own ForkDonorPatch row left or None)."""
    kept, _lost = _dp.revert_dictionary_patch(
        [l.rstrip("\r\n") for l in live_dp_lines], [l.rstrip("\r\n") for l in dp_backup_lines], fid=str(info.fid),
        model_ids=info.model_ids, anim_keys=info.anim_keys, text_blocks=info.text_blocks)
    row = _fd.own_row(_fd.revert_row(live_fd_text, fd_backup_text, info.fid), info.fid) if FD in info.reads else None
    return [l for l in kept if info.owns(l)], row


def _simulation_lines(info: RevertInfo, plan: Plan, game: "Path | None") -> list:
    if game is None:
        return ["  (no game install found -- revert simulation skipped)"]
    live = game / info.mod_folder
    live_dp, live_fd = _lines(live / DP), ((live / FD).read_text(encoding="utf-8-sig") if (live / FD).exists() else "")
    out = []
    new = {p.name: b.decode("utf-8") for p, b, _d, _c in plan.rewrites}
    for tag, dp_text, fd_text in (
            ("as the backups stand", "".join(_lines(info.backup(DP))), "".join(_lines(info.backup(FD)))),
            ("after the repair", new.get(info.backup(DP).name, "".join(_lines(info.backup(DP)))),
             new.get(info.backup(FD).name, "".join(_lines(info.backup(FD)))))):
        left, row = simulate(info, dp_text.splitlines(), fd_text, live_dp, live_fd)
        out.append(f"  revert {tag}: leaves {left or 'no own registration'}"
                   + (f"; ForkDonorPatch row {row!r}" if row else "; no ForkDonorPatch row" if FD in info.reads else ""))
    return out


def _kit_note(info: RevertInfo) -> str:
    return "" if not info.kit or Path(info.kit).is_dir() else f"  (its kit {info.kit} is GONE -- run it with " \
        f"PYTHONPATH=<main repo>/ff9mapkit, or it fails at import before touching anything)"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ids", nargs="*", type=int, help="revert ids to plan/repair (scan mode ignores them)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="verify + simulate each id's repair; write nothing")
    mode.add_argument("--repair", action="store_true", help="rewrite the collided backups (originals kept)")
    ap.add_argument("--allow-other-deploys", action="store_true",
                    help="accept several other deploys' id-keyed lines between the predecessor snapshot and the "
                         "shared one (default: exactly one)")
    ap.add_argument("--scroll-out", type=Path, default=None, help="default: <main repo>/tools/scroll_out")
    ap.add_argument("--game", type=Path, default=None, help="FF9 install for the read-only revert simulation")
    a = ap.parse_args(argv)
    if a.scroll_out is None:
        from repo_root import main_repo_root
        a.scroll_out = main_repo_root() / "tools" / "scroll_out"
    game = a.game
    if game is None:
        try:
            from ff9mapkit.config import find_game_path
            game = find_game_path()
        except Exception:                               # no install: simulation is optional
            game = None
    infos, unparsed = scan(a.scroll_out)
    if not (a.plan or a.repair):
        groups = defaultdict(list)
        for i in infos:
            groups[(i.backup_dir, i.stamp)].append(i)
        n = 0
        for (_bd, stamp), grp in sorted(groups.items(), key=lambda kv: kv[0][1]):
            if len(grp) < 2:
                continue
            for i in sorted(grp, key=lambda i: i.fid):
                dp_own, fd_own = held_own(i)
                bad = bool(dp_own or fd_own)
                n += bad
                print(f"{stamp}  {i.fid}  {'HALF-REVERT' if bad else 'ok':11}  "
                      f"{[l.strip() for l in dp_own + fd_own] if bad else ''}{_kit_note(i)}")
        print(f"\n{len(infos)} reverts scanned ({len(unparsed)} of an older shape skipped); {n} defective.")
        return 1 if n else 0
    if not a.ids:
        ap.error("--plan/--repair need at least one revert id")
    by_id = {i.fid: i for i in infos}
    ledger = _dlog.read(game) if game is not None else None
    rc = 0
    for fid in a.ids:
        info = by_id.get(fid)
        if info is None:
            print(f"== {fid}: no parseable revert_deploy_{fid}.py in {a.scroll_out}")
            rc = 1
            continue
        try:
            plan = plan_repair(info, infos, ledger, allow_other_deploys=a.allow_other_deploys)
        except RepairRefused as e:
            print(f"== {fid}: REFUSED -- {e}")
            rc = 1
            continue
        print(f"== {fid} (stamp {info.stamp})")
        for ev in plan.evidence:
            print(f"  {ev}")
        if not plan.rewrites:
            print("  nothing to drop -- its backups hold none of its own lines (already repaired, or never hit)")
            continue
        for path, _new, drop, carried in plan.rewrites:
            print(f"  {path.name}: drop {[l.strip() for l in drop]}"
                  + (f", carry {[l.strip() for l in carried]}" if carried else ""))
        for ln in _simulation_lines(info, plan, game):
            print(ln)
        note = _kit_note(info)
        if note:
            print(note)
        if a.repair:
            for p in apply_repair(plan):
                print(f"  repaired {p.name} (original kept as {p.name}{ORIG_SUFFIX})")
    return rc


if __name__ == "__main__":
    sys.exit(main())
