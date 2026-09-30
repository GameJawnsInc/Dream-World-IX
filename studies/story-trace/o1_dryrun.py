"""O1's analysis, driven on SYNTHETIC sessions: every registered check must read PASS on a null pair and FAIL (or
VOID) on the mutant built to break it -- a check that cannot fail is not a check.

    py studies/story-trace/o1_dryrun.py [--predictions studies/story-trace/o1_predictions_v1.json]

Each case writes a session directory (o1_session.json, the members' scripts, one trace + log per run) the way the
session does, then runs :func:`o1_opening.analyse` on it. The rows are real store sites of the stock bytes of 50 and
52 (every one joins), shifted onto the fork's ids on the F side (``fld`` = member, ``don`` = donor, as the engine
writes them). Nothing here touches the game or the install.
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import o1_opening as O                                                     # noqa: E402
from ff9mapkit import storytrace as T                                      # noqa: E402

# (donor, sid, tag, ip, width, byte, old, new): real stores in the stock bytes (o1_opening's key scan)
MAIN_50 = (50, 0, 0, 45, "Int16", 2, 0, 10000)          # 50's Main_Init FieldEntrance := 10000 (a guarded write)
COUNTER = [(50, 17, 1, 1164, "Byte", 303, 4, 0)] + [(50, 17, 1, ip, "Byte", 303, v, v + 1)
                                                      for v, ip in enumerate((1198, 1220, 1242, 1264))]
SC_DEBUG = (50, 17, 1, 1790, "UInt16", 0, 1000, 1000)   # the debug-window SC write, never on the route
LADDER = [(50, 17, 1, 1804, "UInt16", 0, 0, 1000), (50, 17, 1, 3240, "Byte", 6, 0, 1),
          (50, 15, 1, 635, "Int16", 2, 0, 100), (52, 3, 1, 1249, "Int16", 2, 100, 102)]
IN_100 = (100, 0, 0, 45, "Int16", 2, 102, 10000)        # a row in the end field: always cut


def row(site, *, side, members, f, m=1, src="eb", ip=None, new=None) -> dict:
    donor, sid, tag, sip, width, byte, old, v = site
    fork = {d: fid for fid, d in members.items()}
    fld = fork.get(donor, donor) if side == "F" else donor
    new = v if new is None else new
    return {"k": "w", "f": f, "p": 0, "m": m, "fld": fld, "don": donor, "sc": 0, "src": src, "sid": sid, "uid": 0,
            "lvl": 0, "ip": sip if ip is None else ip, "tag": tag, "add": 0, "byte": byte, "w": width, "bit": -1,
            "old": old, "new": new, "same": int(old == new)}


def battle(side, members, f, value, byte=206) -> dict:
    """A scene-336 AI row: not a field row (m 2), its engine ip kept as the key's offset."""
    return row((50, 1, -1, 900, "Byte", byte, 0, value), side=side, members=members, f=f, m=2)


def epoch(why, f, fld=70) -> dict:
    return {"k": "e", "f": f, "p": 0, "m": 1, "fld": fld, "don": fld, "sc": 0, "why": why}


def trace(side, members, *, drop=(), extra=(), noise=True, close=True, rng=None, after=()) -> list:
    """One run's rows: arm, the route's stores (minus ``drop``, plus ``extra``), the battle noise, the rows past
    the end (``after``), off."""
    rng = rng or random.Random(0)
    sites = [s for s in [*COUNTER, *LADDER] if s not in drop] + list(extra)
    out, f = [epoch("arm", 100)], 200
    for s in sites:
        f += 10
        out.append(row(s, side=side, members=members, f=f))
        if noise and s == LADDER[1]:                          # the battle sits after the naming, as in the game
            for _ in range(3):
                f += 1
                out.append(battle(side, members, f, rng.randrange(256)))
    for s in [IN_100, *after]:
        f += 10
        out.append(row(s, side=side, members=members, f=f))
    if close:
        out.append(epoch("off", f + 1, fld=100))
    return out


def make_session(tmp: Path, pred_path: Path, runs: list, *, install=None) -> Path:
    """Write a session directory like o1_opening.run does. ``runs`` = [{side, rows, end, beats?, install?}]."""
    pred, sha = O.load_predictions(pred_path)
    d = tmp / f"s{len(list(tmp.iterdir()))}"
    (d / "scripts").mkdir(parents=True)
    stock = T.stock_script_source()
    from ff9mapkit.content.verbatim import remap_fields
    members = O.members_of(pred)
    retarget = {dn: f for f, dn in members.items()}
    for fid, donor in members.items():
        (d / "scripts" / f"{fid}.eb").write_bytes(remap_fields(stock(donor).data, retarget))
    session = {"label": d.name, "predictions": str(pred_path), "predictions_sha256": sha, "predictions_version": 1,
               "order": pred["order"], "runs": []}
    for i, r in enumerate(runs, 1):
        name, log = f"run{i}_{r['side']}.jsonl", f"run{i}_{r['side']}_log.json"
        (d / name).write_text("".join(json.dumps(x) + "\n" for x in r["rows"]), encoding="utf-8")
        beats = r.get("beats", {"candle": True, "named": True, "battle": 1, "garnet": True})
        (d / log).write_text(json.dumps({"outcome": {"end": r.get("end", "reached"), "pages": ["p1", "p2"],
                                                     "beats": beats}, "log": []}), encoding="utf-8")
        rec = {"i": i, "side": r["side"], "trace": name, "log": log, "end": r.get("end", "reached"),
               "why": "field 100", "beats": beats}
        if r.get("install"):
            rec["install"] = r["install"]
        session["runs"].append(rec)
    (d / O.SESSION_FILE).write_text(json.dumps(session), encoding="utf-8")
    return d


def six(pred, fork=None, stock=None) -> list:
    """S F S F S F, each run its own rng (the noise differs run to run)."""
    members = O.members_of(pred)
    out = []
    for n, side in enumerate(pred["order"]):
        kw = (fork if side == "F" else stock) or {}
        out.append({"side": side, "rows": trace(side, members, rng=random.Random(n), **kw)})
    return out


def result(checks) -> dict:
    return {w.split(":")[0]: ok for ok, w, _d in checks}


CASES = []


def case(name, want_verdict, **want):
    def deco(fn):
        CASES.append((name, fn, want_verdict, want))
        return fn
    return deco


@case("null-pair", "PROVEN")
def _(pred):
    return six(pred)


@case("fork-drops-SC", "NOT PROVEN", **{"O1-LADDER": False, "O1-NULL": False})
def _(pred):
    return six(pred, fork={"drop": [LADDER[0]]})


@case("fork-extra-key", "NOT PROVEN", **{"O1-NULL": False, "O1-LADDER": True})
def _(pred):
    return six(pred, fork={"extra": [MAIN_50]})


@case("stock-extra-key", "NOT PROVEN", **{"O1-NULL": False})
def _(pred):
    return six(pred, stock={"extra": [MAIN_50]})


@case("SC-twice", "NOT PROVEN", **{"O1-LADDER": False})
def _(pred):
    return six(pred, stock={"extra": [SC_DEBUG]}, fork={"extra": [SC_DEBUG]})


@case("unstable-outside-noise", "NOT PROVEN", **{"O1-STABLE": False, "O1-NULL": True})
def _(pred):
    runs = six(pred)
    runs[0]["rows"] = trace("S", O.members_of(pred), extra=[MAIN_50], rng=random.Random(0))
    return runs


@case("noise-only-difference", "PROVEN", **{"O1-NULL": True, "O1-STABLE": True})
def _(pred):
    runs = six(pred)
    m = O.members_of(pred)
    for r in runs:                                   # Byte[199] |= 2 in the fork runs only: registered noise
        if r["side"] == "F":
            r["rows"].insert(3, battle("F", m, 205, 2, byte=199))
    return runs


@case("cut-at-the-end-field", "PROVEN")
def _(pred):
    return six(pred, stock={"after": [(100, 0, 0, 45, "Int16", 2, 10000, 5)]})      # stock-only, but past the cut


@case("the-same-key-before-the-cut", "NOT PROVEN", **{"O1-NULL": False})
def _(pred):
    return six(pred, stock={"extra": [MAIN_50]}, fork={})


@case("F-uncovered", "VOID", **{"O1-COVER": None})
def _(pred):
    runs = six(pred)
    for r in runs[1::2][:2]:
        r["end"] = "void"
    return runs


@case("battle-lost-is-uncovered", "VOID", **{"O1-COVER": None})
def _(pred):
    runs = six(pred)
    for r in runs[1::2][:2]:
        r["beats"] = {"candle": True, "named": True, "battle": 3, "garnet": True}
    return runs


@case("trace-without-off", "VOID", **{"O1-COVER": None})
def _(pred):
    runs = six(pred)
    m = O.members_of(pred)
    for r in runs[0::2][:2]:
        r["rows"] = trace("S", m, close=False)
    return runs


@case("install-changed", "VOID", **{"O1-COVER": None})
def _(pred):
    runs = six(pred)
    for r in runs[1::2][:2]:
        r["install"] = "during the run: 1 changed: 31200"
    return runs


@case("join-failure", "NOT PROVEN", **{"O1-JOIN": False})
def _(pred):
    runs = six(pred)
    bad = (50, 17, 1, 1805, "UInt16", 0, 0, 1000)       # one byte off a real store: joins nothing
    m = O.members_of(pred)
    for n, r in enumerate(runs):
        r["rows"] = trace(r["side"], m, extra=[bad], rng=random.Random(n))
    return runs


def run_cases(pred_path: Path) -> int:
    pred, _sha = O.load_predictions(pred_path)
    stock = T.stock_script_source()
    fails = 0
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name, fn, want_verdict, want in CASES:
            d = make_session(tmp, pred_path, fn(copy.deepcopy(pred)))
            checks, _rep = O.analyse(d, stock=stock)
            got = result(checks)
            v = O.verdict(checks)
            ok = v.startswith(want_verdict) and all(got.get(k) is w for k, w in want.items())
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name:32} {v:40} "
                  + " ".join(f"{k}={'P' if got.get(k) is True else 'F' if got.get(k) is False else 'V'}"
                             for k in ("O1-FROZEN", "O1-COVER", "O1-LADDER", "O1-NULL", "O1-STABLE", "O1-JOIN")))
            if not ok:
                print("     " + "\n     ".join(f"{w} :: {dd[:220]}" for _ok, w, dd in checks))
        # O1-FROZEN: the predictions changed after the session recorded them
        frozen_tmp = tmp / "pred_copy.json"
        frozen_tmp.write_bytes(Path(pred_path).read_bytes())
        d = make_session(tmp, frozen_tmp, six(pred))
        frozen_tmp.write_bytes(Path(pred_path).read_bytes() + b" ")
        checks, _rep = O.analyse(d, stock=stock)
        ok = result(checks).get("O1-FROZEN") is False and O.verdict(checks).startswith("NOT PROVEN")
        fails += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {'predictions-changed':32} {O.verdict(checks)}")
    print(f"\n{len(CASES) + 1 - fails}/{len(CASES) + 1} cases as registered")
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", type=Path, default=O.PREDICTIONS)
    sys.exit(run_cases(ap.parse_args().predictions))
