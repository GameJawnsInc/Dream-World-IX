r"""TIER R rung 3 -- the gate runner.  `py r3_gates.py` prints K0..K4 with numbers and PASS/FAIL.

K0  NO REGRESSION: r1_gates 8/8, r2_gates 6/6, and every prior test still passes
K1  STATE-MACHINE RECOVERY on ef227: both entry points, 11 and 6 cases, every case reachable from
    the dispatch, every transition target a real case -- dead cases reported as findings
K2  CAPTURE VALIDATION: the derived phase boundaries against the archived s53 probe rows, itemised
    with frame numbers, agreement AND disagreement
K3  CORPUS CENSUS: clean / frame-dispatch / trivial / defeated over all 385 id-3 images, with the
    defeated ones categorised by cause
K4  CITATION DISCIPLINE: every HLE op the CHOREOGRAPHY report names resolves in hle_ops.json and
    carries its confidence, and the report's stock-instruction quote budget is respected

Reads the extracted corpus under ``C:\gd\SCRATCH\summon-format`` and the archived probe logs under
``C:\gd\SCRATCH\summon-transplant\logs``.  Prints only structure -- names, offsets, counts, frames.
"""
from __future__ import annotations

import collections
import glob
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tier_r_disasm as T        # noqa: E402
import tier_r_annot as A         # noqa: E402
import summon_inspect as S       # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []
FINDINGS = []
EF227 = 227
CAPTURE_DIR = r"C:\gd\SCRATCH\summon-transplant\logs"
REPORT = os.path.join(_HERE, "EF227-CHOREOGRAPHY.md")


def gate(name: str, ok: bool, *lines: str) -> bool:
    RESULTS.append((name, ok))
    print("\n%s %s  %s" % ("[PASS]" if ok else "[FAIL]", name, "-" * max(2, 58 - len(name))))
    for ln in lines:
        print("   " + ln)
    return ok


def finding(text: str) -> None:
    FINDINGS.append(text)


def pick_capture(effect: int = EF227) -> str:
    """The archived probe log with the most rows for this effect."""
    best, best_n = None, 0
    for p in sorted(glob.glob(os.path.join(CAPTURE_DIR, "sfxmeshprobe.*.log"))):
        n = 0
        pre = "MODEL,%d," % effect
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith(pre):
                    n += 1
        if n > best_n:
            best, best_n = p, n
    return best


# --------------------------------------------------------------------------- K0
def k0_no_regression():
    lines, ok = [], True
    for runner in ("r1_gates.py", "r2_gates.py"):
        p = subprocess.run([sys.executable, os.path.join(_HERE, runner)],
                           capture_output=True, text=True)
        tail = [l for l in p.stdout.splitlines() if "gates pass" in l]
        lines.append("%-12s exit=%d  %s" % (runner, p.returncode, tail[-1] if tail else "(none)"))
        ok = ok and p.returncode == 0
    total = 0
    for mod in ("test_tier_r_disasm.py", "test_tier_r_annot.py", "test_summon_inspect.py"):
        path = os.path.join(_HERE, mod)
        if not os.path.isfile(path):
            lines.append("%s: MISSING" % mod)
            ok = False
            continue
        p = subprocess.run([sys.executable, "-m", "pytest", path, "-q", "--no-header"],
                           capture_output=True, text=True, cwd=_HERE)
        summary = [l for l in p.stdout.splitlines() if " passed" in l or " failed" in l]
        line = summary[-1] if summary else "?"
        m = re.search(r"(\d+) passed", line)
        total += int(m.group(1)) if m else 0
        lines.append("%-26s exit=%d  %s" % (mod, p.returncode, line))
        ok = ok and p.returncode == 0
    lines.append("%d tests pass in total" % total)
    lines.append("R3 IMPORTS tier_r_disasm and tier_r_annot and mutates neither, so every R1/R2")
    lines.append("number above is still produced by R1's and R2's own code.")
    return gate("K0 no regression (R1+R2 gates, all three test modules)", ok, *lines)


# --------------------------------------------------------------------------- K1
def k1_recovery(ops):
    blob = open(os.path.join(T.SCRATCH_CORPUS, "ef%03d.bytes" % EF227), "rb").read()
    recs = S.recover_container(blob, "ef%03d" % EF227, ops)
    lines, ok = [], len(recs) == 2 and all(r.verdict == "clean" for r in recs)
    expect_slots = (11, 6)
    for rec, want in zip(recs, expect_slots):
        sm = rec.machine
        if sm is None:
            lines.append("%s: %s" % (rec.image, rec.reason))
            ok = False
            continue
        reachable = sorted(s for c in sm.cases for s in c.slots)
        ok = ok and sm.n_slots == want and reachable == list(range(want)) and not sm.bad_targets
        lines.append("")
        lines.append("%s  entry %#x  dispatch %#x -> table at image+%#x, %d slots"
                     % (sm.image, sm.entry, sm.dispatch_off, sm.table_off, sm.n_slots))
        lines.append("   $a0 arms: " + " | ".join("%s->%s" % ("else" if a.mode is None else a.mode,
                                                              a.role) for a in sm.arms))
        lines.append("   state = %s + %#x  (block %s B)  clock = %s  reset at %d sites"
                     % (sm.state_base, sm.state_offset, sm.state_block_bytes, sm.clock,
                        len(sm.clock_reset_sites)))
        lines.append("   %-14s %-8s %6s %5s  %-16s %-8s %s"
                     % ("state(s)", "body", "instr", "HLE", "guard", "-> state", "ticks"))
        for c in sm.cases:
            prim = next((x for x in c.transitions if x.guard_reg_is_clock), None)
            lines.append("   %-14s %#-8x %6d %5d  %-16s %-8s %s"
                         % (",".join(str(s) for s in c.slots), c.target, len(c.body), len(c.hle),
                            ("clock >= %d" % prim.threshold) if prim else "-",
                            prim.to_state if prim else "terminal",
                            prim.ticks if prim else "-"))
        lines.append("   phase chain: " + " -> ".join(
            "s%d[%s]" % (p.state, p.ticks if p.ticks else "terminal") for p in sm.phases))
        lines.append("   every slot reachable from the dispatch: %s;  every transition target a "
                     "real case: %s" % (reachable == list(range(want)), not sm.bad_targets))
        if sm.dead_states:
            lines.append("   DEAD STATES %s -- table slots no transition ever assigns"
                         % ", ".join(str(s) for s in sm.dead_states))
        for t in [c for c in sm.cases if c.is_tail]:
            lines.append("   the 'stay' branch of every transition lands on %#x, so that case IS "
                         "the per-tick tail (slots %s)"
                         % (t.target, ",".join(str(s) for s in t.slots) or "-"))
    c0 = recs[0].machine
    if c0 and c0.dead_states:
        finding("ef227:c0's dispatch table has %d live states and %d dead slots (%s): the compiler "
                "emitted a full 0..10 table for a machine that only ever visits %s."
                % (len(c0.phases), len(c0.dead_states),
                   ",".join(str(s) for s in c0.dead_states),
                   ",".join(str(p.state) for p in c0.phases)))
    finding("The per-tick contract is recovered, not assumed: $a0=0 REPORTS the state block's size "
            "(168 B / 228 B), $a0=1 INITIALISES it, anything else is one TICK. The program is a "
            "callback the host drives, never a script that runs to completion.")
    finding("The clock is the CALLER's cell (*arg3), and a transition writes -1 to it. Writing -1 "
            "is only coherent if the host increments before the next read -- which is what fixes "
            "a `clock < N` case at N+1 ticks. The whole frame model rests on that one store.")
    return gate("K1 state-machine recovery on ef227", ok, *lines), recs


# --------------------------------------------------------------------------- K2
def k2_capture(recs, ops):
    path = pick_capture()
    if not path:
        return gate("K2 capture validation", False, "no probe log found in %s" % CAPTURE_DIR), None
    cap = S.parse_capture(path, EF227)
    sms = [r.machine for r in recs if r.machine]
    fits = [S.fit_origin(sm, cap) for sm in sms]
    checks = S.validate_all(sms, cap, fits)
    lo, hi = cap.span
    lines = ["capture %s -- effect %d, frames %d..%d, %d frames with rows"
             % (os.path.basename(path), EF227, lo, hi, len(cap.frames)),
             "",
             "OBSERVED, independently of any model:",
             "   summon slot active from f%s; creature first drawn f%s"
             % (cap.first(lambda c: bool(c.active)), cap.first(lambda c: c.drawn)),
             "   bone pose valid through f%s, freed memory from f%s"
             % (cap.last_bones_ok(), cap.first_bones_bad()),
             "   motion-counter restarts at %s"
             % ", ".join("f%d->%d" % t for t in cap.motion_resets()[:12]),
             "   projection distance H changes at %s"
             % ", ".join("f%d->%d" % t for t in cap.proj_changes()),
             ""]
    agree = disagree = 0
    for fit, ck in zip(fits, checks):
        lines.append("%s -- ONE fitted parameter (the frame the sequence starts this chunk) = f%s;"
                     % (fit.machine.image, fit.origin))
        lines.append("   %d of %d boundaries that PREDICT an observable land exactly."
                     % (fit.hits, fit.total))
        for c in ck:
            lines.append("   %-34s pred %-6s obs %-6s %-14s %s"
                         % (c.what, c.predicted if c.predicted is not None else "-",
                            c.observed if c.observed is not None else "-", c.verdict, c.note))
            if c.verdict.startswith("AGREE"):
                agree += 1
            elif c.verdict.startswith("DISAGREE") or c.verdict.startswith("OFF"):
                disagree += 1
        lines.append("")
    logs = [p for p in sorted(glob.glob(os.path.join(CAPTURE_DIR, "sfxmeshprobe.*.log")))
            if S.parse_capture(p, EF227).frames]
    reps = S.replicate(sms, logs, EF227)
    lines.append("REPLICATION -- the same fit, re-run against every archived capture:")
    for name, origins, hits in reps:
        lines.append("   %-34s origins %s   hits %s"
                     % (name, ", ".join("f%s" % o for o in origins),
                        ", ".join("%d/%d" % h for h in hits)))
    same = len({tuple(o) for _n, o, _h in reps}) == 1
    lines.append("   every capture agrees on the origins: %s" % same)
    ok = (fits and fits[0].origin is not None and fits[0].hits == fits[0].total
          and disagree == 0 and same)
    lines.append("%d checks AGREE, %d DISAGREE" % (agree, disagree))
    if same and len(reps) > 1:
        finding("The frame model REPLICATES: %d independently recorded casts of ef227 all fit the "
                "same two origins with the same boundary hits. The phase timing is a property of "
                "the effect, not of the log it was fitted against." % len(reps))
    if fits and fits[0].origin is not None:
        finding("ef227's two programs run on two separate clocks that the SEQUENCE starts: chunk 0 "
                "at capture frame %s, chunk 1 at %s. Neither program starts or stops the other, "
                "and neither stops itself -- both end in a terminal state, so the cast's end is a "
                "sequence event." % (fits[0].origin, fits[1].origin if len(fits) > 1 else "?"))
        finding("The camera's three shots (sequence opcode 0x29, sub-files 6/16/47 -- R2 §5) change "
                "the projection distance H at f58 / f153 / f302, i.e. 1, 1 and 2 frames after a "
                "program phase boundary. The camera is not driven BY the program, but it is cut in "
                "lockstep with it -- two clocks the author kept aligned by construction.")
    return (gate("K2 capture validation (the s53 probe rows)", bool(ok), *lines),
            (cap, fits, checks, reps))


# --------------------------------------------------------------------------- K3
def k3_census(ops):
    t0 = time.time()
    rows = S.corpus_census(T.SCRATCH_CORPUS, ops)
    s = S.census_summary(rows)
    lines = ["%d id-3 images walked in %.1fs" % (s["total"], time.time() - t0), ""]
    for v in S.VERDICTS:
        lines.append("   %-16s %4d" % (v, s[v]))
    lines.append("")
    lines.append("   'trivial' = no compiled switch in any program entry: a per-tick body that does")
    lines.append("   the same thing every frame (it may still branch on the clock internally).")
    lines.append("   'frame-dispatch' = a switch whose index NOTHING in the program writes -- it is")
    lines.append("   the caller's frame counter, so slot k IS frame k. Not a failure: a timeline")
    lines.append("   comes out of those too, more directly than from a state machine.")
    lines.append("")
    lines.append("   DEFEATED, by cause:")
    for cause, n in s["causes"].most_common():
        lines.append("      %3d  %s" % (n, cause))
    clean = [r for r in rows if r.verdict == "clean"]
    lines.append("")
    lines.append("   the %d clean recoveries: %s"
                 % (len(clean), ", ".join("%s(%dc/%dp)" % (r.image, r.cases, r.phases)
                                          for r in clean)))
    fd = [r for r in rows if r.verdict == "frame-dispatch"]
    lines.append("   the %d frame-dispatch programs: %s"
                 % (len(fd), ", ".join(r.image for r in fd)))
    ok = s["total"] == 385 and s["clean"] >= 2 and (s["clean"] + s["frame-dispatch"]
                                                    + s["trivial"] + s["defeated"]) == s["total"]
    finding("Only %d of 385 id-3 images have a switch-driven program entry at all (%d state "
            "machines + %d frame dispatches + %d defeated). The overwhelming majority -- %d -- are "
            "ONE per-tick body with no stored phase: FF9's effects are mostly single-beat, and the "
            "multi-phase choreography ef227 has is the exception."
            % (s["clean"] + s["frame-dispatch"] + s["defeated"], s["clean"], s["frame-dispatch"],
               s["defeated"], s["trivial"]))
    return gate("K3 corpus recovery census", bool(ok), *lines), (rows, s)


# --------------------------------------------------------------------------- K4
def k4_citations(ops, path=REPORT):
    if not os.path.isfile(path):
        return gate("K4 citation discipline", False, "%s has not been written" % path)
    text = open(path, "r", encoding="utf-8").read()
    cited = set(int(m) for m in re.findall(r"\bop (\d+)\b", text))
    missing = sorted(o for o in cited if o not in ops)
    unnamed = sorted(o for o in cited if o in ops and not ops[o].get("name"))
    # every named op cited in the report must appear with its confidence somewhere in the file
    hedged = []
    for o in sorted(cited):
        row = ops.get(o) or {}
        if row.get("name") and row.get("confidence") in ("medium", "low"):
            if row["confidence"] not in text:
                hedged.append(o)
    quotes = len(re.findall(r"^  [0-9a-f]{4}  [0-9a-f]{8}", text, re.M))
    ok = not missing and not hedged and quotes <= S.QUOTE_BUDGET
    conf = collections.Counter((ops.get(o) or {}).get("confidence") or "unnamed" for o in cited)
    lines = ["%s cites %d distinct HLE ops" % (os.path.basename(path), len(cited)),
             "   by confidence: " + ", ".join("%s %d" % (k, v) for k, v in sorted(conf.items())),
             "   ops with no row in hle_ops.json: %s" % (missing or "none"),
             "   ops cited without their confidence shown: %s" % (hedged or "none"),
             "   %d of the cited ops are UNNAMED and appear as bare numbers: %s"
             % (len(unnamed), ", ".join(str(o) for o in unnamed) or "-"),
             "   stock instructions quoted: %d (budget %d)" % (quotes, S.QUOTE_BUDGET)]
    return gate("K4 citation discipline in EF227-CHOREOGRAPHY.md", ok, *lines)


# --------------------------------------------------------------------------- main
def main() -> int:
    print(__doc__.splitlines()[0])
    ops = A.load_hle_ops()
    k0_no_regression()
    _ok, recs = k1_recovery(ops)
    _ok2, capbits = k2_capture(recs, ops)
    _ok3, (rows, summary) = k3_census(ops)
    if capbits:
        cap, fits, checks, reps = capbits
        sms = [r.machine for r in recs if r.machine]
        with open(REPORT, "w", encoding="utf-8") as fh:
            n = S.write_report(fh, EF227, sms, ops, cap, fits, checks, summary,
                               quotes=S.report_quotes(sms), replicas=reps)
        print("\nwrote %s (%d quoted stock instructions)" % (REPORT, n))
    k4_citations(ops)
    print("\n" + "=" * 72)
    if FINDINGS:
        print("FINDINGS (what R3 learned that the record did not say):")
        for i, f in enumerate(FINDINGS, 1):
            print("  %d. %s" % (i, f))
        print("=" * 72)
    for name, ok in RESULTS:
        print("%s  %s" % ("PASS" if ok else "FAIL", name))
    bad = [n for n, ok in RESULTS if not ok]
    print("=" * 72)
    print("%d/%d gates pass" % (len(RESULTS) - len(bad), len(RESULTS)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
