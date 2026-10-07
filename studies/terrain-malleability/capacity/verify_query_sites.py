"""VERIFIER for CAP-10 (READ-ONLY on the Memoria clone): every ground-query call site in ff9.cs, with its
cache argument and the WMPhysics.IgnoreExceptions state in force at the call.

Why: CAP-10's cost model prices a full-scan tri as "cheap mapid/up-facing filter, then 3x TransformPoint +
ray/tri only for tris that pass" and models only the controlled walker's cached probe. WMPhysics.cs:16-29
bypasses BOTH filters when IgnoreExceptions is true, so at such sites EVERY iterated tri is the expensive
test. This lists which sites run cached vs null-cache and filtered vs unfiltered.

Heuristic (stated, not hidden): IgnoreExceptions state = the most recent `WMPhysics.IgnoreExceptions = X;`
textually above the call inside the same enclosing `public static` method (False if none). Calibration: the
NPC re-ground at the w_movementUpdate site must come out (cache=null, IgnoreExceptions=True), the walker's
w_movementRoundCheck cached site must come out (cache=cache, IgnoreExceptions=False) -- both independently
read in walk-decode-claims.md steps 4 and 14.

Writes out/verify_query_sites.json.  Run:  py studies/terrain-malleability/capacity/verify_query_sites.py
"""
import json
import re
from pathlib import Path

SRC = Path(r"C:\gd\FFIX\Memoria\Assembly-CSharp\Global\ff9\ff9.cs")
OUT = Path(__file__).resolve().parent / "out"
CALL = re.compile(r"ff9\.(w_cellHit|w_nwpHit|w_nwpHitBool)\((.*)\);")
METH = re.compile(r"^\s*(public|private) static [\w\.<>\[\]]+ (\w+)\(")
IGN = re.compile(r"WMPhysics\.IgnoreExceptions = (true|false);")


def main():
    lines = SRC.read_text(encoding="utf-8", errors="replace").splitlines()
    meth, ign, rows = None, False, []
    for no, ln in enumerate(lines, 1):
        m = METH.match(ln)
        if m:
            meth, ign = m.group(2), False
        g = IGN.search(ln)
        if g:
            ign = g.group(1) == "true"
        c = CALL.search(ln)
        if c and "public static" not in ln:
            args = [a.strip() for a in c.group(2).split(",")]
            cache = args[3] if c.group(1) in ("w_cellHit", "w_nwpHitBool") else args[3]
            rows.append({"line": no, "method": meth, "call": c.group(1),
                         "cache": "null" if cache == "null" else cache, "ignore_exceptions": ign})
    calib = {
        "npc_reground_null_unfiltered": any(r["method"] == "w_movementUpdate" and r["cache"] == "null"
                                            and r["ignore_exceptions"] for r in rows),
        "walker_roundcheck_cached_filtered": any(r["method"] == "w_movementRoundCheck" and r["cache"] == "cache"
                                                 and not r["ignore_exceptions"] for r in rows),
    }
    summary = {}
    for r in rows:
        k = f"cache={'null' if r['cache'] == 'null' else 'ring'}|filters={'BYPASSED' if r['ignore_exceptions'] else 'on'}"
        summary.setdefault(k, []).append(f"{r['method']}:{r['line']}")
    res = {"calibration": calib, "sites": rows, "summary": summary}
    OUT.mkdir(exist_ok=True)
    (OUT / "verify_query_sites.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("calibration:", calib)
    for k, v in summary.items():
        print(k, len(v), v)


if __name__ == "__main__":
    main()
