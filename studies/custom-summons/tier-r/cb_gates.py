"""cb_gates -- the gate board for the MANAGED-ABI (callback-code) evidence class.

Six falsifiable gates.  Two of them are the ones that could actually have killed the round:

* **C1** reproduces ``A1-TEXTURES.md`` §5.2's issuer table, which was derived independently and
  months earlier by a different method.  It is the only outside control that speaks about these
  functions at all.
* **C4** is the DISJOINTNESS null: if this evidence class were noise, it would collide with the 42
  names R2 derived from the DLL's own debug strings.  It collides with none of them.  A gate that
  can only pass is worth nothing -- C4 is written so that a single overlap fails it.

    py studies/custom-summons/tier-r/cb_gates.py
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import callback_ops as C
import tier_r_annot as A


def _hdr(t: str) -> None:
    print("=" * 72)
    print(t)
    print("=" * 72)


def main() -> int:
    namer = C.OpNamer()
    sweep = namer.sweep()
    named = {op: v for op, v in sweep.items() if v.name}
    ops = A.load_hle_ops()
    msigs = C.managed_signatures()
    results = []

    # -- C1 -------------------------------------------------------------
    ok, lines = C.calibrate(namer)
    for ln in lines:
        print(ln)
    results.append(("C1", "A1-TEXTURES §5.2 issuer table reproduced site-for-site", ok))

    # -- C2: the managed authority is PARSED, and covers every code we name
    codes = {next(iter(v.codes)) for v in named.values()}
    missing = sorted(c for c in codes if c not in msigs)
    cmds = C.load_commands()
    ok2 = not missing and len(cmds) == 52
    print("\nC2 commands parsed=%d ; named codes without a managed case: %s"
          % (len(cmds), missing or "none"))
    results.append(("C2", "every named code has a parsed managed handler", ok2))

    # -- C3: every callback site resolves.  60 of 204 did not until the `or`/`bts`/`movzx` forms
    #        were modelled, and an unresolved site is a silently missing code, not a neutral one.
    unresolved = [s for s in namer.cb.sites if s.code is None]
    forms = {}
    for s in namer.cb.sites:
        forms[s.form] = forms.get(s.form, 0) + 1
    print("\nC3 sites=%d unresolved=%d  encodings=%s"
          % (len(namer.cb.sites), len(unresolved), forms))
    results.append(("C3", "every callback site resolves to a command code", not unresolved))

    # -- C4: THE DISJOINTNESS NULL (see the module docstring)
    dbg_high = {op for op, r in ops.items()
                if r.get("confidence") == "high" and C.MANAGED_ABI_MARKER not in r["evidence"]}
    overlap = sorted(dbg_high & set(named))
    calib = sorted(op for op in A.CALIBRATION_OPS if sweep[op].via)
    print("\nC4 R2 debug-string high rows=%d ; overlap with callback names=%s ; "
          "of the 12 calibration ops, %s reach the callback"
          % (len(dbg_high), overlap or "none", calib or "none"))
    results.append(("C4", "the two evidence lanes are disjoint", not overlap and not calib))

    # -- C5: the cross-check against the managed handler's own shape
    checks = {op: C.crosscheck(op, v, namer.dll.handler(op), msigs) for op, v in named.items()}
    agree = [op for op, c in checks.items() if c.verdict == "AGREE"]
    flags = {op: checks[op].note for op in checks if checks[op].verdict == "FLAG"}
    print("\nC5 cross-check %d/%d agree" % (len(agree), len(checks)))
    for op, note in sorted(flags.items()):
        print("     op %3d FLAG -- %s" % (op, note))
    # The two survivors are the set-and-discard wrapper shape (the managed handler returns the
    # PREVIOUS value and the op throws it away).  They are DISCLOSED, not suppressed -- the gate
    # pins the count so a third one cannot appear unnoticed.
    results.append(("C5", "cross-check agrees except the 2 disclosed set-and-discard wrappers",
                    len(flags) == 2 and set(flags) == {160, 213}))

    # -- C6: the dictionary really carries the round, and single-writer
    carried = {op for op, r in ops.items() if r.get("callback_command")}
    named_rows = {op for op in carried if ops[op]["name"] == ops[op]["callback_command"]}
    ok6 = carried == set(named) and len(A.check_confidence_rule(ops)) == 0
    print("\nC6 hle_ops.json rows carrying a callback_command=%d (named from it: %d) ; "
          "confidence-rule violations=%d"
          % (len(carried), len(named_rows), len(A.check_confidence_rule(ops))))
    results.append(("C6", "hle_ops.json carries the round and the confidence contract holds", ok6))

    _hdr("CB GATES")
    for k, desc, ok in results:
        print("%-5s %-62s %s" % (k, desc, "PASS" if ok else "FAIL"))
    npass = sum(1 for _, _, ok in results if ok)
    print("=" * 72)
    print("%d/%d gates pass" % (npass, len(results)))
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
