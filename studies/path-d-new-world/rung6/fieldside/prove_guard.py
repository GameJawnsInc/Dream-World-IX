#!/usr/bin/env python
"""Break `inject_worldjump.verify()` on purpose and prove it REFUSES.

A verifier nobody has ever seen fail is not evidence ([[feedback-a-check-that-cannot-fail]]).
This harness runs the real splice against a real built `.eb`, then re-runs it with four
deliberate defects injected, and prints what each one is caught by. Expected output:

    A control: the real splice                           -> PASS (no failures)
    B pre-existing entry 2 silently mutated              -> REFUSED
    C region present but never armed                     -> REFUSED
    D right splice, wrong world asserted                 -> REFUSED

Usage (needs a built, UNPATCHED EVT_PATHDGATE.eb.bytes -- see README.md step 1):

    py prove_guard.py <path to an unpatched EVT_PATHDGATE.eb.bytes>
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import inject_worldjump as J                                    # noqa: E402
from ff9mapkit.eb import EbScript                               # noqa: E402  (J bootstraps sys.path)

INITREGION_OP = 0x08
NOTHING_OP = 0x00


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    src = Path(argv[0])
    old = src.read_bytes()
    _, base_degen, base_wm = J.decode_report(old)
    if base_wm:
        print(f"{src} is ALREADY patched (carries {base_wm!r}); point me at an unpatched build")
        return 2

    def run(label: str, mutate=None, world_id: int = J.WORLD_ID) -> bool:
        new, slot, body = J.patch_bytes(old, world_id=J.WORLD_ID, x=J.LANDING_X, z=J.LANDING_Z,
                                        face=J.LANDING_FACE, y=J.LANDING_Y_SEED,
                                        corners=J.ZONE_CORNERS)
        if mutate is not None:
            new, slot, body = mutate(new, slot, body)
        fails = J.verify(new, old=old, slot=slot, body=body, world_id=world_id,
                         corners=J.ZONE_CORNERS, baseline_degenerate=base_degen)
        print(f"{label:<52} -> {'PASS (no failures)' if not fails else 'REFUSED'}")
        for m in fails:
            print(f"      - {m}")
        return not fails

    def corrupt_other_entry(new, slot, body):
        """Flip one bit inside a LANDMARK PROP's Init -- a function the splice never touches."""
        eb = EbScript.from_bytes(new)
        f = eb.entry(2).func_by_tag(0)
        b = bytearray(new)
        b[f.abs_start + 3] ^= 0x01
        return bytes(b), slot, body

    def unarm(new, slot, body):
        """The historical failure mode: the region is present and perfect but never armed
        (an `fpos` fix-up bug once left a 3rd+ region silently un-armed). Blank the
        `InitRegion` to same-length NOTHINGs so nothing about the layout changes."""
        eb = EbScript.from_bytes(new)
        m = eb.entry(0).func_by_tag(0)
        ins = next(i for i in eb.instrs(m) if i.op == INITREGION_OP and i.imm(0) == slot)
        b = bytearray(new)
        b[ins.off:ins.end] = bytes([NOTHING_OP]) * (ins.end - ins.off)
        return bytes(b), slot, body

    ok = run("A control: the real splice")
    caught = [
        not run("B pre-existing entry 2 silently mutated", corrupt_other_entry),
        not run("C region present but never armed", unarm),
        not run("D right splice, wrong world asserted", world_id=9009),
    ]
    print()
    print(f"control passes: {ok}   defects caught: {sum(caught)}/3")
    return 0 if (ok and all(caught)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
