"""RUNG 3'S ANALYSIS, DRY-RUN OFFLINE -- every check of rung3_trace.analyse shown able to PASS, to FAIL, and to go
VOID, before the in-game session, on real rows.

    py studies/story-trace/rung3_dryrun.py [--keep DIR]

The stock side is rung 3 step 1's REAL run (ff9mapkit/tests/fixtures/story_rung3s1_dali.jsonl: the unattended
blind tour of stock Dali, archived), used for all three stock runs. The fork sides are CONSTRUCTED from it, as the
engine would write them for the deployed chains (rung3_forks.json -- the analysis joins them against the members'
real deployed .eb):
  F0  the stock rows relabelled into the F0 member ids up to the first row in 450; from there the real game's, row
      for row (member(350)'s exit leads to the real 450, and the real 450's back to the real 350).
  F4  the same into the F4 ids, plus the round-4 seed: at each member's first visit its prepend's stores (read off
      the member's deployed Main_Init; old values from the bytes as the rows leave them, so byte 297 holds the 1
      359 wrote when the 351 member's word lands), every row of its entry 0 from Main_Init on moved down by the
      prepend, the hub-gated writes the frozen predictions list removed, and the run ending at the controller's
      flip (the story never moves on).
Each run's log is built the way the session writes one: the segment record, and one cross record per crossing --
step 1's 27 for S and F0 (the story moved on at the 27th), 45 for F4 (three passes, never moving on).
Then MUTANTS, one per way the world could differ -- each must come out as its registered verdict: FAIL where the
world falsifies a prediction, VOID where the DRIVE failed (a walker, a budget, the install) and the run says
nothing either way -- and CASES that must still PASS (a VOID run re-run; New Game's rows before the start field).
And the PRE-FLIGHT on the live install, with a mutant chain whose member exits into the OTHER chain.

This proves the ANALYSIS, not the prediction: the base construction encodes the predicted defects, so it passing
says only that the checks read what they claim to. The session decides the prediction.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dali_tour as D  # noqa: E402
import rung3_trace as R  # noqa: E402
from dali_tour import T  # noqa: E402
from ff9mapkit import eventscan  # noqa: E402
from ff9mapkit.eb._exprtable import VAR_TYPE  # noqa: E402

FIXTURE = HERE.parents[1] / "ff9mapkit" / "tests" / "fixtures" / "story_rung3s1_dali.jsonl"
SITE = ("fld", "m", "src", "sid", "tag", "ip", "byte", "w", "bit")
WORD = {True: "PASS", False: "FAIL", None: "VOID"}


def site(o: dict) -> tuple:
    return tuple(o.get(k) for k in SITE)


def relabel(objs: list, members: dict, *, until: int | None = 450) -> list:
    """The stock rows as a verbatim chain would have the engine write them: a row in a member's donor field runs
    in the member (``fld`` the fork id, ``don`` still the donor -- ForkDonorPatch), up to the first row in
    ``until``; from there the real game's. A count row follows its site."""
    fork_of = {d: f for f, d in members.items()}
    cut = next((i for i, o in enumerate(objs) if o["fld"] == until and o["k"] != "c"), len(objs))
    moved, out = set(), []
    for i, o in enumerate(objs):
        o = dict(o)
        if (o["k"] == "c" and site(o) in moved) or (o["k"] != "c" and i < cut and o["fld"] in fork_of):
            if o["k"] == "w":
                moved.add(site(o))
            o["fld"] = fork_of[o["fld"]]
        out.append(o)
    return out


class Bytes:
    """gEventGlobal as the rows leave it -- for the old value of a store the construction inserts."""

    def __init__(self):
        self.b = bytearray(T.STORY_LEN)

    def read(self, byte: int, width: str, bit: int) -> int:
        if width in T.BIT_WIDTHS:
            return (self.b[bit >> 3] >> (bit & 7)) & 1
        n = T.WIDTH_BYTES[width]
        v = int.from_bytes(self.b[byte:byte + n], "little")
        return v - (1 << 8 * n) if width in ("SByte", "Int16", "Int24") and v >= 1 << (8 * n - 1) else v

    def write(self, byte: int, width: str, bit: int, value: int) -> None:
        if width in T.BIT_WIDTHS:
            self.b[bit >> 3] = (self.b[bit >> 3] & ~(1 << (bit & 7))) | ((value & 1) << (bit & 7))
            return
        n = T.WIDTH_BYTES[width]
        self.b[byte:byte + n] = (value & ((1 << 8 * n) - 1)).to_bytes(n, "little")

    def apply(self, o: dict) -> None:
        if o["k"] == "w":
            self.write(o["byte"], o["w"], o["bit"], o["new"])
        elif o["k"] == "r":
            self.b[o["byte"]] = o["new"] & 0xFF


def stock_key(o: dict, stock):
    """The WriteKey a STOCK row keys to (its field's own bytes), or None off the field join."""
    if o["k"] != "w" or o["src"] != "eb" or o["add"] or o["m"] != 1:
        return None
    idx = stock(o["fld"])
    j = idx.join(T.parse_row(o), donor=o["don"]) if idx is not None else None
    if j is None or not j.ok:
        return None
    r = T.parse_row(o)
    return T.WriteKey(o["don"], 1, "eb", o["sid"], o["tag"], j.rel, r.target, o["new"])


def prepends(members: dict, ran, stock, *, word_296: bool = True) -> dict:
    """``{fork id: (main_ip, delta, [(ip, width, byte, bit, value)])}``: where the member's Main_Init starts
    (entry-relative), how long its prepend is, and the prepend's stores -- read off the member's DEPLOYED bytes
    against its donor's. ``word_296`` False writes 296 as the byte it is (the corrected seed)."""
    import re
    out = {}
    for fid, donor in members.items():
        si, base = ran(fid), stock(donor)
        e0 = si.eb.entries[0]
        main = e0.func_by_tag(0)
        delta = T.align_function(si, base, 0, 0)
        stores = []
        for ins in si.instrs(main.abs_start, main.abs_start + delta):
            glob = [s for s in T.instruction_stores(si.data, ins) if s[0] == "global"]
            if not glob:
                continue                                 # the [party] adds: Map-source, never a trace row
            [(_src, vt, idx)] = glob
            width = VAR_TYPE[vt]
            if (width, idx) == ("UInt16", 296) and not word_296:
                width = "SByte"
            value = int(re.search(r"const\((\d+)\)", si.text_at(main.abs_start, si._end(e0, main),
                                                                 ins.off - main.abs_start)).group(1))
            if width == "SByte" and value > 127:
                value -= 256                             # 192 as the byte: -64, the controller's own reset value
            bit = idx if width in T.BIT_WIDTHS else -1
            stores.append((ins.off - e0.abs_start, width, idx >> 3 if bit >= 0 else idx, bit, value))
        out[fid] = (main.abs_start - e0.abs_start, delta, stores)
    return out


def seed(objs: list, members: dict, ran, stock, pred: dict, *, drop_gated: bool = True, cut_flip: bool = True,
         shift: bool = True, word_296: bool = True, latches: bool = True) -> list:
    """F4 as the engine would write it (the module docstring): the relabelled rows + each member's prepend at its
    first visit, entry 0 from Main_Init on moved down by it, the hub-gated writes dropped, the run ended at the
    controller's flip. Each switch off is a mutant (``latches`` False: the prepend stamps no latch -- round 5)."""
    pats = pred["checks"]["R3-LATCH"]["stock_only"]
    flip = next(p for p in pats if p["target"] == "Global.Bit[2079]")
    info = prepends(members, ran, stock, word_296=word_296)
    mem = Bytes()
    out, seen, ended = [], set(), False
    for orig, o in zip(objs, relabel(objs, members)):
        if ended and o["k"] in ("w", "r"):
            continue
        key = stock_key(orig, stock)
        if key is not None and cut_flip and R._matches(flip, key):
            ended = True
            continue
        if key is not None and drop_gated and any(R._matches(p, key) for p in pats):
            continue
        if shift and o["k"] in ("w", "c") and o["fld"] in members and o["sid"] == 0:
            main_ip, delta, _stores = info[o["fld"]]
            if o["ip"] >= main_ip:                       # a count row's site moves with its rows
                o = dict(o, ip=o["ip"] + delta)
        if o["k"] in ("w", "r") and o["fld"] in members and o["fld"] not in seen:
            seen.add(o["fld"])
            for ip, width, byte, bit, value in info[o["fld"]][2]:
                if not latches and width in T.BIT_WIDTHS:
                    continue
                old = mem.read(byte, width, bit)
                w = {"k": "w", "f": o["f"], "p": o["p"], "m": 1, "fld": o["fld"], "don": members[o["fld"]],
                     "sc": o["sc"], "src": "eb", "sid": 0, "uid": 0, "lvl": 0, "ip": ip, "tag": 0, "add": 0,
                     "byte": byte, "w": width, "bit": bit, "old": old, "new": value, "same": int(old == value)}
                mem.apply(w)
                out.append(w)
        if o["k"] in ("w", "r"):
            mem.apply(o)
        if ended and o["k"] in ("c", "e"):
            o = dict(o, sc=pred["beat"])                 # flushed at 2600: the story never moved on
        out.append(o)
    live = {site(o) for o in out if o["k"] == "w"}
    return [o for o in out if o["k"] != "c" or site(o) in live]    # a count whose rows were all dropped goes too


def drop_rows(rows, pred) -> list:
    """``rows`` without every w/r row ``pred(index, row)`` names -- and a count whose site lost its rows."""
    keep = [o for i, o in enumerate(rows) if not (o["k"] in ("w", "r") and pred(i, o))]
    live = {site(o) for o in keep if o["k"] == "w"}
    return [o for o in keep if o["k"] != "c" or site(o) in live]


def tour_log(pred: dict, *, crossings: int, moved_at: int | None, stop: str, seg: dict | None = None) -> dict:
    """A run's log as the session writes one: the segment record, then one cross record per crossing (SC settled
    at the advance on crossing ``moved_at``, else at the beat throughout)."""
    seg = seg or {"k": "segment", "field": 352, "place": pred["segment_place"], "sc": pred["beat"], "control": True,
                  "woke": True, "ok": True, "at_beat": True}
    adv = pred["coverage"]["advanced_sc"]
    cross = [{"k": "cross", "n": n, "sc0": pred["beat"], "sc1": adv if n == moved_at else pred["beat"],
              "verdict": "crossed"} for n in range(1, crossings + 1)]
    return {"stop": stop, "choices": [], "log": [seg, *cross]}


def write_session(d: Path, pred_path: Path, plan: list, *, sha: str | None = None, snap: dict | None = None) -> None:
    """A session dir as rung3_trace.run leaves one: ``plan`` = ``[{side, rows, log, rec}]`` in run order (a
    ``rec`` field ``rerun``/``install``/``skipped`` as the session records it), the session record, the scripts."""
    pred, real_sha = R.load_predictions(pred_path)
    if d.exists():
        shutil.rmtree(d)
    (d / "scripts").mkdir(parents=True)
    for fid, data in (snap or {}).items():
        (d / "scripts" / f"{fid}.eb").write_bytes(data)
    recs = []
    for i, run in enumerate(plan, 1):
        tn, ln = R.run_names(i, run["side"])
        rec = {"i": i, "side": run["side"], "trace": tn, "log": ln, "t0": 0, "t1": 0, **run.get("rec", {})}
        if not (rec.get("skipped") or rec.get("install", "").startswith("before")):
            (d / tn).write_text("".join(json.dumps(o, separators=(",", ":")) + "\n" for o in run["rows"]),
                                encoding="utf-8")
            (d / ln).write_text(json.dumps(run["log"]), encoding="utf-8")
            rec.setdefault("stop", run["log"]["stop"])
        recs.append(rec)
    (d / R.SESSION_FILE).write_text(json.dumps({"label": d.name, "predictions_sha256": sha or real_sha,
                                                "order": pred["order"], "runs": recs}), encoding="utf-8")


def store_row(ran, fid: int, like: dict) -> dict:
    """A `w` row for the first story store in field ``fid``'s Main_Init (a real store of its bytes), as the engine
    would write it -- the rows a run leaves in a field it passed through before its start (New Game's hub)."""
    si = ran(fid)
    e0 = si.eb.entries[0]
    main = e0.func_by_tag(0)
    for ins in si.instrs(main.abs_start, si._end(e0, main)):
        for _src, vt, idx in (s for s in T.instruction_stores(si.data, ins) if s[0] == "global"):
            width = VAR_TYPE[vt]
            bit = idx if width in T.BIT_WIDTHS else -1
            row = {"k": "w", **{k: like[k] for k in ("f", "p", "sc")}, "m": 1, "fld": fid, "don": fid, "src": "eb",
                   "sid": 0, "uid": 0, "lvl": 0, "ip": ins.off - e0.abs_start, "tag": 0, "add": 0,
                   "byte": idx >> 3 if bit >= 0 else idx, "w": width, "bit": bit, "old": 0, "new": 1, "same": 0}
            if not T.noise_regions(T.parse_row(row)):
                return row
    raise LookupError(f"field {fid}'s Main_Init stores no story variable")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", help="write the constructed sessions here (default: a temp dir, removed)")
    a = ap.parse_args(argv)
    pred, _sha = R.load_predictions()
    chains = R.chain_members(pred)
    stock = T.stock_script_source()
    roots = D.mod_roots()
    ran = T.mod_script_source(roots, fallback=stock)
    snap = {f: ran(f).data for m in chains.values() for f in m}
    objs = [json.loads(ln) for ln in FIXTURE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    f0 = relabel(objs, chains["F0"])
    f4 = seed(objs, chains["F4"], ran, stock, pred)
    moved = "SC left 2600: now 2610 in field 354 (pass 2, crossing 27)"
    logs = {"S": tour_log(pred, crossings=27, moved_at=27, stop=moved),
            "F0": tour_log(pred, crossings=27, moved_at=27, stop=moved),
            "F4": tour_log(pred, crossings=45, moved_at=None, stop="passes exhausted (3) without the story moving on")}
    base_rows = {"S": objs, "F0": f0, "F4": f4}
    root = Path(a.keep) if a.keep else Path(tempfile.mkdtemp(prefix="rung3dry-"))
    root.mkdir(parents=True, exist_ok=True)

    def case(name: str, runs=None, *, logs_=None, recs=None, extra=(), **kw):
        """One constructed session: the base nine with ``runs``/``logs_``/``recs`` overriding slot i, then
        ``extra`` re-runs ``[(side, rows)]``."""
        plan = [{"side": s, "rows": (runs or {}).get(i, base_rows[s]), "log": (logs_ or {}).get(i, logs[s]),
                 "rec": (recs or {}).get(i, {})} for i, s in enumerate(pred["order"], 1)]
        plan += [{"side": s, "rows": rows, "log": logs[s], "rec": {"rerun": True}} for s, rows in extra]
        d = root / name
        kw.setdefault("snap", snap)
        write_session(d, R.PREDICTIONS, plan, **kw)
        checks, reports = R.analyse(d, stock=stock, roots=roots)
        return {what.split(":")[0]: (WORD[ok], detail) for ok, what, detail in checks}, reports

    results = {}
    got, reports = case("base")
    results["base"] = got
    print("== BASE (S = the real step-1 run x3; F0 / F4 constructed for the deployed chains)")
    for k, (st, detail) in got.items():
        print(f"  {st}  {k:<12} {detail[:300]}")
    rep0 = reports.get("rung3_report_S_vs_F0.txt", "")
    retro = "  Global.Bit[2102] := 1 <- {450}   -- no member's donor writes it\n"
    print(f"  the F0 report's WRITERS mark the ping as written only outside the members: {retro in rep0}")
    rep4 = reports.get("rung3_report_S_vs_F4.txt", "")
    print("  the F4 report's PRE-EMPTED section:\n    " + "\n    ".join(
        ln for ln in rep4.split("\nPRE-EMPTED")[1].split("\n\n")[0].splitlines()[:6]) if "\nPRE-EMPTED" in rep4
          else "  !! the F4 report has no PRE-EMPTED section")
    if a.keep:
        for name, text in reports.items():
            (root / "base" / name).write_text(text, encoding="utf-8")

    def drop_off(rows):
        return [o for o in rows if not (o["k"] == "e" and o["why"] == "off") and o["k"] != "c"]

    def no_donor(rows):
        return [dict(o, don=o["fld"]) if o["fld"] in chains["F0"] else o for o in rows]

    def stop_log(side, stop, crossings=None):
        lg = copy.deepcopy(logs[side])
        lg["stop"] = stop
        if crossings is not None:
            lg["log"] = lg["log"][:1 + crossings]
        return lg

    place = lambda o, m: m.get(o["fld"], o["fld"])         # noqa: E731
    first = lambda rows, p: next(i for i, o in enumerate(rows) if o["k"] != "c" and p(o))   # noqa: E731
    wake = pred["wake"]

    def is_wake(o, members):
        return (o["k"] == "w" and place(o, members) == wake["donor"] and o["sid"] == wake["sid"]
                and o["tag"] == wake["tag"] and o["w"] == "UInt16" and o["byte"] == 0 and o["new"] in wake["value"])

    ping = lambda i, o: o["k"] == "w" and o["w"] == "Bit" and o["bit"] == 2102 and o["new"] == 1    # noqa: E731
    # a story write (a key, not story noise) member(355) makes before the seam, and every row of its site
    sd = T.digest("S", T.read_trace(FIXTURE), scripts=stock)
    row = next(o.row for k, o in sd.keys.items() if k.donor == 355 and o.row.src == "eb")
    pre_site = (next(f for f, d in chains["F0"].items() if d == 355), row.m, row.src, row.sid, row.tag, row.ip,
                row.byte, row.width, row.bit)
    f0_missing = drop_rows(f0, lambda i, o: o["k"] == "w" and site(o) == pre_site)
    forked_450 = [dict(o, fld=30899) if o["fld"] == 450 else o for o in f0]    # a chain that HAD forked 450
    extra = copy.deepcopy(f0)
    j = next(i for i, o in enumerate(extra) if o["k"] == "w" and o["fld"] == 30833 and o["w"] == "Int16")
    extra.insert(j + 1, dict(extra[j], new=extra[j]["new"] + 7, old=extra[j]["new"], same=0))
    no_gate = seed(objs, chains["F4"], ran, stock, pred, drop_gated=False, cut_flip=False)
    corrected = seed(objs, chains["F4"], ran, stock, pred, word_296=False)
    word = bytes.fromhex("05fc28017dc0002c7f")               # the prepend's SET(Global.UInt16[296] := 192)
    snap_corr = dict(snap)
    for fid in chains["F4"]:
        at = snap[fid].find(word)
        if at >= 0:                                             # the same store as Global.SByte[296] (token 0xD0)
            snap_corr[fid] = snap[fid][:at + 1] + bytes([0xD0]) + snap[fid][at + 2:]
    cut4 = first(f4, lambda o: o["fld"] == 450)
    before_450 = drop_rows(f4, lambda i, o: i >= cut4)
    unshifted = seed(objs, chains["F4"], ran, stock, pred, shift=False)
    bad_seg = {"k": "segment", "field": 30843, "place": 312, "sc": 2600, "control": True, "woke": True, "ok": False,
               "at_beat": True}
    # the tour window: from the first row after the wake outside 352 to the first row in 450
    wk = first(objs, lambda o: is_wake(o, {}))
    tw0 = first(objs[wk:], lambda o: place(o, {}) != wake["donor"]) + wk
    tw1 = first(objs, lambda o: o["fld"] == 450)
    # the tour as if 350's other exits had gone dead: 352 -> 351 (its lobby exit) -> 350 (its door) -> 450 --
    # every row of the window dropped but 351's and 350's LAST visit before 450
    door = max(i for i in range(tw0, tw1) if objs[i]["k"] != "c" and objs[i]["fld"] == 350
               and objs[i - 1]["fld"] != 350)
    no_tour_s = drop_rows(objs, lambda i, o: tw0 <= i < door and o["fld"] != 351)
    no_tour_f0 = drop_rows(f0, lambda i, o: tw0 <= i < door and place(o, chains["F0"]) != 351)
    no_450 = drop_rows(objs, lambda i, o: o["fld"] == 450)
    no_e19_f4 = drop_rows(f4, lambda i, o: o["fld"] == 450 and o.get("sid") == 19)
    no_wake_f4 = drop_rows(f4, lambda i, o: is_wake(o, chains["F4"]))
    no_latch = seed(objs, chains["F4"], ran, stock, pred, latches=False)
    no_2064 = drop_rows(objs, lambda i, o: o["k"] == "w" and o["fld"] == 351 and o["w"] == "Bit" and o["bit"] == 2064)
    # a post-seam story write the real game makes once, in every stock run: gone from every F0 run
    keep = [pred["coverage"]["flip"], *pred["coverage"]["ran"], wake]              # what coverage reads
    post = next(o.row for k, o in sorted(sd.keys.items(), key=lambda ko: ko[1].at)
                if o.at > tw1 + 1 and o.row.fld != 450 and o.row.src == "eb" and not o.counted
                and k.target != "Global.UInt16[0]" and not any(R._matches(p, k) for p in keep)
                and sum(1 for x in objs if x["k"] == "w" and site(x) == o.row.site) == 1)
    f0_post = drop_rows(f0, lambda i, o: o["k"] == "w" and site(o) == post.site)
    hub = store_row(ran, 4600, objs[1])
    with_hub = [objs[0], hub, *objs[1:]]
    with_hub_f0 = [f0[0], hub, *f0[1:]]
    F4 = [i for i, s in enumerate(pred["order"], 1) if s == "F4"]
    F0 = [i for i, s in enumerate(pred["order"], 1) if s == "F0"]
    S_ = [i for i, s in enumerate(pred["order"], 1) if s == "S"]
    stopped = stop_log("F4", "STOPPED: HarnessError: watch_cutscene timed out after 240s")
    mutants = [
        ("R3-RUNS", "VOID", "F0 run 5 has no `off` (the tracer faulted)", dict(runs={5: drop_off(f0)})),
        ("R3-RUNS", "VOID", "F4 run 6's segment handed control back somewhere else",
         dict(logs_={6: {**logs["F4"], "log": [bad_seg, *logs["F4"]["log"][1:]]}})),
        ("R3-RUNS", "VOID", "F4 run 6's trace shows no wake (the segment ended on SC alone)",
         dict(runs={6: no_wake_f4})),
        ("R3-RUNS", "VOID", "another session redeployed a member during F4 run 6",
         dict(recs={6: {"install": "during the run: 1 changed: 30845"}})),
        ("R3-DONOR", "FAIL", "F0 run 2's member rows name no donor (no ForkDonorPatch row)",
         dict(runs={2: no_donor(f0)})),
        ("R3-JOIN", "FAIL", "F4 run 3's entry-0 rows NOT moved down by the prepend", dict(runs={3: unshifted})),
        ("R3-PING", "FAIL", "stock run 7 walked 450's e19 exit but never wrote the ping",
         dict(runs={7: drop_rows(objs, ping)})),
        ("R3-PING", "VOID", "stock run 4's 350 -> 450 exit went dead: it never entered 450", dict(runs={4: no_450})),
        ("R3-NULL-PRE", "FAIL", "every F0 run misses one member(355) write stock makes before 450",
         dict(runs={i: f0_missing for i in F0})),
        ("R3-NULL-PRE", "FAIL", "stock and F0 reach 450 straight after the segment (351's lobby exit, 350's "
                                "door): the segment alone is not zone scale",
         dict(runs={**{i: no_tour_s for i in S_}, **{i: no_tour_f0 for i in F0}})),
        ("R3-SEAM", "FAIL", "the chain HAD forked 450 (fork 30899, 450's own bytes): no seam into the real 450",
         dict(runs={i: forked_450 for i in F0}, snap={**snap, 30899: stock(450).data})),
        ("R3-MIRROR", "FAIL", "every F0 run writes one value no donor does", dict(runs={i: extra for i in F0})),
        ("R3-MIRROR", "FAIL", f"every F0 run misses one post-seam write of the real {post.fld} (STOCK ONLY)",
         dict(runs={i: f0_post for i in F0})),
        ("R3-ADVANCE", "VOID", "every F4 run STOPPED on a HarnessError after 450",
         dict(logs_={i: stopped for i in F4})),
        ("R3-ADVANCE", "VOID", "every F4 tour ended after 12 crossings (fewer than stock needed to move on)",
         dict(logs_={i: stop_log("F4", "passes exhausted (3) without the story moving on", 12) for i in F4})),
        ("R3-LATCH", "FAIL", "F4 with the hub gates OPEN (the latch writes happen, the story moves on)",
         dict(runs={i: no_gate for i in F4})),
        ("R3-LATCH", "FAIL", "F4 seeded with 296 as a byte (the corrected seed): no clobber",
         dict(runs={i: corrected for i in F4}, snap=snap_corr)),
        ("R3-LATCH", "VOID", "F4 never reached 450 (cut before the seam)", dict(runs={i: before_450 for i in F4})),
        ("R3-LATCH", "VOID", "F4 entered 450 but never walked out through e19", dict(runs={i: no_e19_f4 for i in F4})),
        ("R3-LATCH", "VOID", "F4 run 9 cut by the session budget mid-tour",
         dict(logs_={9: stop_log("F4", "session budget spent (crossings 19, 571s)", 19)})),
        ("R3-PREEMPT", "FAIL", "F4's prepend stamps no latch (the round-5 seed)", dict(runs={i: no_latch for i in F4})),
        ("R3-PREEMPT", "FAIL", "no stock run writes 2064 itself", dict(runs={i: no_2064 for i in S_})),
        ("P-FROZEN", "FAIL", "the predictions edited after the session recorded them", dict(sha="0" * 64)),
    ]
    passes = [
        ("stock run 4 VOID (350 -> 450 dead), and the session re-ran S as run 10", dict(runs={4: no_450},
                                                                                     extra=[("S", objs)])),
        ("New Game's hub (4600) traced before the raw warp, on S and F0", dict(runs={1: with_hub, 2: with_hub_f0})),
    ]
    print("\n== MUTANTS (each must come out as its registered verdict on its own check)")
    bad = 0
    for want, verdict, why, kw in mutants:
        got, _rep = case(f"mut-{len(results)}", **kw)
        results[why] = got
        failed = [k for k, (st, _d) in got.items() if st != "PASS"]
        hit = got.get(want, (None,))[0] == verdict
        bad += not hit
        print(f"  {'caught' if hit else '!! MISSED'}  {want:<12} {verdict}  {why}\n           not PASS: "
              f"{[(k, got[k][0]) for k in failed]}\n           {want}: {got.get(want, (None, ''))[1][:260]}")
    print("\n== CASES THAT MUST STILL PASS")
    for why, kw in passes:
        got, _rep = case(f"pass-{len(results)}", **kw)
        results[why] = got
        failed = [(k, st) for k, (st, _d) in got.items() if st != "PASS"]
        bad += bool(failed)
        print(f"  {'passes' if not failed else '!! BROKEN'}  {why}" + (f"\n           {failed}" if failed else ""))

    print("\n== PRE-FLIGHT on the live install (P-EXITS reads each chain through its own side's Tour)")
    tours = R.tours(chains, scripts=ran, stock=stock)
    pre = R.preflight(pred, roots, stock, tours)
    for ok, what, detail in pre:
        print(f"  {'PASS' if ok else 'FAIL'}  {what.split(':')[0]:<12} {detail[:160]}")
    patched = snap[30844].replace((30842).to_bytes(2, "little"), (30831).to_bytes(2, "little"))
    into = sorted({gw["to"] for gw in eventscan.scan_gateways(patched)})
    cross = R.tours(chains, scripts=T.mod_script_source(roots, fallback=stock, explicit={30844: patched}), stock=stock)
    [(ok_x, _w, detail_x)] = [x for x in R.preflight(pred, roots, stock, cross) if x[1].startswith("P-EXITS")]
    merged = D.Tour(members={f: d for m in chains.values() for f, d in m.items()},
                    scripts=T.mod_script_source(roots, fallback=stock, explicit={30844: patched}), stock=stock)
    try:
        merged.gateways(30844)
        old_rule = "passed (the old one-Tour-for-every-chain rule)"
    except D.TourError:
        old_rule = "refused"
    caught = not ok_x
    bad += not caught or not all(ok for ok, _w, _d in pre)
    print(f"  {'caught' if caught else '!! MISSED'}  P-EXITS      F4's member(350) exits into F0's 30831 (targets "
          f"{into}): {detail_x[:160]} -- under one Tour over both chains it {old_rule}")
    base_ok = all(st == "PASS" for st, _d in results["base"].values()) and retro in rep0 and "\nPRE-EMPTED" in rep4
    print(f"\nbase passes every check: {base_ok}; mutants and cases as registered: "
          f"{len(mutants) + len(passes) + 1 - bad}/{len(mutants) + len(passes) + 1}")
    if not a.keep:
        shutil.rmtree(root, ignore_errors=True)
    return 0 if base_ok and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
