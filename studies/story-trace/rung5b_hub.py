"""THE STORY-WRITE TRACE, F5b -- THE POST-WAKE ENTRY: the fixed story-seed resolver's post-advance row (THE SEED IS
THE HAND-OVER STATE OF THE ENTRY) played PAST the wake, against stock Dali and against today's pre-phase row entered
at the same place, under THE PAIRED-WALK LAW.

    py tools/play.py studies/story-trace/rung5b_hub.py --label story-rung5b --timeout 240   # the session
    py studies/story-trace/rung5b_hub.py --analyse <run dir> [--predictions FILE]           # offline, saved traces
    py studies/story-trace/rung5b_hub.py --preflight [--predictions FILE]                   # static P-checks, live
    py studies/story-trace/rung5b_hub.py --offline-check [BUILD_DIR] [--predictions FILE]   # the same, on a build

A SIBLING OF rung5_hub, NEVER AN EDIT OF IT: rung5_hub (H5), rung3_trace (R) and dali_tour (D) are imported and stay
byte-frozen (F5's 28/28 must keep re-analysing identically). They are reused two ways. (1) THE PER-HUB VIEW
``{**pred, "hub": pred["hubs"][side], "budget": pred["budget"]}`` (:func:`hub_view`) serves every H5 function that
reads one hub -- hub_bytes_check, hub_install_check, hub_open, hub_pick, hub_leg, hub_rows, stamps_landed. (2) The
member set stays keyed "F5" (it IS F5's deployed chain, 31101-31112), so H5.chain/chain_map/tours5/pure_check and
R.preflight's P-DEPLOY/P-FLOOR/P-EXITS/P-STOCK run unmodified. Everything that hard-codes F5's two sides is rewritten
here, each citing its original: read_run5b, stop_class5b, judge5b, read_session5b, halted/untwinned/rerun_plan5b,
pairing_faults5b, replay_why5b, p_hubleg5b, preflight5b, analyse5b, run.

THE SIDES (predictions "sides"; rung5b_forks.json names the two hubs):
  S    stock Dali, driven exactly as F5's S: New Game, `warp 359 0 2540`, the game's own segment to the wake, the
       blind tour, settle -- plus two autosave reads: right after the segment (the baseline) and at the run's end.
  F5B  T5B_HUB (31113): its one row is the FIXED resolver's post-advance row -- SC 2600, bits 2078/2086 = 1, words
       208 = 0 / 297 = 1, party_remove garnet/steiner/vivi, party_add zidane, Int16[2] := 6, Field(31101): member(351)
       through the wake room's own exit door, stock's FIRST field entry after the wake. Its drive: the lead-in, a
       pre-leg autosave read, the hub leg and the landing (:func:`enter_past`), a landing read, then the partner's
       walk FROM STEP 2 (``walk[1:]`` -- step 1 IS the hand-over), settle, a run-end read.
  CTL  T5B_CTL (31114): today's pre-phase row (``--pre-phase-control``) with the same entrance -- the calibration
       control, which must FAIL exactly as registered. The same drive, replaying only ``walk[1:2]``
       (:class:`PrefixTour`); its landing read is judged (R5B-CONTROL (e)), its run-end read only recorded.
Order [S, F5B, CTL] x 3; R.round_partner gives F5B and CTL their round's S. THE WALK GATES (predictions
"walk_gate"): an F5B needs its partner's walk[0] == 352.0 -> 351 (else VOID, named, not driven); a CTL needs walk[0:2]
== [352.0 -> 351, 351.0 -> 350] (else "skipped: partner step 2 ...", never counted, and the re-run plan picks a
qualifying S).

THE PRE-FLIGHT, in the frozen order (design 4.9): the static P-CAP, P-MANIFEST, P-DEPLOY, P-HUB x2, P-PARTYOPS,
P-ENTRY, P-PURE, P-FLOOR, P-EXITS, P-STOCK, P-INI, P-PINS (a failure stops the session); P-HUBLEG 31113 then 31114
(:func:`hubleg5b`: the first leg's failure stops it; its autosave clause gets one retry of the leg, whose own failure
is that clause failing -- twice failed only VOIDs R5B-PARTY); P-PARTYREMOVE (a VOID gets one retry; its FAIL or VOID
never stops the session: R5B-PARTY reads it); then NC-THROW's mark.

THE PARTY INSTRUMENT is the sandbox field-entry autosave (design 4.5, E20): ``40000_Common.slot`` of the Memoria
extra file, written synchronously on every field entry before the new field's scripts run. :func:`party_read` is
FRESH only when its st_mtime_ns is after a baseline read taken right before the transition it judges, its sha is
stable over two reads 10 frames apart, and SC / Int16[2] / the field name the arrival. Run-end reads are judged at
the analysis against the trace's own last field entry (:func:`last_entry`).

THE VERDICT IS FROZEN (predictions "verdict", :func:`verdict5b`): PROVEN only when every check PASSes, with at least
3 covered F5B pairs and 2 covered CTL runs; any FAIL is "FAILED: <check>"; otherwise "NOT PROVEN: <half> (<check>:
<why>)" naming the halves (state, latches, party, walk) that are and are not proven. Never a PASS count. So that an
offline --analyse reproduces it, the session RECORDS in its session file what only the live game can judge: the
static pre-flight lines, both P-HUBLEG records, P-PARTYREMOVE, every autosave read, and NC-THROW. A check calibrated by
the control (R5B-LAND/STATE/ECHO/ARRIVAL/PARTY) is VOID while its R5B-CONTROL clause is not PASS, whatever it saw
(checks.json: "each failed clause makes its dependent R5B check VOID as uncalibrated"); calibrated, FAIL before VOID.
Clause (e) calibrates the party instrument alone: its FAIL makes R5B-CONTROL VOID, not FAIL, so a party instrument
that never calibrates reads NOT PROVEN: party, never FAILED (clauses (a)-(d) FAIL it).

THE PREDICTIONS (rung5b_predictions_v1.json) are the next stage's: the dry-run (rung5b_dryrun.py) re-derives every
number and freezes the file. :func:`draft_predictions` builds its skeleton from v3 and the design's constants -- the
keys every function here reads -- leaving ``None`` where only the dry-run may fill a number (:func:`missing_numbers`).
A session refuses to start, and the analysis to read, against a file with a hole.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import struct
import subprocess
import sys
import tempfile
import time
import traceback
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dali_tour as D  # noqa: E402
import rung3_trace as R  # noqa: E402
import rung5_hub as H5  # noqa: E402
from dali_tour import T  # noqa: E402

PREDICTIONS = HERE / "rung5b_predictions_v1.json"
MANIFEST = HERE / "rung5b_forks.json"
F5_MANIFEST = H5.MANIFEST                        # rung5_forks.json: the 12 members' own manifest (F5's chain)
SESSION_FILE = "rung5b_session.json"
SIDES = ("S", "F5B", "CTL")
FORKS = ("F5B", "CTL")
THROWS, WHERE = R.THROWS, R.WHERE
KIT = HERE.parents[1] / "ff9mapkit"               # `py -m ff9mapkit` / pytest run from here (the local package)
P_DIR = Path(r"C:\gd\_ns_playtest\f5b")          # the durable offline build tree (design 4.2)
AUTOSAVE = "SavedData_ww_Memoria_Autosave.dat"    # the sandbox field-entry autosave's Memoria extra file
#: P-PINS: the resolver's seven F5b regression tests -- each must show PASSED (a SKIPPED is not a pass).
PINS = ("test_pre_phase_row_leaves_the_advance_to_the_advance", "test_post_phase_carries_what_the_hand_over_leaves",
        "test_post_phase_refusals", "test_post_phase_roster_rules",
        "test_pre_phase_row_past_the_advance_needs_the_control_flag", "test_real_f5_row_is_unchanged",
        "test_real_dali_post_wake_row")
PREFIX_STOP = "prefix replayed"                   # PrefixTour's stop: CTL's one clean stop
WORD = {True: "PASS", False: "FAIL", None: "VOID"}


# ======================================================================== the frozen predictions
def load_predictions(path: Path = PREDICTIONS) -> tuple:
    """``(predictions, sha256 of the file's bytes)``."""
    return R.load_predictions(path)


def recorded_predictions(session: dict) -> Path:
    """The predictions file a session recorded (H5.recorded_predictions, rung5_hub.py:109-115, with F5b's file as
    the default): its path, or the file of that name here when the path is gone."""
    named = session.get("predictions")
    if not named:
        return PREDICTIONS
    p = Path(named)
    return p if p.is_file() else HERE / p.name


class NotF5B(ValueError):
    """Predictions asked to read a session that is not F5b's -- a side other than S/F5B/CTL, a fork run naming no
    stock partner, predictions of another lane, or predictions with a hole the dry-run never filled: refused, never
    a verdict."""


def hub_view(pred: dict, side: str) -> dict:
    """THE PER-HUB VIEW: ``pred`` with ``hub`` = that side's hub, so every rung5_hub function that reads one hub
    (hub_bytes_check, hub_install_check, hub_open, hub_pick, hub_leg, hub_rows, stamps_landed) reads this one."""
    return {**pred, "hub": pred["hubs"][side], "budget": pred["budget"]}


def chain(pred: dict) -> dict:
    """``{member id: donor}`` -- F5's deployed chain, reused whole (keyed "F5" in the predictions)."""
    return H5.chain(pred)


def members_of(side: str, pred: dict) -> dict:
    """The member set a side's rows are read through: the chain on a fork side, none on S."""
    return chain(pred) if side in FORKS else {}


def place_of(side: str, pred: dict):
    m = members_of(side, pred)
    return lambda fid: m.get(fid, fid)


#: The numbers only the dry-run may fill (a ``None`` there is a hole): ``(path, what)``.
_NUMBERS = (("land.bits", "R5B-LAND's frozen landing set (53 bits with values)"),
            ("control.land_bits", "R5B-CONTROL (b)'s landing set (the landing set plus 2078/2086: 55 bits)"),
            ("hubs.F5B.eb_sha256", "the F5B hub's frozen US .eb sha256"),
            ("hubs.CTL.eb_sha256", "the CTL hub's frozen US .eb sha256"))


def _dig(d, path: str):
    for k in path.split("."):
        d = d.get(k) if isinstance(d, dict) else None
    return d


def missing_numbers(pred: dict) -> list:
    """The frozen numbers the predictions still lack (``None``), named -- [] for a file the dry-run froze."""
    return [f"{p} ({w})" for p, w in _NUMBERS if _dig(pred, p) is None]


def bits_of(values: dict) -> dict:
    """Byte-level registrations -> per-bit ones: ``{byte: [stock, fork]}`` -> ``{bit: [stock bit, fork bit]}``
    for every bit that differs (the reconstructor compares bits)."""
    out = {}
    for b, (s, f) in values.items():
        b = int(b)
        for j in range(8):
            vs, vf = (int(s) >> j) & 1, (int(f) >> j) & 1
            if vs != vf:
                out[str(b * 8 + j)] = [vs, vf]
    return out


def _key(donor, sid, tag, off, target, value, ip=None, name=""):
    k = {"donor": donor, "sid": sid, "tag": tag, "off": off, "target": target, "value": value}
    if ip is not None:
        k["ip"] = ip
    if name:
        k["name"] = name
    return k


def _stamp(off, ip, target, value, old, new):
    return {"sid": 2, "tag": 3, "off": off, "ip": ip, "target": target, "value": value, "old": old, "new": new}


def draft_predictions(v3: dict | None = None) -> dict:
    """The SKELETON of rung5b_predictions_v1.json: every key this module reads, built from v3 (F5's frozen hub rig,
    chain, wake, coverage and patterns, carried) and the design's constants (the two hubs as E13 built them, the
    party table, the SUPP split, the residual R, the verdict rule), with ``None`` where only the dry-run may fill a
    number (:func:`missing_numbers`). The session never reads a draft: the dry-run derives, fills and freezes it."""
    v3 = v3 or H5.load_predictions()[0]
    h3 = v3["hub"]
    rig = {k: h3[k] for k in ("spawn", "narrator", "narrator_pos", "narrator_within", "floor", "options", "pick",
                              "stay", "default", "twist", "twist_expect", "approach", "prologue_targets")}
    prologue = [s for s in h3["static_stores"] if (s["sid"], s["tag"]) == (0, 0)]
    head = ['[[journey]]', 'name  = "Dali (SC 2600)"', 'entry = 31101', 'entrance = 6', 'set_scenario = 2600']
    words = 'set_words = [ { byte = 208, value = 0 }, { byte = 297, value = 1 } ]'

    def hub(side, hid, name, row_id, stamps, row_text, ops, scan, sub, sha):
        return {**rig, "id": hid, "name": name, "lead_in": [hid, 0, v3["start_sc"]], "entry": 31101, "entrance": 6,
                "row_id": row_id, "row_text": row_text,
                "static_stores": prologue + [{k: s[k] for k in ("sid", "tag", "off", "ip", "target", "value")}
                                             for s in stamps],
                "stamp": stamps, "party_ops": ops, "party_scan": scan, "eb_sha256": sha,
                "toml": str(P_DIR / sub / "hub.field.toml"), "journeys": str(P_DIR / sub / "journeys.toml")}

    f5b_stamps = [_stamp(23, 136, "Global.UInt16[0]", 2600, 2540, 2600), _stamp(31, 144, "Global.Bit[2078]", 1, 0, 1),
                  _stamp(40, 153, "Global.Bit[2086]", 1, 0, 1), _stamp(49, 162, "Global.UInt16[208]", 0, 0, 0),
                  _stamp(57, 170, "Global.UInt16[297]", 1, 0, 1), _stamp(95, 208, "Global.Int16[2]", 6, 0, 6)]
    ctl_stamps = [_stamp(23, 136, "Global.UInt16[0]", 2600, 2540, 2600), _stamp(31, 144, "Global.UInt16[208]", 0, 0, 0),
                  _stamp(39, 152, "Global.UInt16[297]", 1, 0, 1), _stamp(95, 208, "Global.Int16[2]", 6, 0, 6)]
    f5b_text = (head[:1] + ['id    = "dali_chain_2600_e6_post"'] + head[1:]
                + ['set_flags = [ { flag = 2078, value = 1 }, { flag = 2086, value = 1 } ]', words,
                   'party_add = [ "zidane" ]', 'party_remove = [ "garnet", "steiner", "vivi" ]'])
    ctl_text = (head[:1] + ['id    = "dali_chain_2600_e6_control"'] + head[1:]
                + [words, 'party_add = [ "garnet", "steiner", "vivi", "zidane" ]'])
    hubs = {"F5B": hub("F5B", 31113, "T5B_HUB", "dali_chain_2600_e6_post", f5b_stamps, f5b_text,
                       [["remove", 2, 66], ["remove", 3, 69], ["remove", 1, 72], ["add", 0, 75], ["field", 31101, 109]],
                       {"adds": [0], "removes": [1, 2, 3]}, "hub",
                       "d140317dd01bb37c9f17bf1b6e39364b4a2e6bc18b27fab1bacde2e40fab4b97"),       # design E13
            "CTL": hub("CTL", 31114, "T5B_CTL", "dali_chain_2600_e6_control", ctl_stamps, ctl_text,
                       [["add", 2, 48], ["add", 3, 57], ["add", 1, 66], ["add", 0, 75], ["field", 31101, 109]],
                       {"adds": [0, 1, 2, 3], "removes": []}, "ctl",
                       "069e9d2f21b826ab4647df30f736bbefc9f950da226873268caaae99c13e8c08")}      # design E13
    residual = {"18": [1, 0], "19": [15, 0], "21": [15, 0], "61": [255, 0], "62": [255, 0], "63": [255, 0],
                "303": [1, 0]}
    ctl_extra = {"238": [1, 0], "241": [6, 0], "251": [6, 0]}
    latch_bits = {str(2078): [1, 0], str(2086): [1, 0]}
    handback_ctl = {**bits_of(residual), **bits_of(ctl_extra), **latch_bits}
    arrival8 = [_key(351, 0, 0, 51, "Global.Int16[9]", 1483, 61), _key(351, 0, 0, 124, "Global.Byte[13]", 1, 134),
                _key(351, 0, 0, 241, "Global.Int16[239]", 2, 251), _key(351, 0, 0, 734, "Global.SByte[238]", 1, 744),
                _key(351, 0, 0, 742, "Global.Int16[241]", 6, 752), _key(351, 0, 0, 770, "Global.UInt16[251]", 6, 780),
                _key(351, 0, 0, 1872, "Global.Byte[13]", 2, 1882), _key(351, 4, 0, 12, "Global.SByte[296]", -64, 22)]
    proven = [_key(351, 0, 0, 132, "Global.Int16[11]", -1, 142), _key(352, 0, 0, 51, "Global.Int16[9]", 1483, 65),
              _key(352, 0, 0, 132, "Global.Int16[11]", -1, 146)]
    blind = [_key(351, 0, 0, 194, "Global.Byte[14]", 0, 204, "guard Byte[14] != 9 and Int16[11] < 0"),
             _key(351, 0, 0, 1377, "Global.Byte[8]", 125, 1387, "guard SC < 2660"),
             _key(352, 0, 0, 194, "Global.Byte[14]", 0, 208, "guard Byte[14] != 9 and Int16[11] < 0"),
             _key(352, 0, 0, 646, "Global.Byte[8]", 125, 660, "guard SC < 2660"),
             _key(352, 2, 0, 12, "Global.SByte[296]", -64, 22, "guard Bit[2102] == 0")]
    supp351 = [k for k in proven + blind if k["donor"] == 351]
    cov3 = v3["coverage"]
    budget = {**v3["budget"], "arrive_s": 60, "run_min_s": {"S": 720, "F5B": 600, "CTL": 240}, "save_frames": 10,
              "expected_minutes": {"S": 10, "F5B": 7.7, "CTL": 1.5, "session": 67, "with_reruns": 128, "cap": 180}}
    return {
        "what": "Story-trace F5b's registered predictions (the post-wake entry): DRAFT -- the dry-run re-derives every "
                "number and freezes this file before any deploy",
        "lane": "F5b", "version": 1,
        "lineage": {"file": "rung5_predictions_v3.json", "carried": "the hub rig, the chain, the wake, the start, the "
                                                                    "budget's numbers, the coverage patterns"},
        "order": ["S", "F5B", "CTL"] * 3,
        "sides": {"S": "stock Dali, as F5's S, plus the autosave reads",
                  "F5B": "T5B_HUB (31113): the fixed post-advance row -> Field(31101) at entrance 6; replays walk[1:]",
                  "CTL": "T5B_CTL (31114): today's pre-phase row at the same entry; replays walk[1:2]"},
        "start": {"S": v3["start"]["S"], "F5B": 31101, "CTL": 31101},
        "entry": {"member": 31101, "donor": 351, "entrance": 6},
        "start_sc": v3["start_sc"], "beat": v3["beat"], "segment_place": v3["segment_place"], "wake": v3["wake"],
        "members": v3["members"], "chain_map": v3["chain_map"], "seams": v3["seams"], "timing_site": v3["timing_site"],
        "replay": {"max_breaks": v3["replay"]["max_breaks"], "F5B": [1, None], "CTL": [1, 2]},
        "walk_gate": {"F5B": [[352, 0, 351]], "CTL": [[352, 0, 351], [351, 0, 350]]},
        "budget": budget, "rerun": {"max": 6, "halt": "R5-REACH decided (F5B only)"},
        "coverage": {"min_covered": 3, "min_ctl": 2,
                     "clean_stop": {"S": ["SC left"], "F5B": ["SC left", "passes exhausted", "budget spent"],
                                    "CTL": [PREFIX_STOP]},
                     "ran": cov3["ran"], "ran_ctl": cov3["ran"][:1], "advancing": ["S"], "flip": cov3["flip"],
                     "advanced_sc": cov3["advanced_sc"], "floor": [], "floor_stops": [], "drive": cov3["drive"],
                     "fork_stop": {**cov3["fork_stop"],
                                   "landing": {"phase": "landing", "raised": [r"HarnessError: landing: "],
                                               "point": "landing@<place>"}}},
        "hubs": hubs,
        "stockstate": v3["stockstate"],
        "land": {"bytes": [9, 10, 13, 18, 19, 21, 61, 62, 63, 238, 239, 241, 251, 296, 303], "n_bits": 53,
                 "bits": None},
        "residual": {"values": residual, "bits": bits_of(residual), "n_bits": 34},
        "class_iii": {"251": {"stock_at_landing": 6, "F5B_at_landing": 0, "after_arrival": 6,
                              "chime": "Map.Bit[152] (351.ebs:452-455): untraced"}},
        "control": {"handback_bits": handback_ctl, "n_handback": 41, "land_extra_bits": latch_bits,
                    "land_bits": None, "n_land": 55,
                    "fork_only": [_key(351, 0, 0, 791, "Global.SByte[238]", 0, 801),
                                  _key(351, 0, 0, 799, "Global.Int16[241]", 0, 809)],
                    "stock_only": arrival8[3:6],
                    "step1": {"absent": {"donor": 351, "sid": 16, "tag": 2, "ip": 105},
                              "present": {"donor": 351, "sid": 16, "tag": 2, "ip": 146, "target": "Global.Bit[2064]",
                                          "old": 0, "new": 1}},
                    "slot": [0, 2, 3, 1]},
        "echo": [{"name": "351 lobby exit e16 t2 ip105: Bit[2078] 1 -> 0", "donor": 351, "sid": 16, "tag": 2,
                  "ip": 105, "off": 71, "target": "Global.Bit[2078]", "value": 0, "old": 1, "new": 0},
                 {"name": "450 Main_Init e0 t0 ip338: Bit[2086] 1 -> 0", "donor": 450, "sid": 0, "tag": 0, "ip": 338,
                  "off": 320, "target": "Global.Bit[2086]", "value": 0, "old": 1, "new": 0}],
        "arrival": {"keys": arrival8 + supp351},
        "supp": {"proven": proven, "blind": blind,
                 "rule": "PROVEN: S emitted it same:1 with that value before its wake row, its count row's last is "
                         "that value, AND S's own post-wake window holds a row in the same function at a site the "
                         "key's site dominates (FuncFlow), in that run; BLIND: the value check only, a registered "
                         "MIRROR blind spot",
                 "rejected": ["re-arming S's trace at the hand-back (every reader takes ONE arm run)",
                              "a count bound (352 +646's n=1 fits pre 1 + post 1 and pre 2 + post 0)"]},
        "step1_keys": [_key(352, 14, 2, 116, "Global.Bit[2103]", 0, 150), _key(352, 14, 2, 314, "Global.Int16[2]", 6,
                                                                              348)],
        "party": {"hubleg": [0, 255, 255, 255],
                  "partyremove": {"r1": [0, 2, 3, 1], "r2": [0, 2, 3, 1], "r3": [0, 255, 255, 255]},
                  "landing": {"F5B": [0, 255, 255, 255], "CTL": [0, 2, 3, 1]}, "run_end": [0, 255, 255, 255],
                  "footprint_bytes": [18, 19, 21, 60, 61, 62, 63, 303]},
        "freshness": {"frames": 10, "rule": "st_mtime_ns after the baseline read taken right before the transition "
                                            "it judges; sha stable over two reads 10 frames apart; SC, Int16[2] and "
                                            "the field name the arrival (run-end reads: the trace's last field entry)"},
        "verdict": {"min_f5b_pairs": 3, "min_ctl": 2,
                    "load_bearing": ["P-PARTYREMOVE", "R5-STAMP", "R5B-NOWAKE", "R5B-CONTROL", "R5B-LAND",
                                     "R5B-STATE", "R5B-ECHO", "R5B-ARRIVAL", "R5B-PARTY", "R5-MIRROR", "R5-PARTIAL",
                                     "R5-LATCH", "R5-ADVANCE", "R5-REACH", "R5-JOIN", "R5-DONOR", "NC-THROW"],
                    "halves": {"state": ["R5B-CONTROL(a)", "R5B-CONTROL(b)", "R5B-LAND", "R5B-STATE"],
                               "latches": ["R5B-ECHO", "R5B-ARRIVAL", "R5-LATCH"],
                               "party": ["P-PARTYREMOVE", "R5B-PARTY", "R5B-CONTROL(e)"],
                               "walk": ["R5-MIRROR", "R5-PARTIAL", "R5-REACH", "R5-ADVANCE", "R5-PING", "R5-NOSEAM"]}},
        "checks": {"R5-JOIN": {"max_failures": 0},
                   "R5-MIRROR": {"min_keys": 150, "min_tour_keys": 110,
                                 "tour_donors": v3["checks"]["R5-MIRROR"]["tour_donors"], "seam_field": 450,
                                 "min_post_keys": 40, "post_donors": v3["checks"]["R5-MIRROR"]["post_donors"]},
                   "R5-PING": {k: v3["checks"]["R5-PING"][k] for k in ("target", "value", "writers", "pattern")},
                   "R5-ADVANCE": {k: v3["checks"]["R5-ADVANCE"][k] for k in ("sc", "pattern")},
                   "R5-LATCH": {"patterns": v3["checks"]["R5-LATCH"]["patterns"][:8]},
                   "R5B-CONTROL": {
                       "fail": "Any of clauses (a)-(d) does not hold; each failed clause makes its dependent R5B "
                               "check VOID as uncalibrated.",
                       "void": "Fewer than 2 covered CTL runs (then every dependent R5B check is VOID), or clause "
                               "(e) not PASS: the party instrument uncalibrated, so R5B-PARTY is VOID and the "
                               "frozen verdict names the party half NOT PROVEN -- never a FAILED headline."},
                   "P-INI": {
                       "claim": "The install's Memoria.ini leaves the removes and the field-entry autosave to the "
                                "engine: the party instrument and the pick's removes can work at all.",
                       "pass": "[Hacks] AllCharactersAvailable < 2, [SaveFile] DisableAutoSave = 0 and "
                               "AutoSaveOnlyAtMoogle = 0, and [Netsync] Enabled = 0 or Role = host (a key the "
                               "file lacks takes the engine's default: 0, host). The values read are recorded.",
                       "fail": "Any switch otherwise, or the file unreadable; the session stops (a static check).",
                       "void": "None (pre-flight).",
                       "can_fail_because": "Another session edits the shared Memoria.ini (AllCharactersAvailable = "
                                           "2 makes RemoveParty a no-op, EventEngine.DoEventCode.cs:2757; the "
                                           "autosave switches stop the field-entry autosave).",
                       "keys": {s: list(k) for s, k in INI_KEYS.items()}}},
    }


# ======================================================================== the drive's pieces (in game)
class PrefixTour(D.Tour):
    """CTL's walk: :meth:`D.Tour.replay` of a PREFIX, and nothing after it. Tour.replay falls through into a blind
    :meth:`D.Tour.run` once its walk is replayed with the story still at the beat (dali_tour.py:725-726); here that
    tour returns at once, so the prefix is the whole drive and the stop is ``prefix replayed`` (CTL's one clean
    stop). Every crossing, strike and step rule is the replay's own."""

    def run(self, g, log, *, crossings: int = 0, started: float | None = None, **_kw) -> str:
        took = 0 if started is None else time.time() - started
        return f"{PREFIX_STOP} ({crossings} crossings, {took:.0f}s)"


def tours5b(pred: dict, *, ran=None, stock=None) -> dict:
    """One Tour per side: S the install's, F5B the members', CTL the members' :class:`PrefixTour`."""
    return {"S": D.Tour(scripts=None, stock=stock, tag="rung5b"),
            "F5B": D.Tour(members=chain(pred), scripts=ran, stock=stock, tag="rung5b"),
            "CTL": PrefixTour(members=chain(pred), scripts=ran, stock=stock, tag="rung5b")}


def walk_gate(pred: dict, side: str, walk) -> str | None:
    """Whether a fork run may REPLAY this partner walk (predictions "walk_gate", design 4.3): None when the walk's
    first steps are the frozen ones, else why not -- the text its record carries. F5B needs walk[0] == 352.0 ->
    351 (its replay starts at step 2, where that crossing left him); CTL walk[0:2] == [352.0 -> 351, 351.0 -> 350]
    (its clauses judge exactly that step 2)."""
    gate = [list(s) for s in pred["walk_gate"][side]]
    got = [list(s) for s in (walk or [])[:len(gate)]]
    if got == gate:
        return None
    j = next((k for k, w in enumerate(gate) if k >= len(got) or got[k] != w), 0)
    it = D.step_name(got[j]) if j < len(got) else "absent"
    if j == 0:
        return f"partner's first step is not the wake room's exit {D.step_name(gate[0])} (it is {it})"
    return f"skipped: partner step {j + 1} is not {D.step_name(gate[j])} (it is {it})"


def step1_rule(pred: dict, walk, lo: int = 1, hi=None) -> set:
    """The stock step-1 keys (352 e14 t2 +116 Bit[2103]=0, +314 Int16[2]=6: the wake room's exit) a fork run is
    EXCUSED from writing: all of them when its replayed slice ``walk[lo:hi]`` never crosses 352.0 -> 351 -- the
    only exit that writes them -- else none. Computed from the walk before the run is read."""
    exit_step = list(pred["walk_gate"]["F5B"][0])
    if any(list(s) == exit_step for s in (walk or [])[lo:hi]):
        return set()
    return {ktuple(k) for k in pred["step1_keys"]}


def autosave_path(g) -> Path:
    """The sandbox autosave's Memoria extra file: beside the save path the agent publishes (state ``save_path``, the
    sandbox the session asserted at launch -- save.extra_file_path's block 0), else under the channel dir, where the
    harness sandboxes it."""
    from ff9mapkit import save
    st = g.state
    sp = (getattr(st, "raw", None) or {}).get("save_path") if st is not None else None
    extra = save.extra_file_path(sp, 0) if sp else None
    return Path(extra) if extra else Path(g.channel.dir) / "save" / AUTOSAVE


def read_autosave(path) -> dict:
    """ONE read of the Memoria extra autosave file (E20): ``{mtime_ns, sha, time, slot, sc, entrance, reserve, hp,
    status}`` -- ``slot`` the four party SLOTS as CharacterId (255 empty, 40000_Common.slot), ``sc``/``entrance``
    gEventGlobal's UInt16[0] / Int16[2], ``reserve`` the players whose info.party is set -- or with ``error`` when
    it is absent or does not decode. The bytes are decoded as read (one read, one sha)."""
    from ff9mapkit import save
    p = Path(path)
    try:
        mtime = p.stat().st_mtime_ns
        data = p.read_bytes()
    except OSError as err:
        return {"mtime_ns": None, "sha": None, "error": f"no autosave at {p.name} ({type(err).__name__})"}
    out = {"mtime_ns": mtime, "sha": hashlib.sha256(data).hexdigest()}
    try:
        tree, _end = save._sjson_node(data, 0)            # read_extra_tree's decoder, on THESE bytes
        common, event = tree["40000_Common"], tree["20000_Event"]
        geg = base64.b64decode(event["gEventGlobal"])
        players = common.get("players") or []
        out.update(time=float((tree.get("95000_Setting") or {}).get("00001_time", -1.0)),
                   slot=[int(x) for x in common["slot"]],
                   sc=struct.unpack_from("<H", geg, 0)[0], entrance=struct.unpack_from("<h", geg, 2)[0],
                   reserve=[i for i, pl in enumerate(players) if (pl.get("info") or {}).get("party")],
                   hp=[(pl.get("cur") or {}).get("hp") for pl in players],
                   status=[pl.get("status") for pl in players])
    except (KeyError, TypeError, ValueError, IndexError, struct.error) as err:
        out["error"] = f"the autosave does not decode ({type(err).__name__}: {str(err)[:80]})"
    return out


def freshness(read: dict, baseline: dict | None = None, want: dict | None = None) -> tuple:
    """THE FROZEN FRESHNESS RULE (design 4.5), pure: ``(fresh, [why not])``. A read is fresh when it decoded, its
    sha was stable over two reads ``frames`` apart (``stable``), its st_mtime_ns is AFTER the baseline read's (a
    read taken right before the transition it judges; a baseline with no file is before any file), and every key
    of ``want`` (``sc``, ``entrance``, ``field``) names the arrival."""
    why = []
    if read is None:
        return False, ["no read"]
    if read.get("error"):
        why.append(read["error"])
    elif not read.get("stable"):
        why.append("its sha changed between two reads 10 frames apart")
    if baseline is not None:
        b, m = baseline.get("mtime_ns"), read.get("mtime_ns")
        if m is None or (b is not None and m <= b):
            why.append(f"st_mtime_ns {m} is not after the baseline's {b} (no new autosave)")
    for k, v in (want or {}).items():
        if read.get(k) != v:
            why.append(f"{k} {read.get(k)}, not the arrival's {v}")
    return not why, why


def party_read(g, baseline: dict | None = None, want: dict | None = None, *, path=None,
               frames: int | None = None) -> dict:
    """Read the sandbox autosave the way the frozen rule judges it (:func:`freshness`): two reads ``frames`` (10)
    frames apart -- one more pair when a write landed between them -- and the field the game stands in, recorded
    with the rule's verdict against ``baseline`` / ``want``. Never raises for the file (a missing or torn one is a
    stale read, named); the frame wait is a request like any other."""
    p = Path(path) if path is not None else autosave_path(g)
    n = 10 if frames is None else frames
    a = read_autosave(p)
    g.wait_frames(n)
    b = read_autosave(p)
    if a.get("sha") != b.get("sha"):                     # a write landed between the two: one more pair
        g.wait_frames(n)
        a, b = b, read_autosave(p)
    st = g.state
    rec = dict(b, field=st.field_id if st is not None else None,
               stable=a.get("sha") is not None and a.get("sha") == b.get("sha"))
    rec["fresh"], rec["why"] = freshness(rec, baseline, want)
    return rec


def enter_past(g, log: list, view: dict, *, place, woke, arrive_s: float | None = None,
               entry_s: float | None = None, budget_s: float | None = None, phase=lambda _name: None) -> dict:
    """F5b's way into its entry -- the analog of dali_tour.segment for an entry PAST the wake: the hub leg
    (H5.hub_leg on the per-hub view: the pick stamps, writes Int16[2] := 6 and runs Field(31101); it waits for
    that field), then the LANDING: control in the entry's place (351) at the beat within ``arrive_s``, with no wake
    row in the run's own trace. Logs and returns ``{"k": "landing", ...}``; raises HarnessError "landing: ..." when
    the wake ran (``woke()``), he stands in another place, control never came, or it came at another SC -- each a
    FORK-STOP "landing@<place>" (the stamps landed: the leg returned). The hub leg's own errors propagate as the leg
    raised them (FORK-STOP "hub" or DRIVE, as F5 classed them)."""
    from harness import HarnessError
    H = view["hub"]
    beat = view["beat"]
    entry = int(H["entry"])
    want = place(entry)
    arrive_s = view["budget"]["arrive_s"] if arrive_s is None else arrive_s
    phase("hub")
    H5.hub_leg(g, log, view, budget_s=budget_s, entry_s=entry_s)
    phase("landing")
    t0 = time.time()
    rec: dict = {"k": "landing", "entry": entry, "entrance": H.get("entrance")}

    def done(s) -> bool:
        return (s.field_id is not None and place(s.field_id) != want) or woke() or bool(s.control)

    why = None
    try:
        st = g.wait_for(done, timeout=arrive_s, what=f"control in place {want} at SC {beat} (the landing)")
        rec.update(field=st.field_id, place=place(st.field_id), sc=st.scenario, control=bool(st.control),
                   woke=bool(woke()))
        if rec["woke"]:
            why = f"the wake ran on an entry past the wake (its SC := {beat} store is in the trace)"
        elif rec["place"] != want:
            why = f"the pick left him in place {rec['place']} (field {st.field_id}), not {want} ({entry})"
        elif st.scenario != beat:
            why = f"control in {entry} at SC {st.scenario}, not {beat}"
    except HarnessError as err:
        now = g.state
        rec.update(field=getattr(now, "field_id", None), sc=getattr(now, "scenario", None), control=False,
                   woke=bool(woke()))
        why = f"control never returned within {arrive_s:.0f}s in {entry} ({str(err)[:200]})"
    rec.update(ok=why is None, t=round(time.time() - t0, 1))
    if why is not None:
        rec["error"] = why
    log.append(rec)
    if why is not None:
        raise HarnessError(f"landing: {why}")
    return rec


# ======================================================================== the untraced pre-flight legs (in game)
def p_hubleg5b(g, view: dict) -> tuple:
    """P-HUBLEG on one hub (H5.p_hubleg, rung5_hub.py:520-565, with the autosave clause): ``(ok, detail, record)``.
    New Game; a PRE-WARP autosave read; the log mark; the hub leg up to its menu (H5.hub_open: the warp, the
    calibration on the hub's twist, the talk); the HUB-ARRIVAL read, inside the leg (after the warp, before the stay
    row) -- fresh against the pre-warp read, and the New Game baseline: SC 2540, Int16[2] 0, slot [0,255,255,255]
    (``record["save"]["ok"]``, NOT part of ``ok``: the caller retries the leg once for it, and a twice-failed
    clause only VOIDs R5B-PARTY); the STAY row, which must leave him in the hub with control for 60 frames; no
    THROWS exception from the mark on; the title restored. Any error the drive raises FAILs the leg, named."""
    H = view["hub"]
    mark = None
    rec: dict = {"k": "hub", "hub": H["id"]}
    bad = []
    t0 = time.time()
    try:
        g.newgame()
        g.wait_frames(30)
        pre = party_read(g)
        rec["pre"] = pre
        mark = g.log_mark()
        end = time.time() + view["budget"]["hub_s"]
        H5.hub_open(g, view, end, rec)
        _fid, entrance, sc = H["lead_in"]
        arrival = party_read(g, pre, {"sc": sc, "entrance": entrance, "field": H["id"]})
        slot_ok = arrival.get("slot") == view["party"]["hubleg"]
        rec["save"] = dict(arrival, ok=bool(arrival["fresh"] and slot_ok),
                           why=arrival["why"] + ([] if slot_ok else
                                                 [f"slot {arrival.get('slot')}, not {view['party']['hubleg']}"]))
        rec["picked"] = H["stay"]
        rec["presses"] = H5.hub_pick(g, view, H["stay"], end, view["budget"]["entry_s"])
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
    rec.setdefault("save", {"ok": False, "why": ["the leg never reached the hub's menu"]})
    rec["t"] = round(time.time() - t0, 1)
    ours = [] if mark is None else [e for e in g.exceptions_since(mark) if e.name in THROWS
                                    and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    if ours:
        bad.append(f"thrown: {[(e.name, e.where) for e in ours[:4]]}")
    ok_t, why_t = g.restore_baseline()
    if not ok_t:
        bad.append(f"the title could not be restored: {why_t}")
    return not bad, "; ".join(bad) or (f"{H['name']}: {H['narrator']} r {rec.get('r')}, talk_r {rec.get('talk_r')}, "
                                       f"{rec.get('tries')} tries, options {rec.get('options')}, stay row stayed "
                                       f"({rec.get('presses')} presses); hub-arrival autosave "
                                       f"{'OK' if rec['save']['ok'] else 'NOT OK: ' + '; '.join(rec['save']['why'])}"
                                       f" (slot {rec['save'].get('slot')})"), rec


def hubleg5b(g, view: dict, *, leg=None) -> tuple:
    """P-HUBLEG with its autosave clause's ONE retry, as the session runs it (design 4.9): ``(ok, detail, record)``.
    The LEG's verdict is the FIRST attempt's -- its menu, stay-row and throw clauses and what it measured (r,
    talk_r) -- and a leg that passed is never ended by its retry. Only when that leg passed with its autosave clause
    not ok does the leg run again, for that clause alone: the retry's ``save`` replaces the first's, and a retry that
    fails AS A LEG (a flaky menu, a missed Confirm) is that clause failing, named in ``save.why`` -- which only VOIDs
    R5B-PARTY, never stops the session. Both attempts are recorded (``attempts``, ``tries``). ``leg`` is the seam
    (default :func:`p_hubleg5b`)."""
    leg = leg or p_hubleg5b
    ok, detail, rec = leg(g, view)
    attempts = [dict(rec, ok=ok, detail=detail)]
    if ok and not (rec.get("save") or {}).get("ok"):
        ok2, detail2, rec2 = leg(g, view)
        attempts.append(dict(rec2, ok=ok2, detail=detail2))
        save = dict(rec2.get("save") or {"ok": False, "why": []})
        if not ok2:
            save = dict(save, ok=False, why=[f"the retry's leg failed: {str(detail2)[:200]}"]
                        + list(save.get("why") or []))
        rec = dict(rec, save=save)
        detail = (f"{detail} || autosave retry: "
                  + ("OK" if save.get("ok") else "NOT OK: " + "; ".join(save.get("why") or [])))
    return ok, detail, dict(rec, attempts=attempts, tries=len(attempts))


def _settled(g, entry: int, timeout: float) -> None:
    """Wait until control is back in ``entry``. The engine flips fldMapNo in the OLD field's shutdown -- where the hub
    leg and a landing wait return -- and writes the new field's autosave only in its StartEvents, a few frames later
    (HonoluluFieldMain.cs:444); control comes after both. A read taken at the flip races that write, and the Python
    read's open can make the engine's FileShare.None write fail silently (SharedDataBytesStorage.Save): read after
    control, seconds clear of it."""
    g.wait_for(lambda s: s.field_id == entry and bool(s.control), timeout=timeout,
               what=f"control back in {entry} (its arrival's autosave written)")


def _partyremove_once(g, pred: dict) -> dict:
    """One P-PARTYREMOVE attempt (design 4.5), untraced: ``{"reads", "verdict", "why"}`` -- verdict True PASS,
    False FAIL (the known positive calibrated and the removes inert), None VOID (uncalibrated, or the drive
    failed). New Game -> r0; the CTL hub's leg lands 31101 -> r1 (fresh vs r0, SC 2600 / e6) must read [0,2,3,1];
    the F5B hub opened from there (its warp to 31113 at SC 2540) -> r2 (fresh vs r1, SC 2540 / e0) must read
    [0,2,3,1]; the F5B pick lands 31101 -> r3 (fresh vs r2, SC 2600 / e6) must read [0,255,255,255] -- inert
    removes read [0,2,3,1]. r1 and r3 are read only once control is back in 31101 (:func:`_settled`: never in the
    frames of the arrival's own autosave write), which also leaves hub_open a settled field to warp from. The title
    restored after, whatever happened."""
    from harness import HarnessError
    P = pred["party"]["partyremove"]
    vf, vc = hub_view(pred, "F5B"), hub_view(pred, "CTL")
    beat, entry, entrance = pred["beat"], int(vf["hub"]["entry"]), vf["hub"]["entrance"]
    at_entry = {"sc": beat, "entrance": entrance, "field": entry}
    arrive_s = pred["budget"]["arrive_s"]
    rec: dict = {"k": "partyremove", "reads": {}, "log": []}
    reads = rec["reads"]
    try:
        ok_t, why_t = g.restore_baseline()
        if not ok_t:
            raise HarnessError(f"the title could not be restored: {why_t}")
        g.newgame()
        g.wait_frames(30)
        reads["r0"] = party_read(g)
        H5.hub_leg(g, rec["log"], vc)
        _settled(g, entry, arrive_s)
        reads["r1"] = party_read(g, reads["r0"], at_entry)
        end = time.time() + vf["budget"]["hub_s"]
        hub_rec: dict = {"k": "hub"}
        H5.hub_open(g, vf, end, hub_rec)
        rec["log"].append(hub_rec)
        _fid, e0, sc0 = vf["hub"]["lead_in"]
        reads["r2"] = party_read(g, reads["r1"], {"sc": sc0, "entrance": e0, "field": vf["hub"]["id"]})
        rec["presses"] = H5.hub_pick(g, vf, vf["hub"]["pick"], end)
        g.wait_for(lambda s: s.field_id == entry, timeout=vf["budget"]["entry_s"], what=f"the pick to land in {entry}")
        _settled(g, entry, arrive_s)
        reads["r3"] = party_read(g, reads["r2"], at_entry)
    except Exception as err:                      # noqa: BLE001 -- a drive failure is an uncalibrated leg: VOID, named
        rec["error"] = f"{type(err).__name__}: {str(err)[:300]}"
    finally:
        try:
            ok_t, why_t = g.restore_baseline()
            if not ok_t:
                rec["restore"] = why_t
        except Exception as err:                  # noqa: BLE001
            rec["restore"] = f"{type(err).__name__}: {str(err)[:200]}"
    rec["verdict"], rec["why"] = partyremove_verdict(reads, P, rec.get("error"))
    return rec


def partyremove_verdict(reads: dict, want: dict, error: str | None = None) -> tuple:
    """P-PARTYREMOVE's frozen rule over its four reads, pure: ``(True | False | None, why)``. VOID when the drive
    failed, a read is not fresh, or the calibration reads r1 / r2 are not the known positive; FAIL when they are and
    r3 is not the removes' result; PASS when it is."""
    if error:
        return None, f"the leg did not complete: {error}"
    for k in ("r1", "r2", "r3"):
        r = reads.get(k)
        if r is None:
            return None, f"no {k} read"
        if not r.get("fresh"):
            return None, f"{k} not fresh: {'; '.join(r.get('why') or [])}"
        if k in ("r1", "r2") and r.get("slot") != want[k]:
            return None, f"{k} reads {r.get('slot')}, not {want[k]} -- the instrument is uncalibrated"
    if reads["r3"].get("slot") != want["r3"]:
        return False, (f"r3 reads {reads['r3'].get('slot')}, not {want['r3']}: the F5B pick's removes did not act "
                       f"on a real roster")
    return True, f"r1 {reads['r1']['slot']}, r2 {reads['r2']['slot']}, r3 {reads['r3']['slot']}"


def p_partyremove(g, pred: dict) -> tuple:
    """P-PARTYREMOVE (in game, untraced, before NC-THROW's mark): ``(ok, detail, record)``, ok True PASS, False
    FAIL, None VOID. ONE RETRY, for a VOID only -- an uncalibrated read or a drive failure; a calibrated FAIL (r1 and
    r2 the known positive, r3 not the removes' result) is evidence and stands. Never raises."""
    attempts = []
    for _k in (1, 2):
        try:
            rec = _partyremove_once(g, pred)
        except Exception as err:                  # noqa: BLE001 -- never escapes: R5B-PARTY reads the verdict
            rec = {"k": "partyremove", "reads": {}, "verdict": None, "why": f"{type(err).__name__}: {str(err)[:200]}"}
        attempts.append(rec)
        if rec["verdict"] is not None:
            break
    last = attempts[-1]
    out = {"k": "partyremove", "verdict": last["verdict"], "why": last["why"], "attempts": attempts}
    return last["verdict"], f"{len(attempts)} attempt(s): {last['why']}", out


# ======================================================================== the static pre-flight (pure, offline)
#: P-INI: the Memoria.ini switches the party instrument and the removes rest on, read as the engine reads them
#: (harness.artifacts.read_memoria_ini: last wins; a key the file lacks takes the engine's default, 0 / Role host).
#: [Hacks] AllCharactersAvailable >= 2 makes RemoveParty a no-op (EventEngine.DoEventCode.cs:2757) -- the F5B pick's
#: removes and stock's own wake removes both inert; [SaveFile] DisableAutoSave / AutoSaveOnlyAtMoogle stop the
#: field-entry autosave the party is read through (WinIosAndrSharedDataSerializer.cs:92, EventEngine.cs:689); a
#: Netsync game that is not the host follows another game.
INI_KEYS = {"Hacks": ("AllCharactersAvailable",), "SaveFile": ("DisableAutoSave", "AutoSaveOnlyAtMoogle"),
            "Netsync": ("Enabled", "Role")}


def ini_check(path=None) -> tuple:
    """P-INI (static, pure given the file): ``(ok, detail, values)`` -- the install's Memoria.ini (``path``, default
    the game's) holds AllCharactersAvailable < 2, DisableAutoSave = 0, AutoSaveOnlyAtMoogle = 0, and Netsync off or
    this game its host. ``values`` are what the check read (the session records them). An unreadable file, or a
    value that is not a number, FAILs."""
    from harness.artifacts import read_memoria_ini
    p = Path(path) if path is not None else D.GAME / "Memoria.ini"
    doc = read_memoria_ini(p, INI_KEYS)
    if doc is None:
        return False, f"cannot read {p}", {}

    def num(sec: str, key: str):
        v = str((doc.get(sec) or {}).get(key, "0")).strip()
        return int(v) if re.fullmatch(r"-?\d+", v) else v

    vals = {"AllCharactersAvailable": num("Hacks", "AllCharactersAvailable"),
            "DisableAutoSave": num("SaveFile", "DisableAutoSave"),
            "AutoSaveOnlyAtMoogle": num("SaveFile", "AutoSaveOnlyAtMoogle"),
            "Netsync.Enabled": num("Netsync", "Enabled"),
            "Netsync.Role": str((doc.get("Netsync") or {}).get("Role", "host")).strip().lower()}
    bad = []
    a = vals["AllCharactersAvailable"]
    if not isinstance(a, int) or a >= 2:
        bad.append(f"[Hacks] AllCharactersAvailable {a} (RemoveParty is a no-op at 2 and above)")
    for k in ("DisableAutoSave", "AutoSaveOnlyAtMoogle"):
        if vals[k] != 0:
            bad.append(f"[SaveFile] {k} {vals[k]} (the field-entry autosave the party is read through)")
    if vals["Netsync.Enabled"] != 0 and vals["Netsync.Role"] != "host":
        bad.append(f"[Netsync] Enabled {vals['Netsync.Enabled']}, Role {vals['Netsync.Role']} (a game that follows "
                   f"another)")
    return not bad, f"{p.name}: " + ("; ".join(bad) if bad else ", ".join(f"{k} {v}" for k, v in vals.items())), vals


def p_pins(*, env: dict | None = None, run=subprocess.run, timeout: float = 900.0) -> tuple:
    """P-PINS: ``(ok, detail, {test: status})`` -- the seven F5b resolver tests (:data:`PINS`) run by pytest with
    ``-rA`` from the kit, and each must show PASSED: a SKIPPED (the census locator found nothing), a FAILED or a test
    not collected is not a pass. ``env`` overrides the environment (the census locator reads FF9_STORY_CENSUS /
    FF9_F5_DIR); ``run`` is the subprocess seam."""
    cmd = [sys.executable, "-m", "pytest", "tests/test_storyseed.py", "-q", "-rA", "-p", "no:cacheprovider",
           "-k", " or ".join(PINS)]
    try:
        p = run(cmd, cwd=KIT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                env=env)
        out = (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.SubprocessError) as err:
        return False, f"pytest could not run: {type(err).__name__}: {str(err)[:200]}", {}
    status = {}
    for ln in out.splitlines():
        m = re.match(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+\S*?::(test_\w+)", ln)
        if m and m.group(2) in PINS:
            status[m.group(2)] = m.group(1)
    for ln in out.splitlines():                           # -rA prints a skip by LOCATION, never by name
        m = re.match(r"^SKIPPED \[\d+\] (\S+?):(\d+): (.*)$", ln)
        if m:
            status.setdefault(f"skipped at {m.group(1)}:{m.group(2)}", "SKIPPED: " + m.group(3)[:120])
    bad = {t: status.get(t, "not PASSED (skipped, failed or not collected)") for t in PINS
           if status.get(t) != "PASSED"}
    tail = next((ln for ln in reversed(out.splitlines()) if re.search(r"\d+ (passed|failed|skipped)", ln)), "")
    return not bad, ("; ".join(f"{t}: {s}" for t, s in bad.items()) + (f" || {tail.strip()}" if tail else "")
                     if bad else f"{len(PINS)}/{len(PINS)} PASSED ({tail.strip()})"), status


def party_ops(data: bytes, sid: int, tag: int) -> list:
    """The party operations and the Field() of one hub function, in order: ``[[op, arg, function offset]]`` --
    ``remove`` (RemoveParty 0xDD, a literal arg), ``add`` (a ``B_PARTYADD`` expression statement), ``field`` (0x2B).
    The trace cannot see them (the pick's party is untraced); P-PARTYOPS holds the deployed bytes to them."""
    from ff9mapkit import forkreport
    from ff9mapkit.eb import EbScript
    eb = EbScript.from_bytes(bytes(data))
    if not 0 <= sid < len(eb.entries) or eb.entries[sid].empty:
        return []
    f = eb.entries[sid].func_by_tag(tag)
    out = []
    for ins in (eb.instrs(f) if f is not None else ()):
        rel = ins.off - f.abs_start
        if ins.op == forkreport.REMOVE_PARTY_OP and ins.args and not any(ins.arg_is_expr):
            out.append(["remove", int(ins.args[0]), rel])
        elif ins.op == forkreport.EXPR_STMT_OP:
            for h in forkreport._PARTYADD_RE.findall(eb.data[ins.off:ins.end]):
                out.append(["add", struct.unpack("<H", h)[0], rel])
        elif ins.op == 0x2B and ins.imm(0) is not None:
            out.append(["field", int(ins.imm(0)), rel])
    return out


def partyops_check(view: dict, data: bytes | None) -> tuple:
    """P-PARTYOPS on one hub's US .eb: its pick's party ops, their order and positions (:func:`party_ops`, the
    stamps' function) and forkreport.scan_party_ops' adds/removes are the frozen ones."""
    from ff9mapkit import forkreport
    H = view["hub"]
    if data is None:
        return False, f"{H['name']}: no .eb"
    s0 = H["stamp"][0]
    got = party_ops(data, s0["sid"], s0["tag"])
    scan = forkreport.scan_party_ops(data)
    bad = []
    if got != H["party_ops"]:
        bad.append(f"{H['name']}: ops {got}, not the frozen {H['party_ops']}")
    if {k: scan[k] for k in ("adds", "removes")} != H["party_scan"]:
        bad.append(f"{H['name']}: scan adds {scan['adds']} removes {scan['removes']}, not {H['party_scan']}")
    return not bad, "; ".join(bad) or f"{H['name']}: {got}; scan adds {scan['adds']} removes {scan['removes']}"


def _switch_cases(data: bytes) -> set:
    """Every entrance value some function dispatches on: a bare Int16[2] read (the arrival's ``D8:2``) feeding a
    switch -- the player setup's SWITCHEX (351's lives in e19, where scan_arrival_table does not look)."""
    from ff9mapkit import eventscan as ES
    from ff9mapkit.eb import EbScript
    from ff9mapkit.eb.disasm import decode_switch
    eb = EbScript.from_bytes(bytes(data))
    out = set()
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            ins_l = list(eb.instrs(f))
            for a, b in zip(ins_l, ins_l[1:]):
                raw = eb.data[a.off:a.end]
                if (a.op == ES.SETVAR_EXPR_OP and len(raw) == 4 and raw[1] == ES.ENTRANCE_VAR_CLASS
                        and raw[2] == ES.ENTRANCE_VAR_IDX and b.op in (0x06, 0x0B, 0x0D)):
                    sw = decode_switch(b)
                    out |= {int(ed.value) for ed in (sw.edges if sw else ()) if not ed.is_default}
    return out


def entry_check(pred: dict, stock, hub_bytes: dict) -> tuple:
    """P-ENTRY: the hand-over the post phase models is the one deployed and the one stock uses. Stock 352's gateways
    hold ONE exit to 351, entrance 6; storyseed.exit_fold over it at the beat returns no clash, bit 2103 = 0 and the
    SC stores at +94/+108 dead; each hub writes Int16[2] := 6 after all its other stamps and before its Field(31101);
    stock 351 dispatches entrance 6. ``hub_bytes`` = ``{side: US .eb bytes}``."""
    from ff9mapkit import eventscan, storyseed
    from ff9mapkit.eb import EbScript
    E = pred["entry"]
    adv = pred["wake"]["donor"]
    bad = []
    s352, s351 = stock(adv), stock(E["donor"])
    if s352 is None or s351 is None:
        return False, f"no stock .eb for {adv} / {E['donor']}"
    gws = [g_ for g_ in eventscan.scan_gateways(s352.data) if g_["to"] == E["donor"]]
    if [(g_["to"], g_["entrance"]) for g_ in gws] != [(E["donor"], E["entrance"])]:
        bad.append(f"stock {adv}'s gateways to {E['donor']}: {[(g_['to'], g_['entrance']) for g_ in gws]}, want one "
                   f"with entrance {E['entrance']}")
    else:
        stamped = {b + k for b in (208, 297) for k in (0, 1)}
        vals, _why, clash, dead = storyseed.exit_fold(EbScript.from_bytes(s352.data), gws[0]["entry"], E["donor"],
                                                      E["entrance"], pred["beat"], {2103}, stamped, label=str(adv))
        if clash:
            bad.append(f"exit_fold clashes: {clash[:2]}")
        if vals.get(2103) != 0:
            bad.append(f"exit_fold leaves bit 2103 {vals.get(2103)!r}, not 0")
        if not all(any(f"+{o} writes" in d for d in dead) for o in (94, 108)):
            bad.append(f"the SC stores at +94/+108 are not dead at {pred['beat']}: {dead[:2]}")
    if E["entrance"] not in _switch_cases(s351.data):
        bad.append(f"stock {E['donor']}'s player setup has no case for entrance {E['entrance']}")
    for side, data in sorted(hub_bytes.items()):
        H = pred["hubs"][side]
        if data is None:
            bad.append(f"{H['name']}: no .eb")
            continue
        stores = [s for s in H5.global_stores(data, field_id=H["id"])
                  if (s["sid"], s["tag"]) == (H["stamp"][0]["sid"], H["stamp"][0]["tag"])]
        ent = [s for s in stores if s["target"] == "Global.Int16[2]"]
        field = [o for op, _a, o in party_ops(data, H["stamp"][0]["sid"], H["stamp"][0]["tag"]) if op == "field"]
        if len(ent) != 1 or ent[0]["value"] != E["entrance"]:
            bad.append(f"{H['name']}: its entrance stores {[(s['off'], s['value']) for s in ent]}, want one := "
                       f"{E['entrance']}")
        elif any(s["off"] > ent[0]["off"] for s in stores) or not field or not ent[0]["off"] < min(field):
            bad.append(f"{H['name']}: Int16[2] := {E['entrance']} at +{ent[0]['off']} is not after every stamp and "
                       f"before Field() {field}")
    return not bad, "; ".join(bad) or (f"stock {adv} -> {E['donor']} at entrance {E['entrance']}; exit_fold: 2103 = 0, "
                                       f"no clash, +94/+108 dead; 351 dispatches {E['entrance']}; each hub stamps "
                                       f"Int16[2] := {E['entrance']} last, before Field({E['member']})")


def hub_options(toml_path) -> list | None:
    """The journey menu's option texts in a gen-hub ``hub.field.toml`` (its ``[[choice]]`` options), or None."""
    import tomllib
    try:
        doc = tomllib.loads(Path(toml_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    ch = doc.get("choice") or []
    return [o.get("text") for o in (ch[0].get("options") or [])] if ch else None


def row_text(journeys_path, row_id: str) -> list | None:
    """The DATA lines (every line not starting with #) of story-seed's marked block for ``row_id`` in a
    journeys.toml, or None when the block is absent."""
    try:
        lines = Path(journeys_path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    start = f'# --- story-seed journey "{row_id}"'
    end = f'# --- end story-seed journey "{row_id}"'
    try:
        i = next(k for k, ln in enumerate(lines) if ln.startswith(start))
        j = next(k for k, ln in enumerate(lines) if ln.startswith(end) and k > i)
    except StopIteration:
        return None
    return [ln.rstrip() for ln in lines[i + 1:j] if ln.strip() and not ln.lstrip().startswith("#")]


def hub_check(view: dict, data: bytes | None, *, texts: bool = True) -> tuple:
    """P-HUB's byte and text clauses on one hub (judged per hub): H5.hub_bytes_check on the per-hub view (the
    frozen store sites in order, the stamps, Field() -> the entry only, no SC gate, no story read, the frozen
    twist), the US .eb's sha256 the frozen one, and -- ``texts`` -- the menu options in its hub.field.toml and the
    row's data lines in its journeys.toml the frozen texts."""
    H = view["hub"]
    ok, detail, _stores = H5.hub_bytes_check(view, data)
    bad = [] if ok else [detail]
    sha = hashlib.sha256(data).hexdigest() if data is not None else None
    if sha != H["eb_sha256"]:
        bad.append(f"US .eb sha256 {str(sha)[:16]}..., not the frozen {str(H['eb_sha256'])[:16]}...")
    if texts:
        opts = hub_options(H["toml"])
        if opts != H["options"]:
            bad.append(f"options {opts} in {H['toml']}, not {H['options']}")
        rt = row_text(H["journeys"], H["row_id"])
        if rt != H["row_text"]:
            bad.append(f"row {H['row_id']} data lines {rt}, not the frozen {H['row_text']}")
    return not bad, f"{H['name']} ({H['id']}): " + ("; ".join(bad) or f"{detail}; sha {sha[:16]}...; options and "
                                                                          f"row text as frozen")


def manifest_check(pred: dict, manifest: Path = MANIFEST, f5_manifest: Path = F5_MANIFEST) -> tuple:
    """P-MANIFEST's hub and member-sha clauses: rung5b_forks.json lists the two hubs with the frozen ids, names and
    eb sha256s (never F5's 31100), and any member eb sha it lists is rung5_forks.json's F5 entry."""
    try:
        man = json.loads(Path(manifest).read_text(encoding="utf-8"))
        f5 = json.loads(Path(f5_manifest).read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        return False, f"cannot read the manifests: {type(err).__name__}: {str(err)[:120]}"
    bad = []
    hubs = man.get("hubs") or {}
    for side in FORKS:
        H, m = pred["hubs"][side], hubs.get(side) or {}
        got = (m.get("id"), m.get("name"), m.get("eb_sha256"))
        if got != (H["id"], H["name"], H["eb_sha256"]):
            bad.append(f"{side} hub {got[:2]} sha {str(got[2])[:16]}, frozen {(H['id'], H['name'])} "
                       f"{str(H['eb_sha256'])[:16]}")
    if any((m or {}).get("id") == f5["hub"]["id"] for m in hubs.values()):
        bad.append(f"F5's hub {f5['hub']['id']} is listed")
    mine = ((man.get("chains") or {}).get("F5") or {}).get("eb_sha256")
    if mine is not None and mine != f5["chains"]["F5"]["eb_sha256"]:
        bad.append("its member eb sha256s are not rung5_forks.json's F5 entries")
    return not bad, "; ".join(bad) or f"hubs {[(hubs[s]['id'], hubs[s]['name']) for s in FORKS]} as frozen"


def preflight5b(pred: dict, roots: list, stock, sides: dict, *, manifest: Path = MANIFEST, ran=None,
                pins: bool = True, env: dict | None = None, ini=None) -> list:
    """Every static pre-flight on the live install, in the frozen order (design 4.9; H5.preflight5, rung5_hub.py:
    289-318, over two hubs): ``[(ok, what, detail)]``. R.preflight (P-MANIFEST's members, P-DEPLOY's members,
    P-FLOOR, P-EXITS, P-STOCK) reads F5's own manifest (the chain IS F5's) through ``sides`` = H5.tours5. P-INI reads
    ``ini`` (default the install's Memoria.ini, :func:`ini_check`)."""
    ran = ran or T.mod_script_source(roots)
    base = {w.split(":")[0]: (ok, w, d) for ok, w, d in R.preflight(pred, roots, stock, sides, F5_MANIFEST)}

    def data(fid):
        try:
            idx = ran(fid)
        except T.TraceError:
            return None
        return None if idx is None else idx.data

    ok_m, _w, d_m = base["P-MANIFEST"]
    ok_h, d_h = manifest_check(pred, manifest)
    out = [(ok_m and ok_h, "P-MANIFEST: the frozen member set and the two hubs are the deployed ones "
                           "(rung5_forks.json, rung5b_forks.json)", f"{d_m} || {d_h}")]
    ok_d, _w, d_d = base["P-DEPLOY"]
    inst = [H5.hub_install_check(hub_view(pred, s), roots) for s in FORKS]
    out.append((ok_d and all(ok for ok, _ in inst), "P-DEPLOY: every member and both hubs registered once; the "
                "members keep their fork rows, the hubs have none and no mod walkmesh",
                d_d + " || " + " || ".join(d for _ok, d in inst)))
    hub_bytes = {s: data(pred["hubs"][s]["id"]) for s in FORKS}
    for s in FORKS:
        ok, d = hub_check(hub_view(pred, s), hub_bytes[s])
        out.append((ok, f"P-HUB ({s}): the deployed hub is its frozen seed and nothing else", d))
    ops = [partyops_check(hub_view(pred, s), hub_bytes[s]) for s in FORKS]
    out.append((all(ok for ok, _ in ops), "P-PARTYOPS: the picks' party operations are the frozen ones",
                " || ".join(d for _ok, d in ops)))
    ok_e, d_e = entry_check(pred, stock, hub_bytes)
    out.append((ok_e, "P-ENTRY: the hand-over the post phase models is the one deployed and the one stock uses", d_e))
    ok_p, d_p = H5.pure_check(pred, data, stock)
    out.append((ok_p, "P-PURE: every member is its donor's .eb with only the chain's Field() targets remapped", d_p))
    out += [base["P-FLOOR"], base["P-EXITS"], base["P-STOCK"]]
    ok_i, d_i, _vals = ini_check(ini)
    out.append((ok_i, "P-INI: the Memoria.ini switches the removes and the autosave rest on (AllCharactersAvailable "
                      "< 2, no autosave switch, Netsync off or the host)", d_i))
    if pins:
        ok_n, d_n, _st = p_pins(env=env)
        out.append((ok_n, "P-PINS: the resolver's seven F5b regression pins ran and PASSED", d_n))
    return out


def build_hubs(out: Path, pred: dict) -> Path:
    """``py -m ff9mapkit build <hub toml> --out <out>/<id>`` for both hubs (offline, sub-second each) -> ``out``."""
    for s in FORKS:
        H = pred["hubs"][s]
        p = subprocess.run([sys.executable, "-m", "ff9mapkit", "build", H["toml"], "--out",
                            str(Path(out) / str(H["id"]))],
                           cwd=KIT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode:
            raise RuntimeError(f"ff9mapkit build {H['toml']} exited {p.returncode}: {(p.stdout + p.stderr)[-400:]}")
    return Path(out)


def offline_check5b(pred: dict, build: Path | None = None, stock=None, *, pins: bool = True,
                    env: dict | None = None) -> list:
    """The OFFLINE pre-flight on a build (build step 10), before anything is deployed: P-HUB (per hub: bytes, sha,
    options, row text), P-PARTYOPS, P-ENTRY and P-PINS. ``build`` = ``<dir>/<id>/`` per hub as ``ff9mapkit build
    --out`` writes it; None builds both hubs from their frozen tomls into a temp dir first."""
    stock = stock or T.stock_script_source()
    tmp = None
    if build is None:
        tmp = tempfile.TemporaryDirectory(prefix="rung5b_build_")
        build = build_hubs(Path(tmp.name), pred)
    try:
        hub_bytes = {s: H5.built_eb(Path(build), pred["hubs"][s]["id"]) for s in FORKS}
        out = []
        for s in FORKS:
            ok, d = hub_check(hub_view(pred, s), hub_bytes[s])
            out.append((ok, f"P-HUB ({s}, offline build)", d))
        ops = [partyops_check(hub_view(pred, s), hub_bytes[s]) for s in FORKS]
        out.append((all(ok for ok, _ in ops), "P-PARTYOPS (offline build)", " || ".join(d for _ok, d in ops)))
        ok_e, d_e = entry_check(pred, stock, hub_bytes)
        out.append((ok_e, "P-ENTRY (offline build)", d_e))
        if pins:
            ok_n, d_n, _st = p_pins(env=env)
            out.append((ok_n, "P-PINS", d_n))
        return out
    finally:
        if tmp is not None:
            tmp.cleanup()


# ======================================================================== the trace's cuts (pure, offline)
def ktuple(k) -> tuple:
    """A WriteKey or a registered key dict as ``(donor, sid, tag, off, target, value)`` (a tuple stays itself)."""
    if isinstance(k, tuple) and not hasattr(k, "donor"):
        return k
    if isinstance(k, dict):
        return (k["donor"], k["sid"], k["tag"], k["off"], k["target"], k["value"])
    return (k.donor, k.sid, k.tag, k.off, k.target, k.value)


def _kshow(ks, n: int = 4) -> list:
    return [f"{d} e{s} t{t} {o:+d} {tg}={v}" for d, s, t, o, tg, v in sorted(ks)[:n]]


def keyset5b(d, pred) -> set:
    """A digested run's keys as tuples, member and seam alike, outside the timing site (H5.keyset's)."""
    return {ktuple(k) for k in H5.keyset(d, pred)}


def _cut(rows, cut: int) -> tuple:
    """R.from_start's body (rung3_trace.py:564-584) at a row INDEX: every epoch row kept, the w/r rows before
    ``cut`` dropped with the count rows of their sites; ``(rows, fields before)``."""
    kept, live = [], set()
    for i, r in enumerate(rows):
        if r.k == "e":
            kept.append(r)
            live = set()
        elif r.k == "c":
            if r.site in live:
                kept.append(r)
        elif i >= cut:
            kept.append(r)
            if r.k == "w":
                live.add(r.site)
    return kept, sorted({r.fld for r in rows[:cut] if r.k in ("w", "r")})


def from_line(rows, line: int) -> tuple:
    """R.from_start's cut at a LINE, not a field: the rows from the first w/r row AFTER ``line`` on (S's post-wake
    window starts at the row after the wake's SC store -- never at tour_line, which would drop the exit's +116)."""
    cut = next((i for i, r in enumerate(rows) if r.k in ("w", "r") and r.line > line), len(rows))
    return _cut(rows, cut)


def _wr(rows) -> list:
    return [(i, r) for i, r in enumerate(rows) if r.k in ("w", "r")]


def cuts(r, pred) -> dict:
    """A run's frozen cuts (design 4.4), off its RAW rows: ``{wake, land, land_cut, hand, hand_cut}``. ``land`` is
    the first row of the landing -- S: its first post-wake row in the entry's place (351); a fork side: its first row
    in the entry member (31101) -- and ``land_cut`` the line of the last w/r row before it (the LAND state is
    taken after that row). ``hand`` is the first row after the landing outside the entry's place or (a store) with
    tag != 0 -- the entry's own arrival is all tag 0 -- and ``hand_cut`` the last w/r row before it (the HAND-BACK
    state). None where the run has no such row."""
    raw = r.get("raw") or []
    side = r["side"]
    place = place_of(side, pred)
    E = pred["entry"]
    out = {"wake": None, "land": None, "land_cut": None, "hand": None, "hand_cut": None}
    wr = _wr(raw)
    if side == "S":
        w = H5.wake_row(raw, pred, {})
        out["wake"] = w
        if w is None:
            return out
        land = next((k for k, (_i, x) in enumerate(wr) if x.line > w.line and place(x.fld) == E["donor"]), None)
    else:
        land = next((k for k, (_i, x) in enumerate(wr) if x.fld == E["member"]), None)
    if land is None or land == 0:
        return out
    out["land"], out["land_cut"] = wr[land][1], wr[land - 1][1].line
    hand = next((k for k in range(land + 1, len(wr))
                 if place(wr[k][1].fld) != E["donor"] or (wr[k][1].k == "w" and wr[k][1].tag != 0)), None)
    if hand is not None:
        out["hand"], out["hand_cut"] = wr[hand][1], wr[hand - 1][1].line
    return out


def land_cut(r, pred) -> tuple:
    """THE LAND CUT: ``(the landing's first row, the line of the last w/r row before it)`` -- R5B-LAND's state is
    taken after that line (:func:`cuts`); ``(None, None)`` when the run never landed."""
    c = cuts(r, pred)
    return c["land"], c["land_cut"]


def handback_cut(r, pred) -> tuple:
    """THE HAND-BACK CUT: ``(the first post-landing row outside the entry's place or with tag != 0, the line of the
    last w/r row before it)`` -- R5B-STATE's state (:func:`cuts`); ``(None, None)`` when there is none."""
    c = cuts(r, pred)
    return c["hand"], c["hand_cut"]


def burst_keys(d, lo: int, hi: int | None) -> set:
    """The keys a digest FIRST evidenced by an emitted row with ``lo <= line < hi`` (the landing burst: the entry's
    own arrival, up to the hand-back cut) -- a key evidenced only by a count row is not in a burst."""
    return {ktuple(k) for k, o in d.keys.items() if not o.counted and o.at >= lo and (hi is None or o.at < hi)}


def state_diff(rs: dict, rf: dict, skip_bytes=()) -> dict:
    """Two reconstructed states (H5.reconstruct) compared PER BIT over the union of what either knows, with the
    NEW-GAME FALLBACK: a bit one side never touched before its cut takes that side's first-seen value (its own later
    ``old``, else the other side's first-seen: both runs start at New Game). ``skip_bytes`` aside (the timing byte).
    Returns ``{"diff": {bit: (s, f)}, "first": [bits whose first-seen values disagree], "uncertain": [bytes]}``."""
    skip = {int(b) for b in skip_bytes}
    ks, kf, fs, ff = rs["known"], rf["known"], rs["first"], rf["first"]
    bits = {b for b in set(ks) | set(kf) if (b >> 3) not in skip}
    diff = {}
    for b in bits:
        vs = ks[b] if b in ks else fs.get(b, ff.get(b))
        vf = kf[b] if b in kf else ff.get(b, fs.get(b))
        if vs != vf:
            diff[b] = (vs, vf)
    first = sorted(b for b in set(fs) & set(ff) if (b >> 3) not in skip and fs[b] != ff[b])
    unc = sorted({b >> 3 for b in bits & (set(rs["uncertain"]) | set(rf["uncertain"]))})
    return {"diff": diff, "first": first, "uncertain": unc}


def registered(bits: dict) -> dict:
    """A frozen ``{bit: [stock, fork]}`` as ``{int bit: (stock, fork)}``."""
    return {int(b): tuple(v) for b, v in (bits or {}).items()}


def diff_against(got: dict, want: dict) -> list:
    """Why a per-bit diff is not the registered one: unregistered differing bits, registered bits that do not
    differ, and registered bits that differ with other values -- each grouped by byte."""
    extra = sorted(b for b in got if b not in want)
    lost = sorted(b for b in want if b not in got)
    other = sorted(b for b in got if b in want and tuple(got[b]) != tuple(want[b]))
    out = []
    if extra:
        out.append(f"unregistered bits differ in bytes {sorted({b >> 3 for b in extra})} (bits {extra[:6]})")
    if lost:
        out.append(f"registered bits do not differ in bytes {sorted({b >> 3 for b in lost})} (bits {lost[:6]})")
    if other:
        out.append(f"registered bits differ with other values: {[(b, got[b], want[b]) for b in other[:4]]}")
    return out


def last_entry(raw, pred) -> dict | None:
    """The trace's LAST FIELD ENTRY -- what a run-end autosave must name: ``{"field", "sc", "entrance"}``, the field
    entered and SC / Int16[2] as the state stood after the last row before it (the autosave is written on entry,
    before the new field's scripts run). None when the run changed field never, or those bytes are not known."""
    wr = [x for x in (raw or []) if x.k in ("w", "r")]
    j = next((k for k in range(len(wr) - 1, 0, -1) if wr[k].fld != wr[k - 1].fld), None)
    if j is None:
        return None
    rc = H5.reconstruct(raw, wr[j - 1].line, saturate=pred["stockstate"]["saturate"])
    vals = [H5.byte_value(rc["known"], b) for b in range(4)]
    if any(v is None for v in vals) or rc["contradictions"] or ({0, 1, 2, 3} & {b >> 3 for b in rc["uncertain"]}):
        return None
    ent = vals[2] | vals[3] << 8
    return {"field": wr[j].fld, "sc": vals[0] | vals[1] << 8, "entrance": ent - 0x10000 if ent & 0x8000 else ent}


def footprint(rows, pred) -> list:
    """The w rows in a window that touch the party-footprint bytes (predictions party.footprint_bytes)."""
    fp = set(pred["party"]["footprint_bytes"])
    return [x for x in (rows or []) if x.k == "w" and fp & set(x.span)]


# ======================================================================== SUPP, two-tier (pure, offline)
_FLOWS: dict = {}


def _flow(stock, donor: int, sid: int, tag: int):
    """``(FuncFlow, entry start, function start)`` of a stock function, memoized; None when it does not decode."""
    k = (donor, sid, tag)
    if k not in _FLOWS:
        from ff9mapkit.eb.cfg import FuncFlow
        idx = stock(donor)
        fn = idx.function(sid, tag) if idx is not None else None
        try:
            _FLOWS[k] = None if fn is None else (FuncFlow.build(idx.data, fn[2], fn[3]), fn[0].abs_start, fn[2])
        except Exception:                         # noqa: BLE001 -- an undecodable function has no dominance to offer
            _FLOWS[k] = None
    return _FLOWS[k]


def supp_tier(pred: dict, k) -> str | None:
    """"proven" / "blind" when key ``k`` is a registered SUPP key, else None."""
    t = ktuple(k)
    for tier in ("proven", "blind"):
        if any(ktuple(x) == t for x in pred["supp"][tier]):
            return tier
    return None


def supp_ok(pred: dict, k, s_run: dict, stock) -> tuple:
    """Is FORK ONLY key ``k`` admitted by SUPP against stock run ``s_run`` (design 4.4, two tiers)? ``(ok, why)``.
    Both tiers: S emitted it same:1 with that value BEFORE its wake row, and S's count row for the site ends at
    that value (``last``) -- the key's post-wake stores were COUNTED, not emitted. SUPP-PROVEN also needs, in THAT
    run, a row of S's own post-wake window in the same function at a site the key's site DOMINATES (FuncFlow):
    evidence the function ran past the key's site after the wake. SUPP-BLIND (no such evidence exists) is
    value-checked only -- a registered MIRROR blind spot."""
    tier = supp_tier(pred, k)
    if tier is None:
        return False, "not a SUPP key"
    donor, sid, tag, off, target, value = ktuple(k)
    raw = s_run.get("raw") or []
    w = H5.wake_row(raw, pred, {})
    if w is None:
        return False, f"{s_run.get('label')}: no wake row"
    fl = _flow(stock, donor, sid, tag)
    if fl is None:
        return False, f"no stock function {donor} e{sid} t{tag}"
    flow, ea, fa = fl
    ip = fa - ea + off
    at = (donor, sid, tag, ip)
    pre = [x for x in raw if x.k == "w" and x.line < w.line and (x.fld, x.sid, x.tag, x.ip) == at
           and x.target == target]
    if not any(x.same == 1 and x.new == value for x in pre):
        return False, f"{s_run.get('label')} never emitted {target}={value} same:1 at ip{ip} before its wake"
    cnt = [x for x in raw if x.k == "c" and (x.fld, x.sid, x.tag, x.ip) == at and x.target == target]
    if not cnt or cnt[-1].last != value:
        return False, f"{s_run.get('label')}'s count row at ip{ip} ends at {cnt[-1].last if cnt else None}, not {value}"
    if tier == "blind":
        return True, "blind: value-checked"
    koff = fa + off
    kb = flow.block_at(koff)
    ev = []
    for x in raw:
        if x.k != "w" or x.line <= w.line or x.src != "eb" or (x.fld, x.sid, x.tag) != (donor, sid, tag):
            continue
        o = ea + x.ip
        bb = flow.block_at(o)
        if kb is not None and bb is not None and (flow._dom[bb] >> kb) & 1 and (bb != kb or o > koff):
            ev.append(x)
    if not ev:
        return False, (f"{s_run.get('label')}: no post-wake row in {donor} e{sid} t{tag} at a site +{off} dominates "
                       f"(SUPP-PROVEN needs that evidence)")
    return True, f"proven: {len(ev)} dominated post-wake rows (first ip{ev[0].ip})"


# ======================================================================== reading a session (pure, offline)
def read_run5b(run_dir: Path, rec: dict, pred: dict, chains: dict, ran, stock) -> dict:
    """One recorded run, read -- H5.read_run5 (rung5_hub.py:647-689) over three sides: a FORK run that never reached
    its entry (31101) is not digested (``side != "S"`` in place of :674). S also gets its POST-WAKE WINDOW:
    ``window_rows`` (:func:`from_line` at its wake row) and ``window`` (their digest) -- what F5B is compared with;
    on a fork side the window IS its digest (its rows start at the entry)."""
    i, side = rec["i"], rec["side"]
    trace_name, log_name = R.run_names(i, side)
    r = {"i": i, "side": side, "label": f"{side}#{i}", "rec": rec, "raw": None, "rows": None, "pre": [], "log": None,
         "digest": None, "window": None, "window_rows": None, "broken": [], "void": []}
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
            if side != "S" and not any(x.k in ("w", "r") and x.fld == start for x in split[0]):
                r["void"].append(f"never reached {start}")
            else:
                r["rows"], r["pre"] = R.from_start(split[0], start)
    else:
        r["void"].append("no trace")
    if lp.is_file():
        r["log"] = json.loads(lp.read_text(encoding="utf-8"))
    else:
        r["void"].append("no log")
    mem = chains.get("F5") if side in FORKS else None
    if r["rows"] is not None:
        try:
            r["digest"] = T.digest(r["label"], r["rows"], scripts=ran, donor_scripts=stock, members=mem)
        except T.TraceError as err:
            r["broken"].append(f"cannot be digested ({str(err)[:100]})")
    if side in FORKS:
        r["window"], r["window_rows"] = r["digest"], r["rows"]
    elif r["digest"] is not None:
        w = H5.wake_row(r["raw"], pred, {})
        if w is not None:
            r["window_rows"], _pre = from_line(r["raw"], w.line)
            try:
                r["window"] = T.digest(r["label"] + " window", r["window_rows"], scripts=ran, donor_scripts=stock)
            except T.TraceError as err:
                r["broken"].append(f"its post-wake window cannot be digested ({str(err)[:100]})")
    return r


def void_why5b(r, pred) -> list:
    """Why FORK run ``r`` is VOID by the frozen coverage rule (R._void_why, rung3_trace.py:642-673, for an entry past
    the wake): not read; incomplete; never stood in the entry; the landing record not ok (the hub leg + landing,
    :func:`enter_past`); an unclean stop (F5B "SC left" / "passes exhausted" / "budget spent", CTL "prefix
    replayed"); a "ran" pattern never written (F5B both, CTL the 351 lobby exit only). The wake is NOT asked for --
    on these sides its absence is R5B-NOWAKE's to judge, never coverage."""
    C = pred["coverage"]
    out = list(r["void"]) + list(r["broken"])
    d, rows, side = r["digest"], r["rows"], r["side"]
    if d is None:
        return out or ["not read"]
    if d.incomplete:
        out.append("INCOMPLETE (no `off`)")
    if not any(x.fld == pred["start"][side] for x in rows if x.k != "c"):
        out.append(f"never stood in its entry {pred['start'][side]}")
    lands = [x for x in (r["log"] or {}).get("log", []) if x.get("k") == "landing"]
    if not (lands and lands[-1].get("ok")):
        out.append(f"the landing handed back no control in {pred['entry']['donor']} at {pred['beat']}")
    stop = R._stop(r)
    if not any(stop.startswith(s) for s in C["clean_stop"][side]):
        out.append(f"stopped: {stop[:120]}")
    out += [f"{p['name']}: never" for p in (C["ran"] if side == "F5B" else C["ran_ctl"]) if not R._has(d, p)]
    return out


def replay_why5b(r, by_i: dict, pred, chains, lo: int, hi: int | None) -> list:
    """Why fork run ``r`` is not a replay of its covered partner's walk SLICE ``[lo:hi]`` -- H5.replay_why5
    (rung5_hub.py:692-720) with ``want = entered_walk(partner)[lo:hi]`` in place of the whole walk (:706), the same
    slice in the "SC left" prefix branch (:713-714). The frozen replay_why5 compares the WHOLE walk and so VOIDs
    every F5B (its replay never holds step 1, the hand-over the pick replaces) -- it is not used here."""
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
    want = D.entered_walk(p["log"]["log"])[lo:hi]
    steps = [x for x in r["log"]["log"] if x.get("k") == "cross" and x.get("leg") == "replay"]
    got = D.entered_walk(steps, chains.get("F5"))
    if got == want:
        return []
    if R._stop(r).startswith("SC left"):
        at = next((j for j, x in enumerate(steps) if x.get("sc1", pred["beat"]) != pred["beat"]), len(steps))
        got = D.entered_walk(steps[:at], chains.get("F5"))
        if got == want[:len(got)]:
            return []
    sl = f"walk[{lo}:{'' if hi is None else hi}]"
    bad = next((j for j, (a, b) in enumerate(zip(got, want)) if a != b), None)
    if bad is not None:
        return [f"its replay of S#{k}'s {sl} diverged at step {bad + 1}: {D.step_name(got[bad])}, not "
                f"{D.step_name(want[bad])}"]
    return [f"it replayed {len(got)} of the {len(want)} steps of S#{k}'s {sl}"]


def _partner_walk(r, by_i) -> list | None:
    p = by_i.get(r["rec"].get("partner"))
    return D.entered_walk(p["log"]["log"]) if p is not None and p.get("log") is not None else None


def stop_class5b(r, pred: dict, by_i: dict) -> dict | None:
    """A VOID fork run's STOP CLASS -- H5.stop_class (rung5_hub.py:735-816) for an entry past the wake, DRIVE tested
    first and always winning: ``{"cls", "point", "why"}``; None for S or a covered run. The points: "hub" (as F5:
    the stamps landed and the landing's own wait timed out live), "landing@<place>" (the leg returned in 31101 and
    :func:`enter_past` raised -- the wake ran, another place, no control -- or the landing record is not ok),
    "replay@<step>(<step name>)" (the step numbered in the REPLAYED slice, named), "scene@<place>@<sc>". Computed
    for CTL too, and listed; THE HALT counts F5B's alone."""
    if r["side"] not in FORKS or not r["why_void"]:
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
    view = hub_view(pred, r["side"])
    start = pred["start"][r["side"]]
    landed = H5.stamps_landed(r, view)
    if phase == S["hub"]["phase"]:
        if r["rows"] is not None:
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
    if r["rows"] is None and not (phase == S["landing"]["phase"] and landed):
        return drive(f"stopped in phase {phase} with no row in {start}" + (" and no stamp in the hub" if not landed
                                                                           else "") + f": {stop[:100]}")
    land = next((x for x in reversed((r["log"] or {}).get("log", [])) if x.get("k") == "landing"), None)
    if phase == S["landing"]["phase"]:
        raised = any(re.search(pat, stop) for pat in S["landing"]["raised"])
        if raised or (land is not None and not land.get("ok")):
            where = (land or {}).get("place") or (rec.get("at") or {}).get("place") or pred["entry"]["donor"]
            return {"cls": "FORK-STOP", "point": f"landing@{where}", "why": stop[:160]}
    m = re.search(S["replay"]["stop"], stop)
    if m:
        return {"cls": "FORK-STOP", "point": f"replay@{m.group(1)}({m.group(2)})", "why": stop[:160]}
    at = rec.get("at") or {}
    if phase in S["scene"]["phases"] and any(re.search(pat, stop) for pat in S["scene"]["raised"]):
        return {"cls": "FORK-STOP", "point": f"scene@{at.get('place')}@{at.get('sc')}", "why": stop[:160]}
    return {"cls": "UNCLASSED", "point": None, "why": "; ".join(r["why_void"])[:200]}


def judge5b(runs: list, pred: dict) -> list:
    """Judge read runs by the frozen coverage rule, in place -- H5.judge5 (rung5_hub.py:819-834) over three sides:
    S first (R._void_why, unchanged); then each fork run (:func:`void_why5b`, its WALK GATE on the partner's walk,
    :func:`replay_why5b` on its frozen slice); then every stop class -- over ``runs`` alone, so the runs a session
    had recorded when it planned a re-run are judged as it judged them then."""
    chains = R.chain_members(pred)
    by_i = {r["i"]: r for r in runs}
    for r in runs:
        if r["side"] == "S":
            r["why_void"] = R._void_why(r, pred, chains, None)
    for r in runs:
        if r["side"] in FORKS:
            r["why_void"] = void_why5b(r, pred)
            walk = _partner_walk(r, by_i)
            if walk is not None and not r["rec"].get("skipped"):
                gate = walk_gate(pred, r["side"], walk)
                if gate:
                    r["why_void"].append(gate)
            lo, hi = pred["replay"][r["side"]]
            r["why_void"] += replay_why5b(r, by_i, pred, chains, lo, hi)
    for r in runs:
        r["stop_class"] = stop_class5b(r, pred, by_i)
    return runs


def read_session5b(run_dir, pred: dict, *, stock, roots, session: dict) -> list:
    """Every run the session recorded, read (:func:`read_run5b`, against the session's scripts/ snapshot first)
    and judged (:func:`judge5b`) -- H5.read_session5 (rung5_hub.py:837-844)."""
    run_dir = Path(run_dir)
    chains = R.chain_members(pred)
    snap = {int(p.stem): p.read_bytes() for p in (run_dir / "scripts").glob("*.eb")}
    ran = T.mod_script_source(roots, fallback=stock, explicit=snap)
    return judge5b([read_run5b(run_dir, rec, pred, chains, ran, stock) for rec in session.get("runs", [])], pred)


def fork_stop_points5b(runs: list) -> Counter:
    """``Counter({point: F5B runs that FORK-STOPped there})`` (H5.fork_stop_points over F5B; CTL's are listed only)."""
    return Counter(r["stop_class"]["point"] for r in runs
                   if r["side"] == "F5B" and (r.get("stop_class") or {}).get("cls") == "FORK-STOP")


def halted5b(runs: list) -> str | None:
    """THE HALT (H5.halted, rung5_hub.py:858-861): the point two F5B runs FORK-STOPped at, or None."""
    twice = sorted(p for p, n in fork_stop_points5b(runs).items() if n >= 2)
    return twice[0] if twice else None


def short_sides5b(runs: list, pred: dict) -> list:
    """The sides short of covered runs: S and F5B under ``min_covered``, CTL under ``min_ctl``."""
    C = pred["coverage"]
    need = {"S": C["min_covered"], "F5B": C["min_covered"], "CTL": C["min_ctl"]}
    return [s for s in SIDES if sum(1 for r in runs if r["side"] == s and not r["why_void"]) < need[s]]


def untwinned5b(runs: list, side: str, pred: dict) -> list:
    """The covered stock runs a ``side`` run may still partner, oldest first -- H5.untwinned5 (rung5_hub.py:869-
    875) per fork side: no covered twin of that side yet, fewer than ``max_breaks`` driven non-covered runs of that
    side on it, and a walk that PASSES that side's gate (:func:`walk_gate`: a CTL is only planned on a qualifying
    S)."""
    mb = pred["replay"]["max_breaks"]
    twinned = {r["rec"].get("partner") for r in runs if r["side"] == side and not r["why_void"]}
    tried = Counter(r["rec"].get("partner") for r in runs if r["side"] == side and r["why_void"] and H5._driven(r))
    return [r["i"] for r in runs if r["side"] == "S" and not r["why_void"] and r["i"] not in twinned
            and tried[r["i"]] < mb and r["log"] is not None
            and walk_gate(pred, side, D.entered_walk(r["log"]["log"])) is None]


def rerun_plan5b(runs: list, pred: dict) -> tuple | None:
    """What runs next after the frozen nine, from judged runs -- H5.rerun_plan5 (rung5_hub.py:878-890) over three
    sides: ``(side, partner)`` or None (no side short, or THE HALT). S first while S is short; then F5B, then CTL,
    each on the oldest S it may still partner (:func:`untwinned5b`) -- none: a fresh S."""
    if halted5b(runs):
        return None
    short = short_sides5b(runs, pred)
    if not short:
        return None
    if short[0] == "S":
        return ("S", None)
    free = untwinned5b(runs, short[0], pred)
    return (short[0], free[0]) if free else ("S", None)


def pairing_faults5b(runs: list, pred: dict) -> list:
    """Where the session broke the registered pairing -- H5.pairing_faults5 (rung5_hub.py:893-928) over F5B and
    CTL: every fork run names an earlier stock run, a frozen-order one its round's S; the walk it was given is that
    partner's entered walk, the slice it replayed the frozen one, and a DRIVEN run's partner passes its side's walk
    gate; no covered S has two covered twins of one side; every re-run is the one :func:`rerun_plan5b` names from
    the runs before it, judged as the session judged them then -- none once the session had HALTED."""
    order = pred["order"]
    by_i = {r["i"]: r for r in runs}
    out = []
    for r in runs:
        if r["side"] not in FORKS:
            continue
        k = r["rec"].get("partner")
        p = by_i.get(k)
        if not isinstance(k, int) or p is None or p["side"] != "S" or k >= r["i"]:
            out.append(f"{r['label']}'s partner {k} is not an earlier stock run")
            continue
        own = R.round_partner(order, r["i"])
        if r["i"] <= len(order) and k != own:
            out.append(f"{r['label']} partners S#{k}, not its round's S#{own}")
        want = D.entered_walk(p["log"]["log"]) if p["log"] is not None else None
        if "walk" in r["rec"] and want is not None and r["rec"]["walk"] != want:
            out.append(f"{r['label']} was given a walk that is not S#{k}'s")
        if "slice" in r["rec"] and list(r["rec"]["slice"]) != list(pred["replay"][r["side"]]):
            out.append(f"{r['label']} replayed walk{r['rec']['slice']}, not the frozen {pred['replay'][r['side']]}")
        if H5._driven(r) and want is not None and walk_gate(pred, r["side"], want):
            out.append(f"{r['label']} was driven on S#{k}, whose walk fails its gate: "
                       f"{walk_gate(pred, r['side'], want)}")
    for side in FORKS:
        twins = Counter(r["rec"].get("partner") for r in runs if r["side"] == side and not r["why_void"])
        out += [f"S#{k} is partnered by {n} covered {side} runs" for k, n in sorted(twins.items()) if n > 1]
    for r in runs:
        if r["i"] <= len(order):
            continue
        before = judge5b([dict(x) for x in runs if x["i"] < r["i"]], pred)
        plan = rerun_plan5b(before, pred)
        ran = (r["side"], r["rec"].get("partner") if r["side"] in FORKS else None)
        if plan != ran:
            why = (f", where the session had HALTED (two F5B runs FORK-STOPped at {halted5b(before)})"
                   if halted5b(before) else f", where the plan named {plan[0]}"
                   + (f" on S#{plan[1]}" if plan[1] is not None else "") if plan else ", where no side was short")
            out.append(f"{r['label']} re-ran {ran[0]}" + (f" on S#{ran[1]}" if ran[1] is not None else "") + why)
    return out


# ======================================================================== the verdict (pure)
def _detail(problems: list, *notes) -> str:
    """A check's detail when it is not a clean PASS: its problems, then every note that is not None ("" when
    there is nothing to say -- the caller's PASS text follows)."""
    return " || ".join(x for x in ["; ".join(problems)] + [n for n in notes if n] if x)


def check_id(what: str) -> str:
    return what.split(":", 1)[0].split(" (", 1)[0].strip()


def verdict5b(checks: list, clauses: dict, *, f5b_pairs: int, ctl_covered: int, pred: dict) -> tuple:
    """THE FROZEN VERDICT (predictions "verdict", design 5), pure: ``(ok, text)`` -- ok True PROVEN, False FAILED,
    None NOT PROVEN. Any check FAIL: "FAILED: <check>[, ...]". Else PROVEN only when every check PASSes (none VOID)
    with at least ``min_f5b_pairs`` covered F5B pairs and ``min_ctl`` covered CTL runs. Else "NOT PROVEN: <halves>
    (<check>: <why>; ...)" -- a VOID check or R5B-CONTROL clause names its half (state, latches, party, walk; a
    load-bearing check outside them "run", any other "other"); too few F5B pairs leave every half unproven, too few
    CTL runs leave state/latches/party uncalibrated -- and the halves that ARE proven are named. The minimums are
    applied here, whatever the checks say."""
    V = pred["verdict"]
    res = {}
    for ok, what, detail in checks:
        res.setdefault(check_id(what), []).append((ok, detail))
    fails = [c for c, xs in res.items() if any(ok is False for ok, _d in xs)]
    if fails:
        first = next(d for ok, d in res[fails[0]] if ok is False)
        return False, f"FAILED: {', '.join(fails)} -- {fails[0]}: {first[:240]}"
    halves = V["halves"]
    member = {c: h for h, cs in halves.items() for c in cs}
    unproven: dict = {}

    def mark(half, what, why):
        unproven.setdefault(half, []).append(f"{what}: {why}")

    # R5-RUNS is VOID only for a coverage minimum, R5B-CONTROL only through its clauses: both are named by those
    for c, xs in res.items():
        for ok, d in xs:
            if ok is None and c not in ("VERDICT", "R5-RUNS", "R5B-CONTROL"):
                mark(member.get(c, "run" if c in V["load_bearing"] else "other"), c, f"VOID -- {d.strip()[:160]}")
    for cl, ok in sorted((clauses or {}).items()):
        name = f"R5B-CONTROL({cl})"
        if ok is not True and name in member:
            mark(member[name], name, "not PASS")
    if f5b_pairs < V["min_f5b_pairs"]:
        for h in halves:
            mark(h, "covered F5B pairs", f"{f5b_pairs} < {V['min_f5b_pairs']}")
    if ctl_covered < V["min_ctl"]:
        for h in ("state", "latches", "party"):
            mark(h, "covered CTL runs", f"{ctl_covered} < {V['min_ctl']} (uncalibrated)")
    if not unproven and any(ok is None for c, xs in res.items() if c != "VERDICT" for ok, _d in xs):
        mark("other", "a VOID check", "PROVEN needs every check PASS")       # never reached while the above hold
    if not unproven:
        return True, (f"PROVEN: every check PASS ({sum(len(x) for x in res.values())} checks), {f5b_pairs} covered "
                      f"F5B pairs, {ctl_covered} covered CTL runs")
    names = [h for h in list(halves) + ["run", "other"] if h in unproven]
    proven = [h for h in halves if h not in unproven]
    why = "; ".join(w for h in names for w in dict.fromkeys(unproven[h]))
    return None, (f"NOT PROVEN: {', '.join(names)} ({why[:600]})"
                  + (f" -- proven: {', '.join(proven)}" if proven else " -- no half proven"))


# ======================================================================== the analysis (pure, offline)
def analyse5b(run_dir, *, pred_path: Path | None = None, stock=None, roots=None) -> tuple:
    """F5b's checks over one session's saved traces, logs and records: ``([(ok, what, detail)], {file: text})``, ok
    True (PASS), False (FAIL) or None (VOID), the last entry THE VERDICT. Pure given the install and the session dir
    (every member's and both hubs' .eb from the session's own snapshot; the pre-flight legs, P-PARTYREMOVE and
    NC-THROW as the session RECORDED them). The predictions are the file the session recorded unless ``pred_path``
    overrides it (P-FROZEN judges either); a session or a predictions file that is not F5b's is refused
    (:class:`NotF5B`)."""
    run_dir = Path(run_dir)
    session = json.loads((run_dir / SESSION_FILE).read_text(encoding="utf-8"))
    pred_path = recorded_predictions(session) if pred_path is None else Path(pred_path)
    pred, sha = load_predictions(pred_path)
    recs = session.get("runs", [])
    alien = sorted({str(x.get("side")) for x in recs} - set(SIDES))
    bare = [f"{x.get('side')}#{x.get('i')}" for x in recs if x.get("side") in FORKS and "partner" not in x]
    holes = missing_numbers(pred) if pred.get("lane") == "F5b" else []
    if pred.get("lane") != "F5b" or alien or bare or holes:
        raise NotF5B(f"session {session.get('label')}: not an F5b session for {pred_path.name} (lane "
                     f"{pred.get('lane')})" + (f" -- sides {alien}" if alien else "")
                     + (f" -- {', '.join(bare)} name no stock partner" if bare else "")
                     + (f" -- the predictions freeze no {', '.join(holes)}" if holes else ""))
    C, n_min, n_ctl = pred["checks"], pred["coverage"]["min_covered"], pred["coverage"]["min_ctl"]
    out = [(session.get("predictions_sha256") == sha,
            "P-FROZEN: the predictions this analysis reads are the ones the session recorded before its first run",
            f"session {str(session.get('predictions_sha256'))[:16]} / file {sha[:16]}")]
    for ok, what, detail in session.get("preflight") or [(None, "P-STATIC: the session's static pre-flight",
                                                           "the session recorded none")]:
        out.append((ok, what, detail))
    legs = session.get("hubleg") or {}
    for side in FORKS:
        leg = legs.get(side)
        out.append((None if leg is None else bool(leg.get("ok")),
                    f"P-HUBLEG ({side}): in game, untraced, the hub leg reaches the menu, the stay row stays, the hub "
                    f"throws nothing", "the session recorded no leg" if leg is None else str(leg.get("detail"))[:400]))
    pr = session.get("partyremove")
    out.append((None if pr is None else pr.get("verdict"),
                "P-PARTYREMOVE: in game, untraced, the F5B pick's removes act on a real roster (CTL [0,2,3,1] -> F5B "
                "[0,255,255,255])", "the session recorded none" if pr is None else str(pr.get("why"))[:300]))
    chains = R.chain_members(pred)
    members = chains["F5"]
    stock = stock or T.stock_script_source()
    roots = D.mod_roots() if roots is None else roots
    runs = read_session5b(run_dir, pred, stock=stock, roots=roots, session=session)
    by_i = {r["i"]: r for r in runs}
    cov = {s: [r for r in runs if r["side"] == s and not r["why_void"]] for s in SIDES}
    pairs = {s: [(f, by_i[f["rec"]["partner"]]) for f in cov[s] if f["rec"].get("partner") in by_i
                 and not by_i[f["rec"]["partner"]]["why_void"]] for s in FORKS}
    skip = {pred["timing_site"]["byte"]}
    hub_idx = {}
    for side in FORKS:
        snap = run_dir / "scripts" / f"{pred['hubs'][side]['id']}.eb"
        hub_idx[side] = T.ScriptIndex(snap.read_bytes(), field_id=pred["hubs"][side]["id"]) if snap.is_file() else None
    memo: dict = {}

    def cut(r):
        if ("cut", r["i"]) not in memo:
            memo[("cut", r["i"])] = cuts(r, pred)
        return memo[("cut", r["i"])]

    def state(r, line):
        if ("st", r["i"], line) not in memo:
            memo[("st", r["i"], line)] = H5.reconstruct(r["raw"] or [], line, saturate=pred["stockstate"]["saturate"])
        return memo[("st", r["i"], line)]

    def compare_at(f, s, which: str) -> tuple:
        """``(diff | None, void why | None)`` of a fork run and its partner at the LAND or HAND-BACK cut."""
        cf, cs = cut(f), cut(s)
        lf, ls = cf[f"{which}_cut"], cs[f"{which}_cut"]
        if lf is None or ls is None:
            return None, f"{f['label']}/{s['label']}: no {which} cut ({'fork' if lf is None else 'stock'} side)"
        rf, rs = state(f, lf), state(s, ls)
        if rf["contradictions"] or rs["contradictions"]:
            return None, (f"{f['label']}/{s['label']}: calibration contradictions "
                          f"{(rf['contradictions'] or rs['contradictions'])[0]}")
        sd = state_diff(rs, rf, skip)
        if sd["uncertain"]:
            return None, f"{f['label']}/{s['label']}: uncertain compared bytes {sd['uncertain']}"
        if sd["first"]:
            return None, f"{f['label']}/{s['label']}: New Game values disagree at bits {sd['first'][:6]}"
        return sd["diff"], None

    def burst(r) -> set | None:
        c = cut(r)
        d = r["window"]
        if d is None or c["land"] is None:
            return None
        return burst_keys(d, c["land"].line, c["hand"].line if c["hand"] is not None else None)

    def cls_text(r) -> str:
        sc = r.get("stop_class")
        return "" if not sc else f"{sc['cls']}" + (f" @{sc['point']}" if sc["point"] else "")

    def verdict_of(fail, vd, enough=True, calibrated=True):
        """UNCALIBRATED FIRST (checks.json R5B-CONTROL: "each failed clause makes its dependent R5B check VOID as
        uncalibrated"): a control clause that is not PASS leaves its dependent check VOID whatever it saw -- a
        difference read by an instrument the control could not calibrate is not evidence. Calibrated: FAIL before
        VOID (a FAIL on one pair stands though another pair is VOID or the pairs are short), as F5's checks."""
        if not calibrated:
            return None
        if fail:
            return False
        if vd or not enough:
            return None
        return True

    # -- R5B-CONTROL first: its clauses calibrate LAND, STATE, ARRIVAL, ECHO and PARTY -------------------------
    K = pred["control"]
    clause = {c: [] for c in "abcde"}                   # per clause: (ok, why) per covered CTL
    want_a = registered(K["handback_bits"])
    want_b = {**registered(pred["land"]["bits"]), **registered(K["land_extra_bits"])}
    if registered(K["land_bits"]) != want_b:
        clause["b"].append((False, "the frozen control.land_bits is not land.bits plus land_extra_bits"))
    fo_frozen = {ktuple(k) for k in K["fork_only"]}
    so_frozen = {ktuple(k) for k in K["stock_only"]}
    supp351 = {ktuple(k) for k in pred["supp"]["proven"] + pred["supp"]["blind"]
               if k["donor"] == pred["entry"]["donor"]}
    for f, s in pairs["CTL"]:
        for which, c, want in (("hand", "a", want_a), ("land", "b", want_b)):
            diff, why = compare_at(f, s, which)
            if diff is None:
                clause[c].append((None, why))
            else:
                bad = diff_against(diff, want)
                clause[c].append((not bad, f"{f['label']}/{s['label']}: " + ("; ".join(bad) if bad else
                                                                             f"{len(diff)} bits as registered")))
        bf, bs = burst(f), burst(s)
        if bf is None or bs is None:
            clause["c"].append((None, f"{f['label']}/{s['label']}: no landing burst"))
        else:
            fo, so = bf - bs, bs - bf
            adm = {k for k in fo & supp351 if supp_ok(pred, k, s, stock)[0]}
            bad = []
            if fo != fo_frozen | supp351 or adm != supp351:
                bad.append(f"FORK ONLY {_kshow(fo - supp351, 6)} + SUPP {len(fo & supp351)} ({len(adm)} admitted), "
                           f"want {_kshow(fo_frozen)} + the three 351 SUPP keys")
            if so != so_frozen:
                bad.append(f"STOCK ONLY {_kshow(so, 6)}, want {_kshow(so_frozen)}")
            clause["c"].append((not bad, f"{f['label']}: " + ("; ".join(bad) or "the burst as registered")))
        cf = cut(f)
        st1 = K["step1"]
        if cf["hand"] is None:
            clause["d"].append((None, f"{f['label']}: no hand-back cut"))
        else:
            raw = f["raw"]
            i0 = next(i for i, x in enumerate(raw) if x is cf["hand"])
            cross = []
            for x in raw[i0:]:
                if x.k in ("w", "r") and members.get(x.fld, x.fld) != pred["entry"]["donor"]:
                    break
                if x.k == "w":
                    cross.append(x)
            gone = [x for x in cross if (x.sid, x.tag, x.ip) == (st1["absent"]["sid"], st1["absent"]["tag"],
                                                                 st1["absent"]["ip"])]
            got = [x for x in cross if (x.sid, x.tag, x.ip, x.target, x.old, x.new) == tuple(
                st1["present"][k] for k in ("sid", "tag", "ip", "target", "old", "new"))]
            ab = st1["absent"]
            bad = ([f"a row at e{ab['sid']} t{ab['tag']} ip{ab['ip']}"] if gone else []) \
                + ([] if got else [f"no ip{st1['present']['ip']} {st1['present']['target']} 0 -> 1"])
            clause["d"].append((not bad, f"{f['label']}: " + ("; ".join(bad) or "the step-1 crossing as registered")))
        lr = ((f["rec"].get("party") or {}).get("landing"))
        base = ((f["rec"].get("party") or {}).get("baseline"))
        fresh, why = freshness(lr, base, {"sc": pred["beat"], "entrance": pred["entry"]["entrance"],
                                          "field": pred["entry"]["member"]})
        if not fresh:
            clause["e"].append((None, f"{f['label']}: landing read not fresh ({'; '.join(why)[:120]})"))
        else:
            clause["e"].append((lr.get("slot") == K["slot"], f"{f['label']}: landing slot {lr.get('slot')}"))
    clauses = {}
    for c, xs in clause.items():
        if len(pairs["CTL"]) < n_ctl:
            clauses[c] = None
        elif any(ok is False for ok, _w in xs):
            clauses[c] = False
        elif any(ok is None for ok, _w in xs) or not xs:
            clauses[c] = None
        else:
            clauses[c] = True
    ctl_detail = "; ".join(f"({c}) {WORD[clauses[c]]}" + (": " + (" | ".join(w for ok, w in clause[c]
                                                                              if ok is not True)[:200]
                                                                   or f"{len(pairs['CTL'])} covered CTL runs")
                                                           if clauses[c] is not True else "") for c in "abcde")
    # clause (e) calibrates the PARTY INSTRUMENT alone: its failure makes R5B-PARTY VOID (checks.json), and the halves
    # put R5B-CONTROL(e) in the party half -- an uncalibrated instrument, so it VOIDs this line, never FAILs it (a
    # FAILED headline needs the seed shown wrong); clauses (a)-(d) calibrate the state and latch checks and FAIL it
    ctl_line = (False if any(clauses[c] is False for c in "abcd")
                else None if any(v is not True for v in clauses.values()) else True,
                "R5B-CONTROL: the instrument is calibrated -- today's pre-phase row entered at the same place FAILS "
                "exactly as registered", f"{len(pairs['CTL'])} covered CTL runs (want >= {n_ctl}); " + ctl_detail)

    # -- R5-RUNS -------------------------------------------------------------------------------------------
    order = pred["order"]
    struct_ = []
    if [x["side"] for x in recs[:len(order)]] != order[:len(recs[:len(order)])]:
        struct_.append(f"the runs are {[x['side'] for x in recs[:len(order)]]}, not the frozen order")
    extra = recs[len(order):]
    if any(not x.get("rerun") for x in extra) or len(extra) > pred["rerun"]["max"]:
        struct_.append(f"{len(extra)} runs after the nine, {sum(1 for x in extra if x.get('rerun'))} of them re-runs "
                       f"(at most {pred['rerun']['max']})")
    if [x.get("i") for x in recs] != list(range(1, len(recs) + 1)):
        struct_.append("the runs are not numbered 1..n")
    struct_ += pairing_faults5b(runs, pred)
    struct_ += [f"{r['label']}: {b}" for r in runs for b in r["broken"]]
    tally = "; ".join(f"{s} {len(cov[s])} covered / {sum(1 for r in runs if r['side'] == s) - len(cov[s])} VOID"
                      for s in SIDES)
    voids = [f"{r['label']} [{cls_text(r) or 'VOID'}]: {', '.join(r['why_void'][:3])}" for r in runs if r["why_void"]]
    enough_runs = len(cov["S"]) >= n_min and len(cov["F5B"]) >= n_min and len(cov["CTL"]) >= n_ctl
    out.append((False if struct_ else True if enough_runs else None,
                "R5-RUNS: the frozen nine in order ([S F5B CTL] x3), then re-runs only (none after the halt); the "
                "pairing and the walk gates; >= 3 covered S and F5B, >= 2 covered CTL",
                ("; ".join(struct_[:4]) + " || " if struct_ else "") + tally
                + (" || VOID " + " | ".join(voids[:6]) if voids else "")))

    # -- R5-DONOR ------------------------------------------------------------------------------------------
    bad, forks_read = [], 0
    rung3 = set(range(30830, 30853))
    hub_ids = {pred["hubs"][s]["id"]: s for s in FORKS}
    for r in runs:
        if r["raw"] is None:
            continue
        wrong = Counter()
        if r["side"] in FORKS:
            forks_read += 1
            mine = pred["hubs"][r["side"]]["id"]
            start = pred["start"][r["side"]]
            c0 = next((j for j, x in enumerate(r["raw"]) if x.k in ("w", "r") and x.fld == start), len(r["raw"]))
            for x in r["raw"][:c0]:
                if x.k not in ("w", "r", "c"):
                    continue
                if x.fld in hub_ids and (x.fld != mine or x.don != x.fld):
                    wrong[f"hub row in {x.fld} don {x.don} (want only {mine}, naming itself)"] += 1
                elif x.fld in members:
                    wrong[f"member {x.fld} before the entry"] += 1
            for x in (r["rows"] or []):
                if x.k not in ("w", "r", "c"):
                    continue
                if x.fld in members:
                    if x.don != members[x.fld]:
                        wrong[f"member {x.fld} don {x.don} (want {members[x.fld]})"] += 1
                else:
                    wrong[f"{'a hub' if x.fld in hub_ids else 'real' if T.real_field(x.fld) else 'id'} {x.fld} after "
                          f"the entry"] += 1
        else:
            for x in (r["rows"] or []):
                if x.k not in ("w", "r", "c"):
                    continue
                if (x.fld in members or x.fld in hub_ids or x.fld in rung3 or 31100 <= x.fld <= 31199
                        or not T.real_field(x.fld) or x.don != x.fld):
                    wrong[f"stock row in {x.fld} don {x.don}"] += 1
        bad += [f"{r['label']}: {w} x{n}" for w, n in wrong.items()]
    out.append((False if bad else True if forks_read else None,
                "R5-DONOR: every fork row from the entry stands in a member naming its donor, every S row in a real "
                "field naming itself; before the entry, hub rows stand in the side's own hub",
                "; ".join(bad[:6]) or (f"{forks_read} fork runs read" if forks_read else "no fork run read")))

    # -- R5-JOIN -------------------------------------------------------------------------------------------
    read = [r for r in runs if r["digest"] is not None]
    fails = [(r["label"], x.fld, x.target, x.ip, why) for r in read for x, why in r["digest"].failures]
    notes = sorted({f"{r['label']}: {n}" for r in read for n in r["digest"].notes})
    out.append((False if len(fails) > C["R5-JOIN"]["max_failures"] or notes else True if read else None,
                "R5-JOIN: every script row from the start field on joins a store in the bytes its side ran",
                f"{len(fails)} failures {fails[:4]}; notes {notes[:3]}; {len(read)} runs digested"))

    # -- R5-REACH (F5B only; CTL's stops listed) --------------------------------------------------------------
    f5b = [r for r in runs if r["side"] == "F5B"]
    points = fork_stop_points5b(runs)
    stops = [(r["label"], r["stop_class"]) for r in runs if r["side"] in FORKS and r.get("stop_class")]
    fs = [f"{l} FORK-STOP @{c['point']}: {c['why'][:90]}" for l, c in stops if c["cls"] == "FORK-STOP"]
    un = [f"{l} UNCLASSED: {c['why'][:90]}" for l, c in stops if c["cls"] == "UNCLASSED"]
    dr = [f"{l} DRIVE: {c['why'][:70]}" for l, c in stops if c["cls"] == "DRIVE"]
    twice = {p: n for p, n in points.items() if n >= 2}
    un_f5b = [l for l, c in stops if c["cls"] == "UNCLASSED" and l.startswith("F5B")]
    ok = False if twice else True if (not points and not un_f5b and len(cov["F5B"]) >= n_min) else None
    out.append((ok, "R5-REACH: the fixed-seed fork does not stop where stock goes on -- no F5B run FORK-STOPs, twice "
                    "at one point FAILs",
                (f"FORK-STOPPED twice at {twice} || " if twice else "")
                + f"{len(cov['F5B'])} F5B runs covered; " + " | ".join(fs + un + dr) if (fs or un or dr)
                else f"{len(cov['F5B'])} F5B runs covered, no FORK-STOP, no UNCLASSED stop"))

    # -- R5-PREFIX -------------------------------------------------------------------------------------------
    bad, n_read = [], 0
    for r in f5b:
        p = by_i.get(r["rec"].get("partner"))
        if r["digest"] is None or p is None or p["why_void"] or p["window"] is None:
            continue
        n_read += 1
        extra_keys = keyset5b(r["digest"], pred) - keyset5b(p["window"], pred)
        left = {k for k in extra_keys if not supp_ok(pred, k, p, stock)[0]}
        if left:
            bad.append(f"{r['label']} (partner {p['label']}, {'covered' if not r['why_void'] else cls_text(r)}): "
                       f"{len(left)} keys its partner's post-wake window never wrote {_kshow(left)}")
    out.append((False if bad else True if n_read else None,
                "R5-PREFIX: THE PAIRED-WALK LAW for runs that did not finish -- every F5B run from its entry wrote "
                "only keys its partner's post-wake window wrote, or SUPP keys supp_ok admits",
                "; ".join(bad[:4]) or (f"{n_read} F5B runs read, each within its partner's window" if n_read
                                       else "no such F5B run")))

    # -- R5-STAMP (per hub; H5's R5-STAMP, rung5_hub.py:1103-1159) ----------------------------------------------
    layout = T.stock_layout([r["window"] for r in cov["S"] if r["window"] is not None]) if cov["S"] else {}
    bad, reached = [], {s: 0 for s in FORKS}
    for r in runs:
        if r["side"] not in FORKS or r["raw"] is None:
            continue
        view = hub_view(pred, r["side"])
        H, hid, idx = view["hub"], view["hub"]["id"], hub_idx[r["side"]]
        rows = H5.hub_rows(r, view)
        did = r["rows"] is not None
        reached[r["side"]] += did
        probs, stamps = [], []
        for x in rows:
            if x.k == "r":
                probs.append(f"list: residue on byte {x.byte} in the hub")
                continue
            if x.src != "eb" or x.don != hid or x.add:
                probs.append(f"src/don: a {x.src} {'count' if x.k == 'c' else 'row'} naming don {x.don}")
            if x.k == "w":
                for b, (o, v) in x.byte_changes().items():
                    if b != x.byte:
                        why = T.outside_target(layout, x.byte, b)
                        if why:
                            probs.append(f"width: {x.target} = {x.new} changed byte {b} {o} -> {v} ({why})")
            j = idx.join(x, donor=hid) if idx is not None and x.src == "eb" and not x.add else None
            if j is None or j.status != "store":
                probs.append(f"join: e{x.sid} t{x.tag} ip {x.ip} {x.target}: "
                             f"{'no hub snapshot' if idx is None else 'no script row' if j is None else j.reason[:80]}")
            elif (x.sid, x.tag) == (0, 0) and x.target in H["prologue_targets"]:
                continue
            if x.k == "c":
                probs.append(f"list: suppressed stores at e{x.sid} t{x.tag} ip {x.ip} {x.target}")
                continue
            stamps.append((x, j.rel if j is not None and j.status == "store" else None))
        got = [(x.sid, x.tag, x.ip, rel, x.target, x.old, x.new) for x, rel in stamps]
        want = [(s["sid"], s["tag"], s["ip"], s["off"], s["target"], s["old"], s["new"]) for s in H["stamp"]]
        if got != want and (did or got != want[:len(got)]):
            probs.append(f"list: the stamps are {[(g_[3], g_[4], g_[5], g_[6]) for g_ in got]}, not the frozen "
                         f"{[(w[3], w[4], w[5], w[6]) for w in want]}")
        last = max((j for j, x in enumerate(r["raw"] or []) if x.fld == hid and x.k in ("w", "r")), default=None)
        if last is not None:
            nxt = next((x for x in r["raw"][last + 1:] if x.k in ("w", "r")), None)
            if nxt is not None and nxt.fld != pred["start"][r["side"]]:
                probs.append(f"entry: the first row after the hub stands in {nxt.fld}, not {pred['start'][r['side']]}")
        elif did:
            probs.append("list: no row in the hub")
        bad += [f"{r['label']}: {p_}" for p_ in dict.fromkeys(probs)]
    out.append((False if bad else True if all(reached[s] >= 1 for s in FORKS) else None,
                "R5-STAMP: each hub's rows are its frozen seed -- the prologue and exactly its stamps, joined against "
                "the hub's own bytes, the entry next, no stamp wider than its variable",
                "; ".join(bad[:5]) or f"runs that reached {pred['entry']['member']}: {reached}"))

    # -- R5-STOCKSTATE (H5's, unchanged) ------------------------------------------------------------------------
    p = pred["stockstate"]
    what = ("R5-STOCKSTATE: fresh stock runs reproduce the wake-instant state (a regression check on S and the "
            "reconstructor)")
    if len(cov["S"]) < n_min:
        out.append((None, what, f"too few covered S runs -- {len(cov['S'])}/{n_min}"))
    else:
        fail, vd, shown = [], [], []
        for r in cov["S"]:
            w = H5.wake_row(r["raw"] or [], pred, {})
            rc = state(r, w.line) if w is not None else None
            if w is None:
                vd.append(f"{r['label']}: no wake row")
                continue
            if rc["contradictions"]:
                vd.append(f"{r['label']}: {len(rc['contradictions'])} contradictions, first {rc['contradictions'][0]}")
                continue
            unc = {b >> 3 for b in rc["uncertain"]}
            ch = H5.changed_bytes(rc) - set(p["input_timing_bytes"])
            frozen = set(p["changed_from_new_game"])
            stamp = {int(b): v for b, v in p["stamp_bytes"].items()}
            u = sorted(unc & (frozen | ch | set(stamp)))
            if u:
                vd.append(f"{r['label']}: uncertain bytes {u}")
                continue
            got = {b: H5.byte_value(rc["known"], b) for b in stamp}
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
                    "; ".join(fail[:4] + vd[:3]) or f"in every covered S run; calibrated: {', '.join(shown)}"))

    # -- R5B-NOWAKE -------------------------------------------------------------------------------------------
    bad, reached_m = [], 0
    m359 = pred["chain_map"].get(str(pred["start"]["S"]), pred["chain_map"].get(pred["start"]["S"]))
    m352 = pred["chain_map"].get(str(pred["wake"]["donor"]), pred["chain_map"].get(pred["wake"]["donor"]))
    for r in runs:
        if r["side"] not in FORKS or r["raw"] is None:
            continue
        mrows = [x for x in r["raw"] if x.k in ("w", "r") and x.fld in members]
        if not mrows:
            continue
        reached_m += 1
        if H5.wake_row(r["raw"], pred, members) is not None:
            bad.append(f"{r['label']}: the wake's SC store is in its trace")
        if any(x.fld == m359 for x in mrows):
            bad.append(f"{r['label']}: rows in {m359} (member(359))")
        first_e = next((x.line for x in mrows if x.fld == pred["entry"]["member"]), None)
        if any(x.fld == m352 and (first_e is None or x.line < first_e) for x in mrows):
            bad.append(f"{r['label']}: rows in {m352} before its first {pred['entry']['member']} row")
        if mrows[0].fld != pred["entry"]["member"]:
            bad.append(f"{r['label']}: its first member row stands in {mrows[0].fld}")
    out.append((False if bad else True if reached_m else None,
                "R5B-NOWAKE: the fork sides entered PAST the wake -- no wake store, no row in member(359), none in "
                "member(352) before the entry, the first member row in 31101",
                "; ".join(bad[:4]) or (f"{reached_m} fork runs reached a member" if reached_m
                                       else "no fork run reached a member")))

    out.append(ctl_line)

    # -- R5B-LAND / R5B-STATE -----------------------------------------------------------------------------------
    for cid, which, want, cl, text in (
            ("R5B-LAND", "land", registered(pred["land"]["bits"]), "b",
             "the seed lands on stock's hand-over state -- at the landing F5B equals stock outside the registered "
             "landing set, which differs exactly as registered"),
            ("R5B-STATE", "hand", registered(pred["residual"]["bits"]), "a",
             "after the entry's own arrival (the HAND-BACK cut) F5B equals stock bit for bit outside the registered "
             "residual R, which differs exactly as registered")):
        fail, vd, shown = [], [], []
        for f, s in pairs["F5B"]:
            diff, why = compare_at(f, s, which)
            if diff is None:
                vd.append(why)
                continue
            bad = diff_against(diff, want)
            if bad:
                fail.append(f"{f['label']}/{s['label']}: " + "; ".join(bad))
            hand = cut(f)["hand"]
            shown.append(f"{f['label']} {len(diff)} bits" + (f" (cut at {hand.fld} e{hand.sid} t{hand.tag} ip{hand.ip})"
                                                              if which == "hand" and hand is not None else ""))
        enough = len(pairs["F5B"]) >= n_min
        ok = verdict_of(fail, vd, enough, clauses[cl] is True)
        out.append((ok, f"{cid}: {text}",
                    _detail(fail[:3] + vd[:3], None if enough else f"{len(pairs['F5B'])} covered pairs (want >= "
                                                                   f"{n_min})",
                            None if clauses[cl] is True else f"R5B-CONTROL ({cl}) {WORD[clauses[cl]]}: uncalibrated")
                    or f"{len(pairs['F5B'])} covered pairs, each {len(want)} bits as registered: {', '.join(shown)}"))

    # -- R5B-ECHO ------------------------------------------------------------------------------------------------
    fail, vd = [], []
    for r in cov["S"] + cov["F5B"]:
        place = place_of(r["side"], pred)
        wl = r["window_rows"] or []
        for e in pred["echo"]:
            hits = [x for x in wl if x.k == "w" and place(x.fld) == e["donor"] and (x.sid, x.tag, x.ip) ==
                    (e["sid"], e["tag"], e["ip"]) and x.target == e["target"]]
            if not any(x.old == e["old"] and x.new == e["new"] and not x.same for x in hits):
                fail.append(f"{r['label']}: {e['name']} " + (f"rows {[(x.old, x.new, x.same) for x in hits][:2]}"
                                                            if hits else "missing"))
            if r["side"] == "F5B" and not any(R._matches({**e, "off": [e["off"]], "value": [e["value"]]}, k)
                                              for k in r["digest"].keys):
                fail.append(f"{r['label']}: {e['name']} is no member key")
    enough = len(cov["S"]) >= n_min and len(pairs["F5B"]) >= n_min
    out.append((verdict_of(fail, vd, enough, clauses["d"] is True),
                "R5B-ECHO: the consumers of the fixed latches fire as in stock (351 e16 t2 ip105 2078 1 -> 0; 450 e0 "
                "ip338 2086 1 -> 0)",
                "; ".join(fail[:4]) or (f"every covered S and F5B" if enough and clauses["d"] is True else
                                        f"{len(pairs['F5B'])} covered pairs; R5B-CONTROL (d) {WORD[clauses['d']]}")))

    # -- R5B-ARRIVAL -----------------------------------------------------------------------------------------------
    want_arr = {ktuple(k) for k in pred["arrival"]["keys"]}
    fail, vd = [], []
    for r in cov["F5B"]:
        b = burst(r)
        if b is None:
            vd.append(f"{r['label']}: no landing burst")
        elif b != want_arr:
            fail.append(f"{r['label']}: extra {_kshow(b - want_arr)}, missing {_kshow(want_arr - b)}")
    enough = len(cov["F5B"]) >= n_min
    out.append((verdict_of(fail, vd, enough, clauses["c"] is True),
                "R5B-ARRIVAL: the entry's arrival is stock's step-1 arrival, key for key (8 keys + the three 351 SUPP)",
                "; ".join(fail[:3] + vd[:3]) or (f"{len(cov['F5B'])} covered F5B, each exactly the {len(want_arr)} keys"
                                                 if enough and clauses["c"] is True else
                                                 f"{len(cov['F5B'])} covered F5B; R5B-CONTROL (c) "
                                                 f"{WORD[clauses['c']]}")))

    # -- R5B-PARTY --------------------------------------------------------------------------------------------------
    P = pred["party"]
    fail, vd, shown = [], [], []
    prv = None if pr is None else pr.get("verdict")
    if prv is False:
        fail.append(f"P-PARTYREMOVE FAIL: {pr.get('why')}")
    elif prv is None:
        vd.append(f"P-PARTYREMOVE {'not recorded' if pr is None else 'VOID: ' + str(pr.get('why'))[:120]}")
    for side in FORKS:
        sv = ((legs.get(side) or {}).get("save") or {})
        if not (sv.get("ok") and sv.get("slot") == P["hubleg"]):
            vd.append(f"the P-HUBLEG ({side}) autosave baseline is not {P['hubleg']} fresh: {sv.get('why')}")
    at_entry = {"sc": pred["beat"], "entrance": pred["entry"]["entrance"], "field": pred["entry"]["member"]}
    for f, s in pairs["F5B"]:
        fp_, sp = f["rec"].get("party") or {}, s["rec"].get("party") or {}
        reads = {"landing": freshness(fp_.get("landing"), fp_.get("baseline"), at_entry)}
        for lab, r, rd, base in (("F5B end", f, fp_.get("end"), fp_.get("landing")),
                                 ("S end", s, sp.get("end"), sp.get("baseline"))):
            le = last_entry(r["raw"], pred)
            reads[lab] = (freshness(rd, base, le) if le is not None
                          else (False, ["the trace's last field entry is not known"]))
        stale = [f"{lab} ({'; '.join(w)[:100]})" for lab, (ok_, w) in reads.items() if not ok_]
        if stale:
            vd.append(f"{f['label']}/{s['label']}: not fresh: {', '.join(stale)}")
        else:
            slots = (fp_["landing"]["slot"], fp_["end"]["slot"], sp["end"]["slot"])
            if not (slots[0] == slots[1] == slots[2] == P["run_end"]):
                fail.append(f"{f['label']}/{s['label']}: landing {slots[0]}, end {slots[1]}, partner end {slots[2]}")
            shown.append(f"{f['label']} reserve {fp_['end'].get('reserve')} (S {sp['end'].get('reserve')})")
        for r in (f, s):
            fprint = footprint(r["window_rows"], pred)
            if fprint:
                vd.append(f"{r['label']}: party-footprint rows {[(x.fld, x.sid, x.ip, x.target) for x in fprint[:3]]}")
    enough = len(pairs["F5B"]) >= n_min
    out.append((verdict_of(fail, vd, enough, clauses["e"] is True),
                "R5B-PARTY: the party the seed leaves equals stock's post-wake party (Zidane alone), the removes "
                "proven load-bearing",
                _detail(fail[:3] + vd[:4], None if enough else f"{len(pairs['F5B'])} covered pairs (want >= {n_min})",
                        None if clauses["e"] is True else f"R5B-CONTROL (e) {WORD[clauses['e']]}: uncalibrated")
                or f"{len(pairs['F5B'])} pairs, all {P['run_end']}, every read fresh; recorded: {'; '.join(shown)}"))

    # -- the comparison: S post-wake windows vs F5B from its entry ------------------------------------------------
    s_win = [r for r in cov["S"] if r["window"] is not None]
    dig_f = [r["digest"] for r in cov["F5B"]]
    c = T.compare([r["window"] for r in s_win], dig_f, members=members) if s_win and dig_f else None
    reports = {}
    if c is not None:
        reports["rung5b_report_S_vs_F5B.txt"] = T.report(
            c, title=f"story trace F5b: stock Dali's post-wake windows x{len(s_win)} vs the post-wake entry (hub "
                     f"{pred['hubs']['F5B']['id']} + 12 pure members) x{len(dig_f)} (covered runs)", writers=True)
    excused = (set.intersection(*[step1_rule(pred, _partner_walk(f, by_i), *pred["replay"]["F5B"])
                                  for f, _s in pairs["F5B"]]) if pairs["F5B"] else set())

    # -- R5-MIRROR ---------------------------------------------------------------------------------------------------
    M = C["R5-MIRROR"]
    what = ("R5-MIRROR: S's post-wake window vs F5B from its entry -- nothing on one side only but the frozen "
            "excusals (SUPP two-tier, the step-1 keys)")
    if len(s_win) < n_min or len(cov["F5B"]) < n_min or c is None:
        out.append((None, what, f"too few covered runs -- S {len(s_win)}/{n_min}, F5B {len(cov['F5B'])}/{n_min}"))
    else:
        fo = [k for k in c.fork_only if not H5._is_timing(k, pred)]
        so = [k for k in c.stock_only if not H5._is_timing(k, pred)]
        fo_bad, blind = [], []
        for k in fo:
            adm = [supp_ok(pred, k, s, stock) for s in s_win]
            if not all(ok_ for ok_, _w in adm):
                fo_bad.append(k)
            elif supp_tier(pred, k) == "blind":
                blind.append(k)
        so_bad = [k for k in so if ktuple(k) not in excused]
        fail = bool(fo_bad or so_bad or c.across_seam or c.seam_only or c.clobbers)
        common = set.intersection(*[set(r["window"].keys) for r in s_win])
        tl = {r["label"]: R.tour_line(r["rows"], r["digest"], pred, {}) for r in s_win}
        post = {r["label"]: R._first_line(r["rows"], lambda x: x.fld == M["seam_field"]) for r in s_win}
        tour = [k for k in common if all(tl[r["label"]] is not None and r["window"].keys[k].at >= tl[r["label"]]
                                         for r in s_win)]
        p450 = [k for k in common if all(post[r["label"]] is not None and r["window"].keys[k].at >= post[r["label"]]
                                         for r in s_win)]
        thin = []
        if len(common) < M["min_keys"]:
            thin.append(f"{len(common)} keys in every stock window (want >= {M['min_keys']})")
        lack = sorted(set(M["tour_donors"]) - {k.donor for k in tour})
        if len(tour) < M["min_tour_keys"] or lack:
            thin.append(f"{len(tour)} tour keys (want >= {M['min_tour_keys']})"
                        + (f", none from {lack}" if lack else ""))
        lack = sorted(set(M["post_donors"]) - {k.donor for k in p450})
        if len(p450) < M["min_post_keys"] or lack:
            thin.append(f"{len(p450)} keys from 450 on (want >= {M['min_post_keys']})" + (f", none from {lack}"
                                                                                         if lack else ""))
        out.append((False if fail else None if thin else True, what,
                    f"{len(fo)} FORK ONLY ({len(fo) - len(fo_bad)} SUPP-admitted, blind spot "
                    f"{_kshow(map(ktuple, blind), 5)}"
                    f"; not admitted {_kshow(map(ktuple, fo_bad))}); {len(so)} STOCK ONLY ({len(so) - len(so_bad)} "
                    f"step-1 excused; left {_kshow(map(ktuple, so_bad))}); {len(c.across_seam)} ACROSS SEAM; "
                    f"{len(c.seam_only)} SEAM ONLY; {len(c.clobbers)} clobbers || stock guard: {len(common)} keys, "
                    f"{len(tour)} in every tour, {len(p450)} from 450 on"
                    + (f" || the stock guard is thin ({'; '.join(thin)})" if thin else "")))

    # -- R5-PARTIAL ----------------------------------------------------------------------------------------------------
    what = "R5-PARTIAL: THE PAIRED-WALK LAW -- every covered pair writes the same keys modulo the frozen excusals"
    if len(pairs["F5B"]) < n_min:
        out.append((None, what, f"{len(pairs['F5B'])} covered pairs (want >= {n_min})"))
    else:
        fail, within = [], []
        for f, s in pairs["F5B"]:
            if s["window"] is None:
                fail.append(f"{s['label']}: no post-wake window")
                continue
            a, b = keyset5b(f["digest"], pred), keyset5b(s["window"], pred)
            fo = {k for k in a - b if not supp_ok(pred, k, s, stock)[0]}
            so = (b - a) - step1_rule(pred, _partner_walk(f, by_i), *pred["replay"]["F5B"])
            if fo or so:
                fail.append(f"{f['label']}/{s['label']}: F5B only {_kshow(fo, 3)}, S only {_kshow(so, 3)}")
            within.append(a & b)
        order_keys = (set.union(*within) - set.intersection(*within)) if within else set()
        out.append((not fail, what, "; ".join(fail[:4]) or
                    f"{len(pairs['F5B'])} pairs equal modulo the excusals; {len(order_keys)} keys differ between "
                    f"pairs and agree within each (the walk's order, listed) {_kshow(order_keys, 3)}"))

    # -- R5-PING -------------------------------------------------------------------------------------------------------
    p = C["R5-PING"]
    what = "R5-PING: the ping, written by member(450) -- matched, never across a seam; stock WRITERS names only 450"
    if len(s_win) < n_min or len(cov["F5B"]) < n_min or c is None:
        out.append((None, what, f"too few covered runs -- S {len(s_win)}, F5B {len(cov['F5B'])}"))
    else:
        bad = []
        got = dict(T.writers([r["window"] for r in s_win]).get((p["target"], p["value"]), Counter()))
        want = {int(w): len(s_win) for w in p["writers"]}
        if got != want:
            bad.append(f"stock writers {got} (want {want})")
        cmap = {d_: f_ for f_, d_ in members.items()}
        for r in cov["F5B"]:
            d = r["digest"]
            mine = [(k, o) for k, o in d.keys.items() if R._matches(p["pattern"], k)]
            seam = [k for k in d.seam_keys if R._matches(p["pattern"], k)]
            if not mine or seam:
                bad.append(f"{r['label']}: member ping keys {len(mine)}, across a seam {len(seam)}")
            for k, o in mine:
                if o.row.fld != cmap[p["pattern"]["donor"]] or o.row.don != p["pattern"]["donor"]:
                    bad.append(f"{r['label']}: the ping in {o.row.fld} don {o.row.don}")
                if k not in c.matched:
                    bad.append(f"{r['label']}: {H5._show([k])} not MATCHED")
        fw = set(T.writers(dig_f).get((p["target"], p["value"]), Counter()))
        if fw != {p["pattern"]["donor"]}:
            bad.append(f"F5B writers {sorted(fw)}")
        out.append((not bad, what, "; ".join(bad[:4]) or f"stock writers {got}; F5B writers {sorted(fw)}, matched"))

    # -- R5-NOSEAM -----------------------------------------------------------------------------------------------------
    what = "R5-NOSEAM: no seam -- F5B stays inside the members after its entry, 450 entered as member 31112"
    if len(cov["F5B"]) < n_min:
        out.append((None, what, f"too few covered F5B runs -- {len(cov['F5B'])}/{n_min}"))
    else:
        bad = []
        m450 = {d_: f_ for f_, d_ in members.items()}[450]
        for r in cov["F5B"]:
            d = r["digest"]
            if d.seams or d.seam_keys:
                bad.append(f"{r['label']}: seams {[s_.origin + ' -> ' + str(s_.to) for s_ in d.seams][:2]}, "
                           f"{len(d.seam_keys)} seam keys")
            out_rows = sorted({x.fld for x in r["rows"] if x.k in ("w", "r") and x.fld not in members})
            if out_rows:
                bad.append(f"{r['label']}: rows outside the members in {out_rows}")
            if not any(x.fld == m450 and x.don == 450 for x in r["rows"] if x.k == "w"):
                bad.append(f"{r['label']}: 450 never entered as member {m450}")
        if c is not None and (c.across_seam or c.seam_only):
            bad.append(f"ACROSS SEAM {len(c.across_seam)}, SEAM ONLY {len(c.seam_only)}")
        out.append((not bad, what, "; ".join(bad[:4]) or "no seam, no row outside the chain, 450 a member"))

    # -- R5-ADVANCE ----------------------------------------------------------------------------------------------------
    p = C["R5-ADVANCE"]
    what = "R5-ADVANCE: the story advances to 2610 in member(354), matched, on the partner's step minus one"
    if len(pairs["F5B"]) < n_min or c is None:
        out.append((None, what, f"{len(pairs['F5B'])} covered pairs (want >= {n_min})"))
    else:
        bad, at_ = [], []
        cmap = {d_: f_ for f_, d_ in members.items()}
        for f, s in pairs["F5B"]:
            first = next((x for x in f["rows"] if x.k != "c" and x.sc >= p["sc"]), None)
            if first is None:
                bad.append(f"{f['label']}: never reached SC {p['sc']}")
                continue
            o = next((o for k, o in f["digest"].keys.items() if o.row.line == first.line), None)
            k = o.key if o is not None else None
            if (first.k != "w" or first.fld != cmap[p["pattern"]["donor"]] or first.don != p["pattern"]["donor"]
                    or k is None or not R._matches(p["pattern"], k)):
                bad.append(f"{f['label']}: first row at SC >= {p['sc']} is {first.k} in {first.fld} (don {first.don})")
            elif k not in c.matched:
                bad.append(f"{f['label']}: the advance {H5._show([k])} is not MATCHED")
            a_f = H5.adv_point(f["log"]["log"], members, p["sc"])
            a_s = H5.adv_point(s["log"]["log"], {}, p["sc"])
            if a_f != (a_s[0] - pred["replay"]["F5B"][0], a_s[1]):
                bad.append(f"{f['label']}: advanced at step {a_f}, its partner {s['label']} at {a_s} (minus "
                           f"{pred['replay']['F5B'][0]})")
            at_.append(str(a_f))
        out.append((not bad, what, "; ".join(bad[:4]) or f"every covered F5B advanced in member("
                                                         f"{p['pattern']['donor']}) at its partner's step minus one "
                                                         f"{sorted(set(at_))}"))

    # -- R5-LATCH ------------------------------------------------------------------------------------------------------
    p = C["R5-LATCH"]
    what = "R5-LATCH: v3's eight hub-gated writes are written by the members in every covered F5B, as in every S window"
    if len(s_win) < n_min or len(cov["F5B"]) < n_min or c is None:
        out.append((None, what, f"too few covered runs -- S {len(s_win)}, F5B {len(cov['F5B'])}"))
    else:
        bad = []
        for pat in p["patterns"]:
            in_s = all(any(R._matches(pat, k) for k in r["window"].keys) for r in s_win)
            in_f = all(any(R._matches(pat, k) for k in d.keys) for d in dig_f)
            seam = any(R._matches(pat, k) for d in dig_f for k in d.seam_keys)
            if not (in_s and in_f) or seam:
                bad.append(f"{pat['name']}: every stock window {in_s}, every F5B run {in_f}, across a seam {seam}")
        if c.clobbers:
            bad.append(f"clobbers {[(x.key.donor, x.key.target, x.byte, x.old, x.new) for x in c.clobbers][:3]}")
        out.append((not bad, what, "; ".join(bad[:5]) or f"all {len(p['patterns'])} on both sides, no clobber"))

    # -- R5-PREEMPT ----------------------------------------------------------------------------------------------------
    what = ("R5-PREEMPT: PRE-EMPTED is empty and no F5B key is a prepend or unaligned (a consistency check P-PURE "
            "implies)")
    if len(s_win) < n_min or len(cov["F5B"]) < n_min or c is None:
        out.append((None, what, f"too few covered runs -- S {len(s_win)}, F5B {len(cov['F5B'])}"))
    else:
        pre = [k for d in dig_f for k in (*d.keys, *d.seam_keys) if k.off < 0 or not k.aligned]
        out.append((not c.pre_empted and not pre, what,
                    f"PRE-EMPTED {[(x.target, x.value) for x in c.pre_empted][:4]}; prepend/unaligned "
                    f"{H5._show(set(pre), 4)}"))

    # -- NC-THROW (as the session recorded it) -------------------------------------------------------------------------
    nc = session.get("nc_throw")
    out.append((None if nc is None else bool(nc.get("ok")),
                "NC-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent from the "
                "mark",
                "the session recorded none" if nc is None else str(nc.get("detail"))[:300]))

    # -- THE VERDICT ---------------------------------------------------------------------------------------------------
    v_ok, v_text = verdict5b(out, clauses, f5b_pairs=len(pairs["F5B"]), ctl_covered=len(pairs["CTL"]), pred=pred)
    out.append((v_ok, "VERDICT: the frozen rule (PROVEN / NOT PROVEN: <half> / FAILED: <check>)", v_text))

    # -- the summary ---------------------------------------------------------------------------------------------------
    lines = [f"story trace F5b (the post-wake entry) -- session {session.get('label')} ({session.get('started')} .. "
             f"{session.get('finished', 'unfinished')}); predictions {pred_path.name} (lane {pred.get('lane')} "
             f"v{pred.get('version')})" + (f"; re-runs stopped: {session['rerun_stop']}"
                                           if session.get("rerun_stop") else ""), "", f"VERDICT: {v_text}", ""]
    for r in runs:
        rec = r["rec"]
        lines.append(f"  {r['label']:<7} {rec.get('t0', '?')}..{rec.get('t1', '?')}s  "
                     f"{'VOID' if r['why_void'] else 'covered'}{' (re-run)' if rec.get('rerun') else ''}  "
                     f"stop: {rec.get('stop', rec.get('skipped', rec.get('install', '?')))}"
                     + (f"  [phase {rec.get('phase')}]" if r["why_void"] and rec.get("phase") else ""))
        if r["why_void"]:
            lines.append(f"          VOID [{cls_text(r) or '-'}]: {'; '.join(r['why_void'])}")
        if r["side"] in FORKS:
            walk = _partner_walk(r, by_i)
            lo, hi = pred["replay"][r["side"]]
            got = D.entered_walk(r["log"]["log"], members, legs=("replay",)) if r["log"] is not None else None
            lines.append(f"          partner: S#{rec.get('partner')}"
                         + (f"; replayed {len(got)} of its walk[{lo}:{'' if hi is None else hi}] "
                            f"({len(walk[lo:hi])} steps)" if got is not None and walk is not None else "")
                         + f"; hub rows {len(H5.hub_rows(r, hub_view(pred, r['side'])))}")
        party = rec.get("party") or {}
        if party:
            lines.append("          autosave: " + "; ".join(f"{k} {v.get('slot')} sc {v.get('sc')} e{v.get('entrance')}"
                                                            f" {'fresh' if v.get('fresh') else 'stale'}"
                                                            for k, v in party.items() if isinstance(v, dict)))
    lines += ["", "CHECKS"] + [f"  {WORD[ok]}  {what}\n        {detail}" for ok, what, detail in out]
    reports["rung5b_summary.txt"] = "\n".join(lines) + "\n"
    return out, reports


# ======================================================================== the session (in game)
def run(g) -> None:
    """The F5b session (design 4.9): the static pre-flight, P-HUBLEG 31113 then 31114, P-PARTYREMOVE, NC-THROW's
    mark, then [S, F5B, CTL] x 3 and the re-runs :func:`rerun_plan5b` names, then the analysis and THE VERDICT --
    rung5_hub.run (rung5_hub.py:1471-1703) over three sides and two hubs."""
    from harness import HarnessError

    cap = g.state.storytrace
    if not g.check(isinstance(cap, dict) and cap.get("proto") == T.PROTO,
                   "P-CAP: the engine advertises the story trace at proto 1", str(cap)):
        return
    pred, sha = load_predictions()
    holes = missing_numbers(pred)
    if not g.check(pred.get("lane") == "F5b" and not holes, "the predictions are F5b's, frozen whole",
                   f"lane {pred.get('lane')}; holes {holes}"):
        return
    b, wk = pred["budget"], pred["wake"]
    members = chain(pred)
    every = {**members, **{pred["hubs"][s]["id"]: pred["hubs"][s]["id"] for s in FORKS}}
    stock = T.stock_script_source()
    roots = D.mod_roots()
    ran = T.mod_script_source(roots, fallback=stock)
    side_tours = tours5b(pred, ran=ran, stock=stock)
    pre = preflight5b(pred, roots, stock, H5.tours5(pred, ran=ran, stock=stock), ran=T.mod_script_source(roots))
    for ok, what, detail in pre:
        g.check(ok, what, detail)
    if not all(ok for ok, _w, _d in pre):
        return
    fp0 = R.fingerprint(roots, every)
    scripts = g.run_dir / "scripts"
    scripts.mkdir(exist_ok=True)
    for fid in sorted(every):
        (scripts / f"{fid}.eb").write_bytes(ran(fid).data)
    session = {"label": g.run_dir.name, "predictions": str(PREDICTIONS), "predictions_sha256": sha,
               "predictions_version": pred.get("version"), "lane": pred.get("lane"), "order": pred["order"],
               "budget": b, "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "install": fp0,
               "preflight": [[ok, what, detail] for ok, what, detail in pre], "ini": ini_check()[2],
               "hubleg": {}, "runs": []}

    def save() -> None:
        (g.run_dir / SESSION_FILE).write_text(json.dumps(session, indent=1), encoding="utf-8")

    save()
    for side in FORKS:
        view = hub_view(pred, side)
        ok, detail, leg = hubleg5b(g, view)                # the first leg's verdict; the retry is the clause's alone
        session["hubleg"][side] = dict(leg, ok=ok, detail=detail)
        save()
        if not g.check(ok, f"P-HUBLEG ({side}): in game, untraced, the hub leg reaches the menu, the stay row "
                           f"stays, and the hub throws nothing", detail):
            return
        g.check(bool(leg["save"]["ok"]), f"P-HUBLEG ({side}) autosave: the hub arrival reads the New Game baseline, "
                                         f"fresh (non-blocking: twice failed only VOIDs R5B-PARTY)",
                "; ".join(leg["save"].get("why") or []) or str(leg["save"].get("slot")))
    ok_pr, detail_pr, pr = p_partyremove(g, pred)
    session["partyremove"] = pr
    save()
    g.check(ok_pr is True, "P-PARTYREMOVE: in game, untraced, the F5B pick's removes act on a real roster "
                           "(non-blocking: R5B-PARTY reads it)", ("VOID -- " if ok_pr is None else "") + detail_pr)
    mark = g.log_mark()                   # NC-THROW's mark: after both P-HUBLEGs and P-PARTYREMOVE
    t0 = time.time()
    deadline = t0 + b["session_s"]

    def partner_walk(k):
        """``(walk, why not)`` for a fork run partnering stock run ``k``, judged by the frozen coverage rule."""
        if k is None:
            return None, "no stock run before it to partner"
        try:
            got = {r["i"]: r for r in read_session5b(g.run_dir, pred, stock=stock, roots=roots, session=session)}
            p = got.get(k)
            if p is None or p["side"] != "S":
                return None, f"its partner #{k} is not a recorded stock run"
            if p["why_void"]:
                return None, f"partner S#{k} VOID: {'; '.join(p['why_void'])[:200]}"
            return D.entered_walk(p["log"]["log"]), None
        except Exception as err:                  # noqa: BLE001 -- one unreadable record must not end the session
            return None, f"partner S#{k} unreadable: {type(err).__name__}: {str(err)[:200]}"

    def one(i: int, side: str, rerun: bool = False, partner: int | None = None) -> None:
        """One run -- rung5_hub.run's one() (rung5_hub.py:1530-1667) for S / F5B / CTL."""
        tour = side_tours[side]
        trace_name, log_name = R.run_names(i, side)
        rec = {"i": i, "side": side, "start": pred["start"][side], "trace": trace_name, "log": log_name}
        if rerun:
            rec["rerun"] = True
        walk = None
        if side in FORKS:
            rec["partner"] = partner if rerun else R.round_partner(pred["order"], i)
            walk, why = partner_walk(rec["partner"])
            if walk is None:
                rec["skipped"] = why
            else:
                rec["walk"] = walk
                gate = walk_gate(pred, side, walk)
                if gate:
                    rec["skipped"] = gate
                else:
                    rec["slice"] = list(pred["replay"][side])
        need = b["run_min_s"][side] if isinstance(b["run_min_s"], dict) else b["run_min_s"]
        if not rec.get("skipped"):
            if time.time() + need > deadline:
                rec["skipped"] = f"session budget: under {need}s of the {b['session_s']}s left"
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
        reads: dict = {}
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

        def read(name, baseline=None, want=None):
            try:
                reads[name] = party_read(g, baseline, want, frames=b.get("save_frames"))
            except HarnessError as err:
                reads[name] = {"error": f"the read raised: {str(err)[:200]}", "fresh": False, "why": [str(err)[:200]]}
            log.append({"k": "autosave", "name": name, **{k: reads[name].get(k) for k in
                                                          ("slot", "sc", "entrance", "field", "fresh", "why")}})
            return reads[name]

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

            tour_kw = dict(beat=pred["beat"], max_crossings=b["max_crossings"], max_passes=b["max_passes"],
                           budget_s=b["tour_s"], deadline=deadline, engine_donor=engine_donor)
            if side == "S":
                phase("segment")
                seg = D.segment(g, log, start=pred["start"]["S"], sc=pred["start_sc"], beat=pred["beat"],
                                place=tour.place, until=pred["segment_place"], timeout=b["segment_s"], woke=woke)
                rec["segment"] = seg
                tour.say(f"run {i} (S) segment: {json.dumps(seg)}")
                if seg["ok"]:
                    read("baseline")
                    phase("tour")
                    stop = tour.run(g, log, **tour_kw)
                else:
                    stop = f"segment: no control in {pred['segment_place']} at {pred['beat']} after the wake"
            else:
                view = hub_view(pred, side)
                read("baseline")
                rec["landing"] = enter_past(g, log, view, place=tour.place, woke=woke, phase=phase)
                read("landing", reads["baseline"], {"sc": pred["beat"], "entrance": view["hub"]["entrance"],
                                                    "field": view["hub"]["entry"]})
                lo, hi = pred["replay"][side]
                phase("replay")
                stop = tour.replay(g, log, walk[lo:hi], **tour_kw)
            if side == "F5B" or (side == "S" and rec.get("segment", {}).get("ok")) or side == "CTL":
                phase("settle")
                try:
                    D.settle(g, log, "after the tour", tour.say)
                except HarnessError as err:
                    rec["settle_error"] = str(err)[:300]
                if side == "S":
                    read("end", reads.get("baseline"))
                else:                             # CTL's is recorded, never judged (design 4.5's table)
                    read("end", reads.get("landing"))
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
                       fields=sorted({x["now"] for x in crossings if x.get("now")}), party=reads)
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
            runs = read_session5b(g.run_dir, pred, stock=stock, roots=roots, session=session)
            plan = rerun_plan5b(runs, pred)
        except Exception as err:                  # noqa: BLE001 -- the nine are kept and analysed all the same
            session["rerun_stop"] = (f"the runs could not be read to plan a re-run: {type(err).__name__}: "
                                     f"{str(err)[:200]}")
            side_tours["S"].say(f"!! re-runs stopped: {traceback.format_exc()[-1500:]}")
            break
        if plan is None:
            if halted5b(runs):
                session["rerun_stop"] = (f"HALTED: two F5B runs FORK-STOPped at {halted5b(runs)} -- R5-REACH's FAIL "
                                         f"is decided and no run can change it")
            break
        need = b["run_min_s"][plan[0]] if isinstance(b["run_min_s"], dict) else b["run_min_s"]
        if time.time() + need > deadline:
            session["rerun_stop"] = (f"sides {short_sides5b(runs, pred)} still short of covered runs, and no run "
                                     f"fits the budget left")
            break
        reruns += 1
        one(len(session["runs"]) + 1, plan[0], rerun=True, partner=plan[1])
    ours = [e for e in g.exceptions_since(mark) if e.name in THROWS
            and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    session["nc_throw"] = {"ok": not ours, "detail": str([(e.name, e.where) for e in ours[:5]])}
    session["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    checks, reports = analyse5b(g.run_dir, stock=stock, roots=roots)
    for name, text in reports.items():
        (g.run_dir / name).write_text(text, encoding="utf-8")
    print(reports.get("rung5b_summary.txt", "")[:4000], flush=True)
    for ok, what, detail in checks:
        g.check(ok is True, what, ("VOID -- " if ok is None else "") + detail)


# ======================================================================== the CLI (offline)
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="F5b's offline modes: the analysis, the live pre-flight, a build's check.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--analyse", metavar="RUN_DIR", help="a session's run directory")
    mode.add_argument("--preflight", action="store_true", help="the static P-checks on the live install")
    mode.add_argument("--offline-check", metavar="BUILD_DIR", nargs="?", const="",
                      help="P-HUB, P-PARTYOPS, P-ENTRY and P-PINS on an offline build (<BUILD_DIR>/<id>/ per hub; "
                           "none: build both hubs from their frozen tomls into a temp dir)")
    ap.add_argument("--predictions", metavar="FILE", default=None,
                    help="read these predictions instead of the file the session recorded / the frozen v1")
    a = ap.parse_args(argv)
    if a.analyse:
        try:
            checks, reports = analyse5b(a.analyse, pred_path=None if a.predictions is None else Path(a.predictions))
        except NotF5B as err:
            print(f"REFUSED: {err}", file=sys.stderr)
            return 2
        for name, text in reports.items():
            (Path(a.analyse) / name).write_text(text, encoding="utf-8")
        print(reports["rung5b_summary.txt"])
        return 0 if checks[-1][0] is True else 1
    path = Path(a.predictions) if a.predictions else PREDICTIONS
    if not path.is_file():
        print(f"REFUSED: no predictions file {path} (rung5b_dryrun.py freezes it; --predictions names another)",
              file=sys.stderr)
        return 2
    pred, _sha = load_predictions(path)
    holes = missing_numbers(pred) if pred.get("lane") == "F5b" else ["anything: these are not F5b's predictions"]
    if holes:
        print(f"REFUSED: the predictions freeze no {', '.join(holes)}", file=sys.stderr)
        return 2
    stock = T.stock_script_source()
    if a.preflight:
        roots = D.mod_roots()
        ran = T.mod_script_source(roots, fallback=stock)
        checks = preflight5b(pred, roots, stock, H5.tours5(pred, ran=ran, stock=stock), ran=T.mod_script_source(roots))
    else:
        checks = offline_check5b(pred, Path(a.offline_check) if a.offline_check else None, stock)
    for ok, what, detail in checks:
        print(f"  {WORD[ok]}  {what}\n        {detail}")
    return 0 if all(ok is True for ok, _w, _d in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
