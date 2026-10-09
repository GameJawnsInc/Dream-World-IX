"""STEP 9 -- the shipped disc-4 replay for in-place coast morphs, re-measured on today's kit (2026-10-09).

s7_morph_replay.py measured the replay as a study replica (before the stitch gate, defects 10-11). This re-runs the
SHIPPED path over the same 129 certified cliff bumps on coastal cells disc 4 redrew: `world-transplant --in-place
--cliff-bump ... --dry-run`, whose disc-4 preview rebuilds the morph from disc 4's bytes and runs every gate there.
Counts: disc 1 clean, disc 4 replay clean / refused (with the reason), against s7's 116/13. Dry runs only.
Writes out/s9_morph_reach.json.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/gap_disc4_edit_reach/s9_morph_reach.py
"""
import contextlib
import io
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))


def main():
    import ff9mapkit
    from ff9mapkit import cli
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    rows = json.loads((HERE / "out" / "s7_morph_replay.json").read_text(encoding="utf-8"))["partB"]["rows"]
    out = []
    for r in rows:
        (x, y), ((x0, z0), (x1, z1)), d = r["cell"], r["window"], r["depth"]
        c = f"{x},{y}"
        args = cli.build_parser().parse_args(["world-transplant", "--mod-folder", "FF9CustomMap_test_nonexistent",
                                              "--in-place", "--cell", c, "--donor", c,
                                              "--cliff-bump", f"{x0},{z0}:{x1},{z1}:{d}", "--dry-run"])
        so, se = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(so), contextlib.redirect_stderr(se):
            rc = cli._cmd_world_transplant(args)
        o = so.getvalue()
        if rc != 0:
            verdict = "disc1_refused"
        elif "the replay passes its gates" in o:
            verdict = "replayed"
        elif "the replay REFUSES there" in o:
            verdict = "disc4_refused"
        elif "the deploy copies this edit there" in o:
            verdict = "copied"
        else:
            verdict = "unknown"
        why = se.getvalue().strip().splitlines()[-1][:200] if verdict.endswith("refused") and se.getvalue().strip() \
            else None
        if verdict == "disc4_refused" and "NOT CLEAN" in (why or ""):
            gates = [ln.strip() for ln in o.splitlines() if ln.strip().startswith("GATE") and ln.endswith("FAIL")]
            why = "; ".join(gates)[:200] or why
        out.append({"cell": r["cell"], "verdict": verdict, "why": why, "s7_replay_clean": r["replay_d4_clean"]})
        print(f"{tuple(r['cell'])} {verdict} {why or ''}")
    n = Counter(o["verdict"] for o in out)
    agree = sum((o["verdict"] == "replayed") == o["s7_replay_clean"] for o in out)
    res = {"tested": len(out), "verdicts": dict(n), "agrees_with_s7": agree, "rows": out}
    (HERE / "out" / "s9_morph_reach.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(dict(n), f"agrees with s7 on {agree}/{len(out)}")


if __name__ == "__main__":
    main()
