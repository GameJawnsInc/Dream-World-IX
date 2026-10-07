"""Score a d9_session run OFFLINE: exact heights, the battle scenes against the fire point's class, the encounter-rate
draw, the recovery receipts, and PART (c) -- the Disc9 bind receipts from the archived Memoria.log.

  H     every burst endpoint's published world_y against the engine's sky query on the LIVE walk list of its cell
        (same rule as session1_post.ground / d9_prep.exact_ground), minus 1.171875 on topo 36/37/38; +-0.15.
  B1/B2 the fire point's exact (area, topograph) -> zone -> the fog-0 record (d9_prep.json) vs the published scene.
  RATE  each battle's walked distance as a percentile of the ENCRATE model (d9_prep.json rate_model*).
  REC   "[Soft Reset]" lines in Memoria.log (UIKeyTrigger.cs:361) vs the recoveries the session recorded.
  (c)   THE BIND ORACLE REPLAY, Disc9 only, both directions -- the consumption lane's own model (bind_oracle.Engine,
        scan_overrides, LOG_RE), re-run against this run's Memoria.log:
          * every logged Disc9 cell's sequence is whole repetitions of the predicted ordered bind list
            (WMWorld.cs:582-810 registration order; WorldMeshOverride.cs:47 logs each bound child once per load);
          * every predicted Disc9 cell with a non-empty bind list appears (the oracle's own calibration only checks
            the logged direction -- a cell that silently failed to bind would pass it);
          * the modal repetition count equals the number of 9013 loads the session made;
          * ZERO Disc1/Disc4 'loaded' lines (no disc-1/4 world loads in this run; s74 keeps Path D in its own
            namespace, WMWorld.cs:174-179) and ZERO '[WorldMeshOverride] failed' / 'bad Donor.txt' lines.
        Files whose mtime is newer than the log's first line are excluded and listed (the oracle's own rule).

Rerun:  py studies/terrain-malleability/ingame/d9_post.py <.harness-runs/...-terrain-d9>
        (cross-check with the lane's unmodified oracle:
         py studies/terrain-malleability/consumption/bind_oracle.py --log <run>/Memoria.log)
"""
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TM = HERE.parent
sys.path.insert(0, str(TM / "gap_area_layer"))
sys.path.insert(0, str(TM / "consumption"))
sys.path.insert(0, str(HERE))
import arealib as A                                   # noqa: E402
import bind_oracle as BO                              # noqa: E402
import numpy as np                                    # noqa: E402
import d9_prep as P                                   # noqa: E402

TOL = 0.15
_MESH = {}


def meshes(cell):
    if cell not in _MESH:
        cf = A.live_cells().get((P.NS, *cell), {})
        _pk, _why, walk = A.live_walk_list(P.NS, cell[0], cell[1], cf)
        _MESH[cell] = A.load_walk_arrays(walk)
    return _MESH[cell]


def exact(x, z):
    cell = (int(x // 64), int(-z // 64))
    r = P.exact_ground(meshes(cell), x, z, cell[0] * 64.0, -cell[1] * 64.0)
    r["cell"] = list(cell)
    return r


def model_rank(model, walked):
    """P(battle by `walked` units) under the ENCRATE model."""
    enc = model["encratio"]
    surv, base, k = 1.0, 0, 0
    while True:
        k += 1
        dist = P.INITIAL_U + (k - 1) * P.INTERVAL_U
        if dist > walked:
            return round(1 - surv, 4)
        base += enc
        surv *= 1 - min(base >> 3, 256) / 256.0
        if surv <= 0:
            return 1.0


def bind_receipts(log_path: Path, n_loads, ns_want: int = P.NS):
    E = BO.Engine(A.census())
    files = BO.scan_overrides(A.GAME, BO.folder_names(A.GAME))
    pred = {}
    newest = {}
    for (ns, x, y), cf in files.items():
        if ns != ns_want:
            continue
        pk, _why, _ = E.effective(ns, x, y, cf)
        _order, bound = E.bind_list(ns, x, y, pk, cf)
        pred[(x, y)] = [n for n, _ in bound]
        newest[(x, y)] = max(t for lst in cf.values() for _, _, _, t in lst[:1])
    seqs = defaultdict(list)
    other_disc = Counter()
    t0 = None
    text = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for ln in text:
        m = BO.LOG_RE.match(ln)
        if not m:
            continue
        dd, mo, yy, hh, mi, ss, ns, _r, x, y, part, _folder = m.groups()
        t = datetime(int(yy), int(mo), int(dd), int(hh), int(mi), int(ss)).timestamp()
        t0 = t if t0 is None else min(t0, t)
        if int(ns) != ns_want:
            other_disc[f"Disc{ns}"] += 1
            continue
        seqs[(int(x), int(y))].append(part)
    failed = [ln for ln in text if "[WorldMeshOverride] failed" in ln or "bad Donor.txt" in ln]
    excluded = sorted(f"{k}" for k, t in newest.items() if t0 and t > t0)
    rows, reps = [], Counter()
    for key in sorted(set(pred) | set(seqs)):
        if f"{key}" in excluded:
            continue
        p, s = pred.get(key, []), seqs.get(key, [])
        n = len(p)
        whole = n > 0 and len(s) % n == 0 and all(s[i:i + n] == p for i in range(0, len(s), n))
        rep = len(s) // n if whole else None
        if rep is not None:
            reps[rep] += 1
        ok = (whole and rep >= 1) if p else not s
        rows.append({"cell": list(key), "pred": p, "logged": s[:12] + (["..."] if len(s) > 12 else []),
                     "n_logged": len(s), "repetitions": rep, "ok": ok})
    modal = reps.most_common(1)[0][0] if reps else None
    return {"log": str(log_path), "predicted_cells": len(pred), "logged_cells": len(seqs),
            "lines_disc9": sum(len(v) for v in seqs.values()), "other_disc_lines": dict(other_disc),
            "failed_lines": failed[:10], "excluded_changed_after_log": excluded, "rows": rows,
            "repetition_histogram": dict(reps), "modal_repetitions": modal, "n_loads": n_loads,
            "mismatch": [r for r in rows if not r["ok"]],
            "pass": (not [r for r in rows if not r["ok"]]) and not other_disc and not failed
                    and modal == n_loads and len(pred) > 0}


def main(run_dir):
    run_dir = Path(run_dir)
    rec = json.loads((run_dir / "d9_session.json").read_text(encoding="utf-8"))
    prep = json.loads((HERE / "out" / "d9_prep.json").read_text(encoding="utf-8"))
    pred = prep["predicted_scenes"]
    out = {"loops": [], "verdicts": {}}
    for lrec in rec.get("loops", []):
        lo = {"label": lrec["label"], "home": lrec["home"]}
        hs = []
        for b in lrec.get("bursts", []):
            if b.get("x") is None or b.get("y") is None:
                continue
            g = exact(b["x"], b["z"])
            if g.get("ground") is None:
                continue
            want = g["ground"] - P.SINK if g["topo"] in P.CANOPY else g["ground"]
            hs.append({"x": b["x"], "z": b["z"], "y": b["y"], "topo": g["topo"], "area": g["area"],
                       "dev": round(b["y"] - want, 4), "ok": abs(b["y"] - want) <= TOL})
        lo["height"] = {"n": len(hs), "ok": sum(h["ok"] for h in hs),
                        "dev_minmax": [min(h["dev"] for h in hs), max(h["dev"] for h in hs)] if hs else None,
                        "classes": dict(Counter(f"area{h['area']}/topo{h['topo']}" for h in hs))}
        bt = lrec.get("battle")
        if bt:
            fp = bt.get("fire_pos") or [None, None]
            fc = exact(*fp) if fp[0] is not None else {}
            zone = A.consequence(fc["area"])["zone"] if fc.get("area") is not None else None
            carry = lrec["home"] != "landing"
            want = (pred.get(f"topo{fc.get('topo')}") if carry else pred["landing"])
            model = prep["rate_model"] if carry else prep["rate_model_landing"]
            lo["battle"] = {"scene": bt["scene"], "enemies": bt.get("enemies"), "fire_pos": fp, "fire_exact": fc,
                            "zone": zone, "B1": (bt["scene"] in pred["zone24_slice"]) if carry else None,
                            "B2": (bt["scene"] in want) if want else None,
                            "C": (bt["scene"] in pred["landing"]) if not carry else None,
                            "walked_u": bt["walked_u"], "P_battle_by_then": model_rank(model, bt["walked_u"])}
        lo["recovery"] = lrec.get("recovery")
        out["loops"].append(lo)
    log = run_dir / "Memoria.log"
    soft = sum(1 for ln in log.read_text(encoding="utf-8", errors="replace").splitlines()
               if "[Soft Reset]" in ln) if log.is_file() else None
    out["soft_reset_lines"] = soft
    out["soft_reset_recoveries"] = sum(1 for l in rec.get("loops", [])
                                       if (l.get("recovery") or {}).get("how") == "soft_reset_from_battle")
    n_loads = len(rec.get("world_loads", []))
    out["bind"] = bind_receipts(log, n_loads) if log.is_file() else {"error": "no Memoria.log in the run dir"}
    carry_b = [l["battle"] for l in out["loops"] if l.get("battle") and l["home"] != "landing"]
    v = out["verdicts"]
    v["H"] = all(l["height"]["n"] and l["height"]["ok"] >= 0.8 * l["height"]["n"] for l in out["loops"]) or "see loops"
    v["B1"] = (len(carry_b) >= 3 and all(b["B1"] for b in carry_b)) if carry_b else "proved-nothing"
    v["B2"] = all(b["B2"] for b in carry_b if b["B2"] is not None) if carry_b else "proved-nothing"
    v["C"] = [l["battle"]["C"] for l in out["loops"] if l.get("battle") and l["home"] == "landing"] or "not run"
    v["c_bind"] = out["bind"].get("pass")
    v["REC"] = (soft == out["soft_reset_recoveries"]) if soft is not None else "no log"
    (run_dir / "d9_post.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    for l in out["loops"]:
        b = l.get("battle") or {}
        print(f"{l['label']:12s} H {l['height']['ok']}/{l['height']['n']} dev {l['height']['dev_minmax']} | scene "
              f"{b.get('scene')} {b.get('enemies')} at {b.get('fire_exact', {}).get('area')}/"
              f"{b.get('fire_exact', {}).get('topo')} zone {b.get('zone')} B1 {b.get('B1')} B2 {b.get('B2')} "
              f"C {b.get('C')} walked {b.get('walked_u')}u (P={b.get('P_battle_by_then')}) | rec "
              f"{(l.get('recovery') or {}).get('how')}")
    bd = out["bind"]
    print(f"(c) Disc9 bind: predicted {bd.get('predicted_cells')} cells, logged {bd.get('logged_cells')}, "
          f"{bd.get('lines_disc9')} lines, reps {bd.get('repetition_histogram')} vs loads {n_loads}, other-disc "
          f"{bd.get('other_disc_lines')}, failed {len(bd.get('failed_lines') or [])}, mismatches "
          f"{len(bd.get('mismatch') or [])} -> {bd.get('pass')}")
    print(f"soft-reset lines {soft} vs soft-reset recoveries {out['soft_reset_recoveries']}")
    print(f"verdicts {v}")
    print(f"wrote {run_dir / 'd9_post.json'}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--calibrate"]:
        # INSTRUMENT CALIBRATION on a log that exists today (no Disc9 receipt exists anywhere yet): the same parser and
        # both-direction comparison, pointed at another namespace. Usage: d9_post.py --calibrate <Memoria.log> <ns>
        r = bind_receipts(Path(sys.argv[2]), None, int(sys.argv[3]))
        print(json.dumps({k: r[k] for k in ("predicted_cells", "logged_cells", "lines_disc9", "other_disc_lines",
                                            "repetition_histogram", "excluded_changed_after_log")}, default=str))
        for m in r["mismatch"][:15]:
            print("  MISMATCH", m)
        sys.exit(0)
    main(sys.argv[1])
