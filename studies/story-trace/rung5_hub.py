"""THE STORY-WRITE TRACE, F5 -- THE HUB LANE UNDER THE TRACE: the kit's hub (a gen-hub field whose journey pick
stamps the seed, then warps into the zone) and 12 PURE verbatim Dali members, 450 among them, against stock Dali,
under THE PAIRED-WALK LAW.

    py tools/play.py studies/story-trace/rung5_hub.py --label story-rung5 --timeout 240     # the session
    py studies/story-trace/rung5_hub.py --analyse <run dir> [--predictions FILE]            # offline, on saved traces
    py studies/story-trace/rung5_hub.py --preflight                                         # the static P-checks, live
    py studies/story-trace/rung5_hub.py --offline-check <build dir> [--predictions FILE]    # the same, on a build

THE SIDES (rung5_forks.json; deployed to FF9CustomMap, ONE RELAUNCH before the session -- the session's own launch):
  S   stock Dali -- the install's scripts. Start: New Game, then `warp 359 0 2540` (rung 3's registered start).
  F5  the hub T5_HUB (31100) and 12 pure verbatim members 31101-31112 (`import-chain 351 --verbatim --ids
      312,350-359,450`; 450 is member 31112 -- no seam into the real 450). Start: New Game, then `warp 31100 0
      2540`, talk to Stiltzkin, pick "Dali (SC 2600)" (:func:`hub_leg`): the pick stamps SC 2600, words 208 = 0 and
      297 = 1, adds the party, and runs Field(31111) -- member(359), where stock starts.

THE SEED IS NOT COMPARED. Both sides are read from their first row in their 359 (``start`` S 359 / F5 31111,
rung3_trace.from_start): the hub's rows fall before the cut with New Game's field-70 residue. They are judged only as
the SEED -- R5-STAMP (the exact rows, joined against the hub's own snapshotted .eb), R5-SAME (their echo in the
members), R5-STATE (the state the seed lands on) -- and read from each run's RAW trace (:func:`read_run5` keeps it),
never from from_start's field list. 359 reads no SC and re-writes everything the stamp writes but the SC itself
(359.ebs:51-53, 66-68, 145-202), so from 31111 on both sides play the same scripted segment -- 359 -> 351 -> 352,
the night, the wake -- at SC 2600 against 2540, which no test on that path separates. That masking is registered
(predictions "known_gap"); it is what this entry cannot test.

THE WALK IS THE PARTNER'S (THE PAIRED-WALK LAW). S runs walk rung 3's blind tour; every F5 run REPLAYS its stock
partner's entered walk (dali_tour.Tour.replay), from the same session's launch. A round's F5 partners the round's S;
a re-run F5 the oldest COVERED S with no covered F5 twin on which fewer than ``max_breaks`` driven, non-covered F5
runs have been made (so a fork-caused stop is retried ONCE on the same walk -- a reproduction -- and a walk that
stops twice is partnered no more); S re-runs first while S is short, or for a fresh walk. THE HALT: once two F5
runs FORK-STOP at the same point, R5-REACH's FAIL is decided and no run can change it -- the session stops
re-running (:func:`rerun_plan5` returns None; R5-RUNS FAILs a run made after it).

COVERAGE, NOT OUTCOME, DECIDES WHAT A RUN IS (predictions "coverage"), as in rung 3: a run is COVERED only when the
drive gave it the chance to show what the checks read -- its trace closed, it stood in its start field, the segment
handed control back in 352 at 2600 AFTER the wake (the log's segment record and the trace's own wake store), its
stop is clean (S "SC left"; F5 "SC left", "passes exhausted" or "budget spent" -- F5 is NOT required to advance:
R5-ADVANCE judges that), 351's lobby exit and 450's e19 exit ran; on S the flip and SC 2610; on F5 its partner is
covered and its replay steps ARE the partner's walk (or its prefix, up to the crossing the story moved on at).

A FORK-CAUSED STOP IS NOT A DRIVE'S (predictions "coverage": "drive", "fork_stop"). Every VOID F5 run gets a STOP CLASS,
the DRIVE patterns tested first: DRIVE -- the walker's limit, a budget (the hub leg's own among them: it is never read
after the pick's Confirm, so it cannot stop a run whose stamps landed), a dead channel, the install, the title, an
unexpected error, a game death, a skip -- is never evidence; FORK-STOP -- the run stood in 31111 (or its stamps
landed) with a covered partner, and stopped where stock went on: "hub" (stamps landed, and the landing's own wait --
budget.entry_s, never the leg's time left -- timed out live with no row in 31111), "segment@<place>" (no wake, a
live soft-lock, a re-asked choice -- at the entry itself too, before member(359) wrote a row), "replay@<step>(<step
name>)" (a crossing entered another place, struck out REAL, or left him elsewhere; the step's name is in the point,
so one step number of two different walks is two points), "scene@<place>@<sc>" (a live soft-lock in the replay or
tour). Two FORK-STOPs at one point FAIL R5-REACH. A VOID run no pattern names is UNCLASSED: listed, and R5-REACH cannot
PASS while one stands. R5-PREFIX reads every F5 run that reached 31111, VOID ones included: its keys must be a
subset of its partner's (the walk is the partner's, so a prefix can only write what the partner wrote). It reads the
COVERED ones too: a covered F5 run whose story never moves on replays the whole walk, then tours blind (Tour.replay),
and the keys that tour adds FAIL R5-PREFIX (and R5-PARTIAL, R5-MIRROR) beside R5-ADVANCE -- one fork difference,
named by each check that reads it.

THE SHARED INSTALL IS RE-READ AROUND EVERY RUN (rung3_trace.fingerprint, the hub included), and every member's and
the hub's .eb is snapshotted into scripts/ before run 1: the analysis outlives the deploy.

P-CAP P-MANIFEST P-DEPLOY P-HUB P-PURE P-FLOOR P-EXITS P-STOCK  static, on the live install, before any run
P-HUBLEG    in game, untraced, before run 1: the hub leg drives the pick up to the menu, takes the STAY row, and
            the hub throws nothing
P-FROZEN    the predictions the analysis reads are the ones the session recorded
R5-RUNS R5-DONOR R5-JOIN R5-REACH R5-PREFIX R5-STAMP R5-STOCKSTATE R5-STATE R5-SAME R5-SEGMENT R5-PING R5-NOSEAM
R5-MIRROR R5-PARTIAL R5-ADVANCE R5-LATCH R5-PREEMPT NC-THROW -- each claim, its PASS, FAIL and VOID, is the frozen
predictions' (rung5_predictions_v3.json "checks"); R5-PREEMPT and R5-LATCH's clobber clause are consistency checks
P-PURE already implies, reported, never counted as independent evidence.

THE STATE RECONSTRUCTOR IS CALIBRATED (:func:`reconstruct`): per bit, from a run's raw rows, and before every w/r row
every bit it already knows must equal the row's own ``old`` -- a contradiction names the row and VOIDs what reads
that run's state. Bytes of a site that has emitted 64 changing rows are uncertain from then on (the engine COUNTS
its later changing stores, PLAN.md "Suppression"). Sessions 2-4: 0 contradictions in 120,673 bit checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dali_tour as D  # noqa: E402
import rung3_trace as R  # noqa: E402
from dali_tour import T  # noqa: E402

PREDICTIONS = HERE / "rung5_predictions_v3.json"
MANIFEST = HERE / "rung5_forks.json"
SESSION_FILE = "rung5_session.json"
SIDES = ("S", "F5")
THROWS, WHERE = R.THROWS, R.WHERE
#: Where R5-STAMP reads a run's hub rows from: its RAW trace (read_run5 keeps it). The dry-run's guard mutant points
#: it at ``"pre"`` (from_start's FIELD list) and must see the base FAIL -- never a crash, never a pass.
STAMP_SOURCE = "raw"


# ======================================================================== the frozen predictions
def load_predictions(path: Path = PREDICTIONS) -> tuple:
    """``(predictions, sha256 of the file's bytes)``."""
    return R.load_predictions(path)


def recorded_predictions(session: dict) -> Path:
    """The predictions file a session recorded: its path, or the file of that name here when the path is gone."""
    named = session.get("predictions")
    if not named:
        return PREDICTIONS
    p = Path(named)
    return p if p.is_file() else HERE / p.name


class NotF5(ValueError):
    """Predictions v3 asked to read a session that is not an F5 session -- a side other than S/F5 (a rung-3 session),
    or an F5 run that names no stock partner (not a replay): refused, never a verdict."""


def chain(pred: dict) -> dict:
    """``{member id: donor}`` -- F5's frozen members."""
    return R.chain_members(pred)["F5"]


def chain_map(pred: dict) -> dict:
    """``{donor: member id}`` -- the Field() remap every member's bytes must carry (P-PURE)."""
    return {d: f for f, d in chain(pred).items()}


def tours5(pred: dict, *, ran=None, stock=None) -> dict:
    """``{"S": the stock Tour, "F5": the members' Tour}`` -- the sides rung3_trace.preflight reads (P-EXITS reads
    only the sides in ``pred["members"]``, so no F0/F4 Tour is ever asked for)."""
    return {"S": D.Tour(scripts=None, stock=stock, tag="rung5"),
            "F5": D.Tour(members=chain(pred), scripts=ran, stock=stock, tag="rung5")}


def _is_timing(k, pred) -> bool:
    """Is WriteKey ``k`` at the frozen INPUT-TIMING site (359 e5 t17 +49 Byte[299]: a villager's Confirm-frame
    counter) -- any value? Every pairwise key comparison excludes it."""
    t = pred["timing_site"]
    return (k.donor, k.sid, k.tag, k.off, k.target) == (t["donor"], t["sid"], t["tag"], t["off"], t["target"])


def keyset(d, pred) -> set:
    """A digested run's keys, member and seam alike, outside the timing site."""
    return {k for k in (*d.keys, *d.seam_keys) if not _is_timing(k, pred)}


def _first_at(d) -> dict:
    """``{key: the line that first evidenced it}`` over member and seam keys."""
    out: dict = {}
    for k, o in (*d.keys.items(), *d.seam_keys.items()):
        out[k] = min(out.get(k, o.at), o.at)
    return out


def _show(keys, n: int = 4) -> list:
    return [f"{k.donor} e{k.sid} t{k.tag} {k.off:+d} {k.target}={k.value}" for k in sorted(keys, key=T.WriteKey.sort_key)[:n]]


# ======================================================================== the hub's bytes and the members' (pure, offline)
def global_stores(data: bytes, *, field_id: int | None = None) -> list:
    """Every gEventGlobal store site of a script, in table order: ``[{sid, tag, off (function-relative), ip
    (entry-relative -- what a trace row carries), target, value}]``. ``value`` is the constant a plain ``target
    const(N) B_LET`` stores (as the text prints it), else None."""
    from ff9mapkit.eb._exprtable import VAR_TYPE
    idx = T.ScriptIndex(data, field_id=field_id)
    out = []
    for e in idx.eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            start, end = f.abs_start, idx._end(e, f)
            for ins in idx.instrs(start, end):
                for s in T.instruction_stores(idx.data, ins):
                    if s[0] != "global":
                        continue
                    target = f"Global.{VAR_TYPE[s[1]]}[{s[2]}]"
                    text = idx.text_at(start, end, ins.off - start)
                    m = re.search(re.escape(target) + r" const\((-?\d+)\) B_LET", text)
                    out.append({"sid": e.index, "tag": f.tag, "off": ins.off - start, "ip": ins.off - e.abs_start,
                                "target": target, "value": int(m.group(1)) if m else None})
    return out


def hub_bytes_check(pred: dict, data: bytes | None) -> tuple:
    """P-HUB's byte clauses on the hub's US .eb: ``(ok, detail, stores)`` -- its global store sites equal the frozen
    ones exactly (site, entry ip, target and value, in order: the prologue's in e0 t0, the three stamps in e2 t3),
    its only literal Field() target is the entry member, no ScenarioCounter gate, no story-bit read, and its Main_Init
    SetControlDirection operands are the frozen ``hub.twist`` (the hub leg calibrates on them: :func:`hub_prior`)."""
    from ff9mapkit import eblint, eventscan, forkreport, storyseed
    from ff9mapkit.eb import EbScript
    H = pred["hub"]
    if data is None:
        return False, f"no .eb for the hub {H['id']}", []
    got = global_stores(data, field_id=H["id"])
    want = H["static_stores"]
    bad = []
    if got != want:
        extra = [s for s in got if s not in want]
        missing = [s for s in want if s not in got]
        bad.append(f"store sites differ from the frozen {len(want)} (got {len(got)}): extra "
                   f"{[(s['sid'], s['tag'], s['off'], s['target'], s['value']) for s in extra][:4]}, missing "
                   f"{[(s['sid'], s['tag'], s['off'], s['target'], s['value']) for s in missing][:4]}"
                   + ("" if extra or missing else " -- the same sites, reordered"))
    stamps = [s for s in got if (s["sid"], s["tag"]) == (H["stamp"][0]["sid"], H["stamp"][0]["tag"])]
    want_st = [{k: s[k] for k in ("sid", "tag", "off", "ip", "target", "value")} for s in H["stamp"]]
    if stamps != want_st:
        bad.append(f"the stamps are {[(s['off'], s['target'], s['value']) for s in stamps]}, not the frozen "
                   f"{[(s['off'], s['target'], s['value']) for s in want_st]}")
    warps = sorted(eblint.warp_targets(data))
    if warps != [H["entry"]]:
        bad.append(f"Field() targets {warps}, want only [{H['entry']}]")
    gates = forkreport.scenario_gates(data)
    if gates:
        bad.append(f"ScenarioCounter gates {gates}")
    reads = storyseed.read_set(EbScript.from_bytes(bytes(data)))
    if reads:
        bad.append(f"story-bit reads {dict(sorted(reads.items())[:6])}")
    twist = eventscan.scan_control_twist(bytes(data))
    if twist is None or list(twist) != list(H["twist"]):
        bad.append(f"SetControlDirection {twist}, not the frozen twist {H['twist']} (the leg's calibration prior)")
    return not bad, "; ".join(bad) or (f"{len(got)} store sites as frozen; stamps at entry ips "
                                       f"{[s['ip'] for s in stamps]} (+{'/+'.join(str(s['off']) for s in stamps)}); "
                                       f"Field() -> {warps}; no SC gate; no story read; twist {list(twist)}"), got


def pure_check(pred: dict, member_bytes, stock) -> tuple:
    """P-PURE: ``(ok, detail)`` -- every member's US .eb IS ``remap_fields(stock .eb of its donor, CHAIN_MAP)`` byte
    for byte (a prepend, an operand left unremapped, any other byte: FAIL), and its literal Field() targets outside
    the members are exactly the frozen seams. ``member_bytes(fid)`` -> the bytes (None: no script)."""
    from ff9mapkit import eblint
    from ff9mapkit.content.verbatim import remap_fields
    cmap = chain_map(pred)
    seams = {int(f): sorted(v) for f, v in pred["seams"].items()}
    bad = []
    for fid, donor in sorted(chain(pred).items()):
        data = member_bytes(fid)
        base = stock(donor)
        if data is None or base is None:
            bad.append(f"{fid}: no .eb" if data is None else f"{fid}: no stock .eb for donor {donor}")
            continue
        want = remap_fields(base.data, cmap)
        if data != want:
            at = next((i for i, (a, b) in enumerate(zip(data, want)) if a != b), min(len(data), len(want)))
            bad.append(f"{fid}: not remap(stock {donor}) -- {len(data)} bytes vs {len(want)}, first difference at "
                       f"{at}")
        out = sorted(eblint.warp_targets(data) - set(chain(pred)))
        if out != seams.get(fid, []):
            bad.append(f"{fid}: Field() targets outside the members {out}, frozen seams {seams.get(fid, [])}")
    return not bad, "; ".join(bad[:6]) or (f"{len(chain(pred))}/{len(chain(pred))} members are their donors "
                                           f"remapped, seams {seams}")


def _message_files(root: Path, fid: int) -> int:
    """How many ``MessageFile <fid> ...`` lines a mod root's DictionaryPatch.txt carries."""
    try:
        text = (Path(root) / "DictionaryPatch.txt").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return sum(1 for ln in text.splitlines() if ln.split()[:2] == ["MessageFile", str(fid)])


def hub_install_check(pred: dict, roots: list) -> tuple:
    """P-HUB's install clauses: the hub is registered ONCE across the Memoria.ini folders under its frozen name, with
    its own MessageFile once, NO ForkDonorPatch row (it is no fork: its rows carry don == fld), and no mod walkmesh
    in any root (it runs on the borrowed room's floor)."""
    H = pred["hub"]
    hid = H["id"]
    hits = [(Path(r).name, T.mod_registrations(r)[hid]) for r in roots if hid in T.mod_registrations(r)]
    bad = []
    if hits != [(hits[0][0] if hits else "", H["name"])] or len(hits) != 1:
        bad.append(f"registered {hits}, want once as {H['name']}")
    mf = sum(_message_files(Path(r), hid) for r in roots)
    if mf != 1:
        bad.append(f"MessageFile {hid} x{mf}, want once")
    fdp = [(Path(r).name, d) for r in roots for f, d in R._fork_donor_rows(Path(r)) if f == hid]
    if fdp:
        bad.append(f"ForkDonorPatch rows {fdp}, want none")
    bgi = [Path(r).name for r in roots if R._deployed_walkmesh(Path(r), hid) is not None]
    if bgi:
        bad.append(f"a mod walkmesh in {bgi}, want none (floor {H['floor']})")
    return not bad, "; ".join(bad) or f"{hid} registered once as {H['name']}, MessageFile once, no fork row, no walkmesh"


def preflight5(pred: dict, roots: list, stock, sides: dict, *, manifest: Path = MANIFEST, ran=None) -> list:
    """Every static pre-flight, in the frozen order: ``[(ok, what, detail)]``. rung3_trace.preflight (P-MANIFEST,
    P-DEPLOY, P-FLOOR, P-EXITS, P-STOCK -- it reads only the sides ``pred["members"]`` names: S and F5), with the
    hub's id in P-MANIFEST, and P-HUB and P-PURE on the live bytes."""
    ran = ran or T.mod_script_source(roots)
    base = {w.split(":")[0]: (ok, w, d) for ok, w, d in R.preflight(pred, roots, stock, sides, manifest)}
    man = json.loads(Path(manifest).read_text(encoding="utf-8"))
    hub_man = man.get("hub", {})
    ok_m, _w, d_m = base["P-MANIFEST"]
    hub_ok = (hub_man.get("id"), hub_man.get("name")) == (pred["hub"]["id"], pred["hub"]["name"])
    out = [(ok_m and hub_ok, "P-MANIFEST: the frozen F5 members and hub are the deployed ones (rung5_forks.json)",
            d_m + ("" if hub_ok else f"; hub {hub_man.get('id')}/{hub_man.get('name')} in the manifest, frozen "
                                     f"{pred['hub']['id']}/{pred['hub']['name']}")),
           base["P-DEPLOY"]]

    def data(fid):
        try:
            idx = ran(fid)
        except T.TraceError:
            return None
        return None if idx is None else idx.data

    ok_i, d_i = hub_install_check(pred, roots)
    ok_b, d_b, _stores = hub_bytes_check(pred, data(pred["hub"]["id"]))
    out.append((ok_i and ok_b, "P-HUB: the deployed hub is the frozen seed and nothing else", f"{d_i} || {d_b}"))
    ok_p, d_p = pure_check(pred, data, stock)
    out.append((ok_p, "P-PURE: every member is its donor's .eb with only the chain's Field() targets remapped, and its "
                      "seams the frozen ones", d_p))
    out += [base["P-FLOOR"], base["P-EXITS"], base["P-STOCK"]]
    return out


def built_eb(build: Path, fid: int) -> bytes | None:
    """The US .eb an offline ``ff9mapkit build --out <build>/<fid>`` wrote for field ``fid``, or None."""
    hits = sorted((Path(build) / str(fid)).glob("StreamingAssets/**/field/us/*.eb.bytes"))
    return hits[0].read_bytes() if len(hits) == 1 else None


def offline_check(build: Path, pred: dict, stock=None) -> list:
    """P-PURE and P-HUB's byte clauses on an OFFLINE build (``<build>/<id>/`` per field, as build step 8 writes it),
    before anything is deployed: ``[(ok, what, detail)]``, the last entry the hub's store sites found (to freeze)."""
    stock = stock or T.stock_script_source()
    ok_p, d_p = pure_check(pred, lambda f: built_eb(build, f), stock)
    ok_h, d_h, stores = hub_bytes_check(pred, built_eb(build, pred["hub"]["id"]))
    return [(ok_p, "P-PURE (offline build)", d_p), (ok_h, "P-HUB bytes (offline build)", d_h),
            (True, "the hub's store sites, as built", json.dumps(stores))]


# ======================================================================== the hub leg (in game)
def _left(end: float) -> float:
    """Seconds left of the hub leg's one deadline -- HarnessError("hub leg: budget") when none are."""
    from harness import HarnessError
    left = end - time.time()
    if left <= 0:
        raise HarnessError("hub leg: budget -- the leg's hub_s ran out")
    return left


def _pad_toward(basis: dict, vec) -> str:
    """The one pad direction whose CALIBRATED world vector points most nearly along ``vec``."""
    n = math.hypot(*vec) or 1.0
    ux, uz = vec[0] / n, vec[1] / n
    cand = [("up", basis["v"]), ("down", (-basis["v"][0], -basis["v"][1])),
            ("right", basis["h"]), ("left", (-basis["h"][0], -basis["h"][1]))]
    return max(cand, key=lambda c: c[1][0] * ux + c[1][1] * uz)[0]


def hub_prior(g, pred: dict) -> dict:
    """The hub's PREDICTED button->world basis, ``{"v", "h"}``: movement.key_move_basis of the operand of the hub's
    own Main_Init SetControlDirection (frozen ``hub.twist``, which P-HUB holds the deployed bytes to) that a harness
    press is rotated by (Session._key_twist_operand) -- Session.key_prior's rule, read off the frozen hub instead of
    a stock script (a custom id has none: key_prior(31100) is None)."""
    from ff9mapkit.content import movement
    return movement.key_move_basis(pred["hub"]["twist"][g._key_twist_operand()])


def hub_open(g, pred: dict, end: float, rec: dict | None = None, *, after_warp=None) -> dict:
    """The hub leg up to its menu (design steps 1-6): warp into the hub at the lead-in, calibrate_axes ON THE HUB'S
    OWN TWIST (:func:`hub_prior`), Stiltzkin read off the published objects -- the talker nearest his frozen spot --
    a walk_to (strict False, slides True: his body stops the walk and slides it) to a point his body leaves free and
    his talk ring reaches, then Confirm, at most 3 tries. BEFORE EVERY Confirm he is turned IN PLACE toward
    Stiltzkin (s90; skipped on an engine that cannot turn in place, ``facing_status`` "cannot"): the walk's last
    burst need not face him -- walk_to corrects an overshoot with a burst the OTHER way (the FakeGame leg: "hold
    right 13", then "hold left 1"), and a talk search needs him facing the talker. After a silent try he is given
    one walked tick toward him (his body holds him at ``r``). The menu must offer exactly the frozen options once it
    takes answers, its cursor on the default. Fills ``rec`` (the leg's record) IN PLACE as it goes -- so a leg that
    raises still leaves what it measured -- and returns it; raises HarnessError on any failure.

    NEVER A BLIND CALIBRATION HERE: the hub's spawn stands INSIDE Stiltzkin's body (76u from him; his r is 4*(14 + 24)
    = 152 by the built hub's SetObjectLogicalSize). MovePC pushes a step that faces him (+-90 degrees) out to its safe
    distance, 4*20 + 4*14 = 136 < r, which collides again, so the step is undone whole (FieldMapActorController.cs:
    772-793): up, down and right -- whose turns all swing his facing through east, at him -- do not move him at all,
    and a blind calibrate_axes refuses the v axis outright ("neither up nor down moved"). With the prior, a one-sided
    probe (left, away from him) that agrees with it is a measurement and the other axis is derived (Session.
    _calibrate_clear_of). The basis is cached for the launch: every later leg walks west out of the body on it.

    ``after_warp`` (F5c, rung5b_hub's traced P-AMBIENT leg): called with no argument right after the warp returns and
    before the calibration -- its control marker. None, every F5 caller, leaves the leg exactly as it was."""
    from harness import HarnessError
    H = pred["hub"]
    hid = int(H["id"])
    rec = {"k": "hub"} if rec is None else rec
    _fid, entrance, sc = H["lead_in"]
    g.warp(hid, entrance=entrance, scenario=sc, timeout=min(60.0, _left(end)))
    if after_warp is not None:
        after_warp()
    _left(end)
    basis = g.calibrate_axes(prior=hub_prior(g, pred))
    _left(end)
    # the agent nulls the whole list on ANY failure of its walk (null = "could not say THIS sample"): read it over a
    # few samples, never off one
    st = g.wait_for(lambda s: s.objects is not None, timeout=min(5.0, _left(end)),
                    what=f"the hub's objects ({hid})")
    objs = st.objects
    nx, nz = H["narrator_pos"]
    talkers = [o for o in objs if o.get("talk")]
    if not talkers:
        raise HarnessError(f"hub leg: no object with a talk function in {hid}: {objs}")
    o = min(talkers, key=lambda b: math.hypot(b["x"] - nx, b["z"] - nz))
    off = math.hypot(o["x"] - nx, o["z"] - nz)
    if off > H["narrator_within"]:
        raise HarnessError(f"hub leg: the nearest talker is {off:.0f}u from {H['narrator']}'s frozen spot "
                           f"({o['x']:.0f}, {o['z']:.0f})")
    r, tr = o.get("r"), o.get("talk_r")
    if r is None or tr is None:
        raise HarnessError(f"hub leg: {H['narrator']} publishes no r/talk_r ({r}, {tr})")
    a = H["approach"]
    if tr <= r + a["margin"]:
        raise HarnessError(f"hub leg: no talk ring outside the body (r {r:.0f}, talk_r {tr:.0f})")
    d = max(r + a["margin"], min(tr - a["margin"], r + a["reach"]))
    ax, az = o["x"] - d, o["z"]                          # west of him, on the spawn's line (950's floor)
    rec.update(narrator=[round(o["x"]), round(o["z"])], r=r, talk_r=tr, approach=[round(ax), round(az), round(d, 1)])
    rec["walked"] = bool(g.walk_to(ax, az, tolerance=a["tolerance"], strict=False, slides=True))
    rec.update(tries=0, turns=0, nudges=0)
    box = None
    for k in range(a["tries"]):
        now = g.state
        if now.player_x is None:
            raise HarnessError(f"hub leg: no player position in {hid} before Confirm {k + 1}")
        pad = _pad_toward(basis, (o["x"] - now.player_x, o["z"] - now.player_z))
        if now.facing_status != "cannot":
            g.turn_in_place(pad, a["turn_frames"], timeout=min(10.0, _left(end)))
            rec["turns"] += 1
        rec["tries"] += 1
        box = g.interact(timeout=min(6.0, _left(end)))
        if box is not None or k == a["tries"] - 1:
            break
        frames = g.rate().frames_for_ticks(1)             # one walked tick: into him, his body holds him at r
        g.send(f"hold cancel {frames}", f"hold {pad} {frames}", f"wait {frames + 4}", timeout=min(60.0, _left(end)))
        rec["nudges"] += 1
        _left(end)
    now = g.state
    rec["at"] = [None if now.player_x is None else round(now.player_x),
                 None if now.player_z is None else round(now.player_z)]
    if box is None:
        raise HarnessError(f"hub leg: no dialogue after {rec['tries']} tries at {rec['at']} ({H['narrator']} at "
                           f"{rec['narrator']}, r {r:.0f}, talk_r {tr:.0f})")
    ready = g.wait_for(lambda s: g._choice_ready(s), timeout=min(10.0, _left(end)),
                       what="the journey menu to take answers")
    names = g.options(timeout=min(10.0, _left(end)))      # read once it takes answers: its phrases are parsed
    rec["options"] = names
    rec["cursor"] = (ready.choice or {}).get("selected")
    if names != H["options"]:
        raise HarnessError(f"hub leg: the menu offers {names}, not the frozen {H['options']}")
    if rec["cursor"] != H["default"]:
        raise HarnessError(f"hub leg: the menu's cursor rests on {rec['cursor']}, not the frozen default "
                           f"{H['default']}")
    return rec


def hub_pick(g, pred: dict, label: str, end: float, land_s: float | None = None) -> int:
    """Pick the row reading ``label`` by NAME (option_index -> select) and confirm it like a player (the
    rung4_save_act ``_pick`` rule): Confirm, then watch up to 20 frames for the menu to close or the field to
    change; the same menu still open -- a prompt still typing eats the first Confirm -- gets ONE more, never a
    second blind. Returns the presses; HarnessError when the menu never took one.

    TWO CLOCKS. Up to each press the leg's own (``end``): the selection gets ``min(its default, the time left)``, and
    none left raises "hub leg: budget" BEFORE the press -- the menu is open and ready then (the first press, or one a
    typing prompt ate), so no stamp can have landed: DRIVE. From the press on, the landing's (``land_s``, the frozen
    ``budget.entry_s``): the press and the polls after it are sent with ``min(send's default, land_s)`` and the leg's
    clock is never read again -- once a Confirm may have been taken the stamps may have landed, and a budget that ran
    out after them would file a fork's stall as a DRIVE stop (press/wait_frames take no timeout at all: a game that
    stops taking requests would hold each a default 60 s)."""
    from harness import HarnessError
    hid = int(pred["hub"]["id"])
    land_s = pred["budget"]["entry_s"] if land_s is None else land_s
    i = g.option_index(label, timeout=min(10.0, _left(end)))
    g.select(i, timeout=min(10.0, _left(end)))
    before = json.dumps((g.state.choice or {}).get("options"))
    for presses in (1, 2):
        _left(end)                                    # the last read of the leg's clock before this press
        g.send("press confirm 4", timeout=min(60.0, land_s))
        land = time.time() + land_s
        for _ in range(5):
            g.send("wait 4", timeout=max(1.0, min(60.0, land - time.time())))
            st = g.state
            if (st.field_id != hid or st.choice is None or json.dumps(st.choice.get("options")) != before
                    or not g._choice_ready(st)):
                return presses
    raise HarnessError(f"hub leg: the menu never took its Confirm on {label!r} (2 presses)")


def hub_leg(g, log: list, pred: dict, *, budget_s: float | None = None, entry_s: float | None = None) -> dict:
    """THE HUB LEG, F5's way into its start field -- dali_tour.segment's ``enter``: :func:`hub_open`, the pick of the
    frozen row (:func:`hub_pick`), and the wait for the entry member the pick's own Field() leads to. ONE deadline
    for the leg UP TO THE PICK'S CONFIRM (``hub_s``): every call gets ``min(its default, the time left)``, and
    between calls none left raises HarnessError("hub leg: budget") -- a DRIVE stop whatever the trace shows
    (predictions coverage.drive), sound because it can only fire before a stamp. From the Confirm on, THE LANDING IS
    THE FORK'S, on its own clock (``entry_s``, the frozen budget.entry_s: rung 3's raw path waited 60 s for its start
    field): the press, its polls and the wait for 31111 never read the leg's clock, so a slow leg cannot shorten the
    one wait that tells a fork's stall ("timed out ... waiting for the pick to land in 31111 over N live samples",
    FORK-STOP "hub" once the stamps landed) from a slow drive. Logs and returns ``{"k": "hub", ...}``; raises
    HarnessError on any failure (the run then stops in phase "hub"), logging the record as far as it got, with the
    ``error`` -- what the leg measured (r, talk_r, the approach, the tries) is the diagnosis of a leg that failed.
    Any other error (a drive bug) is logged the same way and re-raised as it is: the run's own handler names it
    (STOPPED (unexpected), DRIVE)."""
    H = pred["hub"]
    t0 = time.time()
    end = t0 + (pred["budget"]["hub_s"] if budget_s is None else budget_s)
    land_s = pred["budget"]["entry_s"] if entry_s is None else entry_s
    rec: dict = {"k": "hub"}
    try:
        hub_open(g, pred, end, rec)
        rec["picked"] = H["pick"]
        rec["presses"] = hub_pick(g, pred, H["pick"], end, land_s)
        entry = int(H["entry"])
        g.wait_for(lambda s: s.field_id == entry, timeout=land_s, what=f"the pick to land in {entry}")
    except Exception as err:                      # noqa: BLE001 -- logged, then re-raised unchanged
        rec.update(error=f"{type(err).__name__}: {str(err)[:300]}", t=round(time.time() - t0, 1))
        log.append(rec)
        raise
    rec["t"] = round(time.time() - t0, 1)
    log.append(rec)
    return rec


def p_hubleg(g, pred: dict) -> tuple:
    """P-HUBLEG (in game, untraced, before run 1): ``(ok, detail, record)``. New Game, the hub leg up to its menu,
    the STAY row picked (guarded Confirm) -- which must leave him in the hub with control and no field change for 60
    frames -- no THROWS exception with an EventEngine/EBin/StoryTrace/HarnessAgent frame between the leg's hub warp
    and that check (its log mark is taken after New Game, right before the warp), and the title restored. The
    record carries the measured r, talk_r and approach -- as far as the leg got, when it failed. Any error the
    drive raises FAILs it (named), never escapes: P-HUBLEG stops the session before run 1 either way. The FIRST
    calibration of 31100 in the launch is this one (hub_open, on the hub's twist): every run's leg reuses its basis."""
    H = pred["hub"]
    mark = None
    rec: dict = {"k": "hub"}
    bad = []
    t0 = time.time()
    try:
        g.newgame()
        g.wait_frames(30)
        mark = g.log_mark()
        end = time.time() + pred["budget"]["hub_s"]
        hub_open(g, pred, end, rec)
        rec["picked"] = H["stay"]
        rec["presses"] = hub_pick(g, pred, H["stay"], end, pred["budget"]["entry_s"])
        moved = None
        for _ in range(15):
            g.wait_frames(4)
            st = g.state
            if st.field_id != H["id"]:
                moved = st.field_id
                break
        st = g.state
        if moved is not None:
            bad.append(f"the stay row warped to {moved}")
        elif not st.control or st.choice is not None:
            bad.append(f"the stay row left control {st.control}, a menu {st.choice is not None}")
    except Exception as err:                      # noqa: BLE001 -- a HarnessError, or the drive's own bug: FAIL, named
        bad.append(f"{type(err).__name__}: {str(err)[:300]}")
    rec["t"] = round(time.time() - t0, 1)
    ours = [] if mark is None else [e for e in g.exceptions_since(mark) if e.name in THROWS
                                    and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    if ours:
        bad.append(f"thrown: {[(e.name, e.where) for e in ours[:4]]}")
    ok_t, why_t = g.restore_baseline()
    if not ok_t:
        bad.append(f"the title could not be restored: {why_t}")
    return not bad, "; ".join(bad) or (f"{H['narrator']} r {rec.get('r')}, talk_r {rec.get('talk_r')}, approach "
                                       f"{rec.get('approach')}, {rec.get('tries')} tries, options {rec.get('options')}, "
                                       f"stay row stayed ({rec.get('presses')} presses)"), rec


# ======================================================================== the state reconstructor (pure, offline)
def _bits(r) -> dict:
    """``{global bit: (old, new)}`` a w/r row touches: a bit store its one bit, any other store every bit of its
    width (two's complement, little-endian), a residue row its byte."""
    if r.k == "w" and r.is_bit:
        return {r.bit: (r.old & 1, r.new & 1)}
    n = T.WIDTH_BYTES[r.width] if r.k == "w" else 1
    mask = (1 << 8 * n) - 1
    o, v = r.old & mask, r.new & mask
    return {(r.byte + k) * 8 + j: ((o >> (8 * k + j)) & 1, (v >> (8 * k + j)) & 1) for k in range(n) for j in range(8)}


def reconstruct(rows, stop_line: int | None = None, *, saturate: int = 64) -> dict:
    """gEventGlobal per BIT, rebuilt from one run's RAW rows (split_runs' run: residue, field 70, the hub included),
    CALIBRATED against the trace itself: before every w/r row of the WHOLE run, every bit already known (and not
    uncertain) must equal the row's own ``old`` -- else a contradiction, named. A site that has emitted ``saturate``
    changing rows has its later changing stores COUNTED, not emitted (PLAN.md "Suppression"): its bytes are uncertain
    from then on. Any epoch row after the first (a swap, a debug restore) replaces the whole array: nothing is known
    after it. ``stop_line``: the snapshot is taken after that row (the wake), inclusive.

    Returns ``{"known": {bit: v}, "first": {bit: the first old seen -- New Game's}, "uncertain": set, "checked": n,
    "contradictions": [(line, fld, sid, tag, ip, target, bit, known, old)], "at": the snapshot's line or None}``,
    the snapshot's known/uncertain as of ``stop_line``, the calibration over every row."""
    known: dict = {}
    first: dict = {}
    unc: set = set()
    changing: Counter = Counter()
    checked, bad = 0, []
    snap = None
    epochs = 0
    for r in rows:
        if r.k == "e":
            epochs += 1
            if epochs > 1:
                known, unc, changing = {}, set(), Counter()
            continue
        if r.k not in ("w", "r"):
            continue
        tb = _bits(r)
        for b, (o, _v) in tb.items():
            first.setdefault(b, o)
            if b in known and b not in unc:
                checked += 1
                if known[b] != o:
                    bad.append((r.line, r.fld, r.sid, r.tag, r.ip, r.target if r.k == "w" else f"byte {r.byte}",
                                b, known[b], o))
        if r.k == "w" and not r.same:
            changing[r.site] += 1
            if changing[r.site] >= saturate:
                unc.update(tb)
        for b, (_o, v) in tb.items():
            known[b] = v
        if snap is None and stop_line is not None and r.line >= stop_line:
            snap = (dict(known), set(unc), r.line)
    if snap is None:
        snap = (dict(known), set(unc), None) if stop_line is None else ({}, set(), None)
    return {"known": snap[0], "first": first, "uncertain": snap[1], "checked": checked, "contradictions": bad,
            "at": snap[2]}


def byte_value(known: dict, b: int) -> int | None:
    """Byte ``b``'s value when all 8 of its bits are known, else None."""
    vals = [known.get(b * 8 + j) for j in range(8)]
    return None if any(v is None for v in vals) else sum(v << j for j, v in enumerate(vals))


def changed_bytes(rc: dict) -> set:
    """The bytes with a known bit that differs from its first-seen (New Game's) value."""
    return {b >> 3 for b, v in rc["known"].items() if b in rc["first"] and rc["first"][b] != v}


def wake_row(raw, pred: dict, members: dict):
    """The run's first raw wake row -- 352's SC := beat (e17 tag 1), in its place on this side -- or None."""
    wk = pred["wake"]
    return next((r for r in raw if r.k == "w" and members.get(r.fld, r.fld) == wk["donor"] and r.sid == wk["sid"]
                 and r.tag == wk["tag"] and r.target == wk["target"] and r.new in wk["value"]), None)


# ======================================================================== reading a session (pure, offline)
def read_run5(run_dir: Path, rec: dict, pred: dict, chains: dict, ran, stock) -> dict:
    """One recorded run, read -- rung3_trace.read_run (rung3_trace.py:602-635), keeping the RAW run: ``{i, side,
    label, rec, raw, rows, pre, log, digest, broken, void}``. ``raw`` is split_runs' one run, whole (the field-70
    residue and, on F5, the hub's rows: R5-STAMP, R5-STATE and R5-STOCKSTATE read it). ``rows`` are from_start's.

    AN F5 RUN THAT NEVER REACHED ITS START is not digested at all (``rows`` = ``digest`` = None, VOID "never reached
    31111"): from_start would hand back the whole run, the hub's rows would key as FORK ONLY under a donor with no
    stock .eb, and a walker's failure in the hub would FAIL R5-JOIN and R5-DONOR. Its stop class says what it was."""
    i, side = rec["i"], rec["side"]
    trace_name, log_name = R.run_names(i, side)
    r = {"i": i, "side": side, "label": f"{side}#{i}", "rec": rec, "raw": None, "rows": None, "pre": [], "log": None,
         "digest": None, "broken": [], "void": []}
    if rec.get("skipped") or rec.get("install"):
        r["void"].append(rec.get("skipped") or f"the install changed {rec['install']}")
        return r
    tp, lp = run_dir / rec.get("trace", trace_name), run_dir / rec.get("log", log_name)
    if tp.is_file():
        try:
            split = T.split_runs(T.read_trace(tp))
        except T.TraceError as err:
            split = None
            r["broken"].append(f"its trace breaks the row contract ({str(err)[:100]})")
        if split is not None and len(split) != 1:
            r["broken"].append(f"{len(split)} traced runs in its file")
        elif split is not None:
            r["raw"] = split[0]
            start = pred["start"][side]
            if side == "F5" and not any(x.k in ("w", "r") and x.fld == start for x in split[0]):
                r["void"].append(f"never reached {start}")
            else:
                r["rows"], r["pre"] = R.from_start(split[0], start)
    else:
        r["void"].append("no trace")
    if lp.is_file():
        r["log"] = json.loads(lp.read_text(encoding="utf-8"))
    else:
        r["void"].append("no log")
    if r["rows"] is not None:
        try:
            r["digest"] = T.digest(r["label"], r["rows"], scripts=ran, donor_scripts=stock, members=chains.get(side))
        except T.TraceError as err:
            r["broken"].append(f"cannot be digested ({str(err)[:100]})")
    return r


def replay_why5(r, by_i: dict, pred, chains) -> list:
    """Why F5 run ``r`` is not a replay of a covered partner -- rung3_trace._replay_why (rung3_trace.py:676-709) over
    F5's chain: its partner an earlier covered stock run, and its log's replay steps that partner's entered walk
    whole, or -- the story moved on during it ("SC left") -- a prefix up to the crossing it moved on at."""
    if r["rec"].get("skipped") or r["rec"].get("install"):
        return []
    k = r["rec"].get("partner")
    p = by_i.get(k)
    if not isinstance(k, int) or p is None or p["side"] != "S" or k >= r["i"]:
        return [f"not a replay: its partner {k} is not an earlier stock run"]
    if p["why_void"]:
        return [f"partner S#{k} VOID"]
    if r["log"] is None or p["log"] is None:
        return []
    want = D.entered_walk(p["log"]["log"])
    steps = [x for x in r["log"]["log"] if x.get("k") == "cross" and x.get("leg") == "replay"]
    got = D.entered_walk(steps, chains.get("F5"))
    if got == want:
        return []
    if R._stop(r).startswith("SC left"):
        at = next((j for j, x in enumerate(steps) if x.get("sc1", pred["beat"]) != pred["beat"]), len(steps))
        got = D.entered_walk(steps[:at], chains.get("F5"))
        if got == want[:len(got)]:
            return []
    bad = next((j for j, (a, b) in enumerate(zip(got, want)) if a != b), None)
    if bad is not None:
        return [f"its replay of S#{k}'s walk diverged at step {bad + 1}: {D.step_name(got[bad])}, not "
                f"{D.step_name(want[bad])}"]
    return [f"it replayed {len(got)} of the {len(want)} steps of S#{k}'s walk"]


def hub_rows(r, pred) -> list:
    """The rows a run wrote in the hub (w, c and r alike), off its RAW trace (``STAMP_SOURCE``)."""
    hid = pred["hub"]["id"]
    return [x for x in (r.get(STAMP_SOURCE) or []) if isinstance(x, T.Row) and x.fld == hid and x.k in ("w", "c", "r")]


def stamps_landed(r, pred) -> bool:
    """Did the run's raw trace record all three frozen stamps in the hub (target and value)?"""
    rows = [x for x in hub_rows(r, pred) if x.k == "w"]
    return all(any(x.target == s["target"] and x.new == s["new"] for x in rows) for s in pred["hub"]["stamp"])


def stop_class(r, pred: dict, by_i: dict) -> dict | None:
    """A VOID F5 run's STOP CLASS by the frozen table (predictions "coverage": its "drive" patterns and its
    "fork_stop" table), DRIVE tested first and always winning: ``{"cls": "DRIVE" | "FORK-STOP" | "UNCLASSED",
    "point", "why"}``; None for a covered run.

    DRIVE (never evidence): a skip, the install moving, no trace or log, a broken trace, a trace that never closed (a
    game death or a tracer fault), a stop text among the frozen DRIVE patterns (the budgets -- the hub leg's own
    included, which can only fire before a stamp -- the walker's limits, a dead channel, the title, an unexpected
    error), a partner not covered, a hub leg that stopped before any stamp landed, or a hub leg that raised though
    its own Field() had already landed in 31111 (the trace has rows there: the harness's view of the landing, not
    the fork's). FORK-STOP (the run stood in 31111 or its stamps landed, its partner covered): "hub" (the stamps
    landed and the landing's own wait timed out, live, before any row in 31111), "segment@<place>" (the segment
    class -- also a stop at the entry itself: the leg returned in 31111 and the stall came before member(359) wrote
    a row), "replay@<step>(<step name>)", "scene@<place>@<sc>". UNCLASSED: VOID for a reason no pattern names (the
    stamps landed and 31111 was never reached, but the stop is not the landing's timeout, among others): listed;
    R5-REACH cannot PASS while one stands."""
    if r["side"] != "F5" or not r["why_void"]:
        return None
    S = pred["coverage"]["fork_stop"]
    rec = r["rec"]
    stop = R._stop(r)
    phase = rec.get("phase")

    def drive(why):
        return {"cls": "DRIVE", "point": None, "why": why}

    if rec.get("skipped") or rec.get("install"):
        return drive(rec.get("skipped") or f"the install changed {rec['install']}")
    if r["broken"]:
        return drive(f"broken trace: {r['broken'][0]}")
    if r["raw"] is None or r["log"] is None:
        return drive("no trace" if r["raw"] is None else "no log")
    # read off the RAW run, not the digest: a run that died in the hub after its stamps (never reached 31111) has
    # no digest, and a game death there is DRIVE like any other -- never a FORK-STOP "hub"
    try:
        eps = T.epochs(r["raw"])
    except T.TraceError as err:
        return drive(f"broken trace: {str(err)[:100]}")
    if not eps or eps[-1].closed_by is None:
        return drive("the trace never closed (a game death or a tracer fault)")
    for pat in pred["coverage"]["drive"]:
        if re.search(pat, stop):
            return drive(f"stop {stop[:100]!r} ({pat!r})")
    p = by_i.get(rec.get("partner"))
    if p is None or p["side"] != "S" or p["why_void"]:
        return drive(f"its partner {rec.get('partner')} is not covered")
    start = pred["start"]["F5"]
    landed = stamps_landed(r, pred)
    if phase == S["hub"]["phase"]:
        if r["rows"] is not None:
            # the leg raised after its own Field() had run: the trace has rows in 31111, so the fork went there --
            # the harness's view of the landing (its wait, its polls), not the fork's
            return drive(f"the hub leg raised though the trace has rows in {start} (its Field() had landed): "
                         f"{stop[:100]}")
        if not landed:
            return drive(f"the hub leg stopped before the stamps: {stop[:100]}")
        if re.search(S["hub"]["stop"], stop):
            return {"cls": "FORK-STOP", "point": "hub", "why": f"the stamps landed and {start} was never reached: "
                                                              f"{stop[:100]}"}
        return {"cls": "UNCLASSED", "point": None,
                "why": f"the stamps landed and {start} was never reached, but the stop is not the landing's own "
                       f"timeout: {stop[:120]}"}
    if r["rows"] is None:
        if not (phase == S["segment"]["phase"] and landed):
            return drive(f"stopped in phase {phase} with no row in {start}"
                         + (" and no stamp in the hub" if not landed else "") + f": {stop[:100]}")
        # the leg RETURNED (the harness saw 31111: phase segment) and the run stopped before member(359) wrote a
        # row -- a stall at the entry itself: the segment class below, at the place the run stood in (rec "at")
    seg = next((x for x in reversed((r["log"] or {}).get("log", [])) if x.get("k") == "segment"), None)
    at = rec.get("at") or {}
    if phase == S["segment"]["phase"]:
        raised = any(re.search(pat, stop) for pat in S["segment"]["raised"])
        if raised or (seg is not None and not seg.get("ok")):
            where = seg.get("place") if seg is not None else at.get("place")
            return {"cls": "FORK-STOP", "point": f"segment@{where}", "why": stop[:160]}
    m = re.search(S["replay"]["stop"], stop)
    if m:
        # the step's NAME is part of the point: two breaks at one step number of two different walks are two points
        return {"cls": "FORK-STOP", "point": f"replay@{m.group(1)}({m.group(2)})", "why": stop[:160]}
    if phase in S["scene"]["phases"] and any(re.search(pat, stop) for pat in S["scene"]["raised"]):
        return {"cls": "FORK-STOP", "point": f"scene@{at.get('place')}@{at.get('sc')}", "why": stop[:160]}
    return {"cls": "UNCLASSED", "point": None, "why": "; ".join(r["why_void"])[:200]}


def judge5(runs: list, pred: dict) -> list:
    """Judge read runs by the frozen coverage rule, in place -- rung3_trace.judge (rung3_trace.py:721-738) for S and
    F5: each gets ``why_void`` ([] = covered) and ``stop_class`` (:func:`stop_class`). S first, then F5 (its
    coverage reads its partner's; its stop class, whether that partner is covered) -- over ``runs`` alone, so the
    runs a session had recorded when it planned a re-run are judged as it judged them then."""
    chains = R.chain_members(pred)
    by_i = {r["i"]: r for r in runs}
    for side in SIDES:
        for r in runs:
            if r["side"] == side:
                r["why_void"] = R._void_why(r, pred, chains, None)
                if side == "F5":
                    r["why_void"] += replay_why5(r, by_i, pred, chains)
    for r in runs:
        r["stop_class"] = stop_class(r, pred, by_i)
    return runs


def read_session5(run_dir, pred: dict, *, stock, roots, session: dict) -> list:
    """Every run the session recorded, read (:func:`read_run5`, against the session's scripts/ snapshot first) and
    judged (:func:`judge5`). Always given the session dict -- never a file name's default."""
    run_dir = Path(run_dir)
    chains = R.chain_members(pred)
    snap = {int(p.stem): p.read_bytes() for p in (run_dir / "scripts").glob("*.eb")}
    ran = T.mod_script_source(roots, fallback=stock, explicit=snap)
    return judge5([read_run5(run_dir, rec, pred, chains, ran, stock) for rec in session.get("runs", [])], pred)


def _driven(r) -> bool:
    """Was the run driven at all (not skipped, not refused before it began for a moved install)?"""
    return not r["rec"].get("skipped") and not str(r["rec"].get("install", "")).startswith("before")


def fork_stop_points(runs: list) -> Counter:
    """``Counter({point: F5 runs that FORK-STOPped there})``."""
    return Counter(r["stop_class"]["point"] for r in runs
                   if r["side"] == "F5" and (r.get("stop_class") or {}).get("cls") == "FORK-STOP")


def halted(runs: list) -> str | None:
    """THE HALT: the point two F5 runs FORK-STOPped at (R5-REACH's FAIL is decided), or None."""
    twice = sorted(p for p, n in fork_stop_points(runs).items() if n >= 2)
    return twice[0] if twice else None


def short_sides5(runs: list, pred: dict) -> list:
    n = pred["coverage"]["min_covered"]
    return [s for s in SIDES if sum(1 for r in runs if r["side"] == s and not r["why_void"]) < n]


def untwinned5(runs: list, max_breaks: int) -> list:
    """The covered stock runs no covered F5 run partners yet, oldest first, less those on which ``max_breaks``
    driven, non-covered F5 runs have already been made (a FORK-STOP is retried once on the same walk)."""
    twinned = {r["rec"].get("partner") for r in runs if r["side"] == "F5" and not r["why_void"]}
    tried = Counter(r["rec"].get("partner") for r in runs if r["side"] == "F5" and r["why_void"] and _driven(r))
    return [r["i"] for r in runs if r["side"] == "S" and not r["why_void"] and r["i"] not in twinned
            and tried[r["i"]] < max_breaks]


def rerun_plan5(runs: list, pred: dict) -> tuple | None:
    """What runs next after the frozen six, from judged runs: ``(side, partner)``, or None -- no side short, or THE
    HALT (:func:`halted`). S first while S is short; then F5 on the oldest untwinned covered S
    (:func:`untwinned5`); none -- a fresh S. R5-RUNS recomputes it for every re-run (:func:`pairing_faults5`)."""
    if halted(runs):
        return None
    short = short_sides5(runs, pred)
    if not short:
        return None
    if short[0] == "S":
        return ("S", None)
    free = untwinned5(runs, pred["replay"]["max_breaks"])
    return ("F5", free[0]) if free else ("S", None)


def pairing_faults5(runs: list, pred: dict) -> list:
    """Where the session broke the registered pairing -- rung3_trace.pairing_faults (rung3_trace.py:751-786) for F5:
    every F5 run names an earlier stock run as its partner, a frozen-order F5 its round's S, the walk it was given
    is that partner's entered walk, no covered S has two covered F5 twins, and every re-run is the one
    :func:`rerun_plan5` names from the runs before it, judged as the session judged them then -- none at all once
    the session had HALTED. The session's own rule broken is the instrument's fault: R5-RUNS FAILs."""
    order = pred["order"]
    by_i = {r["i"]: r for r in runs}
    out = []
    for r in runs:
        if r["side"] != "F5":
            continue
        k = r["rec"].get("partner")
        p = by_i.get(k)
        if not isinstance(k, int) or p is None or p["side"] != "S" or k >= r["i"]:
            out.append(f"{r['label']}'s partner {k} is not an earlier stock run")
            continue
        own = R.round_partner(order, r["i"])
        if r["i"] <= len(order) and k != own:
            out.append(f"{r['label']} partners S#{k}, not its round's S#{own}")
        if "walk" in r["rec"] and p["log"] is not None and r["rec"]["walk"] != D.entered_walk(p["log"]["log"]):
            out.append(f"{r['label']} was given a walk that is not S#{k}'s")
    twins = Counter(r["rec"].get("partner") for r in runs if r["side"] == "F5" and not r["why_void"])
    out += [f"S#{k} is partnered by {n} covered F5 runs" for k, n in sorted(twins.items()) if n > 1]
    for r in runs:
        if r["i"] <= len(order):
            continue
        before = judge5([dict(x) for x in runs if x["i"] < r["i"]], pred)
        plan = rerun_plan5(before, pred)
        ran = (r["side"], r["rec"].get("partner") if r["side"] == "F5" else None)
        if plan != ran:
            why = (f", where the session had HALTED (two F5 runs FORK-STOPped at {halted(before)})" if halted(before)
                   else f", where the plan named {plan[0]}" + (f" on S#{plan[1]}" if plan[1] is not None else "")
                   if plan else ", where no side was short")
            out.append(f"{r['label']} re-ran {ran[0]}" + (f" on S#{ran[1]}" if ran[1] is not None else "") + why)
    return out


def adv_point(log: list, members: dict, sc: int) -> tuple:
    """Where a run's story moved on, on its ENTERED walk: ``(entered steps up to and including the first crossing
    whose settled SC is at least ``sc``, that crossing's [place, exit, entered] or None)`` -- ``(steps, None)`` when
    no crossing settled there (it moved on between crossings, or never)."""
    walk = []
    for x in log:
        if x.get("k") != "cross":
            continue
        e = D.entered(x, members)
        if e is not None:
            walk.append([x.get("place", members.get(x["from"], x["from"])), x["exit"], e])
        if x.get("sc1", 0) >= sc:
            return (len(walk), walk[-1] if e is not None else None)
    return (len(walk), None)


# ======================================================================== the analysis (pure, offline)
def analyse5(run_dir, *, pred_path: Path | None = None, stock=None, roots=None) -> tuple:
    """F5's checks over one session's saved traces and logs: ``([(ok, what, detail)], {file name: text})``, ``ok``
    True (PASS), False (FAIL) or None (VOID). Pure given the install and the session dir (every member's and the
    hub's .eb from the session's own snapshot). The predictions are the file the session recorded unless
    ``pred_path`` overrides it (P-FROZEN judges either); a session that is not F5's is refused (:class:`NotF5`)."""
    run_dir = Path(run_dir)
    session = json.loads((run_dir / SESSION_FILE).read_text(encoding="utf-8"))
    pred_path = recorded_predictions(session) if pred_path is None else Path(pred_path)
    pred, sha = load_predictions(pred_path)
    recs = session.get("runs", [])
    alien = sorted({x.get("side") for x in recs} - set(SIDES))
    bare = [f"F5#{x.get('i')}" for x in recs if x.get("side") == "F5" and "partner" not in x]
    if pred.get("version") != 3 or alien or bare:
        raise NotF5(f"session {session.get('label')}: not an F5 session for {pred_path.name} (v{pred.get('version')})"
                    + (f" -- sides {alien}" if alien else "") + (f" -- {', '.join(bare)} name no stock partner" if bare
                                                                   else ""))
    C, n_min = pred["checks"], pred["coverage"]["min_covered"]
    out = [(session.get("predictions_sha256") == sha,
            "P-FROZEN: the predictions this analysis reads are the ones the session recorded before its first run",
            f"session {str(session.get('predictions_sha256'))[:16]} / file {sha[:16]}")]
    chains = R.chain_members(pred)
    members = chains["F5"]
    cmap = {d: f for f, d in members.items()}
    hid = pred["hub"]["id"]
    stock = stock or T.stock_script_source()
    roots = D.mod_roots() if roots is None else roots
    runs = read_session5(run_dir, pred, stock=stock, roots=roots, session=session)
    by_i = {r["i"]: r for r in runs}
    cov = {s: [r for r in runs if r["side"] == s and not r["why_void"]] for s in SIDES}
    dig = {s: [r["digest"] for r in cov[s]] for s in SIDES}
    pairs = [(f, by_i[f["rec"]["partner"]]) for f in cov["F5"] if f["rec"].get("partner") in by_i
             and not by_i[f["rec"]["partner"]]["why_void"]]
    snap = run_dir / "scripts" / f"{hid}.eb"
    hub_idx = T.ScriptIndex(snap.read_bytes(), field_id=hid) if snap.is_file() else None
    recon: dict = {}

    def state(r):
        """The calibrated state at the run's own wake row, over its whole raw run (memoized)."""
        if r["i"] not in recon:
            w = wake_row(r["raw"] or [], pred, members if r["side"] == "F5" else {})
            recon[r["i"]] = (reconstruct(r["raw"] or [], w.line if w is not None else None,
                                         saturate=pred["stockstate"]["saturate"]), w)
        return recon[r["i"]]

    def enough(*sides) -> bool:
        return all(len(cov[s]) >= n_min for s in sides)

    def void(*sides) -> str:
        return "too few covered runs -- " + ", ".join(f"{s} {len(cov[s])}/{n_min}" for s in sides)

    def cls_text(r) -> str:
        sc = r.get("stop_class")
        return "" if not sc else f"{sc['cls']}" + (f" @{sc['point']}" if sc["point"] else "")

    # -- R5-RUNS -------------------------------------------------------------------------------------------
    order = pred["order"]
    struct = []
    if [x["side"] for x in recs[:len(order)]] != order[:len(recs[:len(order)])]:
        struct.append(f"the runs are {[x['side'] for x in recs[:len(order)]]}, not the frozen order")
    extra = recs[len(order):]
    if any(not x.get("rerun") for x in extra) or len(extra) > pred["rerun"]["max"]:
        struct.append(f"{len(extra)} runs after the six, {sum(1 for x in extra if x.get('rerun'))} of them re-runs "
                      f"(at most {pred['rerun']['max']})")
    if [x.get("i") for x in recs] != list(range(1, len(recs) + 1)):
        struct.append("the runs are not numbered 1..n")
    struct += pairing_faults5(runs, pred)
    struct += [f"{r['label']}: {b}" for r in runs for b in r["broken"]]
    tally = "; ".join(f"{s} {len(cov[s])} covered / {sum(1 for r in runs if r['side'] == s) - len(cov[s])} VOID"
                      for s in SIDES)
    voids = [f"{r['label']} [{cls_text(r) or 'VOID'}]: {', '.join(r['why_void'][:3])}" for r in runs if r["why_void"]]
    out.append((False if struct else True if enough(*SIDES) else None,
                f"R5-RUNS: the frozen six in order (S F5 x3), then re-runs only (none after the halt); the pairing; "
                f">= {n_min} covered runs per side",
                ("; ".join(struct[:4]) + " || " if struct else "") + tally
                + (" || VOID " + " | ".join(voids[:6]) if voids else "")))

    # -- R5-DONOR (every run read; an F5 run that never reached 31111, its raw clause only) ----------------
    bad, f5_read = [], 0
    rung3 = set(range(30830, 30853))
    for r in runs:
        if r["raw"] is None:
            continue
        wrong = Counter()
        if r["side"] == "F5":
            f5_read += 1
            cut = next((j for j, x in enumerate(r["raw"]) if x.k in ("w", "r") and x.fld == pred["start"]["F5"]),
                       len(r["raw"]))
            for x in r["raw"][:cut]:
                if x.k not in ("w", "r", "c"):
                    continue
                if x.fld == hid and x.don != hid:
                    wrong[f"hub row don {x.don} (want {hid})"] += 1
                elif x.fld in members:
                    wrong[f"member {x.fld} before the start"] += 1
            for x in (r["rows"] or []):
                if x.k not in ("w", "r", "c"):
                    continue
                if x.fld in members:
                    if x.don != members[x.fld]:
                        wrong[f"member {x.fld} don {x.don} (want {members[x.fld]})"] += 1
                else:
                    wrong[f"{'the hub' if x.fld == hid else 'real' if T.real_field(x.fld) else 'id'} {x.fld} after "
                          f"the start"] += 1
        else:
            for x in (r["rows"] or []):
                if x.k not in ("w", "r", "c"):
                    continue
                if x.fld in members or x.fld == hid or x.fld in rung3 or not T.real_field(x.fld) or x.don != x.fld:
                    wrong[f"stock row in {x.fld} don {x.don}"] += 1
        bad += [f"{r['label']}: {w} x{n}" for w, n in wrong.items()]
    out.append((False if bad else True if f5_read else None,
                "R5-DONOR: every F5 row from the start stands in a member and names its donor, every S row in a real "
                "field naming itself; before the start, hub rows name the hub and no row stands in a member",
                "; ".join(bad[:6]) or (f"{f5_read} F5 runs read" if f5_read else "no F5 run read")))

    # -- R5-JOIN (every run digested) ------------------------------------------------------------------------
    read = [r for r in runs if r["digest"] is not None]
    fails = [(r["label"], x.fld, x.target, x.ip, why) for r in read for x, why in r["digest"].failures]
    notes = sorted({f"{r['label']}: {n}" for r in read for n in r["digest"].notes})
    out.append((False if len(fails) > C["R5-JOIN"]["max_failures"] or notes else True if read else None,
                "R5-JOIN: every script row from the start field on joins a store in the bytes its side ran",
                f"{len(fails)} failures {fails[:4]}; notes {notes[:3]}; {len(read)} runs digested"))

    # -- R5-REACH --------------------------------------------------------------------------------------------
    f5 = [r for r in runs if r["side"] == "F5"]
    points = fork_stop_points(runs)
    stops = [(r["label"], r["stop_class"]) for r in f5 if r.get("stop_class")]
    fs = [f"{l} FORK-STOP @{c['point']}: {c['why'][:90]}" for l, c in stops if c["cls"] == "FORK-STOP"]
    un = [f"{l} UNCLASSED: {c['why'][:90]}" for l, c in stops if c["cls"] == "UNCLASSED"]
    dr = [f"{l} DRIVE: {c['why'][:70]}" for l, c in stops if c["cls"] == "DRIVE"]
    twice = {p: n for p, n in points.items() if n >= 2}
    ok = False if twice else True if (not points and not un and len(cov["F5"]) >= n_min) else None
    out.append((ok, "R5-REACH: the fork does not stop where stock goes on -- no F5 run FORK-STOPs, twice at one "
                    "point FAILs",
                (f"FORK-STOPPED twice at {twice} || " if twice else "")
                + f"{len(cov['F5'])} F5 runs covered; " + " | ".join(fs + un + dr) if (fs or un or dr)
                else f"{len(cov['F5'])} F5 runs covered, no FORK-STOP, no UNCLASSED stop"))

    # -- R5-PREFIX (every F5 run that reached 31111 and was digested, covered or not, partner covered) ------
    bad, n_read = [], 0
    for r in f5:
        p = by_i.get(r["rec"].get("partner"))
        if r["digest"] is None or p is None or p["why_void"]:
            continue
        n_read += 1
        extra_keys = keyset(r["digest"], pred) - keyset(p["digest"], pred)
        if extra_keys:
            bad.append(f"{r['label']} (partner {p['label']}, {'covered' if not r['why_void'] else cls_text(r)}): "
                       f"{len(extra_keys)} keys its partner never wrote {_show(extra_keys)}")
    out.append((False if bad else True if n_read else None,
                "R5-PREFIX: THE PAIRED-WALK LAW for runs that did not finish -- every F5 run that reached 31111 wrote "
                "only keys its partner wrote",
                "; ".join(bad[:4]) or (f"{n_read} F5 runs read, each a subset of its partner's" if n_read
                                       else "no such F5 run")))

    # -- R5-STAMP ----------------------------------------------------------------------------------------
    H = pred["hub"]
    layout = T.stock_layout(dig["S"]) if dig["S"] else {}
    bad, reached = [], 0
    for r in f5:
        if r["raw"] is None:
            continue
        rows = hub_rows(r, pred)
        did = r["rows"] is not None
        reached += did
        probs = []
        stamps = []
        for x in rows:
            if x.k == "r":
                probs.append(f"list: residue on byte {x.byte} in the hub")
                continue
            if x.src != "eb" or x.don != hid or x.add:
                probs.append(f"src/don: a {x.src} {'count' if x.k == 'c' else 'row'} naming don {x.don}")
            if x.k == "w":
                # the width clause, on EVERY hub store: a changed neighbour byte outside the variable stock writes at
                # the store's start byte (T.outside_target over the covered stock runs' layout) -- round 4's class
                for b, (o, v) in x.byte_changes().items():
                    if b != x.byte:
                        why = T.outside_target(layout, x.byte, b)
                        if why:
                            probs.append(f"width: {x.target} = {x.new} changed byte {b} {o} -> {v} ({why})")
            j = hub_idx.join(x, donor=hid) if hub_idx is not None and x.src == "eb" and not x.add else None
            if j is None or j.status != "store":
                probs.append(f"join: e{x.sid} t{x.tag} ip {x.ip} {x.target}: "
                             f"{'no hub snapshot' if hub_idx is None else 'no script row' if j is None else j.reason[:80]}")
            elif (x.sid, x.tag) == (0, 0) and x.target in H["prologue_targets"]:
                continue                            # the prologue: Main_Init's sound-environment idiom
            if x.k == "c":
                probs.append(f"list: suppressed stores at e{x.sid} t{x.tag} ip {x.ip} {x.target}")
                continue
            stamps.append((x, j.rel if j is not None and j.status == "store" else None))
        got = [(x.sid, x.tag, x.ip, rel, x.target, x.old, x.new) for x, rel in stamps]
        want = [(s["sid"], s["tag"], s["ip"], s["off"], s["target"], s["old"], s["new"]) for s in H["stamp"]]
        if got != want and (did or got != want[:len(got)]):
            probs.append(f"list: the stamps are {[(g_[3], g_[4], g_[5], g_[6]) for g_ in got]}, not the frozen "
                         f"{[(w[3], w[4], w[5], w[6]) for w in want]}")
        # clause (3) on EVERY run with a hub row, reached or not (the frozen claim, as amended): a pick that led
        # elsewhere -- the stamps, then 31104 -- never reaches 31111, and only this clause can see it
        last = max((j for j, x in enumerate(r["raw"] or []) if x.fld == hid and x.k in ("w", "r")), default=None)
        if last is not None:
            nxt = next((x for x in r["raw"][last + 1:] if x.k in ("w", "r")), None)
            if nxt is not None and nxt.fld != pred["start"]["F5"]:
                probs.append(f"entry: the first row after the hub stands in {nxt.fld}, not {pred['start']['F5']}")
        elif did:
            probs.append("list: no row in the hub")
        bad += [f"{r['label']}: {p_}" for p_ in dict.fromkeys(probs)]
    out.append((False if bad else True if reached >= n_min else None,
                "R5-STAMP: the hub's rows are the frozen seed -- the prologue and exactly the three stamps, joined "
                "against the hub's own bytes, the entry next, no stamp wider than its variable",
                "; ".join(bad[:5]) or (f"{reached} F5 runs reached {pred['start']['F5']}, each stamped "
                                       f"{[(s['target'], s['old'], s['new']) for s in H['stamp']]}" if reached >= n_min
                                       else f"only {reached} F5 runs reached {pred['start']['F5']}")))

    # -- R5-STOCKSTATE --------------------------------------------------------------------------------------
    p = pred["stockstate"]
    what = ("R5-STOCKSTATE: fresh stock runs reproduce session 4's beat-instant state (a regression check on the "
            "stock side and the reconstructor, not seed evidence)")
    if not enough("S"):
        out.append((None, what, void("S")))
    else:
        fail, vd, shown = [], [], []
        for r in cov["S"]:
            rc, w = state(r)
            if rc["contradictions"]:
                vd.append(f"{r['label']}: {len(rc['contradictions'])} contradictions, first {rc['contradictions'][0]}")
                continue
            if w is None:
                vd.append(f"{r['label']}: no wake row")
                continue
            unc = {b >> 3 for b in rc["uncertain"]}
            ch = changed_bytes(rc) - set(p["input_timing_bytes"])
            frozen = set(p["changed_from_new_game"])
            stamp = {int(b): v for b, v in p["stamp_bytes"].items()}
            u = sorted(unc & (frozen | ch | set(stamp)))
            if u:
                vd.append(f"{r['label']}: uncertain bytes {u}")
                continue
            got = {b: byte_value(rc["known"], b) for b in stamp}
            if any(v is None for v in got.values()):
                vd.append(f"{r['label']}: stamp bytes not known {got}")
                continue
            if got != stamp:
                fail.append(f"{r['label']}: stamp bytes {got}, want {stamp}")
            if ch != frozen:
                fail.append(f"{r['label']}: changed from New Game gains {sorted(ch - frozen)} loses "
                            f"{sorted(frozen - ch)}")
            zone = sorted(b for b, v in rc["known"].items() if v and (b >> 3) in p["zone_bytes"])
            if zone != sorted(p["zone_set_bits"]):
                fail.append(f"{r['label']}: set zone bits {zone}, want {p['zone_set_bits']}")
            shown.append(f"{r['label']} {rc['checked']} bit checks")
        out.append((False if fail else None if vd else True, what,
                    "; ".join(fail[:4] + vd[:3]) or f"(a) (b) (c) hold in every covered stock run; calibrated: "
                                                    f"{', '.join(shown)}, 0 contradictions"))

    # -- R5-STATE (pairwise) ------------------------------------------------------------------------------
    what = "R5-STATE: the seed lands on stock's state -- every covered pair's wake-instant state equal, bit for bit"
    if len(pairs) < n_min:
        out.append((None, what, f"{len(pairs)} covered pairs (want >= {n_min})"))
    else:
        fail, vd = [], []
        skip = {pred["timing_site"]["byte"]}
        for f, s in pairs:
            (rf, wf), (rs, ws) = state(f), state(s)
            if rf["contradictions"] or rs["contradictions"]:
                vd.append(f"{f['label']}/{s['label']}: calibration contradictions "
                          f"{(rf['contradictions'] or rs['contradictions'])[0]}")
                continue
            if wf is None or ws is None:
                vd.append(f"{f['label']}/{s['label']}: no wake row")
                continue
            bits = {b for b in set(rf["known"]) | set(rs["known"]) if (b >> 3) not in skip}
            u = sorted({b >> 3 for b in bits & (rf["uncertain"] | rs["uncertain"])})
            if u:
                vd.append(f"{f['label']}/{s['label']}: uncertain compared bytes {u}")
                continue
            one = sorted({b >> 3 for b in bits if (b in rf["known"]) != (b in rs["known"])})
            diff = sorted({b >> 3 for b in bits if b in rf["known"] and b in rs["known"]
                           and rf["known"][b] != rs["known"][b]})
            if one or diff:
                fail.append(f"{f['label']}/{s['label']}: bytes differ {diff}"
                            + (f", known on one side only {one}" if one else ""))
        out.append((False if fail else None if vd else True, what,
                    "; ".join(fail[:4] + vd[:3]) or f"{len(pairs)} covered pairs equal at the wake, byte 299 aside"))

    # -- R5-SAME -------------------------------------------------------------------------------------------
    what = "R5-SAME: the seed's echo -- 359's 297 store and the wake's SC store are same-value in F5, changing in S"
    if not enough("S", "F5"):
        out.append((None, what, void("S", "F5")))
    else:
        bad = []
        for pat in C["R5-SAME"]["stores"]:
            for side in SIDES:
                for r in cov[side]:
                    hit = [o for k, o in r["digest"].keys.items() if R._matches(pat, k)]
                    if not hit:
                        bad.append(f"{r['label']}: no {pat['name']}")
                        continue
                    row = hit[0].row
                    if side == "F5" and (row.same != 1 or row.old != pat["f5_old"]
                                         or row.fld != cmap.get(pat["donor"])):
                        bad.append(f"{r['label']}: {pat['name']} in {row.fld} old {row.old} same {row.same}")
                    if side == "S" and (row.same != 0 or row.old != pat["s_old"]):
                        bad.append(f"{r['label']}: {pat['name']} old {row.old} same {row.same}")
        out.append((not bad, what, "; ".join(bad[:4]) or "both stores as frozen on both sides"))

    # -- R5-SEGMENT (pairwise, the segment window) -----------------------------------------------------------
    p = C["R5-SEGMENT"]
    what = "R5-SEGMENT: both sides run the same scripted segment write for write, SC 2600 against 2540 included"
    if len(pairs) < n_min:
        out.append((None, what, f"{len(pairs)} covered pairs (want >= {n_min})"))
    else:
        def seg_keys(d):
            w = R.wake_line(d, pred)
            return {k for k, at in _first_at(d).items() if w is not None and at <= w and not _is_timing(k, pred)}
        fail, thin = [], []
        for f, s in pairs:
            a, b = seg_keys(f["digest"]), seg_keys(s["digest"])
            if a != b:
                fail.append(f"{f['label']}/{s['label']}: F5 only {len(a - b)} ({sum(1 for k in a - b if k.off < 0)} "
                            f"prepend) {_show(a - b, 3)}, S only {len(b - a)} {_show(b - a, 3)}")
        for r in cov["S"]:
            ks = seg_keys(r["digest"])
            lack = sorted(set(p["donors"]) - {k.donor for k in ks})
            if len(ks) < p["min_keys"] or lack:
                thin.append(f"{r['label']}: {len(ks)} segment keys (want >= {p['min_keys']})"
                            + (f", none from {lack}" if lack else ""))
        out.append((False if fail else None if thin else True, what,
                    "; ".join(fail[:3] + thin[:3]) or f"{len(pairs)} pairs equal; stock segment keys "
                                                     f"{[len(seg_keys(r['digest'])) for r in cov['S']]}"))

    reports = {}
    c = T.compare(dig["S"], dig["F5"], members=members) if dig["S"] and dig["F5"] else None
    if c is not None:
        reports["rung5_report_S_vs_F5.txt"] = T.report(
            c, title=f"story trace F5: stock Dali x{len(dig['S'])} vs the hub lane (hub {hid} + 12 pure members) "
                     f"x{len(dig['F5'])} (covered runs)", writers=True)

    # -- R5-PING --------------------------------------------------------------------------------------------
    p = C["R5-PING"]
    what = "R5-PING: the ping, written by member(450) -- matched, never across a seam; stock WRITERS names only 450"
    if not enough("S", "F5"):
        out.append((None, what, void("S", "F5")))
    else:
        bad = []
        got = dict(T.writers(dig["S"]).get((p["target"], p["value"]), Counter()))
        want = {int(w): len(dig["S"]) for w in p["writers"]}
        if got != want:
            bad.append(f"stock writers {got} (want {want})")
        for r in cov["F5"]:
            d = r["digest"]
            mine = [(k, o) for k, o in d.keys.items() if R._matches(p["pattern"], k)]
            seam = [k for k in d.seam_keys if R._matches(p["pattern"], k)]
            if not mine or seam:
                bad.append(f"{r['label']}: member ping keys {len(mine)}, across a seam {len(seam)}")
            for k, o in mine:
                if o.row.fld != cmap[p["pattern"]["donor"]] or o.row.don != p["pattern"]["donor"]:
                    bad.append(f"{r['label']}: the ping in {o.row.fld} don {o.row.don}")
                if k not in c.matched:
                    bad.append(f"{r['label']}: {_show([k])} not MATCHED")
        fw = set(T.writers(dig["F5"]).get((p["target"], p["value"]), Counter()))
        if fw != {p["pattern"]["donor"]}:
            bad.append(f"F5 writers {sorted(fw)}")
        out.append((not bad, what, "; ".join(bad[:4]) or f"stock writers {got}; F5 writers {sorted(fw)}, matched"))

    # -- R5-NOSEAM ------------------------------------------------------------------------------------------
    what = "R5-NOSEAM: no seam anywhere -- 450 is entered as member 31112, and no row after the start leaves the chain"
    if not enough("F5"):
        out.append((None, what, void("F5")))
    else:
        bad = []
        for r in cov["F5"]:
            d = r["digest"]
            if d.seams or d.seam_keys:
                bad.append(f"{r['label']}: seams {[s.origin + ' -> ' + str(s.to) for s in d.seams][:2]}, "
                           f"{len(d.seam_keys)} seam keys")
            out_rows = sorted({x.fld for x in r["rows"] if x.k in ("w", "r") and x.fld not in members})
            if out_rows:
                bad.append(f"{r['label']}: rows outside the members in {out_rows}")
            m450 = cmap[450]
            if not any(x.fld == m450 and x.don == 450 for x in r["rows"] if x.k == "w"):
                bad.append(f"{r['label']}: 450 never entered as member {m450}")
        if c is not None and (c.across_seam or c.seam_only):
            bad.append(f"ACROSS SEAM {len(c.across_seam)}, SEAM ONLY {len(c.seam_only)}")
        out.append((not bad, what, "; ".join(bad[:4]) or "no seam, no row outside the chain, 450 a member"))

    # -- R5-MIRROR ------------------------------------------------------------------------------------------
    p = C["R5-MIRROR"]
    what = "R5-MIRROR: S vs F5 -- FORK ONLY, STOCK ONLY, ACROSS SEAM and SEAM ONLY empty, no clobber (the timing site aside)"
    if not enough("S", "F5"):
        out.append((None, what, void("S", "F5")))
    else:
        fo = [k for k in c.fork_only if not _is_timing(k, pred)]
        so = [k for k in c.stock_only if not _is_timing(k, pred)]
        fail = bool(fo or so or c.across_seam or c.seam_only or c.clobbers)
        common = set.intersection(*[set(d.keys) for d in dig["S"]])
        tl = {r["label"]: R.tour_line(r["rows"], r["digest"], pred, {}) for r in cov["S"]}
        cut = {r["label"]: R._first_line(r["rows"], lambda x: x.fld == p["seam_field"]) for r in cov["S"]}
        tour = [k for k in common if all(tl[d.label] is not None and d.keys[k].at >= tl[d.label] for d in dig["S"])]
        post = [k for k in common if all(cut[d.label] is not None and d.keys[k].at >= cut[d.label] for d in dig["S"])]
        thin = []
        if len(common) < p["min_keys"]:
            thin.append(f"{len(common)} keys in every stock run (want >= {p['min_keys']})")
        lack = sorted(set(p["tour_donors"]) - {k.donor for k in tour})
        if len(tour) < p["min_tour_keys"] or lack:
            thin.append(f"{len(tour)} tour keys (want >= {p['min_tour_keys']})" + (f", none from {lack}" if lack else ""))
        lack = sorted(set(p["post_donors"]) - {k.donor for k in post})
        if len(post) < p["min_post_keys"] or lack:
            thin.append(f"{len(post)} keys from 450 on (want >= {p['min_post_keys']})"
                        + (f", none from {lack}" if lack else ""))
        out.append((False if fail else None if thin else True, what,
                    f"{len(fo)} FORK ONLY {_show(fo)}; {len(so)} STOCK ONLY {_show(so)}; {len(c.across_seam)} ACROSS "
                    f"SEAM; {len(c.seam_only)} SEAM ONLY; {len(c.clobbers)} clobbers || stock guard: {len(common)} "
                    f"keys, {len(tour)} in every tour, {len(post)} from 450 on"
                    + (f" || the stock guard is thin ({'; '.join(thin)})" if thin else "")))

    # -- R5-PARTIAL (pairwise) ----------------------------------------------------------------------------
    what = "R5-PARTIAL: THE PAIRED-WALK LAW -- every covered pair writes the same keys (the timing site aside)"
    if len(pairs) < n_min:
        out.append((None, what, f"{len(pairs)} covered pairs (want >= {n_min})"))
    else:
        fail = []
        within = []
        for f, s in pairs:
            a, b = keyset(f["digest"], pred), keyset(s["digest"], pred)
            if a != b:
                fail.append(f"{f['label']}/{s['label']}: F5 only {_show(a - b, 3)}, S only {_show(b - a, 3)}")
            within.append(a & b)
        order_keys = set.union(*within) - set.intersection(*within)
        out.append((not fail, what, "; ".join(fail[:4]) or
                    f"{len(pairs)} pairs equal; {len(order_keys)} keys differ between pairs and agree within each "
                    f"(the walk's order, listed) {_show(order_keys, 3)}"))

    # -- R5-ADVANCE -----------------------------------------------------------------------------------------
    p = C["R5-ADVANCE"]
    what = "R5-ADVANCE: the story advances to 2610 in member(354), on the partner's step, matched"
    if not enough("S", "F5"):
        out.append((None, what, void("S", "F5")))
    else:
        bad = []
        for f, s in pairs:
            first = next((x for x in f["rows"] if x.k != "c" and x.sc >= p["sc"]), None)
            if first is None:
                bad.append(f"{f['label']}: never reached SC {p['sc']}")
                continue
            o = next((o for k, o in f["digest"].keys.items() if o.row.line == first.line), None)
            k = o.key if o is not None else None
            if (first.k != "w" or first.fld != cmap[p["pattern"]["donor"]] or first.don != p["pattern"]["donor"]
                    or k is None or not R._matches(p["pattern"], k)):
                bad.append(f"{f['label']}: first row at SC >= {p['sc']} is {first.k} in {first.fld} (don {first.don}) "
                           f"{first.target if first.k == 'w' else ''}")
            elif k not in c.matched:
                bad.append(f"{f['label']}: the advance {_show([k])} is not MATCHED")
            a_f = adv_point(f["log"]["log"], members, p["sc"])
            a_s = adv_point(s["log"]["log"], {}, p["sc"])
            if a_f != a_s:
                bad.append(f"{f['label']}: advanced at step {a_f}, its partner {s['label']} at {a_s}")
        out.append((not bad, what, "; ".join(bad[:4]) or
                    f"every covered F5 run advanced in member({p['pattern']['donor']}) at its partner's step "
                    f"{sorted({str(adv_point(f['log']['log'], members, p['sc'])) for f, _s in pairs})}"))

    # -- R5-LATCH ---------------------------------------------------------------------------------------------
    p = C["R5-LATCH"]
    what = "R5-LATCH: the eight hub-gated writes and the wake's two latches are written on both sides by the members"
    if not enough("S", "F5"):
        out.append((None, what, void("S", "F5")))
    else:
        bad, parts = [], []
        for pat in p["patterns"]:
            in_s = all(any(R._matches(pat, k) for k in d.keys) for d in dig["S"])
            in_f = all(any(R._matches(pat, k) for k in d.keys) for d in dig["F5"])
            seam = any(R._matches(pat, k) for d in dig["F5"] for k in d.seam_keys)
            if not (in_s and in_f) or seam:
                bad.append(f"{pat['name']}: every stock run {in_s}, every F5 run {in_f}, across a seam {seam}")
            parts.append(pat["name"].split(":")[0])
        if c.clobbers:
            bad.append(f"clobbers {[(x.key.donor, x.key.target, x.byte, x.old, x.new) for x in c.clobbers][:3]} "
                       f"(a consistency check P-PURE implies)")
        out.append((not bad, what, "; ".join(bad[:5]) or f"all {len(p['patterns'])} on both sides, no clobber"))

    # -- R5-PREEMPT (a consistency check P-PURE implies) -----------------------------------------------------
    what = "R5-PREEMPT: PRE-EMPTED is empty and no F5 key is a prepend or unaligned (a consistency check P-PURE implies)"
    if not enough("S", "F5"):
        out.append((None, what, void("S", "F5")))
    else:
        pre = [k for d in dig["F5"] for k in (*d.keys, *d.seam_keys) if k.off < 0 or not k.aligned]
        out.append((not c.pre_empted and not pre, what,
                    f"PRE-EMPTED {[(x.target, x.value) for x in c.pre_empted][:4]}; prepend/unaligned "
                    f"{_show(set(pre), 4)}"))

    # -- the summary -----------------------------------------------------------------------------------------
    lines = [f"story trace F5 (the hub lane) -- session {session.get('label')} ({session.get('started')} .. "
             f"{session.get('finished', 'unfinished')}); predictions {pred_path.name} v{pred.get('version')}"
             + (f"; re-runs stopped: {session['rerun_stop']}" if session.get("rerun_stop") else ""), ""]
    if session.get("hubleg"):
        lines.append(f"  P-HUBLEG record: {json.dumps(session['hubleg'])[:300]}")
    for r in runs:
        rec = r["rec"]
        lines.append(f"  {r['label']:<6} {rec.get('t0', '?')}..{rec.get('t1', '?')}s  "
                     f"{'VOID' if r['why_void'] else 'covered'}{' (re-run)' if rec.get('rerun') else ''}  "
                     f"stop: {rec.get('stop', rec.get('skipped', rec.get('install', '?')))}"
                     + (f"  [phase {rec.get('phase')}]" if r["why_void"] and rec.get("phase") else ""))
        if r["why_void"]:
            lines.append(f"         VOID [{cls_text(r) or '-'}]: {'; '.join(r['why_void'])}")
        if r["side"] == "F5":
            mate = by_i.get(rec.get("partner"))
            want = D.entered_walk(mate["log"]["log"]) if mate is not None and mate["log"] is not None else None
            got = D.entered_walk(r["log"]["log"], members, legs=("replay",)) if r["log"] is not None else None
            hub = next((x for x in (r["log"] or {}).get("log", []) if x.get("k") == "hub"), None)
            lines.append(f"         partner: S#{rec.get('partner')}"
                         + (f"; replayed {len(got)} of its {len(want)} steps" if got is not None and want is not None
                            else "") + f"; hub rows {len(hub_rows(r, pred))}"
                         + (f"; hub leg {hub.get('tries')} tries, {hub.get('presses')} presses, {hub.get('t')}s"
                            if hub else ""))
        if r["rows"] is not None:
            lines.append(f"         places: {R._places(r['rows'], members if r['side'] == 'F5' else {})}"
                         + (f"   (rows before the start field, not compared: fields {r['pre']})" if r["pre"] else ""))
    word = {True: "PASS", False: "FAIL", None: "VOID"}
    lines += ["", "CHECKS"] + [f"  {word[ok]}  {what}\n        {detail}" for ok, what, detail in out]
    reports["rung5_summary.txt"] = "\n".join(lines) + "\n"
    return out, reports


# ======================================================================== the session (in game)
def run(g) -> None:
    from harness import HarnessError

    cap = g.state.storytrace
    if not g.check(isinstance(cap, dict) and cap.get("proto") == T.PROTO,
                   "P-CAP: the engine advertises the story trace at proto 1", str(cap)):
        return
    pred, sha = load_predictions()
    b, wk, H = pred["budget"], pred["wake"], pred["hub"]
    members = chain(pred)
    every = {**members, H["id"]: H["id"]}
    stock = T.stock_script_source()
    roots = D.mod_roots()
    ran = T.mod_script_source(roots, fallback=stock)
    side_tours = tours5(pred, ran=ran, stock=stock)
    pre = preflight5(pred, roots, stock, side_tours, ran=T.mod_script_source(roots))
    for ok, what, detail in pre:
        g.check(ok, what, detail)
    if not all(ok for ok, _w, _d in pre):
        return
    fp0 = R.fingerprint(roots, every)
    scripts = g.run_dir / "scripts"   # the bytes each member and the hub ran, kept: the analysis outlives the deploy
    scripts.mkdir(exist_ok=True)
    for fid in sorted(every):
        (scripts / f"{fid}.eb").write_bytes(ran(fid).data)
    session = {"label": g.run_dir.name, "predictions": str(PREDICTIONS), "predictions_sha256": sha,
               "predictions_version": pred.get("version"), "order": pred["order"], "budget": b,
               "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "install": fp0, "runs": []}

    def save() -> None:
        (g.run_dir / SESSION_FILE).write_text(json.dumps(session, indent=1), encoding="utf-8")

    save()
    ok, detail, leg = p_hubleg(g, pred)
    session["hubleg"] = dict(leg, ok=ok, detail=detail)
    save()
    if not g.check(ok, "P-HUBLEG: in game, untraced, the hub leg reaches the menu, the stay row stays, and the hub "
                       "throws nothing", detail):
        return
    mark = g.log_mark()                   # NC-THROW's mark: after P-HUBLEG, which judged the hub's own exceptions
    t0 = time.time()
    deadline = t0 + b["session_s"]

    def partner_walk(k):
        """``(walk, why not)`` for an F5 partnering stock run ``k``, judged by the frozen coverage rule
        (read_session5, the analysis's own reading); whatever that read raises makes this one F5 VOID."""
        if k is None:
            return None, "no stock run before it to partner"
        try:
            got = {r["i"]: r for r in read_session5(g.run_dir, pred, stock=stock, roots=roots, session=session)}
            p = got.get(k)
            if p is None or p["side"] != "S":
                return None, f"its partner #{k} is not a recorded stock run"
            if p["why_void"]:
                return None, f"partner S#{k} VOID: {'; '.join(p['why_void'])[:200]}"
            return D.entered_walk(p["log"]["log"]), None
        except Exception as err:                  # noqa: BLE001 -- one unreadable record must not end the session
            return None, f"partner S#{k} unreadable: {type(err).__name__}: {str(err)[:200]}"

    def one(i: int, side: str, rerun: bool = False, partner: int | None = None) -> None:
        """One run -- rung3_trace.run's one() (rung3_trace.py:394-508) for S / F5, recording ``phase``: the stage
        the drive was in (lead-in, hub, segment, replay, tour, settle), which the collection never overwrites -- the
        stop class reads it -- and ``at`` (field, place, SC) when it raised."""
        tour = side_tours[side]
        trace_name, log_name = R.run_names(i, side)
        rec = {"i": i, "side": side, "start": pred["start"][side], "trace": trace_name, "log": log_name}
        if rerun:
            rec["rerun"] = True
        walk = None
        if side == "F5":
            rec["partner"] = partner if rerun else R.round_partner(pred["order"], i)
            walk, why = partner_walk(rec["partner"])
            if walk is None:
                rec["skipped"] = why
            else:
                rec["walk"] = walk
        if not rec.get("skipped"):
            if time.time() + b["run_min_s"] > deadline:
                rec["skipped"] = f"session budget: under {b['run_min_s']}s of the {b['session_s']}s left"
            else:
                moved = R._changed(fp0, R.fingerprint(roots, every))
                if moved:
                    rec["install"] = "before the run: " + moved
        if rec.get("skipped") or rec.get("install"):
            session["runs"].append(rec)
            save()
            tour.say(f"run {i} ({side}) VOID, not run: {rec.get('skipped') or rec['install']}")
            return
        log: list = []
        stop = "not reached"
        smark = None
        rec["t0"] = round(time.time() - t0)
        g.shot_prefix = f"run{i}-{side}"

        def phase(name: str) -> None:
            rec["phase"] = name

        def at() -> dict:
            try:
                st = g.state
                return {"field": st.field_id, "place": tour.place(st.field_id), "sc": st.scenario}
            except Exception:                     # noqa: BLE001 -- best effort, on a run that already stopped
                return {}

        try:
            phase("lead-in")
            ok_, why = g.restore_baseline()
            if not ok_:
                raise HarnessError(f"between runs, the title could not be restored: {why}")
            g.newgame()
            g.wait_frames(30)
            smark = g.story_mark()
            before = len(g.channel.story_text() or "")
            g.storytrace(True)
            seen = {"n": -1, "rows": []}

            def live_rows() -> list:
                text = g.channel.story_text() or ""
                tail = text[before:] if len(text) >= before else text
                if len(tail) != seen["n"]:
                    try:
                        seen["rows"] = T.parse_text(tail[:tail.rfind("\n") + 1], live=True)
                    except T.TraceError:
                        seen["rows"] = []
                    seen["n"] = len(tail)
                return seen["rows"]

            def engine_donor(fid: int):
                dons = [r.don for r in live_rows() if r.fld == fid and r.k != "c"]
                return dons[-1] if dons else None

            def woke() -> bool:
                return any(r.k == "w" and tour.place(r.fld) == wk["donor"] and r.sid == wk["sid"] and r.tag == wk["tag"]
                           and r.target == wk["target"] and r.new in wk["value"] for r in live_rows())

            enter = None
            if side == "F5":
                def enter() -> None:
                    phase("hub")
                    hub_leg(g, log, pred)
                    phase("segment")
            else:
                phase("segment")
            seg = D.segment(g, log, start=pred["start"][side], sc=pred["start_sc"], beat=pred["beat"],
                            place=tour.place, until=pred["segment_place"], timeout=b["segment_s"], woke=woke,
                            enter=enter)
            rec["segment"] = seg
            tour.say(f"run {i} ({side}) segment: {json.dumps(seg)}")
            if seg["ok"] and walk is not None:
                phase("replay")
                stop = tour.replay(g, log, walk, beat=pred["beat"], max_crossings=b["max_crossings"],
                                   max_passes=b["max_passes"], budget_s=b["tour_s"], deadline=deadline,
                                   engine_donor=engine_donor)
            elif seg["ok"]:
                phase("tour")
                stop = tour.run(g, log, beat=pred["beat"], max_crossings=b["max_crossings"],
                                max_passes=b["max_passes"], budget_s=b["tour_s"], deadline=deadline,
                                engine_donor=engine_donor)
            if seg["ok"]:
                phase("settle")
                try:
                    D.settle(g, log, "after the tour", tour.say)
                except HarnessError as err:
                    rec["settle_error"] = str(err)[:300]
            else:
                stop = f"segment: no control in {pred['segment_place']} at {pred['beat']} after the wake"
        except (HarnessError, D.TourError) as err:
            stop = f"STOPPED: {type(err).__name__}: {str(err)[:300]}"
            rec["at"] = at()
        except Exception as err:                  # noqa: BLE001 -- one run's bug must not cost the others
            stop = f"STOPPED (unexpected): {type(err).__name__}: {str(err)[:300]}"
            rec["at"] = at()
            log.append({"k": "error", "traceback": traceback.format_exc()[-3000:]})
            tour.say(f"!! run {i} ({side}) raised: {traceback.format_exc()[-1500:]}")
        finally:
            g.shot_prefix = ""
            if smark is not None:
                try:
                    rec["traced"] = g.collect_story(g.run_dir / trace_name, smark)
                except HarnessError as err:
                    rec["trace_error"] = str(err)[:300]
            crossings = [x for x in log if x["k"] == "cross"]
            rec.update(stop=stop, t1=round(time.time() - t0), crossings=len(crossings),
                       landed=sum(1 for x in crossings if x.get("landed") is not None and x["landed"] == x.get("to")),
                       fields=sorted({x["now"] for x in crossings if x.get("now")}))
            if walk is not None:
                rec["replayed"] = sum(1 for x in crossings if x.get("verdict") == "replayed")
            moved = R._changed(fp0, R.fingerprint(roots, every))
            if moved:
                rec["install"] = "during the run: " + moved
            choices = [dict(c, why=x["why"]) for x in log if x["k"] == "scene" for c in x.get("choices", [])]
            (g.run_dir / log_name).write_text(json.dumps({"stop": stop, "choices": choices, "log": log}, indent=1),
                                              encoding="utf-8")
            session["runs"].append(rec)
            save()
            tour.say(f"run {i} ({side}) done at {rec['t1']}s [{rec.get('phase')}]: {stop}"
                     + (f" -- VOID: {moved}" if moved else ""))

    for i, side in enumerate(pred["order"], 1):
        one(i, side)
    reruns = 0
    while reruns < pred["rerun"]["max"]:
        try:
            runs = read_session5(g.run_dir, pred, stock=stock, roots=roots, session=session)
            plan = rerun_plan5(runs, pred)
        except Exception as err:                  # noqa: BLE001 -- the six are kept and analysed all the same
            session["rerun_stop"] = (f"the runs could not be read to plan a re-run: {type(err).__name__}: "
                                     f"{str(err)[:200]}")
            side_tours["S"].say(f"!! re-runs stopped: {traceback.format_exc()[-1500:]}")
            break
        if plan is None:
            if halted(runs):
                session["rerun_stop"] = (f"HALTED: two F5 runs FORK-STOPped at {halted(runs)} -- R5-REACH's FAIL is "
                                         f"decided and no run can change it")
            break
        if time.time() + b["run_min_s"] > deadline:
            session["rerun_stop"] = (f"sides {short_sides5(runs, pred)} still short of covered runs, and no run fits "
                                     f"the budget left")
            break
        reruns += 1
        one(len(session["runs"]) + 1, plan[0], rerun=True, partner=plan[1])
    session["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    checks, reports = analyse5(g.run_dir, stock=stock, roots=roots)
    for name, text in reports.items():
        (g.run_dir / name).write_text(text, encoding="utf-8")
    print(reports.get("rung5_summary.txt", "")[:4000], flush=True)
    for ok, what, detail in checks:
        g.check(ok is True, what, ("VOID -- " if ok is None else "") + detail)
    ours = [e for e in g.exceptions_since(mark) if e.name in THROWS
            and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    g.check(not ours, "NC-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
            str([(e.name, e.where) for e in ours[:5]]))


# ======================================================================== the CLI (offline)
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="F5's offline modes: the analysis, the live pre-flight, a build's check.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--analyse", metavar="RUN_DIR", help="a session's run directory")
    mode.add_argument("--preflight", action="store_true", help="the static P-checks on the live install")
    mode.add_argument("--offline-check", metavar="BUILD_DIR",
                      help="P-PURE and P-HUB's byte clauses on an offline build (<BUILD_DIR>/<id>/ per field)")
    ap.add_argument("--predictions", metavar="FILE", default=None,
                    help="read these predictions instead of the file the session recorded / the frozen v3")
    a = ap.parse_args(argv)
    word = {True: "PASS", False: "FAIL", None: "VOID"}
    if a.analyse:
        try:
            checks, reports = analyse5(a.analyse, pred_path=None if a.predictions is None else Path(a.predictions))
        except NotF5 as err:
            print(f"REFUSED: {err}", file=sys.stderr)
            return 2
        for name, text in reports.items():
            (Path(a.analyse) / name).write_text(text, encoding="utf-8")
        print(reports["rung5_summary.txt"])
        return 0 if all(ok is True for ok, _w, _d in checks) else 1
    pred, _sha = load_predictions(Path(a.predictions) if a.predictions else PREDICTIONS)
    stock = T.stock_script_source()
    if a.preflight:
        roots = D.mod_roots()
        ran = T.mod_script_source(roots, fallback=stock)
        checks = preflight5(pred, roots, stock, tours5(pred, ran=ran, stock=stock), ran=T.mod_script_source(roots))
    else:
        checks = offline_check(Path(a.offline_check), pred, stock)
    for ok, what, detail in checks:
        print(f"  {word[ok]}  {what}\n        {detail}")
    return 0 if all(ok is True for ok, _w, _d in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
