"""F5'S ANALYSIS, DRY-RUN OFFLINE -- every check of rung5_hub.analyse5 shown able to PASS, to FAIL and -- every one
with a VOID branch (P-FROZEN has none) -- to go VOID as the frozen predictions (rung5_predictions_v3.json) register it,
before any F5 deploy or run, on real rows. A case registered for one clause of a check names that clause (a ``need`` on
the check's detail, ``also_need`` on another check's), never the verdict alone.

    py studies/story-trace/rung5_dryrun.py [--build DIR] [--keep DIR] [--session4 DIR] [--session3 DIR] [--pre-ambient]

F5c: the kit's synthesized builds now restore the ambient clear (e1317a42), so the hub 31100 no longer builds to its
frozen 148bda04 from the tomls. Reproduce this frozen dry-run with ``--build`` on a preserved pre-fix build
(C:\\gd\\_ns_playtest\\f5\\keep_v3\\build, with its SHA256SUMS) or with ``--pre-ambient``: every build through a
shim that sets ``ff9mapkit.content.ambient.restore_clear`` to identity before ``cli.main`` (:data:`PRE_AMBIENT_SHIM`).

THE BUILD. The 13 fields are built here, offline, from the tomls rung5_forks.json names (``ff9mapkit build <toml>
--out <tmp>/<id>``, sub-second each; ``--build DIR`` reads a build already made the same way), and every US .eb is
checked against the frozen sha in rung5_forks.json first: the analysis is joined against the bytes the session will
deploy, never against a stand-in. The hub's rows are joined against the BUILT hub (its prologue and stamp sites at
their real entry ips), the members' rows against the built members.

THE BASE is session 4 (story-rung3d, archived in the main checkout's .harness-runs; read only, every file this reads is
copied into a temp session): its three stock runs S#1, S#4 and S#7, traces and logs, as F5's runs 1, 3 and 5. Each F5
run (2, 4, 6) is CONSTRUCTED from its round's S, as the engine would write the hub lane's run:
  * the partner's rows relabelled into the 12 members (rung3_dryrun.relabel with ``until=None``: 450 is member 31112,
    no seam) -- New Game's field-70 residue kept as it is;
  * the HUB's rows inserted before the first row in 359: its Main_Init prologue -- the same sound-environment idiom as
    359's Main_Init, which takes the same branches on the same state, so its rows are 359's first prologue rows at
    the hub's own sites (target and value) -- then the three frozen stamps (e2 t3), fld = don = 31100;
  * every row's ``old`` RE-SEATED on the state the rows themselves leave (:func:`reseat` -- a row the S world never
    had reads the state; a row both worlds have keeps S's old outside the bits the worlds differ on), so 359 +220
    UInt16[297] reads old 1 / same 1, the wake old 2600 / same 1, and the reconstructor finds 0 contradictions;
  * ``sc`` 2600 from the stamp to the wake;
  * its log: rung3_dryrun.replay_log of the partner's entered walk (read off the partner's real log), led by a hub
    record, its segment record in member(352).
THE BASE MUST PASS EVERY CHECK.

Then MUTANTS, one per way the world could differ, each registered in the predictions (a check's "mutants") and in the
design's dry-run table -- each must come out AS REGISTERED: the check's verdict, and where registered the stop class,
the re-run plan's halt, the VOID it lists, the note it must (not) carry. A registered mutant that comes out otherwise is
a defect of the analysis or of the construction, never a reason to weaken the mutant. And the OFFLINE PRE-FLIGHT
cases: the build passes P-PURE and P-HUB's byte clauses; 31103 with 450 left unremapped and a chain seeded without
--hub (a prepend) FAIL P-PURE; a hub built with set_scenario 2610 FAILs P-HUB; rung5_hub.preflight5 runs with only
the S and F5 sides, over the offline build merged into one mod root (hermetic: it does not read what is deployed), and
PASSes every static check. The guard of the STAMP_SOURCE switch: R5-STAMP fed from_start's field list FAILs the base.

This proves the ANALYSIS, not the prediction: the base construction encodes the predicted world, so it passing says
only that the checks read what they claim to. The session decides the prediction. Exit 0 only when the base passes
every check and every case comes out as registered; one line per case.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dali_tour as D  # noqa: E402
import rung3_dryrun as RD  # noqa: E402
import rung3_trace as R  # noqa: E402
import rung5_hub as M  # noqa: E402
from dali_tour import T  # noqa: E402

KIT = HERE.parents[1] / "ff9mapkit"                     # `py -m ff9mapkit` runs from here (the local package)
SESSION4 = RD.main_repo() / ".harness-runs" / "20260928-011959-story-rung3d"
SESSION3 = RD.main_repo() / ".harness-runs" / "20260926-101447-story-rung3c"
WORD = RD.WORD
S_OF = {1: 1, 3: 4, 5: 7}                                # F5's stock run i <- session 4's S run
EXHAUSTED = "passes exhausted (3) without the story moving on"       # Tour.run's stop when the story never moves


# ======================================================================== the build (offline, from the durable tomls)
#: F5c: the kit's synthesized builds restore the ambient clear (content/ambient.py, the fix e1317a42), so every
#: frozen synthesized sha in this lane (F5's hub 31100, F5b v1's two hubs) moved. ``--pre-ambient`` builds the
#: PRE-fix bytes: the build runs through this shim, which sets the pass to identity before the CLI (T-AMB-5 pins that
#: identity reproduces the pre-fix build). A kit with no ambient module refuses the shim loudly (ImportError).
PRE_AMBIENT_SHIM = ("import sys\n"
                    "import ff9mapkit.content.ambient as _a\n"
                    "_a.restore_clear = lambda eb: bytes(eb)\n"
                    "from ff9mapkit.cli import main\n"
                    "sys.exit(main(sys.argv[1:]))\n")


def kit(args: list, *, log: Path | None = None, pre_ambient: bool = False) -> None:
    """``py -m ff9mapkit <args>`` from the worktree's own package; its output to ``log``; raises on a non-zero exit.
    ``pre_ambient``: through :data:`PRE_AMBIENT_SHIM` (``py -c``), the ambient clear as identity."""
    head = [sys.executable, "-c", PRE_AMBIENT_SHIM] if pre_ambient else [sys.executable, "-m", "ff9mapkit"]
    p = subprocess.run([*head, *map(str, args)], cwd=KIT, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if log is not None:
        log.write_text(p.stdout + p.stderr, encoding="utf-8")
    if p.returncode:
        raise RuntimeError(f"ff9mapkit {' '.join(map(str, args[:2]))} exited {p.returncode}: "
                           f"{(p.stdout + p.stderr)[-600:]}")


def manifest_tomls(man: dict) -> dict:
    """``{field id: its field.toml}`` -- the 12 members' and the hub's, as rung5_forks.json records them."""
    out = {int(f): Path(t) for f, t in man["chains"]["F5"]["tomls"].items()}
    out[int(man["hub"]["id"])] = Path(man["hub"]["toml"])
    return out


def build(out: Path, tomls: dict, *, pre_ambient: bool = False) -> None:
    """Build each ``{id: toml}`` into ``out/<id>`` (a mod folder per field, as build step 8 does)."""
    for fid, toml in sorted(tomls.items()):
        kit(["build", toml, "--out", out / str(fid)], log=out / f"{fid}.log", pre_ambient=pre_ambient)


def sha_miss_cause(ebs, *, pre_ambient: bool = False, fixed: bool = False) -> str:
    """Why a frozen synthesized sha may miss (F5c), from the built US .eb bytes ``ebs`` (None: absent): each read by
    ``ambient.classify``. A build that carries the restored tail against pre-fix predictions names the fix and the
    two ways to the pre-fix bytes; ``--pre-ambient`` against predictions of the fixed bytes names that."""
    try:
        from ff9mapkit.content import ambient
    except ImportError:
        return "the kit has no content.ambient: the miss is not the F5c ambient tail"
    got = []
    for data in ebs:
        try:
            got.append(None if data is None else ambient.classify(data))
        except ValueError:
            got.append("drift")
    if "restored" in got and not fixed:
        return ("CAUSE: synthesized bytes changed at the F5c ambient-tail commit (e1317a42: every synthesized Main_Init "
                "gained the 38-byte clear); pass --build <preserved dir> or --pre-ambient")
    if pre_ambient and fixed:
        return "CAUSE: these predictions freeze the fixed bytes (the ambient tail): drop --pre-ambient"
    return f"the built hubs classify {got} (content.ambient): the miss is not the F5c ambient tail alone"


def frozen_build(build_dir: Path, man: dict) -> tuple:
    """``(ok, detail, {id: US .eb bytes})``: every built field's US .eb against rung5_forks.json's frozen sha --
    the bytes the analysis joins against are the bytes the session will deploy."""
    want = {int(f): s for f, s in man["chains"]["F5"]["eb_sha256"].items()}
    want[int(man["hub"]["id"])] = man["hub"]["eb_sha256"]
    got, bad = {}, []
    for fid, sha in sorted(want.items()):
        data = M.built_eb(build_dir, fid)
        if data is None:
            bad.append(f"{fid}: no US .eb")
            continue
        got[fid] = data
        if hashlib.sha256(data).hexdigest() != sha:
            bad.append(f"{fid}: sha {hashlib.sha256(data).hexdigest()[:12]}, frozen {sha[:12]}")
    return not bad, "; ".join(bad) or f"{len(got)} US .eb files, each its frozen sha", got


def merged_root(build_dir: Path, out: Path, ids) -> Path:
    """ONE mod root holding the builds of ``ids`` -- their StreamingAssets trees copied, their DictionaryPatch and
    ForkDonorPatch lines concatenated -- the offline stand-in for FF9CustomMap after the deploy, so the static
    pre-flight can run hermetically (it never reads what is deployed)."""
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    dp, fdp = [], []
    for fid in sorted(ids):
        src = Path(build_dir) / str(fid)
        shutil.copytree(src / "StreamingAssets", out / "StreamingAssets", dirs_exist_ok=True)
        dp += [ln for ln in (src / "DictionaryPatch.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]
        if (src / "ForkDonorPatch.txt").is_file():
            fdp += [ln for ln in (src / "ForkDonorPatch.txt").read_text(encoding="utf-8").splitlines()
                    if ln.strip() and not ln.startswith("#")]
    (out / "DictionaryPatch.txt").write_text("\n".join(dp) + "\n", encoding="utf-8")
    (out / "ForkDonorPatch.txt").write_text("# merged offline builds\n" + "\n".join(fdp) + "\n", encoding="utf-8")
    return out


# ======================================================================== rows: variables, bits, the re-seat
def parse_target(target: str) -> tuple:
    """``Global.UInt16[297]`` -> ``("UInt16", 297, -1)``; ``Global.Bit[191]`` -> ``("Bit", 23, 191)``."""
    m = re.fullmatch(r"Global\.(\w+)\[(\d+)\]", target)
    w, i = m.group(1), int(m.group(2))
    return (w, i >> 3, i) if w in T.BIT_WIDTHS else (w, i, -1)


def span_bits(o: dict) -> list:
    """The global bits a w/r row dict touches."""
    if o["k"] == "w" and o["w"] in T.BIT_WIDTHS:
        return [o["bit"]]
    n = T.WIDTH_BYTES[o["w"]] if o["k"] == "w" else 1
    return [(o["byte"] + k) * 8 + j for k in range(n) for j in range(8)]


def value_bits(o: dict, value: int) -> dict:
    """``{bit: 0/1}``: ``value`` laid over the row's span as the engine lays it (two's complement, little-endian)."""
    if o["k"] == "w" and o["w"] in T.BIT_WIDTHS:
        return {o["bit"]: value & 1}
    n = T.WIDTH_BYTES[o["w"]] if o["k"] == "w" else 1
    v = value & ((1 << 8 * n) - 1)
    return {(o["byte"] + k) * 8 + j: (v >> (8 * k + j)) & 1 for k in range(n) for j in range(8)}


def bits_value(o: dict, bits: dict) -> int:
    """The value the row's width reads back from its span's bits (signed where the engine reads it signed)."""
    if o["k"] == "w" and o["w"] in T.BIT_WIDTHS:
        return bits[o["bit"]]
    n = T.WIDTH_BYTES[o["w"]] if o["k"] == "w" else 1
    v = sum(bits[(o["byte"] + k) * 8 + j] << (8 * k + j) for k in range(n) for j in range(8))
    lo, _hi = T._WIDTH_RANGE[o["w"]] if o["k"] == "w" else (0, 255)
    return v - (1 << 8 * n) if lo < 0 and v >= 1 << (8 * n - 1) else v


def reseat(entries: list) -> list:
    """THE ROWS ONE SIDE WRITES, their ``old`` values re-seated on the state those rows leave. ``entries`` =
    ``[(kind, S row, this side's row)]`` in the engine's order: ``"both"`` a row both worlds wrote (this side's copy
    keeps S's old outside the bits where the worlds differ, and its new may differ), ``"s"`` a row the S world wrote
    and this side lost (the worlds differ on its bits from then on), ``"new"`` a row only this side wrote (its old is
    this side's state: where the worlds agree, S's value there -- the next S row over that bit says what it was, else
    the last one's new). ``c``/``e`` rows pass through. A residue row whose byte no longer changes is gone (the engine
    writes residue only for a byte that changed); every ``w`` row's ``same`` follows its old."""
    s_world = [(i, s) for i, (kind, s, _f) in enumerate(entries) if kind in ("both", "s") and s["k"] in ("w", "r")]

    def s_value(i: int, b: int) -> int:
        nxt = next((s for j, s in s_world if j > i and b in span_bits(s)), None)
        if nxt is not None:
            return value_bits(nxt, nxt["old"])[b]
        prev = next((s for j, s in reversed(s_world) if j < i and b in span_bits(s)), None)
        return value_bits(prev, prev["new"])[b] if prev is not None else 0

    div: dict = {}                                      # bit -> this side's value, where it differs from S's
    out = []
    for i, (kind, s, f) in enumerate(entries):
        row = f if kind != "s" else s
        if row["k"] not in ("w", "r"):
            if kind != "s":
                out.append(dict(f))
            continue
        if kind == "s":
            s_old, s_new = value_bits(s, s["old"]), value_bits(s, s["new"])
            for b in span_bits(s):
                mine = div.get(b, s_old[b])
                if mine != s_new[b]:
                    div[b] = mine
                else:
                    div.pop(b, None)
            continue
        if kind == "both":
            assert span_bits(s) == span_bits(f), "a 'both' row must keep S's span: a lost row plus a new one"
            s_now = value_bits(s, s["old"])
            s_after = value_bits(s, s["new"])
        else:
            s_now = {b: s_value(i, b) for b in span_bits(f)}
            s_after = s_now
        mine = {b: div.get(b, s_now[b]) for b in span_bits(f)}
        new = value_bits(f, f["new"])
        for b in span_bits(f):
            if new[b] != s_after[b]:
                div[b] = new[b]
            else:
                div.pop(b, None)
        o = dict(f, old=bits_value(f, mine))
        if o["k"] == "w":
            o["same"] = int(o["old"] == o["new"])
        elif o["old"] == o["new"]:
            continue
        out.append(o)
    return out


def rows_of(path: Path) -> list:
    return [json.loads(ln) for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]


def target(o: dict) -> str:
    """A w/c row dict's variable as eb-src spells it (storytrace.Row.target)."""
    return f"Global.{o['w']}[{o['bit'] if o['w'] in T.BIT_WIDTHS else o['byte']}]"


def is_wake(o: dict, pred: dict, members: dict) -> bool:
    """Is row dict ``o`` the wake's own store (352 e17 t1 SC := beat), in its place on this side?"""
    wk = pred["wake"]
    return (o["k"] == "w" and members.get(o["fld"], o["fld"]) == wk["donor"] and o["sid"] == wk["sid"]
            and o["tag"] == wk["tag"] and target(o) == wk["target"] and o["new"] in wk["value"])


# ======================================================================== the F5 side, constructed
def hub_rows(s_rows: list, pred: dict, hub_sites: list) -> list:
    """The hub's rows as its engine would write them on New Game's state after the field-70 lead-in: its Main_Init
    prologue -- 359's Main_Init's own idiom (Bit[191], Bit[184], Int16[9], Byte[13], Int16[11], Byte[14] and their
    branches), which on the same state takes the same branches: so each of the partner's FIRST 359 prologue rows at
    the hub's site with the same target and value -- then the three frozen stamps. ``old`` is re-seated later."""
    H = pred["hub"]
    hid = H["id"]
    at = next(i for i, o in enumerate(s_rows) if o["k"] in ("w", "r") and o["fld"] == 359)
    first = s_rows[at]
    out = []
    for o in s_rows[at:]:
        if o["k"] != "w" or o["fld"] != 359 or (o["sid"], o["tag"]) != (0, 0):
            break
        if target(o) not in H["prologue_targets"]:
            break
        mask = (1 << (8 * T.WIDTH_BYTES[o["w"]])) - 1
        site = next(s for s in hub_sites if (s["sid"], s["tag"], s["target"]) == (0, 0, target(o))
                    and s["value"] is not None and s["value"] & mask == o["new"] & mask)
        out.append(dict(o, fld=hid, don=hid, ip=site["ip"]))
    for st in H["stamp"]:
        w, byte, bit = parse_target(st["target"])
        out.append({"k": "w", "f": first["f"], "p": first["p"], "m": 1, "fld": hid, "don": hid, "sc": pred["beat"],
                    "src": "eb", "sid": st["sid"],
                    "uid": st["sid"], "lvl": 0, "ip": st["ip"], "tag": st["tag"], "add": 0, "byte": byte, "w": w,
                    "bit": bit, "old": st["old"], "new": st["new"], "same": int(st["old"] == st["new"])})
    return out


def f5_entries(s_rows: list, pred: dict, members: dict, hub_sites: list, *, until: int | None = None,
               hub: list | None = None) -> list:
    """F5's run as re-seat entries, built from its partner's rows (the module docstring): relabelled into the members
    (``until`` None: 450 is a member; 450: the F0 layout, rows from 450 on left in the real fields), the hub's rows
    (``hub``, default :func:`hub_rows`) inserted before the first row in 359, ``sc`` the beat from the stamp to the
    wake."""
    rel = RD.relabel(s_rows, members, until=until)
    entries = [["both", s, f] for s, f in zip(s_rows, rel)]
    at = next(i for i, (_k, s, _f) in enumerate(entries) if s["k"] in ("w", "r") and s["fld"] == 359)
    hub = hub_rows(s_rows, pred, hub_sites) if hub is None else hub
    entries[at:at] = [["new", None, h] for h in hub]
    stamp = next((i for i, (_k, _s, f) in enumerate(entries) if f["fld"] == pred["hub"]["id"]
                  and f["k"] == "w" and f["sid"] == pred["hub"]["stamp"][0]["sid"]), None)
    wake = next((i for i, (_k, _s, f) in enumerate(entries) if is_wake(f, pred, members)), None)
    if stamp is not None and wake is not None:
        for e in entries[stamp:wake + 1]:
            if e[2]["k"] in ("w", "r", "e"):
                e[2] = dict(e[2], sc=pred["beat"])
    return entries


def f5_log(pred: dict, walk: list, hub_rec: dict | None = None, **kw) -> dict:
    """An F5 run's log: rung3_dryrun.replay_log of ``walk`` (its keywords: a cut, a divergence, the stop), led by the
    hub leg's record, its segment record handing control back in member(352)."""
    lg = RD.replay_log(pred, walk, **kw)
    seg = dict(lg["log"][0], field=M.chain_map(pred)[pred["segment_place"]])
    hub = hub_rec if hub_rec is not None else HUB_REC
    return dict(lg, log=[dict(hub), seg, *lg["log"][1:]])


#: the hub leg's log record (hub_leg's keys; the numbers are a constructed leg's, not a measurement)
HUB_REC = {"k": "hub", "narrator": [480, 127], "r": 16, "talk_r": 48, "approach": [440, 127, 40.0], "walked": True,
           "tries": 1, "turns": 0, "nudges": 0, "at": [440, 127], "options": ["Dali (SC 2600)", "Stay here, kupo..."],
           "cursor": 0, "picked": "Dali (SC 2600)", "presses": 1, "t": 38.0}
#: stops the hub leg can raise after its stamps landed: its own budget (DRIVE by pattern -- it is never read after the
#: Confirm, so in a real run it cannot come after a stamp; the guard proves the class holds even if it did), the
#: landing's own wait timing out live (FORK-STOP "hub" with no row in 31111), and a poll's ack (neither: UNCLASSED)
BUDGET_STOP = "STOPPED: HarnessError: hub leg: budget -- the leg's hub_s ran out"
LANDING_STOP = ("STOPPED: HarnessError: timed out after 60s waiting for the pick to land in 31111 over 3412 live "
                "samples (last state: State(field_id=31100))")
POLL_STOP = ("STOPPED: HarnessError: steps ['wait 4'] were not acknowledged within 60s (the agent is alive; last "
             "state: None)")


# ======================================================================== world edits (before the re-seat) and cuts
def lose(entries: list, which) -> list:
    """``entries`` with every w/r row ``which(row)`` names LOST on this side -- a row both worlds wrote becomes S's
    alone (``"s"``: the worlds differ on its bits from then on), a row only this side wrote is gone -- and a count row
    whose site emits no row any more goes too (the engine counts only at a site it emitted)."""
    out = []
    for k, s, f in entries:
        if k != "s" and f["k"] in ("w", "r") and which(f):
            if k == "both":
                out.append(["s", s, None])
            continue
        out.append([k, s, f])
    live = {RD.site(f) for k, _s, f in out if k != "s" and f["k"] == "w"}
    return [e for e in out if e[0] == "s" or e[2]["k"] != "c" or RD.site(e[2]) in live]


def edit(entries: list, which, **change) -> list:
    """``entries`` with every row of this side ``which(row)`` names changed (its old is re-seated after)."""
    return [[k, s, dict(f, **change) if k != "s" and which(f) else f] for k, s, f in entries]


def insert(entries: list, at: int, rows: list) -> list:
    """``rows`` written by this side alone, before entry ``at``."""
    return entries[:at] + [["new", None, r] for r in rows] + entries[at:]


def find(entries: list, which, *, after: int = 0) -> int:
    """The index of the first entry at or after ``after`` whose row on this side ``which(row)`` names."""
    return next(i for i, (k, _s, f) in enumerate(entries) if i >= after and k != "s" and which(f))


def cut(rows: list, at: int) -> list:
    """A run that stopped before row ``at``: its rows up to there (a count row closes an epoch, so none survives the
    cut) and the ``off`` epoch the collection's ``storytrace 0`` writes."""
    keep = [o for o in rows[:at] if o["k"] != "c"]
    last = keep[-1]
    return keep + [{"k": "e", "f": last["f"], "p": last["p"], "m": 1, "fld": last["fld"], "don": last["don"],
                    "sc": last["sc"], "why": "off"}]


def step_at(rows: list, pred: dict, members: dict, walk: list, n: int) -> int:
    """The row where step ``n`` (1-based) of the ENTERED WALK ``walk`` lands -- off the rows themselves: from the
    wake's room, every change of place but one OUT of a room in rung3_dryrun.BOUNCERS (its arrival scene putting him
    back) is a step; checked against ``walk`` step for step."""
    wk = next(i for i, o in enumerate(rows) if is_wake(o, pred, members))
    here, steps = pred["wake"]["donor"], []
    for i, o in enumerate(rows[wk:], wk):
        if o["k"] == "c":
            continue
        place = members.get(o["fld"], o["fld"])
        if place != here:
            if here not in RD.BOUNCERS:
                steps.append((i, here, place))
            here = place
    got = [[a, b] for _i, a, b in steps[:len(walk)]]
    assert got == [[a, b] for a, _e, b in walk], f"the rows' walk {got} is not the log's"
    return steps[n - 1][0]

# ======================================================================== a constructed session
def write_session(d: Path, plan: list, *, snap: dict, pred_path: Path = M.PREDICTIONS, sha: str | None = None) -> None:
    """A session dir as rung5_hub.run leaves one: ``plan`` = ``[{side, rows, log, rec}]`` in run order (``rows`` /
    ``log`` None: no file), the session record (naming the predictions file and its sha256, as the session does),
    the scripts snapshot."""
    pred, real_sha = M.load_predictions(pred_path)
    if d.exists():
        shutil.rmtree(d)
    (d / "scripts").mkdir(parents=True)
    for fid, data in snap.items():
        (d / "scripts" / f"{fid}.eb").write_bytes(data)
    recs = []
    for i, run in enumerate(plan, 1):
        tn, ln = R.run_names(i, run["side"])
        rec = {"i": i, "side": run["side"], "start": pred["start"][run["side"]], "trace": tn, "log": ln, "t0": 0,
               "t1": 0, **run.get("rec", {})}
        if not (rec.get("skipped") or str(rec.get("install", "")).startswith("before")):
            if run.get("rows") is not None:
                (d / tn).write_text("".join(json.dumps(o, separators=(",", ":")) + "\n" for o in run["rows"]),
                                    encoding="utf-8")
            if run.get("log") is not None:
                (d / ln).write_text(json.dumps(run["log"]), encoding="utf-8")
                rec.setdefault("stop", run["log"]["stop"])
        recs.append(rec)
    (d / M.SESSION_FILE).write_text(json.dumps({"label": d.name, "predictions": str(pred_path),
                                                "predictions_sha256": sha or real_sha, "predictions_version": 3,
                                                "order": pred["order"], "started": "dry-run", "finished": "dry-run",
                                                "runs": recs}), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", help="an offline build of the 13 fields (<DIR>/<id>/ each, as build step 8 makes it); "
                                    "default: built here from rung5_forks.json's tomls into a temp dir")
    ap.add_argument("--keep", help="write the constructed sessions and builds here (default: a temp dir, removed)")
    ap.add_argument("--session4", default=str(SESSION4), help="session 4's run dir (story-rung3d); read only")
    ap.add_argument("--session3", default=str(SESSION3), help="session 3's run dir (story-rung3c); read only")
    ap.add_argument("--pre-ambient", action="store_true",
                    help="build with ff9mapkit.content.ambient.restore_clear as identity (the pre-fix bytes, F5c)")
    a = ap.parse_args(argv)
    pa = a.pre_ambient
    pred, _sha = M.load_predictions()
    man = json.loads(M.MANIFEST.read_text(encoding="utf-8"))
    members = M.chain(pred)
    hid = pred["hub"]["id"]
    root = Path(a.keep) if a.keep else Path(tempfile.mkdtemp(prefix="rung5dry-"))
    root.mkdir(parents=True, exist_ok=True)
    stock = T.stock_script_source()
    roots = D.mod_roots()
    bad, n_cases = 0, 0

    print("== THE BUILD")
    bdir = Path(a.build) if a.build else root / "build"
    if not a.build:
        build(bdir, manifest_tomls(man), pre_ambient=pa)
    ok_b, detail_b, snap = frozen_build(bdir, man)
    n_cases += 1
    bad += not ok_b
    print(f"  {'as registered' if ok_b else '!! BROKEN'}  the build {bdir}: {detail_b}")
    if not ok_b:
        print("  " + sha_miss_cause([M.built_eb(bdir, int(man["hub"]["id"]))], pre_ambient=pa))
        print("\nthe build is not the frozen one: nothing below would test the bytes the session deploys")
        return 1
    hub_sites = M.global_stores(snap[hid], field_id=hid)

    # -- the stock side: session 4's S#1/S#4/S#7, as runs 1, 3, 5 ---------------------------------------------
    s4 = Path(a.session4)
    sess4 = json.loads((s4 / R.SESSION_FILE).read_text(encoding="utf-8"))

    def stock_run(d: Path, sess: dict, k: int) -> tuple:
        """``(rows, log, rec)`` of a recorded stock run ``k``, read only."""
        rec = next(r for r in sess["runs"] if r["i"] == k)
        return (rows_of(d / rec["trace"]), json.loads((d / rec["log"]).read_text(encoding="utf-8")),
                {x: v for x, v in rec.items() if x in ("segment", "traced", "crossings", "landed", "fields")})

    s_rows, s_logs, s_recs = {}, {}, {}
    for i, k in S_OF.items():
        s_rows[i], s_logs[i], s_recs[i] = stock_run(s4, sess4, k)
    walks = {i: D.entered_walk(s_logs[i]["log"]) for i in S_OF}
    order = pred["order"]
    partner = {i: R.round_partner(order, i) for i, s in enumerate(order, 1) if s == "F5"}
    cmap = M.chain_map(pred)
    m_of = lambda donor: cmap[donor]                                          # noqa: E731

    def f5(p: int, xform=None, *, rows=None, **kw) -> list:
        """F5's rows partnering stock run ``p`` (``rows``: that partner's rows, default S#p's), the world edited by
        ``xform(entries)`` before the re-seat."""
        e = f5_entries(s_rows[p] if rows is None else rows, pred, members, hub_sites, **kw)
        return reseat(xform(e) if xform else e)

    def s_side(p: int, xform) -> list:
        """Stock run ``p``'s rows with the world edited by ``xform(entries)`` (its olds re-seated)."""
        return reseat(xform([["both", o, dict(o)] for o in s_rows[p]]))

    base_f5 = {p: f5(p) for p in S_OF}

    def s_run(i: int, rows=None, log=None, **rec) -> dict:
        return {"side": "S", "rows": s_rows[i] if rows is None else rows, "log": s_logs[i] if log is None else log,
                "rec": {**s_recs[i], "phase": "settle", **rec}}

    def f5_run(p: int, rows=None, log=None, **rec) -> dict:
        return {"side": "F5", "rows": base_f5[p] if rows is None else rows,
                "log": f5_log(pred, walks[p]) if log is None else log,
                "rec": {"partner": p, "walk": walks[p], "phase": "settle", "traced": 1, **rec}}

    def skipped(i: int, side: str) -> dict:
        """Run ``i`` recorded and not driven: the session's budget was spent (no trace, no log)."""
        return {"side": side, "rows": None, "log": None,
                "rec": {"skipped": "session budget: under 720s of the 10800s left",
                        **({"partner": partner[i]} if side == "F5" else {})}}

    def plan(runs=None, extra=()) -> list:
        """The frozen six (S#1 F5#2 S#3 F5#4 S#5 F5#6, each F5 on its round's S), ``runs`` ``{i: run}`` overriding
        slot i, then the re-runs ``extra`` (each marked a re-run, as the session marks one)."""
        out = [(runs or {}).get(i) or (s_run(i) if s == "S" else f5_run(partner[i])) for i, s in enumerate(order, 1)]
        return out + [dict(r, rec=dict(r["rec"], rerun=True)) for r in extra]

    def every_f5(fn) -> dict:
        """``{i: fn(partner)}`` for the three F5 runs."""
        return {i: fn(p) for i, p in partner.items()}

    def case(name: str, plan_: list, *, snap_=None, sha=None) -> tuple:
        """One constructed session, analysed: ``({check: (word, detail)}, reports, judged runs)``."""
        d = root / name
        write_session(d, plan_, snap=snap_ or snap, sha=sha)
        checks, reports = M.analyse5(d, stock=stock, roots=roots)
        session = json.loads((d / M.SESSION_FILE).read_text(encoding="utf-8"))
        runs = M.read_session5(d, pred, stock=stock, roots=roots, session=session)
        return {what.split(":")[0]: (WORD[ok], detail) for ok, what, detail in checks}, reports, runs

    # -- the BASE ---------------------------------------------------------------------------------------------
    got, reports, _runs = case("base", plan())
    print("\n== BASE (S = session 4's S#1/S#4/S#7; F5 = each partner's rows relabelled into the members, the hub's "
          "rows before 359, re-seated)")
    stamps_ok = all([(o["old"], o["new"]) for o in base_f5[p] if o["fld"] == hid and o["sid"] == 2]
                    == [(s["old"], s["new"]) for s in pred["hub"]["stamp"]] for p in S_OF)
    base_ok = all(st == "PASS" for st, _d in got.values()) and stamps_ok
    for k, (st, detail) in got.items():
        print(f"  {st}  {k:<14} {detail[:300]}")
    print(f"  the re-seated stamp rows read the frozen old/new values: {stamps_ok}")
    if a.keep:
        for name, text in reports.items():
            (root / "base" / name).write_text(text, encoding="utf-8")

    # -- rows and logs the mutants are made of ---------------------------------------------------------------
    def wake_at(rows: list) -> int:
        return next(i for i, o in enumerate(rows) if is_wake(o, pred, members))

    def at_step(p: int, n: int, rows=None) -> int:
        return step_at(base_f5[p] if rows is None else rows, pred, members, walks[p], n)

    def replay_stop(p: int, n: int, *, entered: int | None = None, why: str | None = None) -> dict:
        """F5's log when its replay of S#p's walk broke at step ``n``: it ENTERED ``entered`` there (a divergence),
        or -- ``why`` -- it stopped before entering anything."""
        w = walks[p]
        where = f"replay broke at step {n} ({D.step_name(w[n - 1])})"
        if entered is None:
            return f5_log(pred, w, steps=n - 1, moved_at=len(w) + 1, stop=f"{where}: {why}")
        lg = f5_log(pred, w, steps=n, moved_at=len(w) + 1, diverge_at=n, stop=f"{where}: entered {entered}")
        lg["log"][-1].update(entered=entered, landed=entered, now=entered, verdict=f"diverged: entered {entered}")
        return lg

    def stop15(p: int) -> dict:
        """An F5 run on S#p whose replay DIVERGED at step 15 -- it entered member(355) where S#p entered 450."""
        return f5_run(p, cut(base_f5[p], at_step(p, 15)), replay_stop(p, 15, entered=355))

    def stall(p: int) -> dict:
        """An F5 run on S#p whose segment stalled in member(352): no wake, control never handed back."""
        seg = {"k": "segment", "field": m_of(352), "place": 352, "sc": pred["beat"], "control": False, "woke": False,
               "ok": False, "at_beat": False}
        log = {"stop": f"segment: no control in {pred['segment_place']} at {pred['beat']} after the wake",
               "choices": [], "log": [dict(HUB_REC), seg]}
        return f5_run(p, cut(base_f5[p], wake_at(base_f5[p])), log, phase="segment", segment=seg)

    def soft_lock(p: int) -> dict:
        """An F5 run on S#p that raised a LIVE soft-lock in its replay, standing in member(350) at the beat (the
        harness's own error: control never came back): FORK-STOP scene@350@2600."""
        log = f5_log(pred, walks[p], steps=11, moved_at=len(walks[p]) + 1,
                     stop=f"STOPPED: HarnessError: control never returned within 900 live frames in field {m_of(350)}")
        return f5_run(p, cut(base_f5[p], at_step(p, 12)), log, phase="replay",
                      at={"field": m_of(350), "place": 350, "sc": pred["beat"]})

    def hub_store(like: dict, sid: int, tag: int, ip: int, tgt: str, new: int, **kw) -> dict:
        """A hub store row (its old re-seated)."""
        w, byte, bit = parse_target(tgt)
        return dict(like, sid=sid, uid=sid, tag=tag, ip=ip, w=w, byte=byte, bit=bit, old=0, new=new, same=0, **kw)

    def hub_of(p: int, fn) -> list:
        """The hub's rows for S#p's partner, edited by ``fn``."""
        return fn(hub_rows(s_rows[p], pred, hub_sites))

    def last_stamp(h: list) -> dict:
        return [o for o in h if o["sid"] == 2][-1]

    in_members = lambda f: f["fld"] in members                                 # noqa: E731

    def hub_raised(p: int) -> dict:
        """The hub leg raised before the pick (no dialogue): New Game's residue and the hub's PROLOGUE only."""
        rows = f5(p, hub=[h for h in hub_rows(s_rows[p], pred, hub_sites) if h["sid"] == 0])
        log = {"stop": "STOPPED: HarnessError: hub leg: no dialogue after 3 tries at [440, 127] (Stiltzkin at "
                       "[480, 127], r 16, talk_r 48)", "choices": [], "log": []}
        return f5_run(p, cut(rows, next(i for i, o in enumerate(rows) if in_members(o))), log, phase="hub",
                      at={"field": hid, "place": hid, "sc": pred["start_sc"]})

    def hub_died(p: int) -> dict:
        """The game died in the hub AFTER the stamps (the pick's warp never landed): New Game's residue, the hub's
        prologue and its three stamps, and NO ``off`` -- the collection's ``storytrace 0`` never reached a dead game,
        so the trace never closed. A game death is DRIVE (the frozen stop-class rule), never FORK-STOP "hub"."""
        rows = f5(p)
        keep = [o for o in rows[:next(i for i, o in enumerate(rows) if in_members(o))] if o["k"] != "c"]
        log = {"stop": "STOPPED: HarnessError: press confirm 4 not acknowledged within 60s", "choices": [],
               "log": []}
        return f5_run(p, keep, log, phase="hub", at={})

    def entry_row(rows: list) -> int:
        """The index of the run's first w/r row in 31111 (member(359))."""
        return next(i for i, o in enumerate(rows) if o["k"] in ("w", "r") and o["fld"] == pred["start"]["F5"])

    def entry_stall(p: int) -> dict:
        """The stamps landed, the hub leg RETURNED in 31111 (phase segment), then a live soft-lock stopped the run
        before member(359) wrote any traced row: its rows New Game's and the hub's, closed; no segment record (the
        segment loop raised in watch_cutscene); rec.at in 31111 -- the reviewers' m7."""
        rows = cut(base_f5[p], entry_row(base_f5[p]))
        log = {"stop": "STOPPED: HarnessError: control never returned within 300s across 9000 live frames -- the game "
                       "holds it", "choices": [], "log": [dict(HUB_REC)]}
        return f5_run(p, rows, log, phase="segment", at={"field": m_of(359), "place": 359, "sc": pred["beat"]})

    def hub_late(p: int, stop: str, extra: int) -> dict:
        """The stamps landed and the hub leg then RAISED ``stop`` (phase hub), the collection cutting the trace
        ``extra`` rows into 31111 (0: before any row there -- the landing never traced)."""
        rows = cut(base_f5[p], entry_row(base_f5[p]) + extra)
        log = {"stop": stop, "choices": [], "log": [dict(HUB_REC, error=stop.split("STOPPED: ", 1)[1], t=179.9)]}
        return f5_run(p, rows, log, phase="hub", at={"field": hid, "place": hid, "sc": pred["beat"]})

    def wrong_entry(p: int) -> dict:
        """The stamps landed, then the pick's Field() led to member(352) (31104), never to 31111: the hub leg's
        wait for 31111 timed out there. Its rows: New Game's, the hub's, then 352's arrival rows in 31104."""
        e = f5_entries(s_rows[p], pred, members, hub_sites)
        at = find(e, in_members)
        j = find(e, lambda f: f["fld"] == m_of(352), after=at)
        visit = []
        for k_, _s, f in e[j:]:
            if f["k"] == "c" or f["fld"] != m_of(352):
                break
            visit.append(dict(f))
        e = e[:at] + [["new", None, r] for r in visit] + [["s", s, None] for k_, s, f in e[at:]
                                                          if k_ == "both" and s["k"] in ("w", "r")]
        rows = reseat(e)
        log = {"stop": f"STOPPED: HarnessError: timed out after 142s waiting for the pick to land in "
                       f"{pred['start']['F5']} over 812 live samples", "choices": [], "log": []}
        return f5_run(p, cut(rows, len(rows)), log, phase="hub", at={"field": m_of(352), "place": 352,
                                                                     "sc": pred["beat"]})

    def extra_key(e: list) -> list:
        """One value no donor writes: member(350)'s first Int16 store after the wake written again, +7 (the site's
        own instruction, so it joins) -- the rung-3 dry-run's FORK ONLY key."""
        w = find(e, lambda f: is_wake(f, pred, members))
        j = find(e, lambda f: f["k"] == "w" and f["fld"] == m_of(350) and f["w"] == "Int16", after=w)
        f = e[j][2]
        return insert(e, j + 1, [dict(f, old=0, new=f["new"] + 7, same=0)])

    # a stock key every S run writes once, in the tour, at a site with one row and no count, that no pattern reads:
    # the key a mutant drops from F5
    pats = [*pred["coverage"]["ran"], pred["coverage"]["flip"], pred["wake"], *pred["checks"]["R5-SAME"]["stores"],
            pred["checks"]["R5-PING"]["pattern"], pred["checks"]["R5-ADVANCE"]["pattern"],
            *pred["checks"]["R5-LATCH"]["patterns"]]
    sd = {i: T.digest(f"S#{i}", [T.parse_row(o, line=n) for n, o in enumerate(s_rows[i], 1)], scripts=stock)
          for i in S_OF}

    def one_row_site(i: int, o) -> bool:
        st = [x for x in s_rows[i] if x["k"] in ("w", "c") and RD.site(x)[1:] == o.row.site[1:]
              and x["fld"] == o.row.fld]
        return len(st) == 1 and st[0]["k"] == "w"

    common = set.intersection(*(set(d.keys) for d in sd.values()))
    drop_key = next(k for k, o in sorted(sd[1].keys.items(), key=lambda ko: ko[1].at)
                    if k in common and o.at > wake_at(s_rows[1]) + 30 and o.row.src == "eb" and not o.counted
                    and 350 <= o.row.fld <= 358 and k.target != "Global.UInt16[0]" and not M._is_timing(k, pred)
                    and not any(R._matches(p_, k) for p_ in pats) and all(one_row_site(i, sd[i].keys[k]) for i in S_OF))
    drop_site = sd[1].keys[drop_key].row.site

    def at_drop_site(f: dict) -> bool:
        return f["k"] in ("w", "c") and (members.get(f["fld"], f["fld"]), *RD.site(f)[1:]) == drop_site

    # member(351)'s e4 Main_Init store Global.SByte[296] := 65472, made a WORD store: the clobber mutant's site
    clob = (m_of(351), 4, 0, 22)
    snap_clob = dict(snap)
    e4 = T.ScriptIndex(snap[clob[0]]).eb.entries[clob[1]]
    at_tok = e4.abs_start + clob[3] + 1
    assert snap[clob[0]][at_tok] == 0xF0, "member(351) e4 +12: the SByte[296] token moved"
    snap_clob[clob[0]] = snap[clob[0]][:at_tok] + bytes([0xFC]) + snap[clob[0]][at_tok + 1:]

    def clobber(e: list) -> list:
        """Every row of the clobber site written as the WORD store the patched member runs (UInt16[296] := 65472):
        its SByte row lost, a UInt16 row in its place, its count rows the word's."""
        out = []
        for k_, s, f in e:
            if k_ == "both" and f["k"] in ("w", "c") and (f["fld"], f["sid"], f["tag"], f["ip"]) == clob \
                    and target(f) == "Global.SByte[296]":
                if f["k"] == "w":
                    out += [["s", s, None], ["new", None, dict(f, w="UInt16", old=0, new=65472, same=0)]]
                else:
                    out.append([k_, s, dict(f, w="UInt16", last=65472)])
                continue
            out.append([k_, s, f])
        return out

    adv = pred["checks"]["R5-ADVANCE"]["pattern"]
    is_adv = lambda f: (f["k"] == "w" and f["fld"] == m_of(adv["donor"])  # noqa: E731 -- 354 e13 t1 SC := 2610
                        and (f["sid"], f["tag"], target(f)) == (adv["sid"], adv["tag"], adv["target"])
                        and f["new"] in adv["value"])
    is_2085 = lambda f: f["k"] in ("w", "c") and f["fld"] == m_of(450) and target(f) == "Global.Bit[2085]"  # noqa: E731

    def lone_member_row(rows: list) -> int:
        """A member store after the wake whose site has that one row and no count: an ip moved there moves one key."""
        w = wake_at(rows)
        sites = Counter(RD.site(o) for o in rows if o["k"] in ("w", "c"))
        return next(i for i, o in enumerate(rows) if i > w + 20 and o["k"] == "w" and in_members(o)
                    and sites[RD.site(o)] == 1)

    timing = pred["timing_site"]

    def more_timing(e: list) -> list:
        """Two more Confirm frames at the timing site (359 e5 t17 +49 Byte[299]) than the partner counted."""
        j = max(i for i, (k_, _s, f) in enumerate(e) if k_ != "s" and f["k"] == "w" and f["fld"] == m_of(359)
                and (f["sid"], f["tag"]) == (timing["sid"], timing["tag"]) and target(f) == timing["target"]
                and f["new"] > 0)
        f = e[j][2]
        return insert(e, j + 1, [dict(f, old=0, new=f["new"] + 1, same=0), dict(f, old=0, new=f["new"] + 2, same=0)])

    # F4's session-4 runs relabelled as F5 (rung 3's round-4 seed, its prepend bytes snapshotted under F5's ids)
    f4 = R.chain_members(R.load_predictions(R.PREDICTIONS)[0])["F4"]
    f4_to_f5 = {f: m_of(d) for f, d in f4.items()}
    snap_f4 = {**snap, **{f4_to_f5[f]: (s4 / "scripts" / f"{f}.eb").read_bytes() for f in f4}}

    def f4_as_f5(i: int) -> list:
        k = {2: 3, 4: 6, 6: 9}[i]
        return [dict(o, fld=f4_to_f5.get(o["fld"], o["fld"])) for o in rows_of(s4 / f"run{k}_F4.jsonl")]

    frozen21 = set(pred["stockstate"]["changed_from_new_game"])
    stamp_b = {int(b) for b in pred["stockstate"]["stamp_bytes"]}

    def extra_byte(e: list) -> list:
        """A same-value Byte store before the wake, on a byte no other row touches before it and outside the frozen
        21, the stamp bytes and 299, made to change (+5): the changed-from-New-Game set gains that byte."""
        rows = [f for _k, _s, f in e]
        w = wake_at(rows)
        touched = Counter(b >> 3 for o in rows[:w] if o["k"] in ("w", "r") for b in span_bits(o))
        j = next(i for i, o in enumerate(rows[:w]) if o["k"] == "w" and o["w"] == "Byte" and o["same"]
                 and o["byte"] not in frozen21 | stamp_b | {299} and touched[o["byte"]] == 8)
        e[j][2] = dict(e[j][2], new=(e[j][2]["new"] + 5) & 0xFF)
        return e

    s1_2078 = RD.drop_rows(s_rows[1], lambda i, o: o["k"] == "w" and o["fld"] == 352 and o["sid"] == 17
                           and o["tag"] == 1 and target(o) == "Global.Bit[2078]" and o["new"] == 1)
    untouched = 1500
    assert not any(o["k"] in ("w", "r") and untouched in {b >> 3 for b in span_bits(o)} for r in s_rows.values()
                   for o in r), f"byte {untouched} is touched by a stock row"
    s297 = lambda f: (f["k"] == "w" and members.get(f["fld"], f["fld"]) == 359  # noqa: E731 -- 359 +220, either side
                      and (f["sid"], f["tag"]) == (0, 0) and target(f) == "Global.UInt16[297]")

    with_extra = f5(1, extra_key)

    def all_f5(xform=None, **kw) -> list:
        """The frozen six, every F5 run's world edited by ``xform`` (and ``f5``'s keywords)."""
        return plan(every_f5(lambda p: f5_run(p, f5(p, xform, **kw))))

    def hub_mut(fn) -> list:
        """The frozen six, every F5 run's hub rows edited by ``fn``."""
        return plan(every_f5(lambda p: f5_run(p, f5(p, hub=hub_of(p, fn)))))
    lone = lone_member_row(base_f5[1])

    # -- the MUTANTS: each must come out as registered --------------------------------------------------------
    side_checks =["R5-RUNS", "R5-STATE", "R5-SAME", "R5-SEGMENT", "R5-PING", "R5-NOSEAM", "R5-MIRROR", "R5-PARTIAL",
                   "R5-ADVANCE", "R5-LATCH", "R5-PREEMPT"]
    p15 = f"replay@15({D.step_name(walks[1][14])})"          # the point names the step: replay@15(350.6 -> 450)
    f15 = ("FORK-STOP", p15)
    mutants = [
        dict(check="R5-REACH", verdict="FAIL", why="all 3 F5 runs break at replay step 15 (diverged: entered 355)",
             plan=plan(every_f5(stop15)), stops={2: f15, 4: f15, 6: f15}, halt=p15, void=side_checks),
        dict(check="R5-REACH", verdict="FAIL", why="all 3 F5 segments stall in member(352) with no wake",
             plan=plan(every_f5(stall)), stops={i: ("FORK-STOP", "segment@352") for i in partner},
             halt="segment@352"),
        dict(check="R5-REACH", verdict="FAIL", why="F5#2 FORK-STOPs at step 15, its re-run on S#1 stops at step 15",
             plan=plan({2: stop15(1)}, [stop15(1)]), stops={2: f15, 7: f15}, halt=p15,
             also={"R5-RUNS": "VOID"}, no_faults=True),
        dict(check="R5-RUNS", verdict="FAIL", why="a re-run after the halt (F5 on S#1 again, run 8)",
             plan=plan({2: stop15(1)}, [stop15(1), f5_run(1)]), need=["HALTED"]),
        dict(check="R5-REACH", verdict="VOID", why="one F5 FORK-STOP (F5#2 at step 15), reproduced nowhere: its "
                                                   "re-run on S#1 covered",
             plan=plan({2: stop15(1)}, [f5_run(1)]), stops={2: f15, 7: None}, halt=None,
             need=[f"F5#2 FORK-STOP @{p15}"], rest="PASS"),
        dict(check="R5-REACH", verdict="FAIL", why="(guard, the entry) F5#2 and its re-run on S#1: the stamps landed, "
                                                   "the leg returned in 31111, and a live soft-lock stopped each run "
                                                   "before member(359) wrote a row -- the segment class, never DRIVE",
             plan=plan({2: entry_stall(1)}, [entry_stall(1)]),
             stops={2: ("FORK-STOP", "segment@359"), 7: ("FORK-STOP", "segment@359")}, halt="segment@359",
             need=["F5#2 FORK-STOP @segment@359: STOPPED: HarnessError: control never returned within"],
             also={"R5-RUNS": "VOID"}, no_faults=True, undigested=[2, 7]),
        dict(check="R5-REACH", verdict="PASS", why="(guard, the hub leg's budget) F5#2's own hub_s ran out after its "
                                                   "stamps, no row in 31111 ('hub leg: budget' is DRIVE); its re-run "
                                                   "on S#1 covered",
             plan=plan({2: hub_late(1, BUDGET_STOP, 0)}, [f5_run(1)]), stops={2: ("DRIVE", None)},
             need=["F5#2 DRIVE: stop ", "STOPPED: HarnessError: hub leg: budget"], undigested=[2]),
        dict(check="R5-REACH", verdict="PASS", why="(guard, the hub leg's budget) F5#2's own hub_s ran out after its "
                                                   "stamps with member(359)'s first 40 rows already traced: DRIVE, "
                                                   "never UNCLASSED; its re-run on S#1 covered",
             plan=plan({2: hub_late(1, BUDGET_STOP, 40)}, [f5_run(1)]), stops={2: ("DRIVE", None)},
             need=["F5#2 DRIVE: stop ", "STOPPED: HarnessError: hub leg: budget"]),
        dict(check="R5-REACH", verdict="PASS", why="(guard, the landing) F5#2's landing wait timed out though its "
                                                   "trace has member(359)'s first 40 rows (its Field() had landed): "
                                                   "DRIVE, "
                                                   "the harness's view; its re-run on S#1 covered",
             plan=plan({2: hub_late(1, LANDING_STOP, 40)}, [f5_run(1)]), stops={2: ("DRIVE", None)},
             need=["F5#2 DRIVE: the hub leg raised though the trace has rows in 31111"]),
        dict(check="R5-REACH", verdict="VOID", why="(guard, the hub FORK-STOP's text) F5#2's stamps landed, no row in "
                                                   "31111, and its stop is a poll's ack, not the landing's own "
                                                   "timeout: UNCLASSED; its re-run on S#1 covered",
             plan=plan({2: hub_late(1, POLL_STOP, 0)}, [f5_run(1)]), stops={2: ("UNCLASSED", None)},
             need=["F5#2 UNCLASSED: the stamps landed and 31111 was never reached, but the stop is not the landing's"],
             undigested=[2]),
        dict(check="R5-PREFIX", verdict="FAIL", why="a truncated F5 run (a DRIVE stop, the session's budget, at step "
                                                    "16) carrying one key its partner lacks",
             plan=plan({2: f5_run(1, cut(with_extra, at_step(1, 16, with_extra)),
                                  f5_log(pred, walks[1], steps=15, moved_at=len(walks[1]) + 1,
                                         stop="session budget spent (replay step 16 of 24, crossings 15, 900s)"))}),
             stops={2: ("DRIVE", None)}, need=["F5#2 (partner S#1, DRIVE)"]),
        dict(check="R5-REACH", verdict="PASS", why="F5#2 stops on 'the gated door was never faced' (DRIVE), its re-run "
                                                   "on S#1 covered: R5-REACH unaffected",
             plan=plan({2: f5_run(1, cut(base_f5[1], at_step(1, 9)),
                                  replay_stop(1, 9, why="the gated door was never faced (2 times)"))}, [f5_run(1)]),
             stops={2: ("DRIVE", None)}),
        dict(check="R5-REACH", verdict="FAIL", why="(guard, the frozen stop-class table) F5#2 and its re-run on S#1 "
                                                   "both raise a live soft-lock in the replay, in member(350) at 2600",
             plan=plan({2: soft_lock(1)}, [soft_lock(1)]), stops={2: ("FORK-STOP", "scene@350@2600"),
                                                                 7: ("FORK-STOP", "scene@350@2600")},
             halt="scene@350@2600"),
        dict(check="R5-REACH", verdict="VOID", why="(guard, predictions 'implementation') F5#2 stops for a reason no "
                                                   "pattern names -- UNCLASSED keeps R5-REACH from PASS though its "
                                                   "re-run on S#1 is covered",
             plan=plan({2: f5_run(1, cut(base_f5[1], at_step(1, 12)), f5_log(
                 pred, walks[1], steps=11, moved_at=len(walks[1]) + 1,
                 stop="STOPPED: HarnessError: watch_cutscene timed out after 300s"), phase="replay",
                 at={"field": m_of(350), "place": 350, "sc": pred["beat"]})}, [f5_run(1)]),
             stops={2: ("UNCLASSED", None)}, need=["F5#2 UNCLASSED"]),
        dict(check="R5-JOIN", verdict="PASS", why="F5#2's hub leg raised before the pick (prologue rows only, no "
                                                  "31111): DRIVE, never digested; its re-run on S#1 covered",
             plan=plan({2: hub_raised(1)}, [f5_run(1)]), stops={2: ("DRIVE", None)}, need=["notes []"],
             also={"R5-DONOR": "PASS", "R5-STAMP": "PASS"}, undigested=[2]),
        dict(check="R5-PREFIX", verdict="VOID", why="(guard, the VOID branch) every F5 run's hub leg raised before the "
                                                    "pick: none reached 31111, none digested",
             plan=plan(every_f5(hub_raised)), need=["no such F5 run"], stops={i: ("DRIVE", None) for i in partner},
             also={"R5-STAMP": "VOID", "R5-DONOR": "PASS", "R5-JOIN": "PASS"},
             also_need={"R5-STAMP": ["only 0 F5 runs reached 31111"], "R5-DONOR": ["3 F5 runs read"]},
             undigested=list(partner)),
        dict(check="R5-JOIN", verdict="VOID", why="(guard, the VOID branch) every run skipped -- the session budget "
                                                  "spent before run 1: no trace read, none digested",
             plan=[skipped(i, s) for i, s in enumerate(order, 1)], need=["0 runs digested"],
             also={"R5-DONOR": "VOID", "R5-PREFIX": "VOID", "R5-STAMP": "VOID"},
             also_need={"R5-DONOR": ["no F5 run read"]}),
        dict(check="R5-REACH", verdict="PASS", why="(guard, the frozen stop-class rule) F5#2's game died in the hub "
                                                   "AFTER its stamps (no row in 31111, the trace never closed): DRIVE, "
                                                   "never FORK-STOP hub; its re-run on S#1 covered",
             plan=plan({2: hub_died(1)}, [f5_run(1)]), stops={2: ("DRIVE", None)},
             need=["F5#2 DRIVE: the trace never closed"], undigested=[2]),
        dict(check="R5-STAMP", verdict="FAIL", why="F5#2's stamps landed, then its first member row is in 31104 "
                                                   "(never 31111)",
             plan=plan({2: wrong_entry(1)}), stops={2: ("FORK-STOP", "hub")},
             need=["F5#2: entry: the first row after the hub stands in 31104"]),
        dict(check="R5-STAMP", verdict="FAIL", why="R5-STAMP fed r['pre'] (from_start's FIELD list) as its rows: the "
                                                   "base (the STAMP_SOURCE guard)",
             plan=plan(), stamp_source="pre", need=["list: the stamps are []"]),
        dict(check="R5-STAMP", verdict="FAIL", why="the 297 stamp dropped",
             plan=hub_mut(lambda h: [o for o in h if target(o) != "Global.UInt16[297]"]),
             need=["list: the stamps are [(23, 'Global.UInt16[0]', 2540, 2600), (31, 'Global.UInt16[208]', 0, 0)], "
                   "not the frozen"]),
        dict(check="R5-STAMP", verdict="FAIL", why="a hub Bit write (e2 t3 ip 161 Bit[2078] := 1)",
             plan=hub_mut(lambda h: h + [hub_store(last_stamp(h), 2, 3, 161, "Global.Bit[2078]", 1)]),
             need=["list: the stamps are [", "(None, 'Global.Bit[2078]', 0, 1)], not the frozen"]),
        dict(check="R5-STAMP", verdict="FAIL", why="the hub rows carry don 351",
             plan=hub_mut(lambda h: [dict(o, don=351) for o in h]),
             need=["don 351"], also={"R5-DONOR": "FAIL"}),
        dict(check="R5-STAMP", verdict="FAIL", why="a hub stamp's ip off by one (SC at 137)",
             plan=hub_mut(lambda h: [dict(o, ip=o["ip"] + 1) if target(o) == "Global.UInt16[0]" else o for o in h]),
             need=["not an instruction boundary"]),
        dict(check="R5-STAMP", verdict="FAIL", why="a hub UInt16[296] := 192 after the 297 stamp: its exact list AND "
                                                   "its width clause",
             plan=hub_mut(lambda h: h + [hub_store(last_stamp(h), 2, 3, 161, "Global.UInt16[296]", 192)]),
             need=["width: Global.UInt16[296] = 192 changed byte 297", "list: the stamps are"]),
        dict(check="R5-STOCKSTATE", verdict="FAIL", why="stock 359 +220 UInt16[297] := 3 (every stock run)",
             plan=plan({i: s_run(i, s_side(i, lambda e: edit(e, s297, new=3))) for i in S_OF}),
             need=["stamp bytes"]),
        dict(check="R5-STOCKSTATE", verdict="FAIL", why="S#1 changes one more byte before the wake (a same-value Byte "
                                                        "store made to change)",
             plan=plan({1: s_run(1, s_side(1, extra_byte))}), need=["changed from New Game gains"]),
        dict(check="R5-STOCKSTATE", verdict="VOID", why="S#1's 352 +2096 Bit[2078] := 1 row dropped (not re-seated): "
                                                        "the calibration names the contradiction at 351's 2078 row",
             plan=plan({1: s_run(1, s1_2078)}), need=["S#1: 1 contradictions", "Global.Bit[2078]"],
             also={"R5-STATE": "VOID"}),
        dict(check="R5-STATE", verdict="FAIL", why="F4's session-4 rows relabelled as F5 (its prepend bytes as the "
                                                   "members')",
             plan=plan({i: f5_run(p, f4_as_f5(i), f5_log(pred, walks[p], moved_at=len(walks[p]) + 1, stop=EXHAUSTED))
                        for i, p in partner.items()}), snap=snap_f4,
             need=["238", "241", "251", "258", "259", "261", "297", "known on one side only", "909"],
             also={"R5-SEGMENT": "FAIL", "R5-PREEMPT": "FAIL"},
             also_need={"R5-SEGMENT": ["F5#2/S#1: F5 only 21 (17 prepend)",
                                       "S only 5 ['351 e0 t0 +791 Global.SByte[238]"],
                        "R5-PREEMPT": ["PRE-EMPTED [('Global.UInt16[0]', 2600)"]}),
        dict(check="R5-STATE", verdict="FAIL", why=f"a hub write to an untouched byte (e2 t3 ip 161 Byte[{untouched}] "
                                                   f":= 7)",
             plan=hub_mut(lambda h: h + [hub_store(last_stamp(h), 2, 3, 161, f"Global.Byte[{untouched}]", 7)]),
             need=[f"known on one side only [{untouched}]"]),
        dict(check="R5-SAME", verdict="FAIL", why="297 changing in F5#4 (359 +220 old 0, same 0)",
             plan=plan({4: f5_run(3, [dict(o, old=0, same=0) if s297(o) else o for o in base_f5[3]])}),
             need=["F5#4: 359 Main_Init +220 UInt16[297] := 1 in 31111 old 0 same 0"]),
        dict(check="R5-NOSEAM", verdict="FAIL", why="rows from 450 on left in the real fields (F0-style)",
             plan=all_f5(until=450), also={"R5-PING": "FAIL"},
             need=["seams ['member(350) [fork 31103] -> 450']", "rows outside the members in [",
                   "450 never entered as member 31112"]),
        dict(check="R5-PARTIAL", verdict="FAIL", why=f"a key dropped from F5#4 ({drop_key.donor} e{drop_key.sid} "
                                                     f"t{drop_key.tag} {drop_key.off:+d} {drop_key.target} = "
                                                     f"{drop_key.value})",
             plan=plan({4: f5_run(3, f5(3, lambda e: lose(e, at_drop_site)))}), need=["F5#4/S#3"]),
        dict(check="R5-MIRROR", verdict="FAIL", why="the same key dropped from every F5 run (STOCK ONLY)",
             plan=all_f5(lambda e: lose(e, at_drop_site)),
             need=["1 STOCK ONLY"]),
        dict(check="R5-MIRROR", verdict="FAIL", why="an extra F5 key in every F5 run (FORK ONLY)",
             plan=all_f5(extra_key), need=["1 FORK ONLY"]),
        dict(check="R5-MIRROR", verdict="FAIL", why="a member word store clobbering 297 (member(351) e4 SByte[296] "
                                                    "run as UInt16[296] := 65472)",
             plan=all_f5(clobber), snap=snap_clob,
             need=["1 clobbers"], also={"R5-LATCH": "FAIL"}),
        dict(check="R5-ADVANCE", verdict="FAIL", why="the 2610 row moved to member(356) in every F5 run",
             plan=all_f5(lambda e: edit(e, is_adv, fld=m_of(356), don=356)),
             need=[f"is w in {m_of(356)} (don 356)"]),
        dict(check="R5-ADVANCE", verdict="FAIL", why="F5#6 replays all 24 steps and never advances (the story never "
                                                     "moves on: passes exhausted)",
             plan=plan({6: f5_run(5, cut(base_f5[5], next(i for i, o in enumerate(base_f5[5]) if is_adv(o))),
                                  f5_log(pred, walks[5], moved_at=len(walks[5]) + 1, stop=EXHAUSTED))}),
             need=["F5#6: never reached SC 2610"], stops={6: None}),
        dict(check="R5-LATCH", verdict="FAIL", why="Bit[2085] := 1 (450 e19) dropped from every F5 run",
             plan=all_f5(lambda e: lose(e, is_2085)), need=["Bit[2085]"]),
        dict(check="R5-JOIN", verdict="FAIL", why="one member row's ip off by one (F5#2)",
             plan=plan({2: f5_run(1, [dict(o, ip=o["ip"] + 1) if n == lone else o
                                      for n, o in enumerate(base_f5[1])])}), need=["1 failures"]),
        dict(check="R5-DONOR", verdict="FAIL", why="one member row with don 999 (F5#2)",
             plan=plan({2: f5_run(1, [dict(o, don=999) if n == lone else o
                                      for n, o in enumerate(base_f5[1])])}), need=["don 999 (want"]),
        dict(check="R5-RUNS", verdict="FAIL", why="the wrong order (S F5 F5 S S F5)",
             plan=plan({3: f5_run(1), 4: s_run(3)}), need=["not the frozen order"]),
        dict(check="R5-RUNS", verdict="FAIL", why="the wrong partner (F5#4 partners S#1)",
             plan=plan({4: f5_run(1)}), need=["F5#4 partners S#1, not its round's S#3"]),
        dict(check="R5-RUNS", verdict="FAIL", why="two covered F5 runs on one partner (re-run F5 on S#1)",
             plan=plan(extra=[f5_run(1)]), need=["S#1 is partnered by 2 covered F5 runs"]),
        dict(check="P-FROZEN", verdict="FAIL", why="(guard) the predictions edited after the session recorded them",
             plan=plan(), sha="0" * 64),
    ]
    passes = [
        ("only the byte-299 keys differ (F5#4 counts two more Confirm frames at 359 e5 t17 +49 than S#3)",
         plan({4: f5_run(3, f5(3, more_timing))}), {}, None),
    ]

    # pairs whose walks differ BETWEEN pairs and agree within each: session 3's S#7 -- its own 23-step walk, whose
    # rooms took other SByte[296] / Int16[241] values than session 4's 24-step walks -- as S#3, F5#4 replaying it.
    # (Session 3's S#1, 21 steps, never wrote a tour key of 355 that the others did: the stock guard of R5-MIRROR is
    # then thin -- VOID by the frozen rule, rightly -- so it cannot stand for a walk that only reorders.)
    s3 = Path(a.session3)
    if (s3 / R.SESSION_FILE).is_file():
        sess3 = json.loads((s3 / R.SESSION_FILE).read_text(encoding="utf-8"))
        r3, l3, c3 = stock_run(s3, sess3, 7)
        w3 = D.entered_walk(l3["log"])
        s3_run = {"side": "S", "rows": r3, "log": l3, "rec": {**c3, "phase": "settle"}}
        passes.append((f"pairs whose walks differ between pairs (session 3's S#7, a {len(w3)}-step walk, as S#3 with "
                       f"F5#4 replaying it) and agree within each: listed",
                       plan({3: s3_run,
                             4: {"side": "F5", "rows": f5(3, rows=r3), "log": f5_log(pred, w3),
                                 "rec": {"partner": 3, "walk": w3, "phase": "settle", "traced": 1}}}),
                       {"R5-PARTIAL": "keys differ between pairs and agree within each"}, "R5-PARTIAL"))
        # one step NUMBER, two different walks: F5#2 breaks at step 15 of S#1's walk (350.6 -> 450), F5#4 at step 15
        # of session 3's S#7 walk (another crossing) -- two points, never a reproduction
        f5_3 = f5(3, rows=r3)
        name3 = D.step_name(w3[14])
        assert name3 != D.step_name(walks[1][14]), "the two walks' step 15 is one crossing: no case"
        mutants.append(dict(
            check="R5-REACH", verdict="VOID", why=f"(guard, the replay point) F5#2 breaks at step 15 of S#1's walk, "
                                                  f"F5#4 at step 15 of session 3's S#7 walk ({name3}): two points, no "
                                                  f"halt",
            plan=plan({2: stop15(1), 3: s3_run,
                       4: {"side": "F5", "rows": cut(f5_3, step_at(f5_3, pred, members, w3, 15)),
                           "log": f5_log(pred, w3, steps=14, moved_at=len(w3) + 1,
                                         stop=f"replay broke at step 15 ({name3}): bounce, bounce"),
                           "rec": {"partner": 3, "walk": w3, "phase": "replay", "traced": 1}}}),
            stops={2: f15, 4: ("FORK-STOP", f"replay@15({name3})")}, halt=None,
            need=[f"F5#2 FORK-STOP @{p15}", f"F5#4 FORK-STOP @replay@15({name3})"]))
    else:
        n_cases += 1
        bad += 1
        print(f"  !! MISSING  no session 3 at {s3}: the walks-differ case cannot run (--session3 DIR)")

    print("\n== MUTANTS (each must come out as registered: the verdict, and where registered the stop class, the "
          "halt, the VOIDs, the note)")
    for n, spec in enumerate(mutants):
        if spec.get("stamp_source"):
            M.STAMP_SOURCE = spec["stamp_source"]
        try:
            got_m, _rep, runs_m = case(f"mut-{n}", spec["plan"], snap_=spec.get("snap"), sha=spec.get("sha"))
        finally:
            M.STAMP_SOURCE = "raw"
        chk, want = spec["check"], spec["verdict"]
        st, detail = got_m.get(chk, (None, ""))
        probs = [] if st == want else [f"{chk} {st}"]
        probs += [f"the detail does not say {s!r}" for s in spec.get("need", ()) if s not in detail]
        probs += [f"{c} {got_m[c][0]} (registered {v})" for c, v in spec.get("also", {}).items() if got_m[c][0] != v]
        probs += [f"{c}'s detail does not say {s!r}" for c, ss in spec.get("also_need", {}).items() for s in ss
                  if s not in got_m[c][1]]
        probs += [f"{c} {got_m[c][0]} (registered VOID)" for c in spec.get("void", ()) if got_m[c][0] != "VOID"]
        if spec.get("rest"):
            named = {chk, *spec.get("also", {}), *spec.get("void", ())}
            probs += [f"{c} {w_} (registered {spec['rest']})" for c, (w_, _d) in got_m.items()
                      if c not in named and w_ != spec["rest"]]
        by = {r["i"]: r for r in runs_m}
        for i, cls in spec.get("stops", {}).items():
            sc = by[i].get("stop_class")
            have = None if sc is None else (sc["cls"], sc["point"])
            if have != cls:
                probs.append(f"{by[i]['label']} stop class {have} (registered {cls})")
        if "halt" in spec:
            h, nxt = M.halted(runs_m), M.rerun_plan5(runs_m, pred)
            if h != spec["halt"] or (h is not None and nxt is not None):
                probs.append(f"halted {h}, next {nxt} (registered halt {spec['halt']})")
        if spec.get("no_faults") and M.pairing_faults5(runs_m, pred):
            probs.append(f"pairing faults {M.pairing_faults5(runs_m, pred)[:2]}")
        probs += [f"{by[i]['label']} was digested" for i in spec.get("undigested", ()) if by[i]["digest"] is not None]
        n_cases += 1
        bad += bool(probs)
        others = [f"{c} {w_}" for c, (w_, _d) in got_m.items() if w_ != "PASS" and c != chk]
        print(f"  {'caught' if not probs else '!! MISSED'}  {chk:<13} {want:<4}  {spec['why']}"
              + (f" -- !! {'; '.join(probs)}" if probs else "")
              + f" || {detail[:150]}" + (f" || also not PASS: {', '.join(others)}" if others else ""))

    print("\n== CASES THAT MUST PASS")
    for n, (why, plan_, need, listed) in enumerate(passes):
        got_p, _rep, _runs = case(f"pass-{n}", plan_)
        probs = [f"{c} {w_}: {d[:140]}" for c, (w_, d) in got_p.items() if w_ != "PASS"]
        probs += [f"{c} does not say {s!r}" for c, s in need.items() if s not in got_p[c][1]]
        if listed and re.search(r"0 keys differ between pairs", got_p[listed][1]):
            probs.append(f"{listed} lists no key: the walks do not differ in what they wrote")
        n_cases += 1
        bad += bool(probs)
        print(f"  {'passes' if not probs else '!! BROKEN'}  {why}" + (f" -- !! {probs}" if probs else "")
              + "".join(f" || {c}: {got_p[c][1][:200]}" for c in need))

    # -- the OFFLINE PRE-FLIGHT --------------------------------------------------------------------------------
    print("\n== THE OFFLINE PRE-FLIGHT")
    from ff9mapkit.content.verbatim import remap_fields
    pre = []
    (ok_p, _w, d_p), (ok_h, _w2, d_h), _stores = M.offline_check(bdir, pred, stock)
    pre.append(("P-PURE + P-HUB", "PASS", "the frozen build: every member its donor remapped, the hub the frozen seed",
                "PASS" if ok_p and ok_h else "FAIL", f"{d_p} || {d_h}", []))
    less_450 = {d: f for d, f in cmap.items() if d != 450}
    unremapped = remap_fields(stock(350).data, less_450)
    ok_u, d_u = M.pure_check(pred, lambda f: unremapped if f == m_of(350) else snap.get(f), stock)
    pre.append(("P-PURE", "FAIL", f"{m_of(350)} built with 450 left unremapped (the F0 layout)", WORD[ok_u], d_u,
                [f"{m_of(350)}: not remap(stock 350)", f"{m_of(350)}: Field() targets outside the members [450"]))
    hub2610 = root / "hub2610"
    if hub2610.exists():
        shutil.rmtree(hub2610)
    hub2610.mkdir(parents=True)
    hub_dir = Path(man["hub"]["journeys"]).parent
    shutil.copy2(hub_dir / "camera_hub.bgx", hub2610 / "camera_hub.bgx")
    jt = (hub_dir / "journeys.toml").read_text(encoding="utf-8")
    assert jt.count("set_scenario = 2600") == 1
    (hub2610 / "journeys.toml").write_text(jt.replace("set_scenario = 2600", "set_scenario = 2610"), encoding="utf-8")
    kit(["gen-hub", hub2610 / "journeys.toml"], log=hub2610 / "gen-hub.log")
    kit(["build", hub2610 / "hub.field.toml", "--out", hub2610 / "build" / str(hid)], log=hub2610 / "build.log",
        pre_ambient=pa)
    ok_x, d_x, _st = M.hub_bytes_check(pred, M.built_eb(hub2610 / "build", hid))
    pre.append(("P-HUB", "FAIL", "a hub built with set_scenario 2610", WORD[ok_x], d_x, ["2610"]))
    seeded = root / "seeded"
    if seeded.exists():
        shutil.rmtree(seeded)
    shutil.copytree(Path(man["chains"]["F5"]["dir"]), seeded / "chain")
    kit(["story-seed", "--chain", seeded / "chain", "--beat", pred["beat"], "--census",
         Path(man["dir"]) / "research" / "dominance_census.json"], log=seeded / "story-seed.log")
    tomls = {int(f): seeded / "chain" / Path(t).relative_to(Path(man["chains"]["F5"]["dir"]))
             for f, t in man["chains"]["F5"]["tomls"].items()}
    build(seeded / "build", tomls, pre_ambient=pa)
    ok_s, d_s = M.pure_check(pred, lambda f: M.built_eb(seeded / "build", f), stock)
    n_bad = sum(1 for f, d in members.items() if M.built_eb(seeded / "build", f) != remap_fields(stock(d).data, cmap))
    pre.append(("P-PURE", "FAIL", "a chain seeded by story-seed WITHOUT --hub (each member a [startup] prepend)",
                WORD[ok_s], d_s, ["not remap(stock"]))
    merged = merged_root(bdir, root / "merged", [*members, hid])
    ran_m = T.mod_script_source([merged], fallback=stock)
    sides = M.tours5(pred, ran=ran_m, stock=stock)
    got_pf = M.preflight5(pred, [merged], stock, sides, ran=T.mod_script_source([merged]))
    names = [w.split(":")[0] for _ok, w, _d in got_pf]
    frozen_names = ["P-MANIFEST", "P-DEPLOY", "P-HUB", "P-PURE", "P-FLOOR", "P-EXITS", "P-STOCK"]
    fails = [f"{w.split(':')[0]}: {d[:120]}" for ok, w, d in got_pf if not ok]
    pre.append(("preflight5", "PASS", f"with only the sides {sorted(sides)}, over the offline build merged into one "
                                      f"mod root", "PASS" if not fails and names == frozen_names else "FAIL",
                f"{names}" + (f" -- {fails}" if fails else ""), []))
    for chk, want, why, st, detail, need in pre:
        probs = ([] if st == want else [f"{st}"]) + [f"the detail does not say {s!r}" for s in need if s not in detail]
        n_cases += 1
        bad += bool(probs)
        print(f"  {'as registered' if not probs else '!! WRONG'}  {chk:<14} {want:<4}  {why}"
              + (f" -- !! {'; '.join(probs)}" if probs else "") + f" || {detail[:220]}")
    print(f"  (the seeded chain: {n_bad} of {len(members)} members not their donor remapped)")

    n_cases += 1
    bad += not base_ok
    print(f"\nbase passes every check: {base_ok}; cases as registered: {n_cases - bad}/{n_cases}")
    if not a.keep:
        shutil.rmtree(root, ignore_errors=True)
    return 0 if base_ok and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
